"""Bounded unit sale with original coin and master-defined stamina rewards."""
import hashlib
import time

from ..common import ProtocolError, compact
from ..policies.instance_ids import remember_instance_ids


def sale_unit(self, state, req, token, operation):
    ids = req.get('unit_instance_id')
    if (not isinstance(ids,list) or not 1 <= len(ids) <= 10
            or any(type(n) is not int or n <= 0 for n in ids)
            or len(ids) != len(set(ids))):
        raise ProtocolError(8194, 'Expected 1-10 unique positive unit instances')
    selected = set(ids)
    fingerprint = hashlib.sha256(compact(sorted(ids)).encode()).hexdigest()
    owned = {u['instance_id']:u for u in state['units']}
    receipts = state.get('unit_sale_receipts',{})
    if fingerprint in receipts:
        if selected & owned.keys():
            raise ProtocolError(8197, 'Sale receipt conflicts with current inventory')
        recovery = receipts[fingerprint]['recover_point']
    else:
        if not selected <= owned.keys():
            raise ProtocolError(8198, 'Unowned sale unit')
        protected = {n for group in state['party']['party'] for n in group['instanceIds'][:3]}
        if selected & protected or any(owned[n]['favorite'] for n in ids):
            raise ProtocolError(8197, 'Favorite or party main unit cannot be sold')
        masters = {m['id']:m for m in self.masters[10]['data_list']}
        price = 0
        recovery_points = 0
        for n in ids:
            unit = owned[n]
            master = masters.get(unit['unit_id'])
            if master is None or type(master['ap_rec_val']) is not int or master['ap_rec_val'] < 0:
                raise ProtocolError(8197, 'Unknown unit or invalid stamina sale value')
            price += master['sale']*unit['level']
            recovery_points += master['ap_rec_val']
        remember_instance_ids(state)
        state['units'] = [u for u in state['units'] if u['instance_id'] not in selected]
        for group in state['party']['party']:
            group['instanceIds'] = [0 if n in selected else n for n in group['instanceIds']]
        state['player']['game_money'] = min(9999999,state['player']['game_money']+price)
        player = state['player']
        recovery = min(recovery_points,max(0,player['max_action_point']-player['action_point']))
        if recovery:
            player['action_point'] += recovery
            if player['action_point'] == player['max_action_point']:
                player['action_point_recover'] = int(time.time())
        state.setdefault('unit_sale_receipts',{})[fingerprint] = dict(recover_point=recovery)
        self.store.save(state)
    player = state['player']
    return dict(code=4096,session_id=token,result=dict(action_point=player['action_point'],
        action_point_recover=player['action_point_recover'],recover_point=recovery))
