---
source: Limitless TCG (play.limitlesstcg.com) — Standard 2026 metagame
url: https://play.limitlesstcg.com/decks?format=standard&rotation=2026
tier: free
concept: meta
rotates: true
extracted: 2026-06-23
---

## Qué es

Foto del metagame **Standard 2026** (post-rotación, sets vigentes hasta Megas/MEG) según el
agregador Limitless TCG, snapshot **23 jun 2026**: 330 torneos, 18.537 jugadores, ~18.500
partidas registradas en el periodo. Sirve para que el agente tenga una **distribución a priori
(prior)** sobre qué mazo enfrenta y qué amenazas anticipar antes de tener información perfecta
(motor cabt, info imperfecta).

> ⚠️ **rotates: true — DESECHABLE EN ~3 MESES.** Las cifras de meta share y win rate rotan con
> cada set y cada Regional. Re-verificar en Limitless antes de confiar en los números exactos.
> Lo que NO caduca tan rápido es la **estructura de decisión** (priors, prize-trade por arquetipo,
> amenaza de spread). Eso es lo que codificamos; los porcentajes son sólo el peso inicial.

## Conceptos clave

**Tabla verificada (Limitless, Standard 2026, 23 jun 2026):**

| # | Arquetipo | Meta share | Win rate | Naturaleza prize-trade |
|---|-----------|-----------|----------|------------------------|
| 1 | Dragapult ex | 8.58% | 52.82% | 2-prize, spread (Phantom Dive) |
| 2 | Dragapult Dusknoir | 5.89% | 51.46% | 2-prize + KO bench vía counters |
| 3 | Mega Greninja ex | 5.82% | 43.91% | 3-prize (Mega), sniping |
| 4 | Slowking | 5.77% | 51.78% | control/single-prize-ish |
| 5 | N's Zoroark | 4.79% | 49.49% | 2-prize, tempo/disruption |
| 6 | Other | 4.74% | 40.94% | — (cola larga, 118 mazos) |
| 7 | Alakazam Dudunsparce | 4.36% | 51.20% | combo/single-prize engine |
| 8 | Beedrill | 4.09% | 49.46% | single-prize agresivo |
| 9 | Ogerpon Meganium Hydrapple | 3.51% | **53.01%** | single-prize tank, mejor WR top10 |
| 10 | Lucario Hariyama (Mega Lucario) | 3.05% | 47.02% | 3-prize Mega que "finge" single-prize |

**El mazo a batir = Dragapult ex** (mayor share + WR>52%). Su pieza nuclear es **Phantom Dive**:
200 de daño al activo + **coloca 6 contadores de daño (60) repartidos sobre el banco rival como
quieras** (carta de Twilight Masquerade, coste R+P). Esto significa que Dragapult **mata cosas del
banco a distancia** y prepara KOs múltiples → el agente NO puede asumir que un Pokémon de banco
está a salvo.

Mega Lucario / Lucario Hariyama emula un mazo de **un solo premio**: juega Hariyama (single-prize)
la mayor parte de la partida y sólo usa el Mega de 3 premios puntualmente. **Rocky Energy** anula
el spread extra de Phantom Dive, por lo que en ese matchup el prize-trade favorable se invierte.

## → Heurística computable

```python
# Prior sobre el arquetipo del oponente antes de revelar cartas (info imperfecta).
# Pesos = meta_share normalizado del snapshot Standard 2026 (Limitless 23-jun-2026).
META_PRIOR_2026_06 = {
    "dragapult":        0.0858,
    "dragapult_dusk":   0.0589,
    "mega_greninja":    0.0582,
    "slowking":         0.0577,
    "ns_zoroark":       0.0479,
    "alakazam_dudun":   0.0436,
    "beedrill":         0.0409,
    "ogerpon_hydra":    0.0351,
    "lucario_hariyama": 0.0305,
    "other":            0.0474 + 0.40,  # cola larga; resto del campo
}
# Naturaleza del prize-trade por arquetipo: cuántos premios da por KO su atacante principal.
PRIZE_VALUE = {
    "dragapult": 2, "dragapult_dusk": 2, "mega_greninja": 3,
    "ns_zoroark": 2, "lucario_hariyama": 1,   # Hariyama es el atacante real, 1 premio
    "alakazam_dudun": 1, "beedrill": 1, "ogerpon_hydra": 1, "slowking": 1,
}

def update_belief(prior, evidence):
    # Bayes: al ver cartas reveladas (atacante, supporter, energía) re-pondera el prior.
    # p.ej. ver Drakloak / Dreepy -> sube dragapult*; ver Hariyama -> sube lucario_hariyama.
    post = {k: prior[k] * likelihood(k, evidence) for k in prior}
    z = sum(post.values()); return {k: v/z for k, v in post.items()}

# REGLA SPREAD: si P(dragapult*) es la moda del belief, NO dejar Pokémon clave en banco
# a <=60 HP de morir por contadores (Phantom Dive reparte 60). Penaliza "bench_exposure".
def bench_is_unsafe(bench_mon, belief):
    p_spread = belief["dragapult"] + belief["dragapult_dusk"]
    return p_spread > 0.15 and bench_mon.remaining_hp <= 60

# REGLA PRIZE-TRADE vs single-prize tank (Ogerpon/Lucario-Hariyama, mejores WR):
# evitar canjear tu 2-prize por su 1-prize de forma repetida -> pierdes la carrera de premios.
def bad_trade(my_attacker_prizes, their_ko_prizes):
    return my_attacker_prizes - their_ko_prizes >= 1  # tú das más de lo que quitas
```

Variables de estado mínimas a llevar para que esto funcione: `belief[arquetipo]`,
`opp_prizes_taken`, `my_prizes_taken`, `bench[i].remaining_hp`, `attacker.prize_value`.

## → Hook de recompensa

Toca dos términos del reward shaping del agente:

- **`prize_efficiency`** (principal): `+w * (prizes_taken_per_KO - prizes_given_per_KO)`.
  El prior de meta hace que, contra el campo single-prize de alto WR (Ogerpon 53%, Beedrill,
  Alakazam), el agente penalice canjes donde entrega un 2/3-prize por un 1-prize.
- **`bench_exposure_penalty`** (secundario): `- w * sum(mon for mon in bench if mon.hp <= 60)
  * P(dragapult_spread)`. Castiga dejar piezas asesinables por Phantom Dive cuando el belief
  apunta a Dragapult. **null** si el belief de spread es < umbral (~0.15).

## Datos parseables

- Listado meta con share/record/winrate por arquetipo:
  `https://play.limitlesstcg.com/decks?format=standard&rotation=2026` (tabla HTML, scrapeable;
  columnas: deck, count, share %, record W-L-T, win rate %).
- Overview por mazo: `https://limitlesstcg.com/decks/<id>` (Dragapult=284, Mega Lucario=345).
- Best finishes filtrables por set/región: `.../decks/dragapult-ex?format=standard&rotation=2026&set=POR`.
- Texto de carta canónico (mecánica Phantom Dive): `https://limitlesstcg.com/cards/twm/130` y
  Bulbapedia. No hay API pública oficial; usar export HTML / scraping respetuoso.

## Caveats / sesgo

- **Caduca rápido (rotates:true):** snapshot de junio 2026. Con cada Regional grande y cada set
  nuevo (Megas ya están dentro), share y WR se mueven varios puntos. Re-verificar.
- **Win rate ≠ skill puro:** Limitless agrega online + presencial mezclando niveles de juego.
  Mega Greninja con 43.91% WR pese a 5.82% de share = mazo muy jugado pero mal pilotado / mal
  posicionado, no necesariamente débil en manos expertas.
- **"Other" (118 mazos)** es ~5% pero con WR bajo (40.94%): cola larga de brews; el prior debe
  asignarle masa pero el agente no debe sobreajustar a un arquetipo concreto dentro de ella.
- **El prior es punto de partida, no verdad:** en cuanto hay cartas reveladas, el belief manda.
  No congelar la creencia en el meta share.
- Los números de "winnings/points" que devuelve la página de overview son acumulados históricos
  del arquetipo, NO indicadores del meta actual; ignorarlos para el prior.

## Fuentes citadas

- **Limitless TCG** — agregador de torneos de referencia del PTCG competitivo (operado por
  Robin Schulz / equipo Limitless, fuente estándar usada por jugadores y por The Pokémon Company
  para coberturas). Meta Standard 2026:
  https://play.limitlesstcg.com/decks?format=standard&rotation=2026
- Limitless — Dragapult ex deck overview: https://limitlesstcg.com/decks/284
- Limitless — Mega Lucario deck overview: https://limitlesstcg.com/decks/345
- Limitless / Bulbapedia — Dragapult ex (Twilight Masquerade 130), texto de Phantom Dive
  (200 daño + 6 contadores al banco): https://limitlesstcg.com/cards/twm/130 ·
  https://bulbapedia.bulbagarden.net/wiki/Dragapult_ex_(Twilight_Masquerade_130)
