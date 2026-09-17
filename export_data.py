#!/usr/bin/env python3
"""
Export Pozitron Market database into JSON and JS files for GitHub Pages static hosting.
"""
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pozitron.db")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data")

def export_static_data():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Categories
    cursor.execute("SELECT * FROM categories ORDER BY item_count DESC")
    categories = [dict(row) for row in cursor.fetchall()]

    # 2. Products
    cursor.execute('''
        SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
        FROM products p
        JOIN categories c ON p.category_id = c.id
        ORDER BY p.id ASC
    ''')
    rows = cursor.fetchall()
    products = []
    brands_set = set()

    for r in rows:
        p = dict(r)
        p['specs'] = json.loads(p['specs_json'])
        p['tags'] = json.loads(p['tags_json'])
        p['gallery'] = json.loads(p['gallery_json'] or '[]')
        p['compatibility'] = json.loads(p['compatibility_json'] or '{}')
        brands_set.add(p['brand'])
        products.append(p)

    brands = sorted(list(brands_set))

    # 3. Reviews
    cursor.execute("SELECT * FROM reviews ORDER BY created_at DESC")
    reviews = [dict(row) for row in cursor.fetchall()]

    # 4. Instagram Posts
    cursor.execute("SELECT * FROM instagram_posts ORDER BY id DESC")
    instagram_posts = [dict(row) for row in cursor.fetchall()]

    # 5. Reddit Interactions
    cursor.execute("SELECT * FROM reddit_interactions ORDER BY id DESC")
    reddit_interactions = [dict(row) for row in cursor.fetchall()]

    # 6. SEO Articles (Subagent 3)
    cursor.execute("SELECT * FROM seo_articles ORDER BY id DESC")
    seo_articles = [dict(row) for row in cursor.fetchall()]

    # 7. Global Trend Proposals (Subagent 6)
    cursor.execute("SELECT * FROM global_trend_proposals ORDER BY id DESC")
    global_trends = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # Save to data/instagram_posts.json
    with open(os.path.join(OUTPUT_DIR, "instagram_posts.json"), "w", encoding="utf-8") as f:
        json.dump(instagram_posts, f, ensure_ascii=False, indent=2)

    # Save to data/reddit_history.json
    with open(os.path.join(OUTPUT_DIR, "reddit_history.json"), "w", encoding="utf-8") as f:
        json.dump(reddit_interactions, f, ensure_ascii=False, indent=2)

    # Save to data/seo_articles.json
    with open(os.path.join(OUTPUT_DIR, "seo_articles.json"), "w", encoding="utf-8") as f:
        json.dump(seo_articles, f, ensure_ascii=False, indent=2)

    # Save to data/global_trends.json
    with open(os.path.join(OUTPUT_DIR, "global_trends.json"), "w", encoding="utf-8") as f:
        json.dump(global_trends, f, ensure_ascii=False, indent=2)

    # Save to data/products.json
    with open(os.path.join(OUTPUT_DIR, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)

    # Save to data/categories.json
    with open(os.path.join(OUTPUT_DIR, "categories.json"), "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)

    # Save full standalone catalog bundle to data/pozitron_data.js
    full_data = {
        "categories": categories,
        "brands": brands,
        "products": products,
        "reviews": reviews,
        "seo_articles": seo_articles[:10]
    }

    with open(os.path.join(OUTPUT_DIR, "pozitron_data.js"), "w", encoding="utf-8") as f:
        f.write(f"// Pozitron Market Static Catalog Bundle for GitHub Pages\n")
        f.write(f"window.__POZITRON_DATA__ = {json.dumps(full_data, ensure_ascii=False)};\n")
        f.write(f"window.pozitronData = window.__POZITRON_DATA__;\n")

    print(f"Exported {len(products)} products, {len(categories)} categories, and {len(brands)} brands to {OUTPUT_DIR}")

    # Generate Google Merchant XML & TSV Feeds
    try:
        from generate_google_feed import generate_feeds
        generate_feeds()
    except Exception as fe:
        print(f"Feed generation note: {fe}")

if __name__ == "__main__":
    export_static_data()
