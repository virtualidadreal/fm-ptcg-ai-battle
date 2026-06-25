"""Random baseline agent for cabt (dict-only, robust).

Reads its OWN deck.csv (60 ids) from the directory of this file. During deck
selection (obs["select"] is None) returns the 60 card ids. Otherwise picks
minCount..(<=maxCount) RANDOM legal option indices. Seeded per decision number
so it varies across decisions but is reproducible. Never crashes: a global
try/except falls back to a legal selection.
"""
import os
import random

# --- load my deck ONCE, cwd-independent ---
# The cabt env loads agents via get_last_callable with NO __file__ defined, but the
# harness chdir's into THIS agent dir before loading, so cwd-relative "deck.csv"
# resolves correctly. We still try a __file__-relative path first when available.
try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _HERE = os.getcwd()


def _load_deck():
    # try the file next to this module first, then cwd-relative as a fallback
    for path in (os.path.join(_HERE, "deck.csv"), "deck.csv"):
        try:
            with open(path) as f:
                ids = [int(line.strip()) for line in f if line.strip()]
            if len(ids) == 60:
                return ids
        except Exception:
            continue
    return None


my_deck = _load_deck()

# per-process decision counter so the seed varies between decisions
_decision = 0


def _legal_fallback(select):
    """A guaranteed-legal selection: minCount distinct indices from the front."""
    n = len(select["option"])
    lo = max(1, int(select.get("minCount", 1) or 1))
    lo = min(lo, n)
    return list(range(lo))


def agent(obs, config=None):
    global _decision
    try:
        select = obs.get("select")
        if select is None:
            # deck-selection phase
            return list(my_deck) if my_deck else []

        option = select["option"]
        n = len(option)
        if n == 0:
            return []
        lo = max(1, int(select.get("minCount", 1) or 1))
        hi = int(select.get("maxCount", lo) or lo)
        lo = min(lo, n)
        hi = max(lo, min(hi, n))

        rng = random.Random(_decision)
        _decision += 1
        k = rng.randint(lo, hi)
        return rng.sample(range(n), k)
    except Exception:
        try:
            return _legal_fallback(obs["select"])
        except Exception:
            return [0]
