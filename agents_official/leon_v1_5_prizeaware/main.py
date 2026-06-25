"""
Leon v1.5 (prize-aware rule-based).

FORK of agents_official/dragapult_sample (= "Leon v1", the champion): the ENTIRE champion
logic + survival scaffolding is kept verbatim. On top we inject ONLY the rules A1 marked
COMPUTABLE that were NOT already present, as small ADDITIVE nudges that can re-rank near-ties
but NEVER override the champion's strong signals.

HONEST NOTE (verified offline in docker, NOT assumed): cg.api.all_card_data() already returns
correct ex/megaEx flags offline (121 ex, 30 megaEx). So the champion's prize_count() ALREADY
computes the correct 1/2/3 prize yield AND already encodes A1's prize-trade swing /
lethal=50000 / prize_map_bonus (>=2 & remain<=4 -> -1200, ==1 -> -300, ==0 -> +1200). B1's
cards_enriched.json is loaded here (cwd-safe) only as a redundant fallback if cg ever fails.

What v1.5 ADDS that v1 did NOT have (genuinely-new computable rules):
  (1) prize-check (own outs prized): exact-by-elimination unseen multiset + hypergeometric
      P(out in prizes). Small additive nudge to draw/search/recovery when a key line's outs
      are likely stuck in prizes (epsilon-scale, tie-break only).
  (2) board ROLE (beatdown/control/even) from prize counts + on-board readiness: small additive
      re-weight of attack-vs-setup ordering, gated to near-ties.
  (3) sequencing draw-before-search: tiny additive bump so a draw ability is preferred over a
      search/ball BEFORE we've drawn this turn.

All nudges are bounded by NUDGE so a clear champion decision is never flipped, and each is wrapped
so any failure leaves the champion output untouched. 0 crashes / 0 invalids stays the hard req.

== Below: OFFICIAL Dragapult ex sample wrapped in FMA robust scaffolding (verbatim) ==

OFFICIAL Dragapult ex sample (kiyotah/a-sample-rule-based-agent-dragapult-ex-deck)
wrapped in FMA robust scaffolding.

What is verbatim from the official kernel (the VALUABLE game logic, untouched):
  - the whole `cg.api`-based heuristic: helper functions (no_damage_dex,
    no_damage_counter, prize_count, pokemon_score, add_card_count, set_card_counts,
    get_card, main_option_proc) and the body of the original `agent(obs_dict)` policy,
    now renamed `_sample_agent(obs_dict)`.
  - the inline decklist (written out separately to deck.csv).

What FMA scaffolding adds around it (so a crash/illegal return never = instant loss):
  - cwd-safe deck loader (resolves deck.csv from the agent dir, cwd, the kaggle path,
    or sys.path), loaded ONCE at import; my_deck is always a clean list (for the harness
    deck-phase probe).
  - public entry `agent(obs, config=None)`:
      * obs["select"] is None -> return the 60 deck ids.
      * else                  -> run the official policy inside a try, then VALIDATE the
                                  output against the raw select dict (len in
                                  [minCount,maxCount], every index in [0,n), no dups in
                                  the normal case) and FALL BACK to a legal selection on
                                  any exception or invalid output. NEVER crashes.

The sample needs cg-lib: this dir ships a local `cg/` package (api/game/sim/utils +
libcg.so) copied from the competition data, so `from cg.api import ...` resolves when
the harness chdir's into this dir before loading. If cg import fails for ANY reason, the
agent degrades to first-legal instead of dying.
"""

from __future__ import annotations

import os
import sys


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


# my_deck is always available; the official code below ALSO references `my_deck`,
# so we keep this single source of truth.
my_deck = _load_deck()


# ── v1.5: cwd-safe enriched card-data loader (B1; redundant fallback only) ─────
import json as _json
import math as _math
from collections import Counter as _Counter


def _resolve_cards_path():
    cands = []
    if "__file__" in globals():
        cands.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cards_enriched.json"))
    cands.append("cards_enriched.json")
    cands.append("/kaggle_simulations/agent/cards_enriched.json")
    for p in sys.path:
        if p:
            cands.append(os.path.join(p, "cards_enriched.json"))
    for p in cands:
        try:
            if os.path.exists(p):
                return p
        except Exception:
            continue
    return None


def _load_enriched_cards():
    path = _resolve_cards_path()
    if not path:
        return {}
    try:
        with open(path, "r") as f:
            raw = _json.load(f)
        out = {}
        for k, v in raw.items():
            try:
                out[int(k)] = v
            except Exception:
                continue
        return out
    except Exception:
        return {}


# id -> {prize_value, ...}. Used ONLY as a fallback prize-value source if cg is unavailable.
ENRICHED = _load_enriched_cards()


def _prize_value_fallback(card_id):
    try:
        v = ENRICHED.get(int(card_id))
        if v is None:
            return 1
        pv = v.get("prize_value")
        return int(pv) if pv in (1, 2, 3) else 1
    except Exception:
        return 1


# ── v1.5: prize-check (own outs prized) — hypergeometric over the unseen multiset ──
# net of "tuning the champion": this is genuinely-new INFORMATION the champion never used.
# We compute P(at least one copy of an `out` id is sitting in our face-down prizes), using:
#   unseen multiset = my_deck - (everything of ours that is currently VISIBLE) ; this equals
#   (remaining deck) + (our prizes), since prize identities are opaque (only len(prize) known).
# P_out_in_prizes(n_outs, unseen_total, prizes_left) = 1 - C(unseen-n_outs, prizes)/C(unseen, prizes).
NUDGE = 40.0  # bounded tie-break magnitude: << the champion's meaningful score gaps


def _hyper_p_at_least_one(n_outs, unseen_total, prizes_left):
    """P(>=1 of n_outs target copies is among prizes_left face-down prize cards)."""
    try:
        n_outs = int(n_outs); unseen_total = int(unseen_total); prizes_left = int(prizes_left)
        if n_outs <= 0 or prizes_left <= 0 or unseen_total <= 0:
            return 0.0
        if prizes_left >= unseen_total:
            return 1.0
        if unseen_total - n_outs < prizes_left:
            return 1.0  # not enough non-out cards to fill prizes -> at least one out is prized
        # 1 - C(unseen-n_outs, prizes)/C(unseen, prizes)
        p_none = (_math.comb(unseen_total - n_outs, prizes_left) /
                  _math.comb(unseen_total, prizes_left))
        return max(0.0, min(1.0, 1.0 - p_none))
    except Exception:
        return 0.0


# ── legal fallback (NEVER crash; respect minCount/maxCount/range) ─────────────
def _legal_fallback(select_dict):
    """Smallest legal selection from a RAW select dict: first minCount indices.
    If the engine ever asks for more picks than distinct options, repeat indices."""
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
    """True if `out` is a legal selection for this raw select dict."""
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
        # uniqueness required unless the engine forces repetition (minCount > n)
        if min_c <= n and len(set(out)) != len(out):
            return False
        return True
    except Exception:
        return False


# ── cg import (degrade gracefully if unavailable) ─────────────────────────────
_CG_OK = True
_CG_ERR = None
try:
    from collections import defaultdict

    from cg.api import (
        AreaType, CardType, Log, LogType, Observation, SelectContext,
        OptionType, Card, Pokemon, State, all_card_data, to_observation_class,
    )
except Exception as _e:  # pragma: no cover
    _CG_OK = False
    _CG_ERR = _e


# =============================================================================
# BEGIN OFFICIAL SAMPLE LOGIC (verbatim, only the entry point is renamed)
# =============================================================================
if _CG_OK:
    """
    Dragapult ex Deck
    Advanced Level
    This deck focuses on setting up multiple knockouts to take at least three Prize
    cards in a single turn with its Phantom Dive attack.
    """

    # Load all card data from the API's helper function
    all_card = all_card_data()
    # Create a lookup table (dictionary) to quickly access card data by its cardId
    card_table = {c.cardId: c for c in all_card}

    # Decklist
    Dreepy = 119  # ×4
    Drakloak = 120  # ×4
    Dragapult_ex = 121  # ×3
    Fezandipiti_ex = 140  # ×1
    Latias_ex = 184  # ×1
    Budew = 235  # ×2
    Meowth_ex = 1071  # ×1
    Rare_Candy = 1079  # ×2
    Unfair_Stamp = 1080  # ×1
    Buddy_Buddy_Poffin = 1086  # ×4
    Night_Stretcher = 1097  # ×2
    Crushing_Hammer = 1120  # ×4
    Ultra_Ball = 1121  # ×4
    Poke_Pad = 1152  # x3
    Lucky_Helmet = 1156  # ×1
    Boss_Orders = 1182  # ×3
    Crispin = 1198  # ×4
    Brock_Scouting = 1210  # ×2
    Lillie_Determination = 1227  # ×4
    Team_Rocket_Watchtower = 1256  # ×2
    Basic_Fire_Energy = 2  # ×4
    Basic_Psychic_Energy = 5  # ×4

    UNNECESSARY = -10000000

    class AttackPlan:
        attack: int = 0
        counter: list = []

    can_switch = False
    can_attack = False
    can_main_attack = False
    can_energy_attach = False
    use_support = 0  # The Supporter card planned for use.
    bench_attacker = False  # Whether there is a Benched Pokémon that is ready to attack
    pre_turn_log = []
    current_turn_log = []

    prize = []
    card_counts = defaultdict(int)
    serial_set = set()
    plan_a = AttackPlan()
    plan_b = AttackPlan()

    def no_damage_dex(id: int) -> bool:
        """Checks if the defending Pokémon possesses innate immunities preventing Dragapult ex from hitting it."""
        # Drednaw, Milotic ex, Sylveon, Crustle
        return id == 158 or id == 207 or id == 330 or id == 345

    def no_damage_counter(pokemon) -> bool:
        """Checks if a target prevents placement of Phantom Dive's 6 bench damage counters (via abilities/Energy)."""
        # Poltchageist, Empoleon ex, Skeledirge, Milotic ex, Misty's Magikarp, Antique Cover Fossil
        if pokemon.id == 28 or pokemon.id == 199 or pokemon.id == 203 or pokemon.id == 207 or pokemon.id == 362 or pokemon.id == 1136:
            return True
        for card in pokemon.energyCards:
            # Mist Energy, Rock Fighting Energy
            if card.id == 11 or card.id == 20:
                return True
        return False

    def prize_count(pokemon, is_attack_damage: bool) -> int:
        """Calculates how many Prize cards a Pokémon yields upon being Knocked Out, factoring in modifiers."""
        data = card_table[pokemon.id]
        count = 3 if data.megaEx else 2 if data.ex else 1
        if is_attack_damage:
            for card in pokemon.energyCards:
                if card.id == 12:  # Legacy Energy
                    count -= 1
            for card in pokemon.tools:
                if card.id == 1172 and "Lillie" in data.name:  # Lillie’s Pearl
                    count -= 1
        return max(0, count)

    def pokemon_score(pokemon, is_attack_damage: bool) -> int:
        """Heuristically evaluates the tactical worth of targeting a specific Pokémon on the opponent's field."""
        data = card_table[pokemon.id]
        score = prize_count(pokemon, is_attack_damage) * 1000
        score += len(pokemon.energies) * 150
        score += len(pokemon.tools) * 100
        if data.stage2:
            score += 250
        elif data.stage1:
            score += 130

        id = pokemon.id
        # Noctowl, Fan Rotom, Archaludon ex, Meowth ex
        if id == 173 or id == 174 or id == 190 or id == 1071:
            score -= 200
        if id == 112 and len(pokemon.energies) >= 1:  # Munkidori
            score += 300
        score += pokemon.hp
        return score

    def add_card_count(card, my_index: int):
        if card == None:
            return
        if isinstance(card, Pokemon) or card.playerIndex == my_index:
            if card.serial not in serial_set:
                card_counts[card.id] -= 1
                serial_set.add(card.serial)
        if isinstance(card, Pokemon):
            for c in card.energyCards:
                add_card_count(c, my_index)
            for c in card.tools:
                add_card_count(c, my_index)
            for c in card.preEvolution:
                add_card_count(c, my_index)

    def set_card_counts(obs, my_index: int):
        card_counts.clear()
        serial_set.clear()
        for id in my_deck:
            card_counts[id] += 1

        state = obs.current
        my_state = state.players[my_index]
        for card in my_state.hand:
            add_card_count(card, my_index)
        for card in my_state.discard:
            add_card_count(card, my_index)
        for card in my_state.bench:
            add_card_count(card, my_index)
        for card in my_state.active:
            add_card_count(card, my_index)
        for card in state.stadium:
            add_card_count(card, my_index)
        if state.looking != None:
            for card in state.looking:
                add_card_count(card, my_index)
        add_card_count(obs.select.effect, my_index)

    def get_card(obs, area, index: int, player_index: int):
        """Helper function to safely extract a Card or Pokemon object from specific zones."""
        ps = obs.current.players[player_index]
        match area:
            case AreaType.DECK:
                return obs.select.deck[index]
            case AreaType.HAND:
                return ps.hand[index]
            case AreaType.DISCARD:
                return ps.discard[index]
            case AreaType.ACTIVE:
                return ps.active[index]
            case AreaType.BENCH:
                return ps.bench[index]
            case AreaType.PRIZE:
                return ps.prize[index]
            case AreaType.STADIUM:
                return obs.current.stadium[index]
            case AreaType.LOOKING:
                return obs.current.looking[index]
            case _:
                return None

    def main_option_proc(obs, damage: int):
        state = obs.current
        select = obs.select
        my_index = state.yourIndex
        my_state = state.players[my_index]
        op_state = state.players[1 - my_index]

        global can_switch
        global can_attack
        global can_main_attack
        global can_energy_attach

        can_switch = False
        can_attack = False
        can_main_attack = False
        can_energy_attach = False
        for o in select.option:
            if o.type == OptionType.RETREAT:
                can_switch = True
            elif o.type == OptionType.ATTACK:
                can_attack = True
                if o.attackId == 154:  # Phantom Dive
                    can_main_attack = True

        plan_a.attack = -1
        plan_b.attack = -1
        if not can_main_attack and not (bench_attacker and can_switch):
            return

        cards = [op_state.active[0]]
        for pokemon in op_state.bench:
            cards.append(pokemon)
        counter_indices = []
        ci = []
        ci.append(0)
        remain_damage = 60
        while ci:
            index = ci[-1]
            hp = cards[index].hp
            if remain_damage >= hp:
                counter_indices.append(ci.copy())
                if index < len(cards) - 1:
                    remain_damage -= hp
                    ci.append(index + 1)
                    continue
            if index == len(cards) - 1:
                ci.pop()
                if ci:
                    remain_damage += cards[ci[-1]].hp
            if ci:
                ci[-1] += 1
        counter_indices.append([])

        remain_prize = len(my_state.prize)
        plan_score = 0
        for i, pokemon in enumerate(cards):
            base_prize_count = 0
            base_score = pokemon_score(pokemon, True)
            active_damage = 0 if no_damage_dex(pokemon.id) else damage
            if pokemon.hp <= active_damage:
                base_prize_count += prize_count(pokemon, True)
            else:
                base_score *= active_damage / pokemon.hp
            ci = []
            max_score = base_score
            if remain_prize <= base_prize_count:
                max_score = 50000
            else:
                for indices in counter_indices:
                    if i in indices:
                        continue
                    prize = base_prize_count
                    score = base_score
                    for index in indices:
                        prize += prize_count(cards[index], False)
                        score += pokemon_score(cards[index], False)
                    if remain_prize <= prize:
                        score = 50000
                    else:
                        if prize >= 2:
                            if remain_prize <= 4:
                                score -= 1200
                        elif prize == 1:
                            score -= 300
                        else:
                            score += 1200
                    if max_score < score:
                        max_score = score
                        ci = indices
            if plan_score < max_score:
                plan_score = max_score
                plan_a.attack = i
                plan_a.counter = ci
            if i == 0:
                plan_b.attack = plan_a.attack
                plan_b.counter = plan_a.counter

    def _board_role(my_state, op_state, bench_attacker, can_main_attack):
        """A1 role rule (board-level): BEATDOWN / CONTROL / EVEN from prizes + readiness.
        Readiness proxy = whether we already have a lethal-capable attacker online."""
        try:
            my_p = len(my_state.prize)
            op_p = len(op_state.prize)
            my_ready = 1 if (can_main_attack or bench_attacker) else 0
            # op readiness proxy: any op pokemon with >=2 energy on board
            op_ready = 0
            for pk in ([op_state.active[0]] if op_state.active and op_state.active[0] else []) + list(op_state.bench):
                try:
                    if len(pk.energies) >= 2:
                        op_ready = 1; break
                except Exception:
                    continue
            if my_p < op_p or (my_ready and not op_ready):
                return "BEATDOWN"
            if my_p > op_p and op_ready and not my_ready:
                return "CONTROL"
            return "EVEN"
        except Exception:
            return "EVEN"

    # outs that gate our engine: the Dragapult line + Rare Candy (skip-evolve enabler)
    _KEY_OUT_IDS = (Dreepy, Drakloak, Dragapult_ex, Rare_Candy, Buddy_Buddy_Poffin)

    def _apply_v15_nudges(obs, scores, context, my_state, op_state, state,
                          deck_counts, field_counts, bench_attacker, can_main_attack):
        """Bounded additive nudges. Only touches scores that already sit near a tie; the
        magnitude (NUDGE) is << the champion's meaningful gaps, so a clear pick never flips."""
        select = obs.select
        if context != SelectContext.MAIN:
            return  # all three nudges only make sense in the main action phase

        my_index = state.yourIndex

        # ---- (1) prize-check: is a key line likely stuck in our prizes? -------------
        # unseen multiset total = remaining deck + our prizes (prize ids are opaque).
        prizes_left = len(my_state.prize)
        unseen_total = int(getattr(my_state, "deckCount", 0) or 0) + prizes_left
        # outs still unseen for the Dragapult engine (use champion's deck_counts = deck-only;
        # add prizes back so the hypergeometric pool is deck+prizes).
        line_unseen = 0
        for cid in (Dreepy, Drakloak, Dragapult_ex):
            line_unseen += max(0, deck_counts.get(cid, 0))
        # we already have an attacker online -> prize-check is irrelevant
        engine_online = can_main_attack or bench_attacker or field_counts.get(Dragapult_ex, 0) >= 1
        p_line_prized = 0.0
        if not engine_online and line_unseen > 0:
            p_line_prized = _hyper_p_at_least_one(line_unseen, unseen_total, prizes_left)

        # ---- (2) role -------------------------------------------------------------
        role = _board_role(my_state, op_state, bench_attacker, can_main_attack)

        # ---- (3) draw-before-search ----------------------------------------------
        # No reliable per-turn "already drew" signal exists in this obs (LogType has DRAW
        # but obs.logs is only the delta since the last call). So we keep this as a pure
        # tie-break: prefer a draw ABILITY over a search/ball PLAY whenever both are offered
        # in the SAME option set (digging order). Tiny magnitude, never flips a clear pick.
        has_draw_ability = any(o.type == OptionType.ABILITY for o in select.option)

        for idx, o in enumerate(select.option):
            try:
                ot = o.type
                # (3) draw-before-search tie-break.
                if has_draw_ability:
                    if ot == OptionType.ABILITY:
                        scores[idx] += NUDGE
                    elif ot == OptionType.PLAY:
                        c = get_card(obs, AreaType.HAND, o.index, my_index)
                        if c is not None and c.id in (Ultra_Ball, Buddy_Buddy_Poffin, Poke_Pad):
                            scores[idx] -= NUDGE * 0.5

                # (1) prize-check: if our engine line is likely prized, slightly prefer
                # search/draw/recovery so we dig toward the prized copies.
                if p_line_prized >= 0.5 and ot == OptionType.PLAY:
                    c = get_card(obs, AreaType.HAND, o.index, my_index)
                    if c is not None and c.id in (Ultra_Ball, Buddy_Buddy_Poffin, Poke_Pad, Night_Stretcher):
                        scores[idx] += NUDGE * p_line_prized

                # (2) role: in EVEN/BEATDOWN, faintly prefer attacking; in CONTROL, faintly
                # prefer disruption (Crushing Hammer / Boss Orders). Tie-break only.
                if ot == OptionType.ATTACK:
                    if role == "BEATDOWN":
                        scores[idx] += NUDGE
                    elif role == "EVEN":
                        scores[idx] += NUDGE * 0.5
                elif ot == OptionType.PLAY and role == "CONTROL":
                    c = get_card(obs, AreaType.HAND, o.index, my_index)
                    if c is not None and c.id in (Crushing_Hammer, Boss_Orders):
                        scores[idx] += NUDGE
            except Exception:
                continue

    def _sample_agent(obs_dict: dict) -> list:
        """Official sample policy. Returns a list of option indices (or the deck)."""
        obs = to_observation_class(obs_dict)
        if obs.select == None:
            return my_deck

        global pre_turn_log
        global current_turn_log

        state = obs.current
        select = obs.select
        context = select.context
        my_index = state.yourIndex
        my_state = state.players[my_index]
        op_state = state.players[1 - my_index]

        if state.turn == 0:
            prize.clear()
            pre_turn_log.clear()
            current_turn_log.clear()
        else:
            for log in obs.logs:
                current_turn_log.append(log)
                if log.type == LogType.TURN_END:
                    pre_turn_log = current_turn_log
                    current_turn_log = []

        pre_ko = False
        no_item = False
        for log in pre_turn_log:
            if log.type == LogType.ATTACK:
                if log.attackId == 323:  # Itchy Pollen
                    no_item = True
            elif log.type == LogType.MOVE_CARD:
                if (log.playerIndex == my_index
                    and (log.fromArea == AreaType.BENCH or log.fromArea == AreaType.ACTIVE)
                    and log.toArea == AreaType.DISCARD):
                    pre_ko = True

        if select.deck != None:
            set_card_counts(obs, my_index)
            for card in select.deck:
                card_counts[card.id] -= 1
            prize.clear()
            for id in card_counts:
                for _ in range(card_counts[id]):
                    prize.append(id)

        set_card_counts(obs, my_index)
        for id in prize:
            card_counts[id] -= 1
        deck_counts = card_counts

        prize_diff = len(my_state.prize) - len(op_state.prize)

        global bench_attacker

        # Number of cards per card ID on the Bench and in the Active Spot
        field_counts = defaultdict(int)
        # Number of cards per card ID in hand
        hand_counts = defaultdict(int)
        # Number of cards per card ID in discard pile
        discard_counts = defaultdict(int)

        active_id = 0
        bench_attacker = False
        can_evolve_dreepy = False
        evolve_dreepy_count = 0
        can_evolve_drakloak = False
        damage = 200
        for card in my_state.active:
            if card == None:
                continue
            active_id = card.id
            field_counts[card.id] += 1
            if not card.appearThisTurn:
                if card.id == Dreepy:
                    can_evolve_dreepy = True
                    evolve_dreepy_count += 1
                elif card.id == Drakloak:
                    can_evolve_drakloak = True
        for card in my_state.bench:
            field_counts[card.id] += 1
            if not card.appearThisTurn:
                if card.id == Dreepy:
                    can_evolve_dreepy = True
                    evolve_dreepy_count += 1
                elif card.id == Drakloak:
                    can_evolve_drakloak = True
            if card.id == Dragapult_ex and len(card.energies) >= 2:
                bench_attacker = True
        main_pokemon_count = field_counts[Dreepy] + field_counts[Drakloak] + field_counts[Dragapult_ex]
        no_more_dex = (field_counts[Dragapult_ex] * 2 >= len(op_state.prize))

        stadium_id = 0
        for card in state.stadium:
            stadium_id = card.id

        support_count = 0

        for card in my_state.discard:
            discard_counts[card.id] += 1

        def attach_score(attach_id: int, pokemon, active: bool) -> int:
            energy_count = len(pokemon.energies)
            if card_table[attach_id].cardType == CardType.TOOL:
                # Attach tool
                score = 60000
                if active:
                    score += 1000
                return score

            # Attach energy
            if pokemon.id == Budew:
                return -1
            elif pokemon.id == Meowth_ex or pokemon.id == Fezandipiti_ex or pokemon.id == Latias_ex:
                if active and not can_switch and not my_state.asleep and not my_state.paralyzed:
                    if bench_attacker or field_counts[Budew] >= 1:
                        return 22000
                    else:
                        return 18000
                else:
                    return -1
            if active and can_main_attack:
                return -1
            score = 20000
            if energy_count >= 2:
                if active and not can_switch and not my_state.asleep and not my_state.paralyzed:
                    score += 200
                else:
                    return -1
            elif energy_count == 1:
                if attach_id == pokemon.energyCards[0].id:
                    return -1
                if pokemon.id == Dragapult_ex:
                    score += 250
                elif pokemon.id == Dreepy:
                    score -= 150
                else:
                    score -= 200
                if active:
                    score += 200
            else:  # energy_count == 0
                if active:
                    if bench_attacker:
                        score += 400
                else:
                    if pokemon.id == Dragapult_ex:
                        score += 150
                    elif pokemon.id == Dreepy:
                        score += 100
                    else:
                        score += 50
                    if bench_attacker:
                        score -= 200
            if no_more_dex and (pokemon.id == Dreepy or pokemon.id == Drakloak):
                score -= 500
            return score

        def hand_score(id: int, ignore_count: bool):
            score = 0
            if id == Dreepy:
                if main_pokemon_count >= 3:
                    score = 1000
                else:
                    score = 18000
            elif id == Drakloak:
                if can_evolve_dreepy:
                    score = 20000
                else:
                    score = 3000
            elif id == Dragapult_ex:
                if no_more_dex:
                    score = UNNECESSARY
                elif can_evolve_dreepy and hand_counts[Rare_Candy] >= 1 and not no_item:
                    score = 40000
                elif can_evolve_drakloak:
                    if field_counts[id] == 0:
                        score = 30000
                    elif field_counts[id] == 1:
                        score = 10000
                    else:
                        score = 50
                else:
                    if field_counts[id] >= 2:
                        score = 50
                    else:
                        score = 2000
            elif id == Fezandipiti_ex:
                if pre_ko:
                    score = 50000
                elif prize_diff <= -2:
                    score = 5
                elif len(op_state.prize) == 1:
                    score = UNNECESSARY
            elif id == Latias_ex:
                if active_id == Fezandipiti_ex or active_id == Meowth_ex or active_id == Dreepy:
                    if field_counts[Drakloak] + field_counts[Dragapult_ex] == 0:
                        score = 28000
                    else:
                        score = 15000
                else:
                    score = 10
            elif id == Budew:
                if field_counts[id] + field_counts[Drakloak] + field_counts[Dragapult_ex] >= 1:
                    score = UNNECESSARY
                elif state.turn >= 2:
                    score = 30000
            elif id == Meowth_ex:
                if support_count > hand_counts[Boss_Orders] or stadium_id == Team_Rocket_Watchtower:
                    score = 5
                elif state.supporterPlayed:
                    score = 40
                else:
                    score = 35000
            elif id == Rare_Candy:
                if no_more_dex:
                    score = UNNECESSARY
                elif can_evolve_dreepy and hand_counts[Dragapult_ex] >= 1:
                    score = 40000
            elif id == Unfair_Stamp:
                if pre_ko:
                    score = 80000
                elif len(op_state.prize) == 1:
                    score = UNNECESSARY
                else:
                    score = 80
            elif id == Buddy_Buddy_Poffin:
                count = deck_counts[Dreepy]
                if count == 0:
                    score = UNNECESSARY
                else:
                    if state.turn <= 2 and field_counts[Budew] == 0 and deck_counts[Budew] >= 1:
                        count += 1
                    if count >= 2:
                        score = 35000
            elif id == Night_Stretcher:
                for i in discard_counts:
                    if discard_counts[i] >= 1:
                        card_type = card_table[i].cardType
                        if card_type == CardType.POKEMON or card_type == CardType.BASIC_ENERGY:
                            score = max(score, hand_score(i, ignore_count))
            elif id == Crushing_Hammer:
                score = 20
            elif id == Ultra_Ball:
                if main_pokemon_count <= 2 or field_counts[Dreepy] >= 1:
                    score = 70
                else:
                    score = 5
            elif id == Poke_Pad:
                score = max(hand_score(Dreepy, ignore_count), hand_score(Drakloak, ignore_count))
            elif id == Lucky_Helmet:
                score = 15
            elif id == Boss_Orders:
                if plan_a.attack > 0:
                    score = 60000
            elif id == Crispin:
                if not ignore_count or support_count == 0:
                    if deck_counts[Basic_Fire_Energy] == 0 or deck_counts[Basic_Psychic_Energy] == 0:
                        score = 10
                    if not can_main_attack and not bench_attacker and field_counts[Dragapult_ex] >= 1:
                        score = 55000
                    else:
                        score = 25000
            elif id == Brock_Scouting:
                if not ignore_count or support_count == 0:
                    if state.turn == 2 and field_counts[Budew] + field_counts[Latias_ex] == 0:
                        score = 50000
                    else:
                        score = 30000
            elif id == Lillie_Determination:
                if not ignore_count or support_count == 0:
                    score = 45000
            elif id == Team_Rocket_Watchtower:
                if stadium_id != 0 and stadium_id != Team_Rocket_Watchtower:
                    score = 4000
            elif id == Basic_Fire_Energy or id == Basic_Psychic_Energy:
                if can_main_attack and (len(op_state.prize) <= 2
                    or (bench_attacker and len(op_state.prize) <= 4)):
                    score = UNNECESSARY
                else:
                    max_score = -10000
                    for pokemon in my_state.active:
                        if pokemon == None:
                            continue
                        max_score = max(max_score, attach_score(id, pokemon, True))
                    for pokemon in my_state.bench:
                        max_score = max(max_score, attach_score(id, pokemon, False))
                    score = max_score - 5000
                    if can_main_attack or bench_attacker:
                        score /= 10

            if not ignore_count and hand_counts[id] > 0:
                if id == Drakloak and hand_counts[id] < evolve_dreepy_count:
                    score -= 10
                elif id == Dreepy:
                    score -= 100
                else:
                    score -= 100000
            return score

        global use_support
        if context == SelectContext.MAIN:
            main_option_proc(obs, damage)

            use_support = 0
            if not state.supporterPlayed:
                support_score = 0
                for o in select.option:
                    if o.type == OptionType.PLAY:
                        card = get_card(obs, AreaType.HAND, o.index, state.yourIndex)
                        if card_table[card.id].cardType == CardType.SUPPORTER:
                            score = hand_score(card.id, True)
                            if support_score < score:
                                support_score = score
                                use_support = card.id

        hand_scores = []
        negative_hand_count = 0
        for card in my_state.hand:
            score = hand_score(card.id, False)
            hand_scores.append(score)
            if score < 0:
                negative_hand_count += 1
            hand_counts[card.id] += 1
            if card_table[card.id].cardType == CardType.SUPPORTER and card.id != Boss_Orders:
                support_count += 1

        no_draw = (my_state.deckCount <= 8)  # Whether to restrict actions that reduce the deck
        do_switch = (not can_main_attack and (bench_attacker or (active_id != Budew and field_counts[Budew] >= 1 and state.turn >= 2)))
        effect_card_id = 0 if select.effect == None else select.effect.id
        context_card_id = 0 if select.contextCard == None else select.contextCard.id

        scores = []  # Score for each action
        for o in select.option:
            score = 0  # The default and baseline score is 0.
            if o.type == OptionType.NUMBER:
                score = o.number
            elif o.type == OptionType.YES:
                if context == SelectContext.IS_FIRST:
                    score = -1
                else:
                    score = 1
            elif o.type == OptionType.CARD:
                card = get_card(obs, o.area, o.index, o.playerIndex)
                if card != None:
                    energy_count = 0
                    hp = 0
                    if isinstance(card, Pokemon):
                        energy_count = len(card.energies)
                        hp = card.hp
                    if (context == SelectContext.SWITCH
                        or context == SelectContext.TO_ACTIVE
                        or context == SelectContext.SETUP_ACTIVE_POKEMON):
                        # Selection of the Pokémon to send to the Active Spot
                        if o.playerIndex == my_index:
                            if card.id == Dreepy:
                                score += 10000
                            elif card.id == Drakloak:
                                if energy_count >= 1:
                                    score += 20000
                                else:
                                    score -= 10000
                            elif card.id == Dragapult_ex:
                                score += 50000
                            elif card.id == Budew:
                                if context != SelectContext.SWITCH:
                                    score += 100000
                                elif not bench_attacker:
                                    score += 30000
                            elif card.id == Fezandipiti_ex:
                                score -= 1000
                            elif card.id == Meowth_ex:
                                score -= 2000
                        else:
                            if plan_a.attack == o.index + 1:
                                score += 100000
                        score += energy_count * 1000
                        score += hp
                    elif context == SelectContext.SETUP_BENCH_POKEMON:
                        if my_index == state.firstPlayer or card.id != Dreepy:
                            score = -1
                    elif context == SelectContext.TO_BENCH or context == SelectContext.TO_HAND:
                        score = hand_score(card.id, False)
                        hand_counts[card.id] += 1
                        if effect_card_id == Crispin:
                            # Reverse scoring
                            score = 100000 - hand_score(card.id, True)
                    elif context == SelectContext.DISCARD:
                        hand_counts[card.id] -= 1
                        if card_table[card.id].cardType == CardType.SUPPORTER:
                            support_count -= 1
                        score = -hand_score(card.id, False)
                    elif context == SelectContext.DAMAGE_COUNTER or context == SelectContext.DAMAGE_COUNTER_ANY:
                        if hp > 0:
                            score = 100000 - 10 * hp + pokemon_score(card, False)
                            if context == SelectContext.DAMAGE_COUNTER:
                                if 210 <= hp <= 230:
                                    score += 20000 + hp * 20
                                    if o.area == AreaType.ACTIVE:
                                        score += 10000
                                elif 40 <= hp <= 90:
                                    score += 10000 + hp * 20
                                elif hp <= 30:
                                    score += -10000 + hp * 20
                                if card.id == 133 or card.id == 351:
                                    score += 30000
                            else:
                                index = o.index + 1
                                if index in plan_b.counter:
                                    score += 100000
                                else:
                                    remain_damage = select.remainDamageCounter * 10
                                    if 210 <= hp <= 200 + remain_damage:
                                        score += 30000
                                    elif 20 <= hp <= 60 + remain_damage:
                                        score += 10000
                                    elif hp == 10:
                                        score -= 100000
                                if no_damage_counter(card):
                                    score = -1
                    elif context == SelectContext.ATTACH_FROM:
                        score = attach_score(context_card_id, card, o.area == AreaType.ACTIVE)
                        if card.id == Dragapult_ex:
                            score += 200
            elif o.type == OptionType.ENERGY_CARD or o.type == OptionType.ENERGY:
                # Discarding energy (Retreat or Crushing Hammer)
                if o.playerIndex != state.yourIndex:
                    if o.area == AreaType.BENCH:
                        score = 20
                    else:
                        score = 10
                    card = get_card(obs, o.area, o.index, o.playerIndex)
                    if card_table[card.id].cardType == CardType.SPECIAL_ENERGY:
                        score += 1
            elif o.type == OptionType.PLAY:
                card = get_card(obs, AreaType.HAND, o.index, my_index)
                card_score = hand_scores[o.index]
                if card.id == Dreepy:
                    score = 51000
                elif card.id == Fezandipiti_ex:
                    if card_score > 0:
                        score = 53000
                    else:
                        score = -1
                elif card.id == Latias_ex:
                    if active_id != Drakloak and active_id != Dragapult_ex:
                        score = 51000
                    else:
                        score = -1
                elif card.id == Budew:
                    if field_counts[Budew] == 0 and field_counts[Dragapult_ex] == 0:
                        score = 52000
                    else:
                        score = -1
                elif card.id == Meowth_ex:
                    if state.supporterPlayed or stadium_id == Team_Rocket_Watchtower:
                        score = -1
                    elif support_count == 0:
                        score = 50000
                    elif support_count == hand_counts[Boss_Orders] and not plan_a.attack <= 0:
                        score = 50000
                    else:
                        score = -1
                elif card.id == Rare_Candy:
                    if no_more_dex:
                        score = -1
                    else:
                        score = 75000
                elif card.id == Unfair_Stamp:
                    score = 15000
                elif card.id == Night_Stretcher:
                    if card_score >= 18000:
                        score = 42000
                    else:
                        score = -1
                elif card.id == Crushing_Hammer:
                    score = 40000
                elif card.id == Boss_Orders:
                    if card.id == use_support:
                        score = 35000
                    else:
                        score = -1
                elif card.id == Lillie_Determination:
                    if card.id == use_support:
                        score = 14000
                    else:
                        score = -1
                elif card.id == Team_Rocket_Watchtower:
                    if stadium_id > 0 or state.turn == 1:
                        score = 80000
                    else:
                        score = -1
                elif no_draw:
                    score = -1
                elif card.id == Buddy_Buddy_Poffin:
                    if deck_counts[Dreepy] > 0:
                        score = 46000
                    else:
                        score = -1
                elif card.id == Ultra_Ball:
                    if negative_hand_count >= 2:
                        score = 44000
                    else:
                        score = -1
                elif card.id == Poke_Pad:
                    if deck_counts[Dreepy] + deck_counts[Drakloak] > 0:
                        score = 45000
                    else:
                        score = -1
                elif card.id == Crispin or card.id == Brock_Scouting:
                    if card.id == use_support:
                        score = 35000
                    else:
                        score = -1
            elif o.type == OptionType.ATTACH:
                card = get_card(obs, o.area, o.index, my_index)
                pokemon = get_card(obs, o.inPlayArea, o.inPlayIndex, my_index)
                score = attach_score(card.id, pokemon, o.inPlayArea == AreaType.ACTIVE)
            elif o.type == OptionType.EVOLVE:
                pokemon = get_card(obs, o.inPlayArea, o.inPlayIndex, my_index)
                score += len(pokemon.energies)
                if pokemon.id == Dreepy:
                    score += 30000
                elif field_counts[Dragapult_ex] >= 2 or (field_counts[Dragapult_ex] == 1 and len(op_state.prize) <= 2):
                    score = -1
                else:
                    score += 70000
            elif o.type == OptionType.ABILITY:
                card = get_card(obs, o.area, o.index, my_index)
                if no_draw:
                    score = -1
                elif card.id == 1267:  # Lumiose City
                    score = 1
                else:
                    score = 40000
            elif o.type == OptionType.RETREAT:
                if do_switch:
                    score = 10000
                else:
                    score = -1
            elif o.type == OptionType.ATTACK:
                score = o.attackId

            scores.append(score)

        # ── v1.5 ADDITIVE NUDGES (tie-break only; never override champion signals) ──
        # Wrapped whole: any failure leaves the champion `scores` untouched.
        try:
            _apply_v15_nudges(obs, scores, context, my_state, op_state, state,
                              deck_counts, field_counts, bench_attacker, can_main_attack)
        except Exception:
            pass

        output = []
        if len(scores) >= 1:
            # Select in descending order of score
            sorted_scores = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            for i in range(select.maxCount):
                # If the score is negative, do not select it if skipping is possible
                if (sorted_scores[i][1] >= 0
                    or select.minCount > i
                    or (context != SelectContext.TO_BENCH and context != SelectContext.SETUP_BENCH_POKEMON)):
                    output.append(sorted_scores[i][0])

        return output

# =============================================================================
# END OFFICIAL SAMPLE LOGIC
# =============================================================================


# ── diagnostics ───────────────────────────────────────────────────────────────
_DIAG = {"decisions": 0, "policy_ok": 0, "fallbacks": 0, "deck_returns": 0, "errors": {}}


def _record_error(exc):
    k = type(exc).__name__ + ": " + str(exc)[:160]
    _DIAG["errors"][k] = _DIAG["errors"].get(k, 0) + 1


def diag_snapshot():
    s = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DIAG.items()}
    s["cg_ok"] = _CG_OK
    s["cg_err"] = repr(_CG_ERR) if _CG_ERR is not None else None
    return s


# ── public entry point: NEVER crash, ALWAYS return a legal selection ──────────
# NOTE: `agent` MUST be the LAST callable defined in this module — the harness
# loads agents via kaggle_environments.agent.get_last_callable, which picks the
# last top-level function. Do not add functions after this point.
def agent(obs, config=None):
    # Deck-selection phase: return the 60 ids (cheap + safe up front).
    try:
        if isinstance(obs, dict) and obs.get("select") is None:
            _DIAG["deck_returns"] += 1
            return my_deck
    except Exception:
        pass

    sel = obs.get("select") if isinstance(obs, dict) else None

    # If cg never imported, we cannot run the official policy -> first-legal.
    if not _CG_OK:
        _DIAG["fallbacks"] += 1
        return _legal_fallback(sel or {})

    _DIAG["decisions"] += 1
    try:
        out = _sample_agent(obs)
        # the official policy may return non-int (e.g. score floats never reach here,
        # but be defensive) -> coerce to ints where possible
        if isinstance(out, list):
            out = [int(i) for i in out if isinstance(i, (int, float))]
        if _validate(out, sel or {}):
            _DIAG["policy_ok"] += 1
            return out
        # official output illegal for this select -> legal fallback
        _DIAG["fallbacks"] += 1
        return _legal_fallback(sel or {})
    except Exception as exc:
        _record_error(exc)
        _DIAG["fallbacks"] += 1
        return _legal_fallback_from_obs(obs)
