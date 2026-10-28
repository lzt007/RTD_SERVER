import concurrent.futures
import copy
import http.client
import http.server
import json
import pathlib
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch

from rtd.services.api import API
from rtd.services.presents import PRESENT_FIELDS
from rtd.transport.http import handler_for
from rtd.policies.unit_progression import level_exp


class AdminDeliveryTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=pathlib.Path(self.temp.name);self.path=self.root/'state.sqlite3'
        self.api=API(self.path);self.tokens=[]
        for i in range(2):
            identity=str(uuid.uuid4())
            self.api.call('create_user',dict(ver='2.4.0',uuid=identity,unit_no=i,user_name='Local'+str(i)))
            self.tokens.append(self.api.call('auth_user',dict(ver='2.4.0',uuid=identity))['session_id'])
        self.http=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.api,self.root/'http.log'))
        self.thread=threading.Thread(target=self.http.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.http.shutdown();self.http.server_close();self.thread.join()

    def request(self,method,path,body=None,raw=None,media='application/json'):
        c=http.client.HTTPConnection('127.0.0.1',self.http.server_port,timeout=10)
        try:
            c.request(method,'/admin/v1/'+path,body=json.dumps(body).encode() if body is not None else raw,
                      headers={'Content-Type':media})
            r=c.getresponse();self.assertIn('application/json',r.getheader('Content-Type'))
            return r.status,json.loads(r.read())
        finally:c.close()

    def body(self,**kw):
        return dict(dict(request_id='delivery-1',message='Local test',present_type=1,
                         present_param_0=1,present_param_1=0),**kw)

    def snapshot(self):
        with self.api.store.connect() as db:
            return {t:db.execute('SELECT * FROM '+t+' ORDER BY rowid').fetchall()
                    for t in ('players','sessions','runtime_config','quest_runs','operation_receipts')}

    def test_http_claim_restart_and_replay_never_resurrects(self):
        config=self.api.operations.read();other=copy.deepcopy(self.api.store.by_id(2))
        before=self.api.store.by_id(1);money=before['player']['game_money']
        status,ack=self.request('POST','presents/1',self.body())
        self.assertEqual(status,201);self.assertFalse(ack['replayed'])
        gift=ack['data']['present'];self.assertEqual(set(gift),set(PRESENT_FIELDS))
        state=self.api.store.by_id(1)
        self.assertEqual(state['player'],before['player']);self.assertEqual(state['units'],before['units'])
        self.assertEqual(self.request('POST','presents/1',self.body()),(200,dict(ack,replayed=True)))
        gifts=self.api.call('get_presents',dict(ver='2.4.0'),self.tokens[0])['result']
        self.assertIn(gift,gifts)
        self.api.call('open_present',dict(ver='2.4.0',serial_number_list=[gift['serial_number']]),self.tokens[0])
        self.assertEqual(self.api.store.by_id(1)['player']['game_money'],money+1)
        self.api=API(self.path)
        replay=self.api.delivery.send('1',self.body())
        self.assertTrue(replay['replayed']);self.assertEqual(replay['data'],ack['data'])
        self.assertNotIn(gift,self.api.store.by_id(1)['presents'])
        self.assertEqual(self.api.operations.read(),config);self.assertEqual(self.api.store.by_id(2),other)

    def test_conflict_and_player_scoped_request_id(self):
        self.assertEqual(self.request('POST','presents/1',self.body())[0],201)
        before=self.snapshot()
        self.assertEqual(self.request('POST','presents/1',self.body(message='Changed'))[0],409)
        self.assertEqual(self.snapshot(),before)
        self.assertEqual(self.request('POST','presents/2',self.body())[0],201)

    def test_invalid_requests_do_not_write(self):
        cases=[{},[],self.body(extra=1)]
        for field,values in {
            'request_id':['','x'*81,' space','汉字',True],
            'message':['','x'*121,'bad\x00',12],
            'present_type':[True,0,5,'1',1.0],
            'present_param_0':[True,0,-1,10000000,'1',1.0],
            'present_param_1':[True,1,'0',0.0],
        }.items():
            cases.extend(self.body(**{field:v}) for v in values)
        cases.extend([self.body(present_type=2,present_param_0=10001),
                      self.body(present_type=3,present_param_0=1000),
                      self.body(present_type=4,present_param_0=99999999,present_param_1=1),
                      self.body(present_type=4,present_param_0=10000,present_param_1=999)])
        before=self.snapshot()
        for body in cases:
            with self.subTest(body=body):
                self.assertEqual(self.request('POST','presents/1',body)[0],422)
                self.assertEqual(self.snapshot(),before)
        for key in ['0','01','-1','2147483648','true','999']:
            self.assertEqual(self.request('POST','presents/'+key,self.body())[0],404)
            self.assertEqual(self.snapshot(),before)

    def test_unit_claim_uses_original_level_experience(self):
        status,ack=self.request('POST','presents/1',self.body(present_type=4,present_param_0=10000,present_param_1=2))
        self.assertEqual(status,201)
        result=self.api.call('open_present',dict(ver='2.4.0',serial_number_list=[ack['data']['present']['serial_number']]),self.tokens[0])['result']
        unit=result['get_units'][0];master=next(m for m in self.api.masters[10]['data_list'] if m['id']==10000)
        self.assertEqual((unit['unit_id'],unit['level'],unit['exp']),(10000,2,level_exp(master,2)))

    def test_two_instances_serialize_same_delivery(self):
        second=API(self.path)
        barrier=threading.Barrier(2)
        def send(api):barrier.wait();return api.delivery.send('1',self.body())
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results=list(pool.map(send,[self.api,second]))
        self.assertEqual(sorted(r['replayed'] for r in results),[False,True])
        self.assertEqual(results[0]['data'],results[1]['data'])
        state=self.api.store.by_id(1)
        self.assertEqual(len(state['admin_present_receipts']),1)
        self.assertEqual(sum(g['message']=='Local test' for g in state['presents']),1)

    def test_write_then_failure_rolls_back_serial_gift_and_receipt(self):
        before=self.snapshot();save=self.api.store.save
        def fail(state):save(state);raise RuntimeError('after write')
        with patch.object(self.api.store,'save',side_effect=fail):
            with self.assertRaisesRegex(RuntimeError,'after write'):self.api.delivery.send('1',self.body())
        self.assertEqual(self.snapshot(),before)
        self.assertFalse(self.api.delivery.send('1',self.body())['replayed'])

    def test_safe_read_views_and_http_errors(self):
        self.assertEqual(self.request('POST','presents/1',self.body())[0],201)
        status,data=self.request('GET','players');self.assertEqual(status,200)
        self.assertEqual([p['user_id'] for p in data['data']],[1,2])
        for player in data['data']:
            self.assertEqual(set(player),{'user_id','user_name','rank','pending_present_count'})
        status,inbox=self.request('GET','presents/1');self.assertEqual(status,200)
        for gift in inbox['data']:self.assertEqual(set(gift),set(PRESENT_FIELDS))
        state=self.api.store.by_id(1);state['presents'][0].update(open_limit=1,date='2000-01-01T00:00:00Z');self.api.store.save(state)
        self.assertNotIn(state['presents'][0],self.request('GET','presents/1')[1]['data'])
        self.assertEqual(self.request('POST','players',self.body())[0],405)
        self.assertEqual(self.request('PUT','presents/1',self.body())[0],405)
        self.assertEqual(self.request('POST','presents/1',raw=b'{bad')[0],400)
        self.assertEqual(self.request('POST','presents/1',raw=b'{}',media='text/plain')[0],415)


if __name__=='__main__':unittest.main()
