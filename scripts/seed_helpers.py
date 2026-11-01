"""Initialize helpers in an explicitly selected database."""
import argparse
import pathlib
import sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from rtd.services.api import API
from rtd.services.npc_accounts import seed

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True,type=pathlib.Path)
    parser.add_argument('--allow-production',action='store_true',help='Explicitly permit the production directory')
    args=parser.parse_args()
    path=args.database.resolve()
    if (path==pathlib.Path('/home/RTD_SERVER') or pathlib.Path('/home/RTD_SERVER') in path.parents) and not args.allow_production:
        parser.error('Production database is outside this development command scope')
    print('Helper account IDs:',seed(API(path)))
