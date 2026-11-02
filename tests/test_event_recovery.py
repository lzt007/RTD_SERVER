import copy
import unittest
from rtd.masters.catalog import load_catalog
from rtd.policies.event_content import audit_events

class EventRecoveryTest(unittest.TestCase):
    def test_daily_maps_are_admitted(self):
        masters, levels = load_catalog()
        accepted, rejected = audit_events(masters, levels)
        self.assertTrue(set(range(11999,12003)) <= accepted, rejected)
        self.assertEqual(len({11999+10*d+i for d in range(7) for i in range(4)}-accepted), 0)

    def test_registered_event_point_quests_are_admitted(self):
        masters, levels=load_catalog()
        masters=copy.deepcopy(masters)
        quest=next(q for q in masters[30]['data_list'] if q['id']==12000)
        quest['sp_event_id']=masters[34]['data_list'][0]['sp_event_id']
        accepted,rejected=audit_events(masters,levels)
        self.assertIn(12000,accepted)

    def test_missing_drop_is_rejected_without_mutating_catalog(self):
        masters, levels = load_catalog()
        masters=copy.deepcopy(masters)
        quest=next(q for q in masters[30]['data_list'] if q['id']==12000)
        table=next(t for t in masters[21]['data_list'] if t['id']==quest['enemy_table_id'])
        table['boss_drop_id']=2147483647
        accepted, rejected=audit_events(masters, levels)
        self.assertNotIn(12000,accepted)
        self.assertIn('drop',str(rejected[12000]))

import test_quest_content as fixtures
from unittest.mock import patch
from rtd.policies.quest_content import require_unlocked
from rtd.common import ProtocolError

class EventBattleTest(unittest.TestCase):
    def setUp(self):
        fixtures.QuestContentTest.setUp(self)
        # Protocol fixtures exercise all combat-complete events separately
        # from the production visual-resource admission gate.
        self.api.event_quests=audit_events(self.api.masters,self.api.levels)[0]
    state=fixtures.QuestContentTest.state
    request=fixtures.QuestContentTest.request
    clear=fixtures.QuestContentTest.clear
    def test_every_admitted_event_orders_and_settles(self):
        quests={q['id']:q for q in self.api.masters[30]['data_list']}
        for id in sorted(self.api.event_quests):
            with self.subTest(quest=id):
                state=self.state()
                state['player']['action_point']=999
                state['player']['max_unit']=9999
                state['player']['quest_clear_flags']=[255]*len(state['player']['quest_clear_flags'])
                quest=quests[id];flag=quest['flag_no']
                state['player']['quest_clear_flags'][flag//8] &= ~(1<<(flag%8))
                self.api.store.save(state)
                # Exercise combat independently of original weekday/expired windows.
                with patch('rtd.services.battle_entry.require_unlocked'):
                    result=self.api.call('order_quest',self.request(id),self.token)
                self.assertEqual(result['code'],4096)
                drops=[dict(unit_id=e['drop_unit_id'],level=e['drop_unit_level'])
                    for e in self.state()['battle']['enemy_info_list'] if e['drop_unit_id']][:5]
                before=len(self.state()['units'])
                receipt=self.clear(id,units=drops)
                self.assertEqual(len(self.state()['units']),before+len(drops)+1)
                self.assertEqual(receipt['code'],4096)
                self.assertIsNone(self.state()['battle'])

    def test_order_stop_is_closed(self):
        quest=dict(next(q for q in self.api.masters[30]['data_list'] if q['id']==12000))
        for i in range(1,7):quest[f'open_type_{i}']=0
        quest.update(open_type_1=6,open_param_1=1)
        with self.assertRaisesRegex(ProtocolError,'stopped'):
            require_unlocked(self.api,self.state(),quest)

    def test_daily_weekday_and_prerequisite_are_enforced(self):
        quest=next(q for q in self.api.masters[30]['data_list'] if q['id']==12000)
        state=self.state();state['player']['quest_clear_flags']=[0]*len(state['player']['quest_clear_flags'])
        with self.assertRaisesRegex(ProtocolError,'Required quest'):
            require_unlocked(self.api,state,quest)
        target=dict(quest)
        for i in range(1,7):target[f'open_type_{i}']=0
        target.update(open_type_1=1,open_param_1=99)
        with self.assertRaisesRegex(ProtocolError,'weekday'):
            require_unlocked(self.api,self.state(),target)

    def test_daily_order_and_settlement_retries_do_not_duplicate_rewards(self):
        req=self.request(12000)
        with patch('rtd.services.battle_entry.require_unlocked'):
            first=self.api.call('order_quest',req,self.token)
            self.assertEqual(first,self.api.call('order_quest',req,self.token))
        party=self.state()['battle_party_instance_ids']
        quest=next(q for q in self.api.masters[30]['data_list'] if q['id']==12000)
        req=dict(ver='2.4.0',retry=0,list=[dict(quest_id=12000,exp=quest['reward_exp'],
            game_money=quest['reward_money'],yorisiro_exp=0,units=[],challenge_id_list=[])],party_instance_id=party)
        result=self.api.call('clear_quest2',req,self.token);state=self.state()
        req['retry']=1
        self.assertEqual(result,self.api.call('clear_quest2',req,self.token))
        self.assertEqual(state,self.state())

    def test_cleared_and_not_clear_conditions(self):
        quest=dict(next(q for q in self.api.masters[30]['data_list'] if q['id']==12000))
        for i in range(1,7):quest[f'open_type_{i}']=0
        quest.update(open_type_1=7,open_param_1=0)
        state=self.state()
        with self.assertRaisesRegex(ProtocolError,'already be cleared'):
            require_unlocked(self.api,state,quest)
        flag=quest['flag_no'];state['player']['quest_clear_flags'][flag//8]|=1<<(flag%8)
        require_unlocked(self.api,state,quest)
        quest.update(open_type_1=9,open_param_1=12000)
        with self.assertRaisesRegex(ProtocolError,'closed after'):
            require_unlocked(self.api,state,quest)
        state['player']['quest_clear_flags'][flag//8]&=~(1<<(flag%8))
        require_unlocked(self.api,state,quest)

    def test_daily_first_clear_drops_and_challenge(self):
        quest=next(q for q in self.api.masters[30]['data_list'] if q['id']==12000)
        before=self.state()['player']['total_paid_point']
        with patch('rtd.services.battle_entry.require_unlocked'), patch('rtd.services.battle_generation.secrets.SystemRandom') as random:
            random.return_value.randint.side_effect=lambda low,high:low
            self.api.call('order_quest',self.request(12000),self.token)
        drops=[dict(unit_id=e['drop_unit_id'],level=e['drop_unit_level'])
            for e in self.state()['battle']['enemy_info_list'] if e['drop_unit_id']][:5]
        self.assertTrue(drops)
        self.clear(12000,[5003],units=drops)
        self.assertEqual(self.state()['player']['total_paid_point'],before+quest['present_param'])
        self.assertIn(dict(quest_id=12000,challenge_id=5003,state=1),self.state()['player']['quest_challenge_state'])

    def test_daily_continue_is_supported_and_idempotent(self):
        state=self.state();state['player'].update(free_paid_point=3,paid_point=0,total_paid_point=3)
        self.api.store.save(state)
        with patch('rtd.services.battle_entry.require_unlocked'):
            self.api.call('order_quest',self.request(12000),self.token)
        req=dict(ver='2.4.0',floor=0,quest_continue=1,retry=0)
        first=self.api.call('continue_quest',req,self.token)
        self.assertEqual(self.state()['player']['total_paid_point'],2)
        self.assertEqual(self.api.call('continue_quest',req,self.token),first)

class EventAssetTest(unittest.TestCase):
    def test_missing_visual_resources_remain_excluded(self):
        from rtd.policies.event_content import recovered_asset_names
        from rtd.policies.visual_recovery import apply_visual_recovery
        masters,levels=load_catalog();apply_visual_recovery(masters)
        accepted,rejected=audit_events(masters,levels,recovered_asset_names())
        self.assertIn(12001,accepted)
        self.assertNotIn(12000,accepted)
        self.assertTrue(any('missing model' in r for r in rejected[12000]))

class EventSceneTest(unittest.TestCase):
    def test_missing_scene_stays_closed_even_when_enemy_assets_exist(self):
        from rtd.policies.event_content import recovered_asset_manifest,recovered_asset_names
        from rtd.policies.visual_recovery import apply_visual_recovery
        from rtd.policies.event_visuals import apply_event_visuals
        masters,levels=load_catalog();apply_visual_recovery(masters);apply_event_visuals(masters,levels)
        manifest=recovered_asset_manifest();manifest['map_ids']=[]
        with patch('rtd.policies.event_content.recovered_asset_manifest',return_value=manifest):
            accepted,rejected=audit_events(masters,levels,recovered_asset_names())
        self.assertNotIn(12000,accepted)
        self.assertTrue(any('map scene' in r for r in rejected[12000]))

class EventVisualRecoveryTest(unittest.TestCase):
    def test_substitutions_preserve_every_gameplay_field(self):
        from rtd.policies.event_visuals import apply_event_visuals
        from rtd.policies.event_content import recovered_asset_names
        from rtd.policies.visual_recovery import apply_visual_recovery
        masters,levels=load_catalog();apply_visual_recovery(masters)
        before=copy.deepcopy(masters[20]['data_list'])
        changes=apply_event_visuals(masters,levels)
        self.assertTrue(changes)
        for original,updated in zip(before,masters[20]['data_list']):
            self.assertEqual({k:v for k,v in original.items() if k not in ('model','texture')},
                             {k:v for k,v in updated.items() if k not in ('model','texture')})
        accepted,rejected=audit_events(masters,levels,recovered_asset_names())
        self.assertTrue({11999,12000,12001,12002}<=accepted)
        self.assertEqual(len(accepted),len(audit_events(masters,levels)[0]))
