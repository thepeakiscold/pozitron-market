import unittest
import threading
import time
import urllib.request
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server import ThreadedHTTPServer, PozitronRequestHandler

class TestServerInstagramAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from instagram_agent.db import update_agent_config, get_agent_config
        cls.orig_config = get_agent_config()
        update_agent_config({'dry_run_mode': 1})

        cls.port = 8899
        cls.httpd = ThreadedHTTPServer(('127.0.0.1', cls.port), PozitronRequestHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        from instagram_agent.db import update_agent_config
        cls.httpd.shutdown()
        cls.httpd.server_close()
        if hasattr(cls, 'orig_config') and cls.orig_config:
            update_agent_config({'dry_run_mode': cls.orig_config.get('dry_run_mode', 1)})

    def _get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))

    def _post(self, path, data):
        url = f"http://127.0.0.1:{self.port}{path}"
        payload = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))

    def test_get_status(self):
        code, data = self._get('/api/instagram/status')
        self.assertEqual(code, 200)
        self.assertIn('total_posts', data)
        self.assertIn('is_autonomous_enabled', data)

    def test_get_config(self):
        code, data = self._get('/api/instagram/config')
        self.assertEqual(code, 200)
        self.assertIn('posting_frequency_hours', data)
        self.assertIn('public_base_url', data)

    def test_update_config(self):
        code, data = self._post('/api/instagram/config', {'posting_frequency_hours': 6, 'dry_run_mode': 1})
        self.assertEqual(code, 200)
        self.assertTrue(data.get('success'))
        self.assertEqual(data['config']['posting_frequency_hours'], 6)

    def test_generate_and_publish_flow(self):
        # Generate
        code, gen_data = self._post('/api/instagram/generate', {'content_type': 'tool_showcase'})
        self.assertEqual(code, 200)
        self.assertTrue(gen_data.get('success'))
        post = gen_data.get('post')
        self.assertIsNotNone(post)
        post_id = post['id']

        # Publish
        code, pub_data = self._post('/api/instagram/publish', {'id': post_id})
        self.assertEqual(code, 200)
        self.assertTrue(pub_data.get('success'))
        self.assertEqual(pub_data.get('mode'), 'dry_run')

        # Check in list
        code, list_data = self._get('/api/instagram/posts?limit=10')
        self.assertEqual(code, 200)
        posts = list_data.get('posts', [])
        found = any(p['id'] == post_id for p in posts)
        self.assertTrue(found)

if __name__ == '__main__':
    unittest.main()
