import unittest
from scripts.backup_shader_compatibility import validate_shader_mapping

class ShaderGateTests(unittest.TestCase):
    shader={'m_Script':'Shader "Character/brightness" {\nProperties {\n_Color ("Color", Color) = (1,1,1,1)\n}\nSubShader { Tags { "QUEUE"="Transparent" }\nPass {\nCull Off\nBlend SrcAlpha OneMinusSrcAlpha\nProgram "vp" {}\n}\n}\n}'}
    def test_same_states_accept_but_depth_and_blend_changes_block(self):
        self.assertTrue(validate_shader_mapping(self.shader,self.shader)['render_state_compatible'])
        for changed in ('ZWrite Off\nCull Off','Cull Back','Blend One One'):
            source={'m_Script':self.shader['m_Script'].replace('Cull Off',changed)}
            with self.subTest(changed=changed),self.assertRaises(ValueError):validate_shader_mapping(source,self.shader)

    def test_cull_back_mapping_preserves_native_program(self):
        from scripts.backup_shader_compatibility import native_shader_for,render_signature
        target=dict(self.shader,m_Name='brightness')
        source=dict(m_Name='brightnessCullBack',m_Script=target['m_Script'].replace('Character/brightness','Character/brightnessCullBack').replace('Cull Off\n',''))
        result,proof=native_shader_for(source,target)
        self.assertEqual(render_signature(source),render_signature(result))
        self.assertEqual(target['m_Name'],'brightness')
        self.assertEqual(proof['native_mapping'],'brightness-cull-back')
