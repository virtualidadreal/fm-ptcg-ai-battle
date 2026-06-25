"""Throwaway probe: load the candidate in-engine, check deck phase + role module.
Run inside ptcg-cabt docker. Not part of the submission."""
import sys, os
ROOT = "/work"
sys.path.insert(0, os.path.join(ROOT, "agents_official/sabrina_kb_role"))
from kaggle_environments.agent import get_last_callable

adir = os.path.join(ROOT, "agents_official/sabrina_kb_role")
ap = os.path.join(adir, "main.py")
os.chdir(adir)  # so vendored cg/libcg.so resolves (proven ptcg-abc trick)
ag = get_last_callable(open(ap).read(), path=ap)
print("loaded agent:", ag.__name__)
deck = ag({"select": None})
print("deck phase returns:", len(deck), "ids; first/last:", deck[0], deck[-1])

import importlib.util
spec = importlib.util.spec_from_file_location("m", ap)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
RI = m.RoleInputs
print("ROLE BEATDOWN (ahead+ohko):", m.assign_role(RI(2, True, False)))
print("ROLE CONTROL (opp ohko, I can't):", m.assign_role(RI(0, False, True)))
print("ROLE CONTROL (behind>1):", m.assign_role(RI(-2, False, False)))
print("ROLE NEUTRAL:", m.assign_role(RI(0, False, False)))
print("FLAG default ON:", m.ROLE_NUDGE_ON)
print("SMOKE-IMPORT-OK")
