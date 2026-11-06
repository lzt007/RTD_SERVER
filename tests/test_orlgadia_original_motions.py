"""Actual original APK clips must bind the converted unit-boss hierarchy."""
import json,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class OrlgadiaMotionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  subprocess.run([sys.executable,str(ROOT/'scripts/audit_orlgadia_motions.py')],cwd=ROOT,check=True,stdout=subprocess.DEVNULL)
  cls.proof=json.loads((ROOT/'docs/resource-audit/orlgadia-original-motion-audit.json').read_text())
 def test_original_wait_attack_bind_real_move_hierarchy(self):
  for name in ('org_wait_swd_01','org_atk_swd_01'):
   self.assertEqual(len(self.proof[name]['required']),19);self.assertEqual(self.proof[name]['missing_from_move'],[])
 def test_battle_direction_clips_bind_prefab_root(self):
  for name in ('el_boss_tob','el_boss_tob_6'):
   self.assertEqual(self.proof[name]['required'],['']);self.assertEqual(self.proof[name]['missing_from_root'],[])
 def test_run_typo_is_reported_not_hidden(self):
  missing=self.proof['ms03_org_run_01']['missing_from_move'];self.assertEqual(len(missing),2);self.assertTrue(all(p.endswith('_anckle') for p in missing))
 def test_converter_uses_exact_original_type33_clips(self):
  import UnityPy
  sys.path.insert(0,str(ROOT/'scripts'))
  from prepare_monster_recovery import validate_motion_paths
  env=UnityPy.load(str(ROOT/'resources/reconstructed/monsters/bundles/ms03_sen_olgadia_01.unity3d'));trees={o.path_id:(o.type.name,o.read_typetree()) for o in env.objects}
  result=validate_motion_paths(trees,'ms03_sen','ms03_sen_olgadia_01')
  self.assertEqual(result['motion_provenance'],'validated_original_apk_type33')
  self.assertEqual(result['original_motion_clips'],['org_atk_swd_01','org_wait_swd_01'])
  self.assertEqual(result['missing_motion_paths'],[])
