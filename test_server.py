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

if __name__ == '__main__':
    unittest.main()
