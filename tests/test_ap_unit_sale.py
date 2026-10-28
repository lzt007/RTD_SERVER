"""Original 16028 stamina sale, exercised through the transactional public API."""
import concurrent.futures
import copy
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.common import ProtocolError
from rtd.services.api import API

NOW=2000000000


class ApUnitSaleTest(unittest.TestCase):
    def setUp(self):
        self.clock=patch('time.time',return_value=NOW);self.clock.start();self.addCleanup(self.clock.stop)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'sale.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='AP sale'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        state=self.state()
        for instance,unit,level in [(1004,16028,1),(1005,16028,1),(1006,11030,2)]:
            row=copy.deepcopy(state['units'][0]);row.update(instance_id=instance,unit_id=unit,level=level,exp=0,favorite=0)
            state['units'].append(row)
        state['player'].update(action_point=3,max_action_point=10,action_point_recover=NOW-100,game_money=100)
        state['party']['party'][0]['instanceIds'][3:]=[1004,1006]
        self.api.store.save(state);self.call('get_units')

    def state(self):return self.api.store.session(self.token)

    def call(self,operation,**req):
        return self.api.call(operation,dict(ver='2.4.0',retry=0,**req),self.token)

    def test_mixed_batch_restores_literal_master_points_money_and_clears_only_subslots(self):
        before=self.state();result=self.call('sale_unit',unit_instance_id=[1004,1006,1005])
        self.assertEqual(result['result'],dict(action_point=5,action_point_recover=NOW-100,recover_point=2))
        after=self.state()
        self.assertEqual(after['player']['game_money'],402)
        self.assertEqual([u['instance_id'] for u in after['units']],[1001,1002,1003])
        self.assertEqual(after['party']['party'][0]['instanceIds'],[1001,1002,1003,0,0])
        self.assertEqual(after['unit_collection'],before['unit_collection'])
        self.assertGreaterEqual(after['unit_instance_high_water'],1006)
        self.assertEqual(list(after['unit_sale_receipts'].values()),[dict(recover_point=2)])

    def test_full_near_full_and_existing_overflow_never_bank_or_lower_stamina(self):
        for current,want,grant,anchor in [(3,4,1,NOW-100),(9,10,1,NOW),(10,10,0,NOW-100),(12,12,0,NOW-100)]:
            with self.subTest(current=current):
                # Each case needs its own original live unit and untouched receipt.
                before=self.state();row=copy.deepcopy(before['units'][0]);instance=2000+current
                row.update(instance_id=instance,unit_id=16028,level=1,exp=0,favorite=0)
                before['units'].append(row)
                before['player'].update(action_point=current,action_point_recover=NOW-100)
                self.api.store.save(before)
                response=self.call('sale_unit',unit_instance_id=[instance])
                self.assertEqual(response['result'],dict(action_point=want,action_point_recover=anchor,recover_point=grant))

    def test_natural_tick_is_applied_before_bounded_sale_recovery(self):
        before=self.state();before['player'].update(action_point=9,action_point_recover=NOW-600)
        self.api.store.save(before)
        response=self.call('sale_unit',unit_instance_id=[1004])
        self.assertEqual(response['result'],dict(action_point=10,action_point_recover=NOW,recover_point=0))

    def test_reordered_restart_replay_returns_current_stamina_and_original_grant_without_adding(self):
        self.call('sale_unit',unit_instance_id=[1004,1005])
        state=self.state();state['player'].update(action_point=2,action_point_recover=NOW)
        self.api.store.save(state);self.api=API(self.path)
        for retry in [0,1]:
            result=self.api.call('sale_unit',dict(ver='2.4.0',retry=retry,unit_instance_id=[1005,1004]),self.token)
            self.assertEqual(result['result'],dict(action_point=2,action_point_recover=NOW,recover_point=2))
            self.assertEqual(self.state(),state)

    def test_two_api_instances_concurrent_sale_restores_and_pays_once(self):
        other=API(self.path);req=dict(ver='2.4.0',retry=1,unit_instance_id=[1004,1005])
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            futures=[pool.submit(api.call,'sale_unit',copy.deepcopy(req),self.token) for api in [self.api,other]]
            results=[f.result() for f in futures]
        self.assertEqual(results[0],results[1])
        self.assertEqual(results[0]['result']['recover_point'],2)
        state=self.state();self.assertEqual(state['player']['action_point'],5)
        self.assertEqual(state['player']['game_money'],102)
        self.assertEqual(len(state['unit_sale_receipts']),1)

    def test_invalid_mixed_batch_and_protected_special_unit_have_no_partial_effect(self):
        for ids,protected in [([1004,99999],False),([1004,1005],True)]:
            state=self.state()
            if protected:state['units'][-2]['favorite']=1;self.api.store.save(state)
            before=self.state()
            with self.assertRaises(ProtocolError):self.call('sale_unit',unit_instance_id=ids)
            self.assertEqual(self.state(),before)
        state=self.state();state['units'][-2]['favorite']=0
        state['party']['party'][2]['instanceIds'][1]=1004;self.api.store.save(state)
        before=self.state()
        with self.assertRaises(ProtocolError):self.call('sale_unit',unit_instance_id=[1004,1006])
        self.assertEqual(self.state(),before)

    def test_invalid_master_recovery_value_rejects_whole_batch(self):
        master=next(m for m in self.api.masters[10]['data_list'] if m['id']==16028)
        for bad in [-1,True,1.5]:
            with self.subTest(bad=bad):
                master['ap_rec_val']=bad;before=self.state()
                with self.assertRaises(ProtocolError):self.call('sale_unit',unit_instance_id=[1006,1004])
                self.assertEqual(self.state(),before)

    def test_failure_after_persisting_rolls_back_units_money_stamina_and_receipt(self):
        before=self.state();save=self.api.store.save
        def fail(state):save(state);raise RuntimeError('sale write fault')
        with patch.object(self.api.store,'save',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'sale write fault'):
                self.call('sale_unit',unit_instance_id=[1004,1006])
        self.assertEqual(self.state(),before)


if __name__=='__main__':unittest.main()
