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


class BattleLayersTest(unittest.TestCase):
    def setUp(self):
        flag=patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'1'});flag.start();self.addCleanup(flag.stop)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=pathlib.Path(self.temp.name)/'layers.sqlite3';self.api=API(self.path)
        # The recovered root expired in 2013. Protocol fixtures explicitly open
        # it; production masters and default resource gates remain untouched.
        root=next(q for q in self.api.masters[30]['data_list'] if q['id']==20000)
        root['open_type_2']=root['open_type_3']=0
        # Several original layer drop rows are absent from this master version.
        # Explicit no-drop fixture rows exercise the protocol, not original loot.
        drops=self.api.masters[22]['data_list'];known={d['id'] for d in drops}
        for q in self.api.masters[30]['data_list']:
            if q['id'] not in (20000,20100):continue
            table=next(t for t in self.api.masters[21]['data_list'] if t['id']==q['enemy_table_id'])
            for key,value in table.items():
                if key.endswith('_drop_id') and value not in known:
                    drops.append(dict(drops[0],id=value));known.add(value)
        key=str(uuid.uuid4());self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Layers'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        state=self.state();state['player']['quest_clear_flags'][0]|=4
        state['player'].update(free_paid_point=3,paid_point=0,total_paid_point=3);self.api.store.save(state)

    def state(self):return self.api.store.session(self.token)
    def req(self,id,floor=0,**kw):
        result=dict(ver='2.4.0',retry=0,quest_id=id,floor=floor,resume_id=0,bonus_stamina=0,
            helper_user_id=0,token=str(uuid.uuid4()),level_data_hash=self.api.levels[id]['hash'],
            hashes={str(t):str(self.api.masters[t]['hash']) for t in HASH_TYPES})
        result.update(kw);return result
    def order(self,id=20000,floor=0,**kw):
        req=self.req(id,floor,**kw);return req,self.api.call('order_quest',req,self.token)
    def entry(self,id):
        q=next(q for q in self.api.masters[30]['data_list'] if q['id']==id)
        return dict(quest_id=id,exp=q['reward_exp'],game_money=q['reward_money'],yorisiro_exp=0,
                    units=[],challenge_id_list=[])
    def clear_req(self):return dict(ver='2.4.0',retry=0,list=[self.entry(20000),self.entry(20100)],
        party_instance_id=self.state()['battle_party_instance_ids'])

    def test_formal_verified_paths_require_explicit_event_and_keep_other_children_gated(self):
        from rtd.policies.quest_content import available
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):self.api=API(self.path)
        children=(20100,20103,20110,20120,20122,20131)
        self.assertTrue(available(self.api,20000))
        self.assertFalse(available(self.api,20101))
        self.assertEqual(self.api.operations.read()['events'],[])
        before=self.state()
        with self.assertRaises(ProtocolError):self.order()
        self.assertEqual(self.state(),before)  # Original expired schedule remains.
        catalog=self.api.operations.catalog()
        rows={q['quest_id']:q for q in catalog['quests']}
        for qid in (20000,)+children:self.assertTrue(rows[qid]['playable'])
        self.assertFalse(rows[20101]['playable'])
        event_quests=[]
        for qid in (20000,)+children:
            drops=[dict(drop_data_id=d['drop_data_id'],entries=[],no_drop_weight=1)
                   for d in catalog['event_quest_drops'][str(qid)] if d.get('original_missing')]
            event_quests.append(dict(quest_id=qid,drops=drops))
        self.api.operations.update('events','verified-layers',dict(name='Explicit local no-drop fixture',
            enabled=True,starts_at=None,ends_at=None,quests=event_quests))
        for child in children:
            with self.subTest(child=child):
                state=self.state();state['player']['action_point']=state['player']['max_action_point']
                self.api.store.save(state)  # Disposable test stamina, not live QA.
                hashes={str(t):str(self.api.master_table(t)['hash']) for t in HASH_TYPES}
                root_request,root=self.order(hashes=hashes);self.assertEqual(root['code'],4096)
                paid=self.state()
                with self.assertRaises(ProtocolError):self.order(20101,1,hashes=hashes)
                self.assertEqual(self.state(),paid)
                self.assertEqual(self.order(child,1,hashes=hashes)[1]['code'],4096)
                self.assertEqual(self.state()['player']['action_point'],paid['player']['action_point'])
                request=dict(ver='2.4.0',retry=0,list=[self.entry(20000),self.entry(child)],
                    party_instance_id=self.state()['battle_party_instance_ids'])
                cleared=self.api.call('clear_quest2',request,self.token)
                self.assertEqual(cleared['code'],4096);self.assertEqual(len(cleared['result']),2)
                after=self.state()
                with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):self.api=API(self.path)
                self.assertEqual(self.api.call('clear_quest2',dict(request,retry=1),self.token),cleared)
                self.assertEqual(self.state(),after)

    def test_disabled_visual_recovery_rejects_layer_before_order_mutation(self):
        drops=copy.deepcopy(self.api.masters[22]['data_list'])
        with patch.dict(os.environ,{'RTD_VISUAL_RECOVERY':'0'}):
            self.api=API(self.path)
        root=next(q for q in self.api.masters[30]['data_list'] if q['id']==20000)
        root['open_type_2']=root['open_type_3']=0
        self.api.masters[22]['data_list']=drops
        before=self.state()
        with self.assertRaisesRegex(ProtocolError,'requires approved visual recovery'):
            self.api.call('order_quest',self.req(20000),self.token)
        self.assertEqual(self.state(),before)
        self.assertIsNone(self.api.store.active_run(before['player']['user_id']))

    def test_real_stairs_new_quest_id_snapshot_array_no_second_ap_charge(self):
        before=self.state();root,first=self.order();after=self.state()
        self.assertEqual(after['player']['action_point'],before['player']['action_point']-7)
        run=self.api.store.active_run(after['player']['user_id'])
        stairs=[e for e in first['result']['enemy_info_list'] if e['drop_data_id']==20100]
        self.assertTrue(stairs);self.assertTrue(all(e['drop_unit_id']==0 and e['flag'] for e in stairs))
        next_req,next_result=self.order(20100,1)
        self.assertEqual(next_result['result']['action_point'],after['player']['action_point'])
        self.assertEqual(self.api.store.active_run(after['player']['user_id']),run)
        self.api=API(self.path)
        self.assertEqual(self.api.call('order_quest',next_req,self.token),next_result)
        info=self.api.call('get_quest_info',dict(ver='2.4.0'),self.token)['result']
        self.assertEqual([b['quest_id'] for b in info],[20000,20100]);self.assertEqual(info[1]['quest_status'],1)
        before=self.state()
        for bad in (self.req(20100,3),self.req(11000,2),self.req(20100,0),root):
            with self.subTest(bad=bad['quest_id']),self.assertRaises(ProtocolError):
                self.api.call('order_quest',bad,self.token)
            self.assertEqual(self.state(),before)

    def test_batch_settlement_one_receipt_restart_and_no_partial_reward(self):
        self.order();self.order(20100,1);req=self.clear_req();before=self.state()
        bad=copy.deepcopy(req);bad['list'][1]['game_money']=10**9
        with self.assertRaises(ProtocolError):self.api.call('clear_quest2',bad,self.token)
        self.assertEqual(self.state(),before)
        result=self.api.call('clear_quest2',req,self.token)
        self.assertEqual(len(result['result']),2);after=self.state()
        self.assertIsNone(after['battle']);self.assertNotIn('battle_history',after)
        self.assertEqual(len(after['units']),len(before['units'])+2)
        self.assertEqual(after['player']['exp'],before['player']['exp']+330)
        self.api=API(self.path)
        self.assertEqual(self.api.call('clear_quest2',dict(req,retry=1),self.token),result)
        self.assertEqual(self.state(),after)
        with self.api.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM operation_receipts').fetchone()[0],1)

    def test_continue_count_across_layers_and_old_floor_replay_rejected(self):
        self.order()
        req=dict(ver='2.4.0',retry=0,floor=0,quest_continue=1)
        self.api.call('continue_quest',req,self.token)
        self.order(20100,1);self.assertEqual(self.state()['battle']['quest_continue'],1)
        before=self.state()
        with self.assertRaises(ProtocolError):self.api.call('continue_quest',dict(req,retry=1),self.token)
        self.assertEqual(self.state(),before)
        result=self.api.call('continue_quest',dict(req,floor=1,quest_continue=2),self.token)
        self.assertEqual(result['result']['total_paid_point'],1)
        self.assertEqual(self.api.call('continue_quest',dict(req,floor=1,quest_continue=2,retry=1),self.token),result)

    def test_fault_on_later_layer_rolls_back_entire_chain_and_orders(self):
        self.order();before=self.state();save=self.api.store.save
        def fault(s):save(s);raise RuntimeError('layer fault')
        with patch.object(self.api.store,'save',side_effect=fault),self.assertRaises(RuntimeError):self.order(20100,1)
        self.assertEqual(self.state(),before)
        self.order(20100,1);before=self.state()
        with patch.object(self.api.store,'save',side_effect=fault),self.assertRaises(RuntimeError):
            self.api.call('clear_quest2',self.clear_req(),self.token)
        self.assertEqual(self.state(),before)
        self.assertIsNotNone(self.api.store.active_run(before['player']['user_id']))


if __name__=='__main__':unittest.main()
