"""Behavioral mining of local ladder episodes -> locate the best Alakazam pilot.

READ-ONLY over data/episodes. Reuses the archetype-labeling logic from
ptcg-abc/tools/meta_analyze.py (dk()), but sources card metadata from
ptcg-abc/web/card_db.json instead of the cg ctypes lib (the .so is Linux-only and
will not dlopen on macOS; we only need name/hp/stage/ex for labeling).

Outputs to data/alakazam_analysis/:
  - top_index.json  (top ladder agents + their deck archetype + score + best-Alakazam replay paths)
  - extracted replays of the best Alakazam pilot.
"""
import sys, os, json, csv, glob, zipfile
from collections import Counter, defaultdict

ROOT = '/Users/franmilla/FMA/proyectos/ptcg-ai-battle'
OUT = ROOT + '/data/alakazam_analysis'
LB_DIR = ROOT + '/data/leaderboard_dl'
CARD_DB = ROOT + '/ptcg-abc/web/card_db.json'

# zips, most-recent meta first (d21=2026-06-21 current meta, then d20). Sample d19/d18
# only if an agent needs more games -- handled via append order below.
ZIPS = [
    ROOT + '/data/episodes/d21/pokemon-tcg-ai-battle-episodes-2026-06-21.zip',
    ROOT + '/data/episodes/d20/pokemon-tcg-ai-battle-episodes-2026-06-20.zip',
    ROOT + '/data/episodes/d19/pokemon-tcg-ai-battle-episodes-2026-06-19.zip',
    ROOT + '/data/episodes/d18/pokemon-tcg-ai-battle-episodes-2026-06-18.zip',
]
ZIPS = [z for z in ZIPS if os.path.exists(z)]

# ---- card table from card_db.json (id->{name,hp,stage,ex,mega}) ----
_raw = json.load(open(CARD_DB, encoding='utf-8'))
CT = {}
for cid, v in _raw.items():
    try:
        pid = int(cid)
    except ValueError:
        continue
    nm = v.get('name') or ''
    CT[pid] = {
        'name': nm,
        'hp': v.get('hp') or 0,
        'stage': v.get('stage'),
        'ex': bool(v.get('ex')),
        'mega': nm.startswith('Mega ') and nm.endswith(' ex'),
        'pokemon': str(v.get('cardType')) == '0' and bool(v.get('hp')),
    }

# Same SUPPORT list as meta_analyze.py: generic draw/search engines that must never
# become the archetype label.
SUPPORT = ('Fezandipiti', 'Dudunsparce', 'Dunsparce', 'Shaymin', 'Fan Rotom', 'Rotom',
           'Dedenne', 'Genesect', 'Lumineon', 'Radiant', 'Mew ', 'Snorlax', 'Bibarel',
           'Bidoof', 'Lechonk', 'Squawkabilly')


def _is_support(pid):
    nm = CT.get(pid, {}).get('name', '')
    return any(s in nm for s in SUPPORT)


def dk(deck):
    """Archetype label for a 60-card list: the WIN-CONDITION Pokemon, ignoring shared
    draw/search engines. Priority mega-ex > ex > stage2 > stage1 > most copies.
    Mirrors meta_analyze.dk()."""
    cc = Counter(deck)
    poke = [(k, n) for k, n in cc.items() if k in CT and CT[k]['pokemon']]
    core = [p for p in poke if not _is_support(p[0])] or poke
    if not core:
        return '?'
    for keyf in (lambda p: CT[p[0]]['mega'], lambda p: CT[p[0]]['ex']):
        cand = [p for p in sorted(core, key=lambda x: -x[1]) if keyf(p)]
        if cand:
            return CT[cand[0][0]]['name']
    for st in (2, 1):
        cand = [p for p in sorted(core, key=lambda x: -x[1]) if CT[p[0]]['stage'] == st]
        if cand:
            return CT[cand[0][0]]['name']
    return CT[max(core, key=lambda x: x[1])[0]]['name']


def load_elo():
    files = sorted(glob.glob(LB_DIR + '/*publicleaderboard*.csv'))
    elo, rank = {}, {}
    with open(files[-1], encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            try:
                nm = row['TeamName'].strip()
                elo[nm] = float(row['Score'])
                rank[nm] = int(row['Rank'])
            except (KeyError, ValueError):
                continue
    print(f'[elo] {len(elo)} teams from {os.path.basename(files[-1])}')
    return elo, rank


def iter_games(zip_path, max_n=0):
    """Yield (zip_name, json_name, deckA, deckB, winner_idx_or_None, [nameA,nameB])."""
    z = zipfile.ZipFile(zip_path)
    names = [x for x in z.namelist() if x.endswith('.json')]
    n = 0
    for nm in names:
        if max_n and n >= max_n:
            break
        try:
            d = json.loads(z.read(nm))
            rw = d['rewards']
            decks = [d['steps'][1][0]['action'], d['steps'][1][1]['action']]
            if not (isinstance(decks[0], list) and len(decks[0]) == 60
                    and isinstance(decks[1], list) and len(decks[1]) == 60):
                continue
            who = None if rw[0] == rw[1] else (0 if rw[0] > rw[1] else 1)
            pl = [a['Name'] for a in d['info']['Agents']]
            n += 1
            yield zip_path, nm, decks[0], decks[1], who, pl
        except Exception:
            continue


def main():
    elo, rank = load_elo()

    # per-player aggregates
    pl_deck_label = defaultdict(Counter)     # name -> Counter(archetype label per game)
    pl_games = Counter()
    pl_wins = Counter()
    pl_decisive = Counter()
    # store (zip, jsonname) refs per player+label, for replay extraction (cap to avoid RAM blow)
    pl_label_refs = defaultdict(list)        # (name,label) -> [(zip,json), ...] capped at 40

    total = 0
    for zp in ZIPS:
        zc = 0
        for zip_path, jname, dA, dB, who, pl in iter_games(zp):
            total += 1
            zc += 1
            labels = [dk(dA), dk(dB)]
            for i in (0, 1):
                nm = pl[i]
                pl_deck_label[nm][labels[i]] += 1
                pl_games[nm] += 1
                if who is not None:
                    pl_decisive[nm] += 1
                    if who == i:
                        pl_wins[nm] += 1
                key = (nm, labels[i])
                if len(pl_label_refs[key]) < 40:
                    pl_label_refs[key].append((zip_path, jname))
        print(f'[zip] {os.path.basename(zp)}: {zc} valid games (cum {total})')

    def player_archetype(nm):
        return pl_deck_label[nm].most_common(1)[0][0] if pl_deck_label[nm] else '?'

    # --- TOP ~30 leaderboard agents: what they play ---
    top_names = sorted(elo, key=lambda n: rank.get(n, 1e9))[:30]
    top_rows = []
    arch_dist = Counter()
    for nm in top_names:
        seen = nm in pl_deck_label
        arch = player_archetype(nm) if seen else '(not in local episodes)'
        if seen:
            arch_dist[arch] += 1
        wr = (pl_wins[nm] / pl_decisive[nm] * 100) if pl_decisive[nm] else None
        top_rows.append({
            'rank': rank.get(nm), 'name': nm, 'score': elo.get(nm),
            'archetype': arch, 'games_seen': pl_games.get(nm, 0),
            'winrate_pct': round(wr, 1) if wr is not None else None,
            'deck_label_breakdown': dict(pl_deck_label[nm].most_common()),
        })

    # --- find best Alakazam pilot (highest leaderboard score among players whose
    #     dominant archetype is Alakazam, with a min game threshold) ---
    ALAKA = 'Alakazam'
    alaka_players = []
    for nm, lc in pl_deck_label.items():
        if lc.get(ALAKA, 0) == 0:
            continue
        dominant = lc.most_common(1)[0][0]
        n_alaka = lc[ALAKA]
        score = elo.get(nm)
        alaka_players.append({
            'name': nm, 'score': score, 'rank': rank.get(nm),
            'dominant_archetype': dominant,
            'alakazam_games': n_alaka, 'total_games': pl_games[nm],
            'in_leaderboard': score is not None,
        })

    # Best = dominant Alakazam, in leaderboard, max score, requiring >=3 Alakazam games.
    def alaka_key(p):
        return (p['dominant_archetype'] == ALAKA, p['in_leaderboard'],
                p['score'] if p['score'] is not None else -1)
    eligible = [p for p in alaka_players if p['alakazam_games'] >= 3
                and p['dominant_archetype'] == ALAKA and p['in_leaderboard']]
    pool = eligible or [p for p in alaka_players if p['alakazam_games'] >= 3] or alaka_players
    best = max(pool, key=alaka_key) if pool else None

    episode_paths = []
    n_extracted = 0
    if best:
        refs = pl_label_refs.get((best['name'], ALAKA), [])
        # de-dup, take up to 10
        seen_ref = set()
        for zip_path, jname in refs:
            if len(episode_paths) >= 10:
                break
            rk = (zip_path, jname)
            if rk in seen_ref:
                continue
            seen_ref.add(rk)
            z = zipfile.ZipFile(zip_path)
            day = os.path.basename(zip_path).replace('pokemon-tcg-ai-battle-episodes-', '').replace('.zip', '')
            safe = f"alakazam_{best['name'].replace(' ', '_').replace('/', '_')}_{day}_{os.path.basename(jname)}"
            dest = os.path.join(OUT, safe)
            with open(dest, 'wb') as fh:
                fh.write(z.read(jname))
            episode_paths.append(dest)
            n_extracted += 1

    index = {
        'generated': '2026-06-22',
        'episodes_processed': total,
        'zips': [os.path.basename(z) for z in ZIPS],
        'leaderboard_csv': os.path.basename(sorted(glob.glob(LB_DIR + '/*publicleaderboard*.csv'))[-1]),
        'card_db': 'ptcg-abc/web/card_db.json (name/hp/stage/ex; cg .so is Linux-only)',
        'top30_archetype_distribution': dict(arch_dist.most_common()),
        'top30_agents': top_rows,
        'best_alakazam': {
            'found': best is not None,
            'name': best['name'] if best else None,
            'score': best['score'] if best else None,
            'rank': best['rank'] if best else None,
            'dominant_archetype': best['dominant_archetype'] if best else None,
            'alakazam_games': best['alakazam_games'] if best else 0,
            'total_games': best['total_games'] if best else 0,
            'is_dominant_alakazam': (best['dominant_archetype'] == ALAKA) if best else False,
            'in_leaderboard': best['in_leaderboard'] if best else False,
            'episode_paths': episode_paths,
        },
        'all_alakazam_pilots_top': sorted(
            [p for p in alaka_players if p['in_leaderboard']],
            key=lambda p: -(p['score'] or -1))[:20],
        'caveats': [
            'Decklist reconstruction is PARTIAL: only the declared 60-card deck (steps[1] action) is read; '
            'cards never drawn/played are still in the list so the deck itself is complete, but PILOTING lines '
            'require reading per-turn steps (not done here).',
            'Archetype label uses card_db.json metadata (name/hp/stage/ex) + the meta_analyze SUPPORT filter; '
            'megaEx detected by name prefix. Same labeling rule as the project tooling.',
            'Player<->Elo link is by exact episode Agent Name == leaderboard TeamName string match; '
            'mismatches (renames, encoding) drop a player from the leaderboard-scored set.',
            'Episode score in JSON is only win/loss (rewards), NOT Elo. Pilot strength is the leaderboard Score.',
        ],
    }
    out_path = os.path.join(OUT, 'top_index.json')
    json.dump(index, open(out_path, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

    print('\n=== TOP 30 ARCHETYPE DISTRIBUTION ===')
    for k, n in arch_dist.most_common():
        print(f'  {k:28s} {n}')
    print('\n=== BEST ALAKAZAM ===')
    print(json.dumps(index['best_alakazam'], ensure_ascii=False, indent=2)[:1200])
    print(f'\nsaved {out_path}; extracted {n_extracted} replays')


if __name__ == '__main__':
    main()
