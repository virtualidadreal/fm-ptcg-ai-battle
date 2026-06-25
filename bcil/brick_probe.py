"""Brick-rate probe for Mega Starmie v1.

Plays N games (alternating seat) vs an opponent dir and, by wrapping the A agent
callable, inspects every observation A acts on to detect whether a Mega Starmie
(id 1031) EVER appears in A's own active+bench during the game. A game where the
Mega never comes online = a BRICK (the canonical loss signature from the replays).

Reads the obs dict directly (no cg import needed): the cabt obs exposes
current.players[yourIndex].{active,bench} with card .id. We reset the per-game
"saw_mega" flag at the start of each env.run.

Usage: python bcil/brick_probe.py <dirA> <dirB> <games> [seed_base]
Emits: BRICK_RESULT {json}
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "experiments"))
os.chdir(ROOT)
from ab_harness import load_cb, verify_deck_phase
from kaggle_environments import make

dirA, dirB = sys.argv[1], sys.argv[2]
games = int(sys.argv[3]) if len(sys.argv) > 3 else 25
seed_base = int(sys.argv[4]) if len(sys.argv) > 4 else 0

MEGA_ID = 1031
STARYU_ID = 1030

cbA = load_cb(dirA); cbB = load_cb(dirB)
verify_deck_phase(cbA, dirA); verify_deck_phase(cbB, dirB)

# per-game observation flags, set by the wrapper
_state = {"saw_mega": False, "saw_bench": False}


def _board_ids(obs):
    """Return list of card ids in A's own active+bench, robust to dict/obj shape."""
    try:
        cur = obs.get("current") if isinstance(obs, dict) else getattr(obs, "current", None)
        if cur is None:
            return []
        yi = cur.get("yourIndex") if isinstance(cur, dict) else getattr(cur, "yourIndex", None)
        players = cur.get("players") if isinstance(cur, dict) else getattr(cur, "players", None)
        if players is None or yi is None or yi >= len(players):
            return []
        me = players[yi]
        active = me.get("active") if isinstance(me, dict) else getattr(me, "active", None)
        bench = me.get("bench") if isinstance(me, dict) else getattr(me, "bench", None)
        ids = []
        bench_n = 0
        for slot in (active or []):
            if slot is None:
                continue
            cid = slot.get("id") if isinstance(slot, dict) else getattr(slot, "id", None)
            if cid is not None:
                ids.append(cid)
        for slot in (bench or []):
            if slot is None:
                continue
            bench_n += 1
            cid = slot.get("id") if isinstance(slot, dict) else getattr(slot, "id", None)
            if cid is not None:
                ids.append(cid)
        _state["_bench_n"] = bench_n
        return ids
    except Exception:
        return []


def wrappedA(obs_dict, config=None):
    try:
        if isinstance(obs_dict, dict) and obs_dict.get("select") is not None:
            ids = _board_ids(obs_dict)
            if MEGA_ID in ids:
                _state["saw_mega"] = True
            if _state.get("_bench_n", 0) >= 1:
                _state["saw_bench"] = True
    except Exception:
        pass
    return cbA(obs_dict, config)


# preserve diag_snapshot access through the wrapper
wrappedA.__globals__ if hasattr(wrappedA, "__globals__") else None

w = [0, 0, 0]
bricks = 0
brick_games = []
never_bench = 0
for g in range(games):
    _state["saw_mega"] = False
    _state["saw_bench"] = False
    _state["_bench_n"] = 0
    env = make("cabt", configuration={"seed": seed_base + g})
    a_seat = 0 if g % 2 == 0 else 1
    order = [wrappedA, cbB] if a_seat == 0 else [cbB, wrappedA]
    res = env.run(order)
    r = [s.get("reward") for s in res[-1]]
    ra, rb = r[a_seat], r[1 - a_seat]
    if ra is None and rb is None: oc = 2
    elif ra is None: oc = 1
    elif rb is None: oc = 0
    elif ra > rb: oc = 0
    elif rb > ra: oc = 1
    else: oc = 2
    w[oc] += 1
    brick = not _state["saw_mega"]
    if brick:
        bricks += 1
        brick_games.append(g)
    if not _state["saw_bench"]:
        never_bench += 1
    print(f"  game {g+1}/{games}: [{w[0]}W/{w[1]}L/{w[2]}D] mega_online={_state['saw_mega']} "
          f"brick={brick} outcome={'W' if oc==0 else 'L' if oc==1 else 'D'}",
          file=sys.stderr, flush=True)

diag = cbA.__globals__.get("diag_snapshot")
d = diag() if diag else {}
print("BRICK_RESULT " + json.dumps({
    "A": dirA, "B": dirB, "games": games, "seed_base": seed_base,
    "A_wins": w[0], "B_wins": w[1], "draws": w[2],
    "bricks": bricks, "brick_rate": bricks / max(1, games),
    "brick_games": brick_games, "never_benched": never_bench,
    "A_diag": d,
}))
