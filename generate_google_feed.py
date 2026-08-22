#!/usr/bin/env python3
"""
Generate Google Merchant Center XML & TSV Product Feeds for Pozitron Market
Generates 100% Google Shopping compliant feeds with absolute URLs, TRY currency, and rich metadata.
"""

import sqlite3
import xml.etree.ElementTree as ET
from xml.dom import minidom
import csv
import os

DB_PATH = 'pozitron.db'
BASE_URL = 'https://pozitronmarket.com'

def generate_feeds():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, sku, name_tr, name_en, category_id, brand, price_try, original_price_try, stock, image_url, description_tr, description_en
        FROM products
        ORDER BY id ASC
    ''')
    products = cursor.fetchall()
    conn.close()

    # 1. XML Feed (RSS 2.0 Google Merchant Specification)
    rss = ET.Element('rss', {
        'xmlns:g': 'http://base.google.com/ns/1.0',
        'version': '2.0'
    })
    channel = ET.SubElement(rss, 'channel')

    c_title = ET.SubElement(channel, 'title')
    c_title.text = "Pozitron Market - FPV Drone & Yedek Parça"

    c_link = ET.SubElement(channel, 'link')
    c_link.text = BASE_URL

    c_desc = ET.SubElement(channel, 'description')
    c_desc.text = "Türkiye'nin Lider FPV Drone, Motor, ESC, Uçuş Kontrol Kartı ve Yedek Parça Mağazası"

    tsv_rows = []
    tsv_headers = ['id', 'title', 'description', 'link', 'image_link', 'availability', 'price', 'brand', 'condition', 'google_product_category', 'mpn']

    for p in products:
        p_id, sku, name_tr, name_en, cat_id, brand, price_try, orig_price_try, stock, img_url, desc_tr, desc_en = p
        
        # Absolute Image URL
        if img_url.startswith('./'):
            full_img_url = f"{BASE_URL}/{img_url[2:]}"
        elif img_url.startswith('/'):
            full_img_url = f"{BASE_URL}{img_url}"
        elif not img_url.startswith('http'):
            full_img_url = f"{BASE_URL}/{img_url}"
        else:
            full_img_url = img_url

        prod_link = f"{BASE_URL}/#prod-{p_id}"
        title = (name_tr or name_en or 'FPV Drone Parçası').strip()
        description = (desc_tr or desc_en or f"{brand} {title} yüksek performanslı FPV drone bileşeni.").strip()
        availability = 'in_stock' if int(stock) > 0 else 'out_of_stock'
        formatted_price = f"{float(price_try):.2f} TRY"

        # XML Item
        item = ET.SubElement(channel, 'item')
        
        g_id = ET.SubElement(item, 'g:id')
        g_id.text = sku or p_id
        
        g_title = ET.SubElement(item, 'g:title')
        g_title.text = title
        
        g_desc = ET.SubElement(item, 'g:description')
        g_desc.text = description
        
        g_link = ET.SubElement(item, 'g:link')
        g_link.text = prod_link
        
        g_img = ET.SubElement(item, 'g:image_link')
        g_img.text = full_img_url
        
        g_avail = ET.SubElement(item, 'g:availability')
        g_avail.text = availability
        
        g_price = ET.SubElement(item, 'g:price')
        g_price.text = formatted_price
        
        g_brand = ET.SubElement(item, 'g:brand')
        g_brand.text = brand or 'Pozitron'
        
        g_cond = ET.SubElement(item, 'g:condition')
        g_cond.text = 'new'
        
        g_cat = ET.SubElement(item, 'g:google_product_category')
        g_cat.text = '5433'  # Google Taxonomy: Cameras & Optics > Photography > Digital Cameras / Drones & Accessories
        
        g_mpn = ET.SubElement(item, 'g:mpn')
        g_mpn.text = sku or p_id

        g_id_exists = ET.SubElement(item, 'g:identifier_exists')
        g_id_exists.text = 'yes'

        # TSV Row
        tsv_rows.append({
            'id': sku or p_id,
            'title': title,
            'description': description.replace('\n', ' ').replace('\t', ' '),
            'link': prod_link,
            'image_link': full_img_url,
            'availability': availability,
            'price': formatted_price,
            'brand': brand or 'Pozitron',
            'condition': 'new',
            'google_product_category': '5433',
            'mpn': sku or p_id
        })

    # Save XML feed to root and data/
    xml_str = ET.tostring(rss, encoding='utf-8')
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ", encoding="utf-8")

    with open('google_merchant_feed.xml', 'wb') as f:
        f.write(pretty_xml)
    
    with open('data/google_merchant_feed.xml', 'wb') as f:
        f.write(pretty_xml)

    # Save TSV feed
    with open('google_merchant_feed.tsv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=tsv_headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(tsv_rows)

    with open('data/google_merchant_feed.tsv', 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=tsv_headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(tsv_rows)

    print(f"Generated Google Merchant Feed for {len(products)} products successfully!")
    print("Files created:")
    print(" - https://pozitronmarket.com/google_merchant_feed.xml")
    print(" - https://pozitronmarket.com/google_merchant_feed.tsv")

if __name__ == '__main__':
    generate_feeds()
