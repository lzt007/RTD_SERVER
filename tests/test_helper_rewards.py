"""Local helper reward policy on disposable API databases only."""
import concurrent.futures
import copy
import datetime as dt
import os
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.services.api import API
from rtd.services.battle_entry import HASH_TYPES
from rtd.common import ProtocolError

NOW=1793000000


class HelperRewardsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'helpers.sqlite3'
        clock=patch('time.time',return_value=NOW);self.clock=clock.start();self.addCleanup(clock.stop)
        dates=patch('rtd.policies.login_rewards.utc_today',return_value=dt.date(2026,10,26))
        self.dates=dates.start();self.addCleanup(dates.stop)
        env=patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'1'});env.start();self.addCleanup(env.stop)
        self.api=API(self.path);self.tokens=[]
        for i in range(3):
            key=str(uuid.uuid4())
            self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=i,user_name='Helper'+str(i)))
            self.tokens.append(self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id'])
            state=self.state(i);rank=self.api.masters[60]['data_list'][99]
            state['player'].update(rank=100,exp=rank['need_exp'],friend_point=100,max_unit=100)
            state['player']['quest_clear_flags'][0]|=4
            self.api.store.save(state)
        self.call('send_friend_request',friend_user_id=2)
        self.call('accept_friend_request',who=1,friend_user_id=[1])

    def state(self,who=0):return self.api.store.session(self.tokens[who])
    def both(self):return [self.state(),self.state(1)]
    def call(self,operation,who=0,api=None,**req):
        request=dict(ver='2.4.0',retry=0);request.update(req)
        return (api or self.api).call(operation,request,self.tokens[who])['result']

    def order(self,quest=11000,floor=0,helper=2,who=0,**changes):
        request=dict(quest_id=quest,floor=floor,resume_id=0,bonus_stamina=0,helper_user_id=helper,
                     token=str(uuid.uuid4()),level_data_hash=self.api.levels[quest]['hash'],
                     hashes={str(t):str(self.api.master_table(t)['hash']) for t in HASH_TYPES})
        request.update(changes);self.call('order_quest',who=who,**request);return request

    def entry(self,quest=11000):
        q=next(r for r in self.api.masters[30]['data_list'] if r['id']==quest)
        return dict(quest_id=quest,exp=q['reward_exp'],game_money=q['reward_money'],
                    yorisiro_exp=0,units=[],challenge_id_list=[])

    def clear(self,entries=None,who=0):
        request=dict(list=entries or [self.entry()],party_instance_id=self.state(who)['battle_party_instance_ids'])
        result=self.call('clear_quest2',who=who,**request);return request,result

    def open_layers(self):
        root=next(q for q in self.api.masters[30]['data_list'] if q['id']==20000)
        root['open_type_2']=root['open_type_3']=0
        drops=self.api.masters[22]['data_list'];known={r['id'] for r in drops}
        for q in self.api.masters[30]['data_list']:
            if q['id'] not in (20000,20100):continue
            table=next(t for t in self.api.masters[21]['data_list'] if t['id']==q['enemy_table_id'])
            for key,value in table.items():
                if key.endswith('_drop_id') and value not in known:
                    drops.append(dict(drops[0],id=value));known.add(value)

    def test_eligible_list_successful_clear_and_provider_login_once(self):
        self.assertFalse(self.call('get_helpers')[1]['friend_point'])
        before=self.both();self.order()
        self.assertEqual(self.state()['player']['friend_point'],100)
        self.assertEqual(self.state(1),before[1])
        _,result=self.clear()
        self.assertEqual(result[0]['user']['friend_point'],110)
        self.assertEqual(self.state()['player']['friend_point'],110)
        self.assertEqual(self.state(1)['player']['friend_point'],100)
        self.assertTrue(self.call('get_helpers')[1]['friend_point'])
        login=self.call('login',who=1)
        self.assertEqual((login['help_count'],login['received_friend_point'],login['friend_point']),(1,10,110))
        again=self.call('login',who=1,api=API(self.path))
        self.assertEqual((again['help_count'],again['received_friend_point'],again['friend_point']),(0,0,110))

    def test_retry_restart_and_different_guid_same_day_do_not_credit_twice(self):
        order=self.order();self.call('order_quest',**dict(order,retry=1))
        req,result=self.clear();after=self.both();self.api=API(self.path)
        self.assertEqual(self.call('clear_quest2',**dict(req,retry=1)),result)
        self.assertEqual(self.both(),after)
        self.order();self.clear()
        self.assertEqual(self.state()['player']['friend_point'],110)
        self.assertEqual(self.call('login',who=1)['help_count'],1)

    def test_entry_day_is_frozen_across_midnight_and_next_day_can_earn_again(self):
        self.order();self.clock.return_value=NOW+86400
        self.dates.return_value=dt.date(2026,10,27)
        self.clear();self.assertEqual(self.state()['player']['friend_point'],110)
        self.assertFalse(self.call('get_helpers')[1]['friend_point'])
        self.order();self.clear()
        self.assertEqual(self.state()['player']['friend_point'],120)
        login=self.call('login',who=1)
        self.assertEqual((login['help_count'],login['received_friend_point']),(2,20))

    def test_npc_legacy_order_and_abandonment_do_not_mint_points(self):
        self.order(helper=0);self.clear()
        self.assertEqual(self.state()['player']['friend_point'],100)
        self.order();s=self.state();s.pop('battle_helper_reward',None);self.api.store.save(s)
        self.clear();self.assertEqual(self.state()['player']['friend_point'],100)
        self.order();self.order(helper=0);self.clear()
        self.assertEqual(self.call('login',who=1)['received_friend_point'],0)

    def test_accepted_snapshot_survives_friend_removal_and_leader_change(self):
        order=self.order();peer=self.state(1);peer['units'][0]['level']=2;self.api.store.save(peer)
        self.call('delete_friend',friend_user_id=[2]);self.call('order_quest',**dict(order,retry=1))
        self.clear();self.assertEqual(self.state()['player']['friend_point'],110)
        self.assertEqual(self.call('login',who=1)['received_friend_point'],10)

    def test_full_and_overfull_balances_keep_history_and_discard_overflow(self):
        for who,balance in [(0,9996),(1,9998)]:
            s=self.state(who);s['player']['friend_point']=balance;self.api.store.save(s)
        self.order();self.clear();self.assertEqual(self.state()['player']['friend_point'],10000)
        r=self.call('login',who=1)
        self.assertEqual((r['help_count'],r['received_friend_point'],r['friend_point']),(1,2,10000))
        self.clock.return_value+=86400;self.dates.return_value+=dt.timedelta(days=1)
        for who in range(2):
            s=self.state(who);s['player']['friend_point']=10003;self.api.store.save(s)
        self.order();self.clear();r=self.call('login',who=1)
        self.assertEqual((r['help_count'],r['received_friend_point'],r['friend_point']),(1,0,10003))
        self.assertEqual(self.state()['player']['friend_point'],10003)

    def test_bonus_type10_is_frozen_only_for_eligible_borrower(self):
        s=self.state();s['login_reward_snapshot']=dict(bonus=dict(type=10,num=50));self.api.store.save(s)
        self.order();s=self.state();s['login_reward_snapshot']['bonus']=dict(type=10,num=100);self.api.store.save(s)
        self.clear();self.assertEqual(self.state()['player']['friend_point'],160)
        self.assertEqual(self.call('login',who=1)['received_friend_point'],10)
        self.order();self.clear();self.assertEqual(self.state()['player']['friend_point'],160)

    def test_provider_write_failure_rolls_back_reward_daily_receipt_and_battle(self):
        self.order();before=self.both();save=self.api.store.save
        def fail(s):
            save(s)
            if s['player']['user_id']==2:raise RuntimeError('provider write failure')
        with patch.object(self.api.store,'save',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'provider write failure'):self.clear()
        self.assertEqual(self.both(),before)
        self.clear();self.assertEqual(self.state()['player']['friend_point'],110)

    def test_login_daily_failure_does_not_consume_pending_or_change_balances(self):
        self.order();self.clear();before=self.both()
        with patch('rtd.services.accounts.daily',side_effect=RuntimeError('daily failure')):
            with self.assertRaisesRegex(RuntimeError,'daily failure'):self.call('login',who=1)
        self.assertEqual(self.both(),before)
        self.assertEqual(self.call('login',who=1)['received_friend_point'],10)

    def test_login_save_failure_after_consumption_rolls_back_claim_and_daily(self):
        self.order();self.clear();before=self.both();save=self.api.store.save
        def fail(s):
            save(s)
            if s['player']['user_id']==2 and 'helper_reward_pending' not in s:
                raise RuntimeError('after claim write')
        with patch.object(self.api.store,'save',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'after claim write'):self.call('login',who=1)
        self.assertEqual(self.both(),before)
        self.assertEqual(self.call('login',who=1)['received_friend_point'],10)

    def test_new_borrower_same_day_after_login_creates_a_new_claim(self):
        self.order();self.clear();self.assertEqual(self.call('login',who=1)['received_friend_point'],10)
        self.call('send_friend_request',who=2,friend_user_id=2)
        self.call('accept_friend_request',who=1,friend_user_id=[3])
        self.order(who=2);self.clear(who=2)
        r=self.call('login',who=1)
        self.assertEqual((r['help_count'],r['received_friend_point'],r['friend_point']),(1,10,120))

    def test_login_interleaved_with_clear_never_loses_pending_points(self):
        self.order();req=dict(list=[self.entry()],party_instance_id=self.state()['battle_party_instance_ids'])
        other=API(self.path)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            settled=pool.submit(self.call,'clear_quest2',**req)
            logged=pool.submit(self.call,'login',who=1,api=other)
            settled.result();first=logged.result()
        second=self.call('login',who=1)
        self.assertEqual(first['received_friend_point']+second['received_friend_point'],10)
        self.assertEqual(self.state(1)['player']['friend_point'],110)

    def test_missing_provider_rejects_clear_without_partial_reward(self):
        self.order()
        before=self.state()
        by_id=self.api.store.by_id
        with patch.object(self.api.store,'by_id',side_effect=lambda uid:None if uid==2 else by_id(uid)):
            with self.assertRaises(ProtocolError):self.clear()
        self.assertEqual(self.state(),before)

    def test_concurrent_clear_and_concurrent_login_each_credit_once(self):
        self.order();req=dict(list=[self.entry()],party_instance_id=self.state()['battle_party_instance_ids'])
        apis=[self.api,API(self.path)]
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda a:self.call('clear_quest2',api=a,**dict(req,retry=1)),apis))
        self.assertEqual(results[0],results[1]);self.assertEqual(self.state()['player']['friend_point'],110)
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda a:self.call('login',who=1,api=a),apis))
        self.assertEqual(sum(r['received_friend_point'] for r in results),10)
        self.assertEqual(self.state(1)['player']['friend_point'],110)

    def test_two_layers_one_reward_and_invalid_later_floor_rolls_back_both_accounts(self):
        self.open_layers();self.order(20000);self.order(20100,1)
        entries=[self.entry(20000),self.entry(20100)];bad=copy.deepcopy(entries);bad[1]['game_money']=10**9
        before=self.both()
        with self.assertRaises(ProtocolError):self.clear(bad)
        self.assertEqual(self.both(),before)
        _,result=self.clear(entries)
        self.assertEqual([r['user']['friend_point'] for r in result],[110,110])
        self.assertEqual(self.call('login',who=1)['received_friend_point'],10)

    def test_invalid_and_self_helpers_never_write_either_account(self):
        before=self.both()
        for uid in (1,999):
            with self.subTest(uid=uid),self.assertRaises(ProtocolError):self.order(helper=uid)
            self.assertEqual(self.both(),before)
        self.call('delete_friend',friend_user_id=[2]);before=self.both()
        with self.assertRaises(ProtocolError):self.order()
        self.assertEqual(self.both(),before)


if __name__=='__main__':unittest.main()
