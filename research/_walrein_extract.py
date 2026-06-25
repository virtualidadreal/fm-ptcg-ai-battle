"""Extract Walrein decklists from d22 + matchup vs Alakazam + plan analysis.
Run inside ptcg-cabt docker. Read-only.
  docker run --rm --platform=linux/amd64 -v "$PWD":/work -w /work ptcg-cabt:latest \
    python research/_walrein_extract.py /tmp/ep22_unz <or zip>
Accepts either a directory of episode JSONs or a zip.
"""
import sys, os, json, glob, zipfile
from collections import Counter, defaultdict
ROOT = '/work'
sys.path.insert(0, ROOT + '/docs/official/models/cg-lib')
sys.path.insert(0, ROOT + '/ptcg-abc/tools')
from cg.api import all_card_data, all_attack
from meta_analyze import dk, CT, iter_games, load_elo

SRC = sys.argv[1]
elo = load_elo(ROOT + '/_tmp_lb')
ELO_CUT = 1150

ATK = {a.attackId: a for a in all_attack()}


def iter_dir(d):
    """Mirror iter_games but over a directory of JSONs."""
    for nm in sorted(glob.glob(d + '/*.json')):
        try:
            dd = json.loads(open(nm).read())
            rw = dd['rewards']
            decks = [dd['steps'][1][0]['action'], dd['steps'][1][1]['action']]
            if not (isinstance(decks[0], list) and len(decks[0]) == 60):
                continue
            who = None if rw[0] == rw[1] else (0 if rw[0] > rw[1] else 1)
            pl = [a['Name'] for a in dd['info']['Agents']]
            yield decks[0], decks[1], who, pl
        except Exception:
            continue


games = iter_dir(SRC) if os.path.isdir(SRC) else iter_games(SRC, 0)

wal_lists = Counter()
wal_vs_ala = [0, 0]            # walrein wins, total vs alakazam
wal_overall = [0, 0]          # walrein wins, total all matchups
wal_top_overall = [0, 0]      # walrein perspective, pilot Elo>=cut
wal_vs_ala_lists = Counter()  # lists used specifically when beating alakazam
opp_counter = Counter()       # what walrein faces

for dA, dB, who, pl in games:
    if who is None:
        continue
    for me, opp, my_win, my_pl in ((dA, dB, who == 0, pl[0]), (dB, dA, who == 1, pl[1])):
        if dk(me) == 'Walrein':
            wal_lists[tuple(sorted(me))] += 1
            wal_overall[1] += 1
            wal_overall[0] += my_win
            opp_counter[dk(opp)] += 1
            if elo.get(my_pl, 0) >= ELO_CUT:
                wal_top_overall[1] += 1
                wal_top_overall[0] += my_win
            if dk(opp) == 'Alakazam':
                wal_vs_ala[1] += 1
                wal_vs_ala[0] += my_win
                if my_win:
                    wal_vs_ala_lists[tuple(sorted(me))] += 1

print(f'\n=== Walrein distinct lists: {len(wal_lists)} (total appearances {sum(wal_lists.values())}) ===')
print(f'Walrein OVERALL (walrein perspective): {wal_overall[0]}/{wal_overall[1]} = '
      f'{wal_overall[0]/max(wal_overall[1],1)*100:.0f}% WR')
print(f'Walrein TOP-TIER (Elo>={ELO_CUT}): {wal_top_overall[0]}/{wal_top_overall[1]} = '
      f'{wal_top_overall[0]/max(wal_top_overall[1],1)*100:.0f}% WR')
print(f'Walrein vs ALAKAZAM (walrein perspective): {wal_vs_ala[0]}/{wal_vs_ala[1]} = '
      f'{wal_vs_ala[0]/max(wal_vs_ala[1],1)*100:.0f}% Walrein win '
      f'(=> Alakazam wins {100-wal_vs_ala[0]/max(wal_vs_ala[1],1)*100:.0f}%)')

print('\n=== What Walrein faces (opp archetype counts) ===')
for k, n in opp_counter.most_common(12):
    print(f'  {n:4d}x {k}')


def cname(pid):
    c = CT.get(pid)
    return c.name if c else f'?{pid}'


def show_list(lst, label):
    cc = Counter(lst)
    print(f'\n=== {label} ===')
    rows = sorted(cc.items(), key=lambda kv: (-(kv[0] < 1000), -kv[1], cname(kv[0])))
    for pid, n in rows:
        c = CT.get(pid)
        tag = ''
        if c and pid < 1000 and c.hp:
            tag = f'HP{c.hp}'
            for r in ('megaEx', 'ex', 'stage2', 'stage1', 'basic'):
                if getattr(c, r, 0):
                    tag += f' {r}'
                    break
        print(f'  {n}x {cname(pid):34s} {tag}')
    return rows


# overall most common list (the canonical Walrein netdeck)
if wal_lists:
    top_list, cnt = wal_lists.most_common(1)[0]
    rows = show_list(top_list, f'MOST COMMON Walrein list (seen {cnt}x)')

    # if the list that beats Alakazam differs, show it too
    if wal_vs_ala_lists:
        ala_top, acnt = wal_vs_ala_lists.most_common(1)[0]
        if ala_top != top_list:
            show_list(ala_top, f'Most common Walrein list WHEN BEATING Alakazam (seen {acnt}x)')
        else:
            print(f'\n(The anti-Alakazam list == the canonical list, seen {acnt}x in wins vs Alakazam)')

    # ---- mechanics dump for the Pokemon line + key attacks/skills ----
    print('\n=== Pokemon line mechanics (attacks + abilities) ===')
    poke_ids = [pid for pid, n in rows if pid < 1000 and CT.get(pid) and CT[pid].hp]
    for pid in poke_ids:
        c = CT[pid]
        flags = [r for r in ('megaEx', 'ex', 'stage2', 'stage1', 'basic') if getattr(c, r, 0)]
        evo = f' evolvesFrom={c.evolvesFrom}' if getattr(c, 'evolvesFrom', None) else ''
        wk = getattr(c, 'weakness', None)
        rc = getattr(c, 'retreatCost', None)
        print(f'\n-- {c.name} (id {pid}) HP{c.hp} {" ".join(flags)}{evo} weak={wk} retreat={rc}')
        for sk in (getattr(c, 'skills', None) or []):
            nm = getattr(sk, 'name', '?')
            tx = getattr(sk, 'text', '') or getattr(sk, 'description', '') or ''
            print(f'   ABILITY {nm}: {tx}')
        for at in (getattr(c, 'attacks', None) or []):
            aid = getattr(at, 'attackId', None)
            a = ATK.get(aid, at)
            nm = getattr(a, 'name', '?')
            dmg = getattr(a, 'damage', '')
            en = getattr(a, 'energies', '')
            tx = getattr(a, 'text', '') or ''
            print(f'   ATK {nm} [{en}] dmg={dmg} :: {tx}')

    # trainer cards in the deck (non-Pokemon ids >=1000)
    print('\n=== Trainers / energy in the deck ===')
    cc = Counter(top_list)
    trainers = sorted([(pid, n) for pid, n in cc.items() if pid >= 1000 or not (CT.get(pid) and CT[pid].hp)],
                      key=lambda kv: (-kv[1], cname(kv[0])))
    for pid, n in trainers:
        c = CT.get(pid)
        tx = ''
        if c:
            tx = (getattr(c, 'text', '') or getattr(c, 'description', '') or '')[:120]
        print(f'  {n}x {cname(pid):30s} {tx}')

    json.dump({'list': list(top_list), 'count': cnt,
               'named': [[n, cname(p)] for p, n in rows],
               'wal_vs_ala': wal_vs_ala, 'wal_overall': wal_overall,
               'wal_top_overall': wal_top_overall},
              open('/tmp/walrein.json', 'w'), ensure_ascii=False, indent=2)
    print('\nsaved /tmp/walrein.json')
else:
    print('NO Walrein decks found in source.')
