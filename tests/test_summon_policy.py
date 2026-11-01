import json
import pathlib
import tempfile
import unittest
from fractions import Fraction
from rtd.masters.catalog import load_catalog
from rtd.policies.summon_catalog import build_pools, MATERIAL_IDS, STARTER_IDS
from rtd.services.api import API
from scripts.apply_gacha_policy import migrate


class SummonPolicyTest(unittest.TestCase):
    def test_membership_and_exact_group_probability(self):
        masters,_=load_catalog();p,report=build_pools(masters)
        rare={r['unit_id'] for r in p['rare']}
        excluded=set(report['excluded_ids'])
        self.assertFalse(rare & (MATERIAL_IDS|STARTER_IDS|excluded))
        self.assertEqual(rare|MATERIAL_IDS|excluded,{u['id'] for u in masters[10]['data_list']})
        total=sum(r['weight'] for r in p['normal'])
        material=sum(r['weight'] for r in p['normal'] if r['unit_id'] in MATERIAL_IDS)
        self.assertEqual(Fraction(material,total),Fraction(9,10))
        self.assertTrue({10000,10021,10030,10033}<=excluded)
        self.assertEqual(len(MATERIAL_IDS),40)

    def test_existing_database_migration_preserves_events_and_accounts(self):
        with tempfile.TemporaryDirectory() as root:
            path=pathlib.Path(root)/'test.sqlite3';api=API(path)
            cfg=api.operations.read();cfg['gachas'][0]['entries']=[dict(unit_id=10000,level=1,weight=1)]
            cfg['gachas'][0]['enabled']=False
            with api.store.connect() as db:
                db.execute('UPDATE runtime_config SET document=? WHERE id=1',(json.dumps(cfg),));db.commit()
            result=migrate(path)
            self.assertTrue(pathlib.Path(result['backup']).is_file())
            current=api.operations.read()
            self.assertEqual(current['revision'],cfg['revision']+1)
            self.assertFalse(current['gachas'][0]['enabled'])
            self.assertEqual(len(current['gachas'][0]['entries']),550)
            self.assertEqual(current['events'],cfg['events'])
            self.assertFalse(migrate(path)['changed'])
