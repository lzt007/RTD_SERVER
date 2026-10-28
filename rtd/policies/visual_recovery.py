"""Audited reversible visual overlays; preserve all original gameplay fields."""
import copy
import hashlib
import json
import zlib
from ..config import path_for


def apply_visual_recovery(masters):
    table = copy.deepcopy(masters[20])
    enemy = next(row for row in table['data_list'] if row['id'] == 41221)
    before = dict(model=enemy['model'], texture=enemy['texture'])
    if before != dict(model='ms01_sla_lv3', texture='ms01_sla_lv3_fire'):
        raise RuntimeError('Visual recovery source no longer matches audited enemy 41221')
    after = dict(model='ms01_sla_lv1', texture='ms01_sla_lv1_fire')
    enemy.update(after)
    policy=json.loads((path_for('visual_policy')).read_text(encoding='utf-8'))
    if policy['source_enemy_master_hash']!=masters[20]['hash']:
        raise RuntimeError('Placeholder audit no longer matches source master')
    by_id={row['id']:row for row in table['data_list']}
    for replacement in policy['substitutions']:
        row=by_id[replacement['enemy_id']]
        if {k:row[k] for k in ('model','texture')}!=replacement['before']:
            raise RuntimeError('Placeholder source differs: '+str(row['id']))
        if replacement['after']!=policy['placeholder']:
            raise RuntimeError('All new placeholders must use the same fixed boss')
        row.update(replacement['after'])
    payload = json.dumps(table['data_list'], sort_keys=True, ensure_ascii=False,
                         separators=(',', ':')).encode('utf-8')
    table['hash'] = str(zlib.crc32(payload))
    if table['hash'] == masters[20]['hash']:
        raise RuntimeError('Derived visual table hash collides with source hash')
    manifest = dict(policy='local-11000-plus-fixed-placeholder-v2', quest_ids=sorted({11000}|{
        q for row in policy['substitutions'] for q in row['quest_ids']}),
        master_type=20, enemy_id=41221, source_hash=masters[20]['hash'],
        derived_hash=table['hash'], payload_sha256=hashlib.sha256(payload).hexdigest(),
        before=before, after=after,placeholder=policy['placeholder'],substitutions=policy['substitutions'])
    masters[20] = table
    return manifest
