"""Sale lifecycle on disposable accounts; the acceptance save is never used."""
import concurrent.futures
import copy
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.common import ProtocolError
from rtd.services.api import API


class UnitSaleTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = pathlib.Path(self.temp.name)/'test.sqlite3'
        self.api = API(self.path)
        self.key = str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=self.key,unit_no=0,user_name='Sale'))
        self.token = self.api.call('auth_user',dict(ver='2.4.0',uuid=self.key))['session_id']

    def call(self, operation, **req):
        return self.api.call(operation,dict(ver='2.4.0',retry=0,**req),self.token)

    def state(self):
        return self.api.store.session(self.token)

    def add_books(self):
        s = self.state()
        for instance,unit_id,level in ((1004,11030,2),(1005,11100,3)):
            u = copy.deepcopy(s['units'][0])
            u.update(instance_id=instance,unit_id=unit_id,level=level,favorite=0)
            s['units'].append(u)
        self.api.store.save(s)
        self.call('get_units')  # Observe acquisition before a future removal.

    def test_real_summon_uses_remembered_high_water_instead_of_reusing_sold_id(self):
        s = self.state()
        s['unit_instance_high_water'] = 9000
        s['player']['quest_clear_flags'][0] = 2
        s['player'].update(free_paid_point=5,total_paid_point=5)
        self.api.store.save(s)
        result = self.call('buy_gacha',gacha_id='20000',tutorial_flag=True)
        self.assertEqual(result['result']['unit']['instance_id'],9001)

    def test_sale_price_subslot_cleanup_library_and_restart_replay(self):
        self.add_books()
        s = self.state()
        s['party']['party'][0]['instanceIds'][3:] = [1004,1005]
        s['party']['party'][1]['instanceIds'][4] = 1005
        self.api.store.save(s)
        before = self.state()
        response = self.call('sale_unit',unit_instance_id=[1004,1005])
        self.assertEqual(set(response['result']),{'action_point','action_point_recover','recover_point'})
        self.assertEqual(response['result']['recover_point'],0)
        after = self.state()
        self.assertEqual(after['player']['game_money'],before['player']['game_money']+720)
        self.assertEqual([u['instance_id'] for u in after['units']],[1001,1002,1003])
        self.assertEqual(after['party']['party'][0]['instanceIds'],[1001,1002,1003,0,0])
        self.assertEqual(after['party']['party'][1]['instanceIds'][4],0)
        self.assertEqual(after['unit_collection'],before['unit_collection'])
        self.api = API(self.path)
        for retry in (0,1):
            req = dict(ver='2.4.0',retry=retry,unit_instance_id=[1005,1004])
            self.assertEqual(self.api.call('sale_unit',req,self.token),response)
            self.assertEqual(self.state(),after)

    def test_sold_highest_ids_are_not_reused_by_either_battle_reward_path(self):
        from rtd.services.battle_entry import HASH_TYPES
        self.add_books()
        self.call('sale_unit',unit_instance_id=[1004,1005])
        self.call('order_quest',quest_id='10000',floor=0)
        self.call('clear_quest2',list=[dict(quest_id=10000,exp=50,game_money=30000,
            yorisiro_exp=0,units=[],challenge_id_list=[])])
        self.assertEqual(self.state()['units'][-1]['instance_id'],1006)
        # Remove that reward via the real sale API before acquiring again.
        self.call('sale_unit',unit_instance_id=[1006])
        s = self.state()
        s['unit_instance_high_water'] = 9000
        self.api.store.save(s)
        self.call('order_quest',quest_id='10001',floor=0,helper_user_id='0',resume_id=0,
            bonus_stamina=0,token=str(uuid.uuid4()),level_data_hash='4081725474',
            hashes={str(t):str(self.api.masters[t]['hash']) for t in HASH_TYPES})
        self.call('clear_quest2',list=[dict(quest_id=10001,exp=50,game_money=500,
            yorisiro_exp=660,units=[dict(unit_id=10021,level=1)],challenge_id_list=[])],
            party_instance_id=[1001,1002,1003,0,0,0])
        self.assertEqual([u['instance_id'] for u in self.state()['units'][-2:]],[9001,9002])
        self.call('sale_unit',unit_instance_id=[1005,1004])
        self.assertEqual([u['instance_id'] for u in self.state()['units'][-2:]],[9001,9002])

    def test_coin_cap_special_ap_recovery_and_replay_returns_current_stamina(self):
        import time
        self.add_books()
        s = self.state()
        s['player']['game_money'] = 9999990
        self.api.store.save(s)
        self.call('sale_unit',unit_instance_id=[1004])
        self.assertEqual(self.state()['player']['game_money'],9999999)
        s = self.state()
        s['player'].update(action_point=3,action_point_recover=int(time.time()))
        self.api.store.save(s)
        replay = self.call('sale_unit',unit_instance_id=[1004])
        self.assertEqual(replay['result']['action_point'],3)
        special = next(m['id'] for m in self.api.masters[10]['data_list'] if m['ap_rec_val']>0)
        s = self.state()
        s['units'][-1]['unit_id'] = special
        self.api.store.save(s)
        self.call('get_units')
        before = self.state()
        sold=self.call('sale_unit',unit_instance_id=[1005])
        self.assertEqual(sold['result']['recover_point'],1)
        self.assertEqual(self.state()['player']['action_point'],before['player']['action_point']+1)
        self.assertEqual(self.state()['player']['game_money'],9999999)

    def test_invalid_mixed_batches_and_protected_units_never_change_state(self):
        self.add_books()
        s = self.state()
        s['units'][-1]['favorite'] = 1
        self.api.store.save(s)
        for ids in (None,{},'1004',[],[True],[1004,1004],[0],[-1],[1004,99999],
                    [1004,1005],[1004,1001],list(range(1004,1015))):
            with self.subTest(ids=ids):
                before = self.state()
                with self.assertRaises(ProtocolError):
                    self.call('sale_unit',unit_instance_id=ids)
                self.assertEqual(self.state(),before)
        # A main slot in any other party is protected too.
        s = self.state()
        s['party']['party'][2]['instanceIds'][1] = 1004
        self.api.store.save(s)
        before = self.state()
        with self.assertRaises(ProtocolError):
            self.call('sale_unit',unit_instance_id=[1004])
        self.assertEqual(self.state(),before)

    def test_failure_after_persisting_sale_rolls_back_and_concurrent_retry_pays_once(self):
        self.add_books()
        before = self.state()
        original = self.api.store.save
        def fail(state):
            original(state)
            raise RuntimeError('injected sale save fault')
        with patch.object(self.api.store,'save',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'sale save fault'):
                self.call('sale_unit',unit_instance_id=[1004])
        self.assertEqual(self.state(),before)
        other = API(self.path)
        req = dict(ver='2.4.0',retry=1,unit_instance_id=[1004])
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(api.call,'sale_unit',copy.deepcopy(req),self.token)
                       for api in (self.api,other)]
            results = [f.result() for f in futures]
        self.assertEqual(results[0],results[1])
        self.assertEqual(self.state()['player']['game_money'],300)
        self.assertEqual(len(self.state()['units']),4)


if __name__ == '__main__':
    unittest.main()
