import copy
from ..policies.instance_ids import allocate_instance_ids
import hashlib
import time
import json
from ..common import ProtocolError, compact
from ..policies.stamina import spend
from ..config import ROOT, STARTERS
from ..policies.helpers import local_helper
from ..policies.helper_rewards import claimed
from .battle_entry import order_single_floor
from .battle_rewards import settle_single_floor
from ..policies.quest_content import SINGLE_QUESTS,available
from ..policies.quest_content import layer_quests
from .battle_layers import order_layer,settle_layers


def get_helpers(self, state, req, token, operation):
    from .social import profile
    rows=[local_helper(state['starter'])]
    for uid,relation in sorted(state.get('friend_links',{}).items(),key=lambda r:int(r[0])):
        if relation['status']!=0:continue
        peer=self.store.by_id(int(uid))
        if peer is None:continue
        row=profile(peer);row.pop('create_date');row.update(friend=True,friend_point=claimed(state,int(uid)))
        rows.append(row)
    return dict(code=4096, session_id=token, result=rows)

def get_quest_info(self, state, req, token, operation):
    player = state['player']
    result = [dict(row['battle'],quest_status=2) for row in state.get('battle_history',[])]+[state['battle']] if state.get('battle') else []
    return dict(code=4096, session_id=token, result=result)



def clear_quest(self, state, req, token, operation):
    player = state['player']
    entries = req.get('list')
    if operation=='clear_quest2' and isinstance(entries,list) and entries and (
            'battle_history' in state or any(isinstance(row,dict) and type(row.get('quest_id')) is int and row['quest_id'] in layer_quests(self) for row in entries)):
        return dict(code=4096,session_id=token,result=settle_layers(self,state,req))
    if (operation == 'clear_quest2' and isinstance(entries,list) and len(entries) == 1
            and isinstance(entries[0],dict) and type(entries[0].get('quest_id')) is int and entries[0]['quest_id'] in SINGLE_QUESTS):
        result = settle_single_floor(self,state,req,entries[0]['quest_id'])
    else:
        result = self.settle_tutorial(state, operation, req)
    return dict(code=4096, session_id=token, result=result)



def save_quest_new_flags(self, state, req, token, operation):
    player = state['player']
    quests = {q['id']:q for q in self.masters[30]['data_list']}
    for entry in req.get('flags', []):
        if entry.get('quest_id') not in quests or entry.get('flag') not in (0,1):
            raise ProtocolError(8194, 'Invalid quest new flag')
        flag=quests[entry['quest_id']]['flag_no']
        player['quest_new_flags'][flag//8] = (player['quest_new_flags'][flag//8] & ~(1 << (flag%8))) | (entry['flag'] << (flag%8))
    self.store.save(state)
    result = []
    return dict(code=4096, session_id=token, result=result)



def order_quest(self, state, req, token, operation):
    player = state['player']
    if str(req.get('quest_id')) in {str(id) for id in layer_quests(self)}:
        return order_layer(self,state,req,token,int(req['quest_id']))
    if str(req.get('quest_id')) in {str(id) for id in SINGLE_QUESTS}:
        if not available(self,int(req['quest_id'])):raise ProtocolError(8197,'Quest resources are not enabled')
        return order_single_floor(self, state, req, token, int(req['quest_id']))
    if str(req.get('quest_id')) != '10000' or req.get('floor', 0) != 0:
        raise ProtocolError(8197, 'Only tutorial quest 10000 is supported')
    battle = state.get('battle')
    if battle and battle['quest_id'] != 10000:
        raise ProtocolError(8197, 'Another quest is active')
    if not battle:
        if str(req.get('retry', 0)) != '0':
            previous = self.store.previous_order(player['user_id'], 10000)
            if previous:
                return dict(code=4096, session_id=token, result=previous)
        level = self.levels[10000]
        quest = next(q for q in self.masters[30]['data_list'] if q['id'] == 10000)
        table = next(t for t in self.masters[21]['data_list'] if t['id'] == quest['enemy_table_id'])
        enemies = []
        for index, cell in enumerate(bytes.fromhex(level['map_data'])):
            slot = cell & 31
            if not 1 <= slot <= 18:
                continue
            prefix = f'enemy{slot}'
            if table[prefix+'_rate'] != 100:
                raise ProtocolError(8197, 'Random enemy placement is not implemented')
            enemies.append(dict(enemy_id=table[prefix+'_id'], enemy_set_id=table[prefix+'_set_id'],
                x=index % level['width'], y=index // level['width'], flag=True,
                drop_data_id=table[prefix+'_drop_id'], drop_unit_id=0, drop_unit_level=0,
                sp_event_point=0, add_attribute_exp=0))
        # Boss lookup is enemy_id == 0 in BattleManager/DropManager.
        enemies.append(dict(enemy_id=0, enemy_set_id=table['boss_set_id'], x=0, y=0,
            flag=True, drop_data_id=table['boss_drop_id'], drop_unit_id=0,
            drop_unit_level=0, sp_event_point=0, add_attribute_exp=0))
        battle = dict(quest_id=10000, quest_status=1, quest_continue=0,
                      quest_challenge_state=[], enemy_info_list=enemies)
        cost = quest['stamina']
        if player['action_point'] < cost:
            raise ProtocolError(8197, 'Not enough stamina')
        spend(player, cost, time.time())
        state['battle'] = battle
        self.store.begin_run(state, dict(action_point=player['action_point'],
            action_point_recover=player['action_point_recover'], enemy_info_list=enemies))
        self.store.save(state)
    result = dict(action_point=player['action_point'],
                  action_point_recover=player['action_point_recover'],
                  enemy_info_list=battle['enemy_info_list'])
    return dict(code=4096, session_id=token, result=result)



def settle_tutorial(self, state, operation, req):
    # A receipt survives process restarts and response loss. Only a real
    # active quest can create one; a different submission cannot reuse it.
    quests = req.get('list') if operation == 'clear_quest2' else [req]
    if not isinstance(quests, list) or len(quests) != 1:
        raise ProtocolError(8194, 'Expected one tutorial settlement')
    entry = quests[0]
    canonical = [{k:v for k,v in q.items() if k not in ('ver','retry','retry_count')} for q in quests]
    legacy_fingerprint = hashlib.sha256(compact([operation, canonical]).encode()).hexdigest()
    fingerprint = hashlib.sha256(json.dumps([operation, canonical], sort_keys=True,
        ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()
    player_id = state['player']['user_id']
    retry = req.get('retry', 0)
    if state.get('battle') and str(retry) != '0':
        previous = self.store.previous_receipt(player_id, operation, fingerprint)
        if previous is not None:
            return previous
    if not state.get('battle'):
        previous = self.store.previous_receipt(player_id, operation, fingerprint)
        if previous is not None:
            return previous
        receipt = state.get('clear_receipt', {})
        if receipt.get('fingerprint') in (fingerprint, legacy_fingerprint):
            return receipt['result']
        raise ProtocolError(8197, 'No matching active quest')
    if int(entry.get('quest_id', 0)) != 10000 or state['battle']['quest_id'] != 10000:
        raise ProtocolError(8197, 'Only first tutorial settlement is supported')
    # Lazily import legacy active snapshots without adding fields to strict DTOs.
    run_id = self.store.begin_run(state, {})
    quest = next(q for q in self.masters[30]['data_list'] if q['id'] == 10000)
    for field, maximum in [('exp', quest['reward_exp_limit']), ('game_money',quest['reward_money_limit']), ('yorisiro_exp',1000000)]:
        if type(entry.get(field)) is not int or not 0 <= entry[field] <= maximum:
            raise ProtocolError(8194, 'Invalid quest reward: '+field)
    if entry.get('challenge_id_list') or entry.get('units'):
        raise ProtocolError(8197, 'Tutorial drops/challenges not recovered')
    player = state['player']
    if player['exp'] + entry['exp'] >= 100:
        raise ProtocolError(8197, 'Rank-up settlement is not implemented')
    player['exp'] += entry['exp']
    player['game_money'] += entry['game_money']
    flag = quest['flag_no']
    player['quest_clear_flags'][flag//8] |= 1 << (flag%8)
    player['quest_new_flags'][flag//8] |= 1 << (flag%8)
    self.tutorial_credit(state)
    instance = allocate_instance_ids(state,1)[0]
    unit = dict(instance_id=instance,user_id=player['user_id'],unit_id=50000,
                member_id=0,leader=0,level=1,exp=entry['yorisiro_exp'],
                bonus_life=0,bonus_attack=0,bonus_heal=0,bonus_limit=0,attribute_exp=0,favorite=0)
    state['units'].append(unit)
    user = {k:v for k,v in player.items() if k not in ('system_flag','payment_total')}
    result = dict(user=user,present_type=0,present_param=0,get_units=[],yorisiro_instance_id=instance)
    if operation == 'clear_quest2':
        result['present_param_1'] = 0
        result = [result]
    state['battle'] = None
    state['clear_receipt'] = dict(fingerprint=fingerprint,result=copy.deepcopy(result))
    self.store.finish_run(run_id, operation, fingerprint, result)
    self.store.save(state)
    return result

