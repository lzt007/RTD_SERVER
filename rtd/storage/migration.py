"""Ordered SQL migrations, applied atomically under a database write lock."""
import hashlib
from pathlib import Path
import sqlite3


def migrate(db, directory=None):
    scripts = []
    for path in Path(directory or Path(__file__).with_name('migrations')).glob('V*__*.sql'):
        source = path.read_text(encoding='utf-8')
        scripts.append((int(path.name.split('__')[0][1:]), path.name, source,
                        hashlib.sha256(source.encode()).hexdigest()))
    scripts.sort()
    if not scripts or [s[0] for s in scripts] != list(range(1, len(scripts)+1)):
        raise RuntimeError('Migration versions must be unique and contiguous from 1')
    db.execute('BEGIN IMMEDIATE')
    try:
        current = db.execute('PRAGMA user_version').fetchone()[0]
        if current > scripts[-1][0]:
            raise RuntimeError('Database schema is newer than this server')
        db.execute('CREATE TABLE IF NOT EXISTS schema_history (version INTEGER PRIMARY KEY, '
                   'name TEXT NOT NULL, checksum TEXT NOT NULL, '
                   'installed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
        history = {r[0]: r[1:] for r in db.execute('SELECT version,name,checksum FROM schema_history')}
        if any(v > current for v in history):
            raise RuntimeError('Schema history disagrees with user_version')
        for version, name, source, checksum in scripts:
            if version in history:
                if history[version] != (name, checksum):
                    raise RuntimeError('Applied migration changed: ' + name)
                continue
            if version > current:
                statement = ''
                for char in source:
                    statement += char
                    if char == ';' and sqlite3.complete_statement(statement):
                        db.execute(statement)
                        statement = ''
                if statement.strip():
                    db.execute(statement)
                db.execute('PRAGMA user_version=' + str(version))
            db.execute('INSERT INTO schema_history(version,name,checksum) VALUES(?,?,?)',
                       (version, name, checksum))
        db.commit()
    except BaseException:
        db.rollback()
        raise
