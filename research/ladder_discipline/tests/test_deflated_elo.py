#!/usr/bin/env python3
"""
Pure-python pytest for deflated_elo.py. Run:
    /Users/franmilla/FMA/proyectos/ptcg-ai-battle/.venv/bin/python -m pytest \
        /Users/franmilla/FMA/proyectos/ptcg-ai-battle/research/ladder_discipline/tests -q

Properties under test (the discipline's guarantees):
  (a) a placebo gap of 0 NEVER passes, at any N;
  (b) a fixed gap PASSES at small N but FAILS at large N (deflation bites);
  (c) the deflated threshold (expected_max_gap_under_null) is monotone non-decreasing in N;
  (d) FAIL-CLOSED on N < 1 / non-int N / sigma <= 0 / non-finite gap;
  (e) V-FALLBACK GUARD: N>=2 REQUIRES between_gap_std (the between-candidate scale); using
      sigma_gap as the E[max] scale is the under-deflation bug quant fixed 2026-06-15;
  (f) tail-gap (mu-3sigma) reported in mode A as a necessary-not-sufficient ladder check.

NOTE: for N>=2 calls that should be VALID we pass between_gap_std (the sqrt of the
between-candidate gap dispersion). Here we use the same magnitude as sigma_gap purely to
exercise the algebra; in production between_gap_std = grid_dispersion(converged gaps).
"""
import math
import sys
from pathlib import Path

# Make the module importable whether pytest is run from repo root or this dir.
_HERE = Path(__file__).resolve().parent
_MODDIR = _HERE.parent
if str(_MODDIR) not in sys.path:
    sys.path.insert(0, str(_MODDIR))

import deflated_elo as de  # noqa: E402


# --- (a) placebo gap = 0 NEVER passes --------------------------------------
def test_placebo_zero_gap_never_passes():
    for n in (1, 2, 5, 10, 50, 200, 1000):
        res = de.deflated_elo(gap=0.0, sigma_gap=4.0, between_gap_std=4.0, n_trials=n)
        assert res.valid is True
        assert res.passes is False, f"placebo gap=0 passed at N={n}"


def test_placebo_zero_gap_negative_z_when_deflated():
    # With N>=2 the null-max bar is strictly positive, so a zero gap is below it.
    res = de.deflated_elo(gap=0.0, sigma_gap=4.0, between_gap_std=4.0, n_trials=50)
    assert res.expected_max_gap_under_null > 0.0
    assert res.deflated_z < 0.0


# --- (b) a fixed gap passes at small N, fails at large N -------------------
def test_fixed_gap_passes_small_n_fails_large_n():
    # Choose a gap that clears the bar at N=2 but not at a big N. scale=4.
    gap, sg = 12.0, 4.0
    small = de.deflated_elo(gap=gap, sigma_gap=sg, between_gap_std=sg, n_trials=2)
    large = de.deflated_elo(gap=gap, sigma_gap=sg, between_gap_std=sg, n_trials=5000)
    assert small.valid and large.valid
    assert small.passes is True, f"expected PASS at small N (z={small.deflated_z})"
    assert large.passes is False, f"expected FAIL at large N (z={large.deflated_z})"
    # And the bar genuinely rose.
    assert large.expected_max_gap_under_null > small.expected_max_gap_under_null


def test_deflation_lowers_z_as_n_grows():
    gap, sg = 12.0, 4.0
    zs = [de.deflated_elo(gap=gap, sigma_gap=sg, between_gap_std=sg, n_trials=n).deflated_z
          for n in (2, 10, 100, 1000)]
    # z must be non-increasing as N grows (the bar only rises).
    for a, b in zip(zs, zs[1:]):
        assert b <= a + 1e-9, f"deflated_z increased with N: {zs}"


# --- (c) threshold monotone non-decreasing in N ---------------------------
def test_expected_max_gap_monotone_in_n():
    sg = 4.0
    ns = [2, 3, 5, 10, 25, 50, 100, 250, 500, 1000, 5000]
    vals = [de.expected_max_gap_under_null(n, sg) for n in ns]
    for a, b in zip(vals, vals[1:]):
        assert b >= a - 1e-12, f"expected_max_gap not monotone: {list(zip(ns, vals))}"


def test_expected_max_gap_n1_is_zero():
    # No selection with a single try -> no winner's-curse inflation.
    assert de.expected_max_gap_under_null(1, 4.0) == 0.0
    assert de.expected_max_gap_under_null(0, 4.0) == 0.0


# --- (d) FAIL-CLOSED -------------------------------------------------------
def test_fail_closed_n_below_one():
    for bad_n in (0, -1, -100):
        res = de.deflated_elo(gap=20.0, sigma_gap=4.0, between_gap_std=4.0, n_trials=bad_n)
        assert res.valid is False
        assert res.passes is False
        assert "n_trials" in res.reason


def test_fail_closed_non_int_n():
    for bad_n in (2.5, "10", None, True, False):
        res = de.deflated_elo(gap=20.0, sigma_gap=4.0, between_gap_std=4.0, n_trials=bad_n)
        assert res.valid is False
        assert res.passes is False


def test_fail_closed_sigma_non_positive():
    for bad_sigma in (0.0, -1.0):
        res = de.deflated_elo(gap=20.0, sigma_gap=bad_sigma, between_gap_std=4.0, n_trials=2)
        assert res.valid is False
        assert res.passes is False
        assert "sigma" in res.reason


def test_fail_closed_non_finite_sigma():
    for bad_sigma in (float("nan"), float("inf")):
        res = de.deflated_elo(gap=20.0, sigma_gap=bad_sigma, between_gap_std=4.0, n_trials=2)
        assert res.valid is False
        assert res.passes is False


def test_fail_closed_non_finite_gap():
    for bad_gap in (float("nan"), float("inf"), float("-inf")):
        res = de.deflated_elo(gap=bad_gap, sigma_gap=4.0, between_gap_std=4.0, n_trials=2)
        assert res.valid is False
        assert res.passes is False
        assert "gap" in res.reason


def test_fail_closed_mode_a_bad_sigma():
    # Mode A (mu/sigma inputs): a non-positive sigma must fail closed.
    res = de.deflated_elo(
        mu_cand=830.0, mu_floor=826.0, sigma_cand=0.0, sigma_floor=2.0,
        between_gap_std=4.0, n_trials=4,
    )
    assert res.valid is False
    assert res.passes is False


def test_fail_closed_missing_inputs():
    res = de.deflated_elo(n_trials=4)  # neither mode A nor mode B supplied
    assert res.valid is False
    assert res.passes is False
    assert "missing inputs" in res.reason


# --- (e) V-FALLBACK GUARD (the imported quant lesson) ----------------------
def test_v_fallback_guard_n_ge2_requires_between_std():
    # N>=2 with NO between_gap_std and not illustrative => fail-closed (do not
    # silently substitute sigma_gap; that is the under-deflation bug).
    res = de.deflated_elo(gap=20.0, sigma_gap=4.0, n_trials=4)
    assert res.valid is False
    assert res.passes is False
    assert "V-fallback" in res.reason or "between_gap_std" in res.reason


def test_illustrative_flag_uses_fallback_scale_and_is_flagged():
    # illustrative=True allows the sigma_gap placeholder scale but stamps it NOT trustworthy.
    res = de.deflated_elo(gap=40.0, sigma_gap=4.0, n_trials=4, illustrative=True)
    assert res.valid is True
    assert res.scale_is_fallback is True
    # whether it passes or not, the reason must carry the not-trustworthy caveat.
    assert ("ILLUSTRATIVE" in res.reason) or ("scale_is_fallback" in res.reason)


def test_between_std_changes_the_bar_not_the_fallback():
    # A larger between-candidate dispersion raises the bar (more spread => luckier max).
    small_scale = de.deflated_elo(gap=20.0, sigma_gap=4.0, between_gap_std=2.0, n_trials=10)
    big_scale = de.deflated_elo(gap=20.0, sigma_gap=4.0, between_gap_std=8.0, n_trials=10)
    assert small_scale.valid and big_scale.valid
    assert big_scale.expected_max_gap_under_null > small_scale.expected_max_gap_under_null
    assert small_scale.scale_is_fallback is False


def test_grid_dispersion():
    # sample std (ddof=1) of the realized family gaps; nan if < 2 finite values.
    gaps = [4.0, -2.0, 10.0, 1.0]
    expected = math.sqrt(sum((x - sum(gaps) / 4) ** 2 for x in gaps) / 3)
    assert math.isclose(de.grid_dispersion(gaps), expected, rel_tol=1e-9)
    assert math.isnan(de.grid_dispersion([5.0]))
    assert math.isnan(de.grid_dispersion([]))
    # non-finite entries are dropped
    assert math.isclose(de.grid_dispersion([4.0, float("nan"), -2.0]),
                        de.grid_dispersion([4.0, -2.0]), rel_tol=1e-9)


# --- (f) tail-gap (mu-3sigma) reported in mode A ---------------------------
def test_tail_gap_reported_and_can_diverge_from_mean_gap():
    # Higher mu but ALSO higher sigma: mean gap > 0 yet the mu-3sigma tail gap < 0.
    # mean gap = 835-826 = +9; tail gap = (835-3*6) - (826-3*1) = 817 - 823 = -6.
    res = de.deflated_elo(
        mu_cand=835.0, mu_floor=826.0, sigma_cand=6.0, sigma_floor=1.0,
        between_gap_std=4.0, n_trials=4,
    )
    assert res.valid is True
    assert math.isclose(res.gap, 9.0, abs_tol=1e-9)
    assert math.isclose(res.tail_gap, -6.0, abs_tol=1e-9)
    assert res.tail_gap_positive is False  # ladder ranks the tail; mean-pass is not sufficient


def test_tail_gap_positive_when_tail_wins():
    res = de.deflated_elo(
        mu_cand=840.0, mu_floor=826.0, sigma_cand=2.0, sigma_floor=2.0,
        between_gap_std=4.0, n_trials=4,
    )
    assert res.valid is True
    # tail gap = (840-6) - (826-6) = 834 - 820 = +14
    assert math.isclose(res.tail_gap, 14.0, abs_tol=1e-9)
    assert res.tail_gap_positive is True


# --- mode A composition sanity --------------------------------------------
def test_mode_a_matches_mode_b():
    a = de.deflated_elo(mu_cand=840.0, mu_floor=826.0,
                        sigma_cand=2.5, sigma_floor=2.5, between_gap_std=4.0, n_trials=4)
    sg = math.sqrt(2.5 ** 2 + 2.5 ** 2)
    b = de.deflated_elo(gap=14.0, sigma_gap=sg, between_gap_std=4.0, n_trials=4)
    assert a.valid and b.valid
    assert math.isclose(a.gap, b.gap, abs_tol=1e-9)
    assert math.isclose(a.sigma_gap, b.sigma_gap, abs_tol=1e-9)
    assert math.isclose(a.deflated_z, b.deflated_z, abs_tol=1e-9)
    assert a.passes == b.passes


# --- N==1 is a no-op deflation, not a free pass ---------------------------
def test_n1_no_deflation_but_still_needs_margin():
    # gap just under margin*sigma -> fail even at N=1 (no free pass). N=1 needs no between_std.
    res_fail = de.deflated_elo(gap=4.0, sigma_gap=4.0, n_trials=1)  # z=1.0 < 1.645
    assert res_fail.valid and res_fail.passes is False
    res_pass = de.deflated_elo(gap=8.0, sigma_gap=4.0, n_trials=1)  # z=2.0 >= 1.645
    assert res_pass.valid and res_pass.passes is True
    assert res_pass.expected_max_gap_under_null == 0.0
