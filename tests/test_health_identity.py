import http.client
import http.server
import importlib
import json
import os
import pathlib
import tempfile
import threading
import unittest
from unittest.mock import patch

from rtd.services.api import API
from rtd.transport.http import handler_for


class HealthIdentityTest(unittest.TestCase):
    def test_path_identity_is_canonical_respects_platform_case_and_does_not_create_database(self):
        identity=importlib.import_module('rtd.storage.identity').database_path_id
        with tempfile.TemporaryDirectory(prefix='rtd identity 中文 ') as folder:
            root=pathlib.Path(folder);path=root/'new dir'/'测试.sqlite3'
            self.assertEqual(identity(path),identity(root/'unused'/'..'/'new dir'/'测试.sqlite3'))
            upper = str(path).upper()
            if os.path.normcase(str(path)) == os.path.normcase(upper):
                self.assertEqual(identity(path),identity(upper))
            else:
                self.assertNotEqual(identity(path),identity(upper))
            self.assertNotEqual(identity(path),identity(root/'other.sqlite3'))
            self.assertFalse((root/'new dir').exists())

    def test_real_health_binds_selected_database_and_content_mode_without_secrets(self):
        with tempfile.TemporaryDirectory(prefix='rtd health ') as folder:
            values=[]
            for index,experimental in enumerate(('0','1')):
                path=pathlib.Path(folder)/('database '+str(index)+'.sqlite3')
                with patch.dict('os.environ',RTD_CONTENT_EXPERIMENTAL=experimental):api=API(path)
                server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler_for(api,path.with_suffix('.log')))
                thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
                try:
                    c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=5)
                    try:
                        c.request('GET','/health');response=c.getresponse();payload=response.read()
                        self.assertEqual(response.status,200)
                        data=json.loads(payload)
                    finally:c.close()
                    self.assertEqual(data['protocol'],'RTD-2.4.0')
                    self.assertIs(data['experimental_content'],bool(index))
                    identity=importlib.import_module('rtd.storage.identity').database_path_id
                    self.assertEqual(data['database_path_id'],identity(path))
                    self.assertNotIn(str(path),payload.decode())
                    self.assertEqual(set(data),{'status','protocol','master_types','database_path_id','experimental_content'})
                    values.append(data['database_path_id'])
                finally:server.shutdown();server.server_close();thread.join()
            self.assertNotEqual(*values)


if __name__=='__main__':unittest.main()
