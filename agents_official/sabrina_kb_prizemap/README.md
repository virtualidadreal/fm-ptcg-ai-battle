# sabrina_kb_prizemap — adaptive 6-prize prize-map nudge (Knowledge OS H1b)

Fork de `sabrina_v1` que añade **una sola palanca**: un *nudge* post-hoc que sesga la
selección de **ataque** y de **objetivo de gust** para mantenerse en la **secuencia de KO más
barata** que cierra los premios que quedan — el upgrade del **prize map** (H1b) del vídeo de
**CFB Edge / Isaiah Bradner** (`knowledge/free/video-enrichment-2026-06-24.md` §1).

`deck.csv` es **byte-idéntico** a `sabrina_v1` (1 palanca = solo lógica). El scaffolding de
hardening (contrato `agent(obs, config=None) -> list[int]`, doble `try/except` global,
`_legal_fallback` repetición-safe, `_validate_obj` como gate final, carga de módulo
no-raising) es **verbatim** del estándar campeón.

## La heurística del Knowledge OS de la que sale (H1b)

H1b dice: **planifica los 6 premios desde el turno 1, recomputa el mapa cada turno, elige la
jugada por "¿mantiene el mapa en pista?", DESCARTA los planes sin recursos (gust + energía +
recovery), y haz un chequeo de deck-out antes de comprometer el último Boss/energía.**

`sabrina_kb_draw` ya implementa **la mitad del chequeo de deck-out** (deja de robar opcional
cuando la win-con está a salvo). Esta palanca cubre **la OTRA mitad**: el **PLAN adaptativo de
premios** que sesga la elección de ataque/objetivo para gastar los KO en la secuencia más barata
hasta el último premio, con un **gate de factibilidad** que retira el bonus de un objetivo cuyo
plan no podemos ejecutar este turno (no tenemos gust para alcanzarlo). Es **complementaria** a
`kb_draw`, no solapa.

## La palanca (una variable, detrás de flag)

`main.py`: `FMA_KB_PRIZEMAP = os.environ.get("FMA_KB_PRIZEMAP", "1") ...`. Ponlo a `0` y el
comportamiento vuelve a ser **equivalente byte a byte** a `sabrina_v1` (el término se elimina y
`sort_key == scores`).

En `rank()` construimos una **clave de orden SEPARADA** `scores[i] + _prizemap_bias(o)` sin
mutar `scores`, y solo se aplica a opciones que la policy **ya quiere** (`score > 0`) y solo a
opciones de tipo **ATTACK** o **CARD-objetivo del rival** (gust/switch):

- **prize_map (recomputado cada decisión):** `remaining = len(prize)` premios por tomar. Entre
  los KO alcanzables este turno (Activo + banca alcanzable por gust) puntúa cada uno por cuánto
  abarata la secuencia: un **FINISH** este turno (este KO toma el/los último(s) premio(s))
  domina (ordinal 3); si no, prefiere el KO de **más premios por turno** (2-premios > 1-premio),
  acotado a {0,1,2,3}.
- **gate de factibilidad:** un objetivo en **banca** sin Boss's Orders en mano (o con el slot de
  Supporter ya gastado) NO recibe bonus — nunca sesgamos hacia un plan que no podemos ejecutar.
  El gate solo **retira** el bonus; **nunca penaliza** por debajo de v1.

### Por qué es un NUDGE acotado y reversible (no un rewrite)

- **`PRIZEMAP_EPSILON = 8` es minúsculo** frente a la escala de v1 (play/attack en miles; letal
  = 90000; bonus de KO en `_score_attack` = `2500 + prize*200`). `epsilon*3 ≈ 24` solo separa
  empates de base igual. **Nunca puede voltear una decisión de magnitud, nunca anula letal,
  nunca resucita una opción rechazada** (`score <= 0`) ni habilita un pick ilegal.
- **No muta `scores`.** `normalize_selection` usa `scores` con umbral `s > 0`, así que el sesgo
  solo **reordena** opciones ya deseadas: cambia el ORDEN entre KO/objetivos igual de buenos,
  nunca QUÉ cartas se juegan.
- **Solo añade, nunca resta.** `_prizemap_target_advance` devuelve `>= 0` siempre → nunca empuja
  un score por debajo de v1.
- Cualquier fallo en el cálculo del mapa → `except` → se comporta exactamente como v1.

### Archetype-AGNOSTIC (objetivo "mejor jugador de PTCG", no solo Alakazam)

El módulo `_prizemap_*` referencia solo conceptos genéricos del motor (conteos de premios, KO
alcanzables, disponibilidad de gust) y reutiliza los helpers de daño/gust de la propia policy
(`_alakazam_damage`, `_active_best_dmg`, `prize_count`). No introduce **ninguna lógica nueva
específica de Alakazam** → la **forma del planificador** transfiere a un agente general de PTCG.
Lo único que cabría parametrizar para otro mazo (qué carta de gust hay en mano) ya vive aislado
en `_prizemap_gust_available`.

## Smoke test (motor cabt, local, vía Docker)

⚠️ **PENDIENTE de ejecutar** (esta tarea NO corre Docker; la verificación va aparte). El
`_selfcheck.py` instrumenta cuántas veces el sesgo es no-cero (monkeypatch sobre
`_prizemap_bias`) para reportar honestamente si la palanca está viva o casi dormida.

Comando (con colima + Docker `ptcg-cabt` vivos, cwd = este dir):

```bash
docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt python _selfcheck.py
```

PASS requiere: `completed == N_GAMES`, 0 None-rewards, `policy_fallback=0`, `obs_fallback=0`,
`fallback_rate=0.0`, `deck==60`. El reporte añade `prizemap calls / NON-ZERO / bias sum /
prizemap_fires` para ver si el término dispara.

## Protocolo de A/B (dev aumentado)

1. **Filtro local (DIRECTIONAL)**, pareado vs `sabrina_v1`, asientos alternados, N≥60. Comando
   (desde la raíz del repo):

   ```bash
   docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work/ptcg-abc ptcg-cabt \
     python tools/cabt_ab.py ../agents_official/sabrina_kb_prizemap ../agents_official/sabrina_v1 60
   ```

2. 🚫 **NO vetar por una caída de cabt** — cabt es anti-predictivo del ladder (Spearman −0.80).
   Una bajada de cabt NO es evidencia de que el cambio sea malo.
3. **El ladder es el único juez.** Si el filtro local no muestra regresión, `bash
   build_submission.sh` y subir (decisión de Fran), 1 cambio/día, manteniendo `sabrina_v1` (y
   Dragapult/Leon v1) como suelo verificado en la otra ranura. **NO subir sin la decisión de Fran.**

## Scope honesto (no inflar)

Ataca la **selección de qué KO tomar** cuando hay varios KO/objetivos igual de buenos por la
puntuación base de v1: en ese empate, prefiere el que avanza el mapa de premios por la ruta más
barata y que **podemos ejecutar** (gust disponible). NO cambia cuántas cartas robamos (eso es
`kb_draw`), NO toca energía/evolución/setup, NO inventa agresión. Es un nudge de planificación
conservador: en el peor caso es inerte (no hay empates que romper); el upside es no malgastar un
gust/KO en un objetivo subóptimo cuando la partida se decide por la carrera de premios. El
chequeo de deck-out completo de H1b ya vive en `kb_draw`; aquí solo está el PLAN adaptativo.
