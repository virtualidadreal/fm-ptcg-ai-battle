# PTCG Knowledge OS — sistema de destilación de élite

> Sistema operativo agéntico al estilo Dev Aumentado para absorber el pensamiento de
> élite del Pokémon TCG y destilarlo a **heurísticas computables + hooks de función de
> recompensa** para nuestro agente (Kaggle PTCG AI Battle + cualquier futuro bot).
>
> Input madre: `~/Downloads/estrategia pokemon.md` (investigación previa de Fran).
> Proyecto host: `proyectos/ptcg-ai-battle/`. Memoria: [[ptcg-ai-battle-kaggle]].

## Para qué sirve

**Este sistema ES la palanca del tramo difícil.** El repo concluyó que el trozo del gap que
NO se cierra con código —la carrera de premios, cuándo exponer el muro, las líneas de
mulligan, el sequencing— es **juicio humano de juego**, y que el fichaje de mayor ROI para el
top no es un ML-ero sino un **jugador competitivo de PTCG real que encode el árbol de decisión
de verdad** (antes del merge del 9 ago). El Knowledge OS es el sustituto/complemento escalable
de ese fichaje: extrae ese árbol de decisión de las fuentes escritas de élite y de las
transcripciones de coaching, y lo destila a heurísticas implementables.

Distinción clave (no confundir):
- *Listas y números de meta* → rotan cada 3 meses, pool cabt ≠ Standard → **ROI bajo**, desechable.
- *El árbol de decisión humano* (prize trade, exposición del muro, mulligan, sequencing,
  lectura de rival) → **transfiere y es LA palanca** → es lo que este sistema persigue.

Cada fuente se destila a un esquema común que conecta teoría → código. Prioridad absoluta:
las decisiones de juicio, no el deckbuilding del trimestre.

## Pipeline (cómo opera)

1. **Extracción GRATIS** (`free/`): un agente por fuente/concepto. WebSearch + WebFetch,
   nunca screenshots. Cada uno escribe un `.md` con el esquema de abajo.
2. **Verificación adversarial**: un escéptico revisa cada extracción (números de meta que
   rotan, sesgo comercial de fuentes-tienda, citas fabricadas). Marca `confidence`.
3. **Síntesis gratis** (`synthesis/`): fusiona todo a `heuristicas-computables.md` +
   `reward-spec.md` (lo accionable para el agente) y actualiza `SOURCES.md`.
4. **Plan de adquisición DE PAGO** (`paid/`): mapea cada fuente paywall (coste, qué da, ROI,
   stub de ingesta). No se extrae contenido tras paywall; se documenta qué comprar y por qué.

## Esquema de cada ficha de conocimiento (`free/<slug>.md`)

```markdown
---
source: <nombre>            # Limitless, JustInBasil, TCGplayer prize article...
url: <url canónica>
tier: free
concept: <prize-trade|prize-checking|sequencing|tempo|consistency|reading|archetypes|meta|deckbuilding>
confidence: <alta|media|baja>   # la pone el verificador
rotates: <true|false>       # true si depende del meta del trimestre
extracted: 2026-06-23
---

## Qué es (1 párrafo)
## Conceptos clave (bullets)
## → Heurística computable     # cómo se traduce a código del agente
## → Hook de recompensa         # qué término de reward toca, si aplica
## Datos parseables             # endpoints/exports si la fuente los da
## Caveats / sesgo
## Fuentes citadas (con autoridad: credenciales del autor)
```

## Estado

Ver `SOURCES.md` (registro maestro, una fila por fuente). Lo mantiene la fase de síntesis.
