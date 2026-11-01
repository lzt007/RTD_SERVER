"""Next twenty original quests: disposable protocol fixtures, never live wins."""
import copy
import json
import os
import sqlite3
import unittest
from unittest.mock import patch

import test_story_area150 as area_tests
import test_story_batch as story_tests
from rtd.common import ProtocolError
from rtd.config import ROOT
from rtd.masters.catalog import load_catalog
from rtd.policies.quest_content import available
from rtd.services.api import API

QUESTS=tuple(11100+10*i+j for i in range(5) for j in range(4))
COSTS=(5,5,5,6,5,5,6,6,6,6,6,7,6,6,6,7,6,6,7,7)


class Story160200Test(unittest.TestCase):
    setUp=story_tests.StoryBatchTest.setUp
    state=story_tests.StoryBatchTest.state
    order=story_tests.StoryBatchTest.order
    clear_request=story_tests.StoryBatchTest.clear_request
    helper=area_tests.StoryArea150Test.helper

    def test_original_batch_prerequisites_ap_rewards_and_restart_receipts(self):
        before=self.state()
        with self.assertRaises(ProtocolError):self.order(QUESTS[0])
        self.assertEqual(self.state(),before)
        uid,token=self.helper()
        challenges={c['id']:c for c in self.api.masters[32]['data_list']}
        units=self.api.masters[10]['data_list']
        state=self.state();flag=self.quests[11053]['flag_no']
        state['player']['quest_clear_flags'][flag//8]|=1<<(flag%8)
        self.api.store.save(state)
        for qid,cost in zip(QUESTS,COSTS):
            with self.subTest(quest=qid):
                q=self.quests[qid]
                ids=[q[f'challenge_id_{i}'] for i in range(3)]
                rules=[challenges[i] for i in ids]
                chosen=next(u for u in units if all(
                    c['type'] not in (21,23) or u['category' if c['type']==21 else 'attribute']==c['param_0']
                    for c in rules))
                state=self.state()
                state['player'].update(action_point=100,max_unit=1000)
                for u in state['units'][:3]:u.update(unit_id=chosen['id'],level=1,exp=0)
                self.api.store.save(state)
                peer=self.api.store.session(token)
                for u in peer['units'][:3]:u.update(unit_id=chosen['id'],level=1,exp=0)
                self.api.store.save(peer)
                before=self.state()
                with patch('rtd.services.battle_generation.secrets.SystemRandom') as rng:
                    rng.return_value.randint.side_effect=lambda a,b:a
                    self.assertEqual(self.order(qid,uid)['code'],4096)
                self.assertEqual(self.state()['player']['action_point'],100-cost)
                request=self.clear_request(qid,ids)
                request['list'][0]['yorisiro_exp']=int((50*q['reward_soul'])**0.65)*15
                result=self.api.call('clear_quest2',request,self.token)
                after=self.state();flag=q['flag_no']
                self.assertTrue(after['player']['quest_clear_flags'][flag//8]&(1<<(flag%8)))
                self.assertEqual(after['player']['exp']-before['player']['exp'],q['reward_exp'])
                self.assertEqual(after['player']['free_paid_point']-before['player']['free_paid_point'],
                                 q['present_param'] if q['present_type']==3 else 0)
                self.assertTrue(all(dict(quest_id=qid,challenge_id=i,state=1) in
                                    after['player']['quest_challenge_state'] for i in ids))
                with sqlite3.connect(self.path) as db:
                    count=db.execute('SELECT COUNT(*) FROM operation_receipts').fetchone()[0]
                self.assertEqual(count,QUESTS.index(qid)+1)
                self.api=API(self.path)
                self.assertEqual(self.api.call('clear_quest2',dict(request,retry=1),self.token),result)
                self.assertEqual(self.state(),after)
                with sqlite3.connect(self.path) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM operation_receipts').fetchone()[0],count)
        self.assertEqual(sum(COSTS),119)

    def test_main_story_available_without_experimental_mode(self):
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):self.api=API(self.path)
        for qid in QUESTS:self.assertTrue(available(self.api,qid))
        for qid in (11150,20101):self.assertFalse(available(self.api,qid))

    def test_fixed_visuals_preserve_all_original_gameplay_fields(self):
        document=json.loads((ROOT/'config/enemy-visual-placeholders.json').read_text())
        records={r['enemy_id']:r for r in document['substitutions']}
        expected={10120,10221,10231,10322,10500,10501,10502,10512,10521,
                  11010,11011,11012,11013,12201,41539,41540,41541,41542,
                  41543,41544,41545,41546}
        self.assertTrue(expected<=records.keys(),sorted(expected-records.keys()))
        original,_=load_catalog();source={r['id']:r for r in original[20]['data_list']}
        derived={r['id']:r for r in self.api.masters[20]['data_list']}
        tables={t['id']:t for t in original[21]['data_list']}
        for enemy in expected:
            with self.subTest(enemy=enemy):
                record=records[enemy]
                self.assertEqual(record['after'],dict(model='ms02_four_un_01_zako',texture='na'))
                row=copy.deepcopy(derived[enemy]);row.update(record['before'])
                self.assertEqual(row,source[enemy])
                self.assertEqual({k:derived[enemy][k] for k in ('model','texture')},record['after'])
                for qid in QUESTS:
                    table=tables[self.quests[qid]['enemy_table_id']]
                    if enemy in [v for k,v in table.items() if k.endswith('_set_id')]:
                        self.assertIn(qid,record['quest_ids'])


if __name__=='__main__':unittest.main()
