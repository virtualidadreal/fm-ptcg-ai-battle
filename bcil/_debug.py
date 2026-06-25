import os,sys,json,zipfile
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0,ROOT)
rows=[]
for line in open(os.path.join(ROOT,"bcil/dataset/pairs_index.jsonl")):
    rows.append(json.loads(line))
    if len(rows)>=5: break
print("sample rows:", [(r["day"],r["ep"],r["seat"],r["step"]) for r in rows])
day=rows[0]["day"]
z=zipfile.ZipFile(os.path.join(ROOT,f"data/episodes/d{day}/pokemon-tcg-ai-battle-episodes-2026-06-{day}.zip"))
names=[n for n in z.namelist() if n.endswith(".json")]
print("zip first names:", names[:3])
idx={os.path.basename(n)[:-5]:n for n in names}
ep=rows[0]["ep"]
print("looking ep:", ep, "-> found:", idx.get(str(ep)))
nm=idx.get(str(ep))
if nm:
    d=json.loads(z.read(nm)); steps=d["steps"]; seat=rows[0]["seat"]
    a_deck=None
    for t in range(min(6,len(steps))):
        a=steps[t][seat].get("action")
        if isinstance(a,list) and len(a)>=40: a_deck=a; break
    print("deck:", a_deck is not None, len(a_deck) if a_deck else None)
    from bcil import encode as E
    obs=steps[rows[0]["step"]][seat]["observation"]
    try:
        sv_enc,sv_dec,actions=E.encode_pair(obs,a_deck)
        print("encode OK enc",len(sv_enc.offset),"dec",len(sv_dec.offset),"acts",len(actions))
    except Exception as ex:
        import traceback; traceback.print_exc()
