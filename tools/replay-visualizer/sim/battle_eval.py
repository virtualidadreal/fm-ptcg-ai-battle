"""
battle_eval.py - ポケカAI 共有評価ライブラリ

エネルギー管理・盤面評価の関数群。
run_game.py や今後のエージェントで共通利用する。

使い方:
    import sys
    sys.path.insert(0, 'notebooks/pokemon-tcg-ai-battle')
    from battle_eval import turns_to_ready, turns_to_survive, turns_to_ko, energy_attach_score
"""

import sys

_CG_PATH = 'data/raw/pokemon-tcg-ai-battle/sample_submission'
if _CG_PATH not in sys.path:
    sys.path.insert(0, _CG_PATH)

from cg.api import EnergyType


# ---- デッキ内ポケモンの攻撃情報 ----
# card_id -> {min_energy, min_damage, full_energy, damage}
#   min_energy  : 最も弱い攻撃ができる最小エネルギー数
#   min_damage  : min_energy での攻撃ダメージ（弱点・抵抗力適用前）
#   full_energy : メイン攻撃（最大打点）に必要なエネルギー数
#   damage      : メイン攻撃の打点（弱点・抵抗力適用前）
#
# デッキが変わった場合はこの辞書を上書きするか、関数に attack_info を渡す。
LUCARIO_ATTACK_INFO = {
    678: {"min_energy": 1, "min_damage": 130, "full_energy": 2, "damage": 270},  # Mega Lucario ex（1エネ=130、2エネ=270）
    677: {"min_energy": 1, "min_damage": 130, "full_energy": 2, "damage": 270},  # Riolu → 進化でルカリオになる、エネルギーは引き継ぐ
    674: {"min_energy": 3, "min_damage": 210, "full_energy": 3, "damage": 210},  # Hariyama（技は1種類）
    673: {"min_energy": 3, "min_damage": 210, "full_energy": 3, "damage": 210},  # Makuhita → 進化でハリーマンになる
    676: {"min_energy": 1, "min_damage": 70,  "full_energy": 1, "damage": 70},   # Solrock
    675: {"min_energy": 99, "min_damage": 0,  "full_energy": 99, "damage": 0},   # Lunatone（攻撃しない）
}


def _apply_type_modifier(base_damage: int, defender_card) -> int:
    """弱点・抵抗力（ファイティングタイプ攻撃を前提）を適用したダメージを返す。"""
    if defender_card is None or base_damage <= 0:
        return base_damage
    if defender_card.weakness == EnergyType.FIGHTING:
        return base_damage * 2
    if defender_card.resistance == EnergyType.FIGHTING:
        return max(0, base_damage - 30)
    return base_damage


def turns_to_ready(pokemon, attack_info=None) -> int:
    """
    ポケモンがメイン攻撃可能になるまでのターン数（毎ターン1エネ付けられる前提）。
    0 → 今すぐ攻撃可能。99 → 攻撃不可能。

    例:
        Mega Lucario ex (エネ0) → 2
        Mega Lucario ex (エネ1) → 1
        Mega Lucario ex (エネ2) → 0
    """
    if attack_info is None:
        attack_info = LUCARIO_ATTACK_INFO
    info = attack_info.get(pokemon.id)
    if info is None:
        return 99
    return max(0, info["full_energy"] - len(pokemon.energies))


def estimate_damage(attacker, defender, card_table, attack_info=None) -> int:
    """
    attacker が defender に与えるダメージを推定（弱点・抵抗力込み、現在のエネルギーで使える最大攻撃）。
    min_energy に満たない場合は 0 を返す。
    """
    if attack_info is None:
        attack_info = LUCARIO_ATTACK_INFO
    info = attack_info.get(attacker.id)
    if info is None or info["damage"] == 0:
        return 0
    cur_energy = len(attacker.energies)
    if cur_energy < info["min_energy"]:
        return 0
    base = info["damage"] if cur_energy >= info["full_energy"] else info.get("min_damage", info["damage"])
    return _apply_type_modifier(base, card_table.get(defender.id) if card_table else None)


def turns_to_survive(defender, attacker, card_table, attack_info=None) -> int:
    """
    defender が attacker から何ターン持ちこたえるか。
    毎ターン attacker は1エネルギーを獲得すると仮定。

    旧実装との違い（より正確）:
      - チャージ中でも min_energy に達すれば弱い攻撃でダメージが入る
      - 例: Riolu(0e) vs HP270 → ターン1で130dmg、ターン2で270dmg → 2ターンでKO（旧実装は3と過大評価）

    戻り値: defender が KO されるターン番号（1=次のターンKO、99=実質的に倒されない）。

    例:
        Mega Lucario ex(2e) vs Hariyama HP160 → ターン1に270dmg → 1
        Riolu(0e) vs Mega Lucario ex HP270     → ターン1で130、ターン2で270 → 2
        Hariyama(0e) vs Mega Lucario ex HP270  → 3ターンチャージ後ターン4でKO → 4
    """
    if attack_info is None:
        attack_info = LUCARIO_ATTACK_INFO

    info = attack_info.get(attacker.id)
    if info is None or info["damage"] == 0:
        return 99

    cur_energy  = len(attacker.energies)
    min_energy  = info["min_energy"]
    min_damage  = info.get("min_damage", info["damage"])
    full_energy = info["full_energy"]
    full_damage = info["damage"]

    defender_card = card_table.get(defender.id) if card_table else None
    min_dmg_eff   = _apply_type_modifier(min_damage,  defender_card)
    full_dmg_eff  = _apply_type_modifier(full_damage, defender_card)

    if full_dmg_eff <= 0:
        return 99

    hp = defender.hp
    for turn in range(1, 40):
        energy = cur_energy + turn  # 毎ターン1エネ付加
        if energy >= full_energy:
            hp -= full_dmg_eff
        elif energy >= min_energy:
            hp -= min_dmg_eff
        # energy < min_energy → 攻撃できない、このターンはダメージなし
        if hp <= 0:
            return turn

    return 99  # 40ターン超えても生き残る


def turns_to_ko(attacker, defender, card_table, attack_info=None) -> int:
    """
    attacker が defender を KO するまでのターン数（攻撃者視点）。
    turns_to_survive(defender, attacker, ...) と等価だが意味が明確。

    例:
        Mega Lucario ex(2e) → Riolu HP60: ターン1でKO → 1
        Makuhita(0e) → Mega Lucario ex HP270: 3ターンチャージ後ターン4でKO → 4
    """
    return turns_to_survive(defender, attacker, card_table, attack_info)


def energy_attach_score(
    candidate,
    candidate_is_active: bool,
    my_active,
    opp_active,
    card_table,
    attack_info=None,
) -> float:
    """
    candidate へのエネルギー付与スコア（高いほど優先）。

    設計方針：
      - 攻撃までのターンが少ないほど優先（urgency）
      - 倒される前に攻撃できないなら大幅ペナルティ
      - アクティブが盾として機能しているときのベンチは軽いボーナス
    """
    if attack_info is None:
        attack_info = LUCARIO_ATTACK_INFO

    ready_turns = turns_to_ready(candidate, attack_info)

    # 攻撃しないポケモン（Lunatoneなど）にはエネルギーをつけない
    if ready_turns >= 10:
        return 1000

    # 既に攻撃準備完了なら追加エネルギーは不要
    if ready_turns == 0:
        return 5000

    # 1枚付けた後の残り準備ターン
    ready_after_attach = max(0, ready_turns - 1)

    # アクティブが何ターン持ちこたえるか
    active_survive = turns_to_survive(my_active, opp_active, card_table, attack_info)

    # 攻撃が近いほど高い urgency ボーナス
    urgency_bonus = max(0, 200 - ready_after_attach * 100)
    base = 8000 + urgency_bonus

    if candidate_is_active:
        # 倒される前に攻撃できない → 大幅ペナルティ
        if active_survive <= ready_after_attach:
            base -= 2000
    else:
        # ベンチへの付与
        if active_survive >= ready_after_attach:
            base += 50   # 盾が機能しているとき：軽いボーナス
        else:
            base -= 300  # 盾が持たないとき：やや減点

    return base
