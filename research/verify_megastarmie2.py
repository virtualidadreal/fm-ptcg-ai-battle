#!/usr/bin/env python3
"""Adversarial verification v2 - deduped events. READ-ONLY."""
import json, os
from collections import Counter

BASE = "/Users/franmilla/FMA/proyectos/ptcg-ai-battle"
ANA = os.path.join(BASE, "data/megastarmie_analysis")
CARDS = json.load(open(os.path.join(BASE, "data/cards_enriched.json")))
cardmap = {c["id"]: c for c in CARDS} if isinstance(CARDS, list) else {}

EVOLVE, ATTACK, HPCHANGE = 12, 15, 16

FILES = {
 "81046492":"win","81047051":"win","81047620":"win","81048176":"win",
 "81048915":"win","81049656":"win","81050419":"win",
 "81051546":"loss","81052807":"loss","81053955":"loss","81055254":"loss",
 "81056561":"loss","81060852":"loss","81060894":"loss","81061610":"loss",
}
IDX = {str(e["episode_id"]): e for e in json.load(open(os.path.join(ANA,"index.json")))["extracted"]}

def dedup_events(d):
    """Return list of (turn, log) deduped by (turn + full-log-signature)."""
    seen=set(); out=[]
    for step in d["steps"]:
        for ag in step:
            if not isinstance(ag,dict): continue
            obs=ag.get("observation") or {}
            cur=obs.get("current"); turn=cur.get("turn") if isinstance(cur,dict) else None
            for L in obs.get("logs") or []:
                sig=(turn,)+tuple(sorted((k,json.dumps(v)) for k,v in L.items()))
                if sig in seen: continue
                seen.add(sig); out.append((turn,L))
    return out

rows={}
for ep,res in FILES.items():
    e=IDX[ep]; mi=e["my_idx"]; opp=e["opponent"]
    d=json.load(open(os.path.join(ANA,f"keidroid_d21_{ep}_{res}.json")))
    ev=dedup_events(d)
    # attacks: dedupe by (turn, player, serial, attackId) = one attack per card per turn
    atk_sig=set(); atks=[]
    for turn,L in ev:
        if L.get("type")==ATTACK and L.get("playerIndex")==mi:
            sig=(turn,L.get("serial"),L.get("attackId"))
            if sig in atk_sig: continue
            atk_sig.add(sig); atks.append((turn,L.get("attackId")))
    atkc=Counter(a for t,a in atks)
    atk_turns=sorted({t for t,a in atks if t is not None})
    # evolves to 1031
    evo=sorted({turn for turn,L in ev if L.get("type")==EVOLVE and L.get("cardId")==1031 and L.get("playerIndex")==mi and turn is not None})
    # heals: positive HpChange on my pokemon
    heals=[(turn,L.get("value")) for turn,L in ev if L.get("type")==HPCHANGE and L.get("playerIndex")==mi and (L.get("value") or 0)>0]
    bigheal=max([v for t,v in heals],default=0)
    # damage on my 1031
    dmg=[(turn,L.get("value")) for turn,L in ev if L.get("type")==HPCHANGE and L.get("playerIndex")==mi and L.get("cardId")==1031 and (L.get("value") or 0)<0]
    bighit=min([v for t,v in dmg],default=0)
    # opp mons
    oppmons=set()
    for step in d["steps"]:
        for ag in step:
            if isinstance(ag,dict):
                cur=(ag.get("observation") or {}).get("current")
                if isinstance(cur,dict):
                    try:
                        for a in (cur["players"][1-mi].get("active") or []):
                            if a: oppmons.add(a.get("id"))
                        for b in (cur["players"][1-mi].get("bench") or []):
                            if b: oppmons.add(b.get("id"))
                    except: pass
    rows[ep]=dict(res=res,opp=opp,mi=mi,evo=evo,atk_turns=atk_turns,
        first_atk=atk_turns[0] if atk_turns else None,atkc=dict(atkc),
        nheals=len(heals),heals=heals,bigheal=bigheal,bighit=bighit,
        oppmons=sorted(x for x in oppmons if x))

print("ATTACK ID legend: 1487=Jetting Blow(1E,120+50snipe) 1488=Nebula Beam(3E,210) 965/1266=Staryu/other")
print("="*90)
for ep,r in rows.items():
    print(f"{ep}[{r['res'][:1]}] vs {r['opp'][:20]:20} mi{r['mi']} evo→Mega@{r['evo']} 1stAtk@{r['first_atk']} "
          f"atks={r['atkc']} heals={r['heals']} bighit={r['bighit']}")
print("="*90)
W=[r for r in rows.values() if r['res']=='win']; L=[r for r in rows.values() if r['res']=='loss']
def med(xs):
    xs=sorted(x for x in xs if x is not None)
    return None if not xs else (xs[len(xs)//2] if len(xs)%2 else (xs[len(xs)//2-1]+xs[len(xs)//2])/2)
jb=sum(r['atkc'].get(1487,0) for r in rows.values()); nb=sum(r['atkc'].get(1488,0) for r in rows.values())
print(f"DEDUPED Jetting Blow(1487) total={jb}  Nebula Beam(1488) total={nb}")
print(f"median evolve turn WIN={med([min(r['evo']) if r['evo'] else None for r in W])} LOSS={med([min(r['evo']) if r['evo'] else None for r in L])}")
print(f"median 1st-attack turn WIN={med([r['first_atk'] for r in W])} LOSS={med([r['first_atk'] for r in L])}")
print(f"avg heal-events WIN={round(sum(r['nheals'] for r in W)/len(W),2)} LOSS={round(sum(r['nheals'] for r in L)/len(L),2)}")
print(f"games WIN with >=1 big heal (>=200): {sum(1 for r in W if r['bigheal']>=200)}/{len(W)}  LOSS: {sum(1 for r in L if r['bigheal']>=200)}/{len(L)}")
print("Bricks (no evolve, no real attack on Mega, no dmg taken):")
for ep,r in rows.items():
    nonmega_atks = all(a in (965,1266) for a in r['atkc'])  # only Staryu-tier attacks
    if not r['evo'] and r['bighit']==0:
        print(f"   {ep} {r['res']} vs {r['opp'][:20]} atks={r['atkc']} (Mega never evolved, Starmie took 0 dmg)")
print("Loss biggest-hit-on-Mega + opp mons (counter check):")
for ep,r in rows.items():
    if r['res']=='loss':
        print(f"   {ep} vs {r['opp'][:20]:20} bighit={r['bighit']} oppmons={r['oppmons']}")
print("Win biggest-hit-on-Mega:")
for ep,r in rows.items():
    if r['res']=='win':
        print(f"   {ep} vs {r['opp'][:20]:20} bighit={r['bighit']}")
