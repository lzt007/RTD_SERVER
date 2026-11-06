"""Entry-time original attributes and local reward bounds, outside the wire DTO."""
import copy
from ..common import ProtocolError


def reward_snapshot(api,state,enemies,party_ids,party_snapshot=None):
    masters={u['id']:u for u in api.masters[10]['data_list']}
    owned={u['instance_id']:u for u in state['units']}
    if party_snapshot is None:
        party_snapshot=[]
        for instance in (i for i in party_ids if i):
            unit=owned.get(instance);master=masters.get(unit['unit_id']) if unit else None
            if master is None:raise ProtocolError(8197,'Missing original party master for attribute rewards')
            party_snapshot.append(dict(instance_id=instance,unit_id=unit['unit_id'],
                attribute=master['attribute'],max_attribute_exp=master['max_attribute_exp']))
    enemy_masters={e['id']:e for e in api.masters[20]['data_list']}
    limits={str(i):0 for i in range(1,6)}
    for enemy in enemies:
        amount=enemy.get('add_attribute_exp',0)
        if type(amount) is not int or not 0<=amount<=999999:
            raise ProtocolError(8197,'Invalid ordered attribute reward')
        if not enemy['flag'] or not amount:continue
        master=enemy_masters.get(enemy['enemy_set_id'])
        if master is None:raise ProtocolError(8197,'Missing ordered enemy attribute')
        if master['type'] in (20,21):continue
        attribute=str(master['attribute'])
        if attribute not in limits:raise ProtocolError(8197,'Unsupported ordered enemy attribute')
        limits[attribute]=min(999999,limits[attribute]+amount)
    return dict(party=copy.deepcopy(party_snapshot),limits=limits)


FIELDS=('attribute_exp_none','attribute_exp_fire','attribute_exp_water','attribute_exp_shine','attribute_exp_dark')


def apply_rewards(state,entry):
    reported={str(i):entry.get(field,0) for i,field in enumerate(FIELDS,1)}
    if any(type(value) is not int or not 0<=value<=999999 for value in reported.values()):
        raise ProtocolError(8194,'Invalid attribute experience result')
    # Existing zero-reward runs retain their established settlement semantics,
    # including ordinary quest challenge checks based on the entry party.
    if not any(reported.values()):return
    context=state.get('battle_attribute_rewards')
    if not isinstance(context,dict):raise ProtocolError(8197,'Missing frozen attribute reward context')
    limits=context.get('limits');party=context.get('party')
    if (not isinstance(limits,dict) or set(limits)!=set(reported)
            or any(type(v) is not int or not 0<=v<=999999 for v in limits.values())
            or not isinstance(party,list) or not 3<=len(party)<=5):
        raise ProtocolError(8197,'Invalid frozen attribute reward context')
    if any(reported[key]>limits[key] for key in reported):
        raise ProtocolError(8194,'Attribute experience exceeds ordered encounters')
    expected=[i for i in state.get('battle_party_instance_ids',[]) if i]
    if len(expected)!=len(party) or any(not isinstance(row,dict) for row in party) or [r.get('instance_id') for r in party]!=expected:
        raise ProtocolError(8197,'Attribute reward party differs from entry')
    owned={u['instance_id']:u for u in state['units']};updates=[];total=sum(reported.values())
    for row in party:
        unit=owned.get(row['instance_id']);attribute=row.get('attribute');cap=row.get('max_attribute_exp')
        if unit is None or unit['unit_id']!=row.get('unit_id'):
            raise ProtocolError(8198,'Attribute reward recipient changed after entry')
        if (type(attribute) is not int or attribute not in range(1,6)
                or type(cap) is not int or cap<0
                or type(unit.get('attribute_exp')) is not int or unit['attribute_exp']<0):
            raise ProtocolError(8197,'Invalid original unit attribute experience')
        # Preserve legacy progress already over a changed original table cap.
        value=max(unit['attribute_exp'],min(cap,unit['attribute_exp']+total+reported[str(attribute)]))
        updates.append((unit,value))
    for unit,value in updates:unit['attribute_exp']=value
