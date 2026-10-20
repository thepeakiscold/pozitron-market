"""Provider contract and transaction tests; never connect to live payment APIs."""
import json
import os
import sqlite3
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import database
import iyzico_checkout as checkout


class IyzicoCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.tmp.name) / 'checkout.db')
        with sqlite3.connect(database.DB_PATH) as source, sqlite3.connect(self.path) as target:
            source.backup(target)
        self.db_patch = patch.object(database, 'DB_PATH', self.path)
        self.db_patch.start()
        self.env = patch.dict(os.environ, {'IYZICO_API_KEY': 'test-key', 'IYZICO_SECRET_KEY': 'test-secret'})
        self.env.start()
        database.init_db()
        with database.get_db() as conn:
            self.product = conn.execute('SELECT id FROM products LIMIT 1').fetchone()['id']
            conn.execute('UPDATE products SET price_try=100,price_usd=3,stock=10 WHERE id=?', (self.product,))
        self.data = {'items': [{'id': self.product, 'quantity': 2}], 'customer_name': 'Test Buyer',
                     'customer_email': 'buyer@example.invalid', 'customer_phone': '+905350000000',
                     'shipping_address': 'Test Address', 'city': 'Ankara',
                     'buyer_identity_number': '74300864791', 'terms_accepted': True,
                     'total_try': '0.01', 'user_id': 'forged-user', 'payment_status': 'PAID'}

    def tearDown(self):
        self.env.stop()
        self.db_patch.stop()
        self.tmp.cleanup()

    def init_response(self, path, payload):
        self.request = payload
        result = {'status': 'success', 'conversationId': payload['conversationId'], 'token': 'test-token',
                  'paymentPageUrl': 'https://cpp.iyzipay.com?token=test-token'}
        result['signature'] = checkout.signature([result['conversationId'], result['token']])
        return result

    def initialize(self):
        with patch.object(checkout, 'api_request', side_effect=self.init_response):
            return checkout.initialize(self.data, '127.0.0.1')

    def detail(self, **changes):
        result = {'status': 'success', 'paymentStatus': 'SUCCESS', 'paymentId': 'verified-payment-123',
                  'currency': 'TRY', 'basketId': self.request['basketId'],
                  'conversationId': self.request['conversationId'], 'paidPrice': Decimal('299.00'),
                  'price': Decimal('299.00'), 'token': 'test-token', 'fraudStatus': 1}
        result.update(changes)
        fields = ['paymentStatus', 'paymentId', 'currency', 'basketId', 'conversationId', 'paidPrice', 'price', 'token']
        values = [format(result[k].normalize(), 'f') if isinstance(result[k], Decimal) else result[k] for k in fields]
        result['signature'] = checkout.signature(values)
        return result

    def row(self):
        with database.get_db() as conn:
            return dict(conn.execute('SELECT * FROM orders WHERE id=?', (self.request['basketId'],)).fetchone())

    def stock(self):
        with database.get_db() as conn:
            return conn.execute('SELECT stock FROM products WHERE id=?', (self.product,)).fetchone()[0]

    def test_initialization_uses_database_prices_no_stock_deduction_or_client_paid(self):
        result = self.initialize()
        self.assertEqual(result['total_try'], '299.00')
        self.assertEqual(self.request['price'], '299.00')
        self.assertEqual(sum(Decimal(i['price']) for i in self.request['basketItems']), Decimal('299'))
        self.assertEqual(self.row()['payment_status'], 'PENDING')
        self.assertIsNone(self.row()['user_id'])
        self.assertEqual(self.stock(), 10)
        self.assertNotIn(self.data['buyer_identity_number'], json.dumps(self.row()))

    def test_success_is_idempotent_and_decrements_stock_once(self):
        result = self.initialize()
        with patch.object(checkout, 'api_request', return_value=self.detail()):
            self.assertEqual(checkout.callback('test-token'), result['receipt'])
            checkout.callback('test-token')
        self.assertEqual(self.row()['payment_status'], 'PAID')
        self.assertEqual(self.row()['order_status'], 'PROCESSING')
        self.assertEqual(self.stock(), 8)
        self.assertEqual(checkout.status(result['receipt'])['payment_status'], 'PAID')

    def test_mismatched_amount_never_marks_paid(self):
        self.initialize()
        with patch.object(checkout, 'api_request', return_value=self.detail(paidPrice=Decimal('1.00'))):
            with self.assertRaises(checkout.PaymentError): checkout.callback('test-token')
        self.assertEqual(self.row()['payment_status'], 'PENDING')
        self.assertEqual(self.stock(), 10)

    def test_wrong_signature_never_marks_paid(self):
        self.initialize()
        detail = self.detail()
        detail['signature'] = 'forged-signature'
        with patch.object(checkout, 'api_request', return_value=detail):
            with self.assertRaises(checkout.PaymentError): checkout.callback('test-token')
        self.assertEqual(self.stock(), 10)
        self.assertEqual(self.row()['payment_status'], 'PENDING')

    def test_wrong_basket_never_marks_paid(self):
        self.initialize()
        with patch.object(checkout, 'api_request', return_value=self.detail(basketId='other-order')):
            with self.assertRaises(checkout.PaymentError): checkout.callback('test-token')
        self.assertEqual(self.row()['payment_status'], 'PENDING')

    def test_declined_payment_does_not_consume_stock(self):
        self.initialize()
        with patch.object(checkout, 'api_request', return_value=self.detail(paymentStatus='FAILURE')):
            checkout.callback('test-token')
        self.assertEqual(self.row()['payment_status'], 'FAILED')
        self.assertEqual(self.stock(), 10)

    def test_fraud_review_is_not_approved_then_can_be_approved(self):
        self.initialize()
        with patch.object(checkout, 'api_request', return_value=self.detail(fraudStatus=0)):
            checkout.callback('test-token')
        self.assertEqual(self.row()['payment_status'], 'PENDING')
        self.assertEqual(self.row()['order_status'], 'PAYMENT_REVIEW')
        self.assertEqual(self.stock(), 10)
        with patch.object(checkout, 'api_request', return_value=self.detail(fraudStatus=1)):
            checkout.callback('test-token')
        self.assertEqual(self.stock(), 8)
        self.assertEqual(self.row()['payment_status'], 'PAID')

    def test_stock_race_records_charge_but_holds_fulfillment(self):
        self.initialize()
        with database.get_db() as conn:
            conn.execute('UPDATE products SET stock=0 WHERE id=?', (self.product,))
        with patch.object(checkout, 'api_request', return_value=self.detail()):
            checkout.callback('test-token')
        self.assertEqual(self.row()['payment_status'], 'PAID')
        self.assertEqual(self.row()['order_status'], 'PAYMENT_REVIEW')
        self.assertEqual(self.stock(), 0)

    def test_unsafe_redirect_is_rejected_without_order(self):
        def unsafe(path, payload):
            result = self.init_response(path, payload)
            result['paymentPageUrl'] = 'https://attacker.invalid/payment'
            return result
        with patch.object(checkout, 'api_request', side_effect=unsafe):
            with self.assertRaises(checkout.PaymentError): checkout.initialize(self.data, '127.0.0.1')
        self.assertEqual(self.stock(), 10)
        with database.get_db() as conn:
            self.assertIsNone(conn.execute('SELECT * FROM orders WHERE id=?', (self.request['basketId'],)).fetchone())

    def test_rejects_unknown_token_without_provider_call(self):
        with patch.object(checkout, 'api_request') as api:
            with self.assertRaises(checkout.PaymentError): checkout.callback('unknown-token')
            api.assert_not_called()

    def test_invalid_quantity_missing_identity_and_terms_fail_before_network(self):
        for key, value in [('items', [{'id': self.product, 'quantity': -1}]),
                           ('buyer_identity_number', ''), ('terms_accepted', False)]:
            with patch.object(checkout, 'api_request') as api:
                with self.assertRaises(checkout.PaymentError):
                    checkout.initialize({**self.data, key: value}, '127.0.0.1')
                api.assert_not_called()

    def test_response_signature_normalizes_decimal_trailing_zeros(self):
        result = {'price': Decimal('10.00000000'), 'paidPrice': Decimal('10.10000000')}
        result['signature'] = checkout.signature(['10', '10.1'])
        checkout.verify(result, ['price', 'paidPrice'])

    def test_coupon_only_redeemed_on_verified_payment_once(self):
        checkout.coupons.create_coupon('IYZTEST10', 'percent', 10)
        self.data['coupon_code'] = 'IYZTEST10'
        result = self.initialize()
        self.assertEqual(result['total_try'], '279.00')
        with database.get_db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM coupon_redemptions WHERE coupon_code=?', ('IYZTEST10',)).fetchone()[0], 0)
        detail = self.detail(price=Decimal('279.00'), paidPrice=Decimal('279.00'))
        with patch.object(checkout, 'api_request', return_value=detail):
            checkout.callback('test-token')
            checkout.callback('test-token')
        with database.get_db() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM coupon_redemptions WHERE coupon_code=?', ('IYZTEST10',)).fetchone()[0], 1)
        self.assertEqual(self.stock(), 8)

    def test_coupon_race_rolls_back_stock_and_preserves_actual_charge(self):
        checkout.coupons.create_coupon('IYZTEST10', 'percent', 10)
        self.data['coupon_code'] = 'IYZTEST10'
        self.initialize()
        detail = self.detail(price=Decimal('279.00'), paidPrice=Decimal('279.00'))
        with patch.object(checkout, 'api_request', return_value=detail), patch.object(checkout.coupons, 'redeem_coupon', return_value=(False, 'already_used')):
            checkout.callback('test-token')
        self.assertEqual(self.row()['payment_status'], 'PAID')
        self.assertEqual(self.row()['order_status'], 'PAYMENT_REVIEW')
        self.assertEqual(self.stock(), 10)

    def test_reconciliation_recovers_a_missed_callback(self):
        self.initialize()
        with patch.object(checkout, 'api_request', return_value=self.detail()):
            checkout.reconcile_pending()
        self.assertEqual(self.row()['payment_status'], 'PAID')
        self.assertEqual(self.stock(), 8)


if __name__ == '__main__':
    unittest.main()
