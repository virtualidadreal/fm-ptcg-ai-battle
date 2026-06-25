"""Native (macOS) Walrein scan over the d22 zip. Read-only. No docker needed.
Card metadata from ptcg-abc/web/card_db.json (name/hp/stage/ex only)."""
import json, zipfile, sys, os
from collections import Counter

ROOT = '/Users/franmilla/FMA/proyectos/ptcg-ai-battle'
ZIP = ROOT + '/data/episodes/d22/pokemon-tcg-ai-battle-episodes-2026-06-22.zip'
raw = json.load(open(ROOT + '/ptcg-abc/web/card_db.json'))
CT = {}
for cid, v in raw.items():
    try:
        pid = int(cid)
    except ValueError:
        continue
    nm = v.get('name') or ''
    CT[pid] = {'name': nm, 'hp': v.get('hp') or 0, 'stage': v.get('stage'),
               'ex': bool(v.get('ex')), 'mega': nm.startswith('Mega ') and nm.endswith(' ex'),
               'text': v.get('text') or v.get('description') or '',
               'attacks': v.get('attacks') or [], 'abilities': v.get('abilities') or v.get('skills') or []}
SUP = ('Fezandipiti', 'Dudunsparce', 'Dunsparce', 'Shaymin', 'Fan Rotom', 'Rotom', 'Dedenne',
       'Genesect', 'Lumineon', 'Radiant', 'Mew ', 'Snorlax', 'Bibarel', 'Bidoof', 'Lechonk', 'Squawkabilly')


def issup(p):
    return any(s in CT.get(p, {}).get('name', '') for s in SUP)


def dk(deck):
    cc = Counter(deck)
    poke = [(k, v) for k, v in cc.items() if k in CT and k < 1000 and CT[k]['hp']]
    core = [p for p in poke if not issup(p[0])] or poke
    for need in ('mega', 'ex'):
        cand = [p for p in sorted(core, key=lambda x: -x[1]) if CT[p[0]][need]]
        if cand:
            return CT[cand[0][0]]['name']
    for st in ('2', '1'):
        cand = [p for p in sorted(core, key=lambda x: -x[1]) if str(CT[p[0]].get('stage')) == st]
        if cand:
            return CT[cand[0][0]]['name']
    if not core:
        return '?'
    return CT[max(core, key=lambda x: x[1])[0]]['name']


z = zipfile.ZipFile(ZIP)
names = [x for x in z.namelist() if x.endswith('.json')]
print('episodes in d22 zip:', len(names), flush=True)
wal_total = wal_win = 0
wal_vs_ala = [0, 0]
lists = Counter()
opp = Counter()
sample_eps = []   # (episode, walrein_player_idx)
for nm in names:
    try:
        d = json.loads(z.read(nm))
        rw = d['rewards']
        if rw[0] == rw[1]:
            continue
        decks = [d['steps'][1][0]['action'], d['steps'][1][1]['action']]
        if not (isinstance(decks[0], list) and len(decks[0]) == 60):
            continue
        who = 0 if rw[0] > rw[1] else 1
        for idx, (me, op, win) in enumerate(((decks[0], decks[1], who == 0),
                                             (decks[1], decks[0], who == 1))):
            if dk(me) == 'Walrein':
                wal_total += 1
                wal_win += win
                lists[tuple(sorted(me))] += 1
                opp[dk(op)] += 1
                if dk(op) == 'Alakazam':
                    wal_vs_ala[1] += 1
                    wal_vs_ala[0] += win
                    if win and len(sample_eps) < 6:
                        sample_eps.append([nm, idx])
    except Exception:
        continue

print('Walrein appearances:', wal_total, 'WR', round(wal_win / max(wal_total, 1) * 100), '%', flush=True)
print('distinct lists:', len(lists), flush=True)
print('vs Alakazam (walrein perspective):', wal_vs_ala, '=>',
      round(wal_vs_ala[0] / max(wal_vs_ala[1], 1) * 100), '% walrein win =>',
      'Alakazam wins', round(100 - wal_vs_ala[0] / max(wal_vs_ala[1], 1) * 100), '%', flush=True)
print('Walrein faces (opp archetypes):', opp.most_common(12), flush=True)
print('sample win-vs-ala episodes:', sample_eps, flush=True)

if lists:
    top, cnt = lists.most_common(1)[0]
    print('\nTOP LIST seen', cnt, 'x of', sum(lists.values()), 'appearances', flush=True)
    cc = Counter(top)
    for pid, n in sorted(cc.items(), key=lambda kv: (-(kv[0] < 1000), -kv[1])):
        c = CT.get(pid, {})
        if pid < 1000 and c.get('hp'):
            tag = 'HP%s st%s%s%s' % (c.get('hp'), c.get('stage'),
                                     ' EX' if c.get('ex') else '', ' MEGA' if c.get('mega') else '')
        else:
            tag = 'TRAINER/ENERGY'
        print('  %dx %-34s %s' % (n, c.get('name', '?%d' % pid), tag), flush=True)

    # mechanics for the pokemon line
    print('\n=== Pokemon line text (from card_db) ===', flush=True)
    for pid, n in sorted(cc.items(), key=lambda kv: (-(kv[0] < 1000), -kv[1])):
        c = CT.get(pid, {})
        if pid < 1000 and c.get('hp'):
            print('-- %s (id %d) HP%s :: text=%s' % (c['name'], pid, c['hp'], (c.get('text') or '')[:200]), flush=True)
            for a in c.get('attacks', [])[:4]:
                print('    ATK', json.dumps(a, ensure_ascii=False)[:200], flush=True)
            for ab in c.get('abilities', [])[:3]:
                print('    ABILITY', json.dumps(ab, ensure_ascii=False)[:200], flush=True)

    json.dump({'top': list(top), 'cnt': cnt, 'vs_ala': wal_vs_ala,
               'sample_eps': sample_eps, 'opp': opp.most_common(12),
               'wr': round(wal_win / max(wal_total, 1) * 100)},
              open('/tmp/wal_quick.json', 'w'))
    print('\nsaved /tmp/wal_quick.json', flush=True)
