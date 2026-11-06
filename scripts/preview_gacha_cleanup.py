"""Offline preview: input snapshot contains effective masters/levels/playable/overrides/pools.

Export snapshot from the running deployment's effective configuration using a
read-only connection. This script never opens a database or mutates inputs.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rtd.policies.gacha_cleanup import exclusions,clean_pools


def preview(snapshot):
    masters={int(k):v for k,v in snapshot['masters'].items()}
    levels={int(k):v for k,v in snapshot['levels'].items()}
    overrides={(r['quest_id'],r['drop_data_id']):r['entries'] for r in snapshot.get('overrides',[])}
    reasons=exclusions(masters,levels,set(snapshot['playable']),overrides)
    pools,report=clean_pools(snapshot['pools'],reasons)
    roots={u['id'] for u in masters[10]['data_list'] if any(v for k,v in u.items() if k=='rev_unit_id' or k.startswith('ultimate_rev_unit_id_'))}-set(reasons)
    return dict(pools=pools,report=report,excluded={str(k):v for k,v in sorted(reasons.items())},
                absent_chain_roots={name:sorted(roots-{r['unit_id'] for r in rows}) for name,rows in snapshot['pools'].items()})

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot',type=Path);parser.add_argument('output',type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(preview(json.loads(args.snapshot.read_text())),ensure_ascii=False,indent=2)+'\n')
