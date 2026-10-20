"""Hosted iyzico checkout: secrets stay in environment, callbacks are API-verified."""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import coupons
import database

INITIALIZE = '/payment/iyzipos/checkoutform/initialize/auth/ecom'
RETRIEVE = '/payment/iyzipos/checkoutform/auth/ecom/detail'
CENT = Decimal('0.01')
_attempts = {}
_attempt_lock = threading.Lock()


def allow_attempt(ip):
    """Bound anonymous hosted-session creation without persisting buyer data."""
    now = time.monotonic()
    with _attempt_lock:
        for key in list(_attempts):
            if now - _attempts[key][0] >= 60:
                del _attempts[key]
        start, count = _attempts.get(ip, (now, 0))
        if count >= 5 or (ip not in _attempts and len(_attempts) >= 10000):
            return False
        _attempts[ip] = (start, count + 1)
        return True


class PaymentError(Exception):
    pass


def money(value):
    try:
        result = Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
        if not result.is_finite():
            raise InvalidOperation
        return result
    except (InvalidOperation, ValueError, TypeError):
        raise PaymentError('Geçersiz ödeme tutarı.') from None


def configured():
    return bool(os.environ.get('IYZICO_API_KEY') and os.environ.get('IYZICO_SECRET_KEY'))


def signature(values):
    return hmac.new(os.environ['IYZICO_SECRET_KEY'].encode(),
                    ':'.join(str(v) for v in values).encode(), hashlib.sha256).hexdigest()


def verify(result, fields):
    values = []
    for field in fields:
        if field not in result:
            raise PaymentError('iyzico yanıtı doğrulanamadı.')
        value = result[field]
        if field in ('price', 'paidPrice'):
            value = format(Decimal(str(value)), 'f').rstrip('0').rstrip('.') if '.' in str(value) else str(value)
        values.append(value)
    if not hmac.compare_digest(signature(values), str(result.get('signature', ''))):
        raise PaymentError('iyzico yanıt imzası doğrulanamadı.')


def api_request(path, payload):
    if not configured():
        raise PaymentError('iyzico ödemesi şu anda kullanılamıyor.')
    base = os.environ.get('IYZICO_API_BASE', 'https://api.iyzipay.com').rstrip('/')
    if base not in ('https://api.iyzipay.com', 'https://sandbox-api.iyzipay.com'):
        raise PaymentError('Geçersiz iyzico sunucu ayarı.')
    body = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    random_key = secrets.token_hex(16)
    digest = hmac.new(os.environ['IYZICO_SECRET_KEY'].encode(),
                      (random_key + path + body).encode(), hashlib.sha256).hexdigest()
    authorization = base64.b64encode(
        f"apiKey:{os.environ['IYZICO_API_KEY']}&randomKey:{random_key}&signature:{digest}".encode()).decode()
    request = urllib.request.Request(base + path, data=body.encode(), headers={
        'Content-Type': 'application/json', 'Authorization': 'IYZWSv2 ' + authorization,
        'x-iyzi-rnd': random_key})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return json.load(response, parse_float=Decimal)
    except (urllib.error.URLError, TimeoutError, ValueError):
        raise PaymentError('iyzico bağlantısı kurulamadı. Lütfen tekrar deneyin.') from None


def valid_payment_url(url):
    parsed = urllib.parse.urlparse(url)
    hosts = {'cpp.iyzipay.com', 'api.iyzipay.com'}
    if os.environ.get('IYZICO_API_BASE') == 'https://sandbox-api.iyzipay.com':
        hosts |= {'sandbox-cpp.iyzipay.com', 'sandbox-api.iyzipay.com'}
    return parsed.scheme == 'https' and parsed.hostname in hosts and not parsed.username


def initialize(data, ip, identity=None):
    if not configured():
        raise PaymentError('iyzico ödemesi şu anda kullanılamıyor.')
    required = ('customer_name', 'customer_email', 'customer_phone', 'shipping_address', 'city')
    if any(not isinstance(data.get(k), str) or not data[k].strip() for k in required):
        raise PaymentError('Teslimat, telefon ve e-posta bilgilerini eksiksiz girin.')
    name = data['customer_name'].strip().split()
    if len(name) < 2 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', data['customer_email']):
        raise PaymentError('Ad soyad ve geçerli e-posta adresi gereklidir.')
    identity_number = str(data.get('buyer_identity_number', '')).strip()
    if not re.fullmatch(r'[1-9][0-9]{10}', identity_number):
        raise PaymentError('iyzico ödemesi için alıcının 11 haneli T.C. kimlik numarasını girin.')
    if data.get('terms_accepted') is not True:
        raise PaymentError('Satış sözleşmesi onayı gereklidir.')
    items = data.get('items')
    if not isinstance(items, list) or not 1 <= len(items) <= 100:
        raise PaymentError('Sepetiniz boş veya geçersiz.')
    quantities = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str):
            raise PaymentError('Geçersiz sepet ürünü.')
        qty = item.get('quantity', 1)
        if isinstance(qty, bool) or not isinstance(qty, int) or not 1 <= qty <= 100:
            raise PaymentError('Geçersiz ürün miktarı.')
        quantities[item['id']] = quantities.get(item['id'], 0) + qty
    order_id = str(uuid.uuid4())
    receipt = secrets.token_hex(32)
    order_number = 'PZT-' + datetime.now().strftime('%Y%m%d') + '-' + secrets.token_hex(4).upper()
    user_id = (identity or {}).get('uid')
    if user_id in ('master_admin', 'local_dev'):
        user_id = None
    coupon = str(data.get('coupon_code') or '').strip().upper()
    conn = database.get_db()
    try:
        subtotal = Decimal('0.00')
        subtotal_usd = Decimal('0.00')
        snapshot = []
        basket = []
        for product_id, qty in quantities.items():
            row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
            if not row or int(row['stock'] or 0) < qty:
                raise PaymentError('Ürün bulunamadı veya yeterli stok yok. Sepetinizi güncelleyin.')
            product = dict(row)
            price = money(product['price_try'])
            if price <= 0:
                raise PaymentError('Bu ürünün fiyatı doğrulanamadı.')
            line = price * qty
            subtotal += line
            subtotal_usd += money(product.get('price_usd') or 0) * qty
            snapshot.append({k: product.get(k) for k in ('id', 'sku', 'name_tr', 'name_en', 'brand', 'price_try', 'price_usd', 'image_url')})
            snapshot[-1]['quantity'] = qty
            basket.append({'id': product_id, 'name': str(product['name_tr'] or product['name_en'])[:128],
                           'category1': str(product.get('category_id') or 'FPV'), 'itemType': 'PHYSICAL', 'price': str(line)})
        discount = Decimal('0.00')
        discount_usd = Decimal('0.00')
        if coupon:
            validation = coupons.validate_coupon(coupon, subtotal_usd=float(subtotal_usd), subtotal_try=float(subtotal),
                                                  user_id=user_id, email=data['customer_email'], conn=conn, commit=False)
            if not validation.get('valid'):
                raise PaymentError(validation.get('error') or 'Kupon geçersiz.')
            discount = money(validation['discount_try'])
            discount_usd = money(validation['discount_usd'])
        shipping = Decimal('0.00') if subtotal - discount >= 1500 else Decimal('99.00')
        total = subtotal - discount + shipping
        if total <= 0:
            raise PaymentError('Ödeme tutarı sıfırdan büyük olmalıdır.')
        # Distribute discounts without float rounding; basket sum equals paid price.
        remaining = discount
        for line in basket:
            amount = money(line['price'])
            reduction = min(remaining, amount)
            line['price'] = str(amount - reduction)
            remaining -= reduction
        basket = [line for line in basket if money(line['price']) > 0]
        if shipping:
            basket.append({'id': 'shipping', 'name': 'Kargo', 'category1': 'Kargo', 'itemType': 'VIRTUAL', 'price': str(shipping)})
        address = {'contactName': data['customer_name'], 'city': data['city'], 'country': data.get('country') or 'Turkey',
                   'address': data['shipping_address']}
        billing = {**address, 'address': data.get('billing_address') or address['address'],
                   'city': data.get('billing_city') or address['city']}
        payload = {'locale': 'tr', 'conversationId': order_id, 'basketId': order_id,
                   'price': str(total), 'paidPrice': str(total), 'currency': 'TRY', 'paymentGroup': 'PRODUCT',
                   'enabledInstallments': [1],
                   'callbackUrl': 'https://api.pozitronmarket.com/api/iyzico/callback',
                   'buyer': {'id': user_id or order_id, 'name': ' '.join(name[:-1]), 'surname': name[-1],
                             'gsmNumber': data['customer_phone'], 'email': data['customer_email'],
                             'identityNumber': identity_number, 'registrationAddress': data['shipping_address'],
                             'ip': ip, 'city': data['city'], 'country': address['country']},
                   'shippingAddress': address, 'billingAddress': billing, 'basketItems': basket}
        # Commit before network I/O: never hold a write transaction during provider calls.
        conn.rollback()
        result = api_request(INITIALIZE, payload)
        if result.get('status') != 'success':
            raise PaymentError('iyzico ödeme sayfasını başlatamadı. Lütfen bilgilerinizi kontrol edin veya havale seçin.')
        verify(result, ['conversationId', 'token'])
        if result.get('conversationId') != order_id or not result.get('token') or not valid_payment_url(str(result.get('paymentPageUrl', ''))):
            raise PaymentError('iyzico ödeme oturumu doğrulanamadı.')
        record = {'id': order_id, 'order_number': order_number, 'user_id': user_id,
                  'customer_name': data['customer_name'], 'customer_email': data['customer_email'],
                  'customer_phone': data['customer_phone'], 'shipping_address': data['shipping_address'],
                  'city': data['city'], 'country': address['country'], 'items_json': json.dumps(snapshot),
                  'subtotal_usd': float(subtotal_usd), 'subtotal_try': float(subtotal),
                  'discount_usd': float(discount_usd), 'discount_try': float(discount),
                  'shipping_fee_try': float(shipping), 'shipping_fee_usd': 2.10 if shipping else 0,
                  'total_usd': float(max(Decimal('0'), subtotal_usd - discount_usd) + (Decimal('2.10') if shipping else 0)),
                  'total_try': float(total), 'currency': 'TRY',
                  'payment_method': 'iyzico', 'payment_status': 'PENDING', 'order_status': 'PENDING_PAYMENT',
                  'billing_address': billing['address'], 'billing_city': billing['city'],
                  'created_at': datetime.now().isoformat(), 'notes': 'iyzico hosted checkout; awaiting verified payment'}
        for key in ('shipping_district', 'billing_district', 'billing_country', 'invoice_type', 'tax_id', 'tax_office', 'company_name', 'order_notes'):
            record[key] = str(data.get(key) or '')[:2000]
        conn.execute('INSERT INTO orders (' + ','.join(record) + ') VALUES (' + ','.join('?' for _ in record) + ')', tuple(record.values()))
        conn.execute('INSERT INTO iyzico_sessions (token,order_id,receipt,coupon_code,created_at) VALUES (?,?,?,?,?)',
                     (result['token'], order_id, receipt, coupon, record['created_at']))
        conn.commit()
        return {'payment_url': result['paymentPageUrl'], 'order_number': order_number, 'receipt': receipt,
                'total_try': str(total), 'currency': 'TRY', 'payment_status': 'PENDING'}
    finally:
        conn.close()


def callback(token):
    if not isinstance(token, str) or not 1 <= len(token) <= 256:
        raise PaymentError('Geçersiz ödeme bildirimi.')
    conn = database.get_db()
    try:
        session = conn.execute('SELECT * FROM iyzico_sessions WHERE token = ?', (token,)).fetchone()
        if not session:
            raise PaymentError('Ödeme oturumu bulunamadı.')
        session = dict(session)
        result = api_request(RETRIEVE, {'locale': 'tr', 'conversationId': session['order_id'], 'token': token})
        if result.get('status') != 'success':
            raise PaymentError('Ödeme sonucu henüz doğrulanamadı.')
        verify(result, ['paymentStatus', 'paymentId', 'currency', 'basketId', 'conversationId', 'paidPrice', 'price', 'token'])
        conn.execute('BEGIN IMMEDIATE')
        order = dict(conn.execute('SELECT * FROM orders WHERE id = ?', (session['order_id'],)).fetchone())
        if (result['token'] != token or result['basketId'] != order['id'] or result['conversationId'] != order['id']
                or result['currency'] != 'TRY' or money(result['paidPrice']) != money(order['total_try'])
                or money(result['price']) != money(order['total_try']) or not result.get('paymentId')):
            raise PaymentError('Ödeme tutarı veya sipariş kimliği doğrulanamadı.')
        if order['payment_status'] == 'PAID':
            return session['receipt']
        if result['paymentStatus'] != 'SUCCESS':
            conn.execute("UPDATE orders SET payment_status='FAILED',order_status='PAYMENT_FAILED' WHERE id=?", (order['id'],))
            conn.commit()
            return session['receipt']
        if int(result.get('fraudStatus', 0)) != 1:
            conn.execute("UPDATE orders SET payment_status='PENDING',order_status='PAYMENT_REVIEW',transaction_id=? WHERE id=?",
                         (str(result['paymentId']), order['id']))
            conn.commit()
            return session['receipt']
        # Payment can succeed after stock/coupon changed. Record the charge honestly,
        # hold fulfillment for manual review rather than oversell or lose the payment.
        issues = []
        items = json.loads(order['items_json'])
        for item in items:
            row = conn.execute('SELECT stock FROM products WHERE id=?', (item['id'],)).fetchone()
            if not row or int(row['stock'] or 0) < item['quantity']:
                issues.append('Stok yetersiz: ' + item['id'])
        conn.execute('SAVEPOINT fulfillment')
        if not issues:
            for item in items:
                conn.execute('UPDATE products SET stock=stock-? WHERE id=?', (item['quantity'], item['id']))
            if session['coupon_code']:
                ok, reason = coupons.redeem_coupon(conn, session['coupon_code'], user_id=order['user_id'],
                    email=order['customer_email'], order_id=order['id'], order_number=order['order_number'],
                    discount_usd=order['discount_usd'], discount_try=order['discount_try'])
                if not ok:
                    issues.append('Kupon incelemesi: ' + str(reason))
        if issues:
            conn.execute('ROLLBACK TO fulfillment')
        conn.execute('RELEASE fulfillment')
        conn.execute("UPDATE orders SET payment_status='PAID',order_status=?,transaction_id=?,card_last4=?,card_brand=?,notes=? WHERE id=?",
                     ('PAYMENT_REVIEW' if issues else 'PROCESSING', str(result['paymentId']),
                      str(result.get('lastFourDigits', ''))[-4:], str(result.get('cardAssociation', 'iyzico')),
                      '; '.join(issues) if issues else 'iyzico API and signature verified', order['id']))
        conn.commit()
        return session['receipt']
    finally:
        conn.close()


def status(receipt):
    if not isinstance(receipt, str) or not re.fullmatch(r'[0-9a-f]{64}', receipt):
        raise PaymentError('Ödeme kaydı bulunamadı.')
    conn = database.get_db()
    try:
        row = conn.execute('SELECT o.order_number,o.payment_status,o.order_status,o.total_try FROM orders o '
                           'JOIN iyzico_sessions s ON s.order_id=o.id WHERE s.receipt=?', (receipt,)).fetchone()
        if not row:
            raise PaymentError('Ödeme kaydı bulunamadı.')
        return dict(row)
    finally:
        conn.close()


def reconcile_pending():
    """Recover missed callbacks, including provider fraud reviews, after restarts."""
    if not configured():
        return
    conn = database.get_db()
    try:
        rows = conn.execute(
            "SELECT s.token FROM iyzico_sessions s JOIN orders o ON o.id=s.order_id "
            "WHERE o.payment_status='PENDING' AND s.last_checked<? "
            "AND s.created_at>datetime('now','-7 days') ORDER BY s.last_checked LIMIT 20",
            (time.time() - 60,)).fetchall()
        for row in rows:
            conn.execute('UPDATE iyzico_sessions SET last_checked=? WHERE token=?', (time.time(), row['token']))
        conn.commit()
    finally:
        conn.close()
    for row in rows:
        try:
            callback(row['token'])
        except Exception:
            # Never log provider payloads, buyer identity, tokens or secrets.
            # Leave pending for another retry; errors never imply a failed charge.
            pass


def start_reconciler():
    if not configured():
        return
    def run():
        while True:
            try:
                reconcile_pending()
            except Exception:
                pass
            time.sleep(60)
    threading.Thread(target=run, name='iyzico-payment-reconciliation', daemon=True).start()
