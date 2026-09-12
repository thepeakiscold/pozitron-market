import sqlite3
import os
import json
import re
import uuid
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pozitron.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

class TechnicalSeoAgent:
    """
    SUBAGENT 4: TEKNİK DOKÜMANTASYON VE SEO AJANI (CONTENT & SEO AGENT)
    - Pozitron Market için teknik derinliği yüksek rehberler, bağlantı şemaları ve SEO makaleleri üretir.
    - UART konfigürasyonları, ESC protokolleri, motor-pervane tabloları ve LiPo güvenliği konularına odaklanır.
    - Hiyerarşik H1, H2, H3 başlıkları ve arama niyeti (Search Intent) odaklı kurgu uygular.
    - Pozitron Market ürünlerine iç linkleme (internal linking) yapar.
    - İçerikleri Lead Agent havuzuna teslim eder.
    """
    def __init__(self, gemini_api_key: str = ""):
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")

    def _get_matching_products(self, keyword: str, limit: int = 3) -> List[Dict]:
        """Finds related products in Pozitron catalog for internal linking."""
        conn = get_db()
        cursor = conn.cursor()
        search_term = f"%{keyword}%"
        cursor.execute("""
            SELECT id, slug, sku, name_tr, price_try, brand FROM products
            WHERE name_tr LIKE ? OR specs_json LIKE ? OR tags_json LIKE ?
            ORDER BY stock DESC LIMIT ?
        """, (search_term, search_term, search_term, limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def generate_article(self, component_focus: str = None, target_keywords: List[str] = None) -> Dict:
        """
        Generates a comprehensive, engineering-grade technical guide with internal links.
        """
        component_focus = component_focus or "Uçuş Kontrol Kartı (FC) UART & Betaflight 4.5 Konfigürasyonu"
        target_keywords = target_keywords or [
            "Betaflight UART ayarı", "CRSF ELRS port bağlantısı", "FPV uçuş kartı lehimleme", "Pozitron Market FPV"
        ]
        keywords_str = ", ".join(target_keywords)

        # Retrieve matching products for internal linking
        fc_products = self._get_matching_products("F722", 2) or self._get_matching_products("Uçuş", 2)
        esc_products = self._get_matching_products("ESC", 2)
        motor_products = self._get_matching_products("Motor", 2)

        internal_links = []
        for p in (fc_products + esc_products + motor_products)[:4]:
            internal_links.append({
                "sku": p["sku"],
                "name": p["name_tr"],
                "url": f"https://pozitronmarket.com/products/{p['slug']}"
            })

        slug = re.sub(r'[^a-z0-9]+', '-', component_focus.lower()).strip('-')
        slug = f"rehber-{slug}-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:4]}"

        title = f"{component_focus}: Kapsamlı Mühendislik ve Donanım Rehberi"

        # Construct technical markdown content
        links_md = "\n".join([f"- [{item['name']}]({item['url']})" for item in internal_links])

        content = f"""# {title}

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `{keywords_str}`  
**Yayın Tarihi:** {datetime.now().strftime('%d.%m.%Y')}

---

## 1. Giriş ve Donanım Mimarisi

Modern FPV yarış ve serbest stil (freestyle) drone sistemlerinde, uçuş kontrol kartı (Flight Controller) ile çevre birimleri (ESC, Alıcı/ELRS, VTX, GPS) arasındaki haberleşme kararlılığı, sıfır kırım ve minimum gecikme süresi için hayati önem taşır.

Özellikle STM32F405 ve STM32F722 mikrodenetleyici mimarilerinde DMA (Direct Memory Access) kanallarının doğru paylaştırılması ve UART (Universal Asynchronous Receiver-Transmitter) portlarının doğru baudrate hızlarında konfigüre edilmesi gerekir.

---

## 2. UART Port Dağılımı ve Donanım Bağlantı Şeması

Uçuş kontrolcünüzde lehimleme yapmadan önce pinout şemasını ve sinyal gerilimlerini (5V / 9V BEC) multimetre ile test ediniz:

| Donanım Birimi | Önerilen Port | Protokol / Sinyal | Gerilim Toleransı |
| :--- | :--- | :--- | :--- |
| **ELRS / Crossfire Alıcı** | UART 1 / 2 | CRSF (Serial Rx) | 5V DC (Temiz Hat) |
| **VTX (Görüntü Verici)** | UART 3 / 6 | IRC Tramp / MSP / SmartAudio | 9V-12V Filtreli BEC |
| **ESC Telemetri** | UART 4 (veya ESC Telemetry Pini) | KISS / BLHeli_32 / Bluejay | 5V Logic |
| **GPS / Pusula (Opsiyonel)** | UART 5 (Tx/Rx) | UBLOX 57600 / 115200 | 5V DC |

### 2.1. Lehimleme ve Donanım Güvenlik Kuralları
- 350°C - 380°C aralığında kurşunlu (63/37) veya kurşunsuz kaliteli lehim teli kullanın.
- Lehim sonrasında multimetre ile `VCC` ve `GND` pad'leri arasında süreklilik (continuity / bip) testi yapın.
- İlk enerji vermeyi mutlaka bir **Smoke Stopper (Kısa Devre Koruyucu)** üzerinden gerçekleştirin.

---

## 3. Betaflight 4.5 Konfigürasyon Adımları

1. **Ports (Portlar) Sekmesi:**
   - Alıcınızın bağlı olduğu UART satırında **Serial Rx** anahtarını aktif edin.
   - VTX telemetrisi için ilgili UART satırında **Peripherals** menüsünden `VTX (MSP + Displayport)` veya `IRC Tramp` protokolünü seçin.
2. **Receiver (Alıcı) Sekmesi:**
   - Alıcı modunu `CRSF` olarak tanımlayın.
   - Telemetry özelliğini açık tutarak voltaj ve RSSI/LQ sinyal gücünü kumandanızdan izleyin.
3. **PID & DShot Ayarları:**
   - ESC protokolü olarak **DSHOT600** veya **DSHOT300** seçiniz.
   - Bi-directional DShot (RPM Filtering) özelliğini aktif ederek jiroskop gürültülerini filtreleyin.

---

## 4. Pozitron Market Uyumlu Donanım ve Yedek Parça Listesi

Bu rehberde bahsi geçen sistemlerle %100 test edilmiş ve Türkiye stoklarından aynı gün kargolanan resmi donanım bileşenleri:

{links_md}

> 💡 **Teknik İpucu:** Tüm donanım uyumluluk sorularınız ve özel lehimleme destek talepleriniz için [Pozitron Drone Toplama Sihirbazı](https://pozitronmarket.com/drone-toplama-sihirbazi.html) aracımızı kullanabilirsiniz.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Alıcı Bağlantısı Gelmiyor (No Receiver Signal):** Alıcının `Rx` ucunun uçuş kartındaki `Tx` ucuna değil, mutlaka `Rx` ucuna (CRSF protokolünde cross bağlantı: Alıcı TX -> FC RX, Alıcı RX -> FC TX) bağlandığından emin olun.
- **Aşırı Motor Isınması:** RPM filtresi kapalıyken D-Term kazancının yüksek olmasından kaynaklanabilir. Master D-Term çarpanını 0.8 seviyesine çekip motor sıcaklıklarını 30 saniyelik havada asılı kalma (hover) testiyle kontrol edin.
"""

        # Save to database
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO seo_articles (slug, title, component_focus, target_keywords, internal_links_json, content_markdown, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                slug, title, component_focus, keywords_str,
                json.dumps(internal_links, ensure_ascii=False),
                content, datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"Error saving SEO article: {ex}")

        return {
            "slug": slug,
            "title": title,
            "component_focus": component_focus,
            "target_keywords": target_keywords,
            "internal_links": internal_links,
            "content_markdown": content,
            "published_at": datetime.now().isoformat()
        }

    def get_articles(self, limit: int = 20) -> List[Dict]:
        """Fetches stored SEO guides."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM seo_articles ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            # Generate initial article if table is empty
            self.generate_article()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM seo_articles ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()

        return [
            {
                "id": r["id"],
                "slug": r["slug"],
                "title": r["title"],
                "component_focus": r["component_focus"],
                "target_keywords": r["target_keywords"],
                "internal_links": json.loads(r["internal_links_json"]) if r["internal_links_json"] else [],
                "content_markdown": r["content_markdown"],
                "created_at": r["created_at"]
            }
            for r in rows
        ]
