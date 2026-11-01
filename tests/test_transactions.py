"""Transaction/migration tests use disposable databases, never the acceptance save."""
import concurrent.futures
import copy
import json
import pathlib
import sqlite3
import tempfile
import unittest
import uuid
from rtd_server import API, ProtocolError


class TransactionsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rtd-transaction-')
        self.path = pathlib.Path(self.temp.name)/'test.sqlite3'
        self.api = API(self.path)
        self.key = str(uuid.uuid4())
        self.call('create_user', uuid=self.key, unit_no='0', user_name='Atomic')
        self.token = self.call('auth_user', uuid=self.key)['session_id']
        self.settlement = dict(list=[dict(quest_id=10000, exp=0, game_money=1,
            yorisiro_exp=0, units=[], challenge_id_list=[])], party_instance_id=[1001,1002,1003,0,0])

    def tearDown(self):
        self.temp.cleanup()

    def call(self, operation, **req):
        return self.api.call(operation, {'ver':'2.4.0','retry':0,**req}, getattr(self,'token',''))

    def state(self):
        return self.api.store.session(self.token)

    def test_normal_repeat_and_late_retry_are_distinct(self):
        receipts = []
        for index in range(3):
            self.call('order_quest', quest_id='10000', floor=0)
            before = self.state()['player']['action_point']
            if index:
                old = self.call('clear_quest2', **dict(self.settlement,retry=1))
                self.assertEqual(old, receipts[-1])
                self.assertIsNotNone(self.state()['battle'])
            receipts.append(self.call('clear_quest2', **self.settlement))
            self.assertIsNone(self.state()['battle'])
            self.assertEqual(self.state()['player']['action_point'],before)
        state = self.state()
        self.assertEqual(state['player']['game_money'],3)
        self.assertEqual(len(state['units']),6)
        with self.api.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM quest_runs WHERE status='cleared'").fetchone()[0],3)
            self.assertEqual(db.execute('SELECT count(DISTINCT run_id) FROM operation_receipts').fetchone()[0],3)
        self.api = API(self.path)
        self.assertEqual(self.call('clear_quest2', **dict(self.settlement,retry=1)),receipts[-1])
        self.assertEqual(self.state(),state)
        self.call('order_quest', quest_id='10000', floor=0, retry=1)
        self.assertEqual(self.state(),state)

    def test_failure_after_receipt_write_rolls_back_everything(self):
        self.call('order_quest',quest_id='10000',floor=0)
        before = self.state()
        original = self.api.store.finish_run

        def fail(*args):
            original(*args)
            raise RuntimeError('Injected after receipt insert')

        self.api.store.finish_run = fail
        with self.assertRaisesRegex(RuntimeError, 'Injected'):
            self.call('clear_quest2', **self.settlement)
        self.assertEqual(self.state(), before)
        with self.api.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM operation_receipts').fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM quest_runs WHERE status='active'").fetchone()[0],1)
        self.api.store.finish_run = original
        self.call('clear_quest2', **self.settlement)
        self.assertEqual(self.state()['player']['game_money'],1)

    def test_two_independent_stores_cannot_double_settle(self):
        self.call('order_quest', quest_id='10000', floor=0)
        other = API(self.path)
        request = {'ver':'2.4.0','retry':1,**self.settlement}
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            futures = [pool.submit(api.call,'clear_quest2',copy.deepcopy(request),self.token)
                       for api in (self.api,other)]
            responses = [f.result() for f in futures]
        self.assertEqual(responses[0],responses[1])
        self.assertEqual(self.state()['player']['game_money'],1)
        self.assertEqual(len(self.state()['units']),4)

    def test_invalid_request_rolls_back_lazy_legacy_run(self):
        self.call('order_quest', quest_id='10000', floor=0)
        with self.api.store.connect() as db:
            db.execute('DELETE FROM quest_runs')
        before = self.state()
        bad = copy.deepcopy(self.settlement)
        bad['list'][0]['exp'] = 100000
        with self.assertRaises(ProtocolError):
            self.call('clear_quest2', **bad)
        self.assertEqual(self.state(), before)
        with self.api.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM quest_runs').fetchone()[0],0)

    def test_legacy_schema_upgrade_and_backup_restore(self):
        before = self.state()
        with self.api.store.connect() as db:
            db.executescript('DROP TABLE schema_history; DROP TABLE operation_receipts; DROP TABLE quest_runs; PRAGMA user_version=0;')
        backup = pathlib.Path(self.temp.name)/'schema0.sqlite3'
        with self.api.store.connect() as db:
            target=sqlite3.connect(backup)
            try:
                db.backup(target)
            finally:
                target.close()
        self.api=API(self.path)
        self.assertEqual(self.state(),before)
        with self.api.store.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        old=sqlite3.connect(backup)
        try:
            self.assertEqual(old.execute('PRAGMA user_version').fetchone()[0],0)
            restored=json.loads(old.execute('SELECT state FROM players WHERE id=1').fetchone()[0])
            self.assertEqual(restored,before)
        finally:
            old.close()


if __name__ == '__main__':
    unittest.main()
