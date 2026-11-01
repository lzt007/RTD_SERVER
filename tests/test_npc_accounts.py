"""Persistent newcomer helpers on disposable databases."""
import pathlib
import tempfile
import unittest
import uuid
from rtd.services.api import API
from rtd.common import ProtocolError
from rtd.services.npc_accounts import seed

class NpcAccountsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'npc.sqlite3';self.api=API(self.path)
        self.key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=self.key,unit_no=0,user_name='Beginner'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=self.key))['session_id']
    def call(self,op,**kw):return self.api.call(op,dict(ver='2.4.0',retry=0,**kw),self.token)['result']
    def test_seed_roster_restart_and_autoaccept(self):
        ids=seed(self.api)
        self.assertEqual(len(ids),9)
        self.assertEqual(seed(API(self.path)),ids)
        rows={r['user_id']:r for r in self.call('get_helpers')}
        self.assertTrue(set(ids)<=set(rows))
        self.assertEqual({rows[i]['unit_id'] for i in ids},{15550,15559,15562,15565,15577,16003,14209,15033,14203})
        for uid in ids:
            row=rows[uid]
            master=next(r for r in self.api.masters[10]['data_list'] if r['id']==row['unit_id'])
            self.assertEqual(row['unit_level'],master['lv_max'])
            self.assertFalse(row['friend'])
        self.call('send_friend_request',friend_user_id=str(ids[0]))
        self.assertEqual(self.call('get_friends')[0]['friend_status'],0)
        self.assertEqual(self.api.store.by_id(ids[0])['friend_links']['1']['status'],0)
        self.assertEqual(self.call('select_user_code',user_id=ids[0])['unit_level'],99)
        self.call('delete_friend',friend_user_id=[ids[0]])
        self.assertEqual(self.call('get_friends'),[])
    def test_npc_cannot_authenticate_and_seed_preserves_state(self):
        uid=seed(self.api)[0]
        with self.api.store.connect() as db:key=db.execute('SELECT uuid FROM players WHERE id=?',(uid,)).fetchone()[0]
        with self.assertRaises(ProtocolError):self.api.call('auth_user',dict(ver='2.4.0',uuid=key))
        state=self.api.store.by_id(uid);state['player']['friend_point']=321;self.api.store.save(state)
        seed(self.api)
        self.assertEqual(self.api.store.by_id(uid),state)

    def test_npc_battle_clear_rewards_and_autoaccepted_friend(self):
        from rtd.services.battle_entry import HASH_TYPES
        uid=seed(self.api)[-1]
        self.call('send_friend_request',friend_user_id=uid)
        state=self.api.store.session(self.token)
        rank=self.api.masters[60]['data_list'][99]
        state['player'].update(rank=100,exp=rank['need_exp'],max_unit=100)
        state['player']['quest_clear_flags'][0]|=4
        self.api.store.save(state)
        self.call('order_quest',quest_id=11000,floor=0,resume_id=0,bonus_stamina=0,
                  helper_user_id=uid,token=str(uuid.uuid4()),
                  level_data_hash=self.api.levels[11000]['hash'],
                  hashes={str(t):str(self.api.master_table(t)['hash']) for t in HASH_TYPES})
        state=self.api.store.session(self.token)
        self.assertEqual(state['battle_helper']['unit_level'],80)
        q=next(q for q in self.api.masters[30]['data_list'] if q['id']==11000)
        self.call('clear_quest2',list=[dict(quest_id=11000,exp=q['reward_exp'],
                  game_money=q['reward_money'],yorisiro_exp=0,units=[],challenge_id_list=[])],
                  party_instance_id=state['battle_party_instance_ids'])
        self.assertEqual(self.api.store.session(self.token)['player']['friend_point'],10)
        self.assertEqual(self.api.store.by_id(uid)['helper_reward_pending']['points'],10)

    def test_npc_can_help_more_than_one_hundred_players(self):
        uid=seed(self.api)[0]
        state=self.api.store.by_id(uid)
        state['friend_links']={str(i):dict(status=0,date='2026-11-01T00:00:00Z') for i in range(1000,1100)}
        self.api.store.save(state)
        self.call('send_friend_request',friend_user_id=uid)
        self.assertEqual(self.call('get_friends')[0]['friend_status'],0)
