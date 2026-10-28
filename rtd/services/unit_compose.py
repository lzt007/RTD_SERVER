"""Ordinary strengthening with durable material-set receipts."""
import copy
import hashlib

from ..common import ProtocolError, compact
from ..policies.instance_ids import remember_instance_ids
from ..policies.unit_progression import compose_result


def compose_unit(self, state, req, token, operation):
    dst=req.get('dst_unit_instance_id')
    ids=req.get('src_unit_instance_id')
    if (type(dst) is not int or dst<=0 or not isinstance(ids,list)
            or not 1<=len(ids)<=6 or any(type(n) is not int or n<=0 for n in ids)
            or len(set(ids))!=len(ids) or dst in ids):
        raise ProtocolError(8194, 'Expected destination and 1-6 unique material instances')
    fingerprint=hashlib.sha256(compact([dst,sorted(ids)]).encode()).hexdigest()
    owned={u['instance_id']:u for u in state['units']}
    receipts=state.get('unit_compose_receipts',{})
    if fingerprint in receipts:
        if set(ids)&owned.keys():
            raise ProtocolError(8197, 'Compose receipt conflicts with current inventory')
        result=copy.deepcopy(receipts[fingerprint])
    else:
        if dst not in owned or not set(ids)<=owned.keys():
            raise ProtocolError(8198, 'Unowned compose target or material')
        protected={n for g in state['party']['party'] for n in g['instanceIds'][:3]}
        if set(ids)&protected or any(owned[n]['favorite'] for n in ids):
            raise ProtocolError(8197, 'Favorite or party main material cannot be consumed')
        masters={m['id']:m for m in self.masters[10]['data_list']}
        base=owned[dst];master=masters.get(base['unit_id'])
        if (master is None or not 1<=master['category']<=6
                or not 1<=base['level']<master['lv_max'] or base['exp']<0):
            raise ProtocolError(8197, 'Unknown, invalid or maximum-level target')
        materials=[owned[n] for n in ids]
        for unit in materials:
            m=masters.get(unit['unit_id'])
            if (m is None or m['material_type']!=0 or unit['level']<1 or unit['exp']<0
                    or any(unit[k] for k in ('bonus_life','bonus_attack','bonus_heal','bonus_limit','attribute_exp'))):
                raise ProtocolError(8197, 'Special or bonus material compose is unsupported')
        outcome=compose_result(base,materials,masters)
        if state['player']['game_money']<outcome['price']:
            raise ProtocolError(8197, 'Insufficient compose coins')
        remember_instance_ids(state)
        state['player']['game_money']-=outcome['price']
        base.update(level=outcome['level'],exp=outcome['exp'])
        state['units']=[u for u in state['units'] if u['instance_id'] not in ids]
        for group in state['party']['party']:
            group['instanceIds']=[0 if n in ids else n for n in group['instanceIds']]
        result=dict(add_exp=outcome['add_exp'],type=0)
        state.setdefault('unit_compose_receipts',{})[fingerprint]=copy.deepcopy(result)
        self.store.save(state)
    return dict(code=4096,session_id=token,result=result)
