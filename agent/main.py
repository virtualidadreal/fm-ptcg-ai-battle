"""
Pokémon TCG AI Battle (Kaggle cabt env) — robust dict-only agent.

Runtime contract (verified empirically in docker, 22 jun 2026):
  - The motor lives in the pip package `kaggle_environments` (env "cabt"). It runs
    OFFLINE with NO Kaggle identity, so `cg.api` / `all_card_data` /
    `to_observation_class` (the cg-lib symbols the official sample uses) are NOT
    importable here. This agent works SOLELY off the raw `obs` dict.
  - agent(obs, config=None) -> list[int].
      * obs["select"] is None  -> deck-selection phase: return the 60 card_ids.
      * otherwise               -> return between select["minCount"] and
                                    select["maxCount"] INDICES into select["option"].
  - The motor only offers LEGAL plays in `option`, but returning the wrong COUNT or
    an out-of-range index makes `battle_select` raise -> INVALID -> reward -1
    (instant loss). So we validate len + range on EVERY return and never crash
    (global try/except + always-legal fallback).

Heuristic (dict-only, by SelectContext + OptionType): finish all setup
(evolve > ability > attach > play) and attack only when no setup remains, plus
sane sub-select tie-breaks (best pokemon, discard duplicates, spread damage on the
opponent). This is strictly better than blind first-legal while staying crash-proof.
"""

from __future__ import annotations

import os
import sys

# ── configuration ───────────────────────────────────────────────────────────
GO_FIRST = True          # context IS_FIRST: pick YES (go first) per task spec.
MAX_ACTIONS_GUARD = 50   # MAIN watchdog: above this turnActionCount, force END.
LOW_TIME_GUARD = 30.0    # seconds: below this remainingOverageTime, play fast.

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

# Area names (used by option dicts as area / inPlayArea, observed as strings).
AREA_ACTIVE = "active"
AREA_BENCH = "bench"

# MAIN priorities: do all setup first, attack last (attack ends the turn).
MAIN_PRIORITY = {
    OPT_EVOLVE: 100,
    OPT_ABILITY: 95,
    OPT_ATTACH: 90,
    OPT_PLAY: 80,
    OPT_ATTACK: 60,
    OPT_RETREAT: 20,
    OPT_END: 1,
}

# ── robust deck loader (cwd-independent, load once at module level) ───────────
def _resolve_deck_path():
    cands = []
    if "__file__" in globals():
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deck.csv"))
    cands.append("deck.csv")
    cands.append("/kaggle_simulations/agent/deck.csv")
    for p in sys.path:
        if p:
            cands.append(os.path.join(p, "deck.csv"))
    for p in cands:
        try:
            if os.path.exists(p):
                return p
        except Exception:
            continue
    return None


def _load_deck():
    path = _resolve_deck_path()
    if not path:
        return []
    try:
        with open(path, "r") as f:
            ids = [int(x) for x in f.read().splitlines() if x.strip()]
        return ids[:60]
    except Exception:
        return []


# my_deck is always *available*; if it isn't a clean 60 we still never crash.
my_deck = _load_deck()

# ── diagnostics ───────────────────────────────────────────────────────────────
_DIAG = {
    "decisions": 0,     # non-deck selection turns
    "policy_ok": 0,     # heuristic produced the answer
    "fallbacks": 0,     # had to fall back to legal default
    "deck_returns": 0,  # deck-selection returns
    "errors": {},       # exception-type -> count
}


def _record_error(exc):
    k = type(exc).__name__ + ": " + str(exc)[:160]
    _DIAG["errors"][k] = _DIAG["errors"].get(k, 0) + 1


def diag_reset():
    _DIAG.update({"decisions": 0, "policy_ok": 0, "fallbacks": 0,
                  "deck_returns": 0, "errors": {}})


def diag_snapshot():
    s = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DIAG.items()}
    dec = max(1, s["decisions"])
    s["fallback_rate"] = s.get("fallbacks", 0) / dec
    return s


# ── legal fallbacks (NEVER crash, ALWAYS respect minCount/range) ──────────────
def _legal_fallback(select):
    """Smallest legal selection: the first minCount indices (>=0). If the engine ever
    asks for more picks than there are distinct options (minCount > n), repetition is
    mandatory, so we repeat indices to reach minCount (never return a short list)."""
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
    """
    ranked_indices: option indices in *preference order* (best first).
    Returns a valid selection: deduped, in [0, n), >= minCount, <= maxCount,
    padded with the next legal indices if we're short of minCount.
    """
    n = len(select.get("option") or [])
    if n == 0:
        return []
    min_c = max(0, select.get("minCount", 0) or 0)
    max_c = max(min_c, select.get("maxCount", 0) or 0)
    # NOTE: do NOT clamp min_c to n. If the engine asks for more picks than distinct
    # options (minCount > n), repetition is mandatory and clamping would return a
    # short, INVALID selection. (Never observed in ~6.8k decisions, but cheap to guard.)

    out = []
    seen = set()
    for i in ranked_indices:
        if isinstance(i, int) and 0 <= i < n and i not in seen:
            out.append(i)
            seen.add(i)
            if len(out) >= max_c:
                break
    # pad up to minCount with the lowest unused legal indices
    if len(out) < min_c:
        for i in range(n):
            if i not in seen:
                out.append(i)
                seen.add(i)
                if len(out) >= min_c:
                    break
    # still short => repetition is required: repeat best-ranked legal indices.
    if len(out) < min_c:
        pool = [i for i in ranked_indices if isinstance(i, int) and 0 <= i < n] or list(range(n))
        k = 0
        while len(out) < min_c:
            out.append(pool[k % len(pool)])
            k += 1
    # clamp to maxCount (>= min_c, so a forced-repetition selection survives)
    return out[:max_c]


# ── defensive board accessor ──────────────────────────────────────────────────
def _players(obs):
    try:
        return obs["current"]["players"]
    except Exception:
        return None


def get_card(obs, area, index, pi, select=None):
    """
    Map (area, index, playerIndex) -> the card/pokemon dict, defensively.
    Returns None on any miss. `area` may be a string or absent.
    """
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


def _opt_int(opt, key, default=None):
    try:
        v = opt.get(key, default)
        return v if isinstance(v, int) else default
    except Exception:
        return default


def _pokemon_value(card):
    """Tie-break score for a friendly pokemon: hp, then energies, then maxHp."""
    if not isinstance(card, dict):
        return (-1, -1, -1)
    hp = card.get("hp") or 0
    energies = card.get("energies") or []
    max_hp = card.get("maxHp") or 0
    return (hp, len(energies), max_hp)


# ── per-context heuristics; each returns ranked option indices (best first) ───
def _rank_main(obs, select):
    options = select.get("option") or []
    me = obs["current"]["yourIndex"]

    def opt_score(idx, opt):
        t = _opt_int(opt, "type", -1)
        base = MAIN_PRIORITY.get(t, 5)
        # ATTACH tweak: prefer attaching to a pokemon that still can't attack
        # (fewer energies), with a small bonus if it's the active pokemon.
        if t == OPT_ATTACH:
            target = get_card(obs, opt.get("inPlayArea"), _opt_int(opt, "inPlayIndex", -1), me, select)
            if isinstance(target, dict):
                e = len(target.get("energies") or [])
                base += max(0, 6 - e)  # fewer energies => slightly higher
                if opt.get("inPlayArea") in (AREA_ACTIVE, "ACTIVE"):
                    base += 2
        return base

    ranked = sorted(range(len(options)), key=lambda i: opt_score(i, options[i]), reverse=True)
    return ranked


def _rank_friendly_pokemon(obs, select, prefer_friendly=True):
    """SETUP_ACTIVE / SETUP_BENCH / SWITCH / TO_ACTIVE / TO_BENCH: best friendly mon."""
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
        val = _pokemon_value(card)
        # prefer own pokemon when choosing our attacker/active
        scored.append((i, val, own if prefer_friendly else 0))
    scored.sort(key=lambda x: (x[2], x[1]), reverse=True)
    return [s[0] for s in scored]


def _rank_discard(obs, select):
    """DISCARD: discard duplicates (by id in our hand) first; keep singletons."""
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
        # higher count -> prefer discarding; singletons (1) score lowest
        return dup

    return sorted(range(len(options)), key=lambda i: score(options[i]), reverse=True)


def _rank_damage_counter(obs, select):
    """DAMAGE_COUNTER: spread onto the OPPONENT's pokemon, highest hp first."""
    options = select.get("option") or []
    me = obs["current"]["yourIndex"]

    def score(opt):
        if _opt_int(opt, "type", -1) != OPT_CARD:
            return -1
        pi = _opt_int(opt, "playerIndex", me)
        on_opp = 1 if pi != me else 0
        card = get_card(obs, opt.get("area"), _opt_int(opt, "index", -1), pi, select)
        hp = card.get("hp") if isinstance(card, dict) else 0
        # opponent first; among opponents, higher hp first
        return (on_opp, hp or 0)

    return sorted(range(len(options)), key=lambda i: score(options[i]), reverse=True)


def _rank_yes_no(select, want_yes=True):
    """Generic YES/NO outside IS_FIRST: prefer YES (beneficial) by default."""
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
    """IS_FIRST: pick YES if GO_FIRST else NO; YES typically = go first."""
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
    """Return the index of an END option if present, else None."""
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

    # Watchdog: if we've taken absurdly many actions this turn in MAIN, end it.
    if context == CTX_MAIN:
        tac = cur.get("turnActionCount")
        if isinstance(tac, int) and tac > MAX_ACTIONS_GUARD:
            end_i = _force_end(select)
            if end_i is not None:
                return normalize_selection([end_i], select)

    # Low-time guard: just play the smallest legal move, fast.
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

    # YES/NO-shaped selects (e.g. confirm an effect): default YES if available.
    has_yes = any(_opt_int(o, "type", -1) == OPT_YES for o in options)
    has_no = any(_opt_int(o, "type", -1) == OPT_NO for o in options)
    if has_yes or has_no:
        return normalize_selection(_rank_yes_no(select, want_yes=True), select)

    # Any other context / sub-select with no rule: robust first-legal.
    return normalize_selection(list(range(len(options))), select)


# ── public entry point: NEVER crash, ALWAYS return a legal selection ──────────
def agent(obs, config=None):
    # Deck-selection shortcut (also handled in _policy, but cheap + safe here).
    try:
        if isinstance(obs, dict) and obs.get("select") is None:
            _DIAG["deck_returns"] += 1
            return my_deck
    except Exception:
        pass

    _DIAG["decisions"] += 1
    try:
        out = _policy(obs)
        # final safety net: re-validate the heuristic's own output
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            _DIAG["policy_ok"] += 1
            return my_deck
        n = len(sel.get("option") or [])
        min_c = max(0, sel.get("minCount", 0) or 0)
        max_c = max(min_c, sel.get("maxCount", 0) or 0)
        # uniqueness is required normally, but when minCount > n the engine forces
        # repetition, so allow repeats only in that case.
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
        # heuristic produced something illegal -> normalize, then fallback
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
