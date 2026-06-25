---
source: Tord Reklev (TCG Park / Pokemon.com) + Jason Klaczynski (jklaczpokemon.com)
url: https://www.justinbasil.com/guide/testing
tier: free
concept: deckbuilding
rotates: false
extracted: 2026-06-23
---

## Qué es

Filosofía atemporal de construcción de mazos destilada de dos jugadores con credenciales verificadas:

- **Tord Reklev** (Noruega) — primer jugador en ganar los 4 Internacionales (Grand Slam), 2º en el Mundial. Perfil verificado en Limitless (limitlesstcg.com/players/86) y autor invitado en Pokemon.com.
- **Jason Klaczynski** — 3x Campeón del Mundo Masters (2006, 2008, 2013) + Campeón Nacional US 2015. Verificado en Bulbapedia. Mantiene jklaczpokemon.com (archivo histórico 1999–2016).

El núcleo es **consistencia primero**: un mazo solo gana si *primero puede funcionar*. Esto NO rota con el meta porque trata de la estructura del mazo (motor de cartas, redundancia, no-cartas-muertas), no de qué cartas concretas son legales. Para un agente con info imperfecta, esto se traduce en mantener una creencia sobre la "función esperada" del propio mazo y del rival turno a turno.

## Conceptos clave

1. **Consistencia como objetivo, no como ventaja de espejo.** Klaczynski: "Consistency is the goal — to execute your strategy every time." La ventaja en el espejo es solo mentalidad; lo que se construye es la capacidad de ejecutar el plan *todas* las partidas. Reklev: "Your deck will never win if it can't function in the first place."

2. **Regla de las 10 partidas (criterio de poda empírico).** Reklev: si juegas 10 partidas y nunca has usado una carta para ganar, córtala — aunque sea genial contra un mazo concreto. Un tech que solo sirve "en esa situación" no compensa el coste de inconsistencia.

3. **Cartas flexibles vs hard counters.** Klaczynski: las cartas flexibles sirven a más de un propósito y *nunca se alejan de la estrategia principal*; los hard counters son una "reacción mecánica" buena para una sola situación. Preferir opciones flexibles que dan al jugador decisiones, no respuestas rígidas de un solo uso.

4. **Los Trainers son la espina dorsal.** Reklev: tras rotación "los Trainers son las primeras cartas que se echan en falta" (draw Supporters como Iono / Professor's Research son staples de casi cualquier mazo). El motor de robo/búsqueda es lo primero que define la viabilidad del mazo, antes que los ataques.

5. **Plan tempo vs plan setup.** Reklev: cuando el formato favorece coger premios rápido, los mazos rápidos tienen ventaja inmediata; cuando hay disrupción, hay que invertir en setup y cuidar el banco. El deckbuilder elige un eje según la presión del meta.

6. **Disrupción que escala con premios (Iono).** El efecto de robo-disrupción escala con cuántos premios has cogido — un puente directo entre *prize count* y *fuerza de la mano del rival*.

7. **Requisitos mínimos estructurales (checklist JustInBasil).** Todo mazo legal/jugable: exactamente 60 cartas, regla de 4 (máx. 4 copias, Prism Star máx. 1), ≥1 Pokémon Básico, **incluye draw Supporters, incluye búsqueda de Pokémon (ball/search), incluye una forma de gusting** (sacar al activo del rival).

## → Heurística computable

```python
# --- 1. Auto-evaluación de función del mazo (creencia sobre el propio estado) ---
# Reklev: "no gana si no puede funcionar". Antes de optimizar tablero, asegurar setup.
def deck_function_score(state):
    s  = 1.0 if has_active_attacker_with_energy(state) else 0.0
    s += 0.5 if draw_supporter_in_hand_or_reachable(state) else -0.5  # motor de robo
    s += 0.3 if search_card_available(state) else 0.0                 # ball/search
    s += 0.2 if gust_available(state) else 0.0                        # forma de gusting
    return s
# Si deck_function_score < umbral: priorizar acciones de setup sobre acciones de daño.

# --- 2. Iono / disrupción escala con premios (puente prize->mano rival) ---
# La mano del rival tras disrupción ~ premios que LE quedan al rival.
def opp_hand_after_iono(opp_prizes_remaining):
    return opp_prizes_remaining  # creencia: menos premios rival => mano más pequeña
# Reward para JUGAR disrupción crece cuando el rival tiene pocos premios restantes (mano pequeña).
def disruption_value(opp_prizes_remaining):
    return max(0, (6 - opp_prizes_remaining)) / 6.0  # 0 al inicio, máx cuando rival a 1 premio

# --- 3. Evaluación de utilidad de carta tech (regla de las 10 partidas, en runtime) ---
# El agente trackea, por carta, una tasa de uso-que-contribuye-a-ganar (EMA online).
card_usefulness = defaultdict(lambda: 0.5)   # prior neutro
def update_card_usefulness(card, contributed_to_win, alpha=0.1):
    card_usefulness[card] = (1-alpha)*card_usefulness[card] + alpha*(1.0 if contributed_to_win else 0.0)
# Sesgo de mulligan/juego: si card_usefulness[card] muy baja, tratarla como dead draw (descartar antes).

# --- 4. Flexible > hard counter en selección de jugada ---
# Al elegir entre dos cartas/jugadas con valor inmediato similar, romper empate por flexibilidad.
def play_priority(action):
    base = action.expected_value
    flex_bonus = 0.15 if action.serves_main_strategy and action.multi_purpose else 0.0
    rigidity_penalty = -0.10 if action.single_situation_only else 0.0
    return base + flex_bonus + rigidity_penalty
```

Variables de estado clave: `deck_function_score` (¿puedo ejecutar mi plan?), `opp_prizes_remaining` (insumo de la disrupción), `card_usefulness[card]` (EMA de contribución a victorias), flags `serves_main_strategy` / `multi_purpose` / `single_situation_only` por acción.

## → Hook de recompensa

- **Término de setup/consistencia:** `reward += w_setup * deck_function_score(state)` los primeros turnos — penaliza estados donde el mazo "no puede funcionar" (Reklev). `w_setup` decae conforme avanza la partida.
- **Término de disrupción ligado a premios:** `reward += w_disrupt * disruption_value(opp_prizes_remaining)` al jugar Iono/disrupción — captura que la disrupción escala con premios cogidos.
- **Shaping de poda de techs:** no es reward de partida sino meta-señal de deckbuilding/política: cartas con `card_usefulness` baja reciben prioridad de descarte. Si el reto es solo *jugar* (mazo fijo), este hook es **null** y la regla de las 10 partidas se aplica offline al elegir lista.
- Flexibilidad: `reward += w_flex * flex_bonus` como tie-break entre jugadas de valor similar.

## Datos parseables

- **Limitless TCG** — perfil/resultados verificables: `https://limitlesstcg.com/players/86` (Reklev). API/exports de listas en limitlesstcg.com (decklists con counts por carta, parseables a `{card: count}`).
- **JustInBasil checklist** estructurado (`justinbasil.com/guide/testing`): condiciones booleanas directas (60 cartas, regla de 4, ≥1 básico, tiene draw/search/gust) → validador de legalidad/jugabilidad del mazo.
- **jklaczpokemon.com** — archivo histórico 1999–2016 con decklists por era (no API; HTML por artículo). Útil como corpus de listas-arquetipo, NO como reglas en vivo.
- Formato de lista estándar PTCG: `N CardName SET NUM` → parseable a diccionario de counts para validar regla de 4 y ratios de motor.

## Caveats / sesgo

- **Sesgo de formato Standard/eventos grandes.** Ambos jugadores teorizan sobre formatos competitivos con Supporters de robo fuertes (Research, Iono). El motor `cabt` del reto puede tener una pool/legalidad distinta — verificar qué cartas de robo/búsqueda existen ahí antes de fijar pesos.
- **La "regla de las 10 partidas" es heurística humana, no probabilidad.** Como EMA online necesita N partidas para converger; con info imperfecta y varianza alta, no cortar techs con poca muestra.
- **Klaczynski es retro (1999–2016).** Sus principios *atemporales* (consistencia, flexible>hard-counter) trasladan; sus listas concretas NO. Marcado `rotates:false` solo por la capa filosófica.
- No conseguí extraer ratios numéricos exactos de supporters/energía de fuente primaria (las clases de Reklev son de pago en Metafy; jklaczpokemon no expone el cuerpo en fetch). Los counts de la heurística son flags estructurales, no ratios citados.
- `disruption_value` asume que el rival no puede recomponer la mano fácil; en pools con mucho robo extra el supuesto se debilita.

## Fuentes citadas

- Tord Reklev — Grand Slam Internacionales (primer jugador en ganarlos los 4), 2º Mundial. Perfil: https://limitlesstcg.com/players/86 ; cita "Your deck will never win if it can't function in the first place" y regla de las 10 partidas vía JustInBasil testing guide: https://www.justinbasil.com/guide/testing
- Tord Reklev — principios de rotación (Trainers primero, tempo vs setup, Iono escala con premios): https://www.pokemon.com/us/strategy/get-ready-for-the-2026-pokemon-tcg-standard-rotation-with-tord-reklev
- Jason Klaczynski — 3x Campeón del Mundo (2006/2008/2013) + Nacional US 2015 (verificado en Bulbapedia: https://bulbapedia.bulbagarden.net/wiki/Jason_Klaczynski). Archivo de teoría/listas: https://jklaczpokemon.com/ . Principios "consistency is the goal" y flexible-vs-hard-counter vía discusión de selección de lista (60cards.net, user 20 art. 35).
- JustInBasil — checklist estructural de deckbuilding/testing (60 cartas, regla de 4, draw/search/gust): https://www.justinbasil.com/guide/testing
