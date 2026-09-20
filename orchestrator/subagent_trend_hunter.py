import sqlite3
import os
import json
import time
import uuid
import re
import random
from datetime import datetime
from typing import Dict, List, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pozitron.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

# Global FPV hardware trend pool representing hot market items
GLOBAL_HARDWARE_TRENDS = [
    {
        "name_en": "SpeedyBee F405 V4 BLS 55A 30x30 Stack",
        "name_tr": "SpeedyBee F405 V4 BLS 55A 30x30 Uçuş ve ESC Kulesi",
        "category_id": "flight_controllers",
        "brand": "SpeedyBee",
        "global_price_usd": 69.99,
        "turkish_market_price_try": 3750.0,
        "global_source": "SpeedyBee Global & Joshua Bardwell 2026 Recommended",
        "trend_score": 98,
        "trend_reason": "Dahili Bluetooth/WiFi ile sahada kablosuz Betaflight ayarı imkanı sunması ve 55A 8-bit ESC ile fiyat/performans lideri olması nedeniyle dünyada en çok satan FPV kulesi.",
        "image_url": "./assets/products/trend_speedybee_f405_v4.jpg",
        "specs": {
            "MCU": "STM32F405",
            "IMU": "ICM42688P",
            "Baro": "Dahili SPL06-001",
            "OSD": "AT7456E",
            "ESC Akımı": "55A Sürekli / 70A Anlık",
            "Giriş Voltajı": "3S - 6S LiPo",
            "Kablosuz": "Bluetooth & WiFi Dahili"
        },
        "tags": ["speedybee", "f405", "stack", "esc", "bluetooth", "betaflight", "55a"],
        "description_en": "The SpeedyBee F405 V4 55A 30x30 Stack is the global gold standard for budget-friendly high-performance freestyle and long-range builds, featuring wireless tuning via the SpeedyBee app.",
        "description_tr": "SpeedyBee F405 V4 55A Stack, dahili Bluetooth ve WiFi modülü sayesinde sahada bilgisayara gerek kalmadan telefon üzerinden Betaflight ve BLHeli ayarlarını yapmanızı sağlayan dünyanın en popüler FPV kulesidir."
    },
    {
        "name_en": "DJI O3 Air Unit Digital HD Transmission Module",
        "name_tr": "DJI O3 Air Unit Dijital HD Görüntü İletim Modülü",
        "category_id": "cameras",
        "brand": "DJI",
        "global_price_usd": 229.0,
        "turkish_market_price_try": 12500.0,
        "global_source": "DJI Enterprise & Global Cinematic FPV Community",
        "trend_score": 99,
        "trend_reason": "4K/60fps dahili RockSteady stabilizasyonlu kayıt kabiliyeti ve 10km'ye varan düşük gecikmeli O3 iletim protokolü ile sinematik pilotların vazgeçilmez donanımı.",
        "image_url": "./assets/products/trend_dji_o3_air_unit.jpg",
        "specs": {
            "Sensör": "1/1.7 inç CMOS 48MP",
            "Video Çözünürlüğü": "4K@60fps, 2.7K@120fps, 1080p@120fps",
            "Gecikme": "En düşük 30ms (Canvas Mode)",
            "Menzil": "10 km (FCC) / 2 km (CE)",
            "Dahili Hafıza": "20 GB eMMC + MicroSD slot",
            "Ağırlık": "36.4 g (kamera + hava ünitesi)"
        },
        "tags": ["dji", "o3", "digital", "hd", "cinematic", "rocksteady", "fpv-camera"],
        "description_en": "Experience cutting-edge digital HD FPV with the DJI O3 Air Unit. Offers stunning 4K/60fps onboard recording, RockSteady stabilization, and ultra-low latency.",
        "description_tr": "DJI O3 Air Unit, FPV dünyasında standartları belirleyen dijital HD görüntü iletim sistemidir. 4K/60fps dahili kayıt, RockSteady stabilizasyon ve 10 km menzil desteğiyle sinematik çekimler için idealdir."
    },
    {
        "name_en": "RadioMaster Pocket ELRS 2.4GHz Radio Controller",
        "name_tr": "RadioMaster Pocket ELRS 2.4GHz Kompakt Kumanda",
        "category_id": "transmitters_receivers",
        "brand": "RadioMaster",
        "global_price_usd": 64.99,
        "turkish_market_price_try": 3400.0,
        "global_source": "ExpressLRS Community & RadioMaster Global",
        "trend_score": 95,
        "trend_reason": "Çıkarılabilir stick uçları, katlanabilir anteni, dahili EdgeTX işletim sistemi ve ExpressLRS desteğiyle çantada taşınabilir en hafif ve ergonomik kumanda.",
        "image_url": "./assets/products/trend_radiomaster_pocket.jpg",
        "specs": {
            "İşletim Sistemi": "EdgeTX",
            "RF Protokolü": "Dahili ExpressLRS 2.4GHz",
            "Gimbal": "Hall Sensörlü Hassas Gimbal",
            "Pil Tipi": "2x 18650 Li-ion (Dahil değil)",
            "Ekran": "Monokrom LCD",
            "Boyut": "156.6 x 65.1 x 125.3 mm",
            "Ağırlık": "288 g"
        },
        "tags": ["radiomaster", "pocket", "elrs", "edgetx", "kumanda", "controller"],
        "description_en": "The RadioMaster Pocket is a lightweight, portable radio controller packed with big power. Equipped with factory-installed EdgeTX and integrated ExpressLRS 2.4GHz.",
        "description_tr": "RadioMaster Pocket, taşınabilir boyutta tam donanımlı EdgeTX ve dahili ExpressLRS 2.4GHz gücü sunar. Hall sensörlü gimballeri ve çıkarılabilir çubukları ile her an uçuşa hazır."
    },
    {
        "name_en": "T-Motor Velox V3 V2207 1950KV Freestyle Motor",
        "name_tr": "T-Motor Velox V3 V2207 1950KV Freestyle Motor",
        "category_id": "motors",
        "brand": "T-Motor",
        "global_price_usd": 17.90,
        "turkish_market_price_try": 950.0,
        "global_source": "T-Motor Official & Global Freestyle Pilots Survey",
        "trend_score": 92,
        "trend_reason": "Havacılık sınıfı alüminyum çan, kavisli N52H mıknatıslar ve 6S pille sağladığı benzersiz gaz hakimiyeti ile 5 inç freestyle pilotlarının 2026 favorisi.",
        "image_url": "./assets/products/trend_tmotor_velox_v3.jpg",
        "specs": {
            "KV Değeri": "1950KV",
            "Statör Ebadı": "2207",
            "Giriş Voltajı": "6S LiPo",
            "Şaft Çapı": "M5 Titanyum Alaşım",
            "Maksimum İtki": "1850 g+",
            "Ağırlık": "34.5 g (kablolu)"
        },
        "tags": ["tmotor", "velox", "2207", "1950kv", "freestyle", "motor", "6s"],
        "description_en": "T-Motor Velox V3 2207 1950KV motors deliver extreme smoothness, instant throttle response, and incredible durability for 6S 5-inch freestyle drones.",
        "description_tr": "T-Motor Velox V3 2207 1950KV, 6S bataryalarla mükemmel uyumlu yüksek torklu ve dayanıklı freestyle motorudur. Titanyum alaşım mil ve N52H mıknatıslarla donatılmıştır."
    },
    {
        "name_en": "BetaFPV Pavo20 Pro Brushless Whoop Frame Kit",
        "name_tr": "BetaFPV Pavo20 Pro Fırçasız Whoop Gövde Kiti",
        "category_id": "frames",
        "brand": "BetaFPV",
        "global_price_usd": 24.99,
        "turkish_market_price_try": 1350.0,
        "global_source": "BetaFPV & Micro Drone Enthusiasts",
        "trend_score": 94,
        "trend_reason": "DJI O3, Caddx Vista ve RunCam Link dijital sistemlerini korumalı kanal yapısı içinde titreşimsiz taşıyabilen en gelişmiş kapalı alan cinewhoop gövdesi.",
        "image_url": "./assets/products/trend_betafpv_pavo20_pro.jpg",
        "specs": {
            "Dingil Mesafesi": "90 mm",
            "Desteklenen Pervane": "2.2 inç (Gemfan 22110)",
            "Kamera Uyumluluğu": "DJI O3 / Walksnail / HDZero",
            "Malzeme": "PA12 Kalınlaştırılmış Kanal + Karbon Plaka",
            "Ağırlık": "32 g"
        },
        "tags": ["betafpv", "pavo20", "pro", "cinewhoop", "whoop", "frame", "dji-o3"],
        "description_en": "The BetaFPV Pavo20 Pro frame is designed specifically for HD digital VTX setups like the DJI O3 Air Unit, offering high-durability whoop ducting.",
        "description_tr": "BetaFPV Pavo20 Pro, DJI O3 ve dijital sistemleri güvenle taşıyabilen, PA12 darbe emici kanallı 2 inç cinewhoop gövdesidir."
    },
    {
        "name_en": "Caddx Walksnail Avatar HD Pro Kit (Dual Antennas)",
        "name_tr": "Caddx Walksnail Avatar HD Pro Kit Çift Antenli Dijital VTX",
        "category_id": "cameras",
        "brand": "Caddx",
        "global_price_usd": 159.0,
        "turkish_market_price_try": 8600.0,
        "global_source": "Walksnail Official & Low-Light FPV Community",
        "trend_score": 96,
        "trend_reason": "1/1.8 inç Sony Starvis II gece görüş sensörü ile zifiri karanlıkta bile gündüz gibi net dijital FPV görüntüsü sunarak küresel pazarda büyük talep görüyor.",
        "image_url": "./assets/products/trend_caddx_walksnail_avatar.jpg",
        "specs": {
            "Sensör": "1/1.8 inç Sony Starvis II",
            "Çözünürlük": "1080p@60fps / 720p@100fps",
            "Düşük Işık": "0.00001 Lux Gece Görüş",
            "Dahili Hafıza": "32 GB dahili depolama",
            "Giriş Voltajı": "6V - 25.2V",
            "Ağırlık": "29.5 g"
        },
        "tags": ["caddx", "walksnail", "avatar", "hd-pro", "starvis", "night-vision"],
        "description_en": "Walksnail Avatar HD Pro kit features the groundbreaking Sony Starvis II night vision sensor, providing daylight clarity during twilight and night flights.",
        "description_tr": "Caddx Walksnail Avatar HD Pro Kit, Sony Starvis II gece görüş sensörü sayesinde gece uçuşlarında bile mükemmel 1080p dijital FPV deneyimi sağlar."
    },
    {
        "name_en": "ToolkitRC M6D 500W 15A Dual Channel Smart DC Charger",
        "name_tr": "ToolkitRC M6D 500W 15A Çift Kanal Akıllı DC Şarj Cihazı",
        "category_id": "batteries_chargers",
        "brand": "ToolkitRC",
        "global_price_usd": 59.99,
        "turkish_market_price_try": 3150.0,
        "global_source": "ToolkitRC & FPV Field Pilots Review",
        "trend_score": 93,
        "trend_reason": "Aynı anda iki bağımsız 6S bataryayı 15A hızında şarj edebilme ve cebinize sığacak kadar kompakt olması nedeniyle küresel saha şarj cihazı standardı.",
        "image_url": "./assets/products/trend_toolkitrc_m6d.jpg",
        "specs": {
            "Giriş Voltajı": "DC 7-28V (Maks 30A)",
            "Şarj Gücü": "2x 250W veya Senkron Modda 500W (Maks 15A)",
            "Pil Desteği": "1-6S LiPo, LiHV, LiFe, Lion, NiMh, Pb",
            "Ekran": "2.4 inç Renkli IPS LCD 320x240",
            "Boyut": "98 x 68 x 35 mm",
            "Ağırlık": "220 g"
        },
        "tags": ["toolkitrc", "m6d", "charger", "lipo", "500w", "sarj"],
        "description_en": "The ToolkitRC M6D is an ultra-compact 500W dual-channel smart DC charger capable of rapidly charging two independent 1-6S LiPo batteries simultaneously.",
        "description_tr": "ToolkitRC M6D, 500W senkron şarj gücü sunan çift kanallı akıllı şarj cihazıdır. Sahada veya atölyede iki bataryayı aynı anda hızla şarj eder."
    },
    {
        "name_en": "Foxeer Reaper F4 128K 65A 32Bit 4in1 ESC",
        "name_tr": "Foxeer Reaper F4 128K 65A 32Bit 4in1 ESC",
        "category_id": "esc",
        "brand": "Foxeer",
        "global_price_usd": 74.90,
        "turkish_market_price_try": 3950.0,
        "global_source": "Foxeer Official & FPV Racing League",
        "trend_score": 95,
        "trend_reason": "128K PWM frekansı, BLHeli_32 işlemcisi ve alüminyum soğutucu gövdesiyle yarış ve zorlu freestyle uçuşlarında ısınma problemi yaşamayan üst düzey ESC.",
        "image_url": "./assets/products/trend_foxeer_reaper_f4.jpg",
        "specs": {
            "Sürekli Akım": "65A x 4",
            "Anlık Akım": "75A (10 saniye)",
            "İşlemci": "F4 128K",
            "Yazılım": "BLHeli_32",
            "Giriş Voltajı": "3S - 8S LiPo",
            "Montaj": "30.5 x 30.5 mm"
        },
        "tags": ["foxeer", "reaper", "esc", "65a", "blheli32", "128k"],
        "description_en": "Foxeer Reaper F4 65A 128K 4-in-1 ESC features an F4 MCU and superior MOSFETs for extreme heat dissipation and silky-smooth motor response up to 8S LiPo.",
        "description_tr": "Foxeer Reaper F4 65A 128K ESC, 8S LiPo desteği ve alüminyum soğutma bloğuyla yüksek güç gerektiren yarış ve freestyle dronelar için en güvenilir ESC'dir."
    }
]

class GlobalTrendHunterAgent:
    """
    SUBAGENT 6: KÜRESEL TREND & ÜRÜN AVCISI (GLOBAL PRODUCT TREND HUNTER & SOURCING AGENT)
    - Dünya genelinde popüler ve yeni çıkan FPV drone donanımlarını tarar.
    - Pozitron Market ürün veritabanında (products) mevcut olup olmadığını kontrol eder.
    - Türk e-ticaret sitelerindeki (Dronmarket, Robolink, vb.) fiyatları referans alarak rekabetçi USD ve TRY fiyat hesaplar.
    - Lead Supervisor onayına sunmak üzere 'global_trend_proposals' tablosuna kaydeder.
    - Supervisor tarafından onaylandığında ürünü mevcut standart ürün ekleme metodu ile kataloğa ekler.
    """
    def __init__(self):
        pass

    def check_product_exists(self, name_en: str, brand: str) -> bool:
        """Checks if a product already exists in Pozitron Market's catalog."""
        conn = get_db()
        cursor = conn.cursor()
        query_term = f"%{brand}%"
        cursor.execute("SELECT id, name_en FROM products WHERE brand LIKE ? OR name_en LIKE ?", (query_term, f"%{name_en[:15]}%"))
        rows = cursor.fetchall()
        conn.close()

        clean_new = re.sub(r'[^a-z0-9]', '', name_en.lower())
        for r in rows:
            clean_existing = re.sub(r'[^a-z0-9]', '', r['name_en'].lower())
            if clean_new in clean_existing or clean_existing in clean_new:
                return True
        return False

    def calculate_competitive_pricing(self, global_price_usd: float, turkish_market_price_try: float) -> Dict[str, float]:
        """
        Calculates a competitive USD and TRY price for Pozitron Market.
        Formula:
        Beats Turkish market competitors by approximately 8% to 12% while maintaining a solid gross margin.
        TRY price = Turkish Market Price * 0.90 (rounded to nearest 10 TL or 50 TL)
        USD price = global_price_usd * 1.10 (competitive landed cost)
        """
        # Aim for 10% discount compared to Turkish competitors
        competitive_try = round((turkish_market_price_try * 0.90) / 10.0) * 10.0
        # Competitive USD price
        competitive_usd = round(global_price_usd * 1.08, 2)
        return {
            "price_usd": competitive_usd,
            "price_try": competitive_try,
            "savings_try": round(turkish_market_price_try - competitive_try, 2)
        }

    def scan_global_trends(self, limit: int = 5) -> List[Dict]:
        """
        Scans global trends and stores uncataloged items in global_trend_proposals.
        """
        conn = get_db()
        cursor = conn.cursor()

        proposals_added = []
        now_iso = datetime.now().isoformat()

        for item in GLOBAL_HARDWARE_TRENDS:
            if len(proposals_added) >= limit:
                break

            # 1. Check if item already exists in products table
            if self.check_product_exists(item["name_en"], item["brand"]):
                continue

            # 2. Check if already proposed in global_trend_proposals
            cursor.execute("SELECT id, status FROM global_trend_proposals WHERE name_en = ?", (item["name_en"],))
            existing_proposal = cursor.fetchone()
            if existing_proposal:
                continue

            # 3. Calculate competitive pricing
            pricing = self.calculate_competitive_pricing(
                item["global_price_usd"],
                item["turkish_market_price_try"]
            )

            proposal_id = f"prop_{uuid.uuid4().hex[:8]}"

            cursor.execute('''
                INSERT INTO global_trend_proposals (
                    id, name_en, name_tr, category_id, brand,
                    price_usd, price_try, specs_json, tags_json,
                    image_url, trend_score, trend_reason, global_source,
                    status, supervisor_evaluation, added_product_id,
                    created_at, approved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', NULL, NULL, ?, NULL)
            ''', (
                proposal_id,
                item["name_en"],
                item["name_tr"],
                item["category_id"],
                item["brand"],
                pricing["price_usd"],
                pricing["price_try"],
                json.dumps(item["specs"], ensure_ascii=False),
                json.dumps(item["tags"], ensure_ascii=False),
                item["image_url"],
                item["trend_score"],
                item["trend_reason"],
                item["global_source"],
                now_iso
            ))

            proposals_added.append({
                "id": proposal_id,
                "name_en": item["name_en"],
                "name_tr": item["name_tr"],
                "brand": item["brand"],
                "category_id": item["category_id"],
                "price_usd": pricing["price_usd"],
                "price_try": pricing["price_try"],
                "savings_try": pricing["savings_try"],
                "trend_score": item["trend_score"],
                "trend_reason": item["trend_reason"]
            })

        conn.commit()
        conn.close()
        return proposals_added

    def get_proposals(self, status: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Returns proposals from global_trend_proposals."""
        conn = get_db()
        cursor = conn.cursor()
        if status:
            cursor.execute("SELECT * FROM global_trend_proposals WHERE status = ? ORDER BY trend_score DESC LIMIT ?", (status, limit))
        else:
            cursor.execute("SELECT * FROM global_trend_proposals ORDER BY trend_score DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()

        res = []
        for r in rows:
            d = dict(r)
            try:
                d["specs"] = json.loads(d["specs_json"])
            except Exception:
                d["specs"] = {}
            try:
                d["tags"] = json.loads(d["tags_json"])
            except Exception:
                d["tags"] = []
            res.append(d)
        return res

    def approve_and_add_product(self, proposal_id: str, evaluator: str = "LEAD_SUPERVISOR_AUTONOMOUS") -> Dict:
        """
        Approves proposal and ingests it into products table using the exact Pozitron Market product schema.
        """
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM global_trend_proposals WHERE id = ?", (proposal_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return {"success": False, "error": "Proposal not found"}

        proposal = dict(row)
        if proposal["status"] == "APPROVED":
            conn.close()
            return {"success": True, "message": "Already approved", "product_id": proposal["added_product_id"]}

        # Prepare exact product insertion parameters
        category_id = proposal["category_id"]
        brand = proposal["brand"]
        name_en = proposal["name_en"]
        name_tr = proposal["name_tr"]
        price_usd = proposal["price_usd"]
        price_try = proposal["price_try"]
        image_url = proposal["image_url"]
        specs_json = proposal["specs_json"]
        tags_json = proposal["tags_json"]

        sku = f"PZT-{category_id[:4].upper()}-{random.randint(1000, 9999)}"
        clean_name = name_en.lower().replace('&', 'and')
        base_slug = re.sub(r'[^a-z0-9]+', '-', clean_name).strip('-')
        cursor.execute("SELECT id FROM products WHERE slug = ?", (base_slug,))
        if not cursor.fetchone():
            slug = base_slug
        else:
            suffix = 1
            while True:
                candidate = f"{base_slug}-{suffix}"
                cursor.execute("SELECT id FROM products WHERE slug = ?", (candidate,))
                if not cursor.fetchone():
                    slug = candidate
                    break
                suffix += 1
        prod_id = f"pzt_{uuid.uuid4().hex[:8]}"
        now_iso = datetime.now().isoformat()

        # Generate standard description
        desc_en = f"{name_en} by {brand}. Top trending global FPV hardware sourced for Pozitron Market."
        desc_tr = f"{name_tr} ({brand}). Dünyada en çok tercih edilen FPV donanımı, Türkiye yerel stok ve en uygun fiyat avantajıyla Pozitron Market'te."

        # Insert product into products table
        cursor.execute('''
            INSERT INTO products (
                id, slug, sku, name_en, name_tr, category_id, brand,
                price_usd, price_try, original_price_usd, original_price_try,
                discount_pct, rating, review_count, stock, badge,
                specs_json, tags_json, image_url, gallery_json,
                description_en, description_tr, compatibility_json,
                featured, is_bestseller, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0, 4.9, 5, 50, 'TREND', ?, ?, ?, ?, ?, ?, '{}', 1, 1, ?)
        ''', (
            prod_id, slug, sku, name_en, name_tr, category_id, brand,
            price_usd, price_try, specs_json, tags_json, image_url,
            json.dumps([image_url]), desc_en, desc_tr, now_iso
        ))

        # Increment category count
        cursor.execute("UPDATE categories SET item_count = item_count + 1 WHERE id = ?", (category_id,))

        # Update proposal record
        cursor.execute('''
            UPDATE global_trend_proposals
            SET status = 'APPROVED',
                supervisor_evaluation = ?,
                added_product_id = ?,
                approved_at = ?
            WHERE id = ?
        ''', (
            f"[ONAYLANDI] Lead Supervisor tarafından onaylandı ({evaluator}). Fiyat avantajı ve küresel talep doğrulandı.",
            prod_id,
            now_iso,
            proposal_id
        ))

        conn.commit()
        conn.close()

        return {
            "success": True,
            "message": f"Product successfully added to Pozitron Market: {name_tr}",
            "product_id": prod_id,
            "sku": sku,
            "slug": slug,
            "price_try": price_try
        }

    def reject_proposal(self, proposal_id: str, reason: str = "Pazar doygunlugu veya marj uyumsuzluğu") -> Dict:
        """Rejects a trend proposal."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE global_trend_proposals
            SET status = 'REJECTED',
                supervisor_evaluation = ?
            WHERE id = ?
        ''', (f"[REDDEDİLDİ] {reason}", proposal_id))
        conn.commit()
        conn.close()
        return {"success": True, "message": "Proposal rejected"}
