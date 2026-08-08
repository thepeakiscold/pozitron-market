#!/usr/bin/env python3
import sqlite3
import json
import os
import re
import time
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

DB_PATH = os.path.join(os.path.dirname(__file__), "pozitron.db")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "assets", "products")
os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def search_real_images(query, max_results=4):
    url = f'https://www.bing.com/images/search?q={urllib.parse.quote(query)}&form=HDRSC2&first=1'
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        html = urllib.request.urlopen(req, timeout=8).read().decode('utf-8', errors='ignore')
        murls = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', html)
        if not murls:
            murls = re.findall(r'\"murl\":\"(http[^\"]+)\"', html)
        # Filter valid image URLs
        valid = []
        for u in murls:
            if any(ext in u.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                valid.append(u)
        return valid[:max_results]
    except Exception as e:
        return []

def download_image(img_url, dest_path, timeout=10):
    try:
        req = urllib.request.Request(img_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                content = response.read()
                # Basic check that it is indeed an image (> 2KB)
                if len(content) > 2000:
                    with open(dest_path, 'wb') as f:
                        f.write(content)
                    return True
    except Exception as e:
        pass
    return False

def process_product(product):
    p_id, sku, brand, name_en, cat_id, specs_json = product
    clean_sku = re.sub(r'[^a-zA-Z0-9_-]', '', sku)
    dest_filename = f"{clean_sku}.jpg"
    dest_path = os.path.join(OUTPUT_DIR, dest_filename)

    # Parse specs to get model name
    specs = {}
    try:
        specs = json.loads(specs_json)
    except:
        pass
    model = specs.get('model', name_en)

    # Category name for cleaner context
    cat_terms = {
        'motors': 'FPV drone motor',
        'esc': '4in1 ESC drone',
        'propellers': 'FPV drone propellers',
        'flight_controllers': 'FPV flight controller FC',
        'batteries_chargers': 'LiPo battery charger drone',
        'transmitters_receivers': 'FPV radio transmitter receiver',
        'converters': 'FPV BEC power converter',
        'cameras': 'FPV camera DJI O3 Caddx',
        'frames': 'carbon fiber FPV drone frame kit',
        'tools_accessories': 'FPV drone tool soldering',
        'vtx': 'FPV VTX video transmitter',
        'antennas': 'FPV 5.8GHz antenna',
        'gps_telemetry': 'FPV drone GPS module'
    }
    cat_term = cat_terms.get(cat_id, 'FPV drone')
    query = f"{brand} {model} {cat_term}"

    found_images = search_real_images(query, max_results=5)
    
    # Try downloading the primary image
    saved_primary = False
    for img_url in found_images:
        if download_image(img_url, dest_path):
            saved_primary = True
            break
            
    relative_img_path = f"./assets/products/{dest_filename}" if saved_primary else None
    
    # Also save top online gallery URLs
    gallery_urls = [relative_img_path] if relative_img_path else []
    for u in found_images[:3]:
        if u not in gallery_urls:
            gallery_urls.append(u)

    return {
        'id': p_id,
        'sku': sku,
        'query': query,
        'success': saved_primary,
        'image_url': relative_img_path,
        'gallery': gallery_urls
    }

if __name__ == '__main__':
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, sku, brand, name_en, category_id, specs_json FROM products LIMIT 10")
    test_products = cursor.fetchall()
    conn.close()

    print(f"Testing real image download on {len(test_products)} products...")
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_product, p) for p in test_products]
        for f in as_completed(futures):
            res = f.result()
            print(f"[{res['sku']}] {res['query']} -> Success: {res['success']} ({res['image_url']})")
