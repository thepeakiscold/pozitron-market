import sqlite3
import os
import json
import hashlib
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pozitron.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
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

    # Reviews Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            product_id TEXT NOT NULL,
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
            ('usr_admin_master', 'admin', hash_password('9enrtvbgA.'), 'Pozitron Admin', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80', 'manual', 'admin', '05441112233', 'Karaköy Rıhtım No:5', 'İstanbul', 'Turkey', datetime.now().isoformat()),
            ('usr_admin_master_email', 'admin@pozitronmarket.com', hash_password('9enrtvbgA.'), 'Pozitron Admin', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80', 'manual', 'admin', '05441112233', 'Karaköy Rıhtım No:5', 'İstanbul', 'Turkey', datetime.now().isoformat()),
            ('usr_pilot_01', 'pilot@drone.com', hash_password('password123'), 'Pozitron Test Pilot', 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80', 'manual', 'customer', '05551234567', 'Atatürk Cad. No:12', 'İstanbul', 'Turkey', datetime.now().isoformat()),
            ('usr_ahmet_02', 'ahmet@pozitron.market', hash_password('password123'), 'Ahmet Yılmaz', 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80', 'manual', 'customer', '05329876543', 'Bağdat Cad. No:44', 'İstanbul', 'Turkey', datetime.now().isoformat())
        ]
        cursor.executemany('''
            INSERT INTO users (id, email, password_hash, full_name, avatar_url, provider, role, phone, address, city, country, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', default_users)

    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def hash_password(password: str) -> str:
    salt = "pozitron_fpv_salt_2026"
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

if __name__ == '__main__':
    init_db()
