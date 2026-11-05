"""Rescale ONLY existing inferred level enlargements; preserve every other object byte."""
import argparse,copy,hashlib,json,shutil
from pathlib import Path
import UnityPy
from prepare_monster_recovery import ROOT
from prepare_species_recovery import scale_for
from prepare_squirrel_recovery import visual_scale
from prepare_wolf_closed_bundle import rebuild
from validate_backup_recovery import validate
OUT=ROOT/'resources/reconstructed/level-scale-v2'
REVISION='inferred-level-scale-1.3-1.6-1.9-v2'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def build():
 policy_path=ROOT/'config/monster-recovery.json';policy=json.loads(policy_path.read_text())
 if (OUT/'validation.json').exists() and any(r.get('scale_revision')==REVISION for r in policy['bundles']):
  raise RuntimeError('Revision already installed; original before-state is retained. Do not rescale twice.')
 OUT.mkdir(parents=True,exist_ok=True);(OUT/'bundles').mkdir(exist_ok=True);(OUT/'before').mkdir(exist_ok=True)
 rows=[];baseline={r['model']:r['sha256'] for r in policy['bundles']}
 shutil.copy2(policy_path,OUT/'before/manifest.json')
 for previous in policy['bundles']:
  old_scale=previous.get('visual_scale',1.)
  if old_scale<=1 or previous.get('scale_revision')==REVISION:continue
  model=previous['model'];assert previous.get('inferred'),model
  assert not (ROOT/'resources/bundles'/previous['bundle']).exists(),model
  assert previous.get('source_model')!=model,model
  new_scale=visual_scale(model) if model.startswith('ms01_squ_') else scale_for(model,previous['source_model'])
  assert new_scale>old_scale,(model,old_scale,new_scale)
  source=ROOT/'resources/reconstructed/monsters/bundles'/previous['bundle'];assert digest(source)==previous['sha256']
  old=OUT/'before'/source.name;shutil.copy2(source,old)
  env=UnityPy.load(str(old));objects={o.path_id:o for o in env.objects};raw={i:o.get_raw_data() for i,o in objects.items()}
  ab=next(o for o in env.objects if o.type.name=='AssetBundle');root=next(v['asset']['m_PathID'] for name,v in ab.read_typetree()['m_Container'] if name=='ast_'+model)
  transform=next(objects[p['m_PathID']] for _,p in objects[root].read_typetree()['m_Component'] if objects[p['m_PathID']].type.name=='Transform')
  tree=transform.read_typetree();before=copy.deepcopy(tree);tree['m_LocalScale']={k:v*new_scale/old_scale for k,v in tree['m_LocalScale'].items()};transform.save_typetree(tree)
  interim=OUT/source.name;interim.write_bytes(env.file.save());destination=OUT/'bundles'/source.name;info=rebuild(interim,destination,policy=REVISION)
  check={o.path_id:o for o in UnityPy.load(str(destination)).objects};assert set(check)==set(objects)
  for i,o in check.items():
   if i not in (ab.path_id,transform.path_id):assert o.get_raw_data()==raw[i],(model,i)
  after=check[transform.path_id].read_typetree();assert {k:v for k,v in before.items() if k!='m_LocalScale'}=={k:v for k,v in after.items() if k!='m_LocalScale'}
  for k,v in before['m_LocalScale'].items():assert abs(after['m_LocalScale'][k]-v*new_scale/old_scale)<1e-5
  assert info['internal_file']!=previous['internal_file'];validate(destination,info['sha256'])
  row={**previous,**info,'visual_scale':new_scale,'scale_revision':REVISION,'runtime_verified':False,'scale_adjustment':dict(previous_visual_scale=old_scale,previous_sha256=previous['sha256'],root_transform_id=transform.path_id,before_root_scale=before['m_LocalScale'],after_root_scale=after['m_LocalScale'],other_prefab_objects_byte_identical=True)}
  rows.append(row);print('Rescaled',model,old_scale,'->',new_scale,flush=True)
 assert rows,'No unadjusted inferred enlargements found'
 (OUT/'validation.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
 (OUT/'baseline.json').write_text(json.dumps(baseline,indent=2)+'\n')
def install():
 rows=json.loads((OUT/'validation.json').read_text());baseline=json.loads((OUT/'baseline.json').read_text());path=ROOT/'config/monster-recovery.json';policy=json.loads(path.read_text());current={r['model']:r for r in policy['bundles']}
 assert {m:r['sha256'] for m,r in current.items()}==baseline,'Manifest changed after candidate build'
 for row in rows:validate(OUT/'bundles'/row['bundle'],row['sha256'])
 for row in rows:
  shutil.copy2(OUT/'bundles'/row['bundle'],ROOT/'resources/reconstructed/monsters/bundles'/row['bundle']);current[row['model']]=row
  manifests=[ROOT/'resources/reconstructed/squirrel-recovery/validation.json'] if row['model'].startswith('ms01_squ_') else list((ROOT/'resources/reconstructed/species-recovery').glob('*/validation.json'))
  matches=[]
  for manifest in manifests:
   entries=json.loads(manifest.read_text())
   if any(r['model']==row['model'] for r in entries):matches.append((manifest,entries))
  assert len(matches)==1,row['model']
  manifest,entries=matches[0];shutil.copy2(OUT/'bundles'/row['bundle'],manifest.parent/'bundles'/row['bundle']);entries=[row if r['model']==row['model'] else r for r in entries];manifest.write_text(json.dumps(entries,ensure_ascii=False,indent=2)+'\n')
 policy['bundles']=[current[k] for k in sorted(current)];policy['inferred_level_scale_revision']=REVISION
 payload=json.dumps(policy,ensure_ascii=False,indent=2)+'\n';path.write_text(payload);(ROOT/'resources/reconstructed/monsters/manifest.json').write_text(payload)
 for model,sha in baseline.items():
  if model not in {r['model'] for r in rows}:assert current[model]['sha256']==sha
 print('Installed only',len(rows),'inferred enlargements locally.',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--install',action='store_true');args=p.parse_args();install() if args.install else build()
