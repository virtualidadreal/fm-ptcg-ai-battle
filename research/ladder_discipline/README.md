# ladder_discipline — anti-overfitting for the PTCG Kaggle ladder

A forward-looking discipline that imports FMA Quant's anti-overfitting machinery so the
upcoming KB-lever campaign on the ladder does not degenerate into multiple-testing
self-deception. We are about to throw 4+ KB levers at the ladder — textbook
multiple-testing — and the deflation must bite BEFORE we spray submissions.

## The insight being imported

PTCG agent development and quant strategy development are the **same problem**:

- a **cheap, NON-PREDICTIVE local signal** (cabt A/B win-rate, Spearman **-0.80** vs the
  ladder — anti-predictive) you can run cheaply but must NOT trust as a ranking, and
- an **expensive, TRUE judge** (ladder Elo = TrueSkill `mu - 3*sigma`, converges in days)
  you can only sample a handful of times.

Quant ran ~92 hypotheses and **0 alphas survived its honest gate**. Its crown jewel is
**family-wise deflation**: trying N candidates inflates the best one's apparent edge, so
the Deflated Sharpe deflates the winner by `E[max of N draws under the null]`. We port
that **logic** (not the code, not "Sharpe") onto the **Elo gap**.

## The quant -> PTCG mapping

| quant statistic | PTCG analog (this module) |
|-----------------|----------------------------|
| `SR_hat` (per-period Sharpe) | Elo gap `g = mu_cand - mu_floor` |
| `V[SR_k]` (variance of the N trial Sharpes) | `sigma_gap^2 = sigma_cand^2 + sigma_floor^2` (per-experiment gap variance under the null) |
| `N` trials | family-wise count of **ladder** experiments (the KB family) |
| `E[max SR_k]` | `expected_max_gap_under_null` = expected max of N null gaps |
| `SR*` (deflated threshold) | the same `E[max gap]`: the gap a NULL candidate beats just by being best-of-N |
| DSR / PSR significance | `deflated_z = (g - E[max gap]) / sigma_gap`, passes if `>= margin_z` |
| `ledger.family_trial_count` | `ladder_ledger.family_trial_count` (accumulated N per family) |
| AND-gate, fail-closed | `deflated_elo` fail-closed; the AND-gate analog is `deflated_elo` (ladder judge) AND the shuffle control (local prune) |
| control_test (deliberate overfit must be rejected) | `shuffle_control` (same-magnitude nudge on random targets) |

## The deflation math

Direct port of quant's expected-maximum-of-N under the null (Bailey & Lopez de Prado
2014, A.1), with the variance `V` reinterpreted as the per-experiment **gap** variance:

```
E[max gap | null, N] = sigma_gap * ( (1 - gamma) * Phi^-1[1 - 1/N]
                                     + gamma     * Phi^-1[1 - 1/(N*e)] )
```

- `gamma` = Euler-Mascheroni (0.5772156649), `e` = Euler's number, `Phi^-1` = inverse
  normal CDF (`scipy.stats.norm.ppf`). Note `N*e`, not `N/e` (same as quant).
- `sigma_gap = sqrt(sigma_cand^2 + sigma_floor^2)` (independent TrueSkill posteriors).
- A candidate passes only if `deflated_z = (g - E[max gap]) / sigma_gap >= margin_z`
  (default 1.645, one-sided 95%).
- **Monotone:** `E[max gap]` is non-decreasing in N — more tries raise the bar.

## Files

- `deflated_elo.py` — the core. `deflated_elo(...)` returns
  `{gap, sigma_gap, expected_max_gap_under_null, deflated_z, passes, n_trials, ...}`.
  Fail-closed on bad N / sigma / gap. CLI: `python deflated_elo.py --gap 14 --sigma-gap 3.5 --n-trials 4`.
- `ladder_ledger.py` — append-only TSV of every ladder experiment + `family_trial_count(family)`.
  Idempotent (counts unique `(agent, hypothesis)`, never double-counts a re-run/update).
  CLI: `python ladder_ledger.py --count --family kb_levers_sabrina_v1`.
- `PREREGISTER.md` — the pre-registration protocol + the current pre-registered KB-lever
  campaign (`kb_draw`/`kb_role`/`kb_seq`/`kb_prizemap` as ONE family over `sabrina_v1`).
- `shuffle_control.py` — design + seed-stable helpers for the shuffled-nudge control (a
  LOCAL inertness diagnostic, not a ladder verdict). Describes the Docker run command; does
  not run it.
- `tests/test_deflated_elo.py` — pure-python pytest (15 tests). Run:
  `/Users/franmilla/FMA/proyectos/ptcg-ai-battle/.venv/bin/python -m pytest research/ladder_discipline/tests -q`.

## Honest caveats (read these)

1. **Forward-looking, not a result.** We have only a handful of converged ladder Elo
   points and **ZERO laddered KB levers**. This is the discipline for the campaign, not a
   retrospective edge claim.
2. **Local cabt is anti-predictive** (Spearman -0.80). Any LOCAL control (the shuffle
   control) is a LOCAL diagnostic of lever inertness, **never a ladder verdict**. Do not
   feed local win-rates into `deflated_elo` — it judges ladder Elo gaps only.
3. **Sparse Elo data.** TrueSkill needs days to converge; only `status=converged` rows
   carry trustworthy `mu`/`sigma`. Only the last 2 submissions are active on the ladder.
4. **The ladder score `mu - 3*sigma` is a TAIL quantile**, recorded for audit. The
   significance test compares the **MEANS** (`mu_cand` vs `mu_floor`) with the combined
   sigma — do not confuse the conservative public score with the gap test.
5. **Counting too few inflates significance.** Every lever you try (including retired
   ones) counts toward N. Pre-register the family; do not fan out; do not HARK.
6. **Offline & deterministic by rule.** Pure python + scipy. No Docker, no Kaggle
   submissions, no file deletion.

## Adversarial verification + fixes (25 jun 2026)

Built with ultracode + Dev Aumentado, then verified by a 3-lens adversarial panel
(math/stats, honesty/overclaim, completeness critic). No NO-GO; math GO, honesty/critic
GO-WITH-RESIDUALS. **The completeness critic earned its keep**: it caught the first build
re-introducing the exact **V-fallback under-deflation bug** that the FMA Quant system
itself had to discover and fix on 2026-06-15 (`quant/research/rejudge_portfolio_gate.py`
`familial_V`, `reexamine_atr_pass.py`). The same lesson, caught the same way (a single
skeptical critic), in a second independent domain — the strongest possible evidence the
methodology transfers.

**CRITICAL FIX APPLIED.** `deflated_elo` no longer scales `E[max of N]` by the
within-estimate `sigma_gap`. It now requires `between_gap_std = grid_dispersion(gaps)`
(the dispersion of the N realized family gaps = quant's `grid_sharpe_var` analog) for
N>=2, and **fail-closes if it is missing** (no silent under-deflation). An
`illustrative=True` escape uses `sigma_gap` as a placeholder but stamps the result
`scale_is_fallback=True` / NOT trustworthy. `between_gap_std` is computable only AFTER the
family converges. 21 tests pass (was 15) including the V-fallback guard, the illustrative
flag, `grid_dispersion`, and the tail-gap.

**Major residual now in code:** the ladder ranks `mu - 3*sigma` (a tail) while the gate
tests the mean. Mode A now also reports `tail_gap` and `tail_gap_positive` — a mean-gap
PASS is **necessary, not sufficient**; the caller must also confirm the tail gap clears.

**Tracked residuals (guardrails, lower urgency, do before the campaign judges a winner):**
- **Family-laundering is not machine-guarded.** `family_trial_count` keys on a free-text
  family string; calling each lever its own family yields N=1 each and the deflation
  evaporates. Honor-system in `PREREGISTER.md` for now; add a closed-family registry +
  a consistency check before judging.
- **Ledger dedup keys on `(agent, hypothesis)` prose.** A reworded hypothesis inflates N
  (safe), but reusing an agent name across genuinely different attempts could collapse two
  trials into one (unsafe). Consider hashing a canonical lever descriptor (quant did).
- **`PREREGISTER.md` worked example used `sigma_gap=3.5`** vs the realistic converged
  `sigma~0.8` (`sigma_gap~1.13`); treat that number as a deliberately conservative
  placeholder, not the campaign's real bar.
