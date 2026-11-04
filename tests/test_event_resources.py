"""Verify the actual HTTP download overlay and preservation of canonical resources."""
import hashlib
import http.server
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch
from rtd.config import ROOT
from rtd.resources import Handler


class ResourceOverlayTest(unittest.TestCase):
    def test_downloads_are_opt_in_and_original_file_wins(self):
        class QuietHandler(Handler):
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),QuietHandler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            markers=json.loads((ROOT/'config/event-reconstruction-book-markers.json').read_text())['bundles']
            with tempfile.TemporaryDirectory() as tmp,patch('rtd.resources.bundle_root',Path(tmp)):
                for marker in markers:
                    name=marker['generated_bundle'];url=f'http://127.0.0.1:{server.server_port}/bundles/{name}'
                    with patch.dict(os.environ,{'RTD_EVENT_RECONSTRUCTION':'0'}):
                        with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(url)
                        self.assertEqual(error.exception.code,404)
                    with patch.dict(os.environ,{'RTD_EVENT_RECONSTRUCTION':'1'}):
                        with urllib.request.urlopen(url) as reply:data=reply.read()
                        self.assertEqual(hashlib.sha256(data).hexdigest(),marker['generated_sha256'])
                    original=Path(tmp)/name;original.write_bytes(b'original canonical data')
                    with patch.dict(os.environ,{'RTD_EVENT_RECONSTRUCTION':'1'}):
                        with urllib.request.urlopen(url) as reply:self.assertEqual(reply.read(),original.read_bytes())
                    original.unlink()
        finally:
            server.shutdown();server.server_close();thread.join()
