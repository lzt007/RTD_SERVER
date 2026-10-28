"""Basic two-account friend persistence using original request/response shapes."""
import copy
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch
from rtd.common import ProtocolError
from rtd.services.api import API


class FriendsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'friends.sqlite3';self.api=API(self.path)
        self.tokens=[]
        for i in range(2):
            key=str(uuid.uuid4())
            self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=i,user_name='Local'+str(i)))
            self.tokens.append(self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id'])

    def state(self,who):return self.api.store.session(self.tokens[who])
    def call(self,op,who=0,api=None,**kw):
        req=dict(ver='2.4.0',retry=0);req.update(kw)
        return (api or self.api).call(op,req,self.tokens[who])['result']
    def link(self):
        self.call('send_friend_request',friend_user_id='2')
        self.call('accept_friend_request',1,friend_user_id=[1])

    def test_search_original_public_dto_and_not_found(self):
        r=self.call('select_user_code',user_id='2')
        self.assertEqual(set(r),{'user_id','user_name','rank','unit_id','unit_level',
                          'unit_bonus_life','unit_bonus_attack','unit_bonus_heal','last_play_date','create_date'})
        self.assertEqual((r['user_id'],r['user_name'],r['unit_id']),(2,'Local1',self.state(1)['units'][0]['unit_id']))
        self.assertIsNone(self.call('select_user_code',user_id='999'))

    def test_apply_accept_lists_retry_restart_and_delete(self):
        self.assertEqual(self.call('send_friend_request',friend_user_id='2'),[])
        self.assertEqual(self.call('send_friend_request',friend_user_id='2',retry=1),[])
        self.assertEqual(self.call('get_friends')[0]['friend_status'],1)
        self.assertEqual(self.call('get_friends',1)[0]['friend_status'],2)
        self.assertEqual(self.call('accept_friend_request',1,friend_user_id=[1]),{'count':1})
        self.assertEqual(self.call('accept_friend_request',1,friend_user_id=[1],retry=1),{'count':0})
        a=self.call('get_friends');b=self.call('get_friends',1)
        self.assertEqual((a[0]['friend_status'],b[0]['friend_status']),(0,0))
        self.assertEqual(len(a[0]),13)
        self.assertEqual(self.call('get_friends',api=API(self.path)),a)
        self.assertEqual(self.call('delete_friend',friend_user_id=[2]),[])
        self.assertEqual(self.call('delete_friend',friend_user_id=[2],retry=1),[])
        self.assertEqual(self.call('get_friends'),[]);self.assertEqual(self.call('get_friends',1),[])

    def test_failed_batch_and_capacity_leave_both_accounts_unchanged(self):
        self.call('send_friend_request',friend_user_id=2)
        before=[self.state(i) for i in range(2)]
        with self.assertRaises(ProtocolError):self.call('accept_friend_request',1,friend_user_id=[1,999])
        self.assertEqual([self.state(i) for i in range(2)],before)
        s=self.state(1);s['player']['max_friend']=0;self.api.store.save(s)
        with self.assertRaises(ProtocolError) as e:self.call('accept_friend_request',1,friend_user_id=[1])
        self.assertEqual(e.exception.args[0],8704)
        self.assertEqual(self.call('get_friends')[0]['friend_status'],1)

    def test_invalid_self_unknown_and_outgoing_accept(self):
        for op,params in (('send_friend_request',dict(friend_user_id=True)),
                          ('send_friend_request',dict(friend_user_id=1)),
                          ('send_friend_request',dict(friend_user_id=999)),
                          ('accept_friend_request',dict(friend_user_id=[2])),
                          ('delete_friend',dict(friend_user_id=[2,2]))):
            before=[self.state(i) for i in range(2)]
            with self.assertRaises(ProtocolError):self.call(op,**params)
            self.assertEqual([self.state(i) for i in range(2)],before)

    def test_two_account_write_failure_rolls_back_relationship(self):
        before=[self.state(i) for i in range(2)];save=self.api.store.save
        def fail_after_save(s):
            save(s)
            if s['player']['user_id']==2:raise RuntimeError('injected other-account failure')
        with patch.object(self.api.store,'save',side_effect=fail_after_save):
            with self.assertRaises(RuntimeError):self.call('send_friend_request',friend_user_id=2)
        self.assertEqual([self.state(i) for i in range(2)],before)

    def test_current_profile_follows_active_party_leader(self):
        self.link();s=self.state(1);s['party']['party'][0]['instanceIds'][0:2]=list(reversed(s['party']['party'][0]['instanceIds'][0:2]));self.api.store.save(s)
        r=self.call('get_friends')[0]
        self.assertEqual(r['unit_id'],s['units'][1]['unit_id'])
        self.assertEqual(self.call('select_user_code',user_id=2)['unit_id'],r['unit_id'])

    def gift_unit(self):
        s=self.state(0);u=copy.deepcopy(s['units'][0]);u.update(instance_id=1004,unit_id=10000,
            member_id=0,leader=0,level=2,exp=30,attribute_exp=7,bonus_limit=2,favorite=0)
        s['units'].append(u);s['party']['party'][0]['instanceIds'][3]=1004;self.api.store.save(s)
        return u

    def test_gift_moves_unit_to_inbox_and_preserves_progress_on_claim(self):
        self.link();original=self.gift_unit()
        self.assertEqual(self.call('send_present',friend_user_id='2',unit_instance_id='1004'),[])
        self.assertNotIn(1004,[u['instance_id'] for u in self.state(0)['units']])
        self.assertEqual(self.state(0)['party']['party'][0]['instanceIds'][3],0)
        gifts=self.call('get_presents',1);self.assertEqual(len(gifts),1)
        self.assertEqual((gifts[0]['send_user_id'],gifts[0]['present_param_0'],gifts[0]['present_param_1']),(1,10000,2))
        self.assertEqual(self.call('send_present',friend_user_id=2,unit_instance_id=1004,retry=1),[])
        self.assertEqual(len(self.call('get_presents',1)),1)
        serial=gifts[0]['serial_number']
        r=self.call('open_present',1,serial_number_list=[serial]);unit=r['get_units'][0]
        self.assertEqual((unit['instance_id'],unit['user_id']),(2004,2))
        for key in ('unit_id','level','exp','attribute_exp','bonus_limit'):
            self.assertEqual(unit[key],original[key])
        self.assertEqual(self.call('open_present',1,serial_number_list=[serial])['get_units'],[])
        self.assertEqual(len(self.state(1)['units']),4)

    def test_gift_nonfriend_favorite_main_and_nonpresent_master_rejected(self):
        self.gift_unit()
        with self.assertRaises(ProtocolError):self.call('send_present',friend_user_id=2,unit_instance_id=1004)
        self.link()
        for update in (dict(favorite=1),dict(bonus_attack=1),dict(unit_id=20000)):
            s=self.state(0);s['units'][-1].update(update);self.api.store.save(s)
            before=[self.state(i) for i in range(2)]
            with self.assertRaises(ProtocolError):self.call('send_present',friend_user_id=2,unit_instance_id=1004)
            self.assertEqual([self.state(i) for i in range(2)],before)
            s=self.state(0);s['units'][-1].update(favorite=0,bonus_attack=0,unit_id=10000);self.api.store.save(s)
        with self.assertRaises(ProtocolError):self.call('send_present',friend_user_id=2,unit_instance_id=1001)

    def test_gift_write_failure_rolls_back_both_inventories(self):
        self.link();self.gift_unit();before=[self.state(i) for i in range(2)];save=self.api.store.save
        def fail_after_save(s):
            save(s)
            if s['player']['user_id']==2:raise RuntimeError('injected gift inbox failure')
        with patch.object(self.api.store,'save',side_effect=fail_after_save):
            with self.assertRaisesRegex(RuntimeError,'injected gift inbox failure'):
                self.call('send_present',friend_user_id=2,unit_instance_id=1004)
        self.assertEqual([self.state(i) for i in range(2)],before)

    def test_helpers_show_only_accepted_local_peers_and_keep_npc(self):
        self.call('send_friend_request',friend_user_id=2)
        self.assertEqual([r['user_id'] for r in self.call('get_helpers')],[0])
        self.call('accept_friend_request',1,friend_user_id=[1])
        rows=self.call('get_helpers');self.assertEqual([r['user_id'] for r in rows],[0,2])
        self.assertEqual((rows[1]['friend'],rows[1]['friend_point']),(True,False))
        self.assertEqual(rows[1]['unit_id'],self.state(1)['units'][0]['unit_id'])
        self.call('delete_friend',friend_user_id=[2])
        self.assertEqual([r['user_id'] for r in self.call('get_helpers')],[0])

    def test_friend_order_snapshot_survives_friend_profile_change_and_removal(self):
        from rtd.services.battle_entry import HASH_TYPES
        self.link();s=self.state(0);s['player']['quest_clear_flags'][0]|=4;self.api.store.save(s)
        req=dict(quest_id=11000,floor=0,resume_id=0,bonus_stamina=0,helper_user_id='2',
                 token=str(uuid.uuid4()),level_data_hash=self.api.levels[11000]['hash'],
                 hashes={str(t):str(self.api.masters[t]['hash']) for t in HASH_TYPES})
        self.call('order_quest',**req);before=self.state(0)
        self.assertEqual(before['battle_helper']['user_id'],2)
        peer=self.state(1);peer['units'][0]['level']=2;self.api.store.save(peer)
        self.call('delete_friend',friend_user_id=[2]);req['retry']=1
        self.call('order_quest',**req)
        after=self.state(0);self.assertEqual(after['battle_helper'],before['battle_helper'])
        self.assertEqual(after['player']['action_point'],before['player']['action_point'])


if __name__=='__main__':unittest.main()
