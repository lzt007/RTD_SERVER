"""Run from server root, after stopping the service. Backs up SQLite first."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from contextlib import closing
import argparse
import copy
import datetime
import json
import sqlite3
from rtd.config import path_for
from rtd.masters.catalog import load_catalog
from rtd.policies.gacha_pools import load_pools
from rtd.policies.summon_catalog import build_pools


def migrate(database):
    masters,_=load_catalog();pools,report=build_pools(masters)
    configured,_=load_pools(masters)
    if any(configured[k]!=pools[k] for k in ('normal','rare')):
        raise ValueError('Default pool file differs from generated policy')
    database=Path(database)
    if not database.is_file():raise ValueError('Database does not exist')
    with closing(sqlite3.connect(database)) as db:
        backup=database.with_name(database.name+'.gacha-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.bak')
        with closing(sqlite3.connect(backup)) as dest:db.backup(dest)
        db.execute('BEGIN IMMEDIATE')
        row=db.execute('SELECT document FROM runtime_config WHERE id=1').fetchone()
        if row is None:raise ValueError('Missing runtime configuration')
        config=json.loads(row[0])
        # Runtime event overrides can also grant units; include even closed events.
        extra={r['unit_id'] for e in config['events'] for q in e['quests'] for d in q['drops'] for r in d['entries'] if r['weight']>0}
        material=set(report['material_ids'])
        if extra-material-set(report['excluded_ids']):
            raise ValueError('Runtime event adds additional obtainable units; regenerate policy before migration: '+str(sorted(extra-material-set(report['excluded_ids']))))
        changed=False
        for pool in config['gachas']:
            entries=pools['rare' if pool['id']==20000 else 'normal']
            if pool['entries']!=entries:pool['entries']=copy.deepcopy(entries);changed=True
        if changed:
            config['revision']+=1
            db.execute('UPDATE runtime_config SET document=? WHERE id=1',(json.dumps(config,separators=(',',':')),))
        db.commit()
    return dict(backup=str(backup),revision=config['revision'],changed=changed,counts=report['counts'])

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--database',default=str(path_for('database')))
    args=parser.parse_args();print(json.dumps(migrate(args.database),ensure_ascii=False))
