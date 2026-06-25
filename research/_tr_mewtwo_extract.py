"""Extract Team Rocket's Mewtwo ex decklists from d22 + matchup vs Alakazam.
Run inside ptcg-cabt docker. Read-only. Caps episodes; unbuffered."""
import sys, os, json, zipfile
from collections import Counter
ROOT = '/work'
sys.path.insert(0, ROOT + '/docs/official/models/cg-lib')
sys.path.insert(0, ROOT + '/ptcg-abc/tools')
from cg.api import all_card_data
from meta_analyze import dk, CT

ZIP = sys.argv[1]
MAX = int(sys.argv[2]) if len(sys.argv) > 2 else 0

def cname(pid):
    c = CT.get(pid); return c.name if c else f'?{pid}'

z = zipfile.ZipFile(ZIP)
names = [x for x in z.namelist() if x.endswith('.json')]
print(f'episodes in zip: {len(names)}', flush=True)

tr_lists = Counter()
tr_vs_ala = [0, 0]
seen = 0
for nm in names:
    if MAX and seen >= MAX and tr_lists:
        break
    try:
        d = json.loads(z.read(nm))
        rw = d['rewards']
        decks = [d['steps'][1][0]['action'], d['steps'][1][1]['action']]
        if not (isinstance(decks[0], list) and len(decks[0]) == 60):
            continue
        who = None if rw[0] == rw[1] else (0 if rw[0] > rw[1] else 1)
        if who is None:
            continue
        seen += 1
        if seen % 2000 == 0:
            print(f'  scanned {seen} decisive, TR lists so far {len(tr_lists)}', flush=True)
        labels = [dk(decks[0]), dk(decks[1])]
        for i in (0, 1):
            if labels[i] == "Team Rocket's Mewtwo ex":
                tr_lists[tuple(sorted(decks[i]))] += 1
                if labels[1-i] == 'Alakazam':
                    tr_vs_ala[1] += 1
                    if who == i:
                        tr_vs_ala[0] += 1
    except Exception:
        continue

print(f'\n=== scanned {seen} decisive games ===', flush=True)
print(f'TR Mewtwo distinct lists: {len(tr_lists)} | total appearances: {sum(tr_lists.values())}')
print(f'TR vs Alakazam (TR perspective): {tr_vs_ala[0]}/{tr_vs_ala[1]} = '
      f'{tr_vs_ala[0]/max(tr_vs_ala[1],1)*100:.0f}% TR win')

if not tr_lists:
    sys.exit('no TR lists found')

top_list, cnt = tr_lists.most_common(1)[0]
print(f'\n=== MOST COMMON TR Mewtwo list (seen {cnt}x of {sum(tr_lists.values())}) ===')
cc = Counter(top_list)
rows = sorted(cc.items(), key=lambda kv: (-(kv[0] < 1000), -kv[1], cname(kv[0])))
for pid, n in rows:
    c = CT.get(pid); tag = ''
    if c and pid < 1000 and c.hp:
        tag = f'HP{c.hp}'
        for r in ('megaEx','ex','stage2','stage1','basic'):
            if getattr(c, r, 0): tag += f' {r}'; break
    print(f'  {n}x {cname(pid):34s} {tag}')

json.dump({'list': list(top_list), 'count': cnt, 'total': sum(tr_lists.values()),
           'distinct': len(tr_lists),
           'named': [[n, cname(p), p] for p, n in rows],
           'tr_vs_ala': tr_vs_ala},
          open('/tmp/tr_mewtwo.json', 'w'), ensure_ascii=False, indent=2)
print('\nsaved /tmp/tr_mewtwo.json', flush=True)
