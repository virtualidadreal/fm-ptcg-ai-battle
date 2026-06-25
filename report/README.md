# PTCG AI Battle — Report Package

Entry point for the Strategy report and its reproducible evidence base.

## What this is

The competition has two tracks. The **ladder** (Simulation) pays $0; the money and the grade are in the **Strategy report** (8 finalists, weighted **70% methodology / 20% deck concept / 10% quality**). Almost everything that climbs the ladder is public (Kaggle notebooks), so forking the public floor is not an edge. The edge that is not copyable is the **methodology**: a disciplined filter-then-ladder process and three honest, quantified NO-GOs. That is exactly the 70%.

The report is deliberately honest. The advanced methods we tried (BC/IL, ISMCTS) are presented as **ablations with negative results**, not as wins. The NO-GOs are the asset: they are structural, reproducible, and they explain why the top of this ladder is rule-based and simple.

## Files in this folder

| File | Purpose |
|---|---|
| `REPORT.md` | The 2000-word deliverable. Sections 2–5 (the methodology core) are written in full; sections 1, 6, 7 are scaffolded with `[PENDIENTE]` markers. Opens with a per-section word budget. |
| `methodology-evidence.md` | Evidence appendix (outside the word limit). Every methodology claim mapped to its exact figure and the repo file/agent that backs it, with a confidence label and a known-gaps ledger. |
| `README.md` | This file. |

## The three NO-GOs (the report's spine)

1. **BC/IL (Leon v3):** greedy BC loses 14% (21W/129L, N=150); BC+ISMCTS reaches 40% (24W/36L, N=60) but full budget gets *worse* at 22% (4W/14L, N=18), ruling out budget as the confound. Backed by `bcil/_fullbudget_ab_20260622_1845.log`.
2. **ISMCTS + static eval:** 0W/15L vs sample; timing is fine (~0.4ms/step); search goes blind without a learned eval. Backed by `agent_ismcts/`.
3. **Mega Starmie ex clone (`mega_starmie_v1`):** 87% local, laddered at 641.2 vs keidroid's 1358.9 — a ~700-Elo piloting gap. keidroid score backed by `research/extract_keidroid.py`.

## The one methodological insight that shapes everything

**No local proxy predicts the ladder**, triple-confirmed: `cabt` is anti-predictive (Spearman rho = −0.80), agreement-with-top-pilots is blind (+0.3pp vs a 104-point ladder gap), the Track F panel inverts the head (+0.20). The reason is the scoring formula: score = **mu − 3·sigma** measures a ~0.15 tail quantile, while every local proxy measures the mean. So only the ladder judges.

## How to reproduce the ablations

> Detailed runner flags live in the agent folders; this is the map. All commands run from the repo root.
>
> **Prerequisite — Competition Data.** The official card data, daily episodes/replays, the BC dataset and the `cabt` engine binary (`libcg.so`) are **gitignored and not redistributed** (per §2.4 / Pokémon Elements rules). Re-running the game-playing ablations (1–4) first requires fetching the competition data with your own Kaggle token (`kaggle competitions download -c pokemon-tcg-ai-battle`; see `data/DATASET.md`). Step 6 below needs no engine and runs as-is.

1. **BC/IL full-budget NO-GO (22%).** Re-run the paired A/B at full search budget:
   - Runner: `bcil/ab_json.py` (paired, same-seed v_old/v_new).
   - Env: `FMA_WALL_S=2.5` (full budget) vs the reduced 1.2s run.
   - Reference output: `bcil/_fullbudget_ab_20260622_1845.log` (ends `game 18/60: [4W/14L/0D]`).
   - Dataset integrity check: `bcil/dataset/README.md` (99.7% next-step target match vs ~46% same-step).
2. **ISMCTS static-eval NO-GO (0/15).** Agent in `agent_ismcts/`. Default is policy-driven; enable search with `FMA_MCTS_ON=1` to reproduce the static-eval blind-search regression vs the sample policy.
3. **Mega Starmie clone NO-GO (641 vs 1358.9).** Agent `agents_official/mega_starmie_v1/`. keidroid extraction and matchup analysis: `research/extract_keidroid.py`, `research/megastarmie-keidroid-analisis-2026-06-22.md`.
4. **Mulligan math (consistency lever).** Hypergeometric C(52,7)/C(60,7) = 34.64% (8 basics) vs C(48,7)/C(60,7) = 19.06% (12 basics). Encoded in `agents_official/sabrina_cons/main.py` (one variable changed: deck.csv, piloting byte-identical to `sabrina_v1`).
5. **Local-vs-ladder discipline.** The harness opens with a `local != ladder` warning; declare an improvement only if the Wilson CI of the mu difference excludes 0, and never GO below N=60.
6. **No-local-signal correlation (Spearman −0.80).** No engine needed: `.venv/bin/python research/correlation.py` prints `rho = −0.8000` (scipy and the by-hand formula agree) over the four real ladder points. Honest caveat: its inputs are documented constants (the four ladder scores plus the four `cabt`% figures), not re-derived from raw game logs.

## Map to the rest of the repo

- `research/` — methodology evidence base: `top8-roadmap.md` (master plan + TrueSkill formula + ptcg-abc 62%→907 corroboration), `heuristicas-teoria-elite.md` (elite theory + N<60 discipline), `alakazam-top-pilot-analisis-*.md` (deck-out finding), `megastarmie-keidroid-analisis-*.md` + `extract_keidroid.py`, `plan-extraccion-conocimiento-*.md`, `handoff-sabrina-v1-*.md`.
- `agents_official/` — one folder per competing/ablation agent (`sabrina_v1`=826.9 base, `sabrina_v2`=722.5 top-pilot, `sabrina_cons`=mulligan fix, `sabrina_v3`=license-clean ryota re-impl, `mega_starmie_v1`=641.2). Index in `AGENTS.md`.
- `bcil/` — the BC/IL pipeline for NO-GO 1: `extract_pairs.py`, `encode.py`, `model.py`, `train.py`, `ab_json.py`, `PLAN-MODELO-BC.md`, and the full-budget A/B log.
- `agent_ismcts/` — ISMCTS search agent (NO-GO 2).
- `experiments/` — baselines (firstlegal greedy, random) every win-rate claim is measured against.
- `ptcg-abc/` — upstream public reference (the alakazam pilot forked into Sabrina v1), kept for provenance and license traceability.
- `RULES.md` + `COMPETITIONS.md` — scoring/eligibility rules the methodology relies on (mu−3·sigma, 2 active slots, margin-of-victory irrelevant, public = OSI-usable but submission must be own work).
- `NEXT-SESSION.md` + `AGENTS.md` + `BACKLOG.md` — operational handoff, agent registry, backlog — the audit trail of the process, not just the result.
- `data/` + `tools/` — card data, replay extracts, helper tooling needed to re-run any cited number.

## External authorities cited in the report

ryotasueyoshi (rule-based non-psychic Alakazam, ~5th without search), TCGplayer "3 Principles of Prize Checking" (prize-math), JustInBasil (deck roles), Klaczynski (3x world champion, piloting principles). Per the rules, ryota's techniques are re-implemented as own work and cited, never copied verbatim.
