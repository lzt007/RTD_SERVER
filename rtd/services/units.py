import copy
from ..common import ProtocolError, compact
from ..config import ROOT, STARTERS

def get_units(self, state, req, token, operation):
    player = state['player']
    result = dict(units=[{k:v for k,v in unit.items() if k != 'leader'}
                         for unit in state['units']], party=state['party'])
    return dict(code=4096, session_id=token, result=result)



def save_unit_favorite_flags(self, state, req, token, operation):
    player = state['player']
    owned = {u['instance_id']:u for u in state['units']}
    flags = req.get('flags')
    if not isinstance(flags,list) or len(flags)>len(owned):
        raise ProtocolError(8194, 'Expected bounded favorite flags')
    seen = set()
    for entry in flags:
        if (not isinstance(entry,dict) or set(entry)!={'instance_id','flag'}
                or type(entry['instance_id']) is not int or entry['instance_id'] not in owned
                or type(entry['flag']) is not int or entry['flag'] not in (0,1)
                or entry['instance_id'] in seen):
            raise ProtocolError(8194, 'Invalid favorite flag')
        seen.add(entry['instance_id'])
    for entry in flags:
        owned[entry['instance_id']]['favorite'] = entry['flag']
    # ComManager.GetUnits and SEND_FAVORITE use bit5 as the legacy-upload
    # marker. Without it the next boot overwrites server favorites locally.
    player['tutorial_flags'][0] |= 32
    self.store.save(state)
    return dict(code=4096, session_id=token)



def form_units(self, state, req, token, operation):
    player = state['player']
    party = req.get('party')
    if not isinstance(party, dict):
        raise ProtocolError(8194, 'Expected party object')
    groups = party.get('party')
    if not isinstance(groups, list) or not 1 <= len(groups) <= 5:
        raise ProtocolError(8194, 'Invalid party count')
    active = party.get('active')
    if type(active) is not int or not 0 <= active < len(groups):
        raise ProtocolError(8194, 'Invalid active party')
    owned = {u['instance_id'] for u in state['units']}
    for group in groups:
        slots = group.get('instanceIds') if isinstance(group, dict) else None
        if not isinstance(slots, list) or len(slots) != 5 or not slots[0]:
            raise ProtocolError(8194, 'Expected five slots and a leader')
        if any(type(n) is not int or (n != 0 and n not in owned) for n in slots):
            raise ProtocolError(8198, 'Unowned unit')
        nonzero = [n for n in slots if n]
        if len(nonzero) != len(set(nonzero)):
            raise ProtocolError(8194, 'Duplicate unit')
    state['party'] = copy.deepcopy(party)
    self.store.save(state)
    result = dict(party=state['party'])
    return dict(code=4096, session_id=token, result=result)



def save_local_flags(self, state, req, token, operation):
    player = state['player']
    flags = req.get('unit_collection_flags')
    if not isinstance(flags, list) or len(flags) > 65536 or any(type(n) is not int or not 0 <= n <= 255 for n in flags):
        raise ProtocolError(8194, 'Expected byte flags')
    state['unit_collection_flags'] = flags
    self.store.save(state)
    result = []
    return dict(code=4096, session_id=token, result=result)


