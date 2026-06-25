"""
sabrina_lethal = v1 + 1-turn lethal search (gated+fallback).

This is an EXACT copy of Sabrina v1 (same 60-card deck, same AlakazamPolicy piloting logic,
kept VERBATIM) plus an OPTIONAL 1-turn lethal-search layer that runs the REAL forward model
of the cg engine (search_begin / search_step / search_release) to CONFIRM and ORDER a
finishing line the rule-based policy already believes is reachable. Same idea the Top of the
ladder uses (rule-based + lethal search via the Search API), but on a very short leash:

  - GATED: the search only fires at the MAIN root of OUR turn, when an ATTACK option is
    present AND the v1 helpers already say a realistic finish exists (Powerful-Hand
    quasi-lethal, or Boss+attack that closes on prizes). Never in sub-selects, never as
    per-turn exploration -> ~1-3 remate turns/game, not 1/turn.
  - BOUNDED HARD: tiny wall/hard time caps (FMA_LETHAL_WALL_S / FMA_LETHAL_HARD_S), node
    and depth caps, a narrow beam, and search_release on EVERY opened state. A descontrolled
    search on the native cg .so would hang the process = instant-loss timeout, so the bounds
    are strict and a blown budget aborts to fallback.
  - FALLBACK GUARANTEED: the whole layer is wrapped in try/except with a fallback to the
    EXACT v1 rule-based selection. If the search is off, fails, times out, or can't confirm
    a win, the agent plays IDENTICALLY to v1 — never worse, never a crash. The lethal search
    only ever RE-ORDERS the root pick toward a motor-confirmed winning line; if the confirmed
    line starts with the same action v1 would play, nothing changes (parity).
  - KILLSWITCH: FMA_LETHAL_OFF=1 disables everything (paridad garantizada). Default is OFF
    unless FMA_LETHAL_ON=1 — arrancar OFF y activar solo si el smoke da 0-crash/0-timeout y
    el ladder no baja de 826.9.
  - OVERAGE FLOOR: if remainingOverageTime < FMA_LETHAL_OVERAGE_FLOOR, skip the search and
    play fast (a timeout = derrota instantánea, no vale el finish).

Below this point the original Sabrina v1 provenance applies verbatim:

Sabrina v1 — Alakazam (Abra->Kadabra->Alakazam, Powerful Hand) rule-based agent.

Provenance: forked from ptcg-abc/agents/alakazam/main.py (the tuned AlakazamPolicy,
divergence-mined vs the Elo>=1150 pool + cabt-measured) and packaged into FMA as the
"Sabrina v1" line (AGENTS.md trainer<->deck: Alakazam -> Sabrina). The piloting logic is
kept VERBATIM; FMA only hardens the survival scaffolding to the champion standard:
  - repetition-safe _legal_fallback / normalize_selection (handles minCount > #options),
  - final _validate of the policy output vs the raw select (illegal -> legal fallback),
  - non-raising module load (a missing deck.csv degrades instead of killing the module).

HONEST BASELINE: ptcg-abc's Alakazam scored ~674 on the real ladder (BELOW our Dragapult
floor 774-879). The pivot thesis is that the ARCHETYPE has headroom (55% top-tier WR; a
non-psychic Alakazam reached 5th with no search), but the PILOT underperforms it. So
Sabrina v1 is the validated FLOOR of the new line to mine piloting from -- NOT a day-1
Dragapult-beater. Validate on the REAL ladder (local cabt is a filter, not a judge); keep
Dragapult (Leon v1) in a slot as the verified floor. The 'not-psychic-5th' kernel is not
local (403 on kernel download) -- closing the 674->~1014 gap is v2 piloting work
(divergence mining vs the Elo>=1150 Alakazam pool).

Variant choice is evidence-based: alakazam_mist is excluded (ladder-regressed,
907.8 < 1006.7 per ptcg-abc). Base alakazam goes FIRST -- a Stage-2 line wants the extra
turn to set up before it must attack, mitigating the Stage-2 startup risk.

NB: `agent` MUST stay the LAST top-level callable (kaggle get_last_callable picks it).
"""
from __future__ import annotations

import os
import time
from collections import defaultdict

from cg.api import (
    AreaType, Card, CardType, EnergyType, Observation, OptionType, Pokemon,
    SelectContext, all_card_data, all_attack, to_observation_class,
)

# ── lethal-search API (degrade gracefully if unavailable) ─────────────────────
# These are the cg Search API entry points. If they cannot be imported (older cg,
# packaging variation), _SEARCH_OK stays False and the agent is pure v1 forever.
_SEARCH_OK = True
_SEARCH_ERR = None
try:
    from cg.api import search_begin, search_step, search_end, search_release
except Exception as _se:   # pragma: no cover
    _SEARCH_OK = False
    _SEARCH_ERR = _se


# ── Card IDs (胡地小人 / Alakazam + Dudunsparce single-prize) ─────────────────
class C:
    ABRA = 741            # Basic -> Kadabra
    KADABRA = 742         # Stage1 (Psychic Draw on evolve) -> Alakazam
    ALAKAZAM = 743        # Stage2 attacker: Powerful Hand = 20 dmg x cards in hand
    ALAKAZAM_PSY = 245    # Stage2 TECH (1x): Psychic = 10 + 50/energy on opp Active.
                          # It does DAMAGE (not counters) -> bypasses Mist Energy; punishes
                          # energy-loaded ex. Our answer to Mist decks (Dragapult/Crustle).
    DUNSPARCE = 65        # Basic -> Dudunsparce (id65 = the top-pilot consensus printing; id305
                          # is the other Dunsparce printing — both evolve into Dudunsparce 66)
    DUDUNSPARCE = 66      # Stage1 draw engine (Run Away Draw)
    PSYDUCK = 858         # Damp (ability lock tech)
    SHAYMIN = 343         # Flower Curtain (protect non-Rule-Box bench)
    GENESECT = 142        # ACE Nullifier (with tool)

    PSYCHIC_ENERGY = 5
    TELEPATH_ENERGY = 19  # special, provides {P}
    ENRICHING_ENERGY = 13 # ACE SPEC energy

    BUDDY_POFFIN = 1086
    POKE_PAD = 1152
    HILDA = 1225          # Supporter: search Evolution + Energy
    DAWN = 1231           # Supporter: search Basic+Stage1+Stage2
    RARE_CANDY = 1079
    BOSS_ORDERS = 1182
    BATTLE_CAGE = 1264    # Stadium: block bench damage counters
    ENHANCED_HAMMER = 1081  # Item: discard a Special Energy from opp (e.g. Mist Energy)
    LUCKY_HELMET = 1156   # Tool: draw 2 when damaged
    WONDROUS_PATCH = 1146
    NIGHT_STRETCHER = 1097
    SACRED_ASH = 1129
    LANA_AID = 1184


POWERFUL_HAND = 1072   # Alakazam 743: place 2 counters (20 dmg) per card in hand, on opp Active
PSYCHIC_ATK = 339      # Alakazam 245: 10 + 50 per energy on opp Active (DAMAGE; bypasses Mist)
STRANGE_HACKING = 338  # Alakazam 245: confuse + move opp's damage counters around
SUPER_PSY_BOLT = 1071  # Kadabra: 30
ALAKAZAM_IDS = {743, 245}   # both Stage-2 Alakazam attackers (Powerful Hand / Psychic)
ABRA_TELEPORT = 1070   # Abra: 10 + switch
DUDUN_LAND_CRUSH = 76  # Dudunsparce: 90 (rarely; engine instead)
DUNSPARCE_TRADE = 423  # Dunsparce: switch
DUNSPARCE_RAM = 424

ENERGY_TYPES = {C.PSYCHIC_ENERGY, C.TELEPATH_ENERGY, C.ENRICHING_ENERGY}
ATTACKER_IDS = {C.ALAKAZAM, C.KADABRA}
LOW_DECK_COUNT = 6
pre_turn = -1

_DIAG = {"decisions": 0, "policy_ok": 0, "policy_fallback": 0,
         "obs_fallback": 0, "deck_returns": 0, "errors": {},
         # lethal-search observability (never affects play)
         "lethal_gate_pass": 0, "lethal_searched": 0, "lethal_confirmed": 0,
         "lethal_override": 0, "lethal_skip_budget": 0, "lethal_aborted": 0,
         "lethal_errors": 0, "lethal_max_s": 0.0}


def _diag_record_error(exc):
    k = type(exc).__name__ + ": " + str(exc)[:160]
    _DIAG["errors"][k] = _DIAG["errors"].get(k, 0) + 1


def diag_reset():
    _DIAG.update({"decisions": 0, "policy_ok": 0, "policy_fallback": 0,
                  "obs_fallback": 0, "deck_returns": 0, "errors": {},
                  "lethal_gate_pass": 0, "lethal_searched": 0, "lethal_confirmed": 0,
                  "lethal_override": 0, "lethal_skip_budget": 0, "lethal_aborted": 0,
                  "lethal_errors": 0, "lethal_max_s": 0.0})


def diag_snapshot():
    s = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DIAG.items()}
    s["fallback_rate"] = (s.get("policy_fallback", 0) + s.get("obs_fallback", 0)) / max(1, s["decisions"])
    s["deck_ok"] = globals().get("_DECK_OK", True)
    s["lethal_enabled"] = _lethal_enabled()
    s["search_ok_load"] = _SEARCH_OK
    s["search_err"] = repr(_SEARCH_ERR) if _SEARCH_ERR is not None else None
    return s


def _resolve_deck_path():
    import sys
    cands = []
    if "__file__" in globals():
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deck.csv"))
    cands += ["deck.csv", "/kaggle_simulations/agent/deck.csv"]
    cands += [os.path.join(p, "deck.csv") for p in sys.path if p]
    for p in cands:
        try:
            if os.path.exists(p):
                return p
        except Exception:
            continue
    return None


def _load_deck():
    # FMA hardening: never raise at import (a missing/short deck.csv must degrade, not
    # kill the whole module so `agent` is never even defined). deck.csv always ships.
    path = _resolve_deck_path()
    if not path:
        return []
    try:
        with open(path) as f:
            return [int(x) for x in f.read().splitlines() if x.strip()][:60]
    except Exception:
        return []


my_deck = _load_deck()
# FMA: surface a packaging error (missing/short deck.csv) in diag, never abort import.
_DECK_OK = (len(my_deck) == 60)

all_card = all_card_data()
card_table = {c.cardId: c for c in all_card}

# Active-ability Item-lock cards (Tyranitar / Jellicent ex …). Some lock cards
# (e.g. Budew) carry the effect without an exposed skill, so we ALSO detect lock
# from game state (hold Items but none playable) — see AlakazamPolicy._item_locked.
ITEM_LOCK_IDS = set()
for _c in all_card:
    for _s in (_c.skills or []):
        _t = (_s.text or '')
        if 'Item' in _t and 'Active Spot' in _t and 'play' in _t and ('opponent' in _t or 'neither' in _t):
            ITEM_LOCK_IDS.add(_c.cardId)

# CRITICAL for Alakazam: Powerful Hand "places damage counters" = an EFFECT, so a
# target that "prevents all effects of attacks done to it" takes 0 from it.
#   - special energies that grant this (Mist Energy 11, Rock Fighting Energy 20)
#   - Pokémon/Tools whose own ability prevents effects of attacks done to itself
EFFECT_PREVENT_ENERGY = set()
EFFECT_PREVENT_SELF = set()
for _c in all_card:
    _ct = _c.cardType
    for _s in (_c.skills or []):
        _t = (_s.text or '')
        if 'effects of attacks' in _t and 'prevent' in _t.lower():
            if _ct in (CardType.SPECIAL_ENERGY, CardType.BASIC_ENERGY):
                EFFECT_PREVENT_ENERGY.add(_c.cardId)
            elif 'to this Pokémon' in _t or 'to this Pok' in _t:
                EFFECT_PREVENT_SELF.add(_c.cardId)

# GENERAL energy rule: attach only what an attack costs — never over-fill — UNLESS the attack
# scales with energy attached to ITSELF (then more = more damage). Disruption (energy removal)
# is handled automatically: it drops the count back below the need, so we just refill.
ATTACK_COST = {}                 # attackId -> number of energies in its cost
ATTACK_COST_ENERGIES = {}        # attackId -> list of required EnergyType (0=Colorless, 5=Psychic…)
SELF_SCALING_ATTACKS = set()     # attacks whose damage grows with energy on the attacker
for _a in all_attack():
    ATTACK_COST[_a.attackId] = len(_a.energies or [])
    ATTACK_COST_ENERGIES[_a.attackId] = list(_a.energies or [])
    _t = (_a.text or '').lower()
    if 'for each' in _t and 'energy attached to this' in _t:
        SELF_SCALING_ATTACKS.add(_a.attackId)

# What TYPE each energy card provides (Enriching -> Colorless 0; Telepath/Basic {P} -> Psychic 5).
# Critical: attaching energy must satisfy the attack's TYPE requirement, not just its count.
ENERGY_PROVIDES = {}
for _c in all_card:
    if _c.cardType in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY):
        ENERGY_PROVIDES[_c.cardId] = getattr(_c, 'energyType', 0)

# Situational-tech triggers (only bench the tech when the opponent's board warrants it):
#   Shaymin (Flower Curtain) matters ONLY vs bench-damage (spread/snipe) attacks;
#   Psyduck (Damp) matters ONLY vs abilities that require KO-ing the user itself.
BENCH_DAMAGE_ATTACKS = set()
for _a in all_attack():
    _t = (_a.text or '').lower()
    if ('benched' in _t and 'damage' in _t) or ('to each of your opponent' in _t and 'damage' in _t):
        BENCH_DAMAGE_ATTACKS.add(_a.attackId)
SELF_KO_ABILITY_IDS = set()
for _c in all_card:
    for _s in (_c.skills or []):
        _t = (_s.text or '').lower()
        if 'knock out' in _t and ('this pokémon' in _t or 'this pokemon' in _t or 'itself' in _t):
            SELF_KO_ABILITY_IDS.add(_c.cardId)


# ── generic helpers (proven scaffolding) ─────────────────────────────────────
def normalize_selection(ranked, scores, select):
    n = len(select.option)
    minc = max(0, min(select.minCount, n)); maxc = max(minc, min(select.maxCount, n))
    out, seen = [], set()
    for i in ranked:
        if not (0 <= i < n) or i in seen:
            continue
        s = scores[i] if i < len(scores) else 0
        if s > 0 or len(out) < minc:
            out.append(i); seen.add(i)
        if len(out) >= maxc:
            break
    for i in range(n):
        if len(out) >= minc:
            break
        if i not in seen:
            out.append(i); seen.add(i)
    # FMA hardening: if the engine asks for MORE picks than there are distinct options
    # (minCount > n), repeat indices to reach the raw minimum (else the return is too
    # short and the engine rejects it as illegal).
    raw_min = max(0, getattr(select, "minCount", 0) or 0)
    k = 0
    while len(out) < raw_min and n > 0:
        out.append(k % n); k += 1
    return out


def _repeat_to_min(n, minc):
    """First `minc` legal indices, repeating 0..n-1 when minc > n (repetition-safe)."""
    if n <= 0:
        return []
    if minc <= n:
        return list(range(max(0, minc)))
    out = list(range(n)); k = 0
    while len(out) < minc:
        out.append(k % n); k += 1
    return out


def _legal_fallback(select):
    try:
        return _repeat_to_min(len(select.option), max(0, select.minCount or 0))
    except Exception:
        return []


def _legal_fallback_from_dict(obs_dict):
    try:
        sel = obs_dict.get("select") or {}
        return _repeat_to_min(len(sel.get("option") or []), max(0, sel.get("minCount", 0) or 0))
    except Exception:
        return []


def _validate_obj(out, select):
    """True if `out` is a legal selection for this cg select object (FMA final gate)."""
    try:
        if not isinstance(out, list):
            return False
        n = len(select.option)
        minc = max(0, select.minCount or 0)
        maxc = max(minc, select.maxCount or 0)
        if not (minc <= len(out) <= maxc):
            return False
        if not all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < n for i in out):
            return False
        # uniqueness required unless the engine forces repetition (minCount > n)
        if minc <= n and len(set(out)) != len(out):
            return False
        return True
    except Exception:
        return False


def _safe_get(seq, i):
    try:
        if seq is None or i is None or i < 0 or i >= len(seq):
            return None
        return seq[i]
    except Exception:
        return None


def get_card(obs, area, index, pi):
    try:
        player = obs.current.players[pi]
        match area:
            case AreaType.DECK: return _safe_get(getattr(obs.select, "deck", None), index)
            case AreaType.HAND: return _safe_get(getattr(player, "hand", None), index)
            case AreaType.DISCARD: return _safe_get(getattr(player, "discard", None), index)
            case AreaType.ACTIVE: return _safe_get(getattr(player, "active", None), index)
            case AreaType.BENCH: return _safe_get(getattr(player, "bench", None), index)
            case AreaType.PRIZE: return _safe_get(getattr(player, "prize", None), index)
            case AreaType.STADIUM: return _safe_get(getattr(obs.current, "stadium", None), index)
            case AreaType.LOOKING: return _safe_get(getattr(obs.current, "looking", None), index)
            case _: return None
    except Exception:
        return None


def prize_count(p):
    d = card_table.get(p.id)
    return (3 if d.megaEx else 2 if d.ex else 1) if d else 1


def is_energy(cid):
    d = card_table.get(cid)
    return cid in ENERGY_TYPES or (d is not None and d.cardType in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY))


# ── Alakazam policy ──────────────────────────────────────────────────────────
class AlakazamPolicy:
    def __init__(self, obs: Observation):
        self.obs = obs
        self.state = obs.current
        self.select = obs.select
        self.context = self.select.context
        self.my_index = self.state.yourIndex
        self.op_index = 1 - self.my_index
        self.me = self.state.players[self.my_index]
        self.opponent = self.state.players[self.op_index]
        self.stadium_id = self.state.stadium[0].id if self.state.stadium else 0
        self.field = defaultdict(int)
        self.hand = defaultdict(int)
        self.discard = defaultdict(int)
        for p in self._my_board():
            if p is not None:
                self.field[p.id] += 1
        for c in self.me.hand:
            self.hand[c.id] += 1
        for c in self.me.discard:
            self.discard[c.id] += 1

    def _my_board(self):
        return self.me.active + self.me.bench

    def _low_deck(self):
        return self.me.deckCount <= LOW_DECK_COUNT

    def _deck_preserve(self):
        """Don't mill ourselves out of a WINNING game (real-ladder bug: we filtered our
        deck to 0 while ahead enough to close). If we already have a powered attacker and a
        hand big enough to keep KO-ing (Powerful Hand = 20×hand), we don't NEED more cards —
        and once the deck is down to about the number of prizes we still have to take, every
        extra optional draw/filter risks decking out before the last prize. So: stop optional
        drawing and just attack ~1 KO per turn, keeping enough deck to draw 1/turn to the end."""
        if not self._have_attacker():
            return False
        opp = self.opponent.active[0] if self.opponent.active else None
        if opp is None:
            return False
        remaining_prizes = len(self.me.prize)                 # ≈ turns we still need
        big_hand = 20 * self.me.handCount >= max(opp.hp, 130)  # can essentially KO a body now
        deck_low = self.me.deckCount <= remaining_prizes + 4   # keep a draw-1/turn buffer
        return big_hand and deck_low

    def _hand_size(self):
        return self.me.handCount

    def _energy_count(self, p):
        return len(p.energies) if p is not None else 0

    @staticmethod
    def _can_pay(attached, cost):
        """Can `attached` (list of EnergyType) pay `cost` (list of EnergyType, 0=Colorless)?
        Specific-type requirements must be met by that exact type; Colorless by anything left."""
        from collections import Counter
        have = Counter(attached)
        colorless = 0
        for req in cost:
            if req == EnergyType.COLORLESS:
                colorless += 1
            elif have.get(req, 0) > 0:
                have[req] -= 1
            else:
                return False            # e.g. a Psychic requirement with only Colorless attached
        return sum(have.values()) >= colorless

    def _can_attack(self, p):
        """TYPE-AWARE: can p actually pay one of its attacks with its currently attached
        energy? (1 Enriching = Colorless does NOT pay Powerful Hand's Psychic cost.)"""
        c = card_table.get(p.id)
        if c is None:
            return False
        attached = list(p.energies or [])
        return any(aid in ATTACK_COST_ENERGIES and self._can_pay(attached, ATTACK_COST_ENERGIES[aid])
                   for aid in (c.attacks or []))

    def _should_fuel(self, p):
        """Attach more energy ONLY while p still can't pay an attack (type-aware), so we never
        over-fill — UNLESS an attack scales with its own energy (then keep attaching)."""
        c = card_table.get(p.id)
        if c is None or not (c.attacks or []):
            return False
        if any(aid in SELF_SCALING_ATTACKS for aid in c.attacks):
            return True
        return not self._can_attack(p)

    def _attach_helps(self, p, src):
        """Would attaching energy `src` actually let p pay an attack it currently can't?
        (A Colorless Enriching onto a Psychic-needing Alakazam does NOT help -> don't waste it.)"""
        if src is None:
            return True
        prov = ENERGY_PROVIDES.get(src.id)
        if prov is None:
            return True
        new = list(p.energies or []) + [prov]
        c = card_table.get(p.id)
        return any(aid in ATTACK_COST_ENERGIES and self._can_pay(new, ATTACK_COST_ENERGIES[aid])
                   for aid in (c.attacks or []))

    def _opp_threatens_bench(self):
        """Opponent has a bench-damaging (spread/snipe) attacker in play -> Shaymin matters."""
        for p in (self.opponent.active + self.opponent.bench):
            c = card_table.get(p.id) if p is not None else None
            if c and any(aid in BENCH_DAMAGE_ATTACKS for aid in (c.attacks or [])):
                return True
        return False

    def _opp_has_self_ko_ability(self):
        """Opponent has an ability that KOs the user itself -> Psyduck (Damp) matters."""
        return any(p is not None and p.id in SELF_KO_ABILITY_IDS
                   for p in (self.opponent.active + self.opponent.bench))

    def _energy_in_hand(self):
        return any(is_energy(c.id) for c in self.me.hand)

    def _psychic_in_hand(self):
        """A {P}-providing energy in hand (the ONLY kind that fuels our attacks — Enriching's
        Colorless does not). 'Energy in hand' that is just Enriching still leaves us starved."""
        return any(ENERGY_PROVIDES.get(c.id) == EnergyType.PSYCHIC for c in self.me.hand)

    def _energy_starved(self):
        """We have an Alakazam-line attacker in play (or a Kadabra + Alakazam in hand to
        evolve) that CAN'T attack, and no usable {P} energy in hand to fix it. With only 6
        energy in 60 cards, energy is the bottleneck — searches should grab a {P} energy."""
        bodies = [p for p in (self.me.active + self.me.bench) if p is not None]
        has_alakazam = any(p.id in ALAKAZAM_IDS for p in bodies)
        coming = any(p.id == C.KADABRA for p in bodies) and self.hand[C.ALAKAZAM] > 0
        if not (has_alakazam or coming):
            return False
        if any(p.id in ALAKAZAM_IDS and self._can_attack(p) for p in bodies):
            return False                       # already have an attacker that can actually attack
        return not self._psychic_in_hand()

    def _effect_prevented(self, target):
        """True if attack EFFECTS done to `target` are prevented (Mist Energy / Rock
        Fighting Energy attached, or a self-prevention ability). Powerful Hand places
        damage counters = an effect, so it does 0 to such a target."""
        if target is None:
            return False
        if target.id in EFFECT_PREVENT_SELF:
            return True
        for e in (getattr(target, 'energyCards', None) or []):
            if getattr(e, 'id', None) in EFFECT_PREVENT_ENERGY:
                return True
        return False

    def _opp_active_has_prevent_energy(self):
        """Opponent's Active has Mist/Rock-Fighting special energy blocking Powerful
        Hand — Enhanced Hammer should strip it before we attack."""
        opp = self.opponent.active[0] if self.opponent.active else None
        if opp is None:
            return False
        return any(getattr(e, 'id', None) in EFFECT_PREVENT_ENERGY
                   for e in (getattr(opp, 'energyCards', None) or []))

    # — damage —
    def _alakazam_damage(self, attack_id, target):
        if target is None:
            return 0
        if attack_id == POWERFUL_HAND:
            if self._effect_prevented(target):
                return 0                     # Mist Energy etc. negates "place counters"
            return 20 * self._hand_size()    # counter placement -> no weakness
        if attack_id == PSYCHIC_ATK:
            # 245 Alakazam: 10 + 50 per energy on opp Active. This is DAMAGE, so it goes
            # THROUGH Mist Energy and applies Weakness — our answer to Mist/energy decks.
            dmg = 10 + 50 * len(target.energies)
        elif attack_id == SUPER_PSY_BOLT:
            dmg = 30
        elif attack_id == ABRA_TELEPORT:
            dmg = 10
        elif attack_id == DUNSPARCE_RAM:
            dmg = 20
        elif attack_id == DUDUN_LAND_CRUSH:
            dmg = 90
        else:
            dmg = 0
        od = card_table.get(target.id)
        if od is not None:
            if od.weakness == EnergyType.PSYCHIC:
                dmg *= 2
            elif od.resistance == EnergyType.PSYCHIC:
                dmg = max(0, dmg - 30)
        return dmg

    def _active_best_dmg(self, target):
        a = self.me.active[0] if self.me.active else None
        if a is None or target is None:
            return 0
        if self._energy_count(a) >= 1:
            if a.id == C.ALAKAZAM:
                return self._alakazam_damage(POWERFUL_HAND, target)
            if a.id == C.ALAKAZAM_PSY:
                return self._alakazam_damage(PSYCHIC_ATK, target)
            if a.id == C.KADABRA:
                return self._alakazam_damage(SUPER_PSY_BOLT, target)
        return 0

    def _gust_ko_targets(self):
        return [p for p in self.opponent.bench if p is not None and self._active_best_dmg(p) >= p.hp]

    def _target_value(self, p):
        """Tactical worth of removing opponent Pokémon p (ported from the official
        sample agents): prizes + invested energy/tools + evolution stage; avoid
        wasting a KO on a disposable draw-support basic."""
        d = card_table.get(p.id)
        s = prize_count(p) * 1000
        s += len(p.energies) * 150
        s += len(getattr(p, 'tools', []) or []) * 100
        if d is not None:
            if getattr(d, 'stage2', 0):
                s += 250
            elif getattr(d, 'stage1', 0):
                s += 130
        if p.id in (144, 322, 323, 337):     # Squawkabilly ex / Noctowl / Fan Rotom / Archaludon ex
            s -= 200
        if p.id == 112 and len(p.energies) >= 1:   # Munkidori (key disruptor)
            s += 300
        s += getattr(p, 'hp', 0)
        return s

    def _gust_value(self, p):
        d = self._active_best_dmg(p)
        if d >= p.hp:
            if prize_count(p) >= len(self.me.prize):
                return 90000        # KO-ing this wins the game — gust it
            return 8000 + self._target_value(p)
        return max(1, d)

    # — entry —
    def rank(self):
        if not self.select.option or self.select.maxCount == 0:
            return [], []
        scores = [self._score(o) for o in self.select.option]
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return ranked, scores

    def choose(self):
        ranked, scores = self.rank()
        return normalize_selection(ranked, scores, self.select)

    def _score(self, o):
        t = o.type
        # First-or-second: GO FIRST. The Elo≥1150 Alakazam pool goes first 35/35 (unanimous) —
        # a setup/evolution deck wants the extra turn to build the Abra→Kadabra→Alakazam line and
        # get the Dudunsparce draw engine online before it has to attack. (Was hardcoded second.)
        if self.context == SelectContext.IS_FIRST:
            return 100 if t == OptionType.YES else 0
        if t == OptionType.NUMBER:
            return o.number if o.number is not None else 0
        if t == OptionType.YES:
            return 1
        if t == OptionType.NO:
            return 0
        if t == OptionType.CARD:
            return self._score_card(o)
        if t == OptionType.PLAY:
            return self._score_play(o)
        if t in (OptionType.ENERGY, OptionType.ATTACH):
            return self._score_attach(o)
        if t == OptionType.EVOLVE:
            return self._score_evolve(o)
        if t == OptionType.ABILITY:
            return self._score_ability(o)
        if t == OptionType.RETREAT:
            return self._score_retreat()
        if t == OptionType.ATTACK:
            return self._score_attack(o)
        if t == OptionType.END:
            return 0
        return 0

    def _item_locked(self):
        """Are we Item-locked (can't play Item cards)? Detect from a known lock
        ability on the opponent's Active, OR from game state: we hold Item card(s)
        but the engine offers no way to play any of them."""
        opp = self.opponent.active[0] if self.opponent.active else None
        if opp is not None and opp.id in ITEM_LOCK_IDS:
            return True
        items = [c for c in self.me.hand
                 if card_table.get(c.id) is not None and card_table[c.id].cardType == CardType.ITEM]
        if not items:
            return False
        for o in self.select.option:
            if o.type == OptionType.PLAY:
                c = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
                if c is not None and card_table.get(c.id) is not None and card_table[c.id].cardType == CardType.ITEM:
                    return False   # an Item is playable → not locked
        return True

    def _bench_attacker_ready(self):
        """A benched Alakazam that already has the energy to attack (Powerful Hand
        needs 1 {P}). If one exists, we want IT active, not a Dunsparce/Dudunsparce."""
        return any(p is not None and p.id in ALAKAZAM_IDS and self._energy_count(p) >= 1
                   for p in self.me.bench)

    # — abilities —
    def _score_ability(self, o):
        card = get_card(self.obs, o.area, o.index, self.my_index)
        if card is None:
            return 0
        if card.id == C.DUDUNSPARCE:
            # Run Away Draw: draw 3 + shuffle this Pokémon back into the deck.
            if self.me.deckCount <= 7:        # hard deck-out floor
                return -1
            if o.area != AreaType.BENCH:
                # ACTIVE copy: CYCLE this weak active out and promote a ready benched
                # attacker (or escape Item-lock), then attack the same turn. This is
                # REPOSITIONING TO ATTACK, not filtering — so it is ALWAYS allowed, even in
                # deck-preserve mode (getting the powered Alakazam active to swing is the
                # whole point). Bug fixed: gating this on _deck_preserve stranded a powered
                # Alakazam on the bench (Dudunsparce active, 0 energy, can't retreat) -> no
                # attacks -> no_offense loss.
                if self._item_locked() or self._bench_attacker_ready():
                    return 14000
                return -1
            # BENCHED copy = the draw engine (pure filtering). Draw-engine decks WIN by
            # drawing aggressively (big hand = big Powerful Hand) — blanket deck-out guards
            # regressed cabt — so we draw, EXCEPT: when we already have a winning hand and the
            # deck is low, stop filtering ourselves out of a won game (real-ladder bug).
            if self._deck_preserve():
                return -1
            # NB: top pilots activate Run Away Draw ~1/4 as often as we did (MAIN ABILITY 163 vs
            # our 622) — but a blunt hand-cap gave ~0 divergence gain here and risks the documented
            # cabt regression (deck-out guards hurt cabt), so we keep the aggressive-draw identity
            # and leave "draw less" as a separate real-ladder A/B. Only the high-hand floor stays.
            if self.me.handCount >= 14 and self.me.deckCount <= 12:
                return -1
            return 15000
        return 9000

    # — play —
    def _score_play(self, o):
        card = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        if card is None:
            return 0
        d = card_table.get(card.id)
        if d is None:
            return 0
        if d.cardType == CardType.POKEMON:
            return self._score_play_poke(card)
        return self._score_play_trainer(card)

    def _score_play_poke(self, card):
        cid = card.id; n = self.field[cid]
        if cid == C.ABRA:
            return 20000 - 250 * n
        if cid == C.DUNSPARCE:
            return 18500 - 250 * n
        if cid == C.SHAYMIN:
            # Flower Curtain protects the bench from attack damage -> bench it ONLY vs a
            # bench-damage (spread/snipe) opponent; otherwise it just clogs a bench slot.
            return 17000 if (n == 0 and self._opp_threatens_bench()) else -1
        if cid == C.PSYDUCK:
            # Damp only locks self-KO abilities (almost nothing in this meta) -> bench it
            # ONLY when the opponent actually has such an ability in play.
            return 9000 if (n == 0 and self._opp_has_self_ko_ability()) else -1
        if cid == C.GENESECT:
            return 9000 if n == 0 else -1
        return 14000 - 200 * n

    def _alakazam_ready(self):
        a = self.me.active[0] if self.me.active else None
        return a is not None and a.id in ALAKAZAM_IDS and self._energy_count(a) >= 1

    def _need_pieces(self):
        return self.field[C.ALAKAZAM] < 1

    def _open_bench(self):
        return sum(1 for p in self.me.bench if p is not None) < getattr(self.me, "benchMax", 5)

    def _achievable_hand(self):
        """Biggest hand we can realistically reach THIS turn (Powerful Hand = 20×hand):
        current hand + Run Away Draw (+3) + one draw/search Supporter (~+1 net)."""
        extra = 0
        if self.me.deckCount > 7 and any(p is not None and p.id == C.DUDUNSPARCE for p in self.me.bench):
            extra += 3
        if not self.state.supporterPlayed and (self.hand[C.HILDA] or self.hand[C.DAWN]):
            extra += 1
        return self.me.handCount + extra

    def _have_attacker(self):
        a = self.me.active[0] if self.me.active else None
        return (a is not None and a.id in ALAKAZAM_IDS and self._energy_count(a) >= 1) or self._bench_attacker_ready()

    def _ko_active_reachable(self):
        """Can Powerful Hand KO the opponent's ACTIVE this turn — now, or after the
        drawing still available to us? (Each turn, aim to KO the best target: usually
        the dangerous active attacker, by pumping the hand to lethal.)"""
        opp = self.opponent.active[0] if self.opponent.active else None
        return (opp is not None and self._have_attacker()
                and not self._effect_prevented(opp)        # Mist Energy etc. → 0, don't chase it
                and 20 * self._achievable_hand() >= opp.hp)

    def _score_play_trainer(self, card):
        cid = card.id
        ready = self._alakazam_ready()
        if cid == C.RARE_CANDY:
            if self.field[C.ABRA] >= 1 and self.hand[C.ALAKAZAM] >= 1:
                return 20500
            return -1
        opp_active = self.opponent.active[0] if self.opponent.active else None
        # Each turn, if we can KO the dangerous Active this turn by drawing up to a lethal
        # Powerful Hand, DRAW toward it (a draw Supporter beats gusting a weaker target).
        draw_for_ko = (opp_active is not None and self._ko_active_reachable()
                       and 20 * self.me.handCount < opp_active.hp)
        # Winning + deck low: stop spending the deck on draw/search supporters — preserve it
        # so we can draw 1/turn to the finish (Boss's Orders gust is still allowed below).
        if cid in (C.HILDA, C.DAWN, C.POKE_PAD) and self._deck_preserve():
            return -1
        if cid == C.HILDA:
            if self.state.supporterPlayed:
                return -1
            if draw_for_ko:
                return 14000
            return 12500 if self._need_pieces() else 3000
        if cid == C.DAWN:
            if self.state.supporterPlayed:
                return -1
            if draw_for_ko:
                return 13800
            return 12000 if self._need_pieces() else 2500
        if cid == C.BUDDY_POFFIN:
            return 13000 if self._open_bench() else 600
        if cid == C.POKE_PAD:
            return 8500 if self._need_pieces() else 400
        if cid == C.BOSS_ORDERS:
            if self.state.supporterPlayed:
                return -1
            ko = self._gust_ko_targets()
            # If we can KO the Active threat this turn and it's worth at least as much as
            # any benched target, KO IT — don't gust a weaker Pokémon and leave the threat.
            if opp_active is not None and self._ko_active_reachable():
                best_gust = max((self._target_value(p) for p in ko), default=-1)
                if self._target_value(opp_active) >= best_gust:
                    return -1
            if not ko:
                return -1
            best = max(ko, key=self._gust_value)
            if opp_active is not None and self._active_best_dmg(opp_active) >= opp_active.hp \
                    and prize_count(opp_active) >= prize_count(best):
                return -1
            return 13500
        if cid == C.ENHANCED_HAMMER:
            # Strip Mist/effect-prevention Special Energy off the opponent's Active so
            # Powerful Hand stops doing 0. Do it BEFORE drawing/attacking.
            if self._opp_active_has_prevent_energy():
                return 16000
            # otherwise only worth it if the opponent has any Special Energy to remove
            if any(card_table.get(getattr(e, 'id', None)) is not None
                   and card_table[e.id].cardType == CardType.SPECIAL_ENERGY
                   for p in (self.opponent.active + self.opponent.bench) if p is not None
                   for e in (getattr(p, 'energyCards', None) or [])):
                return 1500
            return -1
        if cid == C.BATTLE_CAGE:
            if self.state.stadiumPlayed or self.stadium_id == C.BATTLE_CAGE:
                return -1
            return 9500
        if cid == C.LUCKY_HELMET:
            return 7000 if not ready else 1000
        if cid == C.NIGHT_STRETCHER:
            return 6000 if (self.discard.get(C.ALAKAZAM, 0) or self.discard.get(C.ABRA, 0)) else 300
        if cid == C.LANA_AID:
            if self.state.supporterPlayed:
                return -1
            return 6000 if self._low_deck() else 1500
        if cid == C.SACRED_ASH:
            return 6000 if self._low_deck() and self.me.discard else 200
        if cid == C.WONDROUS_PATCH:
            return 7000 if self.discard.get(C.PSYCHIC_ENERGY, 0) and self._open_bench() else 300
        return 9000

    # — evolve —
    def _score_evolve(self, o):
        target = get_card(self.obs, o.inPlayArea, o.inPlayIndex, self.my_index)
        if not isinstance(target, Pokemon):
            return 0
        card = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        cid = card.id if card is not None else None
        if cid == C.ALAKAZAM_PSY:
            # The Psychic tech (bypasses Mist, punishes energy). Make THIS Alakazam only
            # when (a) the opp Active is Mist-protected AND we can't strip it (no Enhanced
            # Hammer in hand), or (b) it's heavily energy-loaded. Otherwise the 743 Powerful
            # Hand (after Enhanced Hammer if needed) is our higher-ceiling main attacker.
            opp = self.opponent.active[0] if self.opponent.active else None
            if opp is not None and ((self._effect_prevented(opp) and self.hand[C.ENHANCED_HAMMER] == 0)
                                    or len(opp.energies) >= 4):
                return 21500
            return 20400
        if cid == C.ALAKAZAM:
            return 21000
        if cid == C.KADABRA:
            return 20000
        if cid == C.DUDUNSPARCE:
            return 19000
        return 18000

    # — attach energy —
    def _score_attach(self, o):
        p = get_card(self.obs, o.inPlayArea, o.inPlayIndex, self.my_index)
        if not isinstance(p, Pokemon):
            return 0
        # GENERAL RULE (type-aware): attach only while the body still can't pay an attack;
        # once it CAN attack, hold the rest (fuels a backup AND +20 Powerful Hand per card).
        if not self._should_fuel(p):
            return -1
        # The source energy must actually enable an attack — a Colorless Enriching onto a
        # Psychic-needing Alakazam does NOT (the bug); hold it / pick a {P} source instead.
        src = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        if not self._attach_helps(p, src):
            return -1
        if p.id in ALAKAZAM_IDS:
            return 8000 + (200 if o.inPlayArea == AreaType.ACTIVE else 0)
        if p.id in (C.ABRA, C.KADABRA):
            return 1500           # pre-fuel the line (energy carries through evolution)
        return -1                 # non-attacker -> don't waste energy, hold it

    # — retreat —
    def _score_retreat(self):
        active = self.me.active[0] if self.me.active else None
        opp = self.opponent.active[0] if self.opponent.active else None
        if active is None or opp is None:
            return -1
        if active.id not in ALAKAZAM_IDS:
            for p in self.me.bench:
                if p is not None and p.id in ALAKAZAM_IDS and self._energy_count(p) >= 1:
                    return 6000
        return -1

    # — attack —
    def _score_attack(self, o):
        active = self.me.active[0] if self.me.active else None
        opp = self.opponent.active[0] if self.opponent.active else None
        if active is None or opp is None:
            return 800
        aid = o.attackId
        if aid in (ABRA_TELEPORT, DUNSPARCE_TRADE):
            # These switch the Active with a benched Pokémon (ends the turn). Only worth
            # it to bring up a ready attacker when the current Active isn't one and we
            # can't otherwise swap (Issue 1) — otherwise it's just a wasted reposition.
            if active.id not in ALAKAZAM_IDS and active.id != C.KADABRA and self._bench_attacker_ready():
                return 5000
            return 700
        # Score THIS specific attack by its own damage — not the best available attack.
        # (Strange Hacking 338 does 0 damage, just confuses; scoring it like Psychic made
        # the agent spam it: opponent can't attack, but we deal 0 → stall → we deck out.)
        dmg = self._alakazam_damage(aid, opp)
        if aid == STRANGE_HACKING:
            # Utility only: worth a little to Confuse a threatening Active we can't yet KO,
            # but never over a real attack and never as a stall. Stays below END-beating
            # real attacks; above END so it's a last resort if nothing else can act.
            opp_dangerous = prize_count(opp) >= 2 and self._achievable_hand() * 20 < opp.hp
            return 600 if opp_dangerous else 200
        if dmg <= 0:
            return 500
        # Lethal: if this KO takes our last remaining prize(s), it wins the game now.
        if opp.hp <= dmg and prize_count(opp) >= len(self.me.prize):
            return 90000
        score = 1000 + min(dmg, 320)
        if opp.hp <= dmg:
            score += 2500 + prize_count(opp) * 200
        return score

    # — sub-selects —
    def _score_card(self, o):
        card = get_card(self.obs, o.area, o.index, o.playerIndex)
        if card is None:
            return 0
        ctx = self.context
        # Opponent card targeting (e.g. Enhanced Hammer: discard a Special Energy from
        # opp) — strip the Mist/Rock that's blocking Powerful Hand, prefer the Active.
        if o.playerIndex == self.op_index and not isinstance(card, Pokemon):
            if card.id in EFFECT_PREVENT_ENERGY:
                return 2000 + (500 if getattr(o, 'inPlayArea', None) == AreaType.ACTIVE else 0)
            d = card_table.get(card.id)
            if d is not None and d.cardType == CardType.SPECIAL_ENERGY:
                return 300
            return 50
        if ctx in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
            return self._score_active_choice(o, card)
        if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
            return self._score_setup_active(card)
        if ctx in (SelectContext.SETUP_BENCH_POKEMON, SelectContext.TO_BENCH, SelectContext.TO_FIELD):
            return self._score_to_bench(card)
        if ctx == SelectContext.TO_HAND:
            return self._score_to_hand(card)
        if ctx == SelectContext.ATTACH_TO and isinstance(card, Pokemon):
            return self._score_attach_target(card, o.inPlayArea == AreaType.ACTIVE)
        if ctx in (SelectContext.ATTACH_FROM, SelectContext.TO_HAND_ENERGY):
            return 100 if is_energy(card.id) else 10
        if ctx in (SelectContext.DISCARD, SelectContext.DISCARD_CARD_OR_ATTACHED_CARD,
                   SelectContext.DISCARD_ENERGY, SelectContext.DISCARD_ENERGY_CARD):
            return self._score_discard(card)
        if ctx in (SelectContext.DAMAGE_COUNTER, SelectContext.DAMAGE_COUNTER_ANY):
            if isinstance(card, Pokemon) and o.playerIndex == self.op_index:
                return 10000 + prize_count(card) * 1000 - getattr(card, "hp", 0)
            return 0
        if ctx in (SelectContext.TO_DECK, SelectContext.TO_DECK_BOTTOM, SelectContext.TO_PRIZE):
            return self._score_putback(card)
        return 0

    def _score_attach_target(self, p, is_active):
        if not self._should_fuel(p):
            return -1             # already CAN attack (type-aware) -> don't over-fill
        if p.id in ALAKAZAM_IDS:
            return 8000 + (200 if is_active else 0)
        if p.id in (C.ABRA, C.KADABRA):
            return 1500
        return -1

    def _score_active_choice(self, o, card):
        if not isinstance(card, Pokemon):
            return 0
        if o.playerIndex == self.op_index:
            return self._gust_value(card)
        if o.playerIndex != self.my_index:
            return 0
        # Promote (after a KO) the body that best keeps us in the game:
        #  1) a ready Alakazam (can Powerful Hand now) — energy bonus makes it top.
        #  2) any Alakazam (online next turn after we attach 1).
        #  3) the tankiest survivor (Dudunsparce 140 / Kadabra 80) so we don't just feed
        #     the opponent a free prize off a 50-HP Abra; a Kadabra can also evolve into
        #     Alakazam next turn. NEVER strand the win-con behind a fragile chump-promote.
        # Promotion order MEASURED against the Elo≥1150 Alakazam pool: they promote the
        # EVOLUTION LINE (Abra/Kadabra → becomes the Alakazam attacker), NOT the Dudunsparce
        # wall (a draw-engine dead end that can't pressure). We over-promoted Dudunsparce.
        score = len(card.energies) * 10
        if card.id in ALAKAZAM_IDS:
            score += 200         # a powered Alakazam = our attacker
        elif card.id == C.KADABRA:
            score += 95          # 80 HP, one evolve from Alakazam — keep the line going
        elif card.id == C.ABRA:
            score += 80          # continues the line to Alakazam (top pilots promote it)
        elif card.id == C.DUDUNSPARCE:
            score += 40          # 140 HP wall but a dead end — don't strand the win-con
        elif card.id in (C.PSYDUCK, C.SHAYMIN, C.GENESECT):
            score -= 20          # tech bodies: don't promote into the attacker slot
        score += getattr(card, 'hp', 0) // 30   # mild "promote the survivor" tiebreak
        return score + 1

    def _score_setup_active(self, card):
        # Opening-active choice. MEASURED (in-process cabt, 60 games vs Lucario):
        # opening Abra      -> 26% loss, 0 no-offense (evolves in place -> Alakazam fast)
        # opening Dunsparce -> 57% loss, 5 no-offense (70HP body, no attacker path)
        # opening Psyduck/Genesect (pure tech) -> ~60% loss (fragile, can't ever attack).
        # So: Abra >> Dunsparce > (anything that can become an attacker) >> tech basics.
        # Tech basics (Psyduck 858 / Shaymin 343 / Genesect 142) have NO offensive line
        # and must be the last resort — opening them strands us with a dead active.
        if card is None:
            return 0
        if card.id == C.ABRA:
            return 50          # the evolution line -> Alakazam: always preferred
        if card.id == C.DUNSPARCE:
            return 30          # draw engine; digs into Abra but slow to pressure
        if card.id in (C.PSYDUCK, C.SHAYMIN, C.GENESECT):
            return 1           # pure tech, fragile, no attack -> last resort only
        return 5

    def _score_to_bench(self, card):
        if card is None:
            return 0
        d = card_table.get(card.id)
        if d is None or d.cardType != CardType.POKEMON:
            return 0
        cid = card.id; n = self.field[cid]
        if cid == C.ABRA:
            return 200 - 30 * n
        if cid == C.DUNSPARCE:
            return 180 - 30 * n
        if cid == C.SHAYMIN:
            return 150 if (n == 0 and self._opp_threatens_bench()) else -1
        if cid == C.PSYDUCK:
            return 90 if (n == 0 and self._opp_has_self_ko_ability()) else -1
        return 100 - 20 * n

    def _score_to_hand(self, card):
        if card is None:
            return 0
        cid = card.id
        score = 200 - self.hand[cid] * 40
        # Top pilots search the DRAW ENGINE (Dudunsparce) and the cheap evolution basics first,
        # and DON'T hoard the stage-2 Alakazam (one is enough; it's dead without Kadabra+Candy).
        engine_online = self.field[C.DUDUNSPARCE] >= 1
        if cid == C.DUDUNSPARCE:
            score += 90 if not engine_online else 20    # get the draw engine online
        elif cid == C.DUNSPARCE:
            score += 70 if self.field[C.DUDUNSPARCE] + self.field[C.DUNSPARCE] < 1 else -10
        elif cid == C.ABRA:
            score += 55 if self.field[C.ALAKAZAM] + self.field[C.KADABRA] + self.field[C.ABRA] < 2 else -10
        elif cid == C.KADABRA:
            score += 45
        elif cid == C.ALAKAZAM:
            score += 50 if (self.hand[C.ALAKAZAM] == 0 and self.field[C.ABRA] + self.field[C.KADABRA] >= 1) else -10
        elif is_energy(cid):
            # When starved, fetch a {P} energy (the only kind that fuels our attacks) — an
            # Enriching (Colorless) doesn't help, so don't prioritise it.
            if self._energy_starved() and ENERGY_PROVIDES.get(cid) == EnergyType.PSYCHIC:
                score += 300
            else:
                score += 30
        return score

    def _score_discard(self, card):
        if card is None:
            return 0
        cid = card.id
        if is_energy(cid):
            return 20 if self.hand[cid] >= 3 else -40
        if self.hand[cid] >= 2:
            return 60
        if cid in (C.ABRA, C.KADABRA, C.ALAKAZAM, C.DUNSPARCE, C.DUDUNSPARCE):
            return -50 if self.field[cid] == 0 else 5
        if cid in (C.HILDA, C.DAWN) and self.state.supporterPlayed:
            return 30
        return 0

    def _score_putback(self, card):
        if card is None:
            return 0
        if self.hand[card.id] >= 2:
            return 60
        if card.id in (C.ABRA, C.ALAKAZAM, C.DUNSPARCE):
            return -40
        return 10


# =============================================================================
# LETHAL SEARCH  (1-turn finish confirmation over the REAL cg forward model)
# =============================================================================
# Doctrine (see module docstring): GATED + BOUNDED + FALLBACK. The search NEVER
# explores; it only CONFIRMS and ORDERS a finishing line the rule-based policy
# already believes is reachable, then returns the FIRST action of that line. Every
# path out (off, fail, timeout, no-win-found) returns to the EXACT v1 selection.

# ── tunables (env-overridable; defaults are deliberately tiny) ────────────────
LETHAL_WALL_S = float(os.environ.get("FMA_LETHAL_WALL_S", "0.6"))    # soft per-decision wall
LETHAL_HARD_S = float(os.environ.get("FMA_LETHAL_HARD_S", "1.0"))    # absolute cap
LETHAL_MAX_STEPS = int(os.environ.get("FMA_LETHAL_MAX_STEPS", "64")) # total search_step budget
LETHAL_MAX_DEPTH = int(os.environ.get("FMA_LETHAL_MAX_DEPTH", "8"))  # plies deep into the turn
LETHAL_BEAM = int(os.environ.get("FMA_LETHAL_BEAM", "2"))            # top-K children per node
LETHAL_OVERAGE_FLOOR_S = float(os.environ.get("FMA_LETHAL_OVERAGE_FLOOR", "60"))


def _lethal_enabled():
    """Killswitch + default-OFF. FMA_LETHAL_OFF=1 always disables. Otherwise the
    search is ON only if FMA_LETHAL_ON=1 (arrancar OFF, activar tras smoke verde)."""
    if not _SEARCH_OK:
        return False
    if os.environ.get("FMA_LETHAL_OFF"):
        return False
    return bool(os.environ.get("FMA_LETHAL_ON"))


# Opponent-zone fillers for the determinization (notebook convention): the hidden
# info barely affects OUR intra-turn finishing sequence, so cheap guesses suffice.
_OPP_DECK_FILLER = 1072   # Snorlax-id filler (no deep meaning, just a legal card id)
_OPP_FILLER = 1           # Basic Energy filler for prize/hand
_OPP_ACTIVE_FILLER = 1072 # only used if the opp Active is face-down


def _lethal_gate(pol):
    """TRUE iff the lethal search may fire for this decision. ALL must hold; else
    the agent stays pure v1. `pol` is a freshly-built AlakazamPolicy over obs.

    1. context == MAIN and it's our turn (root node of the turn only).
    2. there is an ATTACK option (no attack this turn -> no finish possible).
    3. a realistic finish exists per the v1 helpers:
       (a) Powerful-Hand quasi-lethal that takes the LAST prize(s) (victory), or
       (b) a jugable Boss Orders that gives a closing gust target.
    Static scoring only -> the search merely CONFIRMS what v1 already believes."""
    try:
        if pol.context != SelectContext.MAIN:
            return False
        if pol.state.yourIndex != pol.my_index:
            return False
        if not any(o.type == OptionType.ATTACK for o in pol.select.option):
            return False
        opp = pol.opponent.active[0] if pol.opponent.active else None
        if opp is None:
            return False
        # (a) Powerful-Hand quasi-lethal that closes the game on prizes.
        finish_a = (pol._ko_active_reachable()
                    and prize_count(opp) >= len(pol.me.prize))
        # (b) Boss Orders jugable + a benched closing target (prize math victory or
        #     a key attacker we otherwise can't reach). Reuse v1's gust helpers.
        finish_b = False
        if not pol.state.supporterPlayed and pol.hand[C.BOSS_ORDERS] >= 1:
            ko = pol._gust_ko_targets()
            for t in ko:
                if prize_count(t) >= len(pol.me.prize) or pol._target_value(t) >= 8000:
                    finish_b = True
                    break
        return bool(finish_a or finish_b)
    except Exception:
        return False


def _lethal_priority(opt):
    """Static prior (a hard order, no softmax) for expanding options toward a KO.
    Higher = expanded first. Used to keep the beam aimed at the finishing line."""
    t = opt.type
    if t == OptionType.ATTACK:
        return 100
    if t == OptionType.EVOLVE:
        return 90
    if t == OptionType.ABILITY:           # Run Away Draw etc. -> pumps the hand
        return 80
    if t in (OptionType.PLAY,):
        return 70
    if t in (OptionType.ENERGY, OptionType.ATTACH):
        return 60
    if t == OptionType.RETREAT:
        return 40
    if t == OptionType.END:
        return -100
    return 10


def _enumerate_lethal_actions(select, policy):
    """Candidate selections for a node, narrowed to the beam. For single-pick nodes
    (the common MAIN case) we use the v1 policy's own ranking so the search explores
    the SAME options v1 prefers, just confirmed by the motor. For multi-pick nodes
    we fall back to the policy choice plus a couple of priority singletons.

    Each entry is a list[int] legal for this select. Empty-pass ([]) is added when
    minCount == 0 (declining is sometimes the path to the attack)."""
    n = len(select.option)
    if n == 0:
        return []
    minc = max(0, select.minCount or 0)
    maxc = max(minc, select.maxCount or 0)
    out = []
    # the v1 policy's preferred full selection for THIS node (always a candidate)
    try:
        pref = policy.choose()
        if _validate_obj(pref, select):
            out.append(list(pref))
    except Exception:
        pass
    # priority-ordered singletons (only meaningful when a single pick is legal)
    if minc <= 1 <= maxc:
        order = sorted(range(n), key=lambda i: _lethal_priority(select.option[i]), reverse=True)
        for i in order:
            cand = [i]
            if cand not in out:
                out.append(cand)
            if len(out) >= LETHAL_BEAM + 1:
                break
    # allow passing when the engine permits it (path to reach the attack node)
    if minc == 0 and [] not in out:
        out.append([])
    # beam cap (keep the v1-preferred first)
    return out[:max(1, LETHAL_BEAM + 1)]


def _state_is_win(search_state, seat):
    """Did the cg engine confirm a WIN for `seat` in this SearchState?
    State.result == seat -> that seat won (0/1 = winner index, 2 = draw, -1 = ongoing)."""
    try:
        st = search_state.observation.current
        return st is not None and st.result is not None and st.result == seat
    except Exception:
        return False


def _lethal_search(obs, seat):
    """Run the bounded lethal search over the REAL forward model. Returns the FIRST
    action (list[int], the root select) of a motor-CONFIRMED winning line, or None.

    Bounds: wall+hard deadline, MAX_STEPS, MAX_DEPTH, beam. search_release on EVERY
    opened state (no leaks). Any failure -> None (caller falls back to v1)."""
    t0 = time.monotonic()
    deadline = t0 + min(LETHAL_WALL_S, LETHAL_HARD_S)
    state = obs.current
    me = state.players[seat]
    opp = state.players[1 - seat]

    # Determinización ÚNICA: our deck/prize guessed from my_deck (the engine ignores
    # your_deck when select.deck != None); opp zones get cheap fillers.
    your_deck_guess = (my_deck * 2)[:me.deckCount] if me.deckCount else []
    your_prize_guess = (my_deck * 2)[:len(me.prize)] if me.prize else []
    opp_deck = [_OPP_DECK_FILLER] * opp.deckCount
    opp_prize = [_OPP_FILLER] * len(opp.prize)
    opp_hand = [_OPP_FILLER] * opp.handCount
    opp_active = ([_OPP_ACTIVE_FILLER]
                  if (len(opp.active) > 0 and opp.active[0] is None) else [])

    opened = []
    steps = [0]
    found = [None]

    def _release_all():
        for sid in opened:
            try:
                search_release(sid)
            except Exception:
                pass
        try:
            search_end()
        except Exception:
            pass

    try:
        root = search_begin(
            obs,
            your_deck=your_deck_guess,
            your_prize=your_prize_guess,
            opponent_deck=opp_deck,
            opponent_prize=opp_prize,
            opponent_hand=opp_hand,
            opponent_active=opp_active,
        )
    except Exception:
        _DIAG["lethal_errors"] += 1
        return None
    opened.append(root.searchId)

    def _expand(search_state, root_action, depth):
        """DFS toward a confirmed finish. root_action is the select taken at the root
        (what we'd ultimately return). Returns True if a win was confirmed."""
        if found[0] is not None:
            return True
        if time.monotonic() >= deadline:
            return False
        if steps[0] >= LETHAL_MAX_STEPS or depth >= LETHAL_MAX_DEPTH:
            return False
        cur_obs = search_state.observation
        cur_state = cur_obs.current
        # terminal?
        if cur_state is not None and cur_state.result is not None and cur_state.result >= 0:
            if cur_state.result == seat:
                found[0] = root_action
                return True
            return False
        sel = cur_obs.select
        if sel is None or not sel.option:
            return False
        # only follow OUR decisions; if it became the opponent's pick we cannot
        # force the line -> treat as not-confirmed (stay conservative).
        if cur_state is not None and cur_state.yourIndex != seat:
            return False
        try:
            cand_policy = AlakazamPolicy(cur_obs)
        except Exception:
            return False
        actions = _enumerate_lethal_actions(sel, cand_policy)
        for act in actions:
            if found[0] is not None:
                return True
            if time.monotonic() >= deadline or steps[0] >= LETHAL_MAX_STEPS:
                break
            steps[0] += 1
            try:
                ns = search_step(search_state.searchId, act)
            except Exception:
                continue   # illegal under this determinization -> skip this branch
            opened.append(ns.searchId)
            ra = root_action if root_action is not None else list(act)
            # quick terminal check before recursing (cheap win confirmation)
            if _state_is_win(ns, seat):
                found[0] = ra
                return True
            if _expand(ns, ra, depth + 1):
                return True
        return False

    try:
        _expand(root, None, 0)
    except Exception:
        _DIAG["lethal_errors"] += 1
        found[0] = None
    finally:
        _release_all()

    dt = time.monotonic() - t0
    if dt > _DIAG["lethal_max_s"]:
        _DIAG["lethal_max_s"] = dt
    return found[0]


def _maybe_lethal(obs, v1_sel):
    """Gated + bounded + fallback wrapper. Returns a selection: either a motor-confirmed
    lethal root action, or v1_sel unchanged. NEVER raises (any error -> v1_sel)."""
    if not _lethal_enabled():
        return v1_sel
    try:
        pol = AlakazamPolicy(obs)
    except Exception:
        return v1_sel
    if not _lethal_gate(pol):
        return v1_sel
    _DIAG["lethal_gate_pass"] += 1
    # overage floor: a timeout = instant loss, skip the finish if we're low on slack.
    try:
        rem = getattr(obs, "remainingOverageTime", None)
        if rem is not None and rem < LETHAL_OVERAGE_FLOOR_S:
            _DIAG["lethal_skip_budget"] += 1
            return v1_sel
    except Exception:
        pass
    try:
        seat = pol.my_index
        _DIAG["lethal_searched"] += 1
        confirmed = _lethal_search(obs, seat)
    except Exception as exc:
        _diag_record_error(exc); _DIAG["lethal_errors"] += 1
        return v1_sel
    if confirmed is None:
        _DIAG["lethal_aborted"] += 1
        return v1_sel
    # the motor confirmed a winning line. Use its first action only if it is legal
    # for the real select; otherwise keep v1 (paranoid validation).
    if not _validate_obj(confirmed, obs.select):
        _DIAG["lethal_aborted"] += 1
        return v1_sel
    _DIAG["lethal_confirmed"] += 1
    if confirmed != v1_sel:
        _DIAG["lethal_override"] += 1
    return confirmed


def agent(obs_dict, config=None):
    # FMA: accept an optional 2nd positional (the kaggle/cabt harness calls agent(obs, config));
    # the ptcg-abc original was 1-arg and crashed the deck-phase probe. config is unused.
    global pre_turn
    try:
        if isinstance(obs_dict, dict) and obs_dict.get("select") is None:
            _DIAG["deck_returns"] += 1
            return my_deck
    except Exception:
        pass
    _DIAG["decisions"] += 1
    try:
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            _DIAG["deck_returns"] += 1; _DIAG["decisions"] -= 1
            return my_deck
        if obs.current is not None and pre_turn != obs.current.turn:
            pre_turn = obs.current.turn
        try:
            sel = AlakazamPolicy(obs).choose()
            if not _validate_obj(sel, obs.select):
                # policy produced an illegal selection -> never return it (FMA: 0 INVALIDs)
                _DIAG["policy_fallback"] += 1
                return _legal_fallback(obs.select)
            _DIAG["policy_ok"] += 1
            # LETHAL LAYER (gated + bounded + fallback): may re-order the root pick
            # toward a motor-confirmed winning line. ANY issue -> returns `sel` (v1
            # parity). Final paranoid validation below guarantees a legal output.
            try:
                out = _maybe_lethal(obs, sel)
                if _validate_obj(out, obs.select):
                    return out
            except Exception as exc:
                _diag_record_error(exc); _DIAG["lethal_errors"] += 1
            return sel
        except Exception as exc:
            _diag_record_error(exc); _DIAG["policy_fallback"] += 1
            return _legal_fallback(obs.select)
    except Exception as exc:
        _diag_record_error(exc); _DIAG["obs_fallback"] += 1
        return _legal_fallback_from_dict(obs_dict if isinstance(obs_dict, dict) else {})
