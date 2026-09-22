#!/usr/bin/env python3
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pozitron.db")

def get_usd_rate(conn):
    try:
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'usd_rate'")
        row = c.fetchone()
        if row and row[0]:
            return float(row[0])
    except Exception:
        pass
    return 50.0

MULTIPLIER = 1.0

def update_all_prices():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    usd_rate = get_usd_rate(conn)

    cursor.execute("SELECT id, price_usd, original_price_usd FROM products")
    rows = cursor.fetchall()

    for r in rows:
        pid = r[0]
        price_usd = r[1]
        orig_usd = r[2]

        new_price_try = round(price_usd * usd_rate * MULTIPLIER, 2)
        new_orig_try = round(orig_usd * usd_rate * MULTIPLIER, 2) if orig_usd else None

        cursor.execute('''
            UPDATE products 
            SET price_try = ?, original_price_try = ?
            WHERE id = ?
        ''', (new_price_try, new_orig_try, pid))

    conn.commit()
    print(f"Updated {len(rows)} products with commercial pricing formula.")
    conn.close()

if __name__ == "__main__":
    update_all_prices()
