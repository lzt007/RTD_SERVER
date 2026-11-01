"""Bounded single-floor entry with explicit verified/experimental content gates."""
import uuid
import time
from ..common import ProtocolError
from ..operations.configuration import is_open
from ..policies.stamina import spend
from .battle_generation import generate_enemies
from ..policies.login_rewards import active_bonus
from ..policies.helpers import local_helper
from ..policies.helper_rewards import freeze
from ..policies.attribute_rewards import reward_snapshot
from ..policies.event_points import freeze as freeze_event_points
from .shop import number
from .social import helper_profile
from ..policies.quest_content import available,require_unlocked,ORDINARY_QUESTS

HASH_TYPES = (30,31,21,20,10,11,12,13,14,32,33,90,16,17)


def order_single_floor(api, state, req, session, quest_id):
    player = state['player']
    if not available(api,quest_id):raise ProtocolError(8197,'Quest is blocked by server configuration')
    quest=next(q for q in api.masters[30]['data_list'] if q['id']==quest_id)
    if quest_id==10001:
        if not player['quest_clear_flags'][0]&2:raise ProtocolError(9472,'Required tutorial is not complete')
    else:
        # Preserve the original prerequisite-before-hash error contract for new
        # orders. Only a matching already-admitted token skips fresh unlocks.
        try:accepted_token=str(uuid.UUID(req.get('token')))
        except (ValueError,TypeError,AttributeError):accepted_token=None
        current=state.get('battle')
        admitted=(current and current['quest_id']==quest_id and accepted_token is not None
            and accepted_token==state.get('battle_order_token') and not state.get('battle_history'))
        if not admitted:
            configured=api.operations.event_for_quest(quest_id)
            require_unlocked(api,state,quest,local_schedule=configured is not None)
    if (type(req.get('floor')) is not int or req['floor'] != 0
            or type(req.get('resume_id')) is not int or req['resume_id'] != 0
            or type(req.get('bonus_stamina')) is not int or req['bonus_stamina'] != 0):
        raise ProtocolError(9472, 'Unsupported floor, resume, bonus or helper')
    helper_id=number(req.get('helper_user_id'))
    try:
        order_token = str(uuid.UUID(req['token']))
    except (KeyError, ValueError, TypeError, AttributeError):
        raise ProtocolError(8194, 'Invalid order token')
    battle = state.get('battle')
    same_order=(battle and battle['quest_id']==quest_id
                and state.get('battle_order_token')==order_token
                and state.get('battle_helper',{}).get('user_id',0)==helper_id
                and not state.get('battle_history'))
    frozen=state.get('battle_master_hashes',{}) if same_order else {}
    hashes = req.get('hashes')
    level = api.levels[quest_id]
    if (not isinstance(hashes, dict) or set(hashes) != {str(t) for t in HASH_TYPES}
            or any(str(hashes[str(t)]) not in {str(api.master_table(t)['hash'])}|
                   ({str(frozen['30'])} if t==30 and '30' in frozen else set()) for t in HASH_TYPES)
            or str(req.get('level_data_hash')) != str(level['hash'])):
        raise ProtocolError(8209, 'Battle master data changed')
    if (order_token in state.get('completed_battle_order_tokens', [])
            or order_token in state.get('abandoned_battle_order_tokens', [])):
        raise ProtocolError(9472, 'Battle order is no longer active')
    replace = False
    if battle:
        if state.get('battle_order_token') == order_token:
            if battle['quest_id']!=quest_id or state.get('battle_history'):
                raise ProtocolError(9472,'Order identity differs from active root')
        else:
            if str(req.get('retry',0)) != '0':
                raise ProtocolError(9472, 'Conflicting retried battle order')
            replace = True
    if not battle or replace:
        event=api.operations.event_for_quest(quest_id)
        if event and not is_open(event[0]):raise ProtocolError(8197,'Local event is closed')
        if helper_id:
            helper=helper_profile(api,state,helper_id)
        else:helper=local_helper(state['starter'])
        if len(state['units']) > player['max_unit']:
            raise ProtocolError(9472, 'Unit inventory exceeds capacity')
        owned = {u['instance_id']:u for u in state['units']}
        party = state['party']['party'][state['party']['active']]['instanceIds'][:3]
        if len(party) != 3 or len(set(party)) != 3 or any(i not in owned for i in party):
            raise ProtocolError(9472, 'A complete three-unit party is required')
        quest = next(q for q in api.masters[30]['data_list'] if q['id'] == quest_id)
        if player['action_point'] < quest['stamina']:
            raise ProtocolError(9472, 'Not enough stamina')
        table = next(t for t in api.masters[21]['data_list'] if t['id'] == quest['enemy_table_id'])
        drops = {d['id']:d for d in api.masters[22]['data_list']}
        bonus = active_bonus(state)
        enemies = generate_enemies(table,level,drops,
            drop_attempts=2 if bonus['type']==7 and bonus['num']>0 else 1,
            drop_overrides={r['drop_data_id']:r for r in event[1]['drops']} if event else None,
            enemy_masters={e['id']:e for e in api.masters[20]['data_list']})
        attribute_rewards=reward_snapshot(api,state,enemies,party)
        if replace:
            # Local lifecycle policy: explicit fresh order retires an orphaned
            # tutorial. Validate/generate first; the request transaction rolls
            # back abandonment if any later write fails. No refund or reward.
            run_id = api.store.active_run(player['user_id'])
            if not run_id:
                raise ProtocolError(9472, 'Missing active battle run')
            api.store.abandon_run(run_id)
            state.setdefault('abandoned_battle_order_tokens', []).extend([state['battle_order_token']]+
                [row['order_token'] for row in state.pop('battle_history',[])])
            state.pop('battle_layer_event',None);state.pop('battle_master_hashes',None)
        state['battle'] = dict(quest_id=quest_id,quest_status=1,quest_continue=0,
                              quest_challenge_state=[],enemy_info_list=enemies)
        state['battle_order_token'] = order_token
        # Unrelated layer schedules can change the shared quest-table hash.
        # Only this accepted order may reuse it; other masters stay strict.
        state['battle_master_hashes']={str(t):str(hashes[str(t)]) for t in HASH_TYPES}
        if event:state['battle_event']=dict(id=event[0]['id'],name=event[0]['name'],revision=event[2])
        else:state.pop('battle_event',None)
        state['battle_login_bonus'] = bonus
        state['battle_helper'] = helper
        reward=freeze(state,helper,bonus)
        if reward is None:state.pop('battle_helper_reward',None)
        else:state['battle_helper_reward']=reward
        # RequestClearQuest2 carries six battle slots, unlike five saved-party slots.
        state['battle_party_instance_ids'] = list(party) + [0,0,0]
        state['battle_party_unit_ids'] = [owned[i]['unit_id'] for i in party]
        state['battle_attribute_rewards']=attribute_rewards
        state['battle_event_points']=freeze_event_points(quest,enemies,{r['sp_event_id'] for r in api.masters[34]['data_list']})
        spend(player, quest['stamina'], time.time())
        result = dict(action_point=player['action_point'],
                      action_point_recover=player['action_point_recover'],enemy_info_list=enemies)
        api.store.begin_run(state,result)
        api.store.save(state)
    if state.get('battle_helper',{}).get('user_id',0)!=helper_id:
        raise ProtocolError(9472,'Helper differs from active battle order')
    result = dict(action_point=player['action_point'],action_point_recover=player['action_point_recover'],
                  enemy_info_list=state['battle']['enemy_info_list'])
    return dict(code=4096,session_id=session,result=result)
