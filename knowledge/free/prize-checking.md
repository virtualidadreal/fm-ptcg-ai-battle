---
source: TCGplayer — The 3 Principles of Prize Checking
url: https://www.tcgplayer.com/content/article/The-3-Principles-of-Prize-Checking/a015ad58-7ec5-41ea-ba50-56db0ee9d67f/
tier: free
concept: prize-checking
rotates: false
extracted: 2026-06-23
---

## Qué es

**Prize-checking** = deducir qué cartas de tu mazo quedaron entre tus 6 premios boca abajo, usando la información de qué cartas YA viste (mano, descarte, en juego, búsquedas). En un mazo de 60 cartas con 6 premios, cada carta puede estar premiada y tú no lo sabes hasta que la cuentas. El prize-checking convierte esa incertidumbre en una **distribución de creencias** sobre tus propios premios, que se actualiza cada vez que tocas la baraja (search) o tomas un premio.

La idea central del artículo: NO es algo que se hace una sola vez al inicio. Es un proceso continuo de inferencia bayesiana implícita. Lo que importa para el juego es:
1. saber qué piezas clave (singletons, evolucionadores, win conditions) están bloqueadas en premios,
2. reajustar el plan de juego en consecuencia,
3. evaluar el riesgo de jugadas según qué esperas robar al tomar premios.

## Conceptos clave

Los **3 principios** del artículo:

1. **El prize-check es continuo, no de un solo turno.** Revisar las 6 cartas premiadas de golpe en el primer search cuesta demasiado tiempo en torneo, así que la práctica es chequear singletons y cartas importantes primero, y volver a comprobar a lo largo de la partida en cada search posterior. La info de premios no caduca: cada nuevo search reduce el espacio de cartas desconocidas y precisa la deducción.

2. **El valor de cada carta premiada cambia con el estado de partida → reajusta el plan.** Ejemplos del artículo: con Mew VMAX, dos Power Tablet premiadas cambian cómo cuentas daño toda la partida. Con Gardevoir ex, dos Kirlia premiadas hacen que **priorizar Rare Candy sea crítico** (necesitarás saltar de Basic a Stage 2 sin la línea evolutiva intermedia). Es decir: una carta premiada no solo "falta", reordena prioridades de búsqueda y secuenciación.

3. **Al hacer jugadas arriesgadas, evalúa qué robarás de premios.** Tus premios no están bloqueados para siempre: los tomas al hacer Knock Outs. Antes de ir a 0 cartas en mano por un KO, comprueba tus premios y calcula **qué % de los premios restantes son cartas que te alegraría robar**. Eso convierte un "all-in" en una decisión con esperanza calculable.

**Matemática hipergeométrica (de la fuente de soporte lastlegume, verificada):**
- 1 copia en mazo de 60 con 6 premios: **P(premiada) = (53/60)·(6/53) = 1/10 = 10%**.
- Distribución hipergeométrica: `dhyper(x, m, n, k)` = `C(m,x)·C(n,k-x)/C(m+n,k)`, con `m`=copias en mazo, `n`=no-objetivo, `k`=cartas robadas (k=6 para premios).
- 2 copias (contando mulligans, mano de inicio válida): **P(0 premiadas)=80.85%, P(1 premiada)=18.31%, P(2 premiadas)=0.85%**.
- 4 copias: prizar 3+ ≈ **0.20% (1 en 500)**.
- La probabilidad "naive" de ~10%/copia se corrige a la baja al condicionar por mano de inicio válida (≥1 Basic).

**Traducción al "al menos uno de mis 2 outs lo robaré con mis próximos 2 premios":** si quedan `D` cartas desconocidas en mazo+premios y `o` outs entre ellas, y tomarás `p` premios, P(robar ≥1) ≈ `1 - C(D-o, p)/C(D, p)`. El foco del prompt (2 outs, 2 premios, ~80%) corresponde a outs concentrados en pocos premios restantes al final de partida.

## → Heurística computable

```python
# Belief state sobre TUS premios. En cabt (info imperfecta) tus 6 premios
# están ocultos PARA TI. Mantén una distribución sobre cada card_id propio.

from math import comb

def p_card_prized(copies_unknown, unknown_pool, n_prizes_unknown):
    """P(>=1 copia de una carta esté en los premios desconocidos).
    unknown_pool = cartas aún no vistas (mazo + premios ocultos).
    n_prizes_unknown = cuántas de esas ocultas son premios."""
    if copies_unknown == 0:
        return 0.0
    non_target = unknown_pool - copies_unknown
    # P(0 copias entre los premios) via hipergeométrica
    p_none = comb(non_target, n_prizes_unknown) / comb(unknown_pool, n_prizes_unknown)
    return 1.0 - p_none

class PrizeBelief:
    def __init__(self, decklist):
        self.deck_counts = dict(decklist)        # card_id -> copias totales
        self.seen = {cid: 0 for cid in decklist}  # vistas fuera de premios
        self.prizes_remaining = 6

    def observe(self, card_id, qty=1):
        # Llamar tras CADA search/draw/mill que revele una carta propia
        self.seen[card_id] = min(self.deck_counts[card_id], self.seen[card_id] + qty)

    def take_prize(self):
        self.prizes_remaining = max(0, self.prizes_remaining - 1)

    def unknown_pool(self):
        # cartas no vistas = en mazo + en premios ocultos
        return sum(self.deck_counts[c] - self.seen[c] for c in self.deck_counts)

    def belief(self, card_id):
        copies_unknown = self.deck_counts[card_id] - self.seen[card_id]
        pool = self.unknown_pool()
        if pool == 0 or self.prizes_remaining == 0:
            return 0.0
        return p_card_prized(copies_unknown, pool, self.prizes_remaining)

# REGLA 1 (continuo): recomputar bel(card) tras cada observe()/take_prize().
# REGLA 2 (reajuste de plan): si belief(key_piece) supera umbral, subir
#   prioridad de recovery/alternativa.
#   ej: belief('Kirlia')>0.30 con Gardevoir -> peso(Rare_Candy) += boost.
# REGLA 3 (jugada arriesgada): antes de gastar la mano por un KO, estimar
#   utilidad esperada de los premios que tomarás.

def expected_good_draw(belief_obj, useful_card_ids, n_prizes_to_take):
    pool = belief_obj.unknown_pool()
    pr = belief_obj.prizes_remaining
    if pr == 0 or pool == 0:
        return 0.0
    useful_unknown = sum(belief_obj.deck_counts[c] - belief_obj.seen[c]
                         for c in useful_card_ids)
    # E[# útiles entre los próximos n premios] (hipergeométrica)
    return n_prizes_to_take * useful_unknown / pool  # fracción premios útiles

# Decisión: ir all-in por KO solo si expected_good_draw alto O el KO ya
# decide la partida; si las piezas que necesitas para recuperarte están
# probablemente premiadas, no vacíes la mano.
```

Variables de estado nuevas para el agente: `prize_belief[card_id] ∈ [0,1]`, `prizes_remaining`, `unknown_pool`. Disparadores de recálculo: cualquier evento que revele cartas propias (search, draw, discard, mill) y cada KO que tome premios.

## → Hook de recompensa

Toca dos términos:

- **Reward de planificación (shaping, no terminal):** penaliza secuencias que dependen de una carta con `prize_belief` alta sin plan B. `r -= λ_prize · sum(belief(c) · plan_dependency(c))`. Empuja al agente a buscar redundancia cuando una pieza clave probablemente está premiada (principio 2).
- **Reward de evaluación de riesgo:** al modelar el valor de tomar un KO, usar `expected_good_draw` como bonus esperado de la jugada (principio 3): `Q(go_for_KO) += λ_draw · expected_good_draw(...)`. Esto integra el premio robado en el cálculo de utilidad del all-in.
- Sobre la victoria terminal (tomar el último premio = ganar) el prize-checking NO cambia el reward terminal, solo mejora la **política** que llega a él. Si el motor ya da reward por prize-trade favorable, prize-checking es información que afina ese término, no uno nuevo.

`null` para reward terminal directo; aplica como *shaping* sobre policy de búsqueda/secuenciación y como término de valor en decisiones de KO.

## Datos parseables

- La fuente no expone endpoints/exports. Es prosa estratégica.
- Math reproducible localmente con `scipy.stats.hypergeom` o `math.comb` (sin dependencia externa): `hypergeom.pmf(k, M, n, N)` con `M`=pool desconocido, `n`=copias objetivo, `N`=premios restantes.
- Decklists (los 60 card_ids con counts) los provee el motor cabt al inicio de partida; el belief state se inicializa desde ahí. No vienen de esta fuente (los mazos rotan; la math no).

## Caveats / sesgo

- El artículo es **cualitativo**; la matemática exacta (80.85% etc.) viene de la fuente de soporte lastlegume, no del propio TCGplayer. Cité ambas.
- El 10%/copia "naive" sobreestima ligeramente: condicionar por mano de inicio válida (mulligan) lo baja. Para un agente esto es de 2º orden; usar la hipergeométrica simple sobre `unknown_pool` es suficiente y más barato.
- En cabt con info imperfecta, tus propios premios SON desconocidos para ti (correcto modelarlos como ocultos), pero las cartas del rival añaden otra capa de incertidumbre no cubierta por esta fuente (esto trata solo TUS premios).
- Sesgo competitivo: el consejo "chequea singletons primero" asume presión de tiempo de torneo humano; un agente no tiene ese coste y puede mantener belief completo sobre las 60 cartas siempre. La restricción de "tiempo de search" del artículo NO aplica al bot.
- `rotates: false` — el concepto y la math son atemporales; solo los ejemplos de cartas (Mew VMAX, Gardevoir ex) rotan y son ilustrativos, no load-bearing.

## Fuentes citadas

- **TCGplayer — "The 3 Principles of Prize Checking"** (artículo principal, tier free). Cuerpo extraído vía búsqueda indexada (la página es JS-rendered y no carga por fetch directo). URL: https://www.tcgplayer.com/content/article/The-3-Principles-of-Prize-Checking/a015ad58-7ec5-41ea-ba50-56db0ee9d67f/ — autor no recuperable de forma fiable (la firma no se renderizó); TCGplayer es plataforma editorial de jugadores competitivos.
- **lastlegume — "Prize Card Probability in the Pokémon TCG"** (soporte matemático, derivación hipergeométrica con corrección por mulligan, ejemplos John Kettler/Oddish y Rowlet). URL: https://lastlegume.github.io/blog/prize_probability
