import json
import random
import urllib.request
import urllib.error
import sqlite3
import os
from datetime import datetime
from .db import get_db, get_recent_posted_product_ids

class ContentGenerator:
    def __init__(self, gemini_api_key: str = ""):
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")

    def set_api_key(self, key: str):
        self.gemini_api_key = key

    def generate_content(self, content_type: str = None, product_id: str = None) -> dict:
        """
        Generates content dictionary:
        {
            'content_type': str,
            'product_id': str or None,
            'title': str,
            'caption': str,
            'hashtags': str,
            'product_data': dict or None,
            'tool_info': dict or None
        }
        """
        valid_types = ['product_spotlight', 'tool_showcase', 'deal_drop', 'pilot_tip', 'review_highlight']
        if not content_type or content_type not in valid_types:
            weights = [0.50, 0.20, 0.10, 0.15, 0.05]
            content_type = random.choices(valid_types, weights=weights, k=1)[0]

        if content_type == 'product_spotlight':
            return self._generate_product_spotlight(product_id)
        elif content_type == 'tool_showcase':
            return self._generate_tool_showcase()
        elif content_type == 'deal_drop':
            return self._generate_deal_drop()
        elif content_type == 'pilot_tip':
            return self._generate_pilot_tip()
        elif content_type == 'review_highlight':
            return self._generate_review_highlight()
        else:
            return self._generate_product_spotlight(product_id)

    def _get_candidate_product(self, product_id: str = None):
        conn = get_db()
        cursor = conn.cursor()
        
        if product_id:
            cursor.execute("SELECT * FROM products WHERE id = ? OR slug = ?", (product_id, product_id))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None

        # Exclude recently posted products
        recent_ids = get_recent_posted_product_ids(20)
        query = "SELECT * FROM products"
        params = []
        if recent_ids:
            placeholders = ','.join('?' for _ in recent_ids)
            query += f" WHERE id NOT IN ({placeholders})"
            params.extend(recent_ids)
        
        query += " ORDER BY featured DESC, rating DESC, review_count DESC LIMIT 40"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products ORDER BY RANDOM() LIMIT 1")
            rows = cursor.fetchall()
            conn.close()

        selected = random.choice(rows)
        return dict(selected)

    def _generate_product_spotlight(self, product_id: str = None) -> dict:
        prod = self._get_candidate_product(product_id)
        if not prod:
            raise ValueError("Katalogda paylaşılacak ürün bulunamadı.")

        name = prod['name_tr'] or prod['name_en']
        brand = prod.get('brand', 'Pozitron')
        price_try = prod.get('price_try', 0.0)
        price_usd = prod.get('price_usd', 0.0)
        orig_try = prod.get('original_price_try')
        discount_pct = prod.get('discount_pct', 0)
        slug = prod.get('slug', prod['id'])
        specs = {}
        try:
            specs = json.loads(prod.get('specs_json', '{}'))
        except Exception:
            specs = {}

        # Heuristic Turkish copy
        hooks = [
            f"⚡ FPV filona güç katacak yeni canavar: {name}!",
            f"🛸 Pilotların radarındaki favori donanım: {name} Pozitron Market'te!",
            f"🎯 Uçuş kalitesini bir üst seviyeye taşı: {brand} imzasını taşıyan {name}!",
            f"🔥 Maksimum verim, pürüzsüz tepki ve dayanıklılık: {name}!",
            f"🚀 Freestyle ve yarış pilotları için tasarlandı: {name} stoklarda!"
        ]
        hook = random.choice(hooks)

        specs_lines = []
        if specs:
            specs_items = list(specs.items())[:4]
            for k, v in specs_items:
                specs_lines.append(f"  • {k}: {v}")
        specs_block = "\n".join(specs_lines) if specs_lines else f"  • Marka: {brand}\n  • Orijinal Üretici Garantisi\n  • Profesyonel FPV Sınıfı"

        discount_text = f" (🔥 %{discount_pct} Özel İndirim)" if discount_pct > 0 else ""
        price_text = f"💳 Fiyat: {price_try:,.2f} ₺ / ${price_usd:.2f}{discount_text}"

        caption = f"""{hook}

{prod.get('description_tr', prod.get('description_en', ''))[:180]}...

⚙️ Öne Çıkan Özellikler:
{specs_block}

{price_text}
📦 Stok Durumu: Hızlı Kargo & Güvenli 3D Secure Ödeme
🔗 Sipariş ve detaylar için profildeki linke tıkla! 👆
Ürün linki: pozitronmarket.com/products/{slug}.html"""

        hashtags = f"#fpv #fpvdrone #fpvturkey #{brand.lower().replace(' ', '')} #dronetopla #pozitronmarket #fpvracing #fpvfreestyle #dronehardware #teknofest"

        # Try Gemini AI enhancement if key is provided
        if self.gemini_api_key:
            ai_caption = self._call_gemini_for_product(prod, caption)
            if ai_caption:
                caption = ai_caption

        return {
            'content_type': 'product_spotlight',
            'product_id': prod['id'],
            'title': f"{brand} — {name}",
            'caption': caption.strip(),
            'hashtags': hashtags,
            'product_data': prod,
            'tool_info': None
        }

    def _generate_tool_showcase(self) -> dict:
        is_wizard = random.choice([True, False])
        if is_wizard:
            title = "🛠️ Pozitron FPV Drone Toplama & Uyumluluk Sihirbazı"
            caption = """🛸 "Hangi motora hangi ESC uyar? 4S mi 6S mi? Stack delikleri gövdeye oturur mu?" diye düşünmeye son!

Pozitron Market'in tamamen ÜCRETSİZ geliştirdiği FPV Drone Toplama Sihirbazı ile:
✅ Bütçeni ve uçuş tarzını seç (Freestyle / Racing)
✅ Motor KV, ESC amperajı ve LiPo voltajını anlık eşleştir
✅ 0 hata ile uyumlu donanım paketini tek tıkla oluştur!

Takım arkadaşlarınla listenin çıktısını alabilir veya doğrudan sipariş verebilirsin.

👉 Hemen profildeki linkten Sihirbazı dene: pozitronmarket.com/drone-toplama-sihirbazi.html"""
            hashtags = "#dronetopla #fpvuyumluluk #dronesihirbazi #fpvturkey #pozitronmarket #teknofest #teknofestiha #fpvfreestyle #dronebuild"
            tool_info = {
                'tool_name': 'drone_wizard',
                'badge': 'ÜCRETSİZ ONLİNE ARAÇ',
                'headline': 'FPV DRONE TOPLAMA SİHİRBAZI',
                'subhead': 'Motor-ESC-Pil Uyumluluğunu 0 Hata ile Test Et',
                'url': 'https://pozitronmarket.com/drone-toplama-sihirbazi.html'
            }
        else:
            title = "🦾 Pozitron 3D Baskı TPU Studio"
            caption = """💥 Drone'u sert indirdin veya motor kolu mu çarptı? GoPro mount'un mu kırıldı?

Pozitron 3D Baskı Studio devrede!
🔹 STL veya STEP 3D dosyanı doğrudan siteye yükle
🔹 Esnek, kırılmaz TPU 95A veya rijit PETG/PLA seç
🔹 Gramaj ve online fiyatını saniyeler içinde anında hesapla!
🔹 Canlı renk seçenekleri (Siyah, Pozitron Mavisi, Kırmızı, Sarı) ile aynı gün üretime geçsin.

Kırım yaşamadan önce motorlarını ve kameranı sağlama al! 🛡️

👉 Hemen online baskı al: pozitronmarket.com/3d-baski-studio.html"""
            hashtags = "#3dbaski #tpu95a #dronemount #gopromount #fpvturkey #pozitronmarket #3dprinting #droneparts #teknofest"
            tool_info = {
                'tool_name': '3d_print_studio',
                'badge': 'ONLİNE FİYAT & BASKI',
                'headline': '3D BASKI TPU STUDIO',
                'subhead': 'Kırılmaz TPU 95A GoPro & Motor Koruyucu Parçalar',
                'url': 'https://pozitronmarket.com/3d-baski-studio.html'
            }

        return {
            'content_type': 'tool_showcase',
            'product_id': None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'product_data': None,
            'tool_info': tool_info
        }

    def _generate_deal_drop(self) -> dict:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coupons WHERE is_active = 1 ORDER BY discount_value DESC")
        coupons = cursor.fetchall()
        conn.close()

        coupon_code = "POZITRON10"
        discount_desc = "Tüm siparişlerde %10 net indirim!"
        if coupons:
            c = random.choice(coupons)
            coupon_code = c['code']
            discount_desc = c['description_tr'] or c['description_en']

        title = f"🔥 HAFTANIN FIRSATI: {coupon_code} Kupon Kodu Aktif!"
        caption = f"""⚡ FPV tutkunlarına ve Teknofest takımlarına özel indirim alarmı!

Pozitron Market'te yapacağınız alışverişlerde sepet aşamasında kupon kodunu girerek avantajlı fiyatlardan yararlanın:
🏷️ Kupon Kodu: {coupon_code}
🎁 Kampanya: {discount_desc}

🛸 Motorlar, ESC sürücüler, dijital HD sistemler ve yedek parçalarda geçerli!
Kupon stoklarla sınırlıdır.

👉 Alışverişe başlamak için profildeki linke tıkla: pozitronmarket.com"""
        hashtags = f"#fpvfirsat #indirimkuponu #pozitronmarket #fpvturkey #dronetopla #teknofest #fpvparts #{coupon_code.lower()}"

        return {
            'content_type': 'deal_drop',
            'product_id': None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'product_data': None,
            'tool_info': {
                'badge': 'ÖZEL FIRSAT & KUPON',
                'headline': f'KOD: {coupon_code}',
                'subhead': discount_desc,
                'coupon_code': coupon_code
            }
        }

    def _generate_pilot_tip(self) -> dict:
        tips = [
            {
                'title': '⚡ 4S mi Yoksa 6S Batarya mı? Hangisini Seçmelisin?',
                'summary': '6S LiPo bataryalar daha yüksek voltaj (22.2V) ve daha düşük akım (amper) çekerek voltaj düşmesini (voltage sag) engeller ve daha pürüzsüz gaz tepkisi verir. Ancak motor KV değerinizin 1750-1950KV aralığında olması gerekir!',
                'headline': '4S vs 6S BATARYA REHBERİ',
                'subhead': 'Doğru Voltaj ile Motor Yanmalarını Önle',
                'tags': '#fpvipucu #6sbattery #fpvpilot #pozitronmarket #fpvturkey'
            },
            {
                'title': '🛠️ FPV Motor KV Seçiminde En Sık Yapılan 3 Hata',
                'summary': '1. 6S pille 2500KV motor kullanmak (motorları aşırı ısıtır ve yakar)\n2. Pervane adımı ile motor torkunu eşleştirmemek\n3. ESC amper sınırını hesaba katmadan agresif pervane seçmek.',
                'headline': 'MOTOR KV SEÇİM REHBERİ',
                'subhead': 'Freestyle & Racing İçin En İdeal KV Değerleri',
                'tags': '#motorkv #fpvbuild #teknofest #dronetopla #pozitronmarket'
            },
            {
                'title': '🛡️ TPU 95A Neden FPV Drone İçin En İyi Malzemedir?',
                'summary': 'PLA ve PETG sert olduğu için yüksek hızlı kaza anında anında çatlar. TPU 95A ise esnek yapısıyla darbe enerjisini emer ve GoPro ile anten konektörlerinizi kırılmaktan kurtarır.',
                'headline': 'TPU 95A PARÇA KORUMASI',
                'subhead': 'Kırılmayan Drone Montaj Parçaları',
                'tags': '#3dprinting #tpu95a #fpvkoruma #pozitronmarket #drone'
            }
        ]
        tip = random.choice(tips)

        caption = f"""{tip['title']}

{tip['summary']}

💡 Pozitron Sihirbazı'nı kullanarak motor-ESC-batarya uyumluluğunuzu tek tıkla test edebilirsiniz.
Merak ettiğiniz teknik soruları yorumlarda pilotlarımızla paylaşın! 👇

👉 Donanım ve uyumluluk testi: pozitronmarket.com"""

        return {
            'content_type': 'pilot_tip',
            'product_id': None,
            'title': tip['title'],
            'caption': caption.strip(),
            'hashtags': f"{tip['tags']} #fpvfreestyle #fpvracing #fpvdrone",
            'product_data': None,
            'tool_info': {
                'badge': 'FPV PİLOT AKADEMİSİ',
                'headline': tip['headline'],
                'subhead': tip['subhead']
            }
        }

    def _generate_review_highlight(self) -> dict:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, p.name_tr, p.name_en, p.brand, p.image_url, p.slug
            FROM reviews r
            LEFT JOIN products p ON r.product_id = p.id
            WHERE r.rating >= 4
            ORDER BY RANDOM() LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()

        if not row:
            r = {
                'user_name': 'Kaan T. (FPV Pilotu)',
                'comment': 'Pozitron Market sayesinde aradığım tüm FPV parçalarını tek adresten temin edebildim. Hızlı kargo ve teknik destek harika!',
                'rating': 5,
                'name_tr': 'Pozitron Market Drone Ekosistemi',
                'name_en': 'Pozitron Market Drone Ecosystem',
                'brand': 'Pozitron',
                'slug': '',
                'product_id': None,
                'image_url': None
            }
        else:
            r = dict(row)

        user_name = r.get('user_name') or 'Değerli Pilotumuz'
        product_name = r.get('name_tr') or r.get('name_en') or 'Pozitron FPV Donanım Mağazası'
        comment = r.get('comment', 'Hızlı kargo ve orijinal parçalar!')
        slug = r.get('slug') or ''
        link = f"pozitronmarket.com/products/{slug}.html" if slug else "pozitronmarket.com"

        caption = f"""⭐⭐⭐⭐⭐ Pilot Yorumu: "{comment}"
— {user_name} (Doğrulanmış Pozitron Müşterisi)

🛸 Deneyim / Donanım: {product_name}
Pozitron Market güvencesiyle aynı gün kargo ve teknik destek her siparişinizde yanınızda!

Sen de en son uçuş deneyimini bizimle paylaş! 👇
Detaylar ve sipariş için profildeki linke tıkla: {link}"""

        hashtags = "#musteriyorumu #fpvturkey #pozitronmarket #fpvpilot #dronetopla #fpvdrone #teknofest"

        return {
            'content_type': 'review_highlight',
            'product_id': r.get('product_id'),
            'title': f"Pilot Değerlendirmesi — {product_name}",
            'caption': caption.strip(),
            'hashtags': hashtags,
            'product_data': r if r.get('product_id') else None,
            'tool_info': {
                'badge': '⭐⭐⭐⭐⭐ DOĞRULANMIŞ PİLOT YORUMU',
                'headline': f'"{comment[:40]}..."',
                'subhead': f'— {user_name}'
            }
        }

    def _call_gemini_for_product(self, prod: dict, default_fallback: str) -> str:
        """Calls Gemini 2.5 Flash REST API to craft an Instagram post."""
        if not self.gemini_api_key:
            return default_fallback

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
        prompt = f"""Sen Pozitron Market (pozitronmarket.com) FPV ve Drone e-ticaret sitesinin profesyonel Instagram PR ve Sosyal Medya Yöneticisisin.
Aşağıdaki ürün için Instagram'da yüksek etkileşim alacak, Türkçe, enerjik, samimi ve teknik olarak yetkin bir Instagram gönderisi metni (caption) yaz.

Ürün Bilgileri:
- Adı: {prod.get('name_tr') or prod.get('name_en')}
- Marka: {prod.get('brand')}
- Fiyat: {prod.get('price_try')} TL / ${prod.get('price_usd')} USD
- İndirim: %{prod.get('discount_pct', 0)}
- Özellikler: {prod.get('specs_json')}
- Açıklama: {prod.get('description_tr')}

Format Kuralları:
1. İlk satır dikkat çeken vurucu bir kanca (hook) ve FPV emojileri olsun.
2. 1-2 cümle ürünün pilotlara kazandırdığı avantajı açıklasın.
3. Maddeler halinde 3-4 teknik özellik özetlensin.
4. Fiyat ve stok bilgisi belirtilsin.
5. "Profildeki linke tıkla!" eylem çağrısı (CTA) eklensin.
6. Markdown başlıkları (#, ##) KULLANMA. Sadece temiz Instagram emojili metin olsun."""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 600
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                text = res_data['candidates'][0]['content']['parts'][0]['text']
                if text and len(text.strip()) > 50:
                    return text.strip()
        except Exception as e:
            # Fall back to default on error
            pass
        return default_fallback
