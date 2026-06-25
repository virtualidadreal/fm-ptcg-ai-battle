# Dataset — PTCG AI Battle Challenge

> Metadatos de cartas y materiales de referencia del entorno del simulador.
> ⚠️ Licencia: **Competition Use Only**. Hay que **borrar la Competition Data al terminar** la comp.
> No redistribuir fuera del equipo. Pokémon Elements siguen siendo de Pokémon (ver RULES.md).

## Cómo descargar la data

**Kaggle MCP remoto:** conectar el cliente al servidor MCP `https://www.kaggle.com/mcp` y usar la
herramienta `mcp_kaggle_download_competition_data_files`.
(Requiere verificación de identidad de Kaggle aprobada — pendiente a 21 jun 2026.)

Alternativa CLI: `kaggle competitions download -c pokemon-tcg-ai-battle`.

## Episode Replays

- Replays de NUESTRAS submissions: pestaña Submissions, o vía Kaggle CLI/MCP.
  Docs: https://github.com/Kaggle/kaggle-cli/blob/main/docs/simulation_competitions.md
- Replays de OTROS equipos: descargables desde el Leaderboard.
- Habrá **export diario de los episodios top-rated** (para BC/RL/IL), publicado en el foro de la comp.
  → fuente clave para **imitation learning** del meta ganador.

## Ficheros

| Fichero | Contenido |
|---|---|
| `Card_ID_List_EN.pdf` | Referencia de todas las cartas: card ID, nombre, expansión, nº de colección, imagen |
| `Card_ID_List_JP.pdf` | Igual en japonés |
| `EN Card Data.csv` | Metadatos estructurados de cada carta (inglés) |
| `JP Card Data.csv` | Igual en japonés |

EN y JP son idénticos salvo idioma de nombres/descripciones.

## Esquema de los CSV (EN y JP comparten schema)

| Columna | Significado |
|---|---|
| **Card ID** | Identificador único usado por el simulador (clave para mapear obs ↔ carta) |
| **Card Name** | Nombre de la carta |
| **Expansion** | Set/expansión |
| **Collection No.** | Nº de colección dentro de la expansión |
| **Stage / Type** | Pokémon: stage de evolución (Basic, Stage 1, Stage 2). Energy/Trainer: tipo de carta |
| **Rule** | Texto de regla especial, si aplica |
| **Category** | Categoría (Pokémon, Trainer, Energy) |
| **Previous stage** | Stage de evolución previo requerido |
| **HP** | Puntos de vida del Pokémon |
| **Type** | Tipo del Pokémon (Grass, Fire, Water…) |
| **Weakness** | Debilidad de tipo |
| **Resistance (Type)** | Resistencia de tipo |
| **Retreat** | Coste de retirada para cambiar el Pokémon |
| **Move Name** | Nombre del ataque/movimiento |
| **Cost** | Coste de energía del movimiento |
| **Damage** | Daño del movimiento |
| **Effect Explanation** | Descripción del efecto del movimiento / texto de regla adicional |

## Notas para el pipeline de datos

- El **Card ID** es la pieza que conecta las observaciones del engine (`obs["select"]["option"]`)
  con los metadatos. Construir un índice `card_id -> ficha` desde `EN Card Data.csv`.
- Una carta puede tener varias filas si tiene varios moves (un row por Move Name). Agrupar por Card ID.
- El mazo (`deck.csv`) es una lista de 60 Card IDs (uno por línea); IDs vía `all_card_data()` del SDK.
- Parsear `Cost`/`Damage`/`Effect Explanation` será clave para la heurística y la evaluación de estado.
