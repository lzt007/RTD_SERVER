"""Fail-closed audit of recovered event maps and their combat dependencies."""

def audit_events(masters, levels, asset_names=None):
    assets=recovered_asset_manifest() if asset_names is not None else None
    tables={k:{r['id']:r for r in v['data_list'] if 'id' in r} for k,v in masters.items()}
    tables[34]={r['sp_event_id']:r for r in masters.get(34,{}).get('data_list',[])}
    accepted=set(); rejected={}
    for q in tables[30].values():
        id=q['id']
        if q['division']!=20000 or id not in levels or id==20000 or 20100<=id<=20163:
            continue
        reasons=[]; level=levels[id]
        if assets is not None and q['map'] not in assets['map_ids']:reasons.append('missing map scene '+str(q['map']))
        try:
            cells=bytes.fromhex(level['map_data'])
            if level.get('level_data_id')!=id:reasons.append('map identity')
            if level['width']<=0 or level['height']<=0 or len(cells)!=level['width']*level['height']:reasons.append('map dimensions')
            if not (0<=level['start_x']<level['width'] and 0<=level['start_y']<level['height']):reasons.append('map start')
        except (KeyError,ValueError,TypeError):
            rejected[id]=['invalid map'];continue
        table=tables[21].get(q['enemy_table_id'])
        if table is None:rejected[id]=['missing enemy table'];continue
        for index in range(1,7):
            kind=q[f'open_type_{index}'];value=q[f'open_param_{index}']
            if kind not in (0,1,2,4,5,6,7,9):reasons.append('unsupported open condition '+str(kind))
            if kind in (2,9) and value and value not in tables[30]:reasons.append('missing prerequisite')
        if q['present_type'] not in (0,3):reasons.append('unsupported first-clear reward')
        for index in range(3):
            cid=q[f'challenge_id_{index}']
            if cid and cid in tables[32] and tables[32][cid]['type']==20:
                if any(tables[32][cid][f'param_{i}'] and tables[32][cid][f'param_{i}'] not in tables[10] for i in range(4)):
                    reasons.append('missing challenge unit')
            if cid and (cid not in tables[32] or tables[32][cid]['type'] not in (10,20,21,23,30,31,40,41,42)):
                reasons.append('unsupported challenge '+str(cid))
        for key in ('sp_event_id','open_sp_event_id'):
            if q[key] and q[key] not in tables.get(34,{}):reasons.append('missing event identity')
        slots={b&31 for b in cells if 1<=b&31<=18}
        for prefix in ['boss','death']+[f'enemy{s}' for s in sorted(slots)]:
            enemy=tables[20].get(table[prefix+'_set_id'])
            if enemy is None:reasons.append('missing enemy '+prefix);continue
            if asset_names is not None:
                model=enemy['model'].lower();texture=(enemy.get('texture') or '').lower()
                if model not in assets['models'] and 'ast_'+model not in assets['models']:
                    reasons.append('missing model '+model)
                if texture and texture!='na' and texture not in assets['textures']:
                    reasons.append('missing texture '+texture)
            if enemy['type'] in (20,21):
                destination=table[prefix+'_drop_id']
                if enemy['type']==20 and destination not in levels:
                    reasons.append('missing stair destination '+str(destination))
                else:reasons.append('requires additional floor protocol')
                continue
            drop=tables[22].get(table[prefix+'_drop_id'])
            if drop is None:reasons.append('missing drop '+prefix);continue
            if drop.get('sp_event_point',0) and not q['sp_event_id']:reasons.append('missing point event identity')
            for index in range(1,5):
                uid=drop[f'unit{index}_id']
                if uid and uid not in tables[10]:reasons.append('missing drop unit '+str(uid))
        if reasons:rejected[id]=sorted(set(reasons))
        else:accepted.add(id)
    return accepted,rejected


def single_quests(api):
    from .quest_content import SINGLE_QUESTS
    return SINGLE_QUESTS | getattr(api,'event_quests',set())


def recovered_asset_names():
    import json
    from ..config import ROOT
    return set(json.loads((ROOT/'config/event-asset-support.json').read_text())['names'])


def recovered_asset_manifest():
    import json
    from ..config import ROOT
    return json.loads((ROOT/'config/event-asset-support.json').read_text())
