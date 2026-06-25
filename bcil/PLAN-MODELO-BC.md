# Plan: modelo BC/IL (Leon v3) — instrucciones para montarlo en otra sesión

> Objetivo: una policy/value net APRENDIDA (Behavioral Cloning desde replays de pilotos top) que (a) como
> policy greedy ya bata a Leon v1, y (b) sirva de evaluación/prior del ISMCTS de Leon v2 (lo que lo vuelve
> rentable — Fase 2 probó que sin eval aprendida la búsqueda va ciega). Es el método del 70% del report.

## Estado al arrancar (YA hecho, 22 jun)
- ✅ Datos confirmados y descargables: `kaggle datasets download kaggle/pokemon-tcg-ai-battle-episodes-YYYY-MM-DD`
  (~750MB/día, 5-7,8k partidas; manifest en `data/episodes_index/manifest.csv` con top/median score por día).
- ✅ Parser obs→acción validado: `bcil/extract_pairs.py` (streaming del zip, formato **same_step**, 35K pares
  del día pequeño). Hoy filtra por "ganador"; hay que refinar a "pilotos Elo alto".
- ✅ Binding de búsqueda + ISMCTS listos en `agent_ismcts/` (Leon v2, activable `FMA_MCTS_ON=1`), esperando esta eval.
- ✅ `cg/api.py` oficial da `all_card_data()`, `to_observation_class()`, y el motor corre offline en Docker (`ptcg-cabt`).

## Recurso CLAVE a reutilizar
Notebook oficial `data/official_kernels/mcts_rl/...mcts...ipynb`: trae **`get_encoder_input(obs, your_deck)`** y
**`get_decoder_input(obs, actions)`** (codifican estado y acciones candidatas a `SparseVector`), `eval_nn`, el
modelo Transformer, y `mcts_agent`. REUSAR su encoding (probado) como punto de partida; no reinventarlo.

## Fases

### Fase A — Dataset de calidad
1. Descargar días de alto nivel (top_avg_score alto): 18, 19, 20, 21 jun (~750MB c/u).
2. **Filtrar por Elo:** `kaggle competitions leaderboard pokemon-tcg-ai-battle --download` → CSV nombre→score.
   En `extract_pairs.py`, mapear `info.Agents`/`TeamNames` → Elo y quedarse con pilotos **Elo ≥ ~1150** (aprender de
   los buenos, ganen o pierdan — no solo del ganador). Considerar aprender solo del mazo Dragapult al principio
   (coherencia con Leon), o de todos para generalizar.
3. Salida: dataset de pares `(obs, action_elegida)` + el `your_deck` de ese piloto (lo necesita el encoder).

### Fase B — Encoding + modelo (ligero, inferencia CPU)
1. Copiar las funciones de encoding del notebook (`SparseVector`, `get_encoder_input`, `get_decoder_input`,
   `add_*`) a `bcil/encode.py`. Para cada par: encoder_input(obs, your_deck) + decoder_input(obs, candidate_actions),
   target = índice de la combinación que eligió el experto (el notebook genera hasta 64 combinaciones por maxCount).
2. Modelo: **empezar simple** (MLP o Transformer PEQUEÑO, mucho menor que el del notebook). torch SÍ está en el
   runtime de submission (el sample MCTS lo usa). Entrenar OFFLINE (sin límite de compute); solo la INFERENCIA debe
   ser rápida (CPU, presupuesto 600s/partida).
3. Pérdida: BC = cross-entropy sobre la acción del experto (policy). Opcional value head (predecir el resultado
   de la partida desde el estado) para alimentar el ISMCTS.

### Fase C — Integración y dos modos
1. **Modo policy greedy (validar BC primero):** agente que codifica el estado, puntúa las acciones candidatas con
   la net y elige el argmax. Empaquetar como `agents_official/leon_v3_bc/` (main.py + deck.csv + cg/ + pesos).
   A/B vs Leon v1 (sample) + panel. **Hito:** ¿la policy sola ya bate a Leon v1?
2. **Modo ISMCTS+net (Leon v3 final):** en `agent_ismcts/`, reemplazar la eval estática de `_create_node` por la
   net (value + policy prior), como hace el `eval_nn` del notebook. A/B vs Leon v1 y vs modo greedy.

### Fase D — Validación honesta y submit
- Medir contra el **panel de oponentes** (tarea #8), no solo espejo (el local engaña, §6). Wilson + TrueSkill.
- Verificar inferencia CPU dentro de presupuesto (microbench como en Fase 2). Empaquetar pesos en el tar.
- Si supera a Leon v1 con disciplina de slots → subir como Leon v3 (mantener Leon v1 como el otro slot).

## Decisiones recomendadas (para no re-deliberar)
- Encoding: reusar el del notebook (probado) antes que inventar uno compacto. Simplificar solo si la inferencia es lenta.
- Empezar por **policy greedy** (rápida de validar) antes que el ISMCTS+net (objetivo final).
- torch en el tar: OK (está en el runtime); empaquetar `state_dict`, inferencia CPU.

## Gotchas / riesgos
- Multi-select (maxCount>1): el target es una COMBINACIÓN de índices; usar la generación de combinaciones del notebook.
- Robustez: el agente final SIEMPRE con try/except global + fallback a Leon v1 policy / first-legal (nunca crashear).
- `agent` debe ser la ÚLTIMA función top-level del main.py (get_last_callable).
- No extraer los zips (~21GB); streaming con zipfile.
- Tamaño del encoder del notebook (~22000 vocab): si el modelo/inferencia pesa demasiado, recortar el vocabulario.

## Criterio de éxito
Leon v3 (greedy o ISMCTS+net) **supera a Leon v1 en el panel de oponentes** con significancia, dentro de presupuesto
de tiempo y sin crashes → candidato a subir al ladder.

## Instrucción de arranque (pegar en la otra sesión)
> "Monta el modelo BC/IL (Leon v3). Lee `bcil/PLAN-MODELO-BC.md` y `AGENTS.md`. Empieza por la Fase A (dataset de
> calidad: descargar días 18-21, filtrar Elo≥1150 en `bcil/extract_pairs.py`) y enséñame stats antes de entrenar.
> Reusa el encoding del notebook oficial de MCTS. Valida primero la policy greedy vs Leon v1 + panel. No subas nada
> sin que supere a Leon v1. Docker `ptcg-cabt` para validar; el motor y `cg/` ya están."
