import base64
import http.client
import http.server
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from rtd.transport.http import handler_for

class AdminAuthTest(unittest.TestCase):
    def test_password_gate(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict('os.environ', RTD_ADMIN_PASSWORD='test-password'):
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler_for(None, Path(folder)/'http.log'))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for method, path, password, expected in [
                    ('GET', '/admin/', None, 401),
                    ('HEAD', '/admin/', None, 401),
                    ('POST', '/admin/v1/config', None, 401),
                    ('GET', '/admin/assets/admin.js', 'wrong', 401),
                    ('GET', '/admin/', 'test-password', 200),
                ]:
                    connection = http.client.HTTPConnection(*server.server_address)
                    headers = {} if password is None else {'Authorization': 'Basic '+base64.b64encode(('admin:'+password).encode()).decode()}
                    connection.request(method, path, headers=headers)
                    response = connection.getresponse()
                    self.assertEqual(response.status, expected)
                    response.read()
                    connection.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
