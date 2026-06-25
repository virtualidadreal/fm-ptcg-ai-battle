#!/usr/bin/env python3
"""
agreement_top_pilots.py — Reproducibility probe for the
"AGREEMENT-with-top-pilots" claim (v1 43.52% / v2 43.84%).

WHAT THE CLAIM IS
-----------------
Agreement = the fraction of decisions where OUR AlakazamPolicy (sabrina_v1)
picks the SAME action as the top pilot did, evaluated on the SAME observation,
over the top-pilot replays in data/alakazam_analysis/*.json.

The Kaggle replay stores, per step and per seat:
  - observation (with a `select` carrying the legal `option` list), and
  - action = the indices INTO that option list that the pilot actually played.
Our policy's choose()/normalize_selection ALSO returns option indices, so the two
are directly comparable:  agreement_step = (policy_indices == recorded_action).

WHAT THIS SCRIPT ESTABLISHES (offline, no libcg.so loaded)
----------------------------------------------------------
1. PROOF OF INSTANTIATION OFFLINE. The sabrina_v1 policy module CAN be imported
   and its agent()/AlakazamPolicy().choose() CAN be called on a replay
   observation WITHOUT loading libcg.so. We do this by stubbing cg.sim.lib so
   cg.api imports as pure Python (to_observation_class / to_dataclass are pure
   Python; only the card-DB getters AllCard/AllAttack touch the .so).

2. HONEST GATING. A FAITHFUL agreement requires the engine's card/attack
   database (lib.AllCard()/lib.AllAttack()): the policy keys nearly every
   heuristic on per-card attackId arrays, attack energy-costs, and skill text
   that exist ONLY inside libcg.so's namespace. card_db.json has NO attackId
   field and cannot reconstruct it. So with the stub, the policy runs against an
   EMPTY card DB and behaves like a DIFFERENT (degraded) policy. The number it
   produces is therefore NOT the sabrina_v1-with-engine agreement and MUST NOT
   be reported as 43.52/43.84.

   => The faithful 43.52%/43.84% number is ENGINE-GATED (Linux libcg.so).
      The exact runner to reproduce it on Linux is printed at the end and
      mirrored in research/REPRODUCE.md.

This script prints BOTH:
  (a) the DB-degraded proxy agreement actually computed here (clearly labeled),
  (b) the gating verdict.

Run:  python research/agreement_top_pilots.py
"""
from __future__ import annotations
import os, sys, json, glob, types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_DIR = os.path.join(ROOT, os.environ.get("AGENT_DIR", "agents_official/sabrina_v1"))
DATA_GLOB = os.path.join(ROOT, "data", "alakazam_analysis", "alakazam_*.json")


def _install_sim_stub():
    """Stub cg.sim so cg.api imports without libcg.so.

    AllCard/AllAttack return an EMPTY DB on purpose: we are NOT allowed to load
    the Linux .so here, and there is no faithful offline source for the engine's
    attackId namespace. Any other lib call returns 0 (never used on the
    obs-parsing / choose() path)."""
    fake = types.ModuleType("cg.sim")

    class _FakeLib:
        def AllCard(self):   return b"[]"
        def AllAttack(self): return b"[]"
        def __getattr__(self, name):
            def _f(*a, **k): return 0
            return _f

    fake.lib = _FakeLib()
    fake.Battle = type("Battle", (), {})
    sys.modules["cg.sim"] = fake


def load_policy():
    _install_sim_stub()
    if AGENT_DIR not in sys.path:
        sys.path.insert(0, AGENT_DIR)
    import main as policy  # sabrina_v1/main.py
    return policy


def iter_decision_pairs(replay_path):
    """Yield (obs_dict, recorded_action) for every seat-step that is an ACTIVE
    decision with a non-null select (i.e. a real action choice, not the
    deck-build phase and not an INACTIVE wait)."""
    with open(replay_path) as f:
        d = json.load(f)
    for step in d.get("steps", []):
        for seat in step:
            if seat.get("status") != "ACTIVE":
                continue
            obs = seat.get("observation") or {}
            sel = obs.get("select")
            if sel is None:
                continue
            action = seat.get("action")
            if not isinstance(action, list):
                continue
            yield obs, action


def compute_proxy_agreement(policy):
    """DB-DEGRADED proxy: run policy.agent() (empty card DB) and compare its
    returned option indices against the recorded pilot action.
    NOT the faithful number — see module docstring."""
    total = 0
    match = 0
    crash = 0
    files = sorted(glob.glob(DATA_GLOB))
    policy.diag_reset()
    for fp in files:
        for obs, action in iter_decision_pairs(fp):
            try:
                out = policy.agent(obs)
            except Exception:
                crash += 1
                continue
            if not isinstance(out, list):
                crash += 1
                continue
            total += 1
            if list(out) == list(action):
                match += 1
    return {
        "files": len(files),
        "decisions": total,
        "matches": match,
        "crashes": crash,
        "proxy_agreement_pct": (100.0 * match / total) if total else None,
        "policy_diag": policy.diag_snapshot(),
    }


def main():
    print("=" * 72)
    print("AGREEMENT-with-top-pilots — offline reproducibility probe")
    print("=" * 72)

    # 1) Prove offline instantiation.
    try:
        policy = load_policy()
        print("[OK] sabrina_v1 policy imported WITHOUT libcg.so (cg.sim stubbed).")
    except Exception as exc:
        print(f"[FAIL] could not import policy even with stub: {exc!r}")
        print("VERDICT: engine-gated (import requires engine).")
        return

    # Prove a single choose() call works on a real replay obs.
    sample = sorted(glob.glob(DATA_GLOB))
    if sample:
        for obs, action in iter_decision_pairs(sample[0]):
            out = policy.agent(obs)
            print(f"[OK] agent() ran on a real replay obs -> {out} "
                  f"(pilot played {action}).")
            break

    # 2) Faithful-DB check.
    n_cards = len(policy.all_card)
    print(f"[INFO] card DB size loaded by policy = {n_cards} "
          f"(0 => engine DB ABSENT; faithful run impossible here).")

    # 3) Compute the DB-degraded proxy (clearly labeled).
    res = compute_proxy_agreement(policy)
    print("-" * 72)
    print("DB-DEGRADED PROXY (NOT the faithful number):")
    print(f"  replays                : {res['files']}")
    print(f"  ACTIVE select decisions: {res['decisions']}")
    print(f"  matches                : {res['matches']}")
    print(f"  crashes/skips          : {res['crashes']}")
    if res["proxy_agreement_pct"] is not None:
        print(f"  proxy agreement        : {res['proxy_agreement_pct']:.2f}%")
    print("-" * 72)

    # 4) Verdict.
    faithful = n_cards > 0
    verdict = "computed-offline (FAITHFUL)" if faithful else "ENGINE-GATED"
    print(f"VERDICT: {verdict}")
    if not faithful:
        print(
            "  The policy keys its heuristics on the engine's per-card attackId\n"
            "  arrays + attack energy-costs + skill text (lib.AllCard/AllAttack in\n"
            "  libcg.so). card_db.json has NO attackId field and cannot rebuild that\n"
            "  namespace, so the proxy above is a DIFFERENT (degraded) policy. The\n"
            "  faithful 43.52%/43.84% number CANNOT be honestly reproduced on this\n"
            "  (macOS) machine.\n"
            "  REPRODUCE ON LINUX (real libcg.so present), pseudo-runner:\n"
            "    docker run --rm -v $PWD:/w -w /w ptcg-torch \\\n"
            "      python research/agreement_top_pilots.py --faithful\n"
            "  where --faithful SKIPS the cg.sim stub so the real card DB loads.\n"
            "  See research/REPRODUCE.md for the full command + the v1-vs-v2 A/B.")

    out_path = os.path.join(ROOT, "research", "agreement_top_pilots.out.json")
    with open(out_path, "w") as f:
        json.dump(
            {"verdict": verdict, "faithful": faithful, "card_db_size": n_cards,
             **res}, f, indent=2, default=str)
    print(f"[saved] {out_path}")


if __name__ == "__main__":
    # --faithful: drop the stub so the REAL libcg.so card DB loads (Linux only).
    if "--faithful" in sys.argv:
        if AGENT_DIR not in sys.path:
            sys.path.insert(0, AGENT_DIR)
        import main as policy  # will load libcg.so via cg.api
        res = compute_proxy_agreement(policy)
        res["faithful"] = True
        res["verdict"] = "computed-offline (FAITHFUL, engine present)"
        print(json.dumps(res, indent=2, default=str))
    else:
        main()
