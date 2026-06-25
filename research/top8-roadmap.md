# PTCG AI Battle Challenge — Roadmap a Top 8 (documento maestro)

> Síntesis de 5 investigaciones + 2 pasadas adversariales de verificación.
> Fecha: 22 jun 2026. Estado del campo: ~6.751 entrants / ~2.649 equipos, comp arrancada 16 jun.
> Convención: **[HECHO]** = verificado contra código/doc/URL. **[SUPOSICIÓN]** = inferencia no confirmada.
> **[REFUTADO]** = el campo o la verificación lo contradice.

---

## 1. Resumen ejecutivo

El dinero está en la **Strategy** (Top 8 → $30K c/u + final en Tokio), no en el ladder de la Simulation
(sin premio). La nota de la Strategy es **70% método de decisión del agente / 20% concepto de mazo / 10%
calidad del report**, así que un buen REPORT con método real pesa más que un ELO alto. Eso favorece nuestro
perfil... **pero solo si el método existe de verdad**, no como vocabulario decorativo.

**Probabilidad realista de Top 8, ya filtrada por los verificadores: 10–20%.** Las dos pasadas convergen
en "baja-media, fuertemente condicionada". A favor: el premio está en el método, no en el rating puro;
existe un activo público de oro (repo `wmh/ptcg-abc`) que ahorra semanas; hay samples oficiales tuned
(Dragapult ex) que dan un suelo competente. En contra, todo verificado: (a) campo elite (HEROZ shogi-AI +
Matsuo + japoneses ya iterando A/B en ladder al 5º día) por solo 8 plazas; (b) Fran parte de **cero en
game-AI** y el componente que da el 70% (ISMCTS sobre un binario cuyo wrapper de búsqueda **nadie ha hecho**)
es la tarea más dura del proyecto; (c) nuestra tesis diferenciadora original (self-play masivo + gating)
está **parcialmente refutada por el propio campo**: `wmh/ptcg-abc` documenta que *"local sims NO predicen el
ladder rank"*; (d) tres bloqueantes de Fase 0 (identidad Kaggle, Linux x86, wrapper ctypes de búsqueda)
siguen sin resolver con calendario corto.

El escenario realista de Top 8 NO es "ganar el ladder", es: **agente estable y honesto + mazo defendible +
un report con un MÉTODO REAL implementado y evaluado con rigor**. Si el wrapper de búsqueda no se logra, el
techo es rule-based limpio + report honesto, que probablemente **no entra** frente a equipos con búsqueda/IL real.

---

## 2. Cómo funciona la comp y el camino al dinero

Una sola cosa repartida en **dos competiciones Kaggle conectadas**; hay que entrar en las dos. [HECHO, COMPETITIONS.md]

- **Simulation** (`pokemon-tcg-ai-battle`): el motor de puntuación. Subes `.tar.gz` (`main.py` top-level +
  `deck.csv`), juega en un ladder con rating gaussiano **N(μ,σ²), μ₀=600**. **Sin premio** (medallas/posición).
- **Strategy/Hackathon** (`pokemon-tcg-ai-battle-challenge-strategy`): el dinero. Un **REPORT ≤2.000 palabras**,
  1 por equipo. La nota pondera **70% enfoque del modelo / 20% concepto de mazo / 10% calidad**. El rendimiento
  en la Simulation alimenta la valoración, pero el grueso es la metodología. [HECHO, COMPETITIONS.md + note.com/AICU]

**El ladder (cómo sube el rating).** TrueSkill gaussiano. **μ = skill** (sube con W, baja con L); **σ =
incertidumbre** (baja jugando muchas partidas). El leaderboard ordena combinando ambos de forma conservadora
(**[SUPOSICIÓN]** típicamente μ−3σ o μ−2σ; **no confirmado**, requiere login). **El margen de victoria NO cuenta**:
solo W/D/L. Solo se trackean **los 2 últimos** submissions activos: subir un agente peor desplaza a tu campeón
y te hunde mientras reconverge. [HECHO, RULES.md + docs Kaggle simulation]

**El dinero (confirmar en pestaña Prizes logueado).** [SUPOSICIÓN fuerte, fuentes secundarias COMPETITIONS.md]
- Strategy Top 8 equipos → **$30.000 cash c/u** + pase a la final.
- Final presencial en Tokio (sept), torneo en vivo con los 8 agentes ya congelados (no se itera):
  1º **+$50K**, 2º **+$30K**. Todos los finalistas: $3.000/persona en créditos Google Cloud.

**Calendario (de la Timeline oficial, RULES.md).** Start 16 jun · Entry+merger deadline 9 ago ·
**Final submission del agente 16 ago** · convergencia leaderboard 17–31 ago · **report Strategy ~14 sept**.
⚠️ El deadline del report (~14 sept JST) está **confirmado solo por fuentes secundarias** (note.com/AICU),
NO por la pestaña Rules logueada. Tratar como no-confirmado hasta verificar. [REFUTADO como hecho duro]

---

## 3. La interfaz del motor (lo que el equipo necesita para programar)

Motor **cabt**: librería C/C++ nativa (`libcg.so` / `cg.dll`, ~1.3 MB) envuelta en Python por ctypes en
`kaggle_environments/envs/cabt/`. Toda la lógica vive en el binario; Python solo serializa JSON. [HECHO, código local]

### Contrato del agente
```python
def agent(obs: dict) -> list[int]:
    if obs["select"] is None:        # arranque: devuelve el mazo
        return deck_60_card_ids       # 60 IDs; len != 60 => INVALID => derrota
    sel = obs["select"]
    # devuelve entre sel["minCount"] y sel["maxCount"] ÍNDICES del array sel["option"]
    return [chosen_indices]
```
El motor **solo ofrece jugadas legales** en `option`. PERO devolver mal el conteo/rango => `battle_select`
lanza excepción => `interpreter` marca **INVALID => reward −1 (derrota inmediata)**. La legalidad de las
opciones NO protege del conteo. Validar SIEMPRE `len` y rango. [HECHO, cabt.py try/except]

### `obs` (observación viva): 4 campos top-level
`select` (SelectData|None), `logs` (list[Log]), `current` (State|None), `search_begin_input` (str|None).
Al terminar la partida los 4 → None/[]. [HECHO, cabt.py L184-187]
⚠️ **MATIZ no recogido en findings:** `finish()` hace `obs.pop("search_begin_input")` al serializar replays.
→ **los episodios exportados para BC pueden NO contener `search_begin_input`.** Verificar antes de basar
nada de BC en ese campo. [HECHO]

### Estructuras clave (de api.html, [HECHO])
- **State (`current`):** `turn, turnActionCount, yourIndex, firstPlayer, supporterPlayed, stadiumPlayed,
  energyAttached, retreated, result, stadium, looking, players[2]`. `result`: **−1 en curso, 0 gana p0,
  1 gana p1, 2 empate** (verificado en cabt.py). `yourIndex` te dice cuál de `players[]` eres.
- **PlayerState:** `active[0|1], bench, benchMax, deckCount, discard, prize, handCount, hand, poisoned,
  burned, asleep, paralyzed, confused`.
- **Card:** `{id, serial, playerIndex}`. **`id` = tipo de carta** (mapea a deck.csv y al pool ~2000);
  **`serial` = instancia única en la partida**. NO confundirlos al trackear cartas en logs/búsqueda.
- **Pokemon** (hereda Card): `hp, maxHp, appearThisTurn, energies, energyCards, tools, preEvolution`.

### Información OCULTA vs visible (es imperfect-information, eje del 70%)
OCULTO: **mano del rival = None** (solo `handCount`); composición del mazo (solo `deckCount`); **prizes =
None** boca abajo; activo del rival puede estar boca abajo. VISIBLE: todo lo que está en juego, **discard
completo**, stadium, contadores. La política/búsqueda debe **muestrear estados plausibles** del rival. [HECHO]

### Catálogos
- **SelectType (11):** MAIN, CARD, ATTACHED_CARD, CARD_OR_ATTACHED_CARD, ENERGY, SKILL, ATTACK, EVOLVE,
  COUNT, YES_NO, SPECIAL_CONDITION. → router de la heurística por aquí. [HECHO]
- **OptionType: 17 valores** (no 18 — corregido por verificador): NUMBER, YES, NO, CARD, TOOL_CARD,
  ENERGY_CARD, ENERGY, PLAY, ATTACH, EVOLVE, ABILITY, DISCARD, RETREAT, ATTACK, END, SKILL,
  SPECIAL_CONDITION. [HECHO, conteo corregido en api.html]
- AreaType (12), SpecialConditionType (5), LogType (24): confirmados literal. Los `*_REVERSE` de LogType
  existen para reconstruir/deshacer estado.

### Motor de búsqueda nativo (para ISMCTS) — el matiz crítico
`libcg.so` exporta `SearchBegin/SearchStep/SearchEnd/SearchRelease` (verificado `nm -D`) y están en api.html.
Firma real: `api.search_begin(agent_observation, your_deck, your_prize, opponent_deck, opponent_prize,
opponent_hand, opponent_active, manual_coin=False) -> SearchState`. → **TÚ provees las predicciones del
rival como argumentos explícitos; el engine NO randomiza solo.** Eso resuelve cómo inyectar opponent modeling:
es por args. `search_step(search_id, select) -> SearchState` del siguiente nodo; **no documenta flag terminal
ni reward** → detectar terminal vía `current.result >= 0` dentro del SearchState. [HECHO, api.html]

🔴 **PERO (corrección del verificador, MUY importante):** el wrapper Python instalado (`cg/sim.py`,
`cg/game.py`, **kaggle-environments 1.30.1** — NO 1.14.10 como dice el README local) declara **solo 6
funciones**: `GameInitialize, BattleStart, BattleFinish, GetBattleData, Select, VisualizeData`.
**NO declara las Search* ni AllCard/AllAttack.** Los símbolos existen en el `.so` pero hay que **escribir el
binding ctypes a mano** (restype/argtypes) contra structs C no documentados ni en el código instalado.
**"ISMCTS soportado de fábrica" es FALSO en el estado actual**: la primitiva existe, el binding NO, y **nadie
público lo ha resuelto**. Es la tarea técnica de mayor riesgo del proyecto. [REFUTADO el framing "de fábrica"]

### Cómo correr local
```python
from kaggle_environments import make
env = make("cabt", configuration={"decks": [deck, deck]})
env.run([agent, agent])   # render html disponible
```
🔴 **El binario es ELF x86-64 GNU/Linux y NO carga en macOS (reproducido: dlopen "slice is not valid mach-o
file"). El M1 (ARM) tampoco lo corre nativo.** Self-play local requiere **Linux x86 / Docker linux/amd64 /
VPS**. [HECHO, confirmado en vivo]

### deck.csv
60 líneas, un `card_id` por línea, sin header. `len != 60` => INVALID. **[SUPOSICIÓN]** límite de 4 copias
por carta (regla física) — verificar contra el engine. Detalle interno: el binario usa buffers
`FixedListBase<..., 61>` (capacidad 61, no 60) — irrelevante para el deck pero útil al declarar bindings. [HECHO]

### Pool de cartas
**[REFUTADO]** `all_card_data()` como import directo: **NO existe** función `all_card_data` en el módulo
instalado (grep = 0 hits). Solo símbolos `AllCard/AllAttack` en el binario, sin binding Python. → o se
escribe el binding a mano, o se usa **`EN Card Data.csv`** del dataset (requiere identidad Kaggle). El
pipeline de cartas NO es trivial. Card ID conecta `obs["select"]["option"]` con la ficha; agrupar filas por
Card ID (un row por Move). [HECHO, DATASET.md]

### Presupuesto de tiempo
`cabt.json`: `actTimeout=0, runTimeout=3000, remainingOverageTime=600, episodeSteps=10000`. Interpretación:
**600s (10 min) de overage acumulado por jugador por PARTIDA entera, sin tope duro por jugada.** [HECHO el JSON]
⚠️ La "derrota por TIMEOUT" NO está explícita en cabt.py (lo gestiona kaggle-environments fuera) → esa parte
es **[SUPOSICIÓN razonable]**. El reparto "~15-30s por decisión, de sobra para ISMCTS" es **aritmética
optimista no verificada**: nadie ha medido un `search_step` real, y los turnos tienen micro-decisiones
encadenadas. [REFUTADO como dato]

---

## 4. Plan técnico: la escalera de enfoques y la ruta elegida

| Fase | Enfoque | Esfuerzo | Riesgo | Ganancia | En camino crítico |
|---|---|---|---|---|---|
| 0 | Random/first-legal robusto (entra al ladder) | Bajo | Bajo | Supervivencia | **Sí** |
| 1 | Heurística por OptionType + adoptar **sample oficial** del arquetipo | Medio | Bajo | Suelo competente | **Sí** |
| 2 | **ISMCTS determinizado** sobre API nativa search_* | **Alto** | **Alto** | El salto de ELO + el 70% | **Sí (apuesta central)** |
| 3a | BC/IL desde replays top-rated → policy/value net ligera | Medio-Alto | Medio | Prior PUCT + rollouts | Plan B del 70% |
| 3b | Híbrido search+net (policy prior + value cutoff) | Alto | Medio | Techo de rendimiento | Opcional |
| 4 | RL self-play (PPO/AlphaZero) desde cero | Muy alto | Muy alto | Incierta | **NO** (sumidero de tiempo) |

**Justificación de la escalera (todo [HECHO]):**
- Los tops de Kaggle (Lux, Kore, Hungry Geese, Two Sigma/Halite) fueron **híbridos** heurística+ML, nunca
  rule-based puro ni RL puro. Las reglas oficiales dicen *"rule-based alone may not ensure a high ranking"*.
- **ISMCTS** (Cowling et al. 2012) es el algoritmo de referencia para info imperfecta y supera a IA basada en
  conocimiento sin conocimiento específico del juego (Dou Di Zhu, Spades, Hearthstone). Apuntar a **50–200
  determinizaciones/decisión** (<75 rinde peor).
- **BC/IL** desde replays es palanca de alto ROI probada (Kore: 200M tuplas de top-5; Lux S1: replays de
  Toad Brigade). El export diario de episodios top-rated ES ese dataset, ya estructurado (obs→action).
- **AlphaZero puro es INVIABLE** (compute/tiempo): vale como PATRÓN (search + policy/value net), no como
  reentreno masivo. Mantener RL fuera del camino crítico.

**🔴 Correcciones de los verificadores que reescriben la ruta:**
1. El repo top `wmh/ptcg-abc` **ya construyó** env wrappers + `mcts_agent.py` + `train_bc.py` + `train_value.py`
   y los marcó **SUPERSEDED** porque un rule-based simple sobre sample oficial le rendía MÁS en ladder. El
   "hueco" de MCTS/IL **puede ser un cementerio para el RATING**, no una oportunidad limpia. La oportunidad
   real es para el **REPORT (70% método)**, no necesariamente para el ELO. [REFUTADO "hueco = oportunidad limpia"]
2. Un agente rule-based simple bien pilotado (Bellibolt, Elo ~836) batió a combos teóricamente más fuertes:
   *"un rule-based pilota un mazo simple limpiamente y uno complejo torpemente"*. **Mazo simple > combo frágil.**
3. Cuando hay sample oficial del mazo, **adoptarlo bate al hand-coded 13-1**. NO empezar la política de cero.

**RUTA CONCRETA ELEGIDA PARA NUESTRO PERFIL (cero en game-AI, fuerte iteración agéntica, 8 semanas):**
> Fase 0+1 sólidas y robustas (suelo de supervivencia y un agente que NO se cae) → **apostar Fase 2 (ISMCTS)
> como el corazón del 70% del report**, con un **checkpoint duro**: si a la **semana 5** el binding de búsqueda
> no funciona o no rinde, **pivotar a BC/IL (Fase 3a) como plan B del 70%** y dejar ISMCTS documentado como
> método con ablation honesta. El RATING se defiende con el sample oficial robusto; el PREMIO se defiende con
> el método real (ISMCTS o BC) + la disciplina de evaluación honesta.

---

## 5. Diseño de mazo (el 20%)

**Principios [HECHO]:**
- El PTCG es una **carrera de premios** (6 premios; ex/V/GX dan 2 al rival al caer). El **prize trade** es EL
  concepto: un atacante de 1 premio que pega ~160 antes de caer bate a uno de 2 premios equivalente.
- **Consistencia > exotismo.** Ratio competitivo 2026: ~15-21 Pokémon / 28-33 Trainers / 8-13 Energía.
  Sobre-contar la Basic de cada línea (4-4-3 en Stage 2). Motor: ~4 Supporter de robo + 3-4 de disrupción +
  Items de búsqueda ilimitados (Ultra Ball, Poffin).
- Para el jurado, concepto defendible = **sinergia + plan de premios + matchups + estabilidad ante el ruido
  de robo**, NO carta rara por rareza. Un netdeck adaptado y justificado puntúa mejor que originalidad frágil.
- **Cruzar con la restricción del runtime:** preferir un plan con **menos decisiones de altísima profundidad
  y menos combos frágiles**, porque lo pilota un agente Python sin LLM. Un deck "fácil de pilotar bien"
  rinde más consistente.

**Arquetipos candidatos (meta del simulador a 21-jun, [SUPOSICIÓN — datos de terceros, CLAUDE.md de
wmh/ptcg-abc, snapshot que cambió fuerte en 5 días):**
- **Dragapult ex** — dominante (~63% WR a Elo≥1150), única derrota clara vs Cinderace. Spread+snipe.
  ⚠️ Hay **sample oficial tuned** que TODO el campo serio ya usa (5 pilotos Elo≥1150 comparten UNA lista):
  adoptarlo nos pone **al nivel** del campo, no por encima. No diferencia para Top 8 por sí solo.
- **Hop's Trevenant** — cayendo (WR 64.6%→52.3%). **Alakazam** — estable (~55% WR). **Bellibolt** simple
  (suelo limpio para rule-based).

**Tesis de mazo para el report:** no entregar un netdeck pelado. Dar **concepto + plan de juego + líneas
contra 3-4 arquetipos meta + argumento de estabilidad/consistencia** (prob. de abrir plan A, redundancia,
recuperación), y **co-diseñar deck+política vía self-play**. El meta es volátil → **re-evaluar antes de
congelar deck.csv**, hay margen hasta 16 ago.

**[BLOQUEANTE de diseño]:** confirmar qué regulaciones (G/H/I/J) están en el pool del simulador ejecutando
el binding de cartas en Linux. Si es pre-rotación abril 2026, el meta es Gardevoir/Charizard/Gholdengo;
si es post (H-on/Mega), es Dragapult/Megas. **Cambia todo el deck.** No verificable sin Linux + identidad Kaggle.

---

## 6. Playbook del ladder

**Regla de oro:** NUNCA subir una versión que no haya superado un gate local. El leaderboard es para
**confirmar**, no para **descubrir**. [HECHO, lección Two Sigma/Halite: reemplazaron su red por números
aleatorios y el bot rendía igual — solo el A/B controlado lo reveló].

**Disciplina de slots (regla de los 2 últimos):** ten SIEMPRE tu campeón validado como uno de los 2 activos.
Usa el 2º slot para el candidato. Promuévelo solo si confirma tras suficientes episodios (no juzgar en las
primeras horas con σ alta). Nunca dejes que un experimento crudo desplace al campeón.

**Control de varianza:** evaluación **pareada** (mismas semillas de shuffle para v_old y v_new), como Two
Sigma fijó el mapa. Multiplica la potencia estadística por episodio. Declarar "mejora" solo si el IC de la
diferencia de μ excluye 0. Usar `pip install trueskill` para replicar el ranking en local.

**Robustez = supervivencia:** envolver TODA la lógica en `try/except` con fallback a jugada legal (primera
opción / random-legal) + **watchdog de tiempo** (si te acercas al límite, jugada heurística rápida). Objetivo:
**0 crashes / 0 timeouts**. Un episodio perdido por excepción es rating regalado. Precedente: el propio engine
puede tener bugs (caso Orbit Wars) → programar defensivo.

**🔴 Anti-falso-positivo REANCLADO (la corrección más importante del verificador):** la tesis original
"self-play masivo + gating = nuestro alpha" está **parcialmente refutada**: `wmh/ptcg-abc` verificó que
*"local sims NO predicen el ladder rank"* (ej. una opt con 62% en cabt local quedó 907<1006 en ladder). El
gating como **disciplina** sigue siendo válido, pero **el ground truth NO puede ser self-play en vacío**.
Hay que:
- Construir un **panel de oponentes diverso** (versiones previas + samples oficiales + mazos meta extraídos
  de los episodios diarios) en vez de solo copias propias.
- Anclar el juicio final al **ladder/meta real**, asumiendo que eso reduce el throughput de iteración (no
  puedes correr 1000 partidas baratas que predigan).
- **Test anti-enmascaramiento (Two Sigma):** antes de creer que un componente ML aporta, sustitúyelo por
  ruido y verifica que el rating CAE. Si rinde igual, la heurística lo enmascaraba.

Esta disciplina honesta — **incluida la admisión de que el local engaña** — es justo la narrativa
metodológica que un jurado académico premia.

---

## 7. La Strategy / report (donde está el dinero)

**Cómo se gana el 70% (método):** el protagonista es la **ARQUITECTURA DE DECISIÓN del agente** bajo info
imperfecta — ISMCTS/determinización, belief/opponent modeling (inyectado por args en `search_begin`), manejo
del azar (robo/monedas) — con **justificación de cada elección**. El jurado (Matsuo + HEROZ) premia
*"novel methodologies for strategy learning and decision making"* y detecta el **bluff** de citar ISMCTS/CFR
sin implementarlo. **Solo citar lo que el agente realmente ejecuta.** [HECHO]

**Cómo se gana el 20% (mazo):** tesis de concepto + tabla de líneas contra arquetipos meta + argumento de
estabilidad/consistencia, co-diseñado con la política. No un netdeck.

**El ángulo Dev Aumentado — ¿suma de verdad? SÍ, pero acotado.** Va **DENTRO de la sección de metodología
empírica como PROTOCOLO DE VALIDACIÓN**, nunca como protagonista. Frase tipo: *"cada mejora candidata pasa un
gate estadístico (A/B con N suficiente para la σ del rating gaussiano, IC, test anti-enmascaramiento) antes de
aceptarse; documentamos además que el self-play local NO predice el ladder, y reanclamos el ground truth al
meta real."* Eso convierte nuestra ventaja en **RIGOR** (lo que el lab premia). **Si el report cuenta "relato"
(mira qué chulo el Dev Aumentado) en vez de método, el jurado lo castiga y la probabilidad se desploma.** [HECHO]

**Estructura de las 2.000 palabras (presupuesto orientativo):**
1. **Problem framing (~150p):** PTCG como imperfect-information game + azar; por qué heurística pura no basta.
2. **Model approach / arquitectura de decisión (~750p) — EL 70%:** pipeline sobre el árbol de opciones
   legales (ISMCTS/determinización, evaluación de estado, opponent/belief modeling, manejo del azar),
   justificado.
3. **Deck concept (~350p) — EL 20%:** tesis, plan de juego, sinergias, líneas vs 3-4 arquetipos, estabilidad.
4. **Empirical methodology & results (~500p):** A/B pareado, N para σ, IC, **2-4 ablations por componente**
   (con/sin opponent modeling, profundidad de search, con/sin manejo del azar), WR por matchup, estabilidad
   del rating. Aquí va el Dev Aumentado como protocolo.
5. **Reproducibility & limitations (~250p).**

Incluir **1-2 gráficos** (curva de rating con banda σ; WR por matchup con IC). Report autosuficiente, en
inglés ([SUPOSICIÓN] — confirmar idioma/formato logueado), sin sugerir LLM en runtime (regla NO INGRESS/EGRESS).

---

## 8. Lo que aún NECESITAMOS conseguir — checklist

**Datos / accesos:**
- [ ] 🔴 **Verificación de identidad Kaggle** (pendiente). Bloquea: competition data, `EN Card Data.csv`,
  episodios diarios para BC, leaderboard real, submission, lectura de Rules/notebooks. **Cuello raíz.**
- [ ] 🔴 **Entorno Linux x86-64** que cargue `libcg.so` (Docker linux/amd64 / VPS / entorno Kaggle).
  El M5/M1 (macOS/ARM) NO sirve nativo.
- [ ] Clonar **`github.com/wmh/ptcg-abc`** y estudiar `cabt_eval.py`, `cabt_ab.py`, `meta_analyze.py`,
  `build_submission.sh` y la carpeta `/research/` (su MCTS/RL/IL SUPERSEDED). Alinear a kaggle-environments **1.30.1**.
- [ ] Pipeline de descarga diaria de episodios (`kaggle datasets download kaggle/pokemon-tcg-ai-battle-episodes-YYYY-MM-DD`,
  ~720MB/día) + parser en streaming `(steps[t][pi]['observation'] → steps[t+1][pi]['action'])` filtrando por Elo alto.
- [ ] `pip install trueskill` para el ranking local.

**Decisiones / confirmaciones (logueado en Kaggle):**
- [ ] Fórmula EXACTA de orden del leaderboard (μ−kσ) y episodios/día por agente.
- [ ] Idioma + formato + límite real del report (¿2.000 palabras incluyen refs/captions? ¿enlaces externos a
  repo/notebook permitidos? — si sí, gran palanca para sacar la reproducibilidad fuera del límite).
- [ ] Deadlines oficiales reales (agente 16 ago / report ~14 sept) en la pestaña Rules.
- [ ] Montos/condiciones de premios en la pestaña Prizes.
- [ ] Regla de copias por carta (¿máx 4?) y qué regulaciones (G/H/I/J) hay en el pool.
- [ ] **Differences from official rules** (sigue SIN verificar; WebFetch no la encuentra; abrir api.html a mano).

**Decisiones internas de equipo:**
- [ ] ¿Reclutar a alguien con background game-AI antes del merger deadline 9 ago? (mitiga el gap de capacidad).
- [ ] ¿ISMCTS en camino crítico del RATING o solo del REPORT? (condiciona semanas).
- [ ] Encaje con el bloque HA (foco hasta 17 sept) + posible viaje a Tokio si entramos.

---

## 9. Riesgos: por qué podríamos NO entrar en Top 8 (lista fría)

1. **Campo elite por 8 plazas.** HEROZ (shogi-AI) + Matsuo + japoneses ya iterando A/B en ladder al 5º día.
2. **Cero background en game-AI** + el 70% depende de ISMCTS sobre un binario cuyo wrapper de búsqueda
   **nadie ha hecho** — la tarea más dura del proyecto, riesgo de reverse-binding no trivial.
3. **Tesis diferenciadora parcialmente refutada:** el self-play local NO predice el ladder (verificado por el
   campo top). Sin reanclar, quemamos compute optimizando un proxy malo.
4. **El "hueco" de MCTS/IL puede ser un cementerio:** el campo top probó búsqueda compleja y la abandonó por
   bajo ROI en ladder vs rule-based limpio. Un MCTS clunky puede rendir PEOR que un heurístico limpio.
5. **Bloqueantes de Fase 0 sin resolver** (identidad Kaggle, Linux x86, binding de búsqueda) con calendario
   corto (8 semanas al agente).
6. **Robustez:** un crash/timeout = derrota silenciosa; el propio engine puede tener bugs.
7. **Sobreescribir el campeón** (regla de los 2 últimos) por indisciplina de slots.
8. **Meta volátil:** comprometer deck.csv pronto y no re-evaluarlo.
9. **Report que cae en relato** en vez de método → el jurado académico lo castiga aunque el agente sea decente.
10. **Calendario doble no confirmado** (agente 16 ago / report ~14 sept): si el agente no está fuerte el 16
    ago, el report (70% método) no tiene sustancia que contar.
11. **Multi-índice (`maxCount>1`):** el branching factor de ciertas decisiones puede explotar el ISMCTS.
12. **Diferencias con reglas oficiales sin verificar:** sesgo sistemático en heurística/rollouts que el
    self-play simétrico no detecta.

---

## 10. Roadmap por fases (hitos y fechas)

**Semana 0 (22–28 jun) — DESBLOQUEAR (sin esto nada avanza):**
- Resolver **verificación de identidad Kaggle**.
- Montar **Linux x86** (Docker linux/amd64 o VPS) y verificar `make("cabt")` + `env.run([random,random])`
  end-to-end (una partida random vs random).
- **Clonar `wmh/ptcg-abc`**, estudiar su harness y su lección "local no predice ladder". Alinear a 1.30.1.
- Corregir docs locales: kaggle-environments **1.30.1** (no 1.14.10), OptionType **17** (no 18).

**Semana 1-2 (29 jun–12 jul) — Supervivencia + suelo:**
- Agente **robusto** (try/except global + fallback legal + watchdog) que entra al ladder. 0 crashes/timeouts.
- **Adoptar sample oficial** del arquetipo (Dragapult/Iono) envuelto en scaffolding robusto. Mapear deck a 60
  Card IDs desde `EN Card Data.csv`, validar `len==60`.
- Montar **harness A/B** (reutilizar el de ptcg-abc) + `trueskill` local + panel de oponentes diverso.
- Pipeline de descarga diaria de episodios funcionando.

**Semana 2-5 (13 jul–2 ago) — EL SALTO (apuesta central):**
- Escribir y **VALIDAR el binding ctypes** de `SearchBegin/Step/End/Release` + cartas contra `libcg.so`
  (introspección del binario / pedir specs en el foro del host).
- Implementar **ISMCTS determinizado**: inyectar predicciones del rival como args, 50-200 determinizaciones,
  rollout con la heurística de Fase 1, presupuesto de tiempo adaptativo, **liberar cada search_id** (evitar leaks).
- **🚩 CHECKPOINT semana 5:** si el binding no funciona o no rinde → **pivotar a BC/IL (plan B del 70%)**.

**Semana 4-7 (en paralelo, 27 jul–9 ago) — Plan B del 70% + report arranca:**
- BC/IL desde episodios top-rated → policy/value net ligera (inferencia CPU sin deps pesadas: TorchScript/ONNX
  o NumPy puro en el .tar.gz). Opcional híbrido search+net (policy prior PUCT).
- **Report desde semana 4** (NO al final): estructura sección 7, ablations, gráficos. Confirmar idioma/formato/deadline.

**Semana 6-8 (3–16 ago) — Cierre del agente:**
- Re-evaluar deck.csv contra el meta vivo y **congelar**. Test de estrés de partidas largas (no agotar 600s).
- Elegir las 2 Final Submissions. **16 ago: final submission del agente.**

**17-31 ago — Convergencia del ladder:** monitorizar rating real; NO iterar el agente (congelado), pero
recoger datos para el report.

**Hasta ~14 sept — Report Strategy:** redactar/pulir las 2.000 palabras con el método REALMENTE implementado,
ablations con IC, y el Dev Aumentado como protocolo de rigor. **Entregar.**

---

---

## 11. Tesis competitivas / palancas (input de Fran, 22 jun — evaluado y corregido)

Seis observaciones de Fran (de foros/comentario), contrastadas con la investigación y el competidor `ptcg-abc`.
Veredicto: las 6 son legítimas; 2 llevan corrección. Orden = lo que más mueve la aguja.

1. **Algoritmo de decisión bajo info oculta — EL CORAZÓN (=70% del report). ✅**
   Aquí vive el criterio humano, no el autocompletado. De las opciones: **ISMCTS/determinización** = apuesta
   principal (alto riesgo: binding nativo sin hacer + el competidor abandonó MCTS por bajo ROI en ladder).
   **Deep RL self-play** = alternativa real pero sumidero de tiempo → fuera del camino crítico. **🔧 CFR
   (póker) = DESCARTADO:** necesita recorrer/abstraer el árbol del juego uno mismo; el espacio del TCG es
   enorme y el motor da opciones legales pero no un modelo limpio para CFR. Funciona en póker por ser acotado.
   Criterio real: no "cuál es más cool" sino "cuál podemos implementar Y validar en 8 semanas" → ISMCTS o, plan B, IL.

2. **Diseño de mazo — el 20% y NUESTRO GAP de dominio. ✅**
   Matemática de premios (1 vs 2 prizes, prize trade), consistencia, ratios, matchups = conocimiento de PTCG
   competitivo que no tenemos. **REFRAME del reclutamiento:** el fichaje de mayor ROI quizá NO sea un ML-ero
   sino **un jugador competitivo de Pokémon TCG**. Son dos gaps distintos; el de dominio puede ser más barato
   y vale 20% directo + sube el techo del agente. → A decidir en julio (ver §8, decisión de equipo).

3. **Harness local / "trust your local CV" — ⚠️ LA MÁS PELIGROSA (corregida).**
   Montar el harness es clave (de lo que más separa). PERO el dogma Kaggle "fíate del local antes que del
   leaderboard" **es una TRAMPA verificada aquí**: `ptcg-abc` documentó que las sims locales NO predicen el
   ladder (62% local → peor en ladder real). Reescritura correcta: **valida primero que el local correlaciona
   con el ladder; panel de rivales diverso anclado al meta real (no self-play en vacío); el local es FILTRO
   barato, no JUEZ final.** El juez es el ladder. (Coherente con §6.)

4. **Eficiencia de muestra bajo "cap de gasto" — 🔧 CORRECCIÓN DE HECHO.**
   El "Reasonableness Standard" NO es un tope de compute/GPUs; es equidad sobre datos/herramientas externas
   (no usar dataset/LLM propietario caro que excluya a otros). **No hay límite de GPUs para entrenar.** El
   cuello real es la **inferencia: offline, sin red, 10 min/partida**. Kernel válido: para NOSOTROS gana quien
   entrena listo (por límites de tiempo/skill, no por la regla). Curriculum/reward design solo si vamos RL (no es el caso base).

5. **Robustez al meta adversarial — ✅ CONFIRMADÍSIMO.**
   Prueba viva: el meta gira en UN día (Lucario rey→extinto; Trevenant 64%→52% en una jornada). El foro
   ("bots brute-force subóptimos revientan a los afinados para juego óptimo") encaja con que un rule-based
   simple batía combos teóricamente superiores. **No sobreajustar a un rival; optimizar contra una distribución.**

6. **Dominar el simulador — ✅ y ya iniciado.**
   Es la §3. Primer paso dado (motor corriendo en local, enums extraídos). Pendiente clave: la página oficial
   de **"diferencias entre reglas y simulador"** — exprimir en cuanto haya identidad Kaggle. Quien conoce los
   quirks juega con ventaja.

**Ranking de palancas:** (1)+(5) [el 70% y donde se gana/pierde] > (3 corregido)+(6) [multiplicadores, sin
ellos iteras a ciegas] > (2) [el 20% + gap de dominio] > (4) [filosofía válida, no restricción de reglas].
**Cambios netos a la lista original:** descartar CFR · reescribir "trust your local CV" (aquí el local engaña)
· corregir el encuadre de (4) (no hay cap de compute, hay cap de inferencia offline de 10 min).

---

_Fuentes primarias citadas inline. Activo público clave: `github.com/wmh/ptcg-abc`. Docs engine:
https://matsuoinstitute.github.io/cabt/. Docs locales: README.md, RULES.md, COMPETITIONS.md, data/DATASET.md._
