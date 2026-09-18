import unittest
import threading
import time
import urllib.request
import json
import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server import ThreadedHTTPServer, PozitronRequestHandler
from database import get_db, set_setting, get_setting
from export_data import export_static_data

class TestCurrencyAndAdminPanel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.orig_rate = get_setting('usd_rate', 47.0)
        cls.port = 8895
        cls.httpd = ThreadedHTTPServer(('127.0.0.1', cls.port), PozitronRequestHandler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        # Restore original currency rate
        set_setting('usd_rate', cls.orig_rate)
        # Restore product prices to original rate
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE products SET price_try = ROUND(price_usd * ?, 2)", (cls.orig_rate,))
        # Remove test user and test order if any
        cursor.execute("DELETE FROM orders WHERE id = 'test_order_999'")
        cursor.execute("DELETE FROM users WHERE LOWER(email) = 'new_pilot@pozitron.test'")
        conn.commit()
        conn.close()
        export_static_data()

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
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode('utf-8'))

    def test_01_currency_rate_endpoints(self):
        # 1. Test public settings and currency-rate endpoints
        code, settings = self._get('/api/settings')
        self.assertIn(code, (200, 201))
        self.assertIn('usd_rate', settings)

        code, curr = self._get('/api/currency-rate')
        self.assertIn(code, (200, 201))
        self.assertIn('usd_rate', curr)
        self.assertEqual(curr['currency'], 'TRY')

    def test_02_currency_sync_persistence(self):
        # 2. Update currency to 50.0 TRY
        code, sync_res = self._post('/api/admin/currency-sync', {'usd_rate': 50.0, 'category_id': 'all'})
        self.assertIn(code, (200, 201))
        self.assertTrue(sync_res.get('success'))
        self.assertEqual(float(sync_res.get('usd_rate')), 50.0)

        # Verify /api/settings returns 50.0
        code, settings = self._get('/api/settings')
        self.assertIn(code, (200, 201))
        self.assertEqual(float(settings['usd_rate']), 50.0)

        # Verify /api/currency-rate returns 50.0
        code, curr = self._get('/api/currency-rate')
        self.assertIn(code, (200, 201))
        self.assertEqual(float(curr['usd_rate']), 50.0)

        # Verify in database directly
        db_rate = get_setting('usd_rate')
        self.assertEqual(float(db_rate), 50.0)

        # Verify products in DB have price_try == round(price_usd * 50.0, 2)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT price_usd, price_try FROM products WHERE price_usd > 0 LIMIT 10")
        rows = cursor.fetchall()
        self.assertGreater(len(rows), 0)
        for r in rows:
            expected_try = round(r['price_usd'] * 50.0, 2)
            self.assertAlmostEqual(r['price_try'], expected_try, places=2)
        conn.close()

        # Verify exported data/settings.json exists and has 50.0
        settings_file = os.path.join(BASE_DIR, 'data', 'settings.json')
        self.assertTrue(os.path.exists(settings_file))
        with open(settings_file, 'r', encoding='utf-8') as f:
            saved_json = json.load(f)
            self.assertEqual(float(saved_json.get('usd_rate')), 50.0)

    def test_03_settings_update_bank_info(self):
        # Test updating site settings (bank details)
        payload = {
            'bank_owner': 'Pozitron FPV Drone Teknolojileri',
            'bank_iban': 'TR990006200000012345678901',
            'bank_name': 'Garanti BBVA Ataşehir'
        }
        code, res = self._post('/api/settings', payload)
        self.assertIn(code, (200, 201))
        self.assertTrue(res.get('success'))

        # Verify retrieved settings
        code, settings = self._get('/api/settings')
        self.assertIn(code, (200, 201))
        self.assertEqual(settings.get('bank_owner'), payload['bank_owner'])
        self.assertEqual(settings.get('bank_iban'), payload['bank_iban'])
        self.assertEqual(settings.get('bank_name'), payload['bank_name'])

    def test_04_order_status_update_and_lookup(self):
        # Create a test order
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM orders WHERE id = 'test_order_999'")
        cursor.execute('''
            INSERT INTO orders (
                id, order_number, customer_name, customer_email, customer_phone,
                shipping_address, city, country, items_json, subtotal_usd, subtotal_try,
                total_usd, total_try, currency, payment_method, payment_status,
                order_status, tracking_number, created_at
            ) VALUES (
                'test_order_999', 'PZT-TEST-999', 'Test Pilot Ali', 'ali@example.com', '05321112233',
                'Kadikoy / Istanbul', 'Istanbul', 'Turkey', '[]', 100.0, 5000.0,
                100.0, 5000.0, 'TRY', 'iyzico', 'PAID',
                'CONFIRMED', 'TRK-INIT', datetime('now')
            )
        ''')
        conn.commit()
        conn.close()

        # Update order status via /api/admin/orders/update
        code, update_res = self._post('/api/admin/orders/update', {
            'id': 'test_order_999',
            'status': 'SHIPPED',
            'tracking_number': 'TRK-999-YURTICI'
        })
        self.assertIn(code, (200, 201))
        self.assertTrue(update_res.get('success'))
        self.assertTrue(update_res.get('updated'))

        # Query order lookup endpoint /api/orders/test_order_999
        code, ord_res = self._get('/api/orders/test_order_999')
        self.assertIn(code, (200, 201))
        order = ord_res.get('order')
        self.assertIsNotNone(order)
        self.assertEqual(order.get('status'), 'SHIPPED')
        self.assertEqual(order.get('order_status'), 'SHIPPED')
        self.assertEqual(order.get('tracking_number'), 'TRK-999-YURTICI')

        # Query /api/orders?email=ali@example.com
        code, list_res = self._get('/api/orders?email=ali@example.com')
        self.assertIn(code, (200, 201))
        orders = list_res.get('orders', [])
        matching = [o for o in orders if o.get('id') == 'test_order_999']
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].get('status'), 'SHIPPED')

    def test_05_admin_user_creation(self):
        # Create user via /api/admin/users/create
        code, user_res = self._post('/api/admin/users/create', {
            'email': 'new_pilot@pozitron.test',
            'full_name': 'Yeni FPV Pilotu',
            'role': 'customer',
            'phone': '05550001122',
            'city': 'Izmir'
        })
        self.assertIn(code, (200, 201))
        self.assertTrue(user_res.get('success'))
        self.assertIn('user', user_res)
        self.assertEqual(user_res['user']['email'], 'new_pilot@pozitron.test')

        # Verify in database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT email, full_name, role, city FROM users WHERE email = 'new_pilot@pozitron.test'")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row['role'], 'customer')
        self.assertEqual(row['city'], 'Izmir')
        conn.close()

if __name__ == '__main__':
    unittest.main()
