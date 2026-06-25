#!/usr/bin/env python3
"""Driver de simulacion (Via 2) — porta el loop de la celda 6 del notebook.

Corre SOLO en Docker linux/amd64 (libcg.so es ELF x86-64). Genera:
  - tools/replay-visualizer/sim_steps.json  (lista de pasos del episodio)
  - tools/replay-visualizer/replay_sim.html (replay interactivo, via render_core)

Agentes configurables por env: AGENT0 / AGENT1 (random|rule|mcts|ucb).
"""
import io
import json
import os
import sys
import traceback
from contextlib import redirect_stdout

# Rutas absolutas (este script vive en tools/replay-visualizer/sim/).
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))      # .../sim
_VIS_DIR = os.path.dirname(_SCRIPT_DIR)                        # .../replay-visualizer
_REPO_DIR = os.path.abspath(os.path.join(_VIS_DIR, "..", ".."))  # repo root

# sys.path para resolver 'cg' (symlink sim/cg), 'run_game', 'battle_eval'.
sys.path.insert(0, _SCRIPT_DIR)
# sys.path para resolver render_core (vive en replay-visualizer/).
sys.path.insert(0, _VIS_DIR)

DATA_DIR = os.path.join(_REPO_DIR, "data", "competition")
NOTEBOOK_PATH = os.path.join(
    _VIS_DIR, "battle-replay-visualizer-visualizer.ipynb"
)
STEPS_OUT = os.path.join(_VIS_DIR, "sim_steps.json")
HTML_OUT = os.path.join(_VIS_DIR, "replay_sim.html")


def board_eval(obs, my_index):
    if obs.current is None:
        return 0.5
    state = obs.current
    if state.result != -1:
        return 1.0 if state.result == my_index else 0.0
    my_st = state.players[my_index]
    op_st = state.players[1 - my_index]
    # Prize count difference (most important factor)
    prize_diff = ((6 - len(my_st.prize)) - (6 - len(op_st.prize))) / 6.0
    # Total HP difference
    def total_hp(ps):
        return sum(p.hp for p in list(ps.active) + list(ps.bench) if p is not None)
    my_hp, op_hp = total_hp(my_st), total_hp(op_st)
    hp_diff = (my_hp - op_hp) / max(my_hp + op_hp, 1)
    score = prize_diff * 0.70 + hp_diff * 0.30
    return max(0.0, min(1.0, 0.5 + score * 0.5))


def main():
    from cg.game import (
        battle_start,
        battle_select,
        battle_finish,
        visualize_data,
    )
    from cg.api import to_observation_class
    from run_game import RuleAgent, UCBMCTSAgent, MCTSAgent, random_agent

    # Deck desde sim/cg/deck.csv (60 cartas).
    deck_csv = os.path.join(_SCRIPT_DIR, "cg", "deck.csv")
    with open(deck_csv) as _f:
        SAMPLE_DECK = [int(l.strip()) for l in _f if l.strip()][:60]
    print(f"Deck loaded: {len(SAMPLE_DECK)} cards")

    AGENT0 = os.environ.get("AGENT0", "rule")
    AGENT1 = os.environ.get("AGENT1", "rule")

    def _make_agent(kind):
        if kind == "rule":
            return RuleAgent(SAMPLE_DECK)
        if kind == "mcts":
            return MCTSAgent(SAMPLE_DECK, n_simulations=50)
        if kind == "ucb":
            return UCBMCTSAgent(SAMPLE_DECK, n_simulations=200)
        return random_agent

    print(f"Running game: {AGENT0} vs {AGENT1} ...")
    obs_dict, _ = battle_start(SAMPLE_DECK, SAMPLE_DECK)
    agents = [_make_agent(AGENT0), _make_agent(AGENT1)]
    decks = [SAMPLE_DECK, SAMPLE_DECK]
    step_extras = []
    final_result = -1
    invalid_count = 0

    for _ in range(3000):
        obs = to_observation_class(obs_dict)
        if obs.current and obs.current.result != -1:
            final_result = obs.current.result
            break

        eval_p0 = board_eval(obs, 0)
        player = 0 if obs.current is None else obs.current.yourIndex
        agent = agents[player]

        # Capture stdout from agent (shows in AI Decision panel).
        _buf = io.StringIO()
        with redirect_stdout(_buf):
            action = agent(obs_dict, decks[player])
        debug_out = _buf.getvalue().strip() or None
        if debug_out and "invalid" in debug_out.lower():
            invalid_count += debug_out.lower().count("invalid")

        # Collect per-option scores (RuleAgent only).
        agent_scores = None
        if hasattr(agent, "last_scores_detail") and obs.select:
            sorted_opts = sorted(
                agent.last_scores_detail, key=lambda x: x["score"], reverse=True
            )
            ctx = obs.select.context
            agent_scores = {
                "player": player,
                "context": ctx.name if hasattr(ctx, "name") else str(ctx),
                "options": sorted_opts,
            }

        step_extras.append(
            {
                "eval_p0": eval_p0,
                "agent_scores": agent_scores,
                "debug_out": debug_out,
            }
        )
        obs_dict = battle_select(action)

    steps = json.loads(visualize_data())
    battle_finish()

    # Detecta resultado final tras el loop (por si rompio el rango sin result).
    if final_result == -1:
        try:
            _obs = to_observation_class(obs_dict)
            if _obs.current is not None and _obs.current.result != -1:
                final_result = _obs.current.result
        except Exception:
            pass

    for i, step in enumerate(steps):
        if i < len(step_extras):
            step.update(step_extras[i])

    print(f"Game finished: {len(steps)} steps")

    # Vuelca steps a JSON.
    with open(STEPS_OUT, "w", encoding="utf-8") as f:
        json.dump(steps, f)
    print(f"Wrote steps -> {STEPS_OUT}")

    # Render HTML via render_core.
    import render_core

    nbytes = render_core.render(steps, HTML_OUT, DATA_DIR, NOTEBOOK_PATH)
    print(f"Wrote HTML -> {HTML_OUT} ({nbytes} bytes)")

    print(
        f"STEPS={len(steps)}, RESULT={final_result}, INVALID={invalid_count}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
