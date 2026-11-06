"""Apply reviewed subtraction proposal offline; explicit revision and DB required."""
import argparse
import copy
import json
import sqlite3
from pathlib import Path


def apply(database,proposal,expected_revision):
    with sqlite3.connect(database) as db:
        db.execute('BEGIN IMMEDIATE')
        config=json.loads(db.execute('SELECT document FROM runtime_config WHERE id=1').fetchone()[0])
        if config['revision']!=expected_revision:raise ValueError('Runtime revision changed; regenerate preview')
        updated=copy.deepcopy(config)
        for pool in updated['gachas']:
            key=str(pool['id'])
            entries=proposal['pools'][key]
            original=pool['entries']
            if not entries or entries!=[r for r in original if r['unit_id'] in {e['unit_id'] for e in entries}]:
                raise ValueError('Proposal must be a nonempty exact subtraction preserving weights and order')
            expected=proposal['report'][key]['before']
            if len(original)!=expected:raise ValueError('Original pool size changed')
            pool['entries']=entries
        if updated==config:return False
        updated['revision']+=1
        db.execute('UPDATE runtime_config SET document=? WHERE id=1',(json.dumps(updated,separators=(',',':')),))
        return True

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',required=True);p.add_argument('--proposal',required=True,type=Path);p.add_argument('--expected-revision',required=True,type=int)
    a=p.parse_args();print(json.dumps(dict(changed=apply(a.database,json.loads(a.proposal.read_text()),a.expected_revision))))
