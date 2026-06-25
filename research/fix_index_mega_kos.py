"""Rebuild data/megastarmie_analysis/index.json with a RELIABLE 3-prize-KO metric.

The original prize-progression metric was wrong: the 'prize' arrays in observation
snapshots are fog-of-war + perspective-split (each player sees their own pile differently),
so prize-count deltas were noisy/negative. Replaced with a verifiable proxy:

  count of keidroid's OWN Mega Starmie ex (card id 1031) sitting in keidroid's final
  DISCARD pile == Mega ex Pokemon that were Knocked Out (each conceding 3 prizes).

This is a LOWER BOUND: a Mega ex KO'd and later re-evolved/recycled would not appear in
the final discard snapshot. Result = win/loss come from d['rewards'] (authoritative).
"""
import os, json, glob

ROOT = '/Users/franmilla/FMA/proyectos/ptcg-ai-battle'
OUT = os.path.join(ROOT, 'data/megastarmie_analysis')
MEGA = 1031
STARYU = 1030

idx = json.load(open(os.path.join(OUT, 'index.json')))

# recompute over ALL 116 games is not possible from extracted (only 15 on disk),
# so the per-game corrected metric is added to the 15 extracted; the aggregate 3-KO
# average is computed over those 15 and flagged as a sample, while the 116-game WR stays.

files = {os.path.basename(f): f for f in glob.glob(OUT + '/keidroid_*.json')}

def mega_kos(path):
    d = json.load(open(path))
    nms = [a['Name'] for a in d['info']['Agents']]
    my = nms.index('keidroid')
    last = None
    for st in d['steps']:
        cur = st[my]['observation'].get('current')
        if cur and cur.get('players') and cur.get('yourIndex') == my:
            last = cur
    if not last:
        return None
    disc = last['players'][my].get('discard', [])
    return sum(1 for c in disc if isinstance(c, dict) and c.get('id') == MEGA)

per = []
for e in idx['extracted']:
    fp = files.get(e['file'])
    e2 = dict(e)
    e2['mega_starmie_ex_kod_in_final_discard'] = mega_kos(fp) if fp else None
    # drop the unreliable fields
    for bad in ('my_prizes_left', 'opp_prizes_left', 'prizes_conceded_total',
                'three_prize_kos_conceded'):
        e2.pop(bad, None)
    per.append(e2)

vals = [e['mega_starmie_ex_kod_in_final_discard'] for e in per
        if e['mega_starmie_ex_kod_in_final_discard'] is not None]
avg_mega_ko = round(sum(vals) / len(vals), 2) if vals else None
win_ko = [e['mega_starmie_ex_kod_in_final_discard'] for e in per if e['won']]
loss_ko = [e['mega_starmie_ex_kod_in_final_discard'] for e in per if e['won'] is False]

idx['extracted'] = per
# remove broken aggregates
idx.pop('avg_three_prize_kos_conceded_per_game', None)
idx.pop('avg_prizes_conceded_per_game', None)
idx['avg_mega_starmie_ex_kod_per_game_extracted_sample'] = avg_mega_ko
idx['avg_mega_ex_kod_in_wins'] = round(sum(win_ko) / len(win_ko), 2) if win_ko else None
idx['avg_mega_ex_kod_in_losses'] = round(sum(loss_ko) / len(loss_ko), 2) if loss_ko else None
idx['extracted_wins'] = sum(1 for e in per if e['won'])
idx['extracted_losses'] = sum(1 for e in per if e['won'] is False)
idx['caveats'] = [
    'Decklist read from steps[1][i].action (the submitted 60-card list) — reliable, full deck. keidroid runs 3x Mega Starmie ex + 3x Staryu in every game.',
    'Win/loss from d.rewards (+1/-1) — authoritative. Local 116-game record (78W/38L = 67.2%) matches the official keidroid figure EXACTLY, so these dumps contain keidroid\'s full ladder history, not a subsample.',
    'Mega-ex-KO metric = count of keidroid\'s own Mega Starmie ex (id 1031) in keidroid\'s FINAL discard pile = Megas Knocked Out (each concedes 3 prizes). LOWER BOUND: a Mega KO\'d then recycled/re-evolved would not show. Computed over the 15 EXTRACTED games only, not all 116.',
    'Prize-count arrays in observation snapshots are fog-of-war + perspective-split (each side sees its pile differently and they desync at game end) — NOT a usable prize-progression signal. The original delta metric was discarded as unreliable.',
    '15 extracted = 7 wins / 8 losses (deliberate loss-heavy mix to study how the 3-prize archetype loses).',
]

json.dump(idx, open(os.path.join(OUT, 'index.json'), 'w'), indent=2, ensure_ascii=False)
print('avg Mega ex KO/game (sample of', len(vals), '):', avg_mega_ko)
print('  in wins:', idx['avg_mega_ex_kod_in_wins'], '| in losses:', idx['avg_mega_ex_kod_in_losses'])
print('extracted wins/losses:', idx['extracted_wins'], '/', idx['extracted_losses'])
