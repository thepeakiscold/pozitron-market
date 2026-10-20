"""Shared product verification state for the admin panel and workspace agents."""
import hashlib
import json
from datetime import datetime, timezone

# Stock and prices change operationally; they do not invalidate specification checks.
FIELDS = ('id', 'sku', 'name_tr', 'name_en', 'brand', 'category_id', 'description_tr',
          'description_en', 'specs_json', 'tags_json', 'compatibility_json', 'image_url', 'gallery_json')


def snapshot(product):
    item = dict(product)
    result = {key: item.get(key) for key in FIELDS}
    for key in FIELDS:
        if key.endswith('_json') and isinstance(result[key], str):
            try:
                result[key] = json.loads(result[key])
            except ValueError:
                pass
    return result


def content_hash(product):
    payload = json.dumps(snapshot(product), ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(payload.encode()).hexdigest()


def states(conn, products):
    records = {row['product_id']: dict(row) for row in conn.execute('SELECT * FROM product_quality_checks')}
    result = {}
    for product in products:
        digest = content_hash(product)
        record = records.get(product['id'], {})
        status = record.get('status', 'pending')
        if record and record.get('content_hash') != digest:
            status = 'pending'
        result[product['id']] = {
            'quality_status': status, 'quality_checked': status == 'checked',
            'quality_hash': digest, 'quality_reviewed_at': record.get('reviewed_at'),
            'quality_reviewer': record.get('reviewer', ''), 'quality_notes': record.get('notes', ''),
            'quality_sources': json.loads(record.get('sources_json') or '[]'),
        }
    return result


def record_check(conn, product_id, status, *, reviewer, notes='', sources=None, expected_hash=None):
    if status not in ('pending', 'checked', 'issues'):
        raise ValueError('Geçersiz kontrol durumu.')
    row = conn.execute('SELECT * FROM products WHERE id = ?', (product_id,)).fetchone()
    if row is None:
        raise LookupError('Ürün bulunamadı.')
    digest = content_hash(row)
    if expected_hash and expected_hash != digest:
        raise ValueError('Ürün bilgileri değişti. Güncel ürünü yeniden inceleyin.')
    if sources is None:
        sources = []
    if not isinstance(sources, list) or not all(isinstance(url, str) and url.startswith(('https://', 'http://')) for url in sources):
        raise ValueError('Kaynaklar HTTP/HTTPS adreslerinden oluşmalıdır.')
    conn.execute('''INSERT INTO product_quality_checks
        (product_id, status, content_hash, reviewer, notes, sources_json, reviewed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(product_id) DO UPDATE SET status=excluded.status,
        content_hash=excluded.content_hash, reviewer=excluded.reviewer, notes=excluded.notes,
        sources_json=excluded.sources_json, reviewed_at=excluded.reviewed_at''',
        (product_id, status, digest, reviewer, notes, json.dumps(sources, ensure_ascii=False),
         datetime.now(timezone.utc).isoformat()))
    return states(conn, [row])[product_id]
