import copy
import unittest
from rtd.masters.catalog import load_catalog


class BatchReconstructionTest(unittest.TestCase):
    def test_inferred_encounters_spread_across_lanes_and_depth(self):
        from rtd.masters.event_reconstruction import build_candidate
        masters, levels = load_catalog()
        candidate = build_candidate(masters, levels)
        for level in candidate['levels']:
            if level['height'] < 30:
                continue
            with self.subTest(quest=level['level_data_id']):
                width = level['width']
                points = [(i % width, i // width) for i, cell in
                          enumerate(bytes.fromhex(level['map_data'])) if 1 <= cell & 31 <= 16]
                lanes = {x for x, _ in points}
                self.assertGreaterEqual(len(lanes), 5)
                self.assertLess(min(lanes), level['start_x'])
                self.assertGreater(max(lanes), level['start_x'])
                # Lateral encounters must reach the second half, not cluster at entry.
                self.assertTrue(any(x != level['start_x'] and y > level['height'] // 2
                                    for x, y in points))

    def test_opt_in_preserves_working_content_and_does_not_open_new_events(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from rtd.services.api import API
        from rtd.policies.quest_content import available
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ,{'RTD_EVENT_RECONSTRUCTION':'0','RTD_SHINGETSU_RECONSTRUCTION':'1'}):
                baseline=API(Path(tmp)/'baseline.sqlite3')
            with patch.dict(os.environ,{'RTD_EVENT_RECONSTRUCTION':'1','RTD_SHINGETSU_RECONSTRUCTION':'1'}):
                repaired=API(Path(tmp)/'repaired.sqlite3')
            added=repaired.event_quests-baseline.event_quests
            self.assertGreater(len(added),20)
            self.assertEqual(repaired.operations.read()['events'],[])
            for id in added:
                self.assertFalse(available(repaired,id))
                q=next(q for q in repaired.master_table(30)['data_list'] if q['id']==id)
                self.assertEqual((q['open_type_6'],q['open_param_6']),(6,1))
            for kind in (10,21,30,31,32,33):
                self.assertEqual(repaired.masters[kind],baseline.masters[kind])
            quests={q['id']:q for q in baseline.masters[30]['data_list']}
            tables={t['id']:t for t in baseline.masters[21]['data_list']}
            before={e['id']:e for e in baseline.masters[20]['data_list']}
            after={e['id']:e for e in repaired.masters[20]['data_list']}
            from rtd.policies.quest_content import SINGLE_QUESTS,VERIFIED_LAYER_QUESTS
            original_client={q['id']:q for q in baseline.master_table(30)['data_list']}
            updated_client={q['id']:q for q in repaired.master_table(30)['data_list']}
            for id in baseline.event_quests|SINGLE_QUESTS|VERIFIED_LAYER_QUESTS:
                self.assertEqual(updated_client[id],original_client[id])
                self.assertEqual(repaired.levels[id],baseline.levels[id])
                t=tables[quests[id]['enemy_table_id']]
                for field,enemy in t.items():
                    if field.endswith('_set_id') and enemy in before:self.assertEqual(after[enemy],before[enemy])


class BatchBattleTest(unittest.TestCase):
    def state(self):return self.api.store.session(self.token)

    def test_every_prepared_quest_orders_claims_drops_settles_and_retries(self):
        import os
        from unittest.mock import patch
        import test_quest_content as fixtures
        from rtd.services.battle_entry import HASH_TYPES
        flags=patch.dict(os.environ,{'RTD_EVENT_RECONSTRUCTION':'1','RTD_SHINGETSU_RECONSTRUCTION':'1'})
        flags.start();self.addCleanup(flags.stop)
        fixtures.QuestContentTest.setUp(self)
        ids=sorted(self.api.reconstructed_quests)
        self.assertGreater(len(ids),20)
        self.api.operations.update('events','offline-batch-test',dict(name='Offline batch test',enabled=True,
            starts_at=None,ends_at=None,quests=[dict(quest_id=id,drops=[]) for id in ids]))
        quests={q['id']:q for q in self.api.masters[30]['data_list']}
        for id in ids:
            with self.subTest(quest=id):
                q=quests[id];state=self.state()
                state['sp_event_points']={str(r['sp_event_id']):99999 for r in self.api.masters[34]['data_list']}
                state['player']['action_point']=9999;state['player']['max_unit']=99999
                state['player']['quest_clear_flags']=[0]*len(state['player']['quest_clear_flags'])
                for i in range(1,7):
                    kind=q[f'open_type_{i}'];value=q[f'open_param_{i}']
                    if kind not in (2,7) or (kind==2 and not value):continue
                    prerequisite=quests[value] if kind==2 else q;flag=prerequisite['flag_no']
                    state['player']['quest_clear_flags'][flag//8]|=1<<(flag%8)
                self.api.store.save(state)
                req=fixtures.QuestContentTest.request(self,id)
                req['hashes']={str(t):str(self.api.master_table(t)['hash']) for t in HASH_TYPES}
                first=self.api.call('order_quest',req,self.token)
                self.assertEqual(first,self.api.call('order_quest',req,self.token))
                battle=self.state()['battle']
                drops=[dict(unit_id=e['drop_unit_id'],level=e['drop_unit_level']) for e in battle['enemy_info_list'] if e['drop_unit_id']][:5]
                receipt=dict(ver='2.4.0',retry=0,party_instance_id=self.state()['battle_party_instance_ids'],list=[
                    dict(quest_id=id,exp=q['reward_exp'],game_money=q['reward_money'],yorisiro_exp=0,units=drops,challenge_id_list=[])])
                cleared=self.api.call('clear_quest2',receipt,self.token);after=self.state()
                self.assertIsNone(after['battle'])
                self.assertEqual(cleared,self.api.call('clear_quest2',receipt,self.token))
                self.assertEqual(after,self.state())

    def test_only_absent_records_are_added_and_recovered_data_wins(self):
        from rtd.masters.event_reconstruction import build_candidate,apply_missing
        masters,levels=load_catalog()
        original=copy.deepcopy((masters,levels))
        result=build_candidate(masters,levels,protected={20844})
        self.assertNotIn(20844,result['quest_ids'])
        self.assertGreater(len(result['quest_ids']),20)
        updated,maps=apply_missing(masters,levels,result)
        self.assertEqual((masters,levels),original)
        for kind,table in masters.items():
            self.assertEqual(updated[kind]['data_list'][:len(table['data_list'])],table['data_list'])
        for id,level in levels.items():self.assertEqual(maps[id],level)
        recovered=copy.deepcopy(result['levels'][0]);recovered['hash']='recovered'
        levels[recovered['level_data_id']]=recovered
        self.assertEqual(apply_missing(masters,levels,result)[1][recovered['level_data_id']],recovered)

    def test_routes_include_original_targets_and_retain_neutral_attributes(self):
        from rtd.masters.event_reconstruction import build_candidate
        masters,levels=load_catalog();candidate=build_candidate(masters,levels)
        quests={q['id']:q for q in masters[30]['data_list']}
        for level in candidate['levels']:
            q=quests[level['level_data_id']];w=level['width'];h=level['height']
            cells=bytes.fromhex(level['map_data'])
            self.assertEqual(len(cells),w*h)
            self.assertEqual(h-level['start_y']-10,q['distance'])
            self.assertEqual(cells[(h-10)*w:(h-9)*w],bytes([160])*w)
            self.assertEqual(cells[(h-5)*w:(h-4)*w],bytes([192])*w)
        tables={t['id']:t for t in masters[21]['data_list']}
        enemies={e['id']:e for e in masters[20]['data_list']}
        challenges={c['id']:c for c in masters[32]['data_list']}
        maps={m['level_data_id']:m for m in candidate['levels']}
        for provenance in candidate['provenance']:
            id=provenance['quest_id']
            if id not in maps:continue
            q=quests[id];table=tables[q['enemy_table_id']];level=maps[id]
            path=provenance['route'];previous=(4,4);encounters=[];soul=q['soul']
            self.assertEqual(len(path), len({tuple(point) for point in path}))
            cells=bytes.fromhex(level['map_data'])
            for point in path:
                self.assertEqual(abs(point[0]-previous[0])+abs(point[1]-previous[1]),1)
                slot=cells[point[1]*level['width']+point[0]]
                enemy=enemies[table[f'enemy{slot}_set_id']];encounters.append(enemy['id'])
                soul-=1;self.assertGreaterEqual(soul,0);soul+=enemy['soul_pt'];previous=point
            boss=enemies[table['death_set_id']];soul+=boss['soul_pt']-1
            for i in range(3):
                c=challenges.get(q[f'challenge_id_{i}'])
                if not c:continue
                if c['type']==31:self.assertGreaterEqual(len(path)+1,c['param_0'])
                if c['type']==10:self.assertGreaterEqual(soul,c['param_0'])
                if c['type']==30:self.assertGreaterEqual(encounters.count(c['param_0'])+int(boss['id']==c['param_0']),c['param_1'])
        self.assertTrue(all(p['source'].startswith('docs/archive/wiki/') for p in candidate['provenance']))
