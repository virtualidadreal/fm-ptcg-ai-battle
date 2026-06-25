"""
Preprocess the official EN_Card_Data.csv into a compact agent_v2/cards.json.

Aggregates the multi-row-per-card CSV (one row per Move/Ability) into one object
per Card ID:
  { "hp": int|null, "type": str, "weakness": str, "retreat": int|null,
    "attacks": [ {"name": str, "energy_count": int, "damage": int}, ... ] }

Robustness rules (per spec):
  - Use csv module (quoted commas), NOT split(',').
  - energy_count = number of energy symbols in Cost: count '{X}' tokens AND '●'.
    "n/a"/"" -> 0.
  - damage = first integer in Damage (regex \\d+). "n/a"/"" -> 0. Ignore '+'/'x' for
    now (store the base number).
  - Unknown symbols / kanji ({R}, 竜, etc.) must never crash: leave the field neutral.
  - Skip [Ability]/[Tera]/[Poke-Power]/[Poke-Body] "moves": they are not attacks.
"""

from __future__ import annotations

import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "..", "data", "competition", "EN_Card_Data.csv")
OUT_PATH = os.path.join(HERE, "cards.json")

# column indices (verified against header)
C_ID = 0
C_NAME = 1
C_CATEGORY = 6
C_HP = 8
C_TYPE = 9
C_WEAK = 10
C_RETREAT = 12
C_MOVE = 13
C_COST = 14
C_DAMAGE = 15

_ENERGY_TOKEN_RE = re.compile(r"\{[^}]*\}")  # matches {R}, {G}, {C}, {Stellar}, ...
_INT_RE = re.compile(r"\d+")
_BRACKET_TAG_RE = re.compile(r"\[[^\]]*\]")  # [Ability], [Tera], [Poke-Power], ...


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
    """First integer in the Damage field; 0 if absent/na. Ignores +/x suffixes."""
    if _is_na(s):
        return 0
    m = _INT_RE.search(str(s))
    return int(m.group()) if m else 0


def parse_energy_count(cost):
    """Number of energy symbols: count '{...}' tokens plus literal bullets."""
    if _is_na(cost):
        return 0
    try:
        s = str(cost)
        n_braced = len(_ENERGY_TOKEN_RE.findall(s))
        # bullet variants seen in real TCG data: ● (U+25CF). Count any bullet-ish glyph.
        n_bullets = sum(s.count(ch) for ch in ("●", "⬤", "•"))
        return n_braced + n_bullets
    except Exception:
        return 0


def normalize_type(s):
    """Keep the type tag as-is ({R},{G},...) trimmed; neutral '' if missing/odd."""
    if _is_na(s):
        return ""
    try:
        return str(s).strip()
    except Exception:
        return ""


def is_real_attack(move_name):
    """An attack is a move that is NOT an Ability/Tera/Power/Body tag-only entry."""
    if _is_na(move_name):
        return False
    try:
        name = str(move_name).strip()
        # strip leading newlines/whitespace the CSV sometimes has (e.g. '\nComet Punch')
        name = name.replace("\n", " ").strip()
        if not name:
            return False
        low = name.lower()
        # bracketed-tag-only entries ([Ability] X with no cost are abilities, but
        # an attack name might *also* contain a tag in rare cases). We treat a move
        # as a non-attack when it STARTS with a known non-attack tag.
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


def main():
    cards = {}
    parsed_rows = 0
    skipped_short = 0

    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        for row in reader:
            try:
                if len(row) <= C_DAMAGE:
                    skipped_short += 1
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
                    cards[cid_key] = {
                        "hp": parse_int_or_none(row[C_HP]),
                        "type": normalize_type(row[C_TYPE]),
                        "weakness": normalize_type(row[C_WEAK]),
                        "retreat": parse_int_or_none(row[C_RETREAT]),
                        "attacks": [],
                    }
                entry = cards[cid_key]

                # backfill static fields if the first row was missing them
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
                # never crash on a weird row; just skip it
                skipped_short += 1
                continue

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, separators=(",", ":"))

    # ── summary ──
    n_cards = len(cards)
    n_with_hp = sum(1 for c in cards.values() if c["hp"])
    n_with_attacks = sum(1 for c in cards.values() if c["attacks"])
    n_attacks = sum(len(c["attacks"]) for c in cards.values())
    print(f"parsed rows: {parsed_rows}  skipped: {skipped_short}")
    print(f"cards: {n_cards}  with_hp: {n_with_hp}  with_attacks: {n_with_attacks}  total_attacks: {n_attacks}")
    # a few examples
    for ex in ("21", "23", "30", "119", "1"):
        if ex in cards:
            print(f"  [{ex}] {json.dumps(cards[ex], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
