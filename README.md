# ⚡ Pozitron Market — Türkiye'nin Lider Profesyonel FPV & Drone Ekosistemi

> **Bilingual (Türkçe & English)** • **500+ Premium Parça** • **Minimalist Aydınlık Tasarım** • **Drone Uyumluluk Motoru** • **Canlı Arama & 3D Secure Simülasyonu** • **GitHub Pages Uyumlu**

---

## 🌟 Proje Özeti (Overview)

**Pozitron Market**, yarış ve freestyle FPV pilotları, endüstriyel İHA mühendisleri ve drone meraklıları için geliştirilmiş, yüksek performanslı ve modern bir e-ticaret platformudur.

Tamamen bağımsız çalışan (static client-side architecture + optional Python SQLite backend) yapısı sayesinde **GitHub Pages** üzerinde tek tıkla canlı olarak barındırılabilir.

---

## ✨ Temel Özellikler (Key Features)

- **🛸 500+ Seçkin Ürün:** Motorlar, ESC sürücüler, uçuş kontrol kartları (FC), LiPo bataryalar, kameralar, VTX video vericiler, antenler, pervaneler ve karbon fiber gövdeler.
- **🌐 Çift Dil Desteği (TR / EN):** Gerçek zamanlı i18n sistemi; tek tıkla Türkçe ve İngilizce arasında tüm arayüz, para birimi ($ USD / ₺ TRY) ve filtreler anında güncellenir.
- **🔍 Akıllı Canlı Arama:** Arama kutusuna yazıldığı anda resimli, fiyatlı ve kategorili otomatik tamamlama.
- **⚡ Drone Uyumluluk Sihirbazı:** Motor KV, ESC amperajı, pervane boyutu ve LiPo batarya voltajını eşleştirip uyumluluk puanı (Compatibility Score) hesaplayan interaktif araç.
- **🛒 Gelişmiş Sepet & Kuponlar:** Ücretsiz kargo baremi dinamik ilerleme çubuğu, anlık kupon uygulama (`POZITRON10`, `FPV2026`, `DRONE50`).
- **🔐 Giriş & Kayıt Sistemi:** Google ile tek tıkla giriş veya e-posta ile kayıt/giriş desteği.
- **💳 3D Secure SMS OTP Simülasyonu:** Kart doğrulama, SMS onay kodu (`554433`) ve anında fatura / kargo takip fişi çıktısı.
- **🎯 Google & Arama Motoru SEO:** OpenGraph, Twitter Cards, Schema.org JSON-LD yapısal veri (Product & WebSite), semantik HTML5 yapısı.

---

## 🚀 GitHub Pages Üzerinde Yayına Alma (Deployment)

Bu repo GitHub Pages için özel olarak yapılandırılmıştır.

1. **GitHub'a Gönderme:**
   ```bash
   git add .
   git commit -m "Pozitron Market - Initial Release for GitHub Pages"
   git branch -M main
   git remote add origin https://github.com/<kullanici-adiniz>/pozitron-market.git
   git push -u origin main
   ```

2. **GitHub Pages'i Aktifleştirme:**
   - GitHub deponuzun **Settings** (Ayarlar) sekmesine gidin.
   - Sol menüden **Pages** bölümüne tıklayın.
   - **Branch** olarak `main` ve klasör olarak `/ (root)` seçip **Save** butonuna basın.
   - Birkaç saniye içinde `https://<kullanici-adiniz>.github.io/pozitron-market/` adresinde siteniz dünya genelinde yayına girecektir!

---

## 💻 Yerel Geliştirme (Local Development)

### Yöntem 1: Statik Tarayıcı Sunucusu
```bash
# Python ile hızlı sunucu başlatma
python3 -m http.server 8000
```
Tarayıcınızda `http://localhost:8000` adresini açın.

### Yöntem 2: Python / SQLite API Backend
```bash
# SQLite veritabanı backend ile çalıştırma
python3 server.py
```
Tarayıcınızda `http://localhost:5000` adresini açın.

---

## 📁 Proje Dizin Yapısı

```
Pozitron/
├── index.html            # Ana sayfa, SEO meta etiketleri ve modallar
├── styles.css            # Minimalist aydınlık tasarım sistemi & responsive CSS
├── app.js                # Çift modlu istemci mantığı & sepet/arama/uyumluluk motoru
├── i18n.js               # Türkçe / İngilizce çeviri sözlükleri
├── .nojekyll             # GitHub Pages statik yönlendirme dosyası
├── data/
│   └── pozitron_data.js  # 500 ürünün tam statik JSON veri deposu
├── assets/
│   ├── favicon.svg       # Pozitron logo favikonu
│   ├── logo.svg          # Vektör logo
│   └── products/         # Ürün ve donanım görselleri
├── database.py           # SQLite veritabanı şeması ve modelleri
├── seed_data.py          # 500 ürün ve kategori üretim scripti
├── export_data.py        # SQLite'tan pozitron_data.js üretim scripti
└── server.py             # Python HTTP REST API sunucusu
```

---

© 2026 Pozitron Market. Tüm hakları saklıdır.
