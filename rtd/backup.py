"""Private local SQLite snapshots. Restore always creates a new database."""
import argparse
import datetime
import hashlib
import json
import pathlib
import shutil
import sqlite3
from contextlib import closing

TABLES=('players','sessions','quest_runs','operation_receipts')


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def inspect(path):
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)) as db:
        if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:
            raise ValueError('Backup integrity check failed')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Backup has invalid foreign keys')
        version=db.execute('PRAGMA user_version').fetchone()[0]
        if version not in (1,2):raise ValueError('Unsupported backup schema version')
        tables=TABLES+('runtime_config',) if version==2 else TABLES
        return dict(schema_version=version,table_counts={t:db.execute('SELECT count(*) FROM '+t).fetchone()[0] for t in tables})


def manifest_path(path):return path.with_suffix(path.suffix+'.manifest.json')


def require_new_database(path):
    for candidate in (path,pathlib.Path(str(path)+'-wal'),pathlib.Path(str(path)+'-shm')):
        if candidate.exists():raise FileExistsError(candidate)


def create_backup(source,destination):
    source=pathlib.Path(source);destination=pathlib.Path(destination)
    manifest=manifest_path(destination)
    require_new_database(destination)
    if manifest.exists():raise FileExistsError(manifest)
    if not source.is_file():raise FileNotFoundError(source)
    destination.parent.mkdir(parents=True,exist_ok=True)
    created=False;manifest_created=False
    try:
        with destination.open('xb'):created=True
        with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True)) as live:
            with closing(sqlite3.connect(destination)) as target:live.backup(target)
        report=inspect(destination)
        report.update(format='rtd-local-backup-v1',sha256=digest(destination),
                      created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        with manifest.open('x',encoding='utf-8') as stream:
            manifest_created=True;json.dump(report,stream,indent=2)
        return destination
    except BaseException:
        if manifest_created:manifest.unlink(missing_ok=True)
        if created:destination.unlink(missing_ok=True)
        raise


def restore_backup(backup,destination):
    backup=pathlib.Path(backup);destination=pathlib.Path(destination)
    require_new_database(destination)
    report=json.loads(manifest_path(backup).read_text(encoding='utf-8'))
    if (not isinstance(report,dict) or report.get('format')!='rtd-local-backup-v1'
            or report.get('sha256')!=digest(backup)):
        raise ValueError('Backup manifest or hash does not match')
    actual=inspect(backup)
    if any(report.get(k)!=v for k,v in actual.items()):raise ValueError('Backup metadata does not match')
    destination.parent.mkdir(parents=True,exist_ok=True)
    created=False
    try:
        with backup.open('rb') as source,destination.open('xb') as target:
            created=True;shutil.copyfileobj(source,target)
        if digest(destination)!=report['sha256']:raise ValueError('Restored file hash does not match')
        inspect(destination)
        return destination
    except BaseException:
        if created:destination.unlink(missing_ok=True)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('backup','restore'))
    parser.add_argument('source',type=pathlib.Path);parser.add_argument('destination',type=pathlib.Path)
    args=parser.parse_args()
    action=create_backup if args.operation=='backup' else restore_backup
    print(action(args.source,args.destination))


if __name__=='__main__':main()
