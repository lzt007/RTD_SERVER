"""Daily rewards on disposable accounts with an isolated calendar clock."""
import concurrent.futures
import copy
import datetime as dt
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.services.api import API
from rtd.common import ProtocolError
from rtd.services.battle_entry import HASH_TYPES


class LoginRewardsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'test.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=3,user_name='Daily'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']

    def state(self):return self.api.store.session(self.token)

    def login(self,date,api=None):
        with patch('rtd.policies.login_rewards.utc_today',return_value=dt.date.fromisoformat(date)):
            return (api or self.api).call('login',dict(ver='2.4.0',retry=0),self.token)['result']

    def test_daily_calendar_gift_once_across_restart_and_concurrent_login(self):
        with patch('rtd.policies.login_rewards.utc_today',return_value=dt.date(2026,1,25)):
            other=API(self.path)
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                results=list(pool.map(lambda api:api.call('login',dict(ver='2.4.0'),self.token)['result'],[self.api,other]))
        self.assertTrue(all(r['login_days']==1 and r['login_bonus'] for r in results))
        self.assertEqual(results[0]['sequence_login_bonus'],dict(type=1,num=1000))
        s=self.state();self.assertEqual(len(s['presents']),1)
        self.assertEqual((s['presents'][0]['present_type'],s['presents'][0]['present_param_0']),(3,1))
        self.assertEqual(self.login('2026-01-25',API(self.path)),results[0])
        self.assertEqual(self.state(),s)

    def test_month_reset_streak_gap_and_clock_rollback(self):
        self.login('2026-01-31')
        r=self.login('2026-02-01');self.assertEqual((r['login_days'],r['sequence_login_days']),(1,2))
        r=self.login('2026-02-03');self.assertEqual((r['login_days'],r['sequence_login_days']),(2,1))
        s=self.state();r=self.login('2026-02-02')
        self.assertEqual((r['login_days'],r['sequence_login_days']),(2,1));self.assertEqual(self.state(),s)
        self.assertEqual(len(s['presents']),3)

    def test_available_calendar_and_seven_day_local_streak_cap(self):
        for day in range(1,10):
            r=self.login(f'2026-01-{day:02}')
            row=self.api.masters[52]['data_list'][min(day,7)-1]
            self.assertEqual(r['sequence_login_bonus'],dict(type=row['type'],num=row['num']))
        gifts=self.state()['presents']
        self.assertEqual((gifts[4]['present_type'],gifts[4]['present_param_0']),(4,15022))
        r=self.login('2026-10-25')
        self.assertFalse(r['login_bonus']);self.assertEqual(r['login_days'],1)
        self.assertEqual(len(self.state()['presents']),9)

    def test_migrated_today_defers_bonus_until_next_login_day_and_preserves_flags(self):
        s=self.state();s['last_login']='2026-01-25';s['player']['login_days']=5
        s['player']['sequence_login_days']=4;s['bonus_flags']=[1]+[0]*255;self.api.store.save(s)
        r=self.login('2026-01-25')
        self.assertEqual((r['login_days'],r['sequence_login_days']),(5,4))
        self.assertEqual(r['sequence_login_bonus'],dict(type=0,num=0))
        self.assertFalse(r['login_bonus']);self.assertEqual(r['bonus_flags'][0],1)
        self.assertEqual(self.state().get('presents',[]),[])
        self.assertEqual(self.login('2026-01-26')['sequence_login_bonus'],dict(type=8,num=500))
        # A historical legacy cumulative count is reset at the next month.
        self.assertEqual(self.login('2026-02-01')['login_days'],1)

    def test_login_write_fault_rolls_back_counter_gift_and_snapshot(self):
        before=copy.deepcopy(self.state());save=self.api.store.save
        def fail(state):save(state);raise RuntimeError('after save')
        with patch.object(self.api.store,'save',side_effect=fail),self.assertRaises(RuntimeError):
            self.login('2026-01-01')
        self.assertEqual(self.state(),before)
        self.assertEqual(self.login('2026-01-01')['login_days'],1)

    def order(self,quest_id=11000):
        s=self.state();s['player']['quest_clear_flags'][0]|=6;self.api.store.save(s)
        req=dict(ver='2.4.0',retry=0,quest_id=str(quest_id),floor=0,helper_user_id='0',
            resume_id=0,bonus_stamina=0,token=str(uuid.uuid4()),
            level_data_hash=self.api.levels[quest_id]['hash'],
            hashes={str(t):str(self.api.masters[t]['hash']) for t in HASH_TYPES})
        self.api.call('order_quest',req,self.token);return req

    def clear(self,exp,money,quest_id=11000):
        return self.api.call('clear_quest2',dict(ver='2.4.0',retry=0,
            list=[dict(quest_id=quest_id,exp=exp,game_money=money,yorisiro_exp=0,
                       units=[],challenge_id_list=[])],
            party_instance_id=[1001,1002,1003,0,0,0]),self.token)

    def test_experience_is_flat_added_capped_and_order_snapshot_survives_new_login(self):
        for day in range(1,5):self.login(f'2026-10-{day:02}')
        order=self.order();before=self.state()
        self.assertEqual(before['battle_login_bonus'],dict(type=9,num=50))
        self.login('2026-10-05')
        self.assertEqual(self.api.call('order_quest',dict(order,retry=1),self.token)['code'],4096)
        self.assertEqual(self.state()['battle_login_bonus'],dict(type=9,num=50))
        current=self.state()
        with self.assertRaises(ProtocolError):self.clear(50,500)
        self.assertEqual(self.state(),current)
        self.api=API(self.path)
        result=self.clear(100,500)['result'][0]['user']
        self.assertEqual(result['exp'],100)
        self.assertNotIn('battle_login_bonus',self.state())

    def test_money_flat_bonus_lower_bound_and_upper_cap(self):
        for day in range(1,6):self.login(f'2026-10-{day:02}')
        self.order();before=self.state()
        with self.assertRaises(ProtocolError):self.clear(50,999)
        self.assertEqual(self.state(),before)
        self.assertEqual(self.clear(50,1000)['code'],4096)
        self.order()
        quest=next(q for q in self.api.masters[30]['data_list'] if q['id']==11000)
        with self.assertRaises(ProtocolError):self.clear(50,quest['reward_money_limit']+1)
        self.assertEqual(self.clear(50,quest['reward_money_limit'])['code'],4096)

    def test_second_tutorial_bonus_and_legacy_battle_without_snapshot(self):
        for day in range(1,5):self.login(f'2026-10-{day:02}')
        self.order(10001)
        self.assertEqual(self.clear(100,500,10001)['code'],4096)
        self.order();s=self.state();s.pop('battle_login_bonus');self.api.store.save(s)
        self.assertEqual(self.clear(50,500)['code'],4096)


if __name__=='__main__':unittest.main()
