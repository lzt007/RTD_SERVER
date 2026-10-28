import copy
import os
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch
from rtd.common import ProtocolError
from rtd.services.api import API
from rtd.services.battle_entry import HASH_TYPES
from rtd.policies.quest_content import available


class QuestContentTest(unittest.TestCase):
    def setUp(self):
        flag=patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'1'});flag.start();self.addCleanup(flag.stop)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'quests.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4());self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Quest'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        state=self.state();state['player']['quest_clear_flags'][0]|=4;self.api.store.save(state)

    def state(self):return self.api.store.session(self.token)
    def request(self,id,floor=0,**kw):
        result=dict(ver='2.4.0',retry=0,quest_id=id,floor=floor,resume_id=0,bonus_stamina=0,
            helper_user_id=0,token=str(uuid.uuid4()),level_data_hash=self.api.levels[id]['hash'],
            hashes={str(t):str(self.api.masters[t]['hash']) for t in HASH_TYPES})
        result.update(kw);return result
    def clear(self,id,challenges=None,**kw):
        quest=next(q for q in self.api.masters[30]['data_list'] if q['id']==id)
        entry=dict(quest_id=id,exp=quest['reward_exp'],game_money=quest['reward_money'],yorisiro_exp=0,
                   units=[],challenge_id_list=challenges or []);entry.update(kw)
        return self.api.call('clear_quest2',dict(ver='2.4.0',retry=0,list=[entry],
            party_instance_id=self.state()['battle_party_instance_ids']),self.token)

    def test_11001_original_unlock_order_snapshot_and_generic_challenge(self):
        req=self.request(11001);before=self.state()
        with self.assertRaises(ProtocolError):self.api.call('order_quest',req,self.token)
        self.assertEqual(self.state(),before)
        state=self.state();state['player']['quest_clear_flags'][0]|=8;self.api.store.save(state)
        result=self.api.call('order_quest',req,self.token)
        self.assertEqual(result['result']['action_point'],state['player']['action_point']-3)
        self.api=API(self.path);self.assertEqual(self.api.call('order_quest',req,self.token),result)
        before=self.state()
        with self.assertRaises(ProtocolError):self.clear(11001,[10])
        self.assertEqual(self.state(),before)
        result=self.clear(11001,[13]);self.assertEqual(result['code'],4096)
        self.assertTrue(self.state()['player']['quest_clear_flags'][0]&16)
        self.assertIn(dict(quest_id=11001,challenge_id=13,state=1),self.state()['player']['quest_challenge_state'])

    def test_11002_crystal_first_clear_only_and_soul_threshold(self):
        state=self.state();state['player']['quest_clear_flags'][0]|=16;self.api.store.save(state)
        self.api.call('order_quest',self.request(11002),self.token)
        before=self.state()
        with self.assertRaises(ProtocolError):self.clear(11002,[17])
        self.assertEqual(self.state(),before)
        self.clear(11002,[16]);first=self.state()['player']['total_paid_point']
        self.api.call('order_quest',self.request(11002),self.token);self.clear(11002,[])
        self.assertEqual(self.state()['player']['total_paid_point'],first)
        self.assertEqual(first,1)

    def test_unverified_content_requires_explicit_experimental_opt_in(self):
        state=self.state();state['player']['quest_clear_flags'][0]|=16;self.api.store.save(state)
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):
            api=API(self.path);before=api.store.session(self.token)
            self.assertTrue(available(api,11002))
            self.assertTrue(available(api,20000))
            self.assertFalse(available(api,20101))
            with self.assertRaises(ProtocolError):api.call('order_quest',self.request(20000),self.token)
            self.assertEqual(api.store.session(self.token),before)

    def test_new_root_can_replace_orphan_from_previous_quest_only_after_validation(self):
        s=self.state();s['player']['quest_clear_flags'][0]|=8;self.api.store.save(s)
        old=self.request(11000);self.api.call('order_quest',old,self.token);before=self.state()
        bad=self.request(11001,hashes={})
        with self.assertRaises(ProtocolError):self.api.call('order_quest',bad,self.token)
        self.assertEqual(self.state(),before)
        new=self.request(11001);self.api.call('order_quest',new,self.token)
        after=self.state();self.assertEqual(after['battle']['quest_id'],11001)
        self.assertIn(old['token'],after['abandoned_battle_order_tokens'])
        self.assertEqual(after['player']['action_point'],before['player']['action_point']-3)
        with self.assertRaises(ProtocolError):self.api.call('order_quest',old,self.token)


if __name__=='__main__':unittest.main()
