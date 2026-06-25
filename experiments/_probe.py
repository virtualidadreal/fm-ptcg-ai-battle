"""Probe to settle verifier findings empirically (run in docker).
Findings: (3) does the engine EVER require repeated indices (minCount > #legal options)?
(2) ability loops / runaway turns? (7) is agent/deck.csv accepted vs a DIFFERENT opp?
"""
import os, sys, importlib.util, warnings
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# load our real agent
spec = importlib.util.spec_from_file_location("ag", os.path.join(ROOT, "agent", "main.py"))
ag = importlib.util.module_from_spec(spec); spec.loader.exec_module(ag)

# a first-legal baseline opponent piloting a DIFFERENT deck (alakazam)
ALK = [int(x) for x in open(os.path.join(ROOT, "ptcg-abc/agents/alakazam/deck.csv")).read().splitlines() if x.strip()][:60]
def opp(obs, config=None):
    try:
        sel = obs.get("select")
        if sel is None: return ALK
        opts = sel.get("option") or []
        lo = max(1, sel.get("minCount", 1) or 1)
        return list(range(min(lo, len(opts)))) if opts else []
    except Exception:
        return [0]

STATS = {"max_tac": 0, "max_decisions_game": 0, "rep_required": [], "dmg_ctx": 0,
         "dmg_minc_gt_opts": 0, "selects": 0}
_dec = {"n": 0}

def probe_agent(obs, config=None):
    try:
        sel = obs.get("select")
        if sel is not None:
            STATS["selects"] += 1
            _dec["n"] += 1
            opts = sel.get("option") or []
            minc = sel.get("minCount", 0) or 0
            ctx = sel.get("context")
            cur = obs.get("current") or {}
            tac = cur.get("turnActionCount") or 0
            if isinstance(tac, int): STATS["max_tac"] = max(STATS["max_tac"], tac)
            # repetition required? minCount exceeds number of distinct legal options
            if minc > len(opts):
                STATS["rep_required"].append({"ctx": ctx, "minCount": minc, "maxCount": sel.get("maxCount"), "nopts": len(opts)})
            if ctx in (13, 14):
                STATS["dmg_ctx"] += 1
                if minc > len(opts):
                    STATS["dmg_minc_gt_opts"] += 1
    except Exception:
        pass
    return ag.agent(obs, config)

import kaggle_environments as ke
none_rewards = 0; completed = 0
NG = 30
for g in range(NG):
    _dec["n"] = 0
    env = ke.make("cabt")
    order = [probe_agent, opp] if g % 2 == 0 else [opp, probe_agent]
    out = env.run(order)
    completed += 1
    r = [s.get("reward") for s in out[-1]]
    me = 0 if g % 2 == 0 else 1
    if r[me] is None: none_rewards += 1
    STATS["max_decisions_game"] = max(STATS["max_decisions_game"], _dec["n"])

print("=== PROBE RESULTS (30 games, our agent/deck.csv vs alakazam first-legal) ===")
print("games completed:", completed, "/", NG)
print("our None rewards (INVALID/crash):", none_rewards, " (MUST be 0 => deck accepted + robust)")
print("total selects seen:", STATS["selects"])
print("max turnActionCount:", STATS["max_tac"], " (MAX_ACTIONS_GUARD=", ag.MAX_ACTIONS_GUARD, ")")
print("max decisions in a single game:", STATS["max_decisions_game"], " (runaway-loop check)")
print("DAMAGE_COUNTER selects:", STATS["dmg_ctx"])
print("DAMAGE_COUNTER with minCount>#options (repetition needed):", STATS["dmg_minc_gt_opts"])
print("ANY select with minCount>#options (dedup would fail):", len(STATS["rep_required"]))
for s in STATS["rep_required"][:10]:
    print("   ", s)
print("agent diag:", ag.diag_snapshot())
