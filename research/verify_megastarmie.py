import json, sys

def load(f):
    return json.load(open(f))

def track(file, mine_idx=None):
    d = load(file)
    rewards = d['rewards']
    steps = d['steps']
    # Determine my index from observation yourIndex (keidroid is the POV agent that has full obs)
    # The POV agent is agent0 in steps (has 'visualize'/'step'); yourIndex tells which player slot
    timeline = []
    for st, pair in enumerate(steps):
        obs = pair[0].get('observation')
        if not obs: continue
        cur = obs.get('current')
        if not cur: continue
        yi = cur['yourIndex']
        turn = cur['turn']
        me = cur['players'][yi]
        opp = cur['players'][1-yi]
        def active_info(p):
            act = p.get('active')
            if not act: return None
            act = [c for c in act if c]
            if not act: return None
            # active is list (active + attached evolutions stack). first is top
            top = act[0]
            return {'id':top['id'],'serial':top['serial'],'hp':top['hp'],'maxHp':top['maxHp'],
                    'energies':len(top.get('energies',[])),'tools':top.get('tools',[])}
        timeline.append({
            'step':st,'turn':turn,'yourIndex':yi,
            'me_active':active_info(me),'opp_active':active_info(opp),
            'me_prize':len(me.get('prize',[])) if isinstance(me.get('prize'),list) else me.get('prize'),
            'opp_prize':len(opp.get('prize',[])) if isinstance(opp.get('prize'),list) else opp.get('prize'),
            'me_discard':[c.get('id') for c in me.get('discard',[])] if isinstance(me.get('discard'),list) else None,
        })
    return d, timeline

if __name__=='__main__':
    f=sys.argv[1]
    d,tl=track(f)
    print('FILE',f,'rewards',d['rewards'],'steps_with_obs',len(tl))
    for r in tl:
        ma=r['me_active']; oa=r['opp_active']
        ms = f"id{ma['id']}s{ma['serial']} {ma['hp']}/{ma['maxHp']} e{ma['energies']}{' T'+str(ma['tools']) if ma['tools'] else ''}" if ma else '-'
        os_ = f"id{oa['id']}s{oa['serial']} {oa['hp']}/{oa['maxHp']} e{oa['energies']}" if oa else '-'
        print(f"st{r['step']:>3} T{r['turn']:>2} | ME {ms:<34} | OPP {os_:<28}")
