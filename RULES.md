# Reglas — PTCG AI Battle Challenge Simulation (resumen fiel)

> Título oficial: "The Pokémon Company - PTCG AI Battle Challenge Simulation".
> Host: Google LLC. Sponsor: The Pokémon Company. Licencia winner: **MIT**. Data: **Competition Use Only**.
> Total prizes en ESTA comp (Simulation): **n/a** (el dinero está en la Strategy — ver COMPETITIONS.md).

## Operativa (lo que nos afecta a diario)

- **Equipos:** máx **5** personas. Merger permitido hasta el merger deadline; el equipo combinado no puede
  superar el total de submissions permitidas a esa fecha (5/día × días corridos).
- **Submissions:** máx **5/día**. Eliges hasta **2 Final Submissions** para el juicio. Solo se trackean
  las 2 últimas para evaluación continua.
- **Una sola cuenta** por persona. Multi-cuenta o proxy = descalificación.
- **Scoring:** rating gaussiano. Sin Private Leaderboard en comps de simulación (el leaderboard es público).
  El margen de victoria NO afecta al rating.
- **🔴 NO INGRESS/EGRESS (Sec 2.12):** durante la evaluación de un episodio el agente **no puede traer ni
  enviar información externa**. Agente Python autocontenido y offline. Nada de llamadas a LLM/API en runtime.
- **Replays públicos:** un replay de cada episodio (con las acciones de tu submission) puede ser público y
  descargable.

## Datos externos y herramientas (Sec 2.6)

- **Se permite External Data y modelos** salvo prohibición expresa, SI son "razonablemente accesibles a todos"
  y de "coste mínimo" (Reasonableness Standard). Ej. ok: suscripción pequeña tipo Gemini Advanced.
  No ok: dataset propietario que cueste más que el premio.
- **AMLT (AutoML) permitido** si tienes licencia adecuada.
- Debemos tener los derechos sobre cualquier External Data que usemos.

## Código y sharing (Sec 3.6)

- **No private sharing** fuera del equipo (ni código ni data). Compartir entre equipos distintos = descalificación.
- **Public sharing permitido** SOLO en los foros/notebooks de Kaggle de la comp, y queda licenciado bajo licencia
  OSI que no limite uso comercial. **Nunca** compartir Pokémon Elements.
- Si usas open source en la submission, debe ser licencia aprobada por OSI que no limite uso comercial.

## Obligaciones del ganador (Sec 2.8)

- Entregar el código final (training + inference + descripción del entorno de cómputo) y documentación
  reproducible.
- Conceder licencia **open source (OSI, sin limitar uso comercial)** del winning submission y su código.
- Si usaste software comercial común no propio, basta con identificarlo y cómo obtenerlo.
- Firmar documentos de aceptación (incl. formularios fiscales US: W-9 / W-8BEN). Impuestos a cargo del ganador.

## IP — Pokémon Elements (Sec 3.18.f) — IMPORTANTE

- **Todo lo "Pokémon" (cartas, nombres, reglas, daños, recetas de mazo, tipos, etc.) sigue siendo de Pokémon.**
  No se nos transfiere nada de eso.
- **Lo que SÍ retenemos:** nuestros modelos, algoritmos, código fuente, embeddings, vectores, pesos entrenados.
  PERO con restricciones:
  - No usar modelos entrenados sobre Pokémon Elements (ni los Elements) **fuera de la competición**.
  - No usarlos con **fines comerciales** ni para crear productos que **compitan con Pokémon**.
  - Regenerar/extraer Pokémon Elements fuera de la comp con el modelo = infracción de IP.
- **Borrar la Competition Data al terminar la competición.**

  → Implicación para nosotros: el proyecto es **banco de pruebas del Dev Aumentado y contenido/caso de marca**,
    NO un activo comercial reutilizable. El know-how y el harness genérico (sin Pokémon Elements) sí es nuestro.

## Elegibilidad

- +18, cuenta Kaggle registrada, no residente de territorios sancionados (Crimea, DNR/LNR, Cuba, Irán, N. Corea).
  Residencia en España OK.

## Fechas (de la pestaña Timeline)

| Hito | Fecha |
|---|---|
| Start | 16 jun 2026 |
| Entry deadline (aceptar reglas) | 9 ago 2026 |
| Team merger deadline | 9 ago 2026 |
| Final submission | 16 ago 2026 |
| Convergencia leaderboard | 17–31 ago 2026 |

_Reglas completas oficiales en la web de la comp; este fichero es el resumen operativo de trabajo._
