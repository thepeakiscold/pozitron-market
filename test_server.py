import unittest
import threading
import time
import urllib.request
import json
from server import run_server, PORT
from database import init_db

class TestPozitronAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        # Start server in background thread
        cls.server_thread = threading.Thread(target=run_server, daemon=True)
        cls.server_thread.start()
        time.sleep(1) # wait for server startup

    def get(self, path):
        req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}")
        with urllib.request.urlopen(req) as response:
            return response.getcode(), json.loads(response.read().decode('utf-8'))

    def post(self, path, payload):
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            f"http://127.0.0.1:{PORT}{path}",
            data=data,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            return response.getcode(), json.loads(response.read().decode('utf-8'))

    def test_01_categories(self):
        status, data = self.get("/api/categories")
        self.assertEqual(status, 200)
        self.assertIn("categories", data)
        self.assertEqual(len(data["categories"]), 13)

    def test_02_products_total(self):
        status, data = self.get("/api/products?limit=10")
        self.assertEqual(status, 200)
        self.assertEqual(data["total"], 500)
        self.assertEqual(len(data["products"]), 10)

    def test_03_search_products(self):
        status, data = self.get("/api/products?q=SpeedyBee")
        self.assertEqual(status, 200)
        self.assertGreater(data["total"], 0)

    def test_04_manual_auth_register_and_login(self):
        email = f"pilot_test_{int(time.time())}@pozitron.com"
        reg_payload = {
            "email": email,
            "password": "PilotPassword2026!",
            "full_name": "Test Pilot Alpha",
            "phone": "+905550001122",
            "address": "Ataturk Caddesi No:10",
            "city": "Ankara"
        }
        status, reg_data = self.post("/api/auth/register", reg_payload)
        self.assertEqual(status, 201)
        self.assertTrue(reg_data["success"])
        self.assertEqual(reg_data["user"]["email"], email)

        # Login
        login_payload = {
            "email": email,
            "password": "PilotPassword2026!"
        }
        l_status, l_data = self.post("/api/auth/login", login_payload)
        self.assertEqual(l_status, 200)
        self.assertTrue(l_data["success"])

    def test_05_google_auth(self):
        g_payload = {
            "email": "fpv.google.user@gmail.com",
            "full_name": "Google FPV Tester",
            "avatar_url": "https://lh3.googleusercontent.com/a/sample-photo"
        }
        status, data = self.post("/api/auth/google", g_payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertEqual(data["user"]["provider"], "gmail")

    def test_06_coupon_validation(self):
        payload = {
            "code": "POZITRON10",
            "subtotal_usd": 100.0,
            "subtotal_try": 3550.0
        }
        status, data = self.post("/api/coupons/validate", payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["valid"])
        self.assertEqual(data["discount_usd"], 10.0)

    def test_07_payment_checkout(self):
        # Fetch a real product
        _, p_data = self.get("/api/products?limit=2")
        prod = p_data["products"][0]

        payment_payload = {
            "customer_name": "Eyup Yilmaz",
            "customer_email": "eyup@pozitron.com",
            "customer_phone": "+905551234567",
            "shipping_address": "Teknokent Blok B No: 12",
            "city": "Istanbul",
            "country": "Turkey",
            "currency": "USD",
            "payment_method": "credit_card",
            "card_number": "4532 0123 4567 8910",
            "card_holder": "EYUP YILMAZ",
            "card_expiry": "12/28",
            "card_cvv": "321",
            "coupon_code": "POZITRON10",
            "items": [
                {"id": prod["id"], "quantity": 2}
            ]
        }
        status, data = self.post("/api/payment/process", payment_payload)
        self.assertEqual(status, 200)
        self.assertTrue(data["success"])
        self.assertIn("order_number", data)
        self.assertEqual(data["payment_status"], "PAID")

        # Verify order lookup
        order_num = data["order_number"]
        o_status, o_data = self.get(f"/api/orders/{order_num}")
        self.assertEqual(o_status, 200)
        self.assertEqual(o_data["order"]["order_number"], order_num)

    def test_08_admin_stats(self):
        status, data = self.get("/api/admin/stats")
        self.assertEqual(status, 200)
        self.assertIn("total_products", data)
        self.assertIn("total_stock", data)
        self.assertIn("low_stock_count", data)
        self.assertIn("out_of_stock_count", data)
        self.assertIn("total_val_usd", data)
        self.assertIn("total_val_try", data)
        self.assertGreater(data["total_products"], 0)
        self.assertGreater(data["total_stock"], 0)

    def test_09_admin_products_filter_and_search(self):
        # Filter all
        status, data = self.get("/api/admin/products?limit=10")
        self.assertEqual(status, 200)
        self.assertEqual(len(data["products"]), 10)
        self.assertIn("total", data)

        # Filter by low_stock or in_stock
        s_status, s_data = self.get("/api/admin/products?stock_status=in_stock&limit=5")
        self.assertEqual(s_status, 200)
        for p in s_data["products"]:
            self.assertGreater(p["stock"], 0)

    def test_10_admin_update_product_stock_and_price(self):
        # Fetch first product
        _, p_data = self.get("/api/admin/products?limit=1")
        prod = p_data["products"][0]
        pid = prod["id"]
        orig_stock = prod["stock"]

        # Update stock to 88 and price_usd to 199.99
        up_payload = {
            "id": pid,
            "stock": 88,
            "price_usd": 199.99,
            "price_try": 9399.53,
            "discount_pct": 10,
            "badge": "RESTOCKED"
        }
        status, res = self.post("/api/admin/products/update", up_payload)
        self.assertEqual(status, 200)
        self.assertTrue(res["success"])
        self.assertEqual(res["product"]["stock"], 88)
        self.assertEqual(res["product"]["price_usd"], 199.99)
        self.assertEqual(res["product"]["badge"], "RESTOCKED")

    def test_11_admin_bulk_operations(self):
        # Fetch 2 products
        _, p_data = self.get("/api/admin/products?limit=2")
        ids = [p["id"] for p in p_data["products"]]

        # Bulk stock increment (+15)
        bulk_payload = {
            "product_ids": ids,
            "action": "stock_increment",
            "value": 15
        }
        status, res = self.post("/api/admin/products/bulk", bulk_payload)
        self.assertEqual(status, 200)
        self.assertTrue(res["success"])
        self.assertEqual(res["updated_count"], 2)

        # Bulk price percent (+5%)
        bulk_price_payload = {
            "product_ids": ids,
            "action": "price_percent",
            "value": 5
        }
        status, res = self.post("/api/admin/products/bulk", bulk_price_payload)
        self.assertEqual(status, 200)
        self.assertTrue(res["success"])

    def test_12_admin_create_and_delete_product(self):
        new_item = {
            "name_en": "Pozitron Hyperion 6S 2306 Motor",
            "name_tr": "Pozitron Hyperion 6S 2306 FPV Motoru",
            "category_id": "motors",
            "brand": "Pozitron",
            "price_usd": 24.50,
            "price_try": 1150.00,
            "stock": 40,
            "badge": "PROTOTYPE",
            "image_url": "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?auto=format&fit=crop&w=600&q=80"
        }
        status, res = self.post("/api/admin/products/create", new_item)
        self.assertEqual(status, 201)
        self.assertTrue(res["success"])
        created_id = res["product"]["id"]
        self.assertEqual(res["product"]["name_en"], "Pozitron Hyperion 6S 2306 Motor")

        # Delete it
        del_status, del_res = self.post("/api/admin/products/delete", {"id": created_id})
        self.assertEqual(del_status, 200)
        self.assertTrue(del_res["success"])

    def test_13_admin_currency_sync_and_export(self):
        # Currency sync with custom rate
        sync_payload = {
            "usd_rate": 47.5
        }
        status, res = self.post("/api/admin/currency-sync", sync_payload)
        self.assertEqual(status, 200)
        self.assertTrue(res["success"])
        self.assertEqual(res["usd_rate"], 47.5)

        # Export static data
        exp_status, exp_res = self.post("/api/admin/sync-export", {})
        self.assertEqual(exp_status, 200)
        self.assertTrue(exp_res["success"])

if __name__ == '__main__':
    unittest.main()
