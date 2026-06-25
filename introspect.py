"""Introspección del env cabt empaquetado en kaggle_environments (SIN identidad Kaggle).
Objetivo: ver la forma REAL del obs DICT (tipos de option como int, select.context,
campos de current/players) para escribir un agente heurístico que trabaje solo del dict.
También: ¿hay datos de cartas accesibles offline?
"""
import json, sys, traceback

import kaggle_environments as ke
print("kaggle-environments:", ke.version)

# ¿Qué expone el módulo cabt empaquetado?
import kaggle_environments.envs.cabt.cabt as cabt_mod
print("\n=== dir(cabt_mod) (no dunder) ===")
print([x for x in dir(cabt_mod) if not x.startswith("__")])

deck = []
for path in ["ptcg-abc/agents/dragapult/deck.csv", "ptcg-abc/agents/alakazam/deck.csv"]:
    try:
        with open(path) as f:
            deck = [int(x) for x in f.read().splitlines() if x.strip()][:60]
        print(f"\ndeck cargado de {path}: {len(deck)} cartas")
        break
    except FileNotFoundError:
        continue

CAP = {"n": 0}
SAMPLES = []

def agent(obs, config=None):
    try:
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            return deck
        # capturar hasta 6 selects variados (por contexto distinto)
        if CAP["n"] < 40:
            ctx = sel.get("context")
            opts = sel.get("option", [])
            types = sorted({o.get("type") for o in opts if isinstance(o, dict)})
            SAMPLES.append({
                "decision": CAP["n"],
                "select_keys": sorted(sel.keys()),
                "context": ctx,
                "minCount": sel.get("minCount"),
                "maxCount": sel.get("maxCount"),
                "n_options": len(opts),
                "option_types_present": types,
                "first_option": opts[0] if opts else None,
                "obs_top_keys": sorted(obs.keys()) if isinstance(obs, dict) else None,
            })
            CAP["n"] += 1
        n = max(1, int(sel.get("minCount", 1)))
        opts = sel.get("option", [])
        return list(range(min(n, len(opts)))) if opts else [0]
    except Exception:
        return [0]

env = ke.make("cabt", debug=True)
out = env.run([agent, agent])
print("\n=== PARTIDA OK, pasos:", len(out), "rewards:", [s.get("reward") for s in out[-1]])

# Volcar 1 obs 'current' completo de un paso intermedio para ver la estructura del estado
mid = out[len(out)//2]
for s in mid:
    o = s.get("observation") or {}
    cur = o.get("current") if isinstance(o, dict) else None
    if cur:
        print("\n=== current keys ===", sorted(cur.keys()))
        pl = cur.get("players")
        if pl:
            print("=== player[0] keys ===", sorted(pl[0].keys()))
            act = pl[0].get("active")
            if act:
                print("=== active[0] keys ===", sorted(act[0].keys()) if act and isinstance(act[0], dict) else act)
        break

print("\n=== SAMPLES (decisiones capturadas) ===")
# imprimir contextos únicos y un ejemplo de cada tipo de option
seen_ctx = {}
for smp in SAMPLES:
    c = smp["context"]
    if c not in seen_ctx:
        seen_ctx[c] = smp
print("contextos vistos:", sorted(seen_ctx.keys(), key=lambda x: (x is None, x)))
for c, smp in sorted(seen_ctx.items(), key=lambda kv: (kv[0] is None, kv[0])):
    print(json.dumps(smp, ensure_ascii=False)[:600])
