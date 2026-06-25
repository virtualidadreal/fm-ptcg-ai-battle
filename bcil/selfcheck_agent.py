"""Self-check de leon_v3_bc (corre en Docker ptcg-torch): juega N partidas vs first-legal y comprueba que la
NET de verdad conduce (net_ok alto, fallbacks bajos, 0 crashes) — no que cae en silencio a first-legal.

Uso:  python bcil/selfcheck_agent.py [games]
"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))
from ab_harness import load_cb, verify_deck_phase
from kaggle_environments import make

GAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 4
AG = "agents_official/leon_v3_bc"
OPP = "experiments/baselines/firstlegal"

print(f"cargando {AG} ...")
cbA = load_cb(AG)
cbB = load_cb(OPP)
verify_deck_phase(cbA, AG)
verify_deck_phase(cbB, OPP)

diag = cbA.__globals__.get("diag_snapshot")
print("net cargada (load):", cbA.__globals__.get("_NET_OK"), "| err:", cbA.__globals__.get("_NET_ERR"))

w = [0, 0, 0]
t0 = time.time()
for g in range(GAMES):
    env = make("cabt")
    a_seat = 0 if g % 2 == 0 else 1
    order = [cbA, cbB] if a_seat == 0 else [cbB, cbA]
    res = env.run(order)
    r = [s.get("reward") for s in res[-1]]
    ra, rb = r[a_seat], r[1 - a_seat]
    if ra is None and rb is None: oc = "draw"
    elif ra is None: oc = "B"
    elif rb is None: oc = "A"
    elif ra > rb: oc = "A"
    elif rb > ra: oc = "B"
    else: oc = "draw"
    w[0 if oc == "A" else (1 if oc == "B" else 2)] += 1
    print(f"  game {g+1}/{GAMES}: A(leon_v3)={ra} B(firstlegal)={rb} [{w[0]}W/{w[1]}L/{w[2]}D]", flush=True)

d = diag() if diag else {}
dec = w[0] + w[1]
print("\n=== SELF-CHECK leon_v3_bc ===")
print(f"vs first-legal: {w[0]}W/{w[1]}L/{w[2]}D | win% (decisivas) {100*w[0]/max(1,dec):.0f}% | {(time.time()-t0):.0f}s")
print("DIAG:", d)
tot = d.get("decisions", 0); nok = d.get("net_ok", 0); fb = d.get("fallbacks", 0)
print(f"\ndecisiones {tot} | net_ok {nok} ({100*nok/max(1,tot):.1f}%) | fallbacks {fb} | errores {d.get('errors')}")
ok = (d.get("net_ok_load") is True) and tot > 0 and (nok / max(1, tot) > 0.9) and not d.get("errors")
print("VEREDICTO:", "OK (la net conduce, sin crashes)" if ok else "REVISAR (net no conduce o hay errores)")
