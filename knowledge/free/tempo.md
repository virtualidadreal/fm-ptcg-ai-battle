---
source: SixPrizes "Don't Have a Tempo Tantrum" + JustInBasil Gusting Guide + TCGplayer Counter Catcher analysis + Bulbapedia (card text)
url: https://sixprizes.com/2013/03/29/dont-have-a-tempo/
tier: free
concept: tempo
rotates: false
extracted: 2026-06-23
---

## Qué es

**Tempo = la velocidad a la que un jugador llega a su condición de victoria** (cita literal SixPrizes: "Tempo is the rate or speed at which a player arrives at a win condition"). En PTCG la condición de victoria casi siempre es **tomar 6 premios** (a veces deckout / sin banca). Quien dicta el tempo obliga al rival a reaccionar en vez de ejecutar su propio plan.

El **truco Counter Catcher vs Boss** es el caso más nítido donde un *desventaja aparente* (ir por detrás en premios) **desbloquea** un swing turn más potente:

- **Boss's Orders** = Supporter. Hace gusting (subir un Pokémon de la banca rival al activo) **incondicionalmente**, pero consume el **único Supporter del turno** (1/turno). Si lo usas para gustear, ese turno NO puedes jugar tu Supporter de robo (Professor's Research / Iono, etc.).
- **Counter Catcher** = **Item**. Mismo efecto de gusting, **sin límite por turno**, pero con condición: *"You can use this card only if you have more Prize cards remaining than your opponent"* (texto verbatim, Bulbapedia/Paradox Rift). Es decir: **solo si vas POR DETRÁS en premios** (te quedan MÁS premios sin tomar que al rival).

El swing turn que habilita Counter Catcher: dejar que el rival tome el **1er KO** → ahora vas detrás (p.ej. 6 vs 5) → **Counter Catcher** (Item, gratis de Supporter) saca un objetivo vulnerable + **Professor's Research/Iono** (Supporter de robo, sigue disponible) + atacar y tomar KO. Gusting + mano nueva + premio **en el mismo turno**, algo imposible con Boss porque Boss te robaría el slot de Supporter.

## Conceptos clave

- **Swing turn**: turno que cambia el marcador de premios fuerte y/o invierte la iniciativa. SixPrizes: un Iono/N bien temporizado "creates a four card swing alone" sumado al premio.
- **Item gusting libera el slot de Supporter** (clave de tempo). JustInBasil: el beneficio real surge "when gusting doesn't consume your Supporter slot" → puedes gustar **y** robar el mismo turno.
- **La condición de Counter Catcher es de estado, no de mazo**: depende de `my_prizes_remaining > opp_prizes_remaining`. No rota, no caduca; es regla de carta estable desde 2017.
- **Ir-detrás como ventaja condicional**: ceder el 1er KO para activar Counter Catcher solo compensa si el coste (premio cedido) es menor que el swing habilitado (gusting+robo+KO en un turno, normalmente sobre un 2-prize ex). Trade favorable típico: ceder un KO de **1 premio** (single-prize) para tomar uno de **2 premios** con el slot de Supporter intacto.
- **Quién dicta el ritmo**: forzar al rival a tomar varios KOs sobre Pokémon de 1 premio agota sus copias de Boss (1/turno, ~2-3 por mazo) y lo ralentiza; mientras, tus Counter Catcher (Items, hasta 4 copias, sin límite/turno) escalan mejor en el late-game.

## → Heurística computable

```python
# Estado relevante
my_prizes   = prizes_remaining(me)        # premios que AÚN no he tomado (6..0)
opp_prizes  = prizes_remaining(opp)
behind      = my_prizes > opp_prizes      # voy por detrás (más premios pendientes)

# 1) LEGALIDAD de Counter Catcher (condición de carta, dura)
def can_play_counter_catcher(state):
    return state.my_prizes_remaining > state.opp_prizes_remaining

# 2) VALOR de gusting con Counter Catcher (Item) vs Boss (Supporter)
#    Counter Catcher libera el slot de Supporter -> bonus de tempo
def gust_plan(state, hand):
    target = best_gust_target(state.opp_bench)   # KOable / alto coste de retirada / vulnerable
    if target is None:
        return None
    if can_play_counter_catcher(state) and "counter_catcher" in hand:
        # gusting GRATIS de Supporter: encadena draw-supporter el mismo turno
        return Plan(gust="counter_catcher", supporter_free=True, target=target)
    if "boss" in hand and not state.supporter_used_this_turn:
        # gusting consume el Supporter del turno -> coste de oportunidad
        return Plan(gust="boss", supporter_free=False, target=target)
    return None

# 3) DECISIÓN "ceder el 1er KO para activar Counter Catcher"
#    Solo si el swing habilitado supera el premio cedido.
def should_concede_first_ko(state):
    if state.behind:                       # ya voy detrás: Counter Catcher ya legal, no cedo nada
        return False
    # estoy empatado/por delante: ¿cedo 1 KO barato para volverme 'behind' y habilitar CC?
    prizes_conceded   = prize_value(my_active)           # idealmente 1 (single-prize attacker)
    enabled_swing     = expected_swing_if_behind(state)  # gusting+draw+KO 2-prize = ~2 premios + tempo
    have_cc_online    = ("counter_catcher" in deck_or_hand_reachable(state)
                         and can_setup_attack_next_turn(state))
    return have_cc_online and (enabled_swing - prizes_conceded) > TEMPO_MARGIN
    # TEMPO_MARGIN ~ 0.5–1.0 prize-equivalents; nunca ceder un 2-prize para habilitar CC.
```

Variables de estado mínimas para el agente: `my_prizes_remaining`, `opp_prizes_remaining`, `supporter_used_this_turn`, `opp_bench` (con coste de retirada y HP/daño por objetivo), copias de `counter_catcher`/`boss` accesibles (mano+contadas en mazo), `can_setup_attack_next_turn`.

Regla de inferencia con info imperfecta: aunque no veas la mano rival, **el contador de premios es público** → `behind` y la legalidad de Counter Catcher son siempre computables con certeza. La creencia sobre si el rival TIENE Counter Catcher debe **subir** cuando él va por detrás en premios (la carta solo le sirve detrás).

## → Hook de recompensa

Toca el término de **tempo / iniciativa**, distinto del término puro de prize-trade:

- `reward += w_tempo * (gusting_kos_taken_with_supporter_slot_free)` — premiar KOs por gusting que NO gastaron el Supporter (Counter Catcher), porque encadenan robo el mismo turno.
- `reward += w_swing * delta_prize_lead_this_turn` — premiar swing turns (cambio neto de marcador en un turno).
- `reward -= w_oppgust_resource` por agotar Boss del rival (forzarle KOs sobre single-prizers): término indirecto, modelar como descuento del riesgo futuro de ser gusteado.
- Penalización al "ceder 1er KO" mal calibrado: `reward -= prizes_conceded` si el swing esperado no se materializa (evita que el agente regale premios buscando el combo).

Si el motor solo modela reward terminal (ganar/perder), entonces **null** como término explícito; usarlo como heurística de ordenación de jugadas (move ordering) en la búsqueda, no como reward shaping.

## Datos parseables

- **Texto de carta (verbatim, estable)**: Counter Catcher — tipo **Item** — *"You can use this card only if you have more Prize cards remaining than your opponent. Switch in 1 of your opponent's Benched Pokémon to the Active Spot."* Prints: Crimson Invasion 91, Paradox Rift 160 (mismo efecto).
- Limitless TCG da los datos de carta estructurados: `https://limitlesstcg.com/cards/PAR/160` (parseable por set/número).
- `prizes_remaining` es estado de juego observable en cualquier engine PTCG (el motor cabt debe exponerlo); la condición de Counter Catcher es una guard booleana directa sobre ese estado.
- Boss's Orders: tipo **Supporter**, gusting incondicional, sujeto a la regla global 1 Supporter/turno (no es propiedad de la carta sino del motor).

## Caveats / sesgo

- El artículo seminal de tempo (SixPrizes, 2013) usa cartas rotadas (N, Pokémon Catcher con flip) pero el **concepto** de tempo = velocidad a la condición de victoria es atemporal. `rotates: false` aplica al concepto, no a las listas.
- Counter Catcher es **menos fiable que Boss** como herramienta de cierre: si el rival empata o te adelanta en premios, **deja de ser legal**. No se puede depender de él para el KO final ganador (cuando vas a tomar tu último premio, normalmente ya no vas detrás). Boss es el "guaranteed gust" para el KO de cierre.
- El "ceder el 1er KO a propósito" es un combo de nicho, no una línea por defecto. Regalar premios suele ser malo; solo compensa con el combo armado y objetivo de 2 premios disponible. No sobre-ajustar el agente a buscarlo.
- La fuente TCGplayer original no fue legible directamente (redirige y devuelve solo header); el concepto del swing "dejar tomar el 1er KO → Counter Catcher + Research + KO" se corroboró vía el snippet de búsqueda de TCGplayer/Oreate y es consistente con la regla de carta verificada en Bulbapedia. Tratar el número exacto (6-5) como ilustrativo, no como umbral mágico: el único umbral duro es `my_prizes > opp_prizes`.
- Sesgo de formato Standard: en formatos donde Boss no existe o hay otros gusters (Leafeon VSTAR libera Supporter como hace Counter Catcher), la ventaja relativa de Item-gusting cambia.

## Fuentes citadas

- **SixPrizes — "Don't Have a Tempo Tantrum! (An Intro to Tempo in the Pokemon TCG)"**, 2013. https://sixprizes.com/2013/03/29/dont-have-a-tempo/ — define tempo como "the rate or speed at which a player arrives at a win condition". SixPrizes es sitio histórico de estrategia competitiva PTCG con autores de nivel Worlds.
- **JustInBasil — Gusting and Repulsion guide.** https://www.justinbasil.com/guide/gusting — distingue Item vs Supporter gusting y el valor de no consumir el slot de Supporter. JustInBasil es referencia técnica estándar de la comunidad competitiva.
- **TCGplayer Infinite — "How Will the Return of Counter Catcher Change Standard?"** https://www.tcgplayer.com/content/article/How-Will-the-Return-of-Counter-Catcher-Change-Standard/4874ea26-2eba-463e-af37-0e0be151d8d4/ — concepto del swing al ir por detrás (contenido directo no legible por redirect; corroborado por snippet de búsqueda).
- **Bulbapedia — Counter Catcher (Crimson Invasion 91 / Paradox Rift 160).** https://bulbapedia.bulbagarden.net/wiki/Counter_Catcher_(Crimson_Invasion_91) — texto de carta verbatim y tipo (Item) verificados.
- **Limitless TCG — Counter Catcher PAR 160.** https://limitlesstcg.com/cards/PAR/160 — datos estructurados de carta.
