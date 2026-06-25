# REPRODUCE.md — primary-artifact runners for the engine-gated claims

Several methodology figures in `report/methodology-evidence.md` are marked
`probable (only in memory)` because no primary log was saved. They are
**engine-gated**: reproducing them requires stepping the game engine
(`cg/libcg.so`, x86-64 Linux ELF — does **not** load on macOS/arm). This file
gives the EXACT commands to regenerate each one on a Linux host (or the
`ptcg-torch` Docker image), so the figure can be promoted from `probable` to a
saved primary artifact.

Convention: run from repo root. The Docker image `ptcg-torch` is built from
`Dockerfile.torch` and carries `kaggle_environments` + the `cabt` environment +
`libcg.so`. CPU host is fine; `FMA_MCTS_ON=1` enables the ISMCTS path.

```bash
# build once
docker build -f Dockerfile.torch -t ptcg-torch .
RUN="docker run --rm -v $PWD:/w -w /w ptcg-torch"
```

---

## 1. AGREEMENT-with-top-pilots  (RESOLVED: v1 21.33% / v2 21.17% — old memory 43.52/43.84 was wrong)

Status: **engine-gated, now RESOLVED & verified** (see box below). The offline probe `research/agreement_top_pilots.py`
PROVES the policy imports and runs on a replay obs without the `.so`, but the
policy keys its heuristics on the engine card DB (`lib.AllCard`/`lib.AllAttack`:
per-card attackId arrays, attack energy-costs, skill text). `card_db.json` has
no `attackId` field, so with the stub the policy runs against an EMPTY DB and is
a DIFFERENT policy — its offline proxy was **20.61%** (1252 decisions, NOT the
real number). The faithful figure needs the real DB:

```bash
# Faithful agreement of sabrina_v1 against the top-pilot replays.
# --faithful drops the cg.sim stub so the REAL libcg.so card DB loads.
$RUN python research/agreement_top_pilots.py --faithful

# For the v1-vs-v2 contrast (RESOLVED to 21.33 vs 21.17), point the same script at each
# agent dir. Both share piloting code; only deck.csv differs, so the agreement
# means should nearly coincide (that is the "blind" finding). To do v2, copy the
# script with AGENT_DIR -> agents_official/sabrina_v2, or parametrize it:
#   AGENT_DIR=agents_official/sabrina_v2 $RUN python research/agreement_top_pilots.py --faithful
```

RESOLVED (25 jun, ptcg-torch, faithful run, 0 crashes): **v1 = 21.33% (267/1252)
/ v2 = 21.17% (265/1252)**, saved as `research/agreement_v1_faithful.json` /
`agreement_v2_faithful.json`. The old memory figure 43.52/43.84 was IN ERROR;
the faithful engine run is ~21.3%/21.2%. The qualitative finding HOLDS and is
stronger: the two means coincide to **0.16pp** while the ladder separates them
by 104 points — agreement (a mean) is blind to the card-list tail the ladder
grades. Claim promoted `probable` → `verified` in `methodology-evidence.md`.
The script now reads `AGENT_DIR` from env (default sabrina_v1).

---

## 2. PANEL Track F  (+0.20 correlation, head inversion)

Status: **engine-gated**. Track F ranks agents by win-rate against a fixed PANEL
of opponent decks; producing those win-rates requires `env.run` games (engine).
There is no offline panel-sample artifact in the repo (`experiments/panel_dl/`
is empty). To regenerate the panel ranking:

```bash
# ab_harness real signature:  --panel <dirA> <rival1> <rival2> ...  [--games N]
# (run_panel runs A vs each rival under one shared TrueSkill env). Run each
# candidate as A against the SAME panel of rivals, rank by aggregate, then
# correlate that ranking vs the ladder ranking.
PANEL="agents_official/sabrina_v3 agents_official/leon_v1_5_prizeaware agents_official/mega_starmie_v1 agents_official/sabrina_cons"
for AG in sabrina_v1 sabrina_v2 ; do
  $RUN python experiments/ab_harness.py \
      --panel agents_official/$AG $PANEL --games 200 \
      > experiments/panel_${AG}.txt
done
# Then compute Spearman(panel_rank, ladder_rank); the claim is rho≈+0.20 with the
# ladder-#1 (v1) landing panel-#3 and ladder-#3 (v2) landing panel-#1 (inversion).
```

(If `ab_harness.py` lacks a literal `--panel` flag, loop `bcil/ab_json.py` over
each `ptcg-abc/agents/*/` dir as opponent B and aggregate — see §3 form.)

---

## 3. A/B win-rates: seeds-mirage N=60, greedy BC N=150, ISMCTS 0/15

Status: **engine-gated** (each requires `kaggle_environments.make("cabt")` +
`env.run`, i.e. an engine step per move). Runner = `bcil/ab_json.py`
(`python bcil/ab_json.py <dirA> <dirB> <games> [seed_base]`, emits one
`JSON_RESULT` line; per-game seed = seed_base+g for independent reproducible
workers).

### 3a. Seeds mirage (first-20 65% -> N=60 corrects to ~40%)
```bash
# Leon v3 (BC prior + ISMCTS) vs Leon v1. The "mirage" is that the first 20
# seeds read 65% but N=60 collapses to ~40%. Reproduce by running 60 and
# inspecting the running scoreboard (stderr) to see the early-20 vs full split.
FMA_MCTS_ON=1 $RUN python bcil/ab_json.py \
    agents_official/leon_v3_bc agents_official/leon_v1_5_prizeaware 60 0
# primary full-budget log already saved: bcil/_fullbudget_ab_20260622_1845.log (18/60 = 22%)
```

### 3b. Greedy BC, N=150  (BC greedy policy vs Leon v1)
```bash
# Pure BC greedy (no search): leon_v3_bc is the greedy encoder+net policy.
$RUN python bcil/ab_json.py \
    agents_official/leon_v3_bc agents_official/leon_v1_5_prizeaware 150 0
```

### 3c. ISMCTS 0/15  (ISMCTS agent — 0 wins in 15)
```bash
# agent_ismcts is Leon v2 (search + net), gated behind FMA_MCTS_ON=1.
FMA_MCTS_ON=1 $RUN python bcil/ab_json.py \
    agent_ismcts agents_official/leon_v1_5_prizeaware 15 0
```

For all of §3, save the emitted `JSON_RESULT {...}` line into
`bcil/_<claim>_<date>.log` and cite it as the primary artifact in
`report/methodology-evidence.md`, replacing `probable (only in memory)`.

---

## What is ALREADY reproducible offline (no engine)
- Spearman rho = −0.80  →  `research/correlation.py`
- Mulligan hypergeometric 34.64% / 19.06%  →  `agents_official/sabrina_cons/main.py`
- d22 meta 30.4% / 58.2% / matchups  →  `_meta_d22.log`
- AGREEMENT offline INSTANTIATION proof (policy runs on replay obs w/o `.so`)
  + DB-degraded proxy 20.61%  →  `research/agreement_top_pilots.py`
