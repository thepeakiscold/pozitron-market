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

    def _load_products_from_json(self):
        json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'products.json')
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _get_candidate_product(self, product_id: str = None):
        recent_ids = get_recent_posted_product_ids(20)
        rows = []
        try:
            conn = get_db()
            cursor = conn.cursor()
            
            if product_id:
                cursor.execute("SELECT * FROM products WHERE id = ? OR slug = ?", (product_id, product_id))
                row = cursor.fetchone()
                conn.close()
                if row:
                    return dict(row)
            else:
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
        except Exception:
            rows = []

        if rows:
            selected = random.choice(rows)
            return dict(selected)

        # Fallback to data/products.json (e.g. for GitHub Actions runner)
        json_prods = self._load_products_from_json()
        if json_prods:
            if product_id:
                for p in json_prods:
                    if p.get('id') == product_id or p.get('slug') == product_id:
                        return p
            avail = [p for p in json_prods if p.get('id') not in recent_ids]
            return random.choice(avail if avail else json_prods)

        return None

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

        # Default visual summary (post text summary to display on graphic)
        top_specs = [f"{k}: {v}" for k, v in list(specs.items())[:2]] if specs else [f"Orijinal {brand} Mühendisliği", "Maksimum Verim & Hız"]
        default_summary = {
            'badge': f"-%{discount_pct} İNDİRİM" if discount_pct > 0 else "⚡ ÖNE ÇIKAN DONANIM",
            'headline': name[:32],
            'subhead': f"{brand} • Pozitron Market Güvencesi",
            'key_points': [
                f"⚡ {top_specs[0] if len(top_specs) > 0 else brand}",
                f"🎯 {top_specs[1] if len(top_specs) > 1 else 'Yüksek Performans & Hızlı Tepki'}",
                f"📦 {price_try:,.2f} ₺ • Hızlı Kargo & Stokta"
            ],
            'cta': "👉 PROFİLDEKİ LİNKTEN HEMEN İNCELE"
        }

        visual_summary = default_summary
        post_title = f"{brand} — {name}"

        # Try Gemini AI enhancement if key is provided
        if self.gemini_api_key:
            ai_data = self._call_gemini_post_and_summary('product_spotlight', {
                'name': name, 'brand': brand, 'price_try': price_try, 'price_usd': price_usd,
                'discount_pct': discount_pct, 'specs': specs, 'description': prod.get('description_tr')
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                post_title = ai_data.get('title', post_title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']

        return {
            'content_type': 'product_spotlight',
            'product_id': prod['id'],
            'title': post_title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
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
            visual_summary = {
                'badge': 'ÜCRETSİZ ONLİNE ARAÇ',
                'headline': 'DRONE TOPLAMA SİHİRBAZI',
                'subhead': 'Motor-ESC-Pil Uyumluluğunu 0 Hata İle Test Et',
                'key_points': [
                    "⚡ Motor KV ve 4S / 6S Voltajını Anında Eşleştir",
                    "🎯 ESC Amper ve Stack Deliklerini Otomatik Doğrula",
                    "🚀 0 Risk İle Uyumlu Parça Listesini Anında Oluştur"
                ],
                'cta': '👉 PROFİLDEKİ LİNKTEN HEMEN DENE'
            }
            tool_info = {
                'tool_name': 'drone_wizard',
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
            visual_summary = {
                'badge': 'ONLİNE FİYAT & BASKI',
                'headline': '3D BASKI TPU STUDIO',
                'subhead': 'Kırılmaz TPU 95A GoPro & Motor Koruyucuları',
                'key_points': [
                    "🛡️ Darbe Emici Esnek TPU 95A Malzeme Garantisi",
                    "⏱️ STL / STEP Dosyanı Yükle, Anında Fiyat Al",
                    "🚀 Kişiye Özel Canlı Renkler & Aynı Gün Üretim"
                ],
                'cta': '👉 3D BASKINI HEMEN SİPARİŞ ET'
            }
            tool_info = {
                'tool_name': '3d_print_studio',
                'url': 'https://pozitronmarket.com/3d-baski-studio.html'
            }

        # Try Gemini AI enhancement if key is provided
        if self.gemini_api_key:
            ai_data = self._call_gemini_post_and_summary('tool_showcase', {
                'tool_title': title, 'caption_draft': caption, 'visual_summary': visual_summary
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']

        return {
            'content_type': 'tool_showcase',
            'product_id': None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
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

        visual_summary = {
            'badge': 'ÖZEL FIRSAT & İNDİRİM',
            'headline': f'KUPON KODU: {coupon_code}',
            'subhead': discount_desc,
            'key_points': [
                f"🏷️ Kupon Kodu: {coupon_code}",
                f"🎁 {discount_desc}",
                "⚡ Motor, ESC, FC ve Tüm Yedek Parçalarda Geçerli"
            ],
            'cta': '👉 İNDİRİMDEN YARARLANMAK İÇİN TIKLA'
        }

        # Try Gemini AI enhancement if key is provided
        if self.gemini_api_key:
            ai_data = self._call_gemini_post_and_summary('deal_drop', {
                'coupon_code': coupon_code, 'discount_desc': discount_desc
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']

        return {
            'content_type': 'deal_drop',
            'product_id': None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': None,
            'tool_info': {'coupon_code': coupon_code}
        }

    def _generate_pilot_tip(self) -> dict:
        tips = [
            {
                'title': '⚡ 4S mi Yoksa 6S Batarya mı? Hangisini Seçmelisin?',
                'summary': '6S LiPo bataryalar daha yüksek voltaj (22.2V) ve daha düşük akım (amper) çekerek voltaj düşmesini (voltage sag) engeller ve daha pürüzsüz gaz tepkisi verir. Ancak motor KV değerinizin 1750-1950KV aralığında olması gerekir!',
                'headline': '4S vs 6S BATARYA SEÇİMİ',
                'subhead': 'Doğru Voltaj ile Motor Yanmalarını Önle',
                'points': [
                    "🔋 6S: Daha Az Voltaj Düşüşü & Pürüzsüz Gaz Tepkisi",
                    "⚡ 6S İçin Tavsiye Edilen Motor: 1750 - 1950 KV",
                    "⚠️ 6S Pille Yüksek KV Kullanmak Motoru Aşırı Isıtır"
                ],
                'tags': '#fpvipucu #6sbattery #fpvpilot #pozitronmarket #fpvturkey'
            },
            {
                'title': '🛠️ FPV Motor KV Seçiminde En Sık Yapılan 3 Hata',
                'summary': '1. 6S pille 2500KV motor kullanmak (motorları aşırı ısıtır ve yakar)\n2. Pervane adımı ile motor torkunu eşleştirmemek\n3. ESC amper sınırını hesaba katmadan agresif pervane seçmek.',
                'headline': 'MOTOR KV SEÇİM REHBERİ',
                'subhead': 'Freestyle & Racing İçin En İdeal Değerler',
                'points': [
                    "🎯 5 İnç 6S Freestyle: 1950KV İdeal Denge",
                    "🔥 Agresif Pervanede ESC Amper Sınırına Dikkat Edin",
                    "🛡️ Pozitron Sihirbazı ile Donanımını 0 Hata ile Doğrula"
                ],
                'tags': '#motorkv #fpvbuild #teknofest #dronetopla #pozitronmarket'
            },
            {
                'title': '🛡️ TPU 95A Neden FPV Drone İçin En İyi Malzemedir?',
                'summary': 'PLA ve PETG sert olduğu için yüksek hızlı kaza anında anında çatlar. TPU 95A ise esnek yapısıyla darbe enerjisini emer ve GoPro ile anten konektörlerinizi kırılmaktan kurtarır.',
                'headline': 'TPU 95A DARBE KORUMASI',
                'subhead': 'Kırılmayan Esnek Drone Koruma Parçaları',
                'points': [
                    "💥 Darbe Enerjisini Emer, Kaza Anında Çatlamaz",
                    "📹 GoPro, Anten ve Kol Korumaları İçin Şart",
                    "🖨️ Pozitron 3D Studio'da STL Yükleyip Hemen Bastırın"
                ],
                'tags': '#3dprinting #tpu95a #fpvkoruma #pozitronmarket #drone'
            }
        ]
        tip = random.choice(tips)

        title = tip['title']
        caption = f"""{tip['title']}

{tip['summary']}

💡 Pozitron Sihirbazı'nı kullanarak motor-ESC-batarya uyumluluğunuzu tek tıkla test edebilirsiniz.
Merak ettiğiniz teknik soruları yorumlarda pilotlarımızla paylaşın! 👇

👉 Donanım ve uyumluluk testi: pozitronmarket.com"""
        hashtags = f"{tip['tags']} #fpvfreestyle #fpvracing #fpvdrone"

        visual_summary = {
            'badge': 'FPV PİLOT REHBERİ',
            'headline': tip['headline'],
            'subhead': tip['subhead'],
            'key_points': tip['points'],
            'cta': '👉 DAHA FAZLA TEKNİK REHBER İÇİN TIKLA'
        }

        # Try Gemini AI enhancement if key is provided
        if self.gemini_api_key:
            ai_data = self._call_gemini_post_and_summary('pilot_tip', {
                'tip_title': tip['title'], 'tip_summary': tip['summary']
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']

        return {
            'content_type': 'pilot_tip',
            'product_id': None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': None,
            'tool_info': None
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

        title = f"Pilot Değerlendirmesi — {product_name}"
        caption = f"""⭐⭐⭐⭐⭐ Pilot Yorumu: "{comment}"
— {user_name} (Doğrulanmış Pozitron Müşterisi)

🛸 Deneyim / Donanım: {product_name}
Pozitron Market güvencesiyle aynı gün kargo ve teknik destek her siparişinizde yanınızda!

Sen de en son uçuş deneyimini bizimle paylaş! 👇
Detaylar ve sipariş için profildeki linke tıkla: {link}"""

        hashtags = "#musteriyorumu #fpvturkey #pozitronmarket #fpvpilot #dronetopla #fpvdrone #teknofest"

        visual_summary = {
            'badge': '⭐⭐⭐⭐⭐ DOĞRULANMIŞ PİLOT YORUMU',
            'headline': f'"{comment[:32]}..."',
            'subhead': f'— {user_name} • Pozitron Pilotu',
            'key_points': [
                f"💬 \"{comment[:45]}...\"",
                f"🛸 Donanım: {product_name[:35]}",
                "⚡ %100 Orijinal Ürün & Aynı Gün Kargo"
            ],
            'cta': '👉 SEN DE DENEYİMİNİ PAYLAŞ'
        }

        # Try Gemini AI enhancement if key is provided
        if self.gemini_api_key:
            ai_data = self._call_gemini_post_and_summary('review_highlight', {
                'product': product_name, 'user_name': user_name, 'comment': comment
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']

        return {
            'content_type': 'review_highlight',
            'product_id': r.get('product_id'),
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': r if r.get('product_id') else None,
            'tool_info': None
        }

    def _call_gemini_post_and_summary(self, content_type: str, context: dict) -> dict:
        """
        Calls Gemini 2.5 Flash API to generate:
        1. Engaging Turkish Instagram post caption & hashtags
        2. Structured Visual Summary (Özet Kartı) with 3 key takeaway bullet points
           specifically crafted to be rendered onto the 1080x1080 graphic image!
        """
        if not self.gemini_api_key:
            return None

        prompt = f"""Sen Pozitron Market (pozitronmarket.com) FPV drone platformunun baş sosyal medya ve PR uzmanısın.
İçerik Türü: {content_type}
İçerik Bilgileri:
{json.dumps(context, ensure_ascii=False, indent=2)}

GÖREV:
1. Instagram için etkileyici, Türkçe, enerjik ve samimi bir gönderi metni (caption) ve hashtag'ler yaz.
2. Bu gönderide anlatılan konunun/ürünün EN ÖNEMLİ noktalarını özetleyen bir "visual_summary" (görsel özet) oluştur.
   Bu görsel özet, 1080x1080 boyutundaki Instagram grafik görselinin üzerine büyük ve net şekilde basılacaktır.

SADECE geçerli bir JSON objesi döndür:
{{
  "title": "Gönderi başlığı (maks 40 karakter)",
  "caption": "Instagram gönderi metni (dikkat çekici kanca, teknik avantajlar, emoji'ler, profildeki linke yönlendirme)",
  "hashtags": "#fpvturkey #pozitronmarket #dronetopla ...",
  "visual_summary": {{
    "badge": "Görsel üstü rozet (örn: ⚡ ÖNE ÇIKAN DONANIM, 🔥 FIRSAT ALARMI, 🛠️ PİLOT REHBERİ)",
    "headline": "Görsel üzerindeki ana başlık (maks 32 karakter)",
    "subhead": "Görsel üzerindeki kısa açıklama (maks 45 karakter)",
    "key_points": [
      "⚡ Gönderi metninin 1. özet maddesi (maks 42 karakter)",
      "🎯 Gönderi metninin 2. özet maddesi (maks 42 karakter)",
      "📦 Gönderi metninin 3. özet maddesi (maks 42 karakter)"
    ],
    "cta": "👉 PROFİLDEKİ LİNKTEN HEMEN KEŞFET"
  }}
}}"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800,
                "responseMimeType": "application/json"
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res_data = json.loads(response.read().decode('utf-8'))
                raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
                data = json.loads(raw_text)
                if isinstance(data, dict) and data.get('caption') and data.get('visual_summary'):
                    return data
        except Exception:
            pass
        return None
