#!/usr/bin/env python3
"""
Sync Official Authentic FPV Product Images
Fetches studio-quality product images and galleries directly from verified
FPV catalog stores (RaceDayQuads, Pyrodrone, RotorRiot, BetaFPV, RadioMaster)
via their Shopify direct catalog APIs.
"""

import os
import sys
import json
import sqlite3
import urllib.request
import urllib.parse
import re
import time
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "pozitron.db")
PRODUCTS_DIR = os.path.join(BASE_DIR, "assets", "products")
CACHE_FILE = os.path.join(BASE_DIR, "data", "fpv_official_model_images.json")

os.makedirs(PRODUCTS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)

# Add BASE_DIR to sys.path so export_data can be imported
sys.path.insert(0, BASE_DIR)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json,text/html,*/*;q=0.8'
}

STORES = [
    'https://www.racedayquads.com',
    'https://pyrodrone.com',
    'https://rotorriot.com',
    'https://betafpv.com',
    'https://radiomasterrc.com'
]

NEGATIVE_KEYWORDS = [
    'adapter plate', 'cable wire', 'replacement bell', 'replacement shaft',
    'tpu mount', 'replacement arm', 'prop nut', 'nd filter set',
    'silicone case', 'bumper only', 'antenna mount', 'bottom plate only',
    'top plate only', 'upper main plate'
]

# Curated configurations for all core base models in Pozitron Market
MODELS_CATALOG = [
    # Motors
    {'id': 'F60 PRO V', 'cat': 'motors', 'q': 'T-Motor F60 Pro IV motor', 'require': ['f60', 'motor'], 'reject': ['nut', 'bell']},
    {'id': 'ECO II', 'cat': 'motors', 'q': 'EMAX ECO II motor', 'require': ['eco', 'motor'], 'reject': ['nut', 'bell']},
    {'id': 'XING2', 'cat': 'motors', 'q': 'iFlight Xing2 motor', 'require': ['xing2', 'motor'], 'reject': ['nut', 'bell', 'frame']},
    {'id': 'SPEEDX2', 'cat': 'motors', 'q': 'SPEEDX2 motor', 'require': ['speedx2', 'motor'], 'reject': ['nut', 'bell']},
    {'id': 'Avenger V3', 'cat': 'motors', 'q': 'BrotherHobby Avenger V3 motor', 'require': ['avenger', 'motor'], 'reject': ['nut']},
    {'id': 'Velox V3', 'cat': 'motors', 'q': 'VELOX V2207 V3 motor', 'require': ['velox', 'motor'], 'reject': ['nut']},
    {'id': 'NINJA', 'cat': 'motors', 'q': 'GEPRC 1404 motor', 'require': ['1404', 'motor'], 'reject': ['frame']},
    {'id': 'ROBO RB', 'cat': 'motors', 'q': 'Flywoo Robo motor', 'require': ['robo', 'motor'], 'reject': ['frame']},
    {'id': 'C2807', 'cat': 'motors', 'q': '2807 motor', 'require': ['2807', 'motor'], 'reject': ['frame']},
    {'id': 'U8 II Heavy Lift', 'cat': 'motors', 'q': 'T-Motor F80 Pro motor', 'require': ['f80', 'motor'], 'reject': ['prop']},
    {'id': 'V2207.5', 'cat': 'motors', 'q': '2207.5 motor', 'require': ['2207.5', 'motor'], 'reject': ['bell']},

    # ESCs
    {'id': 'F405 V4 55A', 'cat': 'esc', 'q': 'SpeedyBee F405 V4 55A Stack', 'require': ['speedybee', 'f405'], 'reject': ['cable']},
    {'id': 'Reaper 65A', 'cat': 'esc', 'q': 'Foxeer Reaper 65A ESC', 'require': ['reaper', '65a'], 'reject': ['vtx']},
    {'id': 'Tekko32 F4 4in1 50A', 'cat': 'esc', 'q': 'Holybro Tekko32 50A ESC', 'require': ['tekko32', '50a'], 'reject': []},
    {'id': 'F55A PRO II', 'cat': 'esc', 'q': 'T-Motor F55A Pro ESC', 'require': ['f55a'], 'reject': []},
    {'id': 'AM32 45A Mini', 'cat': 'esc', 'q': '45A AM32 ESC', 'require': ['45a', 'esc'], 'reject': []},
    {'id': 'Crossfire 4in1 60A', 'cat': 'esc', 'q': '60A 4in1 ESC', 'require': ['60a', 'esc'], 'reject': []},
    {'id': 'GOKU Versatile 40A', 'cat': 'esc', 'q': 'Flywoo GOKU 40A ESC', 'require': ['goku', '40a'], 'reject': []},
    {'id': 'Single 32Bit 45A ESC', 'cat': 'esc', 'q': 'Hobbywing 45A ESC', 'require': ['45a', 'esc'], 'reject': []},

    # Propellers
    {'id': 'Hurricane 51466 V2', 'cat': 'propellers', 'q': 'Gemfan Hurricane 51466 V2', 'require': ['51466'], 'reject': []},
    {'id': 'Ethix S3 Watermelon', 'cat': 'propellers', 'q': 'ETHIX S3 Watermelon prop', 'require': ['ethix', 's3'], 'reject': []},
    {'id': 'Cinewhoop D90S Ducted', 'cat': 'propellers', 'q': 'Gemfan D90 Ducted prop', 'require': ['d90'], 'reject': []},
    {'id': '7040 7-Inch Tri-Blade', 'cat': 'propellers', 'q': '7040 prop', 'require': ['7040'], 'reject': []},
    {'id': 'Ethix P3 Peanut Butter', 'cat': 'propellers', 'q': 'ETHIX P3 Peanut Butter prop', 'require': ['ethix', 'p3'], 'reject': []},
    {'id': 'Flash 5152', 'cat': 'propellers', 'q': 'Gemfan Flash 5149 prop', 'require': ['gemfan', 'flash'], 'reject': []},
    {'id': 'Foldable 1045', 'cat': 'propellers', 'q': '1045 propeller', 'require': ['1045'], 'reject': []},
    {'id': 'Micro 31mm 4-Blade', 'cat': 'propellers', 'q': 'Gemfan 31mm prop', 'require': ['31mm'], 'reject': []},

    # Converters
    {'id': 'Micro BEC Step-Down 5V/9V/12V', 'cat': 'converters', 'q': 'Matek Micro BEC', 'require': ['bec'], 'reject': []},
    {'id': 'PDB-XT60 Dual BEC', 'cat': 'converters', 'q': 'Matek PDB XT60', 'require': ['pdb'], 'reject': []},
    {'id': 'Low Noise LC Filter 3A', 'cat': 'converters', 'q': 'LC Filter FPV', 'require': ['filter'], 'reject': []},
    {'id': 'Buck-Boost Converter 12V 2A', 'cat': 'converters', 'q': '12V BEC module', 'require': ['bec'], 'reject': []},
    {'id': 'Current Sensor Board 150A', 'cat': 'converters', 'q': 'Current Sensor FPV', 'require': ['sensor'], 'reject': []},
    {'id': 'Power Hub PDB with 5V/9V BEC', 'cat': 'converters', 'q': 'Matek PDB BEC', 'require': ['pdb'], 'reject': []},

    # Flight Controllers
    {'id': 'F405 V4 Master FC', 'cat': 'flight_controllers', 'q': 'SpeedyBee F405 V4 Flight Controller', 'require': ['f405'], 'reject': []},
    {'id': 'F722 Dual Gyro Pro', 'cat': 'flight_controllers', 'q': 'F722 Flight Controller', 'require': ['f722'], 'reject': []},
    {'id': 'H743-WING V3', 'cat': 'flight_controllers', 'q': 'Matek H743-WING', 'require': ['h743'], 'reject': []},
    {'id': 'Pixhawk 6C Autopilot Flight Controller', 'cat': 'flight_controllers', 'q': 'Holybro Pixhawk 6C', 'require': ['pixhawk'], 'reject': []},
    {'id': 'F722 Mini AIO 40A', 'cat': 'flight_controllers', 'q': 'F722 AIO', 'require': ['f722'], 'reject': []},
    {'id': 'G473 High Performance FC', 'cat': 'flight_controllers', 'q': 'G473 Flight Controller', 'require': ['g473'], 'reject': []},

    # Cameras
    {'id': 'O3 Air Unit Camera & VTX Module', 'cat': 'cameras', 'q': 'DJI O4 Air Unit', 'require': ['o4', 'air unit'], 'reject': ['filter', 'cable', 'mount', 'case']},
    {'id': 'Avatar HD Pro Camera Kit', 'cat': 'cameras', 'q': 'Walksnail Avatar HD Pro Kit', 'require': ['avatar', 'pro'], 'reject': ['cable', 'lens']},
    {'id': 'Ratel 2 Micro FPV Camera', 'cat': 'cameras', 'q': 'Caddx Ratel 2 Micro', 'require': ['ratel'], 'reject': ['case', 'bracket']},
    {'id': 'Predator 5 Nano FPV Camera', 'cat': 'cameras', 'q': 'Foxeer Predator 5 Nano', 'require': ['predator'], 'reject': ['case']},
    {'id': 'HDZero Nano 90 Camera', 'cat': 'cameras', 'q': 'HDZero Nano 90 Camera', 'require': ['hdzero', 'nano'], 'reject': ['cable']},
    {'id': 'Thumb Pro 4K Action Camera', 'cat': 'cameras', 'q': 'RunCam Thumb Pro 4K', 'require': ['thumb'], 'reject': ['cable', 'nd filter']},

    # VTX
    {'id': 'Unify Pro32 HV 5.8GHz 1000mW', 'cat': 'vtx', 'q': 'TBS Unify Pro32 HV', 'require': ['unify', 'pro32'], 'reject': ['cable', 'antenna']},
    {'id': 'Reaper Extreme 2.5W VTX', 'cat': 'vtx', 'q': 'Foxeer Reaper Extreme 2.5W', 'require': ['reaper', 'extreme'], 'reject': ['cable']},
    {'id': 'Tank II Ultimate 1W VTX', 'cat': 'vtx', 'q': 'Rush Tank II Ultimate', 'require': ['tank'], 'reject': ['cable']},
    {'id': 'TX800 VTX 800mW Mini', 'cat': 'vtx', 'q': 'SpeedyBee TX800', 'require': ['tx800'], 'reject': ['cable', 'antenna']},
    {'id': 'Walksnail Avatar GT VTX 2W', 'cat': 'vtx', 'q': 'Walksnail Avatar GT 2W', 'require': ['avatar', 'gt'], 'reject': ['cable']},

    # Transmitters / Receivers
    {'id': 'TX16S MKII MAX Radio Transmitter', 'cat': 'transmitters_receivers', 'q': 'RadioMaster TX16S MKII', 'require': ['tx16s'], 'reject': ['case', 'strap', 'gimbal']},
    {'id': 'Boxer Radio Controller M2', 'cat': 'transmitters_receivers', 'q': 'RadioMaster Boxer Radio Controller', 'require': ['boxer'], 'reject': ['case', 'strap']},
    {'id': 'Pocket Radio Controller', 'cat': 'transmitters_receivers', 'q': 'RadioMaster Pocket Radio Controller', 'require': ['pocket'], 'reject': ['case']},
    {'id': 'RP1 ExpressLRS 2.4GHz Nano Receiver', 'cat': 'transmitters_receivers', 'q': 'RadioMaster RP1 ExpressLRS', 'require': ['rp1'], 'reject': ['antenna']},
    {'id': 'Crossfire Nano RX Pro', 'cat': 'transmitters_receivers', 'q': 'TBS Crossfire Nano RX Pro', 'require': ['crossfire', 'nano'], 'reject': ['antenna']},
    {'id': 'SuperD ELRS 2.4GHz Diversity Receiver', 'cat': 'transmitters_receivers', 'q': 'BetaFPV SuperD ELRS Diversity', 'require': ['superd'], 'reject': ['antenna']},

    # Batteries & Chargers
    {'id': 'R-Line Version 5.0 1400mAh 6S 150C', 'cat': 'batteries_chargers', 'q': 'Tattu R-Line Version 5.0 1400mAh 6S', 'require': ['r-line', '1400mah'], 'reject': ['lead', 'strap']},
    {'id': 'Black Series 1500mAh 4S 100C', 'cat': 'batteries_chargers', 'q': 'CNHL Black Series 1500mAh 4S', 'require': ['cnhl', '1500mah'], 'reject': ['strap']},
    {'id': 'Long Range 21700 6S2P 8000mAh Li-ion', 'cat': 'batteries_chargers', 'q': '21700 6S2P 8000mAh', 'require': ['21700'], 'reject': ['strap']},
    {'id': 'K4 Smart Dual Channel AC/DC Charger', 'cat': 'batteries_chargers', 'q': 'ISDT K4 Smart Charger', 'require': ['k4'], 'reject': ['cable']},
    {'id': '608AC Smart Pocket Charger 200W', 'cat': 'batteries_chargers', 'q': 'ISDT 608AC Smart Pocket Charger', 'require': ['608ac'], 'reject': ['cable']},
    {'id': 'M6D Dual Smart Charger 500W', 'cat': 'batteries_chargers', 'q': 'ToolkitRC M6D Dual Smart Charger', 'require': ['m6d'], 'reject': ['cable']},

    # Frames
    {'id': 'Nazgul5 V3 HD 5-Inch Frame Kit', 'cat': 'frames', 'q': 'iFlight Nazgul Evoque 5" Frame Kit', 'require': ['nazgul', 'frame'], 'reject': ['arm only', 'screw']},
    {'id': 'Mark5 O3 Freestyle Frame Kit', 'cat': 'frames', 'q': 'GEPRC Mark5 Wide X frame', 'require': ['mark5'], 'reject': ['plate', 'arm']},
    {'id': 'Source One V5 5-Inch Frame', 'cat': 'frames', 'q': 'TBS Source One V6 5" Frame Kit', 'require': ['source one'], 'reject': ['arm only']},
    {'id': 'Apex 5-Inch Freestyle Frame', 'cat': 'frames', 'q': 'Axisflying Manta 5" Frame Kit', 'require': ['frame', 'kit'], 'reject': ['arm only', 'plate']},
    {'id': 'Pavo25 V2 Cinewhoop Frame Kit', 'cat': 'frames', 'q': 'BetaFPV Pavo25 Frame', 'require': ['pavo25'], 'reject': ['duct only']},
    {'id': 'Explorer LR 4 HD Long Range Frame', 'cat': 'frames', 'q': 'Flywoo Explorer LR 4 Frame', 'require': ['explorer'], 'reject': ['arm only']},

    # Antennas
    {'id': 'Lollipop 4 Plus 5.8GHz Antenna (2-Pack)', 'cat': 'antennas', 'q': 'Foxeer Lollipop 4 Plus Antenna', 'require': ['lollipop'], 'reject': ['mount']},
    {'id': 'Triumph Pro 5.8GHz RHCP Antenna', 'cat': 'antennas', 'q': 'TBS Triumph Pro Antenna', 'require': ['triumph'], 'reject': ['mount']},
    {'id': 'Singularity 5.8GHz Directional Patch', 'cat': 'antennas', 'q': 'TrueRC Singularity 5.8GHz Patch', 'require': ['singularity'], 'reject': []},
    {'id': 'Matchstick 5.8GHz Carbon Antenna', 'cat': 'antennas', 'q': 'MenaceRC Matchstick Antenna', 'require': ['matchstick'], 'reject': []},

    # GPS & Telemetry
    {'id': 'M10-5883 High Precision GPS Module', 'cat': 'gps_telemetry', 'q': 'Matek M10-5883 GPS', 'require': ['m10-5883'], 'reject': ['mount']},
    {'id': 'Micro M8N GPS Module with Active Patch', 'cat': 'gps_telemetry', 'q': 'M8N GPS Module', 'require': ['m8n'], 'reject': ['mount']},
    {'id': 'Optical Flow & Lidar Sensor Board', 'cat': 'gps_telemetry', 'q': 'Matek Optical Flow Lidar', 'require': ['optical flow'], 'reject': []},

    # Tools
    {'id': 'TS101 Smart Digital Soldering Iron 65W', 'cat': 'tools_accessories', 'q': 'Miniware TS101 Soldering Iron', 'require': ['ts101'], 'reject': ['tip only']},
    {'id': 'Titanium Hex Screwdriver Tool Set (4-Piece)', 'cat': 'tools_accessories', 'q': 'Hex Screwdriver Tool Set', 'require': ['screwdriver'], 'reject': []},
    {'id': 'Smart Smoke Stopper XT60 & XT30', 'cat': 'tools_accessories', 'q': 'Vifly ShortSaver Smoke Stopper', 'require': ['shortsaver'], 'reject': []},
    {'id': 'High Purity 60/40 Rosin Core Solder Wire', 'cat': 'tools_accessories', 'q': 'Kester Solder Wire', 'require': ['solder'], 'reject': []},
    {'id': 'M2 & M3 Black Nylon & Steel Standoff Kit (300Pcs)', 'cat': 'tools_accessories', 'q': 'hardware standoff kit', 'require': ['standoff'], 'reject': []},

    # Original Flagship models
    {'id': 'DJI O3 Air Unit Digital HD Transmission Module', 'cat': 'cameras', 'q': 'DJI O4 Air Unit', 'require': ['o4', 'air unit'], 'reject': ['filter', 'cable', 'mount', 'case']},
    {'id': 'SpeedyBee F405 V4 BLS 55A 30x30 Stack', 'cat': 'flight_controllers', 'q': 'SpeedyBee F405 V4 BLS 55A Stack', 'require': ['speedybee', 'f405'], 'reject': []},
    {'id': 'RadioMaster Pocket ELRS 2.4GHz Radio Controller', 'cat': 'transmitters_receivers', 'q': 'RadioMaster Pocket Radio Controller', 'require': ['pocket'], 'reject': ['case']},
    {'id': 'BetaFPV Pavo20 Pro Brushless Whoop Frame Kit', 'cat': 'frames', 'q': 'BetaFPV Pavo20 Pro Frame', 'require': ['pavo20'], 'reject': []},
    {'id': 'Caddx Walksnail Avatar HD Pro Kit (Dual Antennas)', 'cat': 'cameras', 'q': 'Walksnail Avatar HD Pro Kit', 'require': ['avatar', 'pro'], 'reject': []},
    {'id': 'Foxeer Reaper F4 128K 65A 32Bit 4in1 ESC', 'cat': 'esc', 'q': 'Foxeer Reaper 65A ESC', 'require': ['reaper', '65a'], 'reject': []},
    {'id': 'T-Motor Velox V3 V2207 1950KV Freestyle Motor', 'cat': 'motors', 'q': 'VELOX V2207 V3 motor', 'require': ['velox', 'motor'], 'reject': []},
    {'id': 'ToolkitRC M6D 500W 15A Dual Channel Smart DC Charger', 'cat': 'batteries_chargers', 'q': 'ToolkitRC M6D Dual Smart Charger', 'require': ['m6d'], 'reject': []}
]

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)

def query_store_for_model(cfg):
    query = cfg['q']
    require = [w.lower() for w in cfg.get('require', [])]
    reject = [w.lower() for w in cfg.get('reject', [])] + NEGATIVE_KEYWORDS

    for base in STORES:
        url = f"{base}/search/suggest.json?q={urllib.parse.quote(query)}&resources[type]=product"
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5) as res:
                if res.status != 200:
                    continue
                data = json.loads(res.read().decode('utf-8'))
                products = data.get('resources', {}).get('results', {}).get('products', [])

                for p in products:
                    title = p.get('title', '')
                    t_lower = title.lower()

                    # Check rejects
                    if any(rej in t_lower for rej in reject):
                        continue

                    # Check required tokens
                    if all(req_w in t_lower for req_w in require):
                        handle = p.get('handle')
                        gallery_images = []
                        if handle:
                            try:
                                prod_url = f"{base}/products/{handle}.json"
                                prod_req = urllib.request.Request(prod_url, headers=HEADERS)
                                with urllib.request.urlopen(prod_req, timeout=5) as prod_res:
                                    prod_data = json.loads(prod_res.read().decode('utf-8'))
                                    raw_imgs = prod_data.get('product', {}).get('images', [])
                                    for img_obj in raw_imgs:
                                        src = img_obj.get('src')
                                        if src:
                                            if src.startswith('//'):
                                                src = 'https:' + src
                                            gallery_images.append(src)
                            except Exception:
                                pass

                        primary_img = p.get('image')
                        if primary_img and primary_img.startswith('//'):
                            primary_img = 'https:' + primary_img

                        if not gallery_images and primary_img:
                            gallery_images = [primary_img]

                        if primary_img or gallery_images:
                            return {
                                'source_store': base,
                                'matched_title': title,
                                'primary_image': primary_img or gallery_images[0],
                                'gallery': gallery_images[:5]
                            }
        except Exception:
            continue
    return None

def download_and_validate_image(img_url, dest_path):
    if not img_url:
        return False
    # Try direct URL
    try:
        req = urllib.request.Request(img_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as res:
            if res.status == 200:
                data = res.read()
                if len(data) > 3000:
                    with open(dest_path, 'wb') as f:
                        f.write(data)
                    with Image.open(dest_path) as im:
                        im.verify()
                    return True
    except Exception:
        pass

    # Try high-res shopify parameter
    try:
        clean_url = re.sub(r'(\?v=\d+|_small|_medium|_large|_compact|_grande)', '', img_url)
        clean_url += '?v=1&width=1000'
        req = urllib.request.Request(clean_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=8) as res:
            if res.status == 200:
                data = res.read()
                if len(data) > 3000:
                    with open(dest_path, 'wb') as f:
                        f.write(data)
                    with Image.open(dest_path) as im:
                        im.verify()
                    return True
    except Exception:
        pass

    return False

def build_model_cache():
    cache = load_cache()
    print(f"Loaded existing model image cache with {len(cache)} entries.")
    total = len(MODELS_CATALOG)
    updated = False

    for i, cfg in enumerate(MODELS_CATALOG, 1):
        model_id = cfg['id']
        # Re-check models that were missing or needed refinement
        if model_id in cache and cache[model_id].get('primary_image'):
            # If title has 'plate' or 'arm', re-fetch
            cached_title = cache[model_id].get('matched_title', '').lower()
            if not any(bad in cached_title for bad in ['upper main plate', 'top plate', 'replacement arm', 'flylens 85']):
                continue

        print(f"[{i}/{total}] Searching official FPV catalogs for: {model_id} ({cfg['q']})...")
        res = query_store_for_model(cfg)
        if res:
            print(f"  ✅ Found at {res['source_store']}: {res['matched_title'][:55]} ({len(res['gallery'])} photos)")
            cache[model_id] = res
            updated = True
        else:
            print(f"  ⚠️ No match found for: {model_id}")
        time.sleep(0.15)

    if updated or not os.path.exists(CACHE_FILE):
        save_cache(cache)
        print(f"Saved updated cache ({len(cache)} models).")

    return cache

def sync_products_with_official_images():
    cache = build_model_cache()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, sku, brand, name_en, category_id, specs_json FROM products ORDER BY id ASC")
    products = cursor.fetchall()
    
    print(f"\nProcessing {len(products)} products against official FPV images...")
    
    sorted_model_keys = sorted(cache.keys(), key=len, reverse=True)
    
    # Pre-download images for each distinct model in cache
    downloaded_model_images = {}
    for m_id, m_info in cache.items():
        p_url = m_info.get('primary_image')
        if p_url:
            model_clean_name = re.sub(r'[^a-zA-Z0-9_-]', '_', m_id)
            model_cache_img = os.path.join(PRODUCTS_DIR, f"model_{model_clean_name}.jpg")
            if download_and_validate_image(p_url, model_cache_img):
                downloaded_model_images[m_id] = model_cache_img
                
    print(f"Successfully downloaded {len(downloaded_model_images)}/{len(cache)} official base model master images.")
    
    success_count = 0
    total = len(products)
    
    for i, prod in enumerate(products, 1):
        p_id, sku, brand, name_en, cat_id, specs_json = prod
        clean_sku = re.sub(r'[^a-zA-Z0-9_-]', '', sku)
        dest_filename = f"{clean_sku}.jpg"
        dest_path = os.path.join(PRODUCTS_DIR, dest_filename)
        
        specs = {}
        try:
            specs = json.loads(specs_json) if specs_json else {}
        except Exception:
            pass
        
        model_name = specs.get('model', '')
        
        # Exact or substring match in model or name
        matched_model_id = None
        for b in sorted_model_keys:
            if b.lower() in model_name.lower() or b.lower() in name_en.lower():
                matched_model_id = b
                break
                
        # Token fallback
        if not matched_model_id:
            for b in sorted_model_keys:
                tokens = [t for t in re.split(r'[\s\-_]+', b) if len(t) > 3]
                if any(t.lower() in name_en.lower() for t in tokens):
                    matched_model_id = b
                    break
        
        model_info = cache.get(matched_model_id) if matched_model_id else None
        
        primary_url = model_info.get('primary_image') if model_info else None
        gallery_urls = model_info.get('gallery', []) if model_info else []
        
        local_rel_path = f"./assets/products/{dest_filename}"
        saved = False
        
        # Copy from pre-downloaded master image if available
        if matched_model_id in downloaded_model_images:
            master_img = downloaded_model_images[matched_model_id]
            try:
                with open(master_img, 'rb') as src_f:
                    with open(dest_path, 'wb') as dst_f:
                        dst_f.write(src_f.read())
                saved = True
            except Exception:
                pass
        elif primary_url:
            saved = download_and_validate_image(primary_url, dest_path)
            
        final_img = local_rel_path if saved else (primary_url or f"./assets/products/{cat_id}.png")
        
        full_gallery = [final_img]
        for g_url in gallery_urls:
            if g_url not in full_gallery:
                full_gallery.append(g_url)
                
        gallery_json = json.dumps(full_gallery, ensure_ascii=False)
        
        cursor.execute("UPDATE products SET image_url = ?, gallery_json = ? WHERE id = ?", (final_img, gallery_json, p_id))
        
        if saved:
            success_count += 1
            
        if i % 100 == 0 or i == total:
            print(f"Progress: [{i}/{total}] ({round(i/total*100)}%) - Successfully synced {success_count}/{i} real FPV images.")
            
    conn.commit()
    conn.close()
    
    print(f"\n✅ Finished syncing all {len(products)} products! {success_count}/{total} studio images saved.")
    
    print("\nRegenerating static bundles, sitemaps, and feeds via export_data...")
    from export_data import export_static_data
    export_static_data()
    
    print("\n🎉 All product images, databases, and feeds successfully updated with official FPV catalog data!")

if __name__ == '__main__':
    sync_products_with_official_images()
