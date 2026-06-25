"""Timed A/B: like ab_harness but reports per-game WALL time (slowest game)
to prove no game approaches the 600s overage limit. Also reports the slowest
single ISMCTS decision via the agent's diag."""
import os, sys, time, math, warnings, random
warnings.filterwarnings("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

A_DIR = sys.argv[1] if len(sys.argv) > 1 else "agent_ismcts"
B_DIR = sys.argv[2] if len(sys.argv) > 2 else "agents_official/dragapult_sample"
GAMES = int(sys.argv[3]) if len(sys.argv) > 3 else 15

from kaggle_environments.agent import get_last_callable
from kaggle_environments import make


def load_cb(agent_dir):
    adir = os.path.join(ROOT, agent_dir)
    main = os.path.join(adir, "main.py")
    cur = os.getcwd()
    os.chdir(adir)
    try:
        cb = get_last_callable(open(main).read(), path=main)
    finally:
        os.chdir(cur)
    return cb


cbA = load_cb(A_DIR)
cbB = load_cb(B_DIR)

w = [0, 0, 0]
game_times = []
none_A = 0
for g in range(GAMES):
    env = make("cabt")
    a_seat = 0 if g % 2 == 0 else 1
    order = [cbA, cbB] if a_seat == 0 else [cbB, cbA]
    t0 = time.monotonic()
    res = env.run(order)
    gt = time.monotonic() - t0
    game_times.append(gt)
    r = [s.get("reward") for s in res[-1]]
    ra, rb = r[a_seat], r[1 - a_seat]
    if ra is None:
        none_A += 1
    if ra is None and rb is None:
        out = "draw"
    elif ra is None:
        out = "B"
    elif rb is None:
        out = "A"
    elif ra > rb:
        out = "A"
    elif rb > ra:
        out = "B"
    else:
        out = "draw"
    if out == "A":
        w[0] += 1
    elif out == "B":
        w[1] += 1
    else:
        w[2] += 1
    print(f"  game {g+1}/{GAMES}: A={ra} B={rb} [{w[0]}W/{w[1]}L/{w[2]}D] wall={gt:.1f}s", flush=True)


def wilson(wins, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / denom
    return (max(0.0, center - half), p, min(1.0, center + half))


dec = w[0] + w[1]
lo, p, hi = wilson(w[0], dec)
print("\n===== TIMED A/B =====")
print(f"A={A_DIR}  B={B_DIR}")
print(f"Result (A view): {w[0]}W/{w[1]}L/{w[2]}D  total={sum(w)}")
if dec:
    print(f"win% (decisive): {p*100:.1f}%  Wilson95: [{lo*100:.1f}, {hi*100:.1f}]")
print(f"reward-None on A side (= A errored/timeout): {none_A}")
print(f"slowest GAME wall: {max(game_times):.1f}s  | mean game: {sum(game_times)/len(game_times):.1f}s  | 600s limit")
print(f"A diag: {getattr(cbA, '__globals__', {}).get('diag_snapshot', lambda: {})()}")
