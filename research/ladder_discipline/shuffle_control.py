#!/usr/bin/env python3
"""
shuffle_control.py — the SHUFFLED-NUDGE control for KB levers (LOCAL diagnostic).

WHAT IT IS (and the honesty caveat up front)
--------------------------------------------
A KB lever (e.g. KB_DRAW_GUARD in sabrina_kb_draw) works by adding a same-sign,
bounded NUDGE to the score of the OPTIONS that advance its hypothesised plan (the
"map-advancing" options — e.g. the draw decisions a prize-belief model favours). The
question the shuffle control answers is purely mechanical:

    Is the lever's EDGE coming from WHICH options it nudges, or just from the FACT
    that it perturbs scores at all?

The control builds a lever variant that applies the SAME-MAGNITUDE nudge to RANDOMLY
chosen legal options instead of the map-advancing ones. Then you run the three arms on
the SAME paired seeds:

    flag-OFF   (baseline, no nudge)
    lever-ON   (nudge on the map-advancing options — the real lever)
    shuffle    (nudge on random legal options — same magnitude, wrong target)

Reading:
  - If  lever-ON  ~=  shuffle  ~=  flag-OFF  -> the lever's LOGIC is INERT: any
    apparent movement is pure variance from perturbing scores, not from the
    hypothesised mechanism. Drop it.
  - If  lever-ON  >  shuffle  AND  lever-ON  >  flag-OFF  -> the TARGETING matters:
    the mechanism does something the random nudge does not. Worth laddering.

CRITICAL HONESTY (HARD RULE)
----------------------------
cabt local A/B is ANTI-PREDICTIVE of the ladder (Spearman -0.80, RESULTS-N200). So this
shuffle control is a **LOCAL DIAGNOSTIC of lever inertness ONLY** — it tells you whether
the lever's code does anything distinguishable from a random perturbation in the local
sim. It is **NEVER a ladder verdict**. A lever that beats its shuffle locally may still
lose on the ladder, and a lever that ties its shuffle locally is not proven dead on the
ladder. The only ladder judge is `deflated_elo` on converged Elo gaps. Use this control
to PRUNE obviously-inert levers before spending a scarce ladder slot, nothing more.

DESIGN / SPEC (how to wire it into an agent)
--------------------------------------------
The lever in `agents_official/sabrina_kb_draw/main.py` is gated by KB_DRAW_GUARD and
adds its nudge inside the score path (around the `_score` / draw-guard logic). To build
the shuffle arm without touching the lever's intent:

  1. Add a third mode alongside {OFF, ON}. Suggested env flag: KB_NUDGE_MODE in
     {"off", "on", "shuffle"} (default "on" preserves current behaviour; "off" is the
     existing flag=False byte-equivalent baseline).
  2. Factor the lever into two pieces it already implicitly has:
       (a) target_mask(options) -> the set of option indices the lever WANTS to nudge
           (the map-advancing ones);
       (b) nudge_magnitude       -> the bounded delta it adds to those scores.
  3. mode == "shuffle": keep nudge_magnitude IDENTICAL, but replace target_mask with
     `shuffled_target_mask(options, k, rng)` — k randomly chosen LEGAL option indices,
     where k == len(target_mask(options)) so the NUMBER of nudged options matches. Only
     the WHICH changes; the HOW MUCH and HOW MANY are held fixed. This isolates targeting.
  4. The RNG MUST be seeded deterministically per decision from the SAME paired seed the
     A/B harness uses, so flag-OFF / lever-ON / shuffle see identical game states. Use a
     per-decision seed derived from (game_seed, turn, decision_index) — never a global
     random.Random() (that would desync the paired comparison).

This module ships the seed-stable shuffle helper so the agent can import it offline; it
does NOT modify any agent (no Docker, no engine here).

RUN COMMAND (described, NOT executed — Docker is offline by rule)
-----------------------------------------------------------------
The A/B harness is the existing paired-seed cabt runner used for RESULTS-N200. Conceptually,
for N>=200 paired seeds (N<60 is a mirage — see RESULTS-N200 "espejismo de seeds"):

    # flag-OFF baseline arm
    KB_NUDGE_MODE=off    <existing paired cabt A/B command> --n 200 --seed-base S

    # lever-ON arm (the real lever)
    KB_NUDGE_MODE=on     <existing paired cabt A/B command> --n 200 --seed-base S

    # shuffle arm (same magnitude, random legal targets)
    KB_NUDGE_MODE=shuffle <existing paired cabt A/B command> --n 200 --seed-base S

Then compare the three win-rates with Wilson 95% CIs (same protocol as RESULTS-N200):
inert lever => all three CIs overlap each other; targeting matters => ON's CI sits above
both OFF and shuffle. Again: LOCAL inertness diagnostic, not a ladder GO.
"""
from __future__ import annotations

import hashlib


def decision_seed(game_seed: int, turn: int, decision_index: int) -> int:
    """Deterministic per-decision seed from the paired-seed coordinates.

    MUST be used (not a global RNG) so the OFF / ON / shuffle arms stay in lockstep on
    the same paired game states. Stable across processes (sha256, not Python hash()).
    """
    raw = f"{int(game_seed)}|{int(turn)}|{int(decision_index)}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def shuffled_target_mask(n_options: int, k: int, seed: int) -> list[int]:
    """k distinct random LEGAL option indices out of n_options, deterministic in `seed`.

    Mirrors the lever's targeting CARDINALITY (k == number of options the real lever
    nudges) but randomises WHICH options get the (identical-magnitude) nudge. Pure
    python (no numpy dependency at agent runtime). Fail-safe: clamps k to [0, n_options].

    Implementation: a seeded Fisher-Yates partial shuffle over range(n_options). No
    `random` module global state is touched — a local LCG seeded from `seed` keeps the
    paired A/B in lockstep regardless of interpreter-wide RNG use elsewhere.
    """
    n = max(0, int(n_options))
    kk = max(0, min(int(k), n))
    if n == 0 or kk == 0:
        return []
    idx = list(range(n))
    # Local LCG (Numerical Recipes constants) — no dependence on global random state.
    state = (int(seed) ^ 0x9E3779B97F4A7C15) & ((1 << 64) - 1)

    def _next(bound: int) -> int:
        nonlocal state
        state = (6364136223846793005 * state + 1442695040888963407) & ((1 << 64) - 1)
        return (state >> 11) % bound

    # Partial Fisher-Yates: first kk positions become the random sample.
    for i in range(kk):
        j = i + _next(n - i)
        idx[i], idx[j] = idx[j], idx[i]
    return sorted(idx[:kk])


def is_inert_locally(
    wr_off: float, wr_on: float, wr_shuffle: float, *, tol: float = 0.02
) -> bool:
    """Quick LOCAL heuristic: the lever looks inert if ON is not meaningfully above BOTH
    OFF and shuffle (within `tol` win-rate). LOCAL DIAGNOSTIC ONLY — never a ladder
    verdict (cabt is anti-predictive). The real read uses Wilson 95% CIs per the
    RESULTS-N200 protocol; this is a fast triage flag, not the test.
    """
    above_off = (wr_on - wr_off) > tol
    above_shuffle = (wr_on - wr_shuffle) > tol
    return not (above_off and above_shuffle)


if __name__ == "__main__":  # pragma: no cover — illustrative, no engine/Docker
    s = decision_seed(game_seed=42, turn=3, decision_index=1)
    print("decision_seed(42,3,1) =", s)
    print("shuffled_target_mask(n=6, k=2) =", shuffled_target_mask(6, 2, s))
    print("inert? (off=.50 on=.51 shuf=.505) =",
          is_inert_locally(0.50, 0.51, 0.505))
    print("targeting matters? (off=.50 on=.58 shuf=.51) =",
          not is_inert_locally(0.50, 0.58, 0.51))
