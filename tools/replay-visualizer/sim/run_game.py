"""
ローカル対戦スクリプト
実行: uv run python notebooks/pokemon-tcg-ai-battle/run_game.py [N] [--json] [--agent0 random|rule|mcts|ucb] [--agent1 ...]
  N            試合数 (default: 20)
  --json       結果をJSONで出力
  --agent0/1   エージェント種別: random / rule / mcts(flat) / ucb(UCB1木探索)
"""
import sys
import os
import random
import json
import math
from collections import defaultdict

CG_PATH = 'data/raw/pokemon-tcg-ai-battle/sample_submission'
sys.path.insert(0, CG_PATH)

_NOTEBOOK_DIR = os.path.dirname(os.path.abspath(__file__))
if _NOTEBOOK_DIR not in sys.path:
    sys.path.insert(0, _NOTEBOOK_DIR)
from battle_eval import energy_attach_score as _energy_attach_score

from cg.game import battle_start, battle_select, battle_finish
from cg.api import (
    to_observation_class, LogType,
    AreaType, CardType, EnergyType,
    SelectContext, OptionType, Pokemon, Card, all_card_data,
    search_begin, search_step, search_end,
)

# ---- カードデータベース ----
all_card = all_card_data()
card_table = {c.cardId: c for c in all_card}

# EXポケモンからのダメージを無効化するアビリティを持つポケモンIDセット
# 例: Crustle の "Mysterious Rock Inn"（相手のexポケモンからのダメージを受けない）
IMMUNE_TO_EX_IDS = {
    c.cardId for c in all_card
    for sk in c.skills
    if 'prevent' in sk.text.lower() and 'damage' in sk.text.lower() and 'ex' in sk.text.lower()
}

# ---- カードID定数 ----
Makuhita          = 673
Hariyama          = 674
Lunatone          = 675
Solrock           = 676
Riolu             = 677
Mega_Lucario_ex   = 678
Dusk_Ball         = 1102
Switch            = 1123
Premium_Power_Pro = 1141
Fighting_Gong     = 1142
Poke_Pad          = 1152
Hero_Cape         = 1159
Boss_Orders       = 1182
Carmine           = 1192
Lillie_Det        = 1227
Gravity_Mountain  = 1252
Basic_Fighting_Energy = 6

LUCARIO_DECK = (
    [Makuhita] * 2 + [Hariyama] * 2 + [Lunatone] * 2 + [Solrock] * 3 +
    [Riolu] * 3 + [Mega_Lucario_ex] * 4 + [Dusk_Ball] * 4 + [Switch] * 2 +
    [Premium_Power_Pro] * 4 + [Fighting_Gong] * 4 + [Poke_Pad] * 4 +
    [Hero_Cape] * 1 + [Boss_Orders] * 2 + [Carmine] * 4 +
    [Lillie_Det] * 4 + [Gravity_Mountain] * 2 + [Basic_Fighting_Energy] * 13
)
assert len(LUCARIO_DECK) == 60

# Crustle デッキ（refs/strong-start-crustle-lucario-agent-v6-lb-860.ipynb より）
Dwebble            = 344
Crustle_id         = 345
Basic_Grass_Energy = 1

CRUSTLE_DECK = (
    [Dwebble]*4 + [Crustle_id]*4 +
    [1086]*4 + [1147]*4 + [1212]*4 + [1224]*4 + [1264]*4 +
    [Hero_Cape]*1 +  # ACE SPEC
    [18]*4 + [11]*4 + [14]*4 +
    [Basic_Grass_Energy]*19
)
assert len(CRUSTLE_DECK) == 60


# ---- ヘルパー関数 ----

def get_card(obs, area, index, player_index):
    ps = obs.current.players[player_index]
    match area:
        case AreaType.DECK:    return obs.select.deck[index]
        case AreaType.HAND:    return ps.hand[index]
        case AreaType.DISCARD: return ps.discard[index]
        case AreaType.ACTIVE:  return ps.active[index]
        case AreaType.BENCH:   return ps.bench[index]
        case AreaType.PRIZE:   return ps.prize[index]
        case AreaType.STADIUM: return obs.current.stadium[index]
        case AreaType.LOOKING: return obs.current.looking[index]
        case _:                return None


def prize_count(pokemon):
    data = card_table[pokemon.id]
    count = 3 if data.megaEx else 2 if data.ex else 1
    for card in pokemon.energyCards:
        if card.id == 12:  # Legacy Energy
            count -= 1
    for card in pokemon.tools:
        if card.id == 1172 and 'Lillie' in data.name:
            count -= 1
    return max(0, count)


def pokemon_score(pokemon):
    data = card_table[pokemon.id]
    score = prize_count(pokemon) * 1000
    score += len(pokemon.energies) * 150
    score += len(pokemon.tools) * 100
    if data.stage2:
        score += 250
    elif data.stage1:
        score += 130
    pid = pokemon.id
    if pid in (144, 322, 323, 337):  # Squawkabilly ex, Noctowl, Fan Rotom, Archaludon ex
        score -= 200
    if pid == 112 and len(pokemon.energies) >= 1:  # Munkidori
        score += 300
    score += pokemon.hp
    return score


def board_eval(obs, my_index):
    """盤面評価関数。my_index 視点の勝利確率 [0, 1] を返す。"""
    if obs.current is None:
        return 0.5
    state = obs.current
    if state.result != -1:
        return 1.0 if state.result == my_index else 0.0

    my_st = state.players[my_index]
    op_st = state.players[1 - my_index]

    # サイド差（最重要）: 取ったサイド枚数の差
    my_taken = 6 - len(my_st.prize)
    op_taken = 6 - len(op_st.prize)
    prize_diff = (my_taken - op_taken) / 6.0  # [-1, 1]

    # HP残量の合計差（多いほど有利）
    def total_hp(ps):
        return sum(p.hp for p in list(ps.active) + list(ps.bench) if p is not None)

    my_hp = total_hp(my_st)
    op_hp = total_hp(op_st)
    hp_diff = (my_hp - op_hp) / max(my_hp + op_hp, 1)  # [-1, 1]

    # エネルギー差（多いほど攻撃準備が整っている）
    def total_energies(ps):
        return sum(len(p.energies) for p in list(ps.active) + list(ps.bench) if p is not None)

    my_e = total_energies(my_st)
    op_e = total_energies(op_st)
    energy_diff = (my_e - op_e) / max(my_e + op_e, 1)  # [-1, 1]

    # ベンチポケモン数差（多いほど有利）
    my_bench = sum(1 for p in my_st.bench if p is not None)
    op_bench = sum(1 for p in op_st.bench if p is not None)
    bench_diff = (my_bench - op_bench) / 5.0  # [-1, 1]

    score = (
        prize_diff  * 0.50 +
        hp_diff     * 0.25 +
        energy_diff * 0.15 +
        bench_diff  * 0.10
    )
    return max(0.0, min(1.0, 0.5 + score * 0.5))


# ---- ルールベースエージェント ----

class AttackPlan:
    def __init__(self):
        self.attacker   = -1
        self.target     = -1
        self.attack_index = -1
        self.remain_hp  = -1
        self.energy     = False
        self.damage     = 0   # 計画した攻撃のダメージ（0=攻撃しても意味なし）


class RuleAgent:
    """サンプルノートブックのルールベースエージェント（Mega Lucario ex デッキ用）"""

    def __init__(self, deck, deck_low_threshold=10):
        self.deck = deck
        self.plan = AttackPlan()
        self.pre_turn = 0
        self.ability_used = False
        self.last_scores_detail = []  # 直前の選択肢スコア一覧（可視化用）
        self.deck_low_threshold = deck_low_threshold  # この枚数以下でドローカード封印

    def _card_name(self, card_id):
        d = card_table.get(card_id)
        return d.name if d else f'#{card_id}'

    def _option_label(self, obs, o, my_index):
        try:
            ot = OptionType(o.type).name
            if ot == 'ATTACK':
                return '⚔ Attack'
            if ot == 'RETREAT':
                return 'Retreat'
            if ot == 'PASS':
                return 'Pass'
            if ot == 'YES':
                return 'Yes'
            if ot == 'NUMBER':
                return f'Number: {o.number}'
            if ot == 'PLAY':
                card = get_card(obs, AreaType.HAND, o.index, my_index)
                return f'Play: {self._card_name(card.id)}' if card else 'Play'
            if ot == 'ATTACH':
                card    = get_card(obs, AreaType.HAND, o.index, my_index)
                target  = get_card(obs, o.inPlayArea, o.inPlayIndex, my_index)
                area    = 'Active' if o.inPlayArea == AreaType.ACTIVE else f'Bench{o.inPlayIndex}'
                cn      = self._card_name(card.id) if card else '?'
                tn      = self._card_name(target.id) if target else '?'
                return f'{cn} → {tn} ({area})'
            if ot == 'EVOLVE':
                card = get_card(obs, AreaType.HAND, o.index, my_index)
                return f'Evolve → {self._card_name(card.id)}' if card else 'Evolve'
            if ot == 'ABILITY':
                card = get_card(obs, o.area, o.index, my_index)
                return f'Ability: {self._card_name(card.id)}' if card else 'Ability'
            if ot in ('SWITCH', 'TO_ACTIVE', 'CARD'):
                card = get_card(obs, o.area, o.index, o.playerIndex)
                return f'{ot}: {self._card_name(card.id)}' if card else ot
        except Exception:
            pass
        return OptionType(o.type).name

    def __call__(self, obs_dict, deck):
        # dict でも Observation オブジェクトでも受け付ける（search API との互換性）
        obs = obs_dict if not isinstance(obs_dict, dict) else to_observation_class(obs_dict)
        if obs.select is None:
            return self.deck

        state   = obs.current
        select  = obs.select
        context = select.context
        my_index = state.yourIndex
        my_state = state.players[my_index]
        op_state = state.players[1 - my_index]
        my_prize = len(my_state.prize)

        # 相手フィールドにEX免疫ライン（Dwebble/Crustleなど）が見えているか
        opp_has_immune_line = any(
            p is not None and (p.id in IMMUNE_TO_EX_IDS or p.id == Dwebble)
            for p in list(op_state.active) + list(op_state.bench)
        )

        # デッキ残り N 枚以下ならドロー・サーチカードを封印（deck_low_threshold で調整）
        deck_is_low = my_state.deckCount <= self.deck_low_threshold

        if self.pre_turn != state.turn:
            self.pre_turn = state.turn
            self.plan = AttackPlan()
            self.ability_used = False

        field_counts   = defaultdict(int)
        hand_counts    = defaultdict(int)
        discard_counts = defaultdict(int)

        attacker1 = False
        attacker2 = False
        for card in my_state.active + my_state.bench:
            if card is None:
                continue
            field_counts[card.id] += 1
            if card.id in (Makuhita, Hariyama):
                if len(card.energies) >= 3:
                    attacker2 = True
            elif card.id in (Riolu, Mega_Lucario_ex):
                if len(card.energies) >= 2:
                    attacker1 = True

        for card in my_state.hand:
            hand_counts[card.id] += 1
        for card in my_state.discard:
            discard_counts[card.id] += 1

        stadium_id = 0
        for card in state.stadium:
            stadium_id = card.id

        can_attack = False
        if context == SelectContext.MAIN:
            can_switch = False
            can_op_switch = False
            can_use_mega_brave = False
            for o in select.option:
                if o.type == OptionType.PLAY:
                    card = get_card(obs, AreaType.HAND, o.index, my_index)
                    if card.id == Switch:
                        can_switch = True
                    elif card.id == Boss_Orders:
                        can_op_switch = True
                elif o.type == OptionType.EVOLVE:
                    card = get_card(obs, AreaType.HAND, o.index, my_index)
                    if card.id == Hariyama:
                        can_op_switch = True
                elif o.type == OptionType.RETREAT:
                    can_switch = True
                elif o.type == OptionType.ATTACK:
                    can_attack = True
                    if o.attackId == 983:
                        can_use_mega_brave = True

            my_cards = [my_state.active[0]] + list(my_state.bench)
            op_cards = [op_state.active[0]] + list(op_state.bench)

            if state.turn >= 2:
                best_score = -1
                for i, my_pokemon in enumerate(my_cards):
                    if i != 0 and not can_switch:
                        break
                    for a in range(2):
                        energy_required = 0
                        base_damage = 0
                        base_score = 0
                        if my_pokemon.id == Mega_Lucario_ex:
                            if a == 0:
                                energy_required = 1
                                base_damage = 130
                                base_score += 60 * min(3, discard_counts[Basic_Fighting_Energy])
                            else:
                                energy_required = 2
                                base_damage = 270
                            if my_prize in (2, 3):
                                base_score -= 500
                        elif a == 1:
                            break
                        elif my_pokemon.id == Hariyama:
                            energy_required = 3
                            base_damage = 210
                        elif my_pokemon.id == Makuhita:
                            for o in select.option:
                                if o.type == OptionType.EVOLVE:
                                    index = o.inPlayIndex
                                    if o.inPlayArea == AreaType.BENCH:
                                        index += 1
                                    if index == i:
                                        break
                            else:
                                break
                            base_score -= 100
                            energy_required = 3
                            base_damage = 210
                        elif my_pokemon.id == Solrock:
                            if field_counts[Lunatone] >= 1:
                                energy_required = 1
                                base_damage = 70

                        if base_damage <= 0:
                            continue

                        more_energy = False
                        energy_count = len(my_pokemon.energies)
                        if a == 1 and i == 0 and energy_count >= 2 and not can_use_mega_brave:
                            break
                        if energy_count < energy_required:
                            if hand_counts[Basic_Fighting_Energy] >= 1 and not state.energyAttached:
                                energy_count += 1
                                if energy_count < energy_required:
                                    continue
                                else:
                                    more_energy = True
                            else:
                                continue

                        for j, op_pokemon in enumerate(op_cards):
                            if j != 0 and not can_op_switch:
                                break
                            damage = base_damage
                            data = card_table[op_pokemon.id]
                            if data.weakness == EnergyType.FIGHTING:
                                damage *= 2
                            elif data.resistance == EnergyType.FIGHTING:
                                damage -= 30
                            # EX免疫アビリティチェック: 自分がEX/MegaEXなら相手の免疫を確認
                            my_card = card_table[my_pokemon.id]
                            if (my_card.ex or my_card.megaEx) and op_pokemon.id in IMMUNE_TO_EX_IDS:
                                damage = 0  # 例: Crustle の Mysterious Rock Inn
                            prize = 0
                            score = pokemon_score(op_pokemon)
                            if op_pokemon.hp <= damage:
                                prize = prize_count(op_pokemon)
                            else:
                                score *= damage / op_pokemon.hp
                            score += base_score

                            if len(op_state.prize) <= prize:
                                score = 50000

                            if i == 0:
                                score += 220
                            if j == 0:
                                score += 300
                            score += energy_count
                            if best_score < score:
                                best_score = score
                                self.plan.attacker    = i
                                self.plan.target      = j
                                self.plan.attack_index = a
                                self.plan.remain_hp   = op_pokemon.hp - damage
                                self.plan.energy      = more_energy
                                self.plan.damage      = damage

        def energy_score(pokemon, is_active):
            my_active_pokemon = my_state.active[0] if my_state.active else None
            opp_active_pokemon = op_state.active[0] if op_state.active else None
            if my_active_pokemon is None or opp_active_pokemon is None:
                return 8000
            base = _energy_attach_score(
                pokemon,
                is_active,
                my_active_pokemon,
                opp_active_pokemon,
                card_table,
            )
            # イワパレスライン対策: Dwebble/Crustleが見えたら Hariyama 最優先
            # Mega Lucario ex / Riolu へのエネルギーは完全封印（エネルギー枯渇防止）
            if opp_has_immune_line:
                if pokemon.id in (Hariyama, Makuhita) and len(pokemon.energies) < 3:
                    base += 3000
                elif pokemon.id in (Mega_Lucario_ex, Riolu):
                    base = -5000
            return base

        scores = []
        for o in select.option:
            score = 0
            if o.type == OptionType.NUMBER:
                score = o.number
            elif o.type == OptionType.YES:
                score = 1
            elif o.type == OptionType.CARD:
                card = get_card(obs, o.area, o.index, o.playerIndex)
                if card is not None:
                    energy_count = 0
                    if isinstance(card, Pokemon):
                        energy_count = len(card.energies)
                    if context in (SelectContext.SWITCH, SelectContext.TO_ACTIVE):
                        if o.playerIndex == my_index:
                            score += energy_count * 2
                            if o.index == self.plan.attacker - 1:
                                score += 100
                            if card.id == Mega_Lucario_ex:
                                score += 8 if my_prize in (2, 3) else 20
                            elif card.id == Hariyama and energy_count >= 2:
                                score += 15
                            elif card.id == Makuhita and energy_count >= 2:
                                score += 10
                            elif card.id == Solrock:
                                score += 5
                            elif card.id == Riolu:
                                score += 4
                        else:
                            if o.index == self.plan.target - 1:
                                score += 100
                    elif context == SelectContext.SETUP_ACTIVE_POKEMON:
                        if card.id == Solrock:
                            score = 4 if state.firstPlayer != my_index else 2
                        elif card.id == Riolu:
                            score = 3
                        elif card.id == Makuhita:
                            score = 1
                    elif context == SelectContext.TO_HAND:
                        score = 200 - hand_counts[card.id] * 100
                        if card.id == Makuhita:
                            score += 10 if field_counts[card.id] < 1 else -10
                        elif card.id == Hariyama:
                            score += 20 if field_counts[Makuhita] >= 1 else -20
                        elif card.id == Lunatone:
                            score += -250 if field_counts[card.id] >= 1 else 60
                        elif card.id == Solrock:
                            score += -250 if field_counts[card.id] >= 1 else 50
                        elif card.id == Riolu:
                            total = field_counts[Riolu] + field_counts[Mega_Lucario_ex]
                            score += -150 if total >= 2 else (-3 if total >= 1 else 40)
                        elif card.id == Mega_Lucario_ex:
                            score += 40 if field_counts[Riolu] >= 1 else -15
                        elif card.id == Basic_Fighting_Energy:
                            score += 30 if not self.ability_used or not state.energyAttached else -1
                    elif context == SelectContext.ATTACH_FROM:
                        score = energy_score(card, o.area == AreaType.ACTIVE)
            elif o.type == OptionType.PLAY:
                card = get_card(obs, AreaType.HAND, o.index, my_index)
                data = card_table[card.id]
                if data.cardType == CardType.POKEMON:
                    score = 20000
                    if card.id in (Lunatone, Solrock):
                        score = -1 if field_counts[card.id] >= 1 else score
                    elif card.id == Riolu:
                        if field_counts[Riolu] + field_counts[Mega_Lucario_ex] >= 2:
                            score = -1
                else:
                    score = 10000
                    if card.id == Switch:
                        score = 6000 if self.plan.attacker > 0 else -1
                    elif card.id == Premium_Power_Pro:
                        if state.supporterPlayed and self.plan.remain_hp <= 0:
                            score = -1
                        elif not can_attack:
                            if not state.supporterPlayed and hand_counts[Carmine] > 0 and hand_counts[Lillie_Det] == 0:
                                score = 3050
                            else:
                                score = -1
                        else:
                            score = 5000
                    elif card.id == Boss_Orders:
                        score = 3200 if self.plan.target >= 1 else -1
                    elif card.id == Carmine:
                        score = -1 if deck_is_low else 3000
                    elif card.id == Lillie_Det:
                        score = -1 if deck_is_low else 3100
                    elif card.id in (Dusk_Ball, Poke_Pad) and deck_is_low:
                        score = -1
                    elif card.id == Gravity_Mountain:
                        score = -1 if stadium_id == 0 else score
            elif o.type == OptionType.ATTACH:
                card    = get_card(obs, AreaType.HAND, o.index, my_index)
                pokemon = get_card(obs, o.inPlayArea, o.inPlayIndex, my_index)
                if card.id == Hero_Cape:
                    score = 7000
                    if pokemon.id == Riolu:
                        score += 100
                    elif pokemon.id == Mega_Lucario_ex:
                        score += 200
                else:
                    score = energy_score(pokemon, o.inPlayArea == AreaType.ACTIVE)
                    if o.inPlayArea == AreaType.ACTIVE:
                        if self.plan.attacker == 0 and self.plan.energy:
                            score += 200
                    else:
                        if self.plan.attacker == 1 + o.inPlayIndex and self.plan.energy:
                            score += 200
            elif o.type == OptionType.EVOLVE:
                pokemon = get_card(obs, o.inPlayArea, o.inPlayIndex, my_index)
                score = 9000 + len(pokemon.energies)
                if pokemon.id == Makuhita and self.plan.target == 0:
                    score = -1
            elif o.type == OptionType.ABILITY:
                card = get_card(obs, o.area, o.index, my_index)
                score = 1 if card.id == 1267 else 30000  # Lumiose City
            elif o.type == OptionType.RETREAT:
                score = 2000 if self.plan.attacker >= 1 else -1
            elif o.type == OptionType.ATTACK:
                my_active = my_state.active[0] if my_state.active else None
                # Mega Lucario ex は EX なので Crustle に攻撃が通らない → 攻撃させない
                # Riolu は非EXなので Crustle に攻撃が通る → ブロックしない
                lucario_attacking_immune = (
                    opp_has_immune_line
                    and my_active is not None
                    and my_active.id == Mega_Lucario_ex
                )
                if self.plan.damage == 0 or lucario_attacking_immune:
                    score = -1  # 攻撃してもダメージなし、またはEX免疫ライン対策 → 攻撃しない
                else:
                    score = 1000
                    if self.plan.attack_index == 1:
                        if o.attackId == 983:
                            score += 100
                    else:
                        if o.attackId != 983:
                            score += 100

            scores.append(score)

        desc_indices = [i for i, _ in sorted(enumerate(scores), key=lambda x: x[1], reverse=True)]
        if context == SelectContext.MAIN:
            o = select.option[desc_indices[0]]
            if o.type == OptionType.ABILITY:
                card = get_card(obs, o.area, o.index, my_index)
                if card.id == Lunatone:
                    self.ability_used = True

        selected_set = set(desc_indices[:select.maxCount])
        self.last_scores_detail = [
            {
                "idx":      i,
                "score":    s,
                "type":     OptionType(select.option[i].type).name,
                "label":    self._option_label(obs, select.option[i], my_index),
                "selected": i in selected_set,
            }
            for i, s in enumerate(scores)
        ]

        # ---- デバッグ出力（可視化用） ----
        top = desc_indices[0]
        top_label = self._option_label(obs, select.option[top], my_index)
        top_score = scores[top]
        ctx_name = context.name if hasattr(context, 'name') else str(context)
        def _safe(s): return s.encode('ascii', 'replace').decode()
        print(f"[P{my_index+1} T{state.turn}] {ctx_name} -> {_safe(top_label)} ({top_score:.0f})")
        if self.plan.attacker >= 0:
            my_active = my_state.active[0] if my_state.active else None
            op_active = op_state.active[0] if op_state.active else None
            my_cards = ([my_active] if my_active else []) + list(my_state.bench)
            op_cards = ([op_active] if op_active else []) + list(op_state.bench)
            atk = my_cards[self.plan.attacker] if self.plan.attacker < len(my_cards) else None
            tgt = op_cards[self.plan.target]   if self.plan.target  < len(op_cards)  else None
            if atk and tgt:
                print(f"  plan: {_safe(self._card_name(atk.id))} -> {_safe(self._card_name(tgt.id))}"
                      f"  HP_left={self.plan.remain_hp}")

        return desc_indices[:select.maxCount]


# ---- MCTSエージェント ----

class MCTSAgent:
    """
    Flat Monte Carlo エージェント。
    MAIN コンテキストの選択のみMCTSで行い、サブ選択はルールベースに委譲する。
    """

    def __init__(self, deck, n_simulations=50, n_candidates=5):
        self.deck = deck
        self.n_simulations = n_simulations
        self.n_candidates = n_candidates
        self.rule = RuleAgent(deck)

    def __call__(self, obs_dict, deck):
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return self.deck

        # サブ選択（エネルギー・スイッチ先など）はルールベースに任せる
        if obs.select.context != SelectContext.MAIN:
            return self.rule(obs_dict, deck)

        # ルールベースでスコアリングし、上位候補のみMCTSで評価
        rule_indices = self.rule(obs_dict, deck)
        n_opts = len(obs.select.option)
        # ルール順 + 残りを追加して候補セットを作る
        candidates = list(dict.fromkeys(rule_indices + list(range(n_opts))))
        candidates = candidates[:min(self.n_candidates, n_opts)]

        if len(candidates) == 1:
            return candidates

        hidden = self._estimate_hidden(obs)
        if hidden is None:
            return rule_indices  # 推定失敗時はルールベースにフォールバック

        wins   = {a: 0 for a in candidates}
        totals = {a: 0 for a in candidates}
        sims_each = max(1, self.n_simulations // len(candidates))

        for a in candidates:
            for _ in range(sims_each):
                try:
                    root = search_begin(obs, *hidden)
                    nxt  = search_step(root.searchId, [a])
                    result = self._rollout(nxt)
                    search_end()
                    if result == obs.current.yourIndex:
                        wins[a] += 1
                    totals[a] += 1
                except Exception:
                    try:
                        search_end()
                    except Exception:
                        pass
                    totals[a] += 1

        best = max(candidates, key=lambda a: wins[a] / max(totals[a], 1))
        return [best]

    def _rollout(self, state):
        """ゲーム終了までランダムにプレイ。勝者インデックスを返す。"""
        for _ in range(500):
            obs = state.observation
            if obs.current and obs.current.result != -1:
                return obs.current.result
            if obs.select is None:
                return -1
            n = min(obs.select.maxCount, len(obs.select.option))
            action = random.sample(range(len(obs.select.option)), n)
            state = search_step(state.searchId, action)
        return -1

    def _estimate_hidden(self, obs):
        """search_begin に渡す隠れ情報を推定する。"""
        state    = obs.current
        mi       = state.yourIndex
        my_st    = state.players[mi]
        op_st    = state.players[1 - mi]

        def pokemon_ids(player_state):
            ids = []
            for p in player_state.active + player_state.bench:
                if p is not None:
                    ids.append(p.id)
                    ids += [c.id for c in p.energyCards]
                    ids += [c.id for c in p.tools]
                    ids += [c.id for c in p.preEvolution]
            return ids

        # 自分の見えているカード
        my_visible = (
            [c.id for c in my_st.hand] +
            [c.id for c in my_st.discard] +
            pokemon_ids(my_st) +
            [c.id for c in my_st.prize if c is not None]
        )

        # プールを self.deck から見えているカードを引いた残り
        def subtract(pool, used):
            pool = list(pool)
            for cid in used:
                try:
                    pool.remove(cid)
                except ValueError:
                    pass
            return pool

        my_pool = subtract(self.deck, my_visible)
        random.shuffle(my_pool)

        deck_count  = my_st.deckCount
        n_facedown_prize = sum(1 for p in my_st.prize if p is None)

        # プールが足りない場合はエネルギーで埋める
        while len(my_pool) < deck_count + n_facedown_prize:
            my_pool.append(Basic_Fighting_Energy)

        your_deck  = my_pool[:deck_count]
        your_prize = my_pool[deck_count:deck_count + n_facedown_prize]
        # 表向きサイドも追加
        your_prize += [c.id for c in my_st.prize if c is not None]

        # 相手の見えているカード
        op_visible = (
            [c.id for c in op_st.discard] +
            pokemon_ids(op_st) +
            [c.id for c in op_st.prize if c is not None]
        )

        # 相手のデッキは自分と同じデッキと仮定（ミラーマッチ想定）
        op_pool = subtract(self.deck, op_visible)
        random.shuffle(op_pool)

        op_deck_count   = op_st.deckCount
        n_op_facedown   = sum(1 for p in op_st.prize if p is None)
        op_hand_count   = op_st.handCount

        needed = op_deck_count + n_op_facedown + op_hand_count
        while len(op_pool) < needed:
            op_pool.append(Basic_Fighting_Energy)

        opponent_deck  = op_pool[:op_deck_count]
        op_pool        = op_pool[op_deck_count:]
        opponent_prize = op_pool[:n_op_facedown]
        opponent_prize += [c.id for c in op_st.prize if c is not None]
        opponent_hand  = op_pool[n_op_facedown:n_op_facedown + op_hand_count]

        # 相手のアクティブが表向きでない場合
        opponent_active = []
        if op_st.active and op_st.active[0] is None:
            for cid in opponent_deck:
                data = card_table.get(cid)
                if data and data.basic:
                    opponent_active = [cid]
                    break
            if not opponent_active:
                opponent_active = [Riolu]

        try:
            # 簡単なバリデーション
            assert len(your_deck)  == deck_count
            assert len(your_prize) == len(my_st.prize)
            assert len(opponent_deck)  == op_deck_count
            assert len(opponent_prize) == len(op_st.prize)
            assert len(opponent_hand)  == op_hand_count
        except AssertionError:
            return None

        return your_deck, your_prize, opponent_deck, opponent_prize, opponent_hand, opponent_active


# ---- UCB1 MCTS エージェント ----

class _MCTSNode:
    """MCTS 木のノード。自分の MAIN 選択点のみ追跡する。"""
    __slots__ = ('parent', 'action', 'children', 'wins', 'visits', 'untried')

    def __init__(self, parent=None, action=None):
        self.parent   = parent
        self.action   = action    # この節点に至った MAIN action index
        self.children = {}        # action -> _MCTSNode
        self.wins     = 0
        self.visits   = 0
        self.untried  = None      # 未試行アクションリスト（初訪時に設定）

    def ucb1(self, c):
        if self.visits == 0:
            return float('inf')
        return self.wins / self.visits + c * math.sqrt(
            math.log(self.parent.visits) / self.visits
        )


class UCBMCTSAgent:
    """
    UCB1 木探索 MCTS エージェント。
    - 自分の MAIN 選択点のみ木を構築する
    - それ以外（サブ選択・相手番）はランダム
    - ロールアウトもランダム（評価関数に差し替え可能）
    - hidden info 推定は Flat MCTS と同じ
    """

    def __init__(self, deck, n_simulations=100, c=1.414):
        self.deck          = deck
        self.n_simulations = n_simulations
        self.c             = c
        self.rule          = RuleAgent(deck)

    def __call__(self, obs_dict, deck):
        obs = to_observation_class(obs_dict)
        if obs.select is None:
            return self.deck
        if obs.select.context != SelectContext.MAIN:
            return self.rule(obs_dict, deck)

        my_index = obs.current.yourIndex
        n_options = len(obs.select.option)
        if n_options <= 1:
            return list(range(n_options))

        hidden = self._estimate_hidden(obs)
        if hidden is None:
            return self.rule(obs_dict, deck)

        root = _MCTSNode()
        root.untried = list(range(n_options))
        root.visits  = 1  # UCB1 の log(parent.visits) が 0 にならないよう

        for _ in range(self.n_simulations):
            try:
                root_state = search_begin(obs, *hidden)
            except Exception:
                continue
            try:
                leaf, result = self._simulate(root, root_state, my_index)
                search_end()
            except Exception:
                try:
                    search_end()
                except Exception:
                    pass
                continue

            # バックプロパゲーション（親チェーンを辿る）
            node = leaf
            while node is not None:
                node.visits += 1
                node.wins += result  # float [0, 1]
                node = node.parent

        if not root.children:
            return self.rule(obs_dict, deck)

        # 最も多く訪問された子の action を返す（UCB1 ではなく visits で選ぶのが標準）
        best = max(root.children.values(), key=lambda n: n.visits)
        return [best.action]

    def _simulate(self, root_node, root_state, my_index):
        """1シミュレーション。(leaf_node, result) を返す。"""
        node  = root_node
        state = root_state

        for _ in range(2000):
            obs = state.observation

            if obs.current and obs.current.result != -1:
                return node, (1.0 if obs.current.result == my_index else 0.0)
            if obs.select is None:
                return node, board_eval(obs, my_index)

            is_my_main = (
                obs.current is not None and
                obs.current.yourIndex == my_index and
                obs.select.context == SelectContext.MAIN
            )

            if is_my_main:
                n_opts = len(obs.select.option)

                if node.untried is None:
                    node.untried = list(range(n_opts))
                    random.shuffle(node.untried)

                if node.untried:
                    # ── 展開: 未試行のアクションを試す ──
                    action = node.untried.pop()
                    child  = _MCTSNode(parent=node, action=action)
                    node.children[action] = child
                    node  = child
                    state = search_step(state.searchId, [action])
                    # 展開後はロールアウト
                    result = self._rollout(state, my_index)
                    return node, result
                else:
                    # ── 選択: UCB1 で最良の子を選ぶ ──
                    best_child = max(
                        node.children.values(),
                        key=lambda n: n.ucb1(self.c)
                    )
                    node  = best_child
                    state = search_step(state.searchId, [best_child.action])
            else:
                # サブ選択 or 相手番 → ランダム
                n      = min(obs.select.maxCount, len(obs.select.option))
                action = random.sample(range(len(obs.select.option)), n)
                state  = search_step(state.searchId, action)

        return node, board_eval(state.observation, my_index)

    def _rollout(self, state, my_index, max_depth=50):
        """深さ制限ランダムロールアウト + 盤面評価。勝利確率 [0, 1] を返す。"""
        for _ in range(max_depth):
            obs = state.observation
            if obs.current and obs.current.result != -1:
                return 1.0 if obs.current.result == my_index else 0.0
            if obs.select is None:
                return board_eval(obs, my_index)
            n = min(obs.select.maxCount, len(obs.select.option))
            action = random.sample(range(len(obs.select.option)), n)
            state = search_step(state.searchId, action)
        return board_eval(state.observation, my_index)

    # _estimate_hidden は MCTSAgent と共通ロジック ─ 委譲する
    def _estimate_hidden(self, obs):
        return MCTSAgent(self.deck)._estimate_hidden(obs)


# ---- Crustle エージェント ----

class CrustleAgent:
    """イワパレスデッキ用エージェント（refs notebook ベース）。
    MAIN: ATTACH > EVOLVE > PLAY > ABILITY > ATTACK > RETREAT の優先度でプレイ。
    その他コンテキスト: 最初のオプションを選択。
    """

    def __init__(self, deck):
        self.deck = deck

    def __call__(self, obs_dict, deck):
        obs = obs_dict if not isinstance(obs_dict, dict) else to_observation_class(obs_dict)
        if obs.select is None:
            return self.deck

        ctx = obs.select.context
        pri = {
            OptionType.ATTACH:  1000,
            OptionType.EVOLVE:  800,
            OptionType.PLAY:    600,
            OptionType.ABILITY: 400,
            OptionType.ATTACK:  100,
            OptionType.RETREAT: -1,
        }

        n = len(obs.select.option)
        if ctx == SelectContext.MAIN:
            scores = [pri.get(OptionType(o.type), 0) for o in obs.select.option]
        else:
            scores = [1] * n

        desc = sorted(range(n), key=lambda i: scores[i], reverse=True)
        k = min(obs.select.maxCount, n)
        return desc[:k]


# ---- ランダムエージェント ----

def random_agent(obs_dict, deck):
    obs = to_observation_class(obs_dict)
    if obs.select is None:
        return deck
    return random.sample(range(len(obs.select.option)), obs.select.maxCount)


# ---- 対戦実行 ----

def run_game(agent0, agent1, deck0, deck1, verbose=False, return_reason=False):
    """1試合実行。勝者インデックスを返す。引き分けは-1。
    return_reason=True のとき (result, reason_str) のタプルを返す。
    """
    obs_dict, start = battle_start(deck0, deck1)
    if obs_dict is None:
        if verbose:
            print(f'  Battle start failed (errorType={start.errorType})', file=sys.stderr)
        return (-1, '?') if return_reason else -1

    agents = [agent0, agent1]
    decks  = [deck0, deck1]
    result = -1
    reason_str = '?'
    _reasons = {1: 'Prize0', 2: 'DeckOut', 3: 'NoActive', 4: 'Effect'}

    while True:
        obs = to_observation_class(obs_dict)
        for log in obs.logs:
            if log.type == LogType.RESULT:
                result = log.result
                reason_str = _reasons.get(log.reason, '?')
                if verbose:
                    winner = f'player{result}' if result != 2 else 'Draw'
                    print(f'  Result: {winner} ({reason_str})')

        if obs.current and obs.current.result != -1:
            break

        player = 0 if obs.current is None else obs.current.yourIndex
        action = agents[player](obs_dict, decks[player])
        obs_dict = battle_select(action)

    battle_finish()
    r = result if result != 2 else -1
    return (r, reason_str) if return_reason else r


# ---- エントリポイント ----

if __name__ == '__main__':
    raw = sys.argv[1:]
    use_json = '--json' in raw
    raw = [a for a in raw if a != '--json']

    agent0_type = 'rule'
    agent1_type = 'random'
    nums = []
    i = 0
    while i < len(raw):
        if raw[i] == '--agent0' and i + 1 < len(raw):
            agent0_type = raw[i + 1]; i += 2
        elif raw[i] == '--agent1' and i + 1 < len(raw):
            agent1_type = raw[i + 1]; i += 2
        else:
            nums.append(raw[i]); i += 1
    N = int(nums[0]) if nums else 20
    verbose = not use_json and N <= 5

    def make_agent(kind):
        if kind == 'rule':
            return RuleAgent(LUCARIO_DECK)
        elif kind == 'mcts':
            return MCTSAgent(LUCARIO_DECK, n_simulations=50)
        elif kind == 'ucb':
            return UCBMCTSAgent(LUCARIO_DECK, n_simulations=200)
        else:
            return random_agent

    if not use_json:
        print(f'Running {N} games (agent0={agent0_type} vs agent1={agent1_type})...')

    wins = [0, 0]
    draws = 0
    game_results = []

    for i in range(N):
        a0 = make_agent(agent0_type)
        a1 = make_agent(agent1_type)
        if verbose:
            print(f'Game {i+1}:')
        r = run_game(a0, a1, LUCARIO_DECK, LUCARIO_DECK, verbose=verbose)
        game_results.append(r)
        if r == 0:
            wins[0] += 1
        elif r == 1:
            wins[1] += 1
        else:
            draws += 1
        if not use_json and not verbose:
            winner = f'player{r}' if r != -1 else 'Draw'
            print(f'  Game {i+1}/{N}: {winner}  ({wins[0]}-{wins[1]})', flush=True)

    if use_json:
        print(json.dumps({'n': N, 'wins': wins, 'draws': draws, 'results': game_results}))
    else:
        print(f'\n=== Results ({N} games) ===')
        print(f'Player0 ({agent0_type}): {wins[0]} wins ({wins[0]/N*100:.1f}%)')
        print(f'Player1 ({agent1_type}): {wins[1]} wins ({wins[1]/N*100:.1f}%)')
        print(f'Draws:                  {draws}')
