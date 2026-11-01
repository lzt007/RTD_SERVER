"""Explicit, idempotent creation of login-disabled newcomer helper accounts."""
import json
import uuid
from ..config import ROOT
from ..policies.unit_progression import level_exp


def seed(api, config=None):
    entries=json.loads((config or ROOT/'config/newcomer-helpers.json').read_text(encoding='utf-8'))
    masters={r['id']:r for r in api.masters[10]['data_list']}
    if not isinstance(entries,list) or len({e['key'] for e in entries})!=len(entries):
        raise ValueError('Helper keys must be unique')
    for entry in entries:
        master=masters[entry['unit_id']]
        if master['lv_max']<70 or not isinstance(entry['name'],str) or not 1<=len(entry['name'])<=32:
            raise ValueError('Invalid high-level helper configuration')
    ids=[]
    with api.store.transaction():
        with api.store.connect() as db:
            states=[json.loads(row[0]) for row in db.execute('SELECT state FROM players')]
        existing={s['npc_helper_key']:s for s in states if 'npc_helper_key' in s}
        for entry in entries:
            if entry['key'] in existing:
                ids.append(existing[entry['key']]['player']['user_id']);continue
            state=api.store.create(dict(uuid=str(uuid.uuid4()),unit_no=0,user_name=entry['name']))
            master=masters[entry['unit_id']];level=master['lv_max']
            state['npc_helper_key']=entry['key']
            state['player'].update(rank=100,max_friend=1000000)
            unit=state['units'][0]
            unit.update(unit_id=entry['unit_id'],level=level,exp=level_exp(master,level))
            api.store.save(state);ids.append(state['player']['user_id'])
    return ids
