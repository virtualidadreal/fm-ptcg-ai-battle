---
source: TCG Protectors (Deck Archetypes Guide) + Flipside Gaming
url: https://tcgprotectors.com/blogs/pokemon-deck-guides/pokemon-tcg-deck-archetypes-guide-aggro-control-combo-midrange
tier: free
concept: archetypes
rotates: false
extracted: 2026-06-23
---

## Qué es

Marco de **archetypes** (Aggro / Control / Combo / Midrange-toolbox) y, sobre todo, el concepto de **ROL EN EL MATCHUP** (beatdown vs control): la regla #1 del jugador midrange es "identificar tu rol — ¿eres el agresor o el controlador?". El rol NO es fijo por mazo, sino que se asigna *por enfrentamiento*. Esto es lo que importa para un agente: no necesita saber el nombre del arquetipo, necesita decidir cada turno si su política es **atacar ASAP (carrera de premios)** o **negar recursos / sobrevivir (attrition)**. El error clásico es jugar de control en un matchup donde deberías ser beatdown (te superan en setup) o jugar de beatdown cuando vas perdiendo la carrera.

Los arquetipos se ubican en **dos ejes**: Velocidad (rápido=Aggro ↔ lento=Control) y Sinergia (cartas independientes ↔ combinaciones específicas). El meta es un "rock-paper-scissors": Control > Midrange > Aggro > Control.

## Conceptos clave

- **Aggro** (rápido, baja sinergia): gana la *carrera de premios* lo antes posible, presión desde turno 1, busca OHKOs. Debilidad: "poor comeback potential" si el asalto inicial falla. Cómo identificar: si OHKOeás y vas por delante o empatado en premios, ERES el beatdown.
- **Control** (lento, sinergia media): "gana impidiendo que el rival juegue" — niega recursos, busca deck-out o attrition. NO prioriza tomar premios. Sub-tipos: Stall/Wall (Pokémon que no pueden noquear + trampa de retirada), Mill (descarte de mazo rival).
- **Combo** (velocidad media, alta sinergia): setup lento → turno explosivo ("going off"). Vulnerable a disrupción de mano (Iono, Roxanne) y a que le ataques los Pokémon de setup temprano.
- **Midrange/toolbox** (equilibrado): cambia entre postura ofensiva y defensiva *según matchup*. Contra Aggro → atacantes de 1 premio para ganar trades; contra Control → arma un golpe grande + disrupción. Es el arquetipo que más necesita el clasificador de rol.
- **Regla de oro del rol**: "tu primera prioridad es identificar tu rol — ¿beatdown o controller?". Forzar al rival a un rol que no puede cambiar es ganar.
- **Spread de matchup cuantificable** (Flipside): un buen mazo busca ~60/40, 50/50, 40/60 vs el top-3; ideal 50/50 o mejor vs varios. Spread >50/50 = favorito; <50/50 = unfavored. **El más rápido suele ser beatdown; el favorito tiende a poder permitirse jugar lento (control); el unfavored debe "robar" tempo siendo el agresor.**

## → Heurística computable

Clasificador de rol que condiciona la política del agente. Se recalcula cada turno (info imperfecta → creencias):

```python
# Estado observable / estimado
my_speed       = est_turns_to_first_ohko(my_board, my_hand)   # turnos hasta poder OHKO
opp_speed      = belief_opp_turns_to_ohko(seen_cards, prizes) # creencia (info imperfecta)
prize_diff     = opp_prizes_left - my_prizes_left   # >0 = voy ganando la carrera
my_can_ohko    = exists_attacker_that_ohkos(opp_active)
opp_can_ohko   = belief_opp_ohkos_me(my_active)
i_can_deckout  = belief_opp_deck_size_low() or have_mill_engine()
matchup_fav    = prior_winrate(my_archetype_guess, opp_archetype_belief)  # 0..1, prior del meta

def assign_role():
    # 1) Si voy por delante en premios Y puedo OHKO -> BEATDOWN puro
    if prize_diff > 0 and my_can_ohko:
        return "BEATDOWN"
    # 2) Si soy claramente más rápido -> BEATDOWN (aggro gana a control por velocidad)
    if my_speed < opp_speed - 1:
        return "BEATDOWN"
    # 3) Si NO puedo ganar la carrera (rival OHKO y yo no, o premios en contra) ->
    #    pivota a CONTROL: niega recursos / sobrevive / busca attrition o deck-out
    if (opp_can_ohko and not my_can_ohko) or prize_diff < -1:
        return "CONTROL" if i_can_deckout or have_disruption() else "STALL_TEMPO"
    # 4) Empate de velocidad: el unfavored roba tempo (beatdown), el favorito controla
    return "BEATDOWN" if matchup_fav < 0.5 else "CONTROL"

role = assign_role()
```

Cómo el rol condiciona la **política** (pesos sobre acciones del motor cabt):

```python
if role == "BEATDOWN":
    weight(search_attacker)  += HIGH     # "usa tus search cards agresivamente early"
    weight(accelerate_energy)+= HIGH
    weight(attack_for_ohko)  += HIGH
    weight(single_prize_atk) += MED      # vs aggro rival: ganar prize-trade con 1-premiers
    weight(setup_passive)    -= 
elif role in ("CONTROL", "STALL_TEMPO"):
    weight(disrupt_hand)     += HIGH     # Iono/Roxanne/Eri vs combo y setup
    weight(deny_energy)      += HIGH     # Crushing Hammer, Eri
    weight(heal / wall)      += HIGH
    weight(target_setup_mon) += MED      # matar Pokémon de setup antes del "going off"
    weight(take_prize)       -= LOW      # control no prioriza premios; ojo deck-out propio
```

Variables de creencia clave (info imperfecta): `belief_opp_archetype` (distribución sobre {aggro,control,combo,midrange} actualizada por cartas vistas — p.ej. ver Crushing Hammer/Eri sube control; ver acelerador de energía + basic grande sube aggro), `belief_opp_turns_to_ohko`, `belief_opp_deck_size`. Anti-combo: si `belief_opp_archetype==combo` y `opp_setup_in_progress`, dispara disrupción de mano ANTES del turno de payoff.

## → Hook de recompensa

Toca el término de **shaping de tempo/prize-race condicionado al rol**, no un reward nuevo terminal (el reward terminal sigue siendo ganar = 6 premios o deck-out rival):

- `reward += w_role * role_alignment`, donde `role_alignment` premia acciones coherentes con el rol asignado (beatdown→reducir tu `turns_to_lethal`; control→reducir recursos/mano/energía rival y tu riesgo de ser OHKOeado).
- Como **potential-based shaping** para no romper la política óptima: `Φ_beatdown = -est_turns_to_close_prize_lead`; `Φ_control = -opp_usable_resources`. Reward shaping = `γ·Φ(s') - Φ(s)` con el Φ del rol activo.
- Penalización por **mismatch de rol**: si vas perdiendo la carrera (`prize_diff<0`, `opp_can_ohko`) y aun así juegas pasivo/atacas sin OHKO → pequeña penalización (refleja "poor comeback potential" del aggro mal asignado).
- Si no se quiere shaping: `null` y dejar que el rol solo reordene el *prior* sobre acciones (policy bias), sin tocar reward.

## Datos parseables

Las fuentes son artículos editoriales en HTML, **sin endpoints/exports/API**. Datos estructurables manualmente:
- Matriz 2-ejes (Velocidad × Sinergia) por arquetipo → tabla de priors `{aggro, control, combo, midrange}`.
- Tabla rol→prioridad de cartas (beatdown: search/aceleración/OHKO; control: disrupción/heal/denial) — directamente codificable como pesos de política.
- Umbrales de spread Flipside: `{60/40, 50/50, 40/60}` como buckets de `matchup_fav` (favored / even / unfavored).
- Señales-firma de arquetipo para el clasificador bayesiano: aceleración+basic grande→aggro; Crushing Hammer/Eri/Block→control; Buddy-Buddy Poffin/Arven multi-setup→combo; mix de 1-premiers + atacante grande→midrange.

## Caveats / sesgo

- Los **ejemplos de mazos rotan** (Raging Bolt, Dragapult, Snorlax Stall, Gholdengo, Gardevoir son del meta de extracción 2026, no del entorno cabt del reto). El agente NO debe hardcodear nombres; sí los *conceptos de rol y los ejes*, que no rotan (`rotates:false` aplica al marco, no a las listas).
- Sesgo "Magic-importado": el propio Flipside avisa que aggro/midrange/control vienen de MTG y en Pokémon el deck-out y el prize-trade alteran la dinámica (no hay vida, hay 6 premios + 60 cartas de mazo).
- Flipside (metagame) **niega explícitamente** asignar beatdown/control solo por velocidad/favorabilidad: dice que el rol es "intrínseco al diseño del mazo". El clasificador dinámico de arriba es síntesis del consejo midrange de TCG Protectors + dinámica RPS de Flipside; trátalo como *prior reordenable*, no como verdad fija.
- Cuidado con el **deck-out propio**: jugar de control (search agresivo previo) puede hacerte perder por agotar tu mazo; el reward de control debe incluir tu propio `deck_size`.
- Info imperfecta: `opp_speed`, `opp_deck_size`, arquetipo rival son **creencias**, no observables; el clasificador debe degradar con incertidumbre (cuando la distribución de arquetipo está plana, default a BEATDOWN si eres más rápido, si no a comportamiento balanceado).

## Fuentes citadas

- **TCG Protectors** — "Pokémon TCG Deck Archetypes Guide: Aggro, Control, Combo & Midrange Strategies". Guía editorial de tienda especializada (sleeves/protección + contenido competitivo). URL verificada: https://tcgprotectors.com/blogs/pokemon-deck-guides/pokemon-tcg-deck-archetypes-guide-aggro-control-combo-midrange — fuente de la regla "identifica tu rol: beatdown o controller", ejes Velocidad×Sinergia, y tabla rol→prioridades.
- **Flipside Gaming** — "Aggro, Mid-Range, Control… Wait, this isn't Magic!". Blog de tienda/comunidad competitiva. URL verificada: https://flipsidegaming.com/blogs/pokemon-blog/aggro-mid-range-control-wait-this-isn-t-magic — dinámica rock-paper-scissors (Control>Midrange>Aggro>Control) y "poor comeback potential" del aggro.
- **Flipside Gaming** — "How to Metagame in the Pokemon TCG". URL verificada: https://flipsidegaming.com/blogs/pokemon-blog/how-to-metagame-in-the-pokemon-tcg — umbrales de spread (60/40, 50/50, 40/60; ideal ≥50/50 vs varios) y advertencia contra el over-teching.
