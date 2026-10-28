"""Configured local draws on disposable funded accounts, not official rates."""
import concurrent.futures
import copy
import json
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch
from rtd.common import ProtocolError
from rtd.services.api import API


class GachaTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'gacha.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=3,user_name='Draw'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        self.player(friend_point=2000,free_paid_point=3,paid_point=4,total_paid_point=7)

    def state(self):return self.api.store.session(self.token)
    def player(self,**kw):
        s=self.state();s['player'].update(kw);self.api.store.save(s)
    def call(self,op='buy_gacha',api=None,**kw):
        req=dict(ver='2.4.0',retry=0);req.update(kw)
        return (api or self.api).call(op,req,self.token)
    def error(self,code,op='buy_gacha',**kw):
        before=copy.deepcopy(self.state())
        with self.assertRaises(ProtocolError) as e:self.call(op,**kw)
        self.assertEqual(e.exception.args[0],code);self.assertEqual(self.state(),before)

    def test_normal_identical_retry_zero_is_two_draws_with_monotonic_instances(self):
        a=self.call(gacha_id='10000')['result'];b=self.call(gacha_id='10000')['result']
        self.assertEqual((a['friend_point'],b['friend_point']),(1900,1800))
        self.assertEqual((a['unit']['instance_id'],b['unit']['instance_id']),(1004,1005))
        self.assertEqual(len(self.state()['units']),5)
        normal={10000,10021,10030,10033,11100,11102,11112,11133}
        self.assertIn(a['unit']['unit_id'],normal);self.assertNotIn('leader',a['unit'])
        self.assertEqual((a['unit']['level'],a['unit']['exp']),(1,0))
        self.assertTrue({a['unit']['unit_id'],b['unit']['unit_id']}<=
                        {r['unit_id'] for r in self.state()['unit_collection']})
        self.assertEqual(set(a)-{'unit'},set(b)-{'unit'})
        self.assertEqual(len(set(a)-{'unit'}),17)
        self.assertEqual(self.state()['player']['total_paid_point'],7)

    def test_rare_original_total_balance_field_and_free_paid_split(self):
        r=self.call(gacha_id='20000',tutorial_flag='False',paid_point='7')['result']
        self.assertIn(r['unit']['unit_id'],{20000,20010,20020,20030})
        self.assertEqual((r['free_paid_point'],r['paid_point'],r['total_paid_point']),(0,2,2))
        self.error(8197,gacha_id='20000',tutorial_flag=False,paid_point='7')
        self.error(8961,gacha_id='20000',tutorial_flag=False,paid_point='2')

    def test_ten_is_one_group_of_ten_original_kind_zero_units(self):
        r=self.call('buy_gacha_special',gacha_id=30000,tutorial_flag=False)['result']
        self.assertEqual(r['friend_point'],1000)
        self.assertEqual(len(r['gacha_units']),1)
        units=r['gacha_units'][0]['gacha_unit'];self.assertEqual(len(units),10)
        self.assertEqual([u['instance_id'] for u in units],list(range(1004,1014)))
        self.assertTrue(all(set(u)=={'kind','instance_id','user_id','unit_id','member_id','level','exp'}
                            and u['kind']==0 and u['level']==1 and u['exp']==0 for u in units))
        self.assertEqual(len(self.state()['units']),13)
        self.assertEqual(self.state()['unit_instance_high_water'],1013)

    def test_network_retry_restart_current_economy_and_changed_unit_never_redraws(self):
        self.error(8197,gacha_id='10000',retry='1')
        unit=self.call(gacha_id='10000')['result']['unit']
        self.player(friend_point=800,game_money=123)
        before=self.state()
        r=self.call(api=API(self.path),gacha_id='10000',retry='1')['result']
        self.assertEqual((r['friend_point'],r['game_money'],r['unit']),(800,123,unit))
        self.assertEqual(self.state(),before)
        s=self.state();s['units'][-1]['favorite']=1;self.api.store.save(s)
        self.error(8197,gacha_id=10000,retry=1)
        r=self.call(gacha_id=10000)['result']
        self.assertEqual(r['unit']['instance_id'],1005)

    def test_bad_request_capacity_funds_and_battle_do_not_partially_award(self):
        for value in (True,'010000','+10000','１００００',10000.0,None):
            with self.subTest(value=value):self.error(8194,gacha_id=value)
        self.error(8197,gacha_id=12345)
        self.error(8194,gacha_id=30000)
        self.error(8194,'buy_gacha_special',gacha_id=10000,tutorial_flag=False)
        self.error(8194,'buy_gacha_special',gacha_id=30000,tutorial_flag=True)
        self.error(8194,gacha_id=20000,tutorial_flag=1,paid_point=7)
        self.player(max_unit=12)
        self.error(9472,'buy_gacha_special',gacha_id=30000,tutorial_flag=False)
        self.player(friend_point=99)
        self.error(8961,gacha_id=10000)
        s=self.state();s['battle']=dict(quest_id=11000);self.api.store.save(s)
        self.error(8197,gacha_id=10000)

    def test_ten_fault_rolls_back_and_concurrent_network_retries_never_issue_more(self):
        before=self.state();save=self.api.store.save
        def fail(s):save(s);raise RuntimeError('after save')
        with patch.object(self.api.store,'save',side_effect=fail),self.assertRaises(RuntimeError):
            self.call('buy_gacha_special',gacha_id=30000,tutorial_flag=False)
        self.assertEqual(self.state(),before)
        first=self.call('buy_gacha_special',gacha_id=30000,tutorial_flag=False)
        before=self.state();other=API(self.path)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda api:self.call('buy_gacha_special',api=api,
                gacha_id=30000,tutorial_flag=False,retry=1),[self.api,other]))
        self.assertEqual(results,[first,first]);self.assertEqual(self.state(),before)

    def test_existing_tutorial_stays_fixed_and_has_its_own_receipt(self):
        self.player(free_paid_point=7,paid_point=0,total_paid_point=7)
        s=self.state();s['player']['quest_clear_flags'][0]|=2;self.api.store.save(s)
        r=self.call(gacha_id='20000',tutorial_flag='True')['result']
        self.assertEqual(r['unit']['unit_id'],20000)
        before=self.state()
        self.assertEqual(self.call(gacha_id='20000',tutorial_flag=True)['result'],r)
        self.assertEqual(self.state(),before)

    def test_config_rejects_invalid_rows_and_weighted_boundaries_are_exact(self):
        from rtd.policies.gacha_pools import load_pools,draw
        cfg=dict(version=1,normal=[dict(unit_id=10000,level=1,weight=1),
                                   dict(unit_id=10021,level=1,weight=3)],
                 rare=[dict(unit_id=20000,level=1,weight=1)])
        path=pathlib.Path(self.temp.name)/'pools.json';path.write_text(json.dumps(cfg),encoding='utf-8')
        pools,digest=load_pools(self.api.masters,path);self.assertEqual(len(digest),64)
        class Roll:
            def __init__(self,n):self.n=n
            def randint(self,lo,hi):
                assert (lo,hi)==(1,4);return self.n
        for roll,wanted in ((1,10000),(2,10021),(4,10021)):
            self.assertEqual(draw(pools['normal'],1,Roll(roll))[0]['unit_id'],wanted)
        for bad in (dict(unit_id=999999,level=1,weight=1),dict(unit_id=10000,level=0,weight=1),
                    dict(unit_id=10000,level=1,weight=True),dict(unit_id=10000,level=1,weight=0),
                    dict(unit_id=10000,level=1,weight=1,unknown=1)):
            with self.subTest(row=bad):
                modified=copy.deepcopy(cfg);modified['normal']=[bad]
                path.write_text(json.dumps(modified),encoding='utf-8')
                with self.assertRaises(ValueError):load_pools(self.api.masters,path)


if __name__=='__main__':unittest.main()
