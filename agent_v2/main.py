"""
Pokémon TCG AI Battle (Kaggle cabt env) — robust dict-only agent WITH CARD KNOWLEDGE.

This is agent_v2: it derives from agent/main.py's verified, crash-proof scaffolding
(dict-only over the raw obs; never crash; validate count/range; cwd-safe loaders;
repetition-safe normalize_selection / _legal_fallback) and ADDS A STATIC CARD TABLE
(cards.json, parsed from the official EN_Card_Data.csv) so MAIN scoring can reason
about real damage / KO / weakness instead of playing blind.

Runtime contract (verified empirically in docker, 22 jun 2026):
  - Motor lives in pip `kaggle_environments` (env "cabt"), runs OFFLINE with NO Kaggle
    identity, so cg.api / all_card_data are NOT importable here. We work SOLELY off the
    raw obs dict. cards.json is a STATIC data file packed in the tar — not the engine.
  - agent(obs, config=None) -> list[int].
      * obs["select"] is None -> deck-selection phase: return the 60 card_ids.
      * otherwise              -> return between select["minCount"] and
                                  select["maxCount"] INDICES into select["option"].
  - Wrong count / out-of-range index => INVALID => reward -1 (instant loss). We validate
    len + range on EVERY return and never crash (global try/except + legal fallback).

Card knowledge (agent_v2 only):
  - cards.json maps str(card_id) -> {hp, type, weakness, retreat, attacks:[{name,
    energy_count, damage}]}.
  - The live obs gives our/opponent pokemon as dicts with id/hp/maxHp/energies. We join
    obs (live state) with cards.json (static numbers) to:
      * score ATTACK by estimated damage; HUGE bonus when est. damage >= opp active hp
        (a KO), and the maximum score when that KO takes our last prize (we win);
      * apply a weakness x2 multiplier when our type matches the opponent's weakness;
      * ATTACH energy to the attacker that still can't pay its best attack, and stop
        once it can (no over-fill) so we transition to attacking sooner.
  - If cards.json fails to load, the table is empty and we degrade gracefully to the
    structural heuristic (same as agent/) — never crash.
"""

from __future__ import annotations

import json
import os
import sys

# ── configuration ───────────────────────────────────────────────────────────
# IS_FIRST: pick whether to go first. WEAK SIGNAL (sub-sampled): a 20-game probe hinted
# going second was better (0W/10L first vs 4W/6L second), so we DECLINE to go first. This
# is NOT robustly established — re-measure with >=100 games before trusting it. (Verifier
# 22 jun flagged the original probe as undersampled.)
GO_FIRST = False
MAX_ACTIONS_GUARD = 50   # MAIN watchdog: above this turnActionCount, force END.
LOW_TIME_GUARD = 30.0    # seconds: below this remainingOverageTime, play fast.

# MAIN ordering mode (A/B'd in docker, 22 jun; verifier-reproduced numbers):
#   - False = explicit card-aware type-priority scheme: EVOLVE > ABILITY > ATTACH >
#     PLAY > ATTACK (attacks ranked by est. damage / weakness, KO/winning attack pulled
#     to the front, no voluntary retreat).
# HONEST STANDING (do NOT overstate): this scheme DOMINATES the blind structural agent
# (agent/) ~80%, which proves card knowledge adds real value — BUT it still LOSES to the
# trivial first-legal baseline (~22-27% win-rate, first-legal significantly better). In a
# mirror match there is no card-quality edge to exploit and first-legal's greedy "option[0]"
# is strong because the engine appears to list options best-first. agent_v2 is validated
# only as "better than the blind agent", NOT as competitive with first-legal.
TRUST_ENGINE_ORDER = False

# ── OptionType (int) ─────────────────────────────────────────────────────────
OPT_NUMBER = 0
OPT_YES = 1
OPT_NO = 2
OPT_CARD = 3
OPT_ENERGY = 6
OPT_PLAY = 7
OPT_ATTACH = 8
OPT_EVOLVE = 9
OPT_ABILITY = 10
OPT_RETREAT = 12
OPT_ATTACK = 13
OPT_END = 14

# ── SelectContext (int) ──────────────────────────────────────────────────────
CTX_MAIN = 0
CTX_SETUP_ACTIVE = 1
CTX_SETUP_BENCH = 2
CTX_SWITCH = 3
CTX_TO_ACTIVE = 4
CTX_TO_BENCH = 5
CTX_TO_HAND = 7
CTX_DISCARD = 8
CTX_DAMAGE_COUNTER_A = 13
CTX_DAMAGE_COUNTER_B = 14
CTX_ATTACH_FROM = 21
CTX_ATTACH_TO = 22
CTX_IS_FIRST = 41
CTX_MULLIGAN = 42

AREA_ACTIVE = "active"
AREA_BENCH = "bench"

# Area codes appear as INTS in option dicts (verified in docker 22 jun): inPlayArea
# 4 = own active, 5 = own bench (these mirror CTX_TO_ACTIVE / CTX_TO_BENCH). The
# generic `area` field carries source areas (hand=2, etc.). We only need to resolve
# the in-play target areas to read a live pokemon dict.
INPLAY_ACTIVE_CODES = (4, AREA_ACTIVE, "ACTIVE")
INPLAY_BENCH_CODES = (5, AREA_BENCH, "BENCH")

# MAIN base priorities: setup first, attack handled specially (scored by damage).
MAIN_PRIORITY = {
    OPT_EVOLVE: 100,
    OPT_ABILITY: 95,
    OPT_ATTACH: 90,
    OPT_PLAY: 80,
    OPT_ATTACK: 60,   # base; real attacks get a damage/KO score on top
    OPT_RETREAT: 20,
    OPT_END: 1,
}

# ── robust loaders (cwd-independent, load once at module level) ───────────────
def _resolve_path(filename):
    cands = []
    if "__file__" in globals():
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename))
    cands.append(filename)
    cands.append("/kaggle_simulations/agent/" + filename)
    for p in sys.path:
        if p:
            cands.append(os.path.join(p, filename))
    for p in cands:
        try:
            if os.path.exists(p):
                return p
        except Exception:
            continue
    return None


def _load_deck():
    path = _resolve_path("deck.csv")
    if not path:
        return []
    try:
        with open(path, "r") as f:
            ids = [int(x) for x in f.read().splitlines() if x.strip()]
        return ids[:60]
    except Exception:
        return []


def _load_cards():
    """Load the static card table. On ANY failure return {} (agent degrades, never crashes)."""
    path = _resolve_path("cards.json")
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


my_deck = _load_deck()
CARDS = _load_cards()

# ── diagnostics ───────────────────────────────────────────────────────────────
_DIAG = {
    "decisions": 0,
    "policy_ok": 0,
    "fallbacks": 0,
    "deck_returns": 0,
    "cards_loaded": len(CARDS),
    "attacks_scored": 0,
    "ko_attacks": 0,
    "errors": {},
}


def _record_error(exc):
    k = type(exc).__name__ + ": " + str(exc)[:160]
    _DIAG["errors"][k] = _DIAG["errors"].get(k, 0) + 1


def diag_reset():
    _DIAG.update({"decisions": 0, "policy_ok": 0, "fallbacks": 0,
                  "deck_returns": 0, "attacks_scored": 0, "ko_attacks": 0,
                  "errors": {}})


def diag_snapshot():
    s = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DIAG.items()}
    dec = max(1, s["decisions"])
    s["fallback_rate"] = s.get("fallbacks", 0) / dec
    return s


# ── legal fallbacks (NEVER crash, ALWAYS respect minCount/range) ──────────────
def _legal_fallback(select):
    try:
        n = len(select.get("option") or [])
        lo = max(0, select.get("minCount", 0) or 0)
        if n == 0:
            return []
        if lo <= n:
            return list(range(lo))
        out = list(range(n))
        k = 0
        while len(out) < lo:
            out.append(k % n)
            k += 1
        return out
    except Exception:
        return []


def _legal_fallback_from_obs(obs):
    try:
        sel = (obs or {}).get("select") or {}
        return _legal_fallback(sel)
    except Exception:
        return []


# ── normalize_selection: dedup, respect minCount/maxCount/range, fill legally ──
def normalize_selection(ranked_indices, select):
    n = len(select.get("option") or [])
    if n == 0:
        return []
    min_c = max(0, select.get("minCount", 0) or 0)
    max_c = max(min_c, select.get("maxCount", 0) or 0)

    out = []
    seen = set()
    for i in ranked_indices:
        if isinstance(i, int) and 0 <= i < n and i not in seen:
            out.append(i)
            seen.add(i)
            if len(out) >= max_c:
                break
    if len(out) < min_c:
        for i in range(n):
            if i not in seen:
                out.append(i)
                seen.add(i)
                if len(out) >= min_c:
                    break
    if len(out) < min_c:
        pool = [i for i in ranked_indices if isinstance(i, int) and 0 <= i < n] or list(range(n))
        k = 0
        while len(out) < min_c:
            out.append(pool[k % len(pool)])
            k += 1
    return out[:max_c]


# ── defensive board accessors ──────────────────────────────────────────────────
def _players(obs):
    try:
        return obs["current"]["players"]
    except Exception:
        return None


def get_card(obs, area, index, pi, select=None):
    try:
        players = _players(obs)
        cur = obs.get("current") or {}
        if area in (AREA_ACTIVE, "ACTIVE"):
            lst = players[pi].get("active") or []
            return lst[index] if 0 <= index < len(lst) else None
        if area in (AREA_BENCH, "BENCH"):
            lst = players[pi].get("bench") or []
            return lst[index] if 0 <= index < len(lst) else None
        if area in ("hand", "HAND"):
            lst = players[pi].get("hand") or []
            return lst[index] if 0 <= index < len(lst) else None
        if area in ("discard", "DISCARD"):
            lst = players[pi].get("discard") or []
            return lst[index] if 0 <= index < len(lst) else None
        if area in ("prize", "PRIZE"):
            lst = players[pi].get("prize") or []
            return lst[index] if 0 <= index < len(lst) else None
        if area in ("stadium", "STADIUM"):
            lst = cur.get("stadium") or []
            return lst[index] if 0 <= index < len(lst) else None
        if area in ("looking", "LOOKING"):
            lst = cur.get("looking") or []
            return lst[index] if 0 <= index < len(lst) else None
        if area in ("deck", "DECK") and select is not None:
            lst = select.get("deck") or []
            return lst[index] if 0 <= index < len(lst) else None
    except Exception:
        pass
    return None


def get_inplay_card(obs, area_code, index, pi):
    """Resolve an in-play (active/bench) pokemon dict from an option's inPlayArea/
    inPlayIndex. `area_code` may be an INT (4=active, 5=bench) or a string."""
    try:
        players = _players(obs)
        if not players:
            return None
        if area_code in INPLAY_ACTIVE_CODES:
            lst = players[pi].get("active") or []
        elif area_code in INPLAY_BENCH_CODES:
            lst = players[pi].get("bench") or []
        else:
            return None
        return lst[index] if 0 <= index < len(lst) else None
    except Exception:
        return None


def _opt_int(opt, key, default=None):
    try:
        v = opt.get(key, default)
        return v if isinstance(v, int) else default
    except Exception:
        return default


def _pokemon_value(card):
    if not isinstance(card, dict):
        return (-1, -1, -1)
    hp = card.get("hp") or 0
    energies = card.get("energies") or []
    max_hp = card.get("maxHp") or 0
    return (hp, len(energies), max_hp)


# ── CARD-KNOWLEDGE helpers (static table joined with live obs) ─────────────────
def _card_id(pokemon):
    """Pull a card id out of a live pokemon dict, trying common keys."""
    if not isinstance(pokemon, dict):
        return None
    for k in ("id", "cardId", "card_id", "cardID"):
        v = pokemon.get(k)
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.isdigit():
            return int(v)
    return None


def _card_info(pokemon):
    """Static cards.json entry for a live pokemon dict (or None)."""
    cid = _card_id(pokemon)
    if cid is None:
        return None
    return CARDS.get(str(cid))


def _energy_count(pokemon):
    """How many energies are attached to a live pokemon."""
    if not isinstance(pokemon, dict):
        return 0
    e = pokemon.get("energies")
    if isinstance(e, list):
        return len(e)
    if isinstance(e, int):
        return e
    return 0


def _live_hp(pokemon):
    """Current remaining HP of a live pokemon (best-effort)."""
    if not isinstance(pokemon, dict):
        return None
    hp = pokemon.get("hp")
    if isinstance(hp, int):
        return hp
    # some encodings give maxHp + damage taken
    mx = pokemon.get("maxHp")
    dmg = pokemon.get("damage")
    if isinstance(mx, int):
        return mx - dmg if isinstance(dmg, int) else mx
    return None


def _best_affordable_attack(info, energy_have):
    """Among a card's attacks, the highest-damage one whose energy_count <= energy_have.
    Returns (damage, energy_count) or None."""
    if not info:
        return None
    attacks = info.get("attacks") or []
    best = None
    for a in attacks:
        try:
            ec = a.get("energy_count", 0) or 0
            dm = a.get("damage", 0) or 0
        except Exception:
            continue
        if ec <= energy_have:
            if best is None or dm > best[0]:
                best = (dm, ec)
    return best


def _best_attack_overall(info):
    """The highest-damage attack ignoring energy. Returns (damage, energy_count) or None."""
    if not info:
        return None
    attacks = info.get("attacks") or []
    best = None
    for a in attacks:
        try:
            ec = a.get("energy_count", 0) or 0
            dm = a.get("damage", 0) or 0
        except Exception:
            continue
        if best is None or dm > best[0]:
            best = (dm, ec)
    return best


def _weakness_match(my_type, opp_weakness):
    """True if our active's type matches the opponent active's weakness (x2 damage)."""
    if not my_type or not opp_weakness:
        return False
    try:
        return str(my_type).strip() == str(opp_weakness).strip()
    except Exception:
        return False


def _prizes_left(obs, pi):
    """Best-effort prize count remaining for player pi (fewer = closer to winning)."""
    try:
        players = _players(obs)
        p = players[pi]
        prize = p.get("prize")
        if isinstance(prize, list):
            return len(prize)
        if isinstance(prize, int):
            return prize
        # alternative field
        pr = p.get("prizesRemaining")
        if isinstance(pr, int):
            return pr
    except Exception:
        pass
    return None


# ── per-context heuristics; each returns ranked option indices (best first) ───
def _rank_main(obs, select):
    options = select.get("option") or []
    cur = obs.get("current") or {}
    me = cur.get("yourIndex", 0)
    players = _players(obs)

    # live actives
    my_active = None
    opp_active = None
    try:
        if players:
            ma = players[me].get("active") or []
            my_active = ma[0] if ma else None
            oa = players[1 - me].get("active") or []
            opp_active = oa[0] if oa else None
    except Exception:
        pass

    my_info = _card_info(my_active)
    opp_info = _card_info(opp_active)
    my_type = my_info.get("type") if my_info else None
    opp_hp = _live_hp(opp_active)
    opp_weak = opp_info.get("weakness") if opp_info else None
    my_prizes = _prizes_left(obs, me)

    # Can our active attack RIGHT NOW (an affordable attack that deals damage)?
    e_active = _energy_count(my_active)
    affordable = _best_affordable_attack(my_info, e_active) if my_info else None
    can_attack_now = bool(affordable and affordable[0] > 0)
    # Best attack the active could EVER reach (to know if attaching unlocks more damage).
    best_overall = _best_attack_overall(my_info) if my_info else None
    # Attaching to the ACTIVE is worth doing FIRST only if it moves us toward a
    # strictly bigger attack than what we can already afford (otherwise attack now).
    aff_dmg = affordable[0] if affordable else 0
    overall_dmg = best_overall[0] if best_overall else 0
    attach_active_helps = bool(best_overall and overall_dmg > aff_dmg and e_active < best_overall[1])

    def _is_ko_attack(opt):
        """True if this ATTACK option's estimated effective damage KOs the opp active."""
        if _opt_int(opt, "type", -1) != OPT_ATTACK:
            return False
        if not (isinstance(opp_hp, int) and opp_hp > 0):
            return False
        dmg = None
        for k in ("damage", "baseDamage", "atkDamage"):
            v = _opt_int(opt, k, None)
            if isinstance(v, int):
                dmg = v
                break
        if dmg is None:
            dmg = aff_dmg if affordable else (overall_dmg if best_overall else 0)
        eff = (dmg or 0) * 2 if _weakness_match(my_type, opp_weak) else (dmg or 0)
        return eff >= opp_hp

    # ── HYBRID: trust the engine's best-first option order, override only for the
    # high-value cases. The blind first-legal baseline (always option[0]) is strong,
    # which suggests the engine already lists `option` roughly best-first. So we keep
    # that order and just (1) pull a KO/winning attack to the very front, and
    # (2) drop voluntary RETREAT to the very back.
    if TRUST_ENGINE_ORDER:
        ko_idx = []
        retreat_idx = []
        rest = []
        for i, opt in enumerate(options):
            t = _opt_int(opt, "type", -1)
            if _is_ko_attack(opt):
                _DIAG["attacks_scored"] += 1
                _DIAG["ko_attacks"] += 1
                ko_idx.append(i)
            elif t == OPT_RETREAT:
                retreat_idx.append(i)
            else:
                rest.append(i)
        # If a KO also takes our last prize, it wins -> it's already first anyway.
        return ko_idx + rest + retreat_idx

    def attack_score(opt):
        """Score an ATTACK option. Card knowledge is layered ON TOP of the proven
        setup-first ordering: a normal attack stays at the base ATTACK priority
        (below setup, like the 35%-vs-firstlegal agent), but the BETTER attack
        (more damage, weakness x2) is preferred, and a KO/winning attack jumps to
        the very top so we never miss a kill."""
        _DIAG["attacks_scored"] += 1
        dmg = None
        for k in ("damage", "baseDamage", "atkDamage"):
            v = _opt_int(opt, k, None)
            if isinstance(v, int):
                dmg = v
                break
        if dmg is None:
            # option doesn't expose damage -> estimate from our active's best
            # affordable attack in the static table (per task spec).
            dmg = aff_dmg if affordable else (overall_dmg if best_overall else 0)
        if dmg is None:
            dmg = 0
        eff = dmg * 2 if _weakness_match(my_type, opp_weak) else dmg
        # Base stays in the setup-first band: ATTACK base + small damage tilt so we
        # keep finishing setup first (that balance scored 35% vs firstlegal) while
        # still picking the strongest attack among several.
        score = MAIN_PRIORITY[OPT_ATTACK] + min(eff, 300) * 0.05
        if isinstance(opp_hp, int) and opp_hp > 0 and eff >= opp_hp:
            _DIAG["ko_attacks"] += 1
            score += 1000  # a KO is worth interrupting setup for
            if my_prizes == 1:
                score += 100000  # this KO takes our last prize -> we WIN
        return score

    def opt_score(idx, opt):
        t = _opt_int(opt, "type", -1)

        if t == OPT_ATTACK:
            return attack_score(opt)

        if t == OPT_EVOLVE:
            return MAIN_PRIORITY[OPT_EVOLVE]
        if t == OPT_ABILITY:
            return MAIN_PRIORITY[OPT_ABILITY]

        # ATTACH: charge the attacker that still can't pay its best attack; with the
        # static table, prefer the active when attaching unlocks a bigger attack, and
        # stop charging a mon that can already pay its best attack (no over-fill).
        if t == OPT_ATTACH:
            ipa = opt.get("inPlayArea")
            target = get_inplay_card(obs, ipa, _opt_int(opt, "inPlayIndex", -1), me)
            on_active = ipa in INPLAY_ACTIVE_CODES
            base = MAIN_PRIORITY[OPT_ATTACH]
            if isinstance(target, dict):
                t_info = _card_info(target)
                e_have = _energy_count(target)
                if t_info is not None:
                    best = _best_attack_overall(t_info)
                    if best is not None:
                        need = best[1]
                        if e_have >= need:
                            base = 30  # already pays its best attack -> don't over-fill
                        else:
                            base = MAIN_PRIORITY[OPT_ATTACH] + max(0, 6 - (need - e_have))
                    else:
                        base += max(0, 6 - e_have)
                else:
                    base += max(0, 6 - e_have)
                if on_active:
                    base += 2  # the active attacks this turn -> charge it first
            return base

        if t == OPT_PLAY:
            return MAIN_PRIORITY[OPT_PLAY]

        # RETREAT: voluntarily retreating in MAIN burns the attached energy and a turn
        # of tempo. An A/B over 40 games showed restoring retreat HURT (~18% vs ~35%
        # without it), so we keep it BELOW END -> only ever taken when it's the sole
        # legal option.
        if t == OPT_RETREAT:
            return 0

        if t == OPT_END:
            return MAIN_PRIORITY[OPT_END]

        return MAIN_PRIORITY.get(t, 5)

    ranked = sorted(range(len(options)), key=lambda i: opt_score(i, options[i]), reverse=True)
    return ranked


def _rank_friendly_pokemon(obs, select, prefer_friendly=True):
    """SETUP_ACTIVE / SETUP_BENCH / SWITCH / TO_ACTIVE / TO_BENCH: best friendly mon.
    With card knowledge, prefer the pokemon with the highest best-attack damage,
    then live hp."""
    options = select.get("option") or []
    me = obs["current"]["yourIndex"]
    scored = []
    for i, opt in enumerate(options):
        t = _opt_int(opt, "type", -1)
        if t != OPT_CARD:
            scored.append((i, (-2, -2, -2), 0))
            continue
        pi = _opt_int(opt, "playerIndex", me)
        card = get_card(obs, opt.get("area"), _opt_int(opt, "index", -1), pi, select)
        own = 1 if (pi == me) else 0
        info = _card_info(card)
        best = _best_attack_overall(info) if info else None
        atk_dmg = best[0] if best else 0
        hp = (card.get("hp") if isinstance(card, dict) else 0) or 0
        scored.append((i, (atk_dmg, hp), own if prefer_friendly else 0))
    scored.sort(key=lambda x: (x[2], x[1]), reverse=True)
    return [s[0] for s in scored]


def _rank_discard(obs, select):
    options = select.get("option") or []
    me = obs["current"]["yourIndex"]
    players = _players(obs)
    hand = (players[me].get("hand") or []) if players else []
    counts = {}
    for c in hand:
        if isinstance(c, dict):
            cid = c.get("id")
            counts[cid] = counts.get(cid, 0) + 1

    def score(opt):
        if _opt_int(opt, "type", -1) != OPT_CARD:
            return -1
        pi = _opt_int(opt, "playerIndex", me)
        card = get_card(obs, opt.get("area"), _opt_int(opt, "index", -1), pi, select)
        cid = card.get("id") if isinstance(card, dict) else None
        dup = counts.get(cid, 1)
        return dup

    return sorted(range(len(options)), key=lambda i: score(options[i]), reverse=True)


def _rank_damage_counter(obs, select):
    """DAMAGE_COUNTER: put damage on the OPPONENT's pokemon. With card knowledge,
    prefer the one we can KO (lowest live hp among opponents) so a counter finishes it."""
    options = select.get("option") or []
    me = obs["current"]["yourIndex"]

    def score(opt):
        if _opt_int(opt, "type", -1) != OPT_CARD:
            return (-1, 0)
        pi = _opt_int(opt, "playerIndex", me)
        on_opp = 1 if pi != me else 0
        card = get_card(obs, opt.get("area"), _opt_int(opt, "index", -1), pi, select)
        hp = _live_hp(card)
        hp = hp if isinstance(hp, int) else (card.get("hp") if isinstance(card, dict) else 0) or 0
        # opponent first; among opponents, prefer LOWER hp (closer to KO).
        return (on_opp, -(hp or 0))

    return sorted(range(len(options)), key=lambda i: score(options[i]), reverse=True)


def _rank_yes_no(select, want_yes=True):
    options = select.get("option") or []
    yes_idx, no_idx, other = [], [], []
    for i, opt in enumerate(options):
        t = _opt_int(opt, "type", -1)
        if t == OPT_YES:
            yes_idx.append(i)
        elif t == OPT_NO:
            no_idx.append(i)
        else:
            other.append(i)
    if want_yes:
        return yes_idx + other + no_idx
    return no_idx + other + yes_idx


def _rank_is_first(select):
    options = select.get("option") or []
    yes_idx, no_idx, other = [], [], []
    for i, opt in enumerate(options):
        t = _opt_int(opt, "type", -1)
        if t == OPT_YES:
            yes_idx.append(i)
        elif t == OPT_NO:
            no_idx.append(i)
        else:
            other.append(i)
    if GO_FIRST:
        return yes_idx + other + no_idx
    return no_idx + other + yes_idx


def _force_end(select):
    options = select.get("option") or []
    for i, opt in enumerate(options):
        if _opt_int(opt, "type", -1) == OPT_END:
            return i
    return None


# ── core heuristic dispatcher ─────────────────────────────────────────────────
def _policy(obs):
    select = obs.get("select")
    if select is None:
        _DIAG["deck_returns"] += 1
        return my_deck

    options = select.get("option") or []
    if not options:
        return _legal_fallback(select)

    context = select.get("context")
    cur = obs.get("current") or {}

    if context == CTX_MAIN:
        tac = cur.get("turnActionCount")
        if isinstance(tac, int) and tac > MAX_ACTIONS_GUARD:
            end_i = _force_end(select)
            if end_i is not None:
                return normalize_selection([end_i], select)

    rot = obs.get("remainingOverageTime")
    if isinstance(rot, (int, float)) and rot < LOW_TIME_GUARD:
        return _legal_fallback(select)

    if context == CTX_IS_FIRST:
        return normalize_selection(_rank_is_first(select), select)

    if context == CTX_MAIN:
        return normalize_selection(_rank_main(obs, select), select)

    if context in (CTX_SETUP_ACTIVE, CTX_SETUP_BENCH, CTX_SWITCH,
                   CTX_TO_ACTIVE, CTX_TO_BENCH):
        return normalize_selection(_rank_friendly_pokemon(obs, select), select)

    if context == CTX_DISCARD:
        return normalize_selection(_rank_discard(obs, select), select)

    if context in (CTX_DAMAGE_COUNTER_A, CTX_DAMAGE_COUNTER_B):
        return normalize_selection(_rank_damage_counter(obs, select), select)

    has_yes = any(_opt_int(o, "type", -1) == OPT_YES for o in options)
    has_no = any(_opt_int(o, "type", -1) == OPT_NO for o in options)
    if has_yes or has_no:
        return normalize_selection(_rank_yes_no(select, want_yes=True), select)

    return normalize_selection(list(range(len(options))), select)


# ── public entry point: NEVER crash, ALWAYS return a legal selection ──────────
def agent(obs, config=None):
    try:
        if isinstance(obs, dict) and obs.get("select") is None:
            _DIAG["deck_returns"] += 1
            return my_deck
    except Exception:
        pass

    _DIAG["decisions"] += 1
    try:
        out = _policy(obs)
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            _DIAG["policy_ok"] += 1
            return my_deck
        n = len(sel.get("option") or [])
        min_c = max(0, sel.get("minCount", 0) or 0)
        max_c = max(min_c, sel.get("maxCount", 0) or 0)
        uniq_ok = (len(set(out)) == len(out)) if isinstance(out, list) else False
        if min_c > n:
            uniq_ok = True
        valid = (
            isinstance(out, list)
            and min_c <= len(out) <= max_c
            and all(isinstance(i, int) and 0 <= i < n for i in out)
            and uniq_ok
        )
        if valid:
            _DIAG["policy_ok"] += 1
            return out
        fixed = normalize_selection(out if isinstance(out, list) else [], sel)
        if min_c <= len(fixed) <= max_c:
            _DIAG["policy_ok"] += 1
            return fixed
        _DIAG["fallbacks"] += 1
        return _legal_fallback(sel)
    except Exception as exc:
        _record_error(exc)
        _DIAG["fallbacks"] += 1
        try:
            if isinstance(obs, dict) and obs.get("select") is None:
                return my_deck
            return _legal_fallback_from_obs(obs)
        except Exception as exc2:
            _record_error(exc2)
            return []
