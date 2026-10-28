"""Supported single-floor settlement with bounded validation, not battle replay."""
import copy
from ..policies.instance_ids import allocate_instance_ids
from ..policies.party_challenges import require_party_attribute,require_party_rarity,require_party_units
from ..policies.attribute_rewards import apply_rewards
from ..policies.event_points import apply as apply_event_points
from ..policies.helper_rewards import credit as credit_helper
import hashlib
import json
import time
from ..policies.unit_progression import level_exp as unit_acquisition_exp
from collections import Counter
from ..common import ProtocolError


def settle_single_floor(api, state, req, quest_id, *, layer=False):
    entries = req.get('list')
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        raise ProtocolError(8194, 'Expected one supported single-floor result')
    entry = entries[0]
    if type(entry.get('quest_id')) is not int or entry['quest_id'] != quest_id:
        raise ProtocolError(9472, 'Quest result does not match active supported quest')
    canonical = dict(list=entries, party_instance_id=req.get('party_instance_id'))
    fingerprint = hashlib.sha256(json.dumps(canonical, sort_keys=True,
        ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    player = state['player']
    previous = None if layer else api.store.previous_receipt(player['user_id'], 'clear_quest2', fingerprint)
    if previous is not None:
        if not state.get('battle'):
            return previous
        if str(req.get('retry', 0)) != '0':
            # No run id exists on the wire: an old delayed retry and a new
            # run whose initial packet was lost are indistinguishable.
            # Never acknowledge the new result using a stale success.
            raise ProtocolError(8197, 'Ambiguous settlement retry with active run')
    battle = state.get('battle')
    if not battle or battle['quest_id'] != quest_id:
        raise ProtocolError(9472, 'No matching active single-floor quest')
    quest = next(q for q in api.masters[30]['data_list'] if q['id'] == quest_id)
    challenges = entry.get('challenge_id_list')
    if (not isinstance(challenges,list) or any(type(c) is not int for c in challenges)
            or len(set(challenges)) != len(challenges)):
        raise ProtocolError(8194, 'Invalid challenge list')
    if quest_id == 10001 and challenges:
        raise ProtocolError(8197, 'Second-tutorial challenges are unsupported')
    if quest_id != 10001:
        allowed={quest[f'challenge_id_{i}'] for i in range(3)}-{0}
        if set(challenges)-allowed:
            raise ProtocolError(8197, 'Unsupported challenge')
        soul_values={s for s in range(100)
                     if int((s*quest['reward_soul'])**0.65)*15 == entry.get('yorisiro_exp')}
        # The wire contains no kill trace. Local client attestation is bounded
        # by available non-treasure encounters; this is not replay verification.
        enemy_types={e['id']:e['type'] for e in api.masters[20]['data_list']}
        possible=sum(e['flag'] and e['enemy_id']!=99 and enemy_types[e['enemy_set_id']]!=16
                     for e in battle['enemy_info_list'])
        challenge_masters={r['id']:r for r in api.masters[32]['data_list']}
        for id in challenges:
            condition=challenge_masters[id];kind=condition['type'];limit=condition['param_0']
            if kind==40:
                if battle['quest_continue']!=0:raise ProtocolError(8194,'No-continue challenge is not satisfied')
            elif kind==10:
                if not soul_values or min(soul_values)<limit:raise ProtocolError(8194,'Soul challenge is not satisfied')
            elif kind==31:
                if possible<limit:raise ProtocolError(8194,'Defeat challenge exceeds available encounters')
            elif kind==30:
                # Original grade selects the matching challenge slot's target
                # count. Wire has no kill trace: bound the client attestation
                # by present original targets, excluding treasure (type16).
                grade=condition['grade']
                target_possible=sum(e['flag'] and e['enemy_id']!=99
                    and e['enemy_set_id']==limit and enemy_types[e['enemy_set_id']]!=16
                    for e in battle['enemy_info_list'])
                if (grade not in range(3) or quest['challenge_id_'+str(grade)]!=id
                        or target_possible<condition['param_1']):
                    raise ProtocolError(8194,'Wanted challenge exceeds original target encounters')
            elif kind==20:
                require_party_units(api,state,[condition['param_'+str(i)] for i in range(4)])
            elif kind==23:
                require_party_attribute(api,state,limit)
            elif kind==21:
                require_party_rarity(api,state,limit)
            elif kind in (41,42):
                # Original wire has no damage/skill trace. These permitted IDs
                # are local client attestations, not authoritative combat replay.
                pass
            else:raise ProtocolError(8197,'Challenge condition is not implemented')
    bonus=state.get('battle_login_bonus',dict(type=0,num=0))
    expected_exp=min(quest['reward_exp_limit'],quest['reward_exp']+
                     (bonus['num'] if bonus['type']==9 else 0))
    minimum_money=min(quest['reward_money_limit'],quest['reward_money']+
                      (bonus['num'] if bonus['type']==8 else 0))
    if (type(entry.get('exp')) is not int or entry['exp'] != expected_exp
            or type(entry.get('game_money')) is not int
            or not minimum_money <= entry['game_money'] <= quest['reward_money_limit']
            or type(entry.get('yorisiro_exp')) is not int
            or entry['yorisiro_exp'] not in {int((s*quest['reward_soul'])**0.65)*15 for s in range(100)}):
        raise ProtocolError(8194, 'Reward outside supported tutorial bounds')
    party = req.get('party_instance_id')
    owned = {u['instance_id'] for u in state['units']}
    expected = state.get('battle_party_instance_ids',
                         state['party']['party'][state['party']['active']]['instanceIds'][:3]+[0,0,0])
    if (not isinstance(party,list) or party != expected
            or any(type(i) is not int or (i and i not in owned) for i in party)):
        raise ProtocolError(8198, 'Settlement party does not match order')
    books = entry.get('units')
    if not isinstance(books,list) or len(books) > 5 or any(not isinstance(b,dict)
            or set(b) != {'unit_id','level'} or type(b['unit_id']) is not int
            or type(b['level']) is not int for b in books):
        raise ProtocolError(8194, 'Invalid book list')
    available = Counter((e['drop_unit_id'],e['drop_unit_level'])
                        for e in battle['enemy_info_list'] if e['drop_unit_id'])
    selected = Counter((b['unit_id'],b['level']) for b in books)
    if selected - available:
        raise ProtocolError(8194, 'Books exceed ordered drop snapshot')
    apply_event_points(state,entry.get('sp_event_point',0),state.get('battle_event_points'),
                       {r['sp_event_id'] for r in api.masters[34]['data_list']})
    apply_rewards(state,entry)
    credit_helper(api,state)
    first = not player['quest_clear_flags'][quest['flag_no']//8] & (1 << (quest['flag_no']%8))
    player['exp'] += entry['exp']
    player['game_money'] += entry['game_money']
    for rank in api.masters[60]['data_list']:
        if rank['rank'] <= player['rank'] or rank['need_exp'] > player['exp']:
            continue
        if rank.get('unit_id'):
            raise ProtocolError(8197, 'Rank unit grants are unsupported')
        player['rank'] = rank['rank']
        player['game_money'] += rank['game_money']
        player['friend_point'] += rank['friend_point']
        player['max_action_point'] += bool(rank['flags'] & 1)
        player['max_friend'] += bool(rank['flags'] & 4)
        player['action_point'] = player['max_action_point']
        player['action_point_recover'] = int(time.time())
    flag = quest['flag_no']
    player['quest_clear_flags'][flag//8] |= 1 << (flag%8)
    player['quest_new_flags'][flag//8] |= 1 << (flag%8)
    if first and quest['present_type']:
        if quest['present_type'] != 3:
            raise ProtocolError(8197, 'Unsupported first-clear reward')
        player['free_paid_point'] += quest['present_param']
        player['total_paid_point'] += quest['present_param']
    for challenge in challenges:
        marker=dict(quest_id=quest_id,challenge_id=challenge,state=1)
        if marker not in player['quest_challenge_state']:
            player['quest_challenge_state'].append(marker)
    units = []
    unit_masters={u['id']:u for u in api.masters[10]['data_list']}
    instance_ids = allocate_instance_ids(state,len(books)+1)
    for index, (unit_id, level, exp) in enumerate(
            [(b['unit_id'],b['level'],unit_acquisition_exp(unit_masters[b['unit_id']],b['level']))
             for b in books]+[(50000,1,entry['yorisiro_exp'])]):
        unit = dict(instance_id=instance_ids[index],user_id=player['user_id'],unit_id=unit_id,
            member_id=0,leader=0,level=level,exp=exp,bonus_life=0,bonus_attack=0,
            bonus_heal=0,bonus_limit=0,attribute_exp=0,favorite=0)
        state['units'].append(unit)
        units.append({k:v for k,v in unit.items() if k != 'favorite'})
    result = [dict(user={k:v for k,v in player.items() if k not in ('system_flag','payment_total')},
        present_type=quest['present_type'] if first else 0,
        present_param=quest['present_param'] if first else 0,
        present_param_1=quest['present_param_1'] if first else 0,
        get_units=units,yorisiro_instance_id=units[-1]['instance_id'])]
    if layer:return result
    return complete_battle(api,state,result,fingerprint)


def complete_battle(api,state,result,fingerprint):
    player=state['player']
    run_id = api.store.active_run(player['user_id'])
    if not run_id:
        raise ProtocolError(9472, 'Missing active run')
    order_token = state.pop('battle_order_token', None)
    if order_token:
        state.setdefault('completed_battle_order_tokens', []).append(order_token)
    state.setdefault('completed_battle_order_tokens', []).extend(row['order_token'] for row in state.pop('battle_history',[]))
    state.pop('battle_party_instance_ids', None)
    state.pop('battle_party_unit_ids', None)
    state.pop('battle_attribute_rewards',None)
    state.pop('battle_event_points',None)
    state.pop('battle_login_bonus', None)
    state.pop('battle_helper', None)
    state.pop('battle_helper_reward',None)
    state.pop('battle_event', None)
    state.pop('battle_layer_event',None)
    state.pop('battle_master_hashes',None)
    state['battle'] = None
    api.store.finish_run(run_id,'clear_quest2',fingerprint,copy.deepcopy(result))
    api.store.save(state)
    return result
