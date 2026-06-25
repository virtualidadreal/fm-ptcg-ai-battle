"""Smoke test del motor cabt en Linux x86-64.

Objetivo Semana 0: confirmar que (1) libcg.so CARGA en linux/amd64 (en macOS falla con
'slice is not valid mach-o file'), y (2) podemos correr una partida end-to-end con un
agente trivial 'first-legal' usando un deck.csv real del repo ptcg-abc.

Defensivo a propósito: cada paso informa aunque el siguiente falle.
"""
import sys, traceback

def step(msg):
    print(f"\n=== {msg} ===", flush=True)

step("1. import kaggle_environments")
try:
    import kaggle_environments as ke
    print("kaggle-environments:", ke.version)
except Exception:
    traceback.print_exc(); sys.exit(1)

step("2. make('cabt') (esto carga libcg.so)")
try:
    env = ke.make("cabt", debug=True)
    print("OK: entorno cabt creado. libcg.so cargado en linux/amd64.")
    spec = getattr(env, "specification", {}) or {}
    print("configuration keys:", list((spec.get("configuration") or {}).keys()))
except Exception:
    print("FALLO al crear cabt:")
    traceback.print_exc(); sys.exit(2)

step("3. cargar un deck.csv real (ptcg-abc/agents/dragapult)")
deck = []
for path in ["ptcg-abc/agents/dragapult/deck.csv", "ptcg-abc/agents/alakazam/deck.csv"]:
    try:
        with open(path) as f:
            deck = [int(x) for x in f.read().splitlines() if x.strip()][:60]
        print(f"deck cargado de {path}: {len(deck)} cartas, ids únicos: {sorted(set(deck))[:8]}...")
        break
    except FileNotFoundError:
        continue
if len(deck) != 60:
    print("AVISO: no se encontró un deck.csv de 60 cartas; sigo con deck vacío (puede fallar la partida).")

step("4. agente trivial 'first-legal'")
def agent(obs, config=None):
    try:
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            return deck  # fase de selección de mazo: devolver los 60 ids
        n = max(1, int(sel.get("minCount", 1)))
        opts = sel.get("option", [])
        return list(range(min(n, len(opts)))) if opts else [0]
    except Exception:
        return [0]  # fallback: nunca crashear

step("5. correr una partida agent vs agent")
try:
    out = env.run([agent, agent])
    last = out[-1]
    rewards = [s.get("reward") for s in last]
    print("PARTIDA COMPLETADA. pasos:", len(out), "| rewards finales:", rewards)
    print("\n✅ SMOKE TEST OK: el motor corre end-to-end en este runtime.")
except Exception:
    print("La partida falló (probablemente faltan datos de cartas oficiales o config de decks):")
    traceback.print_exc()
    print("\n⚠️  El motor CARGA pero correr partida necesita ajuste (config de decks / card data).")
