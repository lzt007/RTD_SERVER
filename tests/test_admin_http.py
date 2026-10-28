import http.client
import http.server
import json
import pathlib
import tempfile
import threading
import unittest
import io
from email.message import Message
from unittest.mock import Mock
from rtd.services.api import API
from rtd.transport.admin import handle_admin
from rtd.transport.http import handler_for
from test_live_configuration import event


class AdminHttpTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=pathlib.Path(self.temp.name);self.api=API(root/'http.sqlite3')
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.api,root/'http.log'))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):self.server.shutdown();self.server.server_close();self.thread.join()
    def request(self,method,path,body=None,raw=None,content_type='application/json'):
        connection=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        try:
            data=json.dumps(body).encode() if raw is None and body is not None else raw
            connection.request(method,'/admin/v1/'+path,body=data,headers={'Content-Type':content_type})
            response=connection.getresponse();payload=response.read()
            self.assertTrue(response.getheader('Content-Type','').startswith('application/json'))
            return response.status,json.loads(payload)
        finally:connection.close()

    def test_real_http_read_write_catalog_and_conflict(self):
        status,config=self.request('GET','config');self.assertEqual(status,200)
        self.assertEqual(config['data']['revision'],1)
        self.assertTrue(config['availability']['gachas'][0]['effective_open'])
        status,pool=self.request('GET','gachas/10000');self.assertEqual(pool['data']['id'],10000)
        status,result=self.request('PATCH','gachas/10000',dict(enabled=False,expected_revision=1))
        self.assertEqual(status,200);self.assertEqual(result['data']['revision'],2)
        self.assertFalse(result['availability']['gachas'][0]['effective_open'])
        self.assertEqual(self.request('PATCH','gachas/10000',dict(enabled=True,expected_revision=1))[0],409)
        self.assertEqual(self.request('PUT','events/local-11000',event())[0],200)
        self.assertEqual(self.request('GET','events')[1]['data'][0]['id'],'local-11000')
        self.assertEqual(self.request('GET','events/local-11000')[0],200)
        self.assertEqual(self.request('DELETE','events/local-11000')[0],200)
        self.assertEqual(self.request('GET','events/local-11000')[0],404)
        status,catalog=self.request('GET','catalog');self.assertEqual(status,200)
        self.assertEqual(len(catalog['data']['units']),751)
        self.assertEqual(len(catalog['data']['quests']),1021)

    def test_json_errors_invalid_atomic_replacement_and_methods(self):
        before=self.api.operations.read()
        for method,path,body,expected in (
            ('PUT','config',dict(gachas=before['gachas'],events=[event(quests=[])]),422),
            ('PATCH','gachas/10000',dict(enabled='false'),422),
            ('PATCH','events/missing',dict(enabled=False),404),
            ('DELETE','gachas/10000',None,405),('POST','config',{},405),
            ('GET','unknown',None,404),('GET','gachas/99999',None,404),
            ('PATCH','config',{},405)):
            status,error=self.request(method,path,body);self.assertEqual(status,expected,(method,path,error))
            self.assertIn('message',error['error']);self.assertEqual(self.api.operations.read(),before)
        self.assertEqual(self.request('PUT','config',raw=b'{bad')[0],400)
        self.assertEqual(self.request('PUT','config',raw=b'{}',content_type='text/plain')[0],415)
        self.assertEqual(self.request('PUT','config',raw=b' '*(1024*1024+1))[0],413)
        self.assertEqual(self.request('PUT','config',raw=b'\xff')[0],400)
        self.assertEqual(self.request('PUT','config',raw=b'[]')[0],422)

    def test_rejected_method_consumes_bounded_body_before_closing_connection(self):
        headers=Message();headers['Content-Length']='2';headers['Content-Type']='application/json'
        handler=Mock(command='POST',path='/admin/v1/config',headers=headers,
                     rfile=io.BytesIO(b'{}'),wfile=io.BytesIO())
        handle_admin(handler,self.api)
        self.assertEqual(handler.rfile.read(),b'')
        for _ in range(10):
            self.assertEqual(self.request('POST','config',raw=b' '*65536)[0],405)


if __name__=='__main__':unittest.main()
