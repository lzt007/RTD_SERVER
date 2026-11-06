import unittest
from rtd.policies.gacha_cleanup import clean_pools

class CleanupTest(unittest.TestCase):
    def test_subtraction_and_empty_guard(self):
        pools={'rare':[{'unit_id':3,'weight':1},{'unit_id':4,'weight':2}]}
        cleaned,report=clean_pools(pools,{3:['evolution']})
        self.assertEqual([r['unit_id'] for r in cleaned['rare']],[4])
        self.assertEqual(len(pools['rare']),2)
        self.assertEqual(clean_pools(cleaned,{3:['evolution']})[0],cleaned)
        with self.assertRaises(ValueError):clean_pools(pools,{3:[],4:[]})

    def test_effective_slots_rates_objects_and_evolution(self):
        from rtd.policies.gacha_cleanup import exclusions
        units=[dict(id=i) for i in range(1,20)]
        units[0].update(rev_unit_id=2,ultimate_rev_unit_id_fire=3)
        table=dict(id=1)
        for n,prefix in enumerate(('enemy1','enemy2','enemy3','boss','death'),1):
            table.update({prefix+'_rate':100,prefix+'_set_id':n,prefix+'_drop_id':n})
        table['boss_rate']=0
        drops=[dict(id=i,unit1_id=10+i,unit1_rate=100,unit2_id=19,unit2_rate=10) for i in range(1,6)]
        masters={10:dict(data_list=units),20:dict(data_list=[dict(id=3,type=20)]),21:dict(data_list=[table]),22:dict(data_list=drops),30:dict(data_list=[dict(id=1,enemy_table_id=1)])}
        levels={1:dict(map_data='0103')}
        reasons=exclusions(masters,levels,{1})
        self.assertEqual(set(reasons),{2,3,11,15})
        self.assertEqual(set(exclusions(masters,levels,{1},{(1,1):[]})),{2,3,15})
        self.assertEqual(set(exclusions(masters,levels,set())),{2,3})
        drops[0]['unit1_rate']=0
        drops[0]['unit2_rate']=0
        self.assertEqual(set(exclusions(masters,levels,{1})),{2,3,15})

    def test_offline_migration_guard_and_preservation(self):
        import json,sqlite3,tempfile
        from pathlib import Path
        from scripts.apply_gacha_cleanup import apply
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'test.sqlite'
            original=dict(revision=5,events=[{'custom':'preserved'}],gachas=[dict(id=10000,name='custom',entries=[dict(unit_id=1,weight=7),dict(unit_id=2,weight=9)])])
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE runtime_config(id INTEGER,document TEXT)')
                db.execute('INSERT INTO runtime_config VALUES(1,?)',(json.dumps(original),))
            proposal=dict(pools={'10000':[dict(unit_id=1,weight=7)]},report={'10000':dict(before=2)})
            with self.assertRaises(ValueError):apply(path,proposal,4)
            self.assertTrue(apply(path,proposal,5))
            with sqlite3.connect(path) as db:actual=json.loads(db.execute('SELECT document FROM runtime_config').fetchone()[0])
            self.assertEqual(actual['events'],original['events'])
            self.assertEqual(actual['gachas'][0]['name'],'custom')
            self.assertEqual(actual['revision'],6)
