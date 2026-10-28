"""Transfer a present-enabled owned unit through a local friend's inbox."""
import copy
from ..common import ProtocolError
from ..policies.instance_ids import remember_instance_ids
from .shop import number
from .social import target
from .presents import issue


def send(api,state,req,token,operation):
    uid=number(req.get('friend_user_id'),True);instance=number(req.get('unit_instance_id'),True)
    key=str(instance);receipt=state.get('unit_gift_receipts',{}).get(key)
    if receipt:
        if receipt['target']!=uid:raise ProtocolError(8197,'Unit was already sent to another account')
        return dict(code=4096,session_id=token,result=[])
    other=target(api,state,uid)
    if state.get('friend_links',{}).get(str(uid),{}).get('status')!=0:
        raise ProtocolError(8198,'Only accepted local friends can receive units')
    unit=next((u for u in state['units'] if u['instance_id']==instance),None)
    if unit is None:raise ProtocolError(8198,'Unit is not owned')
    main={n for group in state['party']['party'] for n in group['instanceIds'][:3]}
    master=next((m for m in api.masters[10]['data_list'] if m['id']==unit['unit_id']),None)
    if (state.get('battle') or instance in main or unit['favorite'] or master is None
            or master['present']!=1 or sum(unit[k] for k in ('bonus_life','bonus_attack','bonus_heal'))!=0):
        raise ProtocolError(8197,'This unit cannot be sent as a present')
    gift=issue(other,4,unit['unit_id'],unit['level'],'LOCAL FRIEND UNIT')
    gift.update(send_user_id=state['player']['user_id'],send_user_name=state['player']['user_name'])
    other.setdefault('gift_unit_snapshots',{})[str(gift['serial_number'])]={k:unit[k] for k in
        ('unit_id','level','exp','attribute_exp','bonus_life','bonus_attack','bonus_heal','bonus_limit')}
    remember_instance_ids(state)
    state['units']=[u for u in state['units'] if u['instance_id']!=instance]
    for group in state['party']['party']:
        group['instanceIds']=[0 if n==instance else n for n in group['instanceIds']]
    state.setdefault('unit_gift_receipts',{})[key]=dict(target=uid,serial=gift['serial_number'])
    api.store.save(state);api.store.save(other)
    return dict(code=4096,session_id=token,result=[])
