import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import product_quality
import server

ROOT = Path(__file__).resolve().parents[1]


class ProductQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.temp.name) / 'quality.db')
        with sqlite3.connect(database.DB_PATH) as src, sqlite3.connect(self.db) as dst:
            src.backup(dst)
        self.db_patch = patch.object(database, 'DB_PATH', self.db)
        self.db_patch.start()
        with database.get_db() as conn:
            conn.execute('DELETE FROM product_quality_checks')
            self.product = dict(conn.execute('SELECT * FROM products ORDER BY sku LIMIT 1').fetchone())
        self.handler = object.__new__(server.PozitronRequestHandler)
        self.handler.get_current_user = lambda: {'role': 'admin', 'email': 'test@example.invalid'}
        self.replies = []
        self.handler.send_json = lambda status, data: self.replies.append((status, data))

    def tearDown(self):
        self.db_patch.stop()
        self.temp.cleanup()

    def record(self, status='checked', digest=None):
        with database.get_db() as conn:
            return product_quality.record_check(conn, self.product['id'], status, reviewer='test-agent',
                notes='Checked against source', sources=['https://example.invalid/specification'],
                expected_hash=digest or product_quality.content_hash(self.product))

    def test_check_is_persistent_and_shared_with_admin_list(self):
        self.record()
        self.handler.handle_api_get('/api/admin/products', {'q': [self.product['id']]})
        status, result = self.replies[-1]
        self.assertEqual(status, 200)
        self.assertTrue(result['products'][0]['quality_checked'])
        self.assertEqual(result['products'][0]['quality_reviewer'], 'test-agent')

    def test_spec_changes_reset_check_but_stock_changes_do_not(self):
        self.record()
        with database.get_db() as conn:
            conn.execute('UPDATE products SET stock=stock+1 WHERE id=?', (self.product['id'],))
            row = conn.execute('SELECT * FROM products WHERE id=?', (self.product['id'],)).fetchone()
            self.assertTrue(product_quality.states(conn, [row])[row['id']]['quality_checked'])
            conn.execute("UPDATE products SET description_tr=description_tr || ' changed' WHERE id=?", (self.product['id'],))
            row = conn.execute('SELECT * FROM products WHERE id=?', (self.product['id'],)).fetchone()
            self.assertFalse(product_quality.states(conn, [row])[row['id']]['quality_checked'])
            with self.assertRaises(ValueError):
                product_quality.record_check(conn, row['id'], 'checked', reviewer='test', expected_hash=product_quality.content_hash(self.product))

    def test_manual_toggle_and_rejected_non_boolean(self):
        for checked in (True, False):
            self.handler.handle_api_post('/api/admin/products/check', {
                'id': self.product['id'], 'checked': checked, 'content_hash': product_quality.content_hash(self.product)})
            self.assertEqual(self.replies[-1][0], 200)
            self.assertEqual(self.replies[-1][1]['quality_checked'], checked)
        self.handler.handle_api_post('/api/admin/products/check', {'id': self.product['id'], 'checked': 'false'})
        self.assertEqual(self.replies[-1][0], 400)

    def test_only_admin_can_toggle(self):
        for identity in (None, {'role': 'customer'}):
            self.handler.get_current_user = lambda identity=identity: identity
            self.handler.handle_api_post('/api/admin/products/check', {'id': self.product['id'], 'checked': True})
            self.assertEqual(self.replies[-1][0], 401)

    def test_public_product_list_does_not_apply_review_deletion_column(self):
        self.handler.handle_api_get('/api/products', {'q': [self.product['sku']]})
        self.assertEqual(self.replies[-1][0], 200)
        self.assertGreater(len(self.replies[-1][1]['products']), 0)

    def test_cli_queue_and_report_update_same_state(self):
        env = dict(os.environ, DATABASE_PATH=self.db)
        def cli(*args):
            return subprocess.run([sys.executable, str(ROOT / 'scripts/product_review.py'), *args],
                                  env=env, capture_output=True, text=True)
        queue = cli('next', '--limit', '1')
        self.assertEqual(queue.returncode, 0, queue.stderr)
        item = json.loads(queue.stdout)[0]
        report = {'product_id': item['id'], 'content_hash': item['quality_hash'], 'status': 'checked',
                  'reviewer': 'test-agent', 'notes': 'Verified specification', 'sources': []}
        path = Path(self.temp.name) / 'report.json'
        path.write_text(json.dumps(report))
        self.assertEqual(cli('record', '--report', str(path)).returncode, 1)
        report['sources'] = ['https://example.invalid/specification']
        path.write_text(json.dumps(report))
        result = cli('record', '--report', str(path))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['quality_checked'])
        self.assertEqual(json.loads(cli('stats').stdout)['checked'], 1)


if __name__ == '__main__':
    unittest.main()
