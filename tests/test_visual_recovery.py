"""Visual substitution must never silently alter battle data or source tables."""
import copy
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from rtd.masters.catalog import load_catalog
from rtd.services.api import API
from rtd.common import ProtocolError


class VisualRecoveryTest(unittest.TestCase):
    def test_approved_overlay_is_stable_narrow_and_disableable(self):
        original, _ = load_catalog()
        frozen = copy.deepcopy(original)
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {'RTD_VISUAL_RECOVERY': '0'}):
                disabled = API(Path(temp)/'disabled.sqlite3')
            with patch.dict(os.environ, {'RTD_VISUAL_RECOVERY': '1'}):
                enabled = API(Path(temp)/'enabled.sqlite3')
                again = API(Path(temp)/'again.sqlite3')
            self.assertEqual(disabled.masters, original)
            self.assertNotEqual(enabled.masters[20]['hash'], original[20]['hash'])
            self.assertEqual(enabled.masters, again.masters)
            self.assertEqual(original, frozen)
            for kind, table in original.items():
                if kind != 20:
                    self.assertEqual(enabled.masters[kind], table)
                    continue
                for before, after in zip(table['data_list'], enabled.masters[kind]['data_list']):
                    expected = dict(before)
                    if before['id'] == 41221:
                        expected.update(model='ms01_sla_lv1', texture='ms01_sla_lv1_fire')
                    for replacement in enabled.visual_recovery['substitutions']:
                        if replacement['enemy_id']==before['id']:expected.update(replacement['after'])
                    self.assertEqual(after, expected)
            manifest = enabled.visual_recovery
            self.assertIn(11000,manifest['quest_ids'])
            self.assertEqual(manifest['source_hash'], original[20]['hash'])
            self.assertEqual(manifest['derived_hash'], enabled.masters[20]['hash'])
            self.assertEqual(manifest, again.visual_recovery)
            self.assertEqual(len(manifest['payload_sha256']), 64)
            self.assertIsNone(disabled.visual_recovery)
            key=str(uuid.uuid4())
            disabled.call('create_user',dict(ver='2.4.0',uuid=key,unit_no='3',user_name='Disabled'))
            session=disabled.call('auth_user',dict(ver='2.4.0',uuid=key))['session_id']
            with self.assertRaises(ProtocolError) as error:
                disabled.call('order_quest',dict(ver='2.4.0',quest_id='11000'),session)
            self.assertEqual(error.exception.code,8197)
            with self.assertRaises(ProtocolError) as error:
                disabled.call('order_quest',dict(ver='2.4.0',quest_id='11001'),session)
            self.assertEqual(error.exception.code,8197)


if __name__ == '__main__':
    unittest.main()
