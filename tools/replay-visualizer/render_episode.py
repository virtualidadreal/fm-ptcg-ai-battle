#!/usr/bin/env python3
"""Render a local episode JSON to an interactive replay HTML.

Via 1 del Battle Replay Visualizer v2 (shiiin9): NO usa cg/libcg.so ni Docker.
La logica de plantilla vive en render_core.render(); este script solo resuelve
rutas, carga el episodio y delega.

Uso:
    python render_episode.py [EPISODE_JSON] [-o SALIDA.html]

Defaults:
    EPISODE_JSON = data/episodes/episode-81310338-replay.json
    SALIDA       = tools/replay-visualizer/replay_episode.html
"""
import argparse
import json
import os
import sys

import render_core

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))   # proyectos/ptcg-ai-battle
NOTEBOOK = os.path.join(HERE, "battle-replay-visualizer-visualizer.ipynb")

# DATA_DIR = donde viven los CSV de cartas (EN_Card_Data.csv; JP es opcional).
DATA_DIR = os.path.join(ROOT, "data", "competition")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "episode",
        nargs="?",
        default=os.path.join(ROOT, "data", "episodes", "episode-81310338-replay.json"),
        help="ruta al JSON del episodio",
    )
    ap.add_argument(
        "-o", "--out",
        default=os.path.join(HERE, "replay_episode.html"),
        help="ruta del HTML de salida",
    )
    args = ap.parse_args()

    if not os.path.exists(args.episode):
        sys.exit(f"No existe el episodio: {args.episode}")
    if not os.path.exists(os.path.join(DATA_DIR, "EN_Card_Data.csv")):
        sys.exit(f"No encuentro EN_Card_Data.csv en {DATA_DIR}")

    with open(args.episode, encoding="utf-8") as f:
        episode = json.load(f)

    # Formato replay de Kaggle: dict con steps[0][0]['visualize'].
    steps = None
    if isinstance(episode, dict) and "steps" in episode:
        try:
            steps = episode["steps"][0][0]["visualize"]
        except (KeyError, IndexError, TypeError):
            steps = None
    if steps is None:
        sys.exit(
            f"'{args.episode}' no contiene datos de replay (steps[0][0].visualize).\n"
            "Parece el log del agente (stdout/stderr por turno), no el replay visual.\n"
            "Usa el JSON del replay (dict con 'steps'), o pasa el id del episodio: replay <id>"
        )
    ep_id = episode.get("id", "episode")
    print(f"Episodio: {ep_id}  /  {len(steps)} steps")

    n_bytes = render_core.render(steps, args.out, DATA_DIR, NOTEBOOK)
    print(f"HTML generado: {args.out}  ({n_bytes} bytes)")


if __name__ == "__main__":
    main()
