import json, sys, glob, os
from collections import defaultdict, Counter

CARDS=json.load(open('data/cards_enriched.json'))
def cname(cid):
    c=CARDS.get(str(cid))
    return c if False else (c and None)
NAMES={}
# Build id->name from any deck list in a replay later; but logs carry cardId only.
# We map id->name by scanning the deck arrays (which include name).

def load(fp):
    return json.load(open(fp))

def all_frames(d):
    out=[]
    for si,step in enumerate(d['steps']):
        for pi,ps in enumerate(step):
            for fi,frame in enumerate(ps.get('visualize') or []):
                out.append((si,pi,fi,frame))
    return out

def build_name_map(d):
    nm={}
    for _,_,_,fr in all_frames(d):
        cur=fr.get('current') or {}
        for pl in cur.get('players',[]):
            for area in ('deck','hand','discard','bench','active','prize'):
                for card in (pl.get(area) or []):
                    if isinstance(card,dict) and 'id' in card and 'name' in card:
                        nm[card['id']]=card['name']
    return nm

def analyze(fp):
    d=load(fp)
    me_team='keidroid'
    teams=d['info']['TeamNames']
    my_idx=teams.index(me_team) if me_team in teams else 1
    nm=build_name_map(d)
    def N(cid): return nm.get(cid, f'#{cid}')
    logs=[]
    for si,step in enumerate(d['steps']):
        for pi,ps in enumerate(step):
            for fi,frame in enumerate(ps.get('visualize') or []):
                for l in (frame.get('logs') or []):
                    logs.append((si,fi,l))
    return d, my_idx, teams, N, logs, all_frames(d)

if __name__=='__main__':
    fp=sys.argv[1]
    d,my_idx,teams,N,logs,frames=analyze(fp)
    print(f'FILE={os.path.basename(fp)}  teams={teams} my_idx={my_idx} rewards={d["rewards"]}')
    print(f'log_count={len(logs)}')
