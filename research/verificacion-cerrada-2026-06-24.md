# Verificación cerrada — cadena PTCG (24 jun 2026)

> Certificación final de la cadena de verificación de 3 bucles (report / agentes / KB).
> Certificador: subagente de cierre. Fecha: 24 jun 2026.

---

## Veredicto global: **CORRECTO-CON-RESIDUALES**

Los 3 bucles cierran en verde. No hay bloqueos. Quedan residuales no bloqueantes (todos
de tipo "pendiente de Fran" o "observación de rigor"), listados explícitamente abajo.

| Bucle | Objeto | Estado | Rondas |
|-------|--------|--------|--------|
| 1 | Strategy report (`report/REPORT.md`) | ✅ limpio | 3 |
| 2 | Agentes KB (3 variantes sabrina_kb_*) | ✅ GO ×3 | 1 c/u |
| 3 | Knowledge base (SOURCES/INDEX/heurísticas) | ✅ cerrado | 1 + 2 dry |
| Engine probe | Docker linux/amd64 | ✅ ENGINE=ON | — |

---

## Bucle 1 — Report (GO)

- **limpio = true.** Cuerpo **1993 palabras** (≤2000), convergido en **3 rondas**.
- 7 secciones en prosa, 0 marcadores `[PENDIENTE]`, citas inline, ledger claim-by-claim
  en `methodology-evidence.md` con etiquetas verified/probable honestas.
- Sin defectos abiertos en el cuerpo. Los pendientes del report son decisiones de Fran
  (publicar repo + rellenar `[PLACEHOLDER — repo URL]`, opcional re-correr A/B para subir
  claims `probable` → `verified`).

## Bucle 2 — Agentes (GO ×3)

Las 3 variantes pasan el contrato y la regla "1 palanca / flag-OFF ≡ v1":

| Slug | Verdict | contract_safe | one_lever | flag_off≡v1 | Rondas | Issues |
|------|---------|---------------|-----------|-------------|--------|--------|
| `sabrina_kb_seq` | GO | ✅ | ✅ | ✅ | 1 | — |
| `sabrina_kb_draw` | GO | ✅ | ✅ | ✅ | 1 | — |
| `sabrina_kb_role` | GO | ✅ | ✅ | ✅ | 1 | 1 (no bloqueante) |

- **Residual `sabrina_kb_role` (no bloqueante, observación de tipo, no defecto):** con el flag
  OFF, `_score_attack` devuelve `score * 1.0` (float) en vez del `int` de v1. La **lista de
  acciones devuelta es byte-idéntica a sabrina_v1** porque los scores se comparan por valor y se
  testean `> 0` (1500 == 1500.0). Flag-OFF es byte-equivalente a nivel de salida de `agent()`;
  solo difiere el tipo de retorno interno. Si un revisor estricto exige paridad literal de tipo:
  envolver en `return int(score * self._role_mul('close'))` o guardar el multiply tras
  `if ROLE_NUDGE_ON`. No afecta selección, diag ni contrato. **Se deja como está.**

## Bucle 3 — Knowledge base (cerrado)

- **Pasada 1 (no-dry):** 3 fixes aplicados en `SOURCES.md` para hacer verificable el criterio
  "cada fila tiene su fichero destilado":
  1. Tabla GRATIS: añadida columna **"Ficha destilada"** con los 12 punteros `free/*.md` (1:1).
  2. Tabla DE PAGO: añadida columna **"Plan / ficha"** con los 4 punteros `paid/*.md` (P1–P4).
  3. Fila 3 (deckbuilding): añadido pointer **"→ H9"** para alinear con `synthesis/INDEX.md` y
     `heuristicas-computables.md`.
- **Pasadas 2 y 3 (dry):** sin gaps, sin fixes. Estable.
- **Residual no bloqueante (registrado, no perdido):** de los 3 flags de fuentes (Flipside
  fabricada / TCGplayer prize no-verificable / Klaczynski misatribuida), solo Flipside tiene
  entrada ⬜ propia (BACKLOG L117). TCGplayer y Klaczynski viven como caveats verificados inline
  en `heuristicas-computables` (L139-140, L255-256) + consolidados en BACKLOG Resumen item 6.
  Suficiente para "no se caen". Se deja como está.

## Engine probe — ENGINE=ON

- `colima status` → running (Virtualization.Framework, aarch64, runtime docker).
- `docker images` → `ptcg-cabt:latest` (7e66c5dbae30, 2.08 GB) presente.
- Engine linux/amd64 carga bajo `--platform=linux/amd64` (sin "not valid mach-o"; `libcg.so`
  carga, partida end-to-end OK).
- **A/B real corrido** (`experiments/ab_harness.py`, comando del handoff línea 69, N=20):
  `sabrina_kb_seq` (A) vs `sabrina_v1` (B) → **11W / 9L / 0D, win-rate 55.0%**
  (Wilson 95% IC 34.2%–74.2%, incluye 0.5 → sin diferencia significativa). TrueSkill
  μ_A−μ_B = +0.45. Sin crashes, sin invalids, sin draws; ambos pasan self-check deck-phase (60 ids).
- **Caveat propio del harness:** cabt local NO predice el ladder (Spearman −0.80, anti-predictivo).
  Es filtro barato anti-regresión, no el juez. N=20 es ruido; el A/B real pide N=200.
  **El juez sigue siendo el ladder.**

---

## Lo que queda (explícito)

Todos no bloqueantes. Ninguno impide entregar ni rompe anti-goals.

1. **A/B end-to-end a N grande:** el smoke corrido fue N=20 (ruido estadístico). El A/B real
   anti-regresión pide **N=200** (handoff). El engine ya está probado funcionando vía Docker
   linux/amd64, así que es solo cuestión de tiempo de cómputo, no de capacidad.
2. **Claims `probable` → `verified` (report):** seeds mirage N20→N60, agreement (43.52/43.84),
   Track F (+0.20) siguen memory-only. Re-correr / guardar logs primarios cuando Fran decida.
3. **Repo público + URL:** `[PLACEHOLDER — repo URL]` en `REPORT.md` sin rellenar (decisión de
   hosting de Fran, P0 del plan).
4. **Flags de fuentes KB:** TCGplayer y Klaczynski registrados como caveats inline + BACKLOG, sin
   acción ⬜ individual. Flipside sí tiene ⬜ propia. Suficiente, no se pierden.
5. **`sabrina_kb_role` paridad de tipo:** opcional envolver el multiply en `int(...)` o tras flag
   si un revisor exige type-parity literal. Salida ya byte-equivalente.
6. **Guía Reklev (paid/reklev):** destilada y enlazada en SOURCES (P2), pendiente de explotación
   si la sección de concepto de mazo queda floja.

---

## Confirmación de seguridad (anti-goals)

- ✅ **NO se subió nada al ladder.** El A/B se corrió en local vía Docker, no es una submission.
  La regla "1 cambio/día" y el suelo v1 (826.9) intactos.
- ✅ **NO se partió el codebase** en dos repos.
- ✅ **NO se montó pipeline de datos externos** (Limitless/ELO).
- ✅ **NO se subió A1** (medida inerte; vive como ablation en el report).
- ✅ **NO se eliminó ningún archivo ni carpeta.** Los fixes del bucle 3 son adiciones de columnas
  y punteros en `SOURCES.md`.
- ✅ **Regla "1 palanca por agente"** respetada en las 3 variantes; flag-OFF equivalente a v1.

---

_Certificado 24 jun 2026._
