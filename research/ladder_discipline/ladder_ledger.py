#!/usr/bin/env python3
"""
ladder_ledger.py — append-only family-wise ledger of LADDER experiments (PTCG).

WHY (ported from quant/research/ledger.py)
------------------------------------------
The only mathematical defence against "spraying levers at the ladder until one looks
good" is to deflate the winner's Elo gap by the number of experiments the WHOLE family
has spent — not by campaign. Quant proved this: E[max] rises monotonically with N, so
not counting every trial inflates the apparent edge (winner's curse). This ledger
persists and COUNTS the family-wise N that feeds deflated_elo as its n_trials.

It does NOT re-implement the statistics: deflated_elo.py is the judge. Here we only
keep an honest, append-only count of N per family.

family = the KB-lever family (e.g. "kb_levers_sabrina_v1"). CONSERVATIVE: everything
tried within a family shares the deflator. Counting too few inflates significance —
the exact bug quant's control test catches.

APPEND-ONLY (FMA hard rule): the TSV is opened in mode 'a' only; the header is written
once if missing. Nothing is ever deleted or truncated.

IDEMPOTENCY (quant hit this bug — a campaign run twice double-counted N):
family_trial_count() counts UNIQUE (family, agent, hypothesis) experiments, not raw
rows. Re-logging the same experiment (same agent + same hypothesis in the same family)
does not inflate N. record_experiment() also refuses an exact duplicate append guard
via already_logged().

HONESTY: status is one of {pre_registered, submitted, converged, retired}. Only
converged rows carry trustworthy mu/sigma (TrueSkill needs days to converge). The
score column is mu - 3*sigma (the public ladder TAIL score), recorded for audit; the
DEFLATION test uses mu and sigma (the means), not this tail score.

CLI:
  python ladder_ledger.py --count --family kb_levers_sabrina_v1
  python ladder_ledger.py --map
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

LEDGER_PATH: Path = Path(
    "/Users/franmilla/FMA/proyectos/ptcg-ai-battle/research/ladder_discipline/ladder_ledger.tsv"
)

VALID_STATUS: tuple[str, ...] = ("pre_registered", "submitted", "converged", "retired")

_COLUMNS: tuple[str, ...] = (
    "timestamp",        # ISO-8601 UTC (NOT part of any equality / dedup key)
    "agent",            # submission name, e.g. "sabrina_kb_draw"
    "family",           # family-wise deflation key, e.g. "kb_levers_sabrina_v1"
    "hypothesis",       # 1-line hypothesis / lever id, e.g. "kb_draw anti-deck-out"
    "floor",            # anchor agent the gap is measured against, e.g. "sabrina_v1"
    "mu",               # TrueSkill mu (mean skill); blank/nan until converged
    "sigma",            # TrueSkill sigma (uncertainty); blank/nan until converged
    "score_mu_minus_3sigma",  # public ladder TAIL score = mu - 3*sigma (audit only)
    "status",           # one of VALID_STATUS
)


@dataclass(frozen=True)
class LadderRow:
    timestamp: str
    agent: str
    family: str
    hypothesis: str
    floor: str
    mu: float
    sigma: float
    score_mu_minus_3sigma: float
    status: str


# --- escaping (TSV-safe) ---------------------------------------------------
def _esc(text: str) -> str:
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
        .replace("\n", "\\n")
    )


def _unesc(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if c == "\\" and i + 1 < len(text):
            nxt = text[i + 1]
            out.append({"t": "\t", "r": "\r", "n": "\n", "\\": "\\"}.get(nxt, nxt))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_float(s: str) -> float:
    try:
        return float(s)
    except (ValueError, TypeError):
        return float("nan")


def _ensure_header() -> None:
    """Write the header ONLY if the file does not exist. Never truncates (append-only)."""
    if not LEDGER_PATH.exists():
        LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER_PATH.open("a", encoding="utf-8") as fh:
            fh.write("\t".join(_COLUMNS) + "\n")


def _ledger_path() -> Path:
    return LEDGER_PATH


# --- read (read-only) ------------------------------------------------------
def read_rows() -> tuple[LadderRow, ...]:
    """All rows (read-only). Empty tuple if the file does not exist. Corrupt lines
    are skipped, never deleted (append-only)."""
    path = _ledger_path()
    if not path.exists():
        return ()
    rows: list[LadderRow] = []
    with path.open("r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    for i, line in enumerate(lines):
        if i == 0 or not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != len(_COLUMNS):
            continue
        v = [_unesc(p) for p in parts]
        rows.append(
            LadderRow(
                timestamp=v[0],
                agent=v[1],
                family=v[2],
                hypothesis=v[3],
                floor=v[4],
                mu=_parse_float(v[5]),
                sigma=_parse_float(v[6]),
                score_mu_minus_3sigma=_parse_float(v[7]),
                status=v[8],
            )
        )
    return tuple(rows)


# --- family-wise counting --------------------------------------------------
def _experiment_key(agent: str, hypothesis: str) -> tuple[str, str]:
    """An experiment is identified by (agent, hypothesis). Re-logging the same
    experiment (status change, convergence update) is NOT a new trial."""
    return (str(agent).strip(), str(hypothesis).strip())


def family_trial_count(family: str) -> int:
    """Accumulated number of UNIQUE experiments in `family` across the whole program.

    Counts unique (agent, hypothesis) pairs — NOT raw rows — so a converged update of an
    already-submitted lever, or a re-run of a campaign, does not double-count N (the
    quant double-counting bug). This integer feeds deflated_elo as n_trials.

    Retired experiments STILL count: they were spent tries; pretending they did not
    happen would inflate significance (HARKing). 0 if the TSV does not exist.

    IMPORTANT (mirrors quant): the N passed to deflated_elo for a NEW hypothesis is
    family_trial_count(family) + 1 (the new try itself counts). For a CLOSED
    pre-registered grid of k levers, the honest N for ALL members is
    family_trial_count(family) + k (selection operates over the whole grid).
    """
    fam = str(family).strip()
    seen: set[tuple[str, str]] = set()
    for r in read_rows():
        if r.family.strip() == fam:
            seen.add(_experiment_key(r.agent, r.hypothesis))
    return len(seen)


def already_logged(agent: str, family: str, hypothesis: str) -> bool:
    """True if this exact experiment already has a row (idempotency guard)."""
    fam = str(family).strip()
    key = _experiment_key(agent, hypothesis)
    for r in read_rows():
        if r.family.strip() == fam and _experiment_key(r.agent, r.hypothesis) == key:
            return True
    return False


def family_counts() -> dict[str, int]:
    """Map {family: unique-experiment-count} across the whole ledger."""
    fams: dict[str, set[tuple[str, str]]] = {}
    for r in read_rows():
        fams.setdefault(r.family.strip(), set()).add(_experiment_key(r.agent, r.hypothesis))
    return {f: len(s) for f, s in fams.items()}


# --- write (append-only) ---------------------------------------------------
def record_experiment(
    *,
    agent: str,
    family: str,
    hypothesis: str,
    floor: str,
    mu: float = float("nan"),
    sigma: float = float("nan"),
    status: str = "pre_registered",
    allow_duplicate: bool = False,
) -> LadderRow | None:
    """Append a ladder experiment row (append-only).

    - Validates status in VALID_STATUS.
    - score_mu_minus_3sigma is DERIVED (mu - 3*sigma) when mu/sigma are finite, else nan.
    - IDEMPOTENT by default: if (agent, family, hypothesis) is already logged, returns
      None and writes nothing, unless allow_duplicate=True (e.g. a deliberate status
      update row). Even with a duplicate row, family_trial_count() will not double-count.
    """
    if status not in VALID_STATUS:
        raise ValueError(f"invalid status {status!r}; valid: {VALID_STATUS}")
    if not allow_duplicate and already_logged(agent, family, hypothesis):
        return None

    mu_f = float(mu)
    sigma_f = float(sigma)
    import math as _m
    score = (mu_f - 3.0 * sigma_f) if (_m.isfinite(mu_f) and _m.isfinite(sigma_f)) else float("nan")

    row = LadderRow(
        timestamp=_utc_now(),
        agent=str(agent),
        family=str(family),
        hypothesis=str(hypothesis),
        floor=str(floor),
        mu=mu_f,
        sigma=sigma_f,
        score_mu_minus_3sigma=score,
        status=status,
    )
    _ensure_header()
    fields = [
        _esc(row.timestamp),
        _esc(row.agent),
        _esc(row.family),
        _esc(row.hypothesis),
        _esc(row.floor),
        _esc(repr(row.mu)),
        _esc(repr(row.sigma)),
        _esc(repr(row.score_mu_minus_3sigma)),
        _esc(row.status),
    ]
    with _ledger_path().open("a", encoding="utf-8") as fh:  # append-only, never truncate
        fh.write("\t".join(fields) + "\n")
    return row


# --- CLI -------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Append-only family-wise ladder ledger (PTCG). Counts N, never judges."
    )
    ap.add_argument("--count", action="store_true", help="print family_trial_count(--family)")
    ap.add_argument("--family", default=None)
    ap.add_argument("--map", action="store_true", help="print family_counts() for the whole ledger")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.map:
        counts = family_counts()
        if args.json:
            print(json.dumps(counts, sort_keys=True, ensure_ascii=False, indent=2))
        else:
            for k in sorted(counts):
                print(f"  {k:32s} {counts[k]}")
        return 0

    if args.count:
        if not args.family:
            ap.error("--count requires --family")
        n = family_trial_count(args.family)
        payload = {
            "family": args.family,
            "family_trial_count": n,
            "trial_count_for_next_hypothesis": n + 1,
        }
        if args.json:
            print(json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2))
        else:
            print(f"family_trial_count({args.family}) = {n}")
            print(f"  -> n_trials for the NEXT hypothesis = {n + 1}")
        return 0

    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
