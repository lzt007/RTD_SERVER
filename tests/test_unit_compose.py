"""Ordinary compose rules and transactional API, isolated from runtime saves."""
import concurrent.futures
import copy
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.common import ProtocolError
from rtd.services.api import API


class ComposeRulesTest(unittest.TestCase):
    def test_float_material_exp_orb_and_cumulative_level_cap(self):
        from rtd.policies.unit_progression import material_exp,compose_result
        master=dict(category=1,grow=20,cost=10,lv_max=5,mix=100)
        self.assertEqual(material_exp(dict(unit_id=10,level=2,exp=0),master),141)
        # Real master14100 at level51 differs by one if double math is used.
        self.assertEqual(material_exp(dict(unit_id=14100,level=51,exp=0),dict(mix=1400)),9998)
        self.assertEqual(material_exp(dict(unit_id=50000,level=1,exp=660),master),660)
        base=dict(unit_id=10,level=1,exp=0)
        materials=[dict(unit_id=10,level=2,exp=0),dict(unit_id=50000,level=1,exp=660)]
        self.assertEqual(compose_result(base,materials,{10:master,50000:master}),
                         dict(price=20,add_exp=801,level=5,exp=541))
        base.update(level=2,exp=104)
        self.assertEqual(compose_result(base,[dict(unit_id=50000,level=1,exp=0)],
            {10:master,50000:master}),dict(price=20,add_exp=0,level=3,exp=104))


class UnitComposeTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'test.sqlite3'
        self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Compose'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        s=self.state()
        for instance,unit_id,exp in ((1004,11030,0),(1005,50000,660),(1006,10020,0)):
            u=copy.deepcopy(s['units'][0])
            u.update(instance_id=instance,unit_id=unit_id,level=1,exp=exp,favorite=0)
            s['units'].append(u)
        s['player']['game_money']=10000
        s['party']['party'][0]['instanceIds'][3:]=[1004,1005]
        self.api.store.save(s)
        self.call('get_units')

    def state(self):
        return self.api.store.session(self.token)

    def call(self,operation,**req):
        return self.api.call(operation,dict(ver='2.4.0',retry=0,**req),self.token)

    def compose(self,sources=(1004,),dst=1006):
        return self.call('compose_unit',dst_unit_instance_id=dst,src_unit_instance_id=list(sources))

    def test_real_cost_exp_material_cleanup_collection_and_later_normal_compose(self):
        first=self.compose()
        self.assertEqual(first['result'],dict(add_exp=600,type=0))
        s=self.state();base=next(u for u in s['units'] if u['instance_id']==1006)
        self.assertEqual((base['level'],base['exp'],s['player']['game_money']),(5,600,9900))
        self.assertEqual(s['party']['party'][0]['instanceIds'][3:], [0,1005])
        self.assertIn(dict(unit_id=10020,status=100,level=5),s['unit_collection'])
        self.assertIn(dict(unit_id=11030,status=100,level=1),s['unit_collection'])
        second=self.compose((1005,))
        self.assertEqual(second['result'],dict(add_exp=660,type=0))
        after=self.state();base=next(u for u in after['units'] if u['instance_id']==1006)
        self.assertEqual((base['level'],base['exp'],after['player']['game_money']),(6,1260,9400))
        self.api=API(self.path)
        self.assertEqual(self.compose(),first)
        self.assertEqual(self.state(),after)

    def test_invalid_protected_insufficient_full_or_special_batch_rolls_back(self):
        for dst,src in ((True,[1004]),(99999,[1004]),(1006,None),(1006,[]),(1006,[True]),
                        (1006,[1004]*2),(1006,[1006]),(1006,[1004,99999]),(1006,[1001]),
                        (1006,list(range(1004,1011)))):
            before=self.state()
            with self.subTest(dst=dst,src=src),self.assertRaises(ProtocolError):
                self.call('compose_unit',dst_unit_instance_id=dst,src_unit_instance_id=src)
            self.assertEqual(self.state(),before)
        original=self.state()
        for change in ('favorite','main','money','maxlevel','special','bonus'):
            s=copy.deepcopy(original)
            if change=='favorite':s['units'][3]['favorite']=1
            if change=='main':s['party']['party'][3]['instanceIds'][1]=1004
            if change=='money':s['player']['game_money']=99
            if change=='maxlevel':s['units'][-1].update(level=15,exp=999999)
            if change=='special':
                s['units'][3]['unit_id']=next(m['id'] for m in self.api.masters[10]['data_list'] if m['material_type']!=0)
            if change=='bonus':s['units'][3]['bonus_life']=1
            self.api.store.save(s);self.call('get_units');before=self.state()
            with self.subTest(change=change),self.assertRaises(ProtocolError):self.compose()
            self.assertEqual(self.state(),before)
        self.api.store.save(original)

    def test_favorite_party_main_target_is_preserved_while_unprotected_material_is_consumed(self):
        s=self.state()
        s['units'][-1]['favorite']=1
        s['party']['party'][2]['instanceIds'][0]=1006
        self.api.store.save(s)
        self.compose()
        s=self.state();base=next(u for u in s['units'] if u['instance_id']==1006)
        self.assertEqual((base['favorite'],base['level'],base['exp']),(1,5,600))
        self.assertEqual(s['party']['party'][2]['instanceIds'][0],1006)

    def test_reordered_batch_concurrent_retry_and_save_fault_are_atomic(self):
        before=self.state();original=self.api.store.save
        def fail(state):
            original(state)
            raise RuntimeError('injected compose fault')
        with patch.object(self.api.store,'save',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'compose fault'):self.compose((1004,1005))
        self.assertEqual(self.state(),before)
        other=API(self.path)
        req=dict(ver='2.4.0',retry=1,dst_unit_instance_id=1006,src_unit_instance_id=[1004,1005])
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            fs=[pool.submit(api.call,'compose_unit',dict(req,src_unit_instance_id=ids),self.token)
                for api,ids in ((self.api,[1004,1005]),(other,[1005,1004]))]
            results=[f.result() for f in fs]
        self.assertEqual(results[0],results[1])
        self.assertEqual(self.state()['player']['game_money'],9800)
        after=self.state()
        with self.assertRaises(ProtocolError):self.compose((1004,1005),1002)
        self.assertEqual(self.state(),after)
