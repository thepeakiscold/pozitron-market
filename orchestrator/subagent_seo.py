import sqlite3
import os
import json
import re
import uuid
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Optional, Set

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pozitron.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def turkish_to_slug(text: str) -> str:
    """Converts Turkish text into a clean URL-friendly slug."""
    tr_map = {
        'ç': 'c', 'Ç': 'c',
        'ğ': 'g', 'Ğ': 'g',
        'ı': 'i', 'I': 'i', 'İ': 'i',
        'ö': 'o', 'Ö': 'o',
        'ş': 's', 'Ş': 's',
        'ü': 'u', 'Ü': 'u',
    }
    s = text.lower()
    for k, v in tr_map.items():
        s = s.replace(k, v)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s

def normalize_topic_keywords(text: str) -> Set[str]:
    """Extracts normalized technical keywords to detect conceptual topic duplication."""
    tr_map = {
        'ç': 'c', 'Ç': 'c',
        'ğ': 'g', 'Ğ': 'g',
        'ı': 'i', 'I': 'i', 'İ': 'i',
        'ö': 'o', 'Ö': 'o',
        'ş': 's', 'Ş': 's',
        'ü': 'u', 'Ü': 'u',
    }
    s = text.lower()
    for k, v in tr_map.items():
        s = s.replace(k, v)
    words = re.findall(r'[a-z0-9]{3,}', s)
    stop_words = {
        've', 'ile', 'icin', 'kapsamli', 'muhendislik', 'donanim', 'rehberi',
        'rehber', 'nasil', 'nedir', 'ayari', 'ayar', 'nelerdir', 'adim', 'adimlari',
        'kilavuzu', 'kilavuz', 'pozitron', 'market'
    }
    return {w for w in words if w not in stop_words}

# COMPREHENSIVE FPV & DRONE TECHNICAL TOPIC REPOSITORY (KAPSAMLI REHBER HAVUZU)
TOPIC_REPOSITORY: List[Dict] = [
    {
        "id_code": "fc_uart_betaflight",
        "title": "Uçuş Kontrol Kartı (FC) UART & Betaflight 4.5 Konfigürasyon Rehberi",
        "component_focus": "Uçuş Kontrol Kartı (FC) UART & Betaflight 4.5 Konfigürasyonu",
        "category_search": "Uçuş",
        "target_keywords": [
            "Betaflight 4.5 UART ayarları", "CRSF ELRS port bağlantısı",
            "FPV uçuş kartı lehimleme", "STM32F722 DMA", "Pozitron Market FPV"
        ],
        "content_markdown": """# Uçuş Kontrol Kartı (FC) UART & Betaflight 4.5 Konfigürasyon Rehberi

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `Betaflight 4.5 UART ayarları, CRSF ELRS port bağlantısı, FPV uçuş kartı lehimleme, STM32F722 DMA, Pozitron Market FPV`  
**Yayın Tarihi:** {publish_date}

---

## 1. Giriş ve Donanım Mimarisi

Modern FPV yarış ve serbest stil (freestyle) drone sistemlerinde, uçuş kontrol kartı (Flight Controller) ile çevre birimleri (ESC, Alıcı/ELRS, VTX, GPS) arasındaki haberleşme kararlılığı, sıfır kırım ve minimum gecikme süresi için hayati önem taşır.

Özellikle STM32F405, STM32F722 ve yeni nesil STM32H7 mikrodenetleyici mimarilerinde DMA (Direct Memory Access) kanallarının doğru paylaştırılması ve UART (Universal Asynchronous Receiver-Transmitter) portlarının doğru baudrate hızlarında konfigüre edilmesi gerekir. F4 işlemcilerde donanımsal UART tersleyici (inverter) bulunmazken, F7 ve H7 mimarilerinde tüm portlar çift yönlü ve yazılımsal terslemeyi doğrudan destekler.

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

> [İPUCU] **Teknik İpuçları:** Tüm donanım uyumluluk sorularınız ve özel lehimleme destek talepleriniz için [Pozitron Drone Toplama Sihirbazı](https://pozitronmarket.com/drone-toplama-sihirbazi.html) aracımızı kullanabilirsiniz.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Alıcı Bağlantısı Gelmiyor (No Receiver Signal):** Alıcının `Rx` ucunun uçuş kartındaki `Tx` ucuna değil, mutlaka `Rx` ucuna (CRSF protokolünde cross bağlantı: Alıcı TX -> FC RX, Alıcı RX -> FC TX) bağlandığından emin olun.
- **Aşırı Motor Isınması:** RPM filtresi kapalıyken D-Term kazancının yüksek olmasından kaynaklanabilir. Master D-Term çarpanını 0.8 seviyesine çekip motor sıcaklıklarını 30 saniyelik havada asılı kalma (hover) testiyle kontrol edin.
"""
    },
    {
        "id_code": "lipo_safety_and_charging",
        "title": "LiPo Batarya Güvenliği, Hücre Dengeleme ve C-Değeri Hesaplama Rehberi",
        "component_focus": "LiPo Batarya Güvenliği ve Şarj Kuralları",
        "category_search": "Batarya",
        "target_keywords": [
            "LiPo batarya güvenliği", "LiPo storage modu", "FPV pil şarjı",
            "C değeri hesaplama", "6S LiPo hücre voltajı", "Pozitron Market batarya"
        ],
        "content_markdown": """# LiPo Batarya Güvenliği, Hücre Dengeleme ve C-Değeri Hesaplama Rehberi

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `LiPo batarya güvenliği, LiPo storage modu, FPV pil şarjı, C değeri hesaplama, 6S LiPo hücre voltajı, Pozitron Market batarya`  
**Yayın Tarihi:** {publish_date}

---

## 1. Giriş ve LiPo Kimyasının Temelleri

FPV dronelarda kullanılan Lityum Polimer (LiPo) bataryalar, olağanüstü yüksek anlık deşarj kapasiteleri (akım çıkışı) sayesinde yüksek performanslı fırçasız motorlara ihtiyaç duydukları gücü sağlar. Ancak bu yüksek enerji yoğunluğu, doğru voltaj sınırları ve şarj kurallarına uyulmadığında termal kaçak (thermal runaway) ve yangın riski barındırır.

Bir LiPo hücresinin kimyasal stabilitesini korumak, uçuş süresini uzatmak ve iç direncinin (IR - Internal Resistance) yükselmesini önlemek için hücre başına gerilim değerlerinin hassasiyetle yönetilmesi gerekir.

---

## 2. Hücre Gerilim Seviyeleri ve Güvenlik Limitleri

Her FPV pilotunun ezbere bilmesi gereken standart LiPo ve LiHV (High Voltage) hücre voltaj eşikleri:

| Batarya Durumu | Standart LiPo (Hücre Başı) | LiHV (Yüksek Voltaj LiPo) | Toplam Gerilim (6S Paket) |
| :--- | :--- | :--- | :--- |
| **Maksimum Şarj Voltajı** | 4.20V | 4.35V | 25.20V (LiHV: 26.10V) |
| **Nominal Voltaj** | 3.70V | 3.80V | 22.20V |
| **Depolama (Storage) Modu** | 3.82V - 3.85V | 3.85V - 3.88V | ~23.00V |
| **İniş Eşiği (Uçuş Sonu)** | 3.50V - 3.60V | 3.55V - 3.65V | 21.00V - 21.60V |
| **Kritik Hasar Sınırı (Deşarj)** | < 3.00V (Kimyasal Hasar) | < 3.00V | < 18.00V (Kullanılamaz) |

### 2.1. C-Değeri (Discharge Rate) ve Akım Kapasitesi Hesaplama
Bir bataryanın sürekli ve anlık verebileceği maksimum amper şu formülle hesaplanır:
`Maksimum Akım (Amper) = Kapasite (Ah) x C-Değeri`
Örneğin 1300mAh (1.3Ah) 120C bir 6S batarya:
`1.3 Ah x 120C = 156 Amper` sürekli akım sağlayabilir. 4 adet 2207 motorun tam gazda toplam 140A çektiği bir sistemde bu batarya güvenle çalışır.

---

## 3. Güvenli Şarj ve Saklama Protokolü

1. **1C Kuralı ile Şarj:** Bataryalarınızı daima kapasitesinin 1 katı akımla şarj edin (Örn: 1500mAh için 1.5A). Zorunlu kalmadıkça 2C üzerindeki hızlı şarjlardan kaçının.
2. **Dengeleme (Balance Charge):** Şarj cihazında daima Balance Charge modunu seçin. Hücreler arasındaki gerilim farkı 0.03V üzerinde olmamalıdır.
3. **Depolama (Storage) Şartı:** 48 saatten uzun süre kullanılmayacak bataryaları asla tam dolu (4.20V) veya boş bırakmayın. Mutlaka akıllı şarj cihazının **Storage (Depolama)** modunu çalıştırarak hücreleri 3.83V seviyesine getirin.
4. **LiPo Safe Bag / Metal Kutu:** Şarj esnasında bataryayı yanmaz LiPo çantasında veya metal mühimmat kutusunda, serin ve gözetim altında tutun.

---

## 4. Pozitron Market Uyumlu Batarya ve Şarj Cihazı Kataloğu

Türkiye stoklarımızdan hızlı teslimatla sunulan yüksek C değerli LiPo bataryalar ve akıllı şarj donanımları:

{links_md}

> [İPUCU] **Teknik İpuçları:** Bataryalarınızın iç direncini (IR) şarj cihazınız üzerinden düzenli ölçün. Sağlıklı bir hücrede iç direnç 2 ila 8 mΩ arasındadır; 20 mΩ üzerindeki hücreler artık yüksek akım veremez ve uçuşta voltaj çökmesine (voltage sag) neden olur.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Şişmiş (Puffed) Batarya:** Hücre içindeki elektrolitin gazlaşması sonucu oluşur. Şişmiş bataryaların iç direnci yüksektir ve patlama riski taşır; kesinlikle kullanılmamalı, tuzlu su banyosunda tamamen deşarj edilip geri dönüşüme teslim edilmelidir.
- **Voltaj Çökmesi (Voltage Sag):** Gaz verdiğiniz anda voltajın aniden 3.2V seviyesine düşmesi, bataryanın C-değerinin motor çekişine yetersiz geldiğini veya bataryanın ömrünü tamamladığını gösterir.
"""
    },
    {
        "id_code": "elrs_setup_and_rf",
        "title": "ExpressLRS (ELRS) 2.4GHz ve 868MHz Kurulumu, Paket Oranları ve Telemetri Kılavuzu",
        "component_focus": "ExpressLRS (ELRS) RF Protokolü ve Alıcı Kurulumu",
        "category_search": "Alıcı",
        "target_keywords": [
            "ExpressLRS kurulumu", "ELRS 2.4GHz vs 868MHz", "ELRS paket oranı",
            "Betaflight CRSF ayarı", "FPV kumanda alıcı", "Pozitron Market ELRS"
        ],
        "content_markdown": """# ExpressLRS (ELRS) 2.4GHz ve 868MHz Kurulumu, Paket Oranları ve Telemetri Kılavuzu

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `ExpressLRS kurulumu, ELRS 2.4GHz vs 868MHz, ELRS paket oranı, Betaflight CRSF ayarı, FPV kumanda alıcı, Pozitron Market ELRS`  
**Yayın Tarihi:** {publish_date}

---

## 1. ExpressLRS (ELRS) Mimarisi ve LoRa Teknolojisi

ExpressLRS, RC radyo kontrol sistemlerinde devrim yaratan, açık kaynaklı ve LoRa (Long Range) modülasyonu üzerine kurulu yüksek performanslı bir RF protokolüdür. Geleneksel sistemlere (FrSky D8/D16, FlySky) kıyasla milisaniyenin altında paket gecikmesi, olağanüstü menzil ve endüstri standardı CRSF seri haberleşme sunar.

ELRS sistemi; yarış pilotları için 500Hz - 1000Hz gibi ultra hızlı yenileme hızları sunarken, uzun menzil (Long Range) uçuşları için 50Hz - 150Hz modlarında kilometrelerce güvenli bağlantı sağlar.

---

## 2. 2.4GHz vs 868MHz/915MHz Karşılaştırması ve Paket Oranları

Kullanım amacınıza göre doğru RF frekansı ve paket yenileme oranı (Packet Rate) seçimi:

| Özellik | ELRS 2.4GHz | ELRS 868MHz (EU) / 915MHz (FCC) |
| :--- | :--- | :--- |
| **Öncelikli Kullanım** | Yarış, Freestyle, Yakın/Orta Menzil | Ultra Uzun Menzil (Long Range), Dağ Uçuşları |
| **Anten Boyutu** | Çok küçük (~32mm T-Anten veya Seramik) | Daha büyük (~80mm T-Anten) |
| **Maksimum Paket Oranı** | 250Hz, 500Hz, 1000Hz | 50Hz, 100Hz, 200Hz |
| **Gecikme Süresi (Latency)** | ~1.5 ms - 3 ms (Sıfır Hissiyat) | ~5 ms - 15 ms |
| **Engel Penetrasyonu** | Binalar ve ağaçlar arasında iyi | Çok yüksek (Düşük frekans kırınımı yüksek) |

### 2.1. Dinamik Güç (Dynamic Power) Yönetimi
Kumanda modülünüzü sabit 1W güçte çalıştırmak yerine **Dynamic Power** modunu aktif edin. Sistem RSSI ve Link Quality (LQ) değerlerini anlık analiz ederek sinyal güçlüyken 25mW'a düşürür, pilot engelin arkasına geçtiğinde anında 250mW veya 1000mW seviyesine çıkarır. Bu sayede kumanda pili tasarruf edilir ve modül aşırı ısınmaz.

---

## 3. Wi-Fi ile Firmware Güncelleme ve Binding Phrase Tanımlama

1. **Alıcıyı Wi-Fi Moduna Alma:** Drone'a batarya takın ve kumandayı kapalı tutun. 60 saniye sonra alıcı üzerindeki yeşil/mavi LED hızlı yanıp sönerek Wi-Fi erişim noktası oluşturur (`ExpressLRS RX`).
2. **Web Arayüzüne Bağlanma:** Telefon veya bilgisayarınızdan bu ağa bağlanıp `10.0.0.1` adresine gidin.
3. **Binding Phrase (Eşleşme Parolası):** Hem kumanda modülünüze hem alıcınıza aynı gizli parolayı (örneğin: `pozitron-pilot-2026`) yazın. Artık fiziksel bind butonuna gerek kalmadan cihazlar otomatik eşleşir.
4. **Betaflight Ayarı:** Betaflight Configurator'da Ports sekmesinde alıcının bağlı olduğu UART'ta **Serial Rx** seçin; Receiver sekmesinde **Serial (via UART)** ve **CRSF** protokolünü belirleyin.

---

## 4. Pozitron Market Uyumlu ExpressLRS Donanımları

Türkiye resmi stoklarımızdan temin edebileceğiniz ExpressLRS alıcı, modül ve anten donanımları:

{links_md}

> [İPUCU] **Teknik İpuçları:** OSD ekranınızda RSSI yerine daima **Link Quality (LQ)** değerini izleyin. LQ değeri 100 üzerinden paket teslim başarı oranını gösterir; LQ 70 altına düştüğünde derhal geri dönüşe geçmelisiniz.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Alıcı Eşleşmiyor:** Firmware sürümlerinin (V2.x vs V3.x) ana versiyon numarası aynı olmalıdır. V2 modül ile V3 alıcı eşleşmez; ikisini de en güncel V3.x sürümüne güncelleyin.
- **Düşük Paket Kalitesi (LQ Dalgalanması):** Alıcı anteninin karbon fiber gövdeye doğrudan temas etmediğinden ve motor kablolarından en az 2cm uzakta durduğundan emin olun.
"""
    },
    {
        "id_code": "motor_and_prop_selection",
        "title": "FPV Fırçasız Motor Seçimi: 2207 vs 2306 Stator, KV Değeri ve Pervane Eşleşmesi",
        "component_focus": "FPV Fırçasız Motor ve Pervane Eşleşmesi",
        "category_search": "Motor",
        "target_keywords": [
            "2207 vs 2306 motor", "FPV motor seçimi", "KV değeri nedir",
            "5 inç drone pervanesi", "6S motor seçimi", "Pozitron Market motor"
        ],
        "content_markdown": """# FPV Fırçasız Motor Seçimi: 2207 vs 2306 Stator, KV Değeri ve Pervane Eşleşmesi

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `2207 vs 2306 motor, FPV motor seçimi, KV değeri nedir, 5 inç drone pervanesi, 6S motor seçimi, Pozitron Market motor`  
**Yayın Tarihi:** {publish_date}

---

## 1. Fırçasız (Brushless) Motor Numaralandırması ve Mimarisi

FPV motorlarının üzerinde yazan `2207`, `2306` veya `2807` gibi dört haneli kodlar, motorun iç stator ölçülerini milimetre cinsinden belirtir:
- İlk 2 hane: Stator Çapı (Genişlik)
- Son 2 hane: Stator Yüksekliği (Boy)

Stator hacmi, motorun tork kapasitesini ve manyetik akı yoğunluğunu doğrudan belirler. Geniş statorlar yüksek hızlarda gaz tepkisini pürüzsüzleştirirken, yüksek statorlar ani tork patlamaları ve hızlı devir değişimi sağlar.

---

## 2. 2207 vs 2306 Stator Karşılaştırması ve Uçuş Karakteristiği

5 inç pervaneli freestyle ve yarış dronelarında en yaygın kullanılan iki stator mimarisi:

| Kriter | 2207 Stator (Uzun & İnce) | 2306 Stator (Geniş & Yassı) |
| :--- | :--- | :--- |
| **Tork Üretimi** | Çok yüksek alt ve orta devir torku | Dengeli, pürüzsüz üst devir torku |
| **Gaz Tepkisi (Throttle Punch)** | Anlık, agresif gaz tepkisi | Lineer, tahmin edilebilir gaz eğrisi |
| **Ağırlık** | ~32g - 35g (Biraz daha ağır) | ~30g - 33g (Daha hafif) |
| **İdeal Uçuş Tarzı** | Agresif Freestyle, Ani Kurtarmalar | Akıcı (Juicy) Freestyle, Pist Yarışları |
| **Verimlilik** | Ağır pervanelerle yüksek çekiş | Hafif pervanelerle yüksek verim |

---

## 3. Gerilim Mimarisi (4S vs 6S) ve KV Seçim Tablosu

Motorun KV değeri; 1 Volt gerilim uygulandığında motorun yüksüz durumda dakikada attığı devir sayısını (RPM/Volt) ifade eder:

| Pil Türü | Önerilen Motor KV Değeri | Uyumlu Pervane Hatvesi | İdeal Uçuş Sınıfı |
| :--- | :--- | :--- | :--- |
| **4S LiPo (14.8V - 16.8V)** | 2400KV - 2750KV | 5.1x3.0x3 - 5.1x4.3x3 | 5 İnç Klasik Sistemler |
| **6S LiPo (22.2V - 25.2V)** | 1750KV - 2020KV | 5.1x3.5x3 - 5.1x4.6x3 | 5 İnç Modern Freestyle & Yarış |
| **6S Long Range (7 İnç)** | 1300KV - 1500KV | 7x3.5x3 - 7x4.0x3 | 7 İnç Uzun Menzil & Dağ |
| **4S Cinewhoop (3 İnç)** | 3500KV - 4500KV | 3.0x3.0x3 - D90 Ducted | 3 İnç Kapalı Alan Çekim |

---

## 4. Pozitron Market Uyumlu Motor ve Pervane Kataloğu

Stoklarımızdaki birinci sınıf titanyum şaftlı fırçasız motorlar ve aerodinamik polikarbonat pervaneler:

{links_md}

> [İPUCU] **Teknik İpuçları:** Motor montaj vidalarının boyuna çok dikkat edin! Kol karbon fiberinden geçtikten sonra motor tabanına 1.5mm'den fazla giren vidalar motorun bakır sargılarına temas eder ve ilk gazda ESC'yi yakar.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Motorların Aşırı Isınması:** 30 saniyelik uçuştan sonra motor el değmeyecek kadar sıcaksa (>65°C), Betaflight PID sekmesinde D-Term kazancını düşürün veya pervane hatvesini (pitch) küçültün.
- **Pervane Titreşimi (Jello):** Dengelenmemiş veya darbe almış kırık/bükülmüş pervaneler kamera görüntüsünde dalgalanma (jello) yaratır. Pervanelerinizi düzenli değiştirin.
"""
    },
    {
        "id_code": "esc_protocols_and_bluejay",
        "title": "ESC Protokolleri ve Donanım Yazılımları: DShot300/600, Bluejay ve PWM Optimizasyonu",
        "component_focus": "Elektronik Hız Kontrolcüsü (ESC) ve DShot Protokolleri",
        "category_search": "ESC",
        "target_keywords": [
            "DShot600 ayarı", "Bluejay ESC firmware", "Bi-directional DShot",
            "RPM filtreleme", "48kHz PWM", "Pozitron Market ESC"
        ],
        "content_markdown": """# ESC Protokolleri ve Donanım Yazılımları: DShot300/600, Bluejay ve PWM Optimizasyonu

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `DShot600 ayarı, Bluejay ESC firmware, Bi-directional DShot, RPM filtreleme, 48kHz PWM, Pozitron Market ESC`  
**Yayın Tarihi:** {publish_date}

---

## 1. ESC Protokollerinin Evrimi ve Dijital DShot Sinyali

Elektronik Hız Kontrolcüleri (ESC), uçuş kartından gelen gaz komutlarını 3 fazlı fırçasız motor akımına dönüştürür. Eski nesil analog sinyallerin (PWM, Oneshot, Multishot) aksine dijital **DShot (Digital Shot)** protokolü, sinyalleri 16-bitlik dijital veri paketleri halinde gönderir.

DShot sinyali zamanlama hatalarını ortadan kaldırdığı için **gaz kalibrasyonu gerektirmez** ve her pakette hata kontrolü (CRC checksum) barındırır.

---

## 2. ESC Protokol Hızları ve Karşılaştırma Matrisi

Farklı DShot hızları ve sistem gereksinimleri:

| Protokol | Veri Hızı (Baudrate) | Döngü Süresi | Önerilen FC İşlemcisi | RPM Filtre Desteği |
| :--- | :--- | :--- | :--- | :--- |
| **DShot150** | 150 kbit/s | ~106 µs | STM32F411 / F405 | Sınırlı |
| **DShot300** | 300 kbit/s | ~53 µs | STM32F405 / F722 | Mükemmel (Çok Kararlı) |
| **DShot600** | 600 kbit/s | ~27 µs | STM32F722 / H7 | Mükemmel (Endüstri Standardı) |
| **DShot1200** | 1200 kbit/s | ~13 µs | STM32H7 (Yüksek Hassasiyet) | Yüksek Donanım Gerektirir |

---

## 3. Bluejay Firmware ve Bi-directional DShot Kurulumu

BLHeli_S tabanlı ekonomik ESC'leri modern RPM filtreleme teknolojisine kavuşturmanın yolu **Bluejay** yazılımıdır:

1. **ESC Configurator:** Web tarayıcısı üzerinden `esc-configurator.com` adresine gidin ve ESC'nizi bağlayın.
2. **Yazılım Seçimi:** En güncel kararlı Bluejay sürümünü ve motor büyüklüğünüze göre **48kHz** veya **24kHz** PWM frekansını seçin.
   - *24kHz:* Maksimum frenleme gücü ve yarış tepkisi.
   - *48kHz / 96kHz:* Daha pürüzsüz uçuş, sessiz motorlar ve %10'a varan uçuş süresi artışı.
3. **Betaflight Ayarı:** Betaflight PID sekmesinde **Bi-directional DShot** özelliğini aktif edin ve motor kutup sayısını (5 inç motorlar için genellikle `14`) girin.
4. **Hata Oranı Kontrolü:** Motors sekmesinde motorları hafifçe döndürün; Error oranının **%0.00** olduğundan emin olun.

---

## 4. Pozitron Market Yüksek Akımlı ESC Kataloğu

Aşırı akım korumalı ve yüksek kaliteli MOSFET bileşenlerine sahip 4'ü 1 arada ESC ürünlerimiz:

{links_md}

> [İPUCU] **Teknik İpuçları:** 4'ü 1 arada ESC kartınızın güç girişine mutlaka kartla birlikte gelen 35V 1000µF Low-ESR kapasitörü monte edin. Kapasitörsüz uçuşlarda motorların ürettiği ters voltaj sıçramaları MOSFET'leri delerek ESC'yi yakabilir.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Desync (Motor Senkronizasyon Kaybı):** Hızlı takla ve ani gaz açışlarında motorlardan birinin aniden durmasıdır. Motor Timing ayarını Bluejay veya BLHeli arayüzünde `Medium-High` veya `Auto` seviyesine getirin.
- **Motor Yönü Ters:** Pervane takılı değilken Betaflight Motors sekmesinde Motor Direction Wizard aracını kullanarak ters dönen motorun yönünü tek tıkla yazılımsal olarak düzeltin.
"""
    },
    {
        "id_code": "digital_hd_vs_analog_vtx",
        "title": "Dijital HD vs Analog FPV Görüntü Sistemleri: DJI O3, Walksnail Avatar ve HDZero İncelemesi",
        "component_focus": "FPV Görüntü Sistemleri ve Video Vericiler (VTX)",
        "category_search": "VTX",
        "target_keywords": [
            "Dijital FPV vs Analog", "DJI O3 Air Unit", "Walksnail Avatar HD",
            "HDZero gecikme süresi", "FPV video verici VTX", "Pozitron Market FPV"
        ],
        "content_markdown": """# Dijital HD vs Analog FPV Görüntü Sistemleri: DJI O3, Walksnail Avatar ve HDZero İncelemesi

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `Dijital FPV vs Analog, DJI O3 Air Unit, Walksnail Avatar HD, HDZero gecikme süresi, FPV video verici VTX, Pozitron Market FPV`  
**Yayın Tarihi:** {publish_date}

---

## 1. FPV Video İletim Teknolojilerinde Yeni Dönem

FPV uçuş deneyiminin kalbi olan görüntü aktarımı, son yıllarda geleneksel analog iletimden yüksek çözünürlüklü dijital HD sistemlere doğru büyük bir dönüşüm yaşamıştır. 480p çözünürlüklü karlı analog görüntüler yerini 1080p ve 4K dijital netliğe bırakırken, gecikme süresi (latency) ve penetrasyon dengesi sistem seçiminizi belirler.

DJI O3/O4, Walksnail Avatar ve HDZero ekosistemleri farklı pilot ihtiyaçlarına hitap eder.

---

## 2. Sistem Karşılaştırma Matrisi

Gözlük ve hava ünitesi (Air Unit) ekosistemlerinin teknik parametreleri:

| Sistem | Çözünürlük | Gecikme Süresi (Latency) | Dahili Kayıt | En Uygun Olduğu Alan |
| :--- | :--- | :--- | :--- | :--- |
| **DJI O3 Air Unit** | 1080p / 100fps | 28ms - 40ms (Değişken) | 4K 60fps Stabilize | Sinematik Çekim, Ticari, Freestyle |
| **Walksnail Avatar HD** | 1080p / 120fps | 22ms - 32ms (Değişken) | 1080p Dahili | Gece Uçuşu, Freestyle, Micro/Tinywhoop |
| **HDZero** | 720p / 90fps | 3ms - 14ms (Sabit Gecikme) | 720p Gözlük İçi | Profesyonel Pist Yarışları (Racing) |
| **Klasik Analog 5.8G** | 480p | < 10ms (Sabit Gecikme) | DVR Gözlük İçi | Bütçe Dostu, Yarış, Ultra Hafif |

---

## 3. Pit Modu ve Isı Yönetimi Kuralları

1. **Masaüstü Aşırı Isınması:** Dijital hava üniteleri uçuş rüzgarıyla soğuyacak şekilde tasarlanmıştır. Masada lehimleme ve Betaflight ayarı yaparken hava ünitesini 25mW **Pit Moduna** alın veya önüne harici bir masa fanı yerleştirin.
2. **Güç Kaynağı Filtrelemesi:** Dijital üniteler voltaj dalgalanmalarına karşı hassastır. Asla doğrudan ana pil hattından beslemeyin; uçuş kartı üzerindeki temiz filtrelenmiş 9V/12V BEC çıkışını kullanın.
3. **Kanal Planlaması:** Birlikte uçarken frekans çakışmasını önlemek için RaceBand kanal dağılımına uyun ve en az 40MHz kanal ayrımı bırakın.

---

## 4. Pozitron Market Görüntü ve VTX Sistemleri Kataloğu

Türkiye'nin en zengin dijital ve analog FPV görüntü aktarım bileşenleri:

{links_md}

> [İPUCU] **Teknik İpuçları:** DJI O3 Air Unit kullanıyorsanız dahili Gyroflow verisini kullanarak kurgu aşamasında aksiyon kameraya gerek kalmadan sinematik düzeyde sarsıntısız 4K görüntüler elde edebilirsiniz.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Görüntüde Pikselleşme ve Donma:** Anten konektörünün (U.FL / MMCX) tam oturduğundan ve kilitlendiğinden emin olun. Gevşek anten soketi VTX'in aşırı ısınmasına ve RF gücünün yanmasına yol açar.
- **OSD Ekranı Gelmiyor:** Betaflight Ports sekmesinde VTX'in bağlı olduğu UART'ta `VTX (MSP + Displayport)` seçeneğinin aktif olduğunu doğrulayın.
"""
    },
    {
        "id_code": "fpv_antennas_and_rf",
        "title": "FPV Anten Polarizasyonu ve RF Yerleşimi: RHCP, LHCP ve Lineer Anten Seçim Kriterleri",
        "component_focus": "FPV Antenleri ve Radyo Frekans (RF) Yayılımı",
        "category_search": "Anten",
        "target_keywords": [
            "RHCP vs LHCP anten", "FPV anten polarizasyonu", "dBi kazanç değeri",
            "patch anten yönlü", "omni anten", "Pozitron Market anten"
        ],
        "content_markdown": """# FPV Anten Polarizasyonu ve RF Yerleşimi: RHCP, LHCP ve Lineer Anten Seçim Kriterleri

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `RHCP vs LHCP anten, FPV anten polarizasyonu, dBi kazanç değeri, patch anten yönlü, omni anten, Pozitron Market anten`  
**Yayın Tarihi:** {publish_date}

---

## 1. Anten Polarizasyonunun Fiziksel Temelleri

5.8GHz video ve 2.4GHz kumanda frekanslarında RF dalgaları uzayda belirli bir polarizasyon düzleminde yayılır. Doğru anten seçimi; sinyal kopmalarını (fade), binalardan ve zeminden yansıyan sahte sinyalleri (multipath interference) engelleyerek kesintisiz bir görüntü aktarımı sağlar.

RF dalgası düz bir hat boyunca salınıyorsa **Doğrusal (Lineer)**; dairesel bir vida hareketi çizerek ilerliyorsa **Dairesel (Circular)** polarizasyon adını alır.

---

## 2. Polarizasyon Tipleri ve Karşılaştırması

| Anten Tipi | Polarizasyon | Çok Yollu Yansıma Koruması | İdeal Kullanım Alanı |
| :--- | :--- | :--- | :--- |
| **RHCP (Sağ El Dairesel)** | Saat Yönünde Dairesel | Çok Yüksek (%95+) | Standart FPV Freestyle & Yarış |
| **LHCP (Sol El Dairesel)** | Saat Yönü Tersi Dairesel | Çok Yüksek (%95+) | DJI Sistemleri & Kalabalık Pistler |
| **Lineer (Doğrusal)** | Dikey veya Yatay Düzlem | Düşük (Yansımalardan etkilenir) | Tinywhoop & Ultra Hafif Modeller |

### 2.1. Çapraz Polarizasyon Reddi (Cross-Polar Rejection)
Dairesel polarize bir dalga beton bir duvara çarptığında yön değiştirir (RHCP çarparsa LHCP olarak yansır). Drone'unuzda ve gözlüğünüzde RHCP anten varsa, duvardan yansıyan zayıflatıcı LHCP sinyali gözlük anteni tarafından filtrelenir. Bu sayede karlı ve gölgeli görüntü oluşmaz.

---

## 3. Omni (Tüm Yönlü) vs Patch (Yönlü) Anten Kullanımı (Diversity)

1. **Omni (Mantar / Yonca) Anten:** 360 derece küresel yayın yapar. Drone başınızın üstünde veya arkanızdayken kesintisiz sinyal sağlar; kazancı düşüktür (1.5 - 2.5 dBi).
2. **Patch (Yönlü Panel) Anten:** Önündeki 60-90 derecelik koni şeklinde yoğunlaşır. Çok uzak menzillerde ve penetrasyon gerektiren koridorlarda etkilidir; kazancı yüksektir (8 - 14 dBi).
3. **İdeal Gözlük Konfigürasyonu:** Diversity (çift alıcılı) FPV gözlüğünüzde 1 adet Omni anten ile 1 adet Patch anteni bir arada kullanarak hem yakın çevreyi hem de uzak menzili aynı anda kapsayın.

---

## 4. Pozitron Market Yüksek Kazançlı Anten Kataloğu

Eksenel oranı (Axial Ratio) 1.0'a yakın, düşük kayıplı profesyonel FPV antenleri:

{links_md}

> [İPUCU] **Teknik İpuçları:** Drone üzerindeki VTX antenini daima batarya ve karbon fiber gövdenin gölgesinde kalmayacak şekilde, arka TPU montaj aparatıyla 45 derece açıyla konumlandırın. Karbon fiber iletken bir malzemedir ve RF sinyalini bloke eder.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Yakın Mesafede Aşırı Karıncalanma:** Drone üzerindeki anten RHCP iken gözlükteki antenin LHCP olmasından kaynaklanabilir. İki antenin de aynı dönüş yönüne sahip olduğunu kontrol edin.
- **Anten Kırılması:** Pervanelerin kesme alanına yakın takılan antenler kaza anında pervaneye çarparak parçalanır; anten boyunu ve sert TPU yuvasını doğru ayarlayın.
"""
    },
    {
        "id_code": "soldering_and_smoke_stopper",
        "title": "Profesyonel Drone Lehimleme Teknikleri: 63/37 Lehim, Isı Yönetimi ve Smoke Stopper",
        "component_focus": "Drone Donanım Montajı ve Lehimleme Teknikleri",
        "category_search": "Lehim",
        "target_keywords": [
            "FPV lehimleme teknikleri", "63 37 lehim teli", "smoke stopper kullanımı",
            "soğuk lehim giderme", "lehim pastası flux", "Pozitron Market lehim"
        ],
        "content_markdown": """# Profesyonel Drone Lehimleme Teknikleri: 63/37 Lehim, Isı Yönetimi ve Smoke Stopper

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `FPV lehimleme teknikleri, 63 37 lehim teli, smoke stopper kullanımı, soğuk lehim giderme, lehim pastası flux, Pozitron Market lehim`  
**Yayın Tarihi:** {publish_date}

---

## 1. FPV Elektroniklerinde Lehimleme Kalitesinin Önemi

Bir FPV drone, uçuş sırasında saniyede binlerce kez titreşime, yüksek G kuvvetlerine ve 150 Amper'i aşan anlık akım patlamalarına maruz kalır. Zayıf veya soğuk yapılmış tek bir lehim noktası, havada motorun durmasına, voltaj kopmasına ve doğrudan kırıma neden olur.

Doğru havya sıcaklığı, kaliteli lehim alaşımı ve uygun pasta (flux) kullanımı, fabrika çıkışı parlak ve sağlam lehim eklemleri elde etmenin temelidir.

---

## 2. Lehim Teli Alaşımları ve Sıcaklık Ayar Tablosu

| Lehim Teli Alaşımı | Erime Noktası | Önerilen Havya Isısı (Küçük Padler) | Önerilen Havya Isısı (XT60 Güç Padi) |
| :--- | :--- | :--- | :--- |
| **63/37 Sn/Pb (Ötektik Kurşunlu)** | 183°C (Anında Katılaşır) | 350°C - 360°C | 390°C - 410°C |
| **60/40 Sn/Pb (Klasik Kurşunlu)** | 183°C - 190°C | 360°C - 370°C | 400°C - 420°C |
| **SAC305 (Kurşunsuz)** | 217°C | 380°C - 400°C | 420°C - 440°C |

### 2.1. Ötektik (Eutectic) 63/37 Lehimin Avantajı
Standart lehimler erime ile katılaşma arasında hamur kıvamında plastik bir faza girer. Bu esnada kablo hafifçe oynarsa "soğuk lehim" oluşur ve bağlantı gevşer. 63/37 alaşımı ise tam 183°C'de anında sıvıdan katıya geçer; bu nedenle FPV elektroniğinde en güvenilir lehim türüdür.

---

## 3. Adım Adım Kusursuz Lehimleme ve Test Protokolü

1. **Ön Lehimleme (Tinning):** Hem kart üzerindeki bakır pad'e hem de lehimlenecek silikon kablonun ucuna önce ayrı ayrı taze lehim uygulayın.
2. **Pasta (Flux) Kullanımı:** Pad üzerine bir damla kaliteli lehim pastası uygulayın. Flux oksitlenmeyi önler ve lehimin parlak bir kubbe şeklinde pede yapışmasını sağlar.
3. **Isı Temas Süresi:** Havyayı pad üzerinde 2 ila 3 saniyeden fazla tutmayın. Aşırı ısı karttaki bakır pad'in delaminasyonla kopmasına yol açar.
4. **Multimetre Süreklilik Testi:** Lehim bittikten sonra multimetreyi kısa devre (bip) moduna alın. Batarya kablosunun artı (+) ve eksi (-) uçları arasına dokundurun. Bip sesi duyuluyorsa kesinlikle enerji vermeyin!
5. **Smoke Stopper (Elektronik Sigorta):** İlk kez batarya takarken mutlaka araya bir Smoke Stopper bağlayın. Kısa devre varsa lamba anında kırmızıya dönerek kartların yanmasını saniyesinde engeller.

---

## 4. Pozitron Market Montaj, Havya ve Lehim Malzemeleri

Atölyenizde profesyonel montaj yapmanız için gerekli teknik lehimleme ürünleri:

{links_md}

> [İPUCU] **Teknik İpuçları:** XT60 kablosunu lehimlerken kalın bakır tel yüksek miktarda ısı emer. Havyanızın ucunu ince iğne uçtan geniş balta (chisel) uca değiştirin; böylece ısı transferi hızlanır ve kablo izolasyonu erimeden lehim tamamlanır.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Mat ve Taneli Lehim (Soğuk Lehim):** Kablonun lehim donarken hareket etmesinden veya yetersiz ısıdan kaynaklanır. Üzerine biraz flux sürün ve havyayı 1 saniye değdirip lehimi yeniden eritin.
- **Lehim Köprüsü (İki Padi Birbirine Yapıştırma):** Küçük UART padlerinde lehim birbiriyle temas ederse lehim emme fitili (wick) veya flux kullanarak fazla lehimi temizleyin.
"""
    },
    {
        "id_code": "betaflight_gps_rescue",
        "title": "Betaflight GPS Rescue (Otonom Kurtarma Modu) ve Pusula Kalibrasyon Rehberi",
        "component_focus": "GPS, Pusula ve Otonom Eve Dönüş (RTH)",
        "category_search": "GPS",
        "target_keywords": [
            "Betaflight GPS rescue ayarları", "drone eve dönüş modu",
            "M10 GPS pusula kalibrasyonu", "failsafe GPS kurtarma", "Pozitron Market GPS"
        ],
        "content_markdown": """# Betaflight GPS Rescue (Otonom Kurtarma Modu) ve Pusula Kalibrasyon Rehberi

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `Betaflight GPS rescue ayarları, drone eve dönüş modu, M10 GPS pusula kalibrasyonu, failsafe GPS kurtarma, Pozitron Market GPS`  
**Yayın Tarihi:** {publish_date}

---

## 1. Betaflight GPS Rescue Mantığı ve Güvenlik Felsefesi

Betaflight'ın GPS Rescue özelliği, tam otonom bir otopilot (iNav veya ArduPilot gibi) değildir; temel amacı sinyal kaybı (failsafe) veya video kararması durumunda drone'u pilotun bulunduğu konuma geri getirerek kontrolü yeniden kazanmasını sağlayan bir **acil durum can yeleğidir**.

Betaflight 4.4 ve 4.5 sürümleriyle birlikte GPS Rescue algoritması baştan yazılmış; acil iniş, irtifa basamaklama ve pusulasız yön bulma yetenekleriyle son derece güvenilir hale gelmiştir.

---

## 2. GPS Modülü Donanım Seçimi ve UART Bağlantısı

Yeni nesil M10 çipsetli (UBLOX M10050) GPS modülleri, eski M8 serisine göre uyduları 3 kat daha hızlı kilitler:

| GPS Modülü | Desteklenen Uydu Sistemleri | Tipik Kilitlenme Süresi | Önerilen Baudrate |
| :--- | :--- | :--- | :--- |
| **UBLOX M10 (Örn: M10-QMC5883L)** | GPS + GLONASS + Galileo + BeiDou | 15 - 35 saniye | 115200 Baud |
| **UBLOX M8N (Klasik)** | GPS + GLONASS | 45 - 90 saniye | 57600 Baud |

### 2.1. Donanım Bağlantı Şeması
- GPS `TX` -> Uçuş Kartı `RX`
- GPS `RX` -> Uçuş Kartı `TX`
- GPS `VCC` -> Temiz 5V BEC
- GPS `GND` -> Ortak Toprak
- Pusula (Varsa) `SDA` ve `SCL` uçları uçuş kartının `I2C` padlerine bağlanmalıdır.

---

## 3. Betaflight 4.5 GPS Rescue Konfigürasyon Adımları

1. **Minimum Uydu Sayısı:** Güvenli bir kalkış noktası (Home Point) kaydı için minimum uydu sayısını en az **8** olarak belirleyin.
2. **Kurtarma İrtifası (Initial Altitude):** Uçtuğunuz bölgedeki en yüksek ağaç ve binaları hesaba katarak güvenli irtifayı ayarlayın (Örn: `Max Altitude` moduyla 50 metre). Drone önce 50 metreye tırmanır, ardından eve doğru yönelir.
3. **Eve Dönüş Hızı:** `Ground Speed` değerini 15 - 20 m/s (~50-70 km/s) olarak tanımlayın.
4. **Failsafe Aksiyonu:** Failsafe sekmesinde `Stage 2` ayarını **GPS Rescue** olarak seçin.
5. **Kumanda Switch Ataması:** Modes sekmesinde acil durumlarda elle tetikleyebilmeniz için bir switch'e `GPS Rescue` atayın.

---

## 4. Pozitron Market GPS ve Pusula Donanımları Kataloğu

Hızlı kilitlenen M10 çipli hafif FPV GPS ve telemetri bileşenlerimiz:

{links_md}

> [İPUCU] **Teknik İpuçları:** GPS modülünü drone'un arka kısmında, karbon fiber gövdeden en az 3cm yüksekte duracak şekilde 3D TPU kule üzerine monte edin. Aksiyon kameranın arkasına yakın monte edilen GPS'ler kamera gürültüsü yüzünden uydu bulamaz.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Sanity Check Failsafe (Motorların Anında Durması):** Drone eve dönerken irtifa kaybediyorsa veya uyduları kaybederse Betaflight sistemi korumak için motorları durdurabilir. Açık arazide kalkış yapmadan önce 10+ uydu kilitlendiğinden emin olun.
- **Pusula Hatası:** Manyetometre motor kablolarından geçen yüksek akımın yarattığı manyetik alandan etkilenir. Sorun devam ederse Betaflight'ta pusulayı devre dışı bırakıp GPS yön bulma modunu seçin.
"""
    },
    {
        "id_code": "carbon_fiber_frame_geometry",
        "title": "Karbon Fiber Gövde Geometrisi: True-X, Deadcat ve Stretch-X Uçuş Karakteristikleri",
        "component_focus": "Drone Karbon Fiber Gövdeleri ve Mekanik Tasarım",
        "category_search": "Gövde",
        "target_keywords": [
            "True-X vs Deadcat gövde", "FPV frame seçimi", "karbon fiber drone gövdesi",
            "5 inç freestyle frame", "Pozitron Market gövde"
        ],
        "content_markdown": """# Karbon Fiber Gövde Geometrisi: True-X, Deadcat ve Stretch-X Uçuş Karakteristikleri

**Yazar:** Pozitron Market Donanım & FPV Ar-Ge Ekibi  
**Hedef Arama Terimleri:** `True-X vs Deadcat gövde, FPV frame seçimi, karbon fiber drone gövdesi, 5 inç freestyle frame, Pozitron Market gövde`  
**Yayın Tarihi:** {publish_date}

---

## 1. Karbon Fiber Gövde (Frame) Tasarımının Önemi

FPV drone'un iskeletini oluşturan gövde; tüm elektronik bileşenleri taşırken aynı zamanda uçuş dinamiğini, aerodinamik sürtünmeyi ve motor titreşimlerinin uçuş kartına iletimini belirler. Yüksek kaliteli Toray T700 karbon fiber malzeme, darbe emilimini artırırken rijitliği korur.

Kolların yerleşim açısı olan gövde geometrisi, drone'un takla (roll) ve yunuslama (pitch) eksenlerindeki davranışını baştan aşağı değiştirir.

---

## 2. Gövde Geometrileri ve Uçuş Karakteristikleri

| Gövde Tipi | Kol Yerleşimi | Roll / Pitch Dengesi | Kamerada Pervane Görünürlüğü | İdeal Kullanım |
| :--- | :--- | :--- | :--- | :--- |
| **True-X** | Kollar eşit kare açıdadır (90°) | Kusursuz Simetrik Eksen Dengesi | Pervaneler kamerada görünür | Saf Freestyle & Akrobasi |
| **Deadcat (DC)** | Ön kollar geriye ve yana açıktır | Pitch ekseni biraz daha geniştir | **Pervaneler kadrajda kesinlikle görünmez** | Sinematik HD Çekim, DJI O3 |
| **Stretch-X** | Kollar ileri-geri uzatılmıştır | Roll ekseni çok çevik, Pitch kararlı | Yüksek hızda stabilite sağlar | Profesyonel Kapalı/Açık Pist Yarışları |
| **Wide-X (Squashed-X)**| Kollar yanlara doğru açılmıştır | Stabil kamera açısı | Kısmen görünmez | Genel Serbest Stil |

---

## 3. Karbon Fiber Kalınlıkları ve Titreşim Sönümleme

1. **Kol Kalınlığı (Arm Thickness):** 5 inç freestyle gövdelerde en az 5mm veya 6mm kol kalınlığı tercih edilmelidir. İnce kollar yüksek gazda esner ve jiroskopa zararlı rezonans frekansları iletir.
2. **Vida Sıkılığı:** Karbon fiber gövde vidalarını aşırı sıkmayın (karbon tabakaları ezilmemelidir). Ancak gevşek vidalar doğrudan uçuşta salınıma (oscillation) yol açar; vida sabitleyici (Mavi Loctite) kullanın.
3. **TPU Parçalar:** Kol uçlarına takılan TPU koruyucular sert zemin inişlerinde karbonun ayrışmasını (delamination) engeller.

---

## 4. Pozitron Market Karbon Fiber Gövde Kataloğu

Hafif, modüler ve kırılmaya karşı dirençli birinci sınıf karbon fiber gövde kitlerimiz:

{links_md}

> [İPUCU] **Teknik İpuçları:** Karbon fiber lifleri yüksek oranda elektriği iletir! Açıkta kalan lehim bağlantılarının veya ESC kartının karbon fibere doğrudan temas etmediğinden emin olun, aksi halde ani kısa devre gerçekleşir.

---

## 5. Sık Karşılaşılan Sorunlar ve Çözümleri

- **Kamera Açısı Titremesi:** Yüksek hızlarda FPV kamerası sallanıyorsa TPU montaj vidalarını sıkın ve kamera yan plakalarına titreşim önleyici silikon halkalar ekleyin.
- **Karbon Kol Ayrışması:** Sert kırım sonrası kol ucundaki karbon katmanları ayrılmışsa üzerine ince bir damla siyanoakrilat (japon yapıştırıcısı) damlatıp kıskaçla sıkıştırarak onarabilirsiniz.
"""
    }
]


class TechnicalSeoAgent:
    """
    SUBAGENT 4: TEKNİK DOKÜMANTASYON VE SEO AJANI (CONTENT & SEO AGENT)
    - Pozitron Market için teknik derinliği yüksek rehberler ve bağlantı şemaları üretir.
    - Daha önce yazılmış rehberleri kontrol eder; mükerrer konu ve başlıkları KESİNLİKLE engeller.
    - Tüm rehberleri eksiksiz Türkçe karakterler (ç, ğ, ı, ö, ş, ü, İ) kullanarak yazar.
    - Pozitron Market ürünlerine ilgili kategoriden dinamik iç linkleme (internal linking) yapar.
    """
    def __init__(self, gemini_api_key: str = ""):
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        self._ensure_api_key()

    def _ensure_api_key(self):
        if not self.gemini_api_key:
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT gemini_api_key FROM instagram_agent_config LIMIT 1")
                row = cursor.fetchone()
                if row and row[0]:
                    self.gemini_api_key = row[0].strip()
                if not self.gemini_api_key:
                    cursor.execute("SELECT gemini_api_key FROM reddit_agent_config LIMIT 1")
                    row2 = cursor.fetchone()
                    if row2 and row2[0]:
                        self.gemini_api_key = row2[0].strip()
                conn.close()
            except Exception:
                pass

    def _get_matching_products(self, keyword: str, limit: int = 4) -> List[Dict]:
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

    def get_covered_topics(self) -> List[Dict]:
        """Retrieves all currently covered guides from database."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, slug, title, component_focus, target_keywords FROM seo_articles ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def is_topic_covered(self, component_focus: str, title: str = "") -> bool:
        """
        Checks if a given topic or guide has already been published.
        Uses exact slug match and semantic keyword overlap comparison.
        """
        covered = self.get_covered_topics()
        if not covered:
            return False

        candidate_slug = turkish_to_slug(component_focus)
        candidate_keywords = normalize_topic_keywords(f"{component_focus} {title}")

        for art in covered:
            exist_slug = turkish_to_slug(art.get("component_focus") or "")
            if candidate_slug == exist_slug:
                return True

            exist_title = art.get("title", "").lower()
            if component_focus.lower() in exist_title:
                return True

            # Semantic keyword overlap
            exist_keywords = normalize_topic_keywords(f"{art.get('title', '')} {art.get('component_focus', '')}")
            if candidate_keywords and exist_keywords:
                overlap = len(candidate_keywords.intersection(exist_keywords))
                total_min = min(len(candidate_keywords), len(exist_keywords))
                if total_min > 0 and (overlap / total_min) >= 0.70:
                    return True

        return False

    def get_next_unwritten_topic(self) -> Dict:
        """
        Finds the next unwritten topic from the curated topic repository.
        If all curated topics are covered, generates a fresh unique sub-topic.
        """
        for topic in TOPIC_REPOSITORY:
            if not self.is_topic_covered(topic["component_focus"], topic["title"]):
                return topic

        # If all predefined topics are covered, generate an advanced specialized topic
        covered = self.get_covered_topics()
        count = len(covered) + 1
        return {
            "id_code": f"advanced_fpv_topic_{count}",
            "title": f"İleri Düzey FPV Mühendisliği ve Telemetri Optimizasyonu Rehberi #{count}",
            "component_focus": f"İleri Düzey FPV Mühendisliği ve Telemetri Optimizasyonu #{count}",
            "category_search": "Uçuş",
            "target_keywords": [
                "ileri düzey FPV", "telemetri optimizasyonu", "drone mühendisliği", "Pozitron Market"
            ],
            "content_markdown": None
        }

    def _generate_with_gemini(self, topic: Dict, internal_links: List[Dict]) -> Optional[Dict]:
        """Calls Gemini to generate a fresh, engineering-grade technical guide with 100% Turkish characters."""
        self._ensure_api_key()
        if not self.gemini_api_key:
            return None

        links_context = "\n".join([f"- [{item['name']}](https://pozitronmarket.com/products/{item['slug']})" for item in internal_links])

        covered = self.get_covered_topics()
        covered_titles = [c.get("title", "") for c in covered[:10]]
        covered_str = "\n".join([f"- {t}" for t in covered_titles])

        prompt = f"""Sen Türkiye'nin en büyük FPV drone ve robotik donanım platformu Pozitron Market'in (pozitronmarket.com) Baş Donanım ve Havacılık Mühendisisin.

GÖREV:
Aşağıdaki konu hakkında, FPV pilotları ve robotik mühendisleri için teknik derinliği en üst düzeyde (Engineering-grade), eksiksiz bir rehber ve SEO makalesi yaz.

HEDEF KONU:
- Odak: {topic['component_focus']}
- Örnek Başlık: {topic['title']}
- Anahtar Kelimeler: {", ".join(topic.get('target_keywords', []))}

DAHA ÖNCE YAZILMIŞ REHBERLER (KESİNLİKLE BUNLARI TEKRARLAMA VE KOPYALAMA):
{covered_str}

KRİTİK KURALLAR:
1. EKSİKSİZ TÜRKÇE KARAKTER KULLANIMI: Tüm metin kesinlikle imla kurallarına uygun, tam Türkçe karakterler (ç, ğ, ı, ö, ş, ü, Ç, Ğ, İ, Ö, Ş, Ü) kullanılarak yazılmalıdır. Asla İngilizce ASCII harf ikamesi ("Ucus", "Secimi", "sarj", "Ipuclari") yapma!
2. SIFIR EMOJİ KURALI: Metinde kesinlikle hiçbir emoji kullanma.
3. TEKNİK DERİNLİK VE ŞEMALAR:
   - Giriş ve donanım mimarisi (Mikroişlemci, fiziksel prensipler, standartlar).
   - Donanım bağlantı / pinout veya karşılaştırma tablosu (Markdown formatında | ... | ... |).
   - Adım adım konfigürasyon, lehimleme veya kalibrasyon yönergeleri.
   - Sık karşılaşılan sorunlar ve çözümleri.
4. İÇ LİNKLEME: Rehberin uygun bir bölümüne şu Pozitron Market ürün linklerini ekle:
{links_context}
5. ÇIKTI FORMATI: Sadece geçerli bir JSON çıktısı döndür. Kod bloğu dışında ek metin yazma:
{{
  "title": "Kusursuz Türkçe Başlık",
  "component_focus": "{topic['component_focus']}",
  "target_keywords": ["anahtar1", "anahtar2"],
  "content_markdown": "# Başlık\\n\\nİçerik..."
}}
"""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 3000,
                "responseMimeType": "application/json"
            }
        }

        for model in self.models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=25) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    candidate = res_data.get('candidates', [{}])[0]
                    text_content = candidate.get('content', {}).get('parts', [{}])[0].get('text', '')
                    if text_content:
                        clean_json = re.sub(r'^```json\s*', '', text_content.strip())
                        clean_json = re.sub(r'\s*```$', '', clean_json)
                        parsed = json.loads(clean_json)
                        if parsed.get("content_markdown") and len(parsed["content_markdown"]) > 400:
                            return parsed
            except Exception as e:
                print(f"[SEO Agent] Gemini attempt with {model} notice: {e}")
                continue

        return None

    def generate_article(self, component_focus: str = None, target_keywords: List[str] = None, force: bool = False) -> Dict:
        """
        Generates a comprehensive, engineering-grade technical guide.
        - Checks if topic is already covered; if covered and not forced, picks the next unwritten topic.
        - Enforces 100% Turkish character usage.
        - Integrates matching products from Pozitron Market catalog.
        """
        # Step 1: Determine Topic & Check Duplication
        selected_topic = None
        if component_focus:
            # Check if this topic has already been written
            if not force and self.is_topic_covered(component_focus):
                print(f"[SEO Agent] Konu '{component_focus}' daha önce yazılmış. Tekrara düşmemek için sıradaki yazılmamış konuya geçiliyor.")
                selected_topic = self.get_next_unwritten_topic()
            else:
                # Find matching topic in repository or use requested
                for t in TOPIC_REPOSITORY:
                    if t["component_focus"].lower() == component_focus.lower():
                        selected_topic = t
                        break
                if not selected_topic:
                    selected_topic = {
                        "id_code": turkish_to_slug(component_focus),
                        "title": f"{component_focus}: Kapsamlı Mühendislik ve Donanım Rehberi",
                        "component_focus": component_focus,
                        "category_search": component_focus.split()[0],
                        "target_keywords": target_keywords or [component_focus, "Pozitron Market", "FPV donanım"],
                        "content_markdown": None
                    }
        else:
            selected_topic = self.get_next_unwritten_topic()

        final_focus = selected_topic["component_focus"]
        final_keywords = target_keywords or selected_topic.get("target_keywords", [])
        keywords_str = ", ".join(final_keywords)

        # Step 2: Retrieve matching products for internal linking
        cat_search = selected_topic.get("category_search", "FPV")
        matched_products = self._get_matching_products(cat_search, 4)
        if len(matched_products) < 2:
            matched_products.extend(self._get_matching_products("FPV", 4 - len(matched_products)))

        internal_links = []
        for p in matched_products[:4]:
            internal_links.append({
                "sku": p["sku"],
                "name": p["name_tr"],
                "slug": p.get("slug", p["sku"].lower()),
                "url": f"https://pozitronmarket.com/products/{p['slug']}"
            })

        links_md = "\n".join([f"- [{item['name']}]({item['url']})" for item in internal_links])

        # Step 3: Content Generation (Gemini AI or Curated Deep Technical Template)
        ai_article = self._generate_with_gemini(selected_topic, internal_links)
        if ai_article and ai_article.get("content_markdown"):
            title = ai_article.get("title", selected_topic["title"])
            content = ai_article["content_markdown"]
            if "{links_md}" in content:
                content = content.replace("{links_md}", links_md)
            elif "https://pozitronmarket.com" not in content and links_md:
                content += f"\n\n## Pozitron Market Uyumlu Donanım ve Yedek Parça Listesi\n\n{links_md}\n"
        else:
            # Fallback to curated deep technical guide
            raw_markdown = selected_topic.get("content_markdown")
            if not raw_markdown:
                raw_markdown = TOPIC_REPOSITORY[0]["content_markdown"]

            now_str = datetime.now().strftime('%d.%m.%Y')
            content = raw_markdown.replace("{publish_date}", now_str).replace("{links_md}", links_md)
            title = selected_topic["title"]

        # Step 4: Slug & Storage
        slug_base = turkish_to_slug(final_focus)
        slug = f"rehber-{slug_base}-{int(datetime.now().timestamp())}-{uuid.uuid4().hex[:4]}"

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO seo_articles (slug, title, component_focus, target_keywords, internal_links_json, content_markdown, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                slug, title, final_focus, keywords_str,
                json.dumps(internal_links, ensure_ascii=False),
                content, datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"[SEO Agent] Error saving article to db: {ex}")

        return {
            "slug": slug,
            "title": title,
            "component_focus": final_focus,
            "target_keywords": final_keywords,
            "internal_links": internal_links,
            "content_markdown": content,
            "published_at": datetime.now().isoformat()
        }

    def get_articles(self, limit: int = 50) -> List[Dict]:
        """Fetches stored SEO guides with proper decoding."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM seo_articles ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            self.generate_article()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM seo_articles ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            conn.close()

        articles = []
        for r in rows:
            links = []
            if r["internal_links_json"]:
                try:
                    links = json.loads(r["internal_links_json"])
                except Exception:
                    links = []
            articles.append({
                "id": r["id"],
                "slug": r["slug"],
                "title": r["title"],
                "component_focus": r["component_focus"],
                "target_keywords": r["target_keywords"],
                "internal_links": links,
                "content_markdown": r["content_markdown"],
                "created_at": r["created_at"]
            })
        return articles

    def deduplicate_existing_articles(self) -> Dict:
        """
        Cleans up existing duplicate articles in the database.
        Keeps 1 distinct version per topic with proper Turkish characters.
        Populates missing curated topics to provide a rich catalog.
        """
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, slug, title, component_focus, target_keywords, content_markdown, created_at FROM seo_articles ORDER BY id ASC")
        all_rows = cursor.fetchall()

        seen_concepts = set()
        ids_to_keep = []
        ids_to_delete = []

        for row in all_rows:
            focus = row["component_focus"] or ""
            title = row["title"] or ""
            norm_words = tuple(sorted(list(normalize_topic_keywords(f"{focus} {title}"))))
            
            # If normalized keyword signature has already been seen, mark for deletion
            is_dup = False
            for seen in seen_concepts:
                overlap = len(set(norm_words).intersection(set(seen)))
                min_len = min(len(norm_words), len(seen))
                if min_len > 0 and (overlap / min_len) >= 0.70:
                    is_dup = True
                    break

            if is_dup:
                ids_to_delete.append(row["id"])
            else:
                seen_concepts.add(norm_words)
                ids_to_keep.append(row["id"])

        if ids_to_delete:
            cursor.execute(f"DELETE FROM seo_articles WHERE id IN ({','.join(map(str, ids_to_delete))})")
            conn.commit()

        # Update remaining articles with proper Turkish characters in titles if they had ASCII versions
        cursor.execute("SELECT id, title, component_focus FROM seo_articles")
        current_rows = cursor.fetchall()
        for r in current_rows:
            old_title = r["title"]
            old_focus = r["component_focus"]
            new_title = old_title.replace("Ucus", "Uçuş").replace("Secimi", "Seçimi").replace("Ipuclari", "İpuçları").replace("Donanim", "Donanım")
            new_focus = old_focus.replace("Ucus", "Uçuş").replace("Secimi", "Seçimi").replace("Ipuclari", "İpuçları").replace("Donanim", "Donanım")
            if new_title != old_title or new_focus != old_focus:
                cursor.execute("UPDATE seo_articles SET title = ?, component_focus = ? WHERE id = ?", (new_title, new_focus, r["id"]))
        conn.commit()
        conn.close()

        # Ensure we have a rich diverse set of articles from repository
        for topic in TOPIC_REPOSITORY:
            if not self.is_topic_covered(topic["component_focus"], topic["title"]):
                self.generate_article(component_focus=topic["component_focus"], target_keywords=topic["target_keywords"], force=True)

        # Sync static export
        try:
            from export_data import export_static_data
            export_static_data()
        except Exception as ee:
            print(f"[SEO Agent] Error during static export: {ee}")

        return {
            "deleted_duplicate_count": len(ids_to_delete),
            "kept_count": len(ids_to_keep)
        }
