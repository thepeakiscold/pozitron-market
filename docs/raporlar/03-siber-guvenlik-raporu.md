# Pozitron Market — Siber Güvenlik Denetim Raporu

**Rapor No:** PZTR-SEC-2026-11-01
**Tarih:** 1 Kasım 2026
**Sürüm:** 1.0 (Final)
**Sınıflandırma:** **GİZLİ — Yalnızca yetkili personel**
**Kapsam:** `pozitronmarket.com` (statik vitrin), `api.pozitronmarket.com` (Python API), yerel kurulum (`127.0.0.1:8000`), kaynak kod deposu, CI/CD ve dağıtım tanımları
**Test tipi:** Gri kutu — kaynak kod incelemesi + canlı ortamda salt-okunur doğrulama

---

## ⚠️ ACİL UYARI

Bu denetimde **kimlik doğrulamayı tamamen atlatan, canlı ortamda çalıştığı doğrulanmış** açıklar tespit edilmiştir. Aşağıdaki iki adım, bu raporun geri kalanından bağımsız olarak **bugün** yapılmalıdır:

1. **`ADMIN_API_KEY` ve `SECRET_KEY` değerlerini derhal döndürün** ve istemci kodundan kaldırın.
2. **`/api/auth/google` uç noktasını, Google ID token doğrulaması zorunlu olana kadar devre dışı bırakın.**

Gerekçe: Aşağıdaki iki istek, hiçbir kimlik bilgisi olmadan mağazanın tüm müşteri verisine ve yönetim işlevlerine erişim sağlamaktadır. Her ikisi de 1 Kasım 2026'da canlı ortamda doğrulanmıştır.

```bash
# 1) Herkese açık api.js içindeki anahtar ile yönetici API'si
curl -H "X-Admin-Key: pzt_adm_sec_…" https://api.pozitronmarket.com/api/admin/orders
#   → 200 OK, tüm siparişler: ad, e-posta, telefon, adres

# 2) Yalnızca e-posta adresi vererek yönetici oturumu
curl -X POST https://api.pozitronmarket.com/api/auth/google \
     -H 'Content-Type: application/json' -d '{"email":"<mağaza-yöneticisi-e-postası>"}'
#   → 200 OK, "role": "admin" içeren geçerli Bearer token
```

> **Varsayım:** Bu anahtarlar herkese açık olduğu için **sisteme yetkisiz erişim hâlihazırda gerçekleşmiş olabilir**. Bölüm 8'deki olay müdahale planı uygulanmalı ve erişim kayıtları incelenmelidir.

---

## 1. Yönetici Özeti

Pozitron Market'in güvenlik duruşu **iki uç arasında savrulmaktadır**. Ödeme entegrasyonu (`iyzico_checkout.py`) gerçek anlamda iyi tasarlanmıştır: kart verisi sunucuya hiç dokunmaz, HMAC imzaları `compare_digest` ile doğrulanır, tutar/para birimi/sepet kimliği eşleştirilir, `fraudStatus=1` olmayan işlemler karantinaya alınır, kaçırılan callback'ler telafi edilir. Kupon motoru da benzer olgunluktadır. Yol geçişi (path traversal) ve dosya yükleme korumaları canlı testte **doğru çalışmıştır** (`/pozitron.db` → 404, `/server.py` → 404).

Buna karşılık **kimlik doğrulama ve yetkilendirme katmanı çökmüş durumdadır**. Üç bağımsız kritik hata birleşince, uzaktaki herhangi bir kişi hiçbir kimlik bilgisi olmadan:

- tüm müşterilerin ad, e-posta, telefon ve adres bilgilerine,
- tüm sipariş geçmişine ve tutarlarına,
- yönetici oturumuna ve dolayısıyla ürün silme, kupon oluşturma, ajan tetikleme, fiyat değiştirme yetkilerine

erişebilmektedir.

**Genel güvenlik puanı: 3,1 / 10** — *Kabul edilemez risk. Üretim kullanımı için uygun değil.*

| Alan | Puan | Durum |
|---|---:|---|
| Kimlik doğrulama | 1,0 | Kanıtsız yönetici oturumu |
| Yetkilendirme | 1,5 | Korumasız PII uçları, IDOR |
| Sır yönetimi | 0,5 | Anahtarlar istemcide ve repoda |
| Girdi doğrulama / XSS | 3,5 | Kalıcı XSS doğrulandı |
| Ödeme güvenliği | 8,0 | İyi tasarlanmış |
| Veritabanı güvenliği | 5,5 | Parametreli sorgular iyi; şifre hash'i zayıf |
| Oturum yönetimi | 2,5 | 365 gün, iptal edilemez, `localStorage` |
| Yapılandırma / başlıklar | 3,0 | CSP/HSTS yok, CORS `*` |
| Loglama & izleme | 2,0 | `print()`, yönetici işlem kaydı yok |
| Tedarik zinciri | 4,0 | `git pull` ile otomatik dağıtım |

### Bulgu dağılımı

| Önem | Adet | CVSS aralığı |
|---|---:|---|
| **Kritik** | 8 | 9,0 – 9,8 |
| **Yüksek** | 9 | 7,0 – 8,9 |
| **Orta** | 8 | 4,0 – 6,9 |
| **Düşük** | 4 | 0,1 – 3,9 |
| **Toplam** | **29** | |

### Bulgu özet tablosu

| ID | Bulgu | CVSS | Durum |
|---|---|---:|---|
| SEC-01 | Yönetici API anahtarı herkese açık istemci kodunda | **9,8** | Doğrulandı (canlı) |
| SEC-02 | `/api/auth/google` kanıtsız yönetici token'ı veriyor | **9,8** | Doğrulandı (canlı) |
| SEC-03 | `/api/orders` kimlik doğrulaması olmadan tüm siparişleri döndürüyor | **7,5** | Doğrulandı (canlı) |
| SEC-04 | `/api/orders/<no>` sıralı tahminle PII ifşası | 7,5 | Doğrulandı (canlı) |
| SEC-05 | Yorumlarda kalıcı XSS + sahte "doğrulanmış alışveriş" | **8,2** | Doğrulandı |
| SEC-06 | Varsayılan/gömülü `SECRET_KEY` ile token sahteleme | **9,1** | Kod kanıtı |
| SEC-07 | SMTP uygulama şifresi repoda ve git geçmişinde | 7,5 | Doğrulandı |
| SEC-08 | Adres uçlarında IDOR (oku/yaz/sil, yetkisiz) | **8,1** | Doğrulandı |
| SEC-09 | Şifreler tek tuzlu SHA-256 ile saklanıyor | 7,2 | Kod kanıtı |
| SEC-10 | Şifre sıfırlama kodunda deneme sınırı yok (6 hane) | 6,5 | Kod kanıtı |
| SEC-11 | 365 günlük, iptal edilemeyen oturum + `localStorage` | 6,5 | Kod kanıtı |
| SEC-12 | `Access-Control-Allow-Origin: *` tüm API'de | 5,3 | Doğrulandı |
| SEC-13 | CSP / HSTS / Referrer-Policy yok | 4,3 | Doğrulandı |
| SEC-14 | 500 hatalarında iç hata mesajı sızıntısı | 5,3 | Doğrulandı |
| SEC-15 | İstek gövdesinde boyut sınırı yok (DoS) | 5,3 | Kod kanıtı |
| SEC-16 | `admin.html` yalnızca istemci tarafı kontrolle korunuyor | 7,5 | Doğrulandı |
| SEC-17 | Yerel geliştirici admin bypass'ı (`127.0.0.1`) | 6,5 | Kod kanıtı |
| SEC-18 | E-posta bazlı giriş kilidi ile hesap kilitleme DoS'u | 5,3 | Kod kanıtı |
| SEC-19 | Stok kontrolü olmadan sipariş (oversell) | 5,3 | Kod kanıtı |
| SEC-20 | Güvenlik/telemetri uçları herkese açık | 3,7 | Doğrulandı |
| SEC-21 | Her 60 sn `git pull --rebase` ile denetimsiz dağıtım | 6,5 | Kod kanıtı |
| SEC-22 | Yerel sunucuda Reddit oturum çerezi statik olarak erişilebilir | 6,5 | Doğrulandı (yerel) |
| SEC-23 | Ödeme/sipariş uçlarında idempotency yok | 4,3 | Kod kanıtı |
| SEC-24 | Rate limit bellek içi ve tek süreçli | 3,7 | Kod kanıtı |
| SEC-25 | Yönetici işlemleri için denetim kaydı yok | 4,3 | Kod kanıtı |
| SEC-26 | Para birimi parametresi ile tutar/kur karışıklığı | 4,3 | Kod kanıtı |
| SEC-27 | `/api/telemetry` kimlik doğrulamasız yazma | 3,7 | Doğrulandı |
| SEC-28 | Sunucu `0.0.0.0` dinliyor, hata ayıklama bilgisi | 3,1 | Kod kanıtı |
| SEC-29 | `robots.txt` hassas yolları listeliyor (bilgi sızıntısı) | 2,6 | Doğrulandı |

---

## 2. Kapsam ve Metodoloji

### 2.1 Yetki ve etik çerçeve

Testler, sistem sahibinin talebi üzerine ve **yalnızca kendi varlıkları üzerinde** gerçekleştirilmiştir. Uygulanan sınırlar:

- Canlı ortamda **yalnızca salt-okunur** istekler (GET) ve kimlik doğrulama doğrulaması amaçlı oturum açma denemeleri yapıldı.
- Hiçbir veri kopyalanmadı, dışarı aktarılmadı veya saklanmadı.
- Hiçbir yıkıcı işlem (silme, değiştirme, aşırı yükleme) yapılmadı.
- Yerel ortamda yapılan tek yazma testi (XSS amaçlı yorum kaydı) aynı oturumda silindi; kalan kayıt sayısı `0` olarak doğrulandı.
- Raporda tüm kişisel veriler ve sırlar maskelenmiştir (`pzt_adm_sec_…`, `+9055…`, `b***@gmail.com`).
- **Kapsam dışı:** Sosyal mühendislik, fiziksel erişim, üçüncü taraf hizmetlerin (iyzico, Google, Meta) kendi altyapıları, DDoS/dayanıklılık testleri.

### 2.2 Kullanılan yöntemler

| Yöntem | Detay |
|---|---|
| Manuel kod incelemesi | 21.000 satır Python, 8.300 satır JS hedefli tarama |
| Kalıp taraması | Sır, SQL birleştirme, `innerHTML`, zayıf hash, `eval`, `subprocess` |
| Dinamik doğrulama | `curl` ile canlı ve yerel API'ye yönelik kontrollü istekler |
| Yetkilendirme matrisi | Her uç nokta için "kim erişebilmeli / kim erişebiliyor" karşılaştırması |
| Yapılandırma denetimi | systemd, Dockerfile, Render, Nginx, GitHub Actions |
| Bağımlılık incelemesi | `requirements.txt`, `package.json`, CDN kaynakları |

### 2.3 Varlık envanteri

| Varlık | Kritiklik | Not |
|---|---|---|
| `pozitron.db` (müşteri PII, siparişler) | **Çok yüksek** | 101 kullanıcı, 121 sipariş, 69 şifre sıfırlama kaydı |
| Yönetici API'si (129 route) | **Çok yüksek** | Ürün silme, fiyat, kupon, ajan kontrolü |
| iyzico entegrasyonu | Yüksek | Kart verisi sunucuda yok (iyi) |
| SMTP kimlik bilgileri | Yüksek | E-posta gönderme yetkisi |
| Instagram/Reddit oturumları | Orta | Hesap ele geçirme |
| GitHub deposu | Yüksek | Tüm sırlar geçmişte |
| Sunucu (systemd, root yok) | Yüksek | `www-data` olarak çalışıyor (iyi) |

---

## 3. Kritik Bulgular (detaylı)

### SEC-01 — Yönetici API anahtarı herkese açık istemci kodunda · CVSS 9,8

**Konum:**
- `api.js:102` ve `api.js:172` — `localStorage.getItem('pozitron_admin_key') || 'pzt_adm_sec_…'`
- `admin.html:1644`, `:3284`, `:3592`, `:4430` — aynı sabit
- `server.py:37` — aynı değer varsayılan olarak
- `render.yaml:24-25` — repoda açıkça yazılı
- `scripts/setup_hetzner.sh:81` — kurulum betiği aynı değeri yazıyor

**Kanıt (canlı, salt-okunur):**

```
GET /api/admin/orders                     (anahtarsız) → 401
GET /api/admin/orders  X-Admin-Key: …     (herkese açık anahtar) → 200
  → 67.833 bayt: müşteri adı, e-posta, telefon, teslimat adresi, sipariş tutarı
```

Anahtar, `https://pozitronmarket.com/api.js` dosyasını indiren **herkes** tarafından görülebilir. Yani kimlik doğrulama, "gizli olmayan bir gizli anahtar"a dayanmaktadır.

**Etki:**
- Tüm müşteri PII'si (KVKK kapsamında kişisel veri) ifşa.
- `/api/admin/products` (DELETE), `/api/admin/coupons/create`, `/api/supervisor/run`, `/api/admin/sync-cloud-market`, `/api/media/fix` gibi **yazma** uçları da aynı anahtarla erişilebilir → veri bütünlüğü ve ticari kontrol kaybı.
- Saldırgan ürün silebilir, fiyat değiştirebilir, %100 indirimli kupon üretebilir, ajanları tetikleyebilir, `git pull` çalıştırabilir.

**Düzeltme (acil):**

1. **Anahtarı döndürün** ve `server.py`'de varsayılanı kaldırın:
```python
ADMIN_API_KEY = os.environ.get('ADMIN_API_KEY')
if not ADMIN_API_KEY:
    raise RuntimeError('ADMIN_API_KEY tanımlı değil — üretim ortamı başlatılamaz.')
```
2. **İstemciden tamamen kaldırın.** Yönetici paneli, Google ile giriş sonrası sunucudan alınan **kısa ömürlü Bearer token** ile çalışsın. API anahtarı diye bir kavram istemcide olmamalı.
3. `render.yaml` ve `setup_hetzner.sh` içindeki sabitleri silin; bunun yerine "ortam değişkeni sağlanmalı" hatası verin.
4. Anahtar rotasyonu sonrası `admin.html`'in çalışmaya devam ettiğini doğrulayın (token akışı).

**Doğrulama:**
```bash
curl -s https://pozitronmarket.com/api.js | grep -c "pzt_adm_"   # 0 olmalı
curl -s -o /dev/null -w '%{http_code}\n' -H 'X-Admin-Key: <yeni>' \
     https://api.pozitronmarket.com/api/admin/orders             # 200 (yalnızca yeni anahtar)
```

---

### SEC-02 — `/api/auth/google` kanıtsız yönetici oturumu veriyor · CVSS 9,8

**Konum:** `server.py:4115-4194`

```python
email = data.get('email', '').strip().lower()
credential = data.get('credential', '').strip()      # ← opsiyonel
...
verified_by_google = False
if credential:
    ... # doğrulama yalnızca credential VARSA yapılıyor
...
cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
user = cursor.fetchone()
...
token = create_auth_token(user_dict)                  # ← mevcut kullanıcı için token
```

`credential` gönderilmezse doğrulama tamamen atlanır; ancak kod, veritabanında o e-posta ile kayıtlı kullanıcıyı bulup **onun rolüyle** token üretir. Yönetici e-postaları ayrıca `app.js:2180-2187` ve `server.py:4143-4150` içinde **herkese açık** olarak listelenmiştir.

**Kanıt (canlı):**

```
POST /api/auth/google  {"email":"<veritabanındaki bir yönetici>"}
→ 200 {"success": true, "user": {"role": "admin"}, "token": "pztr.eyJ1aWQiOi…"}

GET  /api/admin/users    Authorization: Bearer <token>  → 200 (7.319 bayt, kullanıcı listesi)
GET  /api/admin/orders   Authorization: Bearer <token>  → 200 (67.833 bayt)
GET  /api/admin/coupons  Authorization: Bearer <token>  → 200
GET  /api/admin/stats    Authorization: Bearer <token>  → 200
```

Bu, **tek HTTP isteğiyle mağazanın tam ele geçirilmesi** demektir. Parola, 2FA veya Google hesabı gerekmez.

**Etki:** Yönetici yetkisiyle her işlem: ürün/fiyat/stok değiştirme, kupon üretme, diğer kullanıcıları listeleme, ajanları ve `git pull`'u tetikleme, medya değiştirme. Ayrıca herhangi bir müşteri hesabı için de token üretilebildiği için **tüm hesapların ele geçirilmesi** mümkündür.

**Düzeltme:**

```python
# Google ID token'ı ZORUNLU kıl ve doğrula
credential = data.get('credential')
if not credential:
    self.send_json(401, {"error": "Google kimlik doğrulaması gerekli."}); return

info = google_id_token_info(credential)          # tokeninfo veya yerel JWKS doğrulaması
if not info:
    self.send_json(401, {"error": "Geçersiz kimlik doğrulaması."}); return
if info['aud'] != os.environ['GOOGLE_CLIENT_ID']:
    self.send_json(401, {"error": "Geçersiz audience."}); return
if info['iss'] not in ('https://accounts.google.com', 'accounts.google.com'):
    self.send_json(401, {"error": "Geçersiz issuer."}); return
if not info.get('email_verified'):
    self.send_json(401, {"error": "E-posta doğrulanmamış."}); return

email = info['email'].lower()                    # e-postayı İSTEMCİDEN DEĞİL token'dan al
```

> **Kritik ayrıntı:** E-posta adresi istek gövdesinden değil, **doğrulanmış token'ın içinden** alınmalıdır. Mevcut kod, token'daki e-postayı gövdedeki e-posta ile karşılaştırıyor; gövde e-postası token'daki ile aynıysa geçiyor — ancak `credential` hiç gönderilmezse bu kontrol hiç çalışmıyor.

**Ek öneri:** Yönetici listesini koddan çıkarıp veritabanında `role` alanına taşıyın. E-posta beyaz listesi herkese açık olduğu için hedef listesi sağlar.

---

### SEC-03 — `/api/orders` kimlik doğrulaması olmadan tüm siparişleri döndürüyor · CVSS 7,5

**Konum:** `server.py:2936-2955`

```python
if path == '/api/orders':
    user_id = query.get('user_id', [''])[0].strip()
    email = query.get('email', [''])[0].strip().lower()
    if user_id or email:
        cursor.execute("SELECT * FROM orders WHERE (user_id = ? …) OR (LOWER(customer_email) = ? …)")
    else:
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50")   # ← TÜM SİPARİŞLER
```

Kimlik doğrulama yok; parametre verilmezse son 50 sipariş **tam PII** ile dönüyor.

**Kanıt (canlı):** `GET /api/orders` → `200`, `67.833` bayt. İçerik: `customer_name`, `customer_email`, `customer_phone`, `shipping_address`, `city`, `items_json`, tutarlar.

**Etki:** KVKK kapsamında kişisel veri ihlali; hedefli dolandırıcılık (sipariş numarası + telefon ile "kargonuz takıldı" aramaları) için hazır veri seti.

**Düzeltme:** Uç noktayı kaldırın veya yalnızca kimliği doğrulanmış kullanıcının kendi siparişlerini döndürün:

```python
if path == '/api/orders':
    me = self.get_current_user()
    if not me:
        self.send_json(401, {"error": "Giriş gerekli."}); return
    if me['role'] == 'admin':
        rows = cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 200").fetchall()
    else:
        rows = cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC",
                              (me['uid'],)).fetchall()
```

**Doğrulama:** `curl -s -o /dev/null -w '%{http_code}' https://api.pozitronmarket.com/api/orders` → `401` olmalı.

---

### SEC-04 — Sipariş numarası ile PII ifşası (IDOR / numaralandırma) · CVSS 7,5

**Konum:** `server.py:2957-2974` — `/api/orders/<order_number>` kimlik doğrulaması yok.

Sipariş numarası formatı `PZT-YYYYMMDD-NNNN` (`server.py:4544`: `random.randint(1000, 9999)`) — yani **günde 9.000 olasılık**, tahmin edilebilir. Aynı uç nokta `/api/orders/user/<user_id>` (satır 2976) ile de herhangi bir `user_id` için sipariş listesi veriyor.

**Kanıt:** `/api/orders/PZT-20261020-79545272` → `200`, tam müşteri kaydı.

**Etki:** Tüm sipariş geçmişinin numaralandırılması; sipariş sahipliği doğrulanmadığı için "sipariş takibi" özelliği üzerinden veri sızıntısı.

**Düzeltme:**
- Sipariş numarasını **tahmin edilemez** yapın: `secrets.token_urlsafe(12)` veya `PZT-<uuid4>`.
- Uç noktaya sahiplik kontrolü ekleyin: `order.user_id == me['uid']` veya `order.customer_email == me['email']` veya `me['role'] == 'admin'`.
- Sipariş takibi için ayrı, HMAC imzalı, süreli bir "takip bağlantısı" üretin.

---

### SEC-05 — Yorumlarda kalıcı XSS ve sahte "doğrulanmış alışveriş" · CVSS 8,2

**Sunucu — `server.py:4693-4745`:**

```python
user_name = data.get('user_name', 'Anonymous Pilot')   # doğrulama yok
comment   = data.get('comment', '').strip()            # HTML filtresi yok
...
INSERT INTO reviews (… verified_purchase …) VALUES (…, 1, ?)   # ← her zaman 1
```

Kimlik doğrulama yok, HTML temizliği yok, `verified_purchase` sabit `1`.

**İstemci — `app.js:6765`:**

```javascript
<p class="comment-text">"${r.comment}"</p>
```

`escapeHTML` fonksiyonu mevcut (`app.js:51`) ama burada kullanılmıyor. `r.userName` de satır 6755/6758'de kaçışsız basılıyor.

**Kanıt (yerel, temizlendi):**

```
POST /api/reviews {"user_name":"<b>XSS</b>","comment":"<img src=x onerror=alert(1)> test", …}
→ 201 {"success": true …}
DB: user_name="<b>XSS</b>", comment="<img src=x onerror=alert(1)> test", verified_purchase=1
```

**Etki:**
- **Kalıcı XSS**: yorum onayı olmadığı için yük herkese ulaşır. Oturum token'ı `localStorage`'da tutulduğu için (`SEC-11`) tek bir zararlı yorum **tüm ziyaretçilerin token'ını çalabilir**, yönetici paneli ziyaret edildiğinde yönetici oturumu da ele geçer.
- **Sahte sosyal kanıt**: her yorum "Doğrulanmış Alışveriş" olarak işaretlenir — ticari mevzuat riski.
- **Sahte puan**: `rating` 1–5 arası kabul edildiği için ürün ortalaması manipüle edilebilir.

**Düzeltme:**

```python
import bleach  # veya html.escape

comment = bleach.clean(data.get('comment','').strip(), tags=[], strip=True)[:2000]
user_name = html.escape(data.get('user_name','').strip()[:60])

# Doğrulanmış alışveriş yalnızca gerçek eşleşme ile
verified = 0
if me:
    row = cursor.execute(
        "SELECT 1 FROM orders WHERE user_id=? AND items_json LIKE ? AND payment_status='PAID' LIMIT 1",
        (me['uid'], f'%"{real_prod_id}"%')).fetchone()
    verified = 1 if row else 0
```

```javascript
// İstemci
<p class="comment-text">"${this.escapeHTML(r.comment)}"</p>
```

Ek olarak: yorum gönderiminde oturum zorunlu olsun veya en azından rate limit + moderasyon kuyruğu eklensin (`reviews.deleted_at` alanı zaten var).

---

### SEC-06 — Gömülü `SECRET_KEY` ile oturum token'ı sahteleme · CVSS 9,1

**Konum:** `server.py:36`

```python
SECRET_KEY = os.environ.get('SECRET_KEY', '<kodda açık sabit değer>')  # ← varsayılan gizli değil
```

`scripts/setup_hetzner.sh:80` de aynı değeri yazıyor; yani üretim ortamında ortam değişkeni "ayarlanmış" görünse bile değer **herkese açık**.

**Etki:** Token formatı `pztr.<base64(payload)>.<hmac>` ve payload'da `role` alanı var (`server.py:62-71`). Anahtarı bilen biri **herhangi bir kullanıcı için, herhangi bir rolde, istediği süreyle** geçerli token üretebilir. İmza doğrulaması `compare_digest` ile yapıldığı için teknik olarak kusursuz çalışır — sorun anahtarın gizli olmamasıdır.

**Düzeltme:**
```python
SECRET_KEY = os.environ['SECRET_KEY']          # zorunlu, varsayılan yok
if len(SECRET_KEY) < 32:
    raise RuntimeError('SECRET_KEY en az 32 bayt olmalı')
```
- `secrets.token_urlsafe(48)` ile yeni anahtar üretin.
- **Anahtar rotasyonu tüm oturumları geçersiz kılar** — bu istenen davranıştır; kullanıcılar yeniden giriş yapar.
- İdeali: `kid` alanlı anahtar seti (eski anahtarla doğrulama, yeniyle imzalama) ile kesintisiz rotasyon.

---

### SEC-07 — SMTP uygulama şifresi repoda ve git geçmişinde · CVSS 7,5

**Konum:**
- `server.py:112` — `os.environ.get('SMTP_PASSWORD', 'fugtmwx…')` (Gmail uygulama şifresi görünümünde)
- `scripts/setup_hetzner.sh:88` — aynı değer plaintext
- Git geçmişi: `79c3b6a5 Update default Gmail SMTP app password to …`
- `server.py:265` — Google Apps Script relay URL'si varsayılan olarak gömülü (`AKfycbw…`) → yetkisiz kullanım

**Etki:** Saldırgan kurumsal e-posta hesabından **marka adına** e-posta gönderebilir: şifre sıfırlama, sahte sipariş onayı, kimlik avı. SPF/DKIM marka itibarı zarar görür ve alan adı spam listelerine girer. GAS relay URL'si ise müşteri verisini üçüncü taraf bir script'e taşır.

**Düzeltme:**
1. Gmail'de uygulama şifresini **derhal iptal edin**.
2. Yeni şifreyi yalnızca `/etc/pozitron/pozitron.env` (600, root) içinde tutun.
3. Varsayılan değerleri koddan silin: `os.environ['SMTP_PASSWORD']` (yoksa e-posta gönderilmesin, sessizce başarısız olmasın — log'a uyarı yazsın).
4. GAS relay'i kaldırın veya anahtarını döndürün.
5. **Git geçmişini temizleyin** (`git filter-repo --replace-text`) ve tüm sırları döndürün; geçmişteki sır "silinmiş" sayılmaz.

---

### SEC-08 — Adres uçlarında IDOR: yetkisiz okuma, yazma ve silme · CVSS 8,1

**Üç ayrı sorun:**

| Uç | Konum | Sorun |
|---|---|---|
| `GET /api/user/addresses?user_id=<herhangi>` | `server.py:2919-2933` | `user_id` istemciden; sahiplik kontrolü yok |
| `POST /api/user/addresses` | `server.py:4340+` | `user_id` gövdeden; başka kullanıcının adresine yazılabilir |
| `DELETE /api/user/addresses/<id>` | `server.py:642-651` | **`require_admin()` çağrılmadan önce** çalışıyor; kimlik doğrulaması yok |

```python
def do_DELETE(self):
    if path.startswith('/api/'):
        addr_del_match = re.match(r'^/api/user/addresses/(.+)$', path)
        if addr_del_match:
            cur.execute("DELETE FROM user_addresses WHERE id = ?", (addr_id,))   # ← korumasız
```

**Ek hata:** `server.py:2922` `self.get_authenticated_user()` çağırıyor — bu metot **tanımlı değil**. Sonuç: token ile çağrıldığında `500 Internal Server Error` (canlıda doğrulandı). Yani mevcut "kimlik doğrulamalı" yol da çalışmıyor.

**Etki:** Müşteri adres defterlerinin ifşası ve tahribi; sipariş adresinin saldırganın adresine çevrilmesi (kargo hırsızlığı) senaryosu.

**Düzeltme:** Ortak bir yardımcı ekleyin ve **her** kullanıcı-verisi ucunda kullanın:

```python
def owned_or_admin(self, owner_user_id):
    me = self.get_current_user()
    if not me:
        self.send_json(401, {"error": "Giriş gerekli."}); return None
    if me['role'] != 'admin' and str(me['uid']) != str(owner_user_id):
        self.send_json(403, {"error": "Yetkisiz."}); return None
    return me
```
`DELETE` işlemini de `require_admin()`/sahiplik kontrolünün **arkasına** taşıyın.

---

## 4. Yüksek Bulgular

### SEC-09 — Şifreler tek tuzlu SHA-256 ile saklanıyor · CVSS 7,2

**Konum:** `database.py:814-816`

```python
def hash_password(password: str) -> str:
    salt = "pozitron_fpv_salt_2026"          # herkes için aynı, kodda sabit
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
```

- Tuz **global ve sabit** → rainbow table ile toplu kırma.
- SHA-256 **hızlı** bir fonksiyon → GPU ile saniyede milyarlarca deneme.
- İstemci tarafında da aynı mantık var (`app.js:62-68`) ve `localStorage`'da saklanıyor.

**Etki:** DB sızıntısında (SEC-01 ile birlikte gerçekçi) tüm şifreler kısa sürede açığa çıkar; kullanıcılar aynı şifreyi başka sitelerde kullandığı için yaygın hesap ele geçirme.

**Düzeltme:** `argon2-cffi` veya `passlib[bcrypt]`:

```python
from argon2 import PasswordHasher
_ph = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

def hash_password(p): return _ph.hash(p)
def verify_password(h, p):
    try: return _ph.verify(h, p)
    except Exception: return False
```
- Mevcut hash'ler için **giriş anında yükseltme** (rehash on login).
- İstemci tarafı hash'lemeyi kaldırın: parola TLS üzerinden gitsin, sunucuda hash'lensin.

### SEC-10 — Şifre sıfırlama kodunda deneme sınırı yok · CVSS 6,5

**Konum:** `server.py:4234-4337`. 6 haneli kod (`random.randint` — kriptografik değil), 30 dakika geçerli, **deneme sayısı sınırsız**, IP/e-posta rate limit'i yok.

**Etki:** 1.000.000 olasılık; otomatik denemeyle dakikalar içinde kırılabilir → hesap ele geçirme. `random` yerine `secrets` kullanılmalı.

**Düzeltme:**
```python
code = f"{secrets.randbelow(1_000_000):06d}"
# password_resets tablosuna attempts INTEGER DEFAULT 0 ekleyin
if row['attempts'] >= 5:
    self.send_json(429, {"error": "Çok fazla deneme. Yeni kod isteyin."}); return
```
Ayrıca kod **loglara yazılmamalı** (`server.py:4274` plaintext basıyor) ve kod gönderimi e-posta başına saatte 3 ile sınırlanmalı.

### SEC-11 — 365 günlük, iptal edilemeyen oturum + `localStorage` · CVSS 6,5

**Konum:** `server.py:67` (`exp = now + 365*86400`), `app.js:2272-2274`.

- Token `localStorage`'da → herhangi bir XSS (SEC-05) doğrudan token hırsızlığına dönüşür.
- Token ayrıca **`pozitron_user_backup` çerezinde** tam kullanıcı nesnesiyle birlikte 1 yıl saklanıyor; `HttpOnly` yok, `Secure` yok, sadece `SameSite=Lax`.
- Sunucu tarafında **iptal listesi yok**; çıkış yalnızca istemci tarafında siliyor. Çalınan token 1 yıl geçerli.

**Düzeltme:**
- Erişim token'ı 15–60 dakika, yenileme token'ı 7–30 gün; yenileme token'ı `HttpOnly; Secure; SameSite=Strict` çerezde.
- Sunucuda `sessions` tablosu + `jti` ile iptal.
- `localStorage`'da token tutmayı bırakın.
- Çıkışta sunucuya `POST /api/auth/logout` ile token'ı iptal ettirin.

### SEC-12 — CORS `*` ve geniş başlık izinleri · CVSS 5,3

**Konum:** `server.py:617-620`, `630-635`

```python
self.send_header('Access-Control-Allow-Origin', '*')
self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Admin-Key')
```

Herhangi bir web sitesi, ziyaretçinin tarayıcısından API'ye istek atıp yanıtı okuyabilir (`Authorization` başlığı izinli olduğu için token'lı istekler de dahil). SEC-01 ile birleşince etkisi artar.

**Düzeltme:** Beyaz liste: `https://pozitronmarket.com`, `https://www.pozitronmarket.com`, yerel geliştirme. `ACAO` değerini istek `Origin` başlığına göre dinamik üretin ve `Vary: Origin` ekleyin.

### SEC-13 — Güvenlik başlıkları eksik (CSP, HSTS, Referrer-Policy) · CVSS 4,3

Nginx'te yalnızca `X-Content-Type-Options` ve `X-Frame-Options` var; uygulamada hiçbiri yok. **CSP yok** → XSS'in etkisi maksimum. **HSTS yok** → SSL stripping mümkün.

**Önerilen başlıklar:**
```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' https://accounts.google.com https://www.googletagmanager.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://api.pozitronmarket.com https://www.google-analytics.com; frame-src https://accounts.google.com; frame-ancestors 'self'; base-uri 'self'; object-src 'none'" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
```
> Not: `'unsafe-inline'` başlangıç için gerekli (sayfa içi script'ler var); zamanla nonce/hash'e geçilmeli. Öncelik: `frame-ancestors`, `object-src 'none'`, `base-uri 'self'`.

### SEC-14 — 500 yanıtlarında iç hata mesajı sızıntısı · CVSS 5,3

**Konum:** `server.py:658`, `:743`, `:1298` — `self.send_json(500, {"error": str(e)})`.

**Kanıt:** `GET /api/user/addresses` (Bearer ile) → `{"error": "'PozitronRequestHandler' object has no attribute 'get_authenticated_user'"}` — sınıf adı ve iç API ifşası.

**Düzeltme:** İstemciye genel mesaj + `request_id`; ayrıntı yalnızca sunucu logunda.

### SEC-15 — İstek gövdesinde boyut sınırı yok · CVSS 5,3

**Konum:** `server.py:1286` — `content_length = int(self.headers.get('Content-Length', 0))` ardından `self.rfile.read(content_length)`. Yalnızca `/api/upload-3d` yolunda 30 MB kontrolü var; diğer tüm `/api/*` POST'larda sınırsız.

**Etki:** Tek bir istekte GB'larca veri gönderilerek bellek tükenmesi; `ThreadingHTTPServer` her istek için thread açtığı için thread tükenmesi.

**Düzeltme:** Genel limit (ör. 1 MB) + `MAX_CONTENT_LENGTH` kontrolü; yükleme uçları için ayrı 30 MB. Nginx'te `client_max_body_size 32m` (şu an 100M).

### SEC-16 — `admin.html` yalnızca istemci tarafı kontrolle korunuyor · CVSS 7,5

`admin.html` GitHub Pages'te herkese açık olarak yayınlanıyor (`.gitignore`'da değil, `git ls-files`'ta). Erişim kontrolü tamamen tarayıcıdaki `isUserAdmin()` fonksiyonuna bağlı; ayrıca **localhost'ta otomatik admin girişi** yapıyor (`admin.html:1636-1641`).

**Etki:** Panelin tüm yapısı, API yolları, varsayılan anahtar ve iş mantığı kaynak olarak okunabilir; "güvenlik through obscurity" sıfır. (Gerçek yetki kontrolü API'de olmalı — ve SEC-01/SEC-02 nedeniyle şu an etkisiz.)

**Düzeltme:** Yönetim panelini ayrı, kimlik doğrulamalı bir alt alan adına taşıyın (`admin.pozitronmarket.com`), IP kısıtı/VPN + MFA ekleyin. Localhost otomatik girişini kaldırın.

### SEC-17 — Yerel geliştirici admin bypass'ı · CVSS 6,5

**Konum:** `server.py:542-547` ve `:4152-4159`

```python
if not is_cloud and not is_proxied and client_ip in ('127.0.0.1','localhost','::1') \
   and os.environ.get('POZITRON_ENV') != 'production':
    return {"uid":"local_dev", ..., "role":"admin"}
```

`is_cloud` kontrolü `PORT` ortam değişkenine bakıyor; `PORT` her yerde tanımlı olduğu için üretimde tesadüfen devre dışı kalıyor — ama bu **kırılgan bir varsayım**. `POZITRON_ENV` unutulursa ve istek proxy'den gelmiyorsa (ör. sunucuya doğrudan erişim, SSRF, yanlış Nginx yapılandırması) tam yönetici erişimi doğar.

**Düzeltme:** Bu bloğu tamamen kaldırın; geliştirme için ayrı bir `DEV_ADMIN_TOKEN` ortam değişkeni kullanın ve varsayılanı **kapalı** olsun.

### SEC-18 — E-posta bazlı giriş kilidi ile hesap kilitleme DoS'u · CVSS 5,3

**Konum:** `server.py:460-498` — kilit anahtarı **yalnızca e-posta**. Saldırgan herhangi bir kullanıcının e-postasını bilerek 3 hatalı denemeyle 30 dakika kilitleyebilir; döngüyle kalıcı hizmet engeli.

**Düzeltme:** Anahtar `(ip, email)` olsun; IP için ayrı geniş limit (ör. 20/15 dk) uygulansın; CAPTCHA eklensin; kilit süresi artan şekilde (exponential backoff) olsun.

### SEC-19 — Stok kontrolü ve atomiklik olmadan sipariş · CVSS 5,3

**Konum:** `server.py:4507-4518`

```python
new_stock = max(0, p_dict['stock'] - qty)          # stok 0 olsa da sipariş kabul
cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, prod_id))
```

Ayrıca `if not prod: continue` → geçersiz ürün sessizce atlanır, **boş sipariş** oluşabilir. Eşzamanlı iki istek aynı stoğu iki kez satabilir (yarış koşulu; `SELECT` ve `UPDATE` arasında kilit yok).

**Düzeltme:**
```python
cur = conn.execute("UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?", (qty, pid, qty))
if cur.rowcount != 1:
    conn.rollback(); return error("Yetersiz stok")
```
Tüm sipariş tek `BEGIN IMMEDIATE` transaction'ında; `items` boşsa reddet.

### SEC-20 — Güvenlik ve telemetri uçları herkese açık · CVSS 3,7

`GET /api/security/status` (4 KB), `GET /api/subagents/status`, `GET /api/telemetry/latest`, `GET /api/pipeline/graph` kimlik doğrulaması istemiyor. Bu uçlar savunma yapısını, ajan adlarını, endpoint listelerini ve altyapı topolojisini ifşa ediyor.

**Düzeltme:** `require_admin()` arkasına alın; vitrin için gereken minimal alanları ayrı bir `public` uçta toplayın.

### SEC-21 — Her 60 saniyede `git pull --rebase` ile denetimsiz dağıtım · CVSS 6,5

**Konum:** `server.py:404-427` ve `:3949-3981` — `subprocess.run(["git","pull","--rebase","origin","main"])`.

**Riskler:** (a) Depo veya GitHub hesabı ele geçirilirse **kod otomatik olarak üretime düşer**; (b) çakışma/bozuk commit çalışan servisi bozar; (c) `--rebase` yerel değişiklikleri gizlice birleştirir; (d) dizin `www-data` sahipliğinde olduğu için git işlemleri veri dizinlerine yazabilir.

**Düzeltme:** Otomatik pull'u kaldırın. Dağıtım: imzalı tag → CI'da test → artefakt → `systemctl restart`. En azından `git fetch` + manuel onay.

### SEC-22 — Reddit oturum çerezi yerel sunucuda statik olarak erişilebilir · CVSS 6,5

`data/reddit_cookies.json` (8,7 KB) içinde `token_v2` JWT'si var. Yerel sunucuda `GET /data/reddit_cookies.json` → **200** (canlıda 404, çünkü dosya orada yok). Sunucu `0.0.0.0:8000` dinlediği için aynı ağdaki herkes okuyabilir. `.gitignore` dosyayı koruyor (`*cookies*`) — olumlu — ancak statik sunucu beyaz listesi `.json` uzantısına izin veriyor.

**Düzeltme:** `data/` altındaki hassas dosyaları açıkça engelleyin (`reddit_cookies.json`, `instagram_interactions.json`), ya da daha iyisi: bu dosyaları web kökünün **dışına** taşıyın. Çerezi döndürün (Reddit oturumunu kapatın).

---

## 5. Orta ve Düşük Bulgular

### SEC-23 — Ödeme ve sipariş uçlarında idempotency yok · CVSS 4,3
`/api/payment/process` ve `/api/iyzico/initialize` aynı istekle iki kez çağrılırsa iki sipariş/iki ödeme oturumu oluşabilir. **Düzeltme:** `Idempotency-Key` başlığı + `orders.idempotency_key UNIQUE`.

### SEC-24 — Rate limit bellek içi ve tek süreçli · CVSS 3,7
`LOGIN_ATTEMPTS` sözlüğü süreç belleğinde; yeniden başlatmada sıfırlanır, çoklu worker'da paylaşılmaz, sınırsız büyür (bellek sızıntısı). **Düzeltme:** Redis veya SQLite tablosu + TTL.

### SEC-25 — Yönetici işlemleri için denetim kaydı yok · CVSS 4,3
`security_audit_logs` yalnızca ajan taramalarını tutuyor. Kimin hangi ürünü sildiği, kupon oluşturduğu veya fiyat değiştirdiği kaydedilmiyor. **Düzeltme:** `admin_audit_log(id, actor, action, target, before, after, ip, ua, ts)`; tüm yazma uçlarında zorunlu.

### SEC-26 — Para birimi parametresi ile tutar karışıklığı · CVSS 4,3
`/api/payment/process` istemciden `currency` alıyor (`server.py:4475`) ama tutarları her zaman hem TRY hem USD hesaplıyor; kupon doğrulamada `35.5` sabit kur, `settings`'te `34.5`. Sipariş kaydı karışık para birimi içerebilir. **Düzeltme:** Para birimini sunucu belirlesin (TRY), kur tek kaynaktan gelsin.

### SEC-27 — `/api/telemetry` kimlik doğrulamasız yazma · CVSS 3,7
`POST /api/telemetry` (ve `/bots`) gövdeyi doğrudan `telemetry_agent._save_to_db(data)`'ya veriyor. Sahte telemetri ile ajan kararları manipüle edilebilir; sınırsız gövde ile DB şişirilebilir. **Düzeltme:** Paylaşılan sır (HMAC) + şema doğrulama + boyut limiti.

### SEC-28 — Sunucu `0.0.0.0` dinliyor · CVSS 3,1
`server.py:5375` — `('0.0.0.0', p)`. Nginx arkasında olması gereken servis doğrudan erişilebilir. **Düzeltme:** `127.0.0.1`'e bağla; konteyner içinde açıkça `HOST` ortam değişkeni verin.

### SEC-29 — `robots.txt` hassas yolları listeliyor · CVSS 2,6
`Disallow: /admin`, `/bots` — bu, saldırgana hedef listesi verir (güvenlik değil, gizleme). Ayrıca `/api/security/status` gibi uçlar robots'ta değil ama erişilebilir. **Düzeltme:** Hassas panelleri kimlik doğrulamasıyla koruyun; `robots.txt`'i yalnızca SEO amaçlı kullanın.

---

## 6. Olumlu Kontroller (korunması gerekenler)

| Kontrol | Kanıt | Değerlendirme |
|---|---|---|
| Kart verisi sunucuya hiç girmiyor | `iyzico_checkout.py` hosted CheckoutForm | ✅ PCI DSS kapsamını daraltır |
| iyzico HMAC imza doğrulaması | `hmac.compare_digest` (`iyzico_checkout.py:65-67`) | ✅ Zamanlama saldırısına dayanıklı |
| Tutar/para birimi/sepet kimliği eşleştirme | `iyzico_checkout.py:257-261` | ✅ Çok iyi |
| `fraudStatus != 1` → `PAYMENT_REVIEW` | `iyzico_checkout.py:268-273` | ✅ Doğru davranış |
| Kaçırılan callback telafisi | `reconcile_pending()` 60 sn / 7 gün | ✅ Operasyonel olgunluk |
| Ödeme başlatmada hız sınırı | `allow_attempt` (5/dk/IP) | ✅ |
| Kupon indirimini sepete kenetleme | `compute_discount` + clamping | ✅ Negatif tutar imkânsız |
| Kupon çapraz kimlik kontrolü | `validate_coupon` + `make_user_key` | ✅ Gmail alias istismarı engelli |
| Kupon yarış koşulu koruması | `UNIQUE(coupon_code, user_key, order_id)` | ✅ DB seviyesinde |
| Path traversal koruması | `os.path.realpath` + prefix kontrolü | ✅ Canlıda 404 doğrulandı |
| Statik dosya uzantı beyaz listesi | `BLOCKED_STATIC_EXTENSIONS`, `ALLOWED_*` | ✅ `.db/.py/.env` engelli |
| Yükleme uzantı beyaz listesi + UUID | `handle_file_upload` | ✅ |
| Yükleme boyut sınırı | 30 MB | ✅ (yalnızca bu uçta) |
| Parametreli SQL | Yaygın `?` kullanımı | ✅ (dinamik `clause` hariç) |
| WAL + `foreign_keys` + `busy_timeout` | `database.py:11-16` | ✅ |
| Honeypot yok ama ajan taraması var | `subagent_security.py` | 🟡 Kısmi değer |
| Servis `www-data` olarak çalışıyor | `pozitron.service` | ✅ root değil |

---

## 7. Saldırı Senaryoları (Kill Chain)

### Senaryo A — "Tek istekte mağaza ele geçirme" (3 dakika)

```
1. Saldırgan api.js'i indirir                     → yönetici anahtarını okur (SEC-01)
   VEYA app.js'ten yönetici e-postasını alır      → herkese açık liste
2. POST /api/auth/google {"email":"<admin>"}      → role=admin token (SEC-02)
3. GET /api/admin/orders                          → tüm PII (67 KB)
4. POST /api/admin/coupons/create {"discount_value":100,...}  → %100 kupon
5. DELETE /api/admin/products/<id>                → rakip/ürün tahribi
6. POST /api/supervisor/run                       → ajanları manipulate et
7. POST /api/admin/sync-cloud-market              → git pull tetikle (SEC-21)
```
**Tespit edilebilirlik:** Şu anda **sıfır** — yönetici işlem kaydı yok (SEC-25), anomali alarmı yok.

### Senaryo B — "Müşteri verisi toplama" (otomatik, saatler)

```
1. GET /api/orders (sayfalama parametresi olmadan son 50)
2. Sipariş numarası formatını öğren: PZT-YYYYMMDD-NNNN
3. Günlük 9.000 olasılığı paralel denenerek numaralandır
4. Toplanan ad/e-posta/telefon/adres ile kimlik avı kampanyası
5. "Kargonuz gümrükte takıldı, 49 TL ödeyin" → ödeme kartı hırsızlığı
```
**Etki:** KVKK ihlali + marka itibarı + tüketici zararı. Bildirim yükümlülüğü doğar.

### Senaryo C — "Zincirleme XSS ile yönetici oturumu" (yüksek etki)

```
1. POST /api/reviews ile <img onerror> yükü bırak (SEC-05) — onay yok, anında yayında
2. Ziyaretçiler token'larını kaybeder (localStorage, SEC-11)
3. Yönetici de yorumlara bakarsa → yönetici token'ı saldırgana gider
4. Token 365 gün geçerli, iptal edilemez → kalıcı arka kapı
```
**Not:** CSP olmadığı için (SEC-13) tarayıcı hiçbir engel koymaz.

---

## 8. Olay Müdahale Planı (IRC)

### 8.1 İlk 60 dakika — kontrol altına alma

```bash
# 1. Kanıtları koru (üzerine yazmadan önce)
sudo cp /var/www/pozitron/pozitron.db /root/incident-$(date +%F-%H%M).db
sudo journalctl -u pozitron --since "30 days ago" > /root/journal-$(date +%F).log
sudo cp /var/log/nginx/access.log /root/nginx-$(date +%F).log

# 2. Sırları döndür
export NEW_ADMIN_KEY=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
export NEW_SECRET_KEY=$(python3 -c "import secrets;print(secrets.token_urlsafe(48))")
sudo sed -i "s|^ADMIN_API_KEY=.*|ADMIN_API_KEY=$NEW_ADMIN_KEY|" /etc/pozitron/pozitron.env
sudo sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$NEW_SECRET_KEY|"       /etc/pozitron/pozitron.env
sudo systemctl restart pozitron

# 3. Gmail uygulama şifresini iptal et (Google Hesap > Güvenlik)
# 4. Google Apps Script relay'i devre dışı bırak / yeni URL üret
# 5. Reddit oturumunu kapat (token_v2'yi iptal et)

# 6. Kötüye kullanım izlerini ara
grep -c "X-Admin-Key" /root/nginx-*.log
grep -E "POST /api/auth/google|GET /api/admin/|DELETE /api/admin" /root/nginx-*.log | head -50
```

### 8.2 İlk 24 saat

- [ ] SEC-01…SEC-08 düzeltmelerini uygula ve doğrula.
- [ ] Tüm kullanıcı oturumlarını geçersiz kıl (SECRET_KEY rotasyonu bunu yapar).
- [ ] Etkilenen veri kapsamını belirle: hangi sipariş/kullanıcı kaydı erişildi?
- [ ] Yetkisiz oluşturulmuş kupon/ürün/sipariş var mı kontrol et.
- [ ] Yedeklerin bütünlüğünü doğrula (zararlı değişiklik var mı?).
- [ ] KVKK bildirimi için hukuk danışmanıyla değerlendirme başlat (72 saat).

### 8.3 İlk 7 gün

- [ ] Tüm bulguların yama-ve-doğrula döngüsü.
- [ ] Yönetici denetim kaydı (SEC-25) devreye alınsın.
- [ ] WAF/rate limit (Nginx `limit_req` veya Cloudflare).
- [ ] Yapılandırılmış log + alarm (5xx, 401/403 artışı, admin uç erişimi).
- [ ] Yedekleme otomasyonu + geri yükleme tatbikatı.
- [ ] Bağımlılık taraması (`pip-audit`, `npm audit`).

### 8.4 İlk 30 gün

- [ ] Yetkilendirme matrisinin tamamı gözden geçirilsin (her uç için sahiplik testi).
- [ ] Oturum mimarisi yenilensin (kısa token + yenileme + iptal).
- [ ] Argon2id geçişi tamamlansın.
- [ ] CSP raporlama modunda başlatılsın, sonra zorunlu kılın.
- [ ] Sızma testi (bağımsız) ve düzeltme doğrulaması.
- [ ] Sır yönetimi: Vault/Doppler veya en azından SOPS ile şifreli `.env`.

---

## 9. Uyumluluk Değerlendirmesi

### 9.1 KVKK (6698)

| Yükümlülük | Durum | Not |
|---|---|---|
| Aydınlatma metni | ✅ | `gizlilik-politikasi.html` mevcut ve kapsamlı |
| Veri güvenliği (Md. 12) | ❌ | Yetkisiz erişim mümkün; teknik-idari tedbir yetersiz |
| İhlal bildirimi (72 saat) | ⚠️ | Süreç tanımlı değil; olay müdahale planı yok |
| Çerez onayı | ❌ | GA4 + Google Ads, ilk yüklemede onay alınmadan çalışıyor (`index.html:8-15`) |
| Yurt dışına aktarım | ⚠️ | Google (Analytics/Ads/Fonts), iyzico, Meta; açık rıza/standart sözleşme durumu belirsiz |
| Veri minimizasyonu | ⚠️ | Sipariş sorgusunda tüm alanlar dönüyor; gereksiz PII |
| Saklama süresi | ⚠️ | Tanımlı değil; `password_resets` 69 kayıt süresiz |

**Aksiyon:** (1) Çerez onay banner'ı + Google Consent Mode v2; (2) ihlal bildirim prosedürü; (3) `data/` altındaki kişisel veriler için saklama politikası; (4) yurt dışı aktarım envanteri.

### 9.2 PCI DSS

- Kart verisi sunucuya hiç girmiyor → **SAQ A** kapsamı (hosted checkout). Bu doğru ve değerli.
- Ancak: yönetici anahtarı ele geçirilirse **ödeme tutarları** değiştirilebilir (ürün fiyatı üzerinden). Bu, dolaylı bütünlük riskidir.
- **Aksiyon:** Fiyat değişikliklerini denetim kaydına al, iyzico `paidPrice` ile DB tutarını her zaman karşılaştır (zaten yapılıyor ✅).

### 9.3 5651 sayılı Kanun (log saklama)

- Erişim logları Nginx'te; saklama süresi ve bütünlüğü tanımlı değil.
- **Aksiyon:** 2 yıl saklama, saat senkronizasyonu (NTP), log bütünlüğü (append-only/WORM).

### 9.4 6563 sayılı ETK (Elektronik Ticaret)

- Satıcı bilgisi, mesafeli sözleşme, ön bilgilendirme mevcut ✅
- ETBİS kaydı ve "teknik olarak korunması gereken bilgiler" için ek doğrulama önerilir.
- Ödeme yöntemi beyanı (PayTR "yakında" ama SSS'te "kullanabilirsiniz") **yanıltıcı** → düzeltilmeli (bkz. UX-40).

---

## 10. Düzeltme Yol Haritası (öncelikli)

| Süre | İş | Sorumlu | Doğrulama |
|---|---|---|---|
| **0–2 saat** | Anahtarları döndür, istemciden kaldır | Backend | `grep pzt_adm_ api.js` → 0 |
| **0–4 saat** | `/api/auth/google` credential zorunlu | Backend | Kanıtsız istek → 401 |
| **0–4 saat** | `/api/orders`, `/api/orders/<no>` yetkilendir | Backend | Anonim → 401 |
| **0–6 saat** | Adres uçlarında sahiplik + DELETE koruması | Backend | IDOR testi → 403 |
| **0–6 saat** | Yorumlarda `escape` + `verified_purchase` düzelt | Full-stack | XSS payload → metin |
| **24 saat** | SMTP/GAS/Reddit sırlarını döndür | DevOps | Eski şifre → auth hatası |
| **48 saat** | CSP/HSTS/CORS daraltma | DevOps | header denetimi |
| **48 saat** | Gövde boyutu limiti + `127.0.0.1` bağlama | Backend | 1 MB istek → 413 |
| **72 saat** | SHA-256 → Argon2id (girişte yükseltme) | Backend | Hash formatı `$argon2id$` |
| **1 hafta** | Oturum mimarisi (kısa token + yenileme + iptal) | Backend | 15 dk sonra 401 |
| **1 hafta** | Şifre sıfırlama deneme limiti + `secrets` | Backend | 6. deneme → 429 |
| **1 hafta** | Yönetici denetim kaydı | Backend | Her yazma loglanır |
| **1 hafta** | Otomatik `git pull` kaldır, CI tabanlı dağıtım | DevOps | Manuel onay |
| **2 hafta** | WAF + rate limit + alarm | DevOps | 429/alert testi |
| **30 gün** | Bağımsız sızma testi | Dış | Rapor |

---

## 11. Teknik Ekler

### Ek A — Yetkilendirme matrisi (mevcut durum)

| Uç | Olması gereken | Mevcut | Durum |
|---|---|---|---|
| `GET /api/products` | Herkes | Herkes | ✅ |
| `GET /api/orders` | Sahip / admin | **Herkes (tümü)** | ❌ |
| `GET /api/orders/<no>` | Sahip / admin | **Herkes** | ❌ |
| `GET /api/orders/user/<id>` | Sahip / admin | **Herkes** | ❌ |
| `GET /api/user/addresses` | Sahip / admin | **Herkes** | ❌ |
| `POST /api/user/addresses` | Sahip | **Herkes** | ❌ |
| `DELETE /api/user/addresses/<id>` | Sahip / admin | **Herkes** | ❌ |
| `POST /api/reviews` | Giriş + moderasyon | **Herkes, anında yayın** | ❌ |
| `POST /api/auth/google` | Google token | **Yalnızca e-posta** | ❌ |
| `GET /api/admin/*` | Admin | Admin (anahtar sızmış) | ⚠️ |
| `GET /api/security/status` | Admin | Herkes | ❌ |
| `GET /api/telemetry/latest` | Admin | Herkes | ❌ |
| `POST /api/telemetry` | Paylaşılan sır | Herkes | ❌ |
| `GET /api/settings` | Herkes (bank hariç) | Herkes | ✅ |
| `POST /api/payment/process` | Herkes (rate limit) | Herkes | ⚠️ |
| `POST /api/iyzico/initialize` | Herkes (rate limit) | 5/dk/IP | ✅ |

### Ek B — Döndürülmesi gereken sırlar

| Sır | Konum | Aciliyet | Etki |
|---|---|---|---|
| `ADMIN_API_KEY` | `server.py:37`, `api.js`, `admin.html` ×4, `render.yaml`, `setup_hetzner.sh` | **P0** | Tüm yönetici API'si |
| `SECRET_KEY` | `server.py:36`, `setup_hetzner.sh:80` | **P0** | Oturum sahteleme |
| SMTP uygulama şifresi | `server.py:112`, `setup_hetzner.sh:88`, git geçmişi | **P0** | Marka adına e-posta |
| GAS relay URL'si | `server.py:265`, `app.js:2518` | P1 | Veri sızıntısı |
| Reddit `token_v2` | `data/reddit_cookies.json` | P1 | Hesap ele geçirme |
| Instagram session/token | `data/instagram_config.json`, Chrome profili | P1 | Hesap ele geçirme |
| iyzico anahtarları | Yalnızca env (✅ doğru) | — | Korunuyor |
| Gemini API anahtarı | Env / `bots.html` formu | P2 | Maliyet |

### Ek C — Tespit komutları (düzeltme sonrası doğrulama)

```bash
# 1. İstemcide sır yok
curl -s https://pozitronmarket.com/api.js | grep -cE "pzt_adm_|ADMIN_API_KEY"   # 0

# 2. Kanıtsız Google girişi reddediliyor
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  https://api.pozitronmarket.com/api/auth/google \
  -H 'Content-Type: application/json' -d '{"email":"test@example.com"}'          # 401

# 3. Siparişler korumalı
curl -s -o /dev/null -w '%{http_code}\n' https://api.pozitronmarket.com/api/orders  # 401

# 4. Adres IDOR kapalı
curl -s -o /dev/null -w '%{http_code}\n' \
  "https://api.pozitronmarket.com/api/user/addresses?user_id=anything"           # 401/403

# 5. Güvenlik başlıkları
curl -sI https://pozitronmarket.com | grep -iE "content-security|strict-transport|referrer"  # 3 satır

# 6. Yorum XSS
curl -s -X POST https://api.pozitronmarket.com/api/reviews \
  -H 'Content-Type: application/json' \
  -d '{"user_name":"x","comment":"<script>alert(1)</script>","rating":5}' | \
  python3 -c "import sys,json;print(json.load(sys.stdin)['review']['comment'])"   # &lt;script&gt;

# 7. Gövde limiti
python3 -c "print('x'*2000000)" | curl -s -o /dev/null -w '%{http_code}\n' \
  -X POST --data-binary @- https://api.pozitronmarket.com/api/stock-alerts       # 413
```

### Ek D — Test edilmeyen alanlar (sonraki faz)

- Üçüncü taraf sağlayıcıların (iyzico, Google, Meta) kendi güvenliği
- Sosyal mühendislik / kimlik avı simülasyonu
- DDoS dayanıklılığı ve yük testi
- Fiziksel/sunucu düzeyi erişim
- Kriptografik protokol derinliği (TLS yapılandırması SSL Labs ile ayrıca ölçülmeli)
- Mobil uygulama (yok)
- Tedarik zinciri (npm/pip paket kökeni) — `npm audit`/`pip-audit` önerilir

---

## 12. Sonuç

Platformun **ödeme ve kupon mühendisliği**, benzer ölçekteki Türk e-ticaret sitelerinin çok üzerinde bir olgunlukta. Ancak **kimlik ve yetki katmanı**, bu iyi mühendisliği tamamen etkisiz bırakan düzeyde zayıf.

Kritik bulguların ortak özelliği şudur: **hepsi "kolay" hatalar değil, "unutulmuş" hatalardır.** Geliştirici, iyzico'yu doğru yapmış; ama `/api/orders`'a kimlik kontrolü eklemeyi atlamış. Kupon yarış koşulunu düşünmüş; ama yorumlarda `escapeHTML` çağırmayı atlamış. Varsayılan değerlere anahtar koymuş; ama bu değerlerin herkese açık olduğunu hesaba katmamış.

Bu nedenle düzeltme pahalı değil. **Bölüm 8.1'deki 6 komut ve Bölüm 10'daki ilk 6 satır**, sistemi birkaç saat içinde "savunulabilir" hale getirir. Asıl maliyet, düzeltmenin **yapılmaması** durumunda ortaya çıkacak KVKK yaptırımı, müşteri kaybı ve marka hasarıdır.

> **Son uyarı:** SEC-01, SEC-02 ve SEC-03 birlikte, sistemin şu anda **halka açık bir veri tabanı** gibi davrandığı anlamına gelir. Bu raporun okunmasından sonraki ilk iş, anahtar rotasyonu olmalıdır.

---

*Bu rapor, 1 Kasım 2026 tarihinde yapılan gri kutu denetiminin sonucudur. Tüm canlı testler salt-okunur niteliktedir; hiçbir veri kopyalanmamış veya saklanmamıştır. Rapor gizlidir ve yalnızca yetkili personelle paylaşılmalıdır.*
