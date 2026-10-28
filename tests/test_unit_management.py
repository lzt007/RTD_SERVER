"""Owned-unit management contracts against transactional SQLite state."""
import copy
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch

from rtd.common import ProtocolError
from rtd.services.api import API


class UnitManagementTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.api = API(pathlib.Path(self.temp.name)/'test.sqlite3')
        self.key = str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=self.key,unit_no=3,user_name='Units'))
        self.token = self.api.call('auth_user',dict(ver='2.4.0',uuid=self.key))['session_id']

    def call(self, operation, **req):
        return self.api.call(operation,dict(ver='2.4.0',retry=0,**req),self.token)

    def state(self):
        return self.api.store.session(self.token)

    def test_favorite_batch_requires_exact_types_unique_owned_ids_and_rolls_back(self):
        instance = self.state()['units'][0]['instance_id']
        bad = [None,{},'flags',[None],[{}],[dict(instance_id=instance,flag=True)],
               [dict(instance_id=instance,flag=1),dict(instance_id=instance,flag=0)],
               [dict(instance_id=instance,flag=1),dict(instance_id=999999,flag=1)]]
        for flags in bad:
            with self.subTest(flags=flags):
                before = self.state()
                with self.assertRaises(ProtocolError):
                    self.call('save_unit_favorite_flags',flags=flags)
                self.assertEqual(self.state(),before)
        for flag in (1,0):
            self.call('save_unit_favorite_flags',flags=[dict(instance_id=instance,flag=flag)])
            self.api = API(self.api.store.path)
            self.assertEqual(self.call('get_units')['result']['units'][0]['favorite'],flag)

    def test_favorite_upload_marks_server_migration_atomically_even_when_empty(self):
        # Original GetUnits reloads legacy local flags until byte0 bit5 is set.
        before = self.state()
        self.assertEqual(before['player']['tutorial_flags'][0] & 32,0)
        original = self.api.store.save
        def save_then_fail(state):
            original(state)
            raise RuntimeError('injected favorite migration fault')
        with patch.object(self.api.store,'save',side_effect=save_then_fail):
            with self.assertRaisesRegex(RuntimeError,'favorite migration'):
                self.call('save_unit_favorite_flags',flags=[])
        self.assertEqual(self.state(),before)
        self.call('save_unit_favorite_flags',flags=[])
        self.api = API(self.api.store.path)
        auth = self.api.call('auth_user',dict(ver='2.4.0',uuid=self.key))
        self.assertEqual(auth['result']['tutorial_flags'][0],32)
        self.assertEqual(self.state()['units'],before['units'])

    def test_collection_is_unique_acquired_and_keeps_highest_ever_level(self):
        s = self.state()
        duplicate = copy.deepcopy(s['units'][0])
        duplicate.update(instance_id=9999,level=5)
        s['units'].append(duplicate)
        self.api.store.save(s)
        collection = self.call('login')['result']['unit_collection']
        ids = [row['unit_id'] for row in collection]
        self.assertEqual(len(ids),len(set(ids)))
        row = next(c for c in collection if c['unit_id']==duplicate['unit_id'])
        self.assertEqual((row['status'],row['level']),(100,5))
        s = self.state()
        s['units'] = [u for u in s['units'] if u['unit_id']!=duplicate['unit_id']]
        self.api.store.save(s)
        self.api = API(self.api.store.path)
        self.assertIn(row,self.call('login')['result']['unit_collection'])

    def test_legacy_collection_migration_is_atomic_and_client_flags_cannot_grant(self):
        s = self.state()
        s.pop('unit_collection',None)
        self.api.store.save(s)
        original = self.api.store.save
        def save_then_fail(state):
            original(state)
            raise RuntimeError('injected collection migration fault')
        with patch.object(self.api.store,'save',side_effect=save_then_fail):
            with self.assertRaisesRegex(RuntimeError,'injected'):
                self.call('get_units')
        self.assertEqual(self.state(),s)
        self.call('get_units')
        before = self.call('login')['result']['unit_collection']
        self.call('save_local_flags',unit_collection_flags=[255]*128)
        self.assertEqual(self.call('login')['result']['unit_collection'],before)

    def test_party_subslots_cross_group_reuse_and_restart(self):
        s = self.state()
        ids = [u['instance_id'] for u in s['units']]
        party = dict(active=1,party=[dict(instanceIds=ids+[0,0]),
                                     dict(instanceIds=[ids[2],ids[1],ids[0],0,0])])
        self.call('form_units',party=party)
        self.api = API(self.api.store.path)
        self.assertEqual(self.call('get_units')['result']['party'],party)
        for bad in (dict(active=True,party=party['party']),
                    dict(active=0,party=[dict(instanceIds=[ids[0],ids[1],ids[2],ids[0],0])]),
                    dict(active=0,party=[dict(instanceIds=[ids[0],ids[1],ids[2],999999,0])])):
            before = self.state()
            with self.assertRaises(ProtocolError):
                self.call('form_units',party=bad)
            self.assertEqual(self.state(),before)

    def test_real_summon_and_collection_write_share_one_transaction(self):
        s = self.state()
        s['player']['quest_clear_flags'][0] = 2
        s['player'].update(free_paid_point=5,total_paid_point=5)
        self.api.store.save(s)
        before = self.state()
        original = self.api.store.save
        writes = 0
        def fail_collection_write(state):
            nonlocal writes
            original(state)
            writes += 1
            if writes == 2:
                raise RuntimeError('injected post-acquisition collection fault')
        with patch.object(self.api.store,'save',side_effect=fail_collection_write):
            with self.assertRaisesRegex(RuntimeError,'post-acquisition'):
                self.call('buy_gacha',gacha_id='20000',tutorial_flag=True)
        self.assertEqual(self.state(),before)
        result = self.call('buy_gacha',gacha_id='20000',tutorial_flag=True)
        unit = result['result']['unit']
        row = dict(unit_id=unit['unit_id'],status=100,level=unit['level'])
        self.assertIn(row,self.state()['unit_collection'])
        self.assertEqual(self.call('buy_gacha',gacha_id='20000',tutorial_flag=True),result)

    def test_over_capacity_blocks_new_order_but_preserves_active_guid(self):
        from rtd.services.battle_entry import HASH_TYPES
        s = self.state()
        s['player']['quest_clear_flags'][0] = 6
        s['player']['max_unit'] = len(s['units'])
        self.api.store.save(s)
        req = dict(quest_id='11000',floor=0,resume_id=0,bonus_stamina=0,
                   helper_user_id='0',token=str(uuid.uuid4()),
                   hashes={str(t):str(self.api.masters[t]['hash']) for t in HASH_TYPES},
                   level_data_hash=str(self.api.levels[11000]['hash']))
        result = self.call('order_quest',**req)
        s = self.state()
        extra = copy.deepcopy(s['units'][0])
        extra['instance_id'] = 9999
        s['units'].append(extra)
        self.api.store.save(s)
        before = self.state()
        self.assertEqual(self.call('order_quest',**req),result)
        req['token'] = str(uuid.uuid4())
        with self.assertRaises(ProtocolError):
            self.call('order_quest',**req)
        self.assertEqual(self.state(),before)


if __name__ == '__main__':
    unittest.main()
