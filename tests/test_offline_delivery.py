"""Real HTTP regression for legacy Unity bundle transfer framing."""
import hashlib
import http.server
import pathlib
import tempfile
import threading
import unittest
import urllib.request

from rtd import resources as bundles


class OfflineDeliveryTest(unittest.TestCase):
    def test_large_binary_response_has_exact_length_and_payload(self):
        original = bundles.bundle_root
        with tempfile.TemporaryDirectory() as directory:
            bundles.bundle_root = pathlib.Path(directory)
            payload = bytes(range(256)) * 8192 + b'final-block'
            (bundles.bundle_root / 'fixture.unity3d').write_bytes(payload)
            server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), bundles.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                url = f'http://127.0.0.1:{server.server_port}/Android/V1/fixture.unity3d'
                with urllib.request.urlopen(url, timeout=5) as response:
                    self.assertEqual(response.headers['Content-Length'], str(len(payload)))
                    self.assertEqual(response.headers['Connection'], 'keep-alive')
                    self.assertEqual(hashlib.sha256(response.read()).digest(), hashlib.sha256(payload).digest())
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
                bundles.bundle_root = original


if __name__ == '__main__':
    unittest.main()
