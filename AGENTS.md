# PTCG AI Battle — Registro de agentes (nombres + versionado)

> **Esquema de nombres:** cada *línea* de agente que compite lleva el nombre del **entrenador canónico del
> mazo que pilota** (entrenador + su Pokémon). Versionado `Nombre vN`, sube solo en cambios sustantivos.
> Los baselines y el scaffolding NO llevan nombre propio (son utillaje).
> Mapa entrenador↔mazo (para futuras líneas): Dragapult→**Leon**, Alakazam→Sabrina, Mega Lucario→Korrina,
> Hop's Trevenant→Hop, Iono's Bellibolt→Iono.

## Líneas activas

### 🐉 Leon (mazo: Dragapult ex)
| Versión | Qué es | Estado | Local | Ladder |
|---|---|---|---|---|
| **Leon v1** | Sample oficial tuneado (`kiyotah/...dragapult`) + scaffolding robusto. `agents_official/dragapult_sample/` | 🟢 **CAMPEÓN ACTIVO** (en el ladder) | 85% vs first-legal, 95% vs card-data | submission `53940465`, score ~774 (22 jun), 4-1 primeras partidas |
| **Leon v2 (search)** | Leon v1 + ISMCTS sobre la Search API. `agent_ismcts/` | 🧪 **en banco** (activable `FMA_MCTS_ON=1`) | búsqueda con eval estática net-negativa (0/15) → espera eval APRENDIDA | no subido |
| **Leon v3 (BC/IL)** | _En desarrollo:_ eval/policy aprendida (BC/IL desde replays) para enchufar al ISMCTS de v2 | 🟡 arrancado: datos OK + parser validado (`bcil/extract_pairs.py`, 35K pares/día pequeño, formato same_step). Falta encoding + modelo + entreno | — | — |

### 🔮 Sabrina (mazo: Alakazam) — PIVOTE 22 jun NOCHE
| Versión | Qué es | Estado | Local | Ladder |
|---|---|---|---|---|
| **Sabrina v1** | Fork de `ptcg-abc/agents/alakazam` (AlakazamPolicy tuneada, pilotaje VERBATIM) + hardening scaffolding al estándar campeón (fallback repetición-safe, `_validate_obj`, carga no-raising). `agents_official/sabrina_v1/` | 🟡 **CONSTRUIDO, listo para subir** (verificador GO, 0 bloqueantes) | pendiente cabt smoke | no subido |

**Por qué el pivote (resumen):** el mirror Dragapult rule-based está techado (paridad con el sample); Leon v3 (BC/IL) NO-GO. Alakazam tiene headroom de ARQUETIPO (55% WR top-tier; un Alakazam no-psychic llegó 5º del ladder SIN búsqueda). Decidido en sesión paralela (carril selección de mazo). Detalle: `research/pivote-mazo-evaluacion-2026-06-22.md`.

**Honestidad (NO inflar):** la alakazam de ptcg-abc puntuó **~674 en ladder**, por DEBAJO del suelo Dragapult (774-879). Sabrina v1 = **baseline validado del que minar pilotaje**, no un Dragapult-beater day-1. El headroom (674→~1014 del 5º) es trabajo de pilotaje v2 (divergence mining vs el pool Elo≥1150). El kernel del 5º NO está en local (403 al bajar kernels).
- **Variante:** base `alakazam` (go-first), NO `alakazam_mist` (regresó en ladder 907.8<1006.7, descartado por ptcg-abc).
- **Disciplina de slots:** Sabrina en una ranura (crecimiento) + **Leon v1 Dragapult en la otra (suelo verificado, NO quemar)**.
- **Build/submit:** `bash agents_official/sabrina_v1/build_submission.sh` → `submission.tar.gz` (main.py+deck.csv+cg/). Subida = decisión de Fran.

## Registro canónico de los 3 NO-GOs (métodos avanzados)

> Registro de hechos de una línea cada uno (la frase canónica que el report referencia). El 3º (Mega Starmie) deja de ser inferido: queda etiquetado aquí explícitamente.

1. **NO-GO 1 — BC/IL (Leon v3):** greedy BC pierde 14% (21W/129L, N=150) vs el specialist Leon v1; BC+ISMCTS sube a 40% (24W/36L, N=60) pero a full budget empeora a 22% (4W/14L, N=18) → presupuesto descartado como confound. Causa: BC entrenado sobre pilotos elite mayormente no-Dragapult (8.62% juegan Dragapult). Log primario: `bcil/_fullbudget_ab_20260622_1845.log` (solo el N=18). El N=60/N=150 viven en notas (re-corribles con `bcil/ab_json.py`).
2. **NO-GO 2 — ISMCTS con eval estática (prize-based):** pierde 0W/15L vs el sample policy (peor que first-legal); timing OK (~0.4ms/step). La búsqueda va ciega sin eval aprendida. Sin log primario guardado (re-corrible con `FMA_MCTS_ON=1`).
3. **NO-GO 3 — clon Mega Starmie ex (`mega_starmie_v1`):** 87% local vs first-legal pero ladder 641.2 vs keidroid 1358.9 → gap de pilotaje ~700 Elo. Score keidroid primario: `research/extract_keidroid.py`.

## Ramas experimentales (aprendizaje, no compiten)
- **card-data dict-only** (`agent_v2/`): heurística con `cards.json`. Aporta valor (80% vs agente ciego) pero
  NO bate a first-legal en espejo (~22-27%). 📦 archivada como aprendizaje (el card data solo no basta).
- **estructural ciego** (`agent/`): primer scaffolding robusto dict-only, sin conocimiento. Baseline interno.

## Baselines (utillaje del harness, sin nombre)
- `experiments/baselines/firstlegal` (greedy option[0], sorprendentemente fuerte), `experiments/baselines/random`.

## Disciplina de slots (ladder)
5 envíos/día, cuentan los 2 últimos. Mantener SIEMPRE el campeón validado (hoy: Leon v1) como uno de los 2;
promover un candidato solo tras pasar filtro local + A/B contra el panel. Detalle: [[ptcg-ladder-como-subir]].
