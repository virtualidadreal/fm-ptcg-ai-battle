"""Test de humo del encoding sobre un obs REAL de replay (corre en Docker ptcg-cabt).

Verifica: (1) to_observation_class acepta el obs dict del replay, (2) get_encoder_input produce 24 words,
(3) get_decoder_input produce 1 word por accion candidata, (4) el target de BC del experto encaja.
"""
import zipfile, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bcil import encode as E

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
zp = os.path.join(ROOT, "data/episodes/d18/pokemon-tcg-ai-battle-episodes-2026-06-18.zip")
z = zipfile.ZipFile(zp)
names = [n for n in z.namelist() if n.endswith(".json")]


def action_for(steps, t, pi):
    # alineacion confirmada: la accion vive en t+1 (la misma celda es placeholder)
    if t + 1 < len(steps):
        return steps[t + 1][pi].get("action")
    return None


def deck_of(d, seat):
    for t in range(min(4, len(d["steps"]))):
        try:
            vz = d["steps"][t][seat].get("visualize")
            if vz and vz[0].get("action"):
                a = vz[0]["action"][0]
                if isinstance(a, list) and len(a) >= 40:
                    return a
        except Exception:
            continue
    return None


tested = ok = label_ok = 0
for n in names[:200]:
    d = json.loads(z.read(n))
    steps = d.get("steps");
    if not steps:
        continue
    for seat in (0, 1):
        deck = deck_of(d, seat)
        if deck is None:
            continue
        for t in range(len(steps)):
            if steps[t][seat].get("status") != "ACTIVE":
                continue
            obs = steps[t][seat].get("observation")
            if not obs or obs.get("select") is None:
                continue
            act = action_for(steps, t, seat)
            if not isinstance(act, list) or len(act) >= 40:
                continue
            tested += 1
            try:
                sv_enc, sv_dec, actions = E.encode_pair(obs, deck)
                assert len(sv_enc.offset) == E.num_words_encoder, f"enc words {len(sv_enc.offset)}"
                assert len(sv_dec.offset) == len(actions), f"dec words {len(sv_dec.offset)} vs {len(actions)}"
                tgt = E.bc_target(act, obs["select"]["maxCount"], len(obs["select"]["option"]),
                                  obs["select"].get("minCount", 1))
                if tgt >= 0:
                    label_ok += 1
                ok += 1
            except Exception as ex:
                print(f"  FALLO ep={d['info'].get('EpisodeId')} seat={seat} step={t}: {type(ex).__name__}: {ex}")
            if tested >= 300:
                break
        if tested >= 300:
            break
    if tested >= 300:
        break

print(f"\nencodings probados: {tested} | OK: {ok} ({100*ok/max(1,tested):.1f}%) | con target valido: {label_ok}")
print("card_count:", E.card_count, "| encoder_size:", E.encoder_size, "| decoder_size:", E.decoder_size)
print("OK" if ok == tested and ok > 0 else "HAY FALLOS")
