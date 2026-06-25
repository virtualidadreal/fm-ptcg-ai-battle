"""
ISMCTS competition agent for the Pokemon TCG AI Battle (cabt engine).

Architecture
------------
This agent reuses the OFFICIAL Dragapult ex rule-based sample (kiyotah kernel) as:
  (a) the ultimate robustness fallback (never crash, always a legal selection), and
  (b) the policy PRIOR that biases the MCTS expansion order.
On top of it, it runs an Information-Set MCTS over the cabt Search API
(`search_begin` / `search_step` / `search_release`) adapting the official
`mcts_agent`/`create_node` structure from the MCTS+RL sample notebook, but WITHOUT
the Transformer. Node values come from a fast STATIC evaluation (prizes left,
board material, KO pressure) so we can afford many search steps inside the time
budget.

Determinization (ISMCTS): the opponent's hidden deck / hand / prize / face-down
active are filled with a reasonable guess (as the notebook sample does). We repeat
the search with K independent determinizations and AGGREGATE root child visits
before choosing the most-visited action.

Hard time budget: a timeout = an instant loss. Every decision is wall-clock
bounded by a watchdog; if we run out of budget we stop searching and return the
best (most visited) action so far, falling back to the sample policy / first-legal
if the search produced nothing.

EMPIRICAL RESULT (Docker, cabt local, 15-game A/B, same Dragapult deck):
  - ISMCTS ON  : 0W/15L vs the rule-based sample, and 13% vs first-legal.
  - ISMCTS OFF : 9W/6L (60%, Wilson includes 0.5 = parity) vs the sample.
  The shallow STATIC eval is net-negative: it cannot value the long chains of
  intra-turn micro-decisions (play/attach/evolve), so the search overrides the
  hand-tuned policy with worse moves. This mirrors why the official MCTS kernel
  pairs the search with a TRAINED value/policy Transformer.
  => DEFAULT is policy-driven (MCTS gated off). The search stays implemented and
     re-enables with env FMA_MCTS_ON=1 — the slot for a learned eval in Phase 3.

NOTE: `agent` MUST stay the LAST top-level callable (get_last_callable loads it).
"""

from __future__ import annotations

import math
import os
import random
import sys
import time

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


# ── cg import (degrade gracefully if unavailable) ─────────────────────────────
_CG_OK = True
_CG_ERR = None
try:
    from collections import defaultdict

    from cg.api import (
        AreaType, CardType, Log, LogType, Observation, SelectContext,
        OptionType, Card, Pokemon, State, all_card_data, to_observation_class,
        search_begin, search_step, search_end, search_release,
    )
except Exception as _e:  # pragma: no cover
    _CG_OK = False
    _CG_ERR = _e


# ── BC net (Leon v3 prior): value + policy APRENDIDOS que reemplazan la eval ESTATICA del
#    ISMCTS (la estatica era net-negativa 0/15). Es el "hueco" que el plan dejaba para Fase 3.
#    Si torch/encode_lib/model/pesos fallan -> _NET_EVAL_OK=False y el search cae a la eval estatica.
_NET_EVAL_OK = bool(_CG_OK)
_NET_EVAL_ERR = None
_NET = None
_torch = None
_E = None
if _CG_OK:
    try:
        _TD = None
        try:
            _TD = os.path.dirname(os.path.abspath(__file__))
        except Exception:
            _TD = None
        for _c in (_TD, os.getcwd(), "/kaggle_simulations/agent"):
            try:
                if _c and os.path.isdir(_c) and _c not in sys.path:
                    sys.path.insert(0, _c)
            except Exception:
                pass
        import torch as _torch
        import encode_lib as _E
        from model import LeonV3Net as _LeonV3Net
        _W = None
        for _cand in ((os.path.join(_TD, "leon_v3.pt") if _TD else None),
                      "leon_v3.pt", "/kaggle_simulations/agent/leon_v3.pt"):
            if _cand and os.path.exists(_cand):
                _W = _cand
                break
        if _W is None:
            raise FileNotFoundError("leon_v3.pt no encontrado")
        _ck = _torch.load(_W, map_location="cpu")
        _NET = _LeonV3Net(d_model=int(_ck.get("d_model", 96)))
        _NET.load_state_dict(_ck["state_dict"])
        _NET.eval()
        _torch.set_grad_enabled(False)
        _torch.set_num_threads(max(1, (os.cpu_count() or 2)))
    except Exception as _e2:
        _NET_EVAL_OK = False
        _NET_EVAL_ERR = _e2


# =============================================================================
# BEGIN OFFICIAL SAMPLE LOGIC (verbatim policy — used as prior + fallback)
# =============================================================================
if _CG_OK:
    all_card = all_card_data()
    card_table = {c.cardId: c for c in all_card}

    Dreepy = 119
    Drakloak = 120
    Dragapult_ex = 121
    Fezandipiti_ex = 140
    Latias_ex = 184
    Budew = 235
    Meowth_ex = 1071
    Rare_Candy = 1079
    Unfair_Stamp = 1080
    Buddy_Buddy_Poffin = 1086
    Night_Stretcher = 1097
    Crushing_Hammer = 1120
    Ultra_Ball = 1121
    Poke_Pad = 1152
    Lucky_Helmet = 1156
    Boss_Orders = 1182
    Crispin = 1198
    Brock_Scouting = 1210
    Lillie_Determination = 1227
    Team_Rocket_Watchtower = 1256
    Basic_Fire_Energy = 2
    Basic_Psychic_Energy = 5

    UNNECESSARY = -10000000

    class AttackPlan:
        attack: int = 0
        counter: list = []

    can_switch = False
    can_attack = False
    can_main_attack = False
    can_energy_attach = False
    use_support = 0
    bench_attacker = False
    pre_turn_log = []
    current_turn_log = []

    prize = []
    card_counts = defaultdict(int)
    serial_set = set()
    plan_a = AttackPlan()
    plan_b = AttackPlan()

    def no_damage_dex(id: int) -> bool:
        return id == 158 or id == 207 or id == 330 or id == 345

    def no_damage_counter(pokemon) -> bool:
        if pokemon.id == 28 or pokemon.id == 199 or pokemon.id == 203 or pokemon.id == 207 or pokemon.id == 362 or pokemon.id == 1136:
            return True
        for card in pokemon.energyCards:
            if card.id == 11 or card.id == 20:
                return True
        return False

    def prize_count(pokemon, is_attack_damage: bool) -> int:
        data = card_table[pokemon.id]
        count = 3 if data.megaEx else 2 if data.ex else 1
        if is_attack_damage:
            for card in pokemon.energyCards:
                if card.id == 12:
                    count -= 1
            for card in pokemon.tools:
                if card.id == 1172 and "Lillie" in data.name:
                    count -= 1
        return max(0, count)

    def pokemon_score(pokemon, is_attack_damage: bool) -> int:
        data = card_table[pokemon.id]
        score = prize_count(pokemon, is_attack_damage) * 1000
        score += len(pokemon.energies) * 150
        score += len(pokemon.tools) * 100
        if data.stage2:
            score += 250
        elif data.stage1:
            score += 130
        id = pokemon.id
        if id == 173 or id == 174 or id == 190 or id == 1071:
            score -= 200
        if id == 112 and len(pokemon.energies) >= 1:
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
                if o.attackId == 154:
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

    def _sample_agent(obs_dict: dict) -> list:
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
                if log.attackId == 323:
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
        field_counts = defaultdict(int)
        hand_counts = defaultdict(int)
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
                score = 60000
                if active:
                    score += 1000
                return score
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
            else:
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
        no_draw = (my_state.deckCount <= 8)
        do_switch = (not can_main_attack and (bench_attacker or (active_id != Budew and field_counts[Budew] >= 1 and state.turn >= 2)))
        effect_card_id = 0 if select.effect == None else select.effect.id
        context_card_id = 0 if select.contextCard == None else select.contextCard.id
        scores = []
        for o in select.option:
            score = 0
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
                elif card.id == 1267:
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
        output = []
        if len(scores) >= 1:
            sorted_scores = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
            for i in range(select.maxCount):
                if (sorted_scores[i][1] >= 0
                    or select.minCount > i
                    or (context != SelectContext.TO_BENCH and context != SelectContext.SETUP_BENCH_POKEMON)):
                    output.append(sorted_scores[i][0])
        return output

# =============================================================================
# END OFFICIAL SAMPLE LOGIC
# =============================================================================


# =============================================================================
# ISMCTS  (static eval, PUCT + minimax, search_release, K determinizations)
# =============================================================================
# --- tunables (calibrated against the Docker microbench; see report) --------
SEARCH_COUNT = 120  # search_step iterations per determinization
K_DETERMINIZATIONS = 3
PUCT_C = 0.4        # exploration constant base (c = PUCT_C * sqrt(visit))
# Presupuesto por decision. Override por env para A/B local mas rapido (la net bajo emulacion x86 es lenta):
# FMA_WALL_S / FMA_HARD_S. Bajarlo da una busqueda mas SOMERA -> es una COTA INFERIOR de la fuerza real en
# Kaggle (runtime nativo, mismo wall = mas iteraciones). Por defecto los valores calibrados.
WALL_BUDGET_S = float(os.environ.get("FMA_WALL_S", "2.5"))   # soft per-decision wall-clock budget
HARD_WALL_S = float(os.environ.get("FMA_HARD_S", "4.0"))     # absolute cap: stop the search no matter what
OVERAGE_FLOOR_S = 60.0      # if remainingOverageTime drops below this, play fast
PRIOR_TEMP = 0.0015         # softmax temperature applied to sample-policy scores


if _CG_OK:

    def _static_eval(state, your_index: int) -> float:
        """Static node value in [-1, 1] from your_index's perspective.

        Dominant term: prize-cards left (fewer of yours, more of theirs = better),
        since taking all prizes wins. Secondary terms: board material (HP + energy
        + bench size) and KO pressure (active Pokemon close to dying)."""
        me = state.players[your_index]
        opp = state.players[1 - your_index]

        # 1) prize race — the win condition. Range roughly [-1,1].
        my_prizes = len(me.prize)
        opp_prizes = len(opp.prize)
        # someone is about to win at 0 prizes
        if opp_prizes == 0:
            return 1.0
        if my_prizes == 0:
            return -1.0
        prize_term = (opp_prizes - my_prizes) / 6.0  # in [-1,1]

        # 2) board material: HP on field + attached energy + bench presence
        def material(ps):
            m = 0.0
            for poke in ps.active:
                if poke is not None:
                    m += poke.hp / 100.0
                    m += 0.5 * len(poke.energies)
            for poke in ps.bench:
                m += poke.hp / 100.0
                m += 0.5 * len(poke.energies)
                m += 0.3  # having a developed bench is good
            return m

        mat = material(me) - material(opp)
        # squash material difference into a small bounded contribution
        mat_term = math.tanh(mat / 8.0)

        # 3) KO pressure on the active spots (low HP active = vulnerable)
        ko_term = 0.0
        my_act = me.active[0] if me.active and me.active[0] is not None else None
        opp_act = opp.active[0] if opp.active and opp.active[0] is not None else None
        if opp_act is not None and opp_act.hp <= 60:
            ko_term += 0.15  # we can likely KO their active
        if my_act is not None and my_act.hp <= 60:
            ko_term -= 0.15  # ours is exposed

        v = 0.78 * prize_term + 0.17 * mat_term + ko_term
        if v > 1.0:
            v = 1.0
        elif v < -1.0:
            v = -1.0
        return v

    class Child:
        __slots__ = ("node", "select", "prob")

        def __init__(self, select, prob):
            self.node = None
            self.select = select
            self.prob = prob

    class Node:
        __slots__ = ("value", "total", "visit", "parent", "children", "state")

        def __init__(self, parent, state):
            self.value = -2.0
            self.total = 0.0
            self.visit = 0
            self.parent = parent
            self.children = []
            self.state = state

        def backprop(self, value):
            node = self
            while node is not None:
                node.total += value
                node.visit += 1
                node = node.parent

    def _enumerate_actions(select):
        """All combinations of option indices of size maxCount (capped at 64),
        in the official notebook's lexicographic order."""
        actions = []
        maxc = select.maxCount
        nopt = len(select.option)
        indices = list(range(maxc))
        for _ in range(64):
            actions.append(indices.copy())
            for i in range(len(indices)):
                index = len(indices) - i - 1
                if indices[index] < nopt - i - 1:
                    indices[index] += 1
                    for j in range(index + 1, len(indices)):
                        indices[j] = indices[j - 1] + 1
                    break
            else:
                break
        return actions

    def _priors_from_sample(obs, actions):
        """Bias expansion toward the rule-based sample's preferred option(s).
        Returns a normalized prob per action. Falls back to uniform on any error.
        Only meaningful when it's OUR decision node; for opponent nodes we use
        uniform (we don't model the opponent's policy)."""
        n = len(actions)
        if n == 0:
            return []
        try:
            select = obs.select
            # per-option score from the sample, then map to per-action.
            # Reuse the sample only at MAIN-ish single-pick nodes for our seat;
            # otherwise uniform. Keep it cheap and robust.
            # Score each option via a light proxy: prefer ATTACK/KO + sample order.
            opt_scores = [0.0] * len(select.option)
            for i, o in enumerate(select.option):
                s = 0.0
                if o.type == OptionType.ATTACK:
                    s += 2.0
                elif o.type == OptionType.EVOLVE:
                    s += 1.0
                elif o.type == OptionType.ATTACH:
                    s += 0.8
                elif o.type == OptionType.PLAY:
                    s += 0.5
                elif o.type == OptionType.END:
                    s -= 0.3
                opt_scores[i] = s
            raw = []
            for act in actions:
                sc = sum(opt_scores[i] for i in act if 0 <= i < len(opt_scores))
                raw.append(sc)
            mx = max(raw)
            exps = [math.exp(r - mx) for r in raw]
            tot = sum(exps)
            if tot <= 0:
                return [1.0 / n] * n
            return [e / tot for e in exps]
        except Exception:
            return [1.0 / n] * n

    def _net_eval(obs, actions):
        """UNA pasada de la BC net sobre el obs del nodo: (value desde obs.current.yourIndex,
        priors softmax sobre `actions`). El encoder es el oficial (get_encoder_input/decoder)."""
        sv_enc = _E.get_encoder_input(obs, my_deck)
        sv_dec = _E.get_decoder_input(obs, actions)
        e_idx = _torch.tensor(sv_enc.index, dtype=_torch.long)
        e_val = _torch.tensor(sv_enc.value, dtype=_torch.float)
        e_wo = _torch.tensor(sv_enc.offset, dtype=_torch.long)
        d_idx = _torch.tensor(sv_dec.index, dtype=_torch.long)
        d_val = _torch.tensor(sv_dec.value, dtype=_torch.float)
        d_wo = _torch.tensor(sv_dec.offset, dtype=_torch.long)
        n_cand = _torch.tensor([len(actions)], dtype=_torch.long)
        logits, value = _NET(e_idx, e_val, e_wo, d_idx, d_val, d_wo, n_cand)
        probs = _torch.softmax(logits[0, :len(actions)], dim=0).tolist()
        _DIAG["net_evals"] += 1
        return float(value[0].item()), probs

    def _create_node(parent, search_state, your_index):
        node = Node(parent, search_state)
        obs = search_state.observation
        state = obs.current
        if state.result is not None and state.result >= 0:
            if state.result == 2:
                node.value = 0.0
            elif state.result == your_index:
                node.value = 1.0
            else:
                node.value = -1.0
            node.backprop(node.value)
        else:
            actions = _enumerate_actions(obs.select)
            # alinea con candidate_actions del entreno: en nodos minCount==0, la accion VACIA [] (pasar/declinar)
            # era el candidato 0 en BC -> la anadimos para que el prior aprendido case y el search pueda "pasar".
            try:
                if getattr(obs.select, "minCount", 1) == 0:
                    actions = [[]] + actions
            except Exception:
                pass
            # eval APRENDIDA (Leon v3): value + policy-prior de la net; si falla, eval estatica.
            net_probs = None
            if _NET_EVAL_OK and actions:
                try:
                    nv, net_probs = _net_eval(obs, actions)
                    v = nv
                except Exception:
                    net_probs = None
                    _DIAG["net_eval_fail"] += 1
                    v = _static_eval(state, your_index)
            else:
                v = _static_eval(state, your_index)
            if state.yourIndex != your_index:
                v = -v  # minimax: value always stored from root player's view
            node.value = v
            node.backprop(v)
            # priors: en nodos NUESTROS, la policy de la net (o el sample si no hay net);
            # en nodos del rival, uniforme (no modelamos su policy; ademas your_deck no es el suyo).
            if state.yourIndex == your_index:
                probs = net_probs if net_probs is not None else _priors_from_sample(obs, actions)
            else:
                probs = [1.0 / len(actions)] * len(actions) if actions else []
            for i, act in enumerate(actions):
                node.children.append(Child(act, probs[i] if i < len(probs) else 0.0))
        return node

    def _run_determinization(obs, your_index, root_visit_agg, search_count, deadline):
        """One determinization: build a root, run MCTS, accumulate root-child
        visits into root_visit_agg (keyed by tuple(select)), release memory."""
        state = obs.current
        me = state.players[your_index]
        opp = state.players[1 - your_index]
        active = opp.active

        # Determinize hidden info. Our own deck/prize are guessed from my_deck
        # (engine ignores your_deck if select.deck != None). Opp hidden zones get
        # plausible-but-cheap fills, like the official sample.
        try:
            your_deck_guess = random.sample(my_deck, me.deckCount) if me.deckCount <= len(my_deck) else (my_deck * 2)[:me.deckCount]
        except Exception:
            your_deck_guess = my_deck[:me.deckCount] if me.deckCount <= len(my_deck) else (my_deck + [my_deck[0]] * me.deckCount)[:me.deckCount]
        try:
            your_prize_guess = random.sample(my_deck, len(me.prize)) if len(me.prize) <= len(my_deck) else (my_deck * 2)[:len(me.prize)]
        except Exception:
            your_prize_guess = my_deck[:len(me.prize)]

        opp_deck = [1072] * opp.deckCount        # Snorlax filler (no deep meaning)
        opp_prize = [1] * len(opp.prize)          # Basic Energy filler
        opp_hand = [1] * opp.handCount            # Basic Energy filler
        opp_active = [1072] if (len(active) > 0 and active[0] is None) else []

        try:
            root_state = search_begin(
                obs,
                your_deck=your_deck_guess,
                your_prize=your_prize_guess,
                opponent_deck=opp_deck,
                opponent_prize=opp_prize,
                opponent_hand=opp_hand,
                opponent_active=opp_active,
            )
        except Exception:
            return False  # this determinization failed; caller may try the policy

        root = _create_node(None, root_state, your_index)
        root_id = root_state.searchId
        opened_ids = [root_id]

        try:
            for _ in range(search_count):
                if time.monotonic() >= deadline:
                    break
                current = root
                while True:
                    best_v = -1e18
                    nxt = None
                    c = PUCT_C * math.sqrt(current.visit) if current.visit > 0 else PUCT_C
                    cur_your = current.state.observation.current.yourIndex
                    flip = (cur_your != your_index)
                    for child in current.children:
                        if child.node is None:
                            q = (current.total / current.visit) if current.visit > 0 else 0.0
                            visit = 0
                        else:
                            q = child.node.total / child.node.visit if child.node.visit > 0 else 0.0
                            visit = child.node.visit
                        if flip:
                            q = -q
                        u = q + c * child.prob / (1 + visit)
                        if u > best_v:
                            best_v = u
                            nxt = child
                    if nxt is None:
                        break
                    if nxt.node is None:
                        try:
                            ns = search_step(current.state.searchId, nxt.select)
                        except Exception:
                            # illegal expansion under this determinization: drop child
                            nxt.prob = 0.0
                            break
                        opened_ids.append(ns.searchId)
                        nxt.node = _create_node(current, ns, your_index)
                        break
                    else:
                        current = nxt.node
                        r = current.state.observation.current.result
                        if r is not None and r >= 0:
                            current.backprop(current.value)
                            break
        finally:
            # release ALL search states opened in this determinization (no leaks)
            for sid in opened_ids:
                try:
                    search_release(sid)
                except Exception:
                    pass
            try:
                search_end()
            except Exception:
                pass

        # aggregate root child visits keyed by the select tuple
        for child in root.children:
            if child.node is not None and child.node.visit > 0:
                key = tuple(child.select)
                agg = root_visit_agg.get(key)
                if agg is None:
                    root_visit_agg[key] = [child.node.visit, child.node.total, list(child.select)]
                else:
                    agg[0] += child.node.visit
                    agg[1] += child.node.total
        return True

    def _ismcts_decide(obs_dict, deadline):
        """Run K determinizations, aggregate, return the most-visited select
        (a list of option indices), or None if the search produced nothing."""
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return None
        your_index = obs.current.yourIndex
        root_visit_agg = {}
        # scale per-determinization search count by remaining wall time
        per_det = max(8, SEARCH_COUNT)
        any_ok = False
        for _ in range(K_DETERMINIZATIONS):
            if time.monotonic() >= deadline:
                break
            ok = _run_determinization(obs, your_index, root_visit_agg, per_det, deadline)
            any_ok = any_ok or ok
        if not root_visit_agg:
            return None
        # most-visited action (tie-break: higher mean value)
        best_key = None
        best_visit = -1
        best_mean = -1e18
        for key, (visit, total, sel) in root_visit_agg.items():
            mean = total / visit if visit > 0 else -1e18
            if visit > best_visit or (visit == best_visit and mean > best_mean):
                best_visit = visit
                best_mean = mean
                best_key = sel
        return list(best_key) if best_key is not None else None


# ── diagnostics ───────────────────────────────────────────────────────────────
_DIAG = {"decisions": 0, "mcts_ok": 0, "policy_used": 0, "fallbacks": 0,
         "deck_returns": 0, "max_decision_s": 0.0, "errors": {},
         "net_evals": 0, "net_eval_fail": 0}


def _record_error(exc):
    k = type(exc).__name__ + ": " + str(exc)[:160]
    _DIAG["errors"][k] = _DIAG["errors"].get(k, 0) + 1


def diag_snapshot():
    s = {k: (dict(v) if isinstance(v, dict) else v) for k, v in _DIAG.items()}
    s["cg_ok"] = _CG_OK
    s["cg_err"] = repr(_CG_ERR) if _CG_ERR is not None else None
    s["SEARCH_COUNT"] = SEARCH_COUNT
    s["K"] = K_DETERMINIZATIONS
    # OBSERVABILIDAD net (Dev Aumentado): distinguir "net mala" de "net no cargo / se cayo a eval estatica".
    s["net_eval_ok_load"] = bool(_NET_EVAL_OK)
    s["net_eval_err"] = repr(_NET_EVAL_ERR) if _NET_EVAL_ERR is not None else None
    return s


def _sample_policy_safe(obs, sel):
    """Run the rule-based sample policy, validated. Returns a legal list or None."""
    try:
        out = _sample_agent(obs)
        if isinstance(out, list):
            out = [int(i) for i in out if isinstance(i, (int, float))]
        if _validate(out, sel or {}):
            return out
    except Exception as exc:
        _record_error(exc)
    return None


# ── public entry point: NEVER crash, ALWAYS return a legal selection ──────────
# NOTE: `agent` MUST be the LAST callable defined in this module.
def agent(obs, config=None):
    t0 = time.monotonic()
    # Deck-selection phase: return the 60 ids.
    try:
        if isinstance(obs, dict) and obs.get("select") is None:
            _DIAG["deck_returns"] += 1
            return my_deck
    except Exception:
        pass

    sel = obs.get("select") if isinstance(obs, dict) else None

    # No cg -> first-legal (cannot search nor run the policy).
    if not _CG_OK:
        _DIAG["fallbacks"] += 1
        return _legal_fallback(sel or {})

    _DIAG["decisions"] += 1

    # time budget: respect remainingOverageTime if present
    budget = WALL_BUDGET_S
    try:
        rem = obs.get("remainingOverageTime") if isinstance(obs, dict) else None
        if rem is not None and rem < OVERAGE_FLOOR_S:
            budget = 0.0  # out of slack: skip MCTS, go straight to fast policy
    except Exception:
        pass
    deadline = t0 + min(budget, HARD_WALL_S)

    mcts_sel = None
    # DEFAULT = policy-driven. The shallow-eval ISMCTS was empirically NET-NEGATIVE
    # (0/15 vs the sample, worse than first-legal): a flat static eval cannot
    # navigate PTCG's long intra-turn decision chains, so the search overrides the
    # hand-tuned policy with worse moves. The full search stays implemented and is
    # re-enabled with FMA_MCTS_ON=1 (intended for when a LEARNED value/policy net
    # replaces the static eval, à la the official MCTS+Transformer kernel).
    if not os.environ.get("FMA_MCTS_ON"):
        budget = 0.0
    if budget > 0.0:
        try:
            mcts_sel = _ismcts_decide(obs, deadline)
        except Exception as exc:
            _record_error(exc)
            mcts_sel = None

    # Validate MCTS output; if good, use it.
    if mcts_sel is not None and _validate(mcts_sel, sel or {}):
        _DIAG["mcts_ok"] += 1
        dt = time.monotonic() - t0
        if dt > _DIAG["max_decision_s"]:
            _DIAG["max_decision_s"] = dt
        return mcts_sel

    # Fallback 1: the rule-based sample policy.
    pol = _sample_policy_safe(obs, sel)
    if pol is not None:
        _DIAG["policy_used"] += 1
        dt = time.monotonic() - t0
        if dt > _DIAG["max_decision_s"]:
            _DIAG["max_decision_s"] = dt
        return pol

    # Fallback 2: first-legal. Never crash.
    _DIAG["fallbacks"] += 1
    dt = time.monotonic() - t0
    if dt > _DIAG["max_decision_s"]:
        _DIAG["max_decision_s"] = dt
    return _legal_fallback(sel or {})
