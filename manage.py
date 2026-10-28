"""Read account summaries or create a consistent online SQLite backup."""
import argparse
import datetime
import json
import pathlib
import sqlite3
from contextlib import closing
from rtd.config import ROOT, path_for

p = argparse.ArgumentParser()
p.add_argument('action', choices=['list','backup'])
p.add_argument('--database', type=pathlib.Path, default=path_for('database'))
p.add_argument('--output', type=pathlib.Path)
args = p.parse_args()
if not args.database.is_absolute(): args.database=ROOT/args.database
if args.output is not None and not args.output.is_absolute(): args.output=ROOT/args.output
with closing(sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro', uri=True)) as db:
    if args.action == 'list':
        for uid, state_json in db.execute('SELECT id,state FROM players ORDER BY id'):
            state = json.loads(state_json)
            print(json.dumps(dict(user_id=uid, name=state['player']['user_name'],
                starter=state['starter'], units=len(state['units']), last_login=state['last_login']),
                ensure_ascii=True))
    else:
        output = args.output or path_for('backups')/datetime.datetime.now().strftime('rtd-%Y%m%d-%H%M%S.sqlite3')
        output.parent.mkdir(parents=True, exist_ok=True)
        # Never overwrite an earlier snapshot.
        with output.open('xb'):
            pass
        with closing(sqlite3.connect(output)) as target:
            db.backup(target)
        print(output)
