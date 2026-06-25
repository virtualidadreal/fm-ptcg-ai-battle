# PTCG AI Battle — Strategy Report

> Repository (full code, logs, reproducible ablations): **https://github.com/virtualidadreal/fm-ptcg-ai-battle**
> All numbers cited inline are backed file-by-file in `report/methodology-evidence.md` (outside the 2000-word limit, per the deliverable rules).

**Target word budget per section (total ~2000):**

| Section | Target words | Status |
|---|---|---|
| 1. Introduction & Problem Framing | 180 | **written** |
| 2. Methodology — Filter-then-Ladder Protocol | 320 | **written** |
| 3. The Seeds Mirage — Why N<60 Is a Hard Gate | 200 | **written** |
| 4. Ablation — Why Advanced Methods Don't Scale (3 NO-GOs) | 480 | **written** |
| 5. No Local Signal Predicts the Ladder | 280 | **written** |
| 6. Deck Concept — Alakazam (Single-Prize) | 400 | **written** |
| 7. Conclusion — What Generalizes & Next Steps | 140 | **written** |

---

## 1. Introduction & Problem Framing

PTCG AI Battle has agents play full Pokémon TCG games on the `cabt` engine; the objective is to ladder high under the official scoring. That scoring drives everything below. The ladder ranks agents by **TrueSkill mu − 3·sigma** (mu0 = 600), so it rewards low-variance reliability, not peak skill. An agent that wins big occasionally but is erratic scores below a duller, steadier one.

Our thesis: the top of the ladder is rule-based and simple, and our edge is not a clever model but a rigorous filter-then-ladder process that refused to ship false positives. The report runs methodology first, then the deck concept, then next steps.

One honesty marker up front: we mark every claim as ladder-verified or local-only. Local results are a filter, never a verdict, and we never present an unconverged ladder run as one.

---

## 2. Methodology — The Filter-then-Ladder Protocol

Every claim in this report hangs on one protocol, and the protocol exists because the engine is adversarial to optimize. We separate the two things people usually conflate. The local A/B harness is a **filter**: cheap, fast, directional. The ladder is the only **judge**. The harness opens with a prominent warning, `local != ladder`, so no result is ever mistaken for a verdict.

The statistical discipline is a set of hard rules, not preferences. We evaluate **paired**: the same seeds drive `v_old` and `v_new` so that seed variance cancels and we measure the difference, not two noisy absolutes. We report **Wilson confidence intervals** on win-rate and track **TrueSkill mu/sigma** on the ladder. We declare an improvement **only if the confidence interval of the mu difference excludes 0**. A point estimate that "looks better" is not an improvement until its interval says so (see `research/top8-roadmap.md`, `bcil/PLAN-MODELO-BC.md`).

Sample size is governed by a rule we earned the hard way: **no GO with N < 60. The first ~20 games lie.** Any N=20 smoke test is labeled **DIRECTIONAL**, never GO. Section 3 shows the exact case that produced this rule (`research/plan-extraccion-conocimiento-2026-06-22.md`, `research/heuristicas-teoria-elite.md`).

Ladder hygiene follows from the scoring formula: **one change per day, one variable at a time.** We keep the validated champion (Sabrina v1, 826.9) in one of the two active submission slots as a floor and A/B baseline, and we never burn all five daily submissions on correlated variants. The day we relaxed this, two weaker agents (v2 = 722.5, mega_starmie = 641.2) displaced the champion and dragged the displayed score down (`research/top8-roadmap.md`).

The same anti-false-positive discipline runs one level up, on the **knowledge** feeding the deck. A two-tier Knowledge OS distilled **12 free sources into 9 computable heuristics** (H1–H9), paid tier scoped but never ingested, via fan-out-then-adversarial-verify: agents propose, a verifier gates. That pass **killed 6 fabrications** before any heuristic was trusted — a fake Flipside citation, "Consistency is the goal" misattributed to Klaczynski, a players-vs-games conflation, a prior that didn't sum to 1, Limitless posing as an "official TPCi partner", and a mis-cited Counter Catcher (`report/knowledge-os-evidence.md`).

This process is the non-copyable edge: the public notebooks are a floor everyone forks; the reproducible process is what the methodology grade rewards. Full reproducibility lives in the linked repo.

---

## 3. The Seeds Mirage — Why N<60 Is a Hard Gate

The N<60 rule is empirical, not dogmatic, and one case proves it. In the Leon v3 A/B (BC prior + ISMCTS vs Leon v1, the Dragapult specialist), the **first ~20 games showed 65%**. Extending the same paired run to **N=60 collapsed it to 40% (24W/36L)**, a 25-point swing produced purely by seed variance (`research/plan-extraccion-conocimiento-2026-06-22.md`, `NEXT-SESSION.md`).

The Wilson tooling makes the same point at the other end of the sample range. The greedy BC policy lost to Leon v1 at **14% (21W/129L, N=150)**, Wilson interval **[9.3%, 20.5%]**. Even at N=150 the interval is wide enough to flag genuine uncertainty (`bcil/`, evidence in `ptcg-leon-v3-bcil` notes).

The derived rule, registered verbatim: **"No GO with N<60; the first 20 games lie (65→40 was real)."**

The same caution applies to the ladder itself. Early scores are sigma-high and misleading. Sabrina v1's provisional 829.4 was read explicitly through the "mirage" lens, not banked. A submission is not judged in its first hours.

This single discipline is the reason a false-positive BC agent never reached the ladder.

---

## 4. Ablation — Why Advanced Methods Don't Scale on This Engine (3 NO-GOs)

These are **ablations, not ladder wins**. The top of the ladder is rule-based and simple, so advanced methods earn their place in this report by explaining *why* they do not help here. We registered exactly three structural NO-GOs.

**NO-GO 1 — Behavioral Cloning / Imitation Learning (Leon v3).** Greedy BC alone loses to the rule-based Dragapult specialist Leon v1 at **14% (21W/129L, N=150, Wilson [9.3–20.5%])**, despite a strong 77% top-1 match offline. Adding ISMCTS on top of the BC prior improves to **40% (24W/36L, N=60)** but never closes the gap. At full search budget (`FMA_WALL_S=2.5`) the directional read is even worse, **22% (4W/14L, N=18)**, below the poor-budget 40%. This points against budget being the confound, but at **N=18 it sits below our own N<60 gate**, so we report it as directional, not a GO-level result (`bcil/_fullbudget_ab_20260622_1845.log`). The structural cause: BC was trained mostly on elite **non-Dragapult** pilots (only **8.62% of Elo≥1150 pilots play Dragapult, 392/4548**), so a general policy pilots the mirror worse than the hand-tuned specialist.

**NO-GO 2 — ISMCTS with static (prize-based) evaluation.** Search with a static prize-count eval goes blind and replaces tuned plays with worse ones, losing **0W/15L vs the sample policy** (worse than first-legal). This is not an implementation or timing artifact: the agent is **policy-driven by default** (~73% parity vs sample), search is gated behind `FMA_MCTS_ON=1`, and the microbench is comfortable (`search_step ~0.4ms`, worst game ~8s against the 600s limit). The structural cause: a PTCG turn is a long chain of the player's own micro-decisions where a static eval barely moves until an attack resolves. With weak priors and no per-node signal, search distributes its budget blindly. This confirms empirically that ISMCTS needs a **learned** eval/policy, which is exactly why the official strong kernel pairs MCTS with a trained Transformer.

**NO-GO 3 — the Mega Starmie ex clone (`mega_starmie_v1`).** A from-scratch policy inspired by keidroid, the ladder #1. It looked strong locally (**87% vs first-legal, brick-rate ~5%**) but laddered at **641.2**, below Sabrina v1 (826.9), Leon v1 (778.2) and even the alakazam baseline (674), and far below keidroid's **1358.9**. The structural cause is a **~700-Elo piloting gap**: "near-deterministic" combat is not enough, and the local `cabt` lied optimistic about setup, sequencing and the three-prize race.

**Honesty caveat (taxonomy).** A separate Phase-1 lesson, "dict-only structural heuristic loses to first-legal at 35% (7W/13L)", is *not* one of these three advanced-method NO-GOs. It belongs to a different finding (all dict-only heuristics without card data lose to first-legal) and we keep the taxonomy clean rather than inflate the count.

Each negative result is structural and reproducible. Turning failures into defensible evidence is this report's strongest contribution.

---

## 5. No Local Signal Predicts the Ladder (Triple-Confirmed)

The ladder scores **mu − 3·sigma**, a tail quantile near the 0.15 percentile. Every local proxy we have measures **mu**, mean skill. A mean cannot track a tail, so no local proxy can predict the ladder. This is not a calibration gap to be tuned away, it is a structural mismatch between what we can measure cheaply and what gets graded. We proved it three independent ways.

**Confirmation #1 (verified).** `cabt`-vs-first-legal is **anti-predictive**: Spearman **rho = −0.80** over four real ladder points (v1 826 > Dragapult 778 > v2 722 > Mega 641), reproducible from `research/correlation.py`. Maximizing `cabt` *lowers* the ladder, so we stopped targeting it.

**Confirmation #2 (verified).** This one shows the mean-vs-quantile gap directly. Agreement-with-top-pilots is blind: replayed faithfully against the engine, **v1 = 21.33% vs v2 = 21.17%** (+0.16pp, noise) while the ladder separates them by **104 points**. v1 and v2 share the same piloting policy, so their means coincide, yet the tail does not. The 104-point gap lives in the card **list**, the exact dimension a mean-based proxy cannot see.

**Confirmation #3 (probable).** The meta-representative panel (Track F) correlates **+0.20 and inverts the head**: ladder-#1 v1 falls to panel-#3, ladder-#3 v2 rises to panel-#1. Useful as a diverse crash-test (0-crash, 0-timeout), useless as a quality judge.

This is the report's most generalizable lesson. The metric is a quantile, the proxies measure a mean, and the two do not meet. So we run **one change per day on the ladder** and treat every local A/B as a filter, never a verdict.

---

## 6. Deck Concept — Alakazam (Single-Prize, Consistency-First)

We pivoted to a pure single-prize Alakazam deck with no EX attacker, a 4-4-3 Alakazam line plus 3 Rare Candy, keyed on Powerful Hand. The pivot followed directly from the Leon v3 BC/IL NO-GO: if the engine punishes clever piloting and rewards reliability, the right move is a consistent single-prize shell, not a glass-cannon. The single-prize choice also has the prize-trade edge baked in at deckbuild time: a 1-prize attacker can never trade down, which is why the A1 net-prize lever fires **0 times** (§7) — nothing left to penalize. That is the H1/H2 prize-trade core of the Knowledge OS resolved structurally, and its `cabt ≠ Standard` caveat (d22 read in-engine as live, Standard only as corroboration) is the knowledge-layer twin of §5's mean-vs-quantile mismatch.

The archetype choice is data-backed. Alakazam is the most-played top-tier deck in the fresh d22 meta (**30.4% share, 58.2% WR, n=395 at Elo≥1150**; an earlier snapshot read 18.9% / 55.1%). Its spread is healthy: par vs Trevenant and Dragapult (49% each), beats Mega Lucario (65%), all from `_meta_d22.log`. Headroom proof: a rule-based non-psychic Alakazam reached ~5th without search (ryotasueyoshi). The ceiling is piloting, not structure.

The biggest lever is consistency. Sabrina v1 runs only **8 basics → 34.64% mulligan** (hypergeometric C(52,7)/C(60,7)), so one opening in three starts down a card on an already-slow Stage-2 line. The `sabrina_cons` fork raises the count to **12 basics (+4 Shaymin 343, −4 tech singletons) → 19.06% mulligan, −15.58pp**. Precedent: LB950 climbed by cutting mulligan with basics 10→12 (25.9% → 19.1%). Shaymin 343, not Fezandipiti ex, is the basic-count fix. Fezandipiti belonged to the v2 top-pilot deck that *worsened* on the ladder (722.5 < 826.9) and is not part of the recommended build. Shaymin was chosen over a generic scorer (Fan Rotom, which clogged the bench) because the pilot already manages it correctly: one variable changed (deck.csv), piloting code byte-identical to v1, 0-crash.

Honest status of the lever: the consistency gain is **mathematically real (hypergeometric)** but its ladder effect is **not yet validated** (A/B #2 live, sigma not converged). Given triple proof that no local proxy predicts the ladder, only the converged ladder will judge it. Same honesty on the top-pilot deck (v2, 11 net changes): it found a real insight (deck-out in 4/5 top-pilot losses, deckCount=0) yet **worsened** on our ladder (722.5 < 826.9).

---

## 7. Conclusion — What Generalizes & Next Steps

Three conclusions are settled and not worth re-litigating. First, only the ladder judges, no local signal predicts it. Second, BC and MCTS are report value, not ladder value: three structural NO-GOs, and the top stays rule-based. Third, the biggest real lever is consistency plus matchup piloting, not search.

A fourth ablation reinforces the discipline. The A1 net-prize-trade lever (penalize exposing a prize-rich active when in rival KO range, the one edge-y idea not even ryotasueyoshi implements) was built and measured. Honest finding: it is **structurally inert for single-prize Alakazam**, the penalty fired 0 times in 49 attack evaluations because our attacker reads as 1-prize. The prize-trade edge is already baked into the deck choice, so there is nothing left to penalize. A clean case of filter-then-ladder preventing a wasted submission slot.

Honest expectations: closing the ~700-Elo piloting gap to the top is hard. The durable contribution is the reproducible methodology and the honest ablations. Full code, logs and reproducibility live in the linked repo, outside the 2000-word limit.
