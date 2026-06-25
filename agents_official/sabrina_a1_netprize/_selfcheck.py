"""Self-check for Sabrina A1 (net-prize-trade): run the agent vs itself in cabt.

Survival smoke test ONLY. The competition meta-conclusion stands: local self-play does
NOT judge ladder value. cabt here is a FILTER, not a judge. PASS confirms only that the A1
net-prize-trade term does not crash and never emits an INVALID / fallback.

PASS requires: completed == N_GAMES, 0 None-rewards, 0 policy/obs fallbacks, deck == 60.

It also INSTRUMENTS how often the A1 penalty actually fires (monkeypatch on the policy
method) so we can report honestly whether A1 is a live or near-dormant term in our deck.

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

# ── A1 firing instrumentation ────────────────────────────────────────────────
A1 = {"calls": 0, "fired": 0, "penalty_sum": 0.0}
_orig = agent_mod.AlakazamPolicy._a1_self_exposure_penalty


def _wrapped(self):
    A1["calls"] += 1
    pen = _orig(self)
    if pen and pen > 0:
        A1["fired"] += 1
        A1["penalty_sum"] += pen
    return pen


agent_mod.AlakazamPolicy._a1_self_exposure_penalty = _wrapped


def main():
    print("kaggle_environments:", getattr(ke, "version", "?"))
    print("deck loaded ids:    ", len(getattr(agent_mod, "my_deck", [])))
    print("A1 flag ON:         ", agent_mod.FMA_A1_NETPRIZE)
    print("A1_LAMBDA:          ", agent_mod.A1_LAMBDA)

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
    print(f"A1 penalty calls: {A1['calls']}  (every attack-score evaluation)")
    print(f"A1 penalty FIRED: {A1['fired']}  (times it returned > 0)")
    print(f"A1 penalty sum:   {A1['penalty_sum']}")
    print("=" * 60)
    ok = (completed == N_GAMES and none_rewards == 0 and fb == 0
          and len(getattr(agent_mod, "my_deck", [])) == 60)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
