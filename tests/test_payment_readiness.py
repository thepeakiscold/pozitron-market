"""A bank notice or a browser OTP must never become a verified card charge."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import database
import server


class PaymentReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'payments.db')
        # Copy a snapshot for realistic constraints; never mutate the live database.
        with sqlite3.connect(database.DB_PATH) as source, sqlite3.connect(self.db) as target:
            source.backup(target)
        self.handler = object.__new__(server.PozitronRequestHandler)
        self.responses = []
        self.handler.send_json = lambda status, payload: self.responses.append((status, payload))
        self.handler.headers = {}
        self.patch = patch.object(database, 'DB_PATH', self.db)
        self.patch.start()
        with database.get_db() as conn:
            row = conn.execute('SELECT id FROM products LIMIT 1').fetchone()
            self.product = row['id']
            conn.execute('UPDATE products SET stock = 20 WHERE id = ?', (self.product,))
        self.payload = {'items': [{'id': self.product, 'quantity': 1}],
                        'customer_name': 'Test Customer', 'customer_email': 'test@example.invalid',
                        'shipping_address': 'Test Address', 'city': 'Ankara', 'currency': 'TRY'}

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_unconfigured_cards_cannot_create_paid_orders(self):
        with database.get_db() as conn:
            before = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
        for method in ('iyzico', 'paytr', 'credit_card', 'unknown'):
            self.handler.handle_api_post('/api/payment/process', {
                **self.payload, 'payment_method': method, 'payment_status': 'PAID', 'is_3d_secure': True})
            status, payload = self.responses[-1]
            self.assertEqual(status, 503)
            self.assertEqual(payload['code'], 'PAYMENT_PROVIDER_NOT_CONFIGURED')
        with database.get_db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0], before)
            self.assertEqual(conn.execute('SELECT stock FROM products WHERE id = ?', (self.product,)).fetchone()[0], 20)

    def test_transfer_notice_remains_pending_even_if_client_claims_paid(self):
        self.handler.handle_api_post('/api/payment/process', {
            **self.payload, 'payment_method': 'havale', 'payment_status': 'PAID'})
        status, payload = self.responses[-1]
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload['payment_status'], 'PENDING')
        with database.get_db() as conn:
            row = conn.execute('SELECT payment_status, order_status FROM orders WHERE id = ?',
                               (payload['order_id'],)).fetchone()
            self.assertEqual(tuple(row), ('PENDING', 'PENDING_PAYMENT'))

    def test_account_migration_runs_once_and_preserves_later_edits(self):
        with database.get_db() as conn:
            conn.execute("DELETE FROM settings WHERE key = 'business_account_revision'")
            conn.execute("UPDATE settings SET value = 'obsolete' WHERE key = 'bank_iban'")
        database.init_db()
        self.assertEqual(database.get_setting('bank_iban'), 'TR69 0004 6001 9188 8000 3245 80')
        self.assertEqual(database.get_setting('bank_owner'), '')
        database.set_setting('bank_iban', 'later-admin-value')
        database.init_db()
        self.assertEqual(database.get_setting('bank_iban'), 'later-admin-value')


if __name__ == '__main__':
    unittest.main()
