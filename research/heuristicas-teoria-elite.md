# Heurísticas de teoría de élite → spec encodeable (A1)

> Destilado de `Downloads/estrategia pokemon.md` §6 a reglas que el agente offline
> (Leon v1.5 prize-aware rule-based) pueda EJECUTAR, dado que el agente decide SOLO
> con el `obs` dict (no consulta nada en runtime) + una card-data estática que nosotros
> construyamos.
>
> Marco (plan A1): cada concepto entra por una de 4 puertas — **reward / prior / belief / eval**.
> Lo que no entra por una puerta = bibliografía para Fran, no edge.
>
> Estado de la corrida: **spec, sin correr nada**. La verificación A/B es FILTRO posterior
> (Bloque C), no parte de A1. Donde digo "computable" me refiero a *computable con el
> obs+card-data*, NO a "verificado que gana".

---

## 0 · Contrato REAL del runtime (verificado leyendo obs + sample, no asumido)

Esto fija qué es computable. Verificado en `data/episodes/episode-81310338-replay.json`
(steps reales) y en los headers de `agent/main.py` y `agents_official/dragapult_sample/main.py`.

### 0.1 · Forma del `obs` dict (lo que el agente ve cada decisión)
- `obs.current.players[i]` con: `active[]`, `bench[]`, `hand[]`, `discard[]`, `prize[]`,
  `deckCount` (int), `handCount` (int), `benchMax`, y status flags
  (`asleep/paralyzed/confused/poisoned/burned`).
- `obs.current`: `yourIndex`, `firstPlayer`, `turn`, `turnActionCount`, `stadium[]`,
  `supporterPlayed`, `stadiumPlayed`, `looking[]` (cartas que estás mirando ahora, p.ej. tras un search).
- `obs.select`: `context` (int), `option[]`, `minCount`, `maxCount`, `deck[]` (en search),
  `effect`, `contextCard`, `remainDamageCounter`, `remainEnergyCost`.
- `obs.logs`: eventos del turno (incluye `ATTACK` con `attackId`, `MOVE_CARD` con
  `fromArea/toArea/playerIndex`, `TURN_END`). Es la única ventana a lo que hizo el rival.

### 0.2 · Forma de una carta Pokémon en juego (active/bench)
`{ id, hp, maxHp, energies:[int], energyCards:[{id,...}], tools:[{id,...}],
   preEvolution:[...], appearThisTurn:bool, serial, playerIndex }`

### 0.3 · Forma de una carta en mano / descarte / prize
- **hand / discard**: solo `{ id, playerIndex, serial }` (SÍ veo el id de mis cartas).
- **prize**: **lista OPACA**. Los elementos de `prize[]` están vacíos `{}` — el obs expone
  **SOLO la LONGITUD** (`len(prize)` = premios restantes). NO veo qué cartas están premiadas,
  ni mías ni del rival. 🔴 Esto es el dato más importante para clasificar prize-checking.

### 0.4 · ⚠️ La trampa de `card_table` (qué NO está en el obs)
El sample oficial usa `all_card_data()` (cg-lib) para construir `card_table`, y de ahí
saca **`.ex`, `.megaEx`, `.name`, `.stage1`, `.stage2`, `.cardType`, `.megaEx`**. Eso vive
en cg-lib, que **solo importa con identidad Kaggle dentro de docker** (en `agent/main.py`
cg NO está disponible → es dict-only). Nuestro `agent_v2/cards.json` (1267 cartas) trae
SOLO `{hp, type, weakness, retreat, attacks}` — **NO trae ex/megaEx/name/stage**.

**Consecuencia dura:** el valor de premios por carta (binario 1/2/3) NO es derivable del obs
ni de la card-data que tenemos hoy. Es un **bloqueante raíz** (= B1 del plan). Sin una tabla
estática `id → {prizeValue, stage, isEx, isMegaEx}` construida por nosotros, TODA la reward
de prize-trade es incomputable. Ver sección "Bloqueantes".

---

## 1 · Prize-trade / mapa de premios 2-2-2  → puerta REWARD

### Concepto (doc §6)
Ganar = tomar 6 premios primero, no noquear. El valor de un KO NO es binario: depende del
**intercambio NETO de premios**. Un Pokémon "Rule Box" (ex/V/VSTAR) da 2–3 premios al caer;
un single-prize da 1. Un mapa 2-2-2 = tres KOs a ex. Forzar al rival a un mapa ineficiente
(que necesite un "7º premio" imposible) es jugada de élite.

### (a) Regla en pseudocódigo (reward shaping del scoring de opciones)

```
# Estática construida por nosotros (B1). NO está en el obs.
PRIZE_VALUE[id] = 3 if MEGA_EX[id] else 2 if EX[id] else 1

def prize_yield(poke, is_attack_damage):
    # replica prize_count() del sample PERO con card-data NUESTRA
    v = PRIZE_VALUE[poke.id]
    if is_attack_damage:
        for e in poke.energyCards:
            if e.id == LEGACY_ENERGY: v -= 1      # Legacy Energy resta 1 premio
        if has_lillies_pearl(poke): v -= 1        # Lillie's Pearl resta 1 (si name~Lillie)
    return max(0, v)

# --- NETO: la métrica que el doc pide explícitamente ---
def net_prize_swing(my_ko_plan, their_likely_ko):
    # premios que YO me llevo este intercambio
    gained = sum(prize_yield(t, True) for t in my_ko_plan.targets)
    # premios que el rival se lleva al responder (su KO probable a mi atacante)
    lost   = prize_yield(their_likely_ko, True) if their_likely_ko else 0
    return gained - lost     # >0 = intercambio favorable

# --- ponderación por el MAPA 2-2-2 (no solo el swing puntual) ---
def prize_map_bonus(target, my_prizes_left, opp_prizes_left):
    p = prize_yield(target, True)
    # cerrar la partida YA domina todo (lethal):
    if opp_prizes_left - p <= 0:  return +50000     # este KO gana
    # "forzar el 7º premio": si voy por detrás, prefiero KOs grandes que me
    # devuelvan tempo; si voy MUY por delante, no regalar 2-2-2 al rival.
    bonus = 0
    if p >= 2:
        if my_prizes_left <= 4: bonus -= 1200   # no exponer mi ex cuando cierro yo
    elif p == 1:
        bonus -= 300                            # single-prize: peor objetivo en igualdad
    else:
        bonus += 1200                           # 0-premio (Budew, etc): noquéalo gratis
    return bonus
```

**Fórmula del intercambio NETO de premios (lo que el doc pide literal):**

> `valor_de_un_KO(objetivo) = prize_yield(objetivo) * W`
> donde `prize_yield ∈ {0,1,2,3}` (NO binario), ponderado por el mapa:
> `score(plan) = Σ prize_yield(t)·1000  +  prize_map_bonus(t, mis_premios, sus_premios)  −  prize_yield(mi_atacante_expuesto)·λ`
>
> El `−` final es el NETO: descuento por exponer a mi atacante a un KO de respuesta que dé
> 2/3 premios. `λ` = peso del riesgo de represalia (calibrable; empezar λ≈800).

Esto ya existe en germen en el sample (`main_option_proc`: `score -= 1200`, `50000` lethal,
`prize_count*1000`). **Nuestro edge = subirlo de táctico a estratégico:** (1) usar el NETO
(restar el premio que regalo), (2) reusar la misma reward para CUALQUIER mazo (hoy el sample
la tiene hard-codeada a Dragapult).

### (b) Puerta: **REWARD**. Es la definición de "ganar" inyectada en el score de cada opción
de ataque / target de daño. No es un prior ni un belief.

### (c) Datos que necesita del card data
`PRIZE_VALUE[id]` ← requiere `{isEx, isMegaEx}` por carta. Modificadores: `LEGACY_ENERGY` id,
`Lillie's Pearl` tool id + `name~"Lillie"`. **HP y energías SÍ están en el obs.** Los flags
ex/megaEx/name **NO** → hay que construir la tabla estática (B1).

### Computable?
- **Swing/HP/energías/lethal: SÍ** computable (todo está en el obs).
- **prize_yield correcto: NO hoy** — bloqueado por falta de `ex/megaEx` en card-data → **B1**.
  Sin esto, prize-trade colapsa a "todo vale 1 premio" y la reward es ciega al rule-box.

---

## 2 · Prize-checking probabilístico  → puerta BELIEF

### Concepto (doc §6)
Deducir qué cartas están "premiadas" (inaccesibles) por eliminación de lo que ya NO está en
el mazo, y reevaluar tras cada search. Avanzado: estimar P(robar un "out" de mis premios al
tomar KOs). El doc: mantener una **distribución de creencias** sobre cartas premiadas propias.

### (a) Regla en pseudocódigo

```
# PROPIAS (computable por ELIMINACIÓN, igual que hace set_card_counts del sample):
def my_prized_ids(obs, my_deck):
    counts = Counter(my_deck)                      # mi decklist es conocida (la elegí yo)
    for zone in [hand, discard, bench, active, stadium_mine, looking_mine]:
        for card in zone: counts[card.id] -= 1     # resto todo lo visible/contado
    # lo que sobra (counts>0) son las cartas que están en deck O en prize.
    # NO sé cuáles de esas N están prizadas vs en deck, solo CUÁNTAS (len(prize)).
    return counts   # multiset de "no-vistas" = deck restante + premios

def P_out_in_prizes(n_outs_unseen, unseen_total, prizes_left):
    # P(al menos 1 de mis n_outs está premiado) — hipergeométrica.
    # útil para "¿mi pieza clave está prizada?" antes de comprometer un plan.
    from math import comb
    if unseen_total < prizes_left: return 1.0
    p_none = comb(unseen_total - n_outs_unseen, prizes_left) / comb(unseen_total, prizes_left)
    return 1 - p_none
```

### (b) Puerta: **BELIEF**. Es estado de creencia sobre lo oculto que modula el plan
(p.ej. "no me comprometo a una línea que necesita la 2ª Rare Candy si P(prizada) es alta").

### (c) Datos que necesita
Mi decklist (la tengo: `my_deck`/deck.csv) + ids visibles del obs (los tengo) +
`len(prize)` (lo tengo). NO necesita card flags. **`combinatoria` pura.**

### Computable? — **PARCIAL, con un límite duro que hay que decir honesto:**
- ✅ **Mis premios "por eliminación" (qué MULTISET de cartas mías no he visto, y cuántos
  premios quedan): SÍ computable.** Es exactamente lo que `set_card_counts` ya hace para
  Dragapult. Generalizable a cualquier mazo (solo depende de `my_deck`).
- ✅ **P(out propio prizado) vía hipergeométrica: SÍ computable.**
- 🔴 **Saber el ID EXACTO de una carta premiada concreta (mía o del rival): NO.** El obs da
  `prize[]` como lista **opaca de longitud N** (verificado: entries `{}` vacíos). No revela
  identidades. Solo distingues "está en deck" de "está en prize" probabilísticamente, nunca
  con certeza, salvo cuando `unseen_total == prizes_left` (todo lo no-visto está prizado).
- 🔴 **Prize-checking del RIVAL (qué le falta a él por estar prizado): NO computable** —
  no conozco su decklist (info imperfecta) ni veo sus premios. Esto es lectura de rival, no
  prize-checking. → **backlog** (requiere belief sobre arquetipo rival, §4 + C2).

**Veredicto:** prize-checking propio por eliminación = SÍ, edge real y barato (puerta BELIEF).
Prize-checking de identidades exactas / del rival = NO con este obs → **backlog**.

---

## 3 · Sequencing (max info / min compromiso / negar info)  → puerta PRIOR

### Concepto (doc §6)
Orden de jugadas DENTRO de un turno. Tres principios: **(i) maximizar información**
(draw/search antes de comprometerte: "draw before you search"), **(ii) minimizar compromiso**
(retrasa lo irreversible al último momento), **(iii) negar info al rival** (juega cartas que
le den elección —Boss/Sabrina— antes de revelar tu plano completo). Es directamente una
**política de ordenamiento de acciones intra-turno**.

### (a) Regla en pseudocódigo (prior sobre el orden de opciones en CTX_MAIN)

```
# Orden de prioridad de FAMILIAS de acción en MAIN (mayor = antes):
SEQ_PRIORITY = {
  DRAW_ABILITY      : 100,  # (i) max info: roba/mira ANTES de decidir el resto
  SEARCH/PLAY_BALL  : 92,   #     pero DESPUÉS de draw (draw-before-search)
  EVOLVE            : 88,
  ATTACH_ENERGY     : 80,   # (ii) compromiso medio
  PLAY_SUPPORTER    : 70,   # tras ver mano completa (ya robé)
  RETREAT           : 40,
  ATTACK            : 20,   # (ii) IRREVERSIBLE + acaba turno → SIEMPRE lo último
  END               : 1,
}

# (i) max info: si hay una habilidad/draw que no descarta nada útil y aún no robé este
#     turno, sube su score. "draw before search":
if can_draw and not drew_this_turn:  score[draw_opt] += BIG
if is_search and not drew_this_turn and can_draw: score[search_opt] -= PENALTY

# (ii) min compromiso: penaliza jugar la carta irreversible (attack, descartar pieza única,
#     Boss que revela target) hasta que NO queden acciones de setup legales.
if opt is ATTACK and any(setup_option_still_legal): score[opt] -= HUGE
if opt discards a singleton-needed-later:           score[opt] -= HUGE

# (iii) negar info: entre dos órdenes equivalentes, juega primero lo que NO revela plan
#     (energía a banca) y deja Boss's Orders / gust effects para cuando ya no des elección.
if opt reveals_target (Boss/gust) and turn_not_lethal: score[opt] -= MED
```

### (b) Puerta: **PRIOR**. Es qué jugada probar primero; no cambia la definición de ganar
(reward) ni el belief. Reordena el árbol de un turno.

### (c) Datos que necesita
- `obs.select.option` + `type` (OptionType): los tengo (ints en `agent/main.py`).
- "¿ya robé/ya jugué supporter este turno?": `state.supporterPlayed` SÍ; "ya robé" se infiere
  de `obs.logs` del turno (MOVE_CARD a hand) o de un flag propio que mantengamos.
- "¿es target-revealing?": necesita saber qué hace la carta → `attackId`/card semantics.
  Para cartas clave (Boss's Orders id 1182, gusts) se hard-codea una lista pequeña.

### Computable?
- ✅ **(i) draw-before-search y (ii) attack-último: SÍ** — ya es casi el `MAIN_PRIORITY` de
  `agent/main.py` (attack=60 < setup). Refinarlo es barato y NO necesita card flags.
- 🟡 **(iii) negar info / "no descartar singleton needed later": PARCIAL.** Requiere saber qué
  cartas son "necesarias luego" (semántica de carta) → para el mazo propio es codificable
  (lista corta), genérico NO.
- **Veredicto:** sequencing es el concepto MÁS computable y barato de los 4 (puerta PRIOR,
  solo obs+OptionType). Es el primer candidato a inyectar en Leon v1.5 (C1).

---

## 4 · Identificación de rol (beatdown vs control)  → puerta PRIOR (modula REWARD/BELIEF)

### Concepto (doc §6)
En cada matchup identificar tu rol: **beatdown** (eres más rápido → presiona, corre la
carrera de premios) vs **control** (eres más lento → niega recursos, alarga, fuerza mapa
ineficiente). Define si priorizas tempo/agresión o disrupción/longitud.

### (a) Regla en pseudocódigo (clasificador de rol → ajusta pesos)

```
def my_role(obs):
    me, opp = obs.current.yourIndex, 1-obs.current.yourIndex
    my_p, opp_p = len(players[me].prize), len(players[opp].prize)
    my_board_power  = sum(attacker_readiness(p) for p in my_active+my_bench)
    opp_board_power = sum(attacker_readiness(p) for p in opp_active+opp_bench)
    # heurística de rol: ¿voy ganando la carrera de premios / tengo más presión?
    if my_p < opp_p or my_board_power > opp_board_power + MARGIN:
        return BEATDOWN
    if my_p > opp_p and opp_board_power > my_board_power:
        return CONTROL
    return EVEN

# efecto sobre los pesos (NO es una acción nueva, re-pondera reward/sequencing):
if role == BEATDOWN:
    λ_retaliation *= 0.6      # arriesga más, persigue el KO (acepta exponer atacante)
    attack_priority += 10     # ataca antes
elif role == CONTROL:
    λ_retaliation *= 1.4      # protege atacante, no regala 2-2-2
    value_disruption += BIG   # Crushing Hammer / stadium swap / mano-rival valen más
    prefer_force_inefficient_map = True   # noquea single-prizers, niega el 7º premio
```

### (b) Puerta: **PRIOR que modula REWARD y BELIEF.** No es acción nueva: es un selector de
régimen que reescala los pesos de §1 (λ de represalia) y §3 (agresión vs disrupción).

### (c) Datos que necesita
- `len(prize)` de ambos: SÍ (obs).
- `attacker_readiness(poke)` = ¿tiene energía suficiente para su ataque? → energías SÍ (obs),
  pero el COSTE del ataque está en card-data (`attacks[].energy_count` SÍ está en
  `cards.json`). HP/maxHp SÍ.
- `opp_board_power`: veo los Pokémon del rival en mesa (active/bench, con id/hp/energies) → SÍ.

### Computable?
- ✅ **Versión de mesa (premios + readiness de lo que está EN JUEGO): SÍ computable** con
  obs + `attacks[].energy_count` de cards.json. No necesita ex/megaEx para el rol (aunque
  mejora con prize_yield).
- 🔴 **Rol "verdadero por matchup" (sé que enfrento un control tipo Pidgeot y ajusto desde
  turno 1): NO** — requiere identificar el arquetipo rival = belief sobre mano/deck oculto
  (info imperfecta). → versión fuerte a **backlog** (junta con lectura de rival, C2/B3).
- **Veredicto:** rol "instantáneo de tablero" = SÍ, barato, buen multiplicador de §1/§3.
  Rol "por arquetipo anticipado" = backlog.

---

## 5 · Resumen de computabilidad (tabla de gating A1→B/C)

| Concepto | Puerta | Computable con obs+card-data HOY | Bloqueante | Destino |
|---|---|---|---|---|
| Prize-trade swing/lethal/HP | reward | ✅ (HP/energías en obs) | — | C1 directo |
| Prize-trade `prize_yield` correcto (1/2/3) | reward | 🔴 NO | falta `ex/megaEx` en card-data = **B1** | C1 tras B1 |
| Prize-checking propio por eliminación | belief | ✅ (decklist + ids visibles) | — | C2 |
| Prize-checking: ID exacto de carta prizada | belief | 🔴 NO | `prize[]` es opaco (solo longitud) | **backlog** |
| Prize-checking del rival | belief | 🔴 NO | no conozco su deck (info imperfecta) | **backlog** |
| Sequencing (i)+(ii) draw-before / attack-last | prior | ✅ (OptionType en obs) | — | C1 directo (más barato) |
| Sequencing (iii) negar info / no-descartar-singleton | prior | 🟡 parcial | semántica de carta (lista corta por mazo) | C1 parcial |
| Rol beatdown/control (de tablero) | prior→reward/belief | ✅ (premios+readiness) | — | C1 |
| Rol por arquetipo anticipado | prior | 🔴 NO | requiere belief de deck rival | **backlog** (con C2/B3) |

---

## 6 · Backlog explícito (NO computable con este obs — honestidad anti-falso-positivo)

1. **Identidad exacta de cartas premiadas (propias o rival).** El obs entrega `prize[]` como
   lista opaca de longitud N; los elementos vienen `{}` (verificado en replay real). Solo se
   deduce el MULTISET no-visto y la probabilidad por hipergeométrica, nunca el ID concreto
   salvo el caso degenerado `unseen == prizes_left`. No hay forma de subir esto sin que el
   motor exponga ids de premios (no lo hace).
2. **Prize-checking / lectura del arquetipo del RIVAL.** Info imperfecta pura: no veo su mano
   ni su deck. Requiere un belief-state aprendido sobre arquetipos (puerta belief, C2 + panel
   meta B3), no una regla cerrada. Fuera de A1.
3. **Modificadores de premio por carta (Legacy Energy −1, Lillie's Pearl −1).** Computables
   en cuanto B1 dé los ids + `name`, pero hoy `cards.json` no trae `name` → dependen de B1.
4. **Rol "por matchup" anticipado** (saber que es control desde turno 1): depende de (2).

---

## 7 · Diff contra la heurística actual del campeón (qué cambia Leon v1.5)

- **Hoy (Leon v1 = sample Dragapult):** la lógica de prize-trade existe pero (a) está
  **hard-codeada a Dragapult** (ids Dreepy/Drakloak/Dragapult, Phantom Dive 154…), (b) usa
  `card_table.megaEx/.ex` de **cg-lib** (no disponible dict-only en `agent/main.py`),
  (c) el "neto" es implícito (`score -= 1200` cuando voy cerrando) y no resta el premio que
  REGALO al exponer mi atacante.
- **Leon v1.5 aporta:** (1) `prize_yield` desde **tabla estática propia** (B1) → funciona
  dict-only y para cualquier mazo; (2) **NETO explícito** (`− prize_yield(mi_atacante)·λ`);
  (3) **sequencing genérico** (draw-before-search, attack-last) por OptionType, no por ids;
  (4) **selector de rol de tablero** que reescala λ. Todo esto SIN ML, sobre el rule-based.
- **Precondición dura:** sin B1 (card-data con ex/megaEx), el punto (1) cae y prize-trade
  queda ciego al rule-box. **B1 es la ruta crítica antes de C1.**

---

## 8 · Verificación (estado honesto)

- **A1 = spec, no se corrió nada.** No hay GO ni claim de "funciona/gana" aquí.
- La verificación real es **Bloque C** (A/B contra Leon v1 + panel meta), con la disciplina:
  ningún GO con N<60, las primeras ~20 partidas mienten, A/B local = filtro no juez.
- Smoke direccional posterior (cuando se encode C1), comando exacto a correr (no corrido aún):
  `python experiments/ab_harness.py run_ab agents_official/dragapult_sample agents_official/leon_v1_5_prizeaware --games 20`
  → etiquetar **DIRECCIONAL, no GO** (N=20). El A/B largo lo corre la otra sesión en docker;
  no saturar.
