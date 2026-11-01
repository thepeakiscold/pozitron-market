# Pozitron Market — Denetim Raporları

**Tarih:** 1 Kasım 2026
**Sürüm:** 1.0
**Sınıflandırma:** Gizli — Dahili

Bu klasör, Pozitron Market platformunun üç eksende yapılan kapsamlı denetimini içerir.

| # | Rapor | Kapsam | Hedef kitle |
|---|---|---|---|
| 1 | [`01-proje-analiz-raporu.md`](./01-proje-analiz-raporu.md) | Mimari, kod kalitesi, verimlilik, veri kalitesi, teknik borç, yol haritası | Teknik liderlik, ürün sahibi |
| 2 | [`02-ux-raporu.md`](./02-ux-raporu.md) | Kullanıcı deneyimi, dönüşüm hunisi, erişilebilirlik (WCAG 2.2 AA), performans | Ürün, tasarım, pazarlama |
| 3 | [`03-siber-guvenlik-raporu.md`](./03-siber-guvenlik-raporu.md) | Kimlik doğrulama, yetkilendirme, sır yönetimi, uyumluluk, olay müdahale | Teknik liderlik, hukuk, DevOps |

---

## ⚠️ Önce bunu okuyun

Güvenlik raporunda **canlı ortamda doğrulanmış, kimlik doğrulamayı tamamen atlayan** açıklar vardır. Aşağıdaki iki işlem, diğer her şeyden önce yapılmalıdır:

1. `ADMIN_API_KEY` ve `SECRET_KEY` değerlerini döndürün, istemci kodundan kaldırın.
2. `/api/auth/google` uç noktasını Google ID token doğrulaması zorunlu olana kadar kapatın.

Ayrıntı: [`03-siber-guvenlik-raporu.md`](./03-siber-guvenlik-raporu.md) — Bölüm "ACİL UYARI" ve Bölüm 8 (Olay Müdahale Planı).

---

## Yönetici özeti — tek sayfa

### Durum

| Alan | Puan / 10 | Kritik sorun |
|---|---:|---|
| Mimari | 7,0 | İki katmanlı hibrit model doğru; `server.py` 5.408 satır monolit |
| Kod kalitesi | 4,5 | 129 route tek sınıfta; iki paralel ürün sayfası üreticisi |
| Veri kalitesi | 2,5 | 509 ürünün 508'i stok dışı; 209 üründe jenerik görsel |
| UX | 5,0 | Ödemede sipariş özeti yok; stok uyarısı bildirim göndermiyor |
| Performans | 4,0 | Ana sayfada ~3 MB ilk yükleme; 3D eager |
| Test | 6,0 | 201 geçen / 12 kırık test; CI yok |
| Operasyon | 4,0 | `git pull` ile denetimsiz dağıtım; yedek otomasyonu yok |
| **Güvenlik** | **3,1** | **Kanıtsız yönetici oturumu, PII ifşası, istemcide API anahtarı** |

### Ticari gerçek

Site teknik olarak etkileyici ama şu anda **satış yapamıyor**:

- 509 üründen yalnızca 1'inde stok var (6 adet).
- 209 ürün gerçek fotoğraf yerine jenerik görsel kullanıyor; 103 ürün aynı fotoğrafı paylaşıyor.
- Google Merchant feed'indeki 509 ürünün 508'i `out_of_stock`.
- Ödeme adımında kullanıcı ne için ödediğini göremiyor (sipariş özeti yok).
- Stok uyarısı formu "haber vereceğiz" diyor; sistemde hiçbir bildirim gönderilmiyor.

### İlk 48 saat — yapılacaklar

| # | İş | Süre |
|---|---|---|
| 1 | Tüm sırları döndür (admin anahtarı, SECRET_KEY, SMTP, Reddit, GAS) | 1 saat |
| 2 | Admin anahtarını istemci kodundan kaldır | 1 saat |
| 3 | `/api/auth/google`'u token doğrulamasına bağla | 2 saat |
| 4 | `/api/orders`, `/api/orders/<no>`, adres uçlarına yetki kontrolü | 3 saat |
| 5 | Yorum XSS'ini kapat (`escapeHTML` / `bleach`) | 1 saat |
| 6 | Ödeme adımına sipariş özeti ekle | 4 saat |
| 7 | Stok uyarısı metnini düzelt (veya bildirim işini yaz) | 2 saat |

**Toplam: ~14 saatlik iş.** Bu süre sonunda platform "savunulabilir" ve "kullanılabilir" hale gelir.

---

## Ortak metodoloji

- **Statik analiz:** 36 Python dosyası (~21.000 satır), 5 JS dosyası (~8.300 satır), 26 HTML şablonu, 1 CSS (6.399 satır).
- **Veri analizi:** SQLite (`pozitron.db`, 34 tablo, 509 ürün, 121 sipariş), JSON/TSV feed'ler, görsel tekrar analizi.
- **Dinamik doğrulama:** Yerel (`127.0.0.1:8000`) ve canlı API üzerinde **salt-okunur** istekler.
- **Test koşumu:** 36 test dosyası ayrı ayrı `pytest` ile çalıştırıldı.
- **Etik sınır:** Hiçbir veri kopyalanmadı/saklanmadı; raporlarda tüm PII ve sırlar maskelendi.

---

## Öncelikli tek liste (tüm raporlar birleşik)

| Öncelik | İş | Kaynak |
|---|---|---|
| **P0** | Sır rotasyonu + istemciden anahtar kaldırma | SEC-01, SEC-06, SEC-07 |
| **P0** | `/api/auth/google` token zorunluluğu | SEC-02 |
| **P0** | Sipariş ve adres uçlarında yetkilendirme | SEC-03, SEC-04, SEC-08 |
| **P0** | Yorum XSS + sahte doğrulama | SEC-05, UX-41 |
| **P0** | Ödeme adımına sipariş özeti | UX-01 |
| **P0** | Stok uyarısı bildirimi (veya metin düzeltmesi) | UX-02 |
| **P0** | Gerçek stok verisi / ön sipariş modeli | UX-03 |
| **P0** | Görsel–SKU eşleşmesi | UX-21 |
| **P1** | Şifre hash'i (Argon2id) + sıfırlama limiti | SEC-09, SEC-10 |
| **P1** | Oturum mimarisi (kısa token, iptal) | SEC-11 |
| **P1** | CSP/HSTS/CORS daraltma | SEC-12, SEC-13 |
| **P1** | Ödemede kupon alanı + giriş ipucu | UX-04, UX-26 |
| **P1** | Sipariş geçmişini API'den çek | UX-05 |
| **P1** | Erişilebilirlik: skip-link, focus-visible, focus trap | UX Bölüm 5 |
| **P1** | CI pipeline + 12 kırık test | Analiz Bölüm 8 |
| **P1** | Otomatik `git pull` kaldır, kontrollü dağıtım | SEC-21 |
| **P2** | Monolit ayrıştırma (services/routers) | TD-06 |
| **P2** | 4,8 GB medyayı git'ten çıkar | TD-11 |
| **P2** | 603 kopya ürün sayfasını kanonikleştir | TD-10 |
| **P2** | Performans paketi (3D lazy, görsel, cache) | UX Bölüm 6 |
| **P2** | Yedekleme + izleme + alarm | SEC-25, TD-15 |

---

## Doğrulama komutları (düzeltme sonrası)

```bash
# Güvenlik — hepsi geçmeli
curl -s https://pozitronmarket.com/api.js | grep -c "pzt_adm_"            # 0
curl -s -o /dev/null -w '%{http_code}\n' \
  https://api.pozitronmarket.com/api/orders                                # 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  https://api.pozitronmarket.com/api/auth/google \
  -H 'Content-Type: application/json' -d '{"email":"x@y.z"}'               # 401
curl -sI https://pozitronmarket.com | grep -ci "content-security-policy"   # 1

# Veri — hepsi iyileşmeli
python3 -c "import sqlite3;c=sqlite3.connect('pozitron.db');\
print(c.execute('select count(*) from products where stock>0').fetchone()[0])"   # > 300
python3 -c "import json,collections;p=json.load(open('data/products.json'));\
print(len({x['image_url'] for x in p}), len(p))"                                # eşit olmalı

# Test — 0 kırık
pytest tests -q
```

---

*Raporlar 1 Kasım 2026 itibarıyla geçerlidir. Düzeltmeler sonrası yeniden doğrulama önerilir.*
