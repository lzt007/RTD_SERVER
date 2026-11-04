"""Asset integration regressions: no unrelated live hierarchy in an exported wolf."""
import importlib.util
import os
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(importlib.util.find_spec('UnityPy'),'Offline UnityPy tool required')
class WolfClosureTests(unittest.TestCase):
    def test_prefab_preloads_no_unrelated_renderer(self):
        import UnityPy
        directory=Path(os.environ.get('RTD_WOLF_AUDIT_DIR',ROOT/'resources/reconstructed/monsters/bundles'))
        paths=sorted(directory.glob('ms01_wolf*.unity3d'))
        self.assertEqual(len(paths),8,'Expected the complete eight-model wolf set')
        for path in paths:
            with self.subTest(bundle=path.name):
                env=UnityPy.load(str(path));objects={o.path_id:o for o in env.objects}
                def refs(value):
                    if isinstance(value,dict):
                        if 'm_PathID' in value:
                            if value['m_PathID']:
                                self.assertEqual(value['m_FileID'],0);yield value['m_PathID']
                        else:
                            for child in value.values():yield from refs(child)
                    elif isinstance(value,(tuple,list)):
                        for child in value:yield from refs(child)
                def closure(pid):
                    seen=set();todo=[pid]
                    while todo:
                        i=todo.pop()
                        if i in seen:continue
                        seen.add(i);todo.extend(refs(objects[i].read_typetree()))
                    return seen
                bundle=next(o for o in env.objects if o.type.name=='AssetBundle');ab=bundle.read_typetree();union=set()
                for name,entry in ab['m_Container']:
                    expected=closure(entry['asset']['m_PathID']);union|=expected
                    actual={p['m_PathID'] for p in ab['m_PreloadTable'][entry['preloadIndex']:entry['preloadIndex']+entry['preloadSize']]}
                    self.assertEqual(actual,expected,'Export preloads unrelated objects: '+name)
                self.assertEqual(set(objects),union|{bundle.path_id})
                prefab=next(v for n,v in ab['m_Container'] if n.startswith('ast_'))
                renderers=[i for i in closure(prefab['asset']['m_PathID']) if objects[i].type.name=='SkinnedMeshRenderer']
                self.assertEqual(len(renderers),1)

    def test_source_gameobjects_match_native_asset_activation_flags(self):
        import UnityPy
        directory=Path(os.environ.get('RTD_WOLF_AUDIT_DIR',ROOT/'resources/reconstructed/monsters/bundles'))
        # Audited native bear and working gold/silver prefab GameObjects serialize
        # this flag as zero. Modern source scene objects must not retain one.
        native=UnityPy.load(str(ROOT/'resources/bundles/ms01_sla_lv1_gold.unity3d'))
        self.assertEqual({o.read_typetree()['m_IsActive'] for o in native.objects if o.type.name=='GameObject'},{0})
        paths=sorted(directory.glob('ms01_wolf*.unity3d'));self.assertEqual(len(paths),8)
        for path in paths:
            with self.subTest(bundle=path.name):
                env=UnityPy.load(str(path))
                self.assertEqual({o.read_typetree()['m_IsActive'] for o in env.objects if o.type.name=='GameObject'},{0})
