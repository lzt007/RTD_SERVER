"""Original area150 contracts, using disposable test accounts only."""
import copy
import os
import json
import unittest
import uuid
from unittest.mock import patch

import test_story_batch as story_tests
from rtd.common import ProtocolError
from rtd.services.api import API
from rtd.policies.quest_content import available
from rtd.config import ROOT
from rtd.masters.catalog import load_catalog
from rtd.operations.configuration import ConfigurationError
from test_live_configuration import event

QUESTS=(11050,11051,11052,11053)


class StoryArea150Test(unittest.TestCase):
    setUp=story_tests.StoryBatchTest.setUp
    state=story_tests.StoryBatchTest.state
    order=story_tests.StoryBatchTest.order
    clear_request=story_tests.StoryBatchTest.clear_request

    def test_formal_area150_orders_events_and_unverified_floor_gate(self):
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):self.api=API(self.path)
        catalog={q['quest_id']:q for q in self.api.operations.catalog()['quests']}
        self.assertTrue(all(catalog[q]['playable'] for q in QUESTS))
        self.assertEqual(self.api.operations.read()['events'],[])
        for qid in QUESTS:
            with self.subTest(quest=qid):
                self.prepare(qid)
                self.assertEqual(self.order(qid)['code'],4096)
                self.assertEqual(self.api.call('clear_quest2',self.clear_request(qid,[]),self.token)['code'],4096)
                self.assertIsNone(self.state()['battle'])
        cfg=event(id='area150',quests=[dict(quest_id=q,drops=[]) for q in QUESTS])
        self.api.operations.update('events','area150',cfg)
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):self.api=API(self.path)
        self.assertTrue(all(self.api.operations.event_for_quest(q)[0]['id']=='area150' for q in QUESTS))
        self.assertFalse(available(self.api,20101))
        before=self.api.operations.read()
        with self.assertRaises(ConfigurationError):
            self.api.operations.update('events','unverified',event(id='unverified',quests=[dict(quest_id=20101,drops=[])]))
        self.assertEqual(self.api.operations.read(),before)

    def prepare(self,quest_id,*,unlock=True,unit_id=12000):
        s=self.state();q=self.quests[quest_id]
        if unlock:
            previous=self.quests[q['open_param_1']]['flag_no']
            s['player']['quest_clear_flags'][previous//8]|=1<<(previous%8)
        s['player'].update(action_point=s['player']['max_action_point'],max_unit=100)
        for unit in s['units'][:3]:unit.update(unit_id=unit_id,level=1,exp=0)
        self.api.store.save(s)

    def helper(self,unit_id=12000):
        # Explicit temporary accepted-friend fixture, not natural acquisition.
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Rarity'))
        token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        peer=self.api.store.session(token)
        for unit in peer['units'][:3]:unit.update(unit_id=unit_id,level=1,exp=0)
        self.api.store.save(peer)
        uid=peer['player']['user_id'];s=self.state()
        s.setdefault('friend_links',{})[str(uid)]=dict(status=0)
        self.api.store.save(s)
        return uid,token

    def test_area150_prerequisites_rewards_and_challenge_attestations(self):
        before=self.state()
        with self.assertRaises(ProtocolError):self.order(11050)
        self.assertEqual(self.state(),before)
        for qid,cost in zip(QUESTS,(5,5,5,6)):
            with self.subTest(quest=qid):
                self.prepare(qid,unlock=qid==11050)
                before=self.state()
                # Valid minimum rolls make all positive-rate original encounters
                # present, so the18-enemy challenge has a deterministic bound.
                with patch('rtd.services.battle_generation.secrets.SystemRandom') as rng:
                    rng.return_value.randint.side_effect=lambda a,b:a
                    self.assertEqual(self.order(qid)['code'],4096)
                self.assertEqual(self.state()['player']['action_point'],before['player']['action_point']-cost)
                ids=[self.quests[qid][f'challenge_id_{i}'] for i in range(3)]
                if qid==11053:ids.remove(70)  # Default helper is five-star.
                request=self.clear_request(qid,ids)
                request['list'][0]['yorisiro_exp']=int((50*self.quests[qid]['reward_soul'])**0.65)*15
                result=self.api.call('clear_quest2',request,self.token)
                after=self.state();flag=self.quests[qid]['flag_no']
                self.assertTrue(after['player']['quest_clear_flags'][flag//8]&(1<<(flag%8)))
                self.assertTrue(all(dict(quest_id=qid,challenge_id=i,state=1) in
                                    after['player']['quest_challenge_state'] for i in ids))
                self.assertEqual(after['player']['exp']-before['player']['exp'],self.quests[qid]['reward_exp'])
                self.api=API(self.path)
                self.assertEqual(self.api.call('clear_quest2',dict(request,retry=1),self.token),result)
                self.assertEqual(self.state(),after)
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):self.api=API(self.path)
        for qid in QUESTS:
            self.assertTrue(available(self.api,qid))

    def test_rarity_includes_helper_uses_original_category_after_restart(self):
        self.prepare(11053);uid,token=self.helper()
        self.order(11053,uid)
        # Current units/lineup and current helper leader change after entry;
        # original accepted four-unit category remains three-star.
        state=self.state()
        for unit in state['units'][:3]:unit['unit_id']=11000
        group=state['party']['party'][state['party']['active']]['instanceIds']
        group[:3]=list(reversed(group[:3]));self.api.store.save(state)
        peer=self.api.store.session(token);peer['units'][0]['unit_id']=11050
        self.api.store.save(peer);self.api=API(self.path)
        self.assertEqual(self.api.call('clear_quest2',self.clear_request(11053,[70]),self.token)['code'],4096)

    def test_rarity_rejects_lower_higher_or_missing_original_party_and_helper(self):
        for case in ('main-low','main-high','helper-low','helper-high','missing','unknown','bool','helper-missing'):
            with self.subTest(case=case):
                self.prepare(11053)
                unit=11000 if case=='helper-low' else 11050 if case=='helper-high' else 12000
                uid,_=self.helper(unit)
                if case in ('main-low','main-high'):
                    s=self.state();s['units'][0]['unit_id']=11000 if case=='main-low' else 11050
                    self.api.store.save(s)
                self.order(11053,uid);s=self.state()
                if case=='missing':s.pop('battle_party_unit_ids',None)
                elif case=='unknown':s['battle_party_unit_ids']=[2147483647,12000,12000]
                elif case=='bool':s['battle_party_unit_ids']=[True,12000,12000]
                elif case=='helper-missing':s['battle_helper'].pop('unit_id',None)
                self.api.store.save(s);self.api=API(self.path);before=self.state()
                with self.assertRaises(ProtocolError):
                    self.api.call('clear_quest2',self.clear_request(11053,[70]),self.token)
                self.assertEqual(self.state(),before)
                self.assertEqual(self.api.call('clear_quest2',self.clear_request(11053),self.token)['code'],4096)

    def test_invalid_attested_challenge_ids_roll_back_and_retry_once(self):
        self.prepare(11050);self.order(11050)
        valid=self.clear_request(11050,[60,62]);before=self.state()
        for invalid in ([63],[60,60],[999999],[True],['62'],62):
            bad=copy.deepcopy(valid);bad['list'][0]['challenge_id_list']=invalid
            with self.subTest(challenges=invalid),self.assertRaises(ProtocolError):
                self.api.call('clear_quest2',bad,self.token)
            self.assertEqual(self.state(),before)
        condition=next(c for c in self.api.masters[32]['data_list'] if c['id']==62)
        condition['type']=999
        with self.assertRaises(ProtocolError):self.api.call('clear_quest2',valid,self.token)
        self.assertEqual(self.state(),before);condition['type']=42
        result=self.api.call('clear_quest2',valid,self.token);after=self.state()
        self.api=API(self.path)
        self.assertEqual(self.api.call('clear_quest2',dict(valid,retry=1),self.token),result)
        self.assertEqual(self.state(),after)
        reward=dict(ver='2.4.0',retry=0,reward_id=60)
        response=self.api.call('post_quest_challenge_reward',reward,self.token)
        delivered=self.state();self.assertEqual(response['result']['present_param_0'],15014)
        self.api=API(self.path)
        self.assertEqual(self.api.call('post_quest_challenge_reward',dict(reward,retry=1),self.token),response)
        self.assertEqual(self.state(),delivered)

    def test_area150_new_missing_visuals_are_explicit_without_gameplay_changes(self):
        document=json.loads((ROOT/'config/enemy-visual-placeholders.json').read_text())
        replacements={r['enemy_id']:r for r in document['substitutions']}
        expected={12101:{11052},41236:{11050},41237:{11051},41238:{11052}}
        self.assertTrue(expected.keys()<=replacements.keys())
        original,_=load_catalog();source={e['id']:e for e in original[20]['data_list']}
        derived={e['id']:e for e in self.api.masters[20]['data_list']}
        for enemy,quests in expected.items():
            with self.subTest(enemy=enemy):
                record=replacements[enemy]
                self.assertTrue(quests<=set(record['quest_ids']))
                self.assertEqual(record['after'],dict(model='ms02_four_un_01_zako',texture='na'))
                row=copy.deepcopy(derived[enemy])
                self.assertEqual({k:row[k] for k in ('model','texture')},record['after'])
                row.update(record['before'])
                self.assertEqual(row,source[enemy])


if __name__=='__main__':unittest.main()
