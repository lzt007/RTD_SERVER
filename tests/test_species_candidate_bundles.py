"""Independent gate for the per-species generated assets, never assumes runtime success."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
class CandidateTests(unittest.TestCase):
 def test_every_generated_export_is_closed_and_native(self):
  from validate_backup_recovery import validate
  manifests=sorted((ROOT/'resources/reconstructed/species-recovery').glob('*/validation.json'));self.assertTrue(manifests)
  identities=set();count=0
  for manifest in manifests:
   for row in json.loads(manifest.read_text()):
    with self.subTest(model=row['model']):
     proof=validate(manifest.parent/'bundles'/row['bundle'],row['sha256'])
     self.assertNotIn(proof['internal_file'],identities);identities.add(proof['internal_file'])
     self.assertTrue(row['mesh_roundtrip']);self.assertTrue(row['texture_roundtrip'])
     self.assertEqual(row['missing_pointers'],[]);self.assertEqual(row['missing_motion_paths'],[])
     self.assertGreaterEqual(row['visual_scale'],1.);self.assertLessEqual(row['visual_scale'],1.9)
     self.assertFalse(row['runtime_verified']);count+=1
  self.assertGreater(count,0)
 def test_installed_effective_changes_only_restore_original_visuals(self):
  import copy,os
  from unittest.mock import patch
  from rtd.masters.catalog import load_catalog
  from rtd.policies.monster_recovery import apply_monster_recovery
  raw,levels=load_catalog();masters=copy.deepcopy(raw)
  models={r['model'] for r in json.loads((ROOT/'config/monster-recovery.json').read_text())['bundles']}
  for row in masters[20]['data_list']:
   if row['model'] in models:row.update(model='ms02_four_un_01_zako',texture='na')
  before=copy.deepcopy(masters);quest_ids={r['id'] for r in raw[30]['data_list']};levels={**levels,**{qid:{'audit_only':True} for qid in quest_ids if qid not in levels}}
  with patch.dict(os.environ,{'RTD_MONSTER_RECOVERY':'1'}):report=apply_monster_recovery(masters,levels,quest_ids)
  original={r['id']:r for r in raw[20]['data_list']};old={r['id']:r for r in before[20]['data_list']}
  for row in masters[20]['data_list']:
   self.assertEqual({k:v for k,v in row.items() if k not in ('model','texture')},{k:v for k,v in old[row['id']].items() if k not in ('model','texture')})
   if row!=old[row['id']]:self.assertEqual(row,original[row['id']])
  for k in masters:
   if k!=20:self.assertEqual(masters[k],before[k])
 def test_watermelon_head_is_render_bound_with_identical_rest_basis(self):
  import UnityPy
  out=ROOT/'resources/reconstructed/species-recovery/ms01_suika'
  original=UnityPy.load(str(ROOT.parent/'resources/unpacked/assets/assets/quest/ms01_suika_01.unity3d'));adapted=UnityPy.load(str(out/'sources/suika-head-source.unity3d'))
  old={o.path_id:o for o in original.objects};new={o.path_id:o for o in adapted.objects}
  row=json.loads((out/'validation.json').read_text())[0];proof=next(p for p in row['skeleton_adaptations'] if p['kind']=='suika-real-head-binding-v1');head=new[proof['new_head_transform']].read_typetree()
  self.assertEqual(head['m_LocalPosition'],dict(x=0.,y=0.,z=0.));self.assertEqual(head['m_LocalRotation'],dict(x=0.,y=0.,z=0.,w=1.));self.assertEqual(head['m_LocalScale'],dict(x=1.,y=1.,z=1.))
  for i in proof['renderer_ids']:
   before=old[i].read_typetree();after=new[i].read_typetree()
   self.assertTrue(all(p['m_PathID']==head['m_Father']['m_PathID'] for p in before['m_Bones']))
   self.assertTrue(all(p['m_PathID']==proof['new_head_transform'] for p in after['m_Bones']))
   self.assertEqual({k:v for k,v in before.items() if k!='m_Bones'},{k:v for k,v in after.items() if k!='m_Bones'})
  for i,o in old.items():
   if o.type.name in ('Mesh','Texture2D','AnimationClip','Material','Shader'):self.assertEqual(o.get_raw_data(),new[i].get_raw_data())
 def test_native_animation_controller_script_hash_and_fields(self):
  import UnityPy
  from prepare_monster_recovery import native_animation_controller_templates
  source=native_animation_controller_templates();native_script=source['MonoScript'].read_typetree();fields=set(source['MonoBehaviour'].read_typetree())
  path=ROOT/'resources/reconstructed/species-recovery/ms01_akb/bundles/ms01_akb_dra_fire_01.unity3d'
  env=UnityPy.load(str(path));objects={o.path_id:o for o in env.objects};scripts=[o for o in env.objects if o.type.name=='MonoScript'];self.assertTrue(scripts)
  for o in scripts:self.assertEqual(o.read_typetree(),native_script)
  for o in env.objects:
   if o.type.name=='MonoBehaviour':
    tree=o.read_typetree();self.assertEqual(set(tree),fields);self.assertEqual(objects[tree['m_Script']['m_PathID']].read_typetree(),native_script)
 def test_spirit_boss_adapter_preserves_actual_rest_world_matrices(self):
  import UnityPy,numpy as np
  from validate_wolf_cpu_skin import matrix
  directory=ROOT/'resources/reconstructed/species-recovery/ms03_mind'
  row=json.loads((directory/'validation.json').read_text())[0]
  proof=next(p for p in row['skeleton_adaptations'] if p['kind']=='mind-boss-bear-controls-v1')
  before={o.path_id:o for o in UnityPy.load(str(ROOT.parent/proof['original_source'])).objects}
  after={o.path_id:o for o in UnityPy.load(str(ROOT.parent/row['source'])).objects}
  def worlds(objects):
   transforms={i:o.read_typetree() for i,o in objects.items() if o.type.name=='Transform'};cache={0:np.eye(4)}
   def world(i):
    if i not in cache:cache[i]=world(transforms[i]['m_Father']['m_PathID'])@matrix(transforms[i])
    return cache[i]
   return {i:world(i) for i in transforms}
  old_world=worlds(before);new_world=worlds(after)
  for i,value in old_world.items():np.testing.assert_allclose(value,new_world[i],atol=1e-7)
  for i,o in before.items():
   if o.type.name in ('Mesh','SkinnedMeshRenderer','Texture2D','Material','Shader'):self.assertEqual(o.get_raw_data(),after[i].get_raw_data())
  for i in proof['added_identity_bone_ids']:np.testing.assert_allclose(matrix(after[i].read_typetree()),np.eye(4),atol=1e-7)
 def test_fish_exception_binds_real_skin_without_changing_rest_basis(self):
  import UnityPy,numpy as np
  from validate_wolf_cpu_skin import matrix
  directory=ROOT/'resources/reconstructed/species-recovery/ms01_fish'
  for row in json.loads((directory/'validation.json').read_text()):
   self.assertTrue(row['cross_species_fallback'])
   proof=next(p for p in row['skeleton_adaptations'] if p['kind']=='onepiece-fish-controls-v1')
   original={o.path_id:o for o in UnityPy.load(str(ROOT.parent/proof['original_source'])).objects}
   adapted={o.path_id:o for o in UnityPy.load(str(ROOT.parent/row['source'])).objects}
   def worlds(objects):
    transforms={i:o.read_typetree() for i,o in objects.items() if o.type.name=='Transform'};cache={0:np.eye(4)}
    def world(i):
     if i not in cache:cache[i]=world(transforms[i]['m_Father']['m_PathID'])@matrix(transforms[i])
     return cache[i]
    return {i:world(i) for i in transforms}
   before_world=worlds(original);after_world=worlds(adapted);self.assertTrue(proof['head_bound_renderers'])
   for i in proof['head_bound_renderers']:
    before=original[i].read_typetree();after=adapted[i].read_typetree()
    self.assertEqual({k:v for k,v in before.items() if k!='m_Bones'},{k:v for k,v in after.items() if k!='m_Bones'})
    for old,new in zip(before['m_Bones'],after['m_Bones']):np.testing.assert_allclose(before_world[old['m_PathID']],after_world[new['m_PathID']],atol=1e-7)
   for i,o in original.items():
    if o.type.name in ('Mesh','Texture2D','Material','Shader'):self.assertEqual(o.get_raw_data(),adapted[i].get_raw_data())
 def test_exact_multimaterial_boss_keeps_each_original_texture_binding(self):
  import UnityPy
  directory=ROOT/'resources/reconstructed/species-recovery/ms03_sen';row=next(r for r in json.loads((directory/'validation.json').read_text()) if r['model']=='ms03_sen_olgadia_01')
  self.assertEqual(row['source_model'],row['model'])
  def bindings(path):
   objects={o.path_id:o for o in UnityPy.load(str(path)).objects};result={}
   for o in objects.values():
    if o.type.name!='Material':continue
    t=o.read_typetree()
    for key,value in t['m_SavedProperties']['m_TexEnvs']:
     if key['name']=='_MainTex' and value['m_Texture']['m_PathID']:result[t['m_Name']]=objects[value['m_Texture']['m_PathID']].read_typetree()['m_Name']
   return result
  original=bindings(ROOT.parent/row['source']);converted=bindings(directory/'bundles'/row['bundle']);self.assertTrue(converted)
  for material,texture in converted.items():self.assertEqual(texture,original[material])
 def test_all_creature_models_have_audited_coverage_and_same_lineage(self):
  from prepare_species_recovery import family,lineage
  raw=json.loads((ROOT/'resources/master-data/ENEMY_UNIT_MASTER.json').read_text())['result'][0]['data_list']
  apk=json.loads((ROOT/'docs/resource-audit/全种族APK内置扫描.json').read_text())
  native={o['name'].removeprefix('ast_') for o in apk[0]['objects'] if o['type']=='GameObject'}
  rows=[r for p in (ROOT/'resources/reconstructed/species-recovery').glob('*/validation.json') for r in json.loads(p.read_text())]
  provided={r['model'] for r in rows}|native|{p.stem for p in (ROOT/'resources/bundles').glob('*.unity3d')}
  provided|={r['model'] for r in json.loads((ROOT/'resources/reconstructed/squirrel-recovery/validation.json').read_text())}
  wanted={r['model'] for r in raw if family(r['model']) and family(r['model']) not in ('ms00_floor','ms00_wall','ms00_kaidan')}
  self.assertEqual(sorted(wanted-provided),[])
  for row in rows:
   if row.get('cross_species_fallback'):self.assertEqual(family(row['model']),'ms01_fish')
   else:self.assertEqual(lineage(row['model']),lineage(row['source_model']))
