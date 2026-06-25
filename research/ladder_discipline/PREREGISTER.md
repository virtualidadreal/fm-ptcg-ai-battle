# PRE-REGISTRATION PROTOCOL — PTCG ladder KB-lever campaign

> Imported discipline from FMA Quant. Quant ran ~92 hypotheses and **0 alphas survived
> the honest gate**. Its lesson, applied here verbatim: **pre-register FEW hypotheses as
> ONE family, do not fan out, or you burn the deflation.** Every extra try raises the
> `E[max gap]` bar that the winner must clear (see `deflated_elo.py`). This file is the
> contract you sign BEFORE submitting to the ladder.

## Why pre-register (the failure modes it blocks)

1. **HARKing** (Hypothesizing After Results are Known). Looking at converged Elo and then
   inventing the hypothesis that "explains" the winner. The deflation only protects you if
   N is the count of everything you *intended* to try, declared up front.
2. **N-laundering.** Splitting one campaign into "separate" families to shrink each N and
   sneak a winner past a low bar. Counting too few is mathematically identical to lying
   the trial count to the baseline — quant's control test exists precisely to catch it.
3. **Stopping-rule abuse.** Reading the ladder mid-convergence and resubmitting the lucky
   leader. TrueSkill takes days to converge; only `status=converged` rows are trustworthy.

## The protocol (do these IN ORDER, before any Kaggle submission)

1. **Declare the family and the full grid of levers** in this file (a closed list). The
   honest N for *every* member of a closed pre-registered grid is
   `family_trial_count(family) + len(grid)` — selection operates over the whole grid, not
   the execution order (quant adversarial review 2026-06-09, finding D1).
2. **Pick the floor anchor** the gap is measured against (e.g. `sabrina_v1`). The gap is
   `mu_cand - mu_floor`; the deflation needs both converged with their TrueSkill sigmas.
3. **Register each lever** in the ledger as `pre_registered` BEFORE submitting:
   `ladder_ledger.record_experiment(agent=..., family=..., hypothesis=..., floor=...,
   status="pre_registered")`. The ledger is append-only and idempotent.
4. **Submit, wait for convergence (days), then update** the row to `converged` with the
   measured `mu`/`sigma` (`allow_duplicate=True`; N does not inflate — counted by unique
   `(agent, hypothesis)`).
5. **Judge with `deflated_elo`**, passing `n_trials = family_trial_count(family) + k`
   for the closed grid (or `+1` for a single ad-hoc add). A lever is a real edge ONLY if
   `passes=True`. Anything else: not significant. **Fail-closed if N or sigma is unknown.**
6. **Log retired levers too.** A lever you tried and abandoned still spent a trial; it
   stays in the ledger as `retired` and still counts toward N. Deleting it = HARKing.

## What is NOT a ladder verdict

- **The local cabt A/B is anti-predictive of the ladder (Spearman -0.80).** It is a
  regression filter only ("no crashes, not obviously worse"), never a ranking. Do not feed
  local win-rates into `deflated_elo` — it judges LADDER Elo gaps only.
- **The shuffle control (`shuffle_control.py`) is a LOCAL diagnostic of lever inertness,
  not a ladder verdict.** See that file.
- **The public ladder score `mu - 3*sigma` is a TAIL quantile**, recorded for audit. The
  significance test compares the MEANS (`mu_cand` vs `mu_floor`) with the combined sigma.

---

## CURRENT PRE-REGISTERED CAMPAIGN

**Family:** `kb_levers_sabrina_v1`
**Floor anchor:** `sabrina_v1` (its ladder slot; local floor reference ~826.9 mu-3sigma).
**Grid (CLOSED, k = 4 — counted as ONE family, not four campaigns):**

| Agent | Lever (hypothesis) | Local A/B (N=200, NOT a verdict) |
|-------|--------------------|----------------------------------|
| `sabrina_kb_draw` | anti-deck-out / prize-belief (attacks the dominant loss mode) | 54.5% WR, within noise |
| `sabrina_kb_role` | beatdown vs control role selection | 56.0% WR, within noise |
| `sabrina_kb_seq` | play sequencing | 48.5% WR, within noise |
| `sabrina_kb_prizemap` | prize-map (H1b) | 44.0% WR, within noise |

All four Wilson 95% CIs include 0.5 locally (RESULTS-N200-2026-06-24.md): **none qualifies
as a validated local improvement and none regresses.** They are safe to ladder, ranked by
mechanism, not by local WR.

**Honest N for the deflation:** because this is a closed grid of 4 levers over one floor,
the `n_trials` passed to `deflated_elo` for EACH lever is
`family_trial_count("kb_levers_sabrina_v1") + 4`. With an empty ledger that is **N = 4**.
A 4-lever family already lifts the null-max bar measurably — e.g. with `sigma_gap = 3.5`,
`E[max gap] ~= 3.68` Elo, so a lever needs roughly `3.68 + 1.645*3.5 ~= 9.4` Elo of gap
over `sabrina_v1` to clear one-sided 95%. Spraying more levers raises that bar further.

**Stopping rule:** submit the levers, wait for TrueSkill convergence (days), update to
`converged`, then run `deflated_elo`. Do NOT resubmit a mid-convergence leader. Do NOT add
a 5th lever to this family without re-declaring it here (it changes N for everyone).

**Status:** pre-registered, FORWARD-LOOKING. As of writing we have ZERO converged KB-lever
Elo points — this is the discipline for the campaign, not a result.
