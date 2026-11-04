import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('recovery_motion',Path(__file__).resolve().parents[1]/'scripts/prepare_monster_recovery.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class BackupMotionTests(unittest.TestCase):
    def trees(self,path):
        return {1:('GameObject',{'m_Name':'root'}),2:('Transform',{'m_GameObject':{'m_PathID':1},'m_Children':[{'m_PathID':4}]}),3:('GameObject',{'m_Name':'bone'}),4:('Transform',{'m_GameObject':{'m_PathID':3},'m_Children':[]}),5:('Animation',{'m_GameObject':{'m_PathID':1},'m_Animations':[{'m_PathID':6}]}),6:('AnimationClip',{'m_Name':'wait','m_PositionCurves':[{'path':path}]})}
    def test_embedded_owner_binding(self):
        with patch.object(m,'motion_paths',side_effect=ValueError('Original motions not found')):
            self.assertEqual([],m.validate_motion_paths(self.trees('bone'),'bird','x')['missing_motion_paths'])
            self.assertEqual(['wrong'],m.validate_motion_paths(self.trees('wrong'),'bird','x')['missing_motion_paths'])
    def test_original_missing_hierarchy_is_failure(self):
        with patch.object(m,'motion_paths',return_value={'bone'}):
            result=m.validate_motion_paths(self.trees('bone'),'bear','x')
            self.assertIn('no move hierarchy for original runtime clips',result['missing_motion_paths'])

class MotionRoundtripTests(unittest.TestCase):
    def env(self, tree):
        from types import SimpleNamespace
        return SimpleNamespace(objects=[SimpleNamespace(path_id=7,type=SimpleNamespace(name='AnimationClip'),read_typetree=lambda:tree)])
    def clip(self):
        return dict(m_Name='wait',m_Legacy=True,m_Compressed=False,m_SampleRate=60.,m_WrapMode=0,m_PositionCurves=[dict(path='bone',curve=dict(m_Curve=[dict(time=0.,value=dict(x=1.,y=0.,z=0.))]))])
    def test_preserves_samples_and_rejects_loss(self):
        import copy
        source=self.clip();target=copy.deepcopy(source)
        self.assertTrue(m.validate_embedded_motion_roundtrip(self.env(source),self.env(target))['embedded_motion_roundtrip'])
        target['m_PositionCurves'][0]['curve']['m_Curve']=[]
        with self.assertRaisesRegex(ValueError,'curve/packed-data loss'):
            m.validate_embedded_motion_roundtrip(self.env(source),self.env(target))
    def test_rejects_empty_clip(self):
        source=self.clip();source['m_PositionCurves']=[]
        with self.assertRaisesRegex(ValueError,'no supported animation samples'):
            m.validate_embedded_motion_roundtrip(self.env(source),self.env(source))
    def test_packed_rotation_loss(self):
        import copy
        source=self.clip();source['m_CompressedRotationCurves']=[dict(path='bone',times={'m_Data':[1,2]},values={'m_Data':[3,4]})]
        target=copy.deepcopy(source);target['m_CompressedRotationCurves'][0]['values']['m_Data']=[0]
        with self.assertRaisesRegex(ValueError,'packed-data loss'):
            m.validate_embedded_motion_roundtrip(self.env(source),self.env(target))

class SourceUnboundTests(BackupMotionTests):
    def scale_trees(self):
        trees=self.trees('bone')
        trees[6][1]['m_PositionCurves']=[]
        trees[6][1]['m_ScaleCurves']=[dict(path='historical_missing_node',curve=dict(m_Curve=[dict(time=.3,value=dict(x=.9,y=.9,z=1.),inSlope=dict(x=0.,y=0.,z=0.),outSlope=dict(x=0.,y=0.,z=0.))]))]
        return trees
    def check(self,source,target):
        with patch.object(m,'motion_paths',side_effect=ValueError('Original motions not found')):
            return m.validate_motion_paths(target,'bird','x',source_trees=source)
    def test_constant_source_unbound_is_recorded(self):
        import copy
        source=self.scale_trees();result=self.check(source,copy.deepcopy(source))
        self.assertEqual([],result['missing_motion_paths'])
        self.assertEqual(.9,result['source_unbound_motion_paths'][0]['samples'][0]['value']['x'])
    def test_changed_value_is_rejected(self):
        import copy
        source=self.scale_trees();target=copy.deepcopy(source)
        target[6][1]['m_ScaleCurves'][0]['curve']['m_Curve'][0]['value']['x']=.8
        self.assertEqual(['historical_missing_node'],self.check(source,target)['missing_motion_paths'])
    def test_nonzero_slope_is_rejected(self):
        source=self.scale_trees()
        source[6][1]['m_ScaleCurves'][0]['curve']['m_Curve'][0]['inSlope']['x']=1.
        self.assertEqual(['historical_missing_node'],self.check(source,source)['missing_motion_paths'])

class FlyHistoricalPositionTests(SourceUnboundTests):
    def fly(self):
        trees=self.scale_trees();clip=trees[6][1];clip['m_Name']='ms03_fly_tob'
        curve=clip.pop('m_ScaleCurves')[0];curve['path']='ms03_fly_fire_01'
        curve['curve']['m_Curve'][0]['value']=dict(x=.053,y=.54956,z=-61.875)
        clip['m_PositionCurves']=[curve]
        return trees
    def test_exact_fly_position_allowed_and_other_clips_rejected(self):
        import copy
        source=self.fly()
        with patch.object(m,'motion_paths',side_effect=ValueError('Original motions not found')):
            self.assertEqual([],m.validate_motion_paths(source,'ms03_fly','x',source_trees=source)['missing_motion_paths'])
            target=copy.deepcopy(source);target[6][1]['m_Name']='other'
            self.assertEqual(['ms03_fly_fire_01'],m.validate_motion_paths(target,'ms03_fly','x',source_trees=source)['missing_motion_paths'])
