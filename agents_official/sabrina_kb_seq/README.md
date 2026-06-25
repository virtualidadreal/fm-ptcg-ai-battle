# Sabrina kb_seq — turn SEQUENCING nudge

A **single-variable fork of `sabrina_v1`**. The only behavioural change vs v1 is a tiny,
flag-gated, **archetype-agnostic** phase-ordering nudge added to the option score. Everything
else (deck.csv, the `cg/` engine, all of v1's piloting logic and survival scaffolding) is
identical to v1. This makes `kb_seq`-vs-`v1` a clean A/B: **one variable**.

## The lever

When several legal actions are offered together, prefer the **earlier turn phase**:

- **draw before search** (reveal cards to yourself before you commit to a directed search),
- **attach energy / tool as the LAST setup action** before attacking (minimise irreversible
  commitment),
- **disruption / gusting before revealing strength** (force the opponent to decide under
  uncertainty).

It only **reorders legal actions**. It never changes *which* cards are played, never enables
an illegal pick, and is fully reversible (flag OFF ⇒ behaviour identical to v1).

## Knowledge OS heuristic it comes from

`knowledge/synthesis/heuristicas-computables.md` **§5 — "Ordenar el turno por fase + minimizar
commitment irreversible"** (concept `sequencing`, priority **P1**). The doc models the turn as a
queue ordered by a phase ordinal, tie-broken by EV:

```
PHASE = { draw_refresh:0, disruption_forcing_opp_decision:1, directed_search:2,
          reversible_setup:3, attach_energy_or_tool:4, attack:5 }
order_turn(actions) = sorted(actions, key=lambda a: (phase(a), -expected_value(a)))
```

The doc's own caveat (verified): the **method does not rotate with the meta** — it is mechanics
(Rule Box + imperfect info), not a card list — but the phase **predicates must be built from the
cabt option model**, not from the source. That is exactly what `_seq_phase()` does: it maps the
engine's generic `OptionType` (and, for `PLAY`, the card's generic text/`cardType`) to a phase
ordinal **with no reference to any Alakazam/Sabrina card id**. So the sequencing module is
reusable by **any** rule-based cabt pilot — a step toward a general "best PTCG player", not just
this archetype.

The doc also flags that §5's *Principle 3* (`opp_belief_uncertainty`) needs a real opponent
belief-model (heuristic #7, P2) — out of scope here. This lever implements the two cheap, robust
principles (draw-before-search, attach-energy-last) plus a conservative gust-before-reveal bias.

## Exact mechanism (why a NUDGE, not a hard reorder)

sabrina_v1 already emits one best-scored pick per engine `select`, and the engine drives the
phases by **re-asking**. So instead of replacing the selection loop, kb_seq **adds**

```
seq_bias(option) = SEQ_EPSILON * (PHASE_LATE - phase_ordinal(option))     # earlier => more
```

to each option's score, inside `AlakazamPolicy.rank()`. Two guards make this a pure tie-breaker
that can only ever **reorder already-wanted options**, never resurrect a rejected one:

1. The bias is applied **only to options whose base score is already > 0** (options v1 wants).
2. The bias goes into a **separate sort key**, NOT into the `scores` list that
   `normalize_selection` uses with its `s > 0` wanted-threshold. So the *set* of selected
   options (membership / minCount filling) is governed by v1's untouched `scores`; the bias only
   changes their **order**. ⇒ the lever changes ordering, never *which* cards are played.

`SEQ_EPSILON` (default **8**) is deliberately TINY relative to v1's score scale: card/play scores
live in the thousands and attack scores run ~1000–90000, so the term can only separate options of
otherwise-equal base score (e.g. two equally-ranked playable items, or play-vs-attach when both
look equal). It can never flip a real magnitude decision, never override a KO / lethal line, and
never make the agent play a worse card.

### Phase map (`_seq_phase`, archetype-agnostic)

| Phase (ordinal)            | How it's detected (generic only)                                   |
|----------------------------|--------------------------------------------------------------------|
| draw_refresh (0)           | `OptionType.ABILITY`; `PLAY` of a trainer whose text says "draw" (not "search") |
| disruption (1)             | `PLAY` of a trainer whose text gusts/switches the opponent's Active |
| directed_search (2)        | `PLAY` of a trainer whose text says "search your deck" / "look at"  |
| reversible_setup (3)       | `OptionType.EVOLVE`; `PLAY` of a Pokémon (bench); other trainers    |
| attach_energy_or_tool (4)  | `OptionType.ENERGY / ATTACH / TOOL_CARD / ENERGY_CARD`; `RETREAT`   |
| attack (5)                 | `OptionType.ATTACK`; `OptionType.END`                              |

No Sabrina/Alakazam card id appears anywhere in the phase logic — it keys only on `OptionType`,
`CardType`, and skill **text**. Drop the same module into another deck's agent and it works.

## Reversibility / flag

- `FMA_KB_SEQ` (default **1/ON**). Set `FMA_KB_SEQ=0` ⇒ `_seq_bias` returns 0 for every option,
  the sort key equals `scores`, and the agent collapses to **exactly v1** (verified in docker).
- `FMA_KB_SEQ_EPSILON` overrides the tie-breaker weight for A/B tuning (default 8).

## Smoke test (cabt = FILTER, not judge)

`_selfcheck.py`, run in the `ptcg-cabt` docker (linux/amd64) — 12 self-play games:

```
docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt python _selfcheck.py
```

**Result: PASS** — completed **12/12**, None-rewards **0**, policy_fallback **0**, obs_fallback
**0**, **fallback_rate 0.0**, deck = 60, 0 errors (1591 decisions, all `policy_ok`). This only
certifies the lever does **not crash and never emits an INVALID**. It does **not** say kb_seq "is
better": local self-play does not judge ladder value, and cabt here is a survival filter, not a
quality judge.

**The lever is LIVE, not dormant.** Instrumentation across the 12 games: of 8647 scored options
that reached `_seq_bias`, the bias was non-zero **6594** times. Unlike the A1 net-prize term
(which fires ~0× in a mono-single-prize mirror), sequencing has broad surface — it touches the
ordering of most turns, so the ladder A/B should produce a real signal (better, worse, or neutral
— unknown until run on ladder).

## A/B design

- **Baseline:** `sabrina_v1` (unchanged).
- **Variant:** `sabrina_kb_seq` — identical except the sequencing term.
- **One variable.** `diff sabrina_v1/main.py sabrina_kb_seq/main.py` is exactly: the
  `FMA_KB_SEQ` / `SEQ_EPSILON` / `_SEQ_PHASE_BY_OPTYPE` config, the `_seq_phase` / `_seq_bias`
  methods, and the separate-sort-key block in `rank()`. deck.csv, `cg/`, libcg.so byte-identical.

### A/B command (ladder is the judge; local cabt is only a filter)

Local filter (Wilson + TrueSkill), run from the project root:

```
docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt \
  python experiments/ab_harness.py agents_official/sabrina_kb_seq agents_official/sabrina_v1 200
```

The **real** A/B is the ladder: submit `sabrina_kb_seq` paired against `sabrina_v1` in a ladder
slot and compare scores. The cabt local result is a survival/sanity filter, **not** a verdict —
verified by the field that a 62%-local opt ended up *worse* on ladder.

## Honest limitations

- **cabt did not and cannot tell us kb_seq is "better."** It only confirmed it's crash-safe and
  that the term is live. Whether sequencing helps / hurts / is neutral on ladder is unknown until
  an actual ladder A/B.
- **Single-select granularity.** Because the engine re-asks per phase and v1 already picks one
  best option per select, the nudge mostly matters when *multiple comparable actions share one
  select* (e.g. several playable trainers at once). On selects with a clear magnitude winner it is
  a no-op — by design.
- **Conservative gust/search text predicates.** The PLAY-phase classifier reads card text
  ("draw" / "search your deck" / gust), so an oddly-worded card may land in the default
  reversible_setup phase (3). That only means *no* reorder for that card — never a wrong play.

## Status

- Agent dir: `agents_official/sabrina_kb_seq/`
- Smoke test: **PASS** (0 crashes / 0 INVALIDs / fallback_rate 0.0 / deck 60); lever LIVE
  (6594/8647 scored options biased).
- `submission.tar.gz`: **not built, not submitted.**
