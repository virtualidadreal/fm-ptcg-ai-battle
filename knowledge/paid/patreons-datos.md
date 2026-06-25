---
source: Patreons de pago (Trainer Hill / Limitless / JustInBasil)
tier: paid
concept: plan-de-adquisicion
extracted: 2026-06-23
verified: 2026-06-23
note: NO se puede extraer contenido tras paywall. Este doc es un PLAN, no datos.
---

## Resumen ejecutivo

Tres fuentes de pago candidatas para nutrir el agente. **El paywall no es extraíble por scraping**, así que el entregable es un plan de adquisición + ingesta manual. Caveat global que domina toda la evaluación: el reto **cabt usa un pool ≠ Standard**, por tanto cualquier dato de *listas concretas / meta share del Standard actual vale poco* para el agente. Lo que vale es el **proceso de decisión verbalizado** y la **estructura de datos parseables** (esquemas, no valores).

| Fuente | Coste verificado | Qué desbloquea de pago | Veredicto |
|--------|------------------|------------------------|-----------|
| **Trainer Hill — Battle Journal+** | **3 $/mes** (7 días trial, cancela cuando quieras) | Analítica avanzada: WR por matchup/deck/tags, **going first vs second**, cloud sync, filtros por fecha | **comprar-si-floja-seccion** (1 mes, extraer esquema FS/MATRIX, cancelar) |
| **Limitless TCG** | **desde 2 €/mes** | Principalmente **quitar anuncios** + 11 posts. Sin API/datos exclusivos confirmados tras paywall | **descartar** (los datos buenos están en la API pública gratis) |
| **JustInBasil** | 5 / 10 / 25 / 50 $/mes | Excel Deck Builder (5 $+), previews de recursos | **descartar** (autor fallecido, recurso es para humanos, pool ≠ cabt) |

---

## 1. Trainer Hill — Battle Journal+ (3 $/mes)

### Coste verificado
3 $/mes vía Patreon (`plus.trainerhill.com`), con 7 días de prueba gratis y cancelación libre. Un único tier de pago. Verificado por WebFetch directo a la página el 2026-06-23.

### Qué da (de pago, sobre lo gratis)
- WR por **matchup, deck propio y tags custom**, con filtros de rango de fecha.
- Estadística **going first vs going second** separada (clave en PTCG: el que va primero NO ataca en T1).
- Cloud sync multi-dispositivo y entrada rápida de partidas.
- Multi-juego (Pokémon, One Piece...).

Crucial: Battle Journal+ es un **diario de TUS propias partidas** (datos auto-reportados del usuario), no un dataset global del meta. La matriz global representativa ya está en `/meta` (gratis) y en la API de Limitless.

### ROI para el AGENTE
**Marginal, no esencial.** El valor NO está en los win rates de Fran jugando a mano (irrelevantes para el agente: son decisiones humanas y pool distinto). El valor está en una sola cosa: **ver el esquema exacto de campos por match** que Battle Journal+ expone (deck propio, arquetipo rival, W/L, turn order first/second, tags, timestamp) para copiar ese esquema como estructura de las variables `FS[deck]` y `MATRIX[mine][theirs]` que ya están especificadas en `free/trainerhill-analytics.md`. Eso es un trabajo de **1 sesión, no de suscripción recurrente**. La heurística de turn-order (`turn_order_bias`, "aggro quiere ir 2º") ya está derivada sin pagar.

### Veredicto: **comprar-si-floja-seccion**
Comprar 1 mes SOLO si al implementar el módulo de turn-order / belief-update el equipo necesita confirmar el esquema de campos o calibrar el efecto first/second con datos reales. Suscribirse, exportar/capturar el esquema y la UI de analítica, y cancelar dentro del trial de 7 días. No mantener suscripción: no genera datos parseables del entorno cabt.

---

## 2. Limitless TCG (desde 2 €/mes)

### Coste verificado
Desde 2 €/mes en `patreon.com/limitlesstcg`. 253 miembros de pago, 11 posts exclusivos. El beneficio explícito documentado es **quitar anuncios**. No se confirma tras el paywall ningún acceso de datos / API exclusivo. Verificado 2026-06-23.

### ROI para el AGENTE
**Nulo o casi nulo.** El activo de Limitless que importa al agente —placings, decklists, matches, matchup matrix, meta share, score W-L-T crudo— está disponible en la **API pública gratuita** (`docs.limitlesstcg.com/developer.html`) y ya está documentado y parseado en `free/limitless-meta-data.md` (330 eventos, 18.537 jugadores, 41.105 partidas). El Patreon paga por quitar publicidad de la web, que es UX humana, no datos. Un agente que consume la API ni ve los anuncios.

### Veredicto: **descartar**
Pagar no desbloquea ningún dato ni heurística que la API gratis no dé. Si en el futuro Limitless lanzara un tier de pago con API extendida o rate limit superior, reevaluar; hoy no existe evidencia de ello.

---

## 3. JustInBasil (5 / 10 / 25 / 50 $/mes)

### Coste verificado
Cuatro tiers: Fresh Basilites 5 $, Basil Brigade 10 $, Pesto Patriots 25 $, Margherita Masters 50 $. El beneficio "duro" es el **Excel Deck Builder** exclusivo a partir de 5 $. Resto = Discord, previews, agradecimientos, partidas con el autor. Verificado 2026-06-23.

### ROI para el AGENTE
**Nulo.** (1) El recurso estrella es un **Excel para que un HUMANO construya listas** — formato no parseable a heurística y orientado a juego manual. (2) Las listas/recursos son del Standard, **pool ≠ cabt**, así que su valor predictivo para el agente es bajo por el caveat global. (3) **El autor (JustInBasil) ha fallecido**; el recurso no se actualizará, lo que lo aleja aún más del meta vigente y reduce a cero el caso de suscripción recurrente. El conocimiento conceptual valioso de JustInBasil (guías de fundamentos) ya está en abierto en `justinbasil.com/guide` y mirrors, ingerible sin Patreon.

### Veredicto: **descartar**
No comprar. Si se quiere el conocimiento conceptual, scrapear la guía pública gratuita (no requiere Patreon).

---

## Stub de ingesta (si se compra Battle Journal+, el único candidato)

Aplica solo a Trainer Hill BJ+. Limitless y JustInBasil se ingieren por sus rutas gratis (API / guía pública), no por Patreon.

```
1. Suscribirse al trial de 7 días en plus.trainerhill.com (3 $/mes, cancelable).
2. Crear/poblar ~10-20 partidas de prueba para que la analítica muestre datos.
3. Capturar el ESQUEMA, no los valores:
   - Abrir la vista de analítica (WR por matchup, first/second, tags).
   - Con DevTools (Network), localizar el endpoint XHR/JSON que la SPA consume
     y guardar UNA respuesta de ejemplo (payload por match + agregados).
   - Si no hay endpoint limpio, screenshot de la UI + transcripción manual
     de los nombres de campo.
4. Normalizar a los esquemas YA definidos en free/trainerhill-analytics.md:
     match  = {my_deck, opp_archetype, result(W/L/T), turn_order(first/second),
               tags[], timestamp}
     FS     = {deck: {first: wr1, second: wr2}}
     MATRIX = {mine: {theirs: wr}}
5. Escribir knowledge/paid/battle-journal-schema.md con:
     - el esquema de campos confirmado (frontmatter tier: paid, source verificado)
     - el efecto first/second real medido (signo + magnitud por arquetipo) como
       CALIBRACIÓN OFFLINE, nunca como reward online directo (ver reward-spec.md).
6. Cancelar la suscripción antes de que termine el trial.
7. Cross-link desde synthesis/heuristicas-computables.md (belief-update / turn-order)
   y synthesis/reward-spec.md (r_info, term de coherencia de matchup).
```

Regla de ingesta: lo que entra al KB es **esquema + proceso de decisión verbalizado**, nunca tablas de meta share / listas concretas del Standard (rotan y son pool ≠ cabt). Marcar todo lo paid con `rotates: true` cuando aplique y con la fecha de extracción.

## Fuentes citadas
- Battle Journal+ pricing/features (3 $/mes, first/second, filtros): https://plus.trainerhill.com/ (WebFetch verificado 2026-06-23)
- Trainer Hill: https://www.trainerhill.com/
- Limitless Patreon (desde 2 €/mes, quitar ads, 253 miembros): https://www.patreon.com/limitlesstcg
- Limitless API pública (vía gratis a los datos): https://docs.limitlesstcg.com/developer.html
- JustInBasil Patreon (tiers 5/10/25/50 $, Excel Deck Builder): https://www.justinbasil.com/resources/justinbasil-is-now-on-patreon
- JustInBasil guía pública gratuita: https://www.justinbasil.com/guide
- Fallecimiento del autor (VGC): https://www.videogameschronicle.com/news/pokemon-tcg-community-pillar-justinbasil-has-died-aged-36/
