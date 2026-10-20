#!/usr/bin/env python3
"""
Downloads ~100 copyright-free (CC0 / Public Domain) images from Wikimedia Commons
for use as ambient backgrounds in Instagram posts.

Licenses are recorded in assets/instagram/stock/manifest.json. Images that require
attribution (CC BY / CC BY-SA) are still downloaded but flagged in the manifest so
they can be credited or excluded.

Usage:
    python3 scripts/download_free_images.py [--count 100] [--category drone]
"""
import os
import sys
import json
import time
import argparse
import hashlib
import html
import re
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK_DIR = os.path.join(BASE_DIR, 'assets', 'instagram', 'stock')
MANIFEST_PATH = os.path.join(STOCK_DIR, 'manifest.json')

HEADERS = {
    'User-Agent': 'PozitronMarketBot/1.0 (https://pozitronmarket.com; contact@pozitronmarket.com)'
}

API = 'https://commons.wikimedia.org/w/api.php'

# category -> list of Wikimedia Commons search queries
CATEGORY_QUERIES = {
    'drone': [
        'quadcopter drone', 'FPV drone', 'multirotor aircraft', 'drone racing',
        'unmanned aerial vehicle', 'drone flying',
    ],
    'electronics': [
        'circuit board', 'printed circuit board', 'soldering electronics',
        'electronic components', 'lithium polymer battery', 'brushless motor',
    ],
    'nature': [
        'mountain landscape aerial', 'aerial landscape valley', 'forest aerial view',
        'mountain ridge fog', 'coastline aerial', 'sunrise mountains',
    ],
    'workshop': [
        'electronics workbench', 'workshop tools', '3D printer', 'maker workshop',
        'repair tools desk', 'soldering station',
    ],
    'city': [
        'city skyline night', 'rooftop city view', 'night city aerial', 'urban skyline dusk',
    ],
    'tech_abstract': [
        'technology abstract', 'neon lights abstract', 'server room', 'fibre optic light',
        'blue technology background',
    ],
}

# Licenses considered copyright-free. CC-BY* still need attribution (flagged).
FREE_LICENSE_HINTS = ('cc0', 'public domain', 'pd-', 'no restrictions')
ATTRIB_LICENSE_HINTS = ('cc by', 'cc-by', 'attribution', 'gfdl')


def _clean_text(v):
    if not v:
        return ''
    v = re.sub(r'<[^>]+>', '', str(v))
    return html.unescape(v).strip()


def api_get(params, retries=3):
    params = dict(params)
    params.setdefault('format', 'json')
    url = API + '?' + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode('utf-8'))
        except Exception as e:
            if attempt == retries - 1:
                print(f"  [api] hata: {e}")
                return None
            time.sleep(1.5 * (attempt + 1))


def search_images(query, limit=25):
    params = {
        'action': 'query',
        'generator': 'search',
        'gsrsearch': f'{query} filetype:bitmap',
        'gsrnamespace': '6',
        'gsrlimit': str(limit),
        'prop': 'imageinfo',
        'iiprop': 'url|extmetadata|size|sha1',
        'iiurlwidth': '1400',
    }
    data = api_get(params)
    if not data:
        return []
    pages = (data.get('query') or {}).get('pages') or {}
    results = []
    for page in pages.values():
        infos = page.get('imageinfo') or []
        if not infos:
            continue
        info = infos[0]
        meta = info.get('extmetadata') or {}

        license_name = _clean_text((meta.get('LicenseShortName') or {}).get('value'))
        artist = _clean_text((meta.get('Artist') or {}).get('value'))
        credit = _clean_text((meta.get('Credit') or {}).get('value'))
        desc = _clean_text((meta.get('ImageDescription') or {}).get('value'))
        objname = _clean_text((meta.get('ObjectName') or {}).get('value'))

        width = int(info.get('width') or 0)
        if width and width < 1000:
            continue

        results.append({
            'title':  objname or page.get('title', ''),
            'thumburl': info.get('thumburl') or info.get('url'),
            'url': info.get('url'),
            'descurl': info.get('descriptionurl'),
            'license': license_name,
            'artist': artist,
            'credit': credit,
            'description': desc[:300],
            'sha1': info.get('sha1', ''),
        })
    return results


def license_ok(license_name):
    low = (license_name or '').lower()
    if not low:
        return False
    if any(h in low for h in FREE_LICENSE_HINTS):
        return True, False
    if any(h in low for h in ATTRIB_LICENSE_HINTS):
        return True, True  # needs attribution
    return False, False


def download(url, dest_path):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=40) as r:
            if r.status != 200:
                return False
            content = r.read()
        if len(content) < 8000:
            return False
        with open(dest_path, 'wb') as f:
            f.write(content)
        return True
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--count', type=int, default=100)
    parser.add_argument('--category', type=str, default=None)
    args = parser.parse_args()

    os.makedirs(STOCK_DIR, exist_ok=True)
    manifest = []
    if os.path.exists(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
        except Exception:
            manifest = []

    existing = {m.get('file') for m in manifest}
    seen_sha1 = {m.get('sha1') for m in manifest if m.get('sha1')}
    per_cat_target = max(1, args.count // len(CATEGORY_QUERIES))
    downloaded = 0

    categories = [args.category] if args.category else list(CATEGORY_QUERIES.keys())

    for cat in categories:
        cat_dir = os.path.join(STOCK_DIR, cat)
        os.makedirs(cat_dir, exist_ok=True)
        cat_count = sum(1 for m in manifest if m.get('category') == cat)
        queries = CATEGORY_QUERIES.get(cat, [])
        for q in queries:
            if cat_count >= per_cat_target or downloaded >= args.count:
                break
            print(f"[{cat}] arama: {q}")
            for item in search_images(q):
                if cat_count >= per_cat_target or downloaded >= args.count:
                    break
                ok, needs_attr = license_ok(item['license'])
                if not ok:
                    continue
                if item.get('sha1') and item['sha1'] in seen_sha1:
                    continue
                thumb = item.get('thumburl') or item.get('url')
                if not thumb:
                    continue
                ext = os.path.splitext(urllib.parse.urlparse(thumb).path)[1].lower()
                if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
                    ext = '.jpg'
                fname = hashlib.sha1(thumb.encode('utf-8')).hexdigest()[:16] + ext
                rel = f"assets/instagram/stock/{cat}/{fname}"
                if rel in existing:
                    continue
                dest = os.path.join(cat_dir, fname)
                if download(thumb, dest):
                    manifest.append({
                        'file': rel,
                        'category': cat,
                        'title': item['title'],
                        'license': item['license'],
                        'requires_attribution': needs_attr,
                        'artist': item['artist'],
                        'credit': item['credit'],
                        'description': item['description'],
                        'source': item['descurl'],
                        'sha1': item.get('sha1', ''),
                        'query': q,
                    })
                    existing.add(rel)
                    if item.get('sha1'):
                        seen_sha1.add(item['sha1'])
                    cat_count += 1
                    downloaded += 1
                    print(f"  + {rel}  [{item['license']}]")
                else:
                    print(f"  - indirilemedi: {thumb[:80]}")
                time.sleep(0.2)

    with open(MANIFEST_PATH, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    total = len(manifest)
    free = sum(1 for m in manifest if not m.get('requires_attribution'))
    print(f"\n[BITTI] Bu calismada indirilen: {downloaded}. Toplam kutuphane: {total} (CC0/PD: {free}).")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == '__main__':
    main()
