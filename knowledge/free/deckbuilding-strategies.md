---
source: JustInBasil's Pokémon TCG Resources
url: https://www.justinbasil.com/guide
tier: free
concept: deckbuilding
rotates: false
extracted: 2026-06-23
---

## Qué es

El "Deck Building Guide" de JustInBasil es el manual de construcción de mazos de referencia
en la comunidad competitiva de Pokémon TCG (formato Standard). Aunque las LISTAS de mazos
rotan, este corpus codifica los PRINCIPIOS DE DECISIÓN invariantes: qué estrategia persigue
un mazo, qué rol cumple cada carta, qué esqueleto de conteos garantiza consistencia, y cómo
podar el mazo con testing. Para un agente de IA con información imperfecta, esto es un PRIOR
estructural: dado un mazo (propio o, parcialmente observado, el rival), permite inferir su
plan de juego y la distribución probable de cartas no vistas.

Páginas verificadas y abiertas:
- https://www.justinbasil.com/guide (índice)
- https://www.justinbasil.com/guide/deck-strategy (4 estrategias)
- https://www.justinbasil.com/guide/deck-structure (esqueleto + roles)
- https://www.justinbasil.com/guide/consistency (conteos de consistencia)
- https://www.justinbasil.com/guide/crafting-your-deck (refinado/poda)
- https://www.justinbasil.com/guide/testing (testing + cita Reklev "10 games")

## Conceptos clave

**Las 4 estrategias (clasificador de arquetipo):**

| Estrategia | Win condition | Mecanismo | Señales de cartas |
|-----------|---------------|-----------|-------------------|
| **Aggression** | Coger las 6 prizes antes que el rival vía KOs decisivos rápidos | Stream constante de atacantes listos para combatir. Dos sub-formas: Direct (KO secuencial 1-a-1) y Spread (reparte daño a varios targets → KOs simultáneos/encadenados) | Muchos atacantes + aceleración de energía + recovery |
| **Control** | Cortar las vías de victoria del rival negándole recursos (energía, trainers, abilities) | Ralentiza el ritmo para ejecutar una segunda estrategia (stall o aggression) encima. Empuja al rival a jugadas desesperadas | Disruption (Marnie/Judge), lock de abilities (Path to the Peak), negación de energía |
| **Mill** | Forzar **deck-out** del rival (no puede robar al inicio de turno) | Descarta activamente cartas del mazo y mano del rival | Cartas de descarte forzado, negación de recursos |
| **Stall** | Negar prizes al rival → empujarlo a deck-out indirecto | Pokémon de HP alto + cartas que remueven/reducen/previenen daño | HP alto, healing, switch, damage prevention, no atacantes propios |

> Nota crítica para el agente: **aggression y stall son DUALES respecto al prize trade**.
> Aggression maximiza KOs propios; stall minimiza KOs sufridos. Mill/Control atacan el RECURSO
> "cartas restantes del mazo" en vez del recurso "prizes". El motor cabt premia prizes; un
> agente que solo razona sobre prizes está ciego ante mill/stall hasta que es tarde.

**Esqueleto canónico (60 cartas):**
- Pokémon: **20** · Trainers: **30** · Energy: **10**
- Los mejores mazos del Standard se desvían **±3** de cada categoría (no más).

**Roles de Pokémon (cada Pokémon es exactamente uno):**
- **Main Attacker** — foco del mazo; reparte/recibe daño del Active rival. Condiciona TODA otra inclusión.
- **Secondary Attacker** — cubre matchups donde el main es inadecuado o contraproducente. No siempre presente.
- **Utility Pokémon** — incluido por su Ability (rara vez ataque); normalmente NO se le mete energía.

**Desglose de los 30 Trainers (rangos típicos):**
- Supporters: 6-12 total → Draw supporters 4-9 · Boss's Orders/gusting 2-4
- Items: 15-20 total → Pokémon Search 8-10 · resto utility (recovery, boost)
- Stadiums: 2-3

**Conteos de consistencia (copias típicas cuando se incluye la carta):**
- Rare Candy: 3-4 (staple en mazos con stage 2) · Pokégear 3.0: 3-4 · Arven: 3-4
- Irida (agua): 3-4 · Adaman: 3-4 · Arceus VSTAR: 2-3 · PokéStop: 2-3
- Forest Seal Stone: 1-2 · Lumineon V: 1 (a veces 2) · Oranguru: normalmente 0
- Energy: equilibrar para NO robar solo energía.

**Filosofía de poda (Tord Reklev, vía sección Testing):**
> "Play a lot of games with your deck and see which cards you're actually using to win games.
> If you play ten games and you still haven't used your card—then you should probably drop that card."
- Refinado estructural: si tu lista se aleja del esqueleto canónico, recorta lo que la alejó.
- "Instead of running 4 copies of a card, consider 3" en las cartas menos críticas.
- Buscar cartas que cumplan múltiples funciones para liberar slots.

**4 preguntas de testing (qué monitorizar):**
1. ¿Cartas que necesitaba y no estaban disponibles cuando hacían falta?
2. ¿Cartas que aparecen demasiado a menudo?
3. ¿Mis atacantes ganan el prize trade?
4. ¿Cartas que ojalá estuvieran en el mazo?

## → Heurística computable

```python
# ─────────────────────────────────────────────────────────────────────────────
# 1) CLASIFICADOR DE ARQUETIPO (sobre el mazo propio Y como creencia sobre el rival)
#    Variables de estado observables: cartas vistas, energía en juego, HP de bench/active,
#    descartes forzados al rival, abilities-lock activos.
# ─────────────────────────────────────────────────────────────────────────────
def infer_archetype(deck_or_belief) -> str:
    s = score_features(deck_or_belief)   # features extraídas de cartas vistas
    # Señales (cada una en [0,1], normalizada por cartas vistas)
    aggr  = s.attacker_density + s.energy_accel + s.recovery
    ctrl  = s.disruption + s.ability_lock + s.energy_denial
    mill  = s.forced_discard
    stall = s.high_hp + s.healing + s.damage_prevention - s.attacker_density
    return argmax({"aggression": aggr, "control": ctrl, "mill": mill, "stall": stall})

# ─────────────────────────────────────────────────────────────────────────────
# 2) PRIOR DE COMPOSICIÓN para Bayesian belief sobre el mazo RIVAL (info imperfecta)
#    Antes de ver cartas: distribuir 60 cartas según esqueleto canónico ±3.
# ─────────────────────────────────────────────────────────────────────────────
DECK_SKELETON_PRIOR = {           # medias; sigma≈3/√3 ≈ 1.7 por categoría
    "pokemon": 20, "trainers": 30, "energy": 10,
}
TRAINER_SUBPRIOR = {              # dentro de los 30 trainers
    "draw_supporters": (4, 9), "boss_gust": (2, 4),
    "pokemon_search": (8, 10),  "stadium": (2, 3),
}
# Copias por carta-clave vista una vez → P(>=k copias) altísima:
COPY_PRIOR = {  # si veo 1, espera el rango (estima cuántas quedan en deck)
    "rare_candy": (3,4), "pokegear": (3,4), "arven": (3,4),
    "boss_orders": (2,4), "arceus_vstar": (2,3), "lumineon_v": (1,2),
    "forest_seal_stone": (1,2),
}
def expected_remaining(card, seen_count):
    lo, hi = COPY_PRIOR.get(card, (1,1))
    return max(0, (lo+hi)/2 - seen_count)   # cartas aún en deck/mano/prizes

# ─────────────────────────────────────────────────────────────────────────────
# 3) ELECCIÓN DE OBJETIVO según arquetipo DETECTADO (qué recurso atacar)
# ─────────────────────────────────────────────────────────────────────────────
def target_resource(my_arch, opp_arch):
    # contra stall/mill el prize-trade clásico falla → vigilar deck-out propio
    if opp_arch in ("stall", "control"):
        return "preserve_own_deck_count"   # evita over-drawing; vigila deck-out
    if opp_arch == "mill":
        return "race_prizes_fast"          # gana por prizes antes del deck-out
    return "win_prize_trade"               # default: maximiza KOs netos
```

Variables de estado mínimas para el agente:
`attacker_density`, `energy_in_play`, `forced_discards_on_opp`, `own_cards_left`,
`opp_cards_left`, `belief_opp_archetype`, `prize_diff`.

## → Hook de recompensa

El conocimiento toca DOS términos de reward y uno de shaping:

- **Término principal de prize trade** (ya presente en cabt): el clasificador de arquetipo
  CONDICIONA su signo/peso. Contra `stall`/`mill`, `reward += w_deckout * (opp_cards_left⁻¹)`
  y `reward -= penalty * own_overdraw` (penaliza robar de más para no auto-deck-outearse).
- **Shaping de consistencia (mazo propio, fase de deckbuild si el agente arma mazo):**
  `reward += λ * 1[deck_skeleton within ±3 of canonical]`. Penaliza desviaciones grandes
  del esqueleto 20/30/10.
- **Shaping de poda (Reklev):** offline, sobre logs de N≥10 partidas,
  `card_value[c] = P(c usada en partidas ganadas)`; cartas con valor ≈0 tras 10 juegos →
  candidatas a corte. Es una regla de FEATURE SELECTION del mazo, no un reward in-game.

Si el agente NO construye mazo (mazo fijo dado), el único hook activo es el **ajuste del peso
del prize-trade según `belief_opp_archetype`**; el resto es `null`.

## Datos parseables

La fuente es prosa HTML, sin API/export. Lo parseable que entrega:
- **Esqueleto numérico:** `{pokemon:20, trainers:30, energy:10, deviation:±3}`.
- **Rangos de subcategorías de trainers** (ver TRAINER_SUBPRIOR arriba).
- **Tabla de copias por carta** (ver COPY_PRIOR) — extraíble como dict para el prior bayesiano.
- **4 estrategias** como enum: `{AGGRESSION, CONTROL, MILL, STALL}` con sub-tipos de aggression
  `{DIRECT, SPREAD}`.
- Datos de meta/listas reales (rotables) NO viven aquí: usar **limitlesstcg.com** (citado por la
  propia guía en la sección Testing como fuente de resultados de torneo recientes) para listas
  point-in-time del meta actual.

## Caveats / sesgo

- **Formato Standard, no el motor cabt/Kaggle.** Los conteos (20/30/10, Rare Candy 3-4) son del
  TCG físico actual; el reto Kaggle puede usar un pool/formato distinto. Tratar los NÚMEROS como
  priors ajustables, no como verdades absolutas.
- **Cartas nombradas ROTAN** (Lumineon V, Arceus VSTAR, Path to the Peak...). Lo invariante son
  los ROLES y RATIOS, no los nombres. El frontmatter marca `rotates:false` porque los conceptos
  estructurales no rotan, pero las cartas citadas como ejemplo SÍ.
- Varias subsecciones de la guía están marcadas "yet to be updated" para el formato vigente.
- **JustInBasil** es un recurso comunitario (reddit user, sin CV competitivo publicado en la guía):
  autoridad por adopción comunitaria, no por palmarés. La cita de poda SÍ tiene autoría de élite
  (Reklev, ver Fuentes).
- El clasificador de arquetipo es heurístico: muchos mazos son **híbridos** (control+aggression es
  explícito en la fuente). `argmax` duro pierde matiz; mejor mantener distribución de creencia blanda.
- "Ten games" es una regla de pulgar humana para playtesting, no un umbral estadístico calibrado;
  para un agente con miles de self-play games, recalibrar el N (P(uso)≈0 con CI estrecho).

## Fuentes citadas

- **JustInBasil's Pokémon TCG Resources — Deck Building Guide** (índice y subpáginas verificadas):
  https://www.justinbasil.com/guide ·
  /guide/deck-strategy · /guide/deck-structure · /guide/consistency ·
  /guide/crafting-your-deck · /guide/testing
  — Recurso comunitario de referencia (autor: reddit user JustInBasil); el más citado para
  construcción de mazos en Standard.
- **Tord Reklev — filosofía de poda "10 games"** (citada dentro de /guide/testing; origen vídeo
  "Deckbuilding with Tord Reklev"). Credenciales: Tord Reklev es uno de los jugadores más
  laureados de la historia del Pokémon TCG (múltiples campeonatos internacionales / Players Cup;
  perfil: https://limitlesstcg.com/players/86). La regla "si en 10 partidas no usas una carta,
  córtala" es suya, no de JustInBasil.
- **Limitless TCG** (https://limitlesstcg.com) — citado por la guía como fuente de resultados de
  torneo / listas de meta point-in-time (datos rotables, fuera del scope conceptual de este fichero).
