"""Offline structural checks for inferred book artwork bundles."""
import unittest
import importlib.util
from pathlib import Path
import tempfile
from scripts.reconstruct_gacha_book import build_gacha_book, validate_book

@unittest.skipUnless(importlib.util.find_spec('UnityPy'), 'Offline UnityPy build dependency unavailable')
class GachaBookResourcesTest(unittest.TestCase):
    def test_all_six_books_are_minimal_and_self_contained(self):
        root=Path(__file__).resolve().parents[1]
        apk=root.parent/'RTD_CLIENT/inputs/original/game.apk'
        with tempfile.TemporaryDirectory() as tmp:
            internals=set()
            for color in range(1,7):
                out=Path(tmp)/f'ms00_book_el_0{color}.unity3d'
                report=build_gacha_book(apk,root/'resources/bundles/151-160.unity3d',out,color)
                result=validate_book(out,color)
                import UnityPy
                flags=[o.read_typetree()['m_IsActive'] for o in UnityPy.load(str(out)).objects
                       if o.type.name=='GameObject']
                self.assertEqual(flags,[0,0], 'Unity 3.5 book prototypes require native activation encoding')
                self.assertEqual(result['vertex_count'],4)
                self.assertEqual(result['external_references'],0)
                self.assertLess(out.stat().st_size,100000)
                self.assertEqual(report['source_sprite'],f'book_0{color}')
                self.assertTrue(internals.isdisjoint(report['generated_internal_files']))
                internals.update(report['generated_internal_files'])
    def test_legacy_strip_faces_cover_quad_without_overlap(self):
        import UnityPy
        from UnityPy.helpers.MeshHelper import MeshHandler
        root=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'book.unity3d'
            build_gacha_book(root.parent/'RTD_CLIENT/inputs/original/game.apk',
                             root/'resources/bundles/151-160.unity3d',out,5)
            env=UnityPy.load(str(out))
            mesh=next(o for o in env.objects if o.type.name=='Mesh')
            decoded=MeshHandler(mesh.read());decoded.process()
            faces=decoded.get_triangles()[0]
            self.assertEqual(len(faces),2,'Legacy Unity must decode exactly two faces')
            vertices=decoded.m_Vertices
            area=0
            for a,b,c in faces:
                self.assertEqual(len({a,b,c}),3)
                x,y,z=(vertices[i] for i in (a,b,c))
                area+=abs((y[0]-x[0])*(z[1]-x[1])-(z[0]-x[0])*(y[1]-x[1]))/2
            self.assertAlmostEqual(area,1.01*1.36,places=5)
            tree=mesh.read_typetree()
            self.assertEqual(tree['m_SubMeshes'][0]['triangleCount'],len(faces))
            self.assertEqual(tree['m_SubMeshes'][0]['isTriStrip'],2)

    def test_rejects_invalid_color(self):
        for color in (0,7,True):
            with self.assertRaises(ValueError):build_gacha_book('', '', '',color)

if __name__=='__main__':unittest.main()
