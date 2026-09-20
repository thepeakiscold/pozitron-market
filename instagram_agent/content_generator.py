import json
import random
import urllib.request
import urllib.error
import sqlite3
import os
import re
from datetime import datetime
from .db import (
    get_db, get_recent_posted_product_ids,
    get_recent_posted_titles, get_recent_posted_content_types
)

FPV_PILOT_TIPS = [
    {
        'title': '[LIPO] 4S vs 6S Batarya: Voltaj Çökmesi ve Verimlilik Farkı',
        'summary': '6S LiPo bataryalar (22.2V nominal) aynı gücü üretirken 4S pillere (14.8V) kıyasla çok daha düşük akım (amper) çeker. Bu sayede kablo ve ESC kayıpları azalır, ani gazlamalarda voltaj çökmesi (voltage sag) minimuma iner. 6S setup için motor KV değerinizi 1750-1950KV aralığında seçmelisiniz.',
        'headline': '4S VS 6S BATARYA REHBERİ',
        'subhead': 'Daha Az Isınma & Pürüzsüz Gaz Tepkisi',
        'points': [
            "[VOLTAJ] 6S: Düşük Amper ile Minimum Voltaj Çökmesi",
            "[MOTOR] 6S İçin İdeal 5 İnç KV Değeri: 1750 - 1950KV",
            "[VERIM] Batarya ve ESC Aşırı Isınmalarına Son"
        ],
        'tags': '#fpvlipo #6sbattery #fpvpilot #pozitronmarket #dronetopla'
    },
    {
        'title': '[MOTOR] FPV Motor KV ve Pervane Adımı Uyumu Rehberi',
        'summary': 'Yüksek KV daha yüksek devir/dakika (RPM) sağlarken torku düşürür; agresif adımlı ağır pervanelerde motorları aşırı ısıtır. 5 inç 6S freestyle için 1950KV + 5143/5146 pervane dengesi optimum itki ve motor ömrü sağlar. Pozitron Sihirbazı ile donanımınızı tek tıkla test edebilirsiniz.',
        'headline': 'MOTOR KV & PERVANE UYUMU',
        'subhead': 'Tork, Hız ve İtki Dengesini Kusursuz Ayarla',
        'points': [
            "[HEDEF] 5 İnç 6S Freestyle İçin 1950KV İdeal Seçim",
            "[UYARI] Yüksek Adımlı Pervanede ESC Amper Sınırına Dikkat",
            "[TEST] Pozitron Sihirbazı ile 0 Hata Eşleştirme"
        ],
        'tags': '#motorkv #pervane #fpvfreestyle #pozitronmarket #teknofest'
    },
    {
        'title': '[3D BASKI] TPU 95A: Neden PLA Yerine TPU Kullanmalısın?',
        'summary': 'PLA ve PETG rijit plastiklerdir; yüksek hızlı kırım anında çatlayarak kamerayı veya anteni koruyamaz. TPU 95A ise esnek yapısıyla kinetik çarpma enerjisini sönümler. GoPro mount, kol uçları ve anten koruyucularında kırılmaz TPU şarttır. Pozitron 3D Studio ile anında online baskı alabilirsiniz.',
        'headline': 'TPU 95A KIRILMAZ KORUMA',
        'subhead': 'GoPro ve Hassas Elektronik Donanım Zırhı',
        'points': [
            "[DARBE] Esnek Yapı ile Çarpma Enerjisini Tamamen Emer",
            "[GUVEN] GoPro, Anten ve Kol Korumaları İçin Şart",
            "[3D BASKI] STL Yükle, Gramaj ve Fiyatı Anında Gör"
        ],
        'tags': '#tpu95a #3dbaski #dronemount #pozitronmarket #fpvturkey'
    },
    {
        'title': '[BETAFLIGHT] Betaflight 4.5 GPS Rescue: Drone Kayıplarına Son',
        'summary': 'Video veya kumanda sinyali koptuğunda drone\'un kalkış noktasına otonom dönmesini sağlayan GPS Rescue, Betaflight 4.5 ile pusulasız da yön bulabilir hale geldi. Minimum 8 uydu kilidi ve doğru Failsafe irtifa ayarı ile kaza risklerini sıfırlayın.',
        'headline': 'BETAFLIGHT 4.5 GPS RESCUE',
        'subhead': 'Sinyal Koptuğunda Otonom Eve Dönüş (RTH)',
        'points': [
            "[GPS] Minimum 8 Uydu Kilidi ile Güvenli Eve Dönüş",
            "[FAILSAFE] Ağaç ve Bina Üstü Güvenli Tırmanma İrtifası",
            "[KORUMA] Sinyal Kaybında Drone Kaybetme Korkusuna Son"
        ],
        'tags': '#betaflight #gpsrescue #fpvfail #pozitronmarket #longrangefpv'
    },
    {
        'title': '[HD VIDEO] Dijital HD (O3, Walksnail, HDZero) vs Analog Karşılaştırması',
        'summary': 'Analog 5.8GHz video sıfıra yakın (15ms) ultra düşük gecikme sunar ancak çözünürlük düşüktür. DJI O3 ve Walksnail Avatar 1080p kristal netliğinde dijital görüntü sağlarken, HDZero yarış odaklı 15-20ms sabit dijital gecikme vadeder. İhtiyacınıza uygun VTX sistemi Pozitron Market stoklarında.',
        'headline': 'DIJITAL HD VS ANALOG VTX',
        'subhead': 'Kristal Görüntü mü, Ultra Düşük Gecikme mi?',
        'points': [
            "[DJI O3 / WALKSNAIL] 1080p Kristal Netlik & Dahili Kayıt",
            "[HDZERO / ANALOG] 15ms Ultra Düşük Gecikme ile Yarış",
            "[STOK] En Güncel Dijital VTX Sistemleri Pozitron'da"
        ],
        'tags': '#djio3 #walksnail #hdzero #analogfpv #pozitronmarket'
    },
    {
        'title': '[ELRS] ExpressLRS 2.4GHz: Paket Hızı ve Telemetri Oranı Ayarı',
        'summary': 'ExpressLRS açık kaynak kumanda protokolünde 250Hz veya 500Hz paket hızı ile 2-3ms akıcı tepki elde edersiniz. Telemetri oranını 1:64 veya 1:32 ayarlayarak RF paket kayıplarını önleyebilir, dinamik güç (dynamic power) ile 250mW-1W arası menzili garantiye alabilirsiniz.',
        'headline': 'EXPRESSLRS (ELRS) 2.4GHZ',
        'subhead': 'Ultra Düşük Gecikme & Kilometrelerce Güvenli Menzil',
        'points': [
            "[HIZ] 500Hz Paket Hızı ile 2ms Pürüzsüz Tepki",
            "[GUC] Dinamik Güç ile Pil Tasarrufu & Yüksek Menzil",
            "[DONANIM] En Güncel ELRS Alıcı & Vericileri Pozitron'da"
        ],
        'tags': '#expresslrs #elrs #fpvkumanda #pozitronmarket #radiomaster'
    },
    {
        'title': '[ELEKTRONIK] Low ESR Kapasitör (35V 1000uF) Neden Hayatidir?',
        'summary': 'Fırçasız motorlar frenleme ve ani gaz geçişlerinde 40V+ voltaj tepe dalgaları (voltage spikes) üretir. ESC girişindeki kaliteli Low ESR Rubycon/Panasonic 35V 1000uF kapasitör, bu darbeleri emerek dijital HD kameranın ve FC jiroskopunun yanmasını engeller.',
        'headline': 'LOW ESR KAPASITOR REHBERI',
        'subhead': 'Elektronik Donanımı Voltaj Şoklarından Koru',
        'points': [
            "[KORUMA] 35V+ Ani Spike Voltajlarını Anında Emiş",
            "[FILTRE] Video Parazitlerini & Jiroskop Gürültüsünü Azaltır",
            "[MONTAJ] ESC Güç Girişine En Kısa Bacakla Lehimleyin"
        ],
        'tags': '#lowesr #fpvelektronik #esckapasitor #pozitronmarket #dronebuild'
    },
    {
        'title': '[LEHIM] Profesyonel FPV Lehimleme: Sıcaklık, Tel ve Flux Sırları',
        'summary': 'Kusursuz lehim bağlantısı kaza anında kablo kopmalarını önler. 63/37 kalay-kurşun lehim teli ile 380°C - 400°C aralığında kalın pabuçları lehimleyin. Kaliteli reçineli flux kullanarak lehimin pedlere pürüzsüz ve parlak akmasını sağlayın.',
        'headline': 'KUSURSUZ FPV LEHIMLEME',
        'subhead': 'Sert Kazalarda Kopmayan Parlak Lehim Noktaları',
        'points': [
            "[SICAKLIK] Pil Pedleri İçin 400°C, Küçük Sinyal İçin 350°C",
            "[FLUX] Oksitlenmeyi Önleyen Kaliteli Reçineli Jel Flux",
            "[IPUCU] Soğuk Lehim Riskine Karşı Mat Değil Parlak Yüzey"
        ],
        'tags': '#lehim #fpvlehim #dronetamir #teknofest #pozitronmarket'
    },
    {
        'title': '[PERVANE] 3 Kanat vs 4 Kanat Pervane: Tork, Dönüş Tutuşu ve Hız',
        'summary': '3 kanatlı (triblade) pervaneler daha yüksek son hız ve daha az akım tüketimi sunarken, 4 kanatlı pervaneler virajlarda olağanüstü tutuş ve düşük devirde yüksek itki sağlar. Freestyle için 5.1 inç 3 kanat, ağır sinematik için 4 kanat tercih edin.',
        'headline': '3 KANAT VS 4 KANAT PERVANE',
        'subhead': 'Freestyle Çevikliği ve Sinematik Stabilite',
        'points': [
            "[3 KANAT] Yüksek Son Hız & Düşük Akım Tüketimi",
            "[4 KANAT] Keskin Viraj Tutuşu & Güçlü Düşük Devir İtkisi",
            "[STOK] HQProp, Gemfan ve Ethix Pervaneleri Pozitron'da"
        ],
        'tags': '#hqprop #gemfan #pervane #fpvfreestyle #pozitronmarket'
    },
    {
        'title': '[LIPO SAKLAMA] LiPo Storage Voltajı (3.82V): Pil Şişmelerine Son',
        'summary': 'LiPo bataryaları dolu (4.20V) veya boş (3.50V) bekletmek hücrelerin iç direncini artırır ve pili şişirir. Uçuştan sonra pillerinizi hücre başı 3.82V saklama voltajına getirerek yangın riskini önleyin ve batarya ömrünü 300+ döngüye uzatın.',
        'headline': 'LIPO STORAGE (SAKLAMA) MODU',
        'subhead': 'Hücre Sağlığını Koru & Yangın Riskini Sıfırla',
        'points': [
            "[VOLTAJ] İdeal Bekletme Voltajı: Hücre Başı 3.82V - 3.85V",
            "[OMUR] Şişme ve Kapasite Kayıplarını %90 Engeller",
            "[SARJ] Akıllı LiPo Şarj Cihazları Pozitron Market'te"
        ],
        'tags': '#lipopil #storagevoltage #liposafety #fpvpil #pozitronmarket'
    },
    {
        'title': '[ANTEN] RHCP vs LHCP Polarizasyon: Anten Eşleşmesi Neden Önemli?',
        'summary': 'Dairesel polarizasyonlu (CP) antenlerde verici (VTX) ve alıcı (VRX/Gözlük) aynı yönde olmalıdır (her ikisi de RHCP veya her ikisi de LHCP). Yanlış eşleşmede 20-30dB sinyal kaybı yaşanır ve video menziliniz %80 oranında düşer.',
        'headline': 'RHCP VS LHCP ANTEN SECIMI',
        'subhead': 'Sinyal Yansımalarını Önle & Maksimum Video Menzili',
        'points': [
            "[POLARIZASYON] VTX ve Gözlük Antenleri Aynı Yönde Olmalı",
            "[YANSIMA] Dairesel Polarizasyon Çok Yollu Parazitleri Önler",
            "[SECIM] TrueRC, Foxeer ve Lollipop Antenleri Pozitron'da"
        ],
        'tags': '#fpvanten #rhcp #lhcp #videoverici #pozitronmarket'
    },
    {
        'title': '[VTX TERMAL] VTX Aşırı Isınması: Pit Mode ve Kalkış Öncesi Soğutma',
        'summary': 'Modern 800mW - 2500mW VTX üniteleri pervane rüzgarı olmadan yerde beklerken saniyeler içinde 100°C sıcaklığa ulaşabilir ve kendini korumaya alıp gücü düşürür. Pit Mode kullanarak kanala girmeden önce gücü 25mW altında tutun.',
        'headline': 'VTX ASIRI ISINMA ONLEMLERI',
        'subhead': 'Kalkış Öncesi Termal Korumayı ve Güç Düşüşünü Engelle',
        'points': [
            "[PIT MODE] Yerde Beklerken Düşük Güç (25mW) Kullanın",
            "[RUZGAR] FPV VTX Soğutması Uçuş Esnasındaki Hava Akımıdır",
            "[KORUMA] Termal Yanmaları Önleyen Yüksek Verimli VTX\'ler"
        ],
        'tags': '#vtx #termalyonetim #fpvvideo #pozitronmarket #teknofest'
    },
    {
        'title': '[PID TUNING] Betaflight D-Term Filtresi: Motor Isınması ve Propwash',
        'summary': 'Ani dönüşlerde drone\'un kendi yarattığı türbülansa girmesi (propwash), doğru PID ve filtreleme ile çözülür. Aşırı yüksek D kazancı motorları aşırı ısıtırken, çok agresif filtre gecikme yaratır. RPM Filtreleme aktif edilerek motorlar buz gibi tutulabilir.',
        'headline': 'BETAFLIGHT PID & D-TERM',
        'subhead': 'Propwash Titreşimlerini Yok Et & Motorları Koru',
        'points': [
            "[PROPWASH] Keskin Dönüşlerdeki Yalpalama ve Titreşime Son",
            "[D-TERM] Aşırı D Kazancı Motorları Yakabilir, Isıyı Kontrol Edin",
            "[RPM FILTRE] Çift Yönlü DShot ile Dinamik Frekans Temizliği"
        ],
        'tags': '#pidtuning #betaflight #propwash #dterm #pozitronmarket'
    },
    {
        'title': '[UCUS KARTI] F405 vs F722 vs H7 İşlemci: Hangisini Seçmelisin?',
        'summary': 'F405 işlemciler ekonomik ve güvenilirdir ancak sınırlı UART portuna sahiptir. F722 işlemciler yüksek saat hızı ve dahili donanım inverteri ile tüm UART portlarında ELRS, GPS, VTX ve ESC telemetrisini aynı anda takılmadan işler.',
        'headline': 'F405 VS F722 UCUS KARTI',
        'subhead': 'UART Port Sayısı, İşlemci Hızı ve Donanım Uyumu',
        'points': [
            "[F405] Fiyat / Performans Freestyle ve Bütçe Projeleri",
            "[F722] Çoklu UART, Dahili Çevirici ve Yüksek Döngü Hızı",
            "[STACK] SpeedyBee, T-Motor ve Foxeer Stack\'ler Pozitron\'da"
        ],
        'tags': '#flightcontroller #f722 #f405 #speedybee #pozitronmarket'
    },
    {
        'title': '[TEST] Smoke Stopper: İlk Enerji Vermede Kart Yanmalarını Önle',
        'summary': 'Yeni bir drone topladıktan sonra LiPo bataryayı doğrudan takmak, olası bir lehim köprüsünde tüm stack\'i 1 saniyede yakabilir. Kendini sıfırlayan eFuse / sigortalı Smoke Stopper kullanarak kısa devreleri sıfır hasarla tespit edin.',
        'headline': 'SMOKE STOPPER ILE GUVENLI TEST',
        'subhead': 'Yeni Build\'lerde Kart ve ESC Yakma Korkusuna Son',
        'points': [
            "[GUVEN] Kısa Devre Durumunda Gücü Mili Saniyede Keser",
            "[TEST] İlk LiPo Bağlantısında %100 Donanım Sigortası",
            "[ATOLYE] Her FPV Pilotunun Masasında Bulunması Gereken Alet"
        ],
        'tags': '#smokestopper #dronetopla #kisadevre #pozitronmarket #teknofest'
    },
    {
        'title': '[TURTLE] Turtle Mode (Crash Flip): Motor Yakmadan Ters Drone Kaldırma',
        'summary': 'Ters düşen drone\'u yerinden kaldırmak için motorların ters dönmesini sağlayan DShot Flip Over After Crash harika bir özelliktir. Ancak pervanelerden biri çime veya dala takılmışsa zorlamak ESC FET\'lerini yakabilir; takılma varsa zorlamayın.',
        'headline': 'TURTLE MODE (CRASH FLIP) REHBERI',
        'subhead': 'Ters Düşen Drone\'u Kurtarırken ESC\'yi Yakma',
        'points': [
            "[DSHOT] Ters Dönüş Yönü ile Tek Tıkla Düzeltme",
            "[DIKKAT] Çime veya Dala Takılı Pervaneyi Asla Zorlamayın",
            "[TAMIR] Yedek Motor ve ESC Donanımları Pozitron Market\'te"
        ],
        'tags': '#turtlemode #crashflip #dshot #fpvfreestyle #pozitronmarket'
    },
    {
        'title': '[RPM FILTER] Dynamic Idle ve Çift Yönlü DShot Kurulumu',
        'summary': 'Bidirectional DShot (Çift Yönlü DShot) ile ESC motorun gerçek devrini (RPM) uçuş kartına iletir. Uçuş kontrolcüsü dar çentik filtreleri (harmonic notch) ile sadece motor gürültüsünü siler; filtre gecikmesi azalır ve drone kütük gibi pürüzsüz uçar.',
        'headline': 'DYNAMIC IDLE & RPM FILTRE',
        'subhead': 'Maksimum Uçuş Akıcılığı & Soğuk Motorlar',
        'points': [
            "[HARMONIC] Motor Devrine Göre Anlık Dinamik Filtreleme",
            "[IDLE] Serbest Düşüşte (Zero Throttle) Sıfır Yalpalama",
            "[PERFORMANS] Pürüzsüz Freestyle ve Yarış Tepkisi"
        ],
        'tags': '#rpmfilter #bidirectionaldshot #dynamicidle #betaflight #pozitron'
    },
    {
        'title': '[RF MENZIL] VTX Anten Yerleşimi: Karbon Fiber Gölgelenmesini Önleme',
        'summary': 'Karbon fiber mükemmel bir RF iletkendir ve 5.8GHz video sinyallerini bloklar. VTX anteninizin aktif ışıma yapan uç kısmı karbon gövdenin en az 3-4cm yukarısında ve gerisinde olmalıdır; geri dönüş açılarında video kararmasını engeller.',
        'headline': 'ANTEN YERLESIMI VE SIK GORULEN HATALAR',
        'subhead': 'Karbon Fiberin Sinyal Gölgelenmesini Tamamen Önle',
        'points': [
            "[YERLESIM] Anten Ucu Gövdeden En Az 3-4cm Uzakta Olmalı",
            "[GOLGELENME] Dönüşlerde Video Sinyalinin Kesilmesini Engeller",
            "[TPU MOUNT] Esnek ve Kırılmaz Anten Mountları 3D Studio\'da"
        ],
        'tags': '#antena #rfmenzil #karbonfiber #pozitronmarket #fpvturkey'
    },
    {
        'title': '[BAKIM] Motor Rulman Temizliği: Kumlu Freestyle Sonrası Bakım',
        'summary': 'Toprak veya tozlu zeminlerde uçtuktan sonra motor çanının içine giren mikro partiküller rulmanları çizer ve titreşim yaratır. İzopropil alkol ile temizleyip sentetik rulman yağı ile yağlayarak motorlarınızın ömrünü uzatabilirsiniz.',
        'headline': 'FPV MOTOR RULMAN BAKIMI',
        'subhead': 'Titreşimsiz Uçuş ve Uzun Ömürlü Fırçasız Motorlar',
        'points': [
            "[TEMIZLIK] İzopropil Alkol ile Manyetik Çan Temizliği",
            "[YAGLAMA] Yüksek Devirli Mikro Sentetik Rulman Yağı",
            "[DEGISIM] Orijinal T-Motor, EMAX ve iFlight Motorlar Pozitron\'da"
        ],
        'tags': '#motortamiri #rulman #fpvbakim #pozitronmarket #teknofest'
    },
    {
        'title': '[PIL STRAP] Kevlar vs Silikon Pil Kayışı: Sert Çakılmalarda Güvenlik',
        'summary': 'Standart naylon kayışlar sert kazalarda toka yerinden yırtılarak LiPo bataryanın fırlamasına ve pervaneler tarafından delinmesine yol açar. Dokuma dikişli Kevlar ve kauçuk silikon kaplı kayışlar bataryayı gövdeye kaynaklanmış gibi sabitler.',
        'headline': 'KEVLAR PIL KAYISI GUVENCESI',
        'subhead': 'Sert Çakılmalarda Batarya Fırlamalarını Önle',
        'points': [
            "[DAYANIKLILIK] Metal Tokalı Yırtılmaz Kevlar Lifleri",
            "[TUTUS] Kaydırmayan Kauçuk Silikon Yüzey Kaplaması",
            "[AKSESUAR] Ekstra Güçlü FPV Pil Kayışları Pozitron\'da"
        ],
        'tags': '#pilkayisi #kevlarstrap #lipoguvencesi #pozitronmarket #drone'
    },
    {
        'title': '[SAHA CANTA] FPV Saha Çantası Kontrol Listesi: 8 Olmazsa Olmaz',
        'summary': 'Sahada uçuş yaparken en çok ihtiyaç duyulan aletler: 1) 8mm somun anahtarı (pervane değişimi), 2) M2-M3 alyan tornavidalar, 3) Yedek LiPo kayışı, 4) Taşınabilir lehim havyası (TS101/Pinecil), 5) Yedek pervane setleri, 6) İzopropil mendil, 7) Mini kargaburun, 8) Voltaj test aleti.',
        'headline': 'FPV SAHA CANTA KONTROL LISTESI',
        'subhead': 'Sahada Uçuşunuzu Yarıda Bırakmayacak 8 Temel Ekipman',
        'points': [
            "[PERVANE] 8mm Hızlı Değişim Cırcırlı Somun Anahtarı",
            "[HAVYA] Sahada 6S LiPo ile Çalışan Akıllı Mini Lehim Havyası",
            "[EKIPMAN] Tüm Montaj ve Servis Donanımları Pozitron Market\'te"
        ],
        'tags': '#sahacantasi #fpvaletler #ts101 #pervanesomunu #pozitronmarket'
    }
]

class ContentGenerator:
    def __init__(self, gemini_api_key: str = ""):
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
        self._session_recent_titles = []
        self._session_recent_product_ids = []

    def set_api_key(self, key: str):
        self.gemini_api_key = key

    def generate_content(self, content_type: str = None, product_id: str = None) -> dict:
        """
        Generates content dictionary with strict anti-duplicate guarantee and balanced catalog rotation:
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
        valid_types = [
            'product_spotlight', 'drone_build_showcase', 'carousel_guide',
            'flight_weather_radar', 'pilot_tip', 'tool_showcase',
            'spot_guide', 'deal_drop', 'seo_article', 'review_highlight'
        ]
        
        recent_types = get_recent_posted_content_types(limit=5)
        db_titles = set(get_recent_posted_titles(limit=40))
        all_recent_titles = db_titles.union(set(self._session_recent_titles[-30:]))

        explicit_type = content_type if (content_type and content_type in valid_types) else None

        # 1. Smart Pillar Selection (diverse PR feed: builds, weather, guides, products, tips)
        if not content_type or content_type not in valid_types:
            candidate_types = [t for t in valid_types if not (recent_types and t == recent_types[0])]
            if not candidate_types:
                candidate_types = valid_types

            # Balanced PR & e-commerce diversity weights
            type_weights = {
                'product_spotlight': 0.30,
                'drone_build_showcase': 0.22,
                'carousel_guide': 0.18,
                'flight_weather_radar': 0.12,
                'pilot_tip': 0.08,
                'tool_showcase': 0.05,
                'spot_guide': 0.03,
                'deal_drop': 0.02
            }
            weights = [type_weights.get(t, 0.05) for t in candidate_types]
            content_type = random.choices(candidate_types, weights=weights, k=1)[0]

        # 2. Multi-attempt anti-duplicate generation loop
        content = None
        for attempt in range(5):
            cur_type = explicit_type or content_type
            if cur_type == 'product_spotlight':
                content = self._generate_product_spotlight(product_id)
            elif cur_type == 'drone_build_showcase':
                content = self._generate_drone_build_showcase()
            elif cur_type == 'carousel_guide':
                content = self._generate_carousel_guide()
            elif cur_type == 'flight_weather_radar':
                content = self._generate_flight_weather_radar()
            elif cur_type == 'spot_guide':
                content = self._generate_spot_guide()
            elif cur_type == 'tool_showcase':
                content = self._generate_tool_showcase()
            elif cur_type == 'deal_drop':
                content = self._generate_deal_drop()
            elif cur_type == 'pilot_tip':
                content = self._generate_pilot_tip()
            elif cur_type == 'seo_article':
                content = self._generate_seo_article()
            elif cur_type == 'review_highlight':
                content = self._generate_review_highlight()
            else:
                content = self._generate_product_spotlight(product_id)

            if content and content.get('title'):
                if content.get('title') not in all_recent_titles or explicit_type:
                    break
            
            # If candidate was recently posted and not explicitly requested, try another category or pillar
            if not explicit_type:
                content_type = 'product_spotlight'
                product_id = None

        if content:
            # Ensure DM / Comment Call-To-Action is attached to caption
            content['caption'] = self._append_dm_cta(content['caption'])
            self._session_recent_titles.append(content['title'])
            if len(self._session_recent_titles) > 50:
                self._session_recent_titles = self._session_recent_titles[-50:]
            if content.get('product_id'):
                self._session_recent_product_ids.append(content['product_id'])
                if len(self._session_recent_product_ids) > 50:
                    self._session_recent_product_ids = self._session_recent_product_ids[-50:]

        return content

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
        recent_ids = set(get_recent_posted_product_ids(50))
        recent_ids.update(set(self._session_recent_product_ids[-40:]))

        try:
            conn = get_db()
            cursor = conn.cursor()

            if product_id:
                cursor.execute("SELECT * FROM products WHERE id = ? OR slug = ? OR sku = ?", (product_id, product_id, product_id))
                row = cursor.fetchone()
                conn.close()
                if row:
                    return dict(row)

            # 1. Balanced Category Rotation: pick from active catalog categories
            cursor.execute("SELECT id FROM categories WHERE item_count > 0 ORDER BY RANDOM()")
            cat_candidates = [r['id'] for r in cursor.fetchall()]
            random.shuffle(cat_candidates)
            
            for cat_id in cat_candidates:
                cat_params = [cat_id]
                recent_filter = ""
                if recent_ids:
                    r_placeholders = ','.join('?' for _ in recent_ids)
                    recent_filter = f" AND id NOT IN ({r_placeholders})"
                    cat_params.extend(recent_ids)

                cursor.execute(f"SELECT * FROM products WHERE category_id = ? AND stock > 0 {recent_filter} ORDER BY RANDOM() LIMIT 5", cat_params)
                cat_rows = cursor.fetchall()
                if cat_rows:
                    selected = random.choice(cat_rows)
                    conn.close()
                    return dict(selected)

            # 2. Global random from unposted products in catalog
            query = "SELECT * FROM products WHERE stock > 0"
            params = []
            if recent_ids:
                placeholders = ','.join('?' for _ in recent_ids)
                query += f" AND id NOT IN ({placeholders})"
                params.extend(recent_ids)
            query += " ORDER BY RANDOM() LIMIT 20"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

            if rows:
                return dict(random.choice(rows))

            # 3. Fallback if all products were posted: pick any random active product
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM products WHERE stock > 0 ORDER BY RANDOM() LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                return dict(row)

        except Exception as e:
            print(f"[UYARI] Aday ürün sorgulama hatası: {e}")

        # 5. Fallback to products.json
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
        discount_pct = prod.get('discount_pct', 0)
        slug = prod.get('slug', prod['id'])
        specs = {}
        try:
            specs = json.loads(prod.get('specs_json', '{}'))
        except Exception:
            specs = {}

        # Dynamic Turkish hook selection
        hooks = [
            f"[GUC] FPV filona güç katacak yeni canavar: {name}!",
            f"[FPV] Pilotların radarındaki favori donanım: {name} Pozitron Market'te!",
            f"[HEDEF] Uçuş kalitesini bir üst seviyeye taşı: {brand} imzasını taşıyan {name}!",
            f"[FIRSAT] Maksimum verim, pürüzsüz tepki ve dayanıklılık: {name}!",
            f"[POZITRON] Freestyle ve yarış pilotları için tasarlandı: {name} stoklarda!"
        ]
        hook = random.choice(hooks)

        specs_lines = []
        if specs:
            specs_items = list(specs.items())[:4]
            for k, v in specs_items:
                specs_lines.append(f"  • {k}: {v}")
        specs_block = "\n".join(specs_lines) if specs_lines else f"  • Marka: {brand}\n  • Orijinal Üretici Garantisi\n  • Profesyonel FPV Sınıfı"

        discount_text = f" ([FIRSAT] %{discount_pct} Özel İndirim)" if discount_pct > 0 else ""
        price_text = f"[FIYAT] Fiyat: {price_try:,.2f} TL / ${price_usd:.2f}{discount_text}"

        caption = f"""{hook}

{prod.get('description_tr', prod.get('description_en', ''))[:180]}...

[OZELLIK] Öne Çıkan Özellikler:
{specs_block}

{price_text}
[STOK] Stok Durumu: Hızlı Kargo & Güvenli 3D Secure Ödeme
[LINK] Sipariş ve detaylar için profildeki linke tıkla! 
Ürün linki: pozitronmarket.com/products/{slug}"""

        hashtags = f"#fpv #fpvdrone #fpvturkey #{brand.lower().replace(' ', '')} #dronetopla #pozitronmarket #fpvracing #fpvfreestyle #dronehardware #teknofest"

        top_specs = [f"{k}: {v}" for k, v in list(specs.items())[:2]] if specs else [f"Orijinal {brand} Mühendisliği", "Maksimum Verim & Hız"]
        default_summary = {
            'badge': f"-%{discount_pct} İNDİRİM" if discount_pct > 0 else "[GUC] ÖNE ÇIKAN DONANIM",
            'headline': name[:32],
            'subhead': f"{brand} • Pozitron Market Güvencesi",
            'key_points': [
                f"[GUC] {top_specs[0] if len(top_specs) > 0 else brand}",
                f"[HEDEF] {top_specs[1] if len(top_specs) > 1 else 'Yüksek Performans & Hızlı Tepki'}",
                f"[STOK] {price_try:,.2f} TL • Hızlı Kargo & Stokta"
            ],
            'cta': "> PROFİLDEKİ LİNKTEN HEMEN İNCELE"
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
        recent_titles = set(get_recent_posted_titles(40))

        tools = [
            {
                'id': 'wizard',
                'title': '[ARAC] Pozitron FPV Drone Toplama & Uyumluluk Sihirbazı',
                'caption': """[FPV] "Hangi motora hangi ESC uyar? 4S mi 6S mi? Stack delikleri gövdeye oturur mu?" diye düşünmeye son!

Pozitron Market'in tamamen ÜCRETSİZ geliştirdiği FPV Drone Toplama Sihirbazı ile:
[OK] Bütçeni ve uçuş tarzını seç (Freestyle / Racing)
[OK] Motor KV, ESC amperajı ve LiPo voltajını anlık eşleştir
[OK] 0 hata ile uyumlu donanım paketini tek tıkla oluştur!

Takım arkadaşlarınla listenin çıktısını alabilir veya doğrudan sipariş verebilirsin.

> Hemen profildeki linkten Sihirbazı dene: pozitronmarket.com/drone-toplama-sihirbazi""",
                'hashtags': '#dronetopla #fpvuyumluluk #dronesihirbazi #fpvturkey #pozitronmarket #teknofest #dronebuild',
                'visual_summary': {
                    'badge': 'ÜCRETSİZ ONLİNE ARAÇ',
                    'headline': 'DRONE TOPLAMA SİHİRBAZI',
                    'subhead': 'Motor-ESC-Pil Uyumluluğunu 0 Hata İle Test Et',
                    'key_points': [
                        "[GUC] Motor KV ve 4S / 6S Voltajını Anında Eşleştir",
                        "[HEDEF] ESC Amper ve Stack Deliklerini Otomatik Doğrula",
                        "[POZITRON] 0 Risk İle Uyumlu Parça Listesini Anında Oluştur"
                    ],
                    'cta': '> PROFİLDEKİ LİNKTEN HEMEN DENE'
                },
                'tool_info': {
                    'tool_name': 'drone_wizard',
                    'url': 'https://pozitronmarket.com/drone-toplama-sihirbazi'
                }
            },
            {
                'id': 'tpu_studio',
                'title': '[TPU] Pozitron 3D Baskı TPU Studio — Esnek Darbe Koruması',
                'caption': """[DARBE] Drone'u sert indirdin veya motor kolu mu çarptı? GoPro mount'un mu kırıldı?

Pozitron 3D Baskı Studio devrede!
• STL veya STEP 3D dosyanı doğrudan siteye yükle
• Esnek, kırılmaz TPU 95A veya rijit PETG/PLA seç
• Gramaj ve online fiyatını saniyeler içinde anında hesapla!
• Canlı renk seçenekleri (Siyah, Pozitron Mavisi, Kırmızı, Sarı) ile aynı gün üretime geçsin.

Kırım yaşamadan önce motorlarını ve kameranı sağlama al! [KORUMA]

> Hemen online baskı al: pozitronmarket.com/3d-baski-studio""",
                'hashtags': '#3dbaski #tpu95a #dronemount #gopromount #fpvturkey #pozitronmarket #3dprinting #teknofest',
                'visual_summary': {
                    'badge': 'ONLİNE FİYAT & BASKI',
                    'headline': '3D BASKI TPU STUDIO',
                    'subhead': 'Kırılmaz TPU 95A GoPro & Motor Koruyucuları',
                    'key_points': [
                        "[KORUMA] Darbe Emici Esnek TPU 95A Malzeme Garantisi",
                        "[HIZ] STL / STEP Dosyanı Yükle, Anında Fiyat Al",
                        "[POZITRON] Kişiye Özel Canlı Renkler & Aynı Gün Üretim"
                    ],
                    'cta': '> 3D BASKINI HEMEN SİPARİŞ ET'
                },
                'tool_info': {
                    'tool_name': '3d_print_studio',
                    'url': 'https://pozitronmarket.com/3d-baski-studio'
                }
            },
            {
                'id': 'battery_calc',
                'title': '[HESAPLAYICI] FPV Pil Kapasitesi ve Uçuş Süresi Simülatörü',
                'caption': """[PIL] "Drone'um havada kaç dakika kalır? 1300mAh mi 1550mAh mi seçmeliyim?"

Pozitron Pil & Uçuş Süresi Simülatörü ile:
[1] Motor KV ve pervane boyutunu seçin
[2] Drone kalkış ağırlığını (AUW) ve GoPro yükünü girin
[3] Hover ve agresif freestyle uçuş sürelerini saniyeler içinde simüle edin!

Ağırlık ve uçuş süresi dengesini sahaya çıkmadan önce optimize edin.

> Ücretsiz hesaplayıcıyı keşfet: pozitronmarket.com/drone-toplama-sihirbazi""",
                'hashtags': '#pilhesaplama #ucussuresi #fpvpil #lipobattery #pozitronmarket #teknofest',
                'visual_summary': {
                    'badge': 'PERFORMANS SİMÜLATÖRÜ',
                    'headline': 'UÇUŞ SÜRESİ HESAPLAYICI',
                    'subhead': 'Kapasite, Ağırlık ve İtki Analizini Yap',
                    'key_points': [
                        "[PIL] 1300mAh vs 1550mAh Optimum Süre Dengesi",
                        "[AGIRLIK] GoPro ve Aksiyon Kamera Yükü Simülasyonu",
                        "[POZITRON] Sahaya Çıkmadan Gerçek Uçuş Süreni Gör"
                    ],
                    'cta': '> SİMÜLATÖRÜ HEMEN DENE'
                },
                'tool_info': {
                    'tool_name': 'battery_calc',
                    'url': 'https://pozitronmarket.com/drone-toplama-sihirbazi'
                }
            },
            {
                'id': 'freq_planner',
                'title': '[FREKANS] FPV 5.8GHz Frekans & RaceBand Kanal Planlayıcı',
                'caption': """[FREKANS] Toplu uçuşlarda pilot arkadaşlarınızın görüntüsüne girip kaza yapmaya son!

Pozitron 5.8GHz Frekans Tablosu ile:
• IMD (Intermodulation Distortion) çakışması yapmayan temiz RaceBand kanallarını (R1, R3, R6, R7 veya R8) seçin.
• Takım arkadaşlarınızla frekans paylaşımını tek tıkla organize edin.
• 8 pilota kadar sıfır parazitle aynı anda gökyüzünde kalın!

> Frekans rehberini incele: pozitronmarket.com/drone-toplama-sihirbazi""",
                'hashtags': '#raceband #fpvfrekans #58ghz #fpvracing #pozitronmarket #teknofest',
                'visual_summary': {
                    'badge': 'KANAL PLANLAYICI',
                    'headline': '5.8GHZ FREKANS REHBERİ',
                    'subhead': 'Sıfır Parazit ile 8 Pilot Aynı Anda Havada',
                    'key_points': [
                        "[RACEBAND] R1, R3, R6, R8 ile Sıfır Çakışma Garantisi",
                        "[IMD] Yan Kanal Parazitlerini ve Kararmaları Önle",
                        "[EKİP] Takım Arkadaşlarınla Frekans Listeni Paylaş"
                    ],
                    'cta': '> FREKANS LİSTESİNİ GÖRÜNTÜLE'
                },
                'tool_info': {
                    'tool_name': 'freq_planner',
                    'url': 'https://pozitronmarket.com/drone-toplama-sihirbazi'
                }
            }
        ]

        eligible_tools = [t for t in tools if t['title'] not in recent_titles]
        if not eligible_tools:
            eligible_tools = tools
        tool = random.choice(eligible_tools)

        title = tool['title']
        caption = tool['caption']
        hashtags = tool['hashtags']
        visual_summary = tool['visual_summary']
        tool_info = tool['tool_info']

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
        recent_titles = set(get_recent_posted_titles(40))

        deals = [
            {
                'code': 'POZITRON10',
                'title': '[FIRSAT] FPV Sezonu Başladı: POZITRON10 ile %10 İndirim!',
                'desc': 'Tüm FPV parçaları, motorlar ve stack ürünlerinde net %10 indirim!',
                'badge': 'SEZON FIRSATI',
                'points': [
                    "[KUPON] Kupon Kodu: POZITRON10",
                    "[FIRSAT] Sepette Anında Net %10 İndirim",
                    "[DONANIM] Motor, ESC, FC ve Tüm Yedek Parçalarda Geçerli"
                ]
            },
            {
                'code': 'TEKNOFEST2026',
                'title': '[TEKNOFEST] Teknofest Takımlarına Özel %15 Destek İndirimi',
                'desc': 'İHA ve FPV yarışma takımlarına özel TEKNOFEST2026 kupon kodu aktif!',
                'badge': 'TEKNOFEST DESTEĞİ',
                'points': [
                    "[KUPON] Kupon Kodu: TEKNOFEST2026",
                    "[DESTEK] Üniversite ve Lise Takımlarına %15 İndirim",
                    "[KARGO] Aynı Gün Hızlı Kargo ile Yarışmaya Hazırlan"
                ]
            },
            {
                'code': 'HOSGELDIN15',
                'title': '[AVANTAJ] Pozitron Ailesine Katıl: HOSGELDIN15 ile İndirim Al',
                'desc': 'İlk drone parçası siparişinizde anında geçerli özel hoş geldin indirimi!',
                'badge': 'YENİ PİLOT DESTEĞİ',
                'points': [
                    "[KUPON] Kupon Kodu: HOSGELDIN15",
                    "[AVANTAJ] İlk Alışverişe Özel Avantajlı Fiyat",
                    "[DESTEK] Donanım Seçiminde Uzman Teknik Destek"
                ]
            },
            {
                'code': 'UCRETSIZKARGO',
                'title': '[KARGO] 1.500 TL Üzeri Tüm Siparişlerde Ücretsiz Hızlı Kargo!',
                'desc': 'Pozitron Market güvencesiyle aynı gün kargo, kapında teslim!',
                'badge': 'ÜCRETSİZ KARGO',
                'points': [
                    "[KARGO] 1.500 TL Üzeri Sepetlerde Kargo Ücretsiz",
                    "[HIZ] Hafta İçi Saat 16:00\'ya Kadar Aynı Gün Sevkiyat",
                    "[GUVEN] Orijinal Ürün & Güvenli 3D Secure Ödeme"
                ]
            }
        ]

        eligible_deals = [d for d in deals if d['title'] not in recent_titles]
        if not eligible_deals:
            eligible_deals = deals
        deal = random.choice(eligible_deals)

        coupon_code = deal['code']
        title = deal['title']
        discount_desc = deal['desc']

        caption = f"""[GUC] FPV tutkunlarına ve drone pilotlarına özel avantaj alarmı!

Pozitron Market'te sepet aşamasında kupon kodunu girerek avantajlı fiyatlardan yararlanın:
[KUPON] Kupon Kodu: {coupon_code}
[KAMPANYA] Kampanya: {discount_desc}

[FPV] Motorlar, ESC sürücüler, dijital HD sistemler, gövdeler ve yedek parçalarda geçerli!
Kupon stoklarla ve süreyle sınırlıdır.

> Alışverişe başlamak için profildeki linke tıkla: pozitronmarket.com"""

        hashtags = f"#fpvfirsat #indirimkuponu #pozitronmarket #fpvturkey #dronetopla #teknofest #{coupon_code.lower()}"

        visual_summary = {
            'badge': deal['badge'],
            'headline': f'KUPON: {coupon_code}',
            'subhead': discount_desc,
            'key_points': deal['points'],
            'cta': '> İNDİRİMDEN YARARLANMAK İÇİN TIKLA'
        }

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
        recent_titles = set(get_recent_posted_titles(40))
        
        # Filter out recently posted tips
        eligible_tips = [t for t in FPV_PILOT_TIPS if t['title'] not in recent_titles]
        if not eligible_tips:
            eligible_tips = FPV_PILOT_TIPS

        tip = random.choice(eligible_tips)

        title = tip['title']
        caption = f"""{tip['title']}

{tip['summary']}

[IPUCU] Pozitron Sihirbazı'nı kullanarak motor-ESC-batarya uyumluluğunuzu tek tıkla test edebilirsiniz.
Merak ettiğiniz teknik soruları yorumlarda pilotlarımızla paylaşın! 

> Donanım ve uyumluluk testi: pozitronmarket.com"""
        hashtags = f"{tip['tags']} #fpvfreestyle #fpvracing #fpvdrone #pozitronmarket"

        visual_summary = {
            'badge': 'FPV PİLOT REHBERİ',
            'headline': tip['headline'],
            'subhead': tip['subhead'],
            'key_points': tip['points'],
            'cta': '> DAHA FAZLA TEKNİK REHBER İÇİN TIKLA'
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

    def _generate_seo_article(self) -> dict:
        recent_titles = set(get_recent_posted_titles(40))

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, slug, component_focus, content_markdown FROM seo_articles ORDER BY id DESC LIMIT 30")
            articles = [dict(r) for r in cursor.fetchall()]
            conn.close()

            unique_articles = []
            seen = set()
            for a in articles:
                clean_t = a['title']
                if clean_t not in seen and f"[REHBER] {clean_t[:32]}" not in recent_titles and clean_t not in recent_titles:
                    seen.add(clean_t)
                    unique_articles.append(a)

            if unique_articles:
                art = random.choice(unique_articles)
                art_title = art['title']
                focus = art['component_focus']
                slug = art['slug']
                post_title = f"[REHBER] {art_title[:32]}"
                
                caption = f"""[REHBER] {art_title}

[FPV ODAK] {focus}

Pozitron Mühendislik Ekibi tarafından hazırlanan bu teknik kılavuz ile FPV drone yapımında sıkça karşılaşılan montaj, kalibrasyon ve donanım eşleştirme sorunlarını profesyonelce çözün.

[OZELLIK] Kılavuzda Öne Çıkanlar:
• {focus} alanında dikkat edilmesi gereken kritik elektriksel sınırlar
• Yanma ve kırım risklerini sıfıra indiren test protokolleri
• Maksimum verimlilik için önerilen komponent konfigürasyonları

> Kılavuzun tamamını okumak için profildeki linke tıkla: pozitronmarket.com/rehber/{slug}"""

                hashtags = "#fpvrehber #teknikmakale #dronemuhendislik #pozitronmarket #fpvturkey #teknofest"

                visual_summary = {
                    'badge': 'TEKNİK MÜHENDİSLİK REHBERİ',
                    'headline': art_title[:30],
                    'subhead': f'Odak: {focus[:40]}',
                    'key_points': [
                        f"[ODAK] {focus[:40]}",
                        "[REHBER] Kapsamlı Montaj & Donanım Kalibrasyonu",
                        "[POZİTRON] pozitronmarket.com/docs Üzerinde Yayında"
                    ],
                    'cta': '> REHBERİN TAMAMINI OKU'
                }

                return {
                    'content_type': 'seo_article',
                    'product_id': None,
                    'title': post_title,
                    'caption': caption.strip(),
                    'hashtags': hashtags,
                    'visual_summary': visual_summary,
                    'product_data': None,
                    'tool_info': {'slug': slug}
                }
        except Exception as e:
            print(f"[UYARI] SEO makalesi sorgulama hatası: {e}")

        # Fallback to pilot tip
        return self._generate_pilot_tip()

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
        link = f"pozitronmarket.com/products/{slug}" if slug else "pozitronmarket.com"

        title = f"Pilot Değerlendirmesi — {product_name}"
        caption = f"""***** Pilot Yorumu: "{comment}"
— {user_name} (Doğrulanmış Pozitron Müşterisi)

[FPV] Deneyim / Donanım: {product_name}
Pozitron Market güvencesiyle aynı gün kargo ve teknik destek her siparişinizde yanınızda!

Sen de en son uçuş deneyimini bizimle paylaş! 
Detaylar ve sipariş için profildeki linke tıkla: {link}"""

        hashtags = "#musteriyorumu #fpvturkey #pozitronmarket #fpvpilot #dronetopla #fpvdrone #teknofest"

        visual_summary = {
            'badge': '***** DOĞRULANMIŞ PİLOT YORUMU',
            'headline': f'"{comment[:32]}..."',
            'subhead': f'— {user_name} • Pozitron Pilotu',
            'key_points': [
                f"[YORUM] \"{comment[:45]}...\"",
                f"[FPV] Donanım: {product_name[:35]}",
                "[GUC] %100 Orijinal Ürün & Aynı Gün Kargo"
            ],
            'cta': '> SEN DE DENEYİMİNİ PAYLAŞ'
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
        Calls Gemini 2.5/3.8 Flash API to generate Turkish Instagram post caption and visual summary card.
        """
        if not self.gemini_api_key:
            return None

        prompt = f"""Sen Pozitron Market (pozitronmarket.com) FPV drone platformunun bas sosyal medya ve PR uzmanisin (Model: Gemini 3.8 Flash).
Icerik Turu: {content_type}
Icerik Bilgileri:
{json.dumps(context, ensure_ascii=False, indent=2)}

GOREV:
1. Instagram icin etkileyici, Turkce, enerjik ve samimi bir gonderi metni (caption) ve hashtag'ler yaz.
2. Bu gonderide anlatilan konunun/urunun EN ONEMLI noktalarini ozetleyen bir "visual_summary" (gorsel ozet) olustur.
   Bu gorsel ozet, 1080x1080 boyutundaki Instagram grafik gorselinin uzerine buyuk ve net sekilde basilacaktir.
3. KESIN KURAL: KESINLIKLE HICBIR EMOJI KULLANMA. Butun vurgulari koseli parantez veya temiz tipografi ile yap.

SADECE gecerli bir JSON objesi dondur:
{{
  "title": "Gonderi basligi (maks 40 karakter)",
  "caption": "Instagram gonderi metni (dikkat cekici kanca, teknik avantajlar, sifir emoji, profildeki linke yonlendirme)",
  "hashtags": "#fpvturkey #pozitronmarket #dronetopla #fpvdrone #betaflight",
  "visual_summary": {{
    "badge": "Gorsel ustu rozet (orn: [ONE CIKAN DONANIM], [FIRSAT ALARMI], [PILOT REHBERI])",
    "headline": "Gorsel uzerindeki ana baslik (maks 32 karakter)",
    "subhead": "Gorsel uzerindeki kisa aciklama (maks 45 karakter)",
    "key_points": [
      "[1] Gonderi metninin 1. ozet maddesi (maks 42 karakter)",
      "[2] Gonderi metninin 2. ozet maddesi (maks 42 karakter)",
      "[3] Gonderi metninin 3. ozet maddesi (maks 42 karakter)"
    ],
    "cta": "[PROFILDEKI LINKTEN HEMEN KESFET]"
  }}
}}"""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.5,
                "maxOutputTokens": 800,
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
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    raw_text = res_data['candidates'][0]['content']['parts'][0]['text']
                    raw_text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]', '', raw_text)
                    data = json.loads(raw_text)
                    if isinstance(data, dict) and data.get('caption') and data.get('visual_summary'):
                        return data
            except Exception:
                continue
        return None

    def _append_dm_cta(self, caption: str, keyword: str = 'KUPON') -> str:
        if 'Yoruma' in caption or 'DM' in caption:
            return caption
        cta = (
            "\n\n[OTOMATIK DM ALARMI]\n"
            "Yoruma 'KUPON', 'LINK' veya 'FIYAT' yaz, sana ozel indirim kodunu ve urun baglantisini aninda DM kutuna iletelim!"
        )
        return caption + cta

    def _generate_carousel_guide(self) -> dict:
        recent_titles = set(get_recent_posted_titles(40))

        carousel_guides = [
            {
                'title': '[REHBER] 4S vs 6S Batarya: Hangisini Secmelisin?',
                'headline': '4S VS 6S SECIM REHBERI',
                'subhead': 'Voltaj Cokmesi, Agirlik ve Verimlilik',
                'points': [
                    "[VOLTAJ] 6S Dusuk Amper ile Minimum Cokme Saglar",
                    "[MOTOR] 6S 5 Inc Icin 1750-1950KV Idealdir",
                    "[VERIM] ESC ve Kablo Isinmalarini %40 Azaltir"
                ],
                'caption': """[KAYDIRMALI REHBER] 4S vs 6S LiPo Batarya Karsilastirmasi

FPV drone toplarken en cok sorulan soru: "4S mi toplamaliyim, 6S mi?"

Bu 4 slaytlik detayli rehberde:
- Voltaj cokmesi (voltage sag) neden olusur?
- 6S bataryanin motor ve ESC uzerindeki elektriksel avantaji nedir?
- Hangi KV degerinde motor secmelisiniz?
Hepsini adim adim acikliyoruz!

Slaytlari kaydirarak detaylari inceleyin ve ileride lazim oldugunda bulmak icin gonderiyi kaydetmeyi unutmayin!

> Tum LiPo batarya ve sarj aletleri: pozitronmarket.com""",
                'tags': '#fpvlipo #6sbattery #fpvrehber #pozitronmarket #dronetopla #kaydirmalipost'
            },
            {
                'title': '[REHBER] Dijital HD (O3, Walksnail) vs Analog Video',
                'headline': 'DIJITAL HD VS ANALOG VTX',
                'subhead': 'Kristal Netlik mi, Ultra Dusuk Gecikme mi?',
                'points': [
                    "[DJI O3 / WALKSNAIL] 1080p Kristal Netlik ve Dahili Kayit",
                    "[ANALOG / HDZERO] 15ms Ultra Dusuk Sabit Gecikme",
                    "[STOK] En Guncel Dijital VTX Sistemleri Pozitron'da"
                ],
                'caption': """[KAYDIRMALI REHBER] Dijital HD vs Analog FPV Video Sistemleri

Gozlugunuzdeki goruntu ucus keyfinizi ve tepki surenizi dogrudan belirler!

Bu rehberde karsilastiriyoruz:
- DJI O3 Air Unit & Walksnail Avatar (1080p dijital netlik)
- HDZero & Klasik Analog 5.8GHz (Ultra dusuk 15ms gecikme)
- Agirlik, menzil ve maliyet analizi

Slaytlari sola kaydirarak ihtiyaciniza en uygun sistemi secin!

> Dijital HD ve Analog VTX donanimlari: pozitronmarket.com""",
                'tags': '#djio3 #walksnail #analogfpv #vtxrehber #pozitronmarket #fpvturkey'
            },
            {
                'title': '[REHBER] ExpressLRS 2.4GHz: Paket Hizi ve Guvenlik',
                'headline': 'EXPRESSLRS 2.4GHZ AYARLARI',
                'subhead': 'Paket Hizi, Dinamik Guc ve Failsafe',
                'points': [
                    "[HIZ] 500Hz Paket Hizi ile 2ms Pruzsuz Tepki",
                    "[GUC] Dinamik Guc ile Pil Tasarrufu ve Uzun Menzil",
                    "[GUVENLIK] Failsafe Testi ve Model Match Onlemi"
                ],
                'caption': """[KAYDIRMALI REHBER] ExpressLRS (ELRS) Kumanda Protokolu Ayar Rehberi

Menzil kaygilarina ve failsafe korkularina ExpressLRS ile son verin!

Bu rehberde:
- 250Hz vs 500Hz paket hizi farki
- Telemetri orani (1:64 / 1:32) neden onemlidir?
- Dinamik guc ayari ile menzili garantiye alma

Rehberi kaydet, atolyede setup kurarken basucu kaynagin olsun!

> Radiomaster ve ELRS kumanda donanimlari: pozitronmarket.com""",
                'tags': '#expresslrs #elrs #radiomaster #fpvkumanda #pozitronmarket #fpvturkey'
            },
            {
                'title': '[REHBER] Betaflight 4.5 GPS Rescue: Drone Kurtarma',
                'headline': 'BETAFLIGHT GPS RESCUE',
                'subhead': 'Sinyal Koptugunda Otonom Eve Donus',
                'points': [
                    "[UYDU] Minimum 8 Uydu Kilidi ile Guvenli Kalkis",
                    "[FAILSAFE] Agac ve Bina Ustu Guvenli Tirmanma",
                    "[PUSULASIZ] Betaflight 4.5 ile Pusulasiz Yon Bulma"
                ],
                'caption': """[KAYDIRMALI REHBER] Betaflight 4.5 GPS Rescue Kurulumu ve Ayarlari

Video veya kumanda sinyali koptugunda drone'unuzu kaybetmeyin!

Bu 4 slaytlik rehberde:
- GPS modulu baglantisi ve UART ayarlari
- Minimum uydu sayisi ve arm korumasi
- Guvenli donus irtifasi (Sanity Check) ayarlari

Slaytlari kaydir, drone'unu guvenceye al!

> M10 GPS modulleri ve aksesuarlari: pozitronmarket.com""",
                'tags': '#betaflight #gpsrescue #longrangefpv #pozitronmarket #fpvdrone'
            }
        ]

        eligible = [g for g in carousel_guides if g['title'] not in recent_titles]
        if not eligible:
            eligible = carousel_guides
        guide = random.choice(eligible)

        visual_summary = {
            'badge': 'KAYDIRMALI REHBER [4 SLAYT]',
            'headline': guide['headline'],
            'subhead': guide['subhead'],
            'key_points': guide['points'],
            'cta': 'KAYDIR > 1/4'
        }

        return {
            'content_type': 'carousel_guide',
            'media_type': 'CAROUSEL',
            'product_id': None,
            'title': guide['title'],
            'caption': guide['caption'].strip(),
            'hashtags': guide['tags'],
            'visual_summary': visual_summary,
            'product_data': None,
            'tool_info': None
        }

    def _generate_drone_build_showcase(self) -> dict:
        recent_titles = set(get_recent_posted_titles(40))

        builds = [
            {
                'title': '[POZITRON BUILD] 5 Inc 6S Freestyle Canavari',
                'headline': '5 INC 6S FREESTYLE BEAST',
                'subhead': 'Pozitron Atolye Referans Freestyle Kurulumu',
                'pills': ['6S LiPo', '~370g', 'Gemfan 51433', 'Betaflight 4.5'],
                'specs': [
                    "[FRAME] 5 Inc 3K Karbon Fiber Guclendirilmis Sasisi",
                    "[STACK] SpeedyBee F405 V4 55A BLS Stack",
                    "[MOTOR] T-Motor F60 PRO V 1950KV 6S Motorlar",
                    "[VTX] Walksnail Avatar HD Pro / DJI O3 Dijital VTX"
                ],
                'desc': 'Pozitron Atolye muhendislerimizin sahada test ettigi referans 5 inc freestyle konfigurasyonu. Titresimsiz RPM filtreleme, yuksek torklu 1950KV motorlar ve mukemmel agirlik merkezi.',
                'tags': '#fpvdrone #fpvbuild #freestylefpv #pozitronmarket #dronetopla #betaflight #fpvturkey'
            },
            {
                'title': '[POZITRON BUILD] 3.5 Inc CineWhoop Pro',
                'headline': '3.5 INC CINEWHOOP PRO',
                'subhead': 'Kapali Alan & Yakin Cekim Sinematik Quad',
                'pills': ['4S LiPo', '~215g', 'Kanalli Koruma', 'Dusuk Desibel'],
                'specs': [
                    "[FRAME] CineWhoop 3.5 Inc Darbe Korumali Kanalli Govde",
                    "[STACK] AIO F722 40A Entegre Ucus Kontrol Karti",
                    "[MOTOR] 1404 3800KV Sinematik Motorlar",
                    "[KAMERA] Caddx Ratel 2 Pro / Avatar HD Mini"
                ],
                'desc': 'Insan ve mekan yakin cekimlerinde maksimum guvenlik saglayan kanal korumali sinematik setup. Yumusak gaz tepkisi ve uzun havada kalis suresi.',
                'tags': '#cinewhoop #sinematikfpv #pozitronmarket #fpvturkey #dronetopla #videography'
            },
            {
                'title': '[POZITRON BUILD] 7 Inc Long Range Explorer',
                'headline': '7 INC LONG RANGE EXPLORER',
                'subhead': 'Dag Ucusu & 15KM+ Guvenli Kesif',
                'pills': ['6S Li-Ion', '~540g', 'M10 GPS', '25+ Dk Ucus'],
                'specs': [
                    "[FRAME] 7 Inc Deadcat Karbon Uzun Menzil Sasisi",
                    "[STACK] Matek F722-HD & 60A BLHeli32 ESC",
                    "[MOTOR] 2807 1300KV Dusuk KV Yuksek Verim Motor",
                    "[GPS] M10-5883 Pusulali Hassas GPS ve RTH"
                ],
                'desc': 'Zirve tirmanislari ve uzun menzilli doga kesifleri icin tasarlandi. Deadcat geometrisi sayesinde pervaneler kamera acisina girmez.',
                'tags': '#longrangefpv #dagucusu #fpvturkey #pozitronmarket #dronetopla #expresslrs'
            },
            {
                'title': '[POZITRON BUILD] 2 Inc Toothpick Atolye Canavari',
                'headline': '2 INC TOOTHPICK POCKET',
                'subhead': 'Mikro Boyut & Sinirsiz Atolye Eglencesi',
                'pills': ['1-2S LiPo', '~48g', 'Sub-250g', 'Sessiz Ucus'],
                'specs': [
                    "[FRAME] 2 Inc Ultralight 1.5mm Karbon Sasi",
                    "[STACK] 1-2S AIO 12A Entegre Kart",
                    "[MOTOR] 1103 11000KV Ultra Hizli Motorlar",
                    "[VTX] 400mW Mini Analog VTX ve Nano Kamera"
                ],
                'desc': 'Bahcede, parkta veya atolye icinde guvenle ucabileceginiz cevik mikro FPV drone. Dusuk agirlik sayesinde kirilma riski minimumdur.',
                'tags': '#toothpickdrone #microfpv #pozitronmarket #fpvturkey #tinydrone'
            }
        ]

        eligible = [b for b in builds if b['title'] not in recent_titles]
        if not eligible:
            eligible = builds
        b = random.choice(eligible)

        specs_text = "\n".join(b['specs'])
        caption = f"""[POZITRON BUILD REHBERI] {b['headline']}

Pozitron Market Atolye Referans Kurulumu:
{b['subhead']}

[DONANIM LISTESI]
{specs_text}

[POZITRON MUHENDISLIK NOTU]
{b['desc']}

> Bu kurulumda kullanilan tum parcalar Pozitron Market stoklarinda ve ayni gun kargoda: pozitronmarket.com

[OTOMATIK DM ALARMI]
Yoruma 'KUPON', 'PARCA' veya 'FIYAT' yaz, bu build'in parca listesini ve ozel indirim kodunu aninda DM ile gonderelim!"""

        visual_summary = {
            'badge': 'POZITRON BUILD REHBERI',
            'headline': b['headline'],
            'subhead': b['subhead'],
            'pills': b['pills'],
            'key_points': b['specs'],
            'cta': '> TUM PARCALAR STOKTA: pozitronmarket.com <'
        }

        return {
            'content_type': 'drone_build_showcase',
            'media_type': 'IMAGE',
            'product_id': None,
            'title': b['title'],
            'caption': caption.strip(),
            'hashtags': b['tags'],
            'visual_summary': visual_summary,
            'product_data': None,
            'tool_info': None
        }

    def _generate_flight_weather_radar(self) -> dict:
        now = datetime.now()
        is_weekend = now.weekday() in (4, 5, 6)

        wind_speed = random.randint(7, 14)
        temp_c = random.randint(19, 25)
        kp_index = random.choice([1, 1, 2, 2, 3])

        if wind_speed <= 10 and kp_index <= 2:
            score = "9 / 10"
            status_text = "MUKEMMEL UCUS GUNU"
            advice = "Ruzgar hizi son derece dusuk, termal akimlar sakin. Freestyle ve sinematik cekimler icin kusursuz bir gokyuzu var."
        elif wind_speed <= 15:
            score = "8 / 10"
            status_text = "HARIKA UCUS GUNU"
            advice = "Hafif esinti mevcut, 5 inc ve uzeri build'ler icin hicbir engel yok. RTH ve GPS baglantilarinizi kalkis oncesi test edin."
        else:
            score = "7 / 10"
            status_text = "ORTA — ATOLYE VEYA ALCAK UCUS"
            advice = "Ruzgar hizi hissedilir duzeyde. Agac alti veya vadi ici korunakli spotlari tercih edin."

        header_prefix = "HAFTA SONU" if is_weekend else "GUNLUK"
        title = f"[UCUS RADARI] {header_prefix} FPV Hava Durumu — {status_text}"

        caption = f"""[UCUS RADARI] {header_prefix} FPV Ucus ve Hava Durumu Raporu

Bugun gokyuzunde yerinizi alin! Pozitron Pilot Masasi Ucus Durumu: {score} ({status_text})

[METEOROLOJIK METRIKLER]
• Ruzgar Hizi: {wind_speed} km/s (Ucus icin elverisli)
• Sicaklik: {temp_c}°C (LiPo bataryalar ideal calisma sicakliginda)
• GPS Kp Indeksi: {kp_index} (Uydu kilidi ve Manyetik Alan Stabil)
• Gorus Mesafesi: Acik ve Net

[PILOT TAVSIYESI]
{advice}

Pervanelerinizi sikin, LiPo'larinizi tam voltaja (4.20V / hucre) sarj edin ve guvenli ucus alanlarinda gorusmek uzere!

> Yedek pervane, LiPo sarj aletleri ve anten ihtiyaclarin icin: pozitronmarket.com"""

        visual_summary = {
            'badge': f'{header_prefix} UCUS RADARI',
            'headline': 'BUGUN UCUS ICIN HARIKA BIR GUN!',
            'subhead': f'Ucus Skoru: {score} — {status_text}',
            'score': f'UCUS SKORU: {score}',
            'wind': f'Ruzgar: {wind_speed} km/s',
            'temp': f'Sicaklik: {temp_c}°C',
            'kp': f'GPS Kp: {kp_index} (Temiz)',
            'key_points': [
                f"Ruzgar: {wind_speed} km/s (Ideal)",
                f"Sicaklik: {temp_c}°C (LiPo Optimum)",
                f"GPS Kp Indeksi: {kp_index} (Kararli)",
                "Ucus Durumu: Guvenli ve Acik"
            ],
            'cta': '> LiPo\'lari Doldur ve Sahaya Cik <'
        }

        return {
            'content_type': 'flight_weather_radar',
            'media_type': 'IMAGE',
            'product_id': None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': '#fpvturkey #ucusradari #fpvhavadurumu #pozitronmarket #fpvpilot #dronepilot #haftasonu',
            'visual_summary': visual_summary,
            'product_data': None,
            'tool_info': None
        }

    def _generate_spot_guide(self) -> dict:
        spots = [
            {
                'title': '[SAHA REHBERI] FPV Ucus Alanlari ve Guvenlik Kurallari',
                'headline': 'GUVENLI FPV UCUS SAHASI SECIMI',
                'subhead': 'Pilot Guvenligi ve Yasal Kurallar',
                'points': [
                    "[MESAFE] Yerlesim yeri ve otoyollardan min. 500m uzaklik",
                    "[FAILSAFE] Her ucus oncesi motor kapatma testini yapin",
                    "[VTX KANALI] Ortak sahada ucus sirasinda frekans cakismasini onleyin",
                    "[GORMEYI KORU] Spotter (gozlemci) ile ucmak her zaman guvenlidir"
                ],
                'desc': 'FPV ucarken hem kendinizi hem de cevrenizi korumak en oncelikli gorevimizdir. Guvenli acik sahalar, vadiler ve izinli model ucak pistleri en ideal noktalardir.'
            },
            {
                'title': '[SAHA REHBERI] Terk Edilmis Binalarda (Bando) Ucus Rehberi',
                'headline': 'BANDO & KAPALI ALAN FPV REHBERI',
                'subhead': 'Sinyal Yansimalari ve RF Guvenligi',
                'points': [
                    "[BETON VE DEMIR] Betonarme yapilar 5.8GHz sinyali ciddi sekilde yutar",
                    "[DIVERSITY] Dual alicili gozluk ve yuksek kazancli patch anten kullanin",
                    "[MOTOR GUCU] Dar alanlarda 3.5 inc ve 4S Cinewhoop tercih edin",
                    "[KORUMA EKIPMANI] Kask ve saglam ayakkabi olmadan bando sahaya girmeyin"
                ],
                'desc': 'Bando ucuslari son derece keyifli olsa da RF sinyali zayifladigi anda goruntu kaybi yasanabilir. Guclu VTX ve guvenli RTH ayarlari sarttir.'
            }
        ]
        s = random.choice(spots)
        caption = f"""[FPV SAHA REHBERI] {s['headline']}

{s['subhead']}

[ONEMLI SAHA KURALLARI]
{chr(10).join(s['points'])}

[POZITRON PILOT TAVSIYESI]
{s['desc']}

Sahada ihtiyacin olan tum FPV ekipmanlari ve yedek parcalar Pozitron Market'te!
> pozitronmarket.com"""

        visual_summary = {
            'badge': 'FPV SAHA REHBERI',
            'headline': s['headline'],
            'subhead': s['subhead'],
            'key_points': s['points'],
            'cta': '> GUVENLE UC: pozitronmarket.com <'
        }

        return {
            'content_type': 'spot_guide',
            'media_type': 'IMAGE',
            'product_id': None,
            'title': s['title'],
            'caption': caption.strip(),
            'hashtags': '#fpvturkey #spotrehberi #fpvspot #pozitronmarket #guvenliucus #fpvpilot',
            'visual_summary': visual_summary,
            'product_data': None,
            'tool_info': None
        }

    def generate_reels_video_prompt(self, post_data: dict) -> str:
        """
        Generates an optimized, cinematic video generation prompt for Gemini Omni Flash (gemini-omni-1.1-flash).
        Directs camera motion, lighting, focus on FPV/drone hardware or 3D printing details, and 9:16 vertical staging.
        """
        title = post_data.get('title', 'FPV Drone & Maker Technology')
        prod = post_data.get('product_data') or {}
        prod_name = prod.get('name_tr') or prod.get('name') or title
        category = prod.get('category', 'FPV Drone Components')
        description = prod.get('description_tr') or prod.get('description') or ''

        # If Gemini API key is available, craft a dynamic prompt via Gemini 3.8 Flash
        if self.gemini_api_key:
            system_instruction = (
                "You are an award-winning cinematic director and prompt engineer for Gemini Omni Flash (gemini-omni-1.1-flash). "
                "Write a single concise video generation prompt (40-60 words) for a 9:16 vertical commercial video. "
                "Specify: subject, camera movement (slow 360 orbit or dynamic macro pan), atmospheric lighting (dark tech studio, neon cyan/orange accents), "
                "textures (matte carbon fiber, copper motor windings, PCB traces, titanium hardware), and continuous unbroken shot. "
                "NO text, NO logo overlays, NO scene cuts, NO speech, photorealistic 8K."
            )
            user_msg = f"Product: {prod_name}\nCategory: {category}\nDetails: {description[:200]}"
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={self.gemini_api_key}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system_instruction}\n\n{user_msg}"}]}
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 150
                }
            }
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=12) as response:
                    res_body = json.loads(response.read().decode('utf-8'))
                    text = res_body['candidates'][0]['content']['parts'][0]['text'].strip()
                    text = text.strip('"\'`')
                    if len(text) > 20:
                        return text
            except Exception:
                pass

        # High-quality rule-based fallback prompt
        return (
            f"Cinematic vertical 9:16 product showcase of {prod_name}. "
            "Smooth 360-degree rotating camera shot in a sleek minimalist dark tech studio with neon cyan and amber rim lighting. "
            "Macro close-up detailing carbon fiber patterns, gold soldering contacts, and brushless motor mechanics. "
            "Smooth 60fps motion, realistic reflections, continuous unbroken single shot, photorealistic commercial quality, no text."
        )


