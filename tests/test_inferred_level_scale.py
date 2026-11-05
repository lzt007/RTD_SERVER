"""Verify only missing-level inferred sizes changed, with geometry/material bytes intact."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
class InferredScaleTests(unittest.TestCase):
 def test_exact_and_unscaled_models_remain_identical(self):
  from rescale_inferred_levels import OUT
  before=json.loads((OUT/'before/manifest.json').read_text());after=json.loads((ROOT/'config/monster-recovery.json').read_text());old={r['model']:r for r in before['bundles']};new={r['model']:r for r in after['bundles']};changed={r['model'] for r in json.loads((OUT/'validation.json').read_text())}
  expected={m for m,r in old.items() if r.get('visual_scale',1)>1};self.assertEqual(changed,expected);self.assertEqual(set(old),set(new));self.assertEqual(len(changed),17)
  for model,row in old.items():
   if model not in changed:
    # Later evidence-only corrections do not change an asset or its size.
    old_record=dict(row);new_record=dict(new[model])
    if model=='ms03_sen_olgadia_01':
     self.assertEqual(new_record['motion_provenance'],'validated_original_apk_type33')
     self.assertEqual(new_record['original_motion_clips'],['org_atk_swd_01','org_wait_swd_01'])
     for key in ('motion_provenance','original_motion_clips'):
      old_record.pop(key,None);new_record.pop(key,None)
    self.assertEqual(old_record,new_record);self.assertEqual(hashlib.sha256((ROOT/'resources/reconstructed/monsters/bundles'/row['bundle']).read_bytes()).hexdigest(),row['sha256'])
 def test_root_scale_only_and_independent_cab(self):
  import UnityPy
  from rescale_inferred_levels import OUT
  from validate_backup_recovery import validate
  for row in json.loads((OUT/'validation.json').read_text()):
   with self.subTest(model=row['model']):
    old={o.path_id:o for o in UnityPy.load(str(OUT/'before'/row['bundle'])).objects};new={o.path_id:o for o in UnityPy.load(str(OUT/'bundles'/row['bundle'])).objects};proof=row['scale_adjustment'];tid=proof['root_transform_id']
    self.assertTrue(row['inferred']);self.assertFalse((ROOT/'resources/bundles'/row['bundle']).exists());self.assertEqual(set(old),set(new))
    for i,obj in old.items():
     if obj.type.name!='AssetBundle' and i!=tid:self.assertEqual(obj.get_raw_data(),new[i].get_raw_data())
    before=old[tid].read_typetree();after=new[tid].read_typetree();self.assertEqual({k:v for k,v in before.items() if k!='m_LocalScale'},{k:v for k,v in after.items() if k!='m_LocalScale'})
    tier=next(n for n in (2,3,4) if '_lv'+str(n) in row['model']);desired={2:1.3,3:1.6,4:1.9}[tier];self.assertEqual(row['visual_scale'],desired)
    for k,v in before['m_LocalScale'].items():self.assertAlmostEqual(after['m_LocalScale'][k],v*desired/proof['previous_visual_scale'],places=5)
    native=validate(OUT/'bundles'/row['bundle'],row['sha256']);self.assertEqual(native['internal_file'],row['internal_file'])
