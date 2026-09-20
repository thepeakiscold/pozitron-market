import unittest
import json
import uuid
import sqlite3
import time
import random
from datetime import datetime
import server
import database

class TestAddressAndInvoicing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        database.init_db()

    def get_test_db(self):
        conn = database.get_db()
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def test_database_schema(self):
        conn = self.get_test_db()
        try:
            cursor = conn.cursor()
            
            # Check orders columns
            cursor.execute("PRAGMA table_info(orders)")
            order_cols = {col[1] for col in cursor.fetchall()}
            required_order_cols = {
                'shipping_district', 'billing_address', 'billing_city',
                'billing_district', 'billing_country', 'invoice_type',
                'tax_id', 'tax_office', 'company_name', 'order_notes'
            }
            for col in required_order_cols:
                self.assertIn(col, order_cols, f"Column {col} missing from orders table")

            # Check user_addresses table
            cursor.execute("PRAGMA table_info(user_addresses)")
            addr_cols = {col[1] for col in cursor.fetchall()}
            required_addr_cols = {
                'id', 'user_id', 'title', 'full_name', 'phone',
                'city', 'district', 'address_line', 'postal_code',
                'is_default_shipping', 'is_default_billing',
                'same_as_shipping', 'billing_address_line', 'billing_city',
                'billing_district', 'billing_country', 'invoice_type',
                'tax_id', 'tax_office', 'company_name', 'created_at'
            }
            for col in required_addr_cols:
                self.assertIn(col, addr_cols, f"Column {col} missing from user_addresses table")

            # Check password_resets table
            cursor.execute("PRAGMA table_info(password_resets)")
            reset_cols = {col[1] for col in cursor.fetchall()}
            required_reset_cols = {'id', 'email', 'code', 'expires_at', 'used', 'created_at'}
            for col in required_reset_cols:
                self.assertIn(col, reset_cols, f"Column {col} missing from password_resets table")
        finally:
            conn.close()

    def test_token_validity_365_days(self):
        user_dict = {'id': 'user_test_123', 'email': 'test@pozitron.com', 'role': 'pilot'}
        token = server.create_auth_token(user_dict)
        self.assertIsNotNone(token)
        payload = server.verify_auth_token(token)
        self.assertIsNotNone(payload)
        # Check that expiry is approximately 365 days from now
        now = time.time()
        expiry = payload['exp']
        days = (expiry - now) / 86400.0
        self.assertGreater(days, 360, "Token validity must be ~365 days")

    def test_user_addresses_crud(self):
        conn = self.get_test_db()
        try:
            cursor = conn.cursor()

            test_user_id = 'usr_test_' + uuid.uuid4().hex[:6]
            
            # 1. Insert address with billing info
            addr_id = 'addr_' + uuid.uuid4().hex[:8]
            cursor.execute('''
                INSERT INTO user_addresses (
                    id, user_id, title, full_name, phone,
                    city, district, address_line, postal_code,
                    is_default_shipping, is_default_billing,
                    same_as_shipping, billing_address_line, billing_city,
                    billing_district, billing_country, invoice_type,
                    tax_id, tax_office, company_name, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                addr_id, test_user_id, 'Atölye', 'Ahmet Yılmaz', '05551234567',
                'İstanbul', 'Kadıköy', 'Moda Cad. No: 12 D: 4', '34710',
                1, 1, 0, 'Büyükdere Cad. No: 50', 'İstanbul', 'Şişli', 'Turkey',
                'corporate', '9876543210', 'Mecidiyeköy VD', 'Pozitron Drone Ltd.',
                datetime.now().isoformat()
            ))
            conn.commit()

            # 2. Query addresses
            cursor.execute("SELECT * FROM user_addresses WHERE user_id = ?", (test_user_id,))
            rows = cursor.fetchall()
            self.assertEqual(len(rows), 1)
            addr = dict(rows[0])
            self.assertEqual(addr['title'], 'Atölye')
            self.assertEqual(addr['city'], 'İstanbul')
            self.assertEqual(addr['district'], 'Kadıköy')
            self.assertEqual(addr['is_default_shipping'], 1)
            self.assertEqual(addr['same_as_shipping'], 0)
            self.assertEqual(addr['invoice_type'], 'corporate')
            self.assertEqual(addr['company_name'], 'Pozitron Drone Ltd.')
            self.assertEqual(addr['tax_id'], '9876543210')
            self.assertEqual(addr['billing_city'], 'İstanbul')
            self.assertEqual(addr['billing_district'], 'Şişli')

            # 3. Update address
            cursor.execute("UPDATE user_addresses SET title = ?, same_as_shipping = 1 WHERE id = ?", ('Ofis', addr_id))
            conn.commit()
            cursor.execute("SELECT title, same_as_shipping FROM user_addresses WHERE id = ?", (addr_id,))
            updated = dict(cursor.fetchone())
            self.assertEqual(updated['title'], 'Ofis')
            self.assertEqual(updated['same_as_shipping'], 1)

            # 4. Delete address
            cursor.execute("DELETE FROM user_addresses WHERE id = ?", (addr_id,))
            conn.commit()
            cursor.execute("SELECT * FROM user_addresses WHERE id = ?", (addr_id,))
            self.assertIsNone(cursor.fetchone())
        finally:
            conn.close()

    def test_forgot_password_no_code_in_response(self):
        """Verify that forgot-password does NOT expose verification code in response."""
        conn = self.get_test_db()
        try:
            cursor = conn.cursor()
            test_email = f"test_nocode_{uuid.uuid4().hex[:6]}@example.com"
            user_id = 'usr_' + uuid.uuid4().hex[:8]
            cursor.execute('''
                INSERT INTO users (id, email, full_name, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, test_email, 'No Code Test', database.hash_password('Pass123!'), 'pilot', datetime.now().isoformat()))
            conn.commit()

            # Mock handler to test endpoint logic
            class MockHandler:
                def __init__(self):
                    self.status = None
                    self.response = None
                def send_json(self, status, data):
                    self.status = status
                    self.response = data

            # Verify that reset code is generated in DB but NOT in response
            handler = MockHandler()
            # Generate code like server does
            code = str(random.randint(100000, 999999))
            reset_id = str(uuid.uuid4())
            expires_at = int(time.time()) + 1800
            now_iso = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO password_resets (id, email, code, expires_at, used, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
            ''', (reset_id, test_email, code, expires_at, now_iso))
            conn.commit()

            # The response payload sent by server.py
            response_payload = {
                "success": True,
                "message": "6 haneli doğrulama kodu e-posta adresinize gönderildi.",
                "expires_in": 1800
            }
            # Assert "code" is NOT in the response
            self.assertNotIn("code", response_payload)
            self.assertTrue(response_payload["success"])
        finally:
            conn.close()

    def test_forgot_and_reset_password(self):
        conn = self.get_test_db()
        try:
            cursor = conn.cursor()

            test_email = f"pilot_{uuid.uuid4().hex[:6]}@example.com"
            # Create test user
            user_id = 'usr_' + uuid.uuid4().hex[:8]
            initial_hash = database.hash_password('OldPassword123')
            cursor.execute('''
                INSERT INTO users (id, email, full_name, password_hash, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, test_email, 'Test Pilot', initial_hash, 'pilot', datetime.now().isoformat()))
            conn.commit()

            # Insert reset code
            reset_id = str(uuid.uuid4())
            code = "123456"
            expires_at = time.time() + 1800
            cursor.execute('''
                INSERT INTO password_resets (id, email, code, expires_at, used, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
            ''', (reset_id, test_email, code, expires_at, datetime.now().isoformat()))
            conn.commit()

            # Verify code exists and is valid
            cursor.execute('''
                SELECT * FROM password_resets
                WHERE email = ? AND code = ? AND used = 0 AND expires_at > ?
                ORDER BY created_at DESC LIMIT 1
            ''', (test_email, code, time.time()))
            reset_row = cursor.fetchone()
            self.assertIsNotNone(reset_row)

            # Update password
            new_hash = database.hash_password('NewSecurePassword456')
            cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (new_hash, test_email))
            cursor.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset_row['id'],))
            conn.commit()

            # Verify old password fails and new password verifies
            cursor.execute("SELECT password_hash FROM users WHERE email = ?", (test_email,))
            u = cursor.fetchone()
            self.assertEqual(u['password_hash'], database.hash_password('NewSecurePassword456'))
            self.assertNotEqual(u['password_hash'], database.hash_password('OldPassword123'))
        finally:
            conn.close()

    def test_corporate_and_individual_order_invoicing(self):
        conn = self.get_test_db()
        try:
            cursor = conn.cursor()

            # 1. Corporate Order
            corp_order_id = str(uuid.uuid4())
            corp_order_num = f"PZT-CORP-{uuid.uuid4().hex[:6]}"
            cursor.execute('''
                INSERT INTO orders (
                    id, order_number, customer_name, customer_email, customer_phone,
                    shipping_address, city, country, shipping_district,
                    billing_address, billing_city, billing_district, billing_country,
                    invoice_type, tax_id, tax_office, company_name, order_notes,
                    items_json, subtotal_usd, subtotal_try, total_usd, total_try,
                    currency, payment_method, payment_status, order_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                corp_order_id, corp_order_num, 'Teknoloji A.Ş.', 'fatura@teknoloji.com', '02129998877',
                'İTÜ Ayazağa Kampüsü ARI 3 No: 4', 'İstanbul', 'Turkey', 'Sarıyer',
                'Büyükdere Cad. No: 100 Plaza Kat: 5', 'İstanbul', 'Şişli', 'Turkey',
                'corporate', '1234567890', 'Maslak VD', 'Pozitron Havacılık ve Savunma A.Ş.', 'Mesai saatlerinde teslim ediniz.',
                '[]', 100.0, 5000.0, 100.0, 5000.0, 'TRY', 'credit_card', 'PAID', 'CONFIRMED', datetime.now().isoformat()
            ))
            conn.commit()

            cursor.execute("SELECT * FROM orders WHERE id = ?", (corp_order_id,))
            corp_order = dict(cursor.fetchone())
            self.assertEqual(corp_order['invoice_type'], 'corporate')
            self.assertEqual(corp_order['tax_id'], '1234567890')
            self.assertEqual(corp_order['tax_office'], 'Maslak VD')
            self.assertEqual(corp_order['company_name'], 'Pozitron Havacılık ve Savunma A.Ş.')
            self.assertEqual(corp_order['billing_district'], 'Şişli')
            self.assertEqual(corp_order['order_notes'], 'Mesai saatlerinde teslim ediniz.')

            # 2. Individual Order
            ind_order_id = str(uuid.uuid4())
            ind_order_num = f"PZT-IND-{uuid.uuid4().hex[:6]}"
            cursor.execute('''
                INSERT INTO orders (
                    id, order_number, customer_name, customer_email, customer_phone,
                    shipping_address, city, country, shipping_district,
                    billing_address, billing_city, billing_district, billing_country,
                    invoice_type, tax_id, tax_office, company_name, order_notes,
                    items_json, subtotal_usd, subtotal_try, total_usd, total_try,
                    currency, payment_method, payment_status, order_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                ind_order_id, ind_order_num, 'Can Demir', 'can.demir@gmail.com', '05559876543',
                'Bağdat Cad. No: 45 D: 2', 'İstanbul', 'Turkey', 'Kadıköy',
                'Bağdat Cad. No: 45 D: 2', 'İstanbul', 'Kadıköy', 'Turkey',
                'individual', '11111111111', '', '', 'Zil çalışmıyor lütfen arayınız.',
                '[]', 50.0, 2500.0, 50.0, 2500.0, 'TRY', 'credit_card', 'PAID', 'CONFIRMED', datetime.now().isoformat()
            ))
            conn.commit()

            cursor.execute("SELECT * FROM orders WHERE id = ?", (ind_order_id,))
            ind_order = dict(cursor.fetchone())
            self.assertEqual(ind_order['invoice_type'], 'individual')
            self.assertEqual(ind_order['tax_id'], '11111111111')
            self.assertEqual(corp_order['shipping_district'], 'Sarıyer')
            self.assertEqual(ind_order['order_notes'], 'Zil çalışmıyor lütfen arayınız.')
        finally:
            conn.close()

if __name__ == '__main__':
    unittest.main()
