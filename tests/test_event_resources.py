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
    def test_verified_inferred_book_in_canonical_directory_is_accepted(self):
        from rtd.policies.reconstructed_resources import resource_issues
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'resources/bundles').mkdir(parents=True);(root/'config').mkdir()
            book=b'new inferred book';character=b'original character'
            (root/'resources/bundles/ms00_book_el_05.unity3d').write_bytes(book)
            (root/'resources/bundles/characters.unity3d').write_bytes(character)
            (root/'config/event-reconstruction-book-markers.json').write_text(json.dumps(dict(bundles=[
                dict(generated_bundle='ms00_book_el_05.unity3d',generated_sha256=hashlib.sha256(book).hexdigest())])))
            masters={30:dict(data_list=[dict(id=1,enemy_table_id=1)]),
                     21:dict(data_list=[dict(id=1,boss_set_id=1,death_set_id=1,enemy1_set_id=1)]),
                     20:dict(data_list=[dict(id=1,type=24,model='original_character')])}
            assets=dict(source_hashes={'resources/bundles/characters.unity3d':hashlib.sha256(character).hexdigest(),
                                      'resources/bundles/ms00_book_el_05.unity3d':hashlib.sha256(b'old inferred marker').hexdigest()},
                        bundle_sources={},character_dependencies=[dict(enemy_id=1,model_present=True,
                            model='original_character',bundle='characters.unity3d',book_color=5)])
            with patch('rtd.policies.reconstructed_resources.ROOT',root):
                self.assertEqual(resource_issues(masters,{1:dict(map_data='01')},{1},assets),{})
                (root/'resources/bundles/ms00_book_el_05.unity3d').write_bytes(b'unverified bytes')
                self.assertIn('unprepared book marker ms00_book_el_05.unity3d',resource_issues(masters,{1:dict(map_data='01')},{1},assets)['1'])

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
