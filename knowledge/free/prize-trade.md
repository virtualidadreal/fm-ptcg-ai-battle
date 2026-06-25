---
source: TCG Protectors (Prize Trade Guide + Prize Mapping Guide 2026) + Pokémon Authority + Levels PTCG
url: https://tcgprotectors.com/blogs/pokemon-blog/pokemon-tcg-prize-trade-guide-advanced-prize-mapping
tier: free
concept: prize-trade
rotates: false
extracted: 2026-06-23
---

## Qué es

El **prize-trade** (intercambio de premios) es la economía central de Pokémon TCG: una partida es un **intercambio de recursos** donde cambias KOs por cartas de premio, y ganas el que toma sus **6 premios primero** (o deckea / deja al rival sin Pokémon). Cada KO entrega un número de premios que **depende del tipo de Pokémon noqueado**, no de cuántas cartas valió noquearlo. Por eso el valor de un KO **no es binario** ("le di KO" / "no") sino un **intercambio neto**: lo que TÚ ganas en premios menos lo que el rival gana cuando te devuelve el KO.

La consecuencia táctica clave: un atacante de 1 premio que noquea a un Pokémon ex de 2 premios produce un trade **neto +1**, mientras que un VMAX (3 premios) que noquea a un Pokémon de 1 premio es un trade **neto −2** cuando te lo devuelven. Construir el plan de la partida sobre esta matemática es el **prize mapping**.

## Conceptos clave

- **Tabla de valor de premios (regla "Rule Box"):**
  - Pokémon normal (Basic/Stage 1/Stage 2, sin Rule Box): **1 premio**
  - Pokémon ex / V / VSTAR / Mega ex: **2 premios**
  - Pokémon VMAX / Tag Team GX: **3 premios**
- **Intercambio neto, no binario:** el valor de un KO = `premios_que_tomas − premios_que_concedes_al_responder`. Single-prize que mata un ex = `2 − 1 = +1`. VMAX que mata un single = `1 − 3 = −2`.
- **Prize map (mapa de premios):** la secuencia planeada de KOs que suma 6. Tipos canónicos:
  - **2-2-2** — "aggressive ex focus": tres KOs a ex = 6 premios. El más común en Standard.
  - **3-3** — dos VMAX = 6 premios. Alto riesgo / alta recompensa, solo 2 KOs para perder.
  - **1-1-2-2** — "chip away singles first": dos singles + dos ex; mazos con atacantes single-prize eficientes.
  - **2-1-2-1** — recomendado en Standard 2026 frente a mixtos ex + swarm.
- **Asimetría defensiva:** un mazo single-prize obliga al rival a **6 KOs** para ganar; un mazo VMAX/Tag Team solo necesita que le den **2 KOs** para el barrido completo. Ratio estructural 6-vs-2.
- **Forzar el 7º premio:** construir el tablero con **solo atacantes de 1 premio** rompe el mapa 2-2-2 del rival (que esperaba 3 KOs) y le obliga a **6 KOs separados**, agotando sus recursos limitados (Boss's Orders / gusts) y su tempo. "Forzar el 7º" = hacerle tomar más KOs de los que su mapa óptimo necesitaba.
- **No benchear amenazas multi-premio innecesarias:** "no pongas en banca un Pokémon multi-premio salvo que tengas que hacerlo o vayas a usarlo ese turno"; cada ex en banca le regala al rival un mapa de premios más fácil.
- **Prize differential como señal de tempo:** ir 6-a-2 abajo es un perfil de amenaza estructuralmente distinto a ir 6-a-4; cambia la asignación de recursos y el sequencing.
- **Counter Catcher / cartas "behind":** se activan cuando vas **por detrás en premios** (p.ej. tú 6 restantes, rival 5), desbloqueando jugadas que estando por delante no tienes.

## → Heurística computable

```python
PRIZE_VALUE = {  # premios concedidos al rival si ESTE Pokémon es noqueado
    "single": 1,        # Basic/Stage1/Stage2 sin Rule Box
    "ex": 2, "v": 2, "vstar": 2, "mega_ex": 2,
    "vmax": 3, "tag_team_gx": 3,
}

# 1) Valor NETO de un KO, no binario
def net_prize_value(my_attacker_type, target_type):
    gain = PRIZE_VALUE[target_type]          # lo que tomo ahora
    concede = PRIZE_VALUE[my_attacker_type]  # lo que daré cuando me devuelvan el KO
    return gain - concede                    # +1 = bueno, -2 = desastre

# 2) Selección de target: prioriza el KO con mayor valor neto
#    (entre KOs alcanzables este turno dado el daño disponible)
def choose_ko(reachable_kos):  # lista de (target, my_attacker_type, target_type)
    return max(reachable_kos,
               key=lambda k: net_prize_value(k.my_attacker_type, k.target_type))

# 3) Prize map propio: secuencia mínima de KOs que suma 6
#    -> contar amenazas necesarias. Menos KOs = más rápido pero más frágil.
def prizes_needed(opp_board):  # mis amenazas para llegar a 6
    # greedy por valor: noquear primero lo que más premios da
    s, kos = 0, 0
    for p in sorted(opp_board, key=lambda x: -PRIZE_VALUE[x.type]):
        if s >= 6: break
        s += PRIZE_VALUE[p.type]; kos += 1
    return kos  # 2-2-2 => 3 ; 3-3 => 2 ; etc.

# 4) Defensa "forzar el 7º premio": si mi tablero es solo single-prize,
#    el rival necesita 6 KOs. Penaliza benchear multi-premio.
def board_invites_easy_map(my_board):
    multi = sum(1 for p in my_board if PRIZE_VALUE[p.type] >= 2)
    return multi  # >0 => acorta el mapa del rival; minimizar salvo plan de uso

# 5) Modo "behind on prizes": desbloquea Counter Catcher y jugadas reactivas
def is_behind(my_prizes_remaining, opp_prizes_remaining):
    return my_prizes_remaining > opp_prizes_remaining
```

**Variables de estado a mantener en el agente:** `my_prizes_remaining`, `opp_prizes_remaining`, tipo+prize_value de cada Pokémon en juego (mío y rival), `prize_map` planeado (lista de prize_values objetivo), `kos_remaining_for_me = prizes_needed(opp_board)`, `kos_remaining_for_opp` (simétrico sobre mi tablero), flag `behind`.

**Condiciones de decisión derivadas:**
- Si `net_prize_value < 0` y existe alternativa ≥0, **no** hagas ese KO (evita el trade desfavorable).
- Si soy mazo single-prize: minimiza `board_invites_easy_map(my_board)` para forzar al rival a 6 KOs.
- Si `is_behind`, abre la rama de jugadas Counter-Catcher / reactivas.
- Trackea premios prizados (prize mapping): si una carta clave no aparece tras buscar el mazo, está en premios → ajusta el plan.

## → Hook de recompensa

Toca el término de **prize differential / tempo del reward**. Recompensa por intercambio neto, no por KO bruto:

```
reward += W_PRIZE * net_prize_value(my_attacker_type, target_type)   # premia +1, castiga -2
reward += W_TEMPO * (kos_remaining_for_opp - kos_remaining_for_me)   # ventaja estructural
reward -= W_INVITE * board_invites_easy_map(my_board)                # castiga benchear ex innecesarios
reward += W_WIN if my_prizes_remaining == 0 else 0
```
Si el motor cabt ya da reward terminal por ganar la carrera de premios, este hook es **shaping intermedio** que alinea decisiones con el intercambio neto. Si solo se quiere señal terminal: `null` en intermedio y dejar `W_WIN`.

## Datos parseables

- Las fuentes son artículos de blog en HTML; **no** exponen endpoints/exports/JSON. Se parsean como texto.
- El dato estructurado utilizable es la **tabla fija de valor de premios** (single=1, ex/V/VSTAR/Mega ex=2, VMAX/Tag Team GX=3) — codificar como diccionario constante (ver arriba). No rota: es regla del juego.
- Tipos de prize map como enumeración: `["2-2-2", "3-3", "1-1-2-2", "2-1-2-1"]` con su suma fija = 6.

## Caveats / sesgo

- **Contenido educativo de marca (TCG Protectors vende fundas/accesorios):** la guía es marketing de contenido, no análisis de torneo revisado por pares; los conceptos son correctos pero presentados de forma simplificada.
- **Las listas de mazos rotan; los conceptos no.** Ejemplos concretos (Radiant Charizard, Boss's Orders, VMAX) pueden quedar obsoletos con rotación de set/formato. La matemática de premios y la estructura de mapas es estable mientras exista la mecánica Rule Box.
- **VMAX/Tag Team GX** apenas están en Standard 2026 (legacy/Expanded); en Standard el grueso es single (1) vs ex/VSTAR/Mega ex (2). El mapa 2-2-2 domina; el 3-3 es marginal hoy.
- **Información imperfecta (relevante para cabt):** parte del prize-trade depende de premios prizados desconocidos (variance). El agente debe modelar `prize_map` como **distribución de creencia** sobre qué cartas clave están inaccesibles, no como hecho — el prize mapping del rival es inferido, no observable.
- "Forzar el 7º premio" asume que el rival no puede acelerar su daño o cambiar de mapa; un rival con KO en área amplia o multi-prize swap puede neutralizar la defensa single-prize.

## Fuentes citadas

- **TCG Protectors — "Pokémon TCG Prize Trade Guide: Advanced Prize Mapping & Strategies"** — https://tcgprotectors.com/blogs/pokemon-blog/pokemon-tcg-prize-trade-guide-advanced-prize-mapping (blog educativo de tienda de accesorios TCG; fuente del net +1, mapas 2-2-2/3-3/1-1-2-2, "no benchear multi-prize", forzar el 7º premio).
- **TCG Protectors — "Pokémon TCG Prize Mapping Guide 2026"** — https://tcgprotectors.com/blogs/pokemon-blog/pokemon-tcg-prize-mapping-guide-2026 (fuente del "resource exchange", mapa 2-1-2-1 para Standard 2026, regla Counter Catcher cuando vas behind, net +1).
- **Pokémon Authority — "Pokémon TCG Prize Cards Mechanic"** — https://pokemonauthority.com/pokemon-tcg-prize-cards-mechanic (tabla de valores incl. VSTAR=2 / Tag Team GX=3, asimetría 6-vs-2 KOs, prize differential 6-2 vs 6-4 como señal de tempo, riesgo de prizing).
- **Levels PTCG — "How Pokémon Prize Cards Work"** — https://levelsptcg.com/how-pokemon-prize-cards-work/ (4 pasos del prize mapping: memorizar mazo → buscar → trackear premios tomados → adaptar; regla de auto-KO también da premio al rival).
