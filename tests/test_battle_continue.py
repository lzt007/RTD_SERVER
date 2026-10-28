import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch
from rtd.common import ProtocolError
from rtd.services.api import API
from rtd.services.battle_entry import HASH_TYPES
from rtd.services.presents import USER_FIELDS


class BattleContinueTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'continue.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='ContinueTest'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        s=self.state();s['player']['quest_clear_flags'][0]|=4
        s['player'].update(free_paid_point=1,paid_point=1,total_paid_point=2);self.api.store.save(s)
        self.order()

    def state(self):return self.api.store.session(self.token)
    def call(self,**kw):
        req=dict(ver='2.4.0',retry='0',floor='0',quest_continue='1');req.update(kw)
        return self.api.call('continue_quest',req,self.token)['result']
    def order(self):
        self.order_req=dict(ver='2.4.0',retry=0,quest_id=11000,floor=0,resume_id=0,
            bonus_stamina=0,helper_user_id=0,token=str(uuid.uuid4()),
            level_data_hash=self.api.levels[11000]['hash'],
            hashes={str(t):str(self.api.masters[t]['hash']) for t in HASH_TYPES})
        self.api.call('order_quest',self.order_req,self.token)

    def test_cost_exact_response_current_balance_retry_and_restart(self):
        before=self.state();result=self.call()
        self.assertEqual(set(result),set(USER_FIELDS))
        self.assertEqual((result['free_paid_point'],result['paid_point'],result['total_paid_point']),(0,1,1))
        after=self.state();self.assertEqual(after['battle']['quest_continue'],1)
        self.assertEqual(after['player']['action_point'],before['player']['action_point'])
        self.assertEqual(self.call(retry='1'),result)
        s=self.state();s['player']['game_money']+=50;self.api.store.save(s)
        self.assertEqual(self.call()['game_money'],result['game_money']+50)
        self.api=API(self.path)
        info=self.api.call('get_quest_info',dict(ver='2.4.0'),self.token)['result']
        self.assertEqual(info[0]['quest_continue'],1)
        result=self.call(quest_continue='2')
        self.assertEqual((result['free_paid_point'],result['paid_point'],result['total_paid_point']),(0,0,0))
        self.assertEqual(self.call(quest_continue='2',retry='1'),result)

    def test_invalid_floor_count_and_unreceipted_retry_leave_state(self):
        for kw in (dict(floor='1'),dict(floor=True),dict(quest_continue='0'),
                   dict(quest_continue='2'),dict(quest_continue='01'),dict(retry='1')):
            before=self.state()
            with self.assertRaises(ProtocolError):self.call(**kw)
            self.assertEqual(self.state(),before)
        self.call();self.call(quest_continue='2')
        before=self.state()
        with self.assertRaises(ProtocolError):self.call()
        self.assertEqual(self.state(),before)

    def test_insufficient_and_inconsistent_currency_never_increment(self):
        for free,paid,total,code in ((0,0,0,8961),(1,0,2,8197)):
            s=self.state();s['player'].update(free_paid_point=free,paid_point=paid,total_paid_point=total);self.api.store.save(s)
            before=self.state()
            with self.assertRaises(ProtocolError) as e:self.call()
            self.assertEqual(e.exception.code,code);self.assertEqual(self.state(),before)

    def test_failure_after_write_rolls_back_balance_count_and_receipt(self):
        before=self.state();save=self.api.store.save
        def fail(state):save(state);raise RuntimeError('injected continue write failure')
        with patch.object(self.api.store,'save',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'injected continue write failure'):self.call()
        self.assertEqual(self.state(),before)

    def test_late_network_retry_cannot_debit_new_run_or_closed_battle(self):
        self.call();self.order();before=self.state()
        with self.assertRaises(ProtocolError):self.call(retry='1')
        self.assertEqual(self.state(),before)
        self.call()
        s=self.state();s['battle']=None;self.api.store.save(s);before=self.state()
        with self.assertRaises(ProtocolError):self.call(retry='1')
        self.assertEqual(self.state(),before)


if __name__=='__main__':unittest.main()
