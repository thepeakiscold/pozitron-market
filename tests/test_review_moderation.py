import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import server


class ReviewModerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'reviews.db')
        with sqlite3.connect(database.DB_PATH) as source, sqlite3.connect(self.db) as target:
            source.backup(target)
        self.db_patch = patch.object(database, 'DB_PATH', self.db)
        self.db_patch.start()
        self.handler = object.__new__(server.PozitronRequestHandler)
        self.responses = []
        self.handler.send_json = lambda status, payload: self.responses.append((status, payload))
        self.handler.get_current_user = lambda: {'role': 'admin'}
        with database.get_db() as conn:
            self.product = conn.execute('SELECT id FROM products LIMIT 1').fetchone()[0]
            conn.execute('DELETE FROM reviews')
            for rid, rating, product in [('mod-one', 1, self.product), ('mod-two', 5, self.product), ('mod-store', 3, None)]:
                conn.execute('INSERT INTO reviews (id, product_id, user_name, rating, comment, created_at) VALUES (?, ?, ?, ?, ?, ?)',
                             (rid, product, 'Test Writer', rating, '<script>untrusted</script>', '2026-10-20T10:00:00'))

    def tearDown(self):
        self.db_patch.stop()
        self.tmp.cleanup()

    def post(self, action, rid):
        self.handler.handle_api_post('/api/admin/reviews/' + action, {'id': rid})
        return self.responses[-1]

    def get(self, path, query=None):
        self.handler.handle_api_get(path, query or {})
        return self.responses[-1]

    def test_admin_can_search_and_paginate_store_and_product_reviews(self):
        status, data = self.get('/api/admin/reviews', {'search': ['Test Writer'], 'limit': ['2'], 'page': ['1']})
        self.assertEqual(status, 200)
        self.assertEqual(data['total'], 3)
        self.assertEqual(len(data['reviews']), 2)
        _, second = self.get('/api/admin/reviews', {'limit': ['2'], 'page': ['2']})
        self.assertEqual(len(second['reviews']), 1)

    def test_deleted_review_leaves_public_lists_and_updates_product_rating(self):
        self.assertEqual(self.post('delete', 'mod-one')[0], 200)
        _, public = self.get('/api/reviews')
        self.assertNotIn('mod-one', [r['id'] for r in public['reviews']])
        _, trash = self.get('/api/admin/reviews', {'status': ['deleted']})
        self.assertEqual([r['id'] for r in trash['reviews']], ['mod-one'])
        with database.get_db() as conn:
            row = conn.execute('SELECT rating, review_count FROM products WHERE id = ?', (self.product,)).fetchone()
            self.assertEqual(tuple(row), (5.0, 1))
        self.assertEqual(self.post('restore', 'mod-one')[0], 200)
        with database.get_db() as conn:
            row = conn.execute('SELECT rating, review_count FROM products WHERE id = ?', (self.product,)).fetchone()
            self.assertEqual(tuple(row), (3.0, 2))

    def test_last_review_removal_resets_count_and_general_review_can_be_removed(self):
        self.post('delete', 'mod-one')
        self.post('delete', 'mod-two')
        self.post('delete', 'mod-store')
        _, public = self.get('/api/reviews')
        self.assertEqual(public['reviews'], [])
        with database.get_db() as conn:
            row = conn.execute('SELECT rating, review_count FROM products WHERE id = ?', (self.product,)).fetchone()
            self.assertEqual(tuple(row), (0.0, 0))

    def test_missing_review_and_invalid_page_return_errors(self):
        self.assertEqual(self.post('delete', 'missing')[0], 404)
        self.assertEqual(self.post('delete', '')[0], 400)
        self.assertEqual(self.get('/api/admin/reviews', {'page': ['bad']})[0], 400)

    def test_anonymous_and_regular_users_cannot_list_delete_or_restore(self):
        for identity in (None, {'role': 'user'}):
            self.handler.get_current_user = lambda identity=identity: identity
            self.assertEqual(self.get('/api/admin/reviews')[0], 401)
            self.assertEqual(self.post('delete', 'mod-one')[0], 401)
            self.assertEqual(self.post('restore', 'mod-one')[0], 401)
        with database.get_db() as conn:
            self.assertIsNone(conn.execute("SELECT deleted_at FROM reviews WHERE id = 'mod-one'").fetchone()[0])


if __name__ == '__main__':
    unittest.main()
