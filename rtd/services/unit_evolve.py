"""Ordinary and attribute-selected ultimate evolution with durable material receipts."""
import hashlib

from ..common import ProtocolError, compact
from ..policies.instance_ids import remember_instance_ids
from ..policies.unit_progression import evo_points


def evolve_unit(self,state,req,token,operation):
    dst=req.get('dst_unit_instance_id');ids=req.get('src_unit_instance_id');point=req.get('add_point')
    ultimate=operation=='ultimate_evolve'
    attribute=req.get('ultimate_evolve_attribute') if ultimate else None
    branches={2:'fire',3:'water',4:'shine',5:'dark'}
    if ultimate and (type(attribute) is not int or attribute not in branches):
        raise ProtocolError(8194,'Expected ultimate attribute 2, 3, 4 or 5')
    if (type(dst) is not int or dst<=0 or (not ultimate and (type(point) is not int or point<=0))
            or not isinstance(ids,list) or not 1<=len(ids)<=4
            or any(type(n) is not int or n<=0 for n in ids)
            or len(set(ids))!=len(ids) or dst in ids):
        raise ProtocolError(8194,'Expected target, positive point and 1-4 unique materials')
    fingerprint=hashlib.sha256(compact(['ultimate',dst,sorted(ids),attribute] if ultimate else
                                      [dst,sorted(ids),point]).encode()).hexdigest()
    owned={u['instance_id']:u for u in state['units']}
    if fingerprint in state.get('unit_evolve_receipts',{}):
        if set(ids)&owned.keys():
            raise ProtocolError(8197,'Evolution receipt conflicts with current inventory')
    else:
        if dst not in owned or not set(ids)<=owned.keys():
            raise ProtocolError(8198,'Unowned evolve target or material')
        protected={n for g in state['party']['party'] for n in g['instanceIds'][:3]}
        if set(ids)&protected or any(owned[n]['favorite'] for n in ids):
            raise ProtocolError(8197,'Favorite or party main material cannot be consumed')
        masters={m['id']:m for m in self.masters[10]['data_list']}
        base=owned[dst];master=masters.get(base['unit_id'])
        if ultimate and master is not None:point=master['need_pt']
        target=master.get('ultimate_rev_unit_id_'+branches[attribute],0) if ultimate and master else master.get('rev_unit_id',0) if master else 0
        if (master is None or base['level']!=master['lv_max'] or master['need_pt']<=0
                or point!=master['need_pt'] or target not in masters or target==base['unit_id']
                or (ultimate and (type(base['attribute_exp']) is not int
                                  or base['attribute_exp']<master['max_attribute_exp']))):
            raise ProtocolError(8197,'Target is not ready for the selected evolution')
        total=0
        for n in ids:
            unit=owned[n];m=masters.get(unit['unit_id'])
            if (m is None or m['material_type']!=0 or m['set_pt']<0 or unit['level']<1
                    or any(unit[k] for k in ('bonus_life','bonus_attack','bonus_heal','bonus_limit','attribute_exp'))):
                raise ProtocolError(8197,'Special or bonus evolve material is unsupported')
            total+=evo_points(unit['level'],m['set_pt'])
        price=point*100
        if total<point or state['player']['game_money']<price:
            raise ProtocolError(8197,'Insufficient evolution points or coins')
        remember_instance_ids(state)
        before_type=base['unit_id']
        base.update(unit_id=target,level=1,exp=0,attribute_exp=0)
        state['player']['game_money']-=price
        state['units']=[u for u in state['units'] if u['instance_id'] not in ids]
        for group in state['party']['party']:
            group['instanceIds']=[0 if n in ids else n for n in group['instanceIds']]
        state.setdefault('unit_evolve_receipts',{})[fingerprint]=dict(from_unit=before_type,to_unit=base['unit_id'])
        self.store.save(state)
    return dict(code=4096,session_id=token,result=[])
