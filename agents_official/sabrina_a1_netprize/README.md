# Sabrina A1 — net prize-trade

A **single-variable fork of `sabrina_v3`**. The only behavioural change vs v3 is one
additive penalty term in the attack-scoring function. Everything else (deck.csv, the `cg/`
engine, all four re-implemented ryota techniques, the survival scaffolding) is byte-identical
to v3. This makes A1-vs-v3 a clean A/B: one variable.

## What A1 is

In the score that picks which attack to use, A1 **subtracts** a penalty when, after our
attack, our own Active Pokémon would be **left in range of being KO'd by the opponent next
turn** AND our Active is worth **more than 1 prize** (an ex / Mega ex).

Intuition: don't volunteer a 2-prize body into an unfavourable prize trade. If attacking
exposes a 2-prize Pokémon to a KO, the opponent nets +2 prizes off us; A1 makes the agent
prefer a line that doesn't hand that over (a different attack, or — at the margin — not
committing the exposed body). This is the one edge-y idea here; ryota does not do it.

## Exact formula

In `AlakazamPolicy._score_attack`, on the **non-lethal** attack branch only:

```
score = 1000 + min(dmg, 320)            # base v3 scoring
... (Kadabra finisher / opp-KO bonuses, unchanged) ...
if not own_ko:                          # we are NOT taking a prize with this attack
    score -= A1_LAMBDA * prize_yield(our_active)   # ONLY IF the conditions below hold
```

`_a1_self_exposure_penalty()` returns `A1_LAMBDA * prize_yield` iff **all** hold:

1. `FMA_A1_NETPRIZE` flag is ON (default in this variant);
2. `prize_yield(our_active) > 1` — i.e. our Active is an ex (2) or Mega ex (3). `prize_yield`
   reuses v3's `prize_count` (3 if megaEx, 2 if ex, else 1);
3. our Active is **in KO range**: `opp_max_next_damage >= our_active.hp`.

`prize_yield` is the number of prizes the opponent takes by KO'ing our Active (1 / 2 / 3).

`opp_max_next_damage` = the **largest static base damage** among the opponent **Active**'s
attacks (`ATTACK_DAMAGE`, built once from the engine's `all_attack()` data), after applying
our Active's **weakness** (×2) / **resistance** (−30) vs the opponent's energy type.

It is **deliberately conservative / under-counting**:
- only the opponent's **Active** is considered (a benched attacker would have to retreat or be
  gusted in first — we don't assume the opponent sets that up);
- **scaling / effect** attacks (Powerful Hand, "X damage per energy", counter-placement) have
  `damage = 0` in the static table, so they're treated as 0 incoming. We therefore **never
  over-estimate** the opponent and never veto a play on a guess — at worst A1 fails to fire
  when a scaling attacker could in fact KO us. This was the safe direction to err: A1 should
  only ever *discourage* a clearly-bad exposure, never block a good line.

Our Active's HP "after our attack" is taken as its **current HP** — on our own turn our Active
takes no damage, so its HP entering the opponent's turn equals its current HP.

A1 is **skipped when our attack itself KOs the opponent** (`own_ko`): if we're already taking
a prize this turn, this isn't the unfavourable one-sided trade A1 targets. It is also never
applied to the same-turn **winning / lethal** path (`90000`), which returns before the term.

## Lambda — value and why

`A1_LAMBDA = 600` per prize (env-overridable via `FMA_A1_LAMBDA`).

The attack scores in `_score_attack` live on a `~1000 + min(dmg, 320)` scale: a normal attack
scores ~1000–1320; a same-turn lethal jumps to `90000` (or `+2500 + prizes*200` for a KO).
At λ=600, a 2-prize exposure costs **1200** points — enough to flip the choice between two
**non-lethal** attacks (or attack-vs-pass on the margin), but far too small to override any
KO / winning play (those are an order of magnitude higher and A1 doesn't touch them anyway).
It's a deliberately conservative first cut; the right way to tune it is the A/B on ladder, not
local self-play (which can't judge ladder value — see limitations).

## A/B design

- **Baseline:** `sabrina_v3` (unchanged).
- **Variant:** `sabrina_a1_netprize` — identical except the A1 term.
- **One variable.** `diff sabrina_v3/main.py sabrina_a1_netprize/main.py` is exactly: the
  `ATTACK_DAMAGE` map, the `FMA_A1_NETPRIZE` / `A1_LAMBDA` config, the two A1 helper methods,
  and the `score -= self._a1_self_exposure_penalty()` line. deck.csv, `cg/`, libcg.so byte-identical.
- The flag (`FMA_A1_NETPRIZE`, default ON; set `=0` to disable) lets you neutralise the term
  in-place to confirm the variant collapses to v3 behaviour.

## Smoke test (cabt = FILTER, not judge)

`_selfcheck.py`, run in the `ptcg-cabt` docker (linux/amd64) — 12 self-play games:

```
docker run --platform=linux/amd64 --rm -v "$PWD":/work -w /work ptcg-cabt python _selfcheck.py
```

Result: **PASS** — completed 12/12, None-rewards 0, policy_fallback 0, obs_fallback 0,
**fallback_rate 0.0**, deck = 60, 0 errors. This only certifies the term does not crash and
never emits an INVALID. It does **not** say A1 "is better" — local self-play does not judge
ladder value, and cabt here is a survival filter, not a quality judge.

## Honest limitations — does A1 actually fire?

**In our own deck, A1 is a near-dormant term, and this is the headline caveat.**

The engine's card data (verified, not assumed) shows that in our 60-card list the **only**
multi-prize body is **Fezandipiti ex (id 140, 2 prizes)**. Critically, **our main attacker
Alakazam (id 743) is `ex = False` → 1 prize** in this engine. So A1's `prize_yield > 1` gate
is satisfied **only when Fezandipiti ex is our Active and attacking** — and Fez is a bench
ability body (Flip the Script) that is rarely sent Active and rarely attacks.

Measured: across the 12 self-play games (49 attack-score evaluations), the A1 penalty fired
**0 times**. The logic is correct (unit-tested below), it simply has almost no surface in a
mono-Alakazam mirror where the Active is essentially always a 1-prize body.

Unit tests (synthetic states, in docker) confirm the term **does** fire when its conditions
hold, so it is live code, not dead:

| Our Active            | Opp Active        | Our HP | Incoming (est) | Penalty |
|-----------------------|-------------------|--------|----------------|---------|
| Fezandipiti ex (2 pz) | Mega Dragonite ex | 100    | 330 (in range) | **1200** |
| Fezandipiti ex (2 pz) | Leafeon           | 40     | 70 (in range)  | **1200** |
| Fezandipiti ex (2 pz) | Leafeon           | 200    | 70 (safe)      | 0.0     |
| Alakazam (1 pz)       | Mega Dragonite ex | 100    | 330            | 0.0     |
| Fezandipiti ex, flag OFF | Mega Dragonite ex | 100 | 330            | 0.0     |

This matches the prior memory note that net-prize-trade "muerde poco en mono-single-prize" —
and here it's sharper than expected: because Alakazam reads as 1-prize in this engine, A1 only
has a handle on the Fezandipiti-ex edge case. The honest expectation is that **A1 changes our
behaviour very rarely vs v3**, so on ladder it should be close to a no-op for our deck — the
value, if any, is purely in those rare spots where a 2-prize body is forced Active and exposed.

Two further honest caveats:
- **Conservative incoming-damage estimate** under-counts scaling/effect attackers (treated as
  0), so A1 can miss a real exposure. Chosen to avoid false vetoes; documented above.
- **cabt did not and cannot tell us A1 is "better."** It only confirmed it's crash-safe. Whether
  A1 helps, hurts, or is neutral on ladder is unknown until an actual A/B is run on ladder.

## Status

- Agent dir: `agents_official/sabrina_a1_netprize/`
- Smoke test: PASS (0 crashes / 0 INVALIDs / fallback_rate 0.0 / deck 60).
- `submission.tar.gz`: **built, NOT submitted.**
