# Pozitron Market — Kullanıcı Deneyimi (UX) Raporu

**Rapor No:** PZTR-UX-2026-11-01
**Tarih:** 1 Kasım 2026
**Sürüm:** 1.0 (Final)
**Kapsam:** `pozitronmarket.com` ana sayfa, ürün sayfaları, sepet, ödeme, hesap akışları, 3D Baskı Studio, Drone Toplama Sihirbazı, rehber
**Yöntem:** Sezgisel değerlendirme (Nielsen 10), bilişsel yürüyüş, WCAG 2.2 AA denetimi, kod tabanlı akış analizi, performans ölçümü
**Gizlilik:** Dahili — Gizli

---

## 1. Yönetici Özeti

Site, **görsel olarak profesyonel ve teknik olarak iddialı** bir FPV donanım mağazasıdır. Tasarım sistemi tutarlı, tipografi özenli, ürün kartları bilgi yoğun ve rakiplerin çoğundan daha "mühendis dostu"dur. Ödeme sayfasında iyzico hosted checkout'a geçilmesi, kargo eşiği göstergesi (ücretsiz kargo çubuğu), stok uyarısı, WhatsApp sipariş hattı ve drone uyumluluk sihirbazı gibi öğeler **gerçek kullanıcı ihtiyaçlarına** cevap veren doğru kararlardır.

Ancak deneyim, **satın alma anında tamamen kırılmaktadır**. Bunun nedeni tasarım değil, sistemin kullanıcıya verdiği üç yanlış sinyaldir:

1. **"Her şey tükendi" sinyali.** 509 ürünün 508'i stok dışı. Kullanıcı ana sayfaya gelir, 24 ürün kartının hepsinde "Tükendi" görür ve siteyi "ölü mağaza" olarak terk eder.
2. **"Bu ürün gerçekten bu mu?" sinyali.** 103 ürün aynı fotoğrafı, 209 ürün jenerik görsel kullanıyor. Teknik donanım alıcısı görsele değil modele bakar; ama jenerik görsel yine de "bu site özensiz" algısı yaratır.
3. **"Bildirim oluşturdum, haber gelecek" sinyali.** Stok uyarısı formu "e-posta ve WhatsApp ile ilk siz haberdar olun" diyor; oysa sistemde **hiçbir bildirim gönderilmiyor**. Bu, geri dönüşü olmayan güven kaybıdır.

Bunlara ek olarak ödeme adımında **sipariş özeti (sepet satırları) hiç gösterilmiyor**; kullanıcı yalnızca toplam tutarı görerek ödemeye geçiyor. Bu, e-ticarette dönüşümü en çok düşüren tek tek tasarım hatasıdır.

**Genel UX skoru: 5,0 / 10**

| Alan | Puan | Not |
|---|---:|---|
| Görsel tasarım & marka | 8,0 | Tutarlı, sade, güvenilir |
| Bilgi mimarisi & navigasyon | 6,5 | Kategori çubuğu iyi; arama zayıf |
| Ürün keşfi & listeleme | 5,5 | Filtreler var, ama stok nedeniyle işlevsiz |
| Ürün detay sayfası (PDP) | 6,5 | Bilgi zengin, tekrar eden bileşenler var |
| Sepet | 7,0 | Ücretsiz kargo çubuğu iyi |
| **Ödeme** | **3,0** | **Sipariş özeti yok, kupon yok, güven metni zayıf** |
| Hesap & sipariş takibi | 3,5 | Siparişler cihaza bağlı, giriş zorunlu değil |
| Erişilebilirlik (WCAG AA) | 4,0 | Odak yönetimi ve etiketleme eksik |
| Mobil deneyim | 5,5 | Responsive ama ağır ve dokunma hedefleri küçük |
| Performans algısı | 4,0 | 3 MB ilk yükleme |
| Güven & şeffaflık | 5,0 | İyi niyet var, yerine getirilmeyen vaatler var |

### En kritik 8 UX bulgusu

| # | Bulgu | Kullanıcı etkisi | Öncelik |
|---|---|---|---|
| UX-01 | Ödeme adımında sipariş özeti (ürün satırları) yok | "Ne için ödüyorum?" → terk | **P0** |
| UX-02 | Stok uyarısı hiçbir bildirim göndermiyor | Sessiz vaat ihlali → güven kaybı | **P0** |
| UX-03 | %99,8 ürün stok dışı, "Sepete Ekle" hiç görünmüyor | Site "ölü" algısı → hemen çıkış | **P0** |
| UX-04 | Kupon kodu yalnızca sepet çekmecesinde; ödemede yok; üstelik giriş zorunlu | Kuponunu kullanamayan kullanıcı terk eder | **P1** |
| UX-05 | Sipariş geçmişi yalnızca tarayıcı `localStorage`'ında | Cihaz değişince kaybolur; "siparişim nerede?" | **P1** |
| UX-06 | Arama önerileri klavye ile gezilemiyor, ekran okuyucuya kapalı | Erişilebilirlik + güç kullanıcı kaybı | **P1** |
| UX-07 | Odak tuzağı (focus trap) ve odak geri dönüşü yok | Modal içinde klavye tuzağı | **P1** |
| UX-08 | Ödeme metni "test kartı ile anında siparişi onaylayın" diyor | Güven kaybı / mevzuat riski | **P1** |

---

## 2. Kullanıcı Personaları

| Persona | Profil | Birincil ihtiyaç | Sitedeki kritik temas noktası |
|---|---|---|---|
| **"Yarışçı Yasin"** (28) | Aktif FPV pilotu, 5" freestyle, hızlı karar verir | Doğru KV/ESC uyumu, stokta olan parça, hızlı kargo | Filtreler, PDP teknik tablo, uyumluluk sihirbazı |
| **"Yeni Başlayan Elif"** (22) | İlk drone'unu topluyor, terminoloji bilmiyor | Rehberlik, "hangi parça hangisiyle uyumlu", bütçe | Drone Toplama Sihirbazı, rehber, SSS |
| **"Atölye Sahibi Murat"** (35) | Ticari UAV/robotik, sipariş verir, fatura ister | Kurumsal fatura, VKN, tekrar sipariş, toplu alım | Checkout fatura bölümü, hesap, sipariş geçmişi |
| **"Meraklı Ziyaretçi Deniz"** (19) | Fiyat araştırıyor, satın almayabilir | Ürün bilgisi, fiyat karşılaştırma | PDP, kategori listesi, WhatsApp |
| **"3D Üretici Can"** (26) | TPU kamera tutucu bastırmak istiyor | STL yükleme, malzeme/gramaj/fiyat şeffaflığı | 3D Baskı Studio |

**Kritik gözlem:** Beş personanın **beşi de** ilk 30 saniyede aynı duvara çarpıyor — "Tükendi". Bu yüzden persona bazlı kişiselleştirmeden önce stok sorununun çözülmesi gerekir.

---

## 3. Kullanıcı Yolculuğu Haritası ve Duygu Eğrisi

```
AŞAMA        Keşif        Arama        PDP          Sepet       Ödeme       Sonrası
             ─────        ─────        ───          ─────       ─────       ───────
ADIM         Ana sayfa →  Arama/filtre → Ürün incele → Sepete at → Bilgi+ödeme → Sipariş takip
DUYGU        🙂 merak     😐 karışık    🙂 ikna      🙂 umut     😟 güvensiz  😞 belirsiz
SÜRTÜNME     Hero iyi     Öneri klavye Ürün 103     Kupon sadece Özet yok    localStorage
             ama stok 0   ile gezilmez  ürünle aynı  sepette     Kupon yok   kaybolur
                                       görsel       Giriş şartı  Test kartı  Bildirim yok
TERK RİSKİ   Orta         Orta         Düşük        Yüksek      ÇOK YÜKSEK  Yüksek
```

**En büyük kopma noktası:** Sepet → Ödeme geçişi. Kullanıcı sepet çekmecesinde ürünleri ve kupon alanını görüyor; "Ödemeye Geç"e bastığında **ürün satırları kayboluyor**, yalnızca bir toplam tutar kalıyor. Bu, güven kaybının zirvesidir.

---

## 4. Bulgular — Detaylı

Her bulgu: **kimlik, önem, kanıt, etki, öneri** formatındadır. Kanıtlar dosya:satır olarak verilmiştir.

### 4.1 Keşif ve Ana Sayfa

#### UX-09 — Hero alanı üç eşit ağırlıklı CTA ile karar felci yaratıyor · **Orta**
**Kanıt:** `index.html:363-380` — "Tüm Parçaları İncele", "Bütçene Göre Drone Topla", "Özel 3D Parça Bastır" aynı görsel ağırlıkta.
**Etki:** Kullanıcı hangi yolun kendisi için olduğunu bilemiyor; Hick yasası gereği karar süresi uzuyor.
**Öneri:** Birincil CTA tek olsun ("Parçaları Keşfet"). Diğer ikisi ikincil (outline) stile alınsın ve **persona bazlı** konumlansın: yeni başlayan için sihirbaz, üretici için 3D.

#### UX-10 — Hero görseli 463 KB PNG, LCP adayı · **Orta**
**Kanıt:** `assets/hero_drone_white.png` 463 KB; `index.html:419` `loading="eager"`.
**Etki:** Mobil 4G'de LCP gecikmesi; ilk izlenim yavaş.
**Öneri:** AVIF/WebP + `srcset` (400/800/1200w), `fetchpriority="high"`, boyut ~60 KB.

#### UX-11 — Kategori çubuğu yatay kaydırmada görsel ipucu yok · **Düşük**
**Kanıt:** `index.html:335-338` — `category-nav-inner`, taşan öğeler için fade/ok yok.
**Etki:** Kullanıcı 13 kategorinin tamamını göremediğini fark etmiyor.
**Öneri:** Sağ kenarda gradient maske + kaydırma oklarında `aria-hidden` olmayan butonlar.

#### UX-12 — Sayfa içi `#faq` bağlantısı hedefsiz · **Düşük**
**Kanıt:** `index.html:658` footer'da "Sıkça Sorulan Sorular" → `#faq`; sayfada `id="faq"` yok (FAQ yalnızca JSON-LD'de var).
**Etki:** Kullanıcı tıklar, hiçbir şey olmaz — sessiz hata.
**Öneri:** Gerçek bir SSS bölümü ekleyin (JSON-LD ile aynı içerik) veya bağlantıyı kaldırın.

#### UX-13 — İki farklı telefon numarası ve iki `Organization` şeması · **Orta**
**Kanıt:** `index.html:72` (+90-552-128-0617) ve `index.html:110` (+90-850-555-7090). Footer, iletişim ve sözleşme sayfalarında 552 numarası kullanılıyor.
**Etki:** Kullanıcı hangi numarayı arayacağını bilemiyor; Google'da tutarsız kurumsal bilgi.
**Öneri:** Tek numara (552) tüm yüzeylerde; JSON-LD tekilleştirilsin.

#### UX-14 — Sosyal önizlemede iki `og:image` çakışması · **Düşük**
**Kanıt:** `index.html:41` (`hero_drone.png`) ve `index.html:88` (`og-image.jpg`).
**Etki:** WhatsApp/X paylaşımında hangi görselin çıkacağı belirsiz.
**Öneri:** Tek `og:image` (1200×630, <300 KB), `og:image:width/height` ekleyin.

### 4.2 Arama ve Filtreleme

#### UX-06 — Canlı arama önerileri klavye ve ekran okuyucu için erişilemez · **Yüksek**
**Kanıt:** `index.html:259` `<div id="search-suggestions">` — `role`, `aria-live`, `aria-expanded` yok. `app.js:1479-1610` öneriler `<div>` ile basılıyor, `role="option"`/`aria-activedescendant` yok, ok tuşları dinlenmiyor.
**Etki:** Klavye kullanıcısı önerilere inemez; ekran okuyucu listeyi duyurmaz. Arama, e-ticarette en yüksek niyetli giriş kanalıdır.
**Öneri:**
```html
<input type="search" role="combobox" aria-expanded="false"
       aria-controls="search-suggestions" aria-autocomplete="list"
       aria-activedescendant="">
<div id="search-suggestions" role="listbox" aria-label="Arama önerileri"></div>
```
Ok yukarı/aşağı, Enter, Escape desteği; sonuç sayısı `aria-live="polite"` ile duyurulsun.

#### UX-15 — Arama sonuçsuz kaldığında yönlendirme yok · **Orta**
**Kanıt:** `index.html:529` yalnızca "Aradığınız kriterlere uygun parça bulunamadı." metni.
**Etki:** Çıkmaz sokak. Kullanıcı ne yapacağını bilmiyor.
**Öneri:** (a) yazım önerisi ("`motorr` → `motor`"), (b) popüler 4 ürün, (c) filtreleri temizle CTA, (d) "Aradığınızı bulamadık mı? WhatsApp" bağlantısı.

#### UX-16 — Filtre paneli mobilde ayrı bir adım gerektiriyor · **Orta**
**Kanıt:** `styles.css:1441+` medya sorgusu; filtreler sidebar'da, mobilde açılır panel var ancak **aktif filtre sayısı** gösterilmiyor.
**Etki:** Kullanıcı filtre uyguladığını unutup "ürün yok" sanıyor.
**Öneri:** "Filtreler (3)" rozeti, uygulanan filtreler için kaldırılabilir çipler, "Tümünü temizle".

#### UX-17 — Sıralama seçeneği "popüler" varsayılanı belirsiz · **Düşük**
**Kanıt:** `app.js:80` `sort: 'popular'`; PDP/kartlarda bu sıralamanın neye göre olduğu açıklanmıyor (`is_bestseller` mı, puan mı?).
**Öneri:** Etiket: "Öne çıkanlar"; tooltip ile kriteri açıklayın.

### 4.3 Ürün Detay Sayfası (PDP)

#### UX-18 — PDP ile ana sayfa farklı uygulamalar gibi davranıyor · **Yüksek**
**Kanıt:** PDP'ler `app.js` yüklemiyor (yalnızca `api.js`); sepet, kullanıcı menüsü, para birimi ve yorum mantığı PDP içinde ayrı yazılmış (`products/*.html:665-900`). "Sepetim" bağlantısı `../#cart`'a gidiyor.
**Etki:** Sepet rozeti PDP'de güncellenmiyor; kullanıcı ürün ekledikten sonra sayfada hiçbir geri bildirim görmüyor (yalnızca toast). Tutarsız deneyim.
**Öneri:** Ortak bir `cart.js` + `header.js` bileşeni her iki yüzeyde kullanılsın; sepet durumu `storage` olayı ile senkronlansın.

#### UX-19 — Stok yokken birincil eylem "bildirim" ama bildirim gönderilmiyor · **Kritik (UX-02 ile birleşik)**
**Kanıt:** `products/*.html:302` `handleStockAlert`; `server.py:3127-3171` yalnızca DB'ye yazıyor; `stock_alerts.notified_at` hiçbir yerde güncellenmiyor; `stock_alerts` tablosunda **0 kayıt** var.
**Etki:** Kullanıcı e-posta/telefon bırakıyor, asla haber alamıyor. Vaadin yerine getirilmemesi, tüketici mevzuatı ve marka güveni açısından ciddi sorundur.
**Öneri:** (a) Kısa vadede metni düzeltin ("stok bilgisi için e-posta listemize katılın"), (b) 1 hafta içinde stok girişinde tetiklenen e-posta işi yazın, (c) WhatsApp vaadini kaldırın veya gerçekten gönderin.

#### UX-20 — Teknik özellik tablosu tutarlı değil · **Orta**
**Kanıt:** `specs_json` alanları ürüne göre değişiyor; bazı ürünlerde 3 satır, bazılarında 10+ (`data/products.json`).
**Etki:** Karşılaştırma yapılamıyor; "Yasin" personası için kritik.
**Öneri:** Kategori bazlı zorunlu şema (motor: KV, stator, ağırlık, mil çapı, maks. akım; ESC: sürekli/tepe akım, voltaj, firmware). Eksik alan varsa "—" gösterilsin, satır gizlenmesin.

#### UX-21 — Ürün görseli ile ürünün uyuşmaması · **Kritik (ticari)**
**Kanıt:** 103 ürün aynı `trend_speedybee_f405_v4.jpg` görselini kullanıyor; 209 ürün jenerik görselde.
**Etki:** Alıcı yanlış ürünü bekleyerek sipariş verir → iade, itibar kaybı, Merchant reddi.
**Öneri:** Görsel-SKU eşleşmesi zorunlu; eşleşmeyen ürün "yakında" durumuna alınsın.

#### UX-22 — Stok uyarısı formu gereğinden fazla alan istiyor · **Düşük**
**Kanıt:** `products/*.html:302-307` — e-posta (zorunlu) + telefon (opsiyonel).
**Öneri:** Tek alan (e-posta) ile başlayın; telefonu başarı ekranında opsiyonel olarak isteyin. Alan sayısı arttıkça dönüşüm düşer.

#### UX-23 — WhatsApp sipariş bağlantısı ürün bilgisini taşıyor ama fiyatı sabit kodluyor · **Düşük**
**Kanıt:** `products/*.html:312` — `text=...Fiyat: 2.851,77 ₺` statik gömülü.
**Etki:** Fiyat güncellenince WhatsApp mesajı eski fiyatı söyler → fiyat tutarsızlığı şikâyeti.
**Öneri:** Mesajı JS ile anlık fiyattan üretin.

### 4.4 Sepet

#### UX-24 — Ücretsiz kargo çubuğu iyi, ancak eşik iki para biriminde çelişiyor · **Orta**
**Kanıt:** `app.js:1834-1837` TRY eşiği 1.500; `server.py:4560` USD eşiği 35 $ (≈1.207 ₺ @34,5). Aynı sepet, para birimine göre farklı kargo ücreti doğurabilir.
**Etki:** "Ücretsiz kargo" sözü tutulmuyor gibi görünür.
**Öneri:** Tek eşik (TRY) ve USD'yi ondan türetin.

#### UX-25 — Kupon kodu alanı yalnızca sepette, ödemede yok · **Yüksek (UX-04)**
**Kanıt:** `index.html:727-728` kupon alanı sepet çekmecesinde; `index.html:1323-1340` ödeme özetinde kupon alanı yok.
**Etki:** Kullanıcı ödeme ekranında kupon girmek ister, bulamaz; geri dönmek zorunda kalır — hunide en sık terk nedenlerinden biri.
**Öneri:** Ödeme özetine kupon alanı ekleyin; uygulanan kuponu satır olarak gösterin ("FIRSAT628 −105,81 ₺").

#### UX-26 — Kupon kullanımı için giriş zorunlu, ancak bu önceden söylenmiyor · **Yüksek**
**Kanıt:** `coupons.py:503-504` `if not user_key: return False, "login_required"`; `app.js:1913` hata mesajı gösteriliyor.
**Etki:** Misafir kullanıcı tüm formu doldurduktan sonra "giriş yapmalısınız" duvarına çarpıyor.
**Öneri:** Kupon alanının yanında "Kupon kullanmak için giriş yapın" ipucu; veya misafir kuponunu e-posta ile eşleştirin (motor zaten `make_user_key(email)` destekliyor).

### 4.5 Ödeme (en kritik alan)

#### UX-01 — Sipariş özeti (ürün satırları) ödeme adımında yok · **Kritik**
**Kanıt:** `index.html:1323-1327` — yalnızca `<div class="summary-line">Ödenecek Tutar</div>`. Sepet çekmecesindeki `cart-items-container` ödeme modalına taşınmıyor.
**Etki:** Kullanıcı ne için ödediğini göremiyor; güven kaybı ve yanlış sipariş. Sektör ortalamasında bu tek eksik, checkout terk oranını %10–20 artırır.
**Öneri:**
```
┌─────────────────────────────────────────┐
│ Sipariş Özeti                     Düzenle│
│ [img] T-Motor F60 PRO V 1750KV   ×1  1.058,12 ₺ │
│ [img] Gemfan 4525-3 pervane      ×2    240,00 ₺ │
│ ─────────────────────────────────────── │
│ Ara toplam                        1.298,12 ₺ │
│ Kupon (FIRSAT628)                  −105,81 ₺ │
│ Kargo                                99,00 ₺ │
│ Genel toplam                      1.291,31 ₺ │
└─────────────────────────────────────────┘
```
Satırlar `aria-label` ile, "Düzenle" sepeti açar.

#### UX-08 — Ödeme alt başlığı "test kartı ile anında siparişi onaylayın" diyor · **Yüksek**
**Kanıt:** `index.html:1114` `data-i18n="checkout_sub"` → "Bilgilerinizi doldurun veya test kartı ile anında siparişi onaylayın."
**Etki:** Gerçek müşteri "bu site demo mu?" diye düşünür. Ayrıca yanıltıcı beyan riski (test kartı ile ödeme alınmıyor; `/api/payment/process` yalnızca havale kabul ediyor).
**Öneri:** "Bilgilerinizi doldurun, iyzico'nun güvenli ödeme sayfasına yönlendirileceksiniz." Ayrıca `i18n.js` içindeki karşılığını da güncelleyin.

#### UX-27 — Ödeme formunda "Ülke" serbest metin · **Orta**
**Kanıt:** `index.html:1163` `<input id="chk-country" value="Turkey">`. Diğer tüm adres alanları yapılandırılmış (81 il listesi) iken ülke serbest yazı.
**Etki:** "Türkiye", "Turkey", "TR" karışıklığı; kargo/vergi hesaplarında hata.
**Öneri:** `select` (varsayılan Türkiye) + yurt dışı için "Diğer" ve uyarı.

#### UX-28 — İlçe alanı serbest metin, il listesi sabit kodlu · **Düşük**
**Kanıt:** `app.js:5-14` `TURKISH_CITIES` (81 il doğru); ilçe `input` (`index.html:1157`).
**Öneri:** İl seçimine göre ilçe listesi (statik JSON, ~970 ilçe, ~15 KB).

#### UX-29 — TCKN boş bırakıldığında sessizce `11111111111` atanıyor · **Yüksek (mevzuat)**
**Kanıt:** `app.js:3467` `if (!taxId) taxId = '11111111111';`
**Etki:** e-Arşiv faturası geçersiz TCKN ile kesilir; mali risk. Ayrıca kullanıcıya hiç söylenmiyor.
**Öneri:** TCKN'yi zorunlu tutun (11 hane + algoritma doğrulaması) veya "fatura için TCKN gerekli" uyarısı verin. Sessiz varsayılan değer kaldırılsın.

#### UX-30 — Ödeme butonu tutarı tekrar etmiyor · **Orta**
**Kanıt:** `index.html:1336-1339` buton metni sabit ("Havale Bildirimini Tamamla" / "iyzico Güvenli Ödemeye Geç").
**Etki:** Kullanıcı son onayda tutarı görmek ister.
**Öneri:** "1.291,31 ₺ Öde — iyzico ile devam et".

#### UX-31 — Ödeme sonrası durum sayfası zayıf · **Orta**
**Kanıt:** `payment-result.html` 1,1 KB; yalnızca durum gösteriyor.
**Etki:** Kullanıcı "siparişim oluştu mu?" sorusuyla WhatsApp'a yöneliyor.
**Öneri:** Sipariş numarası, tahmini teslim, ürün özeti, "Siparişlerim"e git, e-posta ile tekrar gönder.

### 4.6 Hesap, Giriş ve Sipariş Takibi

#### UX-05 — Sipariş geçmişi cihaza bağlı · **Yüksek**
**Kanıt:** `app.js:2108` `orders = JSON.parse(localStorage.getItem('pozitron_orders') || '[]')`; API'den `syncOrdersFromBackend` yok — `syncReviewsFromBackend` var ama sipariş için yok.
**Etki:** Kullanıcı başka cihaz/tarayıcıdan girdiğinde "Siparişlerim" boş görünür; destek yükü artar.
**Öneri:** `/api/orders?user_id=` veya `/api/orders/user/<id>` uçları zaten var (yetkilendirme düzeltildikten sonra) — istemci bunları kullansın.

#### UX-32 — Giriş zorunlu değil, ama bazı işlevler sessizce giriş istiyor · **Orta**
**Kanıt:** Yorum yazma misafire açık (`comment-guest-name-group`), kupon giriş istiyor, adres kaydetme `user_id` istiyor.
**Etki:** Kullanıcı hangi işlevin hesap gerektirdiğini önceden bilmiyor.
**Öneri:** Her kısıtlı işlevde önceden ipucu + tek tıkla giriş modalı (mevcut yorum korunmalı).

#### UX-33 — Şifre politikası çok zayıf ve geri bildirim yok · **Orta**
**Kanıt:** `app.js:2478` minimum 6 karakter; güç göstergesi yok.
**Etki:** Zayıf şifreler, hesap ele geçirme.
**Öneri:** Min. 10 karakter veya 3 kelimelik parola önerisi; canlı güç göstergesi.

#### UX-34 — "3 hatalı denemede 30 dakika kilit" mesajı kullanıcıyı suçluyor · **Düşük**
**Kanıt:** `app.js:2422` "Güvenlik Koruması: 3 kez hatalı giriş yapıldı!"
**Etki:** Aynı e-postayı yanlış yazan kullanıcı, hesabı olmayan birinin kilidiyle karşılaşabilir (e-posta bazlı kilit).
**Öneri:** Nötr dil: "Çok fazla deneme yapıldı, lütfen X dakika sonra tekrar deneyin." Ayrıca kilidi IP + hesap kombinasyonuna bağlayın (bkz. güvenlik raporu).

### 4.7 3D Baskı Studio ve Drone Sihirbazı

#### UX-35 — 3D Studio yükleme akışında fiyat öncesi beklenti yönetimi yok · **Orta**
**Kanıt:** `index.html:1385-1550`; fiyat ancak STL yüklendikten sonra hesaplanıyor.
**Etki:** Kullanıcı dosya yüklemeden önce maliyeti bilmiyor; yükleme sonrası yüksek fiyat görüp vazgeçiyor.
**Öneri:** Malzeme seçiminde "≈ ₺/gram" göstergesi + örnek parça fiyatları ("tipik kamera tutucu ≈ 120 ₺").

#### UX-36 — Drone Sihirbazı ayrı sayfada, ana sayfa modalıyla çift uygulama · **Düşük**
**Kanıt:** `drone-toplama-sihirbazi.html` (19 KB) + `index.html:810` builder modalı.
**Öneri:** Tek uygulama; modal yalnızca yönlendirsin.

#### UX-37 — 3D görüntüleyici için yükleme/hata durumu yok · **Düşük**
**Kanıt:** `index.html:1635-1637` Three.js eager; STL yükleme sırasında iskelet/ilerleme yok.
**Öneri:** İskelet ekran + "Model yükleniyor… %45" + hata durumunda "Dosya okunamadı, farklı bir STL deneyin".

### 4.8 İçerik, Dil ve Ton

#### UX-38 — Türkçe/İngilizce geçişi kısmi · **Orta**
**Kanıt:** `i18n.js` 203 anahtar tam (eksik yok — olumlu). Ancak PDP'ler, rehber, yasal sayfalar ve hata mesajlarının büyük kısmı `data-i18n` kullanmıyor; ör. `app.js` içinde onlarca sabit Türkçe metin (`"Lütfen tüm teslimat bilgilerini..."`).
**Etki:** İngilizce seçen kullanıcı yarı Türkçe bir arayüzle karşılaşır.
**Öneri:** Ya İngilizceyi "beta" olarak işaretleyin ya da tüm kullanıcı metinlerini sözlüğe taşıyın. Üçüncü yol: İngilizceyi geçici olarak kaldırın — yarım dil, hiç dilden kötüdür.

#### UX-39 — Hata mesajları teknik ve suçlayıcı · **Orta**
**Kanıt:** `app.js:2367` "[GUVENLIK KORUMASI] ...", `app.js:2427` "Hatalı e-posta veya şifre!"; `server.py:556` "Yetkisiz erişim..."
**Etki:** Kullanıcı ne yapacağını bilmiyor.
**Öneri:** "Ne oldu + ne yapmalıyım" formatı; teknik kod göstermeyin.

#### UX-40 — Yasal metinler ile arayüz çelişiyor · **Yüksek (mevzuat)**
**Kanıt:** SSS JSON-LD (`index.html:165`) "PayTR 3D Secure ... ile ödeme yapabilirsiniz" diyor; gerçekte PayTR yok ve butonu "Yakında". Ayrıca iade politikası "ücretsiz iade" diyor (`products/*.html` `returnFees: FreeReturn`) — kargo kim ödüyor belirsiz.
**Etki:** Yanıltıcı beyan; tüketici şikâyeti ve Google Merchant uyumsuzluğu.
**Öneri:** SSS'i gerçek ödeme yöntemleriyle eşleştirin; iade kargo politikasını netleştirin.

#### UX-41 — "Doğrulanmış yorum" etiketi güvenilmez · **Yüksek**
**Kanıt:** `server.py:4717` her yorum `verified_purchase=1` olarak yazılıyor. Ayrıca ana sayfa yorumları yalnızca `localStorage`'dan geliyor (`app.js:6662-6671`), yani herkes farklı yorum görüyor.
**Etki:** Etiket anlamsız; kullanıcı fark ederse tüm sosyal kanıt değersizleşir.
**Öneri:** `verified_purchase` yalnızca e-posta+sipariş eşleşmesiyle 1 olsun; yorumlar API'den tek kaynaktan gelsin; "doğrulanmış" olmayanlar etiketsiz gösterilsin.

---

## 5. Erişilebilirlik (WCAG 2.2 AA) Denetimi

| Kriter | Durum | Kanıt / Not |
|---|---|---|
| 1.1.1 Görsel olmayan içerik | 🟡 Kısmi | `alt` var; ancak dekoratif SVG'lerde `aria-hidden` eksik |
| 1.3.1 Bilgi ve ilişkiler | 🟡 Kısmi | Başlık hiyerarşisi iyi; arama önerileri listbox değil |
| 1.4.1 Renk kullanımı | 🟢 Uygun | Stok durumu renk + metin |
| 1.4.3 Kontrast (4.5:1) | 🟡 Kısmi | `--text-muted` küçük metinlerde sınırda; yeniden ölçülmeli |
| 1.4.10 Yeniden akış | 🟢 Uygun | 320 px'te yatay kaydırma yok |
| 1.4.11 Metin dışı kontrast | 🟡 Kısmi | Buton kenarlıkları bazı temalarda zayıf |
| 2.1.1 Klavye | 🔴 İhlal | Modal içinde odak tuzağı yok; odak arkaya kaçıyor |
| 2.1.2 Klavye tuzağı yok | 🟡 Kısmi | ESC çalışıyor (`app.js:445`) — olumlu |
| 2.4.1 Blokları atla | 🔴 İhlal | Skip-link yok |
| 2.4.3 Odak sırası | 🟡 Kısmi | Modal açılışında odak ilk alana taşınmıyor |
| 2.4.7 Görünür odak | 🔴 İhlal | `:focus-visible` tanımlı değil (yalnızca input) |
| 2.4.11 Odak görünürlüğü (AA, 2.2) | 🔴 İhlal | Yapışkan header odaklanan öğeyi kapatabilir |
| 2.5.7 Sürükleme hareketleri (AA, 2.2) | 🟡 Kısmi | Görsel galerisi sürükleme gerektirebilir |
| 2.5.8 Hedef boyutu 24×24 (AA, 2.2) | 🟡 Kısmi | Kart içi küçük ikon butonlar |
| 3.3.1 Hata tanımlama | 🟡 Kısmi | Metin var, alan bazlı `aria-invalid` yok |
| 3.3.2 Etiketler | 🟡 Kısmi | Checkout alanları etiketli; dinamik alanlar kısmen |
| 3.3.7 Gereksiz yeniden giriş (AA, 2.2) | 🔴 İhlal | Adres bilgisi tekrar isteniyor (kayıtlı adres olsa da) |
| 4.1.2 Ad, rol, değer | 🟡 Kısmi | Dil/para birimi butonlarında `aria-pressed` yok |
| 4.1.3 Durum mesajları | 🟡 Kısmi | `toast` `aria-live="assertive"` — doğru; ama sepet rozeti duyurulmuyor |
| `prefers-reduced-motion` | 🔴 Yok | Animasyonlar kapatılamıyor |

**Öncelikli 5 erişilebilirlik düzeltmesi (toplam ~1 gün):**

1. Skip-link + `main` odak hedefi.
2. Genel `:focus-visible { outline: 3px solid #0284c7; outline-offset: 2px; }`.
3. Modal odak tuzağı + kapanışta odağı tetikleyen butona döndürme (tek yardımcı fonksiyon).
4. Arama kutusuna `role="combobox"` + `aria-activedescendant`.
5. `@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }`.

---

## 6. Performans ve Algılanan Hız

| Ölçüm | Değer | Hedef |
|---|---:|---:|
| İlk yükleme (JS+CSS+görsel) | ~3,0 MB | < 800 KB |
| JS toplamı | ~2,45 MB | < 500 KB |
| Görsel (hero) | 463 KB | < 80 KB |
| İstek sayısı (ana sayfa) | ~18 | < 25 |
| Cache politikası | `no-store` (tüm .js/.css/.html) | hash'li + immutable |
| 3D kütüphaneleri | eager 626 KB | lazy |
| Render-blocking CSS | 1 dosya, 124 KB | kritik CSS inline |

**En yüksek etkili 4 düzeltme:**

1. **3D'yi lazy yükle** — modal açılmadan `three.min.js` indirilmesin (−626 KB).
2. **Katalog verisini böl** — `pozitron_data.js` yerine kategori bazlı JSON + `IntersectionObserver` ile sonsuz kaydırma (−1,2 MB).
3. **Cache'i düzelt** — `server.py:623-628` tüm statik varlıklara `no-store` gönderiyor; `?v=` sorgusu zaten var, `immutable, max-age=31536000` kullanılmalı.
4. **Görselleri dönüştür** — AVIF/WebP + `srcset` + `width/height` (CLS'i de düzeltir).

**Ölçüm önerisi:** Sayfaya hafif bir RUM ekleyin (ör. `web-vitals` 2 KB) ve LCP/INP/CLS değerlerini GA4'e `event` olarak gönderin. Şu anda Core Web Vitals **hiç ölçülmüyor**.

---

## 7. Güven ve Dönüşüm Psikolojisi

| Unsur | Durum | Değerlendirme |
|---|---|---|
| Ücretsiz kargo eşiği | ✅ | Çubuğun olması çok iyi |
| Ödeme logoları | ✅ | iyzico/ Visa/Mastercard görünür |
| SSL/site güvenliği mesajı | 🟡 | Var ama somut değil ("3D Secure" ibaresi ödeme sayfasında) |
| İade politikası görünürlüğü | 🟡 | Footer'da var, PDP'de kısa özet yok |
| Gerçek müşteri yorumları | 🔴 | Sahte/boş; "doğrulanmış" etiketi güvenilmez |
| Teslimat süresi taahhüdü | 🟡 | "1-3 iş günü" var, PDP'de tarih yok |
| Şirket bilgisi (ünvan, vergi, adres) | ✅ | İletişim/hakkımızda sayfalarında mevcut |
| Canlı destek | ✅ | WhatsApp hattı |
| Stok şeffaflığı | 🔴 | "Son 3 adet" iyi fikir, ama her şey tükendi |
| Hata durumunda iletişim | 🟡 | "destek@" var, ortalama yanıt süresi belirtilmemiş |

**En yüksek getirili 3 güven hamlesi:**
1. Gerçek, sipariş doğrulamalı yorumlar (5–10 adet yeterli).
2. PDP'de "Bugün sipariş ver, **3 Kasım**'da kapında" dinamik tarih.
3. Ödeme sayfasında 3 maddelik güven şeridi: "256-bit SSL · iyzico güvenli ödeme · 14 gün iade".

---

## 8. Ölçüm Planı

Şu anda dönüşüm hunisi **ölçülmüyor** (GA4 kurulu ama yalnızca `config` ve birkaç `add_payment_info` olayı var). Önerilen minimum olay şeması:

| Olay | Parametreler | Amaç |
|---|---|---|
| `view_item_list` | `list_id`, `category`, `item_count` | Kategori performansı |
| `search` | `search_term`, `results_count` | Sıfır sonuç oranı |
| `filter_apply` | `filter_type`, `value` | Filtre kullanımı |
| `view_item` | `item_id`, `price`, `stock_status` | PDP görüntüleme |
| `add_to_cart` | `item_id`, `quantity`, `value` | Ana huni |
| `stock_alert_submit` | `item_id` | Talep ölçümü |
| `begin_checkout` | `value`, `items` | Huni |
| `add_coupon` | `code`, `success` | Kupon sürtünmesi |
| `purchase` | `transaction_id`, `value`, `payment_type` | Gelir |
| `checkout_error` | `field`, `message` | Form sürtünmesi |

**Hedef KPI'lar (90 gün):**

| KPI | Bugün (tahmini) | Hedef |
|---|---:|---:|
| Ana sayfa → PDP oranı | ? | > %35 |
| PDP → sepete ekleme | ~%0 (stok) | > %8 |
| Sepet → ödeme başlatma | ? | > %45 |
| Ödeme tamamlama | ? | > %60 |
| Mobil LCP | ~4–6 sn | < 2,5 sn |
| Checkout form hatası oranı | ? | < %5 |
| Destek talebi / sipariş | ? | < 0,3 |

---

## 9. Önceliklendirilmiş UX Backlog'u

Etki = dönüşüm/güven üzerindeki etki (1–5), Efor = geliştirme günü.

| ID | İş | Etki | Efor | Öncelik |
|---|---|---:|---:|---|
| UX-01 | Ödeme adımına sipariş özeti | 5 | 0,5 gün | **P0** |
| UX-02 | Stok uyarısı bildirim işi (veya metni düzelt) | 5 | 0,5–2 gün | **P0** |
| UX-03 | Stok verisini gerçek veriyle doldur / ön sipariş modeli | 5 | 2–3 gün | **P0** |
| UX-21 | Görsel-SKU eşleşmesi | 5 | 3–5 gün | **P0** |
| UX-08 | "Test kartı" metnini kaldır | 4 | 10 dk | **P0** |
| UX-29 | TCKN sessiz varsayılanını kaldır | 4 | 1 saat | P1 |
| UX-04 | Ödemede kupon alanı | 4 | 0,5 gün | P1 |
| UX-26 | Kupon için giriş ipucu | 3 | 2 saat | P1 |
| UX-05 | Sipariş geçmişini API'den çek | 4 | 0,5 gün | P1 |
| UX-41 | Yorum kaynağını tekilleştir | 4 | 1 gün | P1 |
| UX-06 | Arama combobox + klavye | 3 | 0,5 gün | P1 |
| UX-40 | SSS/PayTR çelişkisi | 4 | 2 saat | P1 |
| A11y-1..5 | Skip-link, focus-visible, focus trap, reduced-motion | 3 | 1 gün | P1 |
| UX-18 | PDP'de ortak sepet/başlık bileşeni | 3 | 1 gün | P1 |
| UX-24 | Kargo eşiği tekilleştirme | 3 | 2 saat | P2 |
| UX-15 | Sıfır sonuç ekranı | 3 | 0,5 gün | P2 |
| UX-16 | Filtre rozetleri | 2 | 0,5 gün | P2 |
| UX-20 | Kategori bazlı zorunlu teknik şema | 3 | 2 gün | P2 |
| UX-12 | `#faq` hedefi | 2 | 2 saat | P2 |
| UX-13/14 | Tek telefon, tek og:image | 2 | 1 saat | P2 |
| UX-10 | Hero görsel optimizasyonu | 3 | 2 saat | P2 |
| UX-30 | Butonda tutar | 2 | 1 saat | P3 |
| UX-31 | Ödeme sonrası zengin durum | 2 | 0,5 gün | P3 |
| UX-35 | 3D fiyat önizlemesi | 2 | 0,5 gün | P3 |
| UX-38 | İngilizce kapsamı | 2 | 3–5 gün | P3 |

**Toplam P0 eforu: ~4–6 gün.** Bu süre sonunda huni "çalışan" bir e-ticaret sitesi seviyesine gelir.

---

## 10. Hızlı Kazanımlar (aynı gün, < 4 saat)

1. `checkout_sub` metnini düzelt ("test kartı" ibaresini kaldır).
2. `app.js:3467` sessiz TCKN varsayılanını kaldır.
3. `#faq` bağlantısını gerçek bölüme bağla (veya kaldır).
4. İki `og:image` ve iki telefon numarasını tekilleştir.
5. Stok uyarısı formundaki "WhatsApp ile haberdar olun" vaadini metinden çıkar.
6. Skip-link + global `:focus-visible` ekle.
7. `prefers-reduced-motion` bloğu ekle.
8. `payment-result.html`'e sipariş numarası ve "Siparişlerim" bağlantısı ekle.

---

## Ek — Sezgisel Değerlendirme Kontrol Listesi

| Nielsen Sezgiseli | Durum | Not |
|---|---|---|
| 1. Sistem durumunun görünürlüğü | 🟡 | Toast ve stok rozetleri iyi; sepet/ödeme durumu zayıf |
| 2. Sistem ile gerçek dünya uyumu | 🟢 | FPV terminolojisi doğru |
| 3. Kullanıcı kontrolü ve özgürlük | 🟡 | ESC çalışıyor; "geri al" yok |
| 4. Tutarlılık ve standartlar | 🔴 | PDP ≠ ana sayfa; üç ayrı yorum sistemi |
| 5. Hataları önleme | 🟡 | Form doğrulama var; TCKN varsayılanı riskli |
| 6. Hatırlamak yerine tanıma | 🟢 | Kayıtlı adres seçimi iyi |
| 7. Kullanım esnekliği ve verimlilik | 🟡 | Arama klavye desteklemiyor |
| 8. Estetik ve minimalist tasarım | 🟢 | Güçlü |
| 9. Hatalardan kurtulmaya yardım | 🟡 | Mesajlar teknik |
| 10. Yardım ve dokümantasyon | 🟡 | Rehber var, bağlamsal yardım yok |

---

*Bu rapor, 1 Kasım 2026 itibarıyla kod tabanı ve canlı site üzerinde yapılan incelemeye dayanır. Bulgular önceliklendirilmiş olup, P0 maddeleri ticari olarak bloke edici niteliktedir.*
