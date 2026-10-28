import copy
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
from test_live_configuration import event
import test_battle_layers as layer_tests

FIELDS=('attribute_exp_none','attribute_exp_fire','attribute_exp_water','attribute_exp_shine','attribute_exp_dark')


def fixed_enemies(api,stairs=False):
    # A deterministic generator boundary: real original species/attributes,
    # explicit local reward quantities, no books or invented master rows.
    result=[]
    for attribute,amount in enumerate((2,3,5,7,11),1):
        enemy=next(e for e in api.masters[20]['data_list'] if e['attribute']==attribute and e['type'] not in (20,21))
        result.append(dict(enemy_id=attribute,enemy_set_id=enemy['id'],x=attribute,y=0,flag=True,
            drop_data_id=0,drop_unit_id=0,drop_unit_level=0,sp_event_point=0,add_attribute_exp=amount))
    if stairs:
        enemy=next(e for e in api.masters[20]['data_list'] if e['type']==20)
        result.append(dict(enemy_id=90,enemy_set_id=enemy['id'],x=1,y=1,flag=True,
            drop_data_id=20100,drop_unit_id=0,drop_unit_level=0,sp_event_point=0,add_attribute_exp=0))
    return result


class AttributeExpTest(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.path=pathlib.Path(folder.name)/'attribute.sqlite3';self.api=API(self.path)
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Attribute'))
        self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        s=self.state();s['player']['quest_clear_flags'][0]|=4
        for u,uid in zip(s['units'][:3],(16500,11061,13200)):u.update(unit_id=uid,level=1,exp=0)
        self.api.store.save(s)

    def state(self):return self.api.store.session(self.token)

    def config(self,amount=None):
        cfg=event()
        cfg['quests'][0]['drops']=[dict(drop_data_id=id,no_drop_weight=1,entries=[])
            for id in self.api.operations.drop_ids(11000)]
        if amount is not None:
            for rule in cfg['quests'][0]['drops']:rule['attribute_exp']=amount
        return cfg

    def order(self):
        return dict(ver='2.4.0',retry=0,quest_id=11000,floor=0,resume_id=0,bonus_stamina=0,
            helper_user_id=0,token=str(uuid.uuid4()),level_data_hash=self.api.levels[11000]['hash'],
            hashes={str(t):str(self.api.master_table(t)['hash']) for t in HASH_TYPES})

    def rewarded_order(self,helper_id=0):
        s=self.state()
        for u,uid in zip(s['units'][:3],(16500,14050,11061)):u.update(unit_id=uid,attribute_exp=0)
        s['units'][1]['attribute_exp']=13
        self.api.store.save(s)
        with patch('rtd.services.battle_entry.generate_enemies',return_value=fixed_enemies(self.api)):
            self.api.call('order_quest',dict(self.order(),helper_user_id=helper_id),self.token)
        return self.clear_request()

    def clear_request(self):
        q=next(q for q in self.api.masters[30]['data_list'] if q['id']==11000)
        return dict(ver='2.4.0',retry=0,party_instance_id=self.state()['battle_party_instance_ids'],
            list=[dict(quest_id=11000,exp=q['reward_exp'],game_money=q['reward_money'],yorisiro_exp=0,
                units=[],challenge_id_list=[],**dict(zip(FIELDS,(2,3,5,7,11))))])

    def test_settlement_mixed_original_attributes_caps_restart_and_exact_retry(self):
        req=self.rewarded_order();before=self.state();ids=req['party_instance_id'][:3]
        self.api=API(self.path)
        result=self.api.call('clear_quest2',req,self.token);after=self.state()
        self.assertEqual([next(u for u in after['units'] if u['instance_id']==i)['attribute_exp'] for i in ids],[35,44,0])
        self.assertNotIn('battle_attribute_rewards',after)
        # Original DTO contains only newly obtained cards, not duplicate party cards.
        self.assertFalse(set(ids)&{u['instance_id'] for u in result['result'][0]['get_units']})
        self.api=API(self.path)
        self.assertEqual(self.api.call('clear_quest2',dict(req,retry=1),self.token),result)
        self.assertEqual(self.state(),after)
        self.assertEqual(len(after['units']),len(before['units'])+1)
        different=copy.deepcopy(req);different['retry']=1;different['list'][0][FIELDS[0]]=1
        with self.assertRaises(ProtocolError):self.api.call('clear_quest2',different,self.token)
        self.assertEqual(self.state(),after)

    def test_real_friend_helper_unit_is_not_awarded_and_late_save_failure_is_atomic(self):
        key=str(uuid.uuid4())
        self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Helper'))
        token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
        helper=self.api.store.by_id(2);helper['units'][0].update(unit_id=16500,attribute_exp=77)
        self.api.store.save(helper)
        self.api.call('send_friend_request',dict(ver='2.4.0',friend_user_id=2),self.token)
        self.api.call('accept_friend_request',dict(ver='2.4.0',friend_user_id=[1]),token)
        req=self.rewarded_order(helper_id=2);before=self.state();helper=self.api.store.by_id(2)
        save=self.api.store.save
        def broken(state):save(state);raise RuntimeError('attribute save failure')
        with patch.object(self.api.store,'save',side_effect=broken),self.assertRaisesRegex(RuntimeError,'attribute save'):
            self.api.call('clear_quest2',req,self.token)
        self.assertEqual(self.state(),before)
        self.assertEqual(self.api.store.by_id(2),helper)
        with self.api.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM operation_receipts').fetchone()[0],0)
        self.api.call('clear_quest2',req,self.token)
        # Only the separate friendship-point policy changes the provider state;
        # the provider's actual unit receives no borrowed attribute experience.
        helper['helper_reward_pending']=dict(count=1,points=10)
        self.assertEqual(self.api.store.by_id(2),helper)

    def test_positive_award_caps_and_uses_entry_party_after_current_party_changes(self):
        req=self.rewarded_order();s=self.state();ids=req['party_instance_id'][:3]
        s['units'][0]['attribute_exp']=4990
        other=copy.deepcopy(s['units'][0]);other.update(instance_id=900000,attribute_exp=123)
        s['units'].append(other);s['party']['party'][0]['instanceIds'][0]=900000
        self.api.store.save(s)
        # Later table changes cannot reclassify entry-time reward attributes/caps.
        next(u for u in self.api.masters[10]['data_list'] if u['id']==16500).update(attribute=2,max_attribute_exp=1)
        self.api.call('clear_quest2',req,self.token);after=self.state()
        self.assertEqual(next(u for u in after['units'] if u['instance_id']==ids[0])['attribute_exp'],5000)
        self.assertEqual(next(u for u in after['units'] if u['instance_id']==900000)['attribute_exp'],123)

    def test_invalid_reports_or_changed_recipient_roll_back_complete_settlement(self):
        req=self.rewarded_order()
        for field,value in ((FIELDS[0],True),(FIELDS[1],4),(FIELDS[2],-1),(FIELDS[3],1.5),
                            (FIELDS[4],1000000),('sp_event_point',1)):
            bad=copy.deepcopy(req);bad['list'][0][field]=value;before=self.state()
            with self.subTest(field=field,value=value),self.assertRaises(ProtocolError):
                self.api.call('clear_quest2',bad,self.token)
            self.assertEqual(self.state(),before)
        s=self.state();s['units'][0]['unit_id']=16501;self.api.store.save(s);before=self.state()
        with self.assertRaises(ProtocolError):self.api.call('clear_quest2',req,self.token)
        self.assertEqual(self.state(),before)
        s=self.state();s['units'].pop(0);self.api.store.save(s);before=self.state()
        with self.assertRaises(ProtocolError):self.api.call('clear_quest2',req,self.token)
        self.assertEqual(self.state(),before)

    def test_legacy_context_missing_only_accepts_zero_and_positive_requires_valid_context(self):
        req=self.rewarded_order();s=self.state();s.pop('battle_attribute_rewards');self.api.store.save(s)
        before=self.state()
        with self.assertRaises(ProtocolError):self.api.call('clear_quest2',req,self.token)
        self.assertEqual(self.state(),before)
        for field in FIELDS:req['list'][0][field]=0
        self.api.call('clear_quest2',req,self.token)
        self.assertEqual([u['attribute_exp'] for u in self.state()['units'][:3]],[0,13,0])

    def test_optional_config_freezes_rewards_original_party_and_survives_close_restart(self):
        self.api.operations.update('events','local-11000',self.config(17))
        req=self.order();result=self.api.call('order_quest',req,self.token)
        enemies=result['result']['enemy_info_list']
        self.assertTrue(any(e['flag'] for e in enemies))
        self.assertTrue(all(e['add_attribute_exp']==(17 if e['flag'] else 0) for e in enemies))
        self.assertTrue(all(e['drop_unit_id']==0 for e in enemies))
        snapshot=self.state()['battle_attribute_rewards']
        self.assertEqual([(u['unit_id'],u['attribute'],u['max_attribute_exp']) for u in snapshot['party']],
                         [(16500,4,5000),(11061,3,0),(13200,2,0)])
        self.assertEqual(sum(snapshot['limits'].values()),17*sum(e['flag'] for e in enemies))
        before=self.state()
        self.api.operations.update('events','local-11000',self.config(29))
        self.api.operations.update('events','local-11000',dict(enabled=False),'PATCH')
        self.api=API(self.path)
        self.assertEqual(self.api.call('order_quest',req,self.token),result)
        self.assertEqual(self.state(),before)

    def test_invalid_attribute_config_rolls_back_revision_and_document(self):
        self.api.operations.update('events','local-11000',self.config())
        for amount in (True,-1,1000000,1.5,'3'):
            before=self.api.operations.read()
            with self.subTest(amount=amount),self.assertRaises(ConfigurationError):
                self.api.operations.update('events','local-11000',self.config(amount))
            self.assertEqual(self.api.operations.read(),before)
        cfg=self.config();cfg['quests'][0]['drops'][0]['attribute_exp_typo']=3
        with self.assertRaises(ConfigurationError):self.api.operations.update('events','local-11000',cfg)

    def test_maximum_configuration_and_same_attribute_encounter_saturation(self):
        self.api.operations.update('events','local-11000',self.config(999999))
        rows=fixed_enemies(self.api)
        for row in rows:row['add_attribute_exp']=0
        rows[1]['add_attribute_exp']=999999
        extra=copy.deepcopy(rows[1]);extra.update(enemy_id=91,x=6)
        rows.append(extra)
        with patch('rtd.services.battle_entry.generate_enemies',return_value=rows):
            self.api.call('order_quest',self.order(),self.token)
        self.assertEqual(self.state()['battle_attribute_rewards']['limits'],
                         {'1':0,'2':999999,'3':0,'4':0,'5':0})
        req=self.clear_request()
        req['list'][0].update(dict.fromkeys(FIELDS,0))
        req['list'][0]['attribute_exp_fire']=999999
        self.assertEqual(self.api.call('clear_quest2',req,self.token)['code'],4096)

    def test_generation_no_drop_presence_and_stairs_do_not_share_reward_semantics(self):
        table=copy.deepcopy(next(t for t in self.api.masters[21]['data_list'] if t['id']==10000))
        table['enemy1_rate']=100
        drops={d['id']:d for d in self.api.masters[22]['data_list']}
        rule=dict(entries=[],no_drop_weight=1,attribute_exp=23)
        overrides={table['enemy1_drop_id']:rule}
        class Roll:
            def randint(self,lo,hi):return hi
        def generate():return generate_enemies(table,dict(map_data='01',width=1),drops,Roll(),
            drop_overrides=overrides,enemy_masters={99901:dict(type=20)})[0]
        self.assertEqual((generate()['drop_unit_id'],generate()['add_attribute_exp']),(0,23))
        table['enemy1_rate']=0
        self.assertEqual(generate()['add_attribute_exp'],0)
        table.update(enemy1_rate=100,enemy1_set_id=99901)
        self.assertEqual(generate()['add_attribute_exp'],0)

    def test_legacy_rule_defaults_to_zero_without_document_rewrite(self):
        cfg=self.config();self.api.operations.update('events','local-11000',cfg)
        before=self.api.operations.read()
        result=self.api.call('order_quest',self.order(),self.token)
        self.assertTrue(all(e['add_attribute_exp']==0 for e in result['result']['enemy_info_list']))
        self.assertEqual(self.api.operations.read(),before)


class AttributeLayersTest(unittest.TestCase):
    setUp=layer_tests.BattleLayersTest.setUp
    state=layer_tests.BattleLayersTest.state
    req=layer_tests.BattleLayersTest.req
    order=layer_tests.BattleLayersTest.order
    entry=layer_tests.BattleLayersTest.entry
    clear_req=layer_tests.BattleLayersTest.clear_req

    def test_per_floor_maximum_saturation_accumulates_beyond_maximum_and_rolls_back(self):
        s=self.state()
        for unit,uid in zip(s['units'][:3],(16500,14050,11061)):
            unit.update(unit_id=uid,attribute_exp=0)
            # Explicit test-only cap permits observing chain totals above999999.
            next(m for m in self.api.masters[10]['data_list'] if m['id']==uid)['max_attribute_exp']=5000000
        self.api.store.save(s)
        def enemies(amount,stairs=False):
            rows=fixed_enemies(self.api,stairs)
            for row in rows:row['add_attribute_exp']=0
            rows[1]['add_attribute_exp']=amount
            extra=copy.deepcopy(rows[1]);extra.update(enemy_id=91,x=6)
            return rows+[extra]
        with patch('rtd.services.battle_layers.generate_enemies',return_value=enemies(600000,True)):
            self.order()
        self.assertEqual(self.state()['battle_attribute_rewards']['limits']['2'],999999)
        with patch('rtd.services.battle_layers.generate_enemies',return_value=enemies(300000)):
            self.order(20100,1)
        self.assertEqual(self.state()['battle_attribute_rewards']['limits']['2'],600000)
        req=self.clear_req()
        for row,amount in zip(req['list'],(999999,600000)):
            row.update(dict.fromkeys(FIELDS,0));row['attribute_exp_fire']=amount
        bad=copy.deepcopy(req);bad['list'][1]['attribute_exp_fire']=600001
        def durable():
            with self.api.store.connect() as db:
                return {table:db.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall()
                        for table in ('players','quest_runs','operation_receipts')}
        before=durable()
        with self.assertRaises(ProtocolError):self.api.call('clear_quest2',bad,self.token)
        self.assertEqual(durable(),before)
        self.api=API(self.path)
        result=self.api.call('clear_quest2',req,self.token);after=self.state()
        self.assertEqual([u['attribute_exp'] for u in after['units'][:3]],
                         [1599999,3199998,1599999])
        saved=durable();self.api=API(self.path)
        self.assertEqual(self.api.call('clear_quest2',dict(req,retry=1),self.token),result)
        self.assertEqual(durable(),saved)

    def test_two_floors_add_once_and_later_invalid_reward_rolls_back_first_floor(self):
        s=self.state()
        for u,uid in zip(s['units'][:3],(16500,14050,11061)):u.update(unit_id=uid,attribute_exp=0)
        self.api.store.save(s)
        with patch('rtd.services.battle_layers.generate_enemies',return_value=fixed_enemies(self.api,stairs=True)):self.order()
        with patch('rtd.services.battle_layers.generate_enemies',return_value=fixed_enemies(self.api)):self.order(20100,1)
        req=self.clear_req()
        for row in req['list']:row.update(dict(zip(FIELDS,(2,3,5,7,11))))
        bad=copy.deepcopy(req);bad['list'][1][FIELDS[1]]=4;before=self.state()
        with self.assertRaises(ProtocolError):self.api.call('clear_quest2',bad,self.token)
        self.assertEqual(self.state(),before)
        self.api=API(self.path)
        result=self.api.call('clear_quest2',req,self.token);after=self.state()
        self.assertEqual(len(result['result']),2)
        self.assertEqual([u['attribute_exp'] for u in after['units'][:3]],[70,62,0])
        self.api=API(self.path)
        self.assertEqual(self.api.call('clear_quest2',dict(req,retry=1),self.token),result)
        self.assertEqual(self.state(),after)

    def test_each_floor_freezes_limits_and_keeps_original_root_party_across_restart(self):
        # Explicit master fixture only; no production original rates invented.
        for row in self.api.masters[22]['data_list']:row['add_attribute_exp']=17
        self.order();root=self.state();context=root['battle_attribute_rewards']
        self.assertGreater(sum(context['limits'].values()),0)
        req,result=self.order(20100,1);child=self.state()
        self.assertEqual(child['battle_history'][0]['attribute_rewards'],context)
        self.assertEqual(child['battle_attribute_rewards']['party'],context['party'])
        self.assertGreater(sum(child['battle_attribute_rewards']['limits'].values()),0)
        self.assertEqual(child['player']['action_point'],root['player']['action_point'])
        self.api=API(self.path)
        self.assertEqual(self.api.call('order_quest',req,self.token),result)
        self.assertEqual(self.state(),child)


if __name__=='__main__':unittest.main()
