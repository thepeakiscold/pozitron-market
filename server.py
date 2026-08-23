import http.server
import socketserver
import os
import json
import sqlite3
import urllib.parse
import uuid
import re
import random
import time
import math
import threading
from datetime import datetime
from database import get_db, hash_password
from export_data import export_static_data

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Security Lockout Configuration: 3 failed attempts => 30-minute cooldown
LOGIN_ATTEMPTS_LOCK = threading.Lock()
LOGIN_ATTEMPTS = {}  # key: identifier -> {"count": int, "locked_until": float, "last_attempt": float}
MAX_FAILED_ATTEMPTS = 3
LOCKOUT_DURATION_SECONDS = 30 * 60  # 30 minutes

def check_login_rate_limit(identifier: str):
    """Returns (is_locked, remaining_seconds, remaining_minutes, attempts_left)"""
    with LOGIN_ATTEMPTS_LOCK:
        now = time.time()
        record = LOGIN_ATTEMPTS.get(identifier)
        if not record:
            return False, 0, 0, MAX_FAILED_ATTEMPTS
        
        # Check if currently locked
        if record.get('locked_until', 0) > now:
            rem_sec = int(record['locked_until'] - now)
            rem_min = max(1, int(math.ceil(rem_sec / 60)))
            return True, rem_sec, rem_min, 0
        
        # If lock has expired, reset record
        if record.get('locked_until', 0) > 0 and record['locked_until'] <= now:
            del LOGIN_ATTEMPTS[identifier]
            return False, 0, 0, MAX_FAILED_ATTEMPTS
            
        count = record.get('count', 0)
        attempts_left = max(0, MAX_FAILED_ATTEMPTS - count)
        return False, 0, 0, attempts_left

def record_failed_login(identifier: str):
    """Records a failure. Returns (is_now_locked, remaining_seconds, remaining_minutes, attempts_left)"""
    with LOGIN_ATTEMPTS_LOCK:
        now = time.time()
        record = LOGIN_ATTEMPTS.get(identifier, {"count": 0, "locked_until": 0, "last_attempt": now})
        record['count'] += 1
        record['last_attempt'] = now
        
        if record['count'] >= MAX_FAILED_ATTEMPTS:
            record['locked_until'] = now + LOCKOUT_DURATION_SECONDS
            LOGIN_ATTEMPTS[identifier] = record
            return True, LOCKOUT_DURATION_SECONDS, 30, 0
        else:
            LOGIN_ATTEMPTS[identifier] = record
            attempts_left = MAX_FAILED_ATTEMPTS - record['count']
            return False, 0, 0, attempts_left

def clear_login_attempts(identifier: str):
    with LOGIN_ATTEMPTS_LOCK:
        if identifier in LOGIN_ATTEMPTS:
            del LOGIN_ATTEMPTS[identifier]

def luhn_validate(card_number: str) -> bool:
    digits = [int(c) for c in card_number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    # Allow standard demo / test cards instantly
    clean = "".join(str(d) for d in digits)
    if clean.startswith("4242") or clean.startswith("5555") or clean.startswith("9792") or clean == "4532012345678910":
        return True
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0

class PozitronRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def send_json(self, status_code, data):
        response_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/'):
            try:
                self.handle_api_delete(path)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json(500, {"error": str(e)})
            return

        self.send_json(404, {"error": "Endpoint not found"})

    def handle_api_delete(self, path):
        conn = get_db()
        cursor = conn.cursor()

        prod_match = re.match(r'^/api/admin/products/([a-zA-Z0-9_-]+)$', path)
        if not prod_match:
            prod_match = re.match(r'^/api/products/([a-zA-Z0-9_-]+)$', path)

        if prod_match:
            prod_id = prod_match.group(1)
            cursor.execute("SELECT category_id FROM products WHERE id = ? OR slug = ?", (prod_id, prod_id))
            row = cursor.fetchone()
            if not row:
                conn.close()
                self.send_json(404, {"error": "Product not found"})
                return

            cat_id = row[0]
            cursor.execute("DELETE FROM products WHERE id = ? OR slug = ?", (prod_id, prod_id))
            cursor.execute("UPDATE categories SET item_count = MAX(0, item_count - 1) WHERE id = ?", (cat_id,))
            conn.commit()
            conn.close()
            self.send_json(200, {"success": True, "deleted_id": prod_id})
            return

        conn.close()
        self.send_json(404, {"error": "Route not found"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # SEO Endpoints
        if path == '/robots.txt':
            robots_txt = "User-agent: *\nAllow: /\nSitemap: http://localhost:8000/sitemap.xml\n"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(robots_txt.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(robots_txt.encode('utf-8'))
            return

        if path == '/sitemap.xml':
            self.handle_sitemap_xml()
            return

        if path.startswith('/api/'):
            try:
                self.handle_api_get(path, query)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Serve frontend static files
        if path == '/' or path == '/index.html':
            self.path = '/index.html'
        return super().do_GET()

    def handle_sitemap_xml(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT slug, id, category_id, created_at FROM products ORDER BY id ASC")
        products = cursor.fetchall()
        cursor.execute("SELECT id FROM categories")
        categories = cursor.fetchall()
        conn.close()

        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            '  <url>',
            '    <loc>http://localhost:8000/</loc>',
            '    <changefreq>daily</changefreq>',
            '    <priority>1.0</priority>',
            '  </url>'
        ]

        # Category URLs
        for cat in categories:
            xml_lines.extend([
                '  <url>',
                f'    <loc>http://localhost:8000/#category={cat[0]}</loc>',
                '    <changefreq>weekly</changefreq>',
                '    <priority>0.8</priority>',
                '  </url>'
            ])

        # 500 Product URLs
        for p in products:
            slug = p[0] or p[1]
            lastmod = p[3].split('T')[0] if p[3] and 'T' in p[3] else datetime.now().strftime('%Y-%m-%d')
            xml_lines.extend([
                '  <url>',
                f'    <loc>http://localhost:8000/#product={slug}</loc>',
                f'    <lastmod>{lastmod}</lastmod>',
                '    <changefreq>weekly</changefreq>',
                '    <priority>0.9</priority>',
                '  </url>'
            ])

        xml_lines.append('</urlset>')
        xml_content = "\n".join(xml_lines)
        xml_bytes = xml_content.encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/xml; charset=utf-8')
        self.send_header('Content-Length', str(len(xml_bytes)))
        self.end_headers()
        self.wfile.write(xml_bytes)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/'):
            content_length = int(self.headers.get('Content-Length', 0))
            body_raw = self.rfile.read(content_length) if content_length > 0 else b'{}'
            try:
                data = json.loads(body_raw.decode('utf-8'))
            except Exception:
                data = {}

            try:
                self.handle_api_post(path, data)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json(500, {"error": str(e)})
            return

        self.send_json(404, {"error": "Endpoint not found"})

    def handle_api_get(self, path, query):
        conn = get_db()
        cursor = conn.cursor()

        # Admin: Stats & KPI Metrics
        if path == '/api/admin/stats':
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(stock), 0), COALESCE(SUM(stock * price_usd), 0), COALESCE(SUM(stock * price_try), 0) FROM products")
            row = cursor.fetchone()
            total_products, total_stock, total_val_usd, total_val_try = row[0], row[1], row[2], row[3]

            cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= 5 AND stock > 0")
            low_stock_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM products WHERE stock = 0")
            out_of_stock_count = cursor.fetchone()[0]

            cursor.execute('''
                SELECT c.id, c.name_en, c.name_tr, COUNT(p.id) as count, COALESCE(SUM(p.stock), 0) as category_stock
                FROM categories c
                LEFT JOIN products p ON c.id = p.category_id
                GROUP BY c.id
                ORDER BY count DESC
            ''')
            categories_stats = [dict(r) for r in cursor.fetchall()]
            conn.close()

            self.send_json(200, {
                "total_products": total_products,
                "total_stock": total_stock,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "total_val_usd": round(total_val_usd, 2),
                "total_val_try": round(total_val_try, 2),
                "categories_stats": categories_stats
            })
            return

        # Admin: Products Inventory List with Search, Filter & Stock Status
        if path == '/api/admin/products':
            q = query.get('q', [''])[0].strip()
            cat = query.get('category', ['all'])[0]
            brand = query.get('brand', ['all'])[0]
            stock_status = query.get('stock_status', ['all'])[0]
            sort_by = query.get('sort', ['id_asc'])[0]
            page = max(1, int(query.get('page', [1])[0]))
            limit = min(500, max(1, int(query.get('limit', [50])[0])))

            where_clauses = ["1=1"]
            params = []

            if q:
                where_clauses.append("(p.name_en LIKE ? OR p.name_tr LIKE ? OR p.brand LIKE ? OR p.sku LIKE ? OR p.id LIKE ?)")
                like_str = f"%{q}%"
                params.extend([like_str, like_str, like_str, like_str, like_str])

            if cat and cat != 'all':
                where_clauses.append("p.category_id = ?")
                params.append(cat)

            if brand and brand != 'all':
                where_clauses.append("p.brand = ?")
                params.append(brand)

            if stock_status == 'low_stock':
                where_clauses.append("p.stock <= 5 AND p.stock > 0")
            elif stock_status == 'out_of_stock':
                where_clauses.append("p.stock = 0")
            elif stock_status == 'in_stock':
                where_clauses.append("p.stock > 0")

            where_sql = " AND ".join(where_clauses)

            sort_map = {
                'id_asc': 'p.id ASC',
                'id_desc': 'p.id DESC',
                'stock_asc': 'p.stock ASC',
                'stock_desc': 'p.stock DESC',
                'price_usd_asc': 'p.price_usd ASC',
                'price_usd_desc': 'p.price_usd DESC',
                'price_try_asc': 'p.price_try ASC',
                'price_try_desc': 'p.price_try DESC',
                'name_asc': 'p.name_en ASC',
                'discount_desc': 'p.discount_pct DESC'
            }
            sort_sql = sort_map.get(sort_by, 'p.id ASC')

            count_query = f"SELECT COUNT(*) FROM products p WHERE {where_sql}"
            cursor.execute(count_query, params)
            total_items = cursor.fetchone()[0]

            offset = (page - 1) * limit
            data_query = f'''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE {where_sql}
                ORDER BY {sort_sql}
                LIMIT ? OFFSET ?
            '''
            cursor.execute(data_query, params + [limit, offset])
            rows = cursor.fetchall()
            products = []
            for r in rows:
                p = dict(r)
                p['specs'] = json.loads(p['specs_json']) if p.get('specs_json') else {}
                p['tags'] = json.loads(p['tags_json']) if p.get('tags_json') else []
                p['gallery'] = json.loads(p['gallery_json'] or '[]')
                p['compatibility'] = json.loads(p['compatibility_json'] or '{}')
                products.append(p)

            conn.close()
            self.send_json(200, {
                "products": products,
                "total": total_items,
                "page": page,
                "limit": limit,
                "total_pages": (total_items + limit - 1) // limit if limit > 0 else 1
            })
            return

        # Admin: Registered Users List
        if path == '/api/admin/users':
            cursor.execute('''
                SELECT id, email, full_name, avatar_url, provider, role, phone, address, city, country, created_at 
                FROM users 
                ORDER BY created_at DESC
            ''')
            user_rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            self.send_json(200, {"users": user_rows, "total": len(user_rows)})
            return

        # 1. Categories
        if path == '/api/categories':
            cursor.execute("SELECT * FROM categories ORDER BY item_count DESC")
            categories = [dict(row) for row in cursor.fetchall()]
            conn.close()
            self.send_json(200, {"categories": categories})
            return

        # 2. Brands list
        if path == '/api/brands':
            cat = query.get('category', [None])[0]
            if cat and cat != 'all':
                cursor.execute("SELECT DISTINCT brand FROM products WHERE category_id = ? ORDER BY brand ASC", (cat,))
            else:
                cursor.execute("SELECT DISTINCT brand FROM products ORDER BY brand ASC")
            brands = [r[0] for r in cursor.fetchall()]
            conn.close()
            self.send_json(200, {"brands": brands})
            return

        # 3. Single Product: /api/products/<id_or_slug>
        prod_match = re.match(r'^/api/products/([a-zA-Z0-9_-]+)$', path)
        if prod_match:
            item_id = prod_match.group(1)
            cursor.execute('''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.id = ? OR p.slug = ?
            ''', (item_id, item_id))
            row = cursor.fetchone()
            if not row:
                conn.close()
                self.send_json(404, {"error": "Product not found"})
                return

            prod = dict(row)
            prod['specs'] = json.loads(prod['specs_json'])
            prod['tags'] = json.loads(prod['tags_json'])
            prod['gallery'] = json.loads(prod['gallery_json'] or '[]')
            prod['compatibility'] = json.loads(prod['compatibility_json'] or '{}')

            # Fetch product reviews
            cursor.execute("SELECT * FROM reviews WHERE product_id = ? ORDER BY created_at DESC", (prod['id'],))
            reviews = [dict(r) for r in cursor.fetchall()]
            prod['reviews'] = reviews

            # Fetch related items
            cursor.execute('''
                SELECT id, slug, sku, name_en, name_tr, category_id, brand, price_usd, price_try, rating, review_count, stock, badge, image_url
                FROM products
                WHERE category_id = ? AND id != ?
                ORDER BY rating DESC LIMIT 6
            ''', (prod['category_id'], prod['id']))
            prod['related'] = [dict(r) for r in cursor.fetchall()]

            conn.close()
            self.send_json(200, {"product": prod})
            return

        # 4. Products List (Search, Filter, Pagination, Sort)
        if path == '/api/products':
            q = query.get('q', [''])[0].strip()
            cat = query.get('category', ['all'])[0]
            brand = query.get('brand', ['all'])[0]
            voltage = query.get('voltage', ['all'])[0]
            in_stock = query.get('in_stock', ['0'])[0]
            featured_only = query.get('featured', ['0'])[0]
            bestseller_only = query.get('bestseller', ['0'])[0]
            sort_by = query.get('sort', ['popular'])[0]
            page = max(1, int(query.get('page', [1])[0]))
            limit = min(100, max(1, int(query.get('limit', [24])[0])))
            min_p = float(query.get('min_price', [0])[0])
            max_p = float(query.get('max_price', [99999])[0])
            currency = query.get('currency', ['USD'])[0].upper()

            where_clauses = ["1=1"]
            params = []

            if q:
                where_clauses.append("(p.name_en LIKE ? OR p.name_tr LIKE ? OR p.brand LIKE ? OR p.sku LIKE ? OR p.tags_json LIKE ?)")
                like_str = f"%{q}%"
                params.extend([like_str, like_str, like_str, like_str, like_str])

            if cat and cat != 'all':
                where_clauses.append("p.category_id = ?")
                params.append(cat)

            if brand and brand != 'all':
                where_clauses.append("p.brand = ?")
                params.append(brand)

            if voltage and voltage != 'all':
                where_clauses.append("p.specs_json LIKE ?")
                params.append(f"%{voltage}%")

            if in_stock == '1':
                where_clauses.append("p.stock > 0")

            if featured_only == '1':
                where_clauses.append("p.featured = 1")

            if bestseller_only == '1':
                where_clauses.append("p.is_bestseller = 1")

            # Price filter
            if currency == 'TRY':
                where_clauses.append("p.price_try >= ? AND p.price_try <= ?")
                params.extend([min_p, max_p])
            else:
                where_clauses.append("p.price_usd >= ? AND p.price_usd <= ?")
                params.extend([min_p, max_p])

            where_sql = " AND ".join(where_clauses)

            # Sort mappings
            sort_sql = "p.rating DESC, p.review_count DESC"
            if sort_by == 'price_asc':
                sort_sql = "p.price_usd ASC" if currency == 'USD' else "p.price_try ASC"
            elif sort_by == 'price_desc':
                sort_sql = "p.price_usd DESC" if currency == 'USD' else "p.price_try DESC"
            elif sort_by == 'rating':
                sort_sql = "p.rating DESC, p.review_count DESC"
            elif sort_by == 'newest':
                sort_sql = "p.created_at DESC"
            elif sort_by == 'discount':
                sort_sql = "p.discount_pct DESC"

            # Total Count Query
            count_query = f"SELECT COUNT(*) FROM products p WHERE {where_sql}"
            cursor.execute(count_query, params)
            total_items = cursor.fetchone()[0]

            # Paginated Data Query
            offset = (page - 1) * limit
            data_query = f'''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE {where_sql}
                ORDER BY {sort_sql}
                LIMIT ? OFFSET ?
            '''
            cursor.execute(data_query, params + [limit, offset])
            rows = cursor.fetchall()
            products = []
            for r in rows:
                p = dict(r)
                p['specs'] = json.loads(p['specs_json'])
                p['tags'] = json.loads(p['tags_json'])
                p['gallery'] = json.loads(p['gallery_json'] or '[]')
                products.append(p)

            conn.close()
            self.send_json(200, {
                "products": products,
                "total": total_items,
                "page": page,
                "limit": limit,
                "total_pages": (total_items + limit - 1) // limit
            })
            return

        # 5. Order lookup: /api/orders/<order_number>
        order_match = re.match(r'^/api/orders/([a-zA-Z0-9_-]+)$', path)
        if order_match:
            order_num = order_match.group(1)
            cursor.execute("SELECT * FROM orders WHERE order_number = ? OR id = ?", (order_num, order_num))
            order = cursor.fetchone()
            conn.close()
            if not order:
                self.send_json(404, {"error": "Order not found"})
                return
            od = dict(order)
            od['items'] = json.loads(od['items_json'])
            self.send_json(200, {"order": od})
            return

        # 6. User Orders: /api/orders/user/<user_id>
        user_orders_match = re.match(r'^/api/orders/user/([a-zA-Z0-9_-]+)$', path)
        if user_orders_match:
            user_id = user_orders_match.group(1)
            cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            orders = []
            for r in cursor.fetchall():
                od = dict(r)
                od['items'] = json.loads(od['items_json'])
                orders.append(od)
            conn.close()
            self.send_json(200, {"orders": orders})
            return

        conn.close()
        self.send_json(404, {"error": "API route not found"})

    def handle_api_post(self, path, data):
        conn = get_db()
        cursor = conn.cursor()

        # 1. Manual User Registration
        if path == '/api/auth/register':
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            full_name = data.get('full_name', '').strip()
            phone = data.get('phone', '')
            address = data.get('address', '')
            city = data.get('city', '')

            if not email or not password or not full_name:
                conn.close()
                self.send_json(400, {"error": "Email, password, and full name are required."})
                return

            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                self.send_json(400, {"error": "An account with this email already exists."})
                return

            user_id = str(uuid.uuid4())
            pw_hash = hash_password(password)
            now = datetime.now().isoformat()
            avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={urllib.parse.quote(full_name)}"

            cursor.execute('''
                INSERT INTO users (id, email, password_hash, full_name, avatar_url, provider, role, phone, address, city, country, created_at)
                VALUES (?, ?, ?, ?, ?, 'manual', 'customer', ?, ?, ?, 'Turkey', ?)
            ''', (user_id, email, pw_hash, full_name, avatar, phone, address, city, now))
            conn.commit()

            cursor.execute("SELECT id, email, full_name, avatar_url, provider, role, phone, address, city, country FROM users WHERE id = ?", (user_id,))
            user_data = dict(cursor.fetchone())
            conn.close()

            self.send_json(201, {
                "success": True,
                "message": "Account created successfully!",
                "user": user_data,
                "token": f"pztr_token_{user_id[:8]}"
            })
            return

        # 2. Manual User Login with Brute-Force & Cooldown Protection (3 attempts -> 30 min cooldown)
        if path == '/api/auth/login':
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            client_ip = self.client_address[0] if self.client_address else "127.0.0.1"

            if not email or not password:
                conn.close()
                self.send_json(400, {"error": "Email and password are required."})
                return

            # Check if email is currently locked (3 failed attempts -> 30 min cooldown)
            is_locked, rem_sec, rem_min, attempts_left = check_login_rate_limit(email)

            if is_locked:
                conn.close()
                self.send_json(429, {
                    "error": f"🛡️ Güvenlik Koruması: 3 kez hatalı deneme yapıldığı için bu hesap kilitlendi! Lütfen {rem_min} dakika sonra tekrar deneyiniz.",
                    "locked": True,
                    "remaining_seconds": rem_sec,
                    "remaining_minutes": rem_min
                })
                return

            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if not user or dict(user).get('password_hash') != hash_password(password):
                conn.close()
                is_now_locked, rem_sec, rem_min, left = record_failed_login(email)
                
                if is_now_locked:
                    self.send_json(429, {
                        "error": "🛡️ 3 kez hatalı giriş yapıldı! Güvenlik nedeniyle hesabınız 30 dakika süreyle kilitlenmiştir.",
                        "locked": True,
                        "remaining_seconds": rem_sec,
                        "remaining_minutes": rem_min
                    })
                else:
                    self.send_json(401, {
                        "error": f"❌ Hatalı şifre veya e-posta! Kalan deneme hakkınız: {left}",
                        "attempts_left": left,
                        "locked": False
                    })
                return

            # Successful login - Clear failed attempts for this email
            clear_login_attempts(email)

            user_dict = dict(user)
            if 'password_hash' in user_dict:
                del user_dict['password_hash']
            conn.close()

            self.send_json(200, {
                "success": True,
                "message": "Login successful!",
                "user": user_dict,
                "token": f"pztr_token_{user_dict['id'][:8]}"
            })
            return

        # 3. Google / Gmail Sign-In Simulation
        if path == '/api/auth/google':
            email = data.get('email', '').strip().lower()
            full_name = data.get('full_name', '').strip() or email.split('@')[0].capitalize()
            avatar_url = data.get('avatar_url', f"https://api.dicebear.com/7.x/bottts/svg?seed={email}")

            if not email:
                conn.close()
                self.send_json(400, {"error": "Google email is required."})
                return

            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if user:
                user_dict = dict(user)
                if 'password_hash' in user_dict:
                    del user_dict['password_hash']
                # Grant admin to known admin emails or gmail users
                if user_dict.get('role') != 'admin' and ('furkan' in email or 'eyup' in email or 'thepeak' in email or user_dict.get('provider') == 'gmail'):
                    cursor.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_dict['id'],))
                    conn.commit()
                    user_dict['role'] = 'admin'
            else:
                user_id = str(uuid.uuid4())
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO users (id, email, password_hash, full_name, avatar_url, provider, role, created_at)
                    VALUES (?, ?, NULL, ?, ?, 'gmail', 'admin', ?)
                ''', (user_id, email, full_name, avatar_url, now))
                conn.commit()

                cursor.execute("SELECT id, email, full_name, avatar_url, provider, role, phone, address, city, country FROM users WHERE id = ?", (user_id,))
                user_dict = dict(cursor.fetchone())

            conn.close()
            self.send_json(200, {
                "success": True,
                "message": "Authenticated with Google successfully!",
                "user": user_dict,
                "token": f"pztr_google_{user_dict['id'][:8]}"
            })
            return

        # 4. Coupon Validation
        if path == '/api/coupons/validate':
            code = data.get('code', '').strip().upper()
            subtotal_usd = float(data.get('subtotal_usd', 0))
            subtotal_try = float(data.get('subtotal_try', 0))

            cursor.execute("SELECT * FROM coupons WHERE code = ? AND is_active = 1", (code,))
            coupon = cursor.fetchone()
            conn.close()

            if not coupon:
                self.send_json(400, {"valid": False, "error": "Invalid or expired coupon code."})
                return

            c_dict = dict(coupon)
            if subtotal_usd < c_dict['min_order_usd']:
                self.send_json(400, {
                    "valid": False,
                    "error": f"Minimum order amount for this coupon is ${c_dict['min_order_usd']} / {c_dict['min_order_try']}₺."
                })
                return

            if c_dict['discount_type'] == 'percent':
                discount_usd = round(subtotal_usd * (c_dict['discount_value'] / 100.0), 2)
                discount_try = round(subtotal_try * (c_dict['discount_value'] / 100.0), 2)
            else:
                discount_usd = min(subtotal_usd, c_dict['discount_value'])
                discount_try = min(subtotal_try, c_dict['discount_value'] * 35.5)

            self.send_json(200, {
                "valid": True,
                "code": code,
                "discount_type": c_dict['discount_type'],
                "discount_value": c_dict['discount_value'],
                "discount_usd": discount_usd,
                "discount_try": discount_try,
                "description_en": c_dict['description_en'],
                "description_tr": c_dict['description_tr']
            })
            return

        # 5. Payment & Checkout Processing
        if path == '/api/payment/process':
            items = data.get('items', [])
            if not items:
                conn.close()
                self.send_json(400, {"error": "Your cart is empty."})
                return

            customer_name = data.get('customer_name', '').strip()
            customer_email = data.get('customer_email', '').strip()
            customer_phone = data.get('customer_phone', '').strip()
            shipping_address = data.get('shipping_address', '').strip()
            city = data.get('city', '').strip()
            country = data.get('country', 'Turkey').strip()
            currency = data.get('currency', 'USD').upper()
            payment_method = data.get('payment_method', 'credit_card')
            coupon_code = data.get('coupon_code', '')
            user_id = data.get('user_id', None)

            # Payment validation
            card_number = data.get('card_number', '').replace(' ', '')
            card_holder = data.get('card_holder', '')
            card_expiry = data.get('card_expiry', '')
            card_cvv = data.get('card_cvv', '')
            is_3d_secure = data.get('is_3d_secure', True)

            if payment_method == 'credit_card':
                if not card_number or not card_expiry or not card_cvv:
                    conn.close()
                    self.send_json(400, {"error": "Complete credit card details are required."})
                    return

                # Luhn algorithm check
                if not luhn_validate(card_number):
                    conn.close()
                    self.send_json(400, {"error": "Invalid credit card number. Please check card digits."})
                    return

            # Determine Card Brand
            card_brand = "Visa"
            if card_number.startswith('4'):
                card_brand = "Visa"
            elif card_number.startswith(('51', '52', '53', '54', '55')) or (len(card_number) >= 4 and 2221 <= int(card_number[:4]) <= 2720):
                card_brand = "MasterCard"
            elif card_number.startswith('9792'):
                card_brand = "Troy"
            elif card_number.startswith(('34', '37')):
                card_brand = "American Express"

            # Calculate Subtotals and verify stock
            subtotal_usd = 0.0
            subtotal_try = 0.0
            processed_items = []

            for item in items:
                prod_id = item.get('id')
                qty = max(1, int(item.get('quantity', 1)))
                cursor.execute("SELECT id, name_en, name_tr, brand, price_usd, price_try, stock, image_url, sku FROM products WHERE id = ?", (prod_id,))
                prod = cursor.fetchone()
                if not prod:
                    continue
                p_dict = dict(prod)
                
                # Check & update stock
                new_stock = max(0, p_dict['stock'] - qty)
                cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, prod_id))

                item_usd = round(p_dict['price_usd'] * qty, 2)
                item_try = round(p_dict['price_try'] * qty, 2)
                subtotal_usd += item_usd
                subtotal_try += item_try

                processed_items.append({
                    "id": p_dict['id'],
                    "sku": p_dict['sku'],
                    "name_en": p_dict['name_en'],
                    "name_tr": p_dict['name_tr'],
                    "brand": p_dict['brand'],
                    "price_usd": p_dict['price_usd'],
                    "price_try": p_dict['price_try'],
                    "quantity": qty,
                    "total_usd": item_usd,
                    "total_try": item_try,
                    "image_url": p_dict['image_url']
                })

            # Calculate Discount
            discount_usd = 0.0
            discount_try = 0.0
            if coupon_code:
                cursor.execute("SELECT * FROM coupons WHERE code = ? AND is_active = 1", (coupon_code.upper(),))
                coupon = cursor.fetchone()
                if coupon:
                    c = dict(coupon)
                    if subtotal_usd >= c['min_order_usd']:
                        if c['discount_type'] == 'percent':
                            discount_usd = round(subtotal_usd * (c['discount_value'] / 100.0), 2)
                            discount_try = round(subtotal_try * (c['discount_value'] / 100.0), 2)
                        else:
                            discount_usd = min(subtotal_usd, c['discount_value'])
                            discount_try = min(subtotal_try, c['discount_value'] * 35.5)

            # Shipping fees (Free for orders > $150 or > 5000 TRY)
            shipping_fee_usd = 0.0 if subtotal_usd >= 150.0 else 9.99
            shipping_fee_try = 0.0 if subtotal_try >= 5000.0 else 350.0

            total_usd = max(0.0, round(subtotal_usd - discount_usd + shipping_fee_usd, 2))
            total_try = max(0.0, round(subtotal_try - discount_try + shipping_fee_try, 2))

            order_id = str(uuid.uuid4())
            order_number = f"PZT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            tracking_number = f"TRK-{random.randint(100000000, 999999999)}"
            transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
            card_last4 = card_number[-4:] if card_number else "0000"
            now_iso = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO orders (
                    id, order_number, user_id, customer_name, customer_email, customer_phone,
                    shipping_address, city, country, items_json,
                    subtotal_usd, subtotal_try, discount_usd, discount_try,
                    shipping_fee_usd, shipping_fee_try, total_usd, total_try,
                    currency, payment_method, payment_status, card_last4, card_brand,
                    transaction_id, order_status, tracking_number, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PAID', ?, ?, ?, 'CONFIRMED', ?, 'Standard FPV Express Dispatch', ?)
            ''', (
                order_id, order_number, user_id, customer_name, customer_email, customer_phone,
                shipping_address, city, country, json.dumps(processed_items),
                subtotal_usd, subtotal_try, discount_usd, discount_try,
                shipping_fee_usd, shipping_fee_try, total_usd, total_try,
                currency, payment_method, card_last4, card_brand,
                transaction_id, tracking_number, now_iso
            ))
            conn.commit()
            conn.close()

            self.send_json(200, {
                "success": True,
                "order_number": order_number,
                "order_id": order_id,
                "tracking_number": tracking_number,
                "transaction_id": transaction_id,
                "status": "CONFIRMED",
                "payment_status": "PAID",
                "card_brand": card_brand,
                "card_last4": card_last4,
                "currency": currency,
                "subtotal_usd": subtotal_usd,
                "subtotal_try": subtotal_try,
                "discount_usd": discount_usd,
                "discount_try": discount_try,
                "shipping_fee_usd": shipping_fee_usd,
                "shipping_fee_try": shipping_fee_try,
                "total_usd": total_usd,
                "total_try": total_try,
                "items": processed_items,
                "shipping_address": f"{shipping_address}, {city}, {country}",
                "customer_name": customer_name,
                "customer_email": customer_email,
                "created_at": now_iso
            })
            return

        # 6. Add Review
        if path == '/api/reviews':
            product_id = data.get('product_id')
            user_name = data.get('user_name', 'Anonymous Pilot')
            rating = max(1, min(5, int(data.get('rating', 5))))
            title = data.get('title', '')
            comment = data.get('comment', '').strip()

            if not product_id or not comment:
                conn.close()
                self.send_json(400, {"error": "Product ID and comment are required."})
                return

            rev_id = str(uuid.uuid4())
            now_iso = datetime.now().isoformat()
            avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={urllib.parse.quote(user_name)}"

            cursor.execute('''
                INSERT INTO reviews (id, product_id, user_name, user_avatar, rating, title, comment, verified_purchase, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
            ''', (rev_id, product_id, user_name, avatar, rating, title, comment, now_iso))

            # Recalculate product rating
            cursor.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id = ?", (product_id,))
            avg_r, count_r = cursor.fetchone()
            cursor.execute("UPDATE products SET rating = ?, review_count = ? WHERE id = ?", (round(avg_r, 1), count_r, product_id))

            conn.commit()
            conn.close()

            self.send_json(201, {
                "success": True,
                "review": {
                    "id": rev_id,
                    "product_id": product_id,
                    "user_name": user_name,
                    "user_avatar": avatar,
                    "rating": rating,
                    "title": title,
                    "comment": comment,
                    "created_at": now_iso
                }
            })
            return

        # 7. Drone Compatibility Builder Checker
        if path == '/api/builder/check':
            motor_id = data.get('motor_id')
            esc_id = data.get('esc_id')
            prop_id = data.get('prop_id')
            battery_id = data.get('battery_id')

            warnings = []
            recommendations = []
            score = 100

            # Inspect items from database
            selected = {}
            for k, pid in [('motor', motor_id), ('esc', esc_id), ('prop', prop_id), ('battery', battery_id)]:
                if pid:
                    cursor.execute("SELECT * FROM products WHERE id = ?", (pid,))
                    r = cursor.fetchone()
                    if r:
                        selected[k] = dict(r)
                        selected[k]['specs'] = json.loads(selected[k]['specs_json'])

            conn.close()

            # Compatibility Rules Engine
            if 'battery' in selected and 'motor' in selected:
                bat_name = selected['battery']['name_en']
                motor_name = selected['motor']['name_en']
                if "6S" in bat_name and "2400KV" in motor_name:
                    warnings.append({"en": "Motor KV (2400KV+) is dangerously high for 6S LiPo! Recommended KV for 6S is 1700KV - 1950KV.", "tr": "Motor KV değeri (2400KV+) 6S LiPo için çok yüksek! 6S için önerilen KV: 1700KV - 1950KV."})
                    score -= 30
                elif "4S" in bat_name and "1750KV" in motor_name:
                    recommendations.append({"en": "1750KV motor on 4S will feel underpowered. 2400KV-2750KV is optimal for 4S freestyle.", "tr": "4S pilde 1750KV motor düşük güç hissettirebilir. 4S freestyle için 2400KV-2750KV idealdir."})

            if 'esc' in selected and 'motor' in selected:
                esc_name = selected['esc']['name_en']
                if "45A" in esc_name and "2807" in selected['motor']['name_en']:
                    warnings.append({"en": "2807 Long Range motors with heavy 7-inch props may exceed 45A ESC limits. Consider 55A+ ESC.", "tr": "Ağır 7 inç pervaneli 2807 motorlar 45A ESC limitini aşabilir. 55A+ ESC önerilir."})
                    score -= 20

            self.send_json(200, {
                "compatibility_score": max(0, score),
                "is_compatible": len(warnings) == 0,
                "warnings": warnings,
                "recommendations": recommendations,
                "parts_selected": list(selected.keys())
            })
            return

        # 8. Admin: Update Single Product (Stock, Prices, Metadata)
        if path == '/api/admin/products/update':
            prod_id = data.get('id')
            if not prod_id:
                conn.close()
                self.send_json(400, {"error": "Product ID is required"})
                return

            cursor.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
            existing = cursor.fetchone()
            if not existing:
                conn.close()
                self.send_json(404, {"error": "Product not found"})
                return

            curr = dict(existing)

            stock = int(data.get('stock', curr['stock']))
            stock = max(0, stock)

            price_usd = float(data.get('price_usd', curr['price_usd']))
            price_try = float(data.get('price_try', curr['price_try']))
            if 'price_usd' in data and 'price_try' not in data:
                price_try = round(price_usd * 47.0, 2)

            orig_price_usd = float(data['original_price_usd']) if data.get('original_price_usd') is not None and data['original_price_usd'] != '' else curr['original_price_usd']
            orig_price_try = float(data['original_price_try']) if data.get('original_price_try') is not None and data['original_price_try'] != '' else curr['original_price_try']
            discount_pct = int(data.get('discount_pct', curr['discount_pct']))

            name_en = data.get('name_en', curr['name_en'])
            name_tr = data.get('name_tr', curr['name_tr'])
            category_id = data.get('category_id', curr['category_id'])
            brand = data.get('brand', curr['brand'])
            badge = data.get('badge', curr['badge'])
            featured = int(data.get('featured', curr['featured']))
            is_bestseller = int(data.get('is_bestseller', curr['is_bestseller']))
            image_url = data.get('image_url', curr['image_url'])

            cursor.execute('''
                UPDATE products SET
                    stock = ?,
                    price_usd = ?,
                    price_try = ?,
                    original_price_usd = ?,
                    original_price_try = ?,
                    discount_pct = ?,
                    name_en = ?,
                    name_tr = ?,
                    category_id = ?,
                    brand = ?,
                    badge = ?,
                    featured = ?,
                    is_bestseller = ?,
                    image_url = ?
                WHERE id = ?
            ''', (
                stock, price_usd, price_try, orig_price_usd, orig_price_try, discount_pct,
                name_en, name_tr, category_id, brand, badge, featured, is_bestseller, image_url, prod_id
            ))
            conn.commit()

            cursor.execute('''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.id = ?
            ''', (prod_id,))
            updated_prod = dict(cursor.fetchone())
            updated_prod['specs'] = json.loads(updated_prod['specs_json']) if updated_prod.get('specs_json') else {}
            updated_prod['tags'] = json.loads(updated_prod['tags_json']) if updated_prod.get('tags_json') else []
            updated_prod['gallery'] = json.loads(updated_prod['gallery_json'] or '[]')
            conn.close()

            self.send_json(200, {
                "success": True,
                "message": "Product updated successfully",
                "product": updated_prod
            })
            return

        # 9. Admin: Bulk Operations (Stock increment/set, Price multiplier/discount, FX Sync)
        if path == '/api/admin/products/bulk':
            prod_ids = data.get('product_ids', [])
            action = data.get('action')
            value = data.get('value', 0)

            if not prod_ids or not action:
                conn.close()
                self.send_json(400, {"error": "product_ids and action are required"})
                return

            placeholders = ",".join("?" for _ in prod_ids)

            if action == 'stock_increment':
                inc_val = int(value)
                cursor.execute(f'''
                    UPDATE products
                    SET stock = CASE WHEN stock + ? < 0 THEN 0 ELSE stock + ? END
                    WHERE id IN ({placeholders})
                ''', [inc_val, inc_val] + prod_ids)

            elif action == 'stock_set':
                set_val = max(0, int(value))
                cursor.execute(f'''
                    UPDATE products
                    SET stock = ?
                    WHERE id IN ({placeholders})
                ''', [set_val] + prod_ids)

            elif action == 'price_percent':
                factor = 1.0 + (float(value) / 100.0)
                if factor <= 0:
                    factor = 0.01
                cursor.execute(f'''
                    UPDATE products
                    SET price_usd = ROUND(price_usd * ?, 2),
                        price_try = ROUND(price_try * ?, 2),
                        original_price_usd = CASE WHEN original_price_usd IS NOT NULL THEN ROUND(original_price_usd * ?, 2) ELSE NULL END,
                        original_price_try = CASE WHEN original_price_try IS NOT NULL THEN ROUND(original_price_try * ?, 2) ELSE NULL END
                    WHERE id IN ({placeholders})
                ''', [factor, factor, factor, factor] + prod_ids)

            elif action == 'discount_set':
                disc_val = max(0, min(99, int(value)))
                cursor.execute(f'''
                    UPDATE products
                    SET discount_pct = ?
                    WHERE id IN ({placeholders})
                ''', [disc_val] + prod_ids)

            elif action == 'currency_sync':
                rate = float(value) if value else 47.0
                cursor.execute(f'''
                    UPDATE products
                    SET price_try = ROUND(price_usd * ?, 2),
                        original_price_try = CASE WHEN original_price_usd IS NOT NULL THEN ROUND(original_price_usd * ?, 2) ELSE NULL END
                    WHERE id IN ({placeholders})
                ''', [rate, rate] + prod_ids)

            conn.commit()
            conn.close()

            self.send_json(200, {
                "success": True,
                "action": action,
                "updated_count": len(prod_ids)
            })
            return

        # 10. Admin: Create New Product
        if path == '/api/admin/products/create':
            name_en = data.get('name_en', '').strip()
            name_tr = data.get('name_tr', '').strip() or name_en
            category_id = data.get('category_id', 'motors')
            brand = data.get('brand', 'Pozitron')
            price_usd = float(data.get('price_usd', 29.99))
            price_try = float(data.get('price_try', round(price_usd * 47.0, 2)))
            stock = max(0, int(data.get('stock', 50)))
            badge = data.get('badge', 'NEW')
            image_url = data.get('image_url', 'https://images.unsplash.com/photo-1527977966376-1c8408f9f108?auto=format&fit=crop&w=600&q=80')
            sku = data.get('sku', '').strip() or f"PZT-{category_id[:4].upper()}-{random.randint(1000, 9999)}"
            slug = re.sub(r'[^a-zA-Z0-9_-]', '-', name_en.lower()).strip('-') + f"-{random.randint(100, 999)}"
            prod_id = f"pzt_{uuid.uuid4().hex[:8]}"
            now_iso = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO products (
                    id, slug, sku, name_en, name_tr, category_id, brand,
                    price_usd, price_try, original_price_usd, original_price_try,
                    discount_pct, rating, review_count, stock, badge,
                    specs_json, tags_json, image_url, gallery_json,
                    description_en, description_tr, compatibility_json,
                    featured, is_bestseller, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0, 5.0, 0, ?, ?, '{}', '[]', ?, '[]', ?, ?, '{}', 0, 0, ?)
            ''', (
                prod_id, slug, sku, name_en, name_tr, category_id, brand,
                price_usd, price_try, stock, badge, image_url,
                data.get('description_en', name_en), data.get('description_tr', name_tr), now_iso
            ))

            cursor.execute("UPDATE categories SET item_count = item_count + 1 WHERE id = ?", (category_id,))
            conn.commit()

            cursor.execute('''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.id = ?
            ''', (prod_id,))
            new_prod = dict(cursor.fetchone())
            new_prod['specs'] = {}
            new_prod['tags'] = []
            new_prod['gallery'] = []
            conn.close()

            self.send_json(201, {
                "success": True,
                "message": "Product created successfully",
                "product": new_prod
            })
            return

        # 11. Admin: Delete Product
        if path == '/api/admin/products/delete':
            prod_id = data.get('id')
            if not prod_id:
                conn.close()
                self.send_json(400, {"error": "Product ID is required"})
                return

            cursor.execute("SELECT category_id FROM products WHERE id = ?", (prod_id,))
            p = cursor.fetchone()
            if p:
                cat_id = p[0]
                cursor.execute("DELETE FROM products WHERE id = ?", (prod_id,))
                cursor.execute("UPDATE categories SET item_count = MAX(0, item_count - 1) WHERE id = ?", (cat_id,))
                conn.commit()

            conn.close()
            self.send_json(200, {"success": True, "deleted_id": prod_id})
            return

        # Admin: Delete User
        if path == '/api/admin/users/delete':
            user_id = data.get('id')
            email = (data.get('email') or '').lower().strip()

            if not user_id and not email:
                conn.close()
                self.send_json(400, {"error": "User ID or Email is required"})
                return

            admin_emails = ['furkaniusprimes@gmail.com', 'thepeakiscold@gmail.com', 'eyupfurkanpekoz@gmail.com', 'eyuppekoz@gmail.com', 'pekozfurkan@gmail.com', 'pozitronmarket@gmail.com']
            if email in admin_emails:
                conn.close()
                self.send_json(403, {"error": "Yönetici Gmail hesabı silinemez."})
                return

            if user_id:
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            elif email:
                cursor.execute("DELETE FROM users WHERE LOWER(email) = ?", (email,))

            conn.commit()
            conn.close()

            self.send_json(200, {"success": True, "message": "Kullanıcı başarıyla silindi.", "deleted_id": user_id})
            return

        # 12. Admin: Currency Sync across catalog
        if path == '/api/admin/currency-sync':
            rate = float(data.get('usd_rate', 47.0))
            cat = data.get('category_id')
            brand = data.get('brand')

            where_clauses = ["1=1"]
            params = [rate, rate]

            if cat and cat != 'all':
                where_clauses.append("category_id = ?")
                params.append(cat)

            if brand and brand != 'all':
                where_clauses.append("brand = ?")
                params.append(brand)

            where_sql = " AND ".join(where_clauses)
            cursor.execute(f'''
                UPDATE products
                SET price_try = ROUND(price_usd * ?, 2),
                    original_price_try = CASE WHEN original_price_usd IS NOT NULL THEN ROUND(original_price_usd * ?, 2) ELSE NULL END
                WHERE {where_sql}
            ''', params)
            conn.commit()
            count = cursor.rowcount
            conn.close()

            self.send_json(200, {
                "success": True,
                "usd_rate": rate,
                "updated_count": count
            })
            return

        # 13. Admin: Export to static data files
        if path == '/api/admin/sync-export':
            conn.close()
            try:
                export_static_data()
                self.send_json(200, {
                    "success": True,
                    "message": "Static data bundle exported successfully to data/ folder"
                })
            except Exception as ex:
                self.send_json(500, {"error": f"Export failed: {str(ex)}"})
            return

        conn.close()
        self.send_json(404, {"error": "API route not found"})

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def run_server():
    global PORT
    ports_to_try = [int(os.environ.get('PORT', 8000)), 8080, 8081, 3000]
    httpd = None
    for p in ports_to_try:
        try:
            server_address = ('0.0.0.0', p)
            httpd = ThreadedHTTPServer(server_address, PozitronRequestHandler)
            PORT = p
            break
        except OSError as e:
            if "Address already in use" in str(e) or e.errno == 98:
                continue
            raise
    if not httpd:
        raise RuntimeError(f"Could not bind to any port in {ports_to_try}")
    print(f"==================================================")
    print(f" Pozitron Drone Shopping Platform Running on http://localhost:{PORT}")
    print(f" 500 Drone Items Active in SQLite Database")
    print(f" Languages: Turkish (TR) & English (EN)")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
