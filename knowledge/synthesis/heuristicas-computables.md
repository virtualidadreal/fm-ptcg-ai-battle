---
doc: heuristicas-computables
tier: synthesis
fuentes: knowledge/free/*.md (12 fichas) + verdicts del verificador adversarial
extracted: 2026-06-23
ordenado_por: valor para un agente rule-based de info imperfecta (cabt)
---

# Heurísticas computables — documento maestro accionable

> Destilación de las 12 fichas `free/` a reglas implementables para el motor **cabt**.
> Cada heurística trae: enunciado, pseudocódigo/condición, variable de estado que tocaría,
> y prioridad (P0 / P1 / P2). ⚠️ marca dependencia de meta que rota (NO hardcodear).

---

## 🚨 CAVEAT DE TRANSFERENCIA (leer antes de implementar)

**El pool de cabt (~2000 cartas, reglas ajustadas) NO es Standard completo.** Casi todo lo
"meta-específico" de las fichas (shares de Limitless/Trainer Hill, listas Dragapult/Raging
Bolt, skeletons 4-1-3 de Charizard, conteos COPY_PRIOR como "Rare Candy 3-4") **no transfiere
y puede ser activamente engañoso** dentro de cabt. Prioriza **conceptos** sobre **listas**.

Qué SÍ transfiere (úsalo): la matemática de prize-trade (valor neto de KO), la hipergeométrica
de prize-checking y consistencia, la legalidad pública de Counter Catcher (estado, no carta),
el ordenamiento de fases del sequencing, y el belief-state bayesiano sobre arquetipo/prizes.
Estos son invariantes de la mecánica Rule Box + info imperfecta, no del formato.

**Honestidad table-stakes vs edge real:**
- **Table-stakes** (cualquier motor decente ya lo hace; no es ventaja): contar premios
  restantes, sumar daño, asignar prize_yield 1/2/3 por tipo, comprobar legalidad de cartas.
  *Leon v1 ya computa prize_yield 1/2/3.* No te diferencia.
- **Edge real** (donde ganamos partidas): valorar KOs como **net trade** y no binario;
  penalizar exponer atacante en rango de KO; mantener belief-state de cartas premiadas y de
  arquetipo rival; explotar Counter Catcher como ventaja-condicional-por-ir-detrás; ordenar
  jugadas para minimizar commitment irreversible. *A1 tiene net-prize construido pero inerte
  para tableros single-prize* — ese es exactamente el edge a activar (P0 abajo).

**Regla de oro:** si una heurística depende de un número de meta concreto, leelo de la config
del meta vigente de cabt (medido in-engine), nunca del valor citado en la ficha.

> 🎥 **Enriquecimiento por vídeo (24 jun, transcripción primaria):** `free/video-enrichment-2026-06-24.md`
> upgradea tres heurísticas con material de élite (CFB Edge/Isaiah Bradner, Play! Pokémon oficial):
> **H1b** prize-map adaptativo de 6 premios (plan completo recomputado cada turno + gate de recursos +
> chequeo de deck-out, ata directo con `kb_draw`); **H4b** prize-checking como algoritmo por categorías
> que actualiza el belief también AL TOMAR premios; **H5+** orden search-no-garantizado-antes-que-garantizado
> y thin-antes-del-draw. Métodos transfieren; ejemplos de cartas rotan.

---

## P0 — núcleo del edge (implementar primero)

### 1. Valor NETO de un KO (no binario) — `prize-trade`
**Enunciado:** el valor de un KO = premios que tomas − premios que concedes cuando te devuelven
el golpe. +1 bueno, −2 desastre. Entre KOs alcanzables este turno, elige el de mayor net;
rechaza net<0 si existe alternativa ≥0.

```python
PRIZE_VALUE = {"single":1, "ex":2, "v":2, "vstar":2, "mega_ex":2, "vmax":3, "tag_team_gx":3}

def net_prize_value(my_attacker_type, target_type):
    return PRIZE_VALUE[target_type] - PRIZE_VALUE[my_attacker_type]   # gano − concedo

def choose_ko(reachable_kos):  # [(target, my_attacker_type, target_type)]
    return max(reachable_kos, key=lambda k: net_prize_value(k.my_attacker_type, k.target_type))
# regla: si net_prize_value(best) < 0 y existe alternativa >=0, NO ataques ese target.
```
**Estado cabt:** tipo+`prize_value` de cada Pokémon en juego (mío y rival); lista de KOs
alcanzables dado el daño disponible este turno.
**Nota de implementación:** la tabla PRIZE_VALUE es table-stakes; *Leon v1 ya la tiene*. El edge
es la **resta neta + selección por net**, y que funcione también cuando mi tablero es
single-prize (*donde A1 hoy queda inerte*). Caveat de la ficha: `concede` asume devolución de KO
con certeza — es probabilístico; trátalo como esperanza, no como hecho (ver reward-spec).

### 2. Penalizar exponer atacante en rango de KO rival — `prize-trade` + `reading`
**Enunciado:** antes de comprometer un atacante multi-premio al activo, comprueba si el rival
puede noquearlo el próximo turno (energía visible ≥ coste de su mejor ataque, o spread
alcanza tu HP restante). Si sí y le concedes ≥2, penaliza fuerte / busca alternativa.

```python
def incoming_attack_threat(opp_active, opp_attached_energy):
    # daño que el rival puede hacer YA según energía adjunta visible
    return max_damage_with(opp_active, attached=opp_attached_energy)

def attacker_in_ko_range(my_active, opp_active, opp_attached_energy):
    return incoming_attack_threat(opp_active, opp_attached_energy) >= my_active.hp_remaining

def exposure_penalty(my_active, opp_active, opp_energy):
    if attacker_in_ko_range(my_active, opp_active, opp_energy):
        return PRIZE_VALUE[my_active.type]      # concedería este nº de premios
    return 0
```
**Estado cabt:** `hp_remaining` de mi activo, energía visible adjunta al activo/banca rival,
tabla de costes de ataque del pool. Belief sobre energía oculta si no es observable.
**Por qué P0:** es la otra mitad del prize-trade que los motores ignoran — no basta con tomar
buenos KOs, hay que no regalar el devolverlo. Conecta directo con el term de reward de exposición.

### 3. Counter Catcher / modo "behind" como ventaja condicional — `tempo` + `prize-trade`
**Enunciado:** Counter Catcher (Item) es **legal solo si `my_prizes_remaining > opp_prizes_remaining`**
(vas por detrás). Como es Item, gustea sin gastar el slot de Supporter → encadena
gusting + draw-supporter + KO el mismo turno. El contador de premios es **público**, así que
la legalidad es computable con certeza incluso bajo info imperfecta.

```python
def can_play_counter_catcher(state):                     # guard booleana dura, estado público
    return state.my_prizes_remaining > state.opp_prizes_remaining

def gust_plan(state, hand):
    target = best_gust_target(state.opp_bench)            # KOable / alta vulnerabilidad
    if target is None: return None
    if can_play_counter_catcher(state) and "counter_catcher" in hand:
        return Plan(gust="counter_catcher", supporter_free=True,  target=target)  # robo intacto
    if "boss" in hand and not state.supporter_used_this_turn:
        return Plan(gust="boss",            supporter_free=False, target=target)  # gasta Supporter
    return None
```
**Estado cabt:** `my_prizes_remaining`, `opp_prizes_remaining`, `supporter_used_this_turn`,
`opp_bench`, copias de catcher/boss accesibles (mano + contadas en mazo).
**Edge:** un agente que sabe "ir detrás desbloquea jugadas" valora KOs cedidos de forma no-naive.
Subir belief de que el rival TIENE catcher cuando él va detrás (la carta solo le sirve detrás).
**Caveat ficha (verificado):** el equivalente exacto de Counter Catcher en cabt puede no existir
o llamarse distinto — implementa el **patrón** (gusting-libera-supporter + guard por premios),
mapeado a las cartas reales del pool de cabt, no a "Counter Catcher PAR 160".

---

## P1 — info imperfecta y planificación de turno (alto valor, depende de tener belief-state)

### 4. Belief-state de cartas premiadas (prize-checking) — `prize-checking` + `consistency`
**Enunciado:** mantén `prize_belief[card_id]` sobre tus propios premios ocultos; recomputa tras
cada search/draw/discard/mill y tras cada KO que tome premios. Hipergeométrica sobre el pool
no visto, no sobre 60 fijo.

```python
from math import comb
def prob_at_least_one_prized(copies, prizes_remaining, unknown_pool):
    # P(>=1 de las 'copies' está en los 'prizes_remaining' del pool no visto)
    if copies > unknown_pool: return 1.0
    return 1 - comb(unknown_pool - copies, prizes_remaining) / comb(unknown_pool, prizes_remaining)
# 1 copia / 60 / 6 premios ≈ 10% premiada. Recomputa con unknown_pool decreciente cada search.
```
**Estado cabt:** `prizes_remaining`, `unknown_pool` (mazo + premios aún no vistos),
`known_counts[card_id]` de copias ya localizadas.
**Uso:** si `belief(pieza_clave)` supera umbral, sube prioridad de redundancia/recovery o de su
alternativa (p.ej. buscar el tutor en vez del Pokémon probablemente premiado).
**Caveat ficha:** la fuente primaria (TCGplayer "3 principios") NO se pudo verificar; los
ejemplos de cartas pueden estar parafraseados. La **fórmula** sí está verificada contra lastlegume.
Una ficha invierte la atribución del 80.85% (es el número NAIVE pre-corrección de mulligan) — usa
la fórmula directa, no copies los porcentajes redondeados.

### 5. Ordenar el turno por fase + minimizar commitment irreversible — `sequencing`
**Enunciado:** modela el turno como cola de acciones ordenada por fase ordinal, desempatando por
EV. Roba antes de buscar (revela cartas antes de comprometer); attach de energía como **última**
acción antes de atacar; disrupción (gusting/Iono) **antes** de revelar fuerza (Tool/energía).

```python
PHASE = {  # ordinal: menor = antes
  "draw_refresh":0, "disruption_forcing_opp_decision":1, "directed_search":2,
  "reversible_setup":3, "attach_energy_or_tool":4, "attack":5,
}
def order_turn(actions, state):
    return sorted(actions, key=lambda a: (phase(a), -expected_value(a, state)))
# Principio 1: Supporters de robo (Research/Iono) ANTES de búsqueda dirigida (Ultra Ball/Artazon).
# Principio 2: attach de energía = última acción (minimiza commitment), salvo que dispare ability +EV.
# Principio 3: disrupción ANTES de revelar Tool/energía (rival decide con incertidumbre alta).
```
**Estado cabt:** acciones legales del turno con flags `reveals_new_cards_to_self`,
`forces_opponent_decision`, `is_search`, `attaches_tool/energy`; función `expected_value`.
**Caveat ficha:** los predicados de fase (`is_search`, etc.) **deben construirse desde la base de
cartas de cabt**, no de la fuente. Implementable como esqueleto, no ejecutable tal cual. `opp_belief_uncertainty`
del Principio 3 requiere modelo de creencia del rival (variable no trivial — ver #7).

### 6. Consistencia / mulligan como gate de deckbuild y de mid-game — `consistency`
**Enunciado:** P(mulligan) = C(60−K,7)/C(60,7) con K = nº de Basics. Recomputa siempre con
`deck_size` decreciente y known_counts, nunca con 60 fijo. Elige draw supporter por EV: Research
si mano mala (roba 7), Iono si tus premios restantes son altos o quieres disrupción.

```python
from math import comb
def p_mulligan(basics_in_deck, deck_size=60):
    return comb(deck_size - basics_in_deck, 7) / comb(deck_size, 7)

def p_see_at_least_one(copies, draw_n, deck_size):
    return 1 - comb(deck_size - copies, draw_n) / comb(deck_size, draw_n)
# P(ver >=1 de un 4-of en 7) = 39.95%. Cada mulligan = +1 carta al rival (penalizar en reward).
```
**Estado cabt:** `basics_in_deck`, `deck_size` (decreciente), `known_counts`, `my_prizes_remaining`
(para elegir Iono vs Research).
⚠️ **Rota:** el umbral "8–12 Basics" y las cartas concretas (Iono/Research/Pokégear) son
contextuales del Standard — en cabt deriva el conteo objetivo del pool real. La **matemática** no rota.

---

## P2 — inferencia de rival y arquetipo (mayor valor pero requiere belief-state maduro)

### 7. Belief bayesiano sobre arquetipo rival + colapso por carta-firma — `reading` + `archetypes` + `deckbuilding`
**Enunciado:** mantén distribución sobre el arquetipo rival {aggression, control, mill, stall};
inicialízala con un prior y recolápsala con cada carta vista. La primera línea evolutiva colapsa
fuerte el prior. Lee también por **no-jugada** (turno sin Supporter ⇒ P(mano fuerte) *= 0.5).

```python
def bayes_update(belief, card_seen, usage):     # usage[card][arch] = P(carta | arch)
    post = {a: belief[a] * usage.get(card_seen, {}).get(a, 1.0) for a in belief}
    z = sum(post.values()) or 1.0
    return {a: p / z for a, p in post.items()}

def hidden_copies(card, archetype_skeleton, seen):
    return max(0, archetype_skeleton.get(card, 0) - seen)   # si llega a 0, amenaza neutralizada

def p_opp_has_out(hidden_copies_k, unknown_zone_n, draws):
    if hidden_copies_k == 0: return 0.0
    return 1 - comb(unknown_zone_n - hidden_copies_k, draws) / comb(unknown_zone_n, draws)
```
**Estado cabt:** `belief.archetype` (dist), cartas vistas del rival (descarte+tablero+jugadas),
`unknown_zone_size`, `supporter_played_this_turn` del rival.
**Decisión derivada:** haz la jugada defensiva y obliga al rival a probar el out estrecho cuando
`p_opp_has_out < ~0.2`.
⚠️⚠️ **Rota fuerte y NO transfiere a cabt tal cual:** skeletons (Charizard 4-1-3), priors de share
y `usage[card][arch]` salen del meta de Standard. En cabt **construye el prior y el usage midiendo
partidas in-engine**, no de Limitless/Trainer Hill. El **método bayesiano** transfiere; los números no.
**Caveat ficha:** `meta_distribution()`, `score_features()`, `infer_archetype()` son **stubs** en
las fuentes (feature-extractor sin definir). El bloque hipergeométrico y el conteo de copias SÍ son
implementables; el clasificador de arquetipo necesita que definas tú la extracción de features.

### 8. Asignación dinámica de rol BEATDOWN vs CONTROL — `archetypes`
**Enunciado:** si vas por delante en premios y puedes OHKO, juega BEATDOWN (search atacante +
aceleración + OHKO). Si no puedes ganar la carrera (rival OHKO y tú no, o prize_diff<−1), pivota
a CONTROL/STALL (niega recursos, cura, attrition/deck-out). Empate de velocidad: el unfavored roba
tempo siendo beatdown.

```python
def assign_role(state):
    if state.prize_diff > 0 and state.can_ohko_active:        return "BEATDOWN"
    if state.my_speed < state.opp_speed - 1:                  return "BEATDOWN"
    if state.opp_can_ohko_me and not state.can_ohko_active:   return "CONTROL"
    if state.prize_diff < -1:                                 return "CONTROL"
    return "BEATDOWN" if state.matchup_fav < 0.5 else "CONTROL"  # unfavored roba tempo
```
**Estado cabt:** `prize_diff`, `can_ohko_active`, `opp_can_ohko_me`, `my_speed`/`opp_speed`
(estimadas), `matchup_fav` (belief, reordenable).
**Caveat ficha (importante):** las funciones de velocidad/favorabilidad (`est_turns_to_first_ohko`,
`prior_winrate`, `belief_opp_*`) son **stubs** presentados con sintaxis Python — son nombres, no
implementación. Y una ficha **fabricó una cita** atribuida a Flipside ("rol intrínseco al diseño del
mazo"): NO existe en la fuente. Trata `matchup_fav` como prior reordenable, nunca verdad fija.

### 9. Poda Reklev de deckbuild + regla de las 10 partidas — `deckbuilding` + `top-players-theory`
**Enunciado:** trackea `card_usefulness[card]` como EMA de contribución a victorias; si en ~10
partidas no aporta, córtala (dead draw). Antes de optimizar daño, asegura setup: si el mazo no
puede funcionar (atacante con energía + draw + búsqueda + gusting), prioriza setup.

```python
def update_card_usefulness(ema, card, contributed, alpha=0.2):
    ema[card] = (1-alpha)*ema.get(card,0.5) + alpha*(1.0 if contributed else 0.0)
    return ema  # si ema[card] -> ~0 tras N juegos, candidata a corte

def deck_function_ok(deck):  # checklist booleano JustInBasil — table-stakes, no edge
    return (has_attacker_with_energy(deck) and has_draw_supporter(deck)
            and has_pokemon_search(deck) and has_gusting(deck))
```
**Estado cabt:** historial de partidas (offline, para deckbuild), no estado de turno.
**Caveat ficha:** los pesos `deck_function_score` (1.0/0.5/0.3/0.2/−0.5) son **inventados**, no
citados — flags estructurales razonables, no ratios empíricos. La cita "Consistency is the goal"
está **misatribuida a Klaczynski** (es de un autor tercero de 60cards analizando su mazo). Usa la
estructura, descarta las credenciales infladas.

---

## ⚠️ Heurísticas dependientes de META — NO hardcodear (todas de fichas `meta`/`deckbuilding`)

Estas vienen de Limitless / Trainer Hill / meta-snapshot-2026-06 y **rotan cada set**. En cabt el
"meta" es el de cabt: mídelo in-engine. Lista de lo que NUNCA debe hardcodearse:

- ⚠️ `meta_prior` / shares (Dragapult 8.58%, Mega Greninja 43.91% WR, etc.) — recolectar en cabt.
- ⚠️ matchup matrix `MATRIX[mine][theirs]` — no transitiva; medir, no copiar.
- ⚠️ skeletons y COPY_PRIOR (Rare Candy 3-4, Boss 2-4, Arceus VSTAR 2-3...) — del pool de cabt.
- ⚠️ listas de mazos a batir (Raging Bolt, Snorlax Stall, Gholdengo) — irrelevantes en cabt.
- ⚠️ ventaja going-first/going-second y umbrales mágicos (0.15, HP≤60 por Phantom Dive) — re-derivar.

**Errores verificados en las fichas meta (no replicar):** confusión jugadores↔partidas (18.537
jugadores ≠ partidas; reales ~41.105); `meta_prior` que no suma 1 con un `+0.40` relleno arbitrario
en "other"; credencial inflada de Limitless como "socio oficial de TPCi" (su propio footer lo
desmiente); dataset IEEE presentado como verificación independiente cuando deriva de Trainer Hill
(circular) y está tras paywall.

---

## Tabla resumen de prioridad

| # | Heurística | Concepto | Prio | ⚠️ rota | Estado cabt clave |
|---|-----------|----------|------|--------|-------------------|
| 1 | Net prize value de KO | prize-trade | P0 | no | prize_value por Pokémon en juego |
| 2 | Penalizar exposición a KO | prize-trade/reading | P0 | no | hp_remaining, energía visible rival |
| 3 | Counter Catcher / behind | tempo | P0 | no¹ | my/opp_prizes_remaining, supporter_used |
| 4 | Belief cartas premiadas | prize-checking | P1 | no | unknown_pool, known_counts |
| 5 | Ordenar turno por fase | sequencing | P1 | no² | flags de acción legal |
| 6 | Mulligan / consistencia | consistency | P1 | parcial | basics_in_deck, deck_size |
| 7 | Belief arquetipo rival | reading/archetypes | P2 | sí | belief.archetype, cartas vistas |
| 8 | Rol BEATDOWN/CONTROL | archetypes | P2 | parcial | prize_diff, speeds, matchup_fav |
| 9 | Poda Reklev / setup gate | deckbuilding | P2 | no³ | historial de partidas (offline) |

¹ la mecánica es estable; la carta concreta debe mapearse al pool de cabt.
² el método no rota; los predicados de carta se construyen del pool de cabt.
³ el método no rota; los pesos citados son inventados — re-calibrar.
