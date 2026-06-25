# sabrina_kb_role — dynamic BEATDOWN/CONTROL role nudge (one-lever A/B)

Fork of `sabrina_v1` that adds **exactly one lever**: an archetype-agnostic, dynamic
**role assignment** (BEATDOWN vs CONTROL) that gently re-weights a handful of existing
scores. `deck.csv` is **byte-identical** to sabrina_v1 — this is pure logic, no list change.

## The lever (one variable, bounded, reversible)

A tiny generic module reads only **public turn state** and labels the turn:

```
assign_role(RoleInputs(prize_diff, can_ohko_active, opp_can_ohko_me)):
  ahead + I can OHKO their active   -> BEATDOWN   (press the lead to the finish)
  they can OHKO me, I can't them     -> CONTROL    (can't win the race -> attrition, no deck-out)
  behind by > 1 prize                -> CONTROL    (grind back, don't trade into a lost race)
  else                               -> NEUTRAL    (base policy untouched == sabrina_v1)
```

Then a thin **post-hoc nudge** (a bounded multiplier, never a hard override and never a new
legal move) tilts only **near-ties** inside an existing score class:

| role | what it nudges | effect |
|------|----------------|--------|
| **BEATDOWN** | `_score_attack` non-lethal damage score ×1.20 | bias toward the close: a tie between "attack now" and a reversible setup tilts to the kill |
| **CONTROL** | deck-preserve buffer `+4` (so don't mill out while grinding) **and** Run Away Draw engine ×0.80 *only once the deck is genuinely low* | don't deck yourself out; favour attrition |
| **NEUTRAL** | nothing (×1.0, +0) | identical to sabrina_v1 |

Hard guarantees that keep this a NUDGE, not a rewrite:
- **Lethal / game-winning lines (the `90000` band) are never touched** in either role — you
  always take the win regardless of role.
- The multipliers (1.20 / 0.80) only re-order moves *inside the same class*, because the base
  policy already separates classes by orders of magnitude (lethal 9e4, evolves/Rare Candy ~2e4,
  attacks 1e3–9e4, draw ability ~1.5e4). A ±20% tilt cannot promote a fundamentally worse move.
- The CONTROL draw restraint never STOPS drawing (it stays above the generic-ability floor of
  9000); it only lets the draw engine lose ties to non-mill lines once the deck is short.

### Reversible / ablation switch
Set `SABRINA_ROLE_NUDGE=0` and this file behaves **exactly like sabrina_v1** (NEUTRAL role,
all multipliers 1.0, buffer +4). Default is ON.

## Where the heuristic comes from (Knowledge OS)

`knowledge/synthesis/heuristicas-computables.md`, **#8 "Asignación dinámica de rol BEATDOWN
vs CONTROL"** (from the `archetypes` fiche).

Honest scope per that doc's own caveats:
- The fiche's velocity/favorability functions (`est_turns_to_first_ohko`, `prior_winrate`,
  `belief_opp_*`) are **stubs** — names, not implementations — and one fiche **fabricated** a
  Flipside quote. So we **do NOT** port its `assign_role` verbatim.
- We implement only the part that is a **meta-INVARIANT of imperfect-info Rule-Box mechanics**
  and computable from **public** state in cabt: `prize_diff` is public (prize counters), and
  OHKO-reachability we already compute (`_ko_active_reachable` / `_alakazam_damage` /
  `_achievable_hand`). `matchup_fav` and hidden-energy speed estimates (the rotating,
  meta-dependent parts flagged ⚠️) are **not** used.

## Archetype-agnostic design goal (base of a general PTCG player, not just cabt)

`RoleInputs` + `assign_role` know **nothing about Alakazam**. They take a 3-field duck-typed
struct (`prize_diff`, `can_ohko_active`, `opp_can_ohko_me`) and return a label. Any future
pilot — Dragapult/Leon, or a general "best PTCG player" core — can fill the same struct from
its own public state and reuse the module **unchanged**. Sabrina only supplies a thin adapter
(`AlakazamPolicy.role()` + `_opp_can_ohko_me()`) that fills `RoleInputs` from its policy. The
opponent-OHKO speed proxy uses only **visible attached energy** (no hidden belief), the engine
attack-damage table, and type-aware weakness/resistance — all archetype-neutral.

## Scaffolding (inherited verbatim from sabrina_v1)

Contract `agent(obs, config=None) -> list[int]`, deck-phase short-circuit, double try/except
(policy-level + obs-level), repetition-safe `_legal_fallback` / `normalize_selection`
(handles `minCount > #options`), final `_validate_obj` gate (illegal policy output → legal
fallback, never raised), non-raising module load (a missing/short deck.csv degrades, never
kills the module). The role lever is the ONLY behavioural diff vs sabrina_v1.

## A/B command (the only judge is the ladder; cabt is a filter)

Self-play A/B vs `sabrina_v1`, alternating seats, inside the `ptcg-cabt` docker:

```bash
docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt \
  python experiments/ab_harness.py \
    agents_official/sabrina_kb_role agents_official/sabrina_v1 60
```

Ablation (lever OFF must reproduce sabrina_v1 within noise):

```bash
docker run --platform=linux/amd64 --rm -e SABRINA_ROLE_NUDGE=0 -v "$PWD":/work -w /work \
  ptcg-cabt python experiments/ab_harness.py \
    agents_official/sabrina_kb_role agents_official/sabrina_v1 60
```

Build a submission tarball (Fran's decision to upload, 1 change/day, keep sabrina_v1 as floor):

```bash
cd agents_official/sabrina_kb_role && bash build_submission.sh
```

### Validation status (this build)
Smoke OK inside `ptcg-cabt` docker: agent loads in-engine, deck phase returns 60 ids, role
module returns the 4 expected labels, and an N=12 paired A/B vs sabrina_v1 ran **end-to-end
with 0 crashes / 0 errors** (7W/5L, Wilson IC includes 0.5 = no significant difference at
N=12, as expected for a bounded tie-tilt — run N≥60 for a directional read). **cabt is
anti-predictive of the ladder (Spearman ≈ −0.80): a cabt dip is NOT a veto. The ladder is the
judge.**
