---
source: TCGProtectors (Reading Opponent / Predicting Plays) + JustInBasil (Deck Strategy archetypes)
url: https://tcgprotectors.com/blogs/pokemon-blog/pokemon-tcg-reading-opponent-predicting-plays-guide-2026
tier: free
concept: reading
rotates: false
extracted: 2026-06-23
---

## Qué es

Reading = inferir el arquetipo del rival y el contenido oculto de su mano/baraja/premios a partir de jugadas observables, y mantener esa inferencia actualizada turno a turno. Es el **núcleo del problema de información imperfecta** del reto cabt: el agente no ve la mano ni el deck del rival, pero cada acción observada (qué Pokémon banca, qué Item/Supporter juega, qué NO juega, qué energía adjunta, qué descarta) es una **observación** que estrecha la distribución de creencia sobre el estado oculto.

Conceptualmente: el rival juega un deck de una distribución de arquetipos del meta. El agente mantiene un **belief-state** = distribución de probabilidad sobre (arquetipo del rival, cartas restantes ocultas). Bayes: `P(estado | observaciones)`. La fuente da las observaciones-clave y las reglas de actualización en lenguaje natural; aquí se traducen a código.

## Conceptos clave

- **Tell del primer Pokémon (prior fuerte).** "If your opponent plays Charmander first, you can be 99% certain they are playing a Charizard ex deck." El primer básico/línea evolutiva colapsa casi todo el prior de arquetipo. Implica plan conocido: Stage 2 vía Rare Candy, escalado de daño tardío.
- **Lectura por NO-jugada (información de ausencia).** "They play an Item card, attach an Energy, and then attack. They do not play a Supporter card... strongly suggests no playable Supporters remain." Un turno sin Supporter (cuando casi siempre conviene jugarlo) es evidencia de que no tiene Supporter jugable → mano débil → ventana de agresión/disrupción.
- **Skeleton del meta (conteo esperado de copias).** Listas optimizadas son predecibles: Charizard ex/Pidgeot lleva "4-1-3 or 4-2-3 line", "3-4 copies of Arven and 2-3 copies of Boss's Orders". Esto da el **N de copias esperado** de cada carta clave por arquetipo, base para contar outs ocultos.
- **Depleción de recursos (descarte = público).** "If three copies of Switch are discarded from a four-copy set, only one remains." El descarte y lo jugado son visibles → `copias_ocultas = copias_esperadas − copias_vistas`. Cuando llega a 0, esa amenaza está neutralizada (ventana para Parálisis, gust, etc.).
- **Energía visible predice el ataque.** Si un atacante tiene la energía suficiente adjunta para su ataque, atacará; si le falta, no. Permite anticipar el daño entrante del próximo turno.
- **Forzar a probar el out estrecho.** "Make the defensive play. Force them to prove they have the one specific card they need to win." Si el rival solo gana con una carta concreta y quedan pocas copias ocultas, la jugada defensiva tiene EV positivo porque `P(tiene el out)` es baja (hipergeométrica).
- **Arquetipos como clases de creencia (JustInBasil):** Aggression (atacantes de alto daño, streaming consistente), Control (negación de recursos/energía/abilities), Mill (descarte forzado del deck rival), Stall (HP alto + prevención de daño, busca deck-out). Cada clase implica un policy esperado distinto → distinto modelo de transición del rival.

## → Heurística computable

```python
# BELIEF-STATE del rival sobre estado oculto e info imperfecta.

# 1) Prior de arquetipo, colapsado por el tell del primer Pokémon
ARCHETYPE_PRIORS = meta_distribution()        # P(arquetipo) base del meta
SIGNATURE_CARD = {"Charmander": "charizard_ex", "Comfey":"lost_box", ...}

def update_archetype_belief(belief, observed_card):
    if observed_card in SIGNATURE_CARD:
        arch = SIGNATURE_CARD[observed_card]
        belief.archetype = collapse_to(arch, conf=0.99)   # tell fuerte
    else:
        belief.archetype = bayes_update(belief.archetype, observed_card)
    return belief

# 2) Conteo de copias ocultas por carta clave (skeleton del meta)
#    copias_ocultas = esperadas_por_arquetipo - vistas(jugadas+descartadas+en_juego)
def hidden_copies(belief, card):
    expected = SKELETON[belief.archetype.argmax()].get(card, 0)   # p.ej Boss=2..3
    seen = count_in(discard) + count_in(board) + count_played(card)
    return max(0, expected - seen)

# 3) Probabilidad de que tenga/dibuje un out (hipergeométrica, sin reemplazo)
def p_has_out(belief, card, draws=1):
    k = hidden_copies(belief, card)
    N = est_unknown_zone_size(belief)     # deck oculto + mano oculta
    if k == 0: return 0.0                  # out neutralizado -> jugada segura
    return 1 - hypergeom_pmf(0, N, k, draws)   # P(>=1 en 'draws')

# 4) Lectura por ausencia: turno sin Supporter => mano probablemente débil
def update_hand_strength(belief, opp_turn):
    if opp_turn.played_item and opp_turn.attacked and not opp_turn.played_supporter:
        belief.hand_strength *= 0.5        # baja P(mano fuerte) -> ventana de agresión
    return belief

# 5) Anticipar ataque entrante por energía visible
def incoming_attack_threat(opp_active):
    return opp_active.attached_energy >= opp_active.best_attack_cost  # bool/daño esperado

# 6) Decisión: forzar el out estrecho cuando es improbable
def should_make_safe_defensive_play(belief, lethal_card):
    return p_has_out(belief, lethal_card, draws=expected_draws_next_turn()) < THRESH  # ~0.2
```

Variables de estado a mantener en el agente: `belief.archetype` (vector de prob sobre arquetipos), `belief.hidden_copies[card]`, `belief.hand_strength`, `belief.hand_size` (público), `belief.prizes_remaining` (público), `seen_cards` (descarte + tablero + jugadas), `est_unknown_zone_size`. Toda observación de jugada del rival dispara `update_*`.

## → Hook de recompensa

- **No es un término de reward directo** del entorno (cabt premia ganar/prizes). Reading toca el **modelo del oponente** dentro del planificador (rollouts/expectimax), no la función de recompensa.
- Sí habilita **reward shaping interno / EV de decisión**: usar `p_has_out` para ponderar ramas en la búsqueda (`EV = Σ P(estado_oculto|belief)·reward(rama)`). La "jugada defensiva forzando el out" se justifica porque `p_has_out` bajo ⇒ mayor EV esperado de prizes propios.
- Penalización implícita de **sobre-extensión**: si `incoming_attack_threat` predice KO de un atacante con energía invertida, descontar el valor de bancar ese Pokémon (riesgo de prize-trade desfavorable). Conecta con el reward de prize-trade, no lo define.

## Datos parseables

- **Skeletons del meta** (conteo esperado de copias por arquetipo): exportables desde listas de torneo de JustInBasil (`justinbasil.com/play`, `/guide/meta`) y limitless. Formato útil: `{arquetipo: {carta: copias_esperadas}}` (p.ej. Charizard ex: Arven 3-4, Boss's Orders 2-3, línea Charizard 4-1-3/4-2-3).
- **Calculadora hipergeométrica** (validación de `p_has_out`): SixPrizes "Stats on Starts", cardgamecalculator.com, D3mon Deck Tools — todas implementan `hypergeom` sin reemplazo (N, k, n draws).
- **Tabla de tells** (firma → arquetipo): construible a partir de Pokémon-firma de cada deck del meta de la temporada cargada en cabt.
- No hay endpoint oficial de "lectura"; el dato real es la lista del meta + la distribución hipergeométrica.

## Caveats / sesgo

- **Las listas rotan, los conceptos no.** Los skeletons concretos (Charizard 4-1-3, Arven 3-4) caducan con cada set/rotación; el agente debe leer las copias-esperadas de la config del meta vigente de cabt, no hardcodearlas. (`rotates:false` aplica al método de reading; los números de la fuente sí rotan.)
- El tell del primer Pokémon "99%" es heurístico humano, no probabilidad calibrada; trátalo como prior fuerte pero actualizable (algunos básicos son tech-splashes en varios decks).
- "No jugó Supporter ⇒ no tiene" es falible: el rival puede retener un Supporter por secuenciación (prize-checking, esperar mejor turno). Es evidencia bayesiana, no certeza.
- JustInBasil **no tiene página dedicada a reading**; su aporte verificado aquí es la taxonomía de arquetipos (deck-strategy). El contenido operativo de reading proviene de TCGProtectors (blog comercial, no autoría competitiva acreditada) — fiable como heurística pero no como fuente de torneo. Validar la matemática con las calculadoras hipergeométricas citadas.
- `est_unknown_zone_size` mezcla deck oculto + mano oculta; en cabt hay que separarlos según lo que el entorno exponga como público (tamaño de mano y de deck SÍ son públicos por reglas oficiales).

## Fuentes citadas

- [TCGProtectors — Reading Opponent / Predicting Plays Guide 2026](https://tcgprotectors.com/blogs/pokemon-blog/pokemon-tcg-reading-opponent-predicting-plays-guide-2026) — origen de los tells (primer Pokémon, NO-jugada de Supporter, energía visible, depleción de Switch, forzar el out). Blog de marca de fundas, sin credenciales competitivas verificables; tratar como heurística práctica.
- [JustInBasil — Deck Strategy](https://www.justinbasil.com/guide/deck-strategy) — taxonomía Aggression/Control/Mill/Stall usada como clases de belief de arquetipo. JustInBasil es recurso de referencia estándar de la comunidad competitiva.
- [JustInBasil — What to Play / Meta](https://www.justinbasil.com/guide/meta) — fuente de skeletons/listas para los conteos esperados de copias.
- [SixPrizes — "Stats on Starts": Hypergeometric Distribution and the Pokémon TCG](https://sixprizes.com/2014/11/12/stats-on-starts/) — base matemática de `p_has_out` (hipergeométrica sin reemplazo).
- [TCGplayer — The 3 Principles of Prize Checking](https://www.tcgplayer.com/content/article/The-3-Principles-of-Prize-Checking/a015ad58-7ec5-41ea-ba50-56db0ee9d67f/) — método de deducción "vistas vs decklist conocido", aplicable simétricamente al estado oculto del rival.
