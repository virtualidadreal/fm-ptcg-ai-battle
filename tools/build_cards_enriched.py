"""
Build data/cards_enriched.json from the official EN_Card_Data.csv.

Same schema as agent_v2/cards.json (hp/type/weakness/retreat/attacks) PLUS
prize-awareness fields per card:
  - "rule"        (str): raw Rule column value, "" if n/a
  - "category"    (str): raw Category column value, "" if n/a
  - "stage"       (str): raw Stage/Type column value (for transparency/debug)
  - "is_pokemon"  (bool): True if this card is a Pokemon (derived from Stage)
  - "prize_value" (int|null): prizes the OPPONENT takes when this card is KO'd.
        3  -> "Mega Pokémon ex"
        2  -> "Pokémon ex"        (non-Mega ex)
        1  -> normal Pokemon
        null -> not a Pokemon (Trainer / Energy / Stadium / Tool ...)

Robustness reuses agent_v2/build_cards.py conventions:
  - csv module (handles quoted commas), never split(',').
  - Never crash on kanji / weird symbols ({R}, 竜, ●, ...): skip the row.
  - Aggregates the multi-row-per-card CSV (one row per Move) into one object.

DERIVATION RULES
----------------
is_pokemon: the Stage column ("Stage (Pokémon)/Type (Energy and Trainer)")
  carries the literal word "Pokémon" for every Pokemon row
  (Basic/Stage 1/Stage 2 Pokémon). Energy (Basic/Special Energy) and Trainer
  rows (Item/Supporter/Stadium/Pokémon Tool) do NOT match the standalone
  "Pokémon" stage tag. We test for "pokémon" in the lowercased Stage AND that it
  is one of the known Pokemon stages, so "Pokémon Tool" is NOT counted as a
  Pokemon. Category is NOT used for this (it is "n/a" for >50% of cards).

prize_value: comes from the Rule column.
  - "Mega Pokémon ex"  -> 3
  - "Pokémon ex"       -> 2   (substring match, but excluding the Mega case)
  - anything else, when is_pokemon -> 1
  - not a Pokemon -> null

CAVEATS (reported, not silently dropped):
  - prize_value here is the card's BASE printed value. In-game effects that
    change prizes taken (e.g. some Trainer/attack effects, or rule-box edge
    cases) are NOT modeled. A rule-based agent should read this as the static
    "how juicy is this target" prior.
  - "ACE SPEC" is a Trainer rule, not a Pokemon -> prize_value null.
  - "Trainer's Pokémon (...)" cards ARE Pokemon (Stage says "... Pokémon"),
    so they get prize_value 1 (or 2/3 if also ex) — correct.
"""

from __future__ import annotations

import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "..", "data", "competition", "EN_Card_Data.csv")
OUT_PATH = os.path.join(HERE, "..", "data", "cards_enriched.json")

# column indices (verified against header)
C_ID = 0
C_NAME = 1
C_STAGE = 4
C_RULE = 5
C_CATEGORY = 6
C_HP = 8
C_TYPE = 9
C_WEAK = 10
C_RETREAT = 12
C_MOVE = 13
C_COST = 14
C_DAMAGE = 15

_ENERGY_TOKEN_RE = re.compile(r"\{[^}]*\}")
_INT_RE = re.compile(r"\d+")

# Stages that are genuine Pokemon. "Pokémon Tool" is a Trainer, excluded.
_POKEMON_STAGES = {
    "basic pokémon",
    "stage 1 pokémon",
    "stage 2 pokémon",
}


def _is_na(s):
    if s is None:
        return True
    t = str(s).strip().lower()
    return t == "" or t == "n/a"


def parse_int_or_none(s):
    if _is_na(s):
        return None
    m = _INT_RE.search(str(s))
    return int(m.group()) if m else None


def parse_damage(s):
    if _is_na(s):
        return 0
    m = _INT_RE.search(str(s))
    return int(m.group()) if m else 0


def parse_energy_count(cost):
    if _is_na(cost):
        return 0
    try:
        s = str(cost)
        n_braced = len(_ENERGY_TOKEN_RE.findall(s))
        n_bullets = sum(s.count(ch) for ch in ("●", "⬤", "•"))
        return n_braced + n_bullets
    except Exception:
        return 0


def normalize_type(s):
    if _is_na(s):
        return ""
    try:
        return str(s).strip()
    except Exception:
        return ""


def clean_text(s):
    if _is_na(s):
        return ""
    try:
        return str(s).replace("\n", " ").strip()
    except Exception:
        return ""


def is_real_attack(move_name):
    if _is_na(move_name):
        return False
    try:
        name = str(move_name).replace("\n", " ").strip()
        if not name:
            return False
        low = name.lower()
        for tag in ("[ability]", "[tera]", "[poke-power]", "[poke-body]",
                    "[poké-power]", "[poké-body]", "[ancient trait]"):
            if low.startswith(tag):
                return False
        return True
    except Exception:
        return False


def clean_name(move_name):
    try:
        return str(move_name).replace("\n", " ").strip()
    except Exception:
        return ""


def derive_is_pokemon(stage):
    """True only for genuine Pokemon stages (Basic / Stage 1 / Stage 2)."""
    try:
        low = str(stage).strip().lower()
    except Exception:
        return False
    return low in _POKEMON_STAGES


def derive_prize_value(rule, is_pokemon):
    """Base printed prize value the opponent takes on KO. null if not a Pokemon."""
    if not is_pokemon:
        return None
    try:
        low = str(rule).strip().lower()
    except Exception:
        low = ""
    if "mega" in low and "pokémon ex" in low:
        return 3
    if "pokémon ex" in low:
        return 2
    return 1


def main():
    cards = {}
    parsed_rows = 0
    skipped = 0

    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)  # header
        for row in reader:
            try:
                if len(row) <= C_DAMAGE:
                    skipped += 1
                    continue
                raw_id = row[C_ID].strip()
                if not raw_id:
                    continue
                try:
                    cid = int(raw_id)
                except Exception:
                    continue
                cid_key = str(cid)

                if cid_key not in cards:
                    stage = clean_text(row[C_STAGE])
                    rule = clean_text(row[C_RULE])
                    is_pk = derive_is_pokemon(stage)
                    cards[cid_key] = {
                        "hp": parse_int_or_none(row[C_HP]),
                        "type": normalize_type(row[C_TYPE]),
                        "weakness": normalize_type(row[C_WEAK]),
                        "retreat": parse_int_or_none(row[C_RETREAT]),
                        "attacks": [],
                        "rule": rule,
                        "category": clean_text(row[C_CATEGORY]),
                        "stage": stage,
                        "is_pokemon": is_pk,
                        "prize_value": derive_prize_value(rule, is_pk),
                    }
                entry = cards[cid_key]

                # backfill static fields if first row was missing them
                if entry["hp"] is None:
                    entry["hp"] = parse_int_or_none(row[C_HP])
                if not entry["type"]:
                    entry["type"] = normalize_type(row[C_TYPE])
                if not entry["weakness"]:
                    entry["weakness"] = normalize_type(row[C_WEAK])
                if entry["retreat"] is None:
                    entry["retreat"] = parse_int_or_none(row[C_RETREAT])

                move = row[C_MOVE]
                if is_real_attack(move):
                    entry["attacks"].append({
                        "name": clean_name(move),
                        "energy_count": parse_energy_count(row[C_COST]),
                        "damage": parse_damage(row[C_DAMAGE]),
                    })
                parsed_rows += 1
            except Exception:
                skipped += 1
                continue

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, separators=(",", ":"))

    # ── verification summary ──
    n_cards = len(cards)
    pokemon = [c for c in cards.values() if c["is_pokemon"]]
    n_pk = len(pokemon)

    dist = {}
    for c in cards.values():
        k = c["prize_value"]
        dist[k] = dist.get(k, 0) + 1

    n_complete = sum(
        1 for c in pokemon
        if c["hp"] and c["attacks"] and c["prize_value"] is not None
    )
    cov = (100.0 * n_complete / n_pk) if n_pk else 0.0

    print(f"OUT: {os.path.abspath(OUT_PATH)}")
    print(f"parsed rows: {parsed_rows}  skipped: {skipped}")
    print(f"total cards: {n_cards}  pokemon: {n_pk}")
    print(f"prize_value distribution: {dist}")
    print(f"pokemon w/ hp+attacks+prize complete: {n_complete}/{n_pk} = {cov:.1f}%")

    # spot-check: how many ex / mega ex, and a few examples by prize
    by_prize = {3: [], 2: [], 1: []}
    for cid, c in cards.items():
        pv = c["prize_value"]
        if pv in by_prize and len(by_prize[pv]) < 3:
            by_prize[pv].append((cid, c.get("rule"), c.get("stage")))
    for pv in (3, 2, 1):
        print(f"  prize={pv} examples: {by_prize[pv]}")

    # pokemon missing attacks (caveat candidates)
    no_atk = [cid for cid, c in cards.items() if c["is_pokemon"] and not c["attacks"]]
    print(f"  pokemon with 0 attacks (ability-only/edge): {len(no_atk)}")


if __name__ == "__main__":
    main()
