import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
class SpeciesSelectionTests(unittest.TestCase):
 def test_species_then_attribute_then_level(self):
  from prepare_species_recovery import choose_source
  pool=['ms01_sco_dark_02','ms01_bear_lv2_fire','ms01_sco_fire_02']
  self.assertEqual(choose_source('ms01_sco_lv3','fire',pool),'ms01_sco_fire_02')
 def test_exact_source_and_nearest_lower_level(self):
  from prepare_species_recovery import choose_source,scale_for
  self.assertEqual(choose_source('ms01_dra_lv2','water',['ms01_dra_lv1','ms01_dra_lv2']),'ms01_dra_lv2')
  self.assertEqual([scale_for('ms01_sco_lv'+str(n),'ms01_sco_lv1') for n in (2,3,4)],[1.3,1.6,1.9])
  self.assertAlmostEqual(scale_for('ms01_sco_lv3','ms01_sco_lv2'),1.6/1.3,places=6)
  self.assertEqual(scale_for('ms01_sco_lv2','ms01_sco_lv4'),1.)
 def test_recolor_keeps_alpha(self):
  from prepare_species_recovery import recolor
  from PIL import Image
  im=Image.new('RGBA',(2,1),(180,80,40,67));out=recolor(im,'water')
  self.assertEqual(out.getchannel('A').tobytes(),im.getchannel('A').tobytes())
  r,g,b,a=out.getpixel((0,0));self.assertGreater(b,r)
 def test_already_unbound_static_editor_position_is_preserved(self):
  from unittest.mock import patch
  from prepare_monster_recovery import validate_motion_paths
  curve={'path':'editor_offset','curve':{'m_Curve':[{'time':.3,'value':{'x':.15,'y':-.27,'z':35.3},'inSlope':{'x':0.,'y':0.,'z':0.},'outSlope':{'x':0.,'y':0.,'z':0.}}]}}
  trees={1:('GameObject',{'m_Name':'move'}),2:('Transform',{'m_GameObject':{'m_PathID':1},'m_Children':[]}),3:('Animation',{'m_GameObject':{'m_PathID':1},'m_Animations':[{'m_PathID':4}]}),4:('AnimationClip',{'m_Name':'source_clip','m_PositionCurves':[curve]})}
  with patch('prepare_monster_recovery.motion_paths',side_effect=ValueError('Original motions not found')):
   result=validate_motion_paths(trees,'ms01_neko','candidate',source_trees=trees)
  self.assertEqual(result['missing_motion_paths'],[])
  self.assertEqual(result['source_unbound_motion_paths'][0]['samples'][0],curve['curve']['m_Curve'][0])
 def test_only_unused_known_material_keyword_can_be_ignored(self):
  from prepare_monster_recovery import unused_brightness_keywords
  script='Shader "Character/brightness" { Blend SrcAlpha OneMinusSrcAlpha }'
  self.assertTrue(unused_brightness_keywords('_ALPHAPREMULTIPLY_ON',script))
  self.assertFalse(unused_brightness_keywords('_ALPHAPREMULTIPLY_ON',script+' Keywords { "_ALPHAPREMULTIPLY_ON" }'))
  self.assertFalse(unused_brightness_keywords('UNKNOWN',script))
 def test_dynamic_unbound_curve_is_still_rejected(self):
  import copy
  from unittest.mock import patch
  from prepare_monster_recovery import validate_motion_paths
  key={'time':0.,'value':{'x':1.,'y':0.,'z':0.},'inSlope':{'x':0.,'y':0.,'z':0.},'outSlope':{'x':0.,'y':0.,'z':0.}}
  curve={'path':'missing_dynamic_bone','curve':{'m_Curve':[key,{**copy.deepcopy(key),'time':1.}]}}
  trees={1:('GameObject',{'m_Name':'move'}),2:('Transform',{'m_GameObject':{'m_PathID':1},'m_Children':[]}),3:('Animation',{'m_GameObject':{'m_PathID':1},'m_Animations':[{'m_PathID':4}]}),4:('AnimationClip',{'m_Name':'source_clip','m_PositionCurves':[curve]})}
  with patch('prepare_monster_recovery.motion_paths',side_effect=ValueError('Original motions not found')):result=validate_motion_paths(trees,'ms01_neko','candidate',source_trees=trees)
  self.assertEqual(result['missing_motion_paths'],['missing_dynamic_bone'])
 def test_only_shader_identical_transparent_tag_is_redundant(self):
  from prepare_monster_recovery import redundant_transparent_tag
  script='Shader "Character/brightness" { Tags { "RenderType"="Transparent" } }'
  self.assertTrue(redundant_transparent_tag([('RenderType','Transparent')],script))
  self.assertFalse(redundant_transparent_tag([('RenderType','Opaque')],script))
  self.assertFalse(redundant_transparent_tag([('RenderType','Transparent')],script.replace('Transparent','Opaque')))
  self.assertFalse(redundant_transparent_tag([('Unknown','Transparent')],script))
 def test_segmented_boss_never_uses_another_body_part(self):
  from prepare_species_recovery import choose_source
  self.assertEqual(choose_source('ms04_dra_head_un_01','un',['610_ms04_dra_wing_u_01','610_ms04_dra_head_u_01']),'610_ms04_dra_head_u_01')
  self.assertIsNone(choose_source('ms04_dra_head_un_01','un',['610_ms04_dra_tail_u_01']))
