import copy,unittest,uuid
from rtd.masters.catalog import load_catalog
from rtd.operations.configuration import ConfigurationError
import test_battle_layers as layer_tests
from rtd.common import ProtocolError
from rtd.services.api import API

class LayerOperationsTest(unittest.TestCase):
    setUp=layer_tests.BattleLayersTest.setUp
    state=layer_tests.BattleLayersTest.state
    order=layer_tests.BattleLayersTest.order
    entry=layer_tests.BattleLayersTest.entry
    clear_req=layer_tests.BattleLayersTest.clear_req
    def event(self):
        original,_=load_catalog()
        self.api.masters[22]=copy.deepcopy(original[22])
        root=next(q for q in self.api.masters[30]['data_list'] if q['id']==20000)
        root.update(next(q for q in original[30]['data_list'] if q['id']==20000))
        enemy={e['id']:e for e in self.api.masters[20]['data_list']}
        tables={t['id']:t for t in self.api.masters[21]['data_list']}
        table=tables[root['enemy_table_id']]
        children={table[k.replace('_set_id','_drop_id')] for k,id in table.items()
                  if k.endswith('_set_id') and enemy.get(id,{}).get('type')==20}
        known={d['id'] for d in original[22]['data_list']};rows=[]
        for id in sorted({20000}|children):
            q=next(q for q in self.api.masters[30]['data_list'] if q['id']==id)
            t=tables[q['enemy_table_id']]
            missing={v for k,v in t.items() if k.endswith('_drop_id') and v not in known
                and enemy.get(t[k.replace('_drop_id','_set_id')],{}).get('type') not in (20,21)}
            rows.append(dict(quest_id=id,drops=[dict(drop_data_id=d,no_drop_weight=1,entries=[]) for d in sorted(missing)]))
        return dict(name='Explicit local layer loot',enabled=True,starts_at=None,ends_at=None,quests=rows)

    def req(self,id,floor=0,**kw):
        request=layer_tests.BattleLayersTest.req(self,id,floor,**kw)
        request['hashes']['30']=str(self.api.master_table(30)['hash'])
        return request

    def test_local_schedule_requires_complete_missing_loot_and_reachable_children(self):
        event=self.event();before=self.api.operations.read()
        bad=copy.deepcopy(event);bad['quests']=bad['quests'][:1]
        with self.assertRaises(ConfigurationError):self.api.operations.update('events','layers',bad)
        bad=copy.deepcopy(event);bad['quests'][0]['drops']=[]
        with self.assertRaises(ConfigurationError):self.api.operations.update('events','layers',bad)
        self.assertEqual(self.api.operations.read(),before)
        self.api.operations.update('events','layers',event)
        table=self.api.master_table(30)
        self.assertNotEqual(table['hash'],self.api.masters[30]['hash'])
        original=next(q for q in self.api.masters[30]['data_list'] if q['id']==20000)
        self.assertEqual(original['open_type_3'],5)
        root,result=self.order();self.assertEqual(self.state()['battle']['quest_id'],20000)

    def test_closing_local_event_keeps_prepaid_chain_rules_and_old_master_hash(self):
        event=self.event();self.api.operations.update('events','layers',event)
        root,_=self.order();next_req=self.req(20100,1)
        self.api.operations.update('events','layers',dict(enabled=False),method='PATCH')
        closed=self.api.master_table(30);self.assertNotEqual(root['hashes']['30'],closed['hash'])
        # An existing root keeps its original complete event/drop configuration.
        self.api.call('order_quest',next_req,self.token)
        self.assertEqual(len(self.state()['battle_history']),1)
        result=self.api.call('clear_quest2',self.clear_req(),self.token)
        self.assertEqual(len(result['result']),2)
        before=self.state()
        with self.assertRaises(ProtocolError):self.order()
        self.assertEqual(self.state(),before)

    def test_ordinary_retry_keeps_prepaid_snapshot_after_layer_event_change_and_restart(self):
        self.api.operations.update('events','layers',self.event())
        request,result=self.order(11000)
        saved=self.state();run=self.api.store.active_run(saved['player']['user_id'])
        self.api.operations.update('events','layers',dict(enabled=False),method='PATCH')
        self.assertNotEqual(request['hashes']['30'],str(self.api.master_table(30)['hash']))
        self.api=API(self.path)
        self.assertEqual(self.api.call('order_quest',dict(request,retry=1),self.token),result)
        self.assertEqual(self.state(),saved)
        self.assertEqual(self.api.store.active_run(saved['player']['user_id']),run)
        self.assertEqual(self.state()['battle']['enemy_info_list'],result['result']['enemy_info_list'])
        # A refreshed client may also use current masters for the same order.
        refreshed=copy.deepcopy(request)
        refreshed['hashes']['30']=str(self.api.master_table(30)['hash'])
        self.assertEqual(self.api.call('order_quest',dict(refreshed,retry=1),self.token),result)
        self.assertEqual(self.state(),saved)

    def test_frozen_ordinary_hash_cannot_authorize_new_or_conflicting_orders(self):
        self.api.operations.update('events','layers',self.event())
        request,_=self.order(11000)
        self.api.operations.update('events','layers',dict(enabled=False),method='PATCH')
        self.api=API(self.path);before=self.state()
        wrong_master=copy.deepcopy(request);wrong_master['hashes']['20']='wrong'
        for bad in (dict(request,token=str(uuid.uuid4()),retry=0),
                    dict(request,helper_user_id=999,retry=1),
                    dict(request,quest_id=10001,retry=1),
                    dict(request,level_data_hash='wrong',retry=1),wrong_master):
            with self.subTest(request=bad),self.assertRaises(ProtocolError):
                self.api.call('order_quest',bad,self.token)
            self.assertEqual(self.state(),before)

if __name__=='__main__':unittest.main()
