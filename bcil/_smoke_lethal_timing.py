"""Smoke + timing harness for sabrina_lethal verification.

Wraps the agent callable to record PER-DECISION wall time, runs N games vs a
baseline (alternating seat), reports:
  - zero_crash / sin_timeout (no exception, no per-decision blowup)
  - tiempo_max_decision (seconds, the riesgo #1 metric)
  - A_diag (fallback_rate, errors, deck_ok, lethal_* counters -> search_disparo)

Usage: python bcil/_smoke_lethal_timing.py <dirA> <dirB> <games> [seed_base]
Run with FMA_LETHAL_ON=1 to EXERCISE the lethal search (gate/fallback path).
"""
import os, sys, json, time, warnings
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "experiments"))
os.chdir(ROOT)
from ab_harness import load_cb, verify_deck_phase
from kaggle_environments import make

dirA, dirB = sys.argv[1], sys.argv[2]
games = int(sys.argv[3]) if len(sys.argv) > 3 else 15
seed_base = int(sys.argv[4]) if len(sys.argv) > 4 else 0

cbA = load_cb(dirA); cbB = load_cb(dirB)
verify_deck_phase(cbA, dirA); verify_deck_phase(cbB, dirB)

# ---- timing + crash wrapper around A's callable ----
TIMING = {"max_s": 0.0, "n": 0, "sum_s": 0.0, "crashes": 0, "over_3s": 0,
          "over_60s": 0, "slow_samples": []}

def make_timed(cb):
    def timed(obs_dict, config=None):
        # skip deck phase (returns list, not a decision)
        is_decision = not (isinstance(obs_dict, dict) and obs_dict.get("select") is None)
        t0 = time.monotonic()
        try:
            out = cb(obs_dict, config)
        except Exception as e:
            TIMING["crashes"] += 1
            print(f"  !! CRASH in A callable: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
            raise
        dt = time.monotonic() - t0
        if is_decision:
            TIMING["n"] += 1
            TIMING["sum_s"] += dt
            if dt > TIMING["max_s"]:
                TIMING["max_s"] = dt
            if dt > 3.0:
                TIMING["over_3s"] += 1
                if len(TIMING["slow_samples"]) < 10:
                    TIMING["slow_samples"].append(round(dt, 3))
            if dt > 60.0:
                TIMING["over_60s"] += 1
        return out
    # preserve __globals__ so diag_snapshot is reachable
    timed.__globals__.update(cb.__globals__) if hasattr(timed, "__globals__") else None
    return timed, cb

timedA, rawA = make_timed(cbA)

w = [0, 0, 0]
game_crash = False
for g in range(games):
    env = make("cabt", configuration={"seed": seed_base + g})
    a_seat = 0 if g % 2 == 0 else 1
    order = [timedA, cbB] if a_seat == 0 else [cbB, timedA]
    try:
        res = env.run(order)
    except Exception as e:
        game_crash = True
        print(f"  !! env.run raised game {g}: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        continue
    r = [s.get("reward") for s in res[-1]]
    ra, rb = r[a_seat], r[1 - a_seat]
    if ra is None and rb is None: oc = 2
    elif ra is None: oc = 1
    elif rb is None: oc = 0
    elif ra > rb: oc = 0
    elif rb > ra: oc = 1
    else: oc = 2
    w[oc] += 1
    print(f"  game {g+1}/{games}: [{w[0]}W/{w[1]}L/{w[2]}D] max_dec={TIMING['max_s']:.3f}s",
          file=sys.stderr, flush=True)

diag_fn = rawA.__globals__.get("diag_snapshot")
d = diag_fn() if diag_fn else {}

zero_crash = (TIMING["crashes"] == 0) and (not game_crash) and (d.get("errors") == {} or not d.get("errors"))
sin_timeout = TIMING["over_60s"] == 0  # 60s = clearly safe under the 600s overage pool

print("JSON_RESULT " + json.dumps({
    "A": dirA, "B": dirB, "games": games, "seed_base": seed_base,
    "A_wins": w[0], "B_wins": w[1], "draws": w[2],
    "zero_crash": zero_crash,
    "sin_timeout": sin_timeout,
    "tiempo_max_decision_s": round(TIMING["max_s"], 4),
    "decisions_timed": TIMING["n"],
    "avg_decision_s": round(TIMING["sum_s"] / max(1, TIMING["n"]), 5),
    "decisions_over_3s": TIMING["over_3s"],
    "decisions_over_60s": TIMING["over_60s"],
    "slow_samples_s": TIMING["slow_samples"],
    "callable_crashes": TIMING["crashes"],
    "game_crash": game_crash,
    "A_diag": d,
}))
