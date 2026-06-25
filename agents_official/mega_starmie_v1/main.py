"""
Mega Starmie v1 — Mega Starmie ex (Staryu -> Mega Starmie ex, Cinderace 1-prize) agent.

Provenance: a NEW rule-based pilot (no prior policy to fork) built on the HARDENED survival
scaffolding of FMA's "Sabrina v1" (Alakazam). The piloting decisions are encoded fresh from
the top-pilot (keidroid #1 ladder) replays and the engine-authoritative card recon; the
scaffolding — loaders, repetition-safe fallbacks, _validate gate, the agent() wrapper — is
reused VERBATIM, which is what guarantees the hard requirement: 0 crashes / 0 illegal
selections (any exception or illegal output = instant ladder loss).

DECKLIST (top-pilot keidroid, 60 cards, confidence 100%):
  POKEMON(10): 3x Mega Starmie ex (1031, Stage1 330HP, prize 3) + 3x Staryu (1030, Basic 70HP)
               + 4x Cinderace (666, Stage2 160HP, 1-prize attacker, skill Explosiveness).
  ENERGY(13):  9x Basic {W} (3) + 4x Ignition Energy (17, special: {C}; {C}{C}{C} on Evolutions).
  SUPPORTERS(17): 4x Salvatore (1189) + 4x Wally's Compassion (1229) + 4x Lillie's Determination
               (1227) + 2x Hilda (1225) + 2x Harlequin (1223) + 1x Boss's Orders (1182).
  ITEMS/TOOLS(20): 4x Mega Signal (1145) + 4x Buddy-Buddy Poffin (1086) + 4x Crushing Hammer
               (1120) + 4x Pokégear 3.0 (1122) + 2x Night Stretcher (1097) + 1x Ultra Ball (1121)
               + 1x Hero's Cape (1159, Tool ACE SPEC +100HP).

THE REAL CHALLENGE IS SETUP, NOT TACTICS. 3/8 observed losses are BRICK: the airtight replay
signature is "bench stayed EMPTY all game AND no Mega Starmie ever came online" (NOT literally
"Staryu died" — naked-active-with-empty-bench is the killer). All 7 wins hit first_bench_turn<=3
AND megaT in T2-T4. So this policy's #1 priority is anti-brick setup: never end a turn with an
empty bench, race a 2nd basic into play, and evolve the Mega via Salvatore the same turn Staryu
enters. Combat is near-deterministic afterward.

COMBAT (confirmed attack ids from the engine's all_attack):
  - Jetting Blow (1487, [W]x1, 120): default attack. 120 to Active + 50 snipe to 1 benched
    Pokémon (don't apply W/R to bench). Cheap pressure that also sculpts the opponent's bench.
  - Nebula Beam (1488, [C][C][C]x3, 210): one-shot finisher ONLY. Damage isn't affected by
    Weakness/Resistance or effects on the opponent's Active. Decision is pure HP arithmetic:
    if 210 KOs -> Nebula, else Jetting Blow. Ignition Energy on the (Evolution) Mega pays the
    3 colorless from a single energy, so Nebula is reachable a turn early.
  - Turbo Flare (965, [C]x1, 50, Cinderace): chip + ramp basic energy onto the bench while the
    Mega builds. Free retreat (0) lets Cinderace get out of the way for the finished Mega.

PILOTING RULES (encoded):
  1. Evolve to Mega via Salvatore the turn the Staryu enters (skips the evolution wait).
  2. Jetting Blow by default; Nebula Beam only when 210 lethals the Active.
  3. Boss's Orders = CLOSER only (drag a benched Pokémon up to finish a won game).
  4. No defensive play: attack every turn, let the 330HP wall tank. Wally's Compassion = safety net.
  5. No deck-out management (this deck never decks out); reciclers just re-buy the hand.

NB: `agent` MUST stay the LAST top-level callable (kaggle get_last_callable picks it).
"""
from __future__ import annotations

import os
from collections import defaultdict

from cg.api import (
    AreaType, Card, CardType, EnergyType, Observation, OptionType, Pokemon,
    SelectContext, all_card_data, all_attack, to_observation_class,
)


# ── Card IDs (Mega Starmie ex line + Cinderace single-prize) ─────────────────
class C:
    STARYU = 1030          # Basic 70HP {W} -> Mega Starmie ex. The REAL evolution base.
    MEGA_STARMIE = 1031    # Stage1 330HP {W} attacker, megaEx (prize 3). evolvesFrom 'Staryu'.
    CINDERACE = 666        # Stage2 160HP {R} 1-prize attacker. SKILL 'Explosiveness': can be
                           # placed FACE DOWN in the Active Spot during setup straight from hand
                           # (skips the whole evolution line). The preferred T0 SHIELD active.

    WATER_ENERGY = 3       # Basic {W} (energyType 3). 9 copies, exempt from the 4-copy limit.
    IGNITION_ENERGY = 17   # Special: {C} normally, {C}{C}{C} on an EVOLUTION Pokémon. Discarded
                           # end of turn. Lets the (Evolution) Mega pay Nebula Beam's 3 from one.

    SALVATORE = 1189       # Supporter: evolve a Pokémon put into play THIS turn (Staryu->Mega
                           # same turn it enters). Filter: target has no Abilities — Mega qualifies.
    WALLYS = 1229          # Supporter: fully heal 1 Mega Evolution ex; if healed, return all its
                           # energy to hand. Safety net.
    LILLIE_DET = 1227      # Supporter: shuffle hand into deck, draw 6 (8 if exactly 6 prizes).
    HILDA = 1225           # Supporter: search an Evolution Pokémon + an Energy to hand. Setup motor.
    HARLEQUIN = 1223       # Supporter: both shuffle hands; coin flip self-draw 5/3. Recycler.
    BOSS_ORDERS = 1182     # Supporter: drag a benched opponent Pokémon to Active. CLOSER only.

    MEGA_SIGNAL = 1145     # Item: search a Mega Evolution ex (=Mega Starmie) to HAND (not into play).
    BUDDY_POFFIN = 1086    # Item: put up to 2 Basics with <=70HP onto bench (=> Staryu). Anti-brick.
    CRUSHING_HAMMER = 1120 # Item: coin flip; heads discard 1 opponent Energy. Disruption.
    POKEGEAR = 1122        # Item: look at top 7, take a Supporter to hand. Supporter consistency.
    NIGHT_STRETCHER = 1097 # Item: recover a Pokémon or a Basic Energy from discard to hand.
    ULTRA_BALL = 1121      # Item: discard 2, search any Pokémon to hand.
    HEROS_CAPE = 1159      # Tool ACE SPEC: +100HP to the holder (Mega 330 -> 430). 1-per-deck OK.


# ── Attack ids (confirmed from all_attack(), engine-authoritative) ───────────
JETTING_BLOW = 1487    # Mega Starmie 1031: [W]x1, 120 to Active + 50 snipe to 1 bench. Default.
NEBULA_BEAM = 1488     # Mega Starmie 1031: [C][C][C]x3, 210, ignores W/R + Active effects. Finisher.
WATER_GUN = 1486       # Staryu 1030: [W]x1, 20. Filler if forced to attack as a naked Staryu.
TURBO_FLARE = 965      # Cinderace 666: [C]x1, 50 + ramp up to 3 Basic Energy onto your bench.

MEGA_IDS = {C.MEGA_STARMIE}                 # the win-condition attacker (Mega Starmie ex)
ATTACKER_IDS = {C.MEGA_STARMIE, C.CINDERACE}  # both can attack (Mega main, Cinderace 1-prize)
BASIC_IDS = {C.STARYU, C.CINDERACE}         # bodies that can be in play without an evo line
ENERGY_TYPES = {C.WATER_ENERGY, C.IGNITION_ENERGY}
LOW_DECK_COUNT = 6
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
# FMA: surface a packaging error (missing/short deck.csv) in diag, never abort import.
_DECK_OK = (len(my_deck) == 60)

all_card = all_card_data()
card_table = {c.cardId: c for c in all_card}

# Active-ability Item-lock cards (Tyranitar / Jellicent ex …). Some lock cards
# (e.g. Budew) carry the effect without an exposed skill, so we ALSO detect lock
# from game state (hold Items but none playable) — see MegaStarmiePolicy._item_locked.
ITEM_LOCK_IDS = set()
for _c in all_card:
    for _s in (_c.skills or []):
        _t = (_s.text or '')
        if 'Item' in _t and 'Active Spot' in _t and 'play' in _t and ('opponent' in _t or 'neither' in _t):
            ITEM_LOCK_IDS.add(_c.cardId)

# Targets that "prevent all effects of attacks done to it" take 0 from effect-based hits.
# (Mega Starmie's damage attacks are real damage, but Jetting Blow's 50 bench snipe is an
# effect on a benched body — _effect_prevented stays the correct "don't waste it" gate. And
# Nebula Beam explicitly ignores effects on the opponent's Active, so a protected Active is
# exactly when Nebula's "ignores effects" is the answer.)
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
ATTACK_DAMAGE = {}               # attackId -> base damage (engine-authoritative; for threat read)
SELF_SCALING_ATTACKS = set()     # attacks whose damage grows with energy on the attacker
for _a in all_attack():
    ATTACK_COST[_a.attackId] = len(_a.energies or [])
    ATTACK_COST_ENERGIES[_a.attackId] = list(_a.energies or [])
    ATTACK_DAMAGE[_a.attackId] = getattr(_a, 'damage', 0) or 0
    _t = (_a.text or '').lower()
    if 'for each' in _t and 'energy attached to this' in _t:
        SELF_SCALING_ATTACKS.add(_a.attackId)

# What TYPE each energy card provides (Ignition -> Colorless 0; Basic {W} -> Water 3).
# Critical: attaching energy must satisfy the attack's TYPE requirement, not just its count.
ENERGY_PROVIDES = {}
for _c in all_card:
    if _c.cardType in (CardType.BASIC_ENERGY, CardType.SPECIAL_ENERGY):
        ENERGY_PROVIDES[_c.cardId] = getattr(_c, 'energyType', 0)

# Situational-tech triggers (generic, data-driven):
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


# ── Mega Starmie policy ──────────────────────────────────────────────────────
class MegaStarmiePolicy:
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
                return False            # e.g. a Water requirement with only Colorless attached
        return sum(have.values()) >= colorless

    def _can_attack(self, p):
        """TYPE-AWARE: can p actually pay one of its attacks with its currently attached energy?
        NB Ignition Energy gives {C}{C}{C} on an EVOLUTION Pokémon. The engine resolves the
        true provided types in p.energies, so this stays correct as long as the observation
        reflects Ignition's tripled colorless on the Mega."""
        c = card_table.get(p.id)
        if c is None:
            return False
        attached = list(p.energies or [])
        return any(aid in ATTACK_COST_ENERGIES and self._can_pay(attached, ATTACK_COST_ENERGIES[aid])
                   for aid in (c.attacks or []))

    def _max_payable_dmg(self, attached, c):
        """Best base damage among c's attacks payable with `attached` (list of EnergyType)."""
        best = 0
        for aid in (c.attacks or []):
            cost = ATTACK_COST_ENERGIES.get(aid)
            if cost is not None and self._can_pay(attached, cost):
                best = max(best, self._attack_base_damage(aid))
        return best

    def _provided_types(self, p, src):
        """EnergyType(s) `src` provides when attached to p. CRITICAL: Ignition Energy gives
        {C}{C}{C} on an EVOLUTION Pokémon (stage1/stage2) — that single attach is what flips the
        Mega from Jetting Blow (1 {W}) to Nebula Beam ({C}{C}{C}). The static ENERGY_PROVIDES
        only knows Ignition's base {C}, so we special-case it here (the bug that kept Nebula
        unreachable: the old check saw Ignition as one colorless and never built the finisher)."""
        if src is None:
            return []
        prov = ENERGY_PROVIDES.get(src.id)
        if prov is None:
            return []
        c = card_table.get(p.id)
        if src.id == C.IGNITION_ENERGY and c is not None and (getattr(c, 'stage1', False) or getattr(c, 'stage2', False)):
            return [EnergyType.COLORLESS, EnergyType.COLORLESS, EnergyType.COLORLESS]
        return [prov]

    def _can_upgrade_attack(self, p):
        """True if SOME energy in hand, attached to p, would unlock a strictly higher-damage
        attack than p can pay now. Lets us keep fuelling the Mega toward Nebula (via Ignition)
        even though it can already pay Jetting — without slow over-filling (a 2nd Water that
        unlocks nothing returns False)."""
        c = card_table.get(p.id)
        if c is None:
            return False
        cur = list(p.energies or [])
        best_now = self._max_payable_dmg(cur, c)
        for hc in self.me.hand:
            if is_energy(hc.id) and self._max_payable_dmg(cur + self._provided_types(p, hc), c) > best_now:
                return True
        return False

    def _should_fuel(self, p):
        """Attach more energy while p can't pay an attack (type-aware) — OR while attaching would
        unlock a strictly bigger attack (Ignition -> Nebula on the Evolution Mega). Never just
        over-fills: once the best reachable attack is already payable, stop."""
        c = card_table.get(p.id)
        if c is None or not (c.attacks or []):
            return False
        if any(aid in SELF_SCALING_ATTACKS for aid in c.attacks):
            return True
        if not self._can_attack(p):
            return True
        return self._can_upgrade_attack(p)

    def _attach_helps(self, p, src):
        """Would attaching `src` let p pay an attack it can't now, OR a strictly bigger one?
        Ignition on the Evolution Mega flips Jetting Blow (120) -> Nebula Beam (210) in one attach,
        which the old static-energyType check missed (it saw Ignition as a single {C})."""
        if src is None:
            return True
        added = self._provided_types(p, src)
        if not added:
            return True
        c = card_table.get(p.id)
        if c is None:
            return True
        cur = list(p.energies or [])
        return self._max_payable_dmg(cur + added, c) > self._max_payable_dmg(cur, c)

    def _opp_threatens_bench(self):
        """Opponent has a bench-damaging (spread/snipe) attacker in play."""
        for p in (self.opponent.active + self.opponent.bench):
            c = card_table.get(p.id) if p is not None else None
            if c and any(aid in BENCH_DAMAGE_ATTACKS for aid in (c.attacks or [])):
                return True
        return False

    def _opp_has_self_ko_ability(self):
        return any(p is not None and p.id in SELF_KO_ABILITY_IDS
                   for p in (self.opponent.active + self.opponent.bench))

    def _opp_can_ko_my_mega(self):
        """Is the opponent ALREADY able to one-shot our 330HP Mega next turn? Engine-authoritative,
        no guessing: for every opponent body, take each attack it can PAY RIGHT NOW (its current
        energies via _can_pay), read the real ATTACK_DAMAGE, and double it if the Mega's weakness is
        LIGHTNING and that attack's cost includes a Lightning energy. If any such ready hit >= the
        Mega's HP, promoting the Mega just hands them the 3-prize chunk -> we'd rather wall with a
        1-prize body. Only counts attacks the opponent can pay (not speculative), so it never fires
        on a phantom threat. Any missing data short-circuits to False (current behaviour)."""
        mega_cd = card_table.get(C.MEGA_STARMIE)
        if mega_cd is None:
            return False
        mega_hp = getattr(mega_cd, 'hp', 0) or 0
        if mega_hp <= 0:
            return False
        lightning_weak = (getattr(mega_cd, 'weakness', None) == EnergyType.LIGHTNING)
        for p in (self.opponent.active + self.opponent.bench):
            if p is None:
                continue
            c = card_table.get(p.id)
            if c is None:
                continue
            attached = list(p.energies or [])
            for aid in (c.attacks or []):
                cost = ATTACK_COST_ENERGIES.get(aid)
                if cost is None or not self._can_pay(attached, cost):
                    continue          # only count attacks the opponent can actually pay now
                dmg = ATTACK_DAMAGE.get(aid, 0)
                if lightning_weak and EnergyType.LIGHTNING in cost:
                    dmg *= 2          # weakness doubles a Lightning hit on the Mega
                if dmg >= mega_hp:
                    return True
        return False

    def _energy_in_hand(self):
        return any(is_energy(c.id) for c in self.me.hand)

    def _effect_prevented(self, target):
        """True if attack EFFECTS done to `target` are prevented (Mist-style energy attached,
        or a self-prevention ability). Jetting Blow's 50 bench snipe is an effect -> 0 to such
        a target; don't waste the snipe there."""
        if target is None:
            return False
        if target.id in EFFECT_PREVENT_SELF:
            return True
        for e in (getattr(target, 'energyCards', None) or []):
            if getattr(e, 'id', None) in EFFECT_PREVENT_ENERGY:
                return True
        return False

    # ── board-state predicates (anti-brick is the win condition) ─────────────
    def _bench_count(self):
        return sum(1 for p in self.me.bench if p is not None)

    def _open_bench(self):
        return self._bench_count() < getattr(self.me, "benchMax", 5)

    def _bodies(self):
        return [p for p in (self.me.active + self.me.bench) if p is not None]

    def _mega_online(self):
        """A Mega Starmie is in play (active or bench) — the milestone that exits brick risk."""
        return any(p.id == C.MEGA_STARMIE for p in self._bodies())

    def _has_staryu_in_play(self):
        return any(p.id == C.STARYU for p in self._bodies())

    def _can_evolve_mega_now(self):
        """A Staryu is in play AND a Mega Starmie is in hand (NORMAL evolve path: the Mega comes
        from the HAND). Reserved for that path — Salvatore uses _salvatore_has_target instead."""
        return self._has_staryu_in_play() and self.hand[C.MEGA_STARMIE] > 0

    def _salvatore_has_target(self):
        """Salvatore (1189) pulls the Mega from the DECK (not the hand) and only evolves a Pokémon
        that entered THIS turn or in setup. So a valid premium target = a Staryu in play that
        appeared this turn, with no Mega already online. We DON'T gate on deck contents: the deck
        is hidden by id (only deckCount is observable), and a whiff is just a wasted supporter, not
        a crash/illegal selection — acceptable under the 0-crash rule. `appearThisTurn` is read
        defensively (getattr) so a missing field degrades to the setup fallback, never crashes."""
        if self._mega_online():
            return False
        for p in self._bodies():
            if p.id == C.STARYU and getattr(p, 'appearThisTurn', False):
                return True
        return False

    def _empty_bench_risk(self):
        """The #1 brick cause: about to be left with only the Active and an empty bench."""
        return self._bench_count() == 0

    def _need_setup(self):
        """We have NOT reached the target state (Mega online + >=2 bodies in play)."""
        return not (self._mega_online() and len(self._bodies()) >= 2)

    # ── attacker readiness ───────────────────────────────────────────────────
    def _ready_attacker(self, p):
        return p is not None and p.id in ATTACKER_IDS and self._can_attack(p)

    def _bench_attacker_ready(self):
        return any(self._ready_attacker(p) for p in self.me.bench)

    def _have_attacker(self):
        a = self.me.active[0] if self.me.active else None
        return self._ready_attacker(a) or self._bench_attacker_ready()

    # ── damage model (engine-authoritative ids) ──────────────────────────────
    def _attack_base_damage(self, attack_id):
        if attack_id == JETTING_BLOW:
            return 120
        if attack_id == NEBULA_BEAM:
            return 210
        if attack_id == TURBO_FLARE:
            return 50
        if attack_id == WATER_GUN:
            return 20
        return 0

    def _attack_damage(self, attack_id, target):
        """Damage `attack_id` does to `target` on the ACTIVE (with Weakness/Resistance), except
        Nebula Beam which explicitly ignores W/R and effects on the opponent's Active."""
        if target is None:
            return 0
        dmg = self._attack_base_damage(attack_id)
        if dmg <= 0:
            return 0
        if attack_id == NEBULA_BEAM:
            return dmg                     # ignores W/R and Active effects entirely
        od = card_table.get(target.id)
        if od is not None:
            if od.weakness == EnergyType.WATER:
                dmg *= 2
            elif od.resistance == EnergyType.WATER:
                dmg = max(0, dmg - 30)
        return dmg

    def _active_attacker(self):
        return self.me.active[0] if self.me.active else None

    def _available_attacks(self, p):
        """Attack ids p can actually pay right now (type-aware), in deck order."""
        c = card_table.get(p.id) if p is not None else None
        if c is None:
            return []
        attached = list(p.energies or [])
        return [aid for aid in (c.attacks or [])
                if aid in ATTACK_COST_ENERGIES and self._can_pay(attached, ATTACK_COST_ENERGIES[aid])]

    def _best_active_dmg(self, target):
        """Best damage our current Active can do to `target` with what it can pay now."""
        a = self._active_attacker()
        if a is None or target is None:
            return 0
        return max((self._attack_damage(aid, target) for aid in self._available_attacks(a)), default=0)

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
        # First-or-second: GO FIRST. An evolution/setup deck wants the extra turn to bench a
        # 2nd basic and bring the Mega online (via Salvatore) before it must attack — exactly
        # the anti-brick milestones. (All observed wins set up early.)
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
        """Are we Item-locked (can't play Item cards)? Detect from a known lock ability on the
        opponent's Active, OR from game state: we hold Item card(s) but none is playable."""
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

    # — abilities —
    def _score_ability(self, o):
        # No deck-out management and no recurring offensive ability in this deck. Cinderace's
        # 'Explosiveness' is a setup-time placement (resolved via the SETUP contexts, not an
        # in-turn ability option), so any ABILITY option here is generic utility — take it mildly.
        card = get_card(self.obs, o.area, o.index, self.my_index)
        if card is None:
            return 0
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
        # ANTI-BRICK P0: getting a 2nd basic onto the bench is the single highest-value play.
        # Staryu is the evolution base (must be in play to evolve the Mega); Cinderace is a
        # 1-prize body that also shields. Bench bodies aggressively; never end on an empty bench.
        if cid == C.STARYU:
            # Each Staryu benched is a future Mega. Want at least one in play, ideally two.
            base = 20000 if self._bench_count() == 0 else 18500
            return base - 300 * n
        if cid == C.CINDERACE:
            # A 1-prize body; good shield/secondary attacker. Bench it to avoid empty-bench
            # risk and to have a free-retreat pivot, but below Staryu (Staryu builds the wincon).
            base = 17500 if self._bench_count() == 0 else 14000
            return base - 250 * n
        if cid == C.MEGA_STARMIE:
            # Mega Starmie is a Stage1 evolution — it is NOT played down as a basic. If the
            # engine ever offers it as a PLAY (it shouldn't), don't; evolve it via EVOLVE.
            return -1
        return 12000 - 200 * n

    def _need_pieces(self):
        return not self._mega_online()

    def _score_play_trainer(self, card):
        cid = card.id
        opp_active = self.opponent.active[0] if self.opponent.active else None

        # ── SETUP ENGINE (anti-brick priority order) ────────────────────────
        # P0: Buddy-Buddy Poffin — put up to 2 Staryu (70HP basics) on the bench. The single
        # strongest anti-brick card: directly fixes the empty-bench loss. Always high while we
        # still need bench bodies.
        if cid == C.BUDDY_POFFIN:
            # P0 anti-brick ONLY while we still need setup. Once the Mega is online AND we have
            # >=2 bodies in play, keidroid stops slamming Poffin and instead attacks / develops
            # (the MAIN 44% gap: we spammed Poffin 54x with a full hand and Mega already up).
            # Relax to a low utility score there so attacking/attaching outranks it.
            if self._need_setup() and self._open_bench() and (self.field[C.STARYU] < 2 or self._bench_count() == 0):
                return 19000
            return 600 if self._open_bench() else -1

        # Salvatore — evolve Staryu->Mega the SAME turn the Staryu entered (skip the wait).
        # This is the core combo and the fastest path to "Mega online". Huge while no Mega yet.
        if cid == C.SALVATORE:
            if self.state.supporterPlayed:
                return -1
            # Salvatore pulls the Mega from the DECK, so the gate is "is there a Staryu it can
            # evolve", NOT "is a Mega in hand". Premium case: a Staryu that entered THIS turn (the
            # exact target the normal evolve can't touch) and no Mega online yet -> fire the combo.
            if self._salvatore_has_target():
                return 21000
            # Fallback: a setup Staryu already in play (no appearThisTurn) and no Mega online ->
            # Salvatore still accelerates it onto the board. Below the precise case so we don't
            # spend the supporter on a false read when the premium target exists.
            if not self._mega_online() and self._has_staryu_in_play():
                return 20500
            # No evolvable Staryu (or a Mega is already online) -> Salvatore whiffs; don't waste it.
            return -1

        # Hilda — search an Evolution Pokémon (Mega Starmie) + an Energy. Premier setup motor
        # while we still need the Mega and/or energy. Beats other draw when pieces are missing.
        if cid == C.HILDA:
            if self.state.supporterPlayed:
                return -1
            if self._need_pieces() or not self._energy_in_hand():
                return 18000
            return 4000

        # Mega Signal — tutor a Mega Starmie to hand (sets up the Salvatore/evolve). Item, so
        # it doesn't compete with the supporter slot. Grab the Mega while we lack one in hand.
        if cid == C.MEGA_SIGNAL:
            if self.hand[C.MEGA_STARMIE] == 0 and not self._mega_online():
                return 17000
            if self.hand[C.MEGA_STARMIE] == 0:
                return 9300     # a backup Mega in hand is still useful (3-prize wall x2)
            # keidroid plays Mega Signal 11x: it's a free Item dig that gets played out of the
            # hand every turn (a backup Mega = a second 3-prize wall). Keep it ABOVE attach/attack
            # (the MAIN gap: we attacked/attached while keidroid was still tutoring the 2nd Mega).
            return 8600

        # Ultra Ball — search ANY Pokémon. Dig for the missing setup body (a Staryu to bench, or
        # a Mega to evolve). Costs 2 cards, so only when a piece is actually missing.
        if cid == C.ULTRA_BALL:
            if self._empty_bench_risk() or self._need_pieces():
                if self.me.handCount >= 3:   # need 2 to discard + the ball itself
                    return 16000
            return 600

        # Pokégear 3.0 — dig top 7 for a Supporter (Salvatore/Hilda are the ones we want).
        # Consistency glue; fine to fire early when we haven't played a supporter yet.
        if cid == C.POKEGEAR:
            if not self.state.supporterPlayed and self._need_setup():
                return 12000
            # keidroid plays Pokégear 14x (its most-played MAIN card): a free Item dig played out
            # EVERY turn before attaching/attacking. Keep it above attach (8200) so we play out the
            # hand first instead of immediately committing energy/attacking.
            return 9400

        # Lillie's Determination — shuffle hand, draw 6. Recycler when the hand is small/stuck and
        # we still need setup (small hand only, so it can't dump a developed hand). Supporter slot.
        if cid == C.LILLIE_DET:
            if self.state.supporterPlayed:
                return -1
            if self.me.handCount <= 3 and self._need_setup():
                return 11000
            # keidroid plays Lillie's 14x (tied #1 MAIN card): the primary draw supporter, fired
            # almost every turn the supporter slot is open, BEFORE attaching/attacking (the examples
            # show keidroid playing it at hand=4/6/7 where we instead attached Ignition). Draw refuels
            # the hand cheaply, so keep it above attach (8200) but below the Salvatore/Hilda setup
            # combos. (The supporter-slot gate already prevents double-supporter turns.)
            return 8700

        # Harlequin — both shuffle hands and redraw (coin flip self 5/3). Reset a dead hand only;
        # symmetric (helps opponent too), so it's a last-resort recovery.
        if cid == C.HARLEQUIN:
            if self.state.supporterPlayed:
                return -1
            if self.me.handCount <= 2 and self._need_setup():
                return 7000
            # keidroid plays Harlequin 4x: a redraw supporter it cycles out of the hand. It's
            # symmetric (helps the opponent too), so keep it the LOWEST of the draw band — above
            # attach (8200) so it's played out, but below the cleaner Lillie's/Pokégear draw.
            return 8300

        # Night Stretcher — recover a Staryu/Mega/Cinderace or a Basic {W} from discard. Anti-brick
        # recovery after a KO, or to re-buy the evolution base. Item.
        if cid == C.NIGHT_STRETCHER:
            want = (self.discard.get(C.STARYU, 0) or self.discard.get(C.MEGA_STARMIE, 0)
                    or self.discard.get(C.CINDERACE, 0) or self.discard.get(C.WATER_ENERGY, 0))
            if want:
                # keidroid plays Night Stretcher out of hand even mid-combat (example:
                # Night Stretcher where we attacked). When it has a real recovery target keep it
                # above attach (8200) so the Item is used before committing energy/attacking.
                return 9000 if (self._empty_bench_risk() or self._need_setup()) else 8400
            return 200

        # ── DISRUPTION ──────────────────────────────────────────────────────
        # Crushing Hammer — coin flip to discard an opponent Energy. Free value (Item), but never
        # over real setup; fire when the opponent actually has energy to strip.
        if cid == C.CRUSHING_HAMMER:
            opp_has_energy = any(self._energy_count(p) >= 1
                                 for p in (self.opponent.active + self.opponent.bench) if p is not None)
            return 3500 if opp_has_energy else -1

        # ── TOOLS ───────────────────────────────────────────────────────────
        # Hero's Cape (ACE SPEC) — +100HP on a Mega in play (330->430). One-per-deck; place it
        # once a Mega exists to ride (prefer the Active Mega via the attach-target scoring).
        if cid == C.HEROS_CAPE:
            if self._mega_online():
                return 10000
            return -1

        # ── CLOSER ──────────────────────────────────────────────────────────
        # Boss's Orders — drag a benched opponent up to the Active. CLOSER ONLY: use it when a
        # benched target is lethal to us this turn and KO-ing it wins (or removes a piece we can
        # actually finish). Never a generic mid-development gust.
        if cid == C.BOSS_ORDERS:
            if self.state.supporterPlayed:
                return -1
            ko = [p for p in self.opponent.bench
                  if p is not None and self._best_active_dmg(p) >= getattr(p, "hp", 9999)]
            if not ko:
                return -1
            best = max(ko, key=lambda p: prize_count(p))
            # Winning move: this KO takes our last prize(s) -> drag and finish.
            if prize_count(best) >= len(self.me.prize):
                return 20000
            # Otherwise gust a high-value target only when our Active can't already lethal the
            # opponent's Active (don't trade a better line for a gust).
            if opp_active is not None and self._best_active_dmg(opp_active) >= getattr(opp_active, "hp", 9999):
                return -1
            # NON-closing gust: keidroid uses Boss's Orders as a CLOSER ONLY (it played Boss 0x in
            # development MAIN turns where we played it 8x, burning the supporter slot that should
            # go to Lillie's/Hilda/Pokégear/Salvatore). A non-lethal gust still consumes the
            # once-per-turn supporter, so price it BELOW the draw/setup engine and below attacking:
            # only fire it when nothing else (draw, attach, attack) wants the turn.
            return 700

        # Wally's Compassion — fully heal a Mega ex (returns its energy to hand). Safety net only:
        # the Active Mega is heavily damaged. Returning energy is a real cost (must re-attach),
        # so reserve it for genuine near-death.
        if cid == C.WALLYS:
            if self.state.supporterPlayed:
                return -1
            a = self._active_attacker()
            if a is not None and a.id == C.MEGA_STARMIE:
                # Pokemon has NO `.damage` field — damage taken = maxHp - current hp.
                # Use the live maxHp (reflects Hero's Cape +100 -> 430) with a base fallback.
                max_hp = getattr(a, "maxHp", None) or (getattr(card_table.get(a.id), "hp", 330) or 330)
                dmg = max(0, max_hp - (getattr(a, "hp", max_hp) or max_hp))
                if dmg >= max_hp * 0.6:    # taken >=60% of max HP -> worth a full heal
                    return 12000
            return -1

        return 9000

    # — evolve —
    def _score_evolve(self, o):
        target = get_card(self.obs, o.inPlayArea, o.inPlayIndex, self.my_index)
        if not isinstance(target, Pokemon):
            return 0
        card = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        cid = card.id if card is not None else None
        # Evolving Staryu -> Mega Starmie is the core wincon milestone. Always do it (whether via
        # a normal evolve or enabled by Salvatore the same turn). Prefer evolving the Active Staryu
        # (so the wall is up front), but evolving any Staryu brings a Mega online.
        if cid == C.MEGA_STARMIE:
            base = 21000
            if o.inPlayArea == AreaType.ACTIVE:
                base += 500
            return base
        return 18000

    # — attach energy —
    def _score_attach(self, o):
        p = get_card(self.obs, o.inPlayArea, o.inPlayIndex, self.my_index)
        if not isinstance(p, Pokemon):
            return 0
        # GENERAL RULE (type-aware): attach only while the body still can't pay an attack; once
        # it CAN attack, hold the rest. (No self-scaling attacker here, so we never over-fill.)
        if not self._should_fuel(p):
            return -1
        src = get_card(self.obs, AreaType.HAND, o.index, self.my_index)
        if not self._attach_helps(p, src):
            return -1
        # RESERVE Ignition (the Nebula enabler) — don't pre-load it by default. keidroid attaches
        # Basic {W}->Mega ~10x and Ignition only ~4x (the situational finisher), while our prior
        # fix over-attached Ignition 22x. When the body can ALREADY pay an attack (Jetting is up),
        # an Ignition attach is only the Nebula upgrade: keep it HIGH only if Nebula would be
        # LETHAL on the opponent's Active this turn; otherwise hold Ignition for later (low score).
        if src is not None and src.id == C.IGNITION_ENERGY and self._can_attack(p):
            opp = self.opponent.active[0] if self.opponent.active else None
            nebula_lethal = (opp is not None
                             and self._attack_damage(NEBULA_BEAM, opp) >= max(0, getattr(opp, "hp", 0) or 0))
            if not nebula_lethal:
                return 400        # reserve Ignition; prefer attacking / a Water attach instead
        # FIRST-ATTACH Ignition reservation: even when the body can't attack YET, attaching Ignition
        # straight onto an empty Mega skips Jetting Blow into Nebula Beam — but that BURNS the scarce
        # Ignition (4 copies, the finisher) when a Basic {W} (9 copies) would enable Jetting Blow
        # just as well. keidroid attaches {W}->Mega 5x and Ignition only 4x; we over-attached
        # Ignition 29x vs 16 Water. So if a Basic {W} is also in hand and Nebula isn't lethal now,
        # demote the Ignition attach below the Water attach (8200) so Water is taken first.
        if (src is not None and src.id == C.IGNITION_ENERGY and p.id in ATTACKER_IDS
                and any(hc.id == C.WATER_ENERGY for hc in self.me.hand)):
            opp = self.opponent.active[0] if self.opponent.active else None
            nebula_lethal = (opp is not None
                             and self._attack_damage(NEBULA_BEAM, opp) >= max(0, getattr(opp, "hp", 0) or 0))
            if not nebula_lethal:
                return 7000       # below the {W} attach (8200): take Water first, reserve Ignition
        # Prefer fuelling an attacker (Mega/Cinderace), prioritising the Active so it can swing
        # this turn. A Water on the Active Mega enables Jetting Blow (1 {W}); an Ignition on the
        # (Evolution) Mega gives {C}{C}{C} = Nebula Beam in one attach.
        if p.id in ATTACKER_IDS:
            return 8000 + (200 if o.inPlayArea == AreaType.ACTIVE else 0)
        if p.id == C.STARYU:
            return 1500           # pre-fuel the base (energy carries through evolution to Mega)
        return -1                 # otherwise hold the energy

    # — retreat —
    def _score_retreat(self):
        active = self._active_attacker()
        opp = self.opponent.active[0] if self.opponent.active else None
        if active is None or opp is None:
            return -1
        # No defensive retreating. The ONE good retreat is the planned pivot: a fully-built Mega
        # (or any ready attacker) is on the bench while a non-attacker (e.g. the Cinderace shield
        # that has done its job, or a naked Staryu) is Active -> bring the wincon up to swing.
        if not self._ready_attacker(active):
            for p in self.me.bench:
                if self._ready_attacker(p):
                    return 6000
        return -1

    # — attack —
    def _score_attack(self, o):
        active = self._active_attacker()
        opp = self.opponent.active[0] if self.opponent.active else None
        if active is None or opp is None:
            return 800
        aid = o.attackId
        dmg = self._attack_damage(aid, opp)
        if dmg <= 0:
            # A 0-damage attack (e.g. an unpayable/utility option) — never spend the turn on it
            # if anything else can act. Above END only as a last resort.
            return 300
        opp_hp_left = max(0, getattr(opp, "hp", 0) or 0)   # .hp is ALREADY current remaining HP

        # LETHAL & GAME-WINNING: if this KO takes our last remaining prize(s), win now.
        if opp_hp_left <= dmg and prize_count(opp) >= len(self.me.prize):
            return 95000

        score = 1000 + min(dmg, 320)

        # Jetting Blow vs Nebula Beam = pure HP arithmetic (the confirmed pilot rule):
        #   - if 210 (Nebula) one-shots the Active and 120 (Jetting) does NOT, take Nebula.
        #   - else default to Jetting Blow (cheaper, + the 50 bench snipe sculpts their board).
        if aid == NEBULA_BEAM:
            jetting_dmg = self._attack_damage(JETTING_BLOW, opp)
            if opp_hp_left <= dmg and opp_hp_left > jetting_dmg:
                score += 5000            # Nebula is the one-shot Jetting can't get -> finisher
            elif opp_hp_left <= jetting_dmg:
                # Jetting already KOs AND snipes the bench -> prefer the cheaper Jetting.
                score -= 2000
            else:
                # Neither one-shots: don't burn the 3-energy Nebula for chip; Jetting is barer.
                score -= 1500
        elif aid == JETTING_BLOW:
            score += 600                 # default attack: cheap + bench snipe pressure
            if self._opp_threatens_bench() or any(p is not None for p in self.opponent.bench):
                score += 200             # the 50 snipe has a target / shapes their board
        elif aid == TURBO_FLARE:
            # Cinderace chip + ramp basic energy onto the bench (helps build the Mega). Useful as
            # a shield-active attack while the Mega is offline; below a real Mega KO.
            score += 300
            if not self._mega_online():
                score += 200             # the energy ramp directly advances setup

        if opp_hp_left <= dmg:
            score += 2500 + prize_count(opp) * 200
        return score

    # — sub-selects —
    def _score_card(self, o):
        card = get_card(self.obs, o.area, o.index, o.playerIndex)
        if card is None:
            return 0
        ctx = self.context
        # Opponent card targeting (e.g. Crushing Hammer: discard opp energy) — prefer stripping
        # from the Active / a powered body.
        if o.playerIndex == self.op_index and not isinstance(card, Pokemon):
            d = card_table.get(card.id)
            if d is not None and d.cardType in (CardType.SPECIAL_ENERGY, CardType.BASIC_ENERGY):
                return 300 + (200 if getattr(o, 'inPlayArea', None) == AreaType.ACTIVE else 0)
            return 50
        if ctx in (SelectContext.EVOLVES_TO, SelectContext.EVOLVES_FROM):
            return self._score_evolve_card(card, ctx)
        if ctx in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
            return self._score_active_choice(o, card)
        if ctx == SelectContext.SETUP_ACTIVE_POKEMON:
            return self._score_setup_active(card)
        if ctx in (SelectContext.SETUP_BENCH_POKEMON, SelectContext.TO_BENCH, SelectContext.TO_FIELD):
            return self._score_to_bench(card)
        if ctx == SelectContext.TO_HAND:
            return self._score_to_hand(card)
        if ctx == SelectContext.ATTACH_TO:
            if isinstance(card, Pokemon):
                return self._score_attach_target(card, o.inPlayArea == AreaType.ACTIVE)
            # ATTACH_TO also offers the ENERGY card to attach (not only the target Pokémon).
            # keidroid attaches its Basic {W} here while RESERVING Ignition for the Nebula
            # spike, so prefer a Water source over Ignition; never decline the attach (the
            # old Pokemon-only branch returned 0 -> we played [] and skipped the attach).
            if is_energy(card.id):
                return 120 if ENERGY_PROVIDES.get(card.id) == EnergyType.WATER else 80
            return 10
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

    def _score_evolve_card(self, card, ctx):
        """EVOLVES_TO / EVOLVES_FROM sub-selects. The Mega Starmie line IS the win condition;
        the old code had no branch for these contexts so _score_card fell through to 0 and the
        optional select dropped it -> we DECLINED the evolution (the EVOLVES_TO 0/7 bug, the
        single biggest piloting gap). Score the wincon pieces high so we always evolve.
          - EVOLVES_TO: the evolution TARGET (Mega Starmie ex) -> take it, hard.
          - EVOLVES_FROM: the base to evolve FROM (Staryu) -> take it; Staryu is our only base."""
        if card is None:
            return 0
        cid = card.id
        if cid == C.MEGA_STARMIE:
            return 21000          # bring the Mega online -> the wincon milestone
        if cid in (C.STARYU, C.CINDERACE):
            return 18000          # a valid evolution base in our line
        return 9000               # any other legal evolution offered -> still don't decline

    def _score_attach_target(self, p, is_active):
        if not self._should_fuel(p):
            return -1             # already CAN attack (type-aware) -> don't over-fill
        if p.id in ATTACKER_IDS:
            return 8000 + (200 if is_active else 0)
        if p.id == C.STARYU:
            return 1500
        return -1

    def _score_active_choice(self, o, card):
        if not isinstance(card, Pokemon):
            return 0
        if o.playerIndex == self.op_index:
            # Choosing the opponent's new Active (our Boss/gust) — drag the body whose KO is most
            # valuable / closest to lethal.
            d = self._best_active_dmg(card)
            if d >= getattr(card, "hp", 9999):
                if prize_count(card) >= len(self.me.prize):
                    return 90000
                return 8000 + prize_count(card) * 500
            return max(1, d)
        if o.playerIndex != self.my_index:
            return 0
        # Promote (after a KO) the body that best keeps us attacking. Order:
        #  1) a ready attacker (Mega/Cinderace that can swing now) — top.
        #  2) any Mega Starmie (the 330 wall + wincon), then Cinderace (160 shield, 1-prize).
        #  3) a Staryu (fragile, but the evolution base -> can become a Mega) over nothing.
        score = self._energy_count(card) * 10
        if self._ready_attacker(card):
            score += 300
        elif card.id == C.MEGA_STARMIE:
            # DON'T volunteer the 3-prize wall into a one-shot. If the opponent can ALREADY KO the
            # Mega next turn (e.g. a charged Lightning attacker into the Mega's weakness) AND we can
            # instead promote a 1-prize body, invert the preference: let the cheap body wall (give
            # back 1 prize, not 3) and keep the Mega benched. Otherwise the Mega is top as before.
            if self._opp_can_ko_my_mega() and self._has_one_prize_promo_option():
                score -= 150     # demote below Cinderace's +140 so the 1-prize body walls
            else:
                score += 220     # the wall + wincon (online next turn after 1 energy)
        elif card.id == C.CINDERACE:
            score += 140         # 160 shield, free retreat, 1-prize give-back
        elif card.id == C.STARYU:
            score += 60          # evolution base -> can become the Mega; better than chumping tech
        score += getattr(card, 'hp', 0) // 30   # mild "promote the survivor" tiebreak
        return score + 1

    def _has_one_prize_promo_option(self):
        """Among the bodies we could promote here, is there a 1-prize alternative (a Cinderace)
        to wall with instead of the 3-prize Mega? Scans our own CARD options in this select so we
        only demote the Mega when a cheaper wall actually exists; reads cards defensively."""
        for o in self.select.option:
            if o.type != OptionType.CARD or getattr(o, 'playerIndex', self.my_index) != self.my_index:
                continue
            c = get_card(self.obs, o.area, o.index, self.my_index)
            if isinstance(c, Pokemon) and c.id == C.CINDERACE:
                return True
        return False

    def _score_setup_active(self, card):
        # Opening-active choice (anti-brick rules from the replays):
        #  - Cinderace is the preferred SHIELD active (160HP, 1-prize, retreat 0): tanks early
        #    chip while we build the Mega on the bench, and its 0 retreat frees it for the
        #    finished Mega. (Its Explosiveness lets it START active in setup.)
        #  - Staryu is acceptable only because it's the evolution base; a lone Staryu active with
        #    empty bench is the canonical brick — but with a same-turn Mega path it becomes the
        #    330 wall, so it's a fine #2. The bench rules secure the 2nd body separately.
        #  - Both bodies have an offensive future; never strand a dead active.
        if card is None:
            return 0
        if card.id == C.CINDERACE:
            return 50          # preferred shield active
        if card.id == C.STARYU:
            return 30          # evolution base -> Mega; needs a same-turn path or a benched 2nd body
        if card.id == C.MEGA_STARMIE:
            return 40          # if somehow offered (shouldn't open as a Stage1) it's still the wall
        return 5

    def _score_to_bench(self, card):
        # Anti-brick: filling the bench is THE priority. Staryu first (each is a future Mega),
        # Cinderace second (shield/secondary), anything else last.
        if card is None:
            return 0
        d = card_table.get(card.id)
        if d is None or d.cardType != CardType.POKEMON:
            return 0
        cid = card.id; n = self.field[cid]
        if cid == C.STARYU:
            return 200 - 30 * n
        if cid == C.CINDERACE:
            return 170 - 30 * n
        if cid == C.MEGA_STARMIE:
            return -1            # Mega is an evolution, not a benched basic
        return 100 - 20 * n

    def _score_to_hand(self, card):
        # Search-to-hand priority (Hilda/Mega Signal/Ultra Ball/Pokégear/Night Stretcher).
        # Race the setup milestones: get a Staryu to bench, a Mega to evolve, and {W} to fuel.
        if card is None:
            return 0
        cid = card.id
        score = 200 - self.hand[cid] * 40
        if cid == C.STARYU:
            # Need bodies in play; fetch a Staryu when the bench is thin / no Mega line yet.
            if self.field[C.STARYU] + self.field[C.MEGA_STARMIE] < 2:
                score += 90
            else:
                score += 10
        elif cid == C.MEGA_STARMIE:
            # One Mega in hand is enough to evolve; don't hoard a second over setup pieces.
            score += 80 if (self.hand[C.MEGA_STARMIE] == 0 and self._has_staryu_in_play()) else 20
        elif cid == C.CINDERACE:
            score += 40 if self.field[C.CINDERACE] == 0 else -10
        elif cid == C.SALVATORE:
            # The same-turn evolve enabler — very high when we have a Staryu to evolve.
            score += 85 if self._has_staryu_in_play() else 30
        elif cid == C.HILDA:
            score += 55 if self._need_pieces() else 10
        elif cid in (C.LILLIE_DET, C.HARLEQUIN, C.POKEGEAR):
            score += 25
        elif is_energy(cid):
            # Fetch {W} (the type that fuels Jetting Blow) when we lack energy in hand; Ignition
            # (colorless) is for the Nebula spike, useful but lower default priority.
            if not self._energy_in_hand():
                score += 70 if ENERGY_PROVIDES.get(cid) == EnergyType.WATER else 50
            else:
                score += 30
        return score

    def _score_discard(self, card):
        # Forced discards (Ultra Ball cost, hand-size effects). Higher score = pitch first.
        # PITCH PRIORITY copied from keidroid's curated multi-card discards (the DISCARD 0/4 bug):
        #   Lillie's Determination (3/4 turns)  >  Basic {W} Energy (2/4)  >  Buddy Poffin once
        #   setup is done / spare supporters / duplicate items  >>  keep the wincon BODIES.
        # Two errors this fixes: (a) we under-pitched Lillie's (only when the supporter slot was
        # already spent) — keidroid pitches it freely as dead shuffle-draw fodder (4 copies);
        # (b) we dumped TWO Mega Starmie ex on one Ultra Ball — the Mega must sit BELOW all the
        # fodder so Lillie's/Water/spare-trainers are always pitched first and a 2nd Mega only goes
        # as a last resort.
        if card is None:
            return 0
        cid = card.id

        # Lillie's Determination — keidroid's #1 pitch. A shuffle-and-draw supporter is dead weight
        # in hand the moment you'd rather keep what you drew; with 4 copies it's the prime fodder.
        if cid == C.LILLIE_DET:
            return 95

        # Basic {W} Energy — keidroid's #2 pitch (9 copies, re-buyable via Night Stretcher).
        if cid == C.WATER_ENERGY:
            return 85 if self.hand[cid] >= 2 else 70

        # Buddy-Buddy Poffin — pure anti-brick setup card; once the Mega is online with a board it
        # is dead (keidroid pitched it post-setup). Before setup, keep it (it's our bench fixer).
        if cid == C.BUDDY_POFFIN:
            return 75 if not self._need_setup() else -40

        # Spare/spent supporters (Hilda, Salvatore, Harlequin, Wally's, Boss's). Pitch a duplicate
        # or a supporter that's dead because the slot is already spent this turn (keidroid pitched
        # Hilda). Kept below Lillie's/Water so those go first.
        if cid in (C.SALVATORE, C.HILDA, C.HARLEQUIN, C.WALLYS, C.BOSS_ORDERS):
            if self.hand[cid] >= 2 or self.state.supporterPlayed:
                return 60
            return 5

        # Ignition Energy — the SCARCE finisher enabler (4 copies). Keep unless a duplicate.
        if cid == C.IGNITION_ENERGY:
            return 55 if self.hand[cid] >= 2 else -40

        if self.hand[cid] >= 2 and cid not in (C.STARYU, C.MEGA_STARMIE, C.CINDERACE):
            return 50            # any other duplicate (items) -> fodder

        # Mega Starmie ex — KEEP. The wincon body sits BELOW every piece of fodder above, so it is
        # only ever pitched when nothing else can be (keidroid pitched at most ONE spare Mega, never
        # two). Last/needed copy = never.
        if cid == C.MEGA_STARMIE:
            need_in_hand = 0 if self._mega_online() else 1
            if self.hand[cid] > need_in_hand:
                return 20        # a genuine surplus Mega, only after all fodder is exhausted
            return -120          # the last/needed Mega -> never pitch

        if cid in (C.STARYU, C.CINDERACE):
            # Don't volunteer the last copy of a body we don't have in play.
            return -60 if self.field[cid] == 0 else 5
        return 10                # singleton utility items -> mild pitch over keeping dead cards

    def _score_putback(self, card):
        # Lillie's/Harlequin shuffle-to-deck choices, or a put-to-deck/prize effect. Send back
        # duplicates; keep singletons of the wincon.
        if card is None:
            return 0
        if self.hand[card.id] >= 2:
            return 60
        if card.id in (C.STARYU, C.MEGA_STARMIE, C.CINDERACE, C.SALVATORE):
            return -40
        return 10


def agent(obs_dict, config=None):
    # FMA: accept an optional 2nd positional (the kaggle/cabt harness calls agent(obs, config));
    # config is unused. The deck-phase probe passes a dict with no "select".
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
            sel = MegaStarmiePolicy(obs).choose()
            if not _validate_obj(sel, obs.select):
                # policy produced an illegal selection -> never return it (FMA: 0 INVALIDs)
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
