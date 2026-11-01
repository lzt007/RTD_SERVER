import base64,http.client,http.server,json,pathlib,tempfile,threading,unittest,uuid
from unittest.mock import patch
from rtd.services.api import API
from rtd.transport.http import handler_for

class RewardHttpTest(unittest.TestCase):
 def test_authenticated_batch_and_player_claim(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict('os.environ',RTD_ADMIN_PASSWORD='local-test'):
   api=API(pathlib.Path(tmp)/'db.sqlite3');key=str(uuid.uuid4())
   api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Local'))
   token=api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
   server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler_for(api,pathlib.Path(tmp)/'http.log'))
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    body=dict(target='selected',user_ids=[1],request_id='http-reward',message='Reward',present_type=3,present_param_0=5,present_param_1=0)
    auth='Basic '+base64.b64encode(b'admin:local-test').decode()
    for authorized,expected in ((False,401),(True,201),(True,200)):
     c=http.client.HTTPConnection(*server.server_address)
     c.request('POST','/admin/v1/rewards',json.dumps(body),{'Content-Type':'application/json',**({'Authorization':auth} if authorized else {})})
     r=c.getresponse();self.assertEqual(r.status,expected);r.read();c.close()
    gifts=api.call('get_presents',dict(ver='2.4.0'),token)['result'];self.assertEqual(len(gifts),1)
    api.call('open_present',dict(ver='2.4.0',serial_number_list=[gifts[0]['serial_number']]),token)
    self.assertEqual(api.store.session(token)['player']['free_paid_point'],5)
   finally:server.shutdown();server.server_close();thread.join()
