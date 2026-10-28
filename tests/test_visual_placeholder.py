import copy,unittest
from rtd.masters.catalog import load_catalog
from rtd.policies.visual_recovery import apply_visual_recovery

class VisualPlaceholderTest(unittest.TestCase):
    def test_fixed_boss_for_all_recorded_missing_assets_preserves_gameplay_and_source(self):
        masters,_=load_catalog();before=copy.deepcopy(masters)
        manifest=apply_visual_recovery(masters)
        self.assertEqual(manifest['placeholder'],dict(model='ms02_four_un_01_zako',texture='na'))
        self.assertGreater(len(manifest['substitutions']),2)
        ids={r['enemy_id'] for r in manifest['substitutions']}
        self.assertIn(11001,manifest['quest_ids']);self.assertIn(11002,manifest['quest_ids'])
        for original,derived in zip(before[20]['data_list'],masters[20]['data_list']):
            if original['id'] not in ids|{41221}:self.assertEqual(original,derived);continue
            self.assertEqual({k:v for k,v in original.items() if k not in ('model','texture')},
                             {k:v for k,v in derived.items() if k not in ('model','texture')})
            if original['id'] in ids:
                self.assertEqual((derived['model'],derived['texture']),('ms02_four_un_01_zako','na'))
        self.assertEqual(load_catalog()[0],before)
