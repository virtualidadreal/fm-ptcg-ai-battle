# Plan de mejora — Strategy Report (PTCG AI Battle)

> Documento de arranque para una sesión dedicada al **Strategy** (la competición que paga).
> Última actualización: 23 jun 2026. Vivo: actualizar al cerrar cada sesión de report.
> Handoff general: `NEXT-SESSION.md`. Memoria viva: `memoria-claude/proyectos/ptcg-pivote-sabrina-alakazam.md`.

---

## 0. North star (decisiones cerradas, NO re-litigar)

- **El dinero está en el Strategy:** $240K total, **8 finalistas × $30.000** + final presencial en Tokio. Deadline writeup **14 sep 2026** (Sep 14, 1:59 AM GMT+2). El Simulation paga **$0**.
- **NO hay corte de Top-8 de ladder para optar al Strategy** (verificado en reglas oficiales 23 jun):
  - Strategy §2.1.c: solo exige *"compete as part of the same Team registered in the Simulation division"* + equipo idéntico en ambas divisiones. No menciona rango.
  - Strategy §3.7.a: los ganadores se determinan *"solely by the judges' evaluation"* del writeup. El ladder **alimenta** el 70% como evidencia, no es puerta.
- **Nota = 70% metodología (model approach) / 20% concepto de mazo / 10% calidad del report.**
- **El edge real y NO copiable = nuestra METODOLOGÍA + ablations honestas.** No el winrate (material público = suelo que todos forkean). Top-8 realista ~**10-20%**, y está aquí, no en el ladder.
- **Un repo, dos tracks (cadencia separada):** Strategy = foco activo; Simulation = mantenimiento (1 cambio/día, sin obsesión). El repo del Simulation **es** el repo enlazado que premia la reproducibilidad (§2.8.b).
- **Una sola submission al Strategy** (§2.2.a, hackathon = 1 writeup). Es un disparo: hay que entregarlo pulido.
- **Datos externos:** permitidos por reglas (§2.6, si públicos/accesibles), pero **bajo ROI**. NO montar pipeline de Limitless. Solo un pull único corroborante si la sección 6 queda floja.

---

## 1. Estado actual del report (qué hay hecho)

Carpeta `report/`:
- **`REPORT.md`** — draft completo, **1921 palabras (≤2000)**, 7 secciones en prosa, 0 marcadores `[PENDIENTE]`. Tono de honestidad brutal, citas inline (ryotasueyoshi, TCGplayer prize-checking, JustInBasil, Klaczynski).
- **`methodology-evidence.md`** — apéndice claim-by-claim (fuera del límite de palabras), cada cifra mapeada a su fichero/agente del repo, con etiquetas verified/probable.
- **`README.md`** — punto de entrada del repo enlazado (qué es, cómo reproducir cada ablation, mapa del repo).
- **`research/correlation.py`** — reproduce el Spearman **−0.80** exacto (scipy + a mano). Artefacto de reproducibilidad de la claim estrella.

Secciones del report: (1) Intro + framing μ−3σ · (2) Filter-then-Ladder protocol · (3) Seeds mirage (N<60) · (4) 3 NO-GOs (BC/IL, ISMCTS estático, clon Mega Starmie) + A1 inerte como 4ª ablation · (5) No local signal (triple-confirmado) · (6) Deck concept Alakazam single-prize · (7) Conclusión.

### Hecho en sesión 23 jun (tarde) — pasada dev aumentado + ultracode
- ✅ **Registro canónico de los 3 NO-GOs** añadido a `AGENTS.md` (BC / ISMCTS / Mega Starmie con etiqueta explícita + puntero a evidencia). Cierra open question 4: el 3º deja de ser inferido.
- ✅ **Honestidad del ledger reforzada** (`methodology-evidence.md`): bajadas a `probable` las dos claims sobre-vendidas (ISMCTS 0W/15L y greedy BC 21W/129L) que estaban marcadas `verified` sin log primario; **corregida la cita falsa** `bcil/(greedy run)` (no existe el fichero). Anti-falso-positivo: mejor confesar el gap que arriesgar credibilidad ante el juez.
- ✅ **Meta d22 reconciliada a fuente única** `_meta_d22.log`: los matchups 49/49/65 **estaban en el log primario** (tabla MATCHUP, fila Alakazam), no en memoria — subidos a `verified`. Regla de consistencia TOP-TIER (30.4/58.2/395), nunca FIELD (29.0/50.6/2932). Report ancla el bloque meta a `_meta_d22.log`. Cierra open question 2.
- ✅ **Sección 5 (μ−3σ) reescrita** liderando con el mecanismo cuantil-vs-media; Confirmación #2 ahora muestra el gap media-vs-cola directamente. Arco 1→5→7 reforzado.
- ✅ **Pasada de estilo**: 9 em-dash separadores de prosa → coma/punto (pref de Fran). Cuerpo del report **1958 palabras** (≤2000, verificado). 0 marcadores `[PENDIENTE]`.
- ✅ **README repro**: añadido paso 6 (correlation.py, Spearman −0.80, sin motor) + nota de prerequisito Competition Data (Kaggle token).
- ✅ **Hardening pre-publicación del `.gitignore` del proyecto**: hoy el material propietario solo lo tapa la regla `proyectos/` del monorepo, que **no viaja** al extraer la carpeta. Añadido bloque autosuficiente (card data, leaderboards, replays, pesos `.pt`, notebooks de terceros). Validación documentada en el propio `.gitignore`. **NO se ha borrado nada.**
- ⏳ **Pendiente Fran (decisiones suyas):** (a) hosting + publicar el repo + rellenar `[PLACEHOLDER — repo URL]`; (b) opcional re-correr A/B para guardar logs primarios (seeds mirage N=60, agreement, Track F, greedy N=150, ISMCTS 0/15) — degradados a `probable` honesto entretanto; (c) fichaje jugador competitivo (P2).

### Hecho 24 jun — verificación cerrada (cadena de 3 bucles)
- ✅ **Cadena de verificación cerrada en verde.** Veredicto global: **CORRECTO-CON-RESIDUALES** (sin bloqueos). Certificado completo en `research/verificacion-cerrada-2026-06-24.md`.
  - **Bucle 1 (report):** limpio, cuerpo **1993 palabras** (≤2000) convergido en 3 rondas. 0 `[PENDIENTE]`.
  - **Bucle 2 (agentes):** `sabrina_kb_seq` / `sabrina_kb_draw` / `sabrina_kb_role` → **GO ×3** (contract_safe, 1 palanca, flag-OFF ≡ v1). Único residual: tipo de retorno float vs int en `_score_attack` de `_role` con flag OFF, salida byte-equivalente — no bloqueante.
  - **Bucle 3 (KB):** `SOURCES.md` ahora con columnas-puntero a `free/` (12) y `paid/` (4) + fila deckbuilding alineada a H9. 2 pasadas dry posteriores sin gaps.
  - **Engine probe = ON:** Docker `ptcg-cabt:latest` corre linux/amd64 vía colima. A/B real (`ab_harness.py`, N=20) `sabrina_kb_seq` vs `v1` → 11W/9L/0D (55%, Wilson incluye 0.5 → sin diferencia significativa, sin regresión). N=20 es ruido; el A/B real pide N=200. El ladder sigue siendo el juez (cabt anti-predictivo, Spearman −0.80).
- ✅ **Anti-goals intactos:** NO se subió nada al ladder, NO se partió el repo, NO pipeline externo, NO se subió A1, NO se eliminó ningún archivo (los fixes del bucle 3 son adiciones).
- ⏳ **Residuales no bloqueantes (= pendientes ya conocidos):** A/B N=200 real, claims `probable`→`verified`, repo público + URL, flags de fuentes KB (TCGplayer/Klaczynski inline), guía Reklev sin explotar.

---

## 2. Plan para hacerlo Top-8-competitivo (priorizado)

### P0 — Cerrar a entregable publicable
- [ ] **Repo enlazado público:** decidir hosting (GitHub público, MIT), publicar el codebase del Simulation como repo de reproducibilidad, y **sustituir `[PLACEHOLDER — repo URL]`** en la cabecera de `REPORT.md`. Limpiar de Pokémon Elements/Competition Data antes de publicar (§2.4: borrar competition data; no redistribuir card data oficial). Repo = código + logs + instrucciones, NO el material propietario.
- [ ] **Instrucciones de reproducción** en el README: cada ablation reproducible leyendo el texto (lo exige §2.8.b "reproduce by reading the description" + link al repo).

### P0 — Reforzar el 70% (metodología) — es nuestra estrella
- [x] **Que el insight μ−3σ ATERRICE fuerte:** "la métrica es un cuantil de cola, los proxies miden la media, no se encuentran" + triple confirmación (Spearman −0.80, agreement ciego, panel Track F que invierte). Es lo más diferenciador y lo que casi nadie articula. Pulir su narrativa.
- [ ] **Endurecer evidencia memory-only → primaria** (el verificador lo marcó):
  - Generar artefacto del **espejismo de seeds N20(65%)→N60(40%)** (solo el full-budget 22% N=18 tiene log primario). Re-correr o guardar el run.
  - **Agreement (43.52% vs 43.84%) y Track F (+0.20)**: hoy solo en memoria → script que los recompute o tabla en `research/`.
  - [x] **Registro de los 3 NO-GOs en una línea** (en `AGENTS.md` o `NEXT-SESSION.md`) para quitar la ambigüedad de cuál es el 3º (clon Mega Starmie). ✅ Hecho en `AGENTS.md`.
- [ ] **Dev Aumentado DENTRO como protocolo de rigor, nunca protagonista** (disciplina anti-falso-positivo: A/B pareado, Wilson, N≥60, 1 cambio/día).

### P1 — Reforzar el 20% (concepto de mazo)
- [x] **Reconciliar las cifras de meta d22** (30.4%/58.2%/n=395 en `_meta_d22.log`) vs el snapshot viejo (18.9%/55.1%). Fijar fuente única citada. ✅ Fuente única = `_meta_d22.log`; matchups primarios; regla TOP-TIER vs FIELD fijada.
- [ ] Tesis Alakazam single-prize / consistency-first afilada (el net-prize ya está baked-in en la elección de mazo single-prize — conecta con A1 inerte).
- [ ] **Opcional, solo si la sección queda floja:** pull único de 3-4 eventos STANDARD de Limitless mostrando que Alakazam es top-tier también en humano (prior corroborante). NO pipeline. Decisión: por defecto, NO.

### P1 — Calidad (10%)
- [ ] Arco narrativo claro, figuras/tablas donde aporten, prosa tensa, **mantener ≤2000**. Pasada de estilo (sin em-dash como separador; preferencias de Fran).
- [ ] Pasada del verificador adversarial final (anti-inflado) antes de entregar.

### P2 — Palancas estratégicas (fuera del report en sí)
- [ ] **Fichaje de jugador competitivo de PTCG** (decisión julio, **antes del merger del 9 ago**): sube el 20% (concepto) y la credibilidad de pilotaje. Ojo §2.1.c: equipo idéntico en ambas divisiones, cambios reflejados igual.
- [ ] **Mantener el agente del ladder estable y respetable** (no Top-8, pero que no socave el 70% con un agente flojo). Carril de mantenimiento, ver track Simulation.

---

## 3. Checklist de la próxima sesión de Strategy (orden sugerido)

1. Leer este plan + `report/REPORT.md` (estado) + las 5 open questions del verificador (abajo).
2. Decidir hosting del repo y publicarlo (MIT, limpio de material propietario) → rellenar la URL.
3. Pasada de endurecimiento de evidencia: generar/guardar los artefactos primarios que faltan (seeds mirage, agreement/Track F) + registro 3-NO-GO.
4. Pulir secciones 5 (μ−3σ, la estrella) y 1/7 (arco) → verificador final → conteo ≤2000.
5. Reconciliar meta d22 en sección 6.
6. (Opcional) decidir el pull Limitless solo si 6 queda floja.

---

## 4. Open questions a resolver (del verificador del report)

1. Spearman −0.80 / agreement / Track F: −0.80 ya reproducible (`correlation.py`); falta artefacto primario para agreement (43.52/43.84) y Track F (+0.20) — hoy memory-only.
2. Meta d22 (30.4/58.2/395) vs snapshot viejo (18.9/55.1): reconciliar y fijar fuente (`_meta_d22.log` es primaria).
3. Espejismo N20→N60 (65→40): sin log primario guardado (solo el full-budget N=18). Guardar un run.
4. Los 3 NO-GOs no están listados con etiqueta explícita en un sitio; el 3º (Mega Starmie) es inferido. Añadir registro de 1 línea.
5. `[PLACEHOLDER — repo URL]` en cabecera: rellenar al publicar el repo.

---

## 5. Anti-goals (NO hacer)

- NO partir el codebase en dos repos (rompe citas/reproducibilidad; el report depende del árbol del Simulation).
- NO montar el pipeline de datos externos (Limitless/ELO/fusión): bajo ROI, no mueve la nota.
- NO perseguir rating Top-8 del ladder (826→1257 casi imposible, paga $0).
- NO quemar las ranuras del ladder en variantes correlacionadas; 1 cambio/día, v1 (826.9) de suelo.
- NO vender Dev Aumentado como protagonista; va dentro como protocolo de rigor.
- NO subir A1 (medida inerte para single-prize Alakazam; vive como ablation en el report).
