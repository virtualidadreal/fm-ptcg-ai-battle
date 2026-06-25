---
source: Trainer Hill
url: https://www.trainerhill.com/meta
tier: free
concept: meta
rotates: true
extracted: 2026-06-23
---

## Qué es

Trainer Hill es una plataforma de analítica competitiva de Pokémon TCG que construye su análisis sobre datos de torneos de **Limitless** (online + presenciales, vía la API de Limitless: placings, decklists, matches). No es una fuente de listas, es una **capa de agregación estadística** sobre el meta. Aporta cinco productos relevantes para un agente:

1. **Meta Analysis** (`/meta`): rankings de arquetipos, meta share (%), win rate por arquetipo, matchup spread y usage trends de cartas, filtrable por torneos de cierto tamaño (los datasets públicos derivados usan corte de 50+ jugadores).
2. **Matchup matrix**: matriz pairwise arquetipo-vs-arquetipo con win rate, registro crudo W-L-T y meta share por arquetipo (un dataset derivado documenta una matriz 14×14).
3. **Tier List Builder** (`/tools/tier-list`): construye tiers con datos de torneo y meta percentages.
4. **Deck Diff Venn Diagram** (`/decklist`): visualiza el overlap de cartas entre dos listas (núcleo común vs. flex/tech individuales).
5. **Battle Journal / Battle Journal+** (`plus.trainerhill.com`): diario de testeo personal. La versión Plus trackea **win rate por matchup, deck y tags**, y crucialmente **estadística going first vs. going second**, con filtros por rango de fecha.

Para el agente cabt (info imperfecta), lo accionable NO es la lista del top deck (rota cada set), sino las **distribuciones**: priors de qué arquetipo enfrenta, ventaja estructural de turno (first/second), y el núcleo de cartas que define cada arquetipo (para inferencia de mano oculta).

## Conceptos clave

- **Meta share como prior de oponente**: la distribución de meta share es una prior bayesiana sobre qué arquetipo es el rival antes de ver cartas.
- **Matchup matrix = utilidad esperada pre-partida**: `WR(yo, rival)` ≠ 50%; los matchups son asimétricos y poligonales (piedra-papel-tijera), no transitivos.
- **First/second advantage es medible y NO trivial**: Battle Journal+ separa win rate going first vs going second precisamente porque en PTCG el jugador que va primero NO puede atacar el turno 1 (regla actual), invirtiendo la ventaja respecto a otros TCG. El signo y magnitud del efecto depende del arquetipo (mazos agresivos quieren ir segundo para atacar antes; mazos de setup quieren ir primero).
- **Card usage trends → inferencia de mano oculta**: dado un arquetipo, la frecuencia de inclusión de cada carta (usage %) es la probabilidad marginal de que esa carta esté en la lista del rival. El Venn distingue **cartas núcleo** (overlap ~100%, casi seguras) de **flex/tech** (overlap parcial, inciertas).
- **Tiers comprimen la matriz**: tier S/A/B reduce el espacio de 14+ arquetipos a clases de amenaza para acotar el árbol de búsqueda.

## → Heurística computable

```python
# 1) PRIOR DE OPONENTE desde meta share (Trainer Hill /meta)
#    Tabla rota cada set -> recargar; valores = ejemplo de estructura, NO fijar.
META_SHARE = {  # arquetipo -> share normalizado (suma ~1.0)
    "archetype_A": 0.18, "archetype_B": 0.14, "archetype_C": 0.11, ...
}
def opponent_prior():
    return dict(META_SHARE)  # belief inicial sobre identidad del rival

# 2) BELIEF UPDATE: cada carta vista del rival reescala la prior
#    P(arch | carta) ∝ usage(carta | arch) * P(arch)
def update_belief(belief, card_seen, USAGE):  # USAGE[arch][card] = inclusion %
    post = {a: belief[a] * USAGE.get(a, {}).get(card_seen, 0.01) for a in belief}
    z = sum(post.values()) or 1.0
    return {a: p / z for a, p in post.items()}

# 3) MATCHUP EV: utilidad esperada de la partida dado el belief
def expected_matchup_wr(my_deck, belief, MATRIX):  # MATRIX[mine][theirs] -> WR
    return sum(belief[a] * MATRIX[my_deck].get(a, 0.5) for a in belief)

# 4) TURN-ORDER: decisión de ir primero/segundo o ajuste de agresividad
#    PTCG: el que va 1º NO ataca en T1. Ajusta plan por arquetipo.
def prefer_going(my_deck, FS):  # FS[deck] = {"first": wr1, "second": wr2}
    f, s = FS[my_deck]["first"], FS[my_deck]["second"]
    return "second" if s > f else "first"
def turn_order_bias(my_deck, FS):
    return FS[my_deck]["second"] - FS[my_deck]["first"]  # >0 => aggro, quiere 2º

# 5) INFERENCIA DE CARTAS OCULTAS (Venn núcleo vs flex)
#    Si belief converge a un arquetipo, asume su núcleo presente.
def likely_hidden_cards(belief, CORE, threshold=0.6):
    top = max(belief, key=belief.get)
    return CORE[top] if belief[top] >= threshold else []  # cartas casi seguras
```

Variables de estado del agente: `opponent_belief` (dict arquetipo→prob), `seen_cards` (set), `turn_order` (first/second observado), `matchup_ev` (float). Condiciones: cuando `max(belief) >= 0.6` colapsar a plan específico de matchup; cuando `< 0.6` jugar líneas robustas que no se comprometen.

## → Hook de recompensa

- **Reward shaping pre-juego / opening**: término de **información** — bonus por jugar cartas que reduzcan la entropía de `opponent_belief` (scout) cuando la incertidumbre es alta. `r_info = λ * (H(belief_prev) - H(belief_post))`.
- **Term de coherencia de matchup**: escalar la evaluación de estado por `expected_matchup_wr` para sesgar la política hacia líneas que ganan el matchup probable, no el genérico.
- **Turn-order**: si el motor permite elegir primero/segundo, recompensar la elección que maximiza `FS[deck]` (≈ `turn_order_bias`).
- El win rate por matchup de Battle Journal+ sirve como **baseline / señal de calibración** offline, NO como reward online directo (es win rate empírico humano, no del agente).

## Datos parseables

- **Sin API pública propia documentada** (la org de GitHub `Trainer-Hill` solo publica utilidades: badge-leaderboard, ptcg-calendar-sync, uptime-to-discord; ningún export de meta).
- **El sitio carga datos vía JS en cliente** (las páginas `/`, `/meta`, `/tools`, `/about` devuelven solo "Loading..." a un fetch HTTP plano). Para scrapear haría falta navegador headless o interceptar el endpoint XHR/JSON que la SPA consume.
- **Fuente upstream real = API de Limitless** (`docs.limitlesstcg.com/developer.html`): endpoints de placings, decklists y matches. Es la vía limpia y estable para reconstruir meta share, usage y matchups sin depender del front JS de Trainer Hill.
- **Dataset derivado verificable** (IEEE DataPort): matriz de matchup **14×14** con win rates, registros W-L-T crudos y meta share por arquetipo, de torneos de **50+ jugadores** (ene–feb 2026). Confirma el esquema de datos: `{archetype, meta_share, {opponent: {wr, w, l, t}}}`.
- Métricas Battle Journal+ por match: deck propio, arquetipo rival, resultado W/L, **turn order (first/second)**, tags custom, timestamp. Formato ideal para reconstruir `FS[deck]` y `MATRIX`.

## Caveats / sesgo

- **rotates: true** — meta share, usage y matchup matrix cambian con cada set/regulación. NO hardcodear valores; recargar y tratar como config externa.
- **Carga JS cliente**: difícil de scrapear directamente; preferir la API de Limitless upstream.
- **Sesgo de muestra**: datos de torneos grandes (50+) sobre-representan el meta competitivo "resuelto"; el ladder online o BO1 del reto cabt puede tener distribución distinta (más ruido, listas peores). La prior de meta share es un punto de partida, no la verdad del entorno de evaluación.
- **First/second**: el efecto es real pero arquetipo-dependiente y depende de la regla vigente (el que va primero no ataca T1); verificar que el motor cabt implementa esa regla antes de fijar el signo.
- **Win rates humanos ≠ política del agente**: el matchup WR refleja decisiones de humanos; úsalo como prior/baseline, no como techo del agente.
- Battle Journal es **datos auto-reportados del usuario** (su propio testeo), con sesgo de muestra y de selección; la matriz global de `/meta` es más representativa.

## Fuentes citadas

- Trainer Hill — Meta Analysis & Trends: https://www.trainerhill.com/meta (abierta; render JS cliente)
- Trainer Hill — Tools (Tier List Builder, Deck Diff Venn): https://www.trainerhill.com/tools y https://www.trainerhill.com/tools/tier-list
- Trainer Hill — Decklist / Deck Diff Venn: https://www.trainerhill.com/decklist
- Battle Journal+ (win rate por matchup, going first/second, filtros): https://plus.trainerhill.com/ (verificado vía WebFetch, contenido sustantivo recuperado)
- Trainer Hill GitHub org (sin API/export de meta): https://github.com/Trainer-Hill
- Limitless Developer API (fuente upstream estable: placings/decklists/matches): https://docs.limitlesstcg.com/developer.html
- IEEE DataPort — "Formally Verified Pokémon TCG Metagame Analysis: Tournament Data, Matchup Matrices..." (matriz 14×14, WR + W-L-T + meta share, torneos 50+ jug., ene–feb 2026): https://ieee-dataport.org/documents/formally-verified-pokemon-tcg-metagame-analysis-tournament-data-matchup-matrices-and-lean
