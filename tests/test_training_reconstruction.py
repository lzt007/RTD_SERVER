import copy
import unittest
from rtd.masters.catalog import load_catalog
from rtd.masters.event_reconstruction import build_candidate, apply_missing


class TrainingReconstructionTest(unittest.TestCase):
    def test_all_attributes_missing_only_and_original_records_preserved(self):
        masters, levels = load_catalog()
        original = copy.deepcopy((masters, levels))
        ids = set(range(25061, 25064)) | set(range(25073, 25082))
        candidate = build_candidate(masters, levels)
        self.assertTrue(ids <= set(candidate['quest_ids']))
        repaired, maps = apply_missing(masters, levels, candidate)
        self.assertEqual((masters, levels), original)
        for kind, table in masters.items():
            actual = {r['id']: r for r in repaired[kind]['data_list'] if 'id' in r}
            for row in table['data_list']:
                if 'id' in row:
                    self.assertEqual(actual[row['id']], row)
        for quest in ids:
            self.assertIn(quest, maps)
            provenance = next(r for r in candidate['provenance'] if r['quest_id'] == quest)
            self.assertTrue(provenance['route'])
            self.assertIn('inferred', provenance)
        for quest, level in levels.items():
            self.assertEqual(maps[quest], level)
