#!/usr/bin/env python3
"""
Fetch and download authentic, real product photos from e-commerce/web search
for all 500 products in Pozitron Market and update the SQLite database & static bundles.
"""
import sqlite3
import json
import os
import re
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "pozitron.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "assets", "products")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9'
}

CAT_TERMS = {
    'motors': 'FPV brushless drone motor',
    'esc': '4in1 ESC electronic speed controller drone',
    'propellers': 'FPV drone propellers tri-blade',
    'flight_controllers': 'FPV flight controller FC board',
    'batteries_chargers': 'FPV LiPo battery pack XT60',
    'transmitters_receivers': 'FPV radio transmitter remote ELRS',
    'converters': 'FPV BEC power distribution board',
    'cameras': 'FPV camera DJI O3 Caddx Ratel',
    'frames': 'carbon fiber FPV drone frame kit',
    'tools_accessories': 'FPV drone tools soldering iron hex',
    'vtx': 'FPV VTX video transmitter 5.8GHz',
    'antennas': 'FPV 5.8GHz antenna RHCP SMA',
    'gps_telemetry': 'u-blox M10 FPV drone GPS module'
}

def search_real_images(query, max_results=6):
    url = f'https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        html = urllib.request.urlopen(req, timeout=7).read().decode('utf-8', errors='ignore')
        murls = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', html)
        if not murls:
            murls = re.findall(r'\"murl\":\"(http[^\"]+)\"', html)
        valid = []
        for u in murls:
            # Filter out gifs and ensure valid image extensions or clean urls
            lower_u = u.lower()
            if '.gif' not in lower_u:
                valid.append(u)
        return valid[:max_results]
    except Exception:
        return []

def download_image(img_url, dest_path, timeout=8):
    try:
        req = urllib.request.Request(img_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                content = response.read()
                # Check valid size: at least 3KB and not corrupted/blocked html (<3KB)
                if len(content) > 3000 and not content.startswith(b'<!DOCTYPE') and not content.startswith(b'<html'):
                    with open(dest_path, 'wb') as f:
                        f.write(content)
                    return True
    except Exception:
        pass
    return False

def process_single_product(product_row):
    p_id, sku, brand, name_en, cat_id, specs_json = product_row
    clean_sku = re.sub(r'[^a-zA-Z0-9_-]', '', sku)
    dest_filename = f"{clean_sku}.jpg"
    dest_path = os.path.join(OUTPUT_DIR, dest_filename)

    specs = {}
    try:
        specs = json.loads(specs_json)
    except:
        pass
    model = specs.get('model', name_en)

    cat_term = CAT_TERMS.get(cat_id, 'FPV drone')
    
    # Try search query variations
    queries = [
        f"{brand} {model} {cat_term}",
        f"{brand} {model}",
        f"{brand} {cat_term}"
    ]

    saved = False
    found_images = []
    
    for q in queries:
        img_urls = search_real_images(q, max_results=5)
        for u in img_urls:
            if u not in found_images:
                found_images.append(u)
        for img_url in img_urls:
            if download_image(img_url, dest_path):
                saved = True
                break
        if saved:
            break

    relative_img_path = f"./assets/products/{dest_filename}" if saved else None

    # Construct clean gallery with real image URLs
    gallery = []
    if relative_img_path:
        gallery.append(relative_img_path)
    for u in found_images[:3]:
        if u not in gallery:
            gallery.append(u)

    return {
        'id': p_id,
        'sku': sku,
        'name': name_en,
        'cat_id': cat_id,
        'saved': saved,
        'image_url': relative_img_path,
        'gallery': gallery
    }

def run_sync_all():
    print("Connecting to Pozitron database...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, sku, brand, name_en, category_id, specs_json FROM products ORDER BY id ASC")
    all_products = cursor.fetchall()
    print(f"Total products to process: {len(all_products)}")

    results = []
    success_count = 0
    total = len(all_products)

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = {executor.submit(process_single_product, p): p for p in all_products}
        for i, future in enumerate(as_completed(futures), 1):
            res = future.result()
            results.append(res)
            if res['saved']:
                success_count += 1
            if i % 25 == 0 or i == total:
                elapsed = round(time.time() - start_time, 1)
                print(f"Progress: [{i}/{total}] ({round(i/total*100)}%) - Saved: {success_count} real images ({elapsed}s)")

    print(f"\nAll downloads completed! Successfully downloaded {success_count}/{total} real images.")

    # Update database records
    print("Updating SQLite database with local real image paths & galleries...")
    for res in results:
        # If download succeeded, use local relative path; otherwise use top online real image
        final_img = res['image_url'] if res['image_url'] else (res['gallery'][0] if res['gallery'] else f"./assets/products/{res['cat_id']}.png")
        gallery_json = json.dumps(res['gallery'] if res['gallery'] else [final_img], ensure_ascii=False)
        cursor.execute("UPDATE products SET image_url = ?, gallery_json = ? WHERE id = ?", (final_img, gallery_json, res['id']))

    conn.commit()
    conn.close()
    print("Database updated successfully!")

    # Export to static files
    print("Exporting static data to data/pozitron_data.js and data/products.json...")
    from export_data import export_static_data
    export_static_data()
    print("Sync complete!")

if __name__ == '__main__':
    run_sync_all()
