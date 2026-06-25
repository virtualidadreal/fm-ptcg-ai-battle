"""Microbench: time search_begin / search_step and a full agent decision.
Run inside the ptcg-cabt docker, cwd = agent_ismcts so `from cg.api` resolves."""
import os, sys, time, statistics, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

import main as agent_mod
from cg.game import battle_start, battle_finish, battle_select
from cg.api import to_observation_class

random.seed(0)
deck = agent_mod.my_deck
assert len(deck) == 60, f"deck has {len(deck)}"

# --- raw search_begin + search_step timing over real mid-game observations ---
sb_times, ss_times, dec_times = [], [], []
n_decisions = 0

for game in range(3):
    obs, sd = battle_start(deck, deck)
    your = game % 2
    steps = 0
    while obs["current"]["result"] < 0 and steps < 400:
        steps += 1
        if obs["current"]["yourIndex"] == your:
            # time a full agent decision
            t0 = time.monotonic()
            sel = agent_mod.agent(obs, None)
            dec_times.append(time.monotonic() - t0)
            n_decisions += 1
            # also time a single raw search_begin + a few search_steps
            if obs.get("select") is not None and len(sb_times) < 40:
                o = to_observation_class(obs)
                st = o.current
                me = st.players[your]; opp = st.players[1 - your]
                try:
                    t0 = time.monotonic()
                    ss = agent_mod.search_begin(
                        o,
                        your_deck=random.sample(deck, me.deckCount) if me.deckCount <= 60 else deck,
                        your_prize=random.sample(deck, len(me.prize)),
                        opponent_deck=[1072]*opp.deckCount,
                        opponent_prize=[1]*len(opp.prize),
                        opponent_hand=[1]*opp.handCount,
                        opponent_active=[1072] if (len(opp.active)>0 and opp.active[0] is None) else [])
                    sb_times.append(time.monotonic() - t0)
                    ids = [ss.searchId]
                    cur = ss
                    for _ in range(20):
                        if cur.observation.current.result >= 0:
                            break
                        sela = list(range(cur.observation.select.maxCount))
                        t0 = time.monotonic()
                        cur = agent_mod.search_step(cur.searchId, sela)
                        ss_times.append(time.monotonic() - t0)
                        ids.append(cur.searchId)
                    for sid in ids:
                        agent_mod.search_release(sid)
                    agent_mod.search_end()
                except Exception as e:
                    print("raw bench err:", type(e).__name__, e)
        else:
            sel = agent_mod.agent(obs, None)
        try:
            obs = battle_select(sel)
        except Exception as e:
            print("select err:", e); break
    battle_finish()

def stat(name, xs):
    if not xs:
        print(f"{name}: (no samples)"); return
    xs2 = sorted(xs)
    print(f"{name}: n={len(xs)} mean={statistics.mean(xs)*1000:.2f}ms "
          f"median={statistics.median(xs)*1000:.2f}ms p95={xs2[int(0.95*len(xs2))-1]*1000:.2f}ms "
          f"max={max(xs)*1000:.2f}ms")

print("\n===== MICROBENCH =====")
stat("search_begin", sb_times)
stat("search_step ", ss_times)
stat("AGENT decision", dec_times)
print(f"decisions timed: {n_decisions}")
print(f"SEARCH_COUNT={agent_mod.SEARCH_COUNT}  K={agent_mod.K_DETERMINIZATIONS}")
print("DIAG:", agent_mod.diag_snapshot())
if ss_times:
    sps = 1.0/statistics.mean(ss_times)
    print(f"search_steps/sec ~= {sps:.0f}")
