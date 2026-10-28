"""Actual HTTP routing and additive catalog metadata for the operations UI."""
import http.client
import http.server
import json
import pathlib
import tempfile
import threading
import unittest

from rtd.services.api import API
from rtd.transport.http import handler_for


class AdminWebTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = pathlib.Path(self.temp.name)
        self.api = API(root / 'admin-web.sqlite3')
        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler_for(self.api, root / 'http.log'))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def request(self, path, method='GET'):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_page_and_exact_assets_are_served_without_changing_configuration(self):
        before = self.api.operations.read()
        for path, mime in [('/admin/', 'text/html'), ('/admin', 'text/html'),
                           ('/admin/assets/admin.css', 'text/css'),
                           ('/admin/assets/admin.js', 'text/javascript'),
                           ('/admin/assets/admin-model.mjs', 'text/javascript')]:
            with self.subTest(path=path):
                status, headers, body = self.request(path + '?v=1')
                self.assertEqual(status, 200)
                self.assertTrue(headers['Content-Type'].startswith(mime))
                self.assertEqual(int(headers['Content-Length']), len(body))
                self.assertIn('no-store', headers['Cache-Control'])
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        status, headers, body = self.request('/admin/')
        self.assertIn('卡池与活动管理', body.decode('utf-8'))
        self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
        status, headers, body = self.request('/admin/', 'HEAD')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'')
        self.assertGreater(int(headers['Content-Length']), 0)
        self.assertEqual(self.api.operations.read(), before)

    def test_no_directory_listing_path_traversal_or_game_route_interference(self):
        for path in ('/admin/assets/', '/admin/assets/../../config.py', '/admin/assets/%2e%2e/admin.py',
                     '/admin/config.py', '/admin/assets/unknown.js', '/administer'):
            self.assertEqual(self.request(path)[0], 404, path)
        self.assertEqual(self.request('/health')[0], 200)
        status, _, body = self.request('/admin/v1/config')
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['data']['revision'], 1)

    def test_catalog_exposes_actual_openability_stair_dependencies_and_point_identity(self):
        catalog = self.api.operations.catalog()
        quests = {q['quest_id']: q for q in catalog['quests']}
        self.assertTrue(quests[11000]['event_openable'])
        self.assertFalse(quests[10000]['event_openable'])
        self.assertFalse(quests[20101]['event_openable'])
        self.assertEqual(quests[20000]['next_quest_ids'], sorted(self.api.operations.next_quests(20000)))
        self.assertTrue(quests[20000]['next_quest_ids'])
        self.assertFalse(quests[11000]['event_point_configurable'])
        for q in quests.values():
            self.assertIsInstance(q['sp_event_id'], int)
            self.assertIsInstance(q['event_openable'], bool)
            self.assertIsInstance(q['event_point_configurable'], bool)

    def test_unit_icons_follow_master_g_id_with_png_headers_and_safe_paths(self):
        units={u['unit_id']:u for u in self.api.operations.catalog()['units']}
        self.assertEqual(units[10000]['icon_url'],'/admin/assets/unit-icons/13.png')
        status,headers,body=self.request(units[10000]['icon_url'])
        self.assertEqual(status,200)
        self.assertEqual(headers['Content-Type'],'image/png')
        self.assertTrue(body.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertEqual(int(headers['Content-Length']),len(body))
        self.assertEqual(self.request(units[10000]['icon_url'],'HEAD')[2],b'')
        for path in ('/admin/assets/unit-icons/99999999.png','/admin/assets/unit-icons/../admin.js',
                     '/admin/assets/unit-icons/%2e%2e/admin.js','/admin/assets/unit-icons/13.png/extra'):
            self.assertEqual(self.request(path)[0],404,path)
        for id,unit in units.items():
            expected=self.api.operations.units[id]['g_id']
            self.assertEqual(unit['icon_url'],f'/admin/assets/unit-icons/{expected}.png' if expected else None,id)


if __name__ == '__main__':
    unittest.main()
