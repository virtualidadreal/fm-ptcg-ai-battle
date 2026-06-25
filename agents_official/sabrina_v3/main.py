"""
Sabrina v3 — Alakazam (Abra->Kadabra->Alakazam, Powerful Hand) rule-based agent.

PILOTING PROVENANCE / CITA (comp rules §3.6.b / §3.14):
  The FOUR piloting techniques below — (1) damage-budgeting / hand-size estimation,
  (2) safe_draws anti-deckout gating, (3) prize-targeting, (4) ability-need gating —
  are RE-IMPLEMENTED, as our own original work, from the publicly published 5th-place
  agent by sue124 / ryotasueyoshi ("rule-based (not psychic) Alakazam — best 5th",
  rule-based-not-psychic-alakazam-best-5th). That kernel is OSI-licensed/usable per the
  competition rules, but per §3.14 we do NOT ship it verbatim: the LOGIC was studied from
  ryota's main.py + the notebook "Playing Principles" and then re-written here in OUR
  structure and nomenclature (the C.* id namespace, our helpers _can_pay / _should_fuel /
  _effect_prevented, our _validate_obj / _legal_fallback hardening). The net-deltas of the
  hand-size sources and the per-source draw costs are semantically faithful to ryota's
  published principles; the code is original to FMA. Source credited: sue124/ryotasueyoshi.

Base scaffolding: forked from Sabrina v1 (the hardened AlakazamPolicy line). Survival
scaffolding kept to the champion standard:
  - repetition-safe _legal_fallback / normalize_selection (handles minCount > #options),
  - final _validate of the policy output vs the raw select (illegal -> legal fallback),
  - non-raising module load (a missing deck.csv degrades instead of killing the module).

Deck: the ryota Alakazam list (60), which adds Fezandipiti ex (Flip the Script, the +3
source that Powerful-Hand budgeting needs), Genesect (ACE nullifier tech), Psyduck/Shaymin
(situational tech), Lucky Helmet, Enriching Energy (ACE SPEC) and a 3x Enhanced Hammer
anti-Mist package. New bodies are piloted crash-safe + given matchup-aware bench gates.

NB: `agent` MUST stay the LAST top-level callable (kaggle get_last_callable picks it).
"""
from __future__ import annotations

import os
from collections import Counter, defaultdict

from cg.api import (
    AreaType, Card, CardType, EnergyType, Observation, OptionType, Pokemon,
    SelectContext, all_card_data, all_attack, to_observation_class,
)


# ── Card IDs (胡地小人 / Alakazam + Dudunsparce single-prize) ─────────────────
class C:
    ABRA = 741            # Basic -> Kadabra
    KADABRA = 742         # Stage1 (Psychic Draw on evolve) -> Alakazam
    ALAKAZAM = 743        # Stage2 attacker: Powerful Hand = 20 dmg x cards in hand
    ALAKAZAM_PSY = 245    # Stage2 TECH (1x): Psychic = 10 + 50/energy on opp Active (DAMAGE).
    DUNSPARCE = 65        # Basic -> Dudunsparce (id65 printing)
    DUNSPARCE_ALT = 305   # Basic -> Dudunsparce (id305 printing; the one ryota's list runs)
    DUDUNSPARCE = 66      # Stage1 draw engine (Run Away Draw)
    FEZANDIPITI = 140     # Basic ex: Flip the Script ability = draw 3 (the +3 budget source)
    GENESECT = 142        # ACE Nullifier (with tool)
    PSYDUCK = 858         # Damp / vs-Duskull tech body
    SHAYMIN = 343         # Flower Curtain (protect non-Rule-Box bench) / vs water threat

    PSYCHIC_ENERGY = 5
    TELEPATH_ENERGY = 19  # special, provides {P}; searches 2 from deck on attach
    ENRICHING_ENERGY = 13 # ACE SPEC energy; draws 4 from deck on attach

    BUDDY_POFFIN = 1086
    POKE_PAD = 1152
    HILDA = 1225          # Supporter: search Evolution + Energy (+net hand)
    DAWN = 1231           # Supporter: search Basic+Stage1+Stage2 (+net hand)
    RARE_CANDY = 1079     # Item; Psychic Draw on the resulting evolution draws 3
    BOSS_ORDERS = 1182    # Supporter: gust a benched opp Pokémon to Active
    BATTLE_CAGE = 1264    # Stadium: block bench damage counters
    ENHANCED_HAMMER = 1081  # Item: discard a Special Energy from opp (e.g. Mist Energy)
    LUCKY_HELMET = 1156   # Tool: draw 2 when damaged
    NIGHT_STRETCHER = 1097
    SACRED_ASH = 1129


POWERFUL_HAND = 1072   # Alakazam 743: place 2 counters (20 dmg) per card in hand, on opp Active
PSYCHIC_ATK = 339      # Alakazam 245: 10 + 50 per energy on opp Active (DAMAGE; bypasses Mist)
STRANGE_HACKING = 338  # Alakazam 245: confuse + move opp's damage counters around
SUPER_PSY_BOLT = 1071  # Kadabra: 30
ALAKAZAM_IDS = {743, 245}   # both Stage-2 Alakazam attackers (Powerful Hand / Psychic)
ABRA_TELEPORT = 1070   # Abra: 10 + switch
DUDUN_LAND_CRUSH = 76  # Dudunsparce: 90 (rarely; engine instead)
DUNSPARCE_TRADE = 423  # Dunsparce: switch
DUNSPARCE_RAM = 424

# Opponent ids we react to (kept minimal; matchup tech gates).
OP_DUSKULL = 131
OP_WATER_THREAT = {162, 327, 33, 945, 108, 257}   # Slowpoke/Froakie/Ogerpon-Wellspring/Darumaka
OP_DRAGAPULT_LINE = {119, 120, 121}               # Dreepy / Drakloak / Dragapult ex
MIST_ENERGY = 11
ROCK_FIGHTING_ENERGY = 20

ENERGY_TYPES = {C.PSYCHIC_ENERGY, C.TELEPATH_ENERGY, C.ENRICHING_ENERGY}
PSYCHIC_ENERGY_IDS = {C.PSYCHIC_ENERGY, C.TELEPATH_ENERGY}
DUNSPARCE_IDS = {C.DUNSPARCE, C.DUNSPARCE_ALT}    # both printings evolve into Dudunsparce 66
ABRA_LINE = {C.ABRA, C.KADABRA, C.ALAKAZAM}
LOW_DECK_COUNT = 6

# Per-source DECK COST (cards pulled from deck) — re-implemented from ryota's safe_draws
# gates (Technique 2). Each is the number of cards the source draws/searches off the deck,
# so the gate is `safe_draws >= COST`, NOT a blind deck-out guard.
COST_DRAW = {
    "RARE_CANDY": 3,        # Psychic Draw on the Alakazam it makes
    "ENRICHING": 4,         # Enriching attach draws 4
    "TELEPATH": 2,          # Telepath attach searches 2
    "EVOLVE_ALAKAZAM": 3,   # Psychic Draw (3)
    "EVOLVE_KADABRA": 2,    # Psychic Draw (2)
    "EVOLVE_DUDUNSPARCE": 2,  # draw on evolve (2)
    "ABILITY_DUDUNSPARCE": 3,  # Run Away Draw (3)
    "ABILITY_FEZANDIPITI": 3,  # Flip the Script (3)
    "HILDA": 2,             # net deck pull guard
    "DAWN": 3,
    "BUDDY_POFFIN": 2,      # searches deck
    "POKE_PAD": 1,          # searches deck
}

# Module-level pre_turn (cabt/kaggle call agent() repeatedly; we detect turn change here).
pre_turn = -1

_DIAG = {"decisions": 0, "policy_ok": 0, "policy_fallback": 0,
         "obs_fallback": 0, "deck_returns": 0, "errors": {}}


def _diag_record_error(exc):
    k = type(exc).__name__ + ": " + str(exc)[:160]
    _DIAG["errors"][k] = _DIAG["errors"].get(k, 0) + 1


def diag_reset():
    _DIAG.update({"decisions": 0, "policy_ok": 0, "policy_fallback": 0,
                  "obs_fallback": 0, "deck_returns": 0, "errors": {}})


def diag_snapshot():
    s = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DIAG.items()}
    s["fallback_rate"] = (s.get("policy_fallback", 0) + s.get("obs_fallback", 0)) / max(1, s["decisions"])
    s["deck_ok"] = globals().get("_DECK_OK", True)
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
_DECK_OK = (len(my_deck) == 60)

all_card = all_card_data()
card_table = {c.cardId: c for c in all_card}

# Active-ability Item-lock cards (Tyranitar / Jellicent ex …).
ITEM_LOCK_IDS = set()
for _c in all_card:
    for _s in (_c.skills or []):
        _t = (_s.text or '')
        if 'Item' in _t and 'Active Spot' in _t and 'play' in _t and ('opponent' in _t or 'neither' in _t):
            ITEM_LOCK_IDS.add(_c.cardId)

# CRITICAL for Alakazam: Powerful Hand "places damage counters" = an EFFECT, so a target
# that "prevents all effects of attacks done to it" takes 0 from it (Mist/Rock energy, etc.).
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
EFFECT_PREVENT_ENERGY |= {MIST_ENERGY, ROCK_FIGHTING_ENERGY}

# GENERAL energy rule: attach only what an attack costs — never over-fill — UNLESS the attack
# scales with energy attached to ITSELF (then more = more damage).
ATTACK_COST = {}
ATTACK_COST_ENERGIES = {}
SELF_SCALING_ATTACKS = set()
for _a in all_attack():
    ATTACK_COST[_a.attackId] = len(_a.energies or [])
    ATTACK_COST_ENERGIES[_a.attackId] = list(_a.energies or [])
    _t = (_a.text or '').lower()
    if 'for each' in _t and 'energy attached to this' in _t:
        SELF_SCALING_ATTACKS.add(_a.attackId)

# What TYPE each energy card provides (Enriching -> Colorless 0; Telepath/Basic {P} -> Psychic 5).
ENERGY_PROVIDES = {}
for _c in all_card:
    if _c.cardType in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY):
        ENERGY_PROVIDES[_c.cardId] = getattr(_c, 'energyType', 0)

# Situational-tech triggers.
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


# Per-turn ability-usage flags. ryota tracked these as module globals (Technique 1/4): a
# Run Away Draw / Flip the Script counts toward the hand budget only if NOT already used
# this turn. v1 never tracked them. We keep them at module level and reset on turn change.
ability_used_dudunsparce = False
ability_used_fezandipiti = False


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
        # derived counts on the evolution lines (both Dunsparce printings collapse to one line)
        self._abra_line_field = self.field[C.ABRA] + self.field[C.KADABRA] + self.field[C.ALAKAZAM]
        self._dunsparce_field = sum(self.field[i] for i in DUNSPARCE_IDS) + self.field[C.DUDUNSPARCE]
        # Technique 1 budget + Technique 3 target are computed once per decision.
        self._max_size = self._hand_budget()[1]
        self._target = self._select_prize_target()

    def _my_board(self):
        return self.me.active + self.me.bench

    def _bench_free(self):
        used = sum(1 for p in self.me.bench if p is not None)
        return max(0, getattr(self.me, "benchMax", 5) - used)

    def _open_bench(self):
        return self._bench_free() > 0

    def _hand_size(self):
        return self.me.handCount

    def _energy_count(self, p):
        return len(p.energies) if p is not None else 0

    def _has_psychic_energy(self, p):
        return p is not None and any(ec.id in PSYCHIC_ENERGY_IDS for ec in (p.energyCards or []))

    # ═══════════════════════════════════════════════════════════════════════
    # TECHNIQUE 1 — DAMAGE-BUDGETING (estimate this turn's hand-size range).
    #   Re-implemented from ryota's estimate_hand_increase() + the notebook's
    #   "factors that can increase your hand size" list. Net-deltas are faithful;
    #   the code/nomenclature (C.*, self.field/self.hand, our ability flags) is ours.
    #   v1's _achievable_hand() modelled only Dudunsparce(+3) and a flat supporter(+1):
    #   it systematically UNDER-counted reachable damage and missed KOs ryota plans.
    # ═══════════════════════════════════════════════════════════════════════
    def _hand_budget(self):
        """(min_size, max_size) of hand we can reach THIS turn. max_size*20 feeds
        _max_damage() (Powerful Hand = 20 * cards in hand). Sources, net of the cards
        each play spends, mirror the published Playing Principles:
            Abra+Kadabra(hand)           -> +1 (evolve: -1 hand, +2 draw)
            Abra+RareCandy+Alakazam(hand)-> +1 (-2 hand, +3 draw)
            Kadabra+Alakazam(hand)       -> +2 (evolve: -1 hand, +3 draw)
            Dunsparce+Dudunsparce(hand)  -> +1 (evolve: -1 hand, +2 draw)
            Dudunsparce in play, ability unused -> +3 (Run Away Draw)
            Fezandipiti in play, ability unused -> +3 (Flip the Script)
            Fezandipiti in hand + free bench    -> +2 (-1 play, +3 ability)
            best of one Supporter: Hilda +1 / Dawn +2 / Boss -1
            Enriching attach, no energy attached yet, Alakazam active w/ {P} -> +3
        """
        max_inc = 0
        active = self.me.active[0] if self.me.active else None
        active_is_alakazam_psy = (active is not None and active.id == C.ALAKAZAM
                                  and self._has_psychic_energy(active))
        for p in self._my_board():
            if p is None:
                continue
            pid = p.id
            if pid == C.ABRA and self.hand[C.KADABRA] > 0:
                max_inc += 1
            elif pid == C.ABRA and self.hand[C.RARE_CANDY] > 0 and self.hand[C.ALAKAZAM] > 0:
                max_inc += 1
            elif pid == C.KADABRA and self.hand[C.ALAKAZAM] > 0:
                max_inc += 2
            elif pid in DUNSPARCE_IDS and self.hand[C.DUDUNSPARCE] > 0:
                max_inc += 1
            elif pid == C.DUDUNSPARCE:
                if not ability_used_dudunsparce:
                    max_inc += 3
            elif pid == C.FEZANDIPITI:
                if not ability_used_fezandipiti:
                    max_inc += 3
        # Fezandipiti still in hand: playing it to a free bench unlocks +3, net +2.
        if self.hand[C.FEZANDIPITI] > 0 and self._bench_free() > 0 and self.field[C.FEZANDIPITI] == 0:
            max_inc += 2
        # exactly one Supporter per turn -> take the best net gain available.
        if not self.state.supporterPlayed:
            opts = []
            if self.hand[C.HILDA] > 0:
                opts.append(1)
            if self.hand[C.DAWN] > 0:
                opts.append(2)
            if self.hand[C.BOSS_ORDERS] > 0:
                opts.append(-1)
            if opts:
                max_inc += max(opts)
        # Enriching attach draws 4 (net +3) but only onto an Alakazam already powered.
        if self.hand[C.ENRICHING_ENERGY] > 0 and not self.state.energyAttached and active_is_alakazam_psy:
            max_inc += 3
        return self._hand_size(), self._hand_size() + max_inc

    def _max_damage(self):
        """Powerful Hand ceiling for THIS turn = max reachable hand * 20."""
        return self._max_size * 20

    def _hammers_for(self, target):
        """How many Enhanced Hammers we'd need (and have) to strip the effect-prevention
        Special Energy off `target` so Powerful Hand stops doing 0. Returns (need, possible)."""
        sp = sum(1 for e in (getattr(target, 'energyCards', None) or [])
                 if getattr(e, 'id', None) in EFFECT_PREVENT_ENERGY)
        if sp == 0:
            return 0, True
        if self.hand[C.ENHANCED_HAMMER] >= sp:
            return sp, True
        return sp, False           # can't strip enough -> Powerful Hand still does 0

    # ═══════════════════════════════════════════════════════════════════════
    # TECHNIQUE 3 — PRIZE-TARGETING (whom to attack).
    #   Re-implemented from ryota's target-selection block + the principle "KO the most
    #   prizes; if a KO takes your last prize, take it; ties -> highest HP in range; use
    #   Boss to drag a benched target active". v1 scattered this across _gust_value /
    #   _target_value with a DIFFERENT heuristic — we unify it into one ranked choice.
    # ═══════════════════════════════════════════════════════════════════════
    def _select_prize_target(self):
        """Return a dict describing the turn's intended KO target, or None.
        Keys: idx (0=active, 1..=bench), pkmn, prizes, can_kill, use_boss, hammers,
        kadabra_finish."""
        opp_active = self.opponent.active[0] if self.opponent.active else None
        if self.state.turn < 2 or opp_active is None:
            return None
        active = self.me.active[0] if self.me.active else None
        active_id = active.id if active is not None else -1
        my_prizes = len(self.me.prize)

        # Kadabra finisher: a 30-HP-or-less active dies to Super Psy Bolt directly.
        if opp_active.hp <= 30 and (self.field[C.KADABRA] >= 1 or active_id == C.KADABRA):
            return {"idx": 0, "pkmn": opp_active, "prizes": prize_count(opp_active),
                    "can_kill": True, "use_boss": False, "hammers": 0, "kadabra_finish": True}

        ceiling = self._max_size
        all_op = [(0, opp_active)]
        for bi, bp in enumerate(self.opponent.bench):
            if bp is not None:
                all_op.append((bi + 1, bp))

        cands = []
        for oi, pk in all_op:
            need_h, possible = self._hammers_for(pk)
            eff_dmg = (ceiling - need_h) * 20 if possible else 0
            killable = (eff_dmg > 0 and pk.hp <= eff_dmg)
            cands.append({"idx": oi, "pkmn": pk, "prizes": prize_count(pk),
                          "can_kill": killable, "hammers": need_h})

        # Priority 1: a KO that takes our final prize(s) WINS — prefer active (no Boss), then HP.
        winners = [c for c in cands if c["can_kill"] and my_prizes <= c["prizes"]]
        if winners:
            best = min(winners, key=lambda c: (0 if c["idx"] == 0 else 1, -c["pkmn"].hp))
            best["use_boss"] = best["idx"] != 0
            best["kadabra_finish"] = False
            return best

        # Priority 2: killable target with the MOST prizes (ties -> highest HP in range).
        killables = [c for c in cands if c["can_kill"]]
        if killables:
            best = max(killables, key=lambda c: (c["prizes"], c["pkmn"].hp))
            best["use_boss"] = best["idx"] != 0
            best["kadabra_finish"] = False
            return best

        # Priority 3: nothing dies -> just hit the active.
        return {"idx": 0, "pkmn": opp_active, "prizes": 0, "can_kill": False,
                "use_boss": False, "hammers": 0, "kadabra_finish": False}

    # ═══════════════════════════════════════════════════════════════════════
    # TECHNIQUE 2 — SAFE_DRAWS (anti-deckout gating).
    #   Re-implemented from ryota's `safe_draws = deck - prizes - 1` (999 if winning this
    #   turn). Each deck-touching source is gated by its REAL draw cost (COST_DRAW), not a
    #   blunt deck-out guard. v1 had no safe_draws (only _low_deck / _deck_preserve +4).
    # ═══════════════════════════════════════════════════════════════════════
    def _can_win_now(self):
        t = self._target
        return bool(t and t["can_kill"] and len(self.me.prize) <= t["prizes"])

    def _safe_draws(self):
        """Cards we can pull from deck while keeping deck > prizes (and 1 for next turn's
        draw). If this turn's KO wins the game, decking to 0 is fine -> 999."""
        if self._can_win_now():
            return 999
        return self.me.deckCount - len(self.me.prize) - 1

    def _draw_ok(self, key):
        """Gate a deck-touching source by its specific draw cost."""
        return self._safe_draws() >= COST_DRAW.get(key, 1)

    # — energy payment (type-aware) —
    @staticmethod
    def _can_pay(attached, cost):
        have = Counter(attached)
        colorless = 0
        for req in cost:
            if req == EnergyType.COLORLESS:
                colorless += 1
            elif have.get(req, 0) > 0:
                have[req] -= 1
            else:
                return False
        return sum(have.values()) >= colorless

    def _can_attack(self, p):
        c = card_table.get(p.id)
        if c is None:
            return False
        attached = list(p.energies or [])
        return any(aid in ATTACK_COST_ENERGIES and self._can_pay(attached, ATTACK_COST_ENERGIES[aid])
                   for aid in (c.attacks or []))

    def _should_fuel(self, p):
        c = card_table.get(p.id)
        if c is None or not (c.attacks or []):
            return False
        if any(aid in SELF_SCALING_ATTACKS for aid in c.attacks):
            return True
        return not self._can_attack(p)

    def _attach_helps(self, p, src):
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
        for p in (self.opponent.active + self.opponent.bench):
            c = card_table.get(p.id) if p is not None else None
            if c and any(aid in BENCH_DAMAGE_ATTACKS for aid in (c.attacks or [])):
                return True
        return False

    def _opp_has_self_ko_ability(self):
        return any(p is not None and p.id in SELF_KO_ABILITY_IDS
                   for p in (self.opponent.active + self.opponent.bench))

    def _opp_all(self):
        return [p for p in (self.opponent.active + self.opponent.bench) if p is not None]

    def _opp_has_duskull(self):
        return any(p.id == OP_DUSKULL for p in self._opp_all())

    def _opp_has_water_threat(self):
        return any(p.id in OP_WATER_THREAT for p in self._opp_all())

    def _opp_has_dragapult(self):
        return any(p.id in OP_DRAGAPULT_LINE for p in self._opp_all())

    def _psychic_in_hand(self):
        return any(ENERGY_PROVIDES.get(c.id) == EnergyType.PSYCHIC for c in self.me.hand)

    def _energy_starved(self):
        bodies = [p for p in self._my_board() if p is not None]
        has_alakazam = any(p.id in ALAKAZAM_IDS for p in bodies)
        coming = any(p.id == C.KADABRA for p in bodies) and self.hand[C.ALAKAZAM] > 0
        if not (has_alakazam or coming):
            return False
        if any(p.id in ALAKAZAM_IDS and self._can_attack(p) for p in bodies):
            return False
        return not self._psychic_in_hand()

    def _effect_prevented(self, target):
        if target is None:
            return False
        if target.id in EFFECT_PREVENT_SELF:
            return True
        for e in (getattr(target, 'energyCards', None) or []):
            if getattr(e, 'id', None) in EFFECT_PREVENT_ENERGY:
                return True
        return False

    def _opp_active_has_prevent_energy(self):
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
                return 0
            return 20 * self._hand_size()
        if attack_id == PSYCHIC_ATK:
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

    def _have_attacker(self):
        a = self.me.active[0] if self.me.active else None
        if a is not None and a.id in ALAKAZAM_IDS and self._energy_count(a) >= 1:
            return True
        return self._bench_attacker_ready()

    def _bench_attacker_ready(self):
        return any(p is not None and p.id in ALAKAZAM_IDS and self._energy_count(p) >= 1
                   for p in self.me.bench)

    def _ko_active_reachable(self):
        """Powerful Hand can KO the opp ACTIVE this turn after available drawing —
        now driven by Technique 1's _max_damage(), not the old +3/+1 stub."""
        opp = self.opponent.active[0] if self.opponent.active else None
        return (opp is not None and self._have_attacker()
                and not self._effect_prevented(opp)
                and self._max_damage() >= opp.hp)

    def _target_value(self, p):
        """Tactical worth of removing opp p — used only as a tiebreak vs gusting (kept
        from v1's heuristic; Technique 3 ranks the primary target separately)."""
        d = card_table.get(p.id)
        s = prize_count(p) * 1000
        s += len(p.energies) * 150
        s += len(getattr(p, 'tools', []) or []) * 100
        if d is not None:
            if getattr(d, 'stage2', 0):
                s += 250
            elif getattr(d, 'stage1', 0):
                s += 130
        s += getattr(p, 'hp', 0)
        return s

    def _gust_ko_targets(self):
        return [p for p in self.opponent.bench if p is not None and self._active_best_dmg(p) >= p.hp]

    def _gust_value(self, p):
        d = self._active_best_dmg(p)
        if d >= p.hp:
            if prize_count(p) >= len(self.me.prize):
                return 90000
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
        out = normalize_selection(ranked, scores, self.select)
        # Technique 4 bookkeeping: if the top pick we are about to commit is an ability
        # use of Dudunsparce / Fezandipiti, flag it used so Technique 1 stops double-counting
        # its +3 for the rest of this turn (mirrors ryota's MAIN-context flagging).
        self._mark_ability_used(ranked, scores)
        return out

    def _mark_ability_used(self, ranked, scores):
        global ability_used_dudunsparce, ability_used_fezandipiti
        if self.context != SelectContext.MAIN or not ranked:
            return
        top = ranked[0]
        if top >= len(self.select.option) or scores[top] <= 0:
            return
        o = self.select.option[top]
        if o.type != OptionType.ABILITY:
            return
        card = get_card(self.obs, o.area, o.index, self.my_index)
        if card is None:
            return
        if card.id == C.DUDUNSPARCE:
            ability_used_dudunsparce = True
        elif card.id == C.FEZANDIPITI:
            ability_used_fezandipiti = True

    def _score(self, o):
        t = o.type
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
                    return False
        return True

    def _alakazam_ready(self):
        a = self.me.active[0] if self.me.active else None
        return a is not None and a.id in ALAKAZAM_IDS and self._energy_count(a) >= 1

    def _need_pieces(self):
        return self.field[C.ALAKAZAM] < 1

    # — abilities (Technique 4: gate by need + Technique 2 deck cost) —
    def _score_ability(self, o):
        card = get_card(self.obs, o.area, o.index, self.my_index)
        if card is None:
            return 0
        if card.id == C.DUDUNSPARCE:
            # Run Away Draw: only when we actually NEED the cards to reach lethal on the
            # turn's target (Technique 3) AND the deck can afford it (Technique 2).
            if o.area != AreaType.BENCH and (self._item_locked() or self._bench_attacker_ready()):
                # ACTIVE copy used to cycle/reposition into an attacker — always allowed.
                return 14000
            if self._need_dudunsparce_draw() and self._draw_ok("ABILITY_DUDUNSPARCE"):
                return 30000
            return -1
        if card.id == C.FEZANDIPITI:
            if (self._need_fezandipiti_draw() or self._need_fezandipiti_setup()) \
                    and self._draw_ok("ABILITY_FEZANDIPITI"):
                return 29000
            return -1
        if card.id == C.BATTLE_CAGE:
            return 1
        return 9000

    def _need_dudunsparce_draw(self):
        """Do we need Run Away Draw to push current hand to lethal on the target?"""
        t = self._target
        if not t or not t["can_kill"]:
            return False
        current = (self._hand_size() - t["hammers"]) * 20
        return current < t["pkmn"].hp

    def _fez_contribution(self):
        if self.field[C.FEZANDIPITI] >= 1 and not ability_used_fezandipiti:
            return 3
        if self.hand[C.FEZANDIPITI] > 0 and self._bench_free() > 0 and self.field[C.FEZANDIPITI] == 0:
            return 2
        return 0

    def _need_fezandipiti_draw(self):
        t = self._target
        if not t or not t["can_kill"]:
            return False
        contrib = self._fez_contribution()
        if contrib <= 0:
            return False
        without_fez = (self._max_size - contrib - t["hammers"]) * 20
        return without_fez < t["pkmn"].hp

    def _need_fezandipiti_setup(self):
        """Flip the Script also worth it to dig for the missing enabler (Boss / Rare Candy /
        Alakazam / energy) of a kill we otherwise can't assemble."""
        t = self._target
        if not t or not t["can_kill"] or self._fez_contribution() <= 0 or self._need_fezandipiti_draw():
            return False
        missing_boss = (t["use_boss"] and self.hand[C.BOSS_ORDERS] == 0 and not self.state.supporterPlayed)
        # ready attacker?
        has_ready = any(p is not None and p.id == C.ALAKAZAM and self._has_psychic_energy(p)
                        for p in self._my_board())
        missing_attacker = False
        missing_energy = False
        if not has_ready:
            can_evolve = self.field[C.KADABRA] >= 1 and self.hand[C.ALAKAZAM] >= 1
            can_candy = (self.field[C.ABRA] >= 1 and self.hand[C.RARE_CANDY] >= 1
                         and self.hand[C.ALAKAZAM] >= 1)
            if not can_evolve and not can_candy:
                if self.field[C.KADABRA] >= 1 and self.hand[C.ALAKAZAM] == 0:
                    missing_attacker = True
                elif self.field[C.ABRA] >= 1 and (self.hand[C.RARE_CANDY] == 0 or self.hand[C.ALAKAZAM] == 0):
                    missing_attacker = True
            energy_in_hand = (self.hand[C.PSYCHIC_ENERGY] + self.hand[C.TELEPATH_ENERGY]
                              + self.hand[C.ENRICHING_ENERGY])
            if not self.state.energyAttached and energy_in_hand == 0:
                energized = any(p is not None and p.id in ABRA_LINE and self._has_psychic_energy(p)
                                for p in self._my_board())
                if not energized:
                    missing_energy = True
        return missing_boss or missing_attacker or missing_energy

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
        if cid in DUNSPARCE_IDS:
            return 18500 - 250 * n
        if cid == C.FEZANDIPITI:
            # ex liability: only bench it when its Flip the Script is actually needed
            # (Technique 1/4), otherwise it's just a 2-prize gift on the bench.
            if self._need_fezandipiti_draw() or self._need_fezandipiti_setup():
                return 17500 if n == 0 else -1
            return -1
        if cid == C.GENESECT:
            # ACE nullifier: only relevant before the opp has burnt their ACE SPEC and we
            # have a tool to suit it; cheap heuristic — bench when we hold a tool to wear.
            if n == 0 and (self.hand[C.LUCKY_HELMET] > 0 or self.hand[C.POKE_PAD] > 0):
                return 9000
            return -1
        if cid == C.SHAYMIN:
            return 17000 if (n == 0 and (self._opp_threatens_bench() or self._opp_has_water_threat())) else -1
        if cid == C.PSYDUCK:
            return 9000 if (n == 0 and (self._opp_has_self_ko_ability() or self._opp_has_duskull())) else -1
        return 14000 - 200 * n

    def _score_play_trainer(self, card):
        cid = card.id
        ready = self._alakazam_ready()
        sd = self._safe_draws()
        opp_active = self.opponent.active[0] if self.opponent.active else None
        if cid == C.RARE_CANDY:
            # makes an Alakazam whose Psychic Draw pulls 3 -> gate by deck cost.
            if self.field[C.ABRA] >= 1 and self.hand[C.ALAKAZAM] >= 1 and self._draw_ok("RARE_CANDY"):
                return 20500
            return -1
        draw_for_ko = (opp_active is not None and self._ko_active_reachable()
                       and 20 * self._hand_size() < opp_active.hp)
        if cid == C.HILDA:
            if self.state.supporterPlayed or not self._draw_ok("HILDA"):
                return -1
            if draw_for_ko:
                return 14000
            return 12500 if self._need_pieces() else 3000
        if cid == C.DAWN:
            if self.state.supporterPlayed or not self._draw_ok("DAWN"):
                return -1
            if draw_for_ko:
                return 13800
            return 12000 if self._need_pieces() else 2500
        if cid == C.BUDDY_POFFIN:
            if not self._draw_ok("BUDDY_POFFIN"):
                return -1
            return 13000 if self._open_bench() else 600
        if cid == C.POKE_PAD:
            if not self._draw_ok("POKE_PAD"):
                return -1
            return 8500 if self._need_pieces() else 400
        if cid == C.BOSS_ORDERS:
            if self.state.supporterPlayed:
                return -1
            t = self._target
            # If the planned target (Technique 3) is benched and killable, Boss enables it.
            if t and t["use_boss"] and t["can_kill"]:
                return 13500
            ko = self._gust_ko_targets()
            if not ko:
                return -1
            best = max(ko, key=self._gust_value)
            if opp_active is not None and self._active_best_dmg(opp_active) >= opp_active.hp \
                    and prize_count(opp_active) >= prize_count(best):
                return -1
            return 13000
        if cid == C.ENHANCED_HAMMER:
            if self._opp_active_has_prevent_energy():
                return 16000
            t = self._target
            if t and t.get("hammers", 0) > 0:
                return 6500
            if any(card_table.get(getattr(e, 'id', None)) is not None
                   and card_table[e.id].cardType == CardType.SPECIAL_ENERGY
                   for p in self._opp_all()
                   for e in (getattr(p, 'energyCards', None) or [])):
                return 1500
            return -1
        if cid == C.BATTLE_CAGE:
            if self.stadium_id == C.BATTLE_CAGE:
                return -1
            if self._opp_has_dragapult():
                return 19000
            if self.stadium_id != 0:
                return 7000
            return -1
        if cid == C.LUCKY_HELMET:
            return 7000 if not ready else 1000
        if cid == C.NIGHT_STRETCHER:
            dis_line = self.discard.get(C.ABRA, 0) + self.discard.get(C.KADABRA, 0) + self.discard.get(C.ALAKAZAM, 0)
            if dis_line >= 1:
                return 6000
            if self.discard.get(C.PSYCHIC_ENERGY, 0) + self.discard.get(C.TELEPATH_ENERGY, 0) >= 1:
                return 4000
            return -1
        if cid == C.SACRED_ASH:
            dis_line = self.discard.get(C.ABRA, 0) + self.discard.get(C.KADABRA, 0) + self.discard.get(C.ALAKAZAM, 0)
            if dis_line >= 2:
                return 6500
            if dis_line >= 1:
                return 4500
            return -1
        return 9000

    # — evolve (Technique 2: Psychic-Draw deck-cost gate) —
    def _score_evolve(self, o):
        target = get_card(self.obs, o.inPlayArea, o.inPlayIndex, self.my_index)
        if not isinstance(target, Pokemon):
            return 0
        card = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        cid = card.id if card is not None else None
        if cid == C.ALAKAZAM_PSY:
            opp = self.opponent.active[0] if self.opponent.active else None
            if opp is not None and ((self._effect_prevented(opp) and self.hand[C.ENHANCED_HAMMER] == 0)
                                    or len(opp.energies) >= 4):
                return 21500
            return 20400
        if cid == C.ALAKAZAM:
            if not self._draw_ok("EVOLVE_ALAKAZAM"):
                return -1
            base = 21000 + (200 if o.inPlayArea == AreaType.ACTIVE else 50)
            return base + self._energy_count(target) * 10
        if cid == C.KADABRA:
            if not self._draw_ok("EVOLVE_KADABRA"):
                return -1
            # Principle: evolve a NO-energy Abra first; save an energy Abra for Rare Candy.
            base = 20000
            if self._energy_count(target) == 0:
                base += 50
            else:
                base -= 20
                if self.hand[C.RARE_CANDY] > 0 and self.hand[C.ALAKAZAM] > 0:
                    base -= 100
            return base
        if cid == C.DUDUNSPARCE:
            if not self._draw_ok("EVOLVE_DUDUNSPARCE"):
                return -1
            return 19000
        return 18000

    # — attach energy (Technique 2: Telepath/Enriching deck-cost gates) —
    def _score_attach(self, o):
        p = get_card(self.obs, o.inPlayArea, o.inPlayIndex, self.my_index)
        if not isinstance(p, Pokemon):
            return 0
        src = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        src_id = src.id if src is not None else None
        # Lucky Helmet is a tool, routed here by some engines as ATTACH — wear it.
        if src_id == C.LUCKY_HELMET:
            base = 7000
            if p.id == C.GENESECT:
                base += 300
            elif o.inPlayArea == AreaType.ACTIVE:
                base += 200
            else:
                base += 50
            return base
        if not self._should_fuel(p):
            return -1
        if not self._attach_helps(p, src):
            return -1
        # Telepath searches 2 from deck; Enriching draws 4 — gate both by safe_draws.
        if src_id == C.TELEPATH_ENERGY and not self._draw_ok("TELEPATH"):
            return -1
        if src_id == C.ENRICHING_ENERGY and not self._draw_ok("ENRICHING"):
            return -1
        if p.id in ALAKAZAM_IDS:
            return 8000 + (200 if o.inPlayArea == AreaType.ACTIVE else 0)
        if p.id in (C.ABRA, C.KADABRA):
            return 1500
        return -1

    # — retreat —
    def _score_retreat(self):
        active = self.me.active[0] if self.me.active else None
        opp = self.opponent.active[0] if self.opponent.active else None
        if active is None or opp is None:
            return -1
        t = self._target
        if t and t.get("kadabra_finish") and active.id != C.KADABRA and self.field[C.KADABRA] >= 1:
            return 2500
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
            if active.id not in ALAKAZAM_IDS and active.id != C.KADABRA and self._bench_attacker_ready():
                return 5000
            return 700
        dmg = self._alakazam_damage(aid, opp)
        if aid == STRANGE_HACKING:
            opp_dangerous = prize_count(opp) >= 2 and self._max_damage() < opp.hp
            return 600 if opp_dangerous else 200
        if dmg <= 0:
            return 500
        if opp.hp <= dmg and prize_count(opp) >= len(self.me.prize):
            return 90000
        score = 1000 + min(dmg, 320)
        if aid == SUPER_PSY_BOLT and opp.hp <= 30:
            score += 600           # Kadabra finisher
        if opp.hp <= dmg:
            score += 2500 + prize_count(opp) * 200
        return score

    # — sub-selects —
    def _score_card(self, o):
        card = get_card(self.obs, o.area, o.index, o.playerIndex)
        if card is None:
            return 0
        ctx = self.context
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
            return -1
        if p.id in ALAKAZAM_IDS:
            return 8000 + (200 if is_active else 0)
        if p.id in (C.ABRA, C.KADABRA):
            return 1500
        return -1

    def _score_active_choice(self, o, card):
        if not isinstance(card, Pokemon):
            return 0
        if o.playerIndex == self.op_index:
            # Boss/switch onto opp: prefer the Technique-3 planned benched target.
            t = self._target
            if t and t["use_boss"] and getattr(o, "index", -2) == t["idx"] - 1:
                return 100000 if t["can_kill"] else 50000
            return self._gust_value(card)
        if o.playerIndex != self.my_index:
            return 0
        score = self._energy_count(card) * 10
        if card.id in ALAKAZAM_IDS:
            score += 200
        elif card.id == C.KADABRA:
            score += 95
        elif card.id == C.ABRA:
            score += 80
        elif card.id == C.DUDUNSPARCE:
            score += 40
        elif card.id in (C.PSYDUCK, C.SHAYMIN, C.GENESECT, C.FEZANDIPITI):
            score -= 20
        score += getattr(card, 'hp', 0) // 30
        return score + 1

    def _score_setup_active(self, card):
        if card is None:
            return 0
        if card.id == C.ABRA:
            return 50
        if card.id in DUNSPARCE_IDS:
            return 30
        if card.id in (C.PSYDUCK, C.SHAYMIN, C.GENESECT, C.FEZANDIPITI):
            return 1
        return 5

    def _score_to_bench(self, card):
        if card is None:
            return 0
        d = card_table.get(card.id)
        if d is None or d.cardType != CardType.POKEMON:
            return 0
        cid = card.id; n = self.field[cid]
        if cid == C.ABRA:
            cur = self._abra_line_field
            return (200 if cur == 0 else 100 + (3 - cur) * 10) - 30 * n
        if cid in DUNSPARCE_IDS:
            return (150 if self._dunsparce_field == 0 else 50) - 30 * n
        if cid == C.SHAYMIN:
            return 150 if (n == 0 and (self._opp_threatens_bench() or self._opp_has_water_threat())) else -1
        if cid == C.PSYDUCK:
            return 90 if (n == 0 and (self._opp_has_self_ko_ability() or self._opp_has_duskull())) else -1
        if cid == C.FEZANDIPITI:
            return 60 if (self._need_fezandipiti_draw() or self._need_fezandipiti_setup()) else -1
        if cid == C.GENESECT:
            return 40 if (n == 0 and (self.hand[C.LUCKY_HELMET] > 0 or self.hand[C.POKE_PAD] > 0)) else -1
        return 100 - 20 * n

    def _score_to_hand(self, card):
        if card is None:
            return 0
        cid = card.id
        score = 200 - self.hand[cid] * 40
        engine_online = self.field[C.DUDUNSPARCE] >= 1
        if cid == C.DUDUNSPARCE:
            score += 90 if not engine_online else 20
        elif cid in DUNSPARCE_IDS:
            score += 70 if self._dunsparce_field < 1 else -10
        elif cid == C.ABRA:
            score += 55 if self._abra_line_field < 2 else -10
        elif cid == C.KADABRA:
            score += 45 if self.field[C.ABRA] >= 1 else -20
        elif cid == C.ALAKAZAM:
            score += 50 if (self.hand[C.ALAKAZAM] == 0 and self.field[C.ABRA] + self.field[C.KADABRA] >= 1) else -10
        elif cid == C.RARE_CANDY:
            score += 40 if self.field[C.ABRA] >= 1 else -10
        elif is_energy(cid):
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
        if cid in (C.ABRA, C.KADABRA, C.ALAKAZAM, C.DUDUNSPARCE) or cid in DUNSPARCE_IDS:
            return -50 if self.field[cid] == 0 else 5
        if cid in (C.HILDA, C.DAWN) and self.state.supporterPlayed:
            return 30
        return 0

    def _score_putback(self, card):
        if card is None:
            return 0
        if self.hand[card.id] >= 2:
            return 60
        if card.id in (C.ABRA, C.ALAKAZAM) or card.id in DUNSPARCE_IDS:
            return -40
        return 10


def agent(obs_dict, config=None):
    # FMA: accept an optional 2nd positional (the kaggle/cabt harness calls agent(obs, config));
    # config is unused. This wrapper is the LAST top-level callable so get_last_callable picks it.
    global pre_turn, ability_used_dudunsparce, ability_used_fezandipiti
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
            # turn changed -> reset the per-turn ability-used flags (Technique 4 bookkeeping).
            pre_turn = obs.current.turn
            ability_used_dudunsparce = False
            ability_used_fezandipiti = False
        try:
            sel = AlakazamPolicy(obs).choose()
            if not _validate_obj(sel, obs.select):
                _DIAG["policy_fallback"] += 1
                return _legal_fallback(obs.select)
            _DIAG["policy_ok"] += 1
            return sel
        except Exception as exc:
            _diag_record_error(exc); _DIAG["policy_fallback"] += 1
            return _legal_fallback(obs.select)
    except Exception as exc:
        _diag_record_error(exc); _DIAG["obs_fallback"] += 1
        return _legal_fallback_from_dict(obs_dict if isinstance(obs_dict, dict) else {})
