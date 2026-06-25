---
doc: INDEX
tier: synthesis
rol: índice maestro del PTCG Knowledge OS (curaduría final)
fuentes: knowledge/free/*.md (12) + knowledge/paid/*.md (4 planes) + synthesis/*
curado: 2026-06-23
caveat_global: pool de cabt (~2000 cartas, reglas ajustadas) != Standard. Conceptos > listas.
---

# PTCG Knowledge OS — Índice maestro

> Punto de entrada único al KB. Mapea todo lo destilado (gratis + pago), prioriza las
> heurísticas de mayor valor para el agente cabt, fija el orden de compra de las fuentes de
> pago y conecta el KB con los agentes de `agents_official/`.
>
> **Regla de oro de todo el KB:** si una heurística depende de un número de meta concreto, se
> lee de la config del meta vigente de cabt (medido in-engine), nunca del valor citado en la
> ficha. El pool de cabt != Standard: transfieren los **invariantes de mecánica** (prize-trade,
> hipergeométrica, info imperfecta, contador de premios público), NO las listas ni los shares.

---

## 1. Mapa del KB con estado

### Síntesis (capa accionable — empezar aquí)
| Doc | Qué es | Estado |
|-----|--------|--------|
| `synthesis/heuristicas-computables.md` | 9 heurísticas destiladas a pseudocódigo + estado cabt + prioridad P0/P1/P2 | ✅ maestro |
| `synthesis/reward-spec.md` | Función de recompensa (R1..R7) derivada de las heurísticas, con pesos y estado de implementación | ✅ maestro |
| `synthesis/INDEX.md` | Este índice | ✅ |

### Tier GRATIS (12 fichas, destiladas)
| Ficha | Concepto | Transfiere a cabt | Estado |
|-------|----------|-------------------|--------|
| `free/prize-trade.md` | net prize value de KO, exposición | ✅ invariante | ✅ destilada → H1, H2 |
| `free/tempo.md` | Counter Catcher / ir-detrás como ventaja | ✅ patrón (mapear carta) | ✅ destilada → H3 |
| `free/prize-checking.md` | belief de cartas premiadas (hipergeométrica) | ✅ fórmula | ✅ destilada → H4 |
| `free/sequencing.md` | ordenar turno por fase, minimizar commitment | ✅ método | ✅ destilada → H5 |
| `free/consistency-mulligan.md` | P(mulligan), P(ver ≥1), gate de deckbuild | ✅ matemática | ✅ destilada → H6 |
| `free/opponent-reading.md` | belief bayesiano, lectura por no-jugada | ⚠️ método sí, números no | ✅ destilada → H7 |
| `free/archetypes-roles.md` | rol BEATDOWN/CONTROL, roles de carta | ⚠️ parcial | ✅ destilada → H7, H8 |
| `free/deckbuilding-strategies.md` | poda Reklev, setup gate, 4 estrategias | ⚠️ método sí, pesos inventados | ✅ destilada → H9 |
| `free/top-players-theory.md` | fundamentos, "consistency is the goal" | ⚠️ cita misatribuida | ✅ destilada → H9 |
| `free/limitless-meta-data.md` | API pública: placings, matchup matrix, shares | ❌ ROTA, no hardcodear | ✅ destilada (solo método/esquema) |
| `free/trainerhill-analytics.md` | esquema FS[deck], MATRIX, first/second | ✅ esquema; ❌ valores | ✅ destilada (esquema) |
| `free/meta-snapshot-2026-06.md` | snapshot meta Standard jun 2026 | ❌ ROTA, referencia histórica | ✅ destilada (descartado para cabt) |

### Tier DE PAGO (4 planes de adquisición — NO ingeridos, son planes de compra)
| Fuente | Qué desbloquea | Coste | Veredicto |
|--------|----------------|-------|-----------|
| `paid/pokebeach-premium.md` | razonamiento de construcción/secuenciación verbalizado; método de forecast | 13,99 $/mes (~12,90 €), reembolso 30 d | 🔒 comprar-si-floja-seccion |
| `paid/metafy-guias-reklev.md` | árbol de selección de mazo, protocolo de testing, ideal board states | 40 $ (~37 €) guía "Prep Like a Pro" | 🔒 comprar-si-floja-seccion |
| `paid/metafy-coaching-1a1.md` | decision-rules a demanda (sequencing, prize mapping, pruning, umbrales) | 55 $/h (~51 €) Jespy; plan 110–225 $ | 🔒 comprar-si-floja-seccion |
| `paid/patreons-datos.md` | esquema de campos por match + calibración offline first/second | Trainer Hill BJ+ 3 $/mes (trial 7 d) | 🔒 comprar-si-floja-seccion (solo BJ+; Limitless/JustInBasil descartar) |

**Estado de los 4 planes de pago: NINGUNO comprado.** Son planes de adquisición + stub de
ingesta, no datos ingeridos. El contenido tras paywall no es scrapeable (403). Lo que entra al
KB si se compra es **heurística destilada**, nunca el material literal de pago.

---

## 2. Las 5 heurísticas de mayor valor, en orden de implementación

Seleccionadas por edge real sobre un baseline (no table-stakes) y por no depender de meta que rota.
El orden es de implementación: cada una desbloquea o refuerza a la siguiente.

1. **H1 · Valor NETO de un KO (no binario)** — `prize-trade` · P0 · reward R1.
   `net = PRIZE_VALUE[target] − p_returned·PRIZE_VALUE[my_attacker]`. Elegir el KO de mayor net;
   rechazar net<0 si hay alternativa ≥0. **Edge:** que funcione también con tablero single-prize.
   *Estado: `sabrina_a1_netprize` lo tiene construido pero INERTE para single-prize; `leon_v1_5`
   solo computa la mitad "gano" (prize_yield 1/2/3). Activarlo es el primer movimiento.*

2. **H2 · Penalizar exponer atacante en rango de KO rival** — `prize-trade` + `reading` · P0 · reward R2.
   Antes de comprometer un multi-premio al activo, comprobar si el rival lo noquea el próximo turno
   (energía visible ≥ coste o spread ≥ HP restante). Si concede ≥2, penalizar fuerte. Es la otra
   mitad del prize-trade que los motores ignoran: no basta con tomar buenos KOs, hay que no regalar
   el devolverlo. *Estado: solo esbozado en `sabrina_a1_netprize`; no completo en ningún agente.*

3. **H3 · Counter Catcher / modo "behind" como ventaja condicional** — `tempo` · P0 · reward R3.
   Guard booleana dura sobre estado PÚBLICO: `my_prizes_remaining > opp_prizes_remaining`. Como es
   Item, gustea sin gastar el slot de Supporter → encadena gusting + draw + KO el mismo turno.
   **Mapear el patrón al equivalente real del pool de cabt**, no a "Counter Catcher PAR 160".
   *Estado: el patrón "behind/prizes_remaining" aparece referenciado en la familia sabrina_*; falta
   la guard dura + el plan de gusting-libera-supporter como term de decisión.*

4. **H4 · Belief-state de cartas premiadas (prize-checking)** — `prize-checking` + `consistency` · P1 · reward R4.
   Hipergeométrica sobre el pool no visto (no sobre 60 fijo): `prob_at_least_one_prized(copies,
   prizes_remaining, unknown_pool)`. Recomputar tras cada search/draw/discard/KO. Si la pieza clave
   supera umbral, subir prioridad de redundancia/recovery o de su alternativa. Primera capa de info
   imperfecta sobre el propio mazo. *Estado: no implementado en ningún agente.*

5. **H5 · Ordenar el turno por fase + minimizar commitment irreversible** — `sequencing` · P1 · move-ordering.
   Cola de acciones por fase ordinal, desempatando por EV: robar antes de buscar; attach de energía
   como última acción antes de atacar; disrupción (gusting/Iono) antes de revelar fuerza. Reduce
   commitment irreversible y exprime información. **Los predicados de fase se construyen desde la
   base de cartas de cabt.** *Estado: esqueleto de orden presente en varios agentes; falta el
   ordenamiento por fase + EV explícito.*

> H6 (mulligan/consistencia), H7 (belief de arquetipo rival), H8 (rol BEATDOWN/CONTROL) y H9
> (poda Reklev) son valiosas pero P1-P2: H6 es gate de deckbuild (offline), y H7/H8/H9 dependen de
> un belief-state maduro y de números que se MIDEN in-engine (no se hardcodean). Ver el doc maestro.

---

## 3. Orden de compra recomendado de las fuentes de pago

**Recomendación de cabecera: NO COMPRAR NADA TODAVÍA.** El caveat cabt != Standard hace que el
activo más caro de cada fuente (listas, forecasts, shares) sea ruido o activamente engañoso. Lo
único que transfiere es **proceso verbalizado**, y las 9 heurísticas gratis ya cubren con confianza
el núcleo del edge (P0 completo: prize-trade, exposición, tempo). **El cuello de botella hoy NO es
falta de conocimiento, es implementación**: H1 sigue inerte en A1 y a medias en Leon v1. Gastar en
pago antes de cerrar P0 en código es invertir el orden.

**Disparadores de compra (solo si, tras implementar P0/P1, una sección queda floja):**

1. **PRIMERO — Trainer Hill Battle Journal+ · 3 $/mes (trial 7 días) · riesgo ~0 €.**
   Por qué primero: es lo más barato y concreto. NO por los win rates (irrelevantes: humanos +
   pool != cabt) sino por **confirmar el esquema exacto de campos por match** para poblar `FS[deck]`
   y `MATRIX[mine][theirs]` y **calibrar offline el efecto first/second**. Trabajo de 1 sesión:
   suscribir, capturar esquema, cancelar dentro del trial. Comprar solo si al implementar el módulo
   turn-order/belief el equipo necesita el esquema o la calibración real.

2. **SEGUNDO — Metafy "Prep Like a Pro" (Reklev) · 40 $ (~37 €) · una sola compra.**
   Disparador: si tras la síntesis gratis la sección **selección de mazo por matchup spread +
   protocolo de testing** queda sin un árbol de decisión claro (probable: las gratis cubren bien
   prize-trade/sequencing pero mal el meta-proceso de prep verbalizado). Comprar SOLO la guía de
   proceso, NO las guías de box (otros 40 $ que rotan con el meta y no transfieren).

3. **TERCERO — Metafy coaching 1:1 Jespy · 55 $/h (~51 €), plan 110–225 $ · el más caro y dirigido.**
   Disparador: si tras lo anterior **sequencing (orden de la mano) + prize mapping → acción** siguen
   siendo heurísticas vagas sin árbol condicional explícito (umbrales, precedencia, pruning). Es la
   ÚNICA fuente que produce decision-rules a demanda, pero el ROI depende 100% del guion: hay que
   dirigir al coach a VERBALIZAR su árbol, no a revisar partidas. Solo con guion preparado.

4. **NUNCA por ahora — PokéBeach Premium (13,99 $/mes), Limitless Patreon (2 €/mes), JustInBasil.**
   PokéBeach: reembolso 30 días hace el riesgo ~0, pero su valor más citado (listas/forecasts) no
   transfiere; comprar solo si la capa de deckbuilding/secuenciación quedara floja DESPUÉS de las
   tres anteriores (improbable). Limitless Patreon: ROI nulo (los datos están en la API gratis, el
   Patreon solo quita anuncios). JustInBasil: ROI nulo (Excel para humanos, pool != cabt, autor
   fallecido → no se actualiza).

**Coste total del plan mínimo viable, si TODO se dispara:** ~3 $ (BJ+) + 40 $ (Prep) + 55–110 $
(1-2 sesiones) ≈ **100–155 $ (~92–143 €)**. Pero el plan correcto es **0 € hasta cerrar P0 en
código**, luego comprar incrementalmente solo lo que quede demostradamente flojo.

---

## 4. Próximos pasos — conectar el KB con `agents_official/`

Mapeo heurística → agente. El edge a activar vive casi todo en la familia **sabrina** (single-prize,
donde la net importa más) y en **leon** (que solo tiene la mitad table-stakes).

| Heurística (reward) | Agente destino | Acción concreta |
|---------------------|----------------|-----------------|
| **H1 · net prize (R1)** | `sabrina_a1_netprize` | Activar la net que está construida pero INERTE para tableros single-prize. Es el primer commit. |
| **H1 · mitad "concedo" (R1)** | `leon_v1_5_prizeaware` | Ya computa `prize_yield` 1/2/3 (la mitad "gano"); añadir el término "concedo" + `p_returned`. |
| **H2 · exposición (R2)** | `sabrina_a1_netprize` → resto sabrina_* | Completar `exposure_penalty` (energía visible rival, costes de ataque del pool). Portar a `sabrina_v3`. |
| **H3 · behind/Counter Catcher (R3)** | familia `sabrina_*` (ya referencian `prizes_remaining`/`behind`) | Añadir guard dura `my_prizes > opp_prizes` + plan gusting-libera-supporter, mapeado al equivalente real del pool cabt. |
| **H4 · prize-belief (R4)** | nuevo módulo compartido | Implementar la hipergeométrica como util compartida; integrar primero en `sabrina_a1_netprize`. |
| **H5 · sequencing (move-order)** | `sabrina_v3`, `mega_starmie_v1` | Construir predicados de fase desde la base de cartas de cabt; ordenar acciones por (fase, −EV). |
| H6 · mulligan/consistencia | offline (deckbuild) | Gate de construcción de mazos, no estado de turno. Calcular K=basics objetivo del pool cabt. |
| H7 · belief arquetipo (R7) | `sabrina_*` con belief | Construir prior + usage MIDIENDO partidas in-engine, no de Limitless/Trainer Hill. Requiere H4 antes. |
| H8 · rol BEATDOWN/CONTROL | selector de política | Activar solo cuando `prize_diff`/`speed`/`matchup_fav` se midan in-engine. |

**Secuencia de trabajo recomendada (= orden de valor del reward-spec):**
1. **R1 en `sabrina_a1_netprize`** (activar net single-prize) — desbloquea el edge inerte HOY.
2. **R1 mitad "concedo" en `leon_v1_5_prizeaware`** — completa el prize-trade del baseline.
3. **R2 exposición** en A1, luego portar a `sabrina_v3`.
4. **R3 tempo/behind** con guard pública en la familia sabrina.
5. **R4 prize-belief** como módulo compartido.
6. Recalibrar TODOS los pesos W1..W7 con self-play **en cabt**, nunca contra el meta de Standard.

**Regla de integración:** si cabt solo da reward terminal, R1–R3 se usan como **move-ordering** en
la búsqueda, no como shaping. Si cabt da reward denso por KO, R1 ya está medio puesto: añadir el
término negativo "premios concedidos" + R2. Confirmar la tabla `PRIZE_VALUE` contra el engine.

---

## 5. Deuda / pendientes del KB
- Ninguna fuente de pago ingerida (los 4 son planes). Re-verificar precios en el momento de compra (todos dan 403 a fetch).
- H7/H8 con `usage[card][arch]`, skeletons y priors: **construir midiendo cabt**, nunca copiar de Limitless/Trainer Hill.
- Errores verificados en las fichas meta (NO replicar): jugadores↔partidas, prior que no suma 1, cita fabricada a Flipside, "consistency is the goal" misatribuida a Klaczynski, credencial inflada de Limitless. Detalle en `heuristicas-computables.md`.
