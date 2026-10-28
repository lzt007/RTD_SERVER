import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from rtd import config

class ProjectConfigTest(unittest.TestCase):
    def test_paths_resolve_against_project_not_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'rtd.config.json').write_text(json.dumps({'api':{'host':'127.0.0.2','port':24111},'resources':{'host':'127.0.0.3','port':24112,'public_base_url':'http://device:24112'},'paths':{'database':'state/db.sqlite3','bundles':'assets/bundles'}}))
            data=config.load_config(root/'rtd.config.json')
            self.assertEqual(config.path_for('database',data),root.resolve()/'state/db.sqlite3')
            self.assertEqual(config.path_for('bundles',data),root.resolve()/'assets/bundles')
            self.assertEqual(data['api']['port'],24111)
    def test_invalid_ports_fail_before_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'rtd.config.json';f.write_text(json.dumps({'api':{'port':-2}}))
            with self.assertRaises(ValueError):config.load_config(f)
    def test_default_resource_closure(self):
        for key in ('master_data','level_data','bundles','cache','startup','unit_icons','icon_sources'):
            self.assertTrue(config.path_for(key).is_dir(),key)

if __name__=='__main__':unittest.main()
