#!/usr/bin/env python3
"""Behavioural miner for THIRD PTCG Club Alakazam replays (sequencing + resources).
READ-ONLY. Reconstructs per-turn play order from observation logs.

Log type legend (inferred empirically from this dataset):
  0  = turn start marker (playerIndex = whose turn begins)
  1  = setup/has-basic check
  2  = turn end / pass
  3  = (rare) bench/prize related
  4  = card revealed (setup/search declaration)
  5  = anonymous card (face-down, opponent hand etc.)
  6  = card move fromArea->toArea (cardId, serial)
  7  = anonymous move (face-down draw/shuffle)
  10 = play Item/Supporter/Stadium (cardId)
  11 = attach Energy (cardId energy -> cardIdTarget pokemon)
  12 = Evolve (cardId evolution -> cardIdTarget basic/stage1)
  15 = Attack (attackId by cardId)
  16 = damage counters placed (value)
Areas (inferred): 1=hand, 2=bench-or-board, 3=prize, 4=discard, 5=lost?, 6=deck-facedown
"""
import json, sys, glob, os
from collections import Counter, defaultdict

DB = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'ptcg-abc', 'web', 'card_db.json')))
def nm(cid):
    c = DB.get(str(cid)) or {}
    return c.get('name', f'#{cid}')

DRAW_ENGINE_NAMES = {'Dudunsparce'}  # Run Away Draw (66)
SUPPORTERS = {1225:'Hilda',1231:'Dawn',1184:"Lana's Aid",1182:"Boss's Orders",
              1227:"Lillie's Determination",1197:"Xerosic's Machinations"}
ITEMS = {1086:'Buddy-Buddy Poffin',1152:'Poke Pad',1079:'Rare Candy',1081:'Enhanced Hammer',
         1129:'Sacred Ash',1146:'Wondrous Patch',1097:'Night Stretcher'}

def third_index(d):
    names = [a['Name'] for a in d['info']['Agents']]
    for i,n in enumerate(names):
        if n == 'THIRD PTCG Club':
            return i
    return None

def parse(path):
    d = json.load(open(path))
    me = third_index(d)
    reward = d['rewards'][me]
    eid = d['info']['EpisodeId']
    opp = d['info']['Agents'][1-me]['Name']

    # Build per-turn event stream from MY observation logs (my obs sees my full info)
    # turn segmentation by type-0 markers in my logs
    turns = []  # list of dict(turn_owner, events)
    cur = None
    for si, st in enumerate(d['steps']):
        logs = st[me]['observation'].get('logs') or []
        for e in logs:
            t = e['type']
            if t == 0:
                if cur: turns.append(cur)
                cur = {'owner': e['playerIndex'], 'start_step': si, 'events': []}
            elif cur is not None and t in (10,11,12,15,16,7):
                cur['events'].append((si, e))
    if cur: turns.append(cur)
    return d, me, reward, eid, opp, turns

def describe_my_turns(me, turns):
    out = []
    tn = 0
    for trn in turns:
        if trn['owner'] != me:
            continue
        tn += 1
        seq = []
        draws_facedown = 0
        for si, e in trn['events']:
            t = e['type']
            if t == 7:
                # only count my deck->hand facedown as draw
                if e.get('toArea') == 1 and e.get('playerIndex') == me:
                    draws_facedown += 1
                continue
            if t == 10:
                seq.append(('PLAY', nm(e['cardId']), e['cardId']))
            elif t == 11:
                seq.append(('ATTACH', f"{nm(e['cardId'])}->{nm(e['cardIdTarget'])}"))
            elif t == 12:
                seq.append(('EVOLVE', f"{nm(e['cardId'])}<-{nm(e['cardIdTarget'])}"))
            elif t == 15:
                seq.append(('ATTACK', nm(e['cardId']), e['attackId']))
            elif t == 16:
                seq.append(('DMG', e.get('value')))
        out.append((tn, draws_facedown, seq))
    return out

if __name__ == '__main__':
    paths = sorted(glob.glob(os.path.join(os.path.dirname(__file__), '..', 'data', 'alakazam_analysis', 'alakazam_THIRD_PTCG_Club_*.json')))
    for path in paths:
        d, me, reward, eid, opp, turns = parse(path)
        print(f"\n{'='*70}\nEP {eid}  vs {opp}  | THIRD=p{me} reward={reward} ({'WIN' if reward>0 else 'LOSS'})")
        for tn, draws, seq in describe_my_turns(me, turns):
            actions = '  |  '.join(
                a[0]+':'+str(a[1]) if len(a)>1 else a[0] for a in seq
            )
            print(f"  T{tn} (facedown_draws={draws}): {actions}")
