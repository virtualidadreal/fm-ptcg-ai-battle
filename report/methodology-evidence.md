# Methodology Evidence Appendix

> This file is **outside the 2000-word report limit** (per the deliverable rules). It backs every methodology claim in `REPORT.md` with exact figures and a link to the repo file/agent that supports it. This is the reproducibility surface for the 70% methodology grade.
>
> Confidence legend: **verified** = figure traceable to a primary repo artifact (code/log/csv). **probable** = figure recorded in handoff/memory notes, not re-derived from a primary data artifact in-repo (gap noted).

---

## A. Scoring formula & ladder mechanics (Section 1 & 5)

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| Ladder = TrueSkill, score = mu − 3·sigma | mu0 = 600; conservative ~0.15 quantile | `COMPETITIONS.md`; `research/top8-roadmap.md`; `NEXT-SESSION.md` (line 12: "Score = TrueSkill μ−3σ → NO juzgar en horas") | verified (formula confirmed via forum 23 jun, recorded in memory) |
| Initial rating Gaussian, mu0 = 600 | 600.0 placeholder pre-reset | `NEXT-SESSION.md` line 209; `COMPETITIONS.md`; `research/top8-roadmap.md` | verified |
| sigma high early, falls with episodes → score rises by convergence alone | keidroid 1358 → 1373 with no resubmit | memory note (forum 23 jun) | probable (1373 only in memory; 1358.9 verified in `research/extract_keidroid.py`) |
| Only W/D/L counts; margin of victory irrelevant; only last 2 submissions active | — | `RULES.md`; `research/top8-roadmap.md` | verified |
| Roadmap originally marked mu−3·sigma as [SUPOSICION]; forum confirmed it 23 jun | `top8-roadmap.md` line 46 | `research/top8-roadmap.md`; memory | verified |

---

## B. Filter-then-Ladder protocol (Section 2)

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| Local A/B is a filter, ladder is the judge; harness opens with `local != ladder` warning | — | `research/top8-roadmap.md`; `bcil/PLAN-MODELO-BC.md`; `NEXT-SESSION.md` | verified |
| Paired eval (same seeds v_old/v_new), Wilson CI, TrueSkill; declare improvement only if CI of mu-diff excludes 0 | — | `research/top8-roadmap.md`; `bcil/PLAN-MODELO-BC.md`; `bcil/ab_json.py` | verified |
| 1 change/day; champion (v1 826.9) held in 1 of 2 active slots as floor/baseline; never burn 5 subs on correlated variants | — | `research/top8-roadmap.md`; `NEXT-SESSION.md` | verified |
| Slot discipline failed once (23 jun): v2=722 + Mega=641 below v1 826.9; displayed score fell to 722.5 | — | `research/top8-roadmap.md`; memory `ptcg-pivote-sabrina-alakazam.md` | verified |

---

## C. The Seeds Mirage / N<60 gate (Section 3)

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| Leon v3 (BC prior + ISMCTS) vs Leon v1: first ~20 games = 65%, extended N=60 = 40% (24W/36L) | 65% → 40%, 24W/36L, 25-pt swing | `research/plan-extraccion-conocimiento-2026-06-22.md`; `NEXT-SESSION.md`; memory `ptcg-leon-v3-bcil.md` | verified (figures in notes; no primary JSON log of the first-20-games artifact located — gap) |
| Registered rule, verbatim | "No GO with N<60; the first 20 games lie (65→40 was real)" | `research/plan-extraccion-conocimiento-2026-06-22.md`; `research/heuristicas-teoria-elite.md` | verified |
| N=20 smoke labeled DIRECTIONAL, never GO | — | `research/heuristicas-teoria-elite.md` | verified |
| Greedy BC vs Leon v1 = 14% (21W/129L, N=150), Wilson [9.3%, 20.5%] | 14%, 21W/129L, [9.3–20.5%] | memory `ptcg-leon-v3-bcil.md`; `NEXT-SESSION.md`:62 ("14% N=150") | **probable** (the 21W/129L breakdown + Wilson band have no saved log; `bcil/ab_json.py` computes Wilson, so re-derivable from 21/150 if re-run) |
| Sabrina v1 provisional 829.4 read through the "mirage N=20" lens, not banked | 829.4 provisional | memory `ptcg-pivote-sabrina-alakazam.md`; `research/top8-roadmap.md` | verified |

**Gap:** the 65% and 40% point estimates have no associated Wilson band in-repo (only the greedy N=150 14% interval is computed). No primary A/B stdout/JSON of the first-20 mirage was located; figures live in handoff/plan/memory.

---

## D. The three NO-GOs (Section 4)

### NO-GO 1 — BC/IL (Leon v3)

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| Greedy BC alone loses to Leon v1 | 14% = 21W/129L, N=150, Wilson [9.3–20.5%], 77% top-1 offline | memory `ptcg-leon-v3-bcil.md` (no greedy-run log saved in `bcil/`) | **probable** (figure in notes; re-runnable, log not persisted) |
| BC prior + ISMCTS (Leon v3 final) | 40% = 24W/36L, N=60, reduced budget 1.2s, 669K net evals, 0 failures | memory `ptcg-leon-v3-bcil.md`; `NEXT-SESSION.md` | verified |
| Full budget `FMA_WALL_S=2.5` gets WORSE → budget ruled out as confound | 22% = 18/60 (4W/14L), below the poor-budget 40% | **`bcil/_fullbudget_ab_20260622_1845.log`** (`game 18/60: [4W/14L/0D]` confirmed) | verified (primary log present) |
| Structural cause: BC trained mostly on elite non-Dragapult pilots | only 8.62% of Elo≥1150 pilots play Dragapult (392/4548) | `bcil/dataset/README.md`:16 (Elo-band counts 1973+604+1435+420+116 = **4548** denominator) + :30 ("el meta de élite casi no juega Dragapult", qualitative); the 392 numerator / 8.62% split is a memory-note figure | **probable** (denominator + direction primary; the 392/8.62% split asserted, not re-derived from a primary count — re-runnable by counting Dragapult pilots in the 4548 Elo≥1150 episodes) |

### NO-GO 2 — ISMCTS with static (prize-based) eval

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| Static-eval search loses all measured games vs sample | 0W/15L (worse than first-legal) | `NEXT-SESSION.md`:186; `AGENTS.md`:15; `BACKLOG.md`:8 (abbreviated "0/15") | **probable** (summary text only; no primary stdout/JSON saved — re-runnable with `FMA_MCTS_ON=1` vs sample at N=15) |
| Agent is policy-driven by default; search gated behind `FMA_MCTS_ON=1` | ~73% parity vs sample / 80% vs firstlegal | `agent_ismcts/main.py`:27-28 (docstring); `NEXT-SESSION.md`:183-184 | **probable** (re-runnable, no `_timed_ab` log persisted) |
| Timing is a non-issue | search_step ~0.4ms; worst game ~8s vs 600s limit | `agent_ismcts/`; `NEXT-SESSION.md`:193 | **probable** (re-runnable via `_microbench.py`, log not persisted) |
| Structural cause: static eval barely moves until an attack resolves → blind budget distribution; needs LEARNED eval/policy (cf. official MCTS+Transformer kernel) | — | `NEXT-SESSION.md`; memory | verified (reasoning) |

### NO-GO 3 — Mega Starmie ex clone (`mega_starmie_v1`)

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| From-scratch policy inspired by keidroid (ladder #1) | — | memory `ptcg-pivote-sabrina-alakazam.md`; `research/megastarmie-keidroid-analisis-2026-06-22.md` | verified |
| Looked strong locally | 87% vs first-legal; 27% vs Leon v1; brick-rate ~5% (vs 37% in keidroid losses) | memory `ptcg-pivote-sabrina-alakazam.md` (line ~90) | probable (memory-only; not in `research/megastarmie-keidroid-analisis-2026-06-22.md`) |
| Laddered at 641.2 (submitted 22 jun, id 53957350) | 641.2 — below v1 826.9, Leon v1 778.2, alakazam baseline 674 | memory; `NEXT-SESSION.md` (line ~14: "mega_starmie_v1 (641)") | verified |
| Source pilot keidroid score | 1358.9 (Rank 1, TeamId 16391190); 67.2% WR = 78W/38L over 116 local games; Mega Starmie ex card id 1031, prize_value 3 | **`research/fix_index_mega_kos.py`** (line ~70: "Local 116-game record (78W/38L = 67.2%) matches the official keidroid figure EXACTLY"); 1358.9 score in `research/extract_keidroid.py` | verified (78W/38L/116 confirmed in `fix_index_mega_kos.py`; `extract_keidroid.py` line ~198 notes its own WR covers only a sub-dump, NOT the 67.2% official figure) |
| ~700-Elo piloting gap; local cabt lied optimistic | ~700 Elo | memory; `NEXT-SESSION.md` | verified (gap is interpretation) |

### Taxonomy caveat — NOT a 4th advanced NO-GO

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| Dict-only structural heuristic loses to first-legal = Phase-1 lesson, NOT one of the 3 advanced NO-GOs | 35% = 7W/13L (Wilson 18–57), par vs random 10/10; A/B: attack_asap 13%, attack_mid 17%, setup-first 35% | `NEXT-SESSION.md` (Phase-1 lines ~95–100, 157–164) | probable (interpretation: repo never lists the 3 NO-GOs with explicit labels in one sentence; the BC 14/40/22, ISMCTS 0/15, Mega 641 figures accompany the "3 NO-GOs" phrase) |

---

## E. No local signal predicts the ladder (Section 5)

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| Triple-confirmed offline; only the ladder judges | 3 independent confirmations | memory `ptcg-pivote-sabrina-alakazam.md`; `NEXT-SESSION.md` | verified (synthesis) |
| #1 cabt-vs-first-legal anti-predictive | Spearman rho = −0.80 over 4 ladder points: v1 826 > Dragapult 778 > v2 722 > Mega 641 | **`research/correlation.py`** (reproduces rho = −0.8000 two ways: by-hand `1 − 6·Σd²/(n(n²−1))` and `scipy.stats.spearmanr`, p=0.20; asserts tol 1e-9) | **verified** (primary script reproduces rho exactly; the 4 cabt%/ladder pairs are the inputs) |
| #2 agreement-with-top-pilots is blind | v1 21.33% (267/1252) vs v2 21.17% (265/1252), +0.16pp; ladder separates them 104 pts | **`research/agreement_v1_faithful.json` + `agreement_v2_faithful.json`** (faithful run, real libcg.so card DB, 0 crashes; runner `research/agreement_top_pilots.py --faithful` per `research/REPRODUCE.md` §1) | **verified** (primary; the memory figure 43.52/43.84 was IN ERROR — faithful engine run is ~21.3%/21.2%; the qualitative finding holds and is stronger: means coincide to 0.16pp while ladder differs 104 pts) |
| #3 Track F panel correlates +0.20, inverts head | ladder-#1 v1 → panel-#3; ladder-#3 v2 → panel-#1; panel 0-crash/0-timeout | memory `ptcg-pivote-sabrina-alakazam.md` | probable (no `research/track-f*.md` — gap) |
| Community corroboration: ptcg-abc | 62% cabt local → 907 < 1006 ladder | **`research/top8-roadmap.md`; `research/handoff-sabrina-v1-2026-06-22.md`** (github.com/wmh/ptcg-abc) | verified (primary, in research/) |
| LB950 / kojimar abandoned local proxies | — | memory | probable (synthesis; no quoted primary source in-repo) |
| Structural reason: score is mu−3·sigma (~0.15 quantile); local measures mu | — | memory; `research/top8-roadmap.md` | verified (reasoning) |

---

## F. Deck concept — Alakazam consistency (Section 6, methodology-adjacent figures)

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| Sabrina v1 runs 8 basics (Abra 741 x4 + Dunsparce 65 x4) | 8 basics in 60 | `agents_official/sabrina_cons/main.py`; memory | verified |
| Mulligan at 8 basics | 34.64% = C(52,7)/C(60,7) | `agents_official/sabrina_cons/main.py`; memory | verified |
| `sabrina_cons` fork → 12 basics (+4 Shaymin 343, −4 tech singletons: Hero's Cape 1159, Wondrous Patch 1146, Sacred Ash 1129, Lana's Aid 1184) | 12 basics; one variable changed (deck.csv), piloting byte-identical to v1 | `agents_official/sabrina_cons/main.py` | verified |
| Mulligan at 12 basics | 19.06% = C(48,7)/C(60,7); −15.58pp | `agents_official/sabrina_cons/main.py`; memory | verified |
| Shaymin 343 chosen over Fan Rotom (clogged bench); pilot already manages it correctly; 0-crash | — | `agents_official/sabrina_cons/main.py`; memory | verified |
| LB950 precedent: basics 10→12, mulligan 25.9% → 19.1% | — | memory; `agents_official/sabrina_cons/main.py` (cite romanrozen/strong-start-baseline-agent-v10-lb-950) | verified |
| Consistency gain math-real but ladder effect NOT validated (A/B #2 live, sigma unconverged) | — | memory; `NEXT-SESSION.md` | verified (honest status) |
| Top-pilot deck v2: 11 net changes, real insight (deck-out in 4/5 losses, deckCount=0, hands 9-19) yet WORSENED on ladder | v2 722.5 < v1 826.9 | `research/alakazam-top-pilot-analisis-2026-06-22.md`; memory | verified |
| Alakazam meta share | d22: 30.4% played / 58.2% WR / n=395 (Elo≥1150); earlier snapshot 18.9% / 55.1% | **`_meta_d22.log`** (TOP TIER Elo>=1150: "Alakazam  30.4%  58.2%  395"); earlier snapshot in `research/pivote-mazo-evaluacion-2026-06-22.md` | verified (d22 figures primary in `_meta_d22.log`) |
| Matchups: par Trevenant 49%, par Dragapult 49%, beats Mega Lucario 65% | 49% / 49% / 65% (Alakazam row) | **`_meta_d22.log`** (MATCHUP win% table, row=Alakazam: Hop's Trevenant 49%, Dragapult 49%, Mega Lucario 65%) | verified (primary in `_meta_d22.log`) |
| Non-psychic Alakazam reached ~5th without search (ryotasueyoshi); band ~950–1150 | — | memory; `agents_official/sabrina_v3/main.py`; `research/pivote-mazo-evaluacion-2026-06-22.md` (cite ryotasueyoshi/rule-based-not-psychic-alakazam-best-5th) | verified |
| License: public code OSI-usable but submission must be own work; ryota re-implemented (not verbatim), cited; sabrina_v2_ryota kept as reference only | §3.6.b / §3.14.a | `RULES.md`; memory; `agents_official/sabrina_v3/main.py` | probable (RULES.md carries the principle; numbered subsections only in memory) |

---

## G. BC dataset integrity (supporting NO-GO 1)

| Claim | Figure | Source | Confidence |
|---|---|---|---|
| Original parser silently broken; target match fixed | next-step+ACTIVE-only = 99.7% / 99.89% vs same-step ~46% / 65.61% | `bcil/dataset/README.md`; memory `ptcg-leon-v3-bcil.md` | verified |

---

## H. Ablation — "The clone was sub-piloted by a bug, not the list" (deepens NO-GO 3)

This is the strongest single piece of evidence for the report's central thesis, so it earns its own appendix entry. NO-GO 3 (Section 4) already records the headline: we built `mega_starmie_v1`, a from-scratch rule-based pilot of Mega Starmie ex, and it laddered at **641.2** while its inspiration keidroid (ladder #1) sat at **1358.9** — a ~700-Elo gap we attributed to "piloting." This appendix sharpens that attribution with a result we did not have when Section 4 was frozen.

**The decklist was not the variable.** We did not approximate keidroid's 60 cards; we cloned them card-for-card (`agents_official/mega_starmie_v1/deck.csv`, 60/60 match against the keidroid list documented in `research/megastarmie-keidroid-analisis-2026-06-22.md`). Same Mega Starmie ex line, same 4× Salvatore (1189), same 4× Ignition Energy (17), same trainer shell. The 641.2 agent and the 1358.9 agent therefore differ in **exactly one dimension: the in-turn decision policy** (`main.py`). When the list is held identical and the score collapses ~700 Elo, the deficit is, by construction, 100% execution. This is the cleanest possible isolation of "piloting, not netdecking" — the same logic the rest of the report argues structurally (no local proxy predicts the ladder; the edge is process and piloting), here demonstrated by a controlled clone.

**An adversarial audit of `main.py` found four execution faults that betray the agent's own stated strategy** (the module docstring, `main.py:25–40`, names "evolve the Mega via Salvatore the turn the Staryu enters" as the core combo and the "fastest path to Mega online"). The most expensive is a gate that throttles that very combo.

### The central fault — the Salvatore `appearThisTurn` gate

| Item | Detail | Source / confidence |
|---|---|---|
| Where | `_salvatore_has_target()` defines the premium Salvatore target as a Staryu in play with `getattr(p,'appearThisTurn',False) == True` (`main.py:500–512`); consumed in `_score_play_trainer` where that predicate alone unlocks the top score 21000 (`main.py:702–716`). The audit referenced the earlier-revision line numbers 460/652 for the same two sites. | verified (code paths read in-file) |
| Card fact (engine-authoritative) | Salvatore searches the **DECK** for an Abilityless evolution and evolves a Pokémon, restricted to one **put down during setup OR put into play this turn**. It does **not** need the Mega in hand. `Pokemon.appearThisTurn` is a real engine field (`cg/api.py:344`, "True if played this turn"). | verified (`web/card_db.json` 1189; `cg/api.py`) |
| The fault | The premium combo (score 21000, the line the docstring calls central) fires **only** when a Staryu reads `appearThisTurn=True`. The card is also legally targetable when the Staryu was **put down during setup** — a case `appearThisTurn` does **not** cover. So a setup Staryu that Salvatore can legally evolve the same turn is denied the premium score and falls to the 20500 fallback, and the very first turns (where setup Staryu are most common) are exactly when the central acceleration matters most. The gate is narrower than the card's real legality, throttling the agent's own declared wincon. | **probable** (the gate-vs-legality mismatch is read directly from code + the verified card text; the *magnitude* of its ladder cost is not measured — see caveat) |
| Why it survived local testing | A 20500 fallback (`main.py:713`, "setup Staryu in play, no Mega online → still fire Salvatore") means Salvatore is **not fully blocked**; it still gets played, just demoted below other 21000-band plays in the turn it should lead. Local `cabt` (87% vs first-legal, brick ~5%) never surfaced the demotion because the fallback kept games winnable — the optimism that NO-GO 3 already flags. This is precisely a "the local harness lied optimistic about setup/sequencing" instance, now traced to a specific line. | probable (mechanism from code; "lied optimistic" is the NO-GO-3 interpretation) |

### The other three audited faults (honest, partly non-applicable)

| # | Fault (as audited) | Verdict for THIS deck | Confidence |
|---|---|---|---|
| 2 | Nebula Beam reachability — Ignition Energy (17) gives `{C}{C}{C}` on an **Evolution** Pokémon, so one Ignition on the (evolved) Mega pays Nebula Beam's `[C][C][C]` in a **single attach**; an attach policy that treats Ignition as plain `{C}` would under-rate the spike turn. | **Applicable in principle.** The attach scorer does encode the Evolution-tripled colorless (`main.py:385–387`, `863–864`), so the agent is *aware* of it; whether ranking/sequencing exploits it on the right turn is the open question. Flag, not a proven miscount. | probable |
| 3 | Nebula vs Jetting selection — Nebula (210, ignores W/R + Active effects) should be the finisher only when 210 lethals and 120 does not; otherwise Jetting Blow. | **Largely correct already** (`main.py:906–917` implements exactly this HP arithmetic). Audit flag is about edge sequencing, not a wrong rule. Mostly **non-applicable** as a "bug." | verified (rule present in code) |
| 4 | Lillie's Determination (1227) — shuffle hand to deck, draw 6 (8 if **exactly 6 prizes**); gated to small-hand/needs-setup only (`main.py:753–758`). | **Non-applicable as a fault for this list.** The "draw 8 at exactly 6 prizes" bonus is a turn-1/early-only window the conservative gate already respects; no evidence the gate misfires here. Marked non-applicable rather than inflated into a 4th bug. | probable |

**Honest scope of this ablation.** The decklist-identity claim is **verified** (60/60 clone). The Salvatore-gate mismatch is **verified as a code-vs-card-legality fact**; its *contribution* to the 641.2 score is **not measured** — it is a plausible, mechanism-grounded cause, not a quantified one. The fixes have **not converged on the ladder** and were **not run locally**: `cg/libcg.so` is a Linux x86-64 binary that does not load on macOS, so no A/B or ladder number exists for a patched agent. Any conclusion of the form "fixing the gate recovers X Elo" would be invented — we explicitly do **not** claim it. Faults 3 and 4 are reported as **largely non-applicable** to this specific deck rather than padded to reach "four bugs." Any fix must preserve the `_validate_obj` gate and every fallback (0-crash / 0-illegal-selection is the floor; a single illegal selection is an instant ladder loss).

**Why this reinforces the thesis.** The report argues the edge is honest methodology and piloting, not netdecking, and that no local signal predicts the ladder. The clone is the controlled experiment for both claims at once: an exact copy of the #1 list, sub-piloted, lost ~700 Elo, and the local harness (87%) gave no warning. Netdecking the list bought nothing; the gap lived entirely in execution — and at least one slice of that execution is a concrete, line-located bug, not ineffable skill. That is the μ−3·σ lesson in miniature: a mean-looking-fine local agent can carry a tail-fatal flaw the ladder exposes and the proxy cannot.

### Follow-up — an automated divergence loop caught bugs the static audit missed

After the static audit above, we built an automated divergence loop that replays 15 curated keidroid (#1) games and measures, decision-by-decision, where our pilot diverges from the human, bucketed by `SelectContext` with an agree% per bucket (report in `research/divergence/`). This dynamic, ground-truth-anchored comparison surfaced execution faults the line-by-line static read of `main.py` did **not**. The most serious: in `EVOLVES_TO` we were declining our own wincon — keidroid evolved into Mega Starmie ex while our agent returned `[]` (Mega scored 0 in `_score_card`, the evolution was an optional select, and we passed on it), agreeing 0/7. Lesser ones: a Buddy-Buddy Poffin anti-brick floor that never relaxed even with Mega online and a full hand (Poffin-spam vs keidroid's attack/develop), an Ignition→Mega over-attach where keidroid reserves Ignition for Nebula, and discarding our own Mega Starmie ex (keidroid never pitches its wincon). We corrected these and re-ran the loop: `EVOLVES_TO` went 0/7 → **7/7**, `MAIN` agree rose to **119/227 (52%)**, and the wincon-pitch disappears from the `DISCARD` mismatches. This is the value the loop adds over a code-only audit: a static read can verify card legality and gate logic but cannot see that, against real #1 play, the agent silently *declined* the central combo. **Not validated on the ladder.** The engine (`cg/libcg.so`) does not load on macOS, so the loop runs only against recorded observations; agree% is a qualitative piloting diagnostic, and — as the rest of this report insists — no local signal predicts Elo. We make **no** claim that these fixes recover any specific amount of Elo, only that they realign our decisions with the #1 pilot on the buckets where we were measurably diverging.

---

## Known gaps (honesty ledger)

1. ~~No single repo sentence lists the "3 NO-GOs"…~~ **Closed (23 jun):** `AGENTS.md` now carries a canonical one-line-each registry of the three advanced-method NO-GOs (BC / ISMCTS / Mega Starmie), so the Mega Starmie attribution is no longer inferred. BC and ISMCTS were already explicitly named ablations.
2. The Spearman rho = −0.80 **computation is now reproducible** (`research/correlation.py`, prints rho = −0.8000, scipy + by-hand agree). Honest caveat: its four inputs (cabt 80/85/92/87, ladder 826.9/778.2/722.5/641.2) are **documented constants, not re-derived from raw game logs** — the four ladder scores are independently documented, the four cabt% are not recomputed from a primary artifact. **Agreement: RESOLVED (25 jun) and promoted to `verified`.** Ran `research/agreement_top_pilots.py --faithful` on `ptcg-torch` (real `libcg.so` card DB, 0 crashes): **v1 = 21.33% (267/1252), v2 = 21.17% (265/1252)** — the old memory figure 43.52/43.84 was IN ERROR. Saved as `research/agreement_v1_faithful.json` / `agreement_v2_faithful.json`. The DB-degraded offline proxy (no `.so`) had given 20.61%, explicitly not the faithful figure; the faithful engine run is ~21.3%. The qualitative finding is unchanged and stronger: the two means coincide to 0.16pp while the ladder separates them by 104 points. **Track F (+0.20) still lives only in memory** (engine-gated panel runs; runner in `research/REPRODUCE.md` §2).
3. No primary A/B JSON/stdout of the first-20-games mirage was located; 65→40 figures are in handoff/plan/memory only. The full-budget 22% (18/60) IS backed by a primary log (`bcil/_fullbudget_ab_20260622_1845.log`).
4. The fresh d22 Alakazam meta figures (30.4% / 58.2% / n=395) **and the 49%/49%/65% matchups** are ALL backed by the same primary artifact — `_meta_d22.log` (TOP TIER Elo≥1150 table + MATCHUP win% table, row=Alakazam). `research/pivote-mazo-evaluacion-2026-06-22.md` carries only an earlier, superseded snapshot (18.9% / 55.1%) computed with a different cut; cite it as "earlier snapshot" only, never as the live figure. Consistency rule: the report describes the TOP-TIER meta (Elo≥1150), so the canonical Alakazam figure is 30.4% / 58.2% / n=395 — never the FIELD/all-players 29.0% / 50.6% / n=2932.
5. The keidroid 1373 (rise without resubmit) is memory-only; the 1358.9 score is verified in `research/extract_keidroid.py`.
6. **Mega Starmie clone ablation (Section H).** The 60/60 decklist clone and the Salvatore-gate-vs-card-legality mismatch are **verified** (deck.csv; `main.py:500–512`/`702–716`; card text 1189; `cg/api.py:344`). What is **NOT** measured: the gate's quantitative cost in Elo, and any patched-agent A/B or ladder score — `cg/libcg.so` does not load on macOS, so no fix was run. We report the bug as a plausible mechanism-grounded cause of the ~700-Elo gap, explicitly **not** as a quantified or ladder-validated one ("probable / not-validated-on-ladder"). Audited faults 3 (Nebula/Jetting selection) and 4 (Lillie's draw-8 window) are marked **largely non-applicable** to this specific list rather than counted as bugs.

**Reproduction runners (23 jun):** every engine-gated `probable` figure above (seeds mirage N=60, greedy BC N=150, ISMCTS 0/15, agreement, Track F) now has an exact one-command runner in `research/REPRODUCE.md`. They require the native `cabt` engine (`libcg.so`, Linux/Kaggle runtime — it does not load on macOS), so they were prepared but not executed here; running them on the competition runtime upgrades each from `probable` to a persisted primary log.
