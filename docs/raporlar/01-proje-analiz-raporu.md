# Pozitron Market — Kapsamlı Proje Analiz Raporu

**Rapor No:** PZTR-ANLZ-2026-11-01
**Tarih:** 1 Kasım 2026
**Sürüm:** 1.0 (Final)
**Kapsam:** Tüm depo (`/home/eyup/Pozitron`), canlı ortam (`pozitronmarket.com`, `api.pozitronmarket.com`)
**Hazırlayan:** Teknik Denetim Ekibi
**Gizlilik:** Dahili — Gizli

---

## 1. Yönetici Özeti

Pozitron Market, Türkiye'de FPV/drone donanımı alanında **teknik derinliği ortalamanın çok üzerinde** olan bir e-ticaret platformudur. Statik vitrin + Python backend + otonom çoklu-ajan orkestrasyonu şeklindeki üç katmanlı kurgu, küçük bir ekip için iddialı ve yaratıcı bir mimaridir. İyzico hosted checkout entegrasyonu, kupon güvenlik motoru ve test disiplini (36 test dosyası) ciddi mühendislik emeğine işaret eder.

Buna karşılık platform, **gelir üretme kabiliyeti açısından fiilen durma noktasındadır**. Bunun nedeni kod kalitesi değil, üç yapısal sorundur:

1. **Katalog neredeyse tamamen stok dışıdır.** 509 ürünün 508'i (`%99,8`) stok 0'dır; yalnızca 1 üründe 6 adet stok vardır. Bu, sitedeki tüm "Sepete Ekle" akışını, dönüşüm hunisini ve Google Merchant feed'ini işlevsiz kılar.
2. **Ürün görselleri gerçek değildir.** 509 ürün için yalnızca 308 farklı görsel vardır; 209 ürün jenerik `trend_*.jpg` dosyalarını kullanır ve **tek bir görsel 103 farklı ürüne** atanmıştır. Bu, güven kaybı ve Merchant Center reddi için doğrudan sebeptir.
3. **Güvenlik açısından kritik düzeyde açık mevcuttur.** Genel API anahtarı herkese açık `api.js` içinde gömülüdür ve canlı ortamda çalışmaktadır; `/api/auth/google` uç noktası yalnızca e-posta adresi verilerek **yönetici oturumu** üretmektedir. Ayrıntılar `03-siber-guvenlik-raporu.md` dosyasındadır — bu rapor okunmadan sistem canlıda bırakılmamalıdır.

**Genel değerlendirme notu: 5,4 / 10**

| Boyut | Puan | Kısa Gerekçe |
|---|---:|---|
| Mimari tasarım | 7,0 | Katman ayrımı net, hibrit model akıllı; fakat tek dosya monolit |
| Kod kalitesi | 4,5 | 5.408 satır `server.py`, 129 route, tek sınıf; sürdürülebilirlik düşük |
| Veri kalitesi | 2,5 | Stok, görsel ve fiyat/kur tutarsızlıkları ticari olarak bloke edici |
| Test & CI | 6,0 | İyi kapsam, ancak 12 kırık test ve yavaş/otomatik olmayan koşum |
| Operasyon & DevOps | 4,0 | `git pull` tabanlı dağıtım, sırların repoda, tek nokta arıza |
| Performans | 4,0 | Ana sayfada ~2,6 MB JS; 3D kütüphaneleri eager yükleniyor |
| UX | 5,0 | Güçlü temel, fakat stok/ödeme/güven kırılmaları huniyi koparıyor |
| Güvenlik | 1,5 | Kritik: kimlik doğrulama atlatma ve PII ifşası doğrulandı |

### En kritik 10 bulgu (öncelik sırasıyla)

| # | Bulgu | Etki | Aciliyet |
|---|---|---|---|
| 1 | Genel API anahtarı istemci kodunda sabit ve canlıda geçerli | Tüm yönetici API'si: müşteri PII, siparişler, kuponlar, ürün silme | **0–24 saat** |
| 2 | `/api/auth/google` kanıtsız yönetici token'ı veriyor | Mağazanın tam ele geçirilmesi | **0–24 saat** |
| 3 | `/api/orders` kimlik doğrulaması olmadan tüm siparişleri döndürüyor | Müşteri adı/e-posta/telefon/adres ifşası (KVKK ihlali) | **0–24 saat** |
| 4 | 509 ürünün 508'i stokta yok | Satış yapılamıyor; tüm huni çöküyor | **0–7 gün** |
| 5 | 209 üründe jenerik/yanlış görsel, 103 ürün aynı görseli paylaşıyor | Güven kaybı, Merchant reddi, iade riski | **0–7 gün** |
| 6 | Yorumlar `innerHTML` ile basılıyor + `verified_purchase=1` zorlanıyor | Kalıcı XSS ve sahte "doğrulanmış yorum" | **0–7 gün** |
| 7 | Şifreler tek tuzlu SHA-256 ile saklanıyor | Sızıntıda geri döndürme/tablo saldırısı | 7–30 gün |
| 8 | 1.120 ürün HTML dosyası (509 ürün için 603 kopya) | SEO kanibalizasyonu, bakım maliyeti, depo şişmesi | 30 gün |
| 9 | 4,8 GB Instagram medyası git geçmişinde (depo 5,2 GB) | Klonlama süresi, CI maliyeti, felaket kurtarma riski | 30 gün |
| 10 | Kur/fiyat sabitleri 4 ayrı yerde farklı (34,5 / 35,5 / 38,5) | Yanlış fiyatlama, marj kaybı | 7 gün |

---

## 2. Kapsam ve Metodoloji

**İncelenen varlıklar**

- 36 Python kaynak dosyası (~21.000 satır), 5 JavaScript dosyası (~8.300 satır), 26 HTML şablonu, 1 CSS (6.399 satır)
- SQLite veritabanı (`pozitron.db`, 39 MB, 34 tablo, 42 indeks)
- 1.120 üretilmiş ürün sayfası, 592 görsel dosyası (84 MB), 7.160 Instagram medya dosyası (4,8 GB)
- Git geçmişi (42.000+ nesne, 5,2 GB), GitHub Actions iş akışları, systemd/Docker/Render dağıtım tanımları
- Canlı ortam: `https://pozitronmarket.com` (statik), `https://api.pozitronmarket.com` (API)

**Yöntem**

| Yöntem | Uygulama |
|---|---|
| Statik kod analizi | Dosya bazlı manuel inceleme + `grep` tabanlı kalıp taraması |
| Veri analizi | SQLite sorguları, JSON/TSV feed doğrulaması, görsel tekrar analizi |
| Dinamik doğrulama | Yerel servis (`127.0.0.1:8000`) ve canlı API üzerinde salt-okunur istekler |
| Test koşumu | 36 test dosyası ayrı ayrı `pytest` ile çalıştırıldı |
| Ölçüm | Dosya boyutları, satır sayıları, stok/görsel/kur istatistikleri |

> **Etik not:** Canlı ortamda yalnızca kimlik doğrulama ve veri ifşası doğrulaması amacıyla salt-okunur istekler yapılmıştır. Hiçbir veri değiştirilmemiş, kopyalanmamış veya saklanmamıştır. Yerel ortamda yapılan tek yazma testi (XSS amaçlı yorum kaydı) aynı oturumda silinmiştir. Raporda tüm kişisel veriler ve sırlar maskelenmiştir.

---

## 3. Sistem Envanteri ve Ölçülen Metrikler

### 3.1 Kod tabanı

| Dosya | Satır | Boyut | Rol | Değerlendirme |
|---|---:|---:|---|---|
| `server.py` | 5.408 | 267 KB | HTTP sunucu + 129 API route | **Monolit** — ayrıştırılmalı |
| `app.js` | 7.100 | 279 KB | Tüm istemci mantığı | Monolit — modülleşmeli |
| `bots.html` | 7.245 | 358 KB | Ajan komuta merkezi | Sayfa içi 5.000+ satır JS |
| `admin.html` | 4.523 | 227 KB | Yönetim paneli | İstemci tarafı yetki kontrolü |
| `styles.css` | 6.399 | 124 KB | Tasarım sistemi | 12 medya sorgusu, dağınık |
| `instagram_agent/content_generator.py` | 3.151 | — | İçerik üretimi | En büyük ajan modülü |
| `image_generator.py` | 2.848 | — | Görsel üretimi | Pillow tabanlı |
| `subagent_qa.py` | 2.032 | — | QA ajanı | Aşırı büyük |
| `generate_product_pages.py` | 1.921 | 94 KB | HTML üretici | İki ayrı üretici var (teknik borç) |
| `review-dashboard.html` | 337 | **2,1 MB** | Yorum paneli | **Kullanılmayan dev dosya** |

**Toplam:** ~69.600 satır (testler hariç ~57.000).

### 3.2 Veritabanı

- **34 tablo, 42 indeks**, WAL modu, `busy_timeout=30000`, `foreign_keys=ON`
- Kayıt sayıları: **509 ürün**, **121 sipariş**, **101 kullanıcı**, 25 kupon, 8 kupon kullanımı, 1.090 güvenlik logu, 69 şifre sıfırlama kaydı, **0 yorum**
- Kategori dağılımı dengeli (25–56 ürün), toplam 509

### 3.3 Katalog ve medya

| Metrik | Değer | Yorum |
|---|---:|---|
| Ürün sayısı | 509 | İddialı katalog |
| Stokta olan ürün | **1** | **Kritik** |
| Stokta olmayan ürün | **508 (%99,8)** | **Ticari blokaj** |
| Toplam stok adedi | 6 | Tek SKU |
| Benzersiz görsel | 308 / 509 | %39 tekrar |
| Jenerik `trend_*` görsel kullanan ürün | 209 | Gerçek ürün fotoğrafı yok |
| En çok paylaşılan görsel | 103 ürün | Aynı fotoğraf 103 farklı üründe |
| Galeri görseli olan ürün | 508 üründe 1, 1 üründe 2 | Zengin galeri yok |
| Görsel ortalama boyut | 152 KB (maks. 2,95 MB) | Optimizasyon yok |
| Üretilmiş ürün sayfası | **1.120** | 509 ürün için 603 fazla dosya |
| Aynı ürünün sürüm kopyaları | 452 aile, örn. 7 kopya | SEO kanibalizasyonu |

### 3.4 Depo ve dağıtım

| Metrik | Değer |
|---|---:|
| Git deposu | **5,2 GB** (pack 4,14 GB) |
| İzlenen Instagram medyası | 7.160 dosya / **4,8 GB** |
| Çalışma dizini (node_modules ve .git hariç) | 6,6 GB (assets 6,5 GB) |
| Üretilmiş sitemap URL | 786 (509 ürün + 267 rehber + 10 sabit) |
| Google Merchant feed satırı | 509 — **508'i `out_of_stock`** |
| Test dosyası | 36 |
| CI iş akışı | 3 (Instagram, Reddit, sipariş senkronu) — **test/build iş akışı yok** |

---

## 4. Mimari Analiz

### 4.1 Mevcut mimari

```
                    ┌──────────────────────────────────────────┐
                    │  KATMAN 1 — Statik Vitrin (GitHub Pages) │
                    │  index.html + app.js + i18n.js           │
                    │  data/pozitron_data.js (1,54 MB)         │
                    └───────────────┬──────────────────────────┘
                                    │  HTTPS /api/*
                                    ▼
                    ┌──────────────────────────────────────────┐
                    │  KATMAN 2 — Python API (Hetzner/Render)  │
                    │  server.py: ThreadingHTTPServer, 129 rt.  │
                    │  SQLite WAL (34 tablo)                   │
                    │  iyzico hosted checkout + reconciler      │
                    └───────────────┬──────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌─────────────────┐        ┌──────────────────┐
│ KATMAN 3      │         │ Harici Servisler│        │ Üretilmiş Varlık │
│ 10+1 Otonom   │         │ iyzico, SMTP,   │        │ products/*.html  │
│ Ajan          │         │ Gemini, Meta,   │        │ sitemap, feed    │
│ (orchestrator)│         │ Reddit          │        │ 84 MB görsel     │
└───────────────┘         └─────────────────┘        └──────────────────┘
```

### 4.2 Güçlü yönler

1. **Hibrit model doğru kurgulanmış.** Statik vitrin CDN üzerinden sunulurken API ayrı alt alan adında; vitrin çökse bile katalog görüntülenebilir. Bu, küçük ölçek için pragmatik ve maliyet-etkin bir seçimdir.
2. **Ödeme mimarisi olgun.** `iyzico_checkout.py` kart verisini hiç görmez, hosted checkout kullanır, HMAC imza doğrular, tutar/para birimi/sepet kimliği eşleştirir, `fraudStatus=1` olmayan işlemleri karantinaya alır, kaçırılan callback'leri 60 saniyede bir 7 gün boyunca telafi eder. Bu bölüm **profesyonel standarttadır**.
3. **Kupon motoru düşünülmüş.** Gmail nokta/artı normalizasyonu, oturumlu–misafir geçişini engelleyen çapraz kimlik kontrolü, indirimin sepet tutarına kenetlenmesi (clamping), DB seviyesinde `UNIQUE` kısıtı ile yarış koşulu koruması.
4. **WAL + busy_timeout** doğru yapılandırılmış; eşzamanlı okuma/yazma için makul.
5. **Test kültürü var.** 36 dosya, 201 geçen test — çoğu projede bu yoktur.

### 4.3 Yapısal zayıflıklar

| # | Sorun | Kanıt | Etki |
|---|---|---|---|
| A1 | **Tek sınıf monolit** | `PozitronRequestHandler` içinde 129 route, 5.408 satır | Test edilebilirlik, ekip ölçeklenmesi, hata izolasyonu düşük |
| A2 | **Rota eşleştirme `if/elif` zinciri** | `handle_api_get` / `handle_api_post` | Sıra bağımlı hatalar; yeni route eklemek riskli |
| A3 | **İki paralel ürün sayfası üreticisi** | `generate_product_pages.py` (1.921 satır) + `server.py` içinde dinamik üretim | Şablon tutarsızlığı, çift bakım |
| A4 | **İki katmanlı kimlik doğrulama karmaşası** | `get_current_user`, `require_admin`, `get_authenticated_user` (tanımsız!) | Çağrılan ama var olmayan metot → 500 |
| A5 | **Senkronizasyon yönü belirsiz** | DB → JSON (`export_data.py`) ve JSON → DB (`git pull` + stok güncelleme) aynı anda | Veri kaybı riski, yarış koşulu |
| A6 | **İş mantığı HTTP katmanında** | Fiyat/kur/kupon/stok hesapları handler içinde | Yeniden kullanım yok, test zor |
| A7 | **Ajanlar API sürecine gömülü** | `server.py` import zinciri → tüm ajanlar | Bir ajan hatası API'yi düşürebilir; bellek şişer |
| A8 | **Global mutable durum** | `LAST_EMAIL_STATUS`, `LOGIN_ATTEMPTS`, `_attempts` | Çoklu worker'da tutarsız; yeniden başlatmada sıfırlanır |

### 4.4 Önerilen hedef mimari (aşamalı)

```
src/
  api/
    __init__.py
    app.py               # yalnızca uygulama kurulumu + middleware
    routers/
      catalog.py         # /api/products, /api/categories, /api/brands
      cart.py
      checkout.py        # /api/iyzico/*, /api/payment/process
      auth.py            # /api/auth/*  (tek yetki kaynağı)
      account.py         # adresler, siparişler
      admin/
        products.py  orders.py  users.py  coupons.py  agents.py
  services/              # iş mantığı, HTTP'den bağımsız, birim test edilebilir
    pricing.py  coupon_service.py  inventory.py  orders.py  media.py
  domain/                # veri modelleri, doğrulama
  workers/               # ajanlar ayrı süreç (systemd unit veya Celery/RQ)
  web/                   # statik vitrin (mevcut)
```

- **Çerçeve önerisi:** Mevcut `http.server` yerine **FastAPI** (Pydantic doğrulama, otomatik OpenAPI, async, bağımlılık enjeksiyonu). Geçiş, route'lar tek tek taşınarak kademeli yapılabilir; `ThreadingHTTPServer`'ı bir süre reverse proxy arkasında tutmak mümkündür.
- **Ajanları API'den ayırın.** Ajanlar kendi systemd servislerinde veya tek bir `worker` sürecinde çalışsın; API yalnızca DB üzerinden durum okusun. Bu tek değişiklik bellek kullanımını ve çökme yarıçapını ciddi biçimde azaltır.

---

## 5. Katman Bazlı Değerlendirme

### 5.1 Frontend (statik vitrin)

**Olumlu:** Semantik `header/nav/main/section/footer`, `aria-label` kullanımı yaygın, `role="dialog"`/`aria-modal` mevcut, ürün grid'inde `aria-live`, görsellerde `alt`, kart görsellerinde `loading="lazy"`, klavye ile ESC ile modal kapatma, i18n sözlüğü TR/EN tam (203 anahtar, eksik yok).

**Olumsuz:**

| Sorun | Kanıt | Etki |
|---|---|---|
| Ana sayfada ~2,6 MB JS ilk yüklemede | `three.min.js` 590 KB + `OrbitControls` 26 KB + `STLLoader` 10 KB + `pozitron_data.js` 1,54 MB + `app.js` 279 KB | LCP gecikmesi, mobilde veri maliyeti |
| 3D kütüphaneleri **eager** yükleniyor | `index.html:1635-1637` | 3D stüdyo bir modal olmasına rağmen her ziyaretçiye yükleniyor |
| Tüm katalog tek dosyada | `data/pozitron_data.js` 1,54 MB | Ölçeklenmez; 5.000 SKU'da 15 MB olur |
| `app.js` global `fetch` monkey-patch | `api.js:158` | Hata ayıklama zorluğu, yan etkiler |
| Aynı anda iki `og:image` | `index.html:41` ve `:88` | Sosyal önizlemede belirsiz davranış |
| İki çelişkili `Organization` JSON-LD | Telefon `+90-552…` ve `+90-850…` | Google zengin sonuçlarda tutarsızlık |
| `role="banner"` iki kez | announcement + header | Ekran okuyucu karmaşası |
| Skip-link yok | — | Klavye kullanıcısı her sayfada 30+ bağlantı geçer |
| `:focus-visible` yok | `styles.css` (yalnızca input focus) | WCAG 2.4.7 ihlali |
| `prefers-reduced-motion` yok | `styles.css` | Hareket hassasiyeti olan kullanıcılar için sorun |
| `aria-pressed` eksik | para birimi/dil butonları | Seçili durum ekran okuyucuya bildirilmiyor |

### 5.2 Backend (Python API)

**Olumlu:** Parametreli SQL kullanımı yaygın, statik dosya beyaz listesi (`is_static_path_allowed`) ve path traversal koruması doğru çalışıyor (canlıda `/pozitron.db`, `/server.py` → 404), yükleme uzantı beyaz listesi + UUID yeniden adlandırma, yükleme boyut sınırı 30 MB, 301 temiz URL yönlendirmeleri, sitemap üretimi dinamik.

**Olumsuz:**

| Sorun | Kanıt | Etki |
|---|---|---|
| `get_authenticated_user` **tanımlı değil** ama çağrılıyor | `server.py:2922` | `/api/user/addresses` 500 döner (canlıda doğrulandı) |
| `Content-Length` sınırsız | `server.py:1286` (yalnızca upload'da 30 MB kontrolü) | Bellek tüketimi ile DoS |
| `500` yanıtlarında `str(e)` istemciye dönüyor | `server.py:743, 1298, 658` | Şema/dosya yolu sızıntısı |
| Sunucu `0.0.0.0` dinliyor | `server.py:5375` | Nginx yanlış yapılandırılırsa API doğrudan erişilebilir |
| Yerel geliştirici admin bypass'ı | `server.py:542-547` | `POZITRON_ENV` unutulursa aynı makineden tam yetki |
| Rate limit bellek içi | `LOGIN_ATTEMPTS` | Yeniden başlatmada sıfırlanır; çok işlemcide çalışmaz |
| `/api/payment/process` stok kontrolü yok | `server.py:4507-4518` | Aşırı satış (oversell) |
| `/api/payment/process` geçersiz ürünü sessizce atlıyor | `if not prod: continue` | Boş sipariş oluşabilir |
| İdempotency anahtarı yok | — | Çift tıklama/retry → çift sipariş |
| Reconcile edilen sipariş durumu monotonic değil | `iyzico_checkout.py:262` | PAID → FAILED geri dönüşü teorik olarak mümkün |

### 5.3 Veri katmanı

**Olumlu:** WAL, foreign keys, `busy_timeout`, `init_db()` içinde kademeli migrasyon, `UNIQUE(coupon_code, user_key, order_id)` gibi doğru kısıtlar, yedekleme/rollback script'i (`scripts/rollback_catalog.py`), `sqlite3 .backup` önerisi dokümante edilmiş.

**Olumsuz:**
- **Yedekleme otomasyonu yok.** README'de cron örneği var; sistemde kurulu değil. `backups/` klasörü manuel anlık görüntüler içeriyor ve `.gitignore`'da.
- **Test ve üretim verisi karışık.** DB'de `test-coupon-acc`, `coupon_user@example.com`, `pilot@drone.com`, `test_nocode_*@example.com` gibi kayıtlar var; 121 siparişin 108'i "gerçek görünümlü" ama test mahallesi/adresli. Bu, canlı raporlamayı kirletir.
- **`settings.json` ile DB `settings` tablosu çift kaynak.** `bank_owner` DB'de dolu, API'de zorla boşaltılıyor (`server.py:1445`), statik `data/settings.json`'da boş — üç farklı gerçek.
- **Kur tutarsızlığı:** `settings.usd_rate=34.5`, `coupons._exchange_rate()` varsayılanı `35.5`, `/api/coupons/validate` içinde sabit `35.5`, `subagent_procurement.CURRENT_USD_RATE=38.5`. Aynı anda dört farklı kur.
- **Yorum tablosu boş ama ürünlerde `rating`/`review_count` dolu** (ör. 4,8 / 124). Yani puanlar katalogdan geliyor, gerçek yorumdan değil — tüketici mevzuatı açısından risklidir.

### 5.4 Otomasyon katmanı (11 ajan)

Sistem, "Lead Supervisor + 10 alt ajan" olarak konumlandırılmış. Gerçek değer/risk dağılımı:

| Ajan | Gerçek işlev | Değerlendirme |
|---|---|---|
| `lead_supervisor` | 11 adımlı döngü, direktif kaydı | Değerli ama kararları denetimsiz uyguluyor (fiyat, bestseller işaretleme) |
| 1 Instagram | Görsel/reel üretimi, Meta Graph yayını | En olgun ajan; 241 post üretilmiş |
| 2 Reddit | Topluluk yanıtı | **Marka riski**: gizli pazarlama/astroturfing algısı, hesap askıya alınması |
| 3 Telemetri | CPU/RAM/latency | Faydalı |
| 4 SEO | 267 rehber üretmiş | **Kalite sorunu**: şablon tekrarı, aynı konu varyantları (bkz. test bulguları) |
| 5 Fiyat zekâsı | Rakip fiyat | Faydalı, ancak scrape hukuki riski |
| 6 Trend avcısı | Yeni ürün önerisi | Onay mekanizması var (iyi) |
| 7 QA | Sentetik sipariş/link kontrolü | Faydalı; şu an 6 kırık link buluyor |
| 8 Tedarik | Sipariş planı | Faydalı; kur sabiti hatalı (38,5) |
| 9 Güvenlik | Kod taraması | **Yetersiz**: gerçek açıkları kaçırıyor, yanlış pozitif üretiyor |
| 10 Medya | Görsel denetimi | Faydalı ama tam olarak çözemediği belli (209 jenerik görsel) |

**Genel kanı:** Ajan katmanı etkileyici bir mühendislik gösterisi, fakat **ticari getirisi ölçülmüyor**. 10 ajanın ürettiği işin dönüşüme katkısı için tek bir KPI tanımlı değil. Öneri: ajan sayısını azaltmak değil, **her ajana tek bir ölçülebilir çıktı** bağlamak (ör. SEO ajanı → organik oturum; medya ajanı → görsel eşleşme oranı %100).

### 5.5 Medya ve içerik üretimi

- `content_generator.py` (3.151 satır) + `image_generator.py` (2.848 satır) marka şablonu üretiyor; pedestal ışık, glassmorphic sahne, numaralı özellik çipleri. Tasarım açısından tutarlı.
- Ancak üretilen 4,8 GB medya **git'e commit ediliyor**; her commit depoyu büyütüyor. Bu sürdürülemez.
- `assets/instagram/` `.gitignore`'a eklenmiş ama **mevcut 7.160 dosya hâlâ izleniyor** (yorum satırı bunu açıkça söylüyor). Yani koruma yalnızca yeni dosyalar için.

### 5.6 Dağıtım ve operasyon

| Konu | Mevcut durum | Risk |
|---|---|---|
| Süreç yönetimi | systemd (`pozitron.service`) + Dockerfile + Render | Üç ayrı dağıtım yolu, tek doğru kaynak yok |
| Dağıtım yöntemi | Watchdog her 60 sn'de `git pull --rebase origin main` | **Denetimsiz otomatik dağıtım**; bozuk commit canlıya düşer |
| Sırlar | `server.py`, `render.yaml`, `setup_hetzner.sh` içinde gömülü | Repo erişimi = tüm sırlar |
| Dockerfile | `node:20` tabanlı + Chrome + Python | **~1,2 GB imaj**, gereksiz Node katmanı |
| Render planı | `plan: free` | Uyku modu, 512 MB RAM, iyzico reconciler durur |
| Sağlık kontrolü | `/api/health` sabit "healthy" döner | DB/ajan sağlığını yansıtmıyor |
| Loglama | `print()` | Yapılandırılmış log, korelasyon ID, seviye yok |
| İzleme | Yok (ajan telemetrisi dışında) | Kesinti fark edilmez |
| CI | Test/build iş akışı yok | 12 kırık test fark edilmedi |

---

## 6. Verimlilik ve Gereksizlik Analizi

Bu bölüm, "kaldırılsa/azaltılsa sistem daha iyi olur" başlıklarını içerir.

### 6.1 Depo şişkinliği — 4,8 GB gereksiz

| Varlık | Boyut | Öneri | Kazanç |
|---|---:|---|---|
| `assets/instagram/` (7.160 dosya) | 4,8 GB | Git LFS veya S3/R2'ye taşı; repoda yalnızca manifest | Depo ~400 MB'a iner, klon 20 sn |
| `review-dashboard.html` | 2,1 MB, kullanılmayan | Sil | Bakım yükü −1 dosya |
| `backups/` (repo içi) | 2 klasör | Repo dışına, şifreli depoya | Karışıklık giderilir |
| `products/*.html` kopyaları | 603 fazla dosya | Yönlendirme + tek kanonik sayfa | 39 MB → 17 MB, SEO netleşir |
| `assets/products/_originals/` | — | CDN/arşiv | Depo küçülür |
| `data/reddit_history.json` | 1,72 MB | Özet + arşiv ayrımı | İstemciye hiç gitmemeli |

### 6.2 Kullanılmayan / ölü dosyalar

`fetch_real_images.py`, `update_prices.py`, `sync_all_real_product_images.py`, `review-dashboard.html`, `data/catalog.db` (0 bayt), `data/database.sqlite` (0 bayt), `data/instagram.db` (0 bayt), `data/pozitron.db` (0 bayt) — hiçbiri referans edilmiyor. **Toplam temizlik: 6 dosya, 2,1 MB + kafa karışıklığı.**

> Not: `data/` altındaki 0 baytlık `.db` dosyaları, `DATABASE_PATH` yanlış verildiğinde sessizce boş DB oluşturma riskini gösterir. Silinmeli ve `get_db()` var olmayan yolda hata vermeli.

### 6.3 Tekrar eden kod

| Kalıp | Kaç yerde | Öneri |
|---|---|---|
| `if path == '/api/...'` route bloğu | 129 | Router/dekoratör |
| Sipariş listeleme + `items_json` parse | 5 (`/api/orders`, `/api/orders/<n>`, `/api/orders/user/<id>`, `/api/admin/orders`, admin paneli) | Tek `serialize_order()` |
| `Authorization`/`X-Admin-Key` başlık kurma | 6+ (api.js ×2, admin.html ×3, bots.html) | Tek istemci |
| Kupon geçerlilik akışı | 3 (`validate_coupon`, `/api/coupons/validate`, iyzico init) | Zaten servis var, uçlar onu kullanmalı |
| `git pull` + stok senkronu | 2 (`watchdog`, `/api/admin/sync-cloud-market`) | Tek fonksiyon |
| Para birimi dönüşümü | 4 farklı sabit | Tek `get_usd_rate()` |
| Ürün kartı HTML'i | 2 (app.js, generate_product_pages.py) | Sunucu tarafı render veya tek şablon |

### 6.4 Gereksiz çalışan işler

| İş | Sorun | Öneri |
|---|---|---|
| Watchdog her 60 sn `git pull` | Gereksiz ağ trafiği, `--rebase` çakışma riski, denetimsiz dağıtım | Kaldır; yerine webhook tabanlı kontrollü dağıtım |
| Instagram ajanı 2 saatte bir | 241 post üretmiş; etkileşim ölçülmüyor | Kadansı veriye bağla (engagement < eşik → durdur) |
| 11 ajanın her döngüde çalışması | CPU + LLM maliyeti | Olay tabanlı tetikleme |
| Ana sayfada 3D kütüphaneleri | Modal açılmadan yükleniyor | Dinamik `import()` |
| `fetchProducts()` yorum sonrası tam yeniden çekme | Gereksiz 500 KB trafik | Yerel güncelleme |

### 6.5 Ölçülebilir hedefler

| Metrik | Bugün | 90 gün hedefi |
|---|---:|---:|
| Ana sayfa transfer boyutu | ~2,6 MB | < 800 KB |
| LCP (mobil, 4G) | ölçülmedi (~4–6 sn tahmini) | < 2,5 sn |
| Git deposu | 5,2 GB | < 600 MB |
| Ürün sayfası dosyası | 1.120 | 509 + yönlendirmeler |
| Stokta ürün oranı | %0,2 | > %60 |
| Gerçek görsel eşleşmesi | %59 | %100 |
| Kırık test | 12 | 0 |
| Test koşum süresi | > 15 dk | < 3 dk |

---

## 7. Veri Kalitesi ve Ticari Etki

### 7.1 Stok — en acil ticari sorun

508/509 ürün stok 0. Sonuçları:

- Ürün kartlarında "Sepete Ekle" yerine yalnızca "Stoğa Gelince Haber Ver" görünüyor.
- Google Merchant feed'inde 508 satır `out_of_stock` → Shopping kampanyaları durur.
- `stock_alerts` tablosu **0 kayıt** → talep toplama mekanizması hiç kullanılmamış.
- Checkout'ta satın alınabilir ürün yok; iyzico akışı test edilemez.

**Öneri:** Stok verisi bir "göster" alanı değil, operasyonel bir alandır. (a) Gerçek stok varsa içe aktarın, (b) yoksa "ön sipariş/tedarik süresi" modeli ekleyin (`preorder`, `lead_time_days`), (c) en az 50 yüksek marjlı SKU için acil tedarik planı çalıştırın (Subagent 8 zaten bunu üretiyor — `data/latest_procurement_plan.json`).

### 7.2 Görseller — güven ve mevzuat sorunu

- 209 ürün jenerik trend görseli kullanıyor; 103 ürün **tamamen aynı** fotoğrafı gösteriyor.
- `products/*.html` içindeki `og:image` bu yanlış görseli paylaşıyor.
- Merchant Center, "image_link ürünle eşleşmiyor" gerekçesiyle reddeder; tüketici ise yanlış ürün alır.

**Öneri:** `subagent_media_inspector` zaten pHash ve semantik denetim yapıyor. Kural şu olmalı: **görsel SKU ile birebir eşleşmiyorsa ürün yayına alınmaz.** 209 ürün bu kural devreye girerse "taslak" durumuna düşer; bu, yanlış ürün satmaktan iyidir.

### 7.3 Fiyat ve kur

| Kaynak | Kur | Kullanım |
|---|---:|---|
| `settings.usd_rate` | 34,50 | `/api/settings`, `/api/currency-rate` |
| `coupons._exchange_rate()` | 35,50 | Kupon min. tutar dönüşümü |
| `/api/coupons/validate` sabiti | 35,50 | Kupon doğrulama |
| `subagent_procurement` | 38,50 | Tedarik planı |
| Ürün `price_usd` / `price_try` | 34,50 türevi | Katalog |

Sonuç: aynı sepet için kupon uygunluğu, gösterilen fiyat ve tedarik maliyeti farklı kurla hesaplanıyor. Kur %10 oynadığında marj sessizce eriyor.

**Öneri:** Tek `settings.usd_rate` + `services/pricing.py`. Kur güncellemesi tek transaction'da tüm `price_try` alanlarını yeniden hesaplasın, `price_updated_at` damgası eklensin.

### 7.4 İçerik kalitesi (SEO ajanı)

Testler, SEO üretiminde ciddi tekrar olduğunu gösteriyor:

- 100 konu içinde **yinelenen odaklar** (`Sistem EMC Analizi` 2 kez, `Yedeklilik Mimarisi` 2 kez…)
- Aynı konunun 10 varyantı (`… ileri seviye ince ayar`, `… karşılaştırmalı analiz`, `… bakım prosedürleri` …) → **thin content**
- `seo_articles.json` (266 kayıt) ile DB (100 kayıt) arasında senkron farkı

**Etki:** Google, aynı konunun 10 varyantını "doorway pages" olarak değerlendirebilir; manuel ceza riski. **Öneri:** varyant üretimini kapat, konu başına tek derin makale (1.500+ kelime) üret, `canonical` ve iç linkleme ekle.

### 7.5 Yorumlar ve puanlar

- `reviews` tablosu boş; buna karşın ürünlerde `rating=4.8`, `review_count=124` gibi değerler var.
- `POST /api/reviews` her yoruma `verified_purchase=1` yazıyor (`server.py:4717`), yani "Doğrulanmış Alışveriş" etiketi anlamsız.
- Ana sayfadaki yorumlar yalnızca `localStorage`'dan okunuyor → her ziyaretçi farklı (veya boş) yorum görüyor.

**Etki:** Ticaret Bakanlığı e-ticaret denetimleri ve Ticari Reklam mevzuatı açısından "gerçeği yansıtmayan puan" riski.

---

## 8. Test ve Kalite Güvencesi

36 test dosyası ayrı ayrı çalıştırıldı (tam koşum 15 dakikayı aştığı için paralel/izole koşum yapıldı):

| Sonuç | Sayı |
|---|---:|
| Geçen test | **201** |
| Başarısız test | **12** |
| Zaman aşımı (ağ/LLM bağımlı) | 3 dosya |

### Kırık testler ve kök neden

| Test dosyası | Başarısız | Kök neden | Yorum |
|---|---:|---|---|
| `test_seo_deduplication.py` | 3 | Konu tekrarı + JSON/DB uyumsuzluğu (266 vs 100) | **Gerçek ürün hatası** |
| `test_currency_and_admin_panel.py` | 2 | `bank_owner` API'de boşaltılıyor; PDP'de `pdp-price-current` yok | **Gerçek hata** (test beklentisi güncel değil veya üretici bozuk) |
| `test_cyber_security_agent.py` | 1 | SQL tarayıcı yanlış pozitif | Tarayıcı iyileştirilmeli |
| `test_qa_agent.py` | 1 | 6 kırık ürün linki | **Gerçek hata** |
| `test_procurement_agent.py` | 1 | Marj %22,8 < %30 eşiği | **Gerçek hata** (kur 38,5 etkisi) |
| `test_instagram_diversity.py` | 1 | 12 spotlight'ın tamamı "propellers" | **Gerçek hata** (içerik çeşitliliği) |
| `test_trend_hunter_price_comparison.py` | 1 | Otomatik fiyat güncelleme mesajı yok | **Gerçek hata** |
| `test_turkish_targeting.py` | 1 | Hashtag listesi eksik | Konfigürasyon |
| `test_content_filtering_and_new_reels_types.py` | 1 | Post tipi sayısı 9 ≠ 8 | Test güncel değil |

**Kritik gözlem:** Kırık testlerin 7'si **gerçek ürün hatalarını** işaret ediyor. CI olmadığı için bunlar canlıya yansımış durumda.

### Öneri

```yaml
# .github/workflows/ci.yml (öneri)
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt pytest
      - run: pytest tests -q -x --timeout=60
```

Ayrıca: ağ/LLM bağımlı testler `@pytest.mark.integration` ile ayrılsın; varsayılan koşum < 60 sn olsun.

---

## 9. Performans ve Maliyet

### 9.1 İstemci performansı

| Kaynak | Boyut | Kritik mi? |
|---|---:|---|
| `data/pozitron_data.js` | 1,54 MB | Evet (ilk render) |
| `vendor/three.min.js` | 590 KB | **Hayır** (modal) |
| `app.js` | 279 KB | Evet |
| `styles.css` | 124 KB | Evet |
| `assets/hero_drone_white.png` | 463 KB | Evet (LCP adayı) |
| `assets/og-image.jpg` | 517 KB | Hayır (yalnızca paylaşım) |
| `i18n.js` + `api.js` | 30 KB | Evet |
| **Toplam (cache'siz)** | **~3,0 MB** | |

**En yüksek getirili 5 optimizasyon:**

1. 3D kütüphanelerini modal açılışında `import()` ile yükle → **−626 KB**
2. Hero görselini AVIF/WebP + `srcset` yap → **−350 KB**
3. `pozitron_data.js`'i sayfalanmış API'ye veya parçalı JSON'a böl (kategori bazlı) → **−1,2 MB**
4. `app.js`'i code-split (checkout, 3D, admin ayrı chunk) → **−150 KB**
5. Brotli + `Cache-Control: immutable` (hash'li dosya adlarıyla) → transfer **−70%**

> Not: `end_headers()` tüm `.js/.css/.html/api` yanıtlarına `no-store` gönderiyor (`server.py:623-628`). Bu, tekrar ziyaretlerde **her şeyin yeniden indirilmesi** demektir. Hash'li sürüm sorguları (`?v=...`) zaten var; `no-store` yerine `immutable` kullanılabilir.

### 9.2 Sunucu maliyeti / kapasite

- Python `ThreadingHTTPServer` + SQLite: tek düğüm için yeterli, yatay ölçeklenmez.
- Render `free` planı: 512 MB RAM, uyku modu → **iyzico reconciler ve ajanlar durur**. Ödeme mutabakatı için kabul edilemez.
- Docker imajı Node + Chrome + Python içeriyor (~1,2 GB); Chrome yalnızca Instagram giriş otomasyonu için → ayrı servise çıkarılmalı.

---

## 10. Teknik Borç Kaydı (önceliklendirilmiş)

| ID | Borç | Öncelik | Efor | Etki |
|---|---|---|---|---|
| TD-01 | Gömülü sırlar (API anahtarı, SMTP, SECRET_KEY) | **P0** | 2 saat | Kritik |
| TD-02 | Kanıtsız `/api/auth/google` | **P0** | 4 saat | Kritik |
| TD-03 | Korumasız `/api/orders` | **P0** | 2 saat | Kritik |
| TD-04 | Stok verisinin sıfır olması | **P0** | 1–3 gün | Ticari |
| TD-05 | Görsel-SKU eşleşmemesi | **P0** | 3–5 gün | Ticari |
| TD-06 | `server.py` monoliti | P1 | 2–4 hafta | Sürdürülebilirlik |
| TD-07 | Kur tutarsızlığı | P1 | 1 gün | Marj |
| TD-08 | Yorum XSS + sahte doğrulama | P1 | 1 gün | Güvenlik/mevzuat |
| TD-09 | Şifre hash'i (SHA-256 → Argon2id) | P1 | 1 gün | Güvenlik |
| TD-10 | 603 kopya ürün sayfası | P1 | 2 gün | SEO |
| TD-11 | 4,8 GB medya git'te | P1 | 2 gün | Operasyon |
| TD-12 | CI yok, 12 kırık test | P1 | 2 gün | Kalite |
| TD-13 | 3D kütüphaneleri eager | P2 | 2 saat | Performans |
| TD-14 | `no-store` cache politikası | P2 | 3 saat | Performans |
| TD-15 | Yedekleme otomasyonu yok | P2 | 3 saat | Dayanıklılık |
| TD-16 | Yapılandırılmış log/izleme yok | P2 | 1 gün | Operasyon |
| TD-17 | Ölü dosyalar (6 adet) | P3 | 30 dk | Temizlik |
| TD-18 | İki ürün sayfası üreticisi | P2 | 1 hafta | Bakım |
| TD-19 | `get_authenticated_user` tanımsız | P1 | 1 saat | Hata |
| TD-20 | Test/prod veri karışıklığı | P2 | 1 gün | Raporlama |

---

## 11. Yol Haritası

### Faz 0 — Acil (0–48 saat)

1. Tüm sırları döndür: `ADMIN_API_KEY`, `SECRET_KEY`, SMTP uygulama şifresi, GAS relay URL'si.
2. İstemciden API anahtarını tamamen kaldır (`api.js`, `admin.html`, `bots.html`).
3. `/api/auth/google`'u Google ID token zorunluluğuna bağla; `aud` ve `iss` doğrula.
4. `/api/orders`, `/api/orders/<no>`, `/api/user/addresses*` uçlarına sahiplik kontrolü ekle.
5. Yorumlarda `innerHTML` yerine `textContent`; `verified_purchase` gerçek sipariş kontrolüne bağla.
6. `POZITRON_ENV=production` ve yerel admin bypass'ının kapatıldığını doğrula.

### Faz 1 — Stabilizasyon (1–2 hafta)

1. Gerçek stok ve gerçek görsel içe aktarımı; "görsel yoksa yayına alma" kuralı.
2. Tek kur kaynağı + fiyat yeniden hesaplama.
3. Argon2id'ye geçiş ve şifre sıfırlama akışına deneme sınırı.
4. CI pipeline + 12 kırık testin düzeltilmesi.
5. Güvenlik başlıkları (CSP, HSTS, Referrer-Policy) ve CORS daraltma.
6. `/api/health` gerçek kontrolleri (DB, kuyruk, ödeme reconciler) döndürsün.

### Faz 2 — Sürdürülebilirlik (3–6 hafta)

1. `server.py` → `services/` + `routers/` ayrıştırması (FastAPI'ye kademeli geçiş).
2. Ajanları ayrı sürece çıkar.
3. Medyayı git'ten çıkar (LFS/R2).
4. 603 kopya ürün sayfasını 301 ile kanonikleştir.
5. Performans paketi (3D lazy, görsel optimizasyonu, cache politikası).
6. Yedekleme + izleme + uyarı (uptime, 5xx oranı, ödeme reconciler gecikmesi).

### Faz 3 — Büyüme (2–3 ay)

1. Ölçülebilir ajan KPI'ları; düşük getirili otomasyonu kapat.
2. A/B test altyapısı ve dönüşüm ölçümü.
3. Çoklu depo/stok yönetimi, tedarik otomasyonunun gerçek tedarikçi API'lerine bağlanması.
4. SEO içerik stratejisinin yeniden kurgulanması (thin content temizliği).

---

## 12. Sonuç

Pozitron Market, **iyi fikirli ve yer yer çok iyi uygulanmış** bir platformdur; ödeme ve kupon katmanları profesyonel ölçekte tasarlanmıştır. Ancak sistem şu anda üç ayrı eksende aynı anda tökezlemektedir: **güvenlik (kritik), veri (stok/görsel) ve sürdürülebilirlik (monolit + devasa depo)**.

İyi haber: sorunların hiçbiri mimari olarak çözümsüz değil. Faz 0'daki altı madde, sistemi "savunulabilir" hale getirmek için yeterlidir ve toplamda **1–2 günlük iş**tir. Stok ve görsel sorunu ise bir mühendislik değil, **operasyon ve tedarik** sorunudur; kod tarafında yalnızca "yanlış veriyi yayına alma" kapısının kapatılması gerekir.

---

## Ek A — Doğrulama Komutları

```bash
# Sırların istemcide olup olmadığını doğrula
grep -rn "pzt_adm_\|ADMIN_API_KEY" api.js admin.html bots.html

# Yetkisiz sipariş ifşası (canlı, salt-okunur)
curl -s -o /dev/null -w '%{http_code}\n' https://api.pozitronmarket.com/api/orders

# Kanıtsız Google girişi (yalnızca e-posta ile)
curl -s -X POST https://api.pozitronmarket.com/api/auth/google \
     -H 'Content-Type: application/json' -d '{"email":"<bir-musteri-adresi>"}' | head -c 200

# Kur tutarlılığı
grep -rn "35.5\|38.50\|34.5" --include=*.py .

# Stok durumu
python3 -c "import sqlite3;c=sqlite3.connect('pozitron.db');print(c.execute('select count(*) from products where stock>0').fetchone())"

# Görsel tekrarı
python3 -c "import json,collections;p=json.load(open('data/products.json'));print(collections.Counter(x['image_url'] for x in p).most_common(3))"
```

## Ek B — Rapor Ailesi

| Dosya | İçerik |
|---|---|
| `01-proje-analiz-raporu.md` | Bu rapor — mimari, verimlilik, teknik borç, yol haritası |
| `02-ux-raporu.md` | Kullanıcı deneyimi, erişilebilirlik, dönüşüm |
| `03-siber-guvenlik-raporu.md` | Güvenlik bulguları, PoC, düzeltme planı |

---

*Bu rapor, 1 Kasım 2026 itibarıyla depo ve canlı ortam üzerinde yapılan incelemeye dayanır. Bulguların bir kısmı hızlı değişebilir; düzeltmeler sonrası yeniden doğrulama önerilir.*
