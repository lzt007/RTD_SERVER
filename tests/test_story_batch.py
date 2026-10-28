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

BATCH=(11010,11011,11012,11020,11021,11022,11030,11031,11032,11040,11041,11042)


class StoryBatchTest(unittest.TestCase):
    def setUp(self):
        env=patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'1','RTD_VISUAL_RECOVERY':'1'})
        env.start();self.addCleanup(env.stop)
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.path=pathlib.Path(folder.name)/'story.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Story'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        self.quests={q['id']:q for q in self.api.masters[30]['data_list']}

    def state(self):return self.api.store.session(self.token)

    def prepare(self,quest_id,*,wrong_main=False,wrong_helper=False):
        s=self.state();q=self.quests[quest_id]
        for i in range(1,7):
            if q['open_type_'+str(i)]==2 and q['open_param_'+str(i)]:
                flag=self.quests[q['open_param_'+str(i)]]['flag_no']
                s['player']['quest_clear_flags'][flag//8]|=1<<(flag%8)
        s['player'].update(action_point=s['player']['max_action_point'],max_unit=100)
        # Explicit unit-test fixture: same original water unit in three instances.
        for u in s['units'][:3]:u.update(unit_id=10021,level=1,exp=0)
        if wrong_main:s['units'][0]['unit_id']=11100
        s['starter']=1 if wrong_helper else 0
        self.api.store.save(s)

    def order(self,quest_id,helper_id=0):
        req=dict(ver='2.4.0',retry=0,quest_id=quest_id,floor=0,resume_id=0,bonus_stamina=0,
            helper_user_id=helper_id,token=str(uuid.uuid4()),level_data_hash=self.api.levels[quest_id]['hash'],
            hashes={str(t):str(self.api.master_table(t)['hash']) for t in HASH_TYPES})
        return self.api.call('order_quest',req,self.token)

    def clear_request(self,quest_id,challenges=()):
        q=self.quests[quest_id]
        return dict(ver='2.4.0',retry=0,party_instance_id=self.state()['battle_party_instance_ids'],
            list=[dict(quest_id=quest_id,exp=q['reward_exp'],game_money=q['reward_money'],
                yorisiro_exp=0,units=[],challenge_id_list=list(challenges))])

    def test_twelve_original_maps_unlocks_rewards_first_clear_and_formal_availability(self):
        for quest_id in BATCH:
            with self.subTest(quest_id=quest_id):
                self.prepare(quest_id);before=self.state();self.order(quest_id)
                self.assertEqual(self.state()['player']['action_point'],
                    before['player']['action_point']-self.quests[quest_id]['stamina'])
                self.api.call('clear_quest2',self.clear_request(quest_id),self.token)
                after=self.state();flag=self.quests[quest_id]['flag_no']
                self.assertTrue(after['player']['quest_clear_flags'][flag//8]&(1<<(flag%8)))
                self.assertEqual(after['player']['free_paid_point']-before['player']['free_paid_point'],
                    self.quests[quest_id]['present_param'] if self.quests[quest_id]['present_type']==3 else 0)
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):
            api=API(self.path)
            self.assertTrue(all(available(api,q) for q in BATCH))

    def test_formal_story_orders_and_events_work_while_unverified_content_stays_blocked(self):
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):self.api=API(self.path)
        self.assertEqual(self.api.operations.read()['events'],[])
        for quest in BATCH:
            with self.subTest(quest=quest):
                self.prepare(quest)
                self.assertEqual(self.order(quest)['code'],4096)
                self.assertEqual(self.api.call('clear_quest2',self.clear_request(quest),self.token)['code'],4096)
                self.assertIsNone(self.state()['battle'])
        self.prepare(20000);before=self.state()
        with self.assertRaises(ProtocolError):self.order(20000)
        self.assertEqual(self.state(),before)
        self.assertFalse(available(self.api,20101))

    def test_water_challenge_uses_order_snapshot_after_restart_and_unit_revision(self):
        self.prepare(11012);self.order(11012)
        req=self.clear_request(11012,[self.quests[11012]['challenge_id_2']])
        s=self.state()
        self.assertEqual(s['battle_party_unit_ids'],[10021]*3)
        # A later unit revision must not rewrite the party that actually fought.
        s['units'][0]['unit_id']=11100;self.api.store.save(s);self.api=API(self.path)
        result=self.api.call('clear_quest2',req,self.token)
        after=self.state()
        self.assertEqual(result['code'],4096)
        self.assertNotIn('battle_party_unit_ids',after)
        self.assertEqual(self.api.call('clear_quest2',dict(req,retry=1),self.token),result)
        self.assertEqual(self.state(),after)

    def test_four_original_attributes_with_real_friend_helper_snapshot_and_retry(self):
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Helper'))
        helper_token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        self.api.call('send_friend_request',dict(ver='2.4.0',friend_user_id=2),self.token)
        self.api.call('accept_friend_request',dict(ver='2.4.0',friend_user_id=[1]),helper_token)
        # Original water/fire/dark/shine masters, not client-enum numbers.
        for qid,uid,attribute in ((11012,10021,3),(11022,10020,2),
                                  (11032,10023,5),(11042,10022,4)):
            with self.subTest(quest=qid,attribute=attribute):
                self.prepare(qid);s=self.state()
                for unit in s['units'][:3]:unit['unit_id']=uid
                self.api.store.save(s)
                helper=self.api.store.session(helper_token)
                helper['units'][0]['unit_id']=uid;self.api.store.save(helper)
                self.order(qid,helper_id=2)
                snapshot=self.state()
                self.assertEqual(snapshot['battle_party_unit_ids'],[uid]*3)
                self.assertEqual(snapshot['battle_helper']['unit_id'],uid)
                req=self.clear_request(qid,[self.quests[qid]['challenge_id_2']])
                result=self.api.call('clear_quest2',req,self.token)
                after=self.state()
                self.assertEqual(result['code'],4096)
                self.assertEqual(self.api.call('clear_quest2',dict(req,retry=1),self.token),result)
                self.assertEqual(self.state(),after)

    def test_story_catalog_formal_events_and_visual_audit_names_quests(self):
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):api=API(self.path)
        catalog={q['quest_id']:q for q in api.operations.catalog()['quests']}
        for qid in BATCH:
            self.assertTrue(catalog[qid]['event_configurable'])
            self.assertTrue(catalog[qid]['playable'])
        self.assertTrue(catalog[20000]['playable'])
        self.assertFalse(catalog[20101]['playable'])
        event=dict(name='Verified story fixture',enabled=False,starts_at=None,ends_at=None,
                   quests=[dict(quest_id=11010,drops=[])])
        api.operations.update('events','story-fixture',event)
        before=api.operations.read()
        api.operations.update('events','story-fixture',dict(enabled=True),method='PATCH')
        after=api.operations.read()
        self.assertTrue(next(e for e in after['events'] if e['id']=='story-fixture')['enabled'])
        self.assertEqual(after['revision'],before['revision']+1)
        tables={t['id']:t for t in api.masters[21]['data_list']}
        replacements={r['enemy_id']:r for r in api.visual_recovery['substitutions']}
        for qid in BATCH:
            table=tables[self.quests[qid]['enemy_table_id']]
            for key,enemy_id in table.items():
                if key.endswith('_set_id') and enemy_id in replacements:
                    self.assertIn(qid,replacements[enemy_id]['quest_ids'],(qid,enemy_id))

    def test_main_or_helper_mismatch_rejects_challenge_atomically_but_not_clear_without_it(self):
        for main,helper in ((True,False),(False,True)):
            with self.subTest(main=main,helper=helper):
                self.prepare(11012,wrong_main=main,wrong_helper=helper);self.order(11012)
                before=self.state()
                req=self.clear_request(11012,[self.quests[11012]['challenge_id_2']])
                with self.assertRaises(ProtocolError):self.api.call('clear_quest2',req,self.token)
                self.assertEqual(self.state(),before)
                self.api.call('clear_quest2',self.clear_request(11012),self.token)

    def test_missing_or_unknown_party_or_helper_snapshot_never_guesses_attribute(self):
        for invalid in ('missing','unknown','bool','helper'):
            with self.subTest(invalid=invalid):
                self.prepare(11012);self.order(11012);s=self.state()
                if invalid=='missing':s.pop('battle_party_unit_ids',None)
                elif invalid=='unknown':s['battle_party_unit_ids']=[2147483647,10021,10021]
                elif invalid=='bool':s['battle_party_unit_ids']=[True,10021,10021]
                else:s['battle_helper']['unit_id']=2147483647
                self.api.store.save(s);before=self.state()
                with self.assertRaises(ProtocolError):
                    self.api.call('clear_quest2',self.clear_request(11012,[self.quests[11012]['challenge_id_2']]),self.token)
                self.assertEqual(self.state(),before)


if __name__=='__main__':unittest.main()
