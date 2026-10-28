"""Clock-controlled natural stamina rules, independent of device time."""
import copy
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.common import ProtocolError
from rtd.policies.stamina import recover, spend
from rtd.services.api import API


class StaminaTest(unittest.TestCase):
    def player(self, ap=15, anchor=1000):
        return dict(action_point=ap, max_action_point=21, action_point_recover=anchor)

    def test_boundaries_preserve_partial_interval_and_cap(self):
        p = self.player()
        self.assertFalse(recover(p, 1599))
        self.assertEqual(p, self.player())
        self.assertTrue(recover(p, 1600))
        self.assertEqual(p, self.player(16, 1600))
        self.assertTrue(recover(p, 2899))
        self.assertEqual(p, self.player(18, 2800))
        self.assertTrue(recover(p, 10000))
        self.assertEqual(p, self.player(21, 10000))
        self.assertFalse(recover(p, 20000))
        spend(p, 3, 20000)
        self.assertEqual(p, self.player(18, 20000))
        self.assertFalse(recover(p, 20599))

    def test_spending_partial_stamina_keeps_remainder(self):
        p = self.player()
        spend(p, 3, 1700)
        self.assertEqual(p, self.player(13, 1600))
        self.assertFalse(recover(p, 2199))
        self.assertTrue(recover(p, 2200))
        self.assertEqual(p, self.player(14, 2200))

    def test_clock_reversal_and_invalid_spend_do_not_change_player(self):
        p = self.player()
        self.assertFalse(recover(p, 999))
        self.assertEqual(p, self.player())
        for cost in (True, -1, 0, 22, '3'):
            with self.subTest(cost=cost):
                before = copy.deepcopy(p)
                with self.assertRaises(ProtocolError):
                    spend(p, cost, 1700)
                self.assertEqual(p, before)


class StaminaApiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.api = API(pathlib.Path(self.temp.name)/'test.sqlite3')
        self.clock = patch('time.time', return_value=10000)
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.key = str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=self.key,unit_no=3,user_name='Stamina'))
        self.token = self.api.call('auth_user',dict(ver='2.4.0',uuid=self.key))['session_id']

    def call(self, op, **req):
        return self.api.call(op,dict(ver='2.4.0',retry=0,**req),self.token)

    def state(self):
        return self.api.store.session(self.token)

    def set_ap(self, ap, anchor):
        s = self.state()
        s['player'].update(action_point=ap,action_point_recover=anchor)
        self.api.store.save(s)

    def test_authenticated_and_session_requests_recover_persistently(self):
        self.set_ap(10,8500)
        auth = self.api.call('auth_user',dict(ver='2.4.0',uuid=self.key))
        self.assertEqual((auth['result']['action_point'],auth['result']['action_point_recover']),(12,9700))
        self.assertEqual(self.state()['player']['action_point'],12)
        self.set_ap(10,8500)
        self.call('get_master',get_data_list=[],compare_hash_only=True)
        self.assertEqual((self.state()['player']['action_point'],self.state()['player']['action_point_recover']),(12,9700))
        self.api = API(self.api.store.path)
        self.call('get_units')
        self.assertEqual(self.state()['player']['action_point'],12)

    def test_failed_request_and_save_fault_roll_back_recovery(self):
        self.set_ap(10,8500)
        before = self.state()
        for operation,req in [('unsupported',{}),('form_units',{'party':{}})]:
            with self.assertRaises(ProtocolError):
                self.call(operation,**req)
            self.assertEqual(self.state(),before)
        original = self.api.store.save
        def save_then_fail(state):
            original(state)
            raise RuntimeError('injected recovery save failure')
        with patch.object(self.api.store,'save',side_effect=save_then_fail):
            with self.assertRaisesRegex(RuntimeError,'injected'):
                self.call('get_units')
        self.assertEqual(self.state(),before)

    def test_new_order_starts_clock_and_retry_does_not_spend_again(self):
        self.set_ap(20,1000)
        result = self.call('order_quest',quest_id='10000',floor=0)['result']
        self.assertEqual((result['action_point'],result['action_point_recover']),(19,10000))
        self.assertEqual(self.call('order_quest',quest_id='10000',floor=0)['result'],result)
        self.api = API(self.api.store.path)
        self.assertEqual(self.call('order_quest',quest_id='10000',floor=0)['result'],result)
        with patch('time.time',return_value=10600):
            refreshed = self.call('order_quest',quest_id='10000',floor=0)['result']
            self.assertEqual((refreshed['action_point'],refreshed['action_point_recover']),(20,10600))
            self.assertEqual(refreshed['enemy_info_list'],result['enemy_info_list'])
        with self.api.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM quest_runs').fetchone()[0],1)

    def test_ordinary_guid_order_uses_same_clock_without_double_spend(self):
        state = self.state()
        state['player']['quest_clear_flags'][0] = 6
        state['player']['action_point_recover'] = 1000
        self.api.store.save(state)
        from rtd.services.battle_entry import HASH_TYPES
        req = dict(quest_id='11000',floor=0,resume_id=0,bonus_stamina=0,
                   helper_user_id='0',token=str(uuid.uuid4()),
                   hashes={str(t):str(self.api.masters[t]['hash']) for t in HASH_TYPES},
                   level_data_hash=str(self.api.levels[11000]['hash']))
        result = self.call('order_quest',**req)['result']
        self.assertEqual((result['action_point'],result['action_point_recover']),(17,10000))
        self.api = API(self.api.store.path)
        self.assertEqual(self.call('order_quest',**req)['result'],result)
        with patch('time.time',return_value=10600):
            retried = self.call('order_quest',**req)['result']
            self.assertEqual((retried['action_point'],retried['action_point_recover']),(18,10600))
            self.assertEqual(retried['enemy_info_list'],result['enemy_info_list'])


if __name__ == '__main__':
    unittest.main()
