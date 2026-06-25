---
source: Metafy — Tord's Kitchen (Tord Reklev)
url: https://metafy.gg/@tordtcg/guides
tier: paid
ref: P2
concept: deckbuilding, archetypes, reading, meta
confidence: media        # precio verificado por search; contenido tras paywall NO inspeccionable
rotates: parcial         # el PROCESO no rota; las listas/matchups concretos SÍ
acquisition_only: true   # no se extrae contenido; esto es un PLAN de compra
evaluated: 2026-06-23
verdict: comprar-si-floja-seccion
---

## Qué es

Tord Reklev (5 Internationals, 2º y 4º en Worlds) vende guías digitales de pago dentro de su
comunidad de Metafy "Tord's Kitchen". Son **documentos digitales** (texto + imágenes de board
states + en algunos casos vídeo), NO sesiones 1:1. Dos familias relevantes para nosotros:

1. **"Prepare/Prep Like a Pro"** — guía del *proceso de preparación* de cara a un torneo grande
   (Grand Slam / International). Verbaliza el meta-proceso: cómo recopilar información del meta,
   cómo elegir mazo, cómo testear con eficiencia. Es el activo más valioso para el agente porque
   es **proceso de decisión, no una lista**.
2. **Guías de box / mazo concreto** (ej. "Mega Absol Box Guide", "Ultimate Dragapult guide") —
   estructura típica: *Why play X · Deck List Breakdown · Tech Options · Matchup Section with
   Ideal Board States*. Útil pero rota con el meta.

Existe además una capa más barata (guías de 15 $ tipo "The Psychology behind Improving",
"Playing Gholdengo Properly") y una Master Class en vídeo ("Technical Gameplay and Deck
Building"). En abril 2026 añadió un documento nuevo de technical gameplay; el de deck building
estaba anunciado como pendiente.

## Coste verificado

| Producto | Precio (USD) | Equiv. aprox (EUR) | Verificado |
|----------|--------------|--------------------|------------|
| "Prepare Like a Pro" (proceso de prep) | **40 $** | ~37 € | ✅ search, 23 jun 2026 |
| Guías de box/mazo (Mega Absol Box, Dragapult…) | **40 $** c/u | ~37 € | ✅ search, 23 jun 2026 |
| Guías cortas (psicología, mazo puntual) | 15 $ | ~14 € | ✅ search |
| Master Class vídeo (technical gameplay + deckbuilding) | precio aparte (clase) | — | ⚠️ no verificado nº exacto |

> Páginas de guía y de evento devuelven **HTTP 403** a fetch directo (Cloudflare/paywall):
> confirma que **no hay extracción posible tras el paywall**. El precio se cruza desde múltiples
> resultados de búsqueda, no desde la página servida. Tratar el 40 $ como firme pero re-verificar
> en el momento de compra (Metafy ajusta precios y a veces empaqueta).

## → ROI para el AGENTE (no para jugar a mano)

Lo que de verdad desbloquea para nuestro bot, separando señal de ruido:

**ALTO valor (transfiere, es proceso computable):**
- **Árbol de selección de mazo** verbalizado → se traduce a una **función de scoring de
  arquetipo por matchup spread**: cómo pondera consistencia vs. techo vs. cobertura de meta.
  Esto es exactamente el tipo de heurística que el agente puede ejecutar para elegir/evaluar
  líneas, y NO existe gratis bien articulado.
- **Protocolo de testing eficiente** → estructura para nuestro **bucle de self-play /
  priorización de matchups** (a qué emparejamientos dedicar reps, criterio de "suficientes
  datos para decidir").
- **"Ideal Board States" por matchup** → estados objetivo etiquetados que sirven como
  **shaping de recompensa intermedia** (distancia a board-state ideal) y como heurística de
  evaluación de posición, más allá del prize count.
- Cómo Tord razona *prize trade / tempo / cuándo forzar vs. estabilizar* embebido en las
  secciones de matchup → refuerza términos de reward ya en `synthesis/reward-spec.md`.

**BAJO valor (no comprar por esto):**
- Las **listas concretas (decklists, tech options)** rotan cada set y, recordatorio clave,
  el **pool de cabt ≠ Standard**, así que un forecast de lista vale poco para el agente.
- Cartas específicas (Mega Absol, Dragapult, Gholdengo) son ejemplos, no el activo.

**Veredicto de prioridad de compra dentro de Metafy:** comprar SOLO la guía de **proceso**
("Prep Like a Pro"), 40 $. Las guías de box (otros 40 $ c/u) NO compensan para el agente: su
parte transferible (cómo razonar matchups) ya viene implícita en la de proceso + nuestras
fuentes gratis (TCG Protectors, JustInBasil). Comprar 1, no la colección.

## Veredicto

**comprar-si-floja-seccion.** No es compra día-1. Disparador concreto: comprar SOLO si tras la
síntesis gratis la sección de **selección de mazo por matchup spread + protocolo de testing**
de `synthesis/heuristicas-computables.md` queda floja o sin un árbol de decisión claro
(probable, porque las fuentes gratis cubren bien prize-trade/sequencing pero mal el
*meta-proceso de prep* verbalizado). En ese caso, 40 € por la única articulación de élite de
ese proceso es barato. Si la síntesis gratis ya cubre selección+testing con confianza alta,
**descartar** (las listas no nos sirven y es lo único extra que añaden las guías de box).

## Stub de ingesta (si se compra)

No automatizable: contenido tras login de pago, 403 a scraping. Pipeline **manual asistido**:

1. **Compra y captura.** Fran compra "Prep Like a Pro" (40 $) con su cuenta. La guía es texto +
   imágenes. Exportar/copiar a `~/Downloads/` como `metafy-prep-like-a-pro-RAW.md` (texto pegado
   a mano o vía "imprimir a PDF" del documento logueado → `pdftotext`, NUNCA screenshots para el
   texto; las imágenes de board state sí se guardan como PNG aparte).
2. **No commitear el RAW.** El material es de pago y con copyright. El RAW vive en
   `_privado/` o fuera del repo. **Solo entran al KB las heurísticas destiladas**, nunca el
   texto literal de Tord (citas ≤1 frase, atribuidas).
3. **Destilación a ficha.** Un agente toma el RAW y produce
   `knowledge/free/reklev-prep-process.md`... NO — al ser derivado de fuente de pago va a
   `knowledge/paid/reklev-prep-process-destilado.md` con el mismo esquema canónico
   (`source`, `concept`, `confidence`, `rotates`, secciones Heurística computable / Hook de
   recompensa / Datos parseables). `rotates: false` para el proceso.
4. **Lo que se extrae, en concreto:**
   - El **árbol de selección de mazo** → pseudocódigo de una función `score_archetype(meta,
     candidate) -> {consistency, ceiling, coverage}` con los pesos/criterios que Tord verbaliza.
   - El **protocolo de testing** → reglas para el bucle de priorización de matchups (criterio de
     parada, nº mínimo de reps, qué emparejamientos priorizar).
   - **Ideal board states** → tabla `matchup -> features del estado objetivo` para shaping de
     recompensa intermedia.
5. **Verificación adversarial** (misma fase del pipeline): marcar qué es proceso atemporal
   (mantener) vs. qué está atado a un meta concreto / pool no-cabt (descartar o marcar
   `rotates:true, confidence:baja`).
6. **Síntesis.** Fusionar las heurísticas atemporales en `synthesis/heuristicas-computables.md`
   y `reward-spec.md`; actualizar la fila P2 de `SOURCES.md` a ✅ (destilada) con nota de que el
   RAW no está en repo.

## Fuentes citadas

- Metafy — Tord's Kitchen, listado de guías: https://metafy.gg/@tordtcg/guides (403 a fetch, paywall)
- Metafy — "Prepare Like a Pro": https://metafy.gg/events/prepare-like-a-pro-dxvrXepxSq7
- Metafy — "Mega Absol Box Guide": https://metafy.gg/guides/view/mega-absol-box-guide-X5y6l7Tm8vQ
- Metafy Classes — "Pokémon Essentials: Technical Gameplay and Deck Building (Tord Reklev Master Class)"
- Limitless — perfil de jugador (autoridad: 5 Internationals, 2º/4º Worlds): https://limitlesstcg.com/players/86

_Autoridad de la fuente: Tord Reklev es uno de los jugadores con más palmarés histórico del
PTCG. El sesgo a vigilar es comercial (vende producto) y de meta (sus guías de box describen
listas atadas a un trimestre y a un pool que NO es el de cabt)._
