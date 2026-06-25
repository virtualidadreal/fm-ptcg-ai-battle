"""A/B runner que emite JSON (para los workers paralelos del workflow de validacion).

Juega `games` partidas entre dos agent dirs, ALTERNANDO asiento, con SEED por partida (seed_base+g) para que
distintos workers produzcan partidas INDEPENDIENTES y reproducibles. Emite una linea JSON con W/L/D + diag de
la net del agente A. Corre en Docker ptcg-torch.

Uso:  python bcil/ab_json.py <dirA> <dirB> <games> [seed_base]
"""
import os, sys, json, warnings
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "experiments"))
os.chdir(ROOT)
from ab_harness import load_cb, verify_deck_phase, wilson
from kaggle_environments import make

dirA, dirB = sys.argv[1], sys.argv[2]
games = int(sys.argv[3]) if len(sys.argv) > 3 else 50
seed_base = int(sys.argv[4]) if len(sys.argv) > 4 else 0

cbA = load_cb(dirA); cbB = load_cb(dirB)
verify_deck_phase(cbA, dirA); verify_deck_phase(cbB, dirB)

w = [0, 0, 0]  # A wins, B wins, draws
for g in range(games):
    env = make("cabt", configuration={"seed": seed_base + g})
    a_seat = 0 if g % 2 == 0 else 1
    order = [cbA, cbB] if a_seat == 0 else [cbB, cbA]
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
    # progreso por-partida (para poder ver el marcador parcial en runs largos; va a stderr para no ensuciar el JSON)
    print(f"  game {g+1}/{games}: [{w[0]}W/{w[1]}L/{w[2]}D]", file=sys.stderr, flush=True)

dec = w[0] + w[1]
lo, p, hi = wilson(w[0], dec)
diag = cbA.__globals__.get("diag_snapshot")
d = diag() if diag else {}
print("JSON_RESULT " + json.dumps({
    "A": dirA, "B": dirB, "games": games, "seed_base": seed_base,
    "A_wins": w[0], "B_wins": w[1], "draws": w[2], "decisive": dec,
    "winrate_A": p, "wilson_lo": lo, "wilson_hi": hi,
    "A_decisions": d.get("decisions"), "A_net_ok": d.get("net_ok"),
    "A_fallbacks": d.get("fallbacks"), "A_errors": d.get("errors"),
    "A_net_loaded": d.get("net_ok_load"),
    "A_diag": d,  # diag completo (para ISMCTS: net_evals, net_eval_ok_load, mcts_ok...)
}))
