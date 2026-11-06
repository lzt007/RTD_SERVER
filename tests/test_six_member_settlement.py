import copy
import os
from unittest.mock import patch
import test_quest_content as fixtures
from rtd.common import ProtocolError


import unittest


class SixMemberSettlementTest(unittest.TestCase):
    state=fixtures.QuestContentTest.state
    request=fixtures.QuestContentTest.request
    def setUp(self):
        flags=patch.dict(os.environ,{'RTD_EVENT_RECONSTRUCTION':'1'})
        flags.start();self.addCleanup(flags.stop)
        fixtures.QuestContentTest.setUp(self)

    def test_four_weapon_quests_use_five_owned_slots_and_strict_receipts(self):
        ids=list(range(20840,20844))
        self.api.operations.update('events','six-member-test',dict(name='Six member test',enabled=True,
            starts_at=None,ends_at=None,quests=[dict(quest_id=i,drops=[]) for i in ids]))
        for qid in ids:
            with self.subTest(quest=qid):
                state=self.state();state['player']['action_point']=9999;state['player']['max_unit']=99999
                state['player']['quest_clear_flags']=[255]*len(state['player']['quest_clear_flags'])
                while len(state['units'])<5:
                    unit=copy.deepcopy(state['units'][0]);unit['instance_id']=max(u['instance_id'] for u in state['units'])+1
                    state['units'].append(unit)
                party=[u['instance_id'] for u in state['units'][:5]]
                state['party']['party'][state['party']['active']]['instanceIds']=party
                self.api.store.save(state)
                q=next(q for q in self.api.masters[30]['data_list'] if q['id']==qid)
                self.assertEqual(q['pt_num'],6)
                request=self.request(qid)
                request['hashes']={str(t):str(self.api.master_table(int(t))['hash']) for t in request['hashes']}
                self.api.call('order_quest',request,self.token)
                frozen=self.state()
                self.assertEqual(frozen['battle_party_instance_ids'],party+[0])
                self.assertEqual(len(frozen['battle_attribute_rewards']['party']),5)
                from rtd.policies.party_challenges import _party_masters
                self.assertEqual(len(_party_masters(self.api,frozen)),6)
                entry=dict(quest_id=qid,exp=q['reward_exp'],game_money=q['reward_money'],yorisiro_exp=0,units=[],challenge_id_list=[])
                receipt=dict(ver='2.4.0',retry=0,list=[entry],party_instance_id=party+[0])
                bad=copy.deepcopy(receipt);bad['party_instance_id'][3]=0
                with self.assertRaises(ProtocolError):self.api.call('clear_quest2',bad,self.token)
                self.assertEqual(self.state(),frozen)
                result=self.api.call('clear_quest2',receipt,self.token)
                self.assertIsNone(self.state()['battle'])
                self.assertEqual(result,self.api.call('clear_quest2',dict(receipt,retry=1),self.token))
