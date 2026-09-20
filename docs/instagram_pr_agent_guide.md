# 🤖 Pozitron Market — Otonom Instagram PR Ajanı Kullanım & Entegrasyon Kılavuzu

Bu kılavuz, **Pozitron Market** ([pozitronmarket.com](https://pozitronmarket.com)) e-ticaret platformunun Instagram hesabını (`@pozitronmarket`) otonom olarak yöneten, 1080x1080 piksel boyutunda yüksek kaliteli afişler tasarlayan ve içerik yayınlayan PR Ajanı'nın kurulum ve kullanım detaylarını içerir.

---

## 🌟 Temel Özellikler

1. **5 Farklı İçerik Stratejisi (Content Pillars):**
   - 🛸 **Ürün Vitrini (Product Spotlight):** 500 FPV donanımı arasından öne çıkan motor, ESC, FC, DJI O3, kamera ve LiPo bataryaları teknik özellikleri, TRY/USD fiyatları ve stok bilgisiyle tanıtır.
   - 🛠️ **Araç Tanıtımı (Tool Showcase):** Sitedeki **Drone Uyumluluk Sihirbazı** (`drone-toplama-sihirbazi`) ve **3D Baskı TPU Studio**'sunu (`3d-baski-studio`) tanıtır.
   - 🔥 **Fırsat & Kupon Alarmı (Deal Drop):** Aktif kupon kodlarını (`POZITRON10`, `DRONE20`, `FPVRACE`) ve indirimleri duyurur.
   - 💡 **FPV Pilot Akademisi (Pilot Advice):** 4S vs 6S pil seçimi, motor KV hesabı, TPU malzeme avantajları gibi rehber paylaşımlar.
   - ⭐ **Doğrulanmış Müşteri Yorumları (Social Proof):** Gerçek kullanıcı deneyimlerini şık kartlarla öne çıkarır.

2. **1080x1080 Profesyonel Görsel Motoru (PIL Graphics Engine):**
   - Pozitron kurumsal kimliğine uygun siber/karanlık FPV gradyanı (`#0b0f19` - `#1e293b`), elektrik mavisi vurgular ve filigran.
   - Orijinal ürün görseli, kategori rozeti, marka etiketi, teknik haplar ve ₺ TRY / $ USD fiyat rozeti.

3. **Çift Motorlu Metin Üretimi (Heuristic + Gemini AI):**
   - Dahili kural ve şablon motoru sayesinde harici API anahtarına ihtiyaç duymadan kusursuz Türkçe FPV metinleri üretir.
   - Google Gemini API (`gemini-2.5-flash`) anahtarı tanımlandığında LLM destekli dinamik metinler oluşturur.

4. **Resmi Meta Graph API (v21.0) & Simülasyon (Dry-Run):**
   - API anahtarları girilmeden önce veya test esnasında **Dry-Run Simülasyon Modu** çalışır; afiş diske yazılır ve admin panelinde canlı telefon mockup'ında gösterilir.
   - Canlı kimlik bilgileri girildiğinde resmi Meta Graph API (`POST /{ig_user_id}/media` -> `POST /{ig_user_id}/media_publish`) üzerinden yayına alır.

---

## 🚀 Kullanım Yöntemleri

### Yöntem 1: Yönetim Paneli Üzerinden (Tavsiye Edilen)
1. Yerel sunucuyu başlatın:
   ```bash
   python3 server.py
   ```
2. Tarayıcınızda `http://localhost:8000/admin` adresine gidin.
3. Üst menüden **"🤖 Instagram PR Robotu"** sekmesine tıklayın.
4. **İçerik Stüdyosu**'ndan içerik türünü ve isterseniz belirli bir ürünü seçip **"✨ Yeni Gönderi & 1080x1080 Görsel Üret"** butonuna basın.
5. Sağ taraftaki **Canlı Instagram Telefon Mockup'ı** üzerinde tasarlanan afişi, başlığı ve hashtag'leri anlık olarak inceleyin.
6. **"🚀 Instagram'da Hemen Yayınla"** butonuna basarak yayına alın veya simüle edin.
7. Sayfanın altındaki **⚙️ Ajan Ayarları** bölümünden otonom yayınlama sıklığını (örn: 6 saatte bir) belirleyip **"Otonom Yayınlama Robotunu Aktif Et"** seçeneğini açabilirsiniz.

---

### Yöntem 2: Terminal / CLI Üzerinden (`instagram_pr_agent.py`)

Ajanı terminalden veya arka plan servisi olarak çalıştırmak için komut satırı aracı mevcuttur:

```bash
# Ajanın durumunu ve ayarlarını görüntüleme
python3 instagram_pr_agent.py --status

# Yeni bir gönderi ve 1080x1080 görsel taslağı üretme
python3 instagram_pr_agent.py --generate

# Belirli bir konseptte gönderi üretme
python3 instagram_pr_agent.py --generate --type product_spotlight
python3 instagram_pr_agent.py --generate --type tool_showcase
python3 instagram_pr_agent.py --generate --type deal_drop
python3 instagram_pr_agent.py --generate --type pilot_tip

# Üretilen gönderiyi yayınlama (veya simüle etme)
python3 instagram_pr_agent.py --publish --id <POST_ID>

# Son gönderileri listeleme
python3 instagram_pr_agent.py --list --limit 10

# Otonom modu açma / kapama
python3 instagram_pr_agent.py --toggle on
python3 instagram_pr_agent.py --toggle off

# Sürekli arka plan planlayıcısı (Daemon) olarak çalıştırma
python3 instagram_pr_agent.py --daemon
```

---

## 🔑 Meta Graph API Canlı Yayın Kurulumu

Canlı Instagram yayını yapmak için:

1. Bir **Facebook Sayfası** oluşturun ve Instagram Business hesabınızı bu sayfaya bağlayın.
2. [developers.facebook.com](https://developers.facebook.com) üzerinde bir Meta Developer Uygulaması açın.
3. Uygulamanıza **Instagram Graph API** ürününü ekleyin.
4. Gerekli izinleri verin:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
5. **Graph API Explorer** aracından veya Access Token Tool'dan **Long-Lived Page/User Access Token** alın.
6. `GET /v21.0/me/accounts` ve `GET /v21.0/{page_id}?fields=instagram_business_account` sorgusuyla **Instagram Business Account ID**'nizi öğrenin.
7. Bu iki bilgiyi Pozitron Admin Panelindeki **Ajan Ayarları** formuna girin ve **"Simülasyon / Test Modu"** kutucuğunun işaretini kaldırıp kaydedin.

---

## 🛠️ REST API Referansı (`server.py`)

| Uç Nokta | Metot | Açıklama |
| :--- | :--- | :--- |
| `/api/instagram/status` | `GET` | Ajan çalışma durumu, sıradaki post zamanı ve metrikler. |
| `/api/instagram/config` | `GET` | Maskelenmiş konfigürasyon bilgileri. |
| `/api/instagram/config` | `POST` | Konfigürasyon güncelleme (Token, ID, Gemini Key, Sıklık). |
| `/api/instagram/generate` | `POST` | Yeni gönderi taslağı ve 1080x1080 görsel üretimi. |
| `/api/instagram/publish` | `POST` | Taslağı Instagram'da yayınlama (canlı veya dry-run). |
| `/api/instagram/toggle` | `POST` | Otonom planlayıcıyı açma / kapatma (`{"enabled": true}`). |
| `/api/instagram/posts` | `GET` | Gönderi geçmişi ve kuyruk listesi (`?limit=30`). |
| `/api/instagram/posts/<id>` | `DELETE` | Belirtilen gönderiyi ve görselini silme. |

---

© 2026 Pozitron Market. Tüm hakları saklıdır.
