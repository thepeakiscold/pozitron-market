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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_quality_checks (
            product_id TEXT PRIMARY KEY REFERENCES products(id) ON DELETE CASCADE,
            status TEXT NOT NULL CHECK(status IN ('pending', 'checked', 'issues')),
            content_hash TEXT NOT NULL,
            reviewer TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            sources_json TEXT NOT NULL DEFAULT '[]',
            reviewed_at TEXT NOT NULL
        )
    ''')

    # Stock alert subscriptions ("notify me when back in stock")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_alerts (
            id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT,
            whatsapp INTEGER DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'notified', 'cancelled')),
            created_at TEXT NOT NULL,
            notified_at TEXT,
            UNIQUE(product_id, email),
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_alerts_product ON stock_alerts(product_id, status)')

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

    # Hosted payment tokens and opaque receipt IDs; never card details or API keys.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS iyzico_sessions (
            token TEXT PRIMARY KEY,
            order_id TEXT UNIQUE NOT NULL REFERENCES orders(id),
            receipt TEXT UNIQUE NOT NULL,
            coupon_code TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            last_checked REAL NOT NULL DEFAULT 0
        )
    ''')

    # Additive migration for previously initialized checkout sessions.
    if 'last_checked' not in {row[1] for row in cursor.execute('PRAGMA table_info(iyzico_sessions)')}:
        cursor.execute('ALTER TABLE iyzico_sessions ADD COLUMN last_checked REAL NOT NULL DEFAULT 0')

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

    cursor.execute("PRAGMA table_info(reviews)")
    if 'deleted_at' not in {row[1] for row in cursor.fetchall()}:
        cursor.execute("ALTER TABLE reviews ADD COLUMN deleted_at TEXT")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_deleted_created ON reviews(deleted_at, created_at)")

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
            is_active INTEGER DEFAULT 1,
            starts_at TEXT,
            expires_at TEXT,
            max_uses INTEGER,
            per_user_limit INTEGER DEFAULT 1,
            used_count INTEGER DEFAULT 0,
            created_at TEXT,
            source TEXT DEFAULT 'manual',
            campaign_id TEXT
        )
    ''')

    # Coupon redemptions: one row per (coupon, user, order). UNIQUE(coupon_code, user_key, order_id)
    # allows multi-use coupons (per_user_limit > 1) across different orders while blocking double-spend per order.
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='coupon_redemptions'")
    table_sql = cursor.fetchone()
    if table_sql and "UNIQUE (coupon_code, user_key)" in table_sql[0]:
        cursor.execute("ALTER TABLE coupon_redemptions RENAME TO coupon_redemptions_old")
        cursor.execute('''
            CREATE TABLE coupon_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_code TEXT NOT NULL,
                user_key TEXT NOT NULL,
                user_id TEXT,
                customer_email TEXT,
                order_id TEXT,
                order_number TEXT,
                discount_try REAL DEFAULT 0,
                discount_usd REAL DEFAULT 0,
                redeemed_at TEXT NOT NULL,
                UNIQUE (coupon_code, user_key, order_id)
            )
        ''')
        cursor.execute('''
            INSERT INTO coupon_redemptions (id, coupon_code, user_key, user_id, customer_email, order_id, order_number, discount_try, discount_usd, redeemed_at)
            SELECT id, coupon_code, user_key, user_id, customer_email, order_id, order_number, discount_try, discount_usd, redeemed_at
            FROM coupon_redemptions_old
        ''')
        cursor.execute("DROP TABLE coupon_redemptions_old")
    else:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS coupon_redemptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coupon_code TEXT NOT NULL,
                user_key TEXT NOT NULL,
                user_id TEXT,
                customer_email TEXT,
                order_id TEXT,
                order_number TEXT,
                discount_try REAL DEFAULT 0,
                discount_usd REAL DEFAULT 0,
                redeemed_at TEXT NOT NULL,
                UNIQUE (coupon_code, user_key, order_id)
            )
        ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coupon_redemptions_code ON coupon_redemptions (coupon_code)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coupon_redemptions_user ON coupon_redemptions (user_key)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coupon_redemptions_email ON coupon_redemptions (customer_email)")

    # Coupon audit log: every lifecycle event (created/validated/redeemed/expired/deactivated).
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupon_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            coupon_code TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT,
            actor TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coupon_logs_code ON coupon_logs (coupon_code)")

    # Seed default coupons
    cursor.execute("SELECT count(*) FROM coupons")
    if cursor.fetchone()[0] == 0:
        default_coupons = [
            ('POZITRON10', 'percent', 10, 50, 1500, '10% discount on all orders above $50', '50$ ve üzeri tüm siparişlerde %10 indirim'),
            ('DRONE700', 'fixed', 700, 100, 3000, '700₺ off on orders over 3000₺', '3000₺ ve üzeri siparişlerde 700₺ indirim'),
            ('WELCOME15', 'percent', 15, 30, 900, '15% welcome discount for new pilots', 'Yeni pilotlar için %15 hoş geldin indirimi'),
            ('FPVRACE', 'percent', 12, 40, 1200, '12% FPV racing component discount', 'FPV yarış bileşenlerinde %12 indirim')
        ]
        cursor.executemany('''
            INSERT INTO coupons (code, discount_type, discount_value, min_order_usd, min_order_try, description_en, description_tr, is_active, per_user_limit, used_count, created_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, 0, ?, 'seed')
        ''', [(c[0], c[1], c[2], c[3], c[4], c[5], c[6], datetime.now().isoformat()) for c in default_coupons])

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
            model_code TEXT DEFAULT 'deepseek-v4.1-flash-high',
            updated_at TEXT
        )
    ''')
    cursor.execute("SELECT count(*) FROM lead_supervisor_config WHERE id = 1")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO lead_supervisor_config (id, cycle_interval_hours, is_autonomous_enabled, active_growth_mode, model_code, updated_at)
            VALUES (1, 2, 1, 'AGGRESSIVE_EXPANSION', 'deepseek-v4.1-flash-high', ?)
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
        cursor.execute("ALTER TABLE lead_supervisor_config ADD COLUMN model_code TEXT DEFAULT 'deepseek-v4.1-flash-high'")

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
        ('bank_owner', ''),
        ('bank_iban', 'TR69 0004 6001 9188 8000 3245 80'),
        ('bank_name', 'Akbank / Havale / EFT / FAST'),
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

    # One-time business account update; later administrator changes are preserved.
    cursor.execute("SELECT value FROM settings WHERE key = 'business_account_revision'")
    if cursor.fetchone() is None:
        for key, value in (
            ('bank_owner', ''),
            ('bank_iban', 'TR69 0004 6001 9188 8000 3245 80'),
            ('bank_name', 'Akbank / Havale / EFT / FAST'),
            ('business_account_revision', '2026-10-20'),
        ):
            cursor.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                           (key, value, datetime.now().isoformat()))

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

    # Migration: Ensure coupons table has lifecycle / usage columns
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='coupons'")
    if cursor.fetchone():
        cursor.execute("PRAGMA table_info(coupons)")
        coupon_cols = [c[1] for c in cursor.fetchall()]
        coupon_migrations = [
            ('starts_at', "ALTER TABLE coupons ADD COLUMN starts_at TEXT"),
            ('expires_at', "ALTER TABLE coupons ADD COLUMN expires_at TEXT"),
            ('max_uses', "ALTER TABLE coupons ADD COLUMN max_uses INTEGER"),
            ('per_user_limit', "ALTER TABLE coupons ADD COLUMN per_user_limit INTEGER DEFAULT 1"),
            ('used_count', "ALTER TABLE coupons ADD COLUMN used_count INTEGER DEFAULT 0"),
            ('created_at', "ALTER TABLE coupons ADD COLUMN created_at TEXT"),
            ('source', "ALTER TABLE coupons ADD COLUMN source TEXT DEFAULT 'manual'"),
            ('campaign_id', "ALTER TABLE coupons ADD COLUMN campaign_id TEXT"),
        ]
        for col_name, sql in coupon_migrations:
            if col_name not in coupon_cols:
                try:
                    cursor.execute(sql)
                except Exception as ex:
                    print(f"[Migration Warning] coupons.{col_name}: {ex}")

    # Subagents Enable/Disable Configuration Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subagents_config (
            subagent_id TEXT PRIMARY KEY,
            name_tr TEXT NOT NULL,
            is_enabled INTEGER DEFAULT 1,
            description_tr TEXT,
            updated_at TEXT NOT NULL
        )
    ''')

    default_subagents = [
        ('subagent_1_instagram', 'Instagram PR ve İçerik Botu', 1, 'Otonom Instagram gönderi, hikaye ve reels üretimi'),
        ('subagent_2_reddit', 'Reddit FPV ve Topluluk Asistanı', 0, 'Türk FPV ve teknoloji subredditlerinde otonom soru yanıtlama (Kullanıcı tarafından kapatıldı)'),
        ('subagent_3_telemetry', 'Telemetri ve Metrik Takip Ajanı', 1, 'Satış, stok ve sistem sağlık telemetrilerini derleme'),
        ('subagent_4_seo', 'Teknik Dokümantasyon ve SEO Ajanı', 1, 'Teknik rehberler ve iç linklemeli SEO makaleleri üretme'),
        ('subagent_5_price', 'Türkiye Fiyat ve Rekabet İstihbaratı', 1, 'Türkiye FPV pazarındaki rakip fiyat ve arbitraj analizi'),
        ('subagent_6_trend', 'Küresel Trend Avcısı ve Tedarik Ajanı', 1, 'Dünyadaki yeni çıkan trend FPV donanımlarını keşfetme'),
        ('subagent_7_qa', 'QA Sentinel ve Otonom Sistem Sağlığı', 1, 'Sistem arızalarını, bozuk linkleri ve anomalileri denetleme'),
        ('subagent_8_procurement', 'Sipariş ve Tedarik Optimizasyonu Ajanı', 1, 'En çok kâr ettirecek ve hızlı satılacak ürünleri adetleriyle planlama'),
        ('subagent_9_security', 'Siber Güvenlik ve Savunma Sentineli', 1, 'WAF, brute-force, SQLi/XSS filtreleri, PayTR imza doğrulaması ve SSL takibi'),
        ('subagent_10_media', 'Ürün Medya ve İçerik Kalite Denetleyicisi', 1, 'Ürün fotoğraflarının, başlıklarının ve teknik açıklamalarının Vision AI ile kalite denetimi ve onarımı'),
        ('lead_supervisor', 'Baş Orkestratör ve Stratejik Evrim Motoru', 1, 'Tüm alt ajanları koordine eden ana strateji motoru')
    ]
    for sa_id, sa_name, sa_enabled, sa_desc in default_subagents:
        cursor.execute('''
            INSERT OR IGNORE INTO subagents_config (subagent_id, name_tr, is_enabled, description_tr, updated_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (sa_id, sa_name, sa_enabled, sa_desc, datetime.now().isoformat()))

    # Ensure Reddit agent is disabled per user request
    cursor.execute("UPDATE subagents_config SET is_enabled = 0 WHERE subagent_id = 'subagent_2_reddit'")
    cursor.execute("UPDATE reddit_agent_config SET is_autonomous_enabled = 0 WHERE id = 1")

    # Procurement & Replenishment Order Plans Table (Subagent 8)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS procurement_order_plans (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'PROPOSED', -- 'PROPOSED', 'APPROVED', 'ORDERED'
            total_items_count INTEGER NOT NULL,
            total_units_count INTEGER NOT NULL,
            estimated_investment_try REAL NOT NULL,
            projected_revenue_try REAL NOT NULL,
            projected_profit_try REAL NOT NULL,
            projected_roi_pct REAL NOT NULL,
            items_json TEXT NOT NULL,
            strategy_summary TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Cyber Security Audit Logs Table (Subagent 9)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS security_audit_logs (
            id TEXT PRIMARY KEY,
            audit_type TEXT NOT NULL,
            status TEXT DEFAULT 'SECURE',
            score INTEGER DEFAULT 100,
            summary TEXT,
            details_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Product Media Quality & Vision Audits Table (Subagent 10)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_media_audits (
            product_id TEXT PRIMARY KEY,
            sku TEXT NOT NULL,
            name_tr TEXT NOT NULL,
            category_id TEXT NOT NULL,
            image_url TEXT NOT NULL,
            status TEXT DEFAULT 'VERIFIED', -- 'VERIFIED', 'MISMATCH', 'SUSPICIOUS', 'CORRUPT', 'DUPLICATE'
            issue_type TEXT,
            confidence_score REAL DEFAULT 1.0,
            resolution_status TEXT DEFAULT 'PENDING', -- 'PENDING', 'AUTO_FIXED', 'MANUAL_REQUIRED'
            suggested_image_url TEXT,
            details_json TEXT,
            updated_at TEXT NOT NULL
        )
    ''')

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

def is_subagent_enabled(subagent_id: str) -> bool:
    """Checks whether a given subagent is enabled in the database."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT is_enabled FROM subagents_config WHERE subagent_id = ?", (subagent_id,))
        row = cursor.fetchone()
        conn.close()
        if row is not None:
            return bool(row[0] if isinstance(row, tuple) else row['is_enabled'])
        return True
    except Exception as e:
        print(f"Error checking subagent enabled {subagent_id}: {e}")
        return True

def set_subagent_enabled(subagent_id: str, is_enabled: bool) -> bool:
    """Toggles a subagent on or off in the database."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        val = 1 if is_enabled else 0
        now_str = datetime.now().isoformat()
        cursor.execute("""
            UPDATE subagents_config
            SET is_enabled = ?, updated_at = ?
            WHERE subagent_id = ?
        """, (val, now_str, subagent_id))

        if subagent_id in ('subagent_2_reddit', 'reddit'):
            cursor.execute("UPDATE reddit_agent_config SET is_autonomous_enabled = ? WHERE id = 1", (val,))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating subagent {subagent_id}: {e}")
        return False

def get_all_subagents_config() -> List[Dict]:
    """Retrieves all subagents configuration and active statuses."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subagents_config ORDER BY subagent_id ASC")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        print(f"Error getting subagents config: {e}")
        return []

def hash_password(password: str) -> str:
    salt = "pozitron_fpv_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

if __name__ == '__main__':
    init_db()

