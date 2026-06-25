---
source: Captions de vídeo (yt-dlp en.vtt) — Play! Pokémon oficial (casters), Alloutblitzle (guía control)
url: youtube — NEahGtRGDIM (Worlds 2024 final), gIt8wdzvVuU (Worlds 2025 final), EVZ6eRSKIko (Pidgeot Control guide)
tier: free
concept: belief-state, prize-trade, BEATDOWN vs CONTROL role, anti-deck-out, single-prize denial
confidence: alta (captions primarias leídas; atribución verificada por oEmbed)
rotates: parcial (cartas/meta rotan; los métodos no)
extracted: 2026-06-25
---

# Enriquecimiento Tier-3 — alimenta H7 (lectura bayesiana) / H8 (rol BEATDOWN-CONTROL) / anti-deck-out

> Destilado de 3 captions primarias obtenidas con yt-dlp (los Worlds finals oficiales SÍ traen
> captions; los streams de canal a veces también). Solo recojo lo que AÑADE sobre las fichas ya
> escritas (`video-enrichment-2026-06-24.md`). Captions crudos en scratchpad (copyright), NO en el repo.
>
> ⚠️ Atribución corregida (lección de la sesión previa, que cazó "Tricky Gym"):
> - El vídeo `yZki7OdJY7A` ("Tord Reklev Psychic Elegance") que el curador etiquetó como deck-tech de
>   un finalista (H7) y atribuyó a "TordTCG" es en realidad un **unboxing de "Pete's Packs"** de la
>   caja física del World Championships deck. El uploader dice literalmente "I don't know a ton about
>   the way Pokémon works now" y pregunta a la audiencia qué es la Lost Zone. **CERO razonamiento de
>   juego. Descartado** — no es H7, no transfiere nada.
> - El vídeo `Idx-R5lpx70` (Worlds 2023, Kelley vs Reklev) **NO tiene captions disponibles**
>   (yt-dlp: "There are no subtitles for the requested languages"). No transcrito, no destilado.

## 1. Pidgeot Control (Alloutblitzle) → operacionaliza H8 (rol CONTROL) + anti-deck-out + el dilema del stall espejo

La pieza más densa para H8. Lo que el bot necesita saber cuando juega/enfrenta CONTROL:

```python
# A) El reloj es un recurso. En Bo1 con límite de tiempo, NO tomar premios puede ser correcto.
#    El rival CONTROL "se sienta con un tablero lleno y te reta a tomar un KO" — morder el cebo
#    activa su Counter Catcher o te deja sin él. La presión != tomar premios.
def should_take_ko(state):
    # presionar (forzar descartes/avance) sin tomar premio puede dominar al KO
    if opp_is_control_baiting(state):
        return pressure_without_prize(state)   # atacar para forzar avance, no para KO
    return normal_prize_logic(state)

# B) "Calculated risk" = ir a por la pieza-llave del rival SOLO si conoces su lista.
#    Ej.: ir con un atacante a descartar el Iono de su mano para forzar el avance del juego,
#    pero solo si tu atacante no muere y si SABES qué hay en su mazo (Limitless avg-count).
def go_for_disruption_target(state):
    if not know_opp_decklist(state):  # sin conocer la lista -> indecisión, no lo hagas
        return False
    return attacker_survives(state) and target_is_key_piece(state)

# C) Prize-check PARCIAL y por prioridad bajo presión de reloj (refina H4b).
#    No chequear los 6: chequear SOLO las piezas-llave del matchup concreto
#    (gusting, recovery, atacante clave, counter-catcher). El chequeo total cuesta minutos
#    que en Bo1 no tienes. En partidas SIN reloj (Bo3/cabt), sí chequear todo.
def prize_check_under_clock(matchup):
    return key_pieces_for(matchup)   # subset, no los 6

# D) Espejo stall vs control / anti-deck-out: el modo de derrota es quedarse sin recursos
#    o sin avanzar. Mantener "recursos infinitos" (recursión de supporter) gana el espejo
#    de no-progresión. Quien se queda sin gas pierde, no quien tiene menos premios.
```

**Upgrade H8 (P0):** el rol CONTROL no es "tomar premios", es **gestionar tres recursos a la vez:
premios, RELOJ y gas del rival**. Decisión central recurrente: ¿presionar sin tomar premio (para
no darle Counter-Catcher / no quedarme sin pieza de gust) o tomar el KO? El default del top es
**presionar sin premiar** cuando el rival no progresa. → conecta directo con el modo de derrota
dominante de Alakazam (deck-out) y con la idea de "no premiar al rival" del punto 3.

**Upgrade H4b (matiz):** el prize-check del top es **parcial y priorizado por matchup** cuando hay
reloj, no exhaustivo. En cabt no hay reloj → chequear completo sigue siendo correcto, PERO la
priorización por pieza-llave (qué cuento primero) transfiere como orden de actualización del belief.

## 2. Final Worlds 2024 (Cifuentes vs Shiokawa, casters Play! Pokémon) → H7 + denegación por single-prize + judge como negación de turno

Casters verbalizan el belief-state y la teoría de premios. Lo NUEVO frente a las fichas:

```python
# A) Atacante de 1 premio como NEGACIÓN de prize-map (transfiere a H1b/H8). Verbatim del caster:
#    "es una forma de tomar un premio mientras le dices a tu rival: no consigues nada por KOearme".
#    Un single-prize atacante hace que el KO del rival NO avance su mapa de 6 premios.
def single_prize_denial_value(my_attacker, opp_plan):
    # forzar al rival a "abrirse paso por 3 EX" en vez de premios baratos
    return opp_plan.prizes_per_ko_against(my_attacker) == 1   # le niegas el 2x1

# B) "Judge/Iono como negación de ATAQUE" (refina H5/disrupción). El caster:
#    "no tienes double-turbo ahora mismo, así que te hago judge: o robas el double-turbo
#    o literalmente no puedes atacar el turno que viene". La disrupción de mano se usa
#    quirúrgicamente para QUITAR el ataque del rival, no solo para reducir cartas.
def disruption_targets_attack(opp_state):
    return opp_lacks_attack_enabler(opp_state)   # disrumpir cuando le falta la pieza de ataque

# C) Belief sobre copias limitadas: el caster RASTREA cuántos atacantes-llave le quedan al rival
#    ("solo le queda 1 Iron Thorns disponible; el 4º está premiado"). Cuando un atacante clave
#    se va a Lost Zone o se premia, el conteo de outs restantes CAMBIA la valoración del trade.
def attacker_count_belief(deck_total, in_discard, in_play, prized):
    return deck_total - in_discard - in_play - prized   # outs reales restantes, no nominales

# D) "El mini-juego de la energía": vs un mazo sin aceleración, gustear Pokémon de retreat-cost
#    para forzarle a quemar energía es una línea de victoria por agotamiento (anti-recurso),
#    distinta del prize-race. El caster lo llama explícitamente "the mini game: can I remove
#    energy as fast as you attach it".
```

**Upgrade H7 (P1):** el belief no es solo "¿qué tiene en mano?", incluye **conteo de outs restantes
de cada pieza-llave** (total − descarte − juego − premios). Que el 4º atacante esté premiado o en
Lost Zone cambia si el rival puede sostener su plan → afecta directamente la valoración del trade.

**Upgrade H1b/H8 (P1):** añadir al `prize_map` la noción de **negación**: jugar un atacante de 1
premio para que el KO rival no avance su mapa, y reconocer cuándo el rival lo está haciendo contra ti
(su KO sobre tu single-prize "no vale" — no te apresures a vengarlo).

## 3. Final Worlds 2025 (McKay vs Newdorf, casters Play! Pokémon) → patrón "checkmate que se disuelve" + math de damage-counter

Mucho de este cast es narración de mecánica concreta (rota), pero hay un patrón de método claro:

```python
# A) "Setup for a checkmate and hope it exists next turn" — el caster repite que el jugador de
#    setup/control monta un mate de varios turnos que el rival DESHACE justo a tiempo (quitando
#    la pieza, Iono, recursión). Lección transferible: un plan de KO multi-turno es frágil si
#    depende de que TODAS las piezas sobrevivan el turno del rival. Preferir líneas que no se
#    deshacen con UNA respuesta del rival.
def plan_robustness(plan, opp_outs):
    # cuántas respuestas del rival rompen el plan? 1 respuesta-rompe = plan frágil
    return num_opp_responses_that_break(plan, opp_outs)   # minimizar

# B) Prize-check disciplinado al barajar setup: se OBSERVA a un finalista rastrear premiadas en
#    búsquedas concretas (p.ej. "vio que el doble Dloak estaba premiado"), + narración del caster
#    sobre piezas premiadas. Sugiere H4 como práctica de élite; NO se observa "ambos, cada búsqueda".

# C) "Dar premios a propósito" puede ser correcto: una pieza que se sacrifica para mover/colocar
#    daño (curse-blast-like) regala premios pero habilita un KO mayor. El trade no es
#    "premio por premio" sino "premios cedidos vs daño colocado que cierra la partida".
```

**Refuerza (no nuevo):** robustez del plan = nº de respuestas del rival que lo rompen; minimizarlo.
Conecta con el gate de factibilidad de H1b. El prize-check de élite se observa en búsquedas
concretas (no como "siempre, ambos") y se actualiza al barajar setup (consistente con H4/H4b).

## Caveats / honestidad

- ⚠️ Cartas y matchups (Pidgeot, Gardevoir, Dragapult, Iron Thorns, Roaring Moon, Snorlax, Lugia…)
  **rotan** y cabt ≠ Standard → quédate con el MÉTODO (rol control, negación por single-prize, conteo
  de outs, disrupción que niega ataque, reloj como recurso), NO con las cartas ni los matchups.
- Atribución verificada por oEmbed: NEahGtRGDIM y gIt8wdzvVuU = "Play Pokémon" (oficial, casters);
  EVZ6eRSKIko = "Alloutblitzle". El cuarto, yZki7OdJY7A, NO es deck-tech de Reklev sino unboxing de
  "Pete's Packs" → descartado por inútil (corrige la atribución y el tag H7 del curador).
- Idx-R5lpx70 (Worlds 2023) sin captions → no transcrito, no destilado. obtained=false.
- El cast de 2025 es más narración-de-mecánica que verbalización-de-decisión; el rendimiento de
  destilación es menor que el de la guía de control. Confianza alta en los métodos; captions crudos
  NO se commitean (copyright), solo esta destilación.
