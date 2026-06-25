"""BC/IL Fase B (paso 1) — encodea el indice de pares a tensores sparse para entrenar.

CORRE EN DOCKER ptcg-cabt (necesita el motor: to_observation_class + all_card_data via libcg.so).
Lee bcil/dataset/pairs_index.jsonl, reagrupa por (day, ep) para minimizar lecturas de zip, re-streamea
cada episodio, y para cada par indexado encodea el obs (steps[t][seat]) con su deck -> SparseVector encoder +
SparseVector decoder (una "word" por accion candidata) + target.

Guarda en shards .npz con formato CSR plano (indices/values/offsets concatenados) para entrenar en HOST con
torch sin volver a tocar el motor. Solo encodea pares con target>=0 (los demas no son entrenables).

Uso (Docker):  python bcil/encode_dataset.py [--shard-size 20000] [--limit 0]
"""
import os, sys, json, zipfile, argparse
from collections import defaultdict
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bcil import encode as E

ap = argparse.ArgumentParser()
ap.add_argument("--index", default=os.path.join(ROOT, "bcil/dataset/pairs_index.jsonl"))
ap.add_argument("--out", default=os.path.join(ROOT, "bcil/dataset/encoded"))
ap.add_argument("--shard-size", type=int, default=20000)
ap.add_argument("--limit", type=int, default=0, help="0 = todos")
ap.add_argument("--days", default="", help="filtra el indice a estos dias (ej '18'); vacio = todos")
ap.add_argument("--prefix", default="shard", help="prefijo del nombre de shard (para no colisionar en paralelo)")
ap.add_argument("--part", default="", help="particion balanceada 'i/N' por episodio (ej '1/4'); para paralelizar")
args = ap.parse_args()
os.makedirs(args.out, exist_ok=True)
DAYS_FILTER = set(args.days.split(",")) if args.days else None
PART_I = PART_N = None
if args.part:
    PART_I, PART_N = (int(x) for x in args.part.split("/"))  # i en 1..N


def deck_of(d, seat):
    """Las 60 cartas del seat = su accion de sumision de mazo (lista de >=40 ids) en los primeros steps.
    Verificado: 100% de recuperacion via .action (vs 50% via visualize), y coinciden cuando ambos existen."""
    steps = d.get("steps", [])
    for t in range(min(6, len(steps))):
        try:
            a = steps[t][seat].get("action")
            if isinstance(a, list) and len(a) >= 40:
                return a
        except Exception:
            continue
    # respaldo: visualize (por si algun replay no trae la accion)
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


# agrupa pares por (day, ep)
by_ep = defaultdict(list)
n_idx = 0
with open(args.index) as f:
    for line in f:
        r = json.loads(line)
        if r.get("target", -1) < 0:
            continue
        if DAYS_FILTER is not None and r["day"] not in DAYS_FILTER:
            continue
        by_ep[(r["day"], r["ep"])].append(r)
        n_idx += 1
        if args.limit and n_idx >= args.limit:
            break

# particion balanceada por episodio (para paralelizar sin solapar): cada worker coge 1 de cada N episodios
if PART_N:
    keys = sorted(by_ep.keys())
    keep = {k for j, k in enumerate(keys) if j % PART_N == (PART_I - 1)}
    by_ep = {k: v for k, v in by_ep.items() if k in keep}
    n_idx = sum(len(v) for v in by_ep.values())
print(f"pares entrenables a encodear: {n_idx} | episodios distintos: {len(by_ep)} | part={args.part or 'all'} days={args.days or 'all'}")

# buffers del shard. Guardamos offsets a NIVEL DE WORD (no de muestra) para poder reconstruir las 24 words del
# encoder y CADA accion candidata del decoder por separado (EmbeddingBag necesita el inicio de cada bag).
shard = 0
e_idx = []; e_val = []; e_word_off = []   # e_word_off: inicio global de cada word del encoder (24 por muestra)
d_idx = []; d_val = []; d_word_off = []   # d_word_off: inicio global de cada candidato del decoder (n_cand por muestra)
targets = []; n_cands = []; values = []
done = skipped = 0


def flush(shard):
    if not targets:
        return
    np.savez_compressed(
        os.path.join(args.out, f"{args.prefix}_{shard:04d}.npz"),
        e_idx=np.array(e_idx, dtype=np.int32), e_val=np.array(e_val, dtype=np.float32),
        e_word_off=np.array(e_word_off, dtype=np.int64),   # 24 * n_muestras
        d_idx=np.array(d_idx, dtype=np.int32), d_val=np.array(d_val, dtype=np.float32),
        d_word_off=np.array(d_word_off, dtype=np.int64),   # sum(n_cand) bags
        target=np.array(targets, dtype=np.int32), n_cand=np.array(n_cands, dtype=np.int32),
        value=np.array(values, dtype=np.float32),  # +1 si el maestro gano la partida, -1 si perdio (value head)
    )
    print(f"  shard {shard}: {len(targets)} muestras | {len(e_idx)} enc-tokens, {len(d_idx)} dec-tokens")


# abre zips bajo demanda
zips = {}
def zip_for(day):
    if day not in zips:
        zips[day] = zipfile.ZipFile(os.path.join(ROOT, f"data/episodes/d{day}/pokemon-tcg-ai-battle-episodes-2026-06-{day}.zip"))
    return zips[day]

# index de nombres por ep_id por dia (para localizar el json del episodio)
name_cache = {}
def name_index(day):
    if day not in name_cache:
        z = zip_for(day)
        idx = {}
        for n in z.namelist():
            if n.endswith(".json"):
                base = os.path.basename(n)[:-5]
                idx[base] = n
        name_cache[day] = idx
    return name_cache[day]

for (day, ep), rows in by_ep.items():
    z = zip_for(day)
    nm = name_index(day).get(str(ep))
    if nm is None:
        skipped += len(rows); continue
    try:
        d = json.loads(z.read(nm))
    except Exception:
        skipped += len(rows); continue
    steps = d.get("steps")
    decks = {0: deck_of(d, 0), 1: deck_of(d, 1)}
    for r in rows:
        seat = r["seat"]; t = r["step"]; deck = decks.get(seat)
        if deck is None:
            skipped += 1; continue
        try:
            obs = steps[t][seat]["observation"]
            sv_enc, sv_dec, actions = E.encode_pair(obs, deck)
            if len(sv_enc.offset) != E.num_words_encoder or len(sv_dec.offset) != len(actions):
                skipped += 1; continue
            # encoder: 24 words; offset global de cada word = base + offset local
            base_e = len(e_idx)
            for o in sv_enc.offset:
                e_word_off.append(base_e + o)
            e_idx.extend(sv_enc.index); e_val.extend(sv_enc.value)
            # decoder: n_cand candidatos; offset global de cada candidato
            base_d = len(d_idx)
            for o in sv_dec.offset:
                d_word_off.append(base_d + o)
            d_idx.extend(sv_dec.index); d_val.extend(sv_dec.value)
            targets.append(r["target"]); n_cands.append(len(actions))
            values.append(1.0 if r.get("won") else -1.0)
            done += 1
            if len(targets) >= args.shard_size:
                flush(shard); shard += 1
                e_idx[:] = []; e_val[:] = []; e_word_off[:] = []
                d_idx[:] = []; d_val[:] = []; d_word_off[:] = []
                targets[:] = []; n_cands[:] = []; values[:] = []
        except Exception:
            skipped += 1; continue

flush(shard)
print(f"\nEncodadas {done} muestras en {shard+1} shards | saltadas {skipped} (sin deck / error)")
print(f"salida: {args.out}/shard_*.npz")
