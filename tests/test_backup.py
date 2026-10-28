import json
import pathlib
import sqlite3
import tempfile
import unittest
import uuid
from contextlib import closing
from rtd.services.api import API
from rtd.backup import create_backup, restore_backup


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name);self.source=self.root/'live.sqlite3'
        self.backup=self.root/'backup.sqlite3';self.restored=self.root/'restored.sqlite3'
        self.api=API(self.source);key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='BackupTest'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']

    def test_online_wal_backup_restores_complete_state_and_api_identity(self):
        with self.api.store.connect() as db:
            db.execute("INSERT INTO quest_runs VALUES('run',1,11000,'cleared','{}','{}',1,2)")
            db.execute("INSERT INTO operation_receipts VALUES('run','clear_quest2','fingerprint','[]')")
        with closing(sqlite3.connect(self.source)) as reader:
            reader.execute('BEGIN');reader.execute('SELECT * FROM players').fetchall()
            state=self.api.store.session(self.token);state['player']['game_money']=12345
            self.api.store.save(state)
            self.assertGreater(pathlib.Path(str(self.source)+'-wal').stat().st_size,0)
            create_backup(self.source,self.backup)
            restore_backup(self.backup,self.restored)
            restored_api=API(self.restored)
            self.assertEqual(restored_api.store.session(self.token),state)
            self.assertEqual(self.api.store.session(self.token),state)
            with closing(sqlite3.connect(self.restored)) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
                with closing(sqlite3.connect(self.source)) as original:
                    for table in ('players','sessions','quest_runs','operation_receipts'):
                        self.assertEqual(db.execute('SELECT * FROM '+table).fetchall(),
                                         original.execute('SELECT * FROM '+table).fetchall())

    def test_orphan_target_sidecars_are_never_reused(self):
        create_backup(self.source,self.backup)
        for suffix in ('-wal','-shm'):
            sidecar=pathlib.Path(str(self.restored)+suffix);sidecar.write_bytes(b'old journal')
            with self.assertRaises(FileExistsError):restore_backup(self.backup,self.restored)
            with self.assertRaises(FileExistsError):create_backup(self.source,self.restored)
            self.assertEqual(sidecar.read_bytes(),b'old journal');sidecar.unlink()

    def test_never_overwrites_existing_files_or_source(self):
        create_backup(self.source,self.backup)
        before=self.backup.read_bytes()
        for target in (self.backup,self.source):
            with self.assertRaises(FileExistsError):create_backup(self.source,target)
            with self.assertRaises(FileExistsError):restore_backup(self.backup,target)
        self.assertEqual(self.backup.read_bytes(),before)

    def test_corruption_and_manifest_tampering_rejected_without_target(self):
        create_backup(self.source,self.backup)
        manifest=self.backup.with_suffix('.sqlite3.manifest.json');original=manifest.read_bytes()
        data=json.loads(original);data['schema_version']=99;manifest.write_text(json.dumps(data))
        with self.assertRaises(ValueError):restore_backup(self.backup,self.restored)
        self.assertFalse(self.restored.exists());manifest.write_bytes(original)
        with self.backup.open('ab') as stream:stream.write(b'corrupted')
        with self.assertRaises(ValueError):restore_backup(self.backup,self.restored)
        self.assertFalse(self.restored.exists())

    def test_bad_source_and_new_schema_leave_no_partial_backup(self):
        for source in (self.root/'missing.sqlite3',self.root/'bad.sqlite3'):
            if source.name=='bad.sqlite3':source.write_bytes(b'not a database')
            with self.assertRaises((ValueError,sqlite3.DatabaseError,FileNotFoundError)):
                create_backup(source,self.backup)
            self.assertFalse(self.backup.exists())
        with closing(sqlite3.connect(self.source)) as db:db.execute('PRAGMA user_version=99')
        with self.assertRaises(ValueError):create_backup(self.source,self.backup)
        self.assertFalse(self.backup.exists())
        self.assertFalse(self.backup.with_suffix('.sqlite3.manifest.json').exists())


if __name__=='__main__':unittest.main()
