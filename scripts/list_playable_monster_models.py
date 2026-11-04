"""Enumerate wolf/slime preload references for currently supported quest scopes."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def collect():
    # Audit original references, never feed the inferred overlay back into itself.
    os.environ['RTD_MONSTER_RECOVERY']='0'
    from rtd.services.api import API
    from rtd.masters.catalog import load_catalog
    from rtd.policies.monster_recovery import referenced_enemies
    from rtd.policies.event_content import single_quests
    from rtd.policies.quest_content import layer_quests
    with tempfile.TemporaryDirectory() as tmp:api=API(Path(tmp)/'audit.db')
    raw,_=load_catalog();enemies={r['id']:r for r in raw[20]['data_list']}
    used=referenced_enemies(api.masters,api.levels,(single_quests(api)|layer_quests(api)|{10000})-api.blocked_quests)
    found={}
    for eid in used:
        row=enemies.get(eid)
        if row and any(name in row['model'] for name in ('wolf','sla_','slawing')):
            found.setdefault(row['model'],set()).add(row['texture'])
    return {k:sorted(v) for k,v in sorted(found.items())}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();models=collect()
    args.output.write_text(json.dumps(models,ensure_ascii=False,indent=2)+'\n')
    print(f'{len(models)} wolf/slime model references; no other species included')
