# PTCG AI Battle Challenge — Plan de ataque

> Competición Kaggle de The Pokémon Company (+ HEROZ, Matsuo Institute, Google Cloud, Nvidia).
> Construir un agente de IA que juega al Pokémon TCG. **Decidido competir en serio (Top 8 + premio).**

## Hechos clave (de las reglas oficiales, 21 jun 2026)

- **Dos tracks.** Esta **Simulation** NO da dinero (solo medallas/conocimiento). Los premios salen del
  **Hackathon/Strategy track**, y el ranking final para premio = **leaderboard + un report**. Hay que entrar
  en los dos. Leaderboard = condición necesaria, no suficiente.
- **🔴 NO INGRESS/EGRESS durante la partida.** El agente no puede llamar a nada externo en runtime
  (ni LLM, ni API). Es **Python autocontenido y offline**. Lo único que se entrega: `.tar.gz` con
  `main.py` (top-level) + `deck.csv`. → El runtime es game-AI clásico, NO un wrapper de Claude.
  **El Dev Aumentado es el TALLER de desarrollo, no el jugador.**
- **SDK (cabt Engine)** con la misma lógica que el entorno Kaggle, para entrenar/depurar en local
  y hacer RL. Docs: https://matsuoinstitute.github.io/cabt/ · **kaggle-environments 1.30.1** (lo instalado y
  funcional; la web cita "as of 1.14.10" pero el paquete vivo es 1.30.1 — alinear a 1.30.1).
  Reglas dicen explícito: *"rule-based programming alone may not ensure a high ranking"*.
- **Interfaz del agente:** `agent(obs_dict: dict) -> list[int]`. `obs_dict` = `logs` + `current` (tablero)
  + `select` (opciones legales). Devuelves los índices elegidos (hasta `select["maxCount"]`).
  El motor SOLO ofrece jugadas legales.
- **Mazo:** 60 cartas (CSV de card IDs) desde pool ~2000 cartas Standard. ⚠️ `all_card_data()` NO existe en
  el paquete instalado (grep=0); usar `EN Card Data.csv` del dataset, o escribir binding a `AllCard` del .so.
- **Investigación completa:** ver `research/top8-roadmap.md` (roadmap maestro a Top 8).
- **Rating:** gaussiano N(μ,σ²), μ₀=600. Sube/baja con victorias/derrotas. El margen de victoria NO importa.
- **Submission:** valida primero jugando contra copias de sí mismo. 5 envíos/día, solo cuentan los 2 últimos.

## Fechas

| Hito | Fecha |
|---|---|
| Start | 16 jun 2026 |
| Entry deadline (aceptar reglas) | 9 ago 2026 |
| Team merger deadline | 9 ago 2026 |
| **Final submission** | **16 ago 2026** |
| Convergencia leaderboard | 17–31 ago 2026 |
| Hackathon/Strategy report | ~14 sept 2026 |

Campo: ~6.751 entrants / ~2.649 equipos. Equipos hasta 5.

## Nuestro ángulo (por qué podemos competir)

El runtime no es nuestro terreno; **el PROCESO de desarrollo sí**:
1. **Iteración rápida** (ralph/ultracode/workflows): build → self-play masivo → medir → repetir.
2. **Disciplina anti-falso-positivo = el problema central.** Con μ/σ + aleatoriedad de robo,
   distinguir "v2 es mejor" de "tuvo suerte" es el `dev_gate` + muro FR-8 del Quant. La mayoría
   del campo mirará el ELO subir y se autoengañará. Nosotros corremos A/B de self-play con N
   episodios suficientes para la σ antes de declarar mejora. **Ese es el alpha.**

## Fases

- **Fase 0 — Setup.** Join + verificación identidad (pendiente Kaggle), SDK cabt en local, pipeline
  de las ~2000 cartas, agente random-legal que pase validación y entre al ladder (μ₀=600). Loop de feedback vivo.
- **Fase 1 — Baseline heurístico + mazo decente.** Heurística por OptionType + mazo competitivo del pool.
- **Fase 2 — Búsqueda (el salto).** ISMCTS / determinized MCTS sobre el árbol de opciones legales.
  Presupuesto = 10 min por PARTIDA entera → rollouts baratos.
- **Fase 3 — Optimización conjunta deck+política** (self-play, imitación/RL) + **report del Hackathon** en paralelo.

## Estructura

```
agent/        # main.py + política (lo que va en el .tar.gz)
sdk/          # cabt engine / kaggle-environments local
experiments/  # harness de self-play, A/B con gating estadístico
data/         # pool de cartas, mazos
report/       # borrador del report del Hackathon
.venv/        # entorno python del proyecto
```

## Estado

- 21 jun: decidido competir en serio. Scaffold + venv. Verificación identidad Kaggle pendiente.
- 22 jun: investigación ultracode → `research/top8-roadmap.md` (prob. Top 8 ≈ 10-20%). Decidido: solos por
  ahora (revisar julio) + Docker linux/amd64 local. Clonado `ptcg-abc/` (repo público de un competidor serio).
- 22 jun — **2 bloqueantes externos confirmados (necesitan a Fran):**
  1. 🔴 **Verificación identidad Kaggle** (cuello raíz). Sin ella: ni motor oficial `cg-lib`, ni `EN Card
     Data.csv`, ni episodios, ni leaderboard, ni submission.
  2. 🔴 **Runtime Linux x86** — `docker` NO está instalado en el Mac. Hay que elegir: Docker Desktop / colima
     (CLI) / VM cloud. El `libcg.so` no corre en macOS/M1.
- Matiz de motores: el pip `kaggle-environments` trae un `cabt/cg` SIN `cg.api`/`all_card_data`; los agentes de
  `ptcg-abc` importan el motor **oficial `cg-lib`** (gitignored, vive en Kaggle → bloqueado por identidad).
- 22 jun — ✅ **RUNTIME RESUELTO + SMOKE TEST OK.** colima (vz+Rosetta) + Docker `linux/amd64`. `make("cabt")`
  carga `libcg.so` y corre una **partida completa** (96 pasos, rewards `[1,-1]`) con el `deck.csv` real de
  Dragapult y un agente trivial first-legal. → **El motor del pip TRAE las cartas embebidas**: podemos correr
  partidas y self-play en local YA, sin esperar a la identidad de Kaggle.
  - Cómo: `colima start --vm-type vz --vz-rosetta` · `docker build --platform=linux/amd64 -t ptcg-cabt .` ·
    `docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt python smoke_test.py`
  - **Identidad Kaggle SIGUE necesaria para:** card data legible (`EN Card Data.csv`), notebooks sample
    oficiales, replays de episodios (BC/IL), leaderboard real y SUBIR. Pero ya NO bloquea empezar a construir.
