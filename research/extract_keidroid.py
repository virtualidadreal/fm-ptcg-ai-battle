"""Extract keidroid (Rank 1, Mega Starmie ex) replays from local episode zips.

keidroid = TeamId 16391190, score 1358.9, Mega Starmie ex (card id 1031, prize_value=3).
Replay schema (verified on data/episodes/episode-81310338-replay.json):
  d['info']['Agents'][i]['Name']  -> agent/team name
  d['info']['TeamNames'][i]       -> same
  d['rewards'] = [r0, r1]         -> +1 winner, -1 loser
  d['steps'][1][i]['action']      -> the 60-card decklist (card ids) of player i
  d['steps'][t][0]['observation']['current']['players'][i]['prize'] -> remaining prizes
Card names from ptcg-abc/web/card_db.json (id -> name). Mega Starmie ex = 1031, Staryu = 1030.

Writes selected replay JSONs + index.json into data/megastarmie_analysis/.
"""
import os, sys, json, zipfile, glob
from collections import Counter

ROOT = '/Users/franmilla/FMA/proyectos/ptcg-ai-battle'
OUT = os.path.join(ROOT, 'data/megastarmie_analysis')
os.makedirs(OUT, exist_ok=True)
CARD_DB = json.load(open(os.path.join(ROOT, 'ptcg-abc/web/card_db.json')))
TARGET = 'keidroid'
MEGA_STARMIE = 1031          # Mega Starmie ex (HP330, stage1, ex, prize_value 3)
STARYU = 1030

ZIPS = {
    'd21': os.path.join(ROOT, 'data/episodes/d21/pokemon-tcg-ai-battle-episodes-2026-06-21.zip'),
    'd20': os.path.join(ROOT, 'data/episodes/d20/pokemon-tcg-ai-battle-episodes-2026-06-20.zip'),
    'd19': os.path.join(ROOT, 'data/episodes/d19/pokemon-tcg-ai-battle-episodes-2026-06-19.zip'),
    'd18': os.path.join(ROOT, 'data/episodes/d18/pokemon-tcg-ai-battle-episodes-2026-06-18.zip'),
}


def name(cid):
    v = CARD_DB.get(str(cid))
    return v['name'] if v else f'id{cid}'


def deck_for(d, i):
    """60-card decklist of player i, or None."""
    try:
        a = d['steps'][1][i]['action']
        if isinstance(a, list) and len(a) == 60:
            return a
    except Exception:
        return None
    return None


def prizes_conceded(d, my_idx):
    """How many prizes the OPPONENT took off me (i.e. 6 - my remaining prizes at end),
    and crude count of how many were 3-prize KOs is NOT directly stored — we approximate
    by reading the final 'prize' lists. Returns (my_prizes_left, opp_prizes_left)."""
    try:
        for st in reversed(d['steps']):
            cur = st[0]['observation'].get('current')
            if cur and cur.get('players'):
                pl = cur['players']
                return len(pl[my_idx]['prize']), len(pl[1 - my_idx]['prize'])
    except Exception:
        pass
    return None, None


def scan_logs_for_ko(d, my_idx):
    """Scan logs across steps to count how many of MY Mega ex (3-prize) Pokemon got KO'd.
    Logs may be sparse; we count distinct turns where opponent takes 3 prizes if detectable.
    Returns count of 3-prize-KOs conceded (best-effort, may be 0 if logs empty)."""
    # Track prize count drop on my side; each drop of 3 in one observation step ~ a Mega ex KO.
    seq = []
    for st in d['steps']:
        cur = st[0]['observation'].get('current')
        if cur and cur.get('players'):
            seq.append(len(cur['players'][my_idx]['prize']))
    three_ko = 0
    for a, b in zip(seq, seq[1:]):
        if a - b >= 3:
            three_ko += 1
    return three_ko, (seq[0] - seq[-1] if seq else None)


def main():
    found = []          # list of dicts per keidroid game
    target_total = 14   # aim 10-15
    scanned = 0
    per_zip_cap = {'d21': 0, 'd20': 0, 'd19': 400, 'd18': 400}  # 0 = no cap (full stream)

    for day, zp in ZIPS.items():
        if not os.path.exists(zp):
            print(f'[skip] {day} missing'); continue
        z = zipfile.ZipFile(zp)
        members = [m for m in z.namelist() if m.endswith('.json')]
        cap = per_zip_cap.get(day, 0)
        print(f'[{day}] {len(members)} episodes, cap={cap or "all"}')
        seen = 0
        for m in members:
            if cap and seen >= cap:
                break
            seen += 1; scanned += 1
            try:
                d = json.loads(z.read(m))
            except Exception:
                continue
            agents = d.get('info', {}).get('Agents', [])
            names = [a.get('Name', '') for a in agents]
            if TARGET not in names:
                continue
            my_idx = names.index(TARGET)
            deck = deck_for(d, my_idx)
            has_mega = bool(deck) and MEGA_STARMIE in deck
            rw = d.get('rewards', [0, 0])
            won = None if rw[my_idx] == rw[1 - my_idx] else (rw[my_idx] > rw[1 - my_idx])
            myleft, oppleft = prizes_conceded(d, my_idx)
            three_ko, total_conceded = scan_logs_for_ko(d, my_idx)
            mega_in_deck = deck.count(MEGA_STARMIE) if deck else 0
            staryu_in_deck = deck.count(STARYU) if deck else 0
            found.append({
                'day': day, 'member': m, 'episode_id': d.get('info', {}).get('EpisodeId'),
                'my_idx': my_idx, 'opponent': names[1 - my_idx],
                'has_mega_starmie': has_mega,
                'mega_starmie_copies': mega_in_deck, 'staryu_copies': staryu_in_deck,
                'won': won, 'rewards': rw,
                'my_prizes_left': myleft, 'opp_prizes_left': oppleft,
                'prizes_conceded_total': total_conceded,
                'three_prize_kos_conceded': three_ko,
                '_raw': d,
            })
        print(f'  [{day}] keidroid games so far: {len(found)}')
        # stop early once we have plenty AND scanned the two freshest days fully
        if len(found) >= target_total and day in ('d20',):
            print('  enough games after fresh days, stopping scan')
            break

    print(f'\nTotal scanned ~{scanned} episodes; keidroid games found: {len(found)}')
    if not found:
        idx = {'found': False, 'reason': 'keidroid did not appear in any local episode dump '
               '(its ladder games may not be in these daily dumps). Other path: need kaggle.json '
               'to download keidroid episodes via Kaggle API.', 'scanned': scanned}
        json.dump(idx, open(os.path.join(OUT, 'index.json'), 'w'), indent=2, ensure_ascii=False)
        print('found=False written')
        return

    # select a mix of wins and losses, prefer fresh days
    wins = [g for g in found if g['won'] is True]
    losses = [g for g in found if g['won'] is False]
    draws = [g for g in found if g['won'] is None]
    print(f'wins={len(wins)} losses={len(losses)} draws={len(draws)}')

    sel = []
    # interleave to get a balanced mix up to target_total
    import itertools
    for g in itertools.chain(*itertools.zip_longest(losses, wins, draws)):
        if g is None:
            continue
        sel.append(g)
        if len(sel) >= 15:
            break

    extracted = []
    for g in sel:
        eid = g['episode_id'] or os.path.splitext(os.path.basename(g['member']))[0]
        res = 'win' if g['won'] else ('loss' if g['won'] is False else 'draw')
        fname = f"keidroid_{g['day']}_{eid}_{res}.json"
        fpath = os.path.join(OUT, fname)
        json.dump(g['_raw'], open(fpath, 'w'))
        meta = {k: v for k, v in g.items() if k != '_raw'}
        meta['file'] = fname
        extracted.append(meta)

    # aggregate stats
    dec = [g for g in found if g['won'] is not None]
    n_win = sum(1 for g in dec if g['won'])
    avg_3ko = round(sum(g['three_prize_kos_conceded'] for g in dec) / max(len(dec), 1), 2)
    avg_conceded = round(sum(g['prizes_conceded_total'] for g in dec
                            if g['prizes_conceded_total'] is not None)
                        / max(sum(1 for g in dec if g['prizes_conceded_total'] is not None), 1), 2)
    mega_confirm = sum(1 for g in found if g['has_mega_starmie'])

    index = {
        'found': True,
        'team': 'keidroid', 'team_id': 16391190, 'leaderboard_rank': 1,
        'leaderboard_score': 1358.9,
        'archetype': 'Mega Starmie ex',
        'mega_starmie_card_id': MEGA_STARMIE, 'mega_starmie_prize_value': 3,
        'staryu_card_id': STARYU,
        'scanned_episodes_approx': scanned,
        'keidroid_games_found': len(found),
        'games_with_mega_starmie_confirmed_in_deck': mega_confirm,
        'decisive_games': len(dec),
        'wins_in_found': n_win, 'losses_in_found': len(dec) - n_win,
        'wr_in_local_sample_pct': round(n_win / max(len(dec), 1) * 100, 1),
        'avg_three_prize_kos_conceded_per_game': avg_3ko,
        'avg_prizes_conceded_per_game': avg_conceded,
        'extracted_count': len(extracted),
        'extracted': extracted,
        'caveats': [
            'Decklist read from steps[1][i].action (the 60-card submitted list); reliable, full deck.',
            'three_prize_kos_conceded approximated by detecting a >=3 drop in my remaining prizes between consecutive observation snapshots; conservative (a 2-prize KO same step could mask).',
            'Local-sample WR is NOT the official 67.2%/116 figure; it only covers games present in these dumps.',
        ],
    }
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w'), indent=2, ensure_ascii=False)
    print(f'Extracted {len(extracted)} replays to {OUT}')
    print(json.dumps({k: index[k] for k in ('keidroid_games_found','wins_in_found','losses_in_found','wr_in_local_sample_pct','avg_three_prize_kos_conceded_per_game','games_with_mega_starmie_confirmed_in_deck')}, indent=2))


if __name__ == '__main__':
    main()
