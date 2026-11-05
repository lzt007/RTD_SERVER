"""Install locally validated squirrel candidates, retaining all prior models."""
import hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def install():
 import subprocess,sys
 subprocess.run([sys.executable,'-m','unittest','tests.test_squirrel_recovery.SquirrelTests.test_levels_and_shadow_alpha','tests.test_squirrel_recovery.SquirrelTests.test_built_bundles_closed_scaled_and_shadow_bound'],cwd=ROOT,check=True)
 source=ROOT/'resources/reconstructed/squirrel-recovery';rows=json.loads((source/'validation.json').read_text());config=ROOT/'config/monster-recovery.json';policy=json.loads(config.read_text());destination=ROOT/'resources/reconstructed/monsters'
 for row in rows:
  path=source/'bundles'/row['bundle']
  if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Hash mismatch')
  if (ROOT/'resources/bundles'/row['bundle']).exists():raise ValueError('Original would be shadowed')
 backup=source/'before-install';backup.mkdir(exist_ok=True)
 if not (backup/'manifest.json').exists():shutil.copy2(config,backup/'manifest.json')
 by_model={r['model']:r for r in policy['bundles']}
 for row in rows:
  target=destination/'bundles'/row['bundle']
  if target.exists() and not (backup/row['bundle']).exists():shutil.copy2(target,backup/row['bundle'])
  shutil.copy2(source/'bundles'/row['bundle'],target);by_model[row['model']]=row
 policy['bundles']=[by_model[k] for k in sorted(by_model)];policy['squirrel_revision']='squirrel-original-lv1-v1'
 payload=json.dumps(policy,ensure_ascii=False,indent=2)+'\n';config.write_text(payload);(destination/'manifest.json').write_text(payload)
 print('Installed seven squirrel candidates locally; runtime verification pending.')
if __name__=='__main__':install()
