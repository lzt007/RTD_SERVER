"""Inferred missing Shingetsu maps/drops; never overwrite recovered records."""
import copy
import hashlib
import json
import zlib

QUEST_IDS=(20844,20845,20846)
DROP_IDS=((31145,31149,31591,31594),(31150,31154,31592,31595),(31170,31174,31593,31596))


def _digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def _hash(value):
    return str(zlib.crc32(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()))


def _map(quest,index):
    distance=quest['distance'];width=9;start=4;height=distance+start+10;boss_y=height-10
    cells=bytearray(width*height)
    count=(8,14,22)[index];slots=((1,2),(1,2,3,4),(1,2,3))[index]
    # Distribute encounters on the direct route, including its earliest steps.
    # These positions have no surviving original-map evidence.
    ys=[start+1+(n*(distance-2))//(count-1) for n in range(count)]
    for n,y in enumerate(ys):cells[y*width+4]=slots[n%len(slots)]
    cells[(start+distance//2)*width+3]=17
    cells[boss_y*width:(boss_y+1)*width]=bytes([0xA0])*width
    cells[(height-5)*width:(height-4)*width]=bytes([0xC0])*width
    level=dict(level_data_id=quest['id'],format=0,start_x=4,start_y=start,width=width,height=height,map_data=cells.hex().upper())
    level['hash']=_hash(level)
    return level


def _drop(id,entries,template):
    # Retain the source table schema, but every new row is explicitly inferred.
    row={k:0 for k in template}
    row['id']=id
    for i,(unit,rate) in enumerate(entries,1):
        row.update({f'unit{i}_id':unit,f'unit{i}_rate':rate,f'unit{i}_lv_min':1,f'unit{i}_lv_max':1})
    return row


def build_candidate(masters,levels):
    quests={q['id']:q for q in masters[30]['data_list']}
    drops={d['id']:d for d in masters[22]['data_list']}
    candidate=dict(policy='inferred-shingetsu-v1',quest_ids=list(QUEST_IDS),levels=[],drops=[],provenance=[],
        original_records_sha256=_digest(dict(masters=masters,levels=levels)))
    for index,id in enumerate(QUEST_IDS):
        q=quests[id]
        if id not in levels:
            candidate['levels'].append(_map(q,index))
            candidate['provenance'].append(dict(kind='map',id=id,basis='Original quest distance; inferred dimensions, positions and encounters',confidence='inferred'))
        a,b,boss,rare=DROP_IDS[index];fodder=15000 if index==0 else 15004
        role=14050 if index==2 else 14000
        boss_entries=[(role,(1,3,5)[index]),(fodder,(79,77,65)[index])]
        if index==2:boss_entries.append((15022,10))
        recipes={a:[(fodder,20)],b:[(fodder,30)],boss:boss_entries,
                 rare:[(fodder,100)] if index<2 else [(15004,80),(15018,20)]}
        for did,entries in recipes.items():
            if did in drops:continue
            candidate['drops'].append(_drop(did,entries,drops[0]))
            candidate['provenance'].append(dict(kind='drop',id=did,basis='Wiki boss/rare candidates; ordinary wolf fodder, all weights, empty chance and level 1 inferred',confidence='inferred'))
    return candidate


def apply_missing(masters,levels,candidate):
    """Return independent catalogs; recovered IDs always take precedence."""
    result=copy.deepcopy(masters);maps=copy.deepcopy(levels)
    ids={r['id'] for r in result[22]['data_list']}
    additions=[r for r in candidate['drops'] if r['id'] not in ids]
    if additions:
        result[22]['data_list'].extend(copy.deepcopy(additions));result[22]['hash']=_hash(result[22]['data_list'])
    for level in candidate['levels']:maps.setdefault(level['level_data_id'],copy.deepcopy(level))
    listed={r['level_data_id'] for r in result[70]['data_list']}
    new_ids=[id for id in QUEST_IDS if id in maps and id not in listed]
    if new_ids:
        result[70]['data_list'].extend(dict(level_data_id=id) for id in new_ids)
        result[70]['hash']=_hash(result[70]['data_list'])
    return result,maps
