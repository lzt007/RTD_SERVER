import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.install_backup_recovery import install

class InstallBackupTests(unittest.TestCase):
    @patch("scripts.install_backup_recovery.validate_candidate",return_value={"internal_file":"unique-cab"})
    def test_verified_install_preserves_old_and_dry_run(self, validator):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);candidate=root/'candidate';(candidate/'bundles').mkdir(parents=True);(root/'config').mkdir()
            (root/'config/monster-recovery.json').write_text(json.dumps({'bundles':[{'model':'old','bundle':'old.unity3d'}]}))
            data=b'verified';(candidate/'bundles/book.unity3d').write_bytes(data)
            row=dict(model='book',bundle='book.unity3d',sha256=hashlib.sha256(data).hexdigest(),status='validated_candidate',mesh_roundtrip=True,texture_roundtrip=True,missing_pointers=[],missing_motion_paths=[],retained_object_bytes_unchanged=True,runtime_verified=False)
            (candidate/'validation.json').write_text(json.dumps([row,dict(model='bad',status='blocked')]))
            install(candidate,root,dry_run=True)
            self.assertFalse((root/'resources/reconstructed/monsters/bundles/book.unity3d').exists())
            install(candidate,root)
            result=json.loads((root/'config/monster-recovery.json').read_text())
            self.assertEqual([r['model'] for r in result['bundles']],['book','old'])
            self.assertEqual((root/'resources/reconstructed/monsters/bundles/book.unity3d').read_bytes(),data)
            (candidate/'bundles/book.unity3d').write_bytes(b'corrupt')
            with self.assertRaises(ValueError):install(candidate,root)

class HTTPPriorityTests(unittest.TestCase):
    def test_book_recovery_precedes_old_event_but_original_wins(self):
        import http.server
        import threading
        import urllib.request
        from unittest.mock import patch
        import rtd.resources as resources
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fresh=root/'fresh';fresh.write_bytes(b'new book')
            old=root/'old';old.write_bytes(b'old event')
            server=http.server.ThreadingHTTPServer(('127.0.0.1',0),resources.Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                with patch.object(resources,'bundle_root',root),patch('rtd.policies.monster_recovery.bundle_file',return_value=fresh),patch('rtd.policies.reconstructed_resources.bundle_file',return_value=old):
                    url=f'http://127.0.0.1:{server.server_port}/Android/V1011/ms00_book_el_01.unity3d'
                    self.assertEqual(urllib.request.urlopen(url).read(),b'new book')
                    (root/'ms00_book_el_01.unity3d').write_bytes(b'original')
                    self.assertEqual(urllib.request.urlopen(url).read(),b'original')
            finally:server.shutdown();server.server_close();thread.join()
