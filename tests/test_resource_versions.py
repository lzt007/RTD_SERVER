import http.client
import http.server
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from rtd import resources
from rtd.resource_catalog import publish_resources

class ResourceVersionsTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.file=self.root/'a.unity3d'; self.file.write_bytes(b'old')
        self.catalog=self.root/'catalog'
        publish_resources({'a.unity3d':self.file},{},self.catalog)
        self.override=patch.object(resources,'version_root',self.catalog,create=True);self.override.start();self.addCleanup(self.override.stop)
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),resources.Handler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close)
    def close(self):
        self.server.shutdown();self.server.server_close();self.thread.join()
    def request(self,method,path,body=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        c.request(method,path,body,{'Content-Type':'application/json'});r=c.getresponse(); result=(r.status,r.read());c.close();return result
    def resolve(self):
        return self.request('POST','/resources/v1/resolve',json.dumps({'protocol':1,'operationId':'test','roots':['a.unity3d']}))
    def test_batch_resolve_and_immutable_download(self):
        status,body=self.resolve();self.assertEqual(status,200); release=json.loads(body)
        path=release['resources'][0]['downloadPath']
        self.file.write_bytes(b'new');publish_resources({'a.unity3d':self.file},{},self.catalog)
        self.assertEqual(self.request('GET',path),(200,b'old'))
        self.assertNotEqual(json.loads(self.resolve()[1])['snapshotId'],release['snapshotId'])
    def test_reject_bad_protocol_unknown_root_and_malformed_json(self):
        for value in [{'protocol':2,'roots':['a.unity3d']},{'protocol':1,'roots':['absent.unity3d']},None]:
            body='{' if value is None else json.dumps(value)
            self.assertEqual(self.request('POST','/resources/v1/resolve',body)[0],400)
    def test_blob_traversal_rejected(self):
        for path in ['/resources/v1/blobs/../active.json','/resources/v1/blobs/'+'a'*64+'/%2e%2e']:
            self.assertEqual(self.request('GET',path)[0],404)
