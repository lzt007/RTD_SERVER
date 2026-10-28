"""Protocol integration tests against a real loopback HTTP server and SQLite."""
import gzip
import http.server
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.parse
import urllib.request
import uuid
from rtd_server import API, handler_for


class AccountsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.database = self.root/'account.sqlite3'
        self.start_server()

    def start_server(self):
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
            handler_for(API(self.database), self.root/'requests.jsonl'))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def tearDown(self):
        self.stop_server()
        self.temp.cleanup()

    def call(self, operation, req=None, token='', uid=None):
        payload = dict(ver='2.4.0', retry=0)
        payload.update(req or {})
        address = f'http://127.0.0.1:{self.server.server_port}/rtd/2.4.0/api/{operation}.php'
        if uid is not None:
            address += '?user_id='+str(uid)
        request = urllib.request.Request(address,
            data=urllib.parse.urlencode({'request':json.dumps(payload)}).encode(),
            headers={'Cookie':'RTDSESSID='+token})
        with urllib.request.urlopen(request) as response:
            self.assertIsNone(response.headers.get('Content-Encoding'))
            plain = gzip.decompress(response.read())
        self.assertTrue(plain.startswith(b'{"code":'))
        return json.loads(plain)

    def test_tutorial_order_restart_is_idempotent(self):
        key = str(uuid.uuid4())
        self.call('create_user', dict(uuid=key, unit_no='3', user_name='Tutorial'))
        token = self.call('auth_user', dict(uuid=key))['session_id']
        self.assertEqual(self.call('get_quest_info', token=token)['result'], [])
        request = dict(get_level_list=[dict(level_data_id='10000', hash='0')])
        level = self.call('get_level_master', request, token)['result'][0]
        self.assertEqual((level['width'], level['height']), (8, 34))
        request['get_level_list'][0]['hash'] = level['hash']
        self.assertEqual(self.call('get_level_master', request, token)['result'], [])
        order = self.call('order_quest', dict(quest_id='10000', floor=0), token)
        self.assertEqual(order['code'], 4096)
        self.assertEqual(order['result']['action_point'], 19)
        enemies = order['result']['enemy_info_list']
        self.assertEqual(len(enemies), 4)
        self.assertTrue(all(e['flag'] for e in enemies))
        self.stop_server()
        self.start_server()
        self.assertEqual(self.call('order_quest', dict(quest_id='10000', floor=0), token), order)
        battle = self.call('get_quest_info', token=token)['result'][0]
        self.assertEqual(battle['enemy_info_list'], enemies)
        self.assertEqual(battle['quest_status'], 1)
        self.assertEqual(self.call('order_quest', dict(quest_id='11001'), token)['code'], 9472)

    def test_local_helper_contract_is_authenticated_read_only_and_restart_safe(self):
        key = str(uuid.uuid4())
        self.call('create_user', dict(uuid=key, unit_no='3', user_name='Helpers'))
        token = self.call('auth_user', dict(uuid=key))['session_id']
        # Inspect the persisted state directly, rather than relying on login side effects.
        import sqlite3
        def saved():
            with sqlite3.connect(self.database) as db:
                return db.execute('SELECT state FROM players').fetchone()[0]
        before = saved()
        response = self.call('get_helpers', token=token)
        self.assertEqual(response['code'], 4096)
        self.assertEqual(set(response), {'code', 'session_id', 'result'})
        helper = response['result'][0]
        self.assertEqual(set(helper), {'user_id','user_name','rank','last_play_date',
            'friend','friend_point','unit_id','unit_level','unit_bonus_life',
            'unit_bonus_attack','unit_bonus_heal'})
        self.assertEqual((helper['user_id'],helper['user_name'],helper['unit_id'],helper['unit_level']),
                         (0,'LOCAL_HELPER',14012,20))
        self.assertIs(helper['friend'], False)
        self.assertIs(helper['friend_point'], True)
        import datetime
        datetime.datetime.fromisoformat(helper['last_play_date'].replace('Z','+00:00'))
        self.assertEqual(saved(), before)
        self.assertEqual(self.call('get_helpers')['code'], 8196)
        self.assertEqual(self.call('get_helpers', token=token, uid=999)['code'], 8198)
        self.stop_server()
        self.start_server()
        repeated = self.call('get_helpers', token=token)['result'][0]
        self.assertEqual({k:v for k,v in repeated.items() if k != 'last_play_date'},
                         {k:v for k,v in helper.items() if k != 'last_play_date'})
        self.assertEqual(saved(), before)

    def test_second_tutorial_catalog_uses_shipped_canonical_tables(self):
        key = str(uuid.uuid4())
        self.call('create_user', dict(uuid=key, unit_no='3', user_name='Catalog'))
        token = self.call('auth_user', dict(uuid=key))['session_id']
        response = self.call('get_master', dict(compare_hash_only=False,
            get_data_list=[dict(type=t, hash='0') for t in (22,70)]), token)
        self.assertEqual(response['code'], 4096)
        drop, levels = response['result']
        self.assertEqual((drop['hash'],len(drop['data_list'])),('861272216',1808))
        self.assertEqual((levels['hash'],len(levels['data_list'])),('797777103',269))
        drops = {d['id']:d for d in drop['data_list']}
        self.assertEqual([drops[i]['unit1_id'] for i in range(110,114)],list(range(10020,10024)))
        self.assertIn(10001,{d['level_data_id'] for d in levels['data_list']})

    def test_full_startup_master_manifest(self):
        key = str(uuid.uuid4())
        self.call('create_user', dict(uuid=key, unit_no='0', user_name='MasterTest'))
        token = self.call('auth_user', dict(uuid=key))['session_id']
        kinds = [60,10,11,12,13,14,20,21,30,31,51,52,43,15,90,32,33,34,16,17]
        request = dict(compare_hash_only=True, get_data_list=[dict(type=t,hash='0') for t in kinds])
        response = self.call('get_master', request, token)
        self.assertEqual(response['code'],4096)
        self.assertEqual([t['type'] for t in response['result']],kinds)
        self.assertTrue(all('data_list' not in t for t in response['result']))
        request.update(compare_hash_only=False,get_data_list=[dict(type=t,hash='0') for t in (32,33,16,17)])
        downloaded=self.call('get_master',request,token)
        self.assertEqual([len(t['data_list']) for t in downloaded['result']],[2277,996,34,95])

    def test_second_tutorial_entry_validates_hashes_and_keeps_one_snapshot(self):
        key = str(uuid.uuid4())
        self.call('create_user', dict(uuid=key,unit_no='3',user_name='BattleEntry'))
        token = self.call('auth_user',dict(uuid=key))['session_id']
        kinds = [30,31,21,20,10,11,12,13,14,32,33,90,16,17]
        tables = self.call('get_master',dict(compare_hash_only=True,
            get_data_list=[dict(type=t,hash='0') for t in kinds]),token)['result']
        level = self.call('get_level_master',dict(get_level_list=[dict(level_data_id='10001',hash='0')]),token)['result'][0]
        request = dict(quest_id='10001',floor=0,helper_user_id='0',resume_id=0,
            bonus_stamina=0,token=str(uuid.uuid4()),level_data_hash=level['hash'],
            hashes={str(t['type']):t['hash'] for t in tables})
        self.assertEqual(self.call('order_quest',request,token)['code'],9472)
        self.call('order_quest',dict(quest_id='10000',floor=0),token)
        self.call('clear_quest2',dict(list=[dict(quest_id=10000,exp=50,game_money=30000,
            yorisiro_exp=0,units=[],challenge_id_list=[])]),token)
        before = self.call('get_quest_info',token=token)
        self.assertEqual(self.call('order_quest',dict(request,hashes={}),token)['code'],8209)
        self.assertEqual(self.call('order_quest',dict(request,level_data_hash='0'),token)['code'],8209)
        self.assertEqual(self.call('order_quest',dict(request,helper_user_id='1'),token)['code'],9472)
        self.assertEqual(self.call('order_quest',dict(request,floor=1),token)['code'],9472)
        self.assertEqual(self.call('get_quest_info',token=token),before)
        ordered = self.call('order_quest',request,token)
        self.assertEqual(ordered['code'],4096)
        self.assertEqual(ordered['result']['action_point'],18)
        enemies = ordered['result']['enemy_info_list']
        ordinary = [e for e in enemies if e['enemy_id'] not in (0,99)]
        self.assertEqual(len(ordinary),13)
        self.assertEqual({e['drop_unit_id'] for e in ordinary},set(range(10020,10024)))
        self.assertTrue(all(e['drop_unit_level']==1 for e in ordinary))
        self.assertEqual(len([e for e in enemies if e['enemy_id']==0]),1)
        self.assertEqual(next(e for e in enemies if e['enemy_id']==0)['enemy_set_id'],12021)
        self.assertEqual(next(e for e in enemies if e['enemy_id']==99)['enemy_set_id'],31010)
        self.assertEqual(self.call('order_quest',dict(request,token=str(uuid.uuid4()),retry=1),token)['code'],9472)
        self.assertEqual(self.call('order_quest',dict(request,retry=1),token),ordered)
        self.stop_server()
        self.start_server()
        self.assertEqual(self.call('order_quest',request,token),ordered)
        battle = self.call('get_quest_info',token=token)['result'][0]
        self.assertEqual(battle['quest_id'],10001)
        self.assertEqual(battle['enemy_info_list'],enemies)

    def test_second_tutorial_new_order_abandons_without_rewards_atomically(self):
        key=str(uuid.uuid4())
        self.call('create_user',dict(uuid=key,unit_no='3',user_name='RestartBattle'))
        token=self.call('auth_user',dict(uuid=key))['session_id']
        self.call('order_quest',dict(quest_id='10000',floor=0),token)
        self.call('clear_quest2',dict(list=[dict(quest_id=10000,exp=50,game_money=30000,
            yorisiro_exp=0,units=[],challenge_id_list=[])]),token)
        kinds=[30,31,21,20,10,11,12,13,14,32,33,90,16,17]
        tables=self.call('get_master',dict(compare_hash_only=True,
            get_data_list=[dict(type=t,hash='0') for t in kinds]),token)['result']
        order=dict(quest_id='10001',floor=0,helper_user_id='0',resume_id=0,
            bonus_stamina=0,token=str(uuid.uuid4()),level_data_hash='4081725474',
            hashes={str(t['type']):t['hash'] for t in tables})
        self.assertEqual(self.call('order_quest',order,token)['result']['action_point'],18)
        from rtd_server import API
        before=API(self.database).store.session(token)
        replacement=dict(order,token=str(uuid.uuid4()))
        self.assertEqual(self.call('order_quest',dict(replacement,hashes={}),token)['code'],8209)
        self.assertEqual(API(self.database).store.session(token),before)
        second=self.call('order_quest',replacement,token)
        self.assertEqual(second['code'],4096)
        self.assertEqual(second['result']['action_point'],17)
        state=API(self.database).store.session(token)
        self.assertEqual((state['player']['exp'],state['player']['game_money'],len(state['units'])),(50,30000,4))
        self.assertEqual(state['player']['quest_clear_flags'][0],2)
        self.stop_server();self.start_server()
        self.assertEqual(self.call('order_quest',dict(replacement,retry=1),token),second)
        self.assertEqual(self.call('order_quest',order,token)['code'],9472)
        with API(self.database).store.connect() as db:
            self.assertEqual(db.execute('SELECT status FROM quest_runs ORDER BY rowid').fetchall(),
                             [('cleared',),('abandoned',),('active',)])
            self.assertEqual(db.execute('SELECT count(*) FROM operation_receipts').fetchone()[0],1)

    def test_second_tutorial_settlement_rewards_retry_and_normal_replay(self):
        key = str(uuid.uuid4())
        self.call('create_user',dict(uuid=key,unit_no='3',user_name='SecondClear'))
        token = self.call('auth_user',dict(uuid=key))['session_id']
        self.call('order_quest',dict(quest_id='10000',floor=0),token)
        self.call('clear_quest2',dict(list=[dict(quest_id=10000,exp=50,game_money=30000,
            yorisiro_exp=0,units=[],challenge_id_list=[])]),token)
        kinds = [30,31,21,20,10,11,12,13,14,32,33,90,16,17]
        tables=self.call('get_master',dict(compare_hash_only=True,
            get_data_list=[dict(type=t,hash='0') for t in kinds]),token)['result']
        order=dict(quest_id='10001',floor=0,helper_user_id='0',resume_id=0,
            bonus_stamina=0,token=str(uuid.uuid4()),level_data_hash='4081725474',
            hashes={str(t['type']):t['hash'] for t in tables})
        self.assertEqual(self.call('order_quest',order,token)['code'],4096)
        entry=dict(quest_id=10001,exp=50,game_money=500,yorisiro_exp=660,
            units=[dict(unit_id=10021,level=1)],challenge_id_list=[])
        req=dict(list=[entry],party_instance_id=[1001,1002,1003,0,0,0])
        from rtd_server import API
        def saved():
            return API(self.database).store.session(token)
        before=saved()
        for bad in (dict(entry,exp=101),dict(entry,game_money=9001),dict(entry,yorisiro_exp=1000000),
                    dict(entry,units=[dict(unit_id=14012,level=1)]),
                    dict(entry,units=[dict(unit_id=10021,level=2)]),
                    dict(entry,units=[dict(unit_id=10021,level=1)]*6),
                    dict(entry,challenge_id_list=[1]),dict(entry,sp_event_point=1)):
            self.assertNotEqual(self.call('clear_quest2',dict(req,list=[bad]),token)['code'],4096)
            self.assertEqual(saved(),before)
        cleared=self.call('clear_quest2',req,token)
        self.assertEqual(cleared['code'],4096)
        result=cleared['result'][0]
        user=result['user']
        self.assertEqual((user['exp'],user['rank'],user['game_money'],user['friend_point']),
                         (100,2,80500,200))
        self.assertEqual((user['action_point'],user['max_action_point'],user['max_friend'],user['max_cost']),
                         (21,21,11,200))
        self.assertEqual((user['total_paid_point'],user['free_paid_point']),(6,6))
        self.assertEqual(user['quest_clear_flags'][0]&6,6)
        self.assertEqual((result['present_type'],result['present_param'],result['present_param_1']),(3,1,0))
        self.assertEqual([u['unit_id'] for u in result['get_units']],[10021,50000])
        self.assertTrue(all('favorite' not in u for u in result['get_units']))
        self.assertEqual(result['get_units'][-1]['exp'],660)
        once=saved()
        self.stop_server();self.start_server()
        self.assertEqual(self.call('clear_quest2',dict(req,retry=1),token),cleared)
        self.assertEqual(saved(),once)
        self.assertEqual(self.call('get_quest_info',token=token)['result'],[])
        self.assertEqual(self.call('order_quest',order,token)['code'],9472)
        new_order=dict(order,token=str(uuid.uuid4()))
        self.assertEqual(self.call('order_quest',new_order,token)['code'],4096)
        active=saved()
        # Could be a delayed old retry OR the new run's first packet was lost.
        # A stale success would make the client discard the new battle unrewarded.
        self.assertEqual(self.call('clear_quest2',dict(req,retry=1),token)['code'],8197)
        self.assertEqual(saved(),active)
        again=self.call('clear_quest2',req,token)
        self.assertEqual(again['code'],4096)
        self.assertEqual(again['result'][0]['present_type'],0)
        final=saved()
        self.assertEqual((final['player']['exp'],final['player']['game_money'],
                          final['player']['free_paid_point']),(150,81000,6))
        self.assertEqual(len(final['units']),len(once['units'])+2)

    def test_ordinary_11000_entry_requires_unlock_and_persists_random_snapshot(self):
        key = str(uuid.uuid4())
        self.call('create_user',dict(uuid=key,unit_no='3',user_name='OrdinaryEntry'))
        token = self.call('auth_user',dict(uuid=key))['session_id']
        kinds = [30,31,21,20,10,11,12,13,14,32,33,90,16,17]
        tables=self.call('get_master',dict(compare_hash_only=True,
            get_data_list=[dict(type=t,hash='0') for t in kinds]),token)['result']
        level=self.call('get_level_master',dict(get_level_list=[dict(level_data_id='11000',hash='0')]),token)['result'][0]
        order=dict(quest_id='11000',floor=0,helper_user_id='0',resume_id=0,
            bonus_stamina=0,token=str(uuid.uuid4()),level_data_hash=level['hash'],
            hashes={str(t['type']):t['hash'] for t in tables})
        self.assertEqual(self.call('order_quest',order,token)['code'],9472)
        self.call('order_quest',dict(quest_id='10000',floor=0),token)
        self.call('clear_quest2',dict(list=[dict(quest_id=10000,exp=50,game_money=30000,
            yorisiro_exp=0,units=[],challenge_id_list=[])]),token)
        second=dict(order,quest_id='10001',level_data_hash='4081725474',token=str(uuid.uuid4()))
        self.assertEqual(self.call('order_quest',second,token)['code'],4096)
        self.assertEqual(self.call('clear_quest2',dict(list=[dict(quest_id=10001,exp=50,
            game_money=500,yorisiro_exp=0,units=[],challenge_id_list=[])],
            party_instance_id=[1001,1002,1003,0,0,0]),token)['code'],4096)
        from rtd_server import API
        api=API(self.database)
        before=api.store.session(token)
        from rtd.masters.catalog import load_catalog
        old_hash=load_catalog()[0][20]['hash']
        stale=dict(order,hashes=dict(order['hashes'],**{'20':old_hash}))
        for bad,code in ((stale,8209),(dict(order,floor=1),9472),
                         (dict(order,level_data_hash='0'),8209)):
            self.assertEqual(self.call('order_quest',bad,token)['code'],code)
            self.assertEqual(api.store.session(token),before)
        ordered=self.call('order_quest',order,token)
        self.assertEqual(ordered['code'],4096)
        self.assertEqual(ordered['result']['action_point'],18)
        enemies=ordered['result']['enemy_info_list']
        self.assertEqual(next(e for e in enemies if e['enemy_id']==0)['enemy_set_id'],41221)
        self.assertEqual(next(e for e in enemies if e['enemy_id']==99)['enemy_set_id'],31010)
        self.assertTrue(all(type(e['flag']) is bool for e in enemies))
        self.assertTrue(all(e['drop_unit_id'] in (0,10000,15012,11030,10004,10014,10024,10034) for e in enemies))
        self.assertTrue(all(not e['drop_unit_id'] or 1<=e['drop_unit_level']<=6 for e in enemies))
        self.assertEqual(self.call('order_quest',dict(order,retry=1),token),ordered)
        self.stop_server();self.start_server()
        self.assertEqual(self.call('order_quest',order,token),ordered)
        self.assertEqual(self.call('get_quest_info',token=token)['result'][0]['enemy_info_list'],enemies)
        self.assertEqual(self.call('order_quest',dict(order,quest_id='11001'),token)['code'],9472)
        soul_exp=int((20*30)**0.65)*15
        entry=dict(quest_id=11000,exp=50,game_money=500,yorisiro_exp=soul_exp,
            units=[dict(unit_id=11030,level=1)],challenge_id_list=[10,11])
        req=dict(list=[entry],party_instance_id=[1001,1002,1003,0,0,0])
        active=api.store.session(token)
        for bad in (dict(entry,exp=100),dict(entry,game_money=17501),
                    dict(entry,yorisiro_exp=0),dict(entry,challenge_id_list=[10,10]),
                    dict(entry,challenge_id_list=[123456]),
                    dict(entry,units=[dict(unit_id=11030,level=1)]*2)):
            self.assertNotEqual(self.call('clear_quest2',dict(req,list=[bad]),token)['code'],4096)
            self.assertEqual(api.store.session(token),active)
        cleared=self.call('clear_quest2',req,token)
        self.assertEqual(cleared['code'],4096)
        user=cleared['result'][0]['user']
        self.assertEqual((user['exp'],user['game_money'],user['quest_clear_flags'][0]),(150,81000,14))
        self.assertEqual(cleared['result'][0]['present_type'],0)
        self.assertEqual([u['unit_id'] for u in cleared['result'][0]['get_units']],[11030,50000])
        self.assertEqual(user['quest_challenge_state'],[
            dict(quest_id=11000,challenge_id=10,state=1),dict(quest_id=11000,challenge_id=11,state=1)])
        once=api.store.session(token)
        self.stop_server();self.start_server()
        self.assertEqual(self.call('clear_quest2',dict(req,retry=1),token),cleared)
        self.assertEqual(api.store.session(token),once)
        self.assertEqual(self.call('login',token=token)['result']['quest_challenge_state'],user['quest_challenge_state'])
        self.assertEqual(self.call('order_quest',dict(order,token=str(uuid.uuid4())),token)['code'],4096)
        self.assertEqual(self.call('clear_quest2',req,token)['code'],4096)
        final=api.store.session(token)
        self.assertEqual((final['player']['exp'],final['player']['game_money']),(200,81500))
        self.assertEqual(final['player']['quest_challenge_state'],user['quest_challenge_state'])
        self.assertEqual(len(final['units']),len(once['units'])+2)

    def test_settlement_survives_response_loss_and_restart(self):
        key = str(uuid.uuid4())
        self.call('create_user', dict(uuid=key,unit_no='3',user_name='Settle'))
        token = self.call('auth_user',dict(uuid=key))['session_id']
        entry = dict(quest_id=10000,exp=50,game_money=30000,yorisiro_exp=420,units=[],challenge_id_list=[])
        req = dict(list=[entry],party_instance_id=[1001,1002,1003,0,0])
        self.assertEqual(self.call('clear_quest2',req,token)['code'],8197)
        self.call('order_quest',dict(quest_id='10000',floor=0),token)
        bad = dict(list=[dict(entry,exp=101)])
        self.assertEqual(self.call('clear_quest2',bad,token)['code'],8194)
        cleared = self.call('clear_quest2',req,token)
        self.assertEqual(cleared['code'],4096)
        self.assertEqual(cleared['result'][0]['user']['quest_clear_flags'][0],2)
        self.assertNotIn('system_flag',cleared['result'][0]['user'])
        self.stop_server(); self.start_server()
        self.assertEqual(self.call('clear_quest2',dict(req,retry=1),token),cleared)
        self.assertEqual(self.call('get_quest_info',token=token)['result'],[])
        units=self.call('get_units',token=token)['result']['units']
        self.assertEqual(len(units),4)
        self.assertEqual((units[-1]['unit_id'],units[-1]['exp']),(50000,420))
        for operation in ('get_friends','get_presents'):
            self.assertEqual(self.call(operation,token=token)['result'],[])
        self.assertEqual(self.call('auth_user',dict(uuid=key))['result']['free_paid_point'],5)
        summon=dict(gacha_id='20000',tutorial_flag='True',paid_point='5')
        summoned=self.call('buy_gacha',summon,token)
        self.assertEqual(summoned['code'],4096)
        self.assertEqual(summoned['result']['total_paid_point'],0)
        self.stop_server();self.start_server()
        self.assertEqual(self.call('buy_gacha',dict(summon,retry='1'),token),summoned)
        restored=self.call('auth_user',dict(uuid=key))['result']
        self.assertEqual(restored['tutorial_flags'][0]&1,1)
        self.assertEqual(restored['free_paid_point'],0)
        self.assertEqual(len(self.call('get_units',token=token)['result']['units']),5)

    def test_account_restart_and_storage(self):
        key = str(uuid.uuid4())
        req = dict(uuid=key, unit_no='2', user_name='Local Test')
        created = self.call('create_user', req)
        self.assertEqual(created['code'], 4096)
        self.assertNotIn('system_flag',created['result'])
        self.assertNotIn('payment_total',created['result'])
        self.assertNotIn('favorite',created['result']['get_units'][0])
        uid = created['result']['user_id']
        self.assertEqual([u['unit_id'] for u in created['result']['get_units']], [20020,11102,10030])
        self.assertEqual(self.call('create_user', req), created)
        self.assertEqual(self.call('create_user',dict(req,user_name='Different'))['code'],37122)
        self.assertEqual(self.call('auth_user',{'ver':'1.0','uuid':key})['code'],8193)
        self.assertEqual(self.call('auth_user', {'uuid':str(uuid.uuid4())})['code'], 8195)
        self.assertEqual(self.call('login')['code'], 8196)
        auth = self.call('auth_user', {'uuid':key})
        token = auth['session_id']
        self.assertEqual(self.call('login', token=token, uid=uid+1)['code'],8198)
        login = self.call('login', token=token, uid=uid)
        self.assertEqual(login['result']['login_days'], 1)
        self.assertEqual(self.call('login', token=token)['result']['login_days'], 1)
        party = created['result']['party']
        party['active'] = 1
        party['party'][1]['instanceIds'][0:2] = party['party'][1]['instanceIds'][1::-1]
        self.assertEqual(self.call('form_units', {'party':party},token)['code'],4096)
        self.assertEqual(self.call('save_local_flags', {'unit_collection_flags':[1,2,255]},token)['code'],4096)
        invalid = json.loads(json.dumps(party))
        invalid['party'][1]['instanceIds'][0] = 999999999
        self.assertEqual(self.call('form_units', {'party':invalid},token)['code'],8198)
        self.assertEqual(self.call('order_quest', token=token)['code'],8197)
        self.stop_server()
        self.start_server()
        # A fresh server process-equivalent instance must restore the same account and session.
        units = self.call('get_units',token=token)
        self.assertEqual(units['result']['party'],party)
        self.assertNotIn('leader',units['result']['units'][0])
        auth2 = self.call('auth_user',{'uuid':key})
        self.assertEqual(auth2['result']['user_id'],uid)
        self.assertEqual(auth2['result']['login_days'],1)
        state = API(self.database).store.session(token)
        self.assertEqual(state['unit_collection_flags'],[1,2,255])
        self.assertNotIn(key, (self.root/'requests.jsonl').read_text())
        self.assertNotIn(token, (self.root/'requests.jsonl').read_text())

    def test_expired_session(self):
        key=str(uuid.uuid4())
        created=self.call('create_user',dict(uuid=key,unit_no='0',user_name='Expiry'))
        token=self.call('auth_user',dict(uuid=key))['session_id']
        store=API(self.database).store
        with store.connect() as db:
            db.execute('UPDATE sessions SET expires_at=0 WHERE token=?',(token,))
        self.assertEqual(self.call('login',token=token)['code'],8196)
        auth=self.call('auth_user',dict(uuid=key))
        self.assertEqual(auth['result']['user_id'],created['result']['user_id'])
        self.assertNotEqual(auth['session_id'],token)


if __name__ == '__main__':
    unittest.main()
