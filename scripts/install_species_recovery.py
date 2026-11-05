"""Validate then merge one species into local recovery policy. No service/deployment changes."""
import argparse,hashlib,json,shutil
from pathlib import Path
from prepare_monster_recovery import ROOT
from validate_backup_recovery import validate

def install(species):
 directory=ROOT/'resources/reconstructed/species-recovery'/species;rows=json.loads((directory/'validation.json').read_text());assert rows,'No validated candidates'
 policy_path=ROOT/'config/monster-recovery.json';policy=json.loads(policy_path.read_text());by_model={r['model']:r for r in policy['bundles']};identities=set()
 for row in rows:
  if row.get('status')!='validated_candidate':raise ValueError('Candidate has not passed validation')
  if not row['mesh_roundtrip'] or not row['texture_roundtrip'] or row['missing_pointers'] or row['missing_motion_paths']:raise ValueError('Incomplete evidence')
  if (ROOT/'resources/bundles'/row['bundle']).exists():raise ValueError('Original bundle exists')
  proof=validate(directory/'bundles'/row['bundle'],row['sha256'])
  if proof['internal_file'] in identities:raise ValueError('Duplicate CAB')
  identities.add(proof['internal_file'])
 backup=directory/'before-install';backup.mkdir(exist_ok=True)
 if not (backup/'manifest.json').exists():shutil.copy2(policy_path,backup/'manifest.json')
 destination=ROOT/'resources/reconstructed/monsters'
 for row in rows:
  target=destination/'bundles'/row['bundle']
  if target.exists() and not (backup/row['bundle']).exists():shutil.copy2(target,backup/row['bundle'])
  shutil.copy2(directory/'bundles'/row['bundle'],target);by_model[row['model']]=row
 policy['bundles']=[by_model[k] for k in sorted(by_model)];policy.setdefault('species_revisions',{})[species]='species-attribute-level-v1'
 payload=json.dumps(policy,ensure_ascii=False,indent=2)+'\n';policy_path.write_text(payload);(destination/'manifest.json').write_text(payload)
 print('Installed species locally',species,len(rows),flush=True)
 return len(rows)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('species');args=p.parse_args();install(args.species)
