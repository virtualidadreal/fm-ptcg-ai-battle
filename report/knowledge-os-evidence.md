# Knowledge OS Evidence Appendix

> This file is **outside the 2000-word report limit** (per the deliverable rules). It backs the "Knowledge OS" claims in `REPORT.md` (the adversarially-distilled knowledge base referenced in §2 methodology and §6 deck concept) with the same claim-by-claim discipline as `methodology-evidence.md`.
>
> Confidence legend: **verified** = traceable to a primary repo artifact (`knowledge/synthesis/*.md`, `knowledge/free/*.md`, `knowledge/SOURCES.md`). **probable** = recorded in the distillation notes / verifier verdicts, not re-derived from an independent primary source.
>
> Thesis of this appendix: the Knowledge OS is a **methodological asset (70%)**, not a content dump. It is the same anti-false-positive discipline the report applies to A/B testing — *paired, Wilson-gated, N≥60* — applied to **knowledge**: 30 extraction agents proposed claims, an adversarial verifier pass tore down 6 fabrications before any heuristic was trusted. It also underwrites the **deck concept (20%)**: the single-prize Alakazam choice has the net-prize edge *baked into the deck* (A1 inert is the proof, not a defect), and the distilled decision tree (H1–H9) is the structural backing for "consistency-first, not glass-cannon."

---

## A. The distillation protocol (what the Knowledge OS is)

| Claim | Detail | Source | Confidence |
|---|---|---|---|
| Two-tier KB: 12 free sources distilled + 4 paid sources scoped (none ingested) | `knowledge/free/*.md` (12 fichas) → `synthesis/heuristicas-computables.md` (H1–H9) + `synthesis/reward-spec.md` (R1–R7); paid tier = acquisition *plans*, not data | `knowledge/SOURCES.md`; `knowledge/synthesis/INDEX.md` §1 | verified |
| Extraction was fan-out (many agents propose) → adversarial verify (verdicts gate) → synthesize | "fuentes: knowledge/free/*.md (12 fichas) + **verdicts del verificador adversarial**" | `synthesis/heuristicas-computables.md` frontmatter (`fuentes:` line); `INDEX.md` (curaduría final) | verified (the verifier-verdicts provenance is stamped in the synthesis frontmatter) |
| No paid source was bought; what would enter the KB is *distilled heuristic*, never the literal paid material | "Estado de los 4 planes de pago: NINGUNO comprado"; "Lo que entra al KB si se compra es heurística destilada, nunca el material literal de pago" | `INDEX.md` §1; `SOURCES.md` paid tier | verified |
| The KB's own bottleneck verdict is honest: "the bottleneck is NOT lack of knowledge, it's implementation" (H1 still inert) | "El cuello de botella hoy NO es falta de conocimiento, es implementación" | `INDEX.md` §3 | verified |

**Why this is methodology, not trivia.** The discipline is identical to the report's A/B protocol: a cheap, high-recall proposal step (extraction agents / local A/B) that is **never trusted on its own**, gated by an adversarial judge (verifier verdicts / the ladder + Wilson). The KB explicitly downgrades unverifiable claims to caveats rather than shipping them — the same "confess the gap before risking credibility" stance as `methodology-evidence.md`'s honesty ledger.

---

## B. The 6 fabrications the verifier caught (anti-false-positive applied to knowledge)

These are the claims the extraction agents surfaced that the adversarial pass **tore down before they reached the synthesis layer**. Each is now logged as a do-not-replicate. This is the strongest single piece of evidence that the Knowledge OS is a rigor instrument: a less disciplined KB would have shipped all six as facts.

| # | The fabrication (as proposed) | Why it was false / the correction | Source | Confidence |
|---|---|---|---|---|
| 1 | **Fake Flipside citation** — a ficha attributed to Flipside the claim that "role is intrinsic to the deck's design" | The quote **does not exist in the source**. `matchup_fav` must be treated as a reorderable prior, never a fixed truth dressed in a citation | `heuristicas-computables.md` H8 caveat; `INDEX.md` §5; `SOURCES.md` row 8 | verified |
| 2 | **Klaczynski misattribution** — "Consistency is the goal" attributed to Klaczynski (3× world champion) | It is from a **third-party 60cards author** analyzing his own deck, not Klaczynski. Use the structure, discard the inflated credential | `heuristicas-computables.md` H9 caveat; `INDEX.md` §5 | verified |
| 3 | **Players ↔ games conflation** — "18,537 players" presented as games | 18,537 *players* ≠ *games*; real games ~41,105. A category error that would have poisoned any share/weight derived from it | `heuristicas-computables.md` meta-section "Errores verificados"; `INDEX.md` §5 | verified |
| 4 | **Prior that doesn't sum to 1** — a `meta_prior` distribution with an arbitrary `+0.40` filler in "other" | A probability distribution that doesn't normalize is not a prior. Flagged as not-hardcodable; in cabt the prior is **measured in-engine** | `heuristicas-computables.md` meta-section; `INDEX.md` §5 | verified |
| 5 | **Limitless "official TPCi partner"** — inflated credential to borrow authority | **Limitless's own footer disproves it.** The credential was used to launder the share data's authority; removed | `heuristicas-computables.md` meta-section ("su propio footer lo desmiente"); `INDEX.md` §5 | verified |
| 6 | **Counter Catcher card text mis-cited** — the tempo ficha cited a specific "Counter Catcher PAR 160" with wrong/over-specific text | The *legality pattern* (Item, legal only when `my_prizes > opp_prizes`) is the invariant that transfers; the **specific card text was wrong** and the exact equivalent may not exist in the cabt pool. Implement the pattern, not the quote | `heuristicas-computables.md` H3 caveat ("el equivalente exacto de Counter Catcher en cabt puede no existir o llamarse distinto"); `tempo.md` → H3 | verified |

**Honest scope of this list.** Items 1, 2, 5, 6 are *attribution/text* fabrications (false provenance or false card text). Items 3, 4 are *data-integrity* fabrications (a category error and a non-normalized prior). All six are recorded verbatim as do-not-replicate in `heuristicas-computables.md` and `INDEX.md` §5. A separate class of *soft* defects — stubbed functions presented as runnable code (`meta_distribution()`, `infer_archetype()`, `est_turns_to_first_ohko()`), and **invented weights** (`deck_function_score` 1.0/0.5/0.3/0.2/−0.5) — was also flagged but is **not counted among the 6**, to keep the taxonomy clean (same anti-inflation rule the report applies to the "3 NO-GOs" count).

---

## C. The 9 computable heuristics (map + transfer status)

The free tier distilled to **9 heuristics**, each with pseudocode, the cabt state it touches, a P0/P1/P2 priority, and an explicit ⚠️-rota flag for meta-dependence. This is the structural backing for the deck concept's "concepts over lists" stance.

| H | Heuristic | Concept | Prio | Transfers to cabt? | Maps to deck claim |
|---|---|---|---|---|---|
| H1 | **Net prize value of a KO** (not binary): `net = PRIZE_VALUE[target] − p_returned·PRIZE_VALUE[mine]` | prize-trade | P0 | ✅ invariant | The **edge baked into single-prize Alakazam**: a 1-prize attacker can never trade down. A1 has this built but **inert** because there is nothing to penalize (§7) |
| H2 | **Penalize exposing an attacker in KO range** | prize-trade + reading | P0 | ✅ invariant | The other half of prize-trade; single-prize shells minimize this exposure by construction |
| H3 | **Counter Catcher / "behind" as conditional advantage** (public prize counter → hard guard) | tempo | P0 | ✅ pattern (map card to cabt pool) | Fabrication #6 lives here; ship the pattern, not the card |
| H4 | **Belief-state of prized cards** (hypergeometric over unseen pool) | prize-checking | P1 | ✅ formula | Same hypergeometric family as the mulligan math in §6 |
| H5 | **Order the turn by phase + minimize irreversible commitment** | sequencing | P1 | ✅ method (predicates built from cabt pool) | "draw before search, attach last" — piloting discipline, the gap NO-GO 3 exposed |
| H6 | **Mulligan / consistency as deckbuild gate**: `P(mull)=C(60−K,7)/C(60,7)` | consistency | P1 | ⚠️ partial (math transfers, "8–12 basics" threshold rotates) | **Direct backing for the §6 lever**: `sabrina_cons` 8→12 basics, 34.64%→19.06% mulligan. The *math* transfers; the threshold is derived from the cabt pool, not copied |
| H7 | **Bayesian belief over opponent archetype** | reading + archetypes | P2 | ⚠️ method yes, numbers no | Fabrications #1, #3, #4, #5 cluster here (the meta-share layer) |
| H8 | **Dynamic BEATDOWN vs CONTROL role assignment** | archetypes | P2 | ⚠️ partial | Fabrication #1 (fake Flipside) lives here |
| H9 | **Reklev pruning + 10-game rule + setup gate** | deckbuilding | P2 | ✅ method (cited weights invented → recalibrate) | Fabrication #2 (Klaczynski) lives here |

**The 5 highest-value heuristics**, in implementation order, are H1→H2→H3→H4→H5 (`INDEX.md` §2): selected for *real edge over a baseline* (not table-stakes) and for *not depending on rotating meta*. P0 (H1–H3) is the prize-trade core.

**Table-stakes vs real edge (honest separation).** The KB explicitly separates what any decent engine already does (count prizes, sum damage, assign prize_yield 1/2/3, check legality — *Leon v1 already does this*) from where games are actually won (net-trade valuation, exposure penalty, behind-state tempo, belief-state). This is the same "the public notebooks are a floor everyone reaches by forking" argument the report's §2 makes about methodology — here applied to knowledge.

---

## D. The transfer caveat — cabt ≠ Standard (the load-bearing honesty marker)

| Claim | Detail | Source | Confidence |
|---|---|---|---|
| cabt's pool (~2000 cards, adjusted rules) is **NOT** full Standard | "El pool de cabt (~2000 cartas, reglas ajustadas) NO es Standard completo" | `heuristicas-computables.md` CAVEAT section; `INDEX.md` frontmatter `caveat_global` | verified |
| Meta-specific content does **not** transfer and **can be actively misleading** | Limitless/Trainer Hill shares, Dragapult/Raging Bolt lists, Charizard 4-1-3 skeletons, COPY_PRIOR counts ("Rare Candy 3-4") | `heuristicas-computables.md` CAVEAT + ⚠️ META section | verified |
| What **does** transfer: mechanical invariants | prize-trade math, hypergeometric prize-checking/consistency, public prize-counter legality, sequencing phase order, Bayesian belief over archetype/prizes | `heuristicas-computables.md` CAVEAT ("Qué SÍ transfiere") | verified |
| Rule of gold: any meta-dependent number is **read from the live cabt meta (measured in-engine)**, never from the cited ficha | applies to shares, matchup matrix, skeletons, going-first/second edges, magic thresholds (0.15, HP≤60) | `heuristicas-computables.md` "Regla de oro" + ⚠️ META list; `INDEX.md` frontmatter | verified |

**Why this caveat *is* the methodology.** The same structural mismatch the report proves on the ladder (§5: "the metric is a tail quantile, the proxies measure a mean") has a knowledge-layer twin: **human-Standard meta data measures a different game than cabt.** Importing Standard shares would be the knowledge-layer equivalent of maximizing `cabt`-vs-first-legal (anti-predictive, ρ=−0.80). The KB refuses to hardcode a single rotating number for exactly the reason the report refuses to trust a single local proxy. The deck concept therefore leans on **transferable invariants** (the hypergeometric mulligan math, the net-prize logic baked into single-prize) and treats the Standard-meta corroboration as a *prior*, never a verdict — consistent with `STRATEGY-PLAN.md` §1's "external data: bajo ROI, no pipeline."

---

## E. How this reinforces the two graded axes

**70% methodology.** The Knowledge OS demonstrates the report's central virtue — anti-false-positive discipline — on a *second, independent surface*. Not only does the A/B harness refuse to ship local false positives (the N<60 gate, the Wilson interval), the knowledge layer refuses to ship *epistemic* false positives (6 fabrications killed, stubs and invented weights flagged, every meta number gated behind in-engine measurement). One discipline, two domains. That is harder to fake and harder to copy than any win-rate.

**20% deck concept.** The single-prize Alakazam choice is not an aesthetic preference; it is the H1/H2 prize-trade logic resolved *at deckbuild time*. A single-prize attacker has the net-prize edge **structurally baked in** — it can never trade a 2-prize body into a 1-prize body. A1 (the net-prize lever) firing **0 times in 49 attack evaluations** (REPORT §7) is the positive proof: the edge is already in the deck, so the runtime penalty has nothing to penalize. The distilled decision tree (H6 mulligan math, H5 sequencing, H8 role assignment) is the structural backing for "consistency-first, not glass-cannon," and the cabt≠Standard caveat is exactly why the report cites the d22 *in-engine* meta (`_meta_d22.log`, 30.4%/58.2%/n=395) as the live figure and the Standard snapshot only as corroboration.

## F. Video enrichment — primary transcripts, and the adversarial gate catching a *curator* error

The distillation ran a second pass over expert video. The methodology point is not the content but that **the same adversarial-verify gate caught a mis-attribution twice**, on independent runs.

- **First pass (24 jun, `knowledge/free/video-enrichment-2026-06-24.md`):** 4 primary transcripts (whisper/captions) upgraded three heuristics — **H1b** prize-map as an adaptive 6-prize plan (CFB Edge / Isaiah Bradner), **H4b** prize-checking as a two-event belief update (CFB Edge), **H5+** sequencing detail (Play! Pokémon official). The gate discarded video `nPN8G1em4QQ` after reading it: the curator labeled it "Tricky Gym" but it is a beginner channel — descoped, not distilled.
- **Second pass (25 jun, `knowledge/free/video-tier3-enrichment-2026-06-25.md`):** Tier-3 (Worlds finals + control archetypes), feeding H7 (archetype/outs belief), H8 (BEATDOWN↔CONTROL), and anti-deck-out control. Captions were obtained via `yt-dlp` for **4 of 5** sources (attribution confirmed by oEmbed); the fifth (Worlds 2023, `Idx-R5lpx70`) had **no captions** and is marked `obtained=false` — not fabricated from the title. The gate again caught a curator error: `yZki7OdJY7A`, listed as a "Tord Reklev deck-tech", is in fact a **Pete's Packs unboxing with zero gameplay reasoning** ("I don't know a ton about the way Pokémon works now") — descoped, exactly like the Tricky Gym catch. Honesty markers: raw transcripts are **not committed** (copyright), only the distillation; quotes are caption-level, not human transcription; card examples rotate, methods transfer.

The recurring catch is the asset: a fan-out across noisy sources, gated by an adversarial pass that reads the primary before trusting the curator. The same discipline, a third surface.

---

## Known gaps (honesty ledger)

1. The "30 extraction agents" headcount is a process figure from the distillation run; the synthesis frontmatter stamps the *provenance* (free fichas + verifier verdicts) but not an agent-by-agent log. The **6 fabrications and their corrections are the verifiable artifact** — each is recorded verbatim in `heuristicas-computables.md` and `INDEX.md` §5. Cite the fabrications, not the headcount, as the load-bearing evidence.
2. The heuristics are **distilled-but-not-all-implemented**: H1 is built-but-inert in `sabrina_a1_netprize`, half-present in `leon_v1_5`; H2–H5 are partially scaffolded; H7–H9 require an in-engine-measured belief-state that does not yet exist (`INDEX.md` §4). The KB is honest that its bottleneck is implementation, not knowledge. The report must not claim any heuristic as a *ladder-validated* win — only A1's inertness (§7) is a measured result.
3. Paid-tier verdicts are **plans, not data** (none purchased; paywalls return 403). No claim in the report depends on paid content.
4. The cabt≠Standard caveat is a *qualitative structural* claim (the pool differs, ~2000 cards, adjusted rules) — it is not a quantified per-card diff of cabt vs Standard. It is used as a discipline (measure in-engine), not as a measured delta.
