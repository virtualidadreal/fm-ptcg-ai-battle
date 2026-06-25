"""
Leon v3 (BC/IL) — policy GREEDY aprendida por Behavioral Cloning de pilotos Elo>=1150.

Decision core: codifica el obs con el encoder OFICIAL (encode_lib, verbatim del kernel MCTS), puntua las
acciones candidatas con la policy net entrenada (model.LeonV3Net, pesos leon_v3.pt) y elige el ARGMAX.
Envuelto en el MISMO scaffolding robusto que Leon v1 (deck loader cwd-safe, _validate, _legal_fallback):
si torch/cg/los pesos/el encode fallan por lo que sea, degrada a first-legal en vez de morir. NUNCA crashea.

Cadena de fallback:  net argmax  ->  (si invalido o excepcion)  first-legal.
`agent` es la ULTIMA funcion top-level (get_last_callable carga la ultima).
Tar de submission: main.py + model.py + encode_lib.py + leon_v3.pt + deck.csv + cg/ (con libcg.so).
"""
from __future__ import annotations

import os
import sys

# ── PATH bulletproof: que encode_lib/model/cg/pesos resuelvan SIEMPRE (si no, el agente
#    caeria en silencio a first-legal y la net no jugaria). Anadimos el dir del agente,
#    el cwd y la ruta de submission de Kaggle al sys.path ANTES de cualquier import propio.
_THIS_DIR = None
try:
    _THIS_DIR = os.path.dirname(os.path.abspath(__file__))
except Exception:
    _THIS_DIR = None
for _c in (_THIS_DIR, os.getcwd(), "/kaggle_simulations/agent"):
    try:
        if _c and os.path.isdir(_c) and _c not in sys.path:
            sys.path.insert(0, _c)
    except Exception:
        pass


# ── robust deck loader (cwd-independent, load once at module level) ───────────
def _resolve_deck_path():
    cands = []
    if "__file__" in globals():
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deck.csv"))
    cands.append("deck.csv")
    cands.append("/kaggle_simulations/agent/deck.csv")
    for p in sys.path:
        if p:
            cands.append(os.path.join(p, "deck.csv"))
    for p in cands:
        try:
            if os.path.exists(p):
                return p
        except Exception:
            continue
    return None


def _load_deck():
    path = _resolve_deck_path()
    if not path:
        return []
    try:
        with open(path, "r") as f:
            ids = [int(x) for x in f.read().splitlines() if x.strip()]
        return ids[:60]
    except Exception:
        return []


my_deck = _load_deck()


# ── legal fallback (NEVER crash; respect minCount/maxCount/range) ─────────────
def _legal_fallback(select_dict):
    try:
        n = len(select_dict.get("option") or [])
        lo = max(0, select_dict.get("minCount", 0) or 0)
        if n == 0:
            return []
        if lo <= n:
            return list(range(lo))
        out = list(range(n))
        k = 0
        while len(out) < lo:
            out.append(k % n)
            k += 1
        return out
    except Exception:
        return []


def _legal_fallback_from_obs(obs):
    try:
        sel = (obs or {}).get("select") or {}
        return _legal_fallback(sel)
    except Exception:
        return []


def _validate(out, select_dict):
    try:
        if not isinstance(out, list):
            return False
        n = len(select_dict.get("option") or [])
        min_c = max(0, select_dict.get("minCount", 0) or 0)
        max_c = max(min_c, select_dict.get("maxCount", 0) or 0)
        if not (min_c <= len(out) <= max_c):
            return False
        if not all(isinstance(i, int) and 0 <= i < n for i in out):
            return False
        if min_c <= n and len(set(out)) != len(out):
            return False
        return True
    except Exception:
        return False


# ── net loader (degrade gracefully if torch/cg/pesos no disponibles) ──────────
_NET_OK = True
_NET_ERR = None
_MODEL = None
try:
    import torch
    import encode_lib as E
    from model import LeonV3Net

    _W = None
    for _cand in ((os.path.join(_THIS_DIR, "leon_v3.pt") if _THIS_DIR else None),
                  "leon_v3.pt", "/kaggle_simulations/agent/leon_v3.pt"):
        if _cand and os.path.exists(_cand):
            _W = _cand
            break
    if _W is None:
        raise FileNotFoundError("leon_v3.pt no encontrado")
    _ckpt = torch.load(_W, map_location="cpu")
    _MODEL = LeonV3Net(d_model=int(_ckpt.get("d_model", 96)))
    _MODEL.load_state_dict(_ckpt["state_dict"])
    _MODEL.eval()
    torch.set_grad_enabled(False)
    torch.set_num_threads(max(1, (os.cpu_count() or 2)))
except Exception as exc:  # cualquier fallo -> degradar a first-legal
    _NET_OK = False
    _NET_ERR = exc


def _net_decision(obs_dict):
    """Codifica el estado, puntua candidatos con la net y devuelve el argmax (lista de indices de opcion)."""
    sv_enc, sv_dec, actions = E.encode_pair(obs_dict, my_deck)
    if not actions:
        return None
    import torch
    e_idx = torch.tensor(sv_enc.index, dtype=torch.long)
    e_val = torch.tensor(sv_enc.value, dtype=torch.float)
    e_wo = torch.tensor(sv_enc.offset, dtype=torch.long)
    d_idx = torch.tensor(sv_dec.index, dtype=torch.long)
    d_val = torch.tensor(sv_dec.value, dtype=torch.float)
    d_wo = torch.tensor(sv_dec.offset, dtype=torch.long)
    n_cand = torch.tensor([len(actions)], dtype=torch.long)
    logits, _ = _MODEL(e_idx, e_val, e_wo, d_idx, d_val, d_wo, n_cand)
    best = int(logits[0, :len(actions)].argmax().item())
    return [int(i) for i in actions[best]]


# ── diagnostics ───────────────────────────────────────────────────────────────
_DIAG = {"decisions": 0, "net_ok": 0, "fallbacks": 0, "deck_returns": 0, "errors": {}}


def _record_error(exc):
    k = type(exc).__name__ + ": " + str(exc)[:160]
    _DIAG["errors"][k] = _DIAG["errors"].get(k, 0) + 1


def diag_snapshot():
    s = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DIAG.items()}
    s["net_ok_load"] = _NET_OK
    s["net_err"] = repr(_NET_ERR) if _NET_ERR is not None else None
    return s


# ── public entry point: NEVER crash, ALWAYS return a legal selection ──────────
# NOTE: `agent` MUST be the LAST callable defined in this module (get_last_callable).
def agent(obs, config=None):
    try:
        if isinstance(obs, dict) and obs.get("select") is None:
            _DIAG["deck_returns"] += 1
            return my_deck
    except Exception:
        pass

    sel = obs.get("select") if isinstance(obs, dict) else None

    if not _NET_OK:
        _DIAG["fallbacks"] += 1
        return _legal_fallback(sel or {})

    _DIAG["decisions"] += 1
    try:
        out = _net_decision(obs)
        if _validate(out, sel or {}):
            _DIAG["net_ok"] += 1
            return out
        _DIAG["fallbacks"] += 1
        return _legal_fallback(sel or {})
    except Exception as exc:
        _record_error(exc)
        _DIAG["fallbacks"] += 1
        return _legal_fallback_from_obs(obs)
