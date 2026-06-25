"""Genera variantes del agente base cambiando SOLO la tabla MAIN_PRIORITY, para
A/B de hipótesis (¿"atacar antes" bate a "setup-first"?). Deriva de agent/main.py
(no duplica código a mano -> no hay drift). Cada variante = dir con main.py + deck.csv.

Uso (en docker o local): python experiments/gen_variants.py
"""
import os, re, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = open(os.path.join(ROOT, "agent", "main.py")).read()
DECK = os.path.join(ROOT, "agent", "deck.csv")

# bloque exacto a sustituir en el agente base
PAT = re.compile(r"MAIN_PRIORITY = \{.*?\}", re.DOTALL)

VARIANTS = {
    # atacar SIEMPRE que sea legal (por encima de todo el setup): test directo del hallazgo
    "attack_asap": {
        OPT: v for OPT, v in [
            ("OPT_ATTACK", 200), ("OPT_EVOLVE", 100), ("OPT_ABILITY", 95),
            ("OPT_ATTACH", 90), ("OPT_PLAY", 80), ("OPT_RETREAT", 20), ("OPT_END", 1),
        ]
    },
    # atacar por encima de PLAY pero por debajo de evolve/ability/attach (punto intermedio)
    "attack_mid": {
        OPT: v for OPT, v in [
            ("OPT_EVOLVE", 100), ("OPT_ABILITY", 95), ("OPT_ATTACH", 90),
            ("OPT_ATTACK", 85), ("OPT_PLAY", 80), ("OPT_RETREAT", 20), ("OPT_END", 1),
        ]
    },
}


def render_block(pri):
    lines = ["MAIN_PRIORITY = {"]
    for k, v in pri.items():
        lines.append(f"    {k}: {v},")
    lines.append("}")
    return "\n".join(lines)


def main():
    assert PAT.search(BASE), "no encontré el bloque MAIN_PRIORITY en agent/main.py"
    outroot = os.path.join(ROOT, "experiments", "variants")
    for name, pri in VARIANTS.items():
        d = os.path.join(outroot, name)
        os.makedirs(d, exist_ok=True)
        src = PAT.sub(render_block(pri), BASE, count=1)
        # marca de procedencia para que quede claro que es derivado
        src = f"# DERIVADO de agent/main.py por experiments/gen_variants.py — variante '{name}'.\n" + src
        open(os.path.join(d, "main.py"), "w").write(src)
        shutil.copyfile(DECK, os.path.join(d, "deck.csv"))
        print(f"[ok] {name}: main.py (ATTACK={pri.get('OPT_ATTACK')}) + deck.csv")
    print("variantes en experiments/variants/")


if __name__ == "__main__":
    main()
