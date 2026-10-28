"""Ordinary evolution contracts; every fixture lives in a temporary database."""
import concurrent.futures
import copy
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.common import ProtocolError
from rtd.services.api import API


class EvolvePointsTest(unittest.TestCase):
    def test_original_level_and_set_point_formula(self):
        from rtd.policies.unit_progression import evo_points
        self.assertEqual(evo_points(1,15),15)
        self.assertEqual(evo_points(2,15),18)
        self.assertEqual(evo_points(4,25),40)


class UnitEvolveTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'test.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Evolve'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        s=self.state()
        s['units'][0].update(unit_id=10021,level=15,exp=0,favorite=1,attribute_exp=17,
            bonus_life=2,bonus_attack=3,bonus_heal=4,bonus_limit=5)
        for instance,unit_id in ((1004,11030),(1005,11030),(1006,10020)):
            u=copy.deepcopy(s['units'][1]);u.update(instance_id=instance,unit_id=unit_id,
                level=1,exp=0,member_id=0,favorite=0)
            s['units'].append(u)
        s['player']['game_money']=10000
        s['party']['party'][0]['instanceIds'][3:]=[1004,1006]
        self.api.store.save(s);self.call('get_units')

    def state(self):return self.api.store.session(self.token)

    def call(self,operation,**req):
        return self.api.call(operation,dict(ver='2.4.0',retry=0,**req),self.token)

    def evolve(self,**changes):
        req=dict(dst_unit_instance_id=1001,src_unit_instance_id=[1004,1005,1006],add_point=40)
        req.update(changes);return self.call('evolve_unit',**req)

    def test_same_instance_party_favorite_bonus_and_old_new_collection_survive(self):
        before=self.state();response=self.evolve()
        self.assertEqual(set(response),{'code','session_id','result'})
        self.assertEqual(response['result'],[])
        s=self.state();base=s['units'][0]
        self.assertEqual((base['instance_id'],base['unit_id'],base['level'],base['exp'],base['attribute_exp']),
                         (1001,11021,1,0,0))
        for key in ('member_id','favorite','bonus_life','bonus_attack','bonus_heal','bonus_limit'):
            self.assertEqual(base[key],before['units'][0][key])
        self.assertEqual(s['player']['game_money'],6000)
        self.assertEqual(len(s['units']),3)
        self.assertEqual(s['party']['party'][0]['instanceIds'],[1001,1002,1003,0,0])
        self.assertIn(dict(unit_id=10021,status=100,level=15),s['unit_collection'])
        self.assertIn(dict(unit_id=11021,status=100,level=1),s['unit_collection'])
        # A later change to the same retained instance must not be reverted.
        s['units'][0].update(level=2,exp=22)
        self.api.store.save(s);self.call('get_units');after=self.state()
        self.api=API(self.path)
        self.assertEqual(self.evolve(src_unit_instance_id=[1006,1004,1005]),response)
        self.assertEqual(self.state(),after)

    def test_invalid_identity_shape_points_or_protected_material_batch_rolls_back(self):
        for changes in (dict(dst_unit_instance_id=True),dict(dst_unit_instance_id=99999),
                        dict(src_unit_instance_id=None),dict(src_unit_instance_id=[]),
                        dict(src_unit_instance_id=[True]),dict(src_unit_instance_id=[1004,1004]),
                        dict(src_unit_instance_id=[1001]),dict(src_unit_instance_id=[1004,99999]),
                        dict(src_unit_instance_id=[1004,1002]),dict(src_unit_instance_id=[1004]),
                        dict(src_unit_instance_id=[1004,1005,1006,1007,1008]),
                        dict(add_point=True),dict(add_point=39),dict(add_point=45)):
            before=self.state()
            with self.subTest(changes=changes),self.assertRaises(ProtocolError):self.evolve(**changes)
            self.assertEqual(self.state(),before)
        original=self.state()
        for change in ('level','money','no_evo','favorite','other_main','special'):
            s=copy.deepcopy(original)
            if change=='level':s['units'][0]['level']=14
            if change=='money':s['player']['game_money']=3999
            if change=='no_evo':s['units'][0].update(unit_id=50000,level=1)
            if change=='favorite':s['units'][3]['favorite']=1
            if change=='other_main':s['party']['party'][3]['instanceIds'][1]=1004
            if change=='special':s['units'][3]['unit_id']=next(m['id'] for m in self.api.masters[10]['data_list'] if m['material_type']!=0)
            self.api.store.save(s);self.call('get_units');before=self.state()
            with self.subTest(change=change),self.assertRaises(ProtocolError):self.evolve()
            self.assertEqual(self.state(),before)

    def test_save_fault_and_two_store_retry_are_atomic(self):
        before=self.state();original=self.api.store.save
        def fail(state):
            original(state);raise RuntimeError('injected evolve fault')
        with patch.object(self.api.store,'save',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'evolve fault'):self.evolve()
        self.assertEqual(self.state(),before)
        other=API(self.path)
        req=dict(ver='2.4.0',retry=1,dst_unit_instance_id=1001,src_unit_instance_id=[1004,1005,1006],add_point=40)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            fs=[pool.submit(api.call,'evolve_unit',copy.deepcopy(req),self.token) for api in (self.api,other)]
            responses=[f.result() for f in fs]
        self.assertEqual(responses[0],responses[1])
        self.assertEqual(self.state()['player']['game_money'],6000)
        self.assertEqual(len(self.state()['units']),3)
