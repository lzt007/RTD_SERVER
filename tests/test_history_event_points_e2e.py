"""Real history-event protocol regression using disposable SQLite only.

Only the binary-download readiness audit is bypassed: local book bundles are
separately versioned and are not needed to test order/clear/login contracts.
Original masters, inferred missing maps/drops, generation and persistence are
real. These tests do not establish Android gameplay or bundle correctness.
Run Python in UTF-8 mode, as required by the reconstruction JSON loader.
"""
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.common import ProtocolError
from rtd.masters.catalog import load_catalog
from rtd.services.api import API
from rtd.services.battle_entry import HASH_TYPES
from test_battle_generation import FixedRoll


class HistoryEventEndToEndTests(unittest.TestCase):
    QUESTS = (20710, 20711, 20712)

    def setUp(self):
        environment = patch.dict(os.environ, {
            'RTD_EVENT_RECONSTRUCTION': '1',
            'RTD_SHINGETSU_RECONSTRUCTION': '1',
            'RTD_CONTENT_EXPERIMENTAL': '1',
        })
        environment.start()
        self.addCleanup(environment.stop)
        readiness = patch('rtd.policies.reconstructed_resources.resource_issues', return_value={})
        readiness.start()
        self.addCleanup(readiness.stop)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'history-events.sqlite3'
        self.api = API(self.path)
        self.assertTrue(set(self.QUESTS) <= self.api.reconstructed_quests)
        key = str(uuid.uuid4())
        self.api.call('create_user', dict(ver='2.4.0', uuid=key, unit_no=0,
                                         user_name='History regression'))
        self.token = self.api.call('auth_user', dict(ver='2.4.0', uuid=key))['session_id']
        self.api.operations.update('events', 'history-regression', dict(
            name='Disposable history schedule', enabled=True, starts_at=None, ends_at=None,
            quests=[dict(quest_id=qid, drops=[]) for qid in self.QUESTS]))
        self.progress(0, tutorial=True)

    def state(self):
        return self.api.store.session(self.token)

    def quest(self, qid):
        return next(q for q in self.api.masters[30]['data_list'] if q['id'] == qid)

    def progress(self, points, *, tutorial=True):
        state = self.state()
        state['sp_event_points'] = {'100001': points}
        state['player'].update(action_point=9999, max_action_point=9999, max_unit=9999)
        flags = state['player']['quest_clear_flags']
        flags[:] = [0] * len(flags)
        if tutorial:
            flag = self.quest(10000)['flag_no']
            flags[flag // 8] |= 1 << (flag % 8)
        self.api.store.save(state)

    def request(self, qid):
        return dict(ver='2.4.0', retry=0, quest_id=qid, floor=0, resume_id=0,
                    bonus_stamina=0, helper_user_id=0, token=str(uuid.uuid4()),
                    level_data_hash=self.api.levels[qid]['hash'],
                    hashes={str(kind): str(self.api.master_table(kind)['hash'])
                            for kind in HASH_TYPES})

    def order(self, qid):
        # Fix only RNG, retaining the production enemy-generation implementation.
        with patch('rtd.services.battle_generation.secrets.SystemRandom',
                   return_value=FixedRoll(1)):
            return self.api.call('order_quest', self.request(qid), self.token)

    def clear(self, qid, points):
        quest = self.quest(qid)
        request = dict(ver='2.4.0', retry=0,
                       party_instance_id=self.state()['battle_party_instance_ids'],
                       list=[dict(quest_id=qid, exp=quest['reward_exp'],
                                  game_money=quest['reward_money'], yorisiro_exp=0,
                                  units=[], challenge_id_list=[], sp_event_point=points)])
        return request, self.api.call('clear_quest2', request, self.token)

    def test_real_missing_drops_award_only_present_dark_soldiers(self):
        original, _ = load_catalog()
        original_drops = {row['id'] for row in original[22]['data_list']}
        effective_drops = {row['id']: row for row in self.api.masters[22]['data_list']}
        for qid in self.QUESTS:
            with self.subTest(quest=qid):
                self.progress(50)
                result = self.order(qid)
                enemies = result['result']['enemy_info_list']
                targets = [enemy for enemy in enemies if enemy['enemy_set_id'] == 41028]
                self.assertTrue(targets)
                for enemy in enemies:
                    expected = int(enemy['flag'] and enemy['enemy_set_id'] == 41028)
                    self.assertEqual(enemy['sp_event_point'], expected)
                for target in targets:
                    drop_id = target['drop_data_id']
                    self.assertNotIn(drop_id, original_drops)
                    self.assertIn(drop_id, effective_drops)
                    self.assertNotIn('sp_event_point', effective_drops[drop_id])
                points = sum(enemy['sp_event_point'] for enemy in enemies)
                self.assertGreater(points, 0)
                self.assertEqual(self.state()['battle_event_points'],
                                 dict(event_id=100001, maximum=points))
                self.clear(qid, points)
                self.assertEqual(self.state()['sp_event_points'], {'100001': 50 + points})

    def test_original_four_five_and_fortynine_fifty_gates_without_sequential_prerequisites(self):
        for qid, threshold in ((20711, 5), (20712, 50)):
            with self.subTest(quest=qid):
                quest = self.quest(qid)
                self.assertEqual((quest['open_sp_event_id'], quest['open_sp_event_point']),
                                 (100001, threshold))
                prerequisites = [quest['open_param_' + str(i)] for i in range(1, 7)
                                 if quest['open_type_' + str(i)] == 2]
                self.assertEqual(prerequisites, [10000])
                self.progress(threshold - 1)
                before = self.state()
                with self.assertRaises(ProtocolError) as error:
                    self.order(qid)
                self.assertEqual(error.exception.args[0], 9472)
                self.assertEqual(self.state(), before)
                self.progress(threshold)
                self.assertEqual(self.order(qid)['code'], 4096)
                self.clear(qid, 0)

    def test_original_tutorial_is_required_even_with_enough_points(self):
        for qid in self.QUESTS:
            with self.subTest(quest=qid):
                self.progress(50, tutorial=False)
                before = self.state()
                with self.assertRaises(ProtocolError) as error:
                    self.order(qid)
                self.assertEqual(error.exception.args[0], 9472)
                self.assertEqual(self.state(), before)

    def test_real_clear_crosses_five_gate_and_survives_restart_login_and_replay_once(self):
        self.progress(4)
        ordered = self.order(20710)
        self.assertTrue(any(enemy['flag'] and enemy['enemy_set_id'] == 41028
                            for enemy in ordered['result']['enemy_info_list']))
        request, result = self.clear(20710, 1)
        after = self.state()
        self.assertEqual(after['sp_event_points'], {'100001': 5})
        self.api = API(self.path)
        self.assertEqual(self.api.call('clear_quest2', dict(request, retry=1), self.token), result)
        self.assertEqual(self.state(), after)
        for _ in range(2):
            login = self.api.call('login', dict(ver='2.4.0'), self.token)
            self.assertEqual(login['result']['sp_event_point_list'],
                             [dict(sp_event_id=100001, point=5)])
        self.assertEqual(self.order(20711)['code'], 4096)
        with self.api.store.connect() as database:
            self.assertEqual(database.execute('SELECT COUNT(*) FROM operation_receipts').fetchone()[0], 1)


if __name__ == '__main__':
    unittest.main()
