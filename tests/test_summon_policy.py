import json
import pathlib
import tempfile
import unittest
from rtd.masters.catalog import load_catalog
from rtd.policies.summon_catalog import build_pools
from rtd.policies.gacha_cleanup import exclusions
from scripts.apply_gacha_policy import migrate


class SummonPolicyTest(unittest.TestCase):
    def test_effective_context_required(self):
        masters,_=load_catalog()
        with self.assertRaisesRegex(ValueError,'Effective'):build_pools(masters)

    def test_incomplete_and_evolved_units_never_enter_generated_pools(self):
        masters,levels=load_catalog()
        pools,report=build_pools(masters,levels=levels,playable=set())
        excluded=set(exclusions(masters,levels,set()))|set(map(int,report['unavailable_units']))
        for name in ('normal','rare'):
            self.assertTrue(pools[name])
            self.assertFalse(excluded & {r['unit_id'] for r in pools[name]})

    def test_legacy_migration_cannot_replace_pools_without_review(self):
        with tempfile.TemporaryDirectory() as root:
            path=pathlib.Path(root)/'absent.sqlite3'
            with self.assertRaisesRegex(ValueError,'proposal'):migrate(path)
            self.assertFalse(path.exists())
