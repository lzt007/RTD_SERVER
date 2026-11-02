"""Reproducible local summon policy; no historical probability claims."""
from math import gcd

MATERIAL_IDS = frozenset(range(15000,15032)) | {15082,15083,15593,16027,16028,16338,16540,50000}
STARTER_IDS = {20000,20010,20020,20030}


def unavailable_units(masters):
    """Reject incomplete master rows, not legitimate shared graphics or no-skill materials."""
    result={}
    checks=[(field,{r['id']:r for r in masters[rank_type]['data_list']},
             {r['id'] for r in masters[skill_type]['data_list']})
            for field,rank_type,skill_type in
            (('p_skill_id',12,11),('a_skill_id',14,13),('panel_skill_id',17,16))]
    for unit in masters[10]['data_list']:
        reasons=[]
        if not unit.get('g_id'):reasons.append('missing portrait (g_id=0)')
        if unit.get('model') in (None,'','0'):reasons.append('missing model')
        for field,ranks,skills in checks:
            rank_id=unit.get(field,0)
            if not rank_id:continue
            rank=ranks.get(rank_id)
            if rank is None:reasons.append(f'{field}: missing rank {rank_id}')
            else:
                missing=sorted({v for k,v in rank.items() if k.startswith('skill_') and v and v not in skills})
                if missing:reasons.append(f'{field}: missing skills {missing}')
        if reasons:result[str(unit['id'])]=reasons
    return result


def build_pools(masters):
    units={u['id']:u for u in masters[10]['data_list']}
    unavailable=unavailable_units(masters)
    invalid=set(map(int,unavailable))
    tables={t['id']:t for t in masters[21]['data_list']}
    drops={d['id']:d for d in masters[22]['data_list']}
    enemies={e['id']:e for e in masters[20]['data_list']}
    challenges={c['id']:c for c in masters[33]['data_list']}
    obtained=set(); sources={}
    def record(uid,qid):
        if uid in units:
            obtained.add(uid);sources.setdefault(uid,set()).add(qid)
    for q in masters[30]['data_list']:
        table=tables.get(q['enemy_table_id'],{})
        for key,drop_id in table.items():
            if not key.endswith('_drop_id'):continue
            prefix=key[:-8]
            if table.get(prefix+'_rate',0)<=0:continue
            if enemies.get(table.get(prefix+'_set_id'),{}).get('type') in (20,21):continue
            drop=drops.get(drop_id,{})
            cumulative=0
            for i in range(1,5):
                rate=drop.get(f'unit{i}_rate',0)
                if rate>0 and cumulative<100:record(drop.get(f'unit{i}_id'),q['id'])
                cumulative+=rate
        if q.get('present_type')==4:record(q['present_param'],q['id'])
        for i in range(3):
            c=challenges.get(q.get(f'challenge_id_{i}'),{})
            if c.get('present_type')==4:record(c['present_param_0'],q['id'])
    material=(set(units)&MATERIAL_IDS)-invalid
    excluded=(obtained-material)|STARTER_IDS
    eligible=set(units)-material-excluded-invalid
    if not material or not eligible:raise ValueError('Empty summon category')
    divisor=gcd(9*len(eligible),len(material))
    mw=9*len(eligible)//divisor;cw=len(material)//divisor
    def rows(ids,weight):return [dict(unit_id=i,level=1,weight=weight) for i in sorted(ids)]
    pools=dict(version=1,normal=rows(material,mw)+rows(eligible,cw),rare=rows(eligible,1))
    report=dict(material_ids=sorted(material),excluded_ids=sorted(excluded),eligible_ids=sorted(eligible),unavailable_units=unavailable,
        quest_sources={str(k):sorted(v) for k,v in sorted(sources.items())},
        counts=dict(total=len(units),materials=len(material),excluded=len(excluded),eligible=len(eligible),unavailable=len(invalid)))
    return pools,report
