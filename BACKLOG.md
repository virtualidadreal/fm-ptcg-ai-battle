# PTCG AI Battle — Backlog (ideas/recursos a desarrollar o ejecutar)

> Destilado de los recursos públicos de la competición (`kaggle kernels list`) + el roadmap. Priorizado.
> Estado: 🟢 hecho · 🟡 en curso · ⬜ pendiente. Detalle de recursos en `NEXT-SESSION.md`.

## Método / agente (el 70% del report — máximo valor)
- 🟢 **Fase 2: ISMCTS construido y validado** (`agent_ismcts/`, binding oficial + watchdog + sin leaks). VEREDICTO:
  la búsqueda con eval ESTÁTICA va ciega (0/15 vs sample, EMPEORA). Necesita eval APRENDIDA → activable `FMA_MCTS_ON=1`.
  Entregado policy-driven (paridad con el campeón). NO subido (redundante). Es el hueco para la eval de Fase 3.
- 🔜 **Plan B = AHORA el plan A del 70%: BC/IL** (eval/policy aprendida) — ver sección Método abajo (#12). Es el
  único camino que hace rentable la búsqueda (confirmado empíricamente en Fase 2).
- ⬜ **Belief/opponent modeling informado** en `search_begin`: determinizar el rival con el META real
  (Dragapult/Trevenant/Alakazam consenso) en vez del relleno tonto del sample. Es el corazón del "decision making
  bajo info imperfecta" que premia el jurado. Depende de Fase 2.
- ⬜ **Plan B del 70%: BC/IL desde replays top-rated** → policy/value net ligera (inferencia CPU, sin deps pesadas).
  Base: el notebook oficial `kiyotah/reinforcement-learning-and-mcts-sample-code` (Transformer + Search API).
  Checkpoint roadmap: si ISMCTS no rinde en semana 5, pivotar aquí.

## Inteligencia / verificar (rápidas, alto valor)
- ⬜ **Leer foro Discussion vía CDP** (Chrome logueado): diffs simulador vs reglas oficiales, fórmula EXACTA del
  leaderboard (μ−kσ, el `k`), idioma/formato/deadline real del report, premios, regla de copias por carta,
  regulaciones del pool (G/H/I/J → define el meta). Pasos en NEXT-SESSION. [tarea #6]
- ⬜ **Estudiar agentes de referencia top** (extraer reglas/ideas de pilotaje):
  `ryotasueyoshi/rule-based-not-psychic-alakazam-best-5th` (rule-based 5º del ladder SIN búsqueda = techo
  rule-based) y `romanrozen/strong-start-baseline-agent-v10-lb-950` (LB 950+).

## Harness / evaluación (infraestructura que multiplica)
- ⬜ **Panel de oponentes con samples oficiales** (`kiyotah/...mega-lucario`, `...iono-s`, `...mega-abomasnow`)
  en el harness → anclar el A/B al META real en vez de self-play en vacío (§6: el local engaña). Alta prioridad.
- ⬜ **Pipeline de descarga diaria de episodios** + EDA del meta (referencia `makimakiai/ptcg-official-top-episodes-
  detailed-eda`): qué juega el top del ladder, datos para BC/IL, re-evaluar el mazo antes de congelar (16 ago).
- ⬜ **Visor de replays** para diagnosticar derrotas concretas (qué decisión nos hunde): `shiiin9/battle-replay-
  visualizer` y `kiyotah/how-to-output-local-battle-as-json`. Útil cuando una versión flojee.
- ⬜ (menor) **Vistazo a `avikdas567/...heuristic-agent-data-pipeline`** por ideas para la heurística con card data.

## Operativa del ladder
- 🟢 Primer agente subido (sample Dragapult) — en el ladder, ganando. Cómo subir → [[ptcg-ladder-como-subir]].
- ⬜ **Disciplina de slots:** mantener SIEMPRE el campeón validado como uno de los 2 activos; subir candidatos solo
  tras pasar el filtro local + A/B. 5 envíos/día, cuentan los 2 últimos.
