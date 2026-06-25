---
source: Transcripciones de vídeo (whisper/captions) — CFB Edge (Isaiah Bradner), Play! Pokémon oficial, Sorvirin
url: youtube — bhstuMgyEL4, _W6m6ocV0gI, fH_Vuhgid3M, sRiY8Uk1vr0
tier: free
concept: prize-trade, prize-checking, sequencing, testing
confidence: alta (transcripción primaria leída; atribución verificada)
rotates: parcial (ejemplos de cartas rotan; los métodos no)
extracted: 2026-06-24
---

# Enriquecimiento por vídeo — operacionaliza H1/H2/H4/H5

> Destilado de 4 transcripciones primarias (audio→texto). Solo recojo lo que AÑADE sobre las
> fichas escritas, no lo que repite. Los transcripts crudos viven en scratchpad (copyright),
> NO en el repo. Atribución verificada al leer el texto (corrige el error del curador: el vídeo
> nPN8G1em4QQ NO es Tricky Gym sino "Jank Play TCG/Landon", nivel principiante → descartado).

## 1. Prize MAPPING como plan adaptativo de 6 premios (CFB Edge — Isaiah Bradner) → upgrade de H1/H2

Lo NUEVO frente a H1 (que valoraba el net de UN KO): el top no valora KOs sueltos, **planifica los 6
premios desde el turno 1 y re-planifica cada turno/acción**.

```python
# Plan completo de los 6 premios, no KO miope. Se RECOMPUTA cada turno y tras cada acción (mía o rival).
def prize_map(state):
    plan = []                                  # secuencia de KOs objetivo hasta sumar 6 premios
    remaining = 6 - state.my_prizes_taken
    # backward: ¿qué secuencia de KOs alcanzables suma 'remaining' en menos turnos?
    plan = cheapest_ko_sequence_to(remaining, state)   # p.ej. [1 en Comfey T2, 1, 2 en ex, finish 2]
    return plan

def turn_goal(state, plan):
    # "¿qué ataque al FINAL de este turno me deja en mejor posición para el plan?"
    return best_attack_keeping_map_on_track(state, plan)

def map_is_feasible(plan, state):              # GATE de recursos: un plan sin recursos es inútil
    return (enough_gust_effects(plan, state)        # Boss/Counter Catcher para alcanzar los targets
            and enough_energy(plan, state)
            and enough_recovery(plan, state))       # Night Stretcher/Super Rod: no quedarse sin gas
```

**Heurística H1b (P0):** mantener un `prize_map` (secuencia objetivo de KOs), recomputarlo cada turno,
y elegir la jugada del turno por "¿mantiene el mapa en pista?". **Gate de factibilidad**: descartar
mapas sin recursos (gusting + energía + recovery). **Chequeo de derrota**: antes de adjuntar
energía/usar el último Boss, preguntar "¿esto me puede deckear?" / "¿el rival puede dejar algo que no
puedo noquear?". → conecta directo con el modo de derrota dominante de Alakazam (deck-out) y con `kb_draw`.

## 2. Prize CHECKING como algoritmo de belief con sistema (CFB Edge) → upgrade de H4

Lo NUEVO frente a H4 (que daba la hipergeométrica): el **procedimiento concreto** de actualización y
que el belief se actualiza en DOS eventos, no solo en búsquedas.

```python
# Nivel "hard" (el que usa el top en torneo). En la 1ª búsqueda categoriza TODO el mazo.
def prize_check_first_search(deck_view):
    front = [c for c in deck_view if c.type in ("pokemon","energy")]   # empuja al frente
    back  = [c for c in deck_view if c.type in ("supporter","stadium","oneoff")]
    seen_counts = count(front) + count(back)
    # premiadas = copias_totales_conocidas - copias_vistas_en_mazo
    prized = {cid: total[cid] - seen_counts.get(cid, 0) for cid in total}
    return prized

# El belief se ACTUALIZA en 2 eventos (no solo búsquedas): tras cada search Y al TOMAR premios.
def on_take_prizes(belief, prizes_taken_cards):
    for c in prizes_taken_cards: belief[c] = "in_hand_now"   # bug clásico del top: olvidar anotarlo
    return belief
```

**Heurística H4b (P1):** prize-check estructurado por categorías en la 1ª búsqueda (Pokémon/energía vs
supporters/stadiums/one-offs), priorizar contar las cartas-llave (gusting, recovery, atacante clave),
y **recomputar el belief también al tomar premios** (no solo al buscar). Decisión derivada: si una
pieza clave está probablemente premiada, cambiar de plan ANTES de comprometer recursos (ej. no
descartar la mano por un Pokémon que está premiado).

## 3. Sequencing — orden por garantía de efecto (Play! Pokémon oficial) → detalle operativo de H5

Lo NUEVO frente a H5: regla de orden concreta y verificable.

```python
# 1) Búsquedas de efecto NO garantizado (Capturing Aroma, Great Ball) ANTES que las garantizadas
#    (Nest Ball, Ultra Ball): maximiza información antes de comprometer.
# 2) "Thin before draw": saca cartas que NO quieres robar (energía vía Primal Turbo) ANTES del
#    draw-supporter, para no robarlas. Adelgazar el mazo mejora las odds de fin de partida.
def order_search_actions(actions):
    return sorted(actions, key=lambda a: (a.effect_guaranteed,         # no-garantizado primero
                                          a.thins_unwanted_before_draw))  # thin antes de draw
```
**Refina H5:** además de "draw-before-search", añadir "search-no-garantizado antes que garantizado" y
"thin lo que no quieres robar antes del draw-supporter".

## 4. Protocolo de testing (Sorvirin) → refuerza la METODOLOGÍA, no el agente

Mayormente práctica humana, pero 2 cosas transfieren a NUESTRO proceso de A/B:
- **"10-20 partidas antes de cambiar una sola carta"** y "entender POR QUÉ está cada carta antes de
  tocarla" → es exactamente nuestro gate de tamaño de muestra (N<60) y la poda Reklev. Cita-able en el report.
- **"¿cuál es el resultado óptimo de ESTE turno?"** en cada decisión crucial → mismo framing que el
  turn-goal del prize-map (#1). Útil como objetivo por turno.
- El resto (no autopilotar en ladder, simular Swiss, salud) es para Fran si juega a mano, no para el bot.

## Caveats / honestidad

- ⚠️ Ejemplos de cartas (Lumineon V, Pikachu EX, Lugia VSTAR, Comfey, Mew VMax) **rotan** y el pool de
  cabt ≠ Standard → quédate con el MÉTODO, no con las cartas.
- Atribución: CFB Edge = Isaiah Bradner (top player, serie Edge de ChannelFireball); Sequencing = canal
  oficial Play! Pokémon; Sorvirin = creador competitivo. Verificadas al leer el contenido.
- `azulgg-pickdeck` (278 palabras) demasiado corto para destilar; `jank/tricky` descartado (principiante
  + mal atribuido). OmniPoke sin captions → no transcrito.
- Confianza alta en los métodos; los transcripts crudos NO se commitean (copyright), solo esta destilación.
