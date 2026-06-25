---
source: Limitless DrawCalc + JustInBasil (Appendix IV / Consistency) + SixPrizes TheMathTCG
url: https://www.justinbasil.com/guide/appendix4
tier: free
concept: consistency
rotates: false
extracted: 2026-06-23
---

## Qué es

**Consistency** = la probabilidad de que un mazo haga lo que quiere hacer cada turno: abrir con una mano jugable (al menos un Basic + idealmente acceso a draw/búsqueda), y encadenar setup. Es un problema de **muestreo sin reemplazo** sobre 60 cartas, gobernado por la **distribución hipergeométrica**. No rota con el meta: la matemática del deck de 60 / mano de 7 / 6 prizes es estructural del juego, no de la lista.

Tres preguntas que la fuente cuantifica:
1. **¿Cuál es mi tasa de mulligan?** (función del nº de Basics).
2. **¿Con qué probabilidad veo ≥1 copia de una carta clave en la apertura?** (justifica el 4-of).
3. **¿Con qué probabilidad tengo acceso a draw/setup turno 1?** (justifica densidad de draw supporters).

DrawCalc (Limitless) implementa esto con inputs categóricos: `Basic Pokémon`, `Good Starters`, `Bad Starters`, `Supporters`, y devuelve: `Mulligan (no Basic)`, `Starting with 2+ Basics`, `≥1 good starter`, `only bad starter`, `Supporter en las primeras 8 cartas`.

## Conceptos clave

**Fórmula hipergeométrica (núcleo de DrawCalc).** Para un deck de `N` cartas con `K` copias del tipo objetivo, robando `n` cartas, la probabilidad de obtener exactamente `x` copias:

```
P(X = x) = C(K, x) * C(N-K, n-x) / C(N, n)
```

donde `C(a,b)` es el coeficiente binomial. La métrica útil casi siempre es **"al menos una"**:

```
P(X >= 1) = 1 - C(N-K, n) / C(N, n)
```

SixPrizes la llama `P(M, N, X)` = prob. de encontrar ≥1 de una carta robando N cartas de un deck de M con X copias.

**Tasa de mulligan** (no robar ningún Basic en la apertura de 7) = caso `x=0`:

```
P(mulligan) = C(60-K, 7) / C(60, 7)    # K = nº de Basics
```

Tabla verificada (recomputada y coincide al céntimo con JustInBasil Appendix IV):

| # Basics (K) | P(mulligan) | P(≥1 Basic) |
|---|---|---|
| 4 | 60.05% | 39.95% |
| 7 | 39.91% | 60.09% |
| 8 | 34.64% | 65.36% |
| 9 | 29.98% | 70.02% |
| 10 | 25.86% | 74.14% |
| 12 | 19.06% | 80.94% |
| 15 | 11.75% | 88.25% |
| 20 | 4.83% | 95.17% |

Regla de oro de la fuente: la mayoría de los top decks corren **8–12 Basics** (rango ~7–11 = "60–80% de NO mulligan"). Más Basics = menos mulligan PERO compite con espacio para consistencia/recursos. Cada mulligan que tomas, **tu rival roba 1 carta extra** → coste directo de card advantage.

**Por qué 4 copias (4-of).** Prob. de ver ≥1 copia en la apertura de 7 según nº de copias (tabla JustInBasil, verificada):

| # copias | P(≥1 en mano de 7) |
|---|---|
| 1 | 11.67% |
| 2 | 22.15% |
| 3 | 31.54% |
| 4 | 39.95% |

Pasar de 1→4 copias casi **cuadruplica** la chance de abrir con la carta (12%→40%). Rendimientos decrecientes pero monótonos: por eso las cartas que quieres ver T1 (draw supporter, Poké Ball, starter clave) van a 4; las situacionales van a 1–2 y se buscan con tutores.

**Draw supporters (Professor's Research, Iono, Colress).** No aumentan el tamaño del deck pero **multiplican cartas vistas por turno**, comprimiendo la varianza. Densidad típica objetivo: que la prob. de tener ≥1 draw supporter en la apertura sea alta. Verificado para "≥1 supporter en 8 cartas":

| # draw supporters | P(≥1 en 8) |
|---|---|
| 8 | 70.6% |
| 10 | 79.0% |
| 12 | 85.3% |

- **Professor's Research**: descarta mano, roba 7. Máxima profundidad, pero quema recursos en mano → mejor con mano vacía/mala.
- **Iono**: ambos barajan mano y roban = (prizes restantes). Draw + disrupción; escala con el progreso del juego (menos prizes propios tomados = roba más).
- **Colress's Experiment**: mira 5, coge 3 al descarte 2. Draw filtrado, sinergia con recuperación desde descarte.

El layering (Pokégear/Lumineon V como tutores de supporter) sube la prob. **efectiva** de acceder a draw por encima de la densidad cruda.

## → Heurística computable

```python
from math import comb

def hyper_at_least_one(N, K, n):
    """P(>=1 éxito) robando n de N con K éxitos. N=deck restante, no 60 fijo."""
    if K <= 0 or n <= 0: return 0.0
    if K > N or n > N:    return 1.0  # saturado
    return 1.0 - comb(N - K, n) / comb(N, n)

def hyper_exact(N, K, n, x):
    return comb(K, x) * comb(N - K, n - x) / comb(N, n)

def mulligan_rate(basics, deck=60):
    return comb(deck - basics, 7) / comb(deck, 7)

# --- Variables de estado del agente (creencia bayesiana sobre el deck oculto) ---
state = {
    "deck_size": int,          # cartas restantes en el propio deck
    "known_counts": dict,      # {card_id: copias_aún_en_deck} actualizado al robar/buscar
    "prized_unknown": int,     # 6 al inicio; cartas en prize pool no vistas
    "basics_in_deck": int,
    "draw_supporters_in_deck": int,
}

# 1) DECISIÓN DE MULLIGAN (forzada por reglas: 0 basics -> mulligan automático)
#    El agente no elige; pero modela el riesgo al construir/evaluar aperturas.

# 2) PROBABILIDAD DE "OUTS" PARA PLANIFICAR EL TURNO
def prob_hit_out(state, n_cards_to_draw, target_card):
    K = state["known_counts"].get(target_card, 0)
    return hyper_at_least_one(state["deck_size"], K, n_cards_to_draw)

# 3) ELEGIR DRAW SUPPORTER por valor esperado de cartas útiles vistas
def expected_useful(state, supporter):
    deck = state["deck_size"]
    if supporter == "research":   draw = min(7, deck)        # descarta mano primero
    elif supporter == "iono":     draw = state["my_prizes_remaining"]
    elif supporter == "colress":  draw = 3                   # de 5 mirados
    useful_density = state["live_outs"] / max(deck, 1)
    return draw * useful_density

# 4) ACTUALIZAR CREENCIA SOBRE PRIZES: una copia de X prizada con prob = copias/deck_total
def prob_card_prized(copies, deck_total=60):
    # ej. 1 copia -> ~10% prizada (6/60). Usar hipergeom. exacta para >1 copia.
    return hyper_at_least_one(deck_total, copies, 6)  # P(>=1 de esas copias en 6 prizes)
```

Condiciones umbral usables como gates de policy:
- `if mulligan_rate(basics) > 0.35: penalizar lista` (≈ <8 basics).
- `if prob_hit_out(state, draw, key_card) < 0.5: jugar carta de búsqueda/tutor antes que draw ciego`.
- Preferir Research si `cards_in_hand` es bajo/muerto; preferir Iono si `my_prizes_remaining` alto y/o quiero disrupción al rival.

## → Hook de recompensa

Toca el término de **consistencia/setup**, no el de prizes directamente:

- `reward += w_setup * 1[setup_completo_turno <= T]` — recompensa por completar setup temprano (correlato directo de aperturas jugables).
- `reward -= w_mulligan * num_mulligans_propios` — penaliza listas/políticas que mulliganean (cada mulligan = +1 carta al rival; modelarlo también como `reward += w_card_adv` al rival).
- **Shaping informacional** (opcional): `reward += w_info * reduccion_entropia_belief_deck` — premia acciones que estrechan la creencia sobre prizes/deck (jugar draw para "ver" cartas). Útil bajo info imperfecta.
- Si el motor cabt ya recompensa solo por win/prizes: `hook = null` para consistencia pura; usar estas probabilidades como **features de la value function / heurística de simulación**, no como reward explícito.

## Datos parseables

- **DrawCalc** (https://limitlesstcg.com/tools/drawcalc): UI con inputs `Basic Pokémon / Good Starters / Bad Starters / Supporters`; outputs `Mulligan (no Basic)`, `2+ Basics`, `≥1 good starter`, `only bad starter`, `Supporter en primeras 8`. No expone API ni parámetros URL documentados; replicable 1:1 con la fórmula hipergeométrica de arriba (no hace falta scrapear).
- **Tablas numéricas** de JustInBasil Appendix IV: tasa de mulligan por #Basics (1→20) y P(≥1 de 4-of en 7). Reproducidas y verificadas vía `math.comb` (coinciden al céntimo).
- **No hay endpoint/export oficial**; la fuente entrega tablas pre-computadas en HTML estático. Recomputar en código es trivial y exacto.

## Caveats / sesgo

- Las tablas asumen **deck de 60 y mano de 7 inicial**; el modelo es exacto para la apertura pero el agente debe recomputar con `deck_size` decreciente y `known_counts` actualizados durante la partida (no usar 60 fijo mid-game).
- DrawCalc usa categorías "Good/Bad starter" que son **juicios subjetivos** del usuario, no propiedades del motor; el agente necesita su propia función de evaluación de starter.
- "Basic en mano" ≠ "apertura buena": un solo Basic malo (alto coste, sin ataque T1) cuenta como no-mulligan pero es una apertura pobre. La métrica de mulligan **sobreestima** la jugabilidad real.
- El consejo "8–12 Basics" es heurística de meta-decks de la era de la guía; el número óptimo depende de cuántos sean *buenos* starters. La matemática (hipergeométrica) NO rota; la recomendación de conteo SÍ es contextual.
- Going first vs second cambia cartas vistas T1 (el que va 2º roba 1 extra en algunas eras de reglas); ajustar `n` en las fórmulas de supporter/out según regla vigente del motor cabt.
- SixPrizes no muestra la fórmula como imagen legible en texto; la notación `P(M,N,X)` y la equivalencia con `1 - C(N-K,n)/C(N,n)` se confirmó recomputando las tablas de JustInBasil y verificando coincidencia exacta.

## Fuentes citadas

- **JustInBasil — Appendix IV: Some Deck Math**: https://www.justinbasil.com/guide/appendix4 (tablas de mulligan y 4-of; recurso de referencia de la comunidad competitiva, mantenido por JustInBasil, autor reconocido de guías de PTCG).
- **JustInBasil — Consistency and Setup**: https://www.justinbasil.com/guide/consistency (3–4 copias de cartas clave, layering de búsqueda/draw, Pokégear/Lumineon V/Irida/Hisuian Heavy Ball).
- **Limitless DrawCalc**: https://limitlesstcg.com/tools/drawcalc (Limitless TCG, plataforma oficial de torneos online y datos de meta; herramienta de probabilidad de apertura).
- **SixPrizes — TheMathTCG: The Probabilities Behind the Opening Hand**: https://sixprizes.com/2013/01/13/themathtcg-the-probabilities-behind/ (notación `P(M,N,X)`, fundamento combinatorio; SixPrizes = sitio histórico de estrategia competitiva de PTCG).
- Verificación independiente de todas las cifras vía `python3 math.comb` (coincidencia exacta con las tablas publicadas).
