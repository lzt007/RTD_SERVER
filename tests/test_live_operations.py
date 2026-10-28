import copy
import pathlib
import tempfile
import unittest
import uuid
from rtd.common import ProtocolError
from rtd.services.api import API
from rtd.services.battle_entry import HASH_TYPES
from rtd.services.battle_generation import generate_enemies
from test_live_configuration import event


class LiveOperationsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'live.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Live'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        state=self.state();state['player']['quest_clear_flags'][0]|=4
        state['player']['friend_point']=3000;self.api.store.save(state)

    def state(self):return self.api.store.session(self.token)
    def call(self,op,**kw):return self.api.call(op,dict(ver='2.4.0',retry=0,**kw),self.token)
    def request(self):
        return dict(ver='2.4.0',retry=0,quest_id=11000,floor=0,resume_id=0,bonus_stamina=0,
            helper_user_id=0,token=str(uuid.uuid4()),level_data_hash=self.api.levels[11000]['hash'],
            hashes={str(t):str(self.api.masters[t]['hash']) for t in HASH_TYPES})

    def test_live_pool_replacement_close_retry_and_ten_independence(self):
        self.api.operations.update('gachas','10000',dict(entries=[dict(unit_id=10021,level=2,weight=7)]),'PATCH')
        unit=self.call('buy_gacha',gacha_id=10000)['result']['unit']
        self.assertEqual((unit['unit_id'],unit['level']),(10021,2))
        self.api.operations.update('gachas','10000',dict(enabled=False),'PATCH')
        before=self.state()
        with self.assertRaises(ProtocolError):self.call('buy_gacha',gacha_id=10000)
        self.assertEqual(self.state(),before)
        self.api=API(self.path)
        retry=self.api.call('buy_gacha',dict(ver='2.4.0',retry=1,gacha_id=10000),self.token)
        self.assertEqual(retry['result']['unit'],unit);self.assertEqual(self.state(),before)
        ten=self.call('buy_gacha_special',gacha_id=30000,tutorial_flag=False)['result']
        self.assertTrue(all(u['level']==1 for u in ten['gacha_units'][0]['gacha_unit']))
        self.api.operations.update('gachas','30000',dict(starts_at='2099-01-01T00:00:00Z'),'PATCH')
        before=self.state()
        with self.assertRaises(ProtocolError):self.call('buy_gacha_special',gacha_id=30000,tutorial_flag=False)
        self.assertEqual(self.state(),before)

    def test_closed_event_no_charge_and_existing_order_keeps_drop_snapshot(self):
        self.api.operations.update('events','local-11000',event(enabled=False))
        req=self.request();before=self.state()
        with self.assertRaises(ProtocolError):self.api.call('order_quest',req,self.token)
        self.assertEqual(self.state(),before)
        config=event()
        # Override every referenced table rule, including the boss; appearance is unchanged.
        config['quests'][0]['drops']=[dict(drop_data_id=id,no_drop_weight=0,
            entries=[dict(unit_id=10021,level_min=2,level_max=2,weight=1)])
            for id in self.api.operations.drop_ids(11000)]
        self.api.operations.update('events','local-11000',config)
        first=self.api.call('order_quest',req,self.token)
        self.assertTrue(all((e['drop_unit_id'],e['drop_unit_level'])==(10021,2)
            for e in first['result']['enemy_info_list'] if e['flag']))
        before=self.state()
        self.api.operations.update('events','local-11000',dict(enabled=False),'PATCH')
        self.api=API(self.path)
        self.assertEqual(self.api.call('order_quest',req,self.token),first)
        self.assertEqual(self.state(),before)
        with self.assertRaises(ProtocolError):self.api.call('order_quest',self.request(),self.token)
        self.assertEqual(self.state(),before)
        self.api.operations.update('events','local-11000',None,'DELETE')
        self.api.call('order_quest',self.request(),self.token)
        self.assertNotEqual(self.state()['battle_order_token'],req['token'])

    def test_weighted_override_empty_boundary_and_presence(self):
        table=next(t for t in self.api.masters[21]['data_list'] if t['id']==10000)
        table=dict(table,enemy1_rate=100)
        drops={d['id']:d for d in self.api.masters[22]['data_list']}
        rule=dict(no_drop_weight=3,entries=[dict(unit_id=10021,level_min=2,level_max=4,weight=2)])
        class Roll:
            def __init__(self,value):self.value=value
            def randint(self,lo,hi):return self.value if hi==5 else hi
        for roll,unit in ((1,10021),(2,10021),(3,0),(5,0)):
            result=generate_enemies(table,dict(map_data='01',width=1),drops,Roll(roll),
                drop_overrides={table['enemy1_drop_id']:rule})
            self.assertEqual(result[0]['drop_unit_id'],unit)
            self.assertEqual(result[0]['drop_unit_level'],4 if unit else 0)

    def test_closed_rare_pool_does_not_block_fixed_tutorial(self):
        self.api.operations.update('gachas','20000',dict(enabled=False),'PATCH')
        state=self.state();state['player']['quest_clear_flags'][0]|=2
        state['player'].update(free_paid_point=5,paid_point=0,total_paid_point=5);self.api.store.save(state)
        result=self.call('buy_gacha',gacha_id=20000,tutorial_flag=True)
        self.assertEqual(result['code'],4096)
        self.assertEqual(self.state()['player']['total_paid_point'],0)

    def test_closed_event_existing_clear_uses_saved_books_and_retry(self):
        config=event()
        config['quests'][0]['drops']=[dict(drop_data_id=id,no_drop_weight=0,
            entries=[dict(unit_id=10021,level_min=2,level_max=2,weight=1)])
            for id in self.api.operations.drop_ids(11000)]
        self.api.operations.update('events','local-11000',config)
        self.api.call('order_quest',self.request(),self.token)
        self.api.operations.update('events','local-11000',dict(enabled=False),'PATCH')
        req=dict(ver='2.4.0',retry=0,list=[dict(quest_id=11000,exp=50,game_money=500,
            yorisiro_exp=0,units=[dict(unit_id=10021,level=2)],challenge_id_list=[])],
            party_instance_id=[1001,1002,1003,0,0,0])
        result=self.api.call('clear_quest2',req,self.token)
        self.assertEqual(result['code'],4096)
        self.assertIsNone(self.state()['battle']);self.assertNotIn('battle_event',self.state())
        before=self.state();self.api=API(self.path)
        self.assertEqual(self.api.call('clear_quest2',dict(req,retry=1),self.token),result)
        self.assertEqual(self.state(),before)


if __name__=='__main__':unittest.main()
