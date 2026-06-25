"""Self-check for Leon v1.5 (prize-aware): run the agent vs itself in cabt.

Survival requirement: 0 None-rewards (no crashed games), and 0 EXCEPTION fallbacks
(the only way fallbacks>0 in this agent's diag is an invalid output or a raised
exception inside the policy). Both must be 0.

Run inside the linux/amd64 docker (ptcg-cabt), cwd = this agent dir so deck.csv and
cards_enriched.json resolve and cg/ imports.
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
    print("deck loaded ids:    ", len(agent_mod.my_deck))
    print("enriched cards:     ", len(agent_mod.ENRICHED))
    print("cg_ok:              ", agent_mod._CG_OK)

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
    fallbacks = snap.get("fallbacks", 0)
    errors = snap.get("errors", {})
    fb_rate = (fallbacks / decisions) if decisions else 0.0

    print("=" * 60)
    print(f"games run:     {N_GAMES}")
    print(f"completed:     {completed}")
    print(f"None rewards:  {none_rewards}  (MUST be 0)")
    print(f"results:       {results}")
    print(f"decisions:     {decisions}")
    print(f"policy_ok:     {snap.get('policy_ok', 0)}")
    print(f"fallbacks:     {fallbacks}  (MUST be 0 = no crashes/invalids)")
    print(f"fallback_rate: {fb_rate:.4f}")
    print(f"errors:        {errors}")
    print("=" * 60)
    ok = (completed == N_GAMES and none_rewards == 0 and fallbacks == 0)
    print("PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
