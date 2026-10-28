"""Original special-compose counters and cost, persisted with consumed-material receipts."""
import hashlib
from ..common import ProtocolError,compact
from ..policies.instance_ids import remember_instance_ids

BONUS_FIELDS={20:'bonus_life',30:'bonus_attack',40:'bonus_heal',50:'bonus_limit'}


def sp_compose_unit(api,state,req,token,operation):
    dst=req.get('dst_unit_instance_id');src=req.get('src_unit_instance_id')
    if any(type(n) is not int or n<=0 for n in (dst,src)) or dst==src:
        raise ProtocolError(8194,'Expected distinct target and single material instance IDs')
    key=hashlib.sha256(compact([dst,src]).encode()).hexdigest()
    owned={u['instance_id']:u for u in state['units']}
    if key in state.get('special_compose_receipts',{}):
        if src in owned:raise ProtocolError(8197,'Special compose receipt conflicts with inventory')
        return dict(code=4096,session_id=token,result=[])
    if dst not in owned or src not in owned:raise ProtocolError(8198,'Unowned target or material')
    masters={m['id']:m for m in api.masters[10]['data_list']}
    base=owned[dst];material=owned[src];master=masters[base['unit_id']]
    kind=masters[material['unit_id']]['material_type']
    protected={n for group in state['party']['party'] for n in group['instanceIds'][:3]}
    if master['material_type']!=0 or kind not in BONUS_FIELDS or src in protected or material['favorite']:
        raise ProtocolError(8197,'Ineligible or protected special-compose material/target')
    counters=[base[k] for k in ('bonus_life','bonus_attack','bonus_heal','bonus_limit')]
    if any(type(n) is not int or n<0 for n in counters):raise ProtocolError(8197,'Invalid bonus counters')
    total=sum(counters[:3]);maximum=master['bonus_limit_base']+base['bonus_limit']
    if kind!=50 and total>=maximum:raise ProtocolError(8197,'Special bonus capacity reached')
    price=(total+1)*25000
    if type(state['player']['game_money']) is not int or state['player']['game_money']<price:
        raise ProtocolError(8197,'Not enough special-compose coins')
    remember_instance_ids(state)
    base[BONUS_FIELDS[kind]]+=1
    state['player']['game_money']-=price
    state['units']=[u for u in state['units'] if u['instance_id']!=src]
    for group in state['party']['party']:
        group['instanceIds']=[0 if n==src else n for n in group['instanceIds']]
    state.setdefault('special_compose_receipts',{})[key]=dict(material=src,kind=kind,cost=price)
    api.store.save(state)
    return dict(code=4096,session_id=token,result=[])
