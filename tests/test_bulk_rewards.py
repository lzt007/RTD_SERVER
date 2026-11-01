import pathlib,tempfile,unittest,uuid
from unittest.mock import patch
from rtd.services.api import API
from rtd.operations.configuration import ConfigurationError

class BulkRewardsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.api=API(pathlib.Path(self.temp.name)/'test.sqlite3')
        self.create('One');self.create('Two')
        self.body=dict(request_id='reward-1',message='Reward',present_type=3,present_param_0=5,present_param_1=0,target='all',user_ids=[])
    def create(self,name):self.api.call('create_user',dict(ver='2.4.0',uuid=str(uuid.uuid4()),unit_no=0,user_name=name))
    def test_all_snapshot_retry_and_conflict(self):
        r=self.api.delivery.broadcast(self.body)
        self.assertEqual(r['data']['user_ids'],[1,2])
        self.create('Three')
        self.assertEqual(self.api.delivery.broadcast(dict(reversed(list(self.body.items()))))['data'],r['data'])
        self.assertEqual(self.api.delivery.read('3'),[])
        self.assertEqual(len(self.api.delivery.read('1')),1)
        with self.assertRaises(ConfigurationError):self.api.delivery.broadcast(dict(self.body,present_param_0=6))
    def test_selected_atomic_failure_and_npc_exclusion(self):
        s=self.api.store.by_id(2);s['npc_helper_key']='test';self.api.store.save(s)
        r=self.api.delivery.broadcast(self.body)
        self.assertEqual(r['data']['user_ids'],[1])
        with self.assertRaises(ConfigurationError):self.api.delivery.broadcast(dict(self.body,request_id='selected',target='selected',user_ids=[1,999]))
        self.assertEqual(len(self.api.delivery.read('1')),1)
        save=self.api.store.save
        def fail(s):save(s);raise RuntimeError('injected write failure')
        with patch.object(self.api.store,'save',side_effect=fail),self.assertRaises(RuntimeError):
            self.api.delivery.broadcast(dict(self.body,request_id='fail'))
        self.assertEqual(len(self.api.delivery.read('1')),1)
