import pathlib,tempfile,unittest,uuid,json
from rtd.services.api import API
from rtd.common import ProtocolError

class SimulatedPurchaseTest(unittest.TestCase):
 def test_original_catalog_products(self):
  for suffix,amount in [('10000',1),('10010',6),('10020',12),('10030',30),('10040',60),('10050',85)]:
   product='rtd_item_'+suffix
   self.assertEqual(self.call('google_play_bill_begin',product_id=product),[])
   before=self.api.store.session(self.token)['player']['paid_point']
   signed=json.dumps(dict(productId=product,orderId='catalog-'+suffix))
   result=self.call('google_play_bill_point',signedData=signed,signature='local-simulation')
   self.assertEqual(result['paid_point'],before+amount)
   self.assertEqual(self.call('google_play_bill_point',signedData=signed,signature='local-simulation'),result)
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.path=pathlib.Path(self.temp.name)/'pay.sqlite3';self.api=API(self.path)
  key=str(uuid.uuid4());self.api.call('create_user',dict(ver='2.4.0',uuid=key,unit_no=0,user_name='Local'))
  self.token=self.api.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
 def call(self,op,**kw):return self.api.call(op,dict(ver='2.4.0',retry=0,**kw),self.token)['result']
 def test_success_restart_retry_conflict(self):
  req=dict(product_id='local.crystals.6',transaction_id='test-transaction')
  r=self.call('simulate_purchase',**req)
  self.assertEqual((r['paid_point'],r['total_paid_point'],r['payment_total']),(6,6,0))
  self.api=API(self.path)
  self.assertEqual(self.call('simulate_purchase',**req),r)
  with self.assertRaises(ProtocolError):self.call('simulate_purchase',**dict(req,product_id='local.crystals.1'))
  self.assertEqual(self.api.store.session(self.token)['player']['paid_point'],6)
 def test_original_google_local_receipt_and_unknown_product(self):
  self.assertEqual(self.call('google_play_bill_begin',product_id='local.crystals.6'),[])
  signed=json.dumps(dict(productId='local.crystals.6',orderId='local-order'))
  self.assertEqual(self.call('google_play_bill_point',signedData=signed,signature='')['paid_point'],6)
  self.assertEqual(self.call('google_play_bill_point',signedData=signed,signature='')['paid_point'],6)
  with self.assertRaises(ProtocolError):self.call('simulate_purchase',product_id='missing',transaction_id='bad')
 def test_receipt_replay_after_spending_does_not_restore_old_balance(self):
  self.call('simulate_purchase',product_id='local.crystals.6',transaction_id='spent')
  self.call('buy_max_unit',max_unit=20)
  r=self.call('simulate_purchase',product_id='local.crystals.6',transaction_id='spent')
  self.assertEqual(r['paid_point'],5)
 def test_apple_local_receipt_and_redaction(self):
  import base64
  from rtd.diagnostics.logging import redact
  receipt=base64.b64encode(json.dumps(dict(product_id='local.crystals.1',transaction_id='apple-local')).encode()).decode()
  self.assertEqual(self.call('app_store_purchase_point',encoded_receipt=receipt,price='ignored')['paid_point'],1)
  self.assertEqual(redact(dict(encoded_receipt='test',signedData='test',signature='test')),
                   dict(encoded_receipt='<redacted>',signedData='<redacted>',signature='<redacted>'))
