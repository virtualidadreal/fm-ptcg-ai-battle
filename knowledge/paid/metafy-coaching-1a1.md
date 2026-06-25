---
source: Metafy / Trainers Guild — coaching 1:1 (Lesage / Eriksen / Gabe)
url: https://metafy.gg/@jespy/sessions
tier: paid
ref: P3
concept: sequencing, prize-mapping, decision-tree, prize-trade, reading
confidence: media        # precios verificados por search; contenido de la sesión NO existe hasta encargarla
acquisition_only: true   # no hay nada que scrapear: el activo se GENERA en la sesión
rotates: parcial         # el proceso de decisión NO rota; las listas/matchups concretos SÍ
evaluated: 2026-06-23
verdict: comprar-si-floja-seccion
---

## Qué es

Coaching **1:1 en vivo** (Discord + PTCG Live / Limitless Tabletop) con jugadores de élite,
bookeable vía Metafy. The Trainers Guild es un colectivo que enruta su booking a las páginas
de Metafy de cada coach. Coaches objetivo de esta ficha:

- **Zach Lesage** (@zachlesage) — Regional Champion, International Finalist, Players Cup II 2020,
  coach full-time desde 2017. Ha llevado alumnos a invites de Worlds y a ganar Regionals.
- **Jesper "Jespy" Eriksen** (@jespy) — **Campeón del Mundo 2016**, multi-Regional Champion,
  4x National Champion, 17+ años jugando.
- **Gabe** (#2 NA, vía Trainers Guild) — top jugador NA; booking por su perfil de Metafy.

Punto clave de adquisición: **a diferencia de las guías (P2), aquí no compras un documento
pre-hecho que podrías inspeccionar**. Compras tiempo en vivo. El activo de valor para el
agente **no existe hasta que tú lo provocas en la sesión** dirigiendo al coach a **verbalizar
su árbol de decisión** sobre *sequencing* y *prize mapping*. Mal dirigida, la sesión te da un
repaso genérico de tu juego (inútil para el bot). Bien dirigida, te da el razonamiento
explícito que ninguna fuente gratis articula. El ROI depende 100% del guion de la sesión.

## Coste verificado

| Producto | Precio (USD) | Equiv. aprox (EUR) | Verificado |
|----------|--------------|--------------------|------------|
| Jespy (Eriksen) — coaching en vivo 1 hora | **55 $** | ~51 € | ✅ search, 23 jun 2026 |
| Jespy — deck improvement 30 min | menor (no nº exacto) | — | ⚠️ existe, precio no fijado |
| Banda mercado top-coaches PTCG /hora | **40–150 $** | ~37–139 € | ✅ search (Tonisson 40$, SuperE 48$, Bradner 150$) |
| Zach Lesage — sesión 1:1 /hora | dentro de la banda | — | ⚠️ no nº exacto; consulta 15 min gratis confirmada |
| Gabe (vía Trainers Guild) /hora | dentro de la banda | — | ⚠️ booking por Metafy, nº no servido |

> Las páginas de sesión de Metafy devuelven **HTTP 403** a fetch directo (Cloudflare). El único
> precio firme cruzado es **Jespy 55 $/h**; el resto se acota por la banda de mercado verificada
> (40–150 $/h). **Re-verificar el nº exacto de Lesage/Gabe en el momento de bookear.** Presupuesto
> de trabajo: **~55–75 $ por sesión de 1 h** con coach de élite. Plan mínimo viable = 2-3 sesiones
> dirigidas (≈ 110–225 $) cubriendo sequencing, prize mapping y selección de mazo.

## → ROI para el AGENTE (no para jugar a mano)

El valor NO es que un humano juegue mejor. Es extraer **razonamiento de decisión computable**
que las fuentes gratis no verbalizan. Lo que transfiere:

**ALTO valor (proceso verbalizado, atemporal, computable):**
- **Árbol de decisión de sequencing dictado en voz alta** → "antes de jugar la primera carta,
  evalúo A, luego B, descarto C si…". Se transcribe a un **orden de precedencia de jugadas /
  función de ordenación de la mano** para el motor de turno del agente. Esto es exactamente lo
  que las guías escritas dejan implícito y un coach, presionado, hace explícito.
- **Prize mapping razonado** → cómo el coach deduce premios del rival y **condiciona su línea**
  a esa inferencia (qué prizes asume, cómo actualiza esa creencia con cada carta vista). Alimenta
  directamente el **belief-state / opponent-model** del agente y la heurística de prize-checking
  (refuerza `free/prize-checking.md` con el *cuándo* y el *cómo se actúa sobre el resultado*).
- **Criterios de "cuándo forzar vs. estabilizar"** dichos como reglas → términos de
  `synthesis/reward-spec.md` (shaping intermedio) con umbrales concretos.
- **Qué descarta un experto y por qué** (poda del árbol de búsqueda) → reglas de pruning para
  reducir el espacio de jugadas que el agente evalúa por turno. Muy valioso: el experto te dice
  qué ramas NO mirar, no solo cuál elegir.

**BAJO valor (no pagar por esto):**
- Reviews de **listas concretas / tech** del meta actual: rotan cada set **y recordatorio crítico,
  el pool de cabt ≠ Standard**, así que cualquier forecast de lista del coach vale poco para el bot.
- Coaching de **ejecución mecánica** del propio jugador (no aplica: el bot no tiene "manos").
- "Cómo se siente" el matchup sin regla detrás → no parseable, descartar.

**Por qué este P3 puede batir a P2 (guías):** una guía escrita ya filtró el razonamiento a prosa
pulida; en la sesión en vivo puedes **interrogar el árbol** ("¿por qué esa carta primero? ¿qué
te haría cambiar el orden?") y forzar reglas condicionales explícitas que ningún texto contiene.
Es la única fuente que produce **decision-rules a demanda**.

## Veredicto

**comprar-si-floja-seccion.** No es compra día-1. Orden correcto: primero exprimir el tier gratis
+ sintetizar. Disparador concreto de compra: si tras la síntesis, las secciones de **sequencing
(orden de juego de la mano)** y **prize mapping → acción** de `synthesis/heuristicas-computables.md`
quedan como heurísticas vagas sin un **árbol de decisión condicional explícito** (probable: las
fuentes gratis explican *qué* mirar pero rara vez el *orden de precedencia* y los *umbrales* que un
experto aplica), entonces **1-2 sesiones a ~55 $ con Jespy/Lesage dirigidas SOLO a verbalizar el
árbol** son la forma más barata de obtener ese activo. Si la síntesis gratis ya cierra sequencing y
prize-mapping con reglas claras, **descartar** (las reviews de lista no nos sirven). Preferir **Jespy
(55 $ verificado, Campeón del Mundo, máxima autoridad de proceso)** para la primera; Lesage/Gabe solo
si se quiere contrastar un segundo árbol de decisión.

## Stub de ingesta (si se compra)

No es scraping: el activo se **genera y se captura** en vivo. Pipeline **manual asistido**:

1. **Guion previo a la sesión (lo más importante).** Antes de bookear, redactar un guion que
   fuerce verbalización, NO repaso de juego. Ejemplos de prompts al coach: "Dame 5 board states y
   dime tu orden de juego y POR QUÉ cada carta va antes que la siguiente"; "Cuando mapeas premios,
   ¿qué asumes y qué te hace cambiar de plan?"; "¿Qué jugadas descartas de entrada y bajo qué
   condición las reconsideras?". El objetivo del guion es producir **reglas condicionales (si X
   entonces Y)**, no opiniones.
2. **Captura.** Grabar la sesión (con permiso del coach) → audio. Es el RAW. Vive en `_privado/`
   o fuera del repo (material de pago + voz de un tercero); **nunca se commitea el audio ni la
   transcripción literal**. Transcribir a texto (Whisper local) → `metafy-coaching-RAW.md` en
   `_privado/`.
3. **No commitear el RAW.** Solo entran al KB las **heurísticas destiladas**, nunca la transcripción
   literal. Citas ≤1 frase, atribuidas al coach.
4. **Destilación a ficha** → `knowledge/paid/coaching-decision-tree-destilado.md` con el esquema
   canónico (`source`, `concept`, `confidence`, `rotates`, secciones Heurística computable / Hook de
   recompensa / Datos parseables). `rotates: false` para el árbol de decisión; marcar `rotates: true,
   confidence: baja` cualquier mención atada a listas/meta concreto.
5. **Lo que se extrae, en concreto:**
   - **Árbol de sequencing** → pseudocódigo `order_plays(hand, board) -> [play]` con las reglas de
     precedencia y los umbrales que el coach dictó.
   - **Prize mapping** → reglas `infer_opponent_prizes(seen_cards) -> belief` + `adjust_line(belief)`
     para el opponent-model.
   - **Reglas de pruning** → lista de "ramas que un experto descarta" para reducir el branching del
     agente.
   - **Umbrales forzar/estabilizar** → constantes para el shaping de `reward-spec.md`.
6. **Verificación adversarial.** Marcar proceso atemporal (mantener) vs. atado a meta/pool no-cabt
   (descartar). Cruzar el árbol del coach contra el que ya se infiere de fuentes gratis: quedarse
   con lo que AÑADE (reglas condicionales y umbrales), tirar lo redundante.
7. **Síntesis.** Fusionar en `synthesis/heuristicas-computables.md` (sequencing + prize mapping) y
   `reward-spec.md` (umbrales). Actualizar la fila **P3** de `SOURCES.md` a ✅ (destilada) con nota
   de que el RAW (audio/transcripción) NO está en repo.

## Fuentes citadas

- Metafy — Jesper "Jespy" Eriksen, sesiones (55 $/h verificado): https://metafy.gg/@jespy/sessions (403 a fetch)
- Metafy — Zach Lesage, sesiones: https://metafy.gg/@zachlesage/sessions (403 a fetch; consulta 15 min gratis confirmada)
- Metafy — listado top coaches PTCG (banda 40–150 $/h): https://metafy.gg/pokemon-trading-card-game-online/sessions/top
- The Trainers Guild — coaching 1:1 (enruta booking a Metafy): https://trainersguild.gg/pokemon-tcg-coaching
- Limitless — autoridad de los coaches (palmarés de élite): limitlesstcg.com/players

_Autoridad de la fuente: máxima (Campeón del Mundo + top NA). Sesgos a vigilar: (1) comercial —
venden tiempo; (2) de meta — cualquier consejo sobre listas concretas está atado a Standard y a un
trimestre, y el pool de cabt ≠ Standard, así que solo el PROCESO de decisión transfiere; (3) de
captura — el ROI depende por completo de dirigir la sesión a verbalizar reglas, no a revisar partidas._
