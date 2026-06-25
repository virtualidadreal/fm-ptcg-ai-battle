# Battle Replay Visualizer v2

Visor de partidas del PTCG AI Battle, portado del kernel `shiiin9/battle-replay-visualizer`. Genera un HTML interactivo de la partida con tablero, manos, premios, panel de decisión del agente y eval por paso.

Hay dos vías para producir ese HTML. La 1 renderiza un episodio que ya tienes en disco, no necesita el motor. La 2 simula una partida real entre dos agentes y la renderiza, necesita Docker porque ahí corre el motor `libcg.so`.

## Lanzador rápido (lo normal)

Desde la raíz del proyecto, el script `./replay` cubre todo y abre el HTML en el navegador:

```bash
cd ~/FMA/proyectos/ptcg-ai-battle

./replay                  # episodio de ejemplo
./replay <ruta.json>      # tu replay (JSON formato dict con 'steps')
./replay <id>             # busca <id>.json en los exports de data/episodes/ y lo abre
./replay sim [a0] [a1]    # simula una partida en Docker (a0/a1 = random|rule|mcts|ucb)
./replay list             # lista los exports de episodios disponibles
```

Para cargar tus partidas: descarga el export diario de episodios al `data/episodes/` (zips ya presentes de d16 a d21), mira los ids con `./replay list` y abre el que quieras con `./replay <id>`. El script saca ese `<id>.json` del zip sin descomprimir los 21 GB. Si descargas un replay suelto desde Kaggle, pásale la ruta directamente. Ojo: el JSON debe ser el *replay* (dict con `steps`), no el log del agente (stdout/stderr), que no se puede visualizar.

Una vez abierto cualquier replay en el navegador, el botón **📁 Cargar partida** de la cabecera abre otro `.json` desde tu disco sin volver a la terminal (lo procesa en el navegador, no recarga la página). Útil para ir saltando entre partidas. El JSON debe ser el replay (dict con `steps`), igual que en la CLI.

Los comandos largos de abajo son el detalle de lo que hace `./replay` por dentro.

## Vía 1, nativa, sin Docker

Visor de un episodio existente. Coge un `data/episodes/*.json` y lo renderiza a HTML. No toca `libcg.so`, corre en el Python del host (macOS/arm64).

```bash
/Users/franmilla/FMA/proyectos/ptcg-ai-battle/.venv/bin/python \
  /Users/franmilla/FMA/proyectos/ptcg-ai-battle/tools/replay-visualizer/render_episode.py \
  [EPISODE_JSON] [-o salida.html]
```

Sin argumentos usa un episodio por defecto de `data/episodes/` y escribe `replay_episode.html` en la carpeta del visor.

## Vía 2, simulación real, requiere Docker linux/amd64 + colima

Simula una partida entre dos agentes y la renderiza. Corre dentro de Docker porque `libcg.so` es ELF x86-64 y el host macOS/arm64 no lo carga.

```bash
docker run --platform=linux/amd64 --rm \
  -e AGENT0=rule -e AGENT1=rule \
  -v "/Users/franmilla/FMA/proyectos/ptcg-ai-battle":/work -w /work \
  ptcg-cabt python tools/replay-visualizer/sim/simulate_battle.py
```

Genera `sim_steps.json` (los pasos del episodio) y `replay_sim.html` (el replay) en la carpeta del visor. `AGENT0` y `AGENT1` admiten `random`, `rule`, `mcts`, `ucb` (por defecto `rule` vs `rule`).

Levantar colima y construir la imagen, si hace falta:

```bash
export PATH="/opt/homebrew/bin:$PATH"
colima status || colima start --vm-type vz --vz-rosetta --cpu 4 --memory 6 --disk 40
docker build --platform=linux/amd64 -t ptcg-cabt /Users/franmilla/FMA/proyectos/ptcg-ai-battle
```

## Arquitectura

- `render_core.py`, solo stdlib, compartido entre host y Docker. Reutiliza las celdas 4 (loaders de cartas, leen `EN_Card_Data.csv`) y 5 (plantilla HTML y `generate_html`) del notebook `battle-replay-visualizer-visualizer.ipynb`. Ambas vías delegan aquí el render.
- `render_episode.py`, entrada de la vía 1. Resuelve rutas, carga el episodio y llama a `render_core.render()`.
- `sim/`, todo lo de la vía 2:
  - `simulate_battle.py`, driver que porta el loop de simulación de la celda 6 (`battle_start` -> `to_observation_class` -> agente -> `battle_select` -> `visualize_data`) más `board_eval`.
  - `run_game.py` y `battle_eval.py`, extraídos de la celda 2 del notebook (agentes y evaluación).
  - `cg -> ../../../data/competition`, symlink al motor (`cg/` con `libcg.so`, `deck.csv`, `EN_Card_Data.csv`).

## Limitación

El host macOS/arm64 no carga `libcg.so` (es ELF x86-64), por eso la vía 2 corre obligatoriamente en Docker linux/amd64. La vía 1 no necesita el motor, así que va nativa en el host.
