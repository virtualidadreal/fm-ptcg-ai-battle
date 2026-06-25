"""Self-check for Sabrina v1a: run the agent vs itself in cabt for 0-crash / 0-INVALID.

Only a survival smoke test (the meta-conclusion: local signals do NOT judge ladder value;
this confirms ONLY that the 4x Lillie's Determination (1227) swap does not crash and never
emits an INVALID). PASS requires: completed==N_GAMES, 0 None-rewards, 0 policy/obs fallbacks,
and 1227 present in the engine card_table (so it can be piloted at all).

Run inside ptcg-cabt (linux/amd64), cwd = this agent dir so deck.csv + cg/ resolve.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.chdir(HERE)

import kaggle_environments as ke  # noqa: E402
import main as agent_mod          # noqa: E402

N_GAMES = int(os.environ.get("SELFCHECK_GAMES", "12"))


def main():
    print("kaggle_environments:", getattr(ke, "version", "?"))
    print("deck loaded ids:    ", len(getattr(agent_mod, "my_deck", [])))
    print("1227 in card_table: ", 1227 in agent_mod.card_table)
    print("1227 count in deck: ", getattr(agent_mod, "my_deck", []).count(1227))
    print("1264 count in deck: ", getattr(agent_mod, "my_deck", []).count(1264))

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
    print(f"errors:           {snap.get('errors', {})}")
    print("=" * 60)
    ok = (completed == N_GAMES and none_rewards == 0 and fb == 0
          and 1227 in agent_mod.card_table)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
