"""Compatibility entrypoint for reviewed subtraction proposals, never pool replacement."""
import argparse
import datetime
import json
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.apply_gacha_cleanup import apply


def migrate(database, *, proposal=None, expected_revision=None):
    if proposal is None or expected_revision is None:
        raise ValueError('Reviewed cleanup proposal and expected_revision required; automatic pool regeneration is disabled')
    database=Path(database)
    if not database.is_file():raise ValueError('Database does not exist')
    backup=database.with_name(database.name+'.gacha-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.bak')
    with sqlite3.connect(database) as source, sqlite3.connect(backup) as dest:source.backup(dest)
    changed=apply(database,proposal,expected_revision)
    return dict(backup=str(backup),revision=expected_revision+int(changed),changed=changed)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True);parser.add_argument('--proposal',required=True,type=Path)
    parser.add_argument('--expected-revision',required=True,type=int)
    args=parser.parse_args()
    print(json.dumps(migrate(args.database,proposal=json.loads(args.proposal.read_text()),expected_revision=args.expected_revision)))
