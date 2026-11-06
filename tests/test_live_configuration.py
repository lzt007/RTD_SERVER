import copy
import pathlib
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from rtd.services.api import API
from rtd.operations.configuration import ConfigurationError, is_open
from rtd.backup import create_backup,restore_backup


def event(**changes):
    result=dict(id='local-11000',name='Local event',enabled=True,starts_at=None,ends_at=None,
                quests=[dict(quest_id=11000,drops=[dict(drop_data_id=30140,no_drop_weight=0,
                    entries=[dict(unit_id=10000,level_min=2,level_max=3,weight=1)])])])
    result.update(changes);return result


class LiveConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'operations.sqlite3';self.api=API(self.path)

    def test_defaults_catalog_schema_and_existing_v1_migration(self):
        cfg=self.api.operations.read()
        self.assertEqual(cfg['revision'],1);self.assertEqual(cfg['events'],[])
        self.assertEqual([p['id'] for p in cfg['gachas']],[10000,20000,30000])
        self.assertEqual([len(p['entries']) for p in cfg['gachas']],[176,162,176])
        self.assertTrue(all(p['enabled'] for p in cfg['gachas']))
        catalog=self.api.operations.catalog()
        configurable={q['quest_id'] for q in catalog['quests'] if q['event_configurable']}
        self.assertTrue({11000,11001,11002,20000,20100} <= configurable)
        self.assertTrue(next(q for q in catalog['quests'] if q['quest_id']==20000)['playable'])
        self.assertTrue(next(q for q in catalog['quests'] if q['quest_id']==20101)['playable'])
        self.assertTrue(any(q['division']==20000 and not q['event_configurable'] for q in catalog['quests']))
        self.assertIn(30140,[d['drop_data_id'] for d in catalog['event_quest_drops']['11000']])
        with self.api.store.connect() as db:
            db.executescript('DROP TABLE runtime_config; DROP TABLE admin_reward_batches; '
                             'DELETE FROM schema_history WHERE version>1; PRAGMA user_version=1;')
        self.api=API(self.path)
        self.assertEqual(self.api.operations.read(),cfg)
        with self.api.store.connect() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],3)

    def test_updates_restart_other_instance_revision_and_backup(self):
        other=API(self.path);before=self.api.operations.read();p=copy.deepcopy(before['gachas'][0])
        p.update(enabled=False,entries=[dict(unit_id=10021,level=2,weight=7)])
        cfg=self.api.operations.update('gachas','10000',p)
        self.assertEqual(cfg['revision'],2);self.assertEqual(other.operations.read(),cfg)
        self.assertEqual(cfg['gachas'][2],before['gachas'][2])
        self.api.operations.update('events','local-11000',event())
        expected=other.operations.read();self.assertEqual(expected['revision'],3)
        self.assertEqual(API(self.path).operations.read(),expected)
        backup=pathlib.Path(self.temp.name)/'backup.sqlite3';restored=pathlib.Path(self.temp.name)/'restored.sqlite3'
        create_backup(self.path,backup);restore_backup(backup,restored)
        self.assertEqual(API(restored).operations.read(),expected)
        with self.assertRaises(ConfigurationError) as conflict:
            self.api.operations.update('gachas','10000',dict(enabled=True,expected_revision=1),method='PATCH')
        self.assertEqual(conflict.exception.status,409);self.assertEqual(self.api.operations.read(),expected)
        self.api.operations.update('events','local-11000',None,method='DELETE')
        self.assertEqual(self.api.operations.read()['events'],[])

    def test_persisted_configuration_does_not_require_seed_file_on_restart(self):
        expected=self.api.operations.update('gachas','10000',dict(enabled=False),'PATCH')
        with patch('rtd.services.api.load_pools',side_effect=FileNotFoundError('seed moved')) as seed:
            self.assertEqual(API(self.path).operations.read(),expected)
            seed.assert_not_called()

    def test_utc_conversion_overflow_is_a_validation_error(self):
        before=self.api.operations.read()
        for value in ('0001-01-01T00:00:00+14:00','9999-12-31T23:59:59-14:00'):
            with self.assertRaises(ConfigurationError):
                self.api.operations.update('gachas','10000',dict(starts_at=value),'PATCH')
            self.assertEqual(self.api.operations.read(),before)

    def test_invalid_configuration_has_no_partial_writes(self):
        good=event()
        bad_events=[event(id='../bad'),event(enabled=1),event(quests=[dict(quest_id=10001,drops=[])]),
                    event(starts_at='2026-01-01'),event(starts_at='2026-10-27T00:00:00Z',ends_at='2026-10-26T00:00:00Z')]
        for field,value in (('unit_id',999999),('level_min',0),('level_max',999),('weight',True),('weight',0)):
            bad=copy.deepcopy(good);bad['quests'][0]['drops'][0]['entries'][0][field]=value;bad_events.append(bad)
        bad=copy.deepcopy(good);bad['quests'][0]['drops'][0]['drop_data_id']=999999;bad_events.append(bad)
        for bad in bad_events:
            before=self.api.operations.read()
            with self.subTest(bad=bad),self.assertRaises(ConfigurationError):
                self.api.operations.update('events',bad['id'],bad)
            self.assertEqual(self.api.operations.read(),before)
        cfg=self.api.operations.read()
        for bad in (dict(enabled='false'),dict(entries=[]),dict(unknown=True),dict(id=20000)):
            with self.assertRaises(ConfigurationError):self.api.operations.update('gachas','10000',bad,method='PATCH')
            self.assertEqual(self.api.operations.read(),cfg)
        full=dict(gachas=cfg['gachas'],events=[good,event(id='other')])
        with self.assertRaises(ConfigurationError):self.api.operations.update('config',None,full)
        self.assertEqual(self.api.operations.read(),cfg)

    def test_full_replacement_and_write_fault_are_atomic(self):
        cfg=self.api.operations.read();new=dict(gachas=copy.deepcopy(cfg['gachas']),events=[event()])
        new['gachas'][0]['enabled']=False
        with patch.object(self.api.operations,'_save',side_effect=RuntimeError('injected config failure')):
            with self.assertRaisesRegex(RuntimeError,'injected'):self.api.operations.update('config',None,new)
        self.assertEqual(self.api.operations.read(),cfg)
        result=self.api.operations.update('config',None,new)
        self.assertFalse(result['gachas'][0]['enabled']);self.assertEqual(len(result['events']),1)

    def test_utc_schedule_start_inclusive_end_exclusive_and_boolean(self):
        item=dict(enabled=True,starts_at='2026-10-26T00:00:00Z',ends_at='2026-10-27T00:00:00Z')
        import datetime as dt
        start=dt.datetime(2026,10,26,tzinfo=dt.timezone.utc).timestamp()
        self.assertFalse(is_open(item,start-1));self.assertTrue(is_open(item,start))
        self.assertFalse(is_open(item,start+86400));self.assertFalse(is_open(dict(item,enabled=False),start))


if __name__=='__main__':unittest.main()
