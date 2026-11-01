#!/usr/bin/env python3
"""
Convert all product images to PNG format and sanitize database assignments.
Uses parallel worker processes for fast conversion.
"""
import os
import sqlite3
import json
import re
from PIL import Image
from concurrent.futures import ProcessPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_DIR = os.path.join(BASE_DIR, 'assets', 'products')
DB_PATH = os.path.join(BASE_DIR, 'pozitron.db')

def convert_single(task):
    src, dst = task
    try:
        with Image.open(src) as im:
            if im.mode in ('RGBA', 'LA'):
                im.save(dst, 'PNG', compress_level=6)
            elif im.mode == 'P':
                im = im.convert('RGBA')
                im.save(dst, 'PNG', compress_level=6)
            else:
                im = im.convert('RGB')
                im.save(dst, 'PNG', compress_level=6)
        return True, src, None
    except Exception as e:
        return False, src, str(e)

def main():
    print("Step 1: Identifying image files to convert to PNG in parallel...")
    files = sorted(os.listdir(PRODUCTS_DIR))
    tasks = []

    for fname in files:
        src = os.path.join(PRODUCTS_DIR, fname)
        if not os.path.isfile(src):
            continue
        base, ext = os.path.splitext(fname)
        ext_lower = ext.lower()
        if ext_lower in ('.jpg', '.jpeg', '.webp', '.avif'):
            dst = os.path.join(PRODUCTS_DIR, f"{base}.png")
            tasks.append((src, dst))

    print(f"Found {len(tasks)} files to convert. Running with ProcessPoolExecutor...")
    success = 0
    errors = 0

    cpu_count = min(os.cpu_count() or 4, 8)
    with ProcessPoolExecutor(max_workers=cpu_count) as executor:
        futures = [executor.submit(convert_single, t) for t in tasks]
        for f in as_completed(futures):
            ok, src, err = f.result()
            if ok:
                success += 1
            else:
                errors += 1
                print(f"Error converting {src}: {err}")

    print(f"Parallel conversion complete: {success} converted, {errors} errors.")

    print("\nStep 2: Updating SQLite database pozitron.db to point all products to their dedicated SKU PNG...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT id, sku, name_tr, category_id, image_url, gallery_json FROM products")
    products = cursor.fetchall()
    print(f"Loaded {len(products)} products from database.")

    updated_count = 0
    missing_images = []

    for p in products:
        sku = p['sku']
        clean_sku = re.sub(r'[^a-zA-Z0-9_-]', '', sku.replace('/', '-').replace(' ', ''))
        
        expected_png_filename = f"{clean_sku}.png"
        expected_png_path = os.path.join(PRODUCTS_DIR, expected_png_filename)

        if not os.path.exists(expected_png_path):
            src_jpg = os.path.join(PRODUCTS_DIR, f"{clean_sku}.jpg")
            if os.path.exists(src_jpg):
                ok, _, _ = convert_single((src_jpg, expected_png_path))
                if not ok:
                    missing_images.append((sku, "conversion_failed"))
            else:
                # Use clean category fallback PNG
                cat_fallback = os.path.join(PRODUCTS_DIR, f"{p['category_id']}.png")
                if not os.path.exists(cat_fallback):
                    cat_fallback = os.path.join(PRODUCTS_DIR, "motor.png")
                expected_png_filename = os.path.basename(cat_fallback)
                missing_images.append((sku, f"fallback_{expected_png_filename}"))

        new_image_url = f"./assets/products/{expected_png_filename}"
        new_gallery = json.dumps([new_image_url], ensure_ascii=False)

        cursor.execute(
            "UPDATE products SET image_url = ?, gallery_json = ? WHERE id = ?",
            (new_image_url, new_gallery, p['id'])
        )
        updated_count += 1

    conn.commit()
    conn.close()
    print(f"Updated {updated_count} products in database to use dedicated PNG images.")
    if missing_images:
        print(f"Notes on missing images ({len(missing_images)}):", missing_images[:10])

if __name__ == '__main__':
    main()
