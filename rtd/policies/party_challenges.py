"""Original party challenges use every accepted original party member."""
from ..common import ProtocolError
from .event_content import single_quests


def _party_masters(api,state):
    quest=next(q for q in api.masters[30]['data_list'] if q['id']==state['battle']['quest_id'])
    size=5 if quest['pt_num']==6 else 3
    ids=state.get('battle_party_unit_ids')
    helper=state.get('battle_helper',{}).get('unit_id')
    # Legacy/multilayer runs without this single-floor snapshot are not evidence
    # of an attribute challenge. In particular, never fall back to evolved units.
    if (state['battle']['quest_id'] not in single_quests(api)
            or not isinstance(ids,list) or not 3<=len(ids)<=size
            or any(type(i) is not int or i<=0 for i in ids)
            or type(helper) is not int or helper<=0):
        raise ProtocolError(8197,'Party challenge requires the original party snapshot')
    masters={u['id']:u for u in api.masters[10]['data_list']}
    if any(i not in masters for i in ids+[helper]):
        raise ProtocolError(8197,'Party challenge unit master is unavailable')
    return [masters[i] for i in ids+[helper]]


def require_party_attribute(api,state,attribute):
    if any(unit['attribute']!=attribute for unit in _party_masters(api,state)):
        raise ProtocolError(8194,'Party including helper does not satisfy the attribute challenge')


def require_party_rarity(api,state,category):
    # Original UNIT_RARITY requires equality, not a maximum star rating.
    if any(unit['category']!=category for unit in _party_masters(api,state)):
        raise ProtocolError(8194,'Party including helper does not satisfy the rarity challenge')


def require_party_units(api,state,required):
    # Original UNIT_ID checks each nonzero param against all four party members.
    present={unit['id'] for unit in _party_masters(api,state)}
    if any(unit_id and unit_id not in present for unit_id in required):
        raise ProtocolError(8194,'Party including helper lacks a required original unit')


def require_party_style(api,state,style):
    # Original BattleChallengeData compares UNIT_MASTER.style, including helper.
    if any(unit['style']!=style for unit in _party_masters(api,state)):
        raise ProtocolError(8194,'Party including helper does not satisfy the weapon challenge')
