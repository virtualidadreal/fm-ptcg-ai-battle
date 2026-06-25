# PokéBeach Premium — Plan de Adquisición

> Fuente DE PAGO. Evaluación de ROI para el AGENTE de IA del PTCG Knowledge OS (no para que un humano juegue mejor).
> No hay forma de extraer el contenido tras el paywall sin comprar: este documento es un PLAN, no una ingesta.
> Última verificación: 23 jun 2026 vía WebSearch (WebFetch bloqueado con 403 por el sitio).

---

## 1. Coste verificado

| Plan | Precio | Coste/mes efectivo |
|------|--------|--------------------|
| Semanal | 4,99 $/semana (~4,60 €) | ~21,6 $/mes |
| Mensual | 13,99 $/mes (~12,90 €) | 13,99 $ |
| Trimestral | 12,99 $/mes facturado por trimestre (~38,97 $/tri) | 12,99 $ |

- **Recomendado para una compra-cosecha puntual: 1 mes (13,99 $ / ~12,90 €).** Cancelable.
- **Garantía: reembolso completo a 30 días**, solo nuevos suscriptores, "no questions asked" (cancelar vía PayPal + contactar a Water Pokémon Master). Esto convierte el riesgo económico real en ~0 si se ejecuta la ingesta dentro de la ventana y se decide no continuar.
- Pago vía PayPal. Badge de suscriptor + banner "Advanced Member" en el foro (irrelevante para el agente).

_Nota: pricing verificado por snippets de búsqueda, no por carga directa de la página de upgrade (403). Confirmar el número exacto en el checkout antes de pagar; las tres cifras (4,99 / 13,99 / 12,99) son consistentes entre varias fuentes._

## 2. Qué da (contenido tras el paywall)

- **~15-16 artículos premium/mes** (uno cada dos días), escritos por **top players** del competitivo. Cada artículo pasa por varios borradores + edición.
- Cada artículo = **listas de mazo + estrategia + análisis** +, lo más valioso, **el proceso de decisión verbalizado** (por qué X carta, por qué N copias, líneas de juego, match-ups).
- **Forecasts de metagame para Regionals**, reportados como bastante precisos/útiles para preparar el campo esperado.
- **Foro privado "Subscriber Secret Hideout"**: subes tu lista y top players te la arreglan / discusión de metagame entre suscriptores.
- Torneo mensual con premios físicos (booster boxes/promos) — **irrelevante para el agente**.

## 3. ROI para el AGENTE de IA

**Lo que NO sirve (descartar al ingerir):**
- Listas concretas y forecasts de "qué mazo ganará el Regional X". **Caveat crítico: nuestro pool `cabt` ≠ Standard.** Una lista 60-card optimizada para el meta Standard real no es jugable ni relevante en nuestro pool. Forecast de tier list = ruido para nosotros.
- Premios, badges, noticias de producto.

**Lo que SÍ desbloquea heurísticas computables / datos parseables:**
- **Proceso de decisión verbalizado → reglas de construcción transferibles.** Ej.: ratios consejo-tipo ("con N atacantes de coste 2, juega 7-8 energía"; "Profesor's Research vs Iono según fase de partida"; "líneas evolutivas 4-3-3 vs 3-2-2 según consistencia"). Esto SÍ generaliza a cualquier pool, incluido `cabt`.
- **Reglas de evaluación de match-up y secuenciación de turnos** (qué buscar T1, cuándo "ir all-in", prizes a mappear). Parseable a heurísticas de mulligan/mano/setup para el motor de decisión del agente.
- **Vocabulario y taxonomía de arquetipos** (control vs aggro vs toolbox, roles de carta: pivote, recovery, disruption). Útil para etiquetar/clasificar mazos del pool propio.
- **Lógica de los forecasts** (cómo razonan el meta a partir de resultados): el *método* de inferencia de prevalencia, aunque el *resultado* (qué mazo) no aplique a `cabt`.

**Veredicto de valor:** el activo de alto ROI es el **razonamiento de construcción y de juego destilado en heurísticas**, no las listas. A 12,90 € con garantía de 30 días, una cosecha de 1 mes (~15 artículos) da material suficiente para extraer un set de reglas de deckbuilding/secuenciación independientes del formato. El riesgo financiero es nulo si se respeta la ventana de reembolso.

## 4. Veredicto

**COMPRAR (1 mes, condicional)** — pero **solo si la sección de heurísticas de construcción/secuenciación del KB está floja** y no la cubren las fuentes gratuitas ya ingeridas (Limitless, decklists, reglas oficiales). Si esa capa ya está bien poblada, el delta marginal de PokéBeach es bajo porque su valor más citado (listas/forecasts) no transfiere a `cabt`.

Mapea al enum: **comprar-si-floja-seccion**.

## 5. Stub de ingesta (si se compra)

> Objetivo: NO clonar listas. Destilar el RAZONAMIENTO en heurísticas independientes del pool.

1. **Acceso y captura legal-para-nosotros.** Suscribir 1 mes con la cuenta propia. Dentro del área de suscriptor, guardar el HTML de cada artículo premium del mes (login-gated, captura manual autenticada; PokéBeach devuelve 403 a fetchers automáticos, así que guardar página desde el navegador con sesión iniciada). Carpeta cruda: `knowledge/paid/_raw/pokebeach/AAAA-MM/`.
2. **Parseo a markdown estructurado.** Por artículo extraer: `autor`, `fecha`, `arquetipo`, `formato_origen` (siempre Standard — marcar como NO-cabt), bloque `listas` (archivar aparte, baja prioridad) y bloque `razonamiento` (texto de decisiones).
3. **Destilación a heurísticas.** Pasar el `razonamiento` por un prompt de extracción que produzca reglas atómicas tipo `{regla, condición, justificación, fuente, transferible_a_cabt: bool}`. Descartar todo lo marcado `transferible_a_cabt: false` (listas/ratios atados a cartas Standard concretas).
4. **Forecasts → método, no resultado.** De los forecasts de Regionals, extraer únicamente el *procedimiento* de inferencia de meta (no el ranking). Guardar como nota de método en `knowledge/synthesis/`.
5. **Integración.** Volcar las heurísticas transferibles a la capa de síntesis del KB (`knowledge/synthesis/heuristicas-deckbuilding.md` o equivalente), citando `source: pokebeach-premium (paid, AAAA-MM)`. Marcar cada regla con confianza y si está corroborada por fuente gratuita.
6. **Cierre económico.** Si tras la cosecha el material no aporta delta sobre lo gratuito, ejecutar el reembolso dentro de los 30 días. Registrar decisión en `knowledge/SOURCES.md`.

---

## Fuentes

- [Upgrade Membership — PokéBeach Forums](https://www.pokebeach.com/forums/account/upgrades)
- [How worth it is the premium membership? — PokéBeach Forums](https://www.pokebeach.com/forums/threads/how-worth-it-is-the-premium-membership.145515/)
- [Everything You Need to Know About PokéBeach's Article Program!](https://www.pokebeach.com/2015/05/everything-you-need-to-know-about-pokebeachs-article-program)
- [PokeBeach's Premium Subscription is Getting a Huge Upgrade!](https://www.pokebeach.com/2017/11/pokebeachs-premium-subscription-is-getting-a-huge-upgrade)
- [PokeBeach's Article Program Resumes! (2021)](https://www.pokebeach.com/2021/07/pokebeachs-article-program-resumes)
