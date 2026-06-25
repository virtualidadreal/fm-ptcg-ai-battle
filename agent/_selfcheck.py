"""Self-check: run the agent against itself in the official cabt env."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import kaggle_environments as ke  # noqa: E402
import main as agent_mod          # noqa: E402

N_GAMES = 25


def main():
    print("kaggle_environments:", getattr(ke, "version", "?"))
    print("deck loaded ids:", len(agent_mod.my_deck))
    agent_mod.diag_reset()

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
            print(f"game {g}: NONE rewards -> {rewards} status={[last[0].get('status'), last[1].get('status')]}")
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
    print("=" * 60)
    print(f"games run:          {N_GAMES}")
    print(f"completed:          {completed}")
    print(f"None rewards:       {none_rewards}  (MUST be 0)")
    print(f"results:            {results}")
    print(f"decisions:          {snap['decisions']}")
    print(f"deck_returns:       {snap['deck_returns']}")
    print(f"policy_ok:          {snap['policy_ok']}")
    print(f"fallbacks:          {snap['fallbacks']}")
    print(f"fallback_rate:      {snap['fallback_rate']:.4f}  (want < 0.10)")
    print(f"errors:             {snap['errors']}")
    print("=" * 60)
    ok = (completed == N_GAMES and none_rewards == 0 and snap["fallback_rate"] < 0.10)
    print("PASS" if ok else "FAIL")


if __name__ == "__main__":
    main()
