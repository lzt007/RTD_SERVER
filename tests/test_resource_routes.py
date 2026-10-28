import http.client, http.server, tempfile, threading, unittest
from pathlib import Path
from unittest.mock import patch
from rtd import resources as bundles

class CacheRoutesTest(unittest.TestCase):
    def test_cache_route_serves_exact_bytes_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);
            (root/('a'*40)).mkdir();payload=b'original raw cache payload'
            (root/('a'*40)/'CustomAssetBundle-test').write_bytes(payload)
            with patch.object(bundles,'cache_root',root):
                server=http.server.ThreadingHTTPServer(('127.0.0.1',0),bundles.Handler)
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    for path,status,body in [('/cache/Shared/'+('a'*40)+'/CustomAssetBundle-test',200,payload),('/cache/Shared/../rtd.config.json',404,None),('/cache/Shared/%2e%2e/rtd.config.json',404,None)]:
                        c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5);c.request('GET',path);r=c.getresponse();actual=r.read();self.assertEqual(r.status,status)
                        if body is not None:self.assertEqual(actual,body)
                        c.close()
                finally:server.shutdown();server.server_close();thread.join()
