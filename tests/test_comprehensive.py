import unittest
import threading
import time
import urllib.request
import urllib.error
import json
import os
import sys
import glob
import sqlite3
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from database import get_db, DB_PATH
from server import ThreadedHTTPServer, PozitronRequestHandler


class TestDatabaseIntegrity(unittest.TestCase):
    """Verifies SQLite database schema, foreign key constraints, and review table behaviors."""

    def test_tables_exist(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        conn.close()

        expected = {'products', 'categories', 'coupons', 'orders', 'reviews', 'users', 'instagram_posts'}
        for table in expected:
            self.assertIn(table, tables, f"Expected table '{table}' not found in database")

    def test_coupons_columns(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(coupons)")
        cols = {row['name'] for row in cursor.fetchall()}
        conn.close()

        for c in ['code', 'discount_type', 'discount_value', 'min_order_usd', 'min_order_try', 'is_active']:
            self.assertIn(c, cols, f"Expected column '{c}' in coupons table")

    def test_review_nullable_product_id(self):
        """General store reviews have product_id=None, which must succeed without FK error."""
        conn = get_db()
        cursor = conn.cursor()
        test_id = 'test_gen_rev_001'
        try:
            cursor.execute('''
                INSERT INTO reviews (id, product_id, user_name, user_avatar, rating, title, comment, verified_purchase, created_at)
                VALUES (?, NULL, 'Test Store Reviewer', 'avatar.png', 5, 'General Title', 'General store review body', 1, datetime('now'))
            ''', (test_id,))
            conn.commit()

            cursor.execute("SELECT product_id, user_name, rating FROM reviews WHERE id = ?", (test_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertIsNone(row['product_id'])
            self.assertEqual(row['user_name'], 'Test Store Reviewer')
        finally:
            cursor.execute("DELETE FROM reviews WHERE id = ?", (test_id,))
            conn.commit()
            conn.close()

    def test_review_product_foreign_key(self):
        """Product-specific review with valid product_id must succeed."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM products LIMIT 1")
        prod_row = cursor.fetchone()
        self.assertIsNotNone(prod_row)
        real_prod_id = prod_row[0]

        test_id = 'test_prod_rev_001'
        try:
            cursor.execute('''
                INSERT INTO reviews (id, product_id, user_name, user_avatar, rating, title, comment, verified_purchase, created_at)
                VALUES (?, ?, 'Test Product Reviewer', 'avatar.png', 5, 'Great Part', 'Works perfectly', 1, datetime('now'))
            ''', (test_id, real_prod_id))
            conn.commit()

            cursor.execute("SELECT product_id, rating FROM reviews WHERE id = ?", (test_id,))
            row = cursor.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row['product_id'], real_prod_id)
        finally:
            cursor.execute("DELETE FROM reviews WHERE id = ?", (test_id,))
            conn.commit()
            conn.close()

    def test_review_invalid_foreign_key_fails(self):
        """With PRAGMA foreign_keys = ON, an invalid non-null product_id must raise an IntegrityError."""
        conn = get_db()
        cursor = conn.cursor()
        with self.assertRaises(sqlite3.IntegrityError):
            cursor.execute('''
                INSERT INTO reviews (id, product_id, user_name, user_avatar, rating, title, comment, verified_purchase, created_at)
                VALUES ('fail_rev', 'totally_invalid_nonexistent_product_id', 'User', 'av.png', 5, 'T', 'C', 1, datetime('now'))
            ''')
            conn.commit()
        conn.close()


class TestServerEndpoints(unittest.TestCase):
    """Verifies all main HTTP API endpoints on an ephemeral server instance."""

    @classmethod
    def setUpClass(cls):
        cls.port = 8990
        cls.httpd = ThreadedHTTPServer(('127.0.0.1', cls.port), PozitronRequestHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def _get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))

    def _post(self, path, data):
        url = f"http://127.0.0.1:{self.port}{path}"
        payload = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as err:
            body = err.read().decode('utf-8')
            try:
                return err.code, json.loads(body)
            except Exception:
                return err.code, {"raw": body}

    def test_get_categories(self):
        code, data = self._get('/api/categories')
        self.assertEqual(code, 200)
        self.assertIn('categories', data)
        categories = data['categories']
        self.assertIsInstance(categories, list)
        self.assertGreater(len(categories), 0)
        first = categories[0]
        self.assertIn('id', first)
        self.assertIn('name_en', first)
        self.assertIn('name_tr', first)

    def test_get_brands(self):
        code, data = self._get('/api/brands')
        self.assertEqual(code, 200)
        self.assertIn('brands', data)
        brands = data['brands']
        self.assertIsInstance(brands, list)
        self.assertGreater(len(brands), 0)

    def test_get_products(self):
        code, data = self._get('/api/products?limit=10')
        self.assertEqual(code, 200)
        self.assertIn('products', data)
        self.assertIn('total', data)
        self.assertGreaterEqual(len(data['products']), 1)

    def test_get_reviews(self):
        code, data = self._get('/api/reviews?limit=10')
        self.assertEqual(code, 200)
        self.assertIn('reviews', data)
        self.assertIsInstance(data['reviews'], list)

    def test_post_general_store_review(self):
        payload = {
            "product_id": "general",
            "user_name": "Automated Test Pilot",
            "rating": 5,
            "title": "Harika Hizmet",
            "comment": "Pozitron siparişim 24 saat içinde teslim edildi, paketleme mükemmel!"
        }
        code, data = self._post('/api/reviews', payload)
        self.assertEqual(code, 201)
        self.assertTrue(data.get('success'))
        rev = data.get('review')
        self.assertIsNotNone(rev)
        self.assertIsNone(rev['product_id'])
        self.assertEqual(rev['user_name'], "Automated Test Pilot")

        # Cleanup
        conn = get_db()
        conn.execute("DELETE FROM reviews WHERE id = ?", (rev['id'],))
        conn.commit()
        conn.close()

    def test_post_product_review_updates_rating(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, rating, review_count FROM products LIMIT 1")
        prod = dict(cursor.fetchone())
        conn.close()

        payload = {
            "product_id": prod['id'],
            "user_name": "Test Drone Pilot",
            "rating": 5,
            "title": "Performans Harika",
            "comment": "Tork ve tepki hızı çok iyi, 6S ile kusursuz uyum."
        }
        code, data = self._post('/api/reviews', payload)
        self.assertEqual(code, 201)
        self.assertTrue(data.get('success'))
        rev = data.get('review')
        self.assertEqual(rev['product_id'], prod['id'])

        # Verify product rating & review_count updated in DB
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT rating, review_count FROM products WHERE id = ?", (prod['id'],))
        updated = dict(cursor.fetchone())
        self.assertGreaterEqual(updated['review_count'], 1)

        # Cleanup test review and restore
        cursor.execute("DELETE FROM reviews WHERE id = ?", (rev['id'],))
        cursor.execute("UPDATE products SET rating = ?, review_count = ? WHERE id = ?", (prod['rating'], prod['review_count'], prod['id']))
        conn.commit()
        conn.close()

    def test_post_review_missing_comment_rejected(self):
        payload = {
            "product_id": "general",
            "user_name": "Pilot",
            "rating": 5,
            "title": "Empty Comment",
            "comment": ""
        }
        code, data = self._post('/api/reviews', payload)
        self.assertEqual(code, 400)
        self.assertIn('error', data)

    def test_coupon_validate_usd_success(self):
        payload = {
            "code": "POZITRON10",
            "subtotal_usd": 100.0,
            "subtotal_try": 0
        }
        code, data = self._post('/api/coupons/validate', payload)
        self.assertEqual(code, 200)
        self.assertTrue(data.get('valid'))
        self.assertEqual(data.get('discount_usd'), 10.0)

    def test_coupon_validate_try_success(self):
        payload = {
            "code": "POZITRON10",
            "subtotal_usd": 0,
            "subtotal_try": 2500.0
        }
        code, data = self._post('/api/coupons/validate', payload)
        self.assertEqual(code, 200)
        self.assertTrue(data.get('valid'))
        self.assertEqual(data.get('discount_try'), 250.0)

    def test_coupon_validate_min_order_failed(self):
        payload = {
            "code": "POZITRON10",
            "subtotal_usd": 10.0,
            "subtotal_try": 200.0
        }
        code, data = self._post('/api/coupons/validate', payload)
        self.assertEqual(code, 400)
        self.assertFalse(data.get('valid'))

    def test_coupon_validate_invalid_code(self):
        payload = {
            "code": "NON_EXISTENT_COUPON_XYZ",
            "subtotal_usd": 100.0,
            "subtotal_try": 3500.0
        }
        code, data = self._post('/api/coupons/validate', payload)
        self.assertEqual(code, 400)
        self.assertFalse(data.get('valid'))

    def test_drone_builder_check(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM products WHERE category_id = 'motors' LIMIT 1")
        motor_row = cursor.fetchone()
        cursor.execute("SELECT id FROM products WHERE category_id = 'batteries' LIMIT 1")
        bat_row = cursor.fetchone()
        conn.close()

        motor_id = motor_row[0] if motor_row else None
        bat_id = bat_row[0] if bat_row else None

        payload = {
            "motor_id": motor_id,
            "battery_id": bat_id
        }
        code, data = self._post('/api/builder/check', payload)
        self.assertEqual(code, 200)
        self.assertIn('compatibility_score', data)
        self.assertIn('is_compatible', data)
        self.assertIn('warnings', data)


class TestFrontendIntegrity(unittest.TestCase):
    """Verifies that quick view is completely absent and review components exist across files."""

    def test_index_html_quick_view_removed(self):
        with open(os.path.join(BASE_DIR, 'index.html'), 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertNotIn('card-quick-view-btn', content)
        self.assertNotIn('product-modal-backdrop', content)
        self.assertNotIn('openProductModal', content)

    def test_index_html_reviews_components_present(self):
        with open(os.path.join(BASE_DIR, 'index.html'), 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('id="btn-open-comment-modal"', content)
        self.assertIn('id="comment-modal-backdrop"', content)
        self.assertIn('id="comment-product-select"', content)
        self.assertIn('id="star-rating-picker"', content)

    def test_app_js_quick_view_removed(self):
        with open(os.path.join(BASE_DIR, 'app.js'), 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertNotIn('card-quick-view-btn', content)
        # Check that reviews are not deleted with localStorage filter bug
        self.assertNotIn("r.id && !String(r.id).startsWith('rev_')", content)

    def test_styles_css_quick_view_removed(self):
        with open(os.path.join(BASE_DIR, 'styles.css'), 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertNotIn('.card-quick-view-btn', content)

    def test_product_pages_count_and_integrity(self):
        prod_dir = os.path.join(BASE_DIR, 'products')
        files = glob.glob(os.path.join(prod_dir, '*.html'))
        self.assertGreaterEqual(len(files), 500, f"Expected at least 500 product HTML pages, found {len(files)}")

        # Sample 20 product pages and verify review widgets & no quick view
        sampled = random.sample(files, min(20, len(files)))
        for ppath in sampled:
            fname = os.path.basename(ppath)
            with open(ppath, 'r', encoding='utf-8') as f:
                c = f.read()

            self.assertNotIn('card-quick-view-btn', c, f"Found quick view btn in {fname}")
            self.assertNotIn('product-modal-backdrop', c, f"Found quick view modal in {fname}")
            self.assertIn('id="pdp-reviews-section"', c, f"Missing reviews section in {fname}")
            self.assertIn('id="pdp-review-modal"', c, f"Missing review modal in {fname}")
            self.assertIn('openProductReviewModal', c, f"Missing openProductReviewModal JS in {fname}")
            self.assertIn('submitProductReview', c, f"Missing submitProductReview JS in {fname}")


if __name__ == '__main__':
    unittest.main()
