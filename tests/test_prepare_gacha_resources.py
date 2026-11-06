"""A fresh resource preparation must not recreate the obsolete Fenris markers."""
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec('UnityPy'), 'Offline UnityPy tool required')
class PrepareGachaResourcesTest(unittest.TestCase):
    def test_fresh_overlay_uses_gacha_artwork(self):
        from scripts.prepare_event_reconstruction_resources import prepare
        source = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'config').mkdir()
            (root/'config/event-reconstruction-assets.json').write_text(json.dumps({'bundle_sources': {}}))
            bundles = root/'resources/bundles'
            bundles.mkdir(parents=True)
            shutil.copyfile(source/'resources/bundles/151-160.unity3d', bundles/'151-160.unity3d')
            reports = prepare(root, root/'derived/bundles',
                              apk=source.parent/'RTD_CLIENT/inputs/original/game.apk')
            self.assertEqual(len(reports), 6)
            self.assertTrue(all(r['policy'] == 'inferred-gacha-book-billboard-root-animation-hover-v7' for r in reports))
            self.assertEqual(json.loads((root/'derived/resource-provenance.json').read_text()), reports)
