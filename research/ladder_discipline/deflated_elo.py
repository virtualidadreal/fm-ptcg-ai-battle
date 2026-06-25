#!/usr/bin/env python3
"""
deflated_elo.py — PTCG LADDER-DISCIPLINE (anti-overfitting for the Kaggle ladder).

WHAT THIS IS (and is NOT)
-------------------------
A FORWARD-LOOKING discipline for the upcoming KB-lever campaign on the ladder. It
ports the CONCEPT of FMA Quant's Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014)
to the ladder problem. There is NO Sharpe, NO returns, NO Kaggle submission here. We
port the LOGIC (expected-max-of-N deflation under the null, normal margin, fail-closed,
monotone-in-N), NOT the quant code.

WE DO NOT HAVE A RETROSPECTIVE ALPHA CLAIM. We have a handful of converged ladder Elo
points and ZERO laddered KB levers yet. This module exists to deflate Elo gaps BEFORE we
spray submissions, exactly as quant deflated Sharpe BEFORE it declared an alpha (and 0 of
~92 hypotheses survived its honest gate).

THE QUANT -> PTCG MAPPING
-------------------------
  quant statistic           PTCG analog
  ----------------          ----------------------------------------------------
  SR_hat (per-period)       Elo gap  g = mu_cand - mu_floor
  V[SR_k] (variance of      grid V = var of the N realized family gaps (BETWEEN
    the N trial Sharpes)      candidates) -> scale = sqrt(V)  [see CRITICAL note]
  N trials                  family-wise count of ladder experiments (the KB family)
  E[max SR_k]               expected_max_gap_under_null = expected max of N null gaps
  SR* (deflated threshold)  the same E[max gap]: the gap a NULL candidate would beat
                              just by being the best of N tries
  DSR / PSR significance    deflated_z = (g - E[max gap]) / sigma_gap ; passes if z>margin

CRITICAL: WHICH VARIANCE FEEDS E[max] (the V-fallback bug, imported lesson)
--------------------------------------------------------------------------
The E[max of N] formula needs V = the dispersion of the statistic ACROSS the N
candidates (quant's grid_sharpe_var = np.var(sharpes_across_configs, ddof=1)). It is
NOT the within-estimate posterior variance of ONE gap (sigma_cand^2 + sigma_floor^2).
Quant discovered this the hard way: its own gate used the sampling fallback
(1+SR^2/2)/(T-1) which SHRINKS with T and UNDER-deflates (re-judge 2026-06-15,
quant/research/rejudge_portfolio_gate.py:familial_V, reexamine_atr_pass.py). The PTCG
completeness critic caught the first version of THIS module re-introducing exactly that
bug (it scaled E[max] by sigma_gap). FIX: the scale of E[max] is `between_gap_std` =
sqrt(var of the N realized family gaps), supplied by the caller (computable only AFTER
the N levers converge). The within-estimate `sigma_gap` is used ONLY for the final
normalization deflated_z = (g - E[max]) / sigma_gap, not for the bar.

FAIL-CLOSED on the V (HARD RULE)
--------------------------------
For N >= 2 we REFUSE to substitute sigma_gap for the between-candidate dispersion
(that is the under-deflation bug). If `between_gap_std` is not supplied:
  - default: valid=False, passes=False (you cannot compute an honest bar yet).
  - illustrative=True: we use sigma_gap as a placeholder scale, set
    scale_is_fallback=True and stamp the reason LOUDLY as NOT trustworthy.
At N == 1 there is no selection, so the scale is irrelevant (E[max]=0) and the raw gap
must still clear the margin (no free pass).

THE MATH (ported faithfully from deflated_sharpe.expected_max_sharpe)
---------------------------------------------------------------------
    E[max gap] ~= scale * ( (1 - gamma) * Phi^-1[1 - 1/N]
                            + gamma     * Phi^-1[1 - 1/(N*e)] )
with gamma = Euler-Mascheroni, e = Euler's number, Phi^-1 = inverse normal CDF (ppf),
scale = sqrt(between-candidate V). RISES with N (more tries -> luckier best). Significance:
    deflated_z = (g - E[max gap]) / sigma_gap ; passes = deflated_z >= MARGIN_Z (1.645).

OTHER FAIL-CLOSED: non-int/N<1, sigma_gap<=0/non-finite, gap non-finite => NOT significant.
MONOTONE: expected_max_gap_under_null is non-decreasing in N (more trials -> higher bar).

TAIL vs MEAN (necessary-not-sufficient): the public ladder score is mu - 3*sigma (a TAIL
quantile). This test compares the MEANS with sigma_gap. A mean-gap PASS is NECESSARY, NOT
SUFFICIENT: a candidate with higher mu but higher sigma can still LOSE on the mu-3sigma the
ladder ranks by (report SS5: v1/v2 means coincide to 0.16pp yet ladder separates 104 Elo).
When mu/sigma are supplied we ALSO report the tail gap; passes stays on the mean, with
tail_gap_positive flagged so the caller checks both.

HONESTY: cabt local A/B is ANTI-PREDICTIVE of the ladder (Spearman -0.80). This module
operates on LADDER Elo (mu, sigma from TrueSkill), the only honest judge. NEVER feed it
local cabt win-rates as if they were ladder gaps.

Pure python + scipy.stats.norm. Deterministic, offline, no Docker, no Kaggle.
"""
from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass, asdict
from typing import Sequence

from scipy.stats import norm

# --- Constants (mirror quant deflated_sharpe.py) ---------------------------
EULER_MASCHERONI: float = 0.5772156649015329  # gamma (Bailey & Lopez de Prado 2014)
DEFAULT_MARGIN_Z: float = 1.645               # one-sided 95% normal margin
_EPS: float = 1e-12


@dataclass(frozen=True)
class DeflatedEloResult:
    gap: float                          # g = mu_cand - mu_floor (Elo points)
    sigma_gap: float                    # sqrt(sigma_cand^2 + sigma_floor^2) (within-estimate)
    scale: float                        # sqrt(between-candidate V) used for E[max]
    scale_is_fallback: bool             # True if sigma_gap was used as a placeholder scale (NOT trustworthy)
    expected_max_gap_under_null: float  # E[max of N null gaps] = deflated threshold
    deflated_z: float                   # (g - E[max gap]) / sigma_gap
    passes: bool                        # deflated_z >= margin_z AND inputs valid
    n_trials: int                       # N family-wise ladder experiments
    margin_z: float                     # significance margin applied
    tail_gap: float                     # (mu_cand-3*sigma_cand) - (mu_floor-3*sigma_floor); nan if unknown
    tail_gap_positive: bool             # tail_gap > 0 (necessary-not-sufficient ladder check)
    valid: bool                         # inputs passed fail-closed validation
    reason: str                         # why it failed / caveat (empty if clean pass)


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def sigma_gap_from(sigma_cand: float, sigma_floor: float) -> float:
    """sigma_gap = sqrt(sigma_cand^2 + sigma_floor^2) (within-estimate gap uncertainty).

    The two TrueSkill posteriors are independent, so the variance of THIS gap is the
    sum of variances. NOTE: this is the within-estimate uncertainty used to normalize
    deflated_z; it is NOT the between-candidate dispersion that scales E[max].
    """
    sc = float(sigma_cand)
    sf = float(sigma_floor)
    return math.sqrt(sc * sc + sf * sf)


def grid_dispersion(gaps: Sequence[float]) -> float:
    """sqrt(V) of the realized family gaps = the BETWEEN-candidate scale for E[max].

    This is the quant grid_sharpe_var analog (np.var(stats_across_configs, ddof=1)).
    Pass the list of converged Elo gaps (mu_cand - mu_floor) for ALL N family members.
    Needs >= 2 finite gaps; returns nan otherwise (caller fail-closes).
    """
    vals = [float(x) for x in gaps if _finite(x)]
    if len(vals) < 2:
        return float("nan")
    return float(statistics.stdev(vals))  # ddof=1 sample std


def expected_max_gap_under_null(n_trials: int, scale: float) -> float:
    """E[max of N null gaps] ~= scale * ((1-gamma)*Phi^-1[1-1/N] + gamma*Phi^-1[1-1/(N*e)]).

    Direct port of quant's expected_max_sharpe. `scale` = sqrt(between-candidate V),
    NOT the within-estimate sigma_gap (see module CRITICAL note). Returns 0.0 for N < 2
    (no selection / winner's curse). Monotone non-decreasing in N.
    """
    N = int(n_trials)
    sc = float(scale)
    if N < 2:
        return 0.0
    if not _finite(sc) or sc <= 0.0:
        return 0.0
    g = EULER_MASCHERONI
    z1 = norm.ppf(1.0 - 1.0 / N)             # Phi^-1[1 - 1/N]
    z2 = norm.ppf(1.0 - 1.0 / (N * math.e))  # Phi^-1[1 - 1/(N*e)]  (N*e, not N/e)
    emax = sc * ((1.0 - g) * z1 + g * z2)
    return float(emax)


def deflated_elo(
    *,
    mu_cand: float | None = None,
    mu_floor: float | None = None,
    sigma_cand: float | None = None,
    sigma_floor: float | None = None,
    gap: float | None = None,
    sigma_gap: float | None = None,
    between_gap_std: float | None = None,
    n_trials: int,
    margin_z: float = DEFAULT_MARGIN_Z,
    illustrative: bool = False,
) -> DeflatedEloResult:
    """Deflated Elo-gap significance for a ladder candidate vs a floor anchor.

    Input modes (mutually exclusive for the gap):
      (A) mu_cand, mu_floor, sigma_cand, sigma_floor  -> derives gap, sigma_gap, tail_gap.
      (B) gap and sigma_gap directly (tail_gap unknown).

    `between_gap_std` = sqrt(between-candidate V), the scale for E[max] (use
    grid_dispersion(gaps)). REQUIRED for N >= 2 unless illustrative=True. FAIL-CLOSED:
    any invalid input yields passes=False, valid=False with a reason. A candidate is
    significant ONLY if its gap exceeds the N-deflated null-max by margin_z sigma_gap.
    """
    N_int = _as_int_or_zero(n_trials)
    tail_gap = float("nan")

    # --- derive gap / sigma_gap / tail_gap (mode A) or validate (mode B) -----
    if gap is None or sigma_gap is None:
        if None in (mu_cand, mu_floor, sigma_cand, sigma_floor):
            return _fail(N_int, margin_z,
                         "missing inputs: need (mu_cand,mu_floor,sigma_cand,sigma_floor) or (gap,sigma_gap)")
        if not all(_finite(x) for x in (sigma_cand, sigma_floor)) \
                or float(sigma_cand) <= 0.0 or float(sigma_floor) <= 0.0:
            return _fail(N_int, margin_z, "fail-closed: sigma_cand/sigma_floor must be finite > 0")
        if not all(_finite(x) for x in (mu_cand, mu_floor)):
            return _fail(N_int, margin_z, "fail-closed: mu_cand/mu_floor non-finite")
        g = float(mu_cand) - float(mu_floor)
        sg = sigma_gap_from(sigma_cand, sigma_floor)
        # TAIL gap: ladder ranks mu-3sigma, so report the tail gap too (necessary-not-sufficient).
        tail_gap = (float(mu_cand) - 3.0 * float(sigma_cand)) - (float(mu_floor) - 3.0 * float(sigma_floor))
    else:
        g = gap
        sg = sigma_gap

    # --- FAIL-CLOSED validation (N, sigma_gap, gap) --------------------------
    if not _is_valid_int_ge1(n_trials):
        return _fail(N_int, margin_z, "fail-closed: n_trials must be an int >= 1 (unknown N => NOT significant)")
    if not _finite(sg) or float(sg) <= 0.0:
        return _fail(N_int, margin_z, "fail-closed: sigma_gap must be finite > 0 (unknown sigma => NOT significant)")
    if not _finite(g):
        return _fail(N_int, margin_z, "fail-closed: gap non-finite => NOT significant")

    g = float(g)
    sg = float(sg)
    N = int(n_trials)
    mz = float(margin_z)
    tgp = bool(_finite(tail_gap) and tail_gap > 0.0)

    # --- resolve the E[max] SCALE (the V-fallback guard) ---------------------
    scale_is_fallback = False
    if N < 2:
        scale = 0.0  # no selection; scale irrelevant (E[max] collapses to 0)
    elif between_gap_std is not None and _finite(between_gap_std) and float(between_gap_std) > 0.0:
        scale = float(between_gap_std)
    elif illustrative:
        scale = sg  # placeholder ONLY; loudly flagged as not trustworthy
        scale_is_fallback = True
    else:
        return _fail(
            N_int, margin_z,
            "fail-closed (V-fallback guard): N>=2 needs between_gap_std = sqrt(var of the N "
            "realized family gaps) for the E[max] scale. Substituting sigma_gap is the "
            "under-deflation bug quant fixed 2026-06-15. Supply grid_dispersion(gaps) once the "
            "family converges, or pass illustrative=True (result will be stamped NOT trustworthy).",
            tail_gap=tail_gap, tail_gap_positive=tgp, sigma_gap=sg, gap=g,
        )

    # --- deflation -----------------------------------------------------------
    emax = expected_max_gap_under_null(N, scale)   # 0.0 at N==1 (deflation is a no-op, not a pass)
    deflated_z = (g - emax) / sg
    passes = bool(deflated_z >= mz)

    if passes and scale_is_fallback:
        reason = ("PASS but ILLUSTRATIVE ONLY (scale_is_fallback): E[max] used sigma_gap as a "
                  "placeholder scale, NOT the between-candidate dispersion. NOT trustworthy until "
                  "between_gap_std = grid_dispersion(gaps) is supplied.")
    elif passes:
        reason = ""
    else:
        reason = (
            f"gap {g:.2f} does not clear deflated bar: needs g >= "
            f"E[maxgap]({emax:.2f}) + {mz:.3f}*sigma_gap({sg:.2f}) = "
            f"{emax + mz * sg:.2f} (deflated_z={deflated_z:.3f} < {mz:.3f}, N={N})"
        )
        if scale_is_fallback:
            reason += " [scale_is_fallback: bar used sigma_gap placeholder, NOT trustworthy]"

    return DeflatedEloResult(
        gap=g,
        sigma_gap=sg,
        scale=float(scale),
        scale_is_fallback=scale_is_fallback,
        expected_max_gap_under_null=float(emax),
        deflated_z=float(deflated_z),
        passes=passes,
        n_trials=N,
        margin_z=mz,
        tail_gap=float(tail_gap),
        tail_gap_positive=tgp,
        valid=True,
        reason=reason,
    )


# --- fail-closed helpers ---------------------------------------------------
def _as_int_or_zero(n) -> int:
    try:
        return int(n)
    except (TypeError, ValueError):
        return 0


def _is_valid_int_ge1(n) -> bool:
    if isinstance(n, bool):  # bool is an int subclass; reject True/False as N
        return False
    if not isinstance(n, int):
        return False
    return n >= 1


def _fail(n_trials, margin_z, reason: str, *, tail_gap: float = float("nan"),
          tail_gap_positive: bool = False, sigma_gap: float = float("nan"),
          gap: float = float("nan")) -> DeflatedEloResult:
    return DeflatedEloResult(
        gap=float(gap), sigma_gap=float(sigma_gap), scale=float("nan"),
        scale_is_fallback=False, expected_max_gap_under_null=float("nan"),
        deflated_z=float("nan"), passes=False, n_trials=_as_int_or_zero(n_trials),
        margin_z=float(margin_z), tail_gap=float(tail_gap),
        tail_gap_positive=bool(tail_gap_positive), valid=False, reason=reason,
    )


def to_json(result: DeflatedEloResult) -> str:
    """Canonical JSON (sort_keys, 6-decimal floats). NaN -> null for valid JSON."""
    def _clean(o):
        if isinstance(o, bool):
            return o
        if isinstance(o, float):
            return None if not math.isfinite(o) else round(o, 6)
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()}
        return o
    return json.dumps(_clean(asdict(result)), sort_keys=True, indent=2, ensure_ascii=False)


# --- CLI -------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deflated Elo-gap significance (PTCG ladder discipline; quant DSR port)."
    )
    ap.add_argument("--mu-cand", type=float, default=None)
    ap.add_argument("--mu-floor", type=float, default=None)
    ap.add_argument("--sigma-cand", type=float, default=None)
    ap.add_argument("--sigma-floor", type=float, default=None)
    ap.add_argument("--gap", type=float, default=None)
    ap.add_argument("--sigma-gap", type=float, default=None)
    ap.add_argument("--between-gap-std", type=float, default=None,
                    help="sqrt(var of the N realized family gaps); REQUIRED for N>=2 (E[max] scale)")
    ap.add_argument("--n-trials", type=int, required=True,
                    help="family-wise count of ladder experiments (the KB family N)")
    ap.add_argument("--margin-z", type=float, default=DEFAULT_MARGIN_Z)
    ap.add_argument("--illustrative", action="store_true",
                    help="allow sigma_gap placeholder scale for N>=2 (result stamped NOT trustworthy)")
    args = ap.parse_args()

    res = deflated_elo(
        mu_cand=args.mu_cand, mu_floor=args.mu_floor,
        sigma_cand=args.sigma_cand, sigma_floor=args.sigma_floor,
        gap=args.gap, sigma_gap=args.sigma_gap,
        between_gap_std=args.between_gap_std,
        n_trials=args.n_trials, margin_z=args.margin_z,
        illustrative=args.illustrative,
    )
    print(to_json(res))
    return 0 if res.passes else 1


if __name__ == "__main__":
    raise SystemExit(main())
