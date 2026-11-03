"""Temporary recovered event visuals; combat numbers and drop references stay original."""
import json
import re
import zlib
from .event_content import audit_events, recovered_asset_names, recovered_asset_manifest


def apply_event_visuals(masters, levels, *, quest_ids=None, protected_enemies=(), asset_manifest=None):
    assets=asset_manifest if asset_manifest is not None else recovered_asset_manifest()
    names=set(assets['names'])
    textures=set(assets["textures"])
    prefab_names=set(assets["models"])
    models=sorted(n[4:] for n in names if n.startswith('ast_ms'))
    accepted,_=audit_events(masters,levels)
    quests={q['id']:q for q in masters[30]['data_list']}
    tables={t['id']:t for t in masters[21]['data_list']}
    enemies={e['id']:e for e in masters[20]['data_list']}
    used={}
    for id in accepted:
        if quest_ids is not None and id not in quest_ids:continue
        table=tables[quests[id]['enemy_table_id']]
        slots={b&31 for b in bytes.fromhex(levels[id]['map_data']) if 1<=b&31<=18}
        for prefix in ['boss','death']+[f'enemy{s}' for s in slots]:
            used.setdefault(table[prefix+'_set_id'],set()).add(id)
    changes=[]
    for id,quest_ids in sorted(used.items()):
        if id in protected_enemies:continue
        enemy=enemies[id];model=enemy['model'].lower();texture=(enemy.get('texture') or '').lower()
        model_missing=model not in prefab_names and 'ast_'+model not in prefab_names
        texture_missing=bool(texture and texture!='na' and texture not in textures)
        if not model_missing and not texture_missing:continue
        before={k:enemy[k] for k in ('model','texture')}
        if model_missing:
            family='_'.join(model.split('_')[:2])
            candidates=[m for m in models if m.startswith(family+'_')]
            level=re.search(r'_lv(\d+)',model)
            def distance(candidate):
                match=re.search(r'_lv(\d+)',candidate)
                return (abs(int(match[1])-int(level[1])) if level and match else 100,candidate)
            model=min(candidates,key=distance) if candidates else 'ms02_four_un_01_zako'
            if model not in models:raise RuntimeError('Missing temporary event model '+model)
            enemy['model']=model
        # A texture from another mesh can be incompatible. Select a recovered
        # texture for the chosen mesh, preferring the original element suffix.
        if model_missing or texture_missing:
            suffix=texture.rsplit('_',1)[-1]
            preferred=model+'_'+suffix
            enemy['texture']=preferred if preferred in textures else 'na'
        changes.append(dict(enemy_id=id,quest_ids=sorted(quest_ids),before=before,
                            after={k:enemy[k] for k in ('model','texture')}))
    if changes:
        payload=json.dumps(masters[20]['data_list'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
        masters[20]['hash']=str(zlib.crc32(payload))
    return changes
