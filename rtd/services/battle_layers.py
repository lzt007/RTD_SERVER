"""One durable root run, explicit stairs, per-floor choices and atomic batch rewards."""
import copy
import hashlib
import json
import time
import uuid
from ..common import ProtocolError,compact
from ..operations.configuration import is_open
from ..policies.helpers import local_helper
from ..policies.helper_rewards import freeze
from ..policies.attribute_rewards import reward_snapshot
from ..policies.event_points import freeze as freeze_event_points
from ..policies.login_rewards import active_bonus
from ..policies.quest_content import available,require_unlocked,LAYER_ROOTS,layer_quests
from ..policies.stamina import spend
from .battle_entry import HASH_TYPES
from .battle_generation import generate_enemies
from .battle_rewards import settle_single_floor,complete_battle
from .shop import number
from .social import helper_profile


def snapshot(state):
    return copy.deepcopy(dict(battle=state['battle'],order_token=state['battle_order_token'],
        bonus=state['battle_login_bonus'],party=state['battle_party_instance_ids'],
        attribute_rewards=state.get('battle_attribute_rewards'),event_points=state.get('battle_event_points')))


def order_layer(api,state,req,session,quest_id):
    if not api.visual_recovery:
        raise ProtocolError(8197,'Layer content requires approved visual recovery')
    player=state['player'];floor=req.get('floor');helper_id=number(req.get('helper_user_id'))
    if (quest_id not in layer_quests(api) or not available(api,quest_id)):
        raise ProtocolError(8197,'Layer content is not enabled')
    if (type(floor) is not int or not 0<=floor<32 or type(req.get('resume_id')) is not int
            or req['resume_id']!=0 or type(req.get('bonus_stamina')) is not int or req['bonus_stamina']!=0):
        raise ProtocolError(9472,'Unsupported floor, resume or stamina bonus')
    hashes=req.get('hashes');level=api.levels[quest_id]
    active_hashes=state.get('battle_master_hashes',{}) if state.get('battle') and (floor>0 or state.get('battle_order_token')==req.get('token')) else {}
    if (not isinstance(hashes,dict) or set(hashes)!={str(t) for t in HASH_TYPES}
            or any(str(hashes[str(t)]) not in {str(api.master_table(t)['hash'])}|({str(active_hashes.get(str(t)))} if t==30 else set()) for t in HASH_TYPES)
            or str(req.get('level_data_hash'))!=str(level['hash'])):
        raise ProtocolError(8209,'Battle master data changed')
    try:order_token=str(uuid.UUID(req['token']))
    except (KeyError,ValueError,TypeError,AttributeError):raise ProtocolError(8194,'Invalid order token') from None
    history=state.get('battle_history',[]);battle=state.get('battle')
    retired=state.get('completed_battle_order_tokens',[])+state.get('abandoned_battle_order_tokens',[])
    if order_token in retired or any(row['order_token']==order_token for row in history):
        raise ProtocolError(9472,'Battle order is no longer the active floor')
    if battle and order_token==state.get('battle_order_token'):
        if floor!=len(history) or quest_id!=battle['quest_id'] or helper_id!=state['battle_helper']['user_id']:
            raise ProtocolError(9472,'Order identity differs from active floor')
        return dict(code=4096,session_id=session,result=dict(action_point=player['action_point'],
            action_point_recover=player['action_point_recover'],enemy_info_list=battle['enemy_info_list']))
    transition=floor>0
    if transition:
        if not battle or floor!=len(history)+1 or not api.store.active_run(player['user_id']):
            raise ProtocolError(9472,'Missing previous floor or invalid next floor')
        enemy_types={e['id']:e['type'] for e in api.masters[20]['data_list']}
        destinations={e['drop_data_id'] for e in battle['enemy_info_list'] if e['flag'] and enemy_types[e['enemy_set_id']]==20}
        if quest_id not in destinations:raise ProtocolError(9472,'No ordered stairs lead to this quest')
        helper=state['battle_helper'];bonus=state['battle_login_bonus'];party=state['battle_party_instance_ids']
        if helper_id!=helper['user_id']:raise ProtocolError(9472,'Helper differs from root order')
        current_party=state['party']['party'][state['party']['active']]['instanceIds'][:3]+[0,0,0]
        if current_party!=party:raise ProtocolError(9472,'Party differs from root order')
        count=battle['quest_continue']
    else:
        if quest_id not in LAYER_ROOTS:raise ProtocolError(9472,'Hidden child quest cannot start a root run')
        if battle and str(req.get('retry',0))!='0':raise ProtocolError(9472,'Conflicting retried root order')
        quest=next(q for q in api.masters[30]['data_list'] if q['id']==quest_id)
        require_unlocked(api,state,quest,local_schedule=api.operations.event_for_quest(quest_id) is not None)
        if not player['quest_clear_flags'][0]&4:raise ProtocolError(9472,'Required tutorial is not complete')
        if len(state['units'])>player['max_unit']:raise ProtocolError(9472,'Unit inventory exceeds capacity')
        party=state['party']['party'][state['party']['active']]['instanceIds'][:3]+[0,0,0]
        owned={u['instance_id'] for u in state['units']}
        if len(set(party[:3]))!=3 or not set(party[:3])<=owned:raise ProtocolError(9472,'A complete party is required')
        if helper_id:
            helper=helper_profile(api,state,helper_id)
        else:helper=local_helper(state['starter'])
        if player['action_point']<quest['stamina']:raise ProtocolError(9472,'Not enough stamina')
        bonus=active_bonus(state);count=0
    if transition:
        saved_event=state.get('battle_layer_event')
        event=None
        if saved_event:
            row=next((q for q in saved_event[0]['quests'] if q['quest_id']==quest_id),None)
            if row is None:raise ProtocolError(8197,'Root event snapshot does not cover destination')
            event=(saved_event[0],row,saved_event[1])
    else:event=api.operations.event_for_quest(quest_id)
    if not transition and event and not is_open(event[0]):raise ProtocolError(8197,'Local event is closed')
    quest=next(q for q in api.masters[30]['data_list'] if q['id']==quest_id)
    table=next(t for t in api.masters[21]['data_list'] if t['id']==quest['enemy_table_id'])
    enemies=generate_enemies(table,level,{d['id']:d for d in api.masters[22]['data_list']},event_id=quest.get('sp_event_id',0),
        drop_attempts=2 if bonus['type']==7 and bonus['num']>0 else 1,
        drop_overrides={r['drop_data_id']:r for r in event[1]['drops']} if event else None,
        enemy_masters={e['id']:e for e in api.masters[20]['data_list']})
    prior=state.get('battle_attribute_rewards') if transition else None
    attribute_rewards=reward_snapshot(api,state,enemies,party,prior['party'] if prior else None)
    if transition:history.append(snapshot(state))
    else:
        if battle:
            run=api.store.active_run(player['user_id'])
            if not run:raise ProtocolError(9472,'Missing active root run')
            api.store.abandon_run(run)
            state.setdefault('abandoned_battle_order_tokens',[]).extend([state['battle_order_token']]+[row['order_token'] for row in history])
        history=[];spend(player,quest['stamina'],time.time())
        state['battle_master_hashes']=copy.deepcopy(hashes)
        if event:state['battle_layer_event']=[copy.deepcopy(event[0]),event[2]]
        else:state.pop('battle_layer_event',None)
    state['battle_history']=history
    state['battle']=dict(quest_id=quest_id,quest_status=1,quest_continue=count,quest_challenge_state=[],enemy_info_list=enemies)
    state.update(battle_order_token=order_token,battle_helper=helper,battle_login_bonus=bonus,battle_party_instance_ids=party)
    if not transition:
        reward=freeze(state,helper,bonus)
        if reward is None:state.pop('battle_helper_reward',None)
        else:state['battle_helper_reward']=reward
    state['battle_attribute_rewards']=attribute_rewards
    state['battle_event_points']=freeze_event_points(quest,enemies,{r['sp_event_id'] for r in api.masters[34]['data_list']})
    if event:state['battle_event']=dict(id=event[0]['id'],name=event[0]['name'],revision=event[2])
    else:state.pop('battle_event',None)
    result=dict(action_point=player['action_point'],action_point_recover=player['action_point_recover'],enemy_info_list=enemies)
    run=api.store.begin_run(state,result)
    with api.store.connect() as db:
        db.execute('UPDATE quest_runs SET snapshot=? WHERE run_id=?',
            (compact(dict(floors=[row['battle'] for row in history]+[state['battle']])),run))
    api.store.save(state)
    return dict(code=4096,session_id=session,result=result)


def settle_layers(api,state,req):
    entries=req.get('list');party=req.get('party_instance_id')
    if not isinstance(entries,list) or not entries or len(entries)>32 or any(not isinstance(row,dict) for row in entries):
        raise ProtocolError(8194,'Expected ordered layer result list')
    fingerprint=hashlib.sha256(json.dumps(dict(list=entries,party_instance_id=party),sort_keys=True,
        ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    previous=api.store.previous_receipt(state['player']['user_id'],'clear_quest2',fingerprint)
    if previous is not None:
        if not state.get('battle'):return previous
        if str(req.get('retry',0))!='0':raise ProtocolError(8197,'Ambiguous settlement retry with active run')
    if not state.get('battle') or 'battle_history' not in state:raise ProtocolError(9472,'No active layer chain')
    layers=state['battle_history']+[snapshot(state)]
    if len(entries)!=len(layers) or any(type(row.get('quest_id')) is not int or row['quest_id']!=layer['battle']['quest_id']
                                      for row,layer in zip(entries,layers)):
        raise ProtocolError(9472,'Result chain differs from ordered floors')
    result=[]
    for entry,layer in zip(entries,layers):
        state['battle']=copy.deepcopy(layer['battle']);state['battle_login_bonus']=layer['bonus']
        state['battle_party_instance_ids']=layer['party']
        if layer.get('attribute_rewards') is None:state.pop('battle_attribute_rewards',None)
        else:state['battle_attribute_rewards']=copy.deepcopy(layer['attribute_rewards'])
        if layer.get('event_points') is None:state.pop('battle_event_points',None)
        else:state['battle_event_points']=copy.deepcopy(layer['event_points'])
        result.extend(settle_single_floor(api,state,dict(list=[entry],party_instance_id=party),entry['quest_id'],layer=True))
    return complete_battle(api,state,result,fingerprint)
