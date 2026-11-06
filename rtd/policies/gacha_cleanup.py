"""Auditable subtraction only; never edits master data or owned units."""
import copy


def exclusions(masters, levels, playable, overrides=None):
    units={r['id']:r for r in masters[10]['data_list']}
    tables={r['id']:r for r in masters[21]['data_list']}
    drops={r['id']:r for r in masters[22]['data_list']}
    enemies={r['id']:r for r in masters[20]['data_list']}
    reasons={}
    def add(uid, reason):
        if uid in units:reasons.setdefault(uid,[]).append(reason)
    for unit in units.values():
        for key,value in unit.items():
            if key=='rev_unit_id' or key.startswith('ultimate_rev_unit_id_'):
                if value:add(value,dict(kind='evolution',source=unit['id'],field=key))
    overrides=overrides or {}
    for quest in masters[30]['data_list']:
        qid=quest['id']
        if qid not in playable or qid not in levels:continue
        table=tables.get(quest['enemy_table_id'],{})
        slots={cell&31 for cell in bytes.fromhex(levels[qid]['map_data'])}
        prefixes=['boss','death']+[f'enemy{s}' for s in sorted(slots) if 1<=s<=18]
        for prefix in prefixes:
            if table.get(prefix+'_rate',0)<=0:continue
            if enemies.get(table.get(prefix+'_set_id'),{}).get('type') in (20,21):continue
            did=table.get(prefix+'_drop_id')
            if (qid,did) in overrides:
                for row in overrides[qid,did]:
                    if row['weight']>0:add(row['unit_id'],dict(kind='override_drop',quest=qid,drop=did,slot=prefix))
                continue
            drop=drops.get(did,{})
            cumulative=0
            for i in range(1,5):
                rate=drop.get(f'unit{i}_rate',0)
                if rate>0 and cumulative<100:add(drop.get(f'unit{i}_id'),dict(kind='drop',quest=qid,drop=did,slot=prefix))
                cumulative+=rate
    return reasons


def clean_pools(pools,reasons):
    result=copy.deepcopy(pools);report={}
    for name,rows in pools.items():
        keep=[copy.deepcopy(row) for row in rows if row['unit_id'] not in reasons]
        if not keep:raise ValueError(f'Cleanup would empty pool {name}')
        result[name]=keep
        report[name]=dict(before=len(rows),after=len(keep),removed=[dict(entry=row,reasons=reasons[row['unit_id']]) for row in rows if row['unit_id'] in reasons])
    return result,report
