import sqlite3
import os
import json
import hashlib
import uuid
from datetime import datetime

DB_PATH = os.environ.get('DATABASE_PATH') or os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pozitron.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Categories Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id TEXT PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            name_en TEXT NOT NULL,
            name_tr TEXT NOT NULL,
            icon TEXT NOT NULL,
            description_en TEXT,
            description_tr TEXT,
            item_count INTEGER DEFAULT 0
        )
    ''')

    # Products Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            name_en TEXT NOT NULL,
            name_tr TEXT NOT NULL,
            category_id TEXT NOT NULL,
            brand TEXT NOT NULL,
            price_usd REAL NOT NULL,
            price_try REAL NOT NULL,
            original_price_usd REAL,
            original_price_try REAL,
            discount_pct INTEGER DEFAULT 0,
            rating REAL DEFAULT 4.8,
            review_count INTEGER DEFAULT 0,
            stock INTEGER DEFAULT 50,
            badge TEXT,
            specs_json TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            image_url TEXT NOT NULL,
            gallery_json TEXT,
            description_en TEXT NOT NULL,
            description_tr TEXT NOT NULL,
            compatibility_json TEXT,
            featured INTEGER DEFAULT 0,
            is_bestseller INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            full_name TEXT NOT NULL,
            avatar_url TEXT,
            provider TEXT DEFAULT 'manual', -- 'manual' or 'gmail'
            role TEXT DEFAULT 'customer',
            phone TEXT,
            address TEXT,
            city TEXT,
            country TEXT DEFAULT 'Turkey',
            created_at TEXT NOT NULL
        )
    ''')

    # Orders Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            order_number TEXT UNIQUE NOT NULL,
            user_id TEXT,
            customer_name TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_phone TEXT,
            shipping_address TEXT NOT NULL,
            city TEXT NOT NULL,
            country TEXT NOT NULL,
            shipping_district TEXT,
            billing_address TEXT,
            billing_city TEXT,
            billing_district TEXT,
            billing_country TEXT DEFAULT 'Turkey',
            invoice_type TEXT DEFAULT 'individual', -- 'individual' or 'corporate'
            tax_id TEXT, -- TCKN or VKN
            tax_office TEXT, -- Vergi Dairesi for corporate
            company_name TEXT, -- Şirket Ünvanı for corporate
            order_notes TEXT, -- Müşteri / Kurye Notu
            items_json TEXT NOT NULL,
            subtotal_usd REAL NOT NULL,
            subtotal_try REAL NOT NULL,
            discount_usd REAL DEFAULT 0,
            discount_try REAL DEFAULT 0,
            shipping_fee_usd REAL DEFAULT 0,
            shipping_fee_try REAL DEFAULT 0,
            total_usd REAL NOT NULL,
            total_try REAL NOT NULL,
            currency TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            payment_status TEXT NOT NULL,
            card_last4 TEXT,
            card_brand TEXT,
            transaction_id TEXT,
            order_status TEXT NOT NULL,
            tracking_number TEXT,
            notes TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    # User Addresses Table (Adres Defteri)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_addresses (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL, -- 'Ev', 'İş', 'Atölye', etc.
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            city TEXT NOT NULL,
            district TEXT NOT NULL,
            address_line TEXT NOT NULL,
            postal_code TEXT,
            is_default_shipping INTEGER DEFAULT 0,
            is_default_billing INTEGER DEFAULT 0,
            same_as_shipping INTEGER DEFAULT 1,
            billing_address_line TEXT,
            billing_city TEXT,
            billing_district TEXT,
            billing_country TEXT DEFAULT 'Turkey',
            invoice_type TEXT DEFAULT 'individual',
            tax_id TEXT,
            tax_office TEXT,
            company_name TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    # Migration: Ensure billing and invoice columns exist on user_addresses
    cursor.execute("PRAGMA table_info(user_addresses)")
    existing_addr_cols = [col[1] for col in cursor.fetchall()]
    addr_billing_migrations = [
        ('same_as_shipping', 'INTEGER DEFAULT 1'),
        ('billing_address_line', 'TEXT'),
        ('billing_city', 'TEXT'),
        ('billing_district', 'TEXT'),
        ('billing_country', "TEXT DEFAULT 'Turkey'"),
        ('invoice_type', "TEXT DEFAULT 'individual'"),
        ('tax_id', 'TEXT'),
        ('tax_office', 'TEXT'),
        ('company_name', 'TEXT')
    ]
    for col_name, col_type in addr_billing_migrations:
        if col_name not in existing_addr_cols:
            cursor.execute(f"ALTER TABLE user_addresses ADD COLUMN {col_name} {col_type}")

    # Password Resets Table (Şifremi Unuttum)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS password_resets (
            id TEXT PRIMARY KEY,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')

    # Reviews Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            product_id TEXT,
            user_name TEXT NOT NULL,
            user_avatar TEXT,
            rating INTEGER NOT NULL,
            title TEXT,
            comment TEXT NOT NULL,
            verified_purchase INTEGER DEFAULT 1,
            created_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    ''')

    # Coupons Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            code TEXT PRIMARY KEY,
            discount_type TEXT NOT NULL, -- 'percent' or 'fixed'
            discount_value REAL NOT NULL,
            min_order_usd REAL DEFAULT 0,
            min_order_try REAL DEFAULT 0,
            description_en TEXT,
            description_tr TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # Seed default coupons
    cursor.execute("SELECT count(*) FROM coupons")
    if cursor.fetchone()[0] == 0:
        default_coupons = [
            ('POZITRON10', 'percent', 10, 50, 1500, '10% discount on all orders above $50', '50$ ve üzeri tüm siparişlerde %10 indirim'),
            ('DRONE20', 'fixed', 20, 100, 3000, '$20 off on orders over $100', '100$ ve üzeri siparişlerde 20$ / 700₺ indirim'),
            ('WELCOME15', 'percent', 15, 30, 900, '15% welcome discount for new pilots', 'Yeni pilotlar için %15 hoş geldin indirimi'),
            ('FPVRACE', 'percent', 12, 40, 1200, '12% FPV racing component discount', 'FPV yarış bileşenlerinde %12 indirim')
        ]
        cursor.executemany('''
            INSERT INTO coupons (code, discount_type, discount_value, min_order_usd, min_order_try, description_en, description_tr, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', default_coupons)

    # Seed default users
    cursor.execute("SELECT count(*) FROM users")
    if cursor.fetchone()[0] == 0:
        default_users = [
            ('usr_pilot_01', 'pilot@drone.com', hash_password('password123'), 'Pozitron Pilot', 'https://api.dicebear.com/7.x/bottts/svg?seed=PozitronPilot', 'manual', 'customer', '05551234567', 'Atatürk Cad. No:12', 'İstanbul', 'Turkey', datetime.now().isoformat()),
            ('usr_ahmet_02', 'ahmet@pozitron.market', hash_password('password123'), 'Ahmet Yılmaz', 'https://api.dicebear.com/7.x/bottts/svg?seed=AhmetYilmaz', 'manual', 'customer', '05329876543', 'Bağdat Cad. No:44', 'İstanbul', 'Turkey', datetime.now().isoformat())
        ]
        cursor.executemany('''
            INSERT INTO users (id, email, password_hash, full_name, avatar_url, provider, role, phone, address, city, country, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', default_users)

    # Lead Supervisor Configuration Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lead_supervisor_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            cycle_interval_hours INTEGER DEFAULT 2,
            is_autonomous_enabled INTEGER DEFAULT 1,
            last_run_at TEXT,
            next_run_at TEXT,
            last_evolution_at TEXT,
            next_evolution_at TEXT,
            active_growth_mode TEXT DEFAULT 'AGGRESSIVE_EXPANSION',
            model_code TEXT DEFAULT 'gemini-3.8-flash',
            updated_at TEXT
        )
    ''')
    cursor.execute("SELECT count(*) FROM lead_supervisor_config WHERE id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO lead_supervisor_config (id, cycle_interval_hours, is_autonomous_enabled, active_growth_mode, model_code, updated_at)
            VALUES (1, 2, 1, 'AGGRESSIVE_EXPANSION', 'gemini-3.8-flash', ?)
        ''', (datetime.now().isoformat(),))

    # Migration: Ensure evolution columns exist on lead_supervisor_config
    cursor.execute("PRAGMA table_info(lead_supervisor_config)")
    existing_cols = [col[1] for col in cursor.fetchall()]
    if 'last_evolution_at' not in existing_cols:
        cursor.execute("ALTER TABLE lead_supervisor_config ADD COLUMN last_evolution_at TEXT")
    if 'next_evolution_at' not in existing_cols:
        cursor.execute("ALTER TABLE lead_supervisor_config ADD COLUMN next_evolution_at TEXT")
    if 'active_growth_mode' not in existing_cols:
        cursor.execute("ALTER TABLE lead_supervisor_config ADD COLUMN active_growth_mode TEXT DEFAULT 'AGGRESSIVE_EXPANSION'")
    if 'model_code' not in existing_cols:
        cursor.execute("ALTER TABLE lead_supervisor_config ADD COLUMN model_code TEXT DEFAULT 'gemini-3.8-flash'")

    # Lead Supervisor Directives Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lead_supervisor_directives (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_cycle_id TEXT UNIQUE NOT NULL,
            directive_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Lead Supervisor 12-Hour Evolution & Self-Optimization Logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lead_evolution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evolution_cycle_id TEXT UNIQUE NOT NULL,
            timestamp TEXT NOT NULL,
            growth_mode TEXT NOT NULL,
            metrics_analyzed TEXT NOT NULL,
            diagnosed_bottlenecks TEXT NOT NULL,
            strategic_adjustments TEXT NOT NULL,
            ai_reasoning TEXT NOT NULL,
            applied_changes TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Global Product Trend Proposals Table (Subagent 6)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_trend_proposals (
            id TEXT PRIMARY KEY,
            name_en TEXT NOT NULL,
            name_tr TEXT NOT NULL,
            category_id TEXT NOT NULL,
            brand TEXT NOT NULL,
            price_usd REAL NOT NULL,
            price_try REAL NOT NULL,
            specs_json TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            image_url TEXT NOT NULL,
            trend_score INTEGER NOT NULL,
            trend_reason TEXT NOT NULL,
            global_source TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING_APPROVAL',
            supervisor_evaluation TEXT,
            added_product_id TEXT,
            created_at TEXT NOT NULL,
            approved_at TEXT
        )
    ''')

    # Telemetry History Table (Subagent 3)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telemetry_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Price Intelligence Logs Table (Subagent 5)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS price_intelligence_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lead_cycle_id TEXT,
            sku TEXT NOT NULL,
            product_name TEXT NOT NULL,
            pozitron_price_try REAL NOT NULL,
            market_min_price_try REAL NOT NULL,
            market_avg_price_try REAL NOT NULL,
            status TEXT NOT NULL,
            competitor_stock INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        )
    ''')

    # Trend Hunter: Store Products Turkey Price Comparison & Undervaluation Alerts (Subagent 6)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trend_price_comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT NOT NULL,
            sku TEXT UNIQUE NOT NULL,
            product_name TEXT NOT NULL,
            category_id TEXT,
            image_url TEXT,
            pozitron_price_try REAL NOT NULL,
            turkey_min_price_try REAL,
            turkey_avg_price_try REAL,
            cheapest_vendor TEXT,
            in_stock_vendors_count INTEGER DEFAULT 0,
            out_of_stock_vendors_count INTEGER DEFAULT 0,
            stale_prices_ignored_json TEXT,
            price_diff_try REAL DEFAULT 0,
            price_diff_pct REAL DEFAULT 0,
            status TEXT NOT NULL,
            warning_level TEXT DEFAULT 'NONE',
            warning_message TEXT,
            recommended_price_try REAL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_price_sku ON trend_price_comparisons(sku)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trend_price_status ON trend_price_comparisons(status)")

    # Technical Documentation & SEO Articles Table (Subagent 4)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seo_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            component_focus TEXT NOT NULL,
            target_keywords TEXT NOT NULL,
            internal_links_json TEXT NOT NULL,
            content_markdown TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Settings Table (System, FX, Payment, 3D Print Configurations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')

    # Seed default settings if not exists
    default_settings = [
        ('usd_rate', '50.0'),
        ('site_name', 'Pozitron Market'),
        ('support_email', 'destek@pozitronmarket.com'),
        ('bank_owner', 'Burak Peköz'),
        ('bank_iban', 'TR41 0020 5000 0908 0479 3000 01'),
        ('bank_name', 'Kuveyt Türk Katılım Bankası (7/24 FAST)'),
        ('3d_setup_fee', '50.0'),
        ('3d_price_pla', '1.50'),
        ('3d_price_petg', '2.00'),
        ('3d_price_tpu', '3.50'),
        ('3d_price_abs', '2.25'),
        ('3d_price_asa', '2.50'),
        ('3d_price_pa6', '5.00')
    ]
    for k, v in default_settings:
        cursor.execute("INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                       (k, v, datetime.now().isoformat()))

    # Migration: Ensure image_mode column exists on instagram_posts
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='instagram_posts'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(instagram_posts)")
        ig_cols = [c[1] for c in cursor.fetchall()]
        if 'image_mode' not in ig_cols:
            cursor.execute("ALTER TABLE instagram_posts ADD COLUMN image_mode TEXT DEFAULT 'canvas'")

    # Migration: Ensure orders table has invoice and address detail columns
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(orders)")
        order_cols = [c[1] for c in cursor.fetchall()]
        order_migrations = [
            ('shipping_district', "ALTER TABLE orders ADD COLUMN shipping_district TEXT"),
            ('billing_address', "ALTER TABLE orders ADD COLUMN billing_address TEXT"),
            ('billing_city', "ALTER TABLE orders ADD COLUMN billing_city TEXT"),
            ('billing_district', "ALTER TABLE orders ADD COLUMN billing_district TEXT"),
            ('billing_country', "ALTER TABLE orders ADD COLUMN billing_country TEXT DEFAULT 'Turkey'"),
            ('invoice_type', "ALTER TABLE orders ADD COLUMN invoice_type TEXT DEFAULT 'individual'"),
            ('tax_id', "ALTER TABLE orders ADD COLUMN tax_id TEXT"),
            ('tax_office', "ALTER TABLE orders ADD COLUMN tax_office TEXT"),
            ('company_name', "ALTER TABLE orders ADD COLUMN company_name TEXT"),
            ('order_notes', "ALTER TABLE orders ADD COLUMN order_notes TEXT")
        ]
        for col_name, sql in order_migrations:
            if col_name not in order_cols:
                try:
                    cursor.execute(sql)
                except Exception as ex:
                    print(f"[Migration Warning] {col_name}: {ex}")

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def get_setting(key: str, default=None):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row is not None:
            val = row[0]
            try:
                return float(val) if '.' in val else int(val)
            except ValueError:
                return val
    except Exception:
        pass
    return default

def set_setting(key: str, value) -> bool:
    try:
        conn = get_db()
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
        ''', (key, str(value), now_str))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error setting {key}: {e}")
        return False

def get_all_settings() -> dict:
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM settings")
        rows = cursor.fetchall()
        conn.close()
        res = {}
        for r in rows:
            val = r['value']
            try:
                val = float(val) if '.' in val else int(val)
            except ValueError:
                pass
            res[r['key']] = val
        return res
    except Exception:
        return {}

def hash_password(password: str) -> str:
    salt = "pozitron_fpv_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

if __name__ == '__main__':
    init_db()

