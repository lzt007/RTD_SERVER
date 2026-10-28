import concurrent.futures
import copy
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch
from rtd.common import ProtocolError
from rtd.services.api import API
from rtd.policies.unit_progression import evo_points,level_exp


class SpecialUnitsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'special.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4());self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Special'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        self.masters={m['id']:m for m in self.api.masters[10]['data_list']}
        s=self.state();s['player']['game_money']=1000000
        for id,unit in ((1004,15025),(1005,15026),(1006,15027)):
            material=copy.deepcopy(s['units'][0]);material.update(instance_id=id,unit_id=unit,level=1,exp=0,favorite=0)
            s['units'].append(material)
        self.api.store.save(s);self.api.call('get_units',dict(ver='2.4.0'),self.token)

    def state(self):return self.api.store.session(self.token)
    def call(self,op='sp_compose_unit',**changes):
        req=dict(ver='2.4.0',retry=0,dst_unit_instance_id=1001,src_unit_instance_id=1004)
        req.update(changes);return self.api.call(op,req,self.token)
    def ultimate_fixture(self):
        s=self.state();base=s['units'][0];m=self.masters[16500]
        base.update(unit_id=m['id'],level=m['lv_max'],exp=level_exp(m,m['lv_max']),
                    attribute_exp=m['max_attribute_exp'],bonus_life=1,bonus_limit=2,favorite=1)
        material=max((r for r in self.masters.values() if r['material_type']==0 and r['set_pt']>0),
                     key=lambda r:evo_points(r['lv_max'],r['set_pt']))
        s['units'][3].update(unit_id=material['id'],level=material['lv_max'],exp=level_exp(material,material['lv_max']))
        self.api.store.save(s);self.api.call('get_units',dict(ver='2.4.0'),self.token)
        self.assertGreaterEqual(evo_points(material['lv_max'],material['set_pt']),m['need_pt'])

    def test_special_bonus_exact_cost_metadata_and_restart_retry(self):
        before=self.state();result=self.call()
        self.assertEqual(result['result'],[])
        state=self.state();expected=copy.deepcopy(before['units'][0]);expected['bonus_life']+=1
        self.assertEqual(state['units'][0],expected)
        self.assertEqual(state['player']['game_money'],975000)
        self.assertNotIn(1004,[u['instance_id'] for u in state['units']])
        self.api=API(self.path);self.assertEqual(self.call(retry=1),result);self.assertEqual(self.state(),state)
        self.call(src_unit_instance_id=1005);self.call(src_unit_instance_id=1006)
        state=self.state();self.assertEqual(state['player']['game_money'],850000)
        self.assertEqual([state['units'][0][k] for k in ('bonus_life','bonus_attack','bonus_heal')],[1,1,1])

    def test_special_invalid_material_capacity_funds_and_protection(self):
        original=self.state()
        for reason in ('same','list','bool','owned','favorite','party','ordinary','cap','money'):
            s=copy.deepcopy(original);kw={}
            if reason=='same':kw['src_unit_instance_id']=1001
            if reason=='list':kw['src_unit_instance_id']=[1004]
            if reason=='bool':kw['src_unit_instance_id']=True
            if reason=='owned':kw['src_unit_instance_id']=9999
            if reason=='favorite':s['units'][3]['favorite']=1
            if reason=='party':s['party']['party'][3]['instanceIds'][0]=1004
            if reason=='ordinary':s['units'][3]['unit_id']=10000
            if reason=='cap':s['units'][0]['bonus_life']=self.masters[s['units'][0]['unit_id']]['bonus_limit_base']
            if reason=='money':s['player']['game_money']=24999
            self.api.store.save(s);self.api.call('get_units',dict(ver='2.4.0'),self.token);before=self.state()
            with self.subTest(reason=reason),self.assertRaises(ProtocolError):self.call(**kw)
            self.assertEqual(self.state(),before)

    def test_ultimate_mapping_preserves_identity_bonus_and_receipt(self):
        for attr,target in ((2,16501),(3,16502),(4,16503)):
            self.ultimate_fixture();before=self.state()
            result=self.call('ultimate_evolve',src_unit_instance_id=[1004],ultimate_evolve_attribute=attr)
            after=self.state();unit=after['units'][0]
            self.assertEqual((unit['unit_id'],unit['level'],unit['exp'],unit['attribute_exp']),(target,1,0,0))
            for field in ('instance_id','favorite','bonus_limit','bonus_life','member_id'):
                self.assertEqual(unit[field],before['units'][0][field])
            self.assertEqual(after['party'],before['party'])
            self.assertEqual(after['player']['game_money'],before['player']['game_money']-50000)
            self.api=API(self.path)
            self.assertEqual(self.call('ultimate_evolve',src_unit_instance_id=[1004],ultimate_evolve_attribute=attr,retry=1),result)
            self.assertEqual(self.state(),after)
            # Each branch uses a fresh disposable DB fixture state, not reused consumed IDs.
            if attr!=4:self.setUp()

    def test_ultimate_missing_attribute_wrong_branch_points_or_level_rejected(self):
        self.ultimate_fixture();original=self.state()
        for reason in ('branch','boolean','attribute','level','points','protected','shape'):
            s=copy.deepcopy(original);kw=dict(src_unit_instance_id=[1004],ultimate_evolve_attribute=2)
            if reason=='branch':kw['ultimate_evolve_attribute']=5
            if reason=='boolean':kw['ultimate_evolve_attribute']=True
            if reason=='attribute':s['units'][0]['attribute_exp']-=1
            if reason=='level':s['units'][0]['level']-=1
            if reason=='points':s['units'][3].update(unit_id=10000,level=1,exp=0)
            if reason=='protected':s['units'][3]['favorite']=1
            if reason=='shape':kw['src_unit_instance_id']=1004
            self.api.store.save(s);self.api.call('get_units',dict(ver='2.4.0'),self.token);before=self.state()
            with self.subTest(reason=reason),self.assertRaises(ProtocolError):self.call('ultimate_evolve',**kw)
            self.assertEqual(self.state(),before)

    def test_fault_and_concurrent_retry_never_double_consume(self):
        before=self.state();save=self.api.store.save
        def fault(state):save(state);raise RuntimeError('special fault')
        with patch.object(self.api.store,'save',side_effect=fault),self.assertRaises(RuntimeError):self.call()
        self.assertEqual(self.state(),before)
        other=API(self.path)
        def request(api):return api.call('sp_compose_unit',dict(ver='2.4.0',retry=1,
            dst_unit_instance_id=1001,src_unit_instance_id=1004),self.token)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results=list(executor.map(request,[self.api,other]))
        self.assertEqual(results[0],results[1]);self.assertEqual(self.state()['player']['game_money'],975000)


if __name__=='__main__':unittest.main()
