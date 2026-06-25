# Best-Player Handoff — Knowledge OS → Report + Build

> Curador final. 24 jun 2026. Tono del proyecto: honesto, local≠ladder, 1 cambio/día.
> Suelo a batir: `sabrina_v1` = **826.9** en ladder. Solo el ladder juzga.

---

## TL;DR ejecutivo (8 líneas para Fran)

1. **Report:** aplica el diff propuesto (appendix `knowledge-os-evidence.md` ya escrito + 7 ediciones a `REPORT.md`). Veredicto: **APLICAR-CON-CAMBIOS**, 2 cambios menores, ninguno bloqueante.
2. **Cambio 1 (obligatorio):** el conteo de la propuesta está mal en el desglose. Real: **after = 1992** palabras (no 1993), margen **8** (no 7); línea (d) correcta = **+239 inserido / −209 cortado = +30** (la "+143/−112 = +31" es aritméticamente falsa). El cuerpo queda ≤2000, seguro.
3. **Cambio 2 (recomendado):** en §6-nuevo, `cabt≠Standard` usa `≠` Unicode. Verifica el render; si dudas, escribe "cabt ≠ Standard" con espacios (como ya está en el appendix D).
4. **Todo lo demás del diff se aplica tal cual.** Es honesto, trazable 1:1 al appendix, y net-negativo en credenciales infladas (borra la atribución Klaczynski y la de Limitless "TPCi partner").
5. **Build:** 3 candidatos **GO** para A/B, contract-safe, byte-equivalentes a v1 con flag OFF. Ninguno validado end-to-end en esta máquina (macOS no carga `libcg.so`, es linux/amd64). **Validar en Docker/ladder, no en cabt local** (cabt es anti-predictivo, Spearman −0.80).
6. **Orden (1 cambio/día):** **día 1 → `sabrina_kb_seq`** (cambio más seguro, valida el harness), **día 2 → `sabrina_kb_draw`** (mayor mecanismo: ataca el deck-out, modo de derrota dominante; mayor edge/riesgo), **día 3 → `sabrina_kb_role`** (dial concepto, solapa con role, evaluar aislado).
7. **Expectativa honesta:** el deck-out-fix (`kb_draw`) es el de mayor mecanismo pero **sin validar**; local no predice nada. No combinar palancas antes del A/B individual. Leon v1 se mantiene en su ranura.
8. **Pendiente externo:** la guía de **Reklev (40$)** y el **módulo de heurística general reutilizable** quedan documentados abajo como trabajo futuro, NO bloquean el lanzamiento.

---

## 1. REPORT — qué aplicar y qué recortar (≤2000)

### Estado de fase 1
- **Appendix ya escrito:** `report/knowledge-os-evidence.md` (existe en disco, 14.4 KB). Documenta: protocolo de destilación en dos niveles (12 fuentes gratis → 9 heurísticas + reward-spec, fan-out-then-adversarial-verify, tier de pago nunca ingerido), las 6 fabricaciones claim-by-claim con corrección y fuente, el mapa H1–H9 con estado de transferencia, y el caveat `cabt≠Standard` como marcador de honestidad. Mismo ledger verified/probable + "known gaps" que `methodology-evidence.md`.
- **Verificador (fase 1):** "All claims in the diff trace to verified rows in the appendix. El diff evita el headcount '30 agents' (que el propio appendix marca como no-verificable en Known gaps §1) y usa '12 sources / 9 heuristics', ambos verified. Audit complete."

### Conteo de palabras — CORREGIDO
| | Propuesta dice | Real (verificado) |
|---|---|---|
| Before (§1 a fin) | 1962 | **1962** ✓ |
| After | 1993 | **1992** |
| Margen | 7 | **8** |
| Desglose (d) | +143 / −112 = +31 | **+239 inserido / −209 cortado = +30** |

El número final (~1992) es correcto y seguro. Solo el desglose intermedio de la propuesta está mal redactado. **Corregir el texto (c)/(d) al aplicar.**

### Las 7 ediciones a `REPORT.md` (aplicar tal cual, salvo el conteo)

1. **§1 — TIGHTEN honesty-marker (−20w).** Sustituir el párrafo largo "One honesty marker up front, because it sets the credibility…" por la versión corta "One honesty marker up front: we mark every claim as ladder-verified or local-only. Local results are a filter, never a verdict, and we never present an unconverged ladder run as a result."
2. **§2 — ADD párrafo Knowledge OS (+79w)** antes del párrafo final "non-copyable edge": la disciplina anti-falso-positivo un nivel arriba; 12 fuentes → 9 heurísticas; verificador adversarial mató 6 fabricaciones (Flipside falsa, "Consistency is the goal" mal atribuida a Klaczynski, conflación players-vs-games, prior que no suma 1, Limitless "official TPCi partner", Counter Catcher mal citado). Detalle en `report/knowledge-os-evidence.md`.
3. **§2 — TIGHTEN "non-copyable edge" (−7w).** Versión corta: "This process is the non-copyable edge: the public notebooks are a floor everyone forks; the reproducible process is what the methodology grade rewards. Full reproducibility lives in the linked repo."
4. **§5 — DELETE línea community-corroboration (−24w).** (Se preserva en `methodology-evidence.md` §E; la verdict-line que sigue ya lleva la lección.)
5. **§6 — ADD sentence-block prize-trade (+64w)** al final del párrafo "We pivoted to a pure single-prize Alakazam…": el single-prize tiene el prize-trade edge baked in; el lever A1 net-prize dispara 0 veces (§7). Es el core H1/H2 del Knowledge OS, cuyo caveat `cabt≠Standard` (d22 in-engine como live, Standard solo corroboración) es el gemelo knowledge-layer del mismatch mean-vs-quantile de §5.
6. **§6 — TIGHTEN matchup/headroom (−20w).** Versión corta: "Its spread is healthy: par vs Trevenant and Dragapult (49% each), beats Mega Lucario (65%), all from `_meta_d22.log`. Headroom proof: a rule-based non-psychic Alakazam reached ~5th without search (ryotasueyoshi). The ceiling is piloting, not structure."
7. **§6 — DELETE párrafo "design draws on public competitive theory" (−41w).** Contiene justo la atribución Klaczynski "piloting principles" que el Knowledge OS marcó como mal atribuida. Las fuentes y la re-implementación license-clean de ryotasueyoshi quedan en `methodology-evidence.md` §F y `knowledge-os-evidence.md` (ambos ya enlazados desde el header). **NO añadir el pointer opcional de +13w** (empujaría a 2006, fuera de límite).

### Las 6 fabricaciones (do-not-replicate, una línea)
1. **Flipside falsa** — "role is intrinsic to the deck's design" no existe en la fuente; `matchup_fav` es un prior reordenable, no verdad citada.
2. **Klaczynski** — "Consistency is the goal" es de un autor tercero de 60cards, no del 3× campeón; mantener la estructura, quitar la credencial.
3. **Players↔games** — "18,537 players" presentado como games (real ~41,105 games); error de categoría que envenena cualquier share derivado.
4. **Prior que no suma 1** — `meta_prior` con `+0.40` de relleno arbitrario en "other"; no es distribución válida, debe medirse in-engine.
5. **Limitless "official TPCi partner"** — credencial inflada desmentida por el propio footer de Limitless.
6. **Counter Catcher mal citado** — texto over-specific erróneo; solo el *patrón* de legalidad (Item, legal con `my_prizes > opp_prizes`) transfiere a cabt.

---

## 2. BUILD — candidatos GO, orden y comandos

Spec completa: `research/best-player-build-spec.md`. Los 3 son byte-idénticos a `sabrina_v1` salvo la palanca, solo reordenan scores de opciones ya legales (nunca tocan legalidad ni firmas), preservan `agent` como último callable + `normalize_selection`/`_validate_obj`, y `deck.csv` es byte-idéntico al de v1. Flag OFF ⇒ byte-equivalente a v1 (reversibilidad verificada en código).

> **Aviso de validación (los 3):** end-to-end NO validado en esta máquina. `cg/libcg.so` es linux/amd64; en macOS da "slice is not valid mach-o file". Revisión estática completa y limpia (AST parsea, 0 `raise`, math acotada en [0,1], contrato intacto). **Correr smoke + A/B en runtime Linux/Docker antes de subir.**

### Orden recomendado (1 cambio/día)

**DÍA 1 — `sabrina_kb_seq`** (sequencing, heurística #5)
- *Por qué primero:* cambio más conservador y acotado; valida el harness A/B sobre algo seguro antes de arriesgar. Nudge `bias = SEQ_EPSILON*(PHASE_LATE-ph)`, máx 40, frente a scores base en los miles. Solo rompe empates / huecos <40 en la elección top-level de tipo de acción; sub-selects CARD intactos. No puede resucitar opción rechazada.
- *Comando (Docker linux/amd64):*
```
cd /Users/franmilla/FMA/proyectos/ptcg-ai-battle && docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt python experiments/ab_harness.py agents_official/sabrina_kb_seq agents_official/sabrina_v1 200
```

**DÍA 2 — `sabrina_kb_draw`** (deck-out fix / prize-belief buffer, heurística #4)
- *Por qué:* **mayor mecanismo de todos** — ataca el modo de derrota dominante (deck-out) reemplazando constantes mágicas por regla hipergeométrica citable. Mayor edge y mayor riesgo. `_kb_draw_guard_active()` es estrictamente más conservador que `_deck_preserve` (cede a lo sumo un draw opcional con `deckCount<=9` y `_have_attacker()`). El guard puede ceder algo de tempo: efecto NETO solo lo decide la ladder.
- *Comando:*
```
python experiments/ab_harness.py agents_official/sabrina_kb_draw agents_official/sabrina_v1 200
```
(correr dentro de `ptcg-cabt` Docker linux/amd64)

**DÍA 3 — `sabrina_kb_role`** (rol BEATDOWN/CONTROL/NEUTRAL, heurística #8)
- *Por qué último:* dial de concepto race-vs-grind; 3 knobs (close x1.20 / draw x0.80 / preserve_bar +4) que colapsan a identidad de v1 cuando `role==NEUTRAL` o `SABRINA_ROLE_NUDGE=0`. Solapa con la idea de role/grind — evaluar **aislado**. El nudge nunca toca la banda letal 90000; draw=0.80 tiene suelo 12000 > 9000 (jamás deja de robar, solo pierde empates tarde).
- *Comando:*
```
python experiments/ab_harness.py agents_official/sabrina_kb_role agents_official/sabrina_v1 200
```

**NO hacer:** combinar palancas antes del A/B individual; construir sobre R1/R2/R6 (inertes single-prize) ni #7/R7 (P2 sin ROI). Leon v1 se mantiene en su ranura.

---

## 3. Expectativa honesta

- **Local ≠ ladder. Solo el ladder juzga.** cabt local es anti-predictivo (Spearman −0.80); ningún número local predice el ranking. El A/B de 200 partidas es un filtro para descartar regresiones obvias, no un veredicto.
- **El deck-out-fix (`kb_draw`) es el de mayor mecanismo pero el menos validado.** Ataca el modo de derrota dominante con regla citable, pero su efecto neto en winrate es desconocido hasta correrlo en ladder real. Es el de mayor edge *y* mayor riesgo; por eso va día 2, después de que `kb_seq` haya validado el harness.
- **Suelo a batir: 826.9 (`sabrina_v1`).** Un candidato solo entra si gana en ladder, no en cabt.
- **Ninguno validado en esta máquina.** macOS no carga el motor nativo. Todo lo que se afirma es revisión estática + math acotada; la partida real falta.

---

## 4. Trabajo futuro (NO bloquea el lanzamiento)

### Guía de Reklev (40$, cuando Fran la compre)
- Es contenido **de pago, tier no ingerido** por el Knowledge OS (la regla del protocolo: el tier de pago nunca se mete sin licencia). Cuando Fran la compre, pasarla por el mismo pipeline: fan-out → destilar a heurísticas computables → verificador adversarial → ledger verified/probable, citando fuente (no verbatim).
- Esperar de ella: refinamiento de las heurísticas de piloting/sequencing (H5) y de prize-checking (H1/H2) que ahora están como "probable". Posible des-bloqueo de la atribución que se borró del §6 (sustituir la credencial Klaczynski mal citada por una fuente real y citable de Reklev si aplica).

### Módulo de heurística general reutilizable
- El Knowledge OS (12 fuentes → 9 heurísticas + reward-spec, fan-out-then-adversarial-verify) es **el edge no-copiable** y debería extraerse del proyecto PTCG a un módulo genérico reutilizable (mismo patrón que `deep-research`: fan-out + verificación adversarial).
- Pendiente: separar el motor de destilación/verificación (genérico) de las heurísticas PTCG-específicas (H1–H9). El motor sirve para cualquier dominio donde haya fuentes elite a destilar en reglas computables con un verificador anti-falso-positivo. Documentar como skill/referencia reutilizable.

---

## Archivos relevantes
- `report/REPORT.md` — destino del diff (7 ediciones)
- `report/knowledge-os-evidence.md` — appendix ya escrito (verified/probable + known gaps)
- `report/methodology-evidence.md` — appendix hermano (§E community-corroboration, §F fuentes/licencias)
- `research/best-player-build-spec.md` — spec de los 3 candidatos
- `STRATEGY-PLAN.md` — anti-goals (no perseguir ladder, 1 cambio/día, Dev Aumentado no protagonista)
- Candidatos: `agents_official/sabrina_kb_seq`, `agents_official/sabrina_kb_draw`, `agents_official/sabrina_kb_role`
