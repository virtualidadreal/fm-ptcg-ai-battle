# Cómo continuar (handoff para la próxima sesión)

> 🆕 **25 jun: EMPEZAR POR `HANDOFF-2026-06-25.md`** (supersede el ladder; estado v2/v3 + cola KB + qué necesita Fran).
>
> Proyecto: PTCG AI Battle Challenge (Kaggle). Objetivo: Top 8 de la Strategy ($30K c/u).
> Lee primero, en este orden: `research/top8-roadmap.md` (plan maestro) → `COMPETITIONS.md` → `RULES.md` → este fichero.

## 🆕🆕🆕🆕 EMPEZAR AQUÍ — Estado 23 jun (sesión Strategy; supersede TODO lo de abajo)

**MARCO VERIFICADO EN REGLAS OFICIALES (zanjado, no re-litigar):** el premio del **Strategy NO está gated por Top-8 de Simulation.** Strategy §2.1.c solo exige competir en Simulation con el **mismo equipo** (sin rango); §3.7.a: los 8 finalistas los deciden **solo los jueces** evaluando el writeup (70/20/10). El ladder **alimenta** el 70%, no es puerta. → El plan "ladder = mantenimiento, foco = report" queda **confirmado**.

**UN REPO, DOS TRACKS (cadencia separada, no partir el código):**
- 🟢 **Track STRATEGY (primario, lo que paga):** el report. Plan completo y accionable en **`STRATEGY-PLAN.md`**. Estado: draft `report/REPORT.md` **1921 palabras (≤2000)**, 7 secciones, 0 `[PENDIENTE]`, `research/correlation.py` reproduce el Spearman −0.80. Pendiente: publicar repo enlazado (URL placeholder) + endurecer evidencia memory-only + reconciliar meta d22. **Sesión dedicada → abrir `STRATEGY-PLAN.md`.**
- 🔧 **Track SIMULATION (mantenimiento, no obsesión):** 1 cambio/día, agente estable y compliant (NO Top-8). v1 (826.9) de suelo. Cola A/B abajo. cons (mulligan) convergiendo. v3 al banco. **A1 medida INERTE → no se sube** (ablation en el report).

**Decisiones de esta sesión:** datos externos (Limitless/ELO/fusión) = **descartados** por ROI (permitidos por reglas §2.6 pero no mueven la nota); pull único Limitless solo como contingencia si la sección 6 queda floja. A1 net-prize construida pero inerte para Alakazam single-prize (atacante = 1 premio).

---

## 🆕🆕🆕 EMPEZAR AQUÍ — Estado 23 jun NOCHE (contexto previo; ver bloque de arriba primero)

**EL CAMBIO DE MARCO (lo más importante):** el ladder (Simulation) paga **$0**. El dinero y la nota están en el **REPORT (Strategy): $240K, 8 finalistas × $30K, deadline ~14 sep**, nota **70% metodología / 20% concepto mazo / 10% calidad**. → **El trabajo principal de aquí en adelante es ESCRIBIR EL REPORT.**

**POR QUÉ el report es nuestra ventaja y el ladder NO:** casi todo en el ladder es público (notebooks Kaggle); forkear lo público = un SUELO que todos alcanzan, no edge. El edge real y NO copiable = nuestra **METODOLOGÍA** (proceso Dev Aumentado, ablations honestas). Es justo el 70% de la nota.

**LADDER (23 jun):** mejor = Sabrina v1 Alakazam **826.9**. A/B: v1a (+Lillie's −Battle Cage)=581 (EMPEORÓ); cons (mulligan 34→19%) midiéndose. Score = TrueSkill **μ−3σ** → NO juzgar en horas (σ converge en días).

**AGENTES (`agents_official/`):** sabrina_v1 (826, base) · sabrina_v2 (deck top-pilot, 722, peor) · **sabrina_cons** (mulligan fix, A/B vivo) · sabrina_lethal (lethal-search, sin subir) · **🟢 sabrina_v3 (técnicas del 5º ryota re-implementadas obra propia + deck tech-suite — LISTA, 0-crash, NO subida — nuestro mejor FLOOR)** · mega_starmie_v1 (641) · sabrina_v2_ryota (ryota verbatim = solo REFERENCIA, NO subir por §3.14).

**CONCLUSIONES GRABADAS (no re-litigar):** (1) ningún señal local predice el ladder (cabt −0.80 anti-predictivo, agreement ciego, panel +0.20) → solo el ladder juzga. (2) BC/MCTS = valor de report, no de ladder (3 NO-GOs; el top es rule-based). (3) Mayor fuga = mulligan 34% (8 basics). Palancas reales = consistencia + pilotaje por matchup. (4) Edge = report + A1 net-prize (ni ryota lo hace).

**PLAN (orden próxima sesión):**
1. **Subir Sabrina v3** (floor, license-clean, citar a ryota).
2. **Leer scores convergidos** de cons (A/B #2) y v1a.
3. **🎯 ARRANCAR EL REPORT** (el trabajo de verdad): esqueleto + sección metodología con las ablations que YA tenemos (3 NO-GOs, espejismo seeds N20→N60, μ−3σ, no-señal-local triple-confirmado, fuga mulligan, ablation BC honesta). Citables: TCGplayer prize-checking, JustInBasil, Klaczynski (3x campeón mundial). Repo externo = parte del entregable (reproducibilidad fuera del límite 2000 palabras).
4. **A1 (net prize-trade)** = la única idea edge-y de ladder: un A/B barato (`− λ·prize_yield(mi_active_expuesto)` en el score de ataque cuando queda en rango de KO rival).
5. Ladder en MANTENIMIENTO: 1 cambio/día de la cola, v1/v3 de suelo, sin obsesión.

**COLA A/B** (convicción): cons (vivo) → A1 net-prize → v3 floor → champion sequencing → v1d/c/b → Mist anti-Walrein → lethal-search.

**RECURSOS:** notebooks gold en `_tmp_lb/nb/` (ryota 5º, LB950, prize-tracking-1250, kojimar, kiyotah MCTS). Doc estrategia campeones: `~/Downloads/estrategia pokemon.md` + `research/heuristicas-teoria-elite.md`. Memoria viva: `memoria-claude/proyectos/ptcg-pivote-sabrina-alakazam.md`. Reglas ya leídas (público=OSI usable; §3.14 no-verbatim).

**HONESTO sobre expectativas:** Top-8 del LADDER (corte ~1257) desde 826 es MUY difícil (gap de pilotaje vs agentes no-públicos). Donde hay opción real es el REPORT (~10-20% Top-8 con metodología diferenciada). **Foco ahí.**

---

## 🆕🆕 Estado 22 jun (NOCHE-2) — PIVOTE EJECUTADO: Dragapult → Alakazam (Sabrina v1), SUBIDA

**Decisión y ejecución (Dev Aumentado + ultracode).** Tras el NO-GO de Leon v3:
1. **Confound del budget RESUELTO:** se corrió (b) BC+ISMCTS vs Leon v1 a **budget completo (FMA_WALL_S=2.5)** → parado en **18/60 = 22% (4W/14L)**, POR DEBAJO del 40% de budget pobre. **El budget NO era el confound; la línea BC no escala.** NO-GO confirmado (ablation limpia para el report).
2. **Pivote de mazo (convergencia con la sesión paralela de selección):** Dragapult mirror está techado → **Alakazam = línea "Sabrina v1"**. Headroom de ARQUETIPO (55% WR top-tier; un Alakazam no-psychic fue 5º SIN búsqueda).
3. **Sabrina v1 construida** (`agents_official/sabrina_v1/`): fork de `ptcg-abc/agents/alakazam` (pilotaje byte-idéntico) + hardening FMA (fallback repetición-safe, `_validate_obj`, no-raising, **fix firma `agent(obs, config=None)`** que cazó el smoke). Variante base (go-first), NO mist (ladder-regresó). Verificador GO; **smoke cabt 2182 decisiones, 0 crashes/0 INVALIDs/fallback_rate 0.0**; 80% vs first-legal, 33% vs Leon v1.
4. **SUBIDA al ladder:** submission `53954688` (PENDING). Slots hoy 2/5: Leon v1 Dragapult (774.1, suelo) + Sabrina. Score real tras reset UTC 00:00.

**HONESTO:** Sabrina v1 ≈ baseline ~674, NO Dragapult-beater day-1. El headroom (674→~1014) es **pilotaje v2** (divergence mining vs pool Elo>=1150 Alakazam, `ptcg-abc/tools/replay_divergence.py`+`divergence_decode.py`). Memoria: `[[ptcg-pivote-sabrina-alakazam]]`.

**Próximos pasos:** (1) revisar score real de Sabrina tras el reset (`kaggle competitions submissions pokemon-tcg-ai-battle`); (2) si valida, **v2 = divergence mining del pilotaje**; (3) localizar el kernel del 5º (foro vía CDP, el CLI da 403); (4) re-medir meta diario (gira rápido).

---

## 🆕 Estado 22 jun (NOCHE) — Leon v3 (BC/IL) CONSTRUIDO ENTERO y validado → NO-GO

**Veredicto:** Leon v1 (sample Dragapult tuneado) **sigue de campeón**. Leon v3 (BC) NO lo bate todavía.
- **Greedy (solo policy BC):** 14% vs Leon v1 (N=150). 77% top1 offline = imitación, no calidad de juego.
- **BC prior + ISMCTS (Leon v3 final):** 40% vs Leon v1 (N=60, budget reducido 1,2s). El search ayuda (14→40) pero no basta. Net confirmada conduciendo (diag `net_evals`/`net_eval_ok_load`).
- ⚠️ Las primeras 20 dieron 65% (espejismo de seeds) → N=60 lo corrigió a 40%. NO declarar GO con N pequeño.
- Diagnóstico: la BC se entrenó de élite **mayoritariamente NO-Dragapult**; policy general pilota el mirror peor que el especialista. Detalle + landmines en `bcil/dataset/README.md` y memoria `[[ptcg-leon-v3-bcil]]`.

**Pipeline reutilizable (`bcil/`):** `extract_pairs.py` (325K pares Elo≥1150) → `encode_dataset.py` (Docker, 20 shards) → `train.py` (leon_v3.pt, top1 77%) → `agents_official/leon_v3_bc/` (greedy) + `agent_ismcts/` con net (gated `FMA_MCTS_ON=1`). Imagen `ptcg-torch` (Dockerfile.torch) para validar. A/B: `bcil/ab_json.py`.

**Siguiente (decidir):** (a) fine-tune Dragapult-only la prior; (b) test full-budget N=60 (~5h); (c) pivote a rule-based top NO-Dragapult (tareas #10/#13). Tras el NO-GO, el ROI quizá NO es el mirror Dragapult.

## 🎬 Replay Visualizer (vías 1 y 2)

Visor de partidas en `tools/replay-visualizer/` (README ahí). Dos vías:

- **Vía 1 (nativa, sin Docker)** — renderiza un episodio existente de `data/episodes/`.
  ```bash
  /Users/franmilla/FMA/proyectos/ptcg-ai-battle/.venv/bin/python \
    /Users/franmilla/FMA/proyectos/ptcg-ai-battle/tools/replay-visualizer/render_episode.py \
    [EPISODE_JSON] [-o salida.html]
  ```
- **Vía 2 (simulación real, Docker linux/amd64 + colima)** — simula una partida entre dos agentes y la renderiza.
  ```bash
  docker run --platform=linux/amd64 --rm -e AGENT0=rule -e AGENT1=rule \
    -v "/Users/franmilla/FMA/proyectos/ptcg-ai-battle":/work -w /work \
    ptcg-cabt python tools/replay-visualizer/sim/simulate_battle.py
  ```
  `AGENT0`/`AGENT1` = `random|rule|mcts|ucb`. Genera `sim_steps.json` + `replay_sim.html`.

Estado: vía 1 nativa OK, vía 2 Docker OK (partida verificada de 173 steps, rule vs rule, fin en resultado).

## 🆕 Estado a 22 jun 2026 (TARDE) — FASE 1 arrancada (ultracode)

**Hecho y VALIDADO en docker:**
- ✅ **Contrato del motor verificado EMPÍRICAMENTE** (no solo de la doc). El env `cabt` del paquete pip
  `kaggle_environments` corre **OFFLINE sin identidad Kaggle**. La forma REAL del `obs` DICT está documentada en
  `agent/main.py` (cabecera) e `introspect.py`. Clave: `option["type"]` y `select["context"]` son **ints**;
  `cg.api`/`all_card_data` (lo que usa el competidor) **NO existe offline** → nuestro agente es **dict-only**.
- ✅ **Agente robusto** en `agent/main.py` + `agent/deck.csv` (= mazo consenso Dragapult ex). Scaffolding propio:
  try/except global + doble red, carga de deck cwd-independiente, `normalize_selection`/`_legal_fallback`
  REPETICIÓN-SAFE (por si `minCount>#options`), re-validación de conteo/rango, watchdog turnActionCount/tiempo,
  heurística estructural por context+OptionType. **0 crashes / 0 INVALIDs en ~12.000 decisiones** (self-check
  25 partidas + probe 30 + integración 40). fallback_rate 0.0.
- ✅ **Harness A/B** en `experiments/ab_harness.py` + baselines (`baselines/random`, `baselines/firstlegal`):
  alternancia de asiento, IC de Wilson, TrueSkill, modo `--panel`, chequeo deck-phase FATAL, y un **WARNING
  prominente "local≠ladder"** (es FILTRO, no juez). Pasada adversarial del verificador + 5 fixes aplicados.

**🔴 HALLAZGO HONESTO (no es éxito, es señal):** la heurística estructural **PIERDE contra first-legal**
(7W/13L = **35%** [Wilson 18-57]) y queda **par contra random** (10/10 = 50%); TrueSkill por debajo de ambos.
La regla "haz todo el setup y ataca al final" es **contraproducente sin conocimiento de cartas** (atacamos
tarde, malgastamos tempo adjuntando/evolucionando a ciegas). Esto CONFIRMA la lección §4 del roadmap: un
"smart" clunky rinde PEOR que un rule-based limpio. **El suelo de SUPERVIVENCIA (0 crashes) está; el suelo de
CALIDAD de juego, NO.**

**Próximo paso REAL (revisado por el hallazgo):**
1. **Empujar identidad Kaggle** (sigue siendo el cuello). Sin card data no podemos hacer una heurística que
   supere a first-legal de forma fiable, ni adoptar el sample oficial (que batió 13-1 a un policy from-scratch).
2. Mientras tanto, A/B baratos de hipótesis dict-only: **¿"atacar ASAP" bate a "setup-first"?** ¿bajar la
   prioridad de ABILITY/ATTACH ayuda? Usar el harness para descartar reglas malas (recordando que el local NO
   predice el ladder: es filtro).
3. Cuando llegue identidad: adoptar el **sample oficial Dragapult** envuelto en NUESTRO scaffolding robusto
   (la jugada del competidor) como suelo de calidad, y ahí sí construir la heurística/ISMCTS por encima.

Ficheros nuevos: `agent/main.py`, `agent/deck.csv`, `agent/_selfcheck.py`, `experiments/ab_harness.py`,
`experiments/baselines/*`, `introspect.py`, `experiments/_probe.py`, `experiments/_integration.log` (artefactos).

## Estado a 22 jun 2026 (qué está hecho)

- ✅ **Investigación completa** → `research/top8-roadmap.md` (11 secciones; prob. Top 8 ≈ 10-20%).
- ✅ **Runtime Linux funcionando** (colima vz+Rosetta + Docker linux/amd64). Smoke test OK: el motor `cabt`
  carga y juega una partida completa con un `deck.csv` real, **sin necesitar identidad Kaggle**.
- ✅ **Repo competidor clonado y estudiado**: `ptcg-abc/` (meta vivo, harness A/B, enums del motor, lecciones).
- ✅ Docs base: `README.md`, `RULES.md`, `COMPETITIONS.md`, `data/DATASET.md`. Memoria FMA actualizada.

## Decisiones ya tomadas

- Competir **EN SERIO** (objetivo Top 8). Código vive **dentro de FMA** en `proyectos/ptcg-ai-battle/`.
- Equipo: **solos por ahora**, revisar reclutamiento en julio (antes del merger 9 ago).
  → Reframe: el fichaje de mayor ROI quizá sea **un jugador competitivo de PTCG** (gap de dominio), no un ML-ero.
- Runtime: **colima (vz+Rosetta) + Docker linux/amd64** (decidido y montado).
- Plan técnico: Fase 0+1 robustas → apostar **ISMCTS** (corazón del 70%) con **checkpoint semana 5** → si no,
  pivotar a **BC/IL** desde replays. RL self-play y CFR descartados del camino crítico.

## Cómo levantar el entorno (cada sesión)

```bash
export PATH="/opt/homebrew/bin:$PATH"
colima status || colima start --vm-type vz --vz-rosetta --cpu 4 --memory 6 --disk 40
cd /Users/franmilla/FMA/proyectos/ptcg-ai-battle
docker build --platform=linux/amd64 -t ptcg-cabt .          # solo si cambió el Dockerfile
docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt python smoke_test.py   # verificar motor
```
Notas del setup (ya resuelto, por si hay que rehacerlo en otra máquina): hace falta `brew install colima docker
qemu lima-additional-guestagents`. NO usar `colima --arch x86_64` (VM QEMU pura falla por red y es lentísima);
usar **vz+Rosetta** y contenedores `--platform=linux/amd64`.

## ✅ Kaggle DESBLOQUEADO (22 jun TARDE)

- **Identidad + API token operativos.** Token nuevo formato `KGAT_...` en `~/.kaggle/access_token` (chmod 600).
  CLI: `/Users/franmilla/FMA/proyectos/ptcg-ai-battle/.venv/bin/kaggle`. Reglas de las 2 comps YA aceptadas
  (`userHasEntered: True`). Token en foto del escritorio de Fran; conviene apuntarlo en `_privado/credenciales.md`.
- **Competition data descargado** a `data/competition/` (GITIGNORED, material oficial no redistribuible):
  `EN_Card_Data.csv` (card data: por carta+ataque → HP/tipo/debilidad/resistencia/coste/**daño**/efecto),
  el módulo **`cg/`** completo (`api.py`+`game.py`+`sim.py`+`utils.py`) y **`libcg.so`** (1.3MB), + el sample
  submission oficial (`main.py`+`deck.csv`).
- ⚠️ **El sample oficial `main.py` es RANDOM puro** (`random.sample`), solo el esqueleto. El sample TUNEADO
  Dragapult (el que bate 13-1) es un NOTEBOOK público aparte → buscar con `kaggle kernels list -s dragapult`.
- Pendiente aún (no bloqueante): episodios/replays (BC/IL, ~720MB/día) y leaderboard real.

## 🧪 Resultado A/B de hipótesis "atacar pronto vs setup-first" (22 jun, motor offline)

Refutada mi hipótesis inicial. Contra **first-legal**: `attack_asap` (ATTACK máx) = **13%**, `attack_mid` = **17%**,
`setup-first` (el agente actual) = **35%**. O sea **atacar pronto EMPEORA**; más setup = menos malo. PERO las
variantes de ataque SÍ baten a nuestro setup-first (~73-77%) y a random. Lección dura: **TODAS las heurísticas
estructurales dict-only (sin card data) pierden a first-legal** → el camino NO es afinar prioridades a ciegas,
es **meter card data** (ya descargado) o **adoptar el sample tuneado**. Generador en `experiments/gen_variants.py`,
log en `experiments/_hypothesis.log`.

## 🔬 FASE 2 — ISMCTS: resultado (22 jun, ultracode)

**Hallazgo que cambia el roadmap:** el binding de búsqueda NO es la tarea imposible que se temía — `cg/api.py`
oficial YA lo trae (`search_begin/step/end/release` sobre `libcg.so`), con plantilla MCTS en el notebook
`kiyotah/...mcts-sample-code`. Lo construimos y VALIDAMOS en `agent_ismcts/`: ISMCTS determinizado completo,
watchdog de tiempo, `search_release` (sin leaks), fallback a policy. Microbench: `search_step` ~0.4ms; peor
partida ~8s (límite 600s) → tiempo NO es problema. Verificador: sin críticos, robusto.

**PERO la búsqueda con eval ESTÁTICA va CIEGA: no mejora, EMPEORA** (0W/15L vs el sample, peor que first-legal).
Causa: un turno PTCG es una cadena larga de micro-decisiones propias donde la eval estática (premios) apenas se
mueve hasta resolver un ataque → sin señal por nodo + priors débiles → la búsqueda reparte a ciegas y sustituye
jugadas afinadas por peores. Es justo por qué el kernel oficial empareja MCTS con un Transformer value/policy
ENTRENADO. **Confirma empíricamente la tesis del roadmap: ISMCTS necesita eval/policy APRENDIDA.** (Gran ablation
honesta para el report 70%.)

**Entregado:** `agent_ismcts/` se ejecuta POLICY-DRIVEN por defecto (= sample Dragapult robusto, paridad ~73% vs
sample / 80% vs firstlegal). El ISMCTS queda implementado y se activa con `FMA_MCTS_ON=1` → es el HUECO donde
enchufar la eval aprendida en Fase 3. **NO subir:** es paridad con el campeón ya en el ladder (redundante, gastaría
envío). **Siguiente salto real = BC/IL (eval aprendida) = Leon v3.**

## 🧠 BC/IL (Leon v3) — ARRANCADO, plan completo en `bcil/PLAN-MODELO-BC.md`
Datos confirmados (episodios diarios ~750MB, 5-7,8k partidas, top Elo ~1325). Parser obs→acción VALIDADO
(`bcil/extract_pairs.py`: 35K pares/día pequeño, formato same_step). Falta: dataset de calidad (días 18-21 +
filtro Elo≥1150) → encoding (reusar el del notebook MCTS oficial) → policy net ligera (torch, inferencia CPU) →
validar greedy vs Leon v1 + panel → integrar al ISMCTS. **Nombres/versionado en `AGENTS.md`** (Leon v1 campeón /
v2 search en banco / v3 en desarrollo). Instrucción de arranque al final de `bcil/PLAN-MODELO-BC.md`.

## 🏆 FASE 1b — resultados (22 jun, Kaggle ya desbloqueado)

Dos líneas construidas y validadas en docker (cabt local = FILTRO, no juez):
- **`agents_official/dragapult_sample/` = NUESTRO MEJOR AGENTE (suelo de calidad).** Sample oficial tuneado
  (`kiyotah/...dragapult`) envuelto en scaffolding robusto + su `cg/` (con libcg.so). **85% vs first-legal,
  95% vs agent_v2.** Lógica real (Phantom Dive multi-KO, conteo de premios). 0 crashes/0 fallbacks. → CANDIDATO
  Nº1 a SUBIR. Tar = `main.py + deck.csv + cg/` (excluir __pycache__).
- **`agent_v2/` (heurística dict-only con card data, `cards.json` de 1267 cartas).** Aplasta al agente ciego
  (~80%) → **el card data SÍ aporta valor medible**. PERO pierde a first-legal (~22-27%, no le gana). En espejo
  no hay edge de cartas que explotar y el greedy de first-legal es fuerte (el motor lista best-first). Tar =
  `main.py + deck.csv + cards.json`. ⚠️ docstring corregido para no inflar (no es "competitivo con first-legal").
- **Gotcha submit:** `get_last_callable` carga la ÚLTIMA función top-level → `agent` debe ser la última definida.
- **Hallazgo a re-medir:** ir SEGUNDO podría ser mejor (GO_FIRST=False), pero la sonda fue de solo 20 juegos
  (sub-muestreada, el verificador lo marcó). Re-medir con >=100 juegos antes de fiarse.

**✅ SUBIDO 22 jun:** sample Dragapult en el ladder, id `53940465`, status COMPLETE (validó limpio), score
inicial 600.0 (placeholder μ₀; el real llega tras el reset UTC 00:00 / TW 08:00). Pipeline de submit confirmado.
- **REVISAR score real:** `.venv/bin/kaggle competitions submissions pokemon-tcg-ai-battle` y
  `.venv/bin/kaggle competitions leaderboard pokemon-tcg-ai-battle -s`. Es el PRIMER dato del juez real → dice
  cuánto miente el local (85% local vs first-legal no garantiza nada arriba). Quedan 4/5 envíos hoy.

**Siguiente:** (1) ✅ subido. (2) FASE 2: ISMCTS sobre ese suelo usando el `kiyotah/...mcts-sample-code` + la
evaluación de cartas de agent_v2 como heurística de rollout. (3) Panel de oponentes con los samples oficiales
(Lucario/Iono/Abomasnow). (4) Leer foro vía CDP (diffs reglas, fórmula leaderboard).

## 📚 Código público útil de la competición (revisado 22 jun, vía `kaggle kernels list`)

ORO: **`kiyotah/reinforcement-learning-and-mcts-sample-code`** (420 votos) = sample OFICIAL de MCTS/RL →
base directa para Fase 2 (ISMCTS, el 70% del report, "la tarea más dura"). ESTUDIAR a fondo.
PANEL DE OPONENTES (samples oficiales del host kiyotah, por arquetipo): `a-sample-rule-based-agent-`
**mega-lucario-ex** (437), **iono-s** (86), **mega-abomasnow-ex** (55), dragapult-ex (ya adoptado) →
montarlos como rivales del harness para anclar el A/B al meta (deja de ser self-play en vacío, §6).
TECHO rule-based: `ryotasueyoshi/rule-based-not-psychic-alakazam-best-5th` (5º del ladder SIN búsqueda),
`romanrozen/strong-start-baseline-agent-v10-lb-950` (LB 950+). Referencia heurística: `avikdas567/...heuristic-agent-data-pipeline`.
HERRAMIENTAS (diagnóstico): visores de replay `shiiin9/battle-replay-visualizer`, `kiyotah/how-to-output-local-battle-as-json`;
meta EDA `makimakiai/ptcg-official-top-episodes-detailed-eda`. Descargar kernel: `kaggle kernels pull <ref> -p <dir>`.

## 🔭 TODO: leer la pestaña Discussion del foro vía CDP (Chrome logueado)

El foro de Kaggle es SPA + requiere sesión: WebFetch solo ve el shell (5,6 KB), el `.json` igual, el CLI/token
NO cubren discussions, y `agent-browser` no está instalado. Vía robusta acordada (mismo patrón CDP:9222 que el
[[tradingview-mcp-extraccion-senales]]):
1. Cerrar Chrome (lock de perfil) o usar perfil dedicado: `"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
   --remote-debugging-port=9222 --user-data-dir="$HOME/.chrome-cdp-kaggle"` y loguearse en Kaggle UNA vez en ese perfil.
2. Conectar por CDP (websocket a `http://localhost:9222/json`), navegar a
   `https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion?sort=hotness`, esperar render, y extraer
   por JS los hilos (título + href + votos). ~4 páginas.
3. Para cada hilo jugoso, abrir su URL y volcar el DOM. OBJETIVO prioritario: (1) diferencias simulador vs reglas
   oficiales, (2) fórmula exacta del leaderboard (μ−kσ), (3) hallazgos de MCTS/búsqueda, (4) lecturas del meta.

## Próximo paso de trabajo: FASE 1 (cuando se retome)

1. **Agente propio con scaffolding robusto** en `agent/` (NO copiar el del competidor; usarlo solo de referencia):
   - `agent(obs) -> list[int]` con: carga de `deck.csv` cwd-independiente, `try/except` global con
     `_legal_fallback` (nunca crashear), respeto de `minCount/maxCount`, watchdog de tiempo.
   - Empezar por "first-legal" robusto (ya validado en `smoke_test.py`) → evolucionar a heurística por
     `SelectContext`/`OptionType` (enums en `ptcg-abc/CLAUDE.md` líneas 60-65).
2. **Harness A/B local** en `experiments/` (referencia: `ptcg-abc/tools/cabt_eval.py` y `cabt_ab.py`):
   - Correr N partidas entre dos agentes, panel de rivales diverso (mazos de `ptcg-abc/agents/*/deck.csv`).
   - `pip install trueskill`, IC sobre la diferencia de μ. **Recordar §6/§11.3: el local NO predice el ladder**
     → validar correlación con ladder antes de fiarse; el local es filtro, no juez.
3. **Diseño de mazo**: arrancar con un sample/consenso (Dragapult ex) como suelo; el "concepto" propio para el
   20% se trabaja con conocimiento de dominio (ver decisión de reclutamiento).

## Cuando llegue la identidad Kaggle

- Descargar competition data (Kaggle MCP `https://www.kaggle.com/mcp` → `mcp_kaggle_download_competition_data_files`,
  o CLI) → `EN Card Data.csv`, notebooks sample, motor oficial `cg-lib`.
- Montar pipeline de **descarga diaria de episodios** top-rated (para BC/IL y análisis de meta) — comandos en
  `ptcg-abc/CLAUDE.md` líneas 47-55.
- Leer la página **"differences from official rules"** del simulador (sigue sin verificar).
- Confirmar en Kaggle logueado: fórmula del leaderboard (μ−kσ), idioma/formato/deadline real del report,
  montos de premios, regla de copias por carta, regulaciones del pool (G/H/I/J → cambia el meta/mazo).
- Subir el primer agente robusto al ladder (5/día, cuentan los 2 últimos; ver playbook §6).

## Fechas

Final submission del agente **16 ago** · convergencia ladder 17-31 ago · **report Strategy ~13-14 sept** ·
Final presencial en Tokio (sept). Merger de equipo **9 ago**.

## Aviso de contexto

Esto choca con el bloque exclusivo HA (foco hasta 17 sept). Fran lo asumió a sabiendas. Cada sesión aquí sale
de ese bloque — mantener el coste a la vista.
