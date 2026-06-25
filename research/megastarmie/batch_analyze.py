import json, glob, os
from collections import Counter, defaultdict

CARDS=json.load(open('data/cards_enriched.json'))
FILES=sorted(glob.glob('data/megastarmie_analysis/keidroid_d21_*.json'))

ATTACK_NAME={1487:'Jetting Blow(1E,120+50bench)',1488:'Nebula Beam(3E,210)'}

def namemap(d):
    nm={}
    for step in d['steps']:
        for ps in step:
            for fr in (ps.get('visualize') or []):
                for pl in (fr.get('current') or {}).get('players',[]):
                    for area in ('deck','hand','discard','bench','active','prize'):
                        for c in (pl.get(area) or []):
                            if isinstance(c,dict): nm[c['id']]=c.get('name','?')
    return nm

def analyze(fp):
    d=json.load(open(fp))
    nm=namemap(d); N=lambda c: nm.get(c,f'#{c}')
    teams=d['info']['TeamNames']
    me=teams.index('keidroid') if 'keidroid' in teams else 1
    won = d['rewards'][me]==1
    # frame-by-frame state trace
    starmie_attacks=Counter()
    heal_count=0
    boss_me=0; boss_opp=0
    first_starmie_attack_turn=None
    opp_first_pokemon=None
    my_first_active=None
    ko_by_me=[]   # (turn, victim, prize_taken_estimate)
    ko_of_me=[]   # (turn, victim=starmie?, )
    prize_trace=[]
    cur_turn=0
    # track active to detect KO (active disappears) and prize deltas
    prev_prize=[6,6]; prev_active=[None,None]
    evolves_starmie=[]  # turns staryu->mega
    energy_on_starmie=[]  # attach turns
    for step in d['steps']:
        for ps in step:
            for fr in (ps.get('visualize') or []):
                cur=fr.get('current') or {}
                t=cur.get('turn')
                if t is not None: cur_turn=t
                pls=cur.get('players')
                if pls:
                    pc=[len(p.get('prize') or []) for p in pls]
                    acts=[]
                    for p in pls:
                        a=p.get('active') or []
                        acts.append(a[0]['name'] if a and isinstance(a[0],dict) else None)
                    if opp_first_pokemon is None and acts[1-me]:
                        opp_first_pokemon=acts[1-me]
                    if my_first_active is None and acts[me]:
                        my_first_active=acts[me]
                    # prize delta: someone took prizes
                    if pc!=prev_prize:
                        # the player whose prize went DOWN took prizes
                        for pi in range(2):
                            d_pr=prev_prize[pi]-pc[pi]
                            if d_pr>0:
                                victim=prev_active[1-pi]
                                if pi==me: ko_by_me.append((cur_turn,victim,d_pr))
                                else: ko_of_me.append((cur_turn,victim,d_pr))
                        prev_prize=pc[:]
                    prev_active=acts[:]
                for l in (fr.get('logs') or []):
                    ty=l['type']
                    if ty=='Attack' and l['playerIndex']==me and l.get('cardId')==1031:
                        starmie_attacks[l['attackId']]+=1
                        if first_starmie_attack_turn is None: first_starmie_attack_turn=cur_turn
                    if ty=='Evolve' and l['playerIndex']==me and l.get('cardId')==1031:
                        evolves_starmie.append(cur_turn)
                    if ty=='Attach' and l['playerIndex']==me and l.get('cardIdTarget')==1031:
                        energy_on_starmie.append((cur_turn,N(l['cardId'])))
                    if ty=='HpChange' and l.get('cardId')==1031 and l.get('value',0)>0:
                        heal_count+=1
                    if ty=='Play':
                        nme=N(l['cardId'])
                        if 'Boss' in nme:
                            if l['playerIndex']==me: boss_me+=1
                            else: boss_opp+=1
    return dict(file=os.path.basename(fp),won=won,me=me,opp_first=opp_first_pokemon,
        my_first=my_first_active, first_atk_turn=first_starmie_attack_turn,
        atks=dict(starmie_attacks), heals=heal_count, boss_me=boss_me, boss_opp=boss_opp,
        evolve_turns=evolves_starmie, ko_by_me=ko_by_me, ko_of_me=ko_of_me,
        first_energy=energy_on_starmie[:3])

results=[analyze(f) for f in FILES]
for r in results:
    tag='WIN ' if r['won'] else 'LOSS'
    print(f"{tag} {r['file'][9:]:30} opp1={str(r['opp_first'])[:18]:18} evolveT={r['evolve_turns']} 1stAtkT={r['first_atk_turn']} atks={r['atks']} heals={r['heals']} bossMe={r['boss_me']} bossOpp={r['boss_opp']}")
    print(f"        KOby_me={r['ko_by_me']}")
    print(f"        KOof_me={r['ko_of_me']}")

# aggregate
print('\n=== AGGREGATE ===')
wins=[r for r in results if r['won']]; losses=[r for r in results if not r['won']]
print(f'wins={len(wins)} losses={len(losses)}')
import statistics
def med(xs): 
    xs=[x for x in xs if x is not None]; 
    return statistics.median(xs) if xs else None
print('median 1st-attack turn WIN:', med([r['first_atk_turn'] for r in wins]),' LOSS:', med([r['first_atk_turn'] for r in losses]))
print('median evolve turn WIN:', med([r['evolve_turns'][0] if r['evolve_turns'] else None for r in wins]),' LOSS:', med([r['evolve_turns'][0] if r['evolve_turns'] else None for r in losses]))
ja=sum(r['atks'].get(1487,0) for r in results); nb=sum(r['atks'].get(1488,0) for r in results)
print(f'total Jetting Blow(1487)={ja}  Nebula Beam(1488)={nb}')
print('avg heals WIN:', round(sum(r['heals'] for r in wins)/max(1,len(wins)),2),' LOSS:', round(sum(r['heals'] for r in losses)/max(1,len(losses)),2))
print('avg boss_me WIN:', round(sum(r['boss_me'] for r in wins)/max(1,len(wins)),2),' LOSS:', round(sum(r['boss_me'] for r in losses)/max(1,len(losses)),2))
