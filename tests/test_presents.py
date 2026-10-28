"""Challenge-to-inbox and atomic claim contracts on disposable accounts."""
import concurrent.futures
import copy
import datetime as dt
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.common import ProtocolError
from rtd.services.api import API


class PresentsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'test.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=3,user_name='Gifts'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']

    def call(self,op,**req):
        return self.api.call(op,dict(ver='2.4.0',retry=0,**req),self.token)

    def state(self):return self.api.store.session(self.token)

    def gifts(self,items):
        s=self.state();s['presents']=[dict(serial_number=n,send_user_id=0,
            send_user_name='LOCAL',message='Test',present_type=t,present_param_0=p,
            present_param_1=l,date='2026-10-25T00:00:00+00:00',open_limit=0)
            for n,t,p,l in items];self.api.store.save(s)

    def medals(self):
        s=self.state();s['player']['quest_challenge_state']=[
            dict(quest_id=11000,challenge_id=n,state=1) for n in (10,11,12)]
        self.api.store.save(s)

    def test_challenge_issues_once_then_claims_original_unit_dto_and_library(self):
        self.medals()
        response=self.call('post_quest_challenge_reward',reward_id=10)
        self.assertEqual(response['result'],dict(reward_id=10,present_type=4,
            present_param_0=15012,present_param_1=1))
        self.assertEqual(len(self.state()['units']),3)
        first=self.state();self.assertEqual(self.call('post_quest_challenge_reward',reward_id=10),response)
        self.assertEqual(self.state(),first)
        self.call('post_quest_challenge_reward',reward_id=11)
        inbox=self.call('get_presents')['result'];self.assertEqual(len(inbox),2)
        fields={'serial_number','send_user_id','send_user_name','message','present_type',
                'present_param_0','present_param_1','date','open_limit'}
        self.assertEqual(set(inbox[0]),fields)
        self.assertEqual([p['present_param_0'] for p in inbox],[15012,15013])
        self.assertTrue(all(p['open_limit']==0 for p in inbox))
        ids=[p['serial_number'] for p in inbox]
        out=self.call('open_present',serial_number_list=ids)['result']
        self.assertEqual(set(out),{'serial_number_list','user','get_units'})
        self.assertEqual(out['serial_number_list'],ids)
        self.assertEqual([u['unit_id'] for u in out['get_units']],[15012,15013])
        self.assertEqual([u['instance_id'] for u in out['get_units']],[1004,1005])
        self.assertTrue(all('leader' not in u and u['exp']==0 for u in out['get_units']))
        self.assertEqual(self.call('get_presents')['result'],[])
        self.assertEqual(len(self.state()['units']),5)
        self.assertTrue({15012,15013}<={r['unit_id'] for r in self.state()['unit_collection']})
        self.assertEqual(self.state()['player']['quest_challenge_reward_state'],[
            dict(reward_id=10,state=1),dict(reward_id=11,state=1)])

    def test_original_challenge_builder_sends_canonical_decimal_strings(self):
        self.medals()
        result=self.api.call('post_quest_challenge_reward',
            dict(ver='2.4.0',retry='0',reward_id='10'),self.token)
        self.assertEqual(result['code'],4096)
        before=self.state()
        self.assertEqual(self.call('post_quest_challenge_reward',reward_id=10),result)
        for value in ('0','01','-1','+10',' 10','10.0','1e1','１０'):
            with self.subTest(value=value),self.assertRaises(ProtocolError):
                self.call('post_quest_challenge_reward',reward_id=value)
        self.assertEqual(self.state(),before)

    def test_claim_currencies_caps_and_no_paid_credit(self):
        self.gifts([(1,1,200,0),(2,2,30,0),(3,3,2,0)])
        out=self.call('open_present',serial_number_list=[1,2,3])['result']
        self.assertEqual((out['user']['game_money'],out['user']['friend_point'],
            out['user']['free_paid_point'],out['user']['total_paid_point'],out['user']['paid_point']),
            (200,30,2,2,0))
        self.assertEqual(out['get_units'],[])
        self.assertEqual(set(out['user']),{'user_id','user_name','action_point',
            'action_point_recover','max_action_point','game_money','total_paid_point',
            'paid_point','free_paid_point','friend_point','rank','exp','max_unit',
            'max_cost','max_friend','login_days','sequence_login_days'})

    def test_invalid_batches_caps_capacity_and_expiry_do_not_partially_claim(self):
        for ids in (None,[],[True],[0],[-1],[1,1],[1,999],list(range(1,102))):
            self.gifts([(1,1,100,0)]);before=self.state()
            with self.subTest(ids=ids),self.assertRaises(ProtocolError):
                self.call('open_present',serial_number_list=ids)
            self.assertEqual(self.state(),before)
        for field,value,kind,param,level in (
            ('game_money',9999990,1,11,0),('friend_point',9999,2,2,0),
            ('total_paid_point',999,3,1,0),('max_unit',3,4,15012,1),
            ('game_money',0,5,1,0),('game_money',0,99,1,0),
            ('game_money',0,4,99999999,1),('game_money',0,4,15012,0)):
            self.gifts([(1,1,1,0),(2,kind,param,level)])
            s=self.state();s['player'][field]=value;self.api.store.save(s);before=self.state()
            with self.subTest(field=field,kind=kind),self.assertRaises(ProtocolError):
                self.call('open_present',serial_number_list=[1,2])
            self.assertEqual(self.state(),before)
        self.gifts([(1,1,100,0)]);s=self.state();s['presents'][0]['open_limit']=1
        self.api.store.save(s);start=dt.datetime(2026,10,25,tzinfo=dt.timezone.utc).timestamp()
        with patch('rtd.services.presents.time.time',return_value=start+7*86400):
            before=self.state();self.assertEqual(self.call('get_presents')['result'],[])
            with self.assertRaises(ProtocolError):self.call('open_present',serial_number_list=[1])
            self.assertEqual(self.state(),before)
        with patch('rtd.services.presents.time.time',return_value=start+7*86400-1):
            self.assertEqual(len(self.call('get_presents')['result']),1)
            self.call('open_present',serial_number_list=[1])

    def test_unearned_or_unconfigured_challenges_cannot_issue_rewards(self):
        for reward in (True,0,-1,99999999,10,11):
            s=self.state();s['player']['quest_challenge_state']=[
                dict(quest_id=11000,challenge_id=999,state=1),
                dict(quest_id=11001,challenge_id=10,state=0)]
            self.api.store.save(s);before=self.state()
            with self.subTest(reward=reward),self.assertRaises(ProtocolError):
                self.call('post_quest_challenge_reward',reward_id=reward)
            self.assertEqual(self.state(),before)
        s=self.state();s['player']['quest_challenge_state']=[
            dict(quest_id=11000,challenge_id=10,state=1)]*3;self.api.store.save(s)
        with self.assertRaises(ProtocolError):self.call('post_quest_challenge_reward',reward_id=11)

    def test_receipt_reorder_network_retry_restart_and_later_unit_progress(self):
        self.gifts([(1,1,100,0),(2,4,15012,1)])
        response=self.call('open_present',serial_number_list=[1,2])['result'];after=self.state()
        self.api=API(self.path)
        normal=self.call('open_present',serial_number_list=[2,1])['result']
        self.assertEqual(normal['get_units'],[]);self.assertEqual(self.state(),after)
        retry=self.api.call('open_present',dict(ver='2.4.0',retry=1,serial_number_list=[2,1]),self.token)['result']
        self.assertEqual(retry['get_units'],response['get_units']);self.assertEqual(self.state(),after)
        s=self.state();s['units'][-1].update(level=2,exp=22);s['player']['game_money']=500
        self.api.store.save(s);self.call('get_units');before=self.state()
        retry=self.api.call('open_present',dict(ver='2.4.0',retry=1,serial_number_list=[1,2]),self.token)['result']
        self.assertEqual(retry['get_units'],[]);self.assertEqual(retry['user']['game_money'],500)
        self.assertEqual(self.state(),before)
        self.gifts([(3,1,50,0)]);before=self.state()
        with self.assertRaises(ProtocolError):self.call('open_present',serial_number_list=[1,3])
        self.assertEqual(self.state(),before)

    def test_rollback_and_concurrent_claim_never_award_twice(self):
        self.gifts([(1,1,100,0),(2,4,15012,1)]);before=self.state();save=self.api.store.save
        def fail(s):save(s);raise RuntimeError('simulated storage failure')
        with patch.object(self.api.store,'save',side_effect=fail),self.assertRaises(RuntimeError):
            self.call('open_present',serial_number_list=[1,2])
        self.assertEqual(self.state(),before)
        peers=[API(self.path),API(self.path)]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            responses=list(pool.map(lambda a:a.call('open_present',dict(ver='2.4.0',retry=0,
                serial_number_list=[1,2]),self.token),peers))
        self.assertTrue(all(r['code']==4096 for r in responses))
        self.assertEqual(sum(len(r['result']['get_units']) for r in responses),1)
        self.assertEqual(self.state()['player']['game_money'],100)
        self.assertEqual(len(self.state()['units']),4)

    def test_currency_gift_is_claimable_while_existing_units_are_over_capacity(self):
        self.gifts([(1,1,100,0)])
        s=self.state();s['player']['max_unit']=2;self.api.store.save(s)
        self.assertEqual(self.call('open_present',serial_number_list=[1])['result']['user']['game_money'],100)
        self.assertEqual(len(self.state()['units']),3)

    def test_challenge_rollback_concurrency_cross_account_and_serial_high_water(self):
        self.medals();before=self.state();save=self.api.store.save
        def fail(s):save(s);raise RuntimeError('simulated issue failure')
        with patch.object(self.api.store,'save',side_effect=fail),self.assertRaises(RuntimeError):
            self.call('post_quest_challenge_reward',reward_id=10)
        self.assertEqual(self.state(),before)
        peers=[API(self.path),API(self.path)]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            rows=list(pool.map(lambda a:a.call('post_quest_challenge_reward',
                dict(ver='2.4.0',retry=0,reward_id=10),self.token),peers))
        self.assertTrue(all(r['code']==4096 for r in rows))
        gifts=self.call('get_presents')['result'];self.assertEqual(len(gifts),1)
        first=gifts[0]['serial_number']
        key=str(uuid.uuid4());self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Other'))
        other=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        with self.assertRaises(ProtocolError):
            self.api.call('open_present',dict(ver='2.4.0',retry=0,serial_number_list=[first]),other)
        self.assertEqual(self.call('get_presents')['result'],gifts)
        self.call('open_present',serial_number_list=[first])
        self.call('post_quest_challenge_reward',reward_id=11)
        self.assertGreater(self.call('get_presents')['result'][0]['serial_number'],first)
