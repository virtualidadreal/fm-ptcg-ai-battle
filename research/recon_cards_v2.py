import sys, json
sys.path.insert(0, "/work/agents_official/sabrina_v2")
from cg.api import all_card_data, all_attack, CardType, EnergyType

cards = all_card_data()
attacks = all_attack()
atk_by_id = {a.attackId: a for a in attacks}
card_by_id = {c.cardId: c for c in cards}

# Targets
targets = [140, 305, 1197, 13, 1227, 66, 65, 743]

def etype(e):
    try: return EnergyType(e).name
    except: return str(e)

def dump(cid):
    c = card_by_id.get(cid)
    if not c:
        print(f"\n##### {cid}: NOT FOUND")
        return
    print(f"\n##### {cid} {c.name}")
    print(f"  cardType={CardType(c.cardType).name} hp={c.hp} retreat={c.retreatCost}")
    print(f"  basic={c.basic} stage1={c.stage1} stage2={c.stage2} ex={c.ex} megaEx={c.megaEx} tera={c.tera} aceSpec={c.aceSpec}")
    print(f"  evolvesFrom={c.evolvesFrom!r} energyType={etype(c.energyType)} weakness={c.weakness} resistance={c.resistance}")
    for s in c.skills:
        print(f"  SKILL [{s.name}]: {s.text}")
    for aid in c.attacks:
        a = atk_by_id.get(aid)
        if a:
            cost = "+".join(etype(e) for e in a.energies) if a.energies else "(none)"
            print(f"  ATTACK id={aid} [{a.name}] cost={cost} dmg={a.damage} :: {a.text}")

for t in targets:
    dump(t)

# Also: who evolves into Dudunsparce 66? find cards whose evolvesFrom matches 305/65 names
print("\n##### EVOLUTION CHECK")
d305 = card_by_id.get(305); d65 = card_by_id.get(65); d66 = card_by_id.get(66)
print(f"  305 name={d305.name!r} stage1={d305.stage1 if d305 else '?'}")
print(f"  65  name={d65.name!r}" if d65 else "  65 NOT FOUND")
print(f"  66  name={d66.name!r} evolvesFrom={d66.evolvesFrom!r}" if d66 else "  66 NOT FOUND")
# All cards named Dudunsparce
for c in cards:
    if "dudunsparce" in c.name.lower():
        print(f"  Dudunsparce print id={c.cardId} evolvesFrom={c.evolvesFrom!r} stage2={c.stage2}")
for c in cards:
    if "dunsparce" in c.name.lower() and "dudun" not in c.name.lower():
        print(f"  Dunsparce  print id={c.cardId} basic={c.basic} name={c.name!r}")
