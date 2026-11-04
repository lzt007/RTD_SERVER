import copy
import random
import unittest
from types import SimpleNamespace
from rtd.masters.catalog import load_catalog
from rtd.masters.shingetsu import build_candidate,apply_missing,QUEST_IDS
from rtd.services.battle_generation import generate_enemies
from rtd.services.battle_entry import HASH_TYPES
from rtd.policies.event_content import audit_events
from rtd.policies.quest_content import require_unlocked
from rtd.common import ProtocolError

class ShingetsuDataTest(unittest.TestCase):
    def test_export_is_separate_and_refuses_to_overwrite(self):
        import tempfile
        import subprocess
        import sys
        import json
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'candidate'
            command=[sys.executable,'scripts/reconstruct_shingetsu.py','--output',str(out)]
            first=subprocess.run(command,capture_output=True,text=True)
            self.assertEqual(first.returncode,0,first.stderr)
            candidate=json.loads((out/'candidate.json').read_text())
            self.assertEqual(len(candidate['levels']),3)
            self.assertEqual(len(candidate['drops']),12)
            self.assertTrue((out/'maps.txt').is_file())
            before=(out/'candidate.json').read_bytes()
            second=subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(second.returncode,0)
            self.assertEqual((out/'candidate.json').read_bytes(),before)

    def setUp(self):
        self.m,self.l=load_catalog();self.c=build_candidate(self.m,self.l)

    def test_original_records_and_inputs_remain_exact(self):
        before=copy.deepcopy((self.m,self.l));m,l=apply_missing(self.m,self.l,self.c)
        self.assertEqual((self.m,self.l),before)
        for k,t in self.m.items():
            self.assertEqual(m[k]['data_list'][:len(t['data_list'])],t['data_list'])
            if k not in (22,70):self.assertEqual(m[k],t)
        self.assertEqual(set(l)-set(self.l),set(QUEST_IDS))
        self.assertEqual(len(m[22]['data_list'])-len(self.m[22]['data_list']),12)
        es={e['id']:e for e in m[20]['data_list']}
        for i in (12106,12107,12207):self.assertEqual(es[i]['attribute'],1)
        self.assertEqual(es[41102]['model'],'g01_kn_grt_fire_01')
        for i,v in self.l.items():self.assertEqual(l[i],v)

    def test_recovered_real_data_wins_even_over_stale_candidates(self):
        real=copy.deepcopy(self.c['levels'][0]);real['hash']='real';self.l[20844]=real
        drop=copy.deepcopy(self.c['drops'][0]);drop['unit1_rate']=7;self.m[22]['data_list'].append(drop)
        fresh=build_candidate(self.m,self.l)
        self.assertNotIn(20844,[r['level_data_id'] for r in fresh['levels']])
        self.assertNotIn(drop['id'],[r['id'] for r in fresh['drops']])
        m,l=apply_missing(self.m,self.l,self.c)
        self.assertEqual(l[20844],real)
        self.assertEqual(next(r for r in m[22]['data_list'] if r['id']==drop['id']),drop)
        self.assertEqual(next(r for r in m[22]['data_list'] if r['id']==0),self.m[22]['data_list'][0])

    def test_maps_support_distance_kill_and_soul_challenges_on_direct_route(self):
        qs={q['id']:q for q in self.m[30]['data_list']};ts={t['id']:t for t in self.m[21]['data_list']};es={e['id']:e for e in self.m[20]['data_list']}
        for level in self.c['levels']:
            id=level['level_data_id'];q=qs[id];t=ts[q['enemy_table_id']];w=level['width'];h=level['height'];x=level['start_x'];cells=bytes.fromhex(level['map_data'])
            self.assertEqual(len(cells),w*h);self.assertEqual(h-level['start_y']-10,q['distance'])
            self.assertEqual(cells[level['start_y']*w+x],0)
            self.assertEqual(list(cells[(h-10)*w:(h-9)*w]),[160]*w)
            self.assertEqual(list(cells[(h-5)*w:(h-4)*w]),[192]*w)
            soul=q['soul'];kills=0
            for y in range(level['start_y']+1,h-9):
                soul-=1;self.assertGreaterEqual(soul,0)
                s=cells[y*w+x]&31
                if 1<=s<=18:soul+=es[t[f'enemy{s}_set_id']]['soul_pt'];kills+=1
            soul+=es[t['death_set_id']]['soul_pt']
            self.assertGreaterEqual(kills,{20844:5,20845:10,20846:20}[id])
            self.assertGreaterEqual(soul,{20844:10,20845:30,20846:0}[id])

    def test_drop_sampling_and_original_boss_and_slime(self):
        m,l=apply_missing(self.m,self.l,self.c);qs={q['id']:q for q in m[30]['data_list']};ts={t['id']:t for t in m[21]['data_list']};ds={r['id']:r for r in m[22]['data_list']};us={u['id'] for u in m[10]['data_list']}
        for d in self.c['drops']:
            self.assertLessEqual(sum(d[f'unit{i}_rate'] for i in range(1,5)),100)
            for i in range(1,5):
                if d[f'unit{i}_id']:self.assertIn(d[f'unit{i}_id'],us)
        for id in QUEST_IDS:
            rows=generate_enemies(ts[qs[id]['enemy_table_id']],l[id],ds,random.Random(4))
            self.assertEqual(next(e for e in rows if e['enemy_id']==0)['enemy_set_id'],41102)
            self.assertEqual(next(e for e in rows if e['enemy_id']==99)['enemy_set_id'],31030)
            self.assertIn({20844:12106,20845:12107,20846:12207}[id],{e['enemy_set_id'] for e in rows})

    def test_original_window_and_prerequisite_are_preserved(self):
        api=SimpleNamespace(masters=self.m);f=next(q for q in self.m[30]['data_list'] if q['id']==10000)['flag_no']
        for id in QUEST_IDS:
            q=next(q for q in self.m[30]['data_list'] if q['id']==id);s={'player':{'quest_clear_flags':[0]*2048}}
            with self.assertRaisesRegex(ProtocolError,'Required quest'):require_unlocked(api,s,q,local_schedule=True)
            s['player']['quest_clear_flags'][f//8]|=1<<(f%8)
            with self.assertRaisesRegex(ProtocolError,'time window'):require_unlocked(api,s,q)
            require_unlocked(api,s,q,local_schedule=True)

    def test_upper_bow_challenge_is_supported_without_modifying_its_master(self):
        m,l=apply_missing(self.m,self.l,self.c);accepted,rejected=audit_events(m,l)
        self.assertTrue(set(QUEST_IDS)<=accepted,rejected.get(20846))
        self.assertEqual(next(c for c in m[32]['data_list'] if c['id']==10670)['type'],22)

    def test_bow_style_includes_helper_and_requires_original_party_snapshot(self):
        from rtd.policies.party_challenges import require_party_style
        bow=next(u['id'] for u in self.m[10]['data_list'] if u['style']==3)
        other=next(u['id'] for u in self.m[10]['data_list'] if u['style']!=3)
        api=SimpleNamespace(masters=self.m,event_quests={20846})
        s={'battle':{'quest_id':20846},'battle_party_unit_ids':[bow]*3,'battle_helper':{'unit_id':bow}}
        require_party_style(api,s,3)
        s['battle_helper']['unit_id']=other
        with self.assertRaisesRegex(ProtocolError,'weapon'):require_party_style(api,s,3)
        s.pop('battle_party_unit_ids')
        with self.assertRaisesRegex(ProtocolError,'snapshot'):require_party_style(api,s,3)

    def test_api_opt_in_is_required_and_original_fenris_is_not_replaced(self):
        import tempfile,os
        from pathlib import Path
        from unittest.mock import patch
        from rtd.services.api import API
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ,{'RTD_SHINGETSU_RECONSTRUCTION':'0'}):
                disabled=API(Path(tmp)/'disabled.sqlite3')
            self.assertNotIn(20844,disabled.levels)
            with patch.dict(os.environ,{'RTD_SHINGETSU_RECONSTRUCTION':'1'}):
                enabled=API(Path(tmp)/'enabled.sqlite3')
            self.assertTrue(set(QUEST_IDS)<=enabled.event_quests,enabled.event_rejections)
            original=next(e for e in self.m[20]['data_list'] if e['id']==41102)
            self.assertEqual(next(e for e in enabled.masters[20]['data_list'] if e['id']==41102),original)
            for id in (12106,12107,12207):
                self.assertEqual(next(e for e in enabled.masters[20]['data_list'] if e['id']==id)['attribute'],1)
            q=next(q for q in enabled.masters[30]['data_list'] if q['id']==20844)
            self.assertEqual(q,next(q for q in self.m[30]['data_list'] if q['id']==20844))


class ShingetsuBattleTest(unittest.TestCase):
    def test_schedule_updates_client_master_preserves_source_and_closes_again(self):
        import os
        from unittest.mock import patch
        import test_quest_content as fixtures
        flag=patch.dict(os.environ,{'RTD_SHINGETSU_RECONSTRUCTION':'1'})
        flag.start();self.addCleanup(flag.stop)
        fixtures.QuestContentTest.setUp(self)
        source=copy.deepcopy(self.api.masters[30])
        body=dict(name='神月のケモノ',enabled=True,starts_at=None,ends_at=None,
                  quests=[dict(quest_id=q,drops=[]) for q in QUEST_IDS])
        self.api.operations.update('events','shingetsu',body)
        state=self.state()
        flag=next(q for q in self.api.masters[30]['data_list'] if q['id']==10000)['flag_no']
        state['player']['quest_clear_flags'][flag//8]|=1<<(flag%8)
        state['player']['action_point']=999
        self.api.store.save(state)
        opened=self.api.master_table(30)
        self.assertNotEqual(opened['hash'],source['hash'])
        for id in QUEST_IDS:
            row=next(q for q in opened['data_list'] if q['id']==id)
            self.assertFalse(any(row[f'open_type_{i}'] in (4,5) for i in range(1,7)))
            self.assertEqual((row['open_type_1'],row['open_param_1']),(2,10000))
            self.assertEqual((row['open_type_6'],row['open_param_6']),(6,0))
            req=fixtures.QuestContentTest.request(self,id)
            req['hashes']={str(t):str(self.api.master_table(t)['hash']) for t in HASH_TYPES}
            # No mock of admission: this schedule really reopens the quest.
            self.api.call('order_quest',req,self.token)
        self.api.operations.update('events','shingetsu',dict(enabled=False),'PATCH')
        closed=self.api.master_table(30)
        for id in QUEST_IDS:
            row=next(q for q in closed['data_list'] if q['id']==id)
            self.assertEqual((row['open_type_6'],row['open_param_6']),(6,1))
        self.assertEqual(self.api.masters[30],source)

    def test_three_tiers_order_settle_and_retry_without_duplicate_rewards(self):
        import os
        from unittest.mock import patch
        import test_quest_content as fixtures
        flag=patch.dict(os.environ,{'RTD_SHINGETSU_RECONSTRUCTION':'1'})
        flag.start();self.addCleanup(flag.stop)
        fixtures.QuestContentTest.setUp(self)
        for id in QUEST_IDS:
            state=self.state()
            state['player']['action_point']=999
            state['player']['max_unit']=9999
            self.api.store.save(state)
            req=fixtures.QuestContentTest.request(self,id)
            req['hashes']={str(t):str(self.api.master_table(t)['hash']) for t in HASH_TYPES}
            # Protocol-only validation, not a permanent reopening or bypass.
            with patch('rtd.services.battle_entry.require_unlocked'):
                ordered=self.api.call('order_quest',req,self.token)
                self.assertEqual(ordered,self.api.call('order_quest',req,self.token))
            battle=self.state()['battle']
            self.assertEqual(next(e for e in battle['enemy_info_list'] if e['enemy_id']==0)['enemy_set_id'],41102)
            drops=[dict(unit_id=e['drop_unit_id'],level=e['drop_unit_level']) for e in battle['enemy_info_list'] if e['drop_unit_id']][:5]
            before=self.state()['player']['total_paid_point']
            quest=next(q for q in self.api.masters[30]['data_list'] if q['id']==id)
            receipt=dict(ver='2.4.0',retry=0,party_instance_id=self.state()['battle_party_instance_ids'],
                list=[dict(quest_id=id,exp=quest['reward_exp'],game_money=quest['reward_money'],yorisiro_exp=0,
                           units=drops,challenge_id_list=[])])
            result=self.api.call('clear_quest2',receipt,self.token)
            self.assertIsNone(self.state()['battle'])
            after=self.state()
            self.assertEqual(self.api.call('clear_quest2',receipt,self.token),result)
            self.assertEqual(self.state(),after)
            self.assertEqual(after['player']['total_paid_point']-before,1 if id==20846 else 0)

    def state(self):
        return self.api.store.session(self.token)
