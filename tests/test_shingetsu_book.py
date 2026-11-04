"""Offline UnityPy checks for the inferred, missing unit-enemy map marker."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec('UnityPy'), 'Offline asset tool UnityPy is required')
class ShingetsuBookTest(unittest.TestCase):
    def test_other_missing_book_colors_use_distinct_internal_files(self):
        import UnityPy
        from scripts.reconstruct_shingetsu_book import build_book
        with tempfile.TemporaryDirectory() as tmp:
            one=build_book(Path('resources/bundles/151-160.unity3d'),Path(tmp)/'one.unity3d',book_color=1)
            two=build_book(Path('resources/bundles/151-160.unity3d'),Path(tmp)/'two.unity3d',book_color=2)
            self.assertEqual(one['prefab'],'ast_ms00_book_el_01')
            self.assertTrue(set(one['generated_internal_files']).isdisjoint(two['generated_internal_files']))

    def test_marker_resolves_correct_prefab_and_preserves_original_bundle(self):
        import UnityPy
        from scripts.reconstruct_shingetsu_book import build_book
        source=Path('resources/bundles/151-160.unity3d')
        before=hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'ms00_book_el_05.unity3d'
            report=build_book(source,output)
            self.assertEqual(report['source_sha256'],before)
            self.assertEqual(report['generated_sha256'],'ae8fc933c64c928c06cf55e6b11040cc9615d3af375a3582002d3dc6f2af1555')
            env=UnityPy.load(str(output))
            original=UnityPy.load(str(source))
            self.assertTrue(set(env.file.files).isdisjoint(original.file.files))
            self.assertEqual(env.file.signature,original.file.signature)
            matches=[]
            for obj in env.objects:
                if obj.type.name=='AssetBundle':
                    for name,info in obj.read().m_Container:
                        if name=='ast_ms00_book_el_05' and info.asset.type.name=='GameObject':
                            matches.append(info.asset)
            self.assertEqual(len(matches),1)
            prefab=matches[0].read()
            self.assertEqual(prefab.m_Name,'ast_ms00_book_el_05')
            self.assertIn('Animation',[component.type.name for _,component in prefab.m_Component])
            self.assertEqual(report['generated_sha256'],hashlib.sha256(output.read_bytes()).hexdigest())
            saved=output.read_bytes()
            with self.assertRaises(FileExistsError):build_book(source,output)
            self.assertEqual(output.read_bytes(),saved)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before)
