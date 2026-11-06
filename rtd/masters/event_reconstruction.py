"""Missing-only event records inferred from explicit archived strategy profiles."""
import copy
import json
from pathlib import Path
from .shingetsu import _hash, _digest, _drop, QUEST_IDS

ROOT=Path(__file__).resolve().parents[2]


def _route(quest,table,enemies,challenges):
    distance=quest['distance']
    if distance<2:raise ValueError('distance does not establish a single-floor route')
    slots={i:enemies.get(table[f'enemy{i}_set_id']) for i in range(1,19)}
    if any(e and e['type'] in (20,21) for e in slots.values()):
        raise ValueError('original staircase/exit arrangement requires additional-floor protocol')
    ordinary=[i for i,e in slots.items() if i<17 and e and e['id'] and e['type'] not in (0,16,20,21)]
    if not ordinary:raise ValueError('no original ordinary encounter identity for inferred route')
    conditions=[challenges[quest[f'challenge_id_{i}']] for i in range(3) if quest[f'challenge_id_{i}'] in challenges]
    need=max([c['param_0'] for c in conditions if c['type']==31]+[0])
    soul_need=max([c['param_0'] for c in conditions if c['type']==10]+[0])
    counts={}
    for c in conditions:
        if c['type']!=30:continue
        if table['death_set_id']==c['param_0'] and c['param_1']<=1:continue
        candidates=[i for i,e in slots.items() if e and e['id']==c['param_0']]
        if not candidates:raise ValueError('wanted challenge identity absent from original encounter table')
        counts[candidates[0]]=max(counts.get(candidates[0],0),c['param_1'])
    mandatory=[i for i,n in counts.items() for _ in range(n)]
    # A walkable inferred route spans the map instead of placing every enemy
    # on the start column. Budget the lateral encounters before checking souls.
    rows=distance-1
    count=max(rows+rows//2,need,len(mandatory))
    boss_soul=enemies[table['death_set_id']]['soul_pt']
    def sequence(n):return mandatory+[ordinary[i%len(ordinary)] for i in range(n-len(mandatory))]
    while count<=3*(distance-1):
        encounter=sequence(count)
        soul=quest['soul'];valid=True
        for slot in encounter:
            soul-=1
            if soul<0:valid=False
            soul+=slots[slot]['soul_pt']
        if valid and soul-1+boss_soul>=soul_need:break
        count+=1
    else:raise ValueError('known soul gains cannot support the original challenge on inferred route')
    width=9;height=distance+14;cells=bytearray(width*height)
    extra=count-rows;x=4;direction=1;path=[]
    for row,y in enumerate(range(5,height-10)):
        path.append((x,y))
        # Spread turns over the full depth; at most two per row, matching the
        # existing encounter-capacity bound. Stay inside the two outer margins.
        turns=(row+1)*extra//rows-row*extra//rows
        if not 1<=x+direction*turns<=7:direction=-direction
        for _ in range(turns):
            if x==7:direction=-1
            elif x==1:direction=1
            x+=direction;path.append((x,y))
    for (x,y),slot in zip(path,encounter):cells[y*width+x]=slot
    for i in (17,18):
        if slots[i] and slots[i]['id'] and i not in counts:
            y=5+(i-17)
            x=next(x for x in (3,5,2,6,1,7,0,8) if not cells[y*width+x])
            cells[y*width+x]=i
    cells[(height-10)*width:(height-9)*width]=bytes([160])*width
    cells[(height-5)*width:(height-4)*width]=bytes([192])*width
    level=dict(level_data_id=quest['id'],format=0,start_x=4,start_y=4,width=width,height=height,map_data=cells.hex().upper())
    level['hash']=_hash(level)
    return level,path


def _entries(profile,prefix,enemy,units):
    if prefix=='boss':return []  # Original penalty-death reference is not the quest reward boss.
    role='boss' if prefix=='death' else 'rare' if prefix in ('enemy17','enemy18') else 'ordinary'
    candidates=[]
    for drop in profile['drops']:
        location=drop['row'].split('|')[1].strip().lower()
        belongs=(location=='boss') if role=='boss' else ('史' in location or 'スライム' in location) if role=='rare' else False
        if belongs:
            if len(drop['unit_ids'])!=1:raise ValueError('strategy drop identity unresolved: '+drop['name'])
            if drop['unit_ids'][0] not in candidates:candidates.append(drop['unit_ids'][0])
    if not candidates:
        # Unknown ordinary/undocumented drops are explicit material-only estimates.
        candidates=[15000+max(0,min(enemy['attribute']-2,3))]
    if len(candidates)>4:raise ValueError('strategy lists more than four distinct drop candidates')
    rates=[5 if uid<15000 or uid>15030 else 60 for uid in candidates]
    budget=80 if role=='boss' else 100 if role=='rare' else 20
    total=sum(rates);rates=[max(1,int(rate*budget/total)) for rate in rates]
    return list(zip(candidates,rates))


def build_candidate(masters,levels,protected=()):
    from ..policies.event_content import audit_events
    from ..policies.quest_content import SINGLE_QUESTS, VERIFIED_LAYER_QUESTS
    protected=set(protected)|audit_events(masters,levels)[0]|set(QUEST_IDS)|SINGLE_QUESTS|VERIFIED_LAYER_QUESTS
    tables={kind:{r['id']:r for r in table['data_list'] if 'id' in r} for kind,table in masters.items()}
    profiles=json.loads((ROOT/'config/event-reconstruction-sources.json').read_text())['profiles']
    candidate=dict(policy='inferred-events-v1',quest_ids=[],levels=[],drops=[],provenance=[],blocked={},original_sha256=_digest(dict(masters=masters,levels=levels)))
    proposals={}
    for profile in profiles:
        id=profile['quest_id']
        if id in protected:continue
        q=tables[30][id]
        try:
            if id==20000 or 20100<=id<=20163:
                raise ValueError('original staircase-linked floor must use the existing multilayer protocol')
            table=tables[21].get(q['enemy_table_id'])
            if table is None:raise ValueError('missing original enemy arrangement; identities and levels lack reliable anchor')
            if q['open_type_6'] not in (0,6):raise ValueError('no safe final condition slot for local stop flag')
            if any(q[f'open_type_{i}'] not in (0,1,2,4,5,6,7,9) for i in range(1,7)):
                raise ValueError('unsupported original opening condition')
            if q['present_type'] not in (0,3):raise ValueError('unsupported original first-clear reward')
            if any(q[f'challenge_id_{i}'] and (q[f'challenge_id_{i}'] not in tables[32] or tables[32][q[f'challenge_id_{i}']]['type'] not in (10,20,21,22,23,30,31,40,41,42)) for i in range(3)):
                raise ValueError('unsupported original challenge condition')
            level,path=_route(q,table,tables[20],tables[32]) if id not in levels else (levels[id],None)
            slots={b&31 for b in bytes.fromhex(level['map_data']) if 1<=b&31<=18}
            pending=[]
            for prefix in ['boss','death']+[f'enemy{i}' for i in sorted(slots)]:
                enemy=tables[20].get(table[prefix+'_set_id'])
                if enemy is None:raise ValueError('missing original enemy identity '+prefix)
                if enemy['type'] in (20,21):raise ValueError('original map requires additional-floor protocol')
                did=table[prefix+'_drop_id']
                if did not in tables[22]:pending.append(_drop(did,_entries(profile,prefix,enemy,tables[10]),tables[22][0]))
            candidate['quest_ids'].append(id)
            if id not in levels:candidate['levels'].append(level)
            for drop in pending:proposals.setdefault(drop['id'],[]).append((id,drop))
            candidate['provenance'].append(dict(quest_id=id,source=profile['path'],section=profile['section'],
                route=path,drop_ids=[r['id'] for r in pending],inferred='Map geometry/positions; all probabilities and level1; undocumented drops estimated as attribute material'))
        except (ValueError,KeyError) as error:candidate['blocked'][str(id)]=[str(error)]
    # A missing shared row must have one common estimate. Merge documented
    # candidates rather than treating guessed weights as original conflicts.
    merged={};conflicts=set()
    for did,rows in proposals.items():
        units=sorted({row[f'unit{i}_id'] for _,row in rows for i in range(1,5) if row[f'unit{i}_id']})
        if len(units)>4:
            conflicts.add(did);continue
        if all(row==rows[0][1] for _,row in rows):merged[did]=rows[0][1]
        else:
            weights=[5 if uid<15000 or uid>15030 else 60 for uid in units]
            total=sum(weights)
            merged[did]=_drop(did,[(uid,max(1,int(weight*80/total))) for uid,weight in zip(units,weights)],tables[22][0])
    rejected={id for did in conflicts for id,_ in proposals[did]}
    for id in rejected:candidate['blocked'][str(id)]=['shared missing drop ID needs more than four distinct documented candidates']
    candidate['quest_ids']=[id for id in candidate['quest_ids'] if id not in rejected]
    candidate['levels']=[r for r in candidate['levels'] if r['level_data_id'] not in rejected]
    candidate['provenance']=[r for r in candidate['provenance'] if r['quest_id'] not in rejected]
    candidate['drops']=[merged[did] for did,rows in proposals.items() if did not in conflicts and any(id not in rejected for id,_ in rows)]
    return candidate


def apply_missing(masters,levels,candidate):
    result=copy.deepcopy(masters);maps=copy.deepcopy(levels)
    existing={r['id'] for r in result[22]['data_list']}
    additions=[copy.deepcopy(r) for r in candidate['drops'] if r['id'] not in existing]
    if additions:
        result[22]['data_list'].extend(additions);result[22]['hash']=_hash(result[22]['data_list'])
    for level in candidate['levels']:maps.setdefault(level['level_data_id'],copy.deepcopy(level))
    listed={r['level_data_id'] for r in result[70]['data_list']}
    additions=[dict(level_data_id=id) for id in candidate['quest_ids'] if id in maps and id not in listed]
    if additions:
        result[70]['data_list'].extend(additions);result[70]['hash']=_hash(result[70]['data_list'])
    return result,maps


def prepare_runtime(masters,levels,protected):
    from ..policies.event_visuals import apply_event_visuals
    from ..policies.event_content import audit_events
    from ..policies.reconstructed_resources import resource_issues
    from ..policies.quest_content import SINGLE_QUESTS, VERIFIED_LAYER_QUESTS
    candidate=build_candidate(masters,levels,protected)
    assets=json.loads((ROOT/'config/event-reconstruction-assets.json').read_text())
    quests={q['id']:q for q in masters[30]['data_list']}
    tables={t['id']:t for t in masters[21]['data_list']}
    protected_enemies=set()
    protected_quests=set(protected)|SINGLE_QUESTS|VERIFIED_LAYER_QUESTS|(set(QUEST_IDS)&set(levels))
    for id in protected_quests:
        q=quests.get(id);table=tables.get(q['enemy_table_id']) if q else None
        if table:
            protected_enemies.update(value for key,value in table.items() if key.endswith('_set_id'))
    result,maps=apply_missing(masters,levels,candidate)
    changes=apply_event_visuals(result,maps,quest_ids=set(candidate['quest_ids']),
                               protected_enemies=protected_enemies,asset_manifest=assets)
    accepted,rejected=audit_events(result,maps,set(assets['names']),asset_manifest=assets)
    problems=resource_issues(result,maps,candidate['quest_ids'],assets)
    for id in candidate['quest_ids']:
        reasons=rejected.get(id,[])+problems.get(str(id),[])
        if reasons:candidate['blocked'][str(id)]=reasons
    candidate['ready_quests']=sorted(set(candidate['quest_ids'])&accepted-{int(id) for id in problems})
    candidate['visual_substitutions']=changes
    return result,maps,candidate
