"""Disposable SQLite/original-master protocol fixtures, never live game progress."""
import copy
import os
import pathlib
import tempfile
import unittest
import uuid
from unittest.mock import patch
from rtd.common import ProtocolError
from rtd.operations.configuration import ConfigurationError
from rtd.services.api import API
from rtd.services.battle_entry import HASH_TYPES
from rtd.services.battle_generation import generate_enemies
import test_battle_layers as layers


class EventIntegrationTests(unittest.TestCase):
    def setUp(self):
        env=patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'1'});env.start();self.addCleanup(env.stop)
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.path=pathlib.Path(folder.name)/'events.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4());self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Event fixture'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        s=self.state();s['player'].update(action_point=100,max_action_point=100)
        for qid in (10000,13207):
            flag=self.quest(qid)['flag_no'];s['player']['quest_clear_flags'][flag//8]|=1<<(flag%8)
        self.api.store.save(s)

    def state(self):return self.api.store.session(self.token)
    def quest(self,id=13208):return next(q for q in self.api.masters[30]['data_list'] if q['id']==id)
    def config(self,amount=3,qid=13208):
        return dict(id='point-event',name='Explicit local quantity',enabled=True,starts_at=None,ends_at=None,
            quests=[dict(quest_id=qid,drops=[dict(drop_data_id=id,no_drop_weight=1,entries=[],sp_event_point=amount)
                for id in sorted(self.api.operations.drop_ids(qid))])])
    def request(self,qid=13208):
        return dict(ver='2.4.0',retry=0,quest_id=qid,floor=0,resume_id=0,bonus_stamina=0,helper_user_id=0,
            token=str(uuid.uuid4()),level_data_hash=self.api.levels[qid]['hash'],
            hashes={str(t):str(self.api.master_table(t)['hash']) for t in HASH_TYPES})
    def clear(self,amount,qid=13208):
        q=self.quest(qid)
        return dict(ver='2.4.0',retry=0,party_instance_id=self.state()['battle_party_instance_ids'],
            list=[dict(quest_id=q['id'],exp=q['reward_exp'],game_money=q['reward_money'],yorisiro_exp=0,
                units=[],challenge_id_list=[],sp_event_point=amount)])
    def durable(self):
        with self.api.store.connect() as db:
            return {name:db.execute('SELECT * FROM '+name+' ORDER BY rowid').fetchall()
                for name in ('players','quest_runs','operation_receipts','runtime_config')}

    def test_unknown_stored_event_is_rejected_at_login_and_entry_without_durable_changes(self):
        self.api.call('create_user',dict(ver='2.4.0',uuid=str(uuid.uuid4()),unit_no=0,user_name='Peer fixture'))
        self.api.operations.update('events','point-event',self.config())
        state=self.state();state['sp_event_points']={'1':7};self.api.store.save(state)
        self.api=API(self.path)
        self.assertNotIn(1,{e['sp_event_id'] for e in self.api.masters[34]['data_list']})
        for operation,request in (('login',dict(ver='2.4.0')),('order_quest',self.request())):
            before=self.durable()
            with self.subTest(operation=operation),self.assertRaises(ProtocolError):
                self.api.call(operation,request,self.token)
            self.assertEqual(self.durable(),before)

    def test_unknown_frozen_event_after_restart_cannot_settle_or_create_receipt(self):
        self.api.call('create_user',dict(ver='2.4.0',uuid=str(uuid.uuid4()),unit_no=0,user_name='Peer fixture'))
        self.api.operations.update('events','point-event',self.config())
        self.api.call('order_quest',self.request(),self.token)
        state=self.state();state['battle_event_points']['event_id']=1;self.api.store.save(state)
        self.api=API(self.path);before=self.durable()
        for amount in (0,1):
            with self.subTest(amount=amount),self.assertRaises(ProtocolError):
                self.api.call('clear_quest2',self.clear(amount),self.token)
            self.assertEqual(self.durable(),before)

    def test_original_wanted_challenge_bounds_target_count_grade_and_present_nontreasure(self):
        # Explicit disposable battle fixtures; never alter the running QA battle.
        self.api.operations.update('events','point-event',self.config(0,13206))
        self.api.call('order_quest',self.request(13206),self.token)
        original=self.state();condition=next(c for c in self.api.masters[32]['data_list'] if c['id']==11764)
        for kind in ('absent','wrong-target','treasure','wrong-grade','too-many','valid'):
            s=copy.deepcopy(original)
            for enemy in s['battle']['enemy_info_list']:enemy['flag']=False
            enemy=s['battle']['enemy_info_list'][0];enemy.update(flag=True,enemy_id=1,enemy_set_id=10402)
            test_condition=copy.deepcopy(condition)
            if kind=='absent':enemy['flag']=False
            elif kind=='wrong-target':enemy['enemy_set_id']=11000
            elif kind=='treasure':
                enemy['enemy_set_id']=next(e['id'] for e in self.api.masters[20]['data_list'] if e['type']==16)
                test_condition['param_0']=enemy['enemy_set_id']
            elif kind=='wrong-grade':test_condition['grade']=1
            elif kind=='too-many':test_condition['param_1']=2
            self.api.store.save(s);before=self.durable();req=self.clear(0,13206)
            req['list'][0]['challenge_id_list']=[11764]
            with patch.dict(condition,test_condition,clear=True):
                if kind=='valid':self.api.call('clear_quest2',req,self.token)
                else:
                    with self.subTest(kind=kind),self.assertRaises(ProtocolError):
                        self.api.call('clear_quest2',req,self.token)
                    self.assertEqual(self.durable(),before)

    def test_original_required_unit_ids_use_frozen_party_and_helper_and_all_nonzero_params(self):
        self.api.operations.update('events','point-event',self.config(0))
        self.api.call('order_quest',self.request(),self.token)
        original=self.state();condition=next(c for c in self.api.masters[32]['data_list'] if c['id']==11770)
        for kind in ('missing','missing-second','helper-only','party'):
            if self.state().get('battle') is None:
                self.api.call('order_quest',self.request(),self.token)
                original=self.state()
            s=copy.deepcopy(original);s['battle_party_unit_ids']=[20000,11112,10033]
            s['battle_helper']['unit_id']=20000
            test_condition=dict(condition,param_1=0,param_2=0,param_3=0)
            if kind=='missing-second':
                s['battle_party_unit_ids'][0]=12012;test_condition['param_1']=12022
            elif kind=='helper-only':s['battle_helper']['unit_id']=12012
            elif kind=='party':s['battle_party_unit_ids'][0]=12012
            self.api.store.save(s);before=self.durable();req=self.clear(0)
            req['list'][0]['challenge_id_list']=[11770]
            with patch.dict(condition,test_condition,clear=True):
                if kind in ('party','helper-only'):
                    self.api.call('clear_quest2',req,self.token)
                else:
                    with self.subTest(kind=kind),self.assertRaises(ProtocolError):
                        self.api.call('clear_quest2',req,self.token)
                    self.assertEqual(self.durable(),before)

    def test_config_validation_wrong_original_event_and_explicit_block(self):
        for amount in (True,-1,1000,'3',1.5):
            before=self.api.operations.read()
            with self.assertRaises(ConfigurationError):self.api.operations.update('events','point-event',self.config(amount))
            self.assertEqual(self.api.operations.read(),before)
        for qid in (11000,13206,13207):
            with self.assertRaises(ConfigurationError):self.api.operations.update('events','point-event',self.config(1,qid))
        self.api.operations.update('events','point-event',self.config(999))
        with patch.dict(os.environ,{'RTD_CONTENT_EXPERIMENTAL':'0'}):formal=API(self.path)
        # Experimental mode no longer controls availability; explicit server
        # blocks still reject orders without consuming AP or creating a run.
        formal.blocked_quests.add(13208)
        before=self.durable()
        with self.assertRaises(ProtocolError):formal.call('order_quest',self.request(),self.token)
        self.assertEqual(self.durable(),before)
        formal.blocked_quests.remove(13208)
        self.assertEqual(formal.call('order_quest',self.request(),self.token)['code'],4096)

    def test_config_open_schedule_preserves_original_prerequisites_and_freezes_after_delete(self):
        before=self.durable()
        with self.assertRaises(ProtocolError):self.api.call('order_quest',self.request(),self.token)
        self.assertEqual(self.durable(),before)
        self.api.operations.update('events','point-event',self.config())
        master=next(q for q in self.api.master_table(30)['data_list'] if q['id']==13208)
        self.assertFalse(any(master['open_type_'+str(i)] in (4,5) for i in range(1,7)))
        self.assertIn(13207,[master['open_param_'+str(i)] for i in range(1,7) if master['open_type_'+str(i)]==2])
        order=self.request();self.api.call('order_quest',order,self.token)
        snapshot=copy.deepcopy(self.state()['battle_event_points']);self.assertGreater(snapshot['maximum'],0)
        self.assertEqual(snapshot['event_id'],100002)
        self.api.operations.update('events','point-event',None,method='DELETE')
        before=self.state();self.api.call('order_quest',dict(order,retry=1),self.token)
        self.assertEqual(self.state(),before)
        request=self.clear(snapshot['maximum']);result=self.api.call('clear_quest2',request,self.token)
        after=self.state();self.assertEqual(after['sp_event_points'],{'100002':snapshot['maximum']})
        self.api=API(self.path);self.assertEqual(self.state(),after)
        self.assertEqual(self.api.call('clear_quest2',dict(request,retry=1),self.token),result)
        self.assertEqual(self.state(),after)
        expected=[dict(sp_event_id=100002,point=snapshot['maximum'])]
        self.assertEqual(self.api.call('login',dict(ver='2.4.0'),self.token)['result']['sp_event_point_list'],expected)
        self.assertEqual(self.api.call('login',dict(ver='2.4.0'),self.token)['result']['sp_event_point_list'],expected)

    def test_legacy_snapshot_zero_and_invalid_report_rollback_all_durable_state(self):
        cfg=self.config(0);self.api.operations.update('events','point-event',cfg)
        self.api.call('order_quest',self.request(),self.token)
        state=self.state();state.pop('battle_event_points',None);self.api.store.save(state)
        before=self.durable()
        for amount in (1,True,-1):
            with self.assertRaises(ProtocolError):self.api.call('clear_quest2',self.clear(amount),self.token)
            self.assertEqual(self.durable(),before)
        self.api.call('clear_quest2',self.clear(0),self.token)
        self.assertNotIn('sp_event_points',self.state())

    def test_closed_event_rejects_new_order_but_admitted_snapshot_still_settles_at_cap(self):
        self.api.operations.update('events','point-event',self.config(999));request=self.request()
        self.api.call('order_quest',request,self.token)
        s=self.state();self.assertEqual(s['battle_event_points']['maximum'],999)
        s['sp_event_points']={'100002':99990};self.api.store.save(s)
        self.api.operations.update('events','point-event',dict(enabled=False),method='PATCH')
        before=self.durable()
        with self.assertRaises(ProtocolError):self.api.call('order_quest',self.request(),self.token)
        self.assertEqual(self.durable(),before)
        self.api.call('clear_quest2',self.clear(999),self.token)
        self.assertEqual(self.state()['sp_event_points'],{'100002':99999})

    def test_point_threshold_rejects_new_order_before_ap_or_run_changes(self):
        self.api.operations.update('events','point-event',self.config())
        self.quest().update(open_sp_event_id=100002,open_sp_event_point=5)  # Explicit master boundary fixture.
        before=self.durable()
        with self.assertRaises(ProtocolError):self.api.call('order_quest',self.request(),self.token)
        self.assertEqual(self.durable(),before)
        s=self.state();s['sp_event_points']={'100002':5};self.api.store.save(s)
        self.api.call('order_quest',self.request(),self.token)
        self.assertEqual(self.state()['sp_event_points'],{'100002':5})

    def test_same_result_concurrently_retried_by_two_instances_grants_once_and_preserves_peer(self):
        from concurrent.futures import ThreadPoolExecutor
        key=str(uuid.uuid4());peer=self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=1,user_name='Other fixture'))['result']['user_id']
        original_peer=self.api.store.by_id(peer)
        self.api.operations.update('events','point-event',self.config())
        self.api.call('order_quest',self.request(),self.token)
        amount=self.state()['battle_event_points']['maximum'];request=self.clear(amount)
        first,second=API(self.path),API(self.path)
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(api.call,'clear_quest2',dict(request,retry=1),self.token) for api in (first,second)]
            results=[future.result(timeout=15) for future in futures]
        self.assertEqual(results[0],results[1]);self.assertEqual(self.state()['sp_event_points'],{'100002':amount})
        self.assertEqual(self.api.store.by_id(peer),original_peer)
        with self.api.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM operation_receipts').fetchone()[0],1)

    def test_omitted_local_point_quantity_defaults_zero_without_config_rewrite(self):
        config=self.config()
        for row in config['quests'][0]['drops']:row.pop('sp_event_point')
        self.api.operations.update('events','point-event',config);before=self.api.operations.read()
        result=self.api.call('order_quest',self.request(),self.token)
        self.assertTrue(all(row['sp_event_point']==0 for row in result['result']['enemy_info_list']))
        self.assertEqual(self.state()['battle_event_points'],dict(event_id=100002,maximum=0))
        self.assertEqual(self.api.operations.read(),before)

    def test_generation_zeroes_absent_and_field_objects_with_or_without_override(self):
        table=copy.deepcopy(next(t for t in self.api.masters[21]['data_list'] if t['id']==10000))
        table['enemy1_rate']=100;drops={d['id']:d for d in self.api.masters[22]['data_list']}
        overrides={table['enemy1_drop_id']:dict(entries=[],no_drop_weight=1,sp_event_point=7)}
        class Roll:
            def randint(self,lo,hi):return hi
        def generate():return generate_enemies(table,dict(map_data='01',width=1),drops,Roll(),
            drop_overrides=overrides,enemy_masters={99901:dict(type=20)})[0]['sp_event_point']
        self.assertEqual(generate(),7);table['enemy1_rate']=0;self.assertEqual(generate(),0)
        original_id=table['enemy1_set_id']
        table.update(enemy1_rate=100,enemy1_set_id=99901);self.assertEqual(generate(),0)
        overrides.clear();drops[table['enemy1_drop_id']]['sp_event_point']=9
        self.assertEqual(generate(),0);table['enemy1_set_id']=original_id;self.assertEqual(generate(),9)


class EventLayerIntegrationTests(unittest.TestCase):
    setUp=layers.BattleLayersTest.setUp
    state=layers.BattleLayersTest.state
    req=layers.BattleLayersTest.req
    order=layers.BattleLayersTest.order
    entry=layers.BattleLayersTest.entry
    clear_req=layers.BattleLayersTest.clear_req

    def test_two_floor_original_event_snapshots_survive_restart_and_bad_tail_rolls_back(self):
        for qid,event in ((20000,100001),(20100,100002)):
            next(q for q in self.api.masters[30]['data_list'] if q['id']==qid)['sp_event_id']=event
        import test_attribute_exp as attributes
        root=attributes.fixed_enemies(self.api,stairs=True);child=attributes.fixed_enemies(self.api)
        for rows in (root,child):
            for row in rows:row['add_attribute_exp']=0
        root[0]['sp_event_point']=4;child[0]['sp_event_point']=7
        with patch('rtd.services.battle_layers.generate_enemies',return_value=root):self.order()
        with patch('rtd.services.battle_layers.generate_enemies',return_value=child):self.order(20100,1)
        self.assertEqual(self.state()['battle_history'][0]['event_points'],dict(event_id=100001,maximum=4))
        request=self.clear_req();request['list'][0]['sp_event_point']=4;request['list'][1]['sp_event_point']=7
        bad=copy.deepcopy(request);bad['list'][1]['sp_event_point']=8;before=self.state()
        with self.assertRaises(ProtocolError):self.api.call('clear_quest2',bad,self.token)
        self.assertEqual(self.state(),before)
        self.api=API(self.path);result=self.api.call('clear_quest2',request,self.token);after=self.state()
        self.assertEqual(after['sp_event_points'],{'100001':4,'100002':7})
        self.api=API(self.path);self.assertEqual(self.api.call('clear_quest2',dict(request,retry=1),self.token),result)
        self.assertEqual(self.state(),after)
