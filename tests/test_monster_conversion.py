"""Offline conversion tests; run with the UnityPy asset-tool interpreter."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(importlib.util.find_spec('UnityPy'),'Offline UnityPy tool required')
class ConversionTests(unittest.TestCase):
    def test_wolf_is_old_format_and_self_contained(self):
        import UnityPy
        spec=importlib.util.spec_from_file_location('convert', ROOT/'scripts/prepare_monster_recovery.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ms01_wolf_lv1.unity3d'
            report=module.convert_model(module.WOLF_SOURCE,path,'ms01_wolf_lv1',
                                        {'ms01_wolf_lv1_fire':module.WOLF_SOURCE})
            env=UnityPy.load(str(path))
            sf=next(iter(env.objects)).assets_file
            self.assertEqual(sf.header.version,9)
            self.assertTrue(sf.unity_version.startswith('3.5'))
            self.assertIn('ast_ms01_wolf_lv1',env.container)
            self.assertIn('ms01_wolf_lv1_fire',env.container)
            self.assertEqual(report['missing_pointers'],[])
            self.assertGreater(report['vertices'],0)
            self.assertTrue(report['texture_roundtrip'])
            self.assertTrue(report['mesh_roundtrip'])
            self.assertEqual(report['missing_motion_paths'],[])
            self.assertEqual({o.read_typetree()['m_IsActive'] for o in env.objects if o.type.name=='GameObject'},{0})

    def test_original_motion_loads_when_local_duplicate_is_first_origin(self):
        import json
        from unittest.mock import patch
        spec=importlib.util.spec_from_file_location('convert',ROOT/'scripts/prepare_monster_recovery.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        full=json.loads((ROOT/'docs/resource-audit/loading-chain/catalog.json').read_text())
        selected={k:v for k,v in full['objects'].items() if v['type']=='AnimationClip' and v['name'] in ('ms01_wolf_wait_01','ms01_wolf_atk_01')}
        self.assertTrue(selected)
        files={};sources=[]
        for obj in selected.values():
            fid=obj['file']
            if fid in files:continue
            source=full['sources'][full['files'][fid]['source']]
            sources.append({**source,'origins':[{'path':'RTD_SERVER/resources/local-copy.assets','category':'local_resource'},*source['origins']]})
            files[fid]={'source':len(sources)-1}
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'docs/resource-audit/loading-chain';folder.mkdir(parents=True)
            (folder/'catalog.json').write_text(json.dumps(dict(objects=selected,files=files,sources=sources)))
            with patch.object(module,'ROOT',root):paths=module.motion_paths('wolf')
        self.assertTrue(any('mn_c_main' in path for path in paths))
