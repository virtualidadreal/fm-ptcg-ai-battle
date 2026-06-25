"""Self-check for Sabrina kb_prizemap (adaptive 6-prize prize-map nudge): agent vs itself in cabt.

Survival smoke test ONLY. The competition meta-conclusion stands: local self-play does
NOT judge ladder value. cabt here is a FILTER, not a judge. PASS confirms only that the
prize-map nudge does not crash and never emits an INVALID / fallback.

PASS requires: completed == N_GAMES, 0 None-rewards, 0 policy/obs fallbacks, deck == 60.

It also INSTRUMENTS how often the prize-map bias is non-zero (monkeypatch on the policy
method) so we can report honestly whether the lever is a live or near-dormant term.

Run inside ptcg-cabt (linux/amd64), cwd = this agent dir so deck.csv + cg/ resolve:
  docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt python _selfcheck.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

import kaggle_environments as ke  # noqa: E402
import main as agent_mod          # noqa: E402

N_GAMES = int(os.environ.get("SELFCHECK_GAMES", "12"))

# ── prize-map-bias firing instrumentation ────────────────────────────────────
PM = {"calls": 0, "fired": 0, "bias_sum": 0.0}
_orig = agent_mod.AlakazamPolicy._prizemap_bias


def _wrapped(self, o):
    PM["calls"] += 1
    b = _orig(self, o)
    if b:
        PM["fired"] += 1
        PM["bias_sum"] += b
    return b


agent_mod.AlakazamPolicy._prizemap_bias = _wrapped


def main():
    print("kaggle_environments:   ", getattr(ke, "version", "?"))
    print("deck loaded ids:       ", len(getattr(agent_mod, "my_deck", [])))
    print("FMA_KB_PRIZEMAP flag:  ", agent_mod.FMA_KB_PRIZEMAP)
    print("PRIZEMAP_EPSILON:      ", agent_mod.PRIZEMAP_EPSILON)

    completed = 0
    none_rewards = 0
    results = {"win0": 0, "win1": 0, "draw": 0, "error": 0}

    for g in range(N_GAMES):
        env = ke.make("cabt")
        out = env.run([agent_mod.agent, agent_mod.agent])
        last = out[-1]
        rewards = [last[0].get("reward"), last[1].get("reward")]
        if rewards[0] is None or rewards[1] is None:
            none_rewards += 1
            results["error"] += 1
            print(f"game {g}: NONE rewards -> {rewards} "
                  f"status={[last[0].get('status'), last[1].get('status')]}")
            continue
        completed += 1
        r0, r1 = rewards
        if r0 == r1:
            results["draw"] += 1
        elif r0 > r1:
            results["win0"] += 1
        else:
            results["win1"] += 1

    snap = agent_mod.diag_snapshot()
    decisions = snap.get("decisions", 0)
    fb = snap.get("policy_fallback", 0) + snap.get("obs_fallback", 0)
    print("=" * 60)
    print(f"games run:        {N_GAMES}")
    print(f"completed:        {completed}")
    print(f"None rewards:     {none_rewards}  (MUST be 0)")
    print(f"results:          {results}")
    print(f"decisions:        {decisions}")
    print(f"policy_ok:        {snap.get('policy_ok', 0)}")
    print(f"policy_fallback:  {snap.get('policy_fallback', 0)}  (MUST be 0)")
    print(f"obs_fallback:     {snap.get('obs_fallback', 0)}  (MUST be 0)")
    print(f"fallback_rate:    {snap.get('fallback_rate', 0)}  (MUST be 0.0)")
    print(f"errors:           {snap.get('errors', {})}")
    print("-" * 60)
    print(f"prizemap calls:   {PM['calls']}  (every scored option that hit _prizemap_bias)")
    print(f"prizemap NON-ZERO:{PM['fired']}  (times it returned != 0)")
    print(f"prizemap bias sum:{PM['bias_sum']}")
    print(f"prizemap_fires:   {snap.get('prizemap_fires', 0)}  (decisions where the map biased >=1 option)")
    print("=" * 60)
    ok = (completed == N_GAMES and none_rewards == 0 and fb == 0
          and len(getattr(agent_mod, "my_deck", [])) == 60)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
