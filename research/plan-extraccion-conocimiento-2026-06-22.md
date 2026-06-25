# Plan de extracción de conocimiento → edge en el agente (2026-06-22)

> Objetivo: convertir TODO el conocimiento de "cómo ganar partidas" en cosas que el agente
> offline pueda ejecutar (reward, priors, belief, reglas), priorizado por leverage real.
> Contexto: Leon v1 (sample Dragapult tuneado) = campeón. BC general (Leon v3) = NO-GO (40%).
> Diagnóstico: falta conocimiento ESPECIALISTA encodeado, no más teoría genérica.

## Principio rector

El conocimiento solo da edge si entra por una de estas 4 puertas (el agente no "consulta" nada en runtime):
1. **Reward** — qué es ganar (intercambio neto de premios, no KOs ni setup).
2. **Priors / reglas** — qué jugada probar primero (sequencing, roles).
3. **Belief state** — qué cree el agente de lo oculto (prized cards, mano rival).
4. **Eval aprendida** — BC/IL que ejecuta lo anterior mejor que reglas crudas.

Todo lo que no entre por una de esas 4 puertas es bibliografía para Fran, no edge para el agente.

---

## BLOQUE A — Conocimiento estratégico (destilar fuentes → spec encodeable)

### A1 · Destilar la sección 6 del doc a spec de 4 módulos  ⬜ ALTA
- **Sacamos:** prize-trade math (2-2-2), prize-checking probabilístico, sequencing (max info / min compromiso / negar info), identificación de rol (beatdown vs control).
- **De dónde:** `Downloads/estrategia pokemon.md` §6 + fuentes citadas (TCGplayer "3 Principles of Prize Checking" = la mate exacta; TCG Protectors prize-mapping; JustInBasil roles).
- **Se convierte en:** `research/heuristicas-teoria-elite.md` con cada concepto traducido a (a) fórmula/regla, (b) puerta de entrada (reward/prior/belief), (c) datos que necesita.
- **Verifica:** que cada regla sea computable con la card data que tenemos (si no, va a Bloque B).

### A2 · Extraer reglas de los agentes top PÚBLICOS (atajo de máximo ROI)  ⬜ ALTA
- **Sacamos:** las reglas de pilotaje que YA ganan, destiladas por otros humanos. Esto es conocimiento ganador pre-encodeado.
- **De dónde:** `ryotasueyoshi/rule-based-not-psychic-alakazam-best-5th` (techo rule-based, 5º del ladder SIN búsqueda) y `romanrozen/strong-start-baseline-agent-v10-lb-950`.
- **Se convierte en:** tabla de reglas en `research/heuristicas-teoria-elite.md` (sección "reglas observadas en agentes ganadores") + diff contra nuestra heurística actual.
- **Verifica:** A/B de sus reglas portadas vs Leon v1 en el panel meta (Bloque B3).
- **Nota:** esto es probablemente MÁS rentable que la teoría abstracta — es teoría ya aterrizada al cabt Engine concreto.

### A3 · Inteligencia del foro Discussion (vía CDP, Chrome logueado)  ⬜ MEDIA
- **Sacamos:** fórmula EXACTA del leaderboard (μ−kσ, valor de `k`), regla de copias por carta, regulaciones del pool (G/H/I/J → define qué meta es legal), diffs simulador vs reglas oficiales, idioma/formato/deadline del report.
- **De dónde:** foro Discussion de ambas competiciones.
- **Se convierte en:** actualización de `RULES.md` + ajuste de qué reglas de A1/A2 son legales.
- **Verifica:** cruzar con el comportamiento empírico del motor.

---

## BLOQUE B — Datos para que el conocimiento sea computable

### B1 · Auditar y completar la card data del pool  ⬜ ALTA (precondición de A1)
- **Sacamos:** por cada carta del pool — premios que da al caer (1/2/3), HP, coste de retirada, ataques/daño, habilidades.
- **De dónde:** `agent_v2/cards.json` (auditar cobertura) + `build_cards.py`. Si incompleto, completar con identidad Kaggle (card data legible / notebooks sample).
- **Se convierte en:** tabla de premios y stats que la reward de prize-trade consume.
- **Verifica:** % de cartas del pool con datos completos; prize-trade es incomputable sin esto.
- **🔴 Bloqueante raíz si falta:** sin premios-por-carta, A1 entero se cae.

### B2 · Replays top-rated FILTRADOS al mirror Dragapult  ⬜ ALTA
- **Sacamos:** secuencias de juego de élite ESPECÍFICAS de Dragapult (no la mezcla general que hundió a Leon v3).
- **De dónde:** pipeline de descarga de episodios (`makimakiai/...top-episodes-eda`), filtrar por mazo Dragapult y Elo≥1150.
- **Se convierte en:** dataset de fine-tune especialista para la opción (a) ya identificada en NEXT-SESSION (fine-tune Dragapult-only la prior BC).
- **Verifica:** top1 offline del mirror + A/B real (no declarar GO con N<60, lección Leon v3).

### B3 · Panel de oponentes con samples oficiales (meta real)  ⬜ ALTA
- **Sacamos:** rivales que representan el meta (Mega Lucario, Iono-s, Mega Abomasnow, etc.).
- **De dónde:** kernels oficiales `kiyotah/...mega-lucario`, `...iono-s`, `...mega-abomasnow`.
- **Se convierte en:** modo `--panel` del harness anclado al meta en vez de self-play en vacío (§6: el local engaña).
- **Verifica:** que el A/B contra panel correlacione mejor con el ladder que el self-play (medirlo).

---

## BLOQUE C — Encodear y verificar (donde el conocimiento se vuelve edge)

### C1 · Inyectar prize-trade + sequencing en Leon v1 (rule-based campeón)  ⬜ ALTA
- **Hace:** Leon v1.1 = el campeón actual + reward/regla de intercambio neto de premios + priors de sequencing (draw-before-search, retrasa lo irreversible, atacar cuando el prize-map lo pide).
- **Por qué primero:** es el camino más barato y el doc lo valida (rule-based 5º existe). No necesita ML.
- **Depende de:** A1 + A2 + B1.
- **Verifica:** A/B contra Leon v1 y contra panel meta (B3). Gating disciplinado.

### C2 · Belief de prized cards en search_begin  ⬜ MEDIA
- **Hace:** mantener distribución sobre cartas premiadas propias + determinizar al rival con el meta real (no relleno tonto del sample). Es el núcleo de "decisión bajo info imperfecta" que premia el jurado.
- **Depende de:** B1 (qué cartas faltan) + C1.
- **Verifica:** mejora medible en el mirror; impacto en el report (narrativa Strategy).

### C3 · Fine-tune BC Dragapult-only (rescate de Leon v3)  ⬜ MEDIA
- **Hace:** re-entrena la prior BC solo con el mirror (B2) para arreglar el NO-GO diagnosticado (BC general pilota mal el mirror).
- **Depende de:** B2.
- **Verifica:** ¿bate a Leon v1.1? Si tras esto sigue NO-GO → el ROI del mirror Dragapult está agotado y se pivota a un mazo rule-based no-Dragapult (tareas #10/#13 del backlog).

---

## Orden de ejecución (ruta crítica)

1. **B1** (auditar card data) — precondición, barato. Si falta → empujar identidad Kaggle.
2. **A1 + A2** en paralelo (destilar teoría + reglas de agentes top) → `heuristicas-teoria-elite.md`.
3. **B3** (panel meta) — para poder verificar honesto.
4. **C1** (inyectar en Leon v1) → primer intento de edge real, A/B contra panel.
5. **A3** (foro) — en paralelo, ajusta legalidad.
6. Según C1: si no basta → **B2 + C3** (fine-tune especialista). Si C3 tampoco → pivote de mazo.

## Regla de disciplina (no repetir el espejismo Leon v3)

- Ningún GO con N<60. Las primeras 20 partidas mienten (65%→40% fue real).
- El A/B local es FILTRO, no juez. El ground truth es el ladder.
- Mantener SIEMPRE el campeón validado como uno de los 2 slots activos.

## Qué NO sacamos (descartado explícito)

- Canales YouTube / coaching / PokéBeach Premium: aprendizaje humano, ROI nulo para el agente offline.
- Cifras de meta share/win-rate del doc: caducan + pool Kaggle ≠ Standard. Solo confirman el sample Dragapult (ya hecho).
- Más teoría estratégica: la sección 6 es el conjunto completo. Buscar más es procrastinar sobre lo difícil (encodear + card data).
