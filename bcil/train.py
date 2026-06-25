"""BC/IL Fase B (paso 2) — entrena la policy net Leon v3 sobre los shards encodados.

Corre en HOST (torch nativo, MPS/CPU). Lee bcil/dataset/encoded/shard_*.npz, divide train/val por shard,
entrena BC (cross-entropy del policy contra la accion experta) + value head (MSE opcional). Reporta accuracy
top-1 del policy en validacion (METRICA DE TRAINING, NO de exito — el exito es batir a Leon v1 en el panel).

Uso:  python bcil/train.py [--epochs 8] [--bs 256] [--d-model 96] [--lr 3e-4] [--val-shards 1]
Salida: bcil/dataset/leon_v3.pt (state_dict + config) y curva de accuracy por epoch.
"""
import os, sys, glob, argparse, time, random
import numpy as np
import torch
import torch.nn.functional as F

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from bcil.model import LeonV3Net, NUM_WORDS_ENC

ap = argparse.ArgumentParser()
ap.add_argument("--shards", default=os.path.join(ROOT, "bcil/dataset/encoded"))
ap.add_argument("--epochs", type=int, default=8)
ap.add_argument("--bs", type=int, default=256)
ap.add_argument("--d-model", type=int, default=96)
ap.add_argument("--lr", type=float, default=3e-4)
ap.add_argument("--val-shards", type=int, default=1, help="nº de shards reservados a validacion")
ap.add_argument("--value-weight", type=float, default=0.3)
ap.add_argument("--out", default=os.path.join(ROOT, "bcil/dataset/leon_v3.pt"))
args = ap.parse_args()

dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
print("device:", dev)


class Shard:
    """Un shard cargado en memoria, con indexado por muestra para armar batches."""
    def __init__(self, path):
        z = np.load(path)
        self.e_idx = z["e_idx"]; self.e_val = z["e_val"]; self.e_word_off = z["e_word_off"]
        self.d_idx = z["d_idx"]; self.d_val = z["d_val"]; self.d_word_off = z["d_word_off"]
        self.target = z["target"]; self.n_cand = z["n_cand"]; self.value = z["value"]
        self.n = len(self.target)
        # offset acumulado de words por muestra (24 c/u) y de candidatos por muestra
        self.e_sample_word0 = np.arange(self.n) * NUM_WORDS_ENC
        self.cand_cumsum = np.concatenate([[0], np.cumsum(self.n_cand)])

    def sample(self, i):
        # encoder words [i*24, i*24+24)
        w0 = i * NUM_WORDS_ENC
        word_starts = self.e_word_off[w0:w0 + NUM_WORDS_ENC]
        e_end = self.e_word_off[w0 + NUM_WORDS_ENC] if (w0 + NUM_WORDS_ENC) < len(self.e_word_off) else len(self.e_idx)
        e_tok0 = word_starts[0]
        # decoder candidates
        c0 = self.cand_cumsum[i]; c1 = self.cand_cumsum[i + 1]
        cand_starts = self.d_word_off[c0:c1]
        d_end = self.d_word_off[c1] if c1 < len(self.d_word_off) else len(self.d_idx)
        d_tok0 = cand_starts[0] if len(cand_starts) else 0
        return {
            "e_idx": self.e_idx[e_tok0:e_end], "e_val": self.e_val[e_tok0:e_end],
            "e_word_off": (word_starts - e_tok0),
            "d_idx": self.d_idx[d_tok0:d_end], "d_val": self.d_val[d_tok0:d_end],
            "d_word_off": (cand_starts - d_tok0),
            "target": int(self.target[i]), "n_cand": int(self.n_cand[i]), "value": float(self.value[i]),
        }


def collate(samples):
    # vectorizado con numpy (C-level concat) + from_numpy (zero-copy). Rebasea los offsets de cada muestra.
    e_idx = np.concatenate([s["e_idx"] for s in samples])
    e_val = np.concatenate([s["e_val"] for s in samples])
    d_idx = np.concatenate([s["d_idx"] for s in samples])
    d_val = np.concatenate([s["d_val"] for s in samples])
    e_wo = []; d_wo = []; eb = 0; db = 0
    for s in samples:
        e_wo.append(s["e_word_off"] + eb); eb += len(s["e_idx"])
        d_wo.append(s["d_word_off"] + db); db += len(s["d_idx"])
    e_word_off = np.concatenate(e_wo); d_word_off = np.concatenate(d_wo)
    n_cands = np.fromiter((s["n_cand"] for s in samples), dtype=np.int64, count=len(samples))
    targets = np.fromiter((s["target"] for s in samples), dtype=np.int64, count=len(samples))
    values = np.fromiter((s["value"] for s in samples), dtype=np.float32, count=len(samples))
    fl = lambda a: torch.from_numpy(np.ascontiguousarray(a, dtype=np.int64))
    ff = lambda a: torch.from_numpy(np.ascontiguousarray(a, dtype=np.float32))
    return (fl(e_idx), ff(e_val), fl(e_word_off),
            fl(d_idx), ff(d_val), fl(d_word_off),
            torch.from_numpy(n_cands), torch.from_numpy(targets), torch.from_numpy(values))


def batches(shards, bs, shuffle=True):
    items = [(si, i) for si, sh in enumerate(shards) for i in range(sh.n)]
    if shuffle:
        random.shuffle(items)
    for k in range(0, len(items), bs):
        chunk = items[k:k + bs]
        yield collate([shards[si].sample(i) for si, i in chunk])


def run():
    paths = sorted(glob.glob(os.path.join(args.shards, "shard_*.npz")))
    assert paths, f"no hay shards en {args.shards}"
    print(f"shards: {len(paths)}")
    val_paths = paths[:args.val_shards]; train_paths = paths[args.val_shards:]
    train = [Shard(p) for p in train_paths]
    val = [Shard(p) for p in val_paths]
    n_train = sum(s.n for s in train); n_val = sum(s.n for s in val)
    print(f"train {n_train} muestras ({len(train)} shards) | val {n_val} ({len(val)} shards)")

    model = LeonV3Net(d_model=args.d_model).to(dev)
    nparams = sum(p.numel() for p in model.parameters())
    print(f"modelo: {nparams:,} params (d_model={args.d_model})")
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)

    def evaluate():
        model.eval(); correct = tot = 0; vloss = 0.0
        with torch.no_grad():
            for b in batches(val, args.bs, shuffle=False):
                b = [x.to(dev) for x in b]
                e_idx, e_val, e_wo, d_idx, d_val, d_wo, n_cand, target, value = b
                logits, pred_v = model(e_idx, e_val, e_wo, d_idx, d_val, d_wo, n_cand)
                correct += (logits.argmax(1) == target).sum().item(); tot += len(target)
                vloss += F.mse_loss(pred_v, value).item() * len(target)
        return correct / max(1, tot), vloss / max(1, tot)

    best = 0.0
    for ep in range(args.epochs):
        model.train(); t0 = time.time(); seen = 0; running = 0.0
        for b in batches(train, args.bs):
            b = [x.to(dev) for x in b]
            e_idx, e_val, e_wo, d_idx, d_val, d_wo, n_cand, target, value = b
            logits, pred_v = model(e_idx, e_val, e_wo, d_idx, d_val, d_wo, n_cand)
            ploss = F.cross_entropy(logits, target)
            vloss = F.mse_loss(pred_v, value)
            loss = ploss + args.value_weight * vloss
            opt.zero_grad(); loss.backward(); opt.step()
            seen += len(target); running += loss.item() * len(target)
        acc, vmse = evaluate()
        print(f"epoch {ep+1}/{args.epochs} | loss {running/seen:.3f} | val top1 {100*acc:.1f}% | val vmse {vmse:.3f} | {time.time()-t0:.0f}s")
        if acc > best:
            best = acc
            torch.save({"state_dict": model.state_dict(), "d_model": args.d_model,
                        "val_top1": acc}, args.out)
    print(f"\nmejor val top1: {100*best:.1f}% | pesos en {args.out}")
    print("RECORDATORIO: top1 es metrica de TRAINING. El exito = batir a Leon v1 en el panel (Fase C/D).")


if __name__ == "__main__":
    run()
