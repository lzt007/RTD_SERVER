import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

class MonsterRecoveryTests(unittest.TestCase):
    def fixture(self):
        from rtd.masters.catalog import load_catalog
        self.raw,self.levels=load_catalog();self.masters=copy.deepcopy(self.raw)
        for row in self.masters[20]['data_list']:
            if row['model'].startswith(('ms01_wolf','ms01_sla')):
                row.update(model='placeholder',texture='na')
        return self.masters

    def test_disabled_does_not_change_effective_records(self):
        from rtd.policies.monster_recovery import apply_monster_recovery
        masters=self.fixture();before=copy.deepcopy(masters)
        with patch.dict(os.environ,{'RTD_MONSTER_RECOVERY':'0'}):
            self.assertIsNone(apply_monster_recovery(masters,self.levels,{11012}))
        self.assertEqual(masters,before)

    def test_11012_restores_missing_wolves_and_silver_only(self):
        from rtd.policies.monster_recovery import apply_monster_recovery
        masters=self.fixture();before=copy.deepcopy(masters)
        with patch.dict(os.environ,{'RTD_MONSTER_RECOVERY':'1'}):
            report=apply_monster_recovery(masters,self.levels,{11012})
        old={r['id']:r for r in before[20]['data_list']};raw={r['id']:r for r in self.raw[20]['data_list']}
        changed=[]
        for row in masters[20]['data_list']:
            if row!=old[row['id']]:
                changed.append(row['id'])
                self.assertEqual({k:v for k,v in row.items() if k not in ('model','texture')},
                                 {k:v for k,v in old[row['id']].items() if k not in ('model','texture')})
                self.assertEqual(row,raw[row['id']])
        self.assertEqual(set(changed),{10200,10210,12100})
        self.assertEqual(len(report['substitutions']),3)
        for k in masters:
            if k!=20:self.assertEqual(masters[k],before[k])
        self.assertNotEqual(masters[20]['hash'],before[20]['hash'])

    def test_bundle_requires_opt_in_and_verified_bytes(self):
        from rtd.policies.monster_recovery import bundle_file
        with patch.dict(os.environ,{'RTD_MONSTER_RECOVERY':'0'}):
            self.assertIsNone(bundle_file('ms01_wolf_lv1.unity3d'))
        with patch.dict(os.environ,{'RTD_MONSTER_RECOVERY':'1'}):
            path=bundle_file('ms01_wolf_lv1.unity3d');self.assertTrue(path.is_file())
            self.assertIsNone(bundle_file('../ms01_wolf_lv1.unity3d'))
            self.assertIsNone(bundle_file('unlisted.unity3d'))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'config').mkdir();(root/'resources/reconstructed/monsters/bundles').mkdir(parents=True)
            (root/'config/monster-recovery.json').write_text(json.dumps(dict(bundles=[dict(bundle='a.unity3d',sha256=hashlib.sha256(b'good').hexdigest())])))
            (root/'resources/reconstructed/monsters/bundles/a.unity3d').write_bytes(b'corrupt')
            with patch.dict(os.environ,{'RTD_MONSTER_RECOVERY':'1'}),patch('rtd.policies.monster_recovery.ROOT',root):
                self.assertIsNone(bundle_file('a.unity3d'))

    def test_real_api_layers_preserve_all_gameplay_and_existing_slimes(self):
        from rtd.services.api import API
        from rtd.masters.catalog import load_catalog
        raw,_=load_catalog();original={r['id']:r for r in raw[20]['data_list']}
        for events in ('0','1'):
            with self.subTest(events=events),tempfile.TemporaryDirectory() as tmp:
                common={'RTD_EVENT_RECONSTRUCTION':events,'RTD_MONSTER_RECOVERY':'0'}
                with patch.dict(os.environ,common):baseline=API(Path(tmp)/'before.db')
                with patch.dict(os.environ,{**common,'RTD_MONSTER_RECOVERY':'1'}):repaired=API(Path(tmp)/'after.db')
                self.assertEqual(baseline.levels,repaired.levels)
                self.assertEqual(baseline.event_quests,repaired.event_quests)
                self.assertEqual(baseline.reconstructed_quests,repaired.reconstructed_quests)
                for k in baseline.masters:
                    if k!=20:self.assertEqual(baseline.masters[k],repaired.masters[k])
                before={r['id']:r for r in baseline.masters[20]['data_list']}
                models=set()
                for row in repaired.masters[20]['data_list']:
                    old=before[row['id']]
                    self.assertEqual({k:v for k,v in old.items() if k not in ('model','texture')},
                                     {k:v for k,v in row.items() if k not in ('model','texture')})
                    if row!=old:models.add(row['model'])
                    if original.get(row['id'],{}).get('model') in ('ms01_sla_lv1','ms01_sla_lv1_gold','ms01_sla_lv4_gold'):
                        self.assertEqual(old,row)
                self.assertIn('ms01_wolf_lv1',models)
                self.assertIn('ms01_sla_lv1_silver',models)
                actual={r['id']:r for r in repaired.masters[20]['data_list']}
                self.assertEqual(actual[10200]['model'],'ms01_wolf_lv1')
                self.assertEqual(actual[12100]['model'],'ms01_sla_lv1_silver')

    def test_http_overlay_and_original_file_priority(self):
        import http.server
        import threading
        import urllib.request
        import urllib.error
        import rtd.resources as resources
        from rtd.policies.monster_recovery import bundle_file
        name='ms01_wolf_lv1.unity3d'
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'RTD_MONSTER_RECOVERY':'1'}),patch.object(resources,'bundle_root',Path(tmp)):
            expected=bundle_file(name).read_bytes()
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),resources.Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            url=f'http://127.0.0.1:{server.server_port}/Android/V1011/{name}'
            try:
                with urllib.request.urlopen(url) as response:self.assertEqual(response.read(),expected)
                with patch.dict(os.environ,{'RTD_MONSTER_RECOVERY':'0'}):
                    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(url)
                    self.assertEqual(error.exception.code,404)
                (Path(tmp)/name).write_bytes(b'genuine original takes precedence')
                with urllib.request.urlopen(url) as response:self.assertEqual(response.read(),b'genuine original takes precedence')
            finally:server.shutdown();server.server_close();thread.join()

    def test_preloader_includes_table_slots_absent_from_map(self):
        from rtd.policies.monster_recovery import referenced_enemies
        table={'id':7,'boss_set_id':0,'death_set_id':0,**{f'enemy{i}_set_id':0 for i in range(1,19)}}
        table['enemy18_set_id']=123
        masters={30:{'data_list':[{'id':999,'enemy_table_id':7}]},21:{'data_list':[table]}}
        self.assertEqual(referenced_enemies(masters,{999:{'map_data':'00'}},{999}),{123:{999}})
