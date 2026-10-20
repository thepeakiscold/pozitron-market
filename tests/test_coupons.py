import os
import sys
import json
import time
import threading
import urllib.request
import urllib.error
import unittest
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
import coupons as coupon_service
from database import get_db


class TestCouponService(unittest.TestCase):
    """Domain-level guarantees for the coupon system."""

    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.created = []

    @classmethod
    def tearDownClass(cls):
        conn = get_db()
        for code in cls.created:
            conn.execute("DELETE FROM coupon_redemptions WHERE coupon_code = ?", (code,))
            conn.execute("DELETE FROM coupon_logs WHERE coupon_code = ?", (code,))
            conn.execute("DELETE FROM coupons WHERE code = ?", (code,))
        conn.commit()
        conn.close()

    def _make(self, code, **kw):
        self.created.append(code)
        return coupon_service.create_coupon(code, source='test', **kw)

    def test_expiry_window_and_auto_deactivation(self):
        code = 'TSTEXP1'
        self._make(code, discount_type='percent', discount_value=10,
                   expires_at=(datetime.now() + timedelta(seconds=1)).isoformat())
        self.assertTrue(coupon_service.validate_coupon(code, subtotal_try=2000, user_id='u1')['valid'])
        # Move the window into the past and let the sweeper disable it.
        coupon_service.update_coupon(code, expires_at=(datetime.now() - timedelta(minutes=1)).isoformat())
        coupon_service.expire_coupons()
        c = coupon_service.get_coupon(code)
        self.assertEqual(c['is_active'], 0)
        res = coupon_service.validate_coupon(code, subtotal_try=2000, user_id='u1')
        self.assertFalse(res['valid'])

    def test_min_order_blocks_small_baskets(self):
        code = 'TSTMIN1'
        self._make(code, discount_type='fixed', discount_value=500, min_order_try=5000)
        self.assertFalse(coupon_service.validate_coupon(code, subtotal_try=1000, user_id='u1')['valid'])
        self.assertTrue(coupon_service.validate_coupon(code, subtotal_try=6000, user_id='u1')['valid'])

    def test_fixed_discount_is_try_amount(self):
        code = 'TSTFIX1'
        self._make(code, discount_type='fixed', discount_value=500, min_order_try=5000)
        res = coupon_service.validate_coupon(code, subtotal_try=7000, user_id='u1')
        self.assertTrue(res['valid'])
        self.assertEqual(res['discount_try'], 500.0)

    def test_single_use_per_account(self):
        code = 'TSTONCE1'
        self._make(code, discount_type='percent', discount_value=10)
        conn = get_db()
        ok, reason = coupon_service.redeem_coupon(conn, code, user_id='acc-1', order_id='o1',
                                                  order_number='PZT-1', discount_try=100)
        conn.commit()
        self.assertTrue(ok, reason)
        ok2, reason2 = coupon_service.redeem_coupon(conn, code, user_id='acc-1', order_id='o2',
                                                    order_number='PZT-2', discount_try=100)
        conn.rollback()
        self.assertFalse(ok2)
        self.assertEqual(reason2, 'already_used')
        # A different account can still use it.
        ok3, _ = coupon_service.redeem_coupon(conn, code, user_id='acc-2', order_id='o3',
                                              order_number='PZT-3', discount_try=100)
        conn.commit()
        conn.close()
        self.assertTrue(ok3)

    def test_per_email_single_use_for_guests(self):
        code = 'TSTMAIL1'
        self._make(code, discount_type='percent', discount_value=10)
        conn = get_db()
        ok, _ = coupon_service.redeem_coupon(conn, code, email='pilot@example.com',
                                             order_id='o1', order_number='PZT-1', discount_try=10)
        conn.commit()
        self.assertTrue(ok)
        ok2, reason2 = coupon_service.redeem_coupon(conn, code, email='PILOT@example.com',
                                                    order_id='o2', order_number='PZT-2', discount_try=10)
        conn.rollback()
        conn.close()
        self.assertFalse(ok2)
        self.assertEqual(reason2, 'already_used')

    def test_global_max_uses(self):
        code = 'TSTMAX1'
        self._make(code, discount_type='percent', discount_value=10, max_uses=1)
        conn = get_db()
        ok, _ = coupon_service.redeem_coupon(conn, code, user_id='a', order_id='o1', order_number='P1', discount_try=10)
        conn.commit()
        self.assertTrue(ok)
        self.assertFalse(coupon_service.validate_coupon(code, subtotal_try=9000, user_id='b')['valid'])
        conn.close()

    def test_weekly_deal_is_one_day_and_active(self):
        deal = coupon_service.create_weekly_deal()
        self.assertIsNotNone(deal)
        self.created.append(deal['code'])
        self.assertEqual(deal['source'], 'weekly_deal')
        self.assertEqual(deal['per_user_limit'], 1)
        start = datetime.fromisoformat(deal['starts_at'])
        end = datetime.fromisoformat(deal['expires_at'])
        self.assertAlmostEqual((end - start).total_seconds(), 24 * 3600, delta=5)
        active = coupon_service.get_active_deal()
        self.assertIsNotNone(active)
        self.assertEqual(active['code'], deal['code'])

    def test_logs_recorded(self):
        code = 'TSTLOG1'
        self._make(code, discount_type='percent', discount_value=5)
        conn = get_db()
        coupon_service.redeem_coupon(conn, code, user_id='log-user', order_id='o', order_number='P', discount_try=5)
        conn.commit()
        conn.close()
        actions = [l['action'] for l in coupon_service.get_logs(code)]
        self.assertIn('created', actions)
        self.assertIn('redeemed', actions)


class TestCouponEndpoints(unittest.TestCase):
    """End-to-end HTTP checks, including the once-per-account checkout rule."""

    @classmethod
    def setUpClass(cls):
        from server import ThreadedHTTPServer, PozitronRequestHandler
        database.init_db()
        cls.port = 8993
        cls.httpd = ThreadedHTTPServer(('127.0.0.1', cls.port), PozitronRequestHandler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)
        cls.code = 'TSTHTTP1'
        try:
            coupon_service.create_coupon(cls.code, 'percent', 10, min_order_try=0, source='test')
        except ValueError:
            pass

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        conn = get_db()
        conn.execute("DELETE FROM coupon_redemptions WHERE coupon_code = ?", (cls.code,))
        conn.execute("DELETE FROM coupon_logs WHERE coupon_code = ?", (cls.code,))
        conn.execute("DELETE FROM coupons WHERE code = ?", (cls.code,))
        conn.commit()
        conn.close()

    def _post(self, path, data, headers=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        payload = json.dumps(data).encode('utf-8')
        h = {'Content-Type': 'application/json'}
        h.update(headers or {})
        req = urllib.request.Request(url, data=payload, headers=h, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as err:
            body = err.read().decode('utf-8')
            try:
                return err.code, json.loads(body)
            except Exception:
                return err.code, {"raw": body}

    def _get(self, path, headers=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return resp.status, json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read().decode('utf-8'))

    def test_validate_guest_success(self):
        code, data = self._post('/api/coupons/validate',
                                {"code": self.code, "subtotal_usd": 50, "subtotal_try": 1775})
        self.assertEqual(code, 200)
        self.assertTrue(data.get('valid'))

    def test_active_deal_endpoint_public(self):
        code, data = self._get('/api/coupons/active')
        self.assertEqual(code, 200)
        self.assertIn('active', data)

    def test_validate_invalid(self):
        code, data = self._post('/api/coupons/validate',
                                {"code": "NOPE_XYZ", "subtotal_usd": 50, "subtotal_try": 1775})
        self.assertEqual(code, 400)
        self.assertFalse(data.get('valid'))

    def test_checkout_coupon_single_use_per_account(self):
        conn = get_db()
        row = conn.execute("SELECT id, stock FROM products LIMIT 1").fetchone()
        conn.close()
        if not row:
            self.skipTest("no products")
        pid, orig_stock = row['id'], row['stock']

        base = {
            "items": [{"id": pid, "quantity": 1}],
            "customer_name": "Test Pilot",
            "customer_email": "coupon_user@example.com",
            "customer_phone": "05551112233",
            "shipping_address": "Test Mah. 1",
            "city": "Istanbul",
            "country": "Turkey",
            "currency": "TRY",
            "payment_method": "havale",
            "card_number": "4242424242424242",
            "card_holder": "Test Pilot",
            "card_expiry": "12/30",
            "card_cvv": "123",
            "coupon_code": self.code,
            "user_id": "test-coupon-acc",
        }
        c1, d1 = self._post('/api/payment/process', base)
        self.assertEqual(c1, 200, d1)
        self.assertTrue(d1.get('success'))
        self.assertGreater(d1.get('discount_try', 0), 0)

        c2, d2 = self._post('/api/payment/process', base)
        self.assertEqual(c2, 400)
        self.assertTrue(d2.get('coupon_invalid'))
        self.assertEqual(d2.get('reason'), 'already_used')

        # restore stock consumed by the successful test order
        conn = get_db()
        conn.execute("UPDATE products SET stock = ? WHERE id = ?", (orig_stock, pid))
        conn.commit()
        conn.close()

    def test_admin_create_and_list(self):
        headers = {'X-Admin-Key': 'pzt_adm_sec_9941a87b32c'}
        code, data = self._post('/api/admin/coupons/create', {
            "code": "TSTADMIN1", "discount_type": "fixed", "discount_value": 300,
            "min_order_try": 3000, "valid_hours": 24, "description_tr": "test"
        }, headers=headers)
        self.assertEqual(code, 200, data)
        self.assertTrue(data.get('success'))
        sc, sd = self._get('/api/admin/coupons', headers=headers)
        self.assertEqual(sc, 200)
        self.assertTrue(any(c['code'] == 'TSTADMIN1' for c in sd.get('coupons', [])))
        # cleanup
        conn = get_db()
        conn.execute("DELETE FROM coupon_logs WHERE coupon_code = 'TSTADMIN1'")
        conn.execute("DELETE FROM coupons WHERE code = 'TSTADMIN1'")
        conn.commit()
        conn.close()

    def test_admin_endpoints_require_auth_in_production(self):
        # Without admin headers and with proxied header the request must be rejected.
        code, data = self._post('/api/admin/coupons/create',
                                {"code": "NOAUTH1", "discount_type": "percent", "discount_value": 5},
                                headers={'X-Forwarded-For': '10.0.0.1'})
        self.assertEqual(code, 401)


if __name__ == '__main__':
    unittest.main()
