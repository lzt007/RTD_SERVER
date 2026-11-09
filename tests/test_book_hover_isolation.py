"""Regression for the competing root/child legacy Animation position bindings."""
import copy
import importlib.util
import os
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / 'resources/reconstructed/book-hover-v7-inputs'
CANDIDATE = Path(os.environ.get('RTD_BOOK_HOVER_CANDIDATE', str(INPUT)))

@unittest.skipUnless(importlib.util.find_spec('UnityPy'), 'Offline UnityPy dependency unavailable')
class BookHoverIsolationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global CANDIDATE
        if 'RTD_BOOK_HOVER_CANDIDATE' not in os.environ:
            from scripts.prepare_book_hover_isolation import upgrade_book
            cls.temporary = tempfile.TemporaryDirectory()
            cls.addClassCleanup(cls.temporary.cleanup)
            CANDIDATE = Path(cls.temporary.name)
            for color in range(1, 7):
                name = f'ms00_book_el_0{color}.unity3d'
                upgrade_book(INPUT / name, CANDIDATE / name, color)

    def test_hover_bone_is_independent_of_runtime_move_animation(self):
        import UnityPy
        for color in range(1, 7):
            with self.subTest(color=color):
                objects = {o.path_id: o for o in UnityPy.load((CANDIDATE / f'ms00_book_el_0{color}.unity3d').read_bytes()).objects}
                move = objects[1160].read_typetree()
                renderer = objects[1214].read_typetree()
                bone = renderer['m_Bones'][0]['m_PathID']
                self.assertNotEqual(bone, 1160, 'Character Wait writes move.localPosition; hover skin must use a separate bone')
                self.assertEqual(move['m_Father']['m_PathID'], 1174)
                hover = objects[bone].read_typetree()
                self.assertEqual(hover['m_Father']['m_PathID'], 1160, 'Preserve original controller placement and scaling')
                self.assertIn({'m_FileID': 0, 'm_PathID': bone}, move['m_Children'])
                gameobject = objects[hover['m_GameObject']['m_PathID']].read_typetree()
                self.assertEqual([cls for cls, _ in gameobject['m_Component']], [4])
                clip = objects[1301].read_typetree()
                self.assertEqual([c['path'] for c in clip['m_PositionCurves']], ['move/' + gameobject['m_Name']])
                self.assertNotEqual(gameobject['m_Name'], 'move')

    def test_artwork_geometry_and_original_animation_contracts_are_preserved(self):
        import UnityPy
        for color in range(1, 7):
            name = f'ms00_book_el_0{color}.unity3d'
            old = {o.path_id: o for o in UnityPy.load((INPUT / name).read_bytes()).objects}
            new = {o.path_id: o for o in UnityPy.load((CANDIDATE / name).read_bytes()).objects}
            for path in (6, 26, 42, 52, 603, 1184, 1300):
                self.assertEqual(new[path].get_raw_data(), old[path].get_raw_data(), (color, path))
            old_move = old[1160].read_typetree()
            new_move = copy.deepcopy(new[1160].read_typetree())
            new_move['m_Children'] = old_move['m_Children']
            self.assertEqual(new_move, old_move, 'Do not change original move rest transform')
            original = old[1301].read_typetree()
            actual = copy.deepcopy(new[1301].read_typetree())
            actual['m_PositionCurves'][0]['path'] = 'move'
            self.assertEqual(actual, original, 'Reuse the original el_wait timing, values and tangents')
            for obj in new.values():
                if obj.type.name == 'GameObject':
                    self.assertEqual(obj.read_typetree()['m_IsActive'], 0)
            self.assertFalse(new[1].assets_file.externals)

if __name__ == '__main__':
    unittest.main()
