---
source: Limitless TCG (play.limitlesstcg.com)
url: https://play.limitlesstcg.com/decks
tier: free
concept: meta
rotates: true
extracted: 2026-06-23
---

## Qué es

Limitless TCG es el agregador de datos de torneo de referencia del Pokémon TCG competitivo. La sección `/decks` es un **metagame tracker**: agrega resultados de cientos de torneos (oficiales + online "Moujii's Dojo", "Turn Zero", etc.) y publica, por arquetipo, **share** (cuota de uso), **win-rate**, **count** (apariciones) y el **score** crudo (W-L-T). En la verificación: 330 eventos, 18.537 jugadores, 41.105 partidas en Standard.

Es la fuente canónica de "qué hay en el meta y cómo de bueno es". Para un agente de info imperfecta esto es la **distribución de prior (creencia)** sobre qué mazo tiene enfrente y cuál es el valor esperado de cada matchup. Las listas rotan con cada set, pero la **estructura de datos y cómo parsearla NO rota** — por eso este fichero documenta el formato, no las cartas.

## Conceptos clave

- **Share (cuota de meta)** = `count / total_partidas_lado`. Es el prior P(oponente = arquetipo X) antes de ver cartas. Top deck verificado: Dragapult 8.58%.
- **Win %** = win-rate global agregado del arquetipo (no condicionado al rival). Dragapult 52.82%, Mega Greninja 43.91% (mazo popular pero perdedor → trampa de novato).
- **Score W-L-T** = numerador crudo (ej. `3870-3299-158`). Permite reconstruir tamaño de muestra y calcular intervalos de confianza / suavizado bayesiano. Imprescindible: un win% del 60% con 10 partidas no vale lo que con 1500.
- **Matchup matrix** (pestaña `Matchups` por arquetipo) = win% **condicionado** vs cada otro arquetipo con su record. Esto es la matriz de pagos del meta-juego (rock-paper-scissors entre mazos).
- **"Combine related deck variants"** = filtro que colapsa variantes (ej. Dragapult vs Dragapult Dusknoir vs Dragapult Blaziken) en un arquetipo padre. Cambia la granularidad del prior.
- **"Other"** = cajón de sastre de mazos <umbral. Suele tener win% bajo (40.94% verificado) — no es un arquetipo, es ruido.
- **Best Finishes** (por arquetipo) = listado de top placements con link a decklist real → fuente de listas "stock" para construir el prior de las 60 cartas.

## → Heurística computable

El agente usa estos datos como **prior y matriz de pagos**, no en runtime de partida sino precomputados:

```python
# 1) PRIOR de creencia sobre el mazo del oponente (antes de ver cartas)
#    parseado de la tabla /decks
meta_prior = { "Dragapult": 0.0858, "Dragapult Dusknoir": 0.0589,
               "Mega Greninja": 0.0582, "Slowking": 0.0577, ... }

# 2) win-rate con suavizado bayesiano (no fiarse de muestras chicas)
def smoothed_winrate(W, L, T, k=30, p0=0.50):
    n = W + L + T
    return (W + k*p0) / (n + k)          # shrink hacia 50% si n pequeño

# 3) belief update: al revelar una carta firma, recolapsa el prior
def update_belief(prior, card_seen, signature_index):
    # signature_index["Dusknoir"] -> {"Dragapult Dusknoir":1.0,...}
    compat = signature_index.get(card_seen)
    if not compat: return prior
    post = {d: prior[d]*compat.get(d, 0.02) for d in prior}
    s = sum(post.values()) or 1e-9
    return {d: v/s for d, v in post.items()}

# 4) valor esperado del matchup = sum_d  P(oponente=d) * winrate(yo vs d)
def expected_matchup_value(belief, matchup_matrix, my_deck):
    return sum(belief[d] * matchup_matrix[my_deck].get(d, 0.5) for d in belief)
```

Variables de estado del agente que estos datos alimentan:
- `belief[opponent_archetype]` — distribución, inicializada con `meta_prior`, actualizada por cartas vistas (info imperfecta).
- `matchup_ev` — pago esperado, guía mulligan/agresividad/líneas de riesgo.
- `archetype_signature` — set de cartas-firma que colapsan creencia (de las decklists de Best Finishes).
- `sample_n` — confianza en cada win% (de W+L+T) → cuánto pesar el dato vs jugar genérico.

Regla de decisión derivada: **share alto ≠ jugar el mazo**; ponderar por `win%` y por matchup contra el prior del campo (Mega Greninja = popular y perdedor).

## → Hook de recompensa

`null` para el reward de partida (Limitless no observa el estado de juego; el reward del agente cabt sale de prize cards / win-loss, no de aquí).

**Sí** alimenta la **función de valor / prior**, no el reward directo:
- `value_prior(state)` — estimación inicial de probabilidad de victoria, sembrada por `smoothed_winrate(arquetipo)` antes de jugar.
- Si el reward es shaped por matchup (curriculum / self-play matchmaking), `matchup_matrix` define la **dificultad esperada del oponente** y permite muestrear rivales por dificultad. Eso es shaping del entorno, no del reward terminal.

## Datos parseables

Endpoints / formatos (free, sin auth):

- **Tabla meta:** `GET https://play.limitlesstcg.com/decks?format=standard`
  - Columnas exactas: `Rank | Deck | Count | Share | Score | Win %`
  - `Score` = `"3870-3299-158"` → regex `(\d+)-(\d+)-(\d+)` = (W, L, T).
  - `Share` y `Win %` = string `"8.58%"` → `float(s.strip('%'))/100`.
  - Filtros por query string: `?format=standard|expanded|...`, `&set=CRI`, `&rotation=2026`, `&game=pocket` (también One Piece, Digimon). Toggle "Combine related deck variants".
- **Página de arquetipo:** `GET /decks/{slug}?format=standard` (slug = `dragapult-ex`, `slowking`, ...).
  - Pestaña **Matchups** → matriz condicionada (opponent, record W-L-T, win%).
  - Tabla **Best Finishes** → `player | tournament | placement/field | record | decklist_link`.
- **Decklists (limitlesstcg.com):** filtros `Past month/3/6 months`, tipo (`Regional/International/Worlds`), formato, división (`Masters/Seniors/Juniors`).
- **Export de decklist en TEXTO PLANO (clave para el agente)** — formato `count name SET number`, una carta por línea:
  ```
  4 Boss's Orders BRS 132
  3 Lugia VSTAR SIT 139
  2 Lumineon V BRS 40
  4 Ultra Ball BRS 150
  3 Nest Ball SVI 181
  2 Switch BLW 91
  ```
  - Parser: `^(\d+)\s+(.+?)\s+([A-Z]{2,5})\s+(\d+)$` → (qty, name, set_code, num). Suma de qty == 60.
  - Compatible con export/import de PTCGL (botón Export copia al clipboard). Gotcha: cartas ALT de PTCGL salen con numeración interna (`SWSHALT 127` en vez de `BRS 132`); para Trainer/Energy en inglés basta quitar el código ALT, para Pokémon hace falta set+num correctos.
  - Limitless Deck Builder (`my.limitlesstcg.com/builder`): `Share > Copy as Text` mismo formato.
- **Herramientas:** **DrawCalc** (Opening Hand Calculator, prob. de manos de apertura → input para consistency/mulligan), **Tabletop** (simulador manos/turnos), **Proxy Printer**, **Swiss Calculator** (aprox. resultados Swiss → cuándo aceptar empate/drop), **Image Generator**, **Card Database** (búsqueda avanzada + traducciones), **Limitless Labs** (`labs.limitlesstcg.com`: tournament paths, conversion rate, matchups granulares).

## Caveats / sesgo

- **Rota con cada set** (`rotates: true`): nombres de arquetipo, share y win% cambian con cada lanzamiento/rotación. Re-scrapear; NO hardcodear listas.
- **Sesgo de muestra online:** gran parte de los eventos son torneos online (Moujii's Dojo, Turn Zero), no oficiales → el meta puede divergir del presencial/Regional. Filtrar por tipo de evento si importa.
- **Win% agregado ≠ skill del mazo:** mezcla niveles de jugador. Un mazo "fácil" puede inflar win% por pilotos buenos. El matchup matrix condicionado es más fiable que el win% global.
- **"Other" y muestras pequeñas:** ignorar o suavizar fuerte (`k` alto en el shrink). Win% con n bajo es ruido.
- **Limitless ≠ entorno cabt:** estos datos describen el meta humano de Standard, no necesariamente la pool/reglas del reto Kaggle. Útiles como prior de arquetipos y matchups si el reto usa formato Standard; verificar solapamiento de cartas antes de confiar.
- El detalle de la matriz de matchups requiere abrir la pestaña `Matchups` de cada arquetipo (no viene en la tabla raíz); puede tener celdas vacías por falta de muestra.

## Fuentes citadas

- [Decks – Pokémon TCG | Limitless](https://play.limitlesstcg.com/decks?format=standard) — tabla meta verificada (columnas Rank/Deck/Count/Share/Score/Win%, top 15 con datos reales).
- [Decklist Submission | Limitless Docs](https://docs.limitlesstcg.com/player/decklists) — formato de export en texto plano (`count name SET num`) y gotcha de cartas ALT de PTCGL.
- [Tools – Limitless](https://limitlesstcg.com/tools) — DrawCalc, Tabletop, Swiss Calculator, Card Database, Image Generator, Deck Builder, Labs.
- [Limitless Labs](https://labs.limitlesstcg.com/) — tournament paths, conversion rates, matchups en profundidad.
- [Decklists – Limitless](https://limitlesstcg.com/decks/lists) — filtros de listas (periodo/tipo/formato/división), Best Finishes.

Limitless TCG está operado por Robin Schulz ("LimitlessTCG"), organizador oficial reconocido de eventos online de Pokémon TCG y socio de The Pokémon Company para retransmisión/datos de torneo; es la fuente de datos de meta más usada por la comunidad competitiva.
