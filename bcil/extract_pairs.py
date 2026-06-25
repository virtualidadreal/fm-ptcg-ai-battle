"""BC/IL (Leon v3) — extractor de pares (observation -> action) de pilotos TOP del ladder.

Une cada replay a la tabla de leaderboard (TeamNames[seat] -> Score "Elo") y se queda con las
decisiones de los seats de Elo alto (aprender de los buenos GANEN O PIERDAN, no solo del ganador).
Lee los zips diarios por STREAMING (zipfile, NO extrae los ~85GB).

Para cada par calcula ya el TARGET de BC: la enumeracion de combinaciones de acciones es IDENTICA a la
de `create_node` del notebook oficial MCTS (hasta 64 combos de tamano maxCount), y el target es el indice
de la combinacion que eligio el experto. Asi Fase B solo tiene que encodear el obs (motor) y leer el label.

NO almacena el obs completo (seria GB): el indice guarda (day, ep, seat, step) para re-streamear en Fase B.

Uso:  python bcil/extract_pairs.py [--elo 1150] [--days 18,19,20,21] [--max-per-day 0] [--out bcil/dataset]
Salida: bcil/dataset/pairs_index.jsonl  +  stats por stdout (pares, % target asignable, contextos, decks).
"""
import sys, os, json, glob, zipfile, csv, argparse, time
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument("--elo", type=float, default=1150.0)
ap.add_argument("--days", default="18,19,20,21")
ap.add_argument("--max-per-day", type=int, default=0, help="0 = todos")
ap.add_argument("--out", default=os.path.join(ROOT, "bcil/dataset"))
ap.add_argument("--archetype", default="all", help="'all' o un cardId (ej 121=Dragapult) para filtrar el deck del seat")
args = ap.parse_args()

# --- leaderboard -> Elo ---
lb_cands = glob.glob(os.path.join(ROOT, "data/leaderboard_dl/*.csv"))
assert lb_cands, "no encuentro el CSV de leaderboard en data/leaderboard_dl/"
score = {}
with open(lb_cands[0], encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        score[r["TeamName"].strip()] = float(r["Score"])


def action_for(steps, t, pi):
    """Accion del seat pi en respuesta a su obs del step t. ALINEACION CONFIRMADA EMPIRICAMENTE (next-step):
    la accion vive en steps[t+1][pi].action, NO en la misma celda (alli steps[t][pi].action es un placeholder
    `[]` aunque minCount>=1). Verificado: con esta regla el target de BC encaja en el 99.7% de selects ACTIVE
    (vs ~46% con la regla same-step). Solo se procesan celdas con status==ACTIVE (el seat decide de verdad)."""
    if t + 1 < len(steps):
        return steps[t + 1][pi].get("action")
    return None


def enumerate_combos(max_count, n_option):
    """REPLICA EXACTA de create_node: hasta 64 combinaciones de tamano max_count de los n_option indices."""
    if max_count <= 0:
        return [[]]
    indices = list(range(max_count))
    combos = []
    for _ in range(64):
        combos.append(indices.copy())
        for i in range(len(indices)):
            idx = len(indices) - i - 1
            if indices[idx] < n_option - i - 1:
                indices[idx] += 1
                for j in range(idx + 1, len(indices)):
                    indices[j] = indices[j - 1] + 1
                break
        else:
            break
    return combos


def bc_target(action, max_count, n_option, min_count):
    """Indice de la combinacion enumerada que == accion del experto (orden-insensible). -1 si no encaja.
    Cuando min_count==0 se incluye la accion VACIA ([]) como candidato (pasar/declinar), igual que
    candidate_actions() en encode.py. El orden ([] primero) debe coincidir."""
    if not isinstance(action, list):
        return -1
    combos = enumerate_combos(max_count, n_option)
    if min_count == 0:
        combos = [[]] + combos
    key = sorted(action)
    for k, c in enumerate(combos):
        if sorted(c) == key:
            return k
    return -1


def deck_of(d, seat):
    """Recupera las 60 cartas del seat. Robusto: busca en TODOS los steps de ese seat una accion de >=40 ids
    en visualize (la sumision de mazo del mulligan). Devuelve None si no aparece."""
    steps = d.get("steps", [])
    for t in range(min(4, len(steps))):
        try:
            vz = steps[t][seat].get("visualize")
            if vz and vz[0].get("action"):
                a = vz[0]["action"][0]
                if isinstance(a, list) and len(a) >= 40:
                    return a
        except Exception:
            continue
    return None


days = args.days.split(",")
os.makedirs(args.out, exist_ok=True)
out = open(os.path.join(args.out, "pairs_index.jsonl"), "w")

games = decisive = pairs = target_ok = 0
joinable = total_seats = 0
ctx = Counter(); seltype = Counter(); selsize = Counter()
no_target_by_selsize = Counter()
deck_ok = deck_no = 0
elo_buckets = Counter()
arch_filter = None if args.archetype == "all" else int(args.archetype)
t0 = time.time()

for dd in days:
    zp = os.path.join(ROOT, f"data/episodes/d{dd}/pokemon-tcg-ai-battle-episodes-2026-06-{dd}.zip")
    if not os.path.exists(zp):
        print(f"  [aviso] falta {zp}, salto dia {dd}"); continue
    z = zipfile.ZipFile(zp)
    names = [n for n in z.namelist() if n.endswith(".json")]
    if args.max_per_day > 0:
        names = names[:args.max_per_day]
    print(f"dia {dd}: {len(names)} episodios")
    for n in names:
        try:
            d = json.loads(z.read(n))
        except Exception:
            continue
        games += 1
        rw = d.get("rewards"); steps = d.get("steps")
        info = d.get("info", {}); tn = info.get("TeamNames", [])
        ep_id = info.get("EpisodeId")
        if not steps or len(tn) < 2:
            continue
        is_dec = rw and len(rw) == 2 and rw[0] != rw[1] and None not in rw
        if is_dec:
            decisive += 1
        for seat in (0, 1):
            total_seats += 1
            sc = score.get(tn[seat])
            if sc is None:
                continue
            joinable += 1
            if sc < args.elo:
                continue
            deck = deck_of(d, seat)
            if arch_filter is not None and (deck is None or arch_filter not in deck):
                continue
            if deck is not None:
                deck_ok += 1
            else:
                deck_no += 1
            won = (is_dec and ((rw[seat] > rw[1 - seat])))
            elo_buckets[int(sc // 50) * 50] += 1
            for t in range(len(steps)):
                try:
                    e = steps[t][seat]
                    if e.get("status") != "ACTIVE":
                        continue  # solo las celdas donde el seat decide de verdad (las INACTIVE son vista espejo/stale)
                    obs = e.get("observation")
                    if not obs or obs.get("select") is None:
                        continue
                    sel = obs["select"]
                    act = action_for(steps, t, seat)
                    if act is None or not isinstance(act, list):
                        continue
                    if len(act) >= 40:
                        continue  # sumision de mazo / mulligan (60 ids), no es una decision de juego a clonar
                    opts = sel.get("option") or []
                    maxc = sel.get("maxCount") or 1
                    minc = sel.get("minCount")
                    tgt = bc_target(act, maxc, len(opts), minc if minc is not None else 1)
                    pairs += 1
                    c = sel.get("context")
                    ctx[c] += 1
                    selsize[len(act)] += 1
                    if act and 0 <= act[0] < len(opts):
                        seltype[opts[act[0]].get("type")] += 1
                    if tgt >= 0:
                        target_ok += 1
                    else:
                        no_target_by_selsize[len(act)] += 1
                    out.write(json.dumps({
                        "day": dd, "ep": ep_id, "seat": seat, "step": t,
                        "elo": round(sc, 1), "won": bool(won),
                        "ctx": c, "n_opt": len(opts), "minc": sel.get("minCount"),
                        "maxc": maxc, "action": act, "target": tgt,
                        "has_deck": deck is not None,
                    }) + "\n")
                except Exception:
                    continue
out.close()

el = time.time() - t0
print(f"\n=== DATASET BC (Elo>={args.elo:.0f}, archetype={args.archetype}) — {el:.0f}s ===")
print(f"episodios: {games} | decisivos: {decisive}")
print(f"seat join (TeamNames->Elo): {joinable}/{total_seats} = {100*joinable/max(1,total_seats):.1f}%")
print(f"teacher-seats con deck recuperable: {deck_ok} | sin deck: {deck_no} "
      f"({100*deck_ok/max(1,deck_ok+deck_no):.1f}% recuperado)")
print(f"\nPARES totales: {pairs:,}")
print(f"PARES con TARGET asignable (entrenables): {target_ok:,} = {100*target_ok/max(1,pairs):.1f}%")
print(f"pares SIN target por tamano de seleccion: {dict(sorted(no_target_by_selsize.items()))}")
print(f"\ntamano de seleccion (todos): {dict(sorted(selsize.items()))}")
print(f"contextos (SelectContext) top: {ctx.most_common(10)}")
print(f"tipo de opcion elegida (OptionType) top: {seltype.most_common(10)}")
print(f"distribucion Elo de teacher-seats (bucket 50): {dict(sorted(elo_buckets.items(), reverse=True))}")
print(f"\nindice escrito en {os.path.join(args.out, 'pairs_index.jsonl')}")
