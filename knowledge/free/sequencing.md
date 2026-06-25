---
source: TCG Protectors — Advanced Sequencing Guide (Grandmaster Playbook)
url: https://tcgprotectors.com/blogs/pokemon-blog/pokemon-tcg-advanced-sequencing-guide-grandmaster-playbook
tier: free
concept: sequencing
rotates: false
extracted: 2026-06-23
---

## Qué es

Sequencing = la **política de ordenamiento de las acciones DENTRO de un mismo turno**. No cambia QUÉ cartas juegas, cambia EN QUÉ ORDEN las juegas. Con el mismo conjunto de cartas en mano, un orden distinto produce más información, menos compromiso irreversible y peor información para el rival. Es una decisión pura de *ordering* sobre una cola de acciones legales, no de selección de jugada.

La fuente lo formula como tres principios que se aplican a cada turno, más una pregunta-marco que el jugador debe hacerse al inicio del turno:

> "What do I want to achieve? What information do I need to make the best decision? And what is the last possible moment I can commit my resources?"

## Conceptos clave

**Principio 1 — Maximizar información (draw before you search).**
"Before you make any irreversible play, you should take every available action that gives you more information." Las acciones que *revelan cartas nuevas* (Supporters de robo: Professor's Research, Iono; habilidades que roban) van ANTES de las acciones de búsqueda dirigida (Ultra Ball, Artazon) y antes de cualquier jugada irreversible. Ejemplo: Professor's Research antes de Ultra Ball → ves 7 cartas nuevas antes de comprometer recursos buscando; al revés desperdicias el Ultra Ball porque el draw podría haberte dado lo que buscabas (o te obliga a descartar lo que acabas de encontrar).

**Principio 2 — Minimizar compromiso (retrasa lo irreversible).**
"Every action you take commits resources to a certain line of play. An advanced player holds off on these commitments for as long as possible." Acciones irreversibles (attach de energía del turno, benchear Pokémon multi-prize, evolucionar) se retrasan al ÚLTIMO momento posible. "Attaching your Energy for the turn should often be one of the very last actions you take before attacking." Attachear pronto te bloquea en una línea; esperar preserva flexibilidad según lo que robes después.

**Principio 3 — Negar información (juega disrupción antes de revelar el plan).**
"Every card you play telegraphs your strategy." Las cartas que fuerzan una decisión al rival (Sabrina, Boss's Orders) se juegan ANTES de revelar tu fuerza (Tools como Choice Belt, attach extra de energía). El rival decide a ciegas y puede cometer un error codicioso.

**Ejemplo canónico Sabrina (Ninetales / Choice Belt):**
- Secuencia MALA: Choice Belt en Ninetales → attach 2ª energía → Sabrina. El rival ve el atacante totalmente cargado y elige la promoción más segura.
- Secuencia BUENA: Sabrina primero. "They don't know if you have the Tool card or the extra energy. They might make a greedy play, promoting a valuable two-prize Pokémon they think is safe. After they make their choice, you then play your Tool and Energy and punish their mistake with a surprise Knock Out."

## → Heurística computable

Modelar el turno como ordenar una cola de acciones legales. Asignar a cada acción una **fase ordinal**; ordenar por fase asc, desempatar por valor. Esto traduce los 3 principios a un comparador estable.

```python
# Etiquetado de acciones por tipo de efecto
def phase(action, state):
    # FASE 0: revela info propia sin compromiso (draw masivo / refresh de mano)
    if action.reveals_new_cards_to_self:          # Professor's Research, Iono, draw abilities
        return 0
    # FASE 1: disrupción que fuerza decisión del rival con info imperfecta
    if action.forces_opponent_decision:           # Sabrina, Boss's Orders / gust
        return 1                                   # ANTES de revelar fuerza (Principio 3)
    # FASE 2: búsqueda dirigida (ya con máxima info en mano)
    if action.is_search:                           # Ultra Ball, Nest Ball, Artazon
        return 2
    # FASE 3: setup reversible (poner cartas, evolucionar si no es trampa de info)
    if action.is_setup and not action.irreversible:
        return 3
    # FASE 4: compromisos irreversibles que REVELAN fuerza -> lo más tarde posible
    if action.attaches_energy or action.attaches_tool or action.benches_multiprize:
        return 4                                   # Principio 2 + no telegrafiar (Principio 3)
    # FASE 5: ataque (cierra el turno)
    if action.is_attack:
        return 5
    return 3

def order_turn(legal_actions, state):
    return sorted(legal_actions, key=lambda a: (phase(a, state), -expected_value(a, state)))
```

Variables de estado relevantes:
- `info_gain(action)` — nº esperado de cartas nuevas reveladas a uno mismo (>0 ⇒ adelantar).
- `irreversibility(action)` ∈ {0,1} — energy attach del turno, evolución, bench multi-prize ⇒ 1.
- `telegraphs_strength(action)` ∈ {0,1} — Tool/energy que revela daño letal ⇒ retrasar tras disrupción.
- `forces_opp_decision(action)` ∈ {0,1} — Sabrina/Boss ⇒ jugar antes de telegrafiar.
- `opp_belief_uncertainty` — estimación de la incertidumbre del rival sobre tu mano. La disrupción debe ejecutarse mientras esta variable es ALTA (info imperfecta a tu favor).

Reglas-condición duras (gates antes del comparador):
1. `if has_draw_supporter and has_search: play_draw_before_search` salvo `early_game and need_basics` → entonces juega draw primero pero RESERVA el search (Artazon) como out de respaldo ("playing to your outs").
2. `if has_disruption(Sabrina/Boss) and plan_needs_KO: emit_disruption_before(tool_attach, energy_attach)`.
3. `energy_attach.scheduled_position = last_before_attack` salvo que el attach dispare una habilidad de ventaja (p. ej. descarte de energía → robo de Radiant Greninja), en cuyo caso adelantar.

Excepciones (romper la regla — la fuente lo marca como el nivel más alto de juego):
- Search antes de draw si en early game necesitas Basics y el draw podría no darlos: juega el draw y guarda el search como seguro.
- Attach temprano si el coste irreversible DISPARA ventaja neta de cartas mayor que la flexibilidad perdida.

## → Hook de recompensa

Sequencing es ortogonal al resultado de la jugada (mismo set de cartas), así que NO debe tener un término de reward terminal propio fuerte; el reward principal sigue siendo prize-trade / win. Pero sí admite **shaping intra-turno** para guiar la política de ordenamiento:

- `+w_info * cards_revealed_before_first_irreversible_action` — premia adelantar el draw (Principio 1).
- `-w_commit * irreversible_actions_taken_before_turn_end_minus_1` — penaliza compromiso prematuro (Principio 2); equivale a premiar attach tardío.
- `+w_deny * (opp_uncertainty_at_disruption_time)` — premia ejecutar disrupción (Sabrina/Boss) mientras la incertidumbre del rival sobre tu mano es alta (Principio 3).

Mantener los pesos `w_*` pequeños frente al reward de prize-trade: el sequencing es un *tie-breaker* entre líneas de igual valor de cartas, no un objetivo en sí. `null` si el motor ya optimiza orden por búsqueda de árbol completo intra-turno (en ese caso el shaping es redundante).

## Datos parseables

La fuente es un artículo de blog en prosa, no expone endpoints, exports ni formatos de datos. No hay JSON/CSV ni tabla descargable; sólo una tabla HTML de 3 filas (Principio / Core Goal / Key Example) reproducida arriba. Las etiquetas de fase del comparador deben construirse mapeando cada carta a su tipo de efecto desde la base de cartas del motor (draw / search / disruption / tool / energy / attack), no desde esta fuente.

## Caveats / sesgo

- Fuente comercial (TCG Protectors vende fundas/displays); el contenido estratégico es secundario al marketing, pero los principios son estándar y coinciden con SixPrizes, PokeBeach y TCGplayer (ver búsquedas).
- NO da un checklist ordinal explícito de turno; el comparador de fases de arriba es una INTERPRETACIÓN mía de los 3 principios, no una lista textual de la fuente.
- Los ejemplos usan cartas concretas (Sabrina, Iono, Artazon, Professor's Research, Choice Belt, Radiant Greninja) que SÍ rotan; pero el CONCEPTO de ordenamiento (`rotates: false`) es invariante a rotación — sólo cambia el mapeo carta→fase.
- La fuente admite que las excepciones dependen de "knowledge of the meta and your own deck" pero no detalla CÓMO el meta altera el ordenamiento: queda como caja negra a calibrar empíricamente.
- Bajo información imperfecta (motor cabt), el Principio 3 ("opp_uncertainty alto al disruptir") es el más valioso y el más difícil de medir: requiere un modelo de creencia del rival sobre tu mano que la fuente asume implícito.

## Fuentes citadas

- TCG Protectors — *Pokémon TCG Advanced Sequencing Guide: Master Optimal Turn Order & Strategies (Grandmaster Playbook)*. URL: https://tcgprotectors.com/blogs/pokemon-blog/pokemon-tcg-advanced-sequencing-guide-grandmaster-playbook — Autoría: "TCG Protectors team", liderado por un fundador que es "the owner of Phoenix Cards in Phoenix, Arizona", coleccionista desde la era Diamond & Pearl, organizador de streams y eventos semanales. (Credencial = tienda local + comunidad, no jugador de circuito verificado; tratar como fuente de fundamentos, no de top-meta.)
- Corroboración cruzada de los mismos 3 principios (no citados en el fichero pero verifican que no es idiosincrásico): SixPrizes tag/sequencing, PokeBeach "Steps for Success — How to Master Sequencing" (2024), TCGplayer "How to Sequence Correctly In The Pokémon TCG".
