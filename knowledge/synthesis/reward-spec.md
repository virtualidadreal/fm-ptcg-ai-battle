---
doc: reward-spec
tier: synthesis
fuentes: knowledge/free/*.md (hooks de recompensa de las 12 fichas) + verdicts del verificador
extracted: 2026-06-23
deriva_de: heuristicas-computables.md
---

# Reward spec — función de recompensa del agente cabt

> Especificación de la función de recompensa derivada de las heurísticas computables.
> Para cada term: fórmula, signo, magnitud sugerida, y estado de implementación en nuestros
> agentes. Diseñada como **reward shaping intermedio** sobre un reward terminal de ganar la
> carrera de premios. Si cabt solo expone reward terminal, usar estos terms como **move
> ordering** en la búsqueda, no como shaping.

---

## 🚨 CAVEAT DE TRANSFERENCIA (leer antes de tunear pesos)

**El pool de cabt (~2000 cartas, reglas ajustadas) NO es Standard completo.** Los terms de abajo
están construidos sobre **invariantes de la mecánica** (valor de premio por tipo, contador de
premios público, info imperfecta), que SÍ transfieren. **No** dependen de shares de meta ni de
listas — eso era lo que rotaba y aquí está deliberadamente fuera.

**Lo único potencialmente no-transferible** es el conjunto de *tipos de Pokémon* y sus valores de
premio: si cabt ajustó las reglas de Rule Box (p.ej. distintos repartos 1/2/3), **lee la tabla de
valor de premio del propio engine**, no de la ficha. El esqueleto del reward es estable; la tabla
PRIZE_VALUE es un parámetro a confirmar contra cabt.

**Honestidad table-stakes vs edge real:**
- **Table-stakes** (no es ventaja, cualquier baseline lo tiene): reward terminal por ganar +
  `prize_yield` 1/2/3 por KO. *Leon v1 ya computa prize_yield 1/2/3.* Si el reward se queda aquí,
  el agente juega "tomar el KO más grande disponible", que es subóptimo.
- **Edge real** (lo que estos terms añaden): premiar el **net trade** y no el KO bruto; **penalizar
  exponer** el atacante a ser devuelto; modelar **premios prizados** como creencia; y tratar
  **ir-detrás** como ventaja condicional (tempo). *A1 tiene net-prize construido pero inerte para
  tableros single-prize* — el term R1 abajo es justo lo que hay que activar para que A1 deje de
  empatar en valor todos los KOs cuando ataca con single-prizers.

---

## Forma general

```
R_total = R_terminal                       # ganar la carrera de premios (lo que cabt ya da)
        + W1 * R_net_prize                  # P0 — intercambio neto, no KO binario
        - W2 * R_exposure                   # P0 — penalizar atacante en rango de KO rival
        + W3 * R_tempo                       # P0 — ir-detrás como ventaja condicional / swing
        + W4 * R_prize_belief                # P1 — belief-state de cartas premiadas
        - W5 * R_mulligan                    # P1 — coste de mulligan (carta gratis al rival)
        - W6 * R_invite                      # P1 — castigar benchear multi-premio innecesario
        + W7 * R_info                        # P2 — reducir entropía del belief del rival (scout)
```
Magnitudes en **prize-equivalents** (1 unidad = 1 carta de premio). Mantén shaping ≪ terminal.

---

## P0 — terms del núcleo

### R1 · Net prize trade (no KO binario)
**Fórmula:**
```
R_net_prize = E[net_prize_value(my_attacker_type, target_type)]
            = PRIZE_VALUE[target] - p_returned * PRIZE_VALUE[my_attacker]
```
**Signo:** + para trades favorables (single mata ex = +1), − para desfavorables (vmax mata single
= −2). **Magnitud:** `W1 ≈ 1.0` por prize-equivalent (es la moneda base del juego).
**Refinamiento sobre la ficha (verificado como flag):** la ficha `prize-trade` codifica
`concede = PRIZE_VALUE[my_attacker]` como **certeza**. Es probabilístico — introduce
`p_returned ∈ [0,1]` = P(mi atacante sea noqueado de vuelta el próximo turno), estimable con
`incoming_attack_threat`. Determinista solo si `p_returned=1`.
**Estado cabt:** tipos + prize_value de atacante y target; `p_returned` del belief de amenaza.
**Implementado:** *Leon v1 computa prize_yield 1/2/3 (la mitad "gano")*; falta el término "concedo"
y el `p_returned`. *A1 tiene el net construido pero inerte para single-prize* → activarlo aquí es P0.

### R2 · Exposure penalty (atacante en rango de KO rival)
**Fórmula:**
```
R_exposure = PRIZE_VALUE[my_active] * 1[ incoming_attack_threat(opp) >= my_active.hp_remaining ]
```
**Signo:** negativo en `R_total` (`- W2 * R_exposure`): comprometer un multi-premio que el rival
puede devolver concede `PRIZE_VALUE[my_active]` premios. **Magnitud:** `W2 ≈ 0.8–1.0` (casi a la par
con el net, porque conceder un KO es simétrico a tomar uno). Escala con probabilidad si la amenaza
es incierta: `W2 * p_opp_can_ko`.
**Estado cabt:** `my_active.hp_remaining`, energía visible adjunta rival, costes de ataque del pool.
**Implementado:** no, en ningún agente. Es la otra mitad del prize-trade que falta — **edge real**.

### R3 · Tempo / swing / ir-detrás condicional
**Fórmula (suma de sub-terms):**
```
R_tempo  =  delta_prize_lead_this_turn                       # swing: cambio neto de marcador en 1 turno
         +  k_gust * gusting_kos_with_supporter_slot_free    # KO vía Counter Catcher (no gastó Supporter)
         -  k_concede * prizes_conceded_if_swing_fails        # castigo si cedes 1er KO y el combo no sale
```
**Signo:** + por swings y por gusting que libera el Supporter; − por premios regalados sin payoff.
**Magnitud:** `W3 ≈ 0.3–0.6` (tie-breaker, subordinado al prize-trade puro); `k_gust ≈ 0.5`,
`k_concede = 1.0` (un premio cedido vale un premio). **Guard dura:** el sub-term de Counter Catcher
solo cuenta si `my_prizes_remaining > opp_prizes_remaining` (legalidad pública, computable con
certeza bajo info imperfecta).
**Estado cabt:** `my/opp_prizes_remaining`, `supporter_used_this_turn`, plan de gusting.
**Implementado:** no. **Caveat ficha (verificado):** la ficha cita mal el texto de la carta
("USE" en vez de "PLAY") y atribuye una frase inexistente a JustInBasil — el **concepto** es sólido
(estado público, Item libera Supporter), la cita verbatim no. Mapea al equivalente real en el pool
de cabt; no asumas "Counter Catcher PAR 160" ni "hasta 4 copias" sin verificar el print.

---

## P1 — terms de info imperfecta y consistencia

### R4 · Prize-belief (cartas premiadas)
**Fórmula:** no es un term aditivo simple, es un **modificador de prioridad**. Cuando
`belief(pieza_clave_prizada)` supera umbral, sesga el reward hacia buscar redundancia / la
alternativa:
```
prob_prized(copies, prizes_remaining, unknown_pool)   # hipergeométrica (ver heuristicas #4)
R_prize_belief = + bonus_redundancy  si prob_prized(pieza_clave) > THETA   # THETA medido in-engine
```
**Signo:** + sobre acciones que cubren la pieza probablemente premiada. **Magnitud:** `W4 ≈ 0.2–0.4`
(soft steer, no domina). **Estado cabt:** `prizes_remaining`, `unknown_pool`, `known_counts`.
**Implementado:** no. **Caveat ficha:** fuente primaria no verificable; usa la **fórmula**
hipergeométrica (verificada), no los porcentajes redondeados/mal atribuidos de las fichas.

### R5 · Mulligan cost
**Fórmula:** `R_mulligan = num_mulligans_this_game` (cada mulligan = +1 carta al rival).
**Signo:** negativo (`- W5 * R_mulligan`). **Magnitud:** `W5 ≈ 0.3` por mulligan (≈ valor de una
carta de ventaja para el rival). Es más un term de **deckbuild/reward de inicio** que de turno.
**Estado cabt:** contador de mulligans. **Implementado:** no.

### R6 · Invite penalty (benchear multi-premio innecesario)
**Fórmula:** `R_invite = count(p in my_bench if PRIZE_VALUE[p.type] >= 2 and not used_this_turn)`.
**Signo:** negativo (`- W6 * R_invite`): cada ex en banca acorta el prize-map del rival.
**Magnitud:** `W6 ≈ 0.2` (steer, no prohibición — a veces hay que benchearlo). **Estado cabt:**
`my_bench` con tipos. **Implementado:** no. Conecta con la heurística "forzar el 7º premio" si tu
tablero es single-prize.

---

## P2 — term de información (scout)

### R7 · Information gain (reducir entropía del belief rival)
**Fórmula:** `R_info = H(opp_belief_before) - H(opp_belief_after)` (entropía de la distribución de
arquetipo rival), aplicado solo cuando la incertidumbre es alta.
**Signo:** + por jugadas que revelan info del rival cuando `max(belief) < 0.6`. **Magnitud:**
`W7 ≈ 0.1–0.2`, decae a 0 cuando el belief ya colapsó. **Estado cabt:** `belief.archetype` (dist).
**Implementado:** no, y requiere el belief-state del rival (heurística #7) operativo primero.
⚠️ **Depende de meta:** el belief de arquetipo se construye del meta de cabt medido in-engine,
no de shares de Limitless/Trainer Hill.

---

## Tabla de pesos sugeridos (punto de partida — calibrar in-engine)

| Term | Símbolo | Peso | Signo | Prio | ⚠️ meta | Implementado |
|------|---------|------|-------|------|---------|--------------|
| Net prize trade | W1·R_net_prize | 1.0 | ± | P0 | no | parcial (Leon v1 prize_yield; A1 net inerte) |
| Exposure penalty | W2·R_exposure | 0.8–1.0 | − | P0 | no | no |
| Tempo / swing / behind | W3·R_tempo | 0.3–0.6 | ± | P0 | no¹ | no |
| Prize-belief | W4·R_prize_belief | 0.2–0.4 | + | P1 | no | no |
| Mulligan cost | W5·R_mulligan | 0.3 | − | P1 | no | no |
| Invite penalty | W6·R_invite | 0.2 | − | P1 | no | no |
| Information gain | W7·R_info | 0.1–0.2 | + | P2 | sí | no |

¹ mecánica estable; la carta concreta (gusting que libera Supporter) se mapea al pool de cabt.

---

## Notas de integración

- **Orden de implementación = orden de valor:** R1 (activar el net en A1, completar la mitad
  "concedo" en Leon v1) → R2 (exposición) → R3 (tempo). Esos tres son el grueso del edge sobre un
  baseline de prize_yield bruto.
- **Si cabt da reward denso por KO** (1/2/3 por premio tomado), R1 ya está medio puesto; añade el
  término negativo de "premios concedidos" y la exposición R2 para que deje de ser one-sided.
- **Si cabt solo da reward terminal**, no metas shaping: usa R1–R3 como **función de orden de
  jugadas** en la búsqueda/política rule-based. Todas las fichas advierten esta salida (`null` en
  intermedio, dejar solo el terminal).
- **No tunees pesos contra el meta de Standard.** Todo número de las fichas meta está marcado ⚠️ y
  varios están mal (jugadores↔partidas, prior que no suma 1). Calibra W1–W7 con self-play en cabt.
