"""Opt-in wolf/slime compatibility visuals. Original gameplay records stay intact."""
import copy
import hashlib
import json
import os
import zlib
from ..config import ROOT


def enabled():
    value=os.environ.get('RTD_MONSTER_RECOVERY','0')
    if value not in ('0','1'):raise RuntimeError('RTD_MONSTER_RECOVERY must be 0 or 1')
    return value=='1'


def manifest():
    return json.loads((ROOT/'config/monster-recovery.json').read_text(encoding='utf-8'))


def verified_file(row):
    name=row['bundle']
    if '/' in name or '\\' in name or not name.endswith('.unity3d'):return None
    path=ROOT/'resources/reconstructed/monsters/bundles'/name
    return path if path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'] else None


def bundle_file(name):
    if not enabled():return None
    row=next((r for r in manifest()['bundles'] if r['bundle']==name),None)
    return verified_file(row) if row else None


def referenced_enemies(masters,levels,quest_ids):
    quests={r['id']:r for r in masters[30]['data_list']}
    tables={r['id']:r for r in masters[21]['data_list']}
    found={}
    for qid in quest_ids:
        quest=quests.get(qid);level=levels.get(qid)
        if not quest or not level:continue
        table=tables.get(quest['enemy_table_id'])
        if not table:continue
        # EnemyArrangeTable constructs all 18 entries before the preloader calls
        # GetUniqueEnemyList(); a slot need not appear in this map's cell bytes.
        for prefix in ['boss','death']+[f'enemy{s}' for s in range(1,19)]:
            eid=table[prefix+'_set_id']
            if eid:found.setdefault(eid,set()).add(qid)
    return found


def apply_monster_recovery(masters,levels,quest_ids):
    if not enabled():return None
    from ..masters.catalog import load_catalog
    raw,_=load_catalog();policy=manifest()
    if policy['source_enemy_master_hash']!=raw[20]['hash']:
        raise RuntimeError('Monster recovery source master differs from audited original')
    candidates={r['model']:r for r in policy['bundles']}
    original={r['id']:r for r in raw[20]['data_list']}
    referenced=referenced_enemies(masters,levels,quest_ids)
    table=copy.deepcopy(masters[20]);changes=[];checked=set()
    for row in table['data_list']:
        eid=row['id'];source=original.get(eid)
        if eid not in referenced or source is None or source['model'] not in candidates:continue
        model=source['model'];bundle=candidates[model]
        texture=source['texture']
        if texture!='na' and texture not in bundle['textures']:
            raise RuntimeError('Converted model lacks requested texture '+texture)
        if model not in checked:
            canonical=ROOT/'resources/bundles'/bundle['bundle']
            if not canonical.is_file() and verified_file(bundle) is None:
                raise RuntimeError('Missing/corrupt monster compatibility bundle '+model)
            checked.add(model)
        before={k:row[k] for k in ('model','texture')};after={k:source[k] for k in ('model','texture')}
        if before==after:continue
        row.update(after)
        changes.append(dict(enemy_id=eid,before=before,after=after,quest_ids=sorted(referenced[eid]),inferred=True,reason=bundle['reason']))
    if changes:
        payload=json.dumps(table['data_list'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
        table['hash']=str(zlib.crc32(payload));masters[20]=table
    return dict(policy=policy['policy'],substitutions=changes,available_models=sorted(checked),derived_hash=table['hash'])
