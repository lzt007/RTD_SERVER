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
    def test_complete_dependency_pair_during_concurrent_publication(self):
        import hashlib
        other=self.root/'b.unity3d';other.write_bytes(b'old')
        graph={'a.unity3d':['b.unity3d'],'b.unity3d':[]}
        sources={'a.unity3d':self.file,'b.unity3d':other}
        publish_resources(sources,graph,self.catalog)
        failures=[]
        def writer():
            try:
                for i in range(20):
                    value=('release-'+str(i)).encode();self.file.write_bytes(value);other.write_bytes(value)
                    publish_resources(sources,graph,self.catalog)
            except Exception as error:failures.append(error)
        thread=threading.Thread(target=writer);thread.start()
        try:
            for _ in range(30):
                status,body=self.resolve();self.assertEqual(status,200)
                entries=json.loads(body)['resources'];self.assertEqual(len(entries),2)
                self.assertEqual(entries[0]['sha256'],entries[1]['sha256'])
                for entry in entries:
                    status,data=self.request('GET',entry['downloadPath']);self.assertEqual(status,200)
                    self.assertEqual(hashlib.sha256(data).hexdigest(),entry['sha256'])
        finally:thread.join()
        self.assertEqual(failures,[])

    def test_limits_and_unpublished_catalog_do_not_fall_through_to_legacy(self):
        self.assertEqual(self.request('POST','/resources/v1/resolve','x'*1048577)[0],413)
        for roots in [[],['a.unity3d']*4097]:
            self.assertEqual(self.request('POST','/resources/v1/resolve',json.dumps({'protocol':1,'roots':roots}))[0],400)
        (self.catalog/'active.json').unlink()
        self.assertEqual(self.resolve()[0],503)
