"""First-legal baseline agent for cabt (dict-only, robust).

During deck selection (obs["select"] is None) returns the 60 card ids. Otherwise
returns the first min(max(1, minCount), len(option)) option indices. Deterministic.
Never crashes: a global try/except falls back to a legal selection.
"""
import os

# The cabt env loads agents via get_last_callable with NO __file__ defined, but the
# harness chdir's into THIS agent dir before loading, so cwd-relative "deck.csv"
# resolves correctly. We still try a __file__-relative path first when available.
try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _HERE = os.getcwd()


def _load_deck():
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


def _legal_fallback(select):
    n = len(select["option"])
    lo = max(1, int(select.get("minCount", 1) or 1))
    lo = min(lo, n)
    return list(range(lo))


def agent(obs, config=None):
    try:
        select = obs.get("select")
        if select is None:
            return list(my_deck) if my_deck else []

        option = select["option"]
        n = len(option)
        if n == 0:
            return []
        lo = max(1, int(select.get("minCount", 1) or 1))
        lo = min(lo, n)
        return list(range(lo))
    except Exception:
        try:
            return _legal_fallback(obs["select"])
        except Exception:
            return [0]
