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
    get_recent_posted_titles, get_recent_posted_content_types,
    get_recent_posted_content_types_by_media, get_recent_captions,
    get_recent_reel_combo_ids
)
from .text_utils import humanize_content, humanize_caption, humanize_line

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

HARDWARE_BATTLES = [
    {
        'title': '[DUELLO] ELRS vs TBS Crossfire: Hangisini Seçmelisin?',
        'summary': 'Açık kaynak ExpressLRS (ELRS), 500Hz-1000Hz paket hızı, ultra düşük 2ms gecikme ve uygun fiyatıyla yarış ve freestyle pilotlarının 1 numaralı tercihi oldu. TBS Crossfire ise 868/915MHz düşük frekansta dağlık ve engelli arazilerde stabil long-range penetrasyon sunuyor. Pozitron rehberinde ikisinin artıları ve eksilerini inceliyoruz.',
        'headline': 'ELRS VS TBS CROSSFIRE',
        'subhead': 'Ultra Düşük Gecikme mi, Long-Range Penetrasyon mu?',
        'points': [
            "[HIZ] ELRS 2.4GHz: 1000Hz Paket Hızı & 2ms Gecikme",
            "[MENZIL] Crossfire: 915MHz ile Engelli Arazide Güçlü Nüfuz",
            "[MALIYET] ELRS Uygun Fiyat & Geniş Donanım Desteği"
        ],
        'tags': '#elrs #crossfire #radiomaster #fpvkumanda #pozitronmarket'
    },
    {
        'title': '[DUELLO] 4S vs 6S LiPo: Freestyle İçin Hangisi?',
        'summary': '4S bataryalar ekonomik ve yeni başlayanlar için idealken, 6S bataryalar 22.2V yüksek gerilim sayesinde aynı güçte %33 daha az akım çeker. Bu da ani gazlamalarda voltaj çökmesini (voltage sag) önler, motor ve ESC sıcaklıklarını düşürür.',
        'headline': '4S VS 6S LIPO DUELLOSU',
        'subhead': 'Voltaj Sag Farkı ve Pil Ömrü Kıyaslaması',
        'points': [
            "[VOLTAJ] 6S: Ani Gazlamalarda Sıfır Voltaj Çökmesi",
            "[ISINMA] 6S İle Düşük Amper, Serin Kalan ESC ve Motorlar",
            "[MOTOR] 4S İçin 2400-2750KV, 6S İçin 1750-1950KV"
        ],
        'tags': '#lipobattery #6sfpv #4sfpv #fpvpilot #pozitronmarket'
    },
    {
        'title': '[DUELLO] Dijital HD (DJI O3 / Walksnail) vs Analog 5.8GHz',
        'summary': 'DJI O3 ve Walksnail Avatar 1080p kristal netlik ve dahili 4K kayıt sunarak görsel deneyimi zirveye taşır. Klasik analog sistemler ise 15ms sabit ultra düşük gecikme ve düşük parça maliyetiyle yarış pistlerinde hala vazgeçilmezdir.',
        'headline': 'DIJITAL HD VS ANALOG VTX',
        'subhead': 'Kristal Görüntü mü, 15ms Yarış Gecikmesi mi?',
        'points': [
            "[DIJITAL] 1080p Netlik, Dahili Kayıt & Geniş Dinamik Aralık",
            "[ANALOG] 15ms Sabit Gecikme & Kırımda Düşük Maliyet",
            "[TERCIH] Sinematik İçin Dijital, Yarış İçin Analog/HDZero"
        ],
        'tags': '#djio3 #walksnail #analogfpv #vtx #pozitronmarket'
    },
    {
        'title': '[DUELLO] 20x20 Mini Stack vs 30x30 Standart Stack',
        'summary': '20x20 stackler 3.5 inç ve hafif 5 inç buildlerde ağırlıktan 20-30 gram tasarruf sağlar. 30x30 stackler ise geniş PCB yüzeyiyle 60A+ yüksek akımlarda ısıyı çok daha iyi dağıtır ve zorlu freestyle manevralarında daha dayanıklıdır.',
        'headline': '20X20 VS 30X30 STACK',
        'subhead': 'Hafiflik Tasarrufu mu, Isı Dağıtımı ve Güç mü?',
        'points': [
            "[20X20] Kompakt Gövde & Hafif Buildler İçin Maksimum Tasarruf",
            "[30X30] Geniş PCB ile Mükemmel Isı Dağılımı & 60A+ Güç",
            "[MONTAJ] Şasi Montaj Deliklerine Göre Doğru Tercih"
        ],
        'tags': '#fpvstack #flightcontroller #esc #pozitronmarket #dronetopla'
    },
    {
        'title': '[DUELLO] Tri-Blade (3 Pal) vs Bi-Blade (2 Pal) Pervane',
        'summary': '3 palli pervaneler yüksek itki, virajlarda agresif tutunma ve mükemmel frenleme gücü sunar (freestyle ve yarış standardı). 2 palli pervaneler ise daha az hava direnciyle yüksek uçuş süresi ve long-range verimliliği sağlar.',
        'headline': '3 PALLI VS 2 PALLI PERVANE',
        'subhead': 'Agresif Yol Tutuşu mu, Uzun Uçuş Süresi mi?',
        'points': [
            "[3 PAL] Virajlarda Yüksek Tutunma & Anında Gaz Tepkisi",
            "[2 PAL] Düşük Hava Direnci ile Maksimum Uçuş Süresi",
            "[SECIM] Freestyle İçin 5143/5146 Tri-Blade En Popüleri"
        ],
        'tags': '#pervane #gemfan #hqprop #fpvfreestyle #pozitronmarket'
    }
]

MISTAKE_BREAKDOWNS = [
    {
        'title': '[HATA ANALIZI] Anten Takmadan VTX Kartına Güç Vermek',
        'summary': 'VTX (video verici) modülleri RF enerjisini anten üzerinden yaymak üzere tasarlanmıştır. Anten takılmadan batarya bağlandığında yayılamayan RF enerjisi ısıya dönüşerek VTX güç amplifikatörü çipini saniyeler içinde yakar.',
        'headline': 'ANTENSIZ VTX CALISTIRMA!',
        'subhead': 'Saniyeler İçinde VTX Çipini Yakan En Yaygın Hata',
        'points': [
            "[TEHLIKE] Yayılamayan RF Enerjisi Çipi Anında Kavurur",
            "[KURAL] Masada veya Sahada Asla Antensiz Pil Bağlama",
            "[TEST] Masa Testlerinde VTX Gücünü PitMode (25mW) Yap"
        ],
        'tags': '#vtx #fpvhata #droneonarim #pozitronmarket #fpvturkey'
    },
    {
        'title': '[HATA ANALIZI] Masada Pervaneler Takılıyken Test Yapmak',
        'summary': 'Betaflight Configurator veya ESC ayarları yapılırken motorlar aniden tam gaz alabilir veya arm olabilir. Karbon/polikarbon pervaneler ciddi yaralanmalara ve kablo kesiklerine yol açar. Masada kural 1: Pervaneleri sök!',
        'headline': 'MASADA PERVANELERI SOK!',
        'subhead': 'Kişisel Güvenlik ve Donanım Koruma Kuralı',
        'points': [
            "[GUVENLIK] USB Bağlarken Pervaneleri Mutlaka Çıkar",
            "[RISK] Yanlış Motor Testinde Kontrolsüz Fırlama Tehlikesi",
            "[ALTIN KURAL] Pervaneler Yalnızca Uçuş Alanında Takılır"
        ],
        'tags': '#dronesafety #betaflight #fpvguvenlik #pozitronmarket #dronebuild'
    },
    {
        'title': '[HATA ANALIZI] ESC Güç Girişine Low ESR Kapasitör Takmamak',
        'summary': 'Fırçasız motorların aktif frenleme (damping light) anında ürettiği voltaj dalgalanmaları (voltage spikes) 40-50V seviyesine çıkabilir. 35V 1000uF Low ESR kapasitör takılmazsa jiroskop yanar ve video görüntüsü çizgilenir.',
        'headline': 'KAPASITORSUZ UCUS YAPMA!',
        'subhead': 'Jiroskop ve HD Kamerayı Yakan Voltaj Spike Tehlikesi',
        'points': [
            "[KORUMA] 35V 1000uF Low ESR Kapasitör Voltajı Filtreler",
            "[GORUNTU] Video Sinyalindeki Parazit Çizgilerini Yok Eder",
            "[MONTAJ] XT60 / ESC Pedlerine En Kısa Bacakla Lehimle"
        ],
        'tags': '#lowesr #kapasitor #fpvbuild #pozitronmarket #dronetamir'
    },
    {
        'title': '[HATA ANALIZI] Yanlış Motor Dönüş Yönü ve Ters Pervane',
        'summary': 'Drone havalanır havalanmaz aniden ters dönüp (flip of death) disarm oluyorsa, motor dönüş yönleri veya pervaneler ters takılmıştır. Betaflight motor sekmesinden yönleri ve Props In/Out ayarını kontrol edin.',
        'headline': 'FLIP OF DEATH KABUSU!',
        'subhead': 'Kalkışta Drone Takla Atıyorsa Bu 2 Ayara Bak',
        'points': [
            "[KONTROL 1] Betaflight Motor Yönleri ile Fiziki Yön Aynı mı?",
            "[KONTROL 2] Pervaneler Props-In mi Props-Out mu Takılı?",
            "[COZUM] ESC Configurator ile Motor Yönünü Tek Tıkla Düzelt"
        ],
        'tags': '#betaflight #flipofdeath #motorrotation #pozitronmarket #fpv'
    },
    {
        'title': '[HATA ANALIZI] LiPo Pili 3.5V Hücre Altına Düşürmek ve Depolamamak',
        'summary': 'LiPo bataryalar hücre başına 3.5V altına düştüğünde kalıcı kimyasal hasar görür ve şişer. Uçuş bittiğinde piller dolu veya boş bırakılmamalı, şarj aletinde 3.80V-3.85V Storage moduna getirilmelidir.',
        'headline': 'LIPO PILINI SISIRME!',
        'subhead': 'Pil Ömrünü 3 Katına Çıkaran Doğru Depolama Kuralları',
        'points': [
            "[HUCAR VOLTAJI] Uçuşu Hücre Başı 3.5V Seviyesinde Bitir",
            "[STORAGE] Uçuş Sonrası Pilleri 3.85V Saklama Moduna Al",
            "[GUVENLIK] Şişmiş ve Hasarlı Pilleri LiPo Çantasında Sakla"
        ],
        'tags': '#lipopil #dronepil #fpvbatarya #pozitronmarket #teknofest'
    }
]

COMMUNITY_QUIZZES = [
    {
        'title': '[FPV QUIZ] ELRS Alıcısının TX Pini Uçuş Kartında Nereye Bağlanır?',
        'summary': 'Haftalık FPV bilgi testimiz yayında! Uart haberleşmesinde çapraz bağlantı kuralı geçerlidir. Alıcının TX pini uçuş kartının (FC) hangi pinine lehimlenmelidir? Doğru cevabını yorumlarda belirt, FPV bilgini test et!',
        'headline': 'FPV TEST: UART BAGLANTISI',
        'subhead': 'Alıcı TX Pini Uçuş Kartında Nereye Bağlanır?',
        'points': [
            "A) Uçuş Kartı TX Pinine",
            "B) Uçuş Kartı RX Pinine (Çapraz Bağlantı)",
            "C) 5V Besleme Pinine",
            "D) GND Toprak Pinine"
        ],
        'correct_answer': 'B) Uçuş Kartı RX Pinine (UART TX -> RX çapraz bağlanır)',
        'tags': '#fpvquiz #fpvtest #sorucevap #pozitronmarket #dronebilgi'
    },
    {
        'title': '[FPV QUIZ] 6S Freestyle Drone İçin En Optimum Motor KV Değeri Hangisidir?',
        'summary': '6S 22.2V batarya sisteminde yüksek voltaj nedeniyle düşük KV motorlar tercih edilir. 5 inç freestyle için ideal KV aralığı nedir? Yorumlarda cevabını pilot topluluğuyla paylaş!',
        'headline': 'FPV TEST: 6S MOTOR KV SECIMI',
        'subhead': '5 İnç Freestyle İçin İdeal KV Aralığı Hangisi?',
        'points': [
            "A) 2450 - 2750 KV",
            "B) 1750 - 1950 KV",
            "C) 3100 - 3600 KV",
            "D) 1200 - 1400 KV"
        ],
        'correct_answer': 'B) 1750 - 1950 KV (6S için ideal devir ve tork)',
        'tags': '#fpvquiz #motorkv #6sfreestyle #pozitronmarket #fpvpilot'
    },
    {
        'title': '[FPV QUIZ] Betaflight RPM Filter Açabilmek İçin Hangi Protokol Şarttır?',
        'summary': 'Betaflight RPM filtresi motor devrini anlık okuyarak gyro titreşimlerini donanımsal olarak filtreler. Bu özelliğin çalışabilmesi için ESC üzerinde hangi protokol aktif edilmelidir?',
        'headline': 'FPV TEST: BETAFLIGHT RPM FILTRE',
        'subhead': 'Hangi ESC Protokolü ile RPM Filtre Çalışır?',
        'points': [
            "A) PWM 400Hz",
            "B) OneShot125",
            "C) Bi-directional DShot (DShot300/600)",
            "D) Multishot"
        ],
        'correct_answer': 'C) Bi-directional DShot (ESC telemetrisi ile çift yönlü DShot)',
        'tags': '#rpmfilter #betaflight #dshot #fpvquiz #pozitronmarket'
    },
    {
        'title': '[FPV QUIZ] Antensiz Çalıştırılan VTX Vericisinde İlk Ne Zarar Görür?',
        'summary': 'FPV dünyasının en kritik kuralı! Antensiz batarya takılan bir analog veya dijital VTX kartında ne gerçekleşir?',
        'headline': 'FPV TEST: VTX VE ANTEN',
        'subhead': 'Antensiz Güç Verilen VTX Kartında Ne Olur?',
        'points': [
            "A) Pil anında biter",
            "B) VTX Güç Amplifikatör Çipi Aşırı Isınarak Yanar",
            "C) Kamera merceği çatlar",
            "D) Motorlar ters döner"
        ],
        'correct_answer': 'B) VTX Güç Amplifikatörü (PA) aşırı ısıdan saniyeler içinde yanar',
        'tags': '#vtx #fpvquiz #droneguvenlik #pozitronmarket #fpvturkey'
    }
]

# --- Extra diversity formats (new mechanisms) ---
MYTH_BUSTERS = [
    {
        'title': '[EFSANE] "Yüksek KV Motor Her Zaman Daha Hızlıdır" — Yanlış!',
        'myth': 'Pilotlar arasında yüksek KV motorun her zaman daha hızlı olduğu sanılır.',
        'reality': 'Yüksek KV daha fazla devir verir ama torku düşürür. Ağır pervanede motor aşırı ısınır, verim düşer ve akım tüketimi artar. Doğru motor, pervaneniz ve pil hücre sayınızla uyumlu olandır.',
        'points': [
            "[EFSANE] Yüksek KV = Daha fazla hız",
            "[GERCEK] Tork ve devir dengesi önemlidir",
            "[COZUM] 6S 5 inç için 1750-1950KV ideal aralıktır"
        ],
        'tags': '#fpvefsane #motorkv #fpvbilgi #pozitronmarket #dronetopla'
    },
    {
        'title': '[EFSANE] "Lipo Pili Tamamen Bitene Kadar Kullanmak Zararsız" — Yanlış!',
        'myth': 'Lipo pili 3.0V altına düşürmenin bir zararı olmadığı düşünülür.',
        'reality': 'Hücre voltajını 3.5V altına düşürmek Lipo kimyasını kalıcı olarak bozar. Pil şişer, kapasitesi düşer ve yangın riski oluşur. İniş voltajı 3.5V olmalıdır.',
        'points': [
            "[EFSANE] 3.0V altına inmek sorun değil",
            "[GERCEK] 3.5V altı hücreyi kalıcı bozar",
            "[COZUM] Uçuş sonrası pili depolama voltajına getir"
        ],
        'tags': '#lipo #pilbakimi #fpvguvenlik #pozitronmarket #droneguvenlik'
    },
    {
        'title': '[EFSANE] "Antensiz VTX Testi Kısa Sürede Zarar Vermez" — Yanlış!',
        'myth': 'Kısa bir antensiz güç testinin VTX için güvenli olduğu sanılır.',
        'reality': 'VTX güç amplifikatörü anten yükü olmadan saniyeler içinde aşırı ısınıp yanar. Anten bağlamadan asla güç vermeyin; yüklü bir anten veya uygun bir yük direnci kullanın.',
        'points': [
            "[EFSANE] Kısa test zarar vermez",
            "[GERCEK] PA çipi saniyeler içinde yanar",
            "[COZUM] Her zaman anten takılı iken güç ver"
        ],
        'tags': '#vtx #fpvguvenlik #dronebakim #pozitronmarket #fpvturkey'
    }
]

MAINTENANCE_CHECKS = [
    {
        'title': '[BAKIM] Her 10 Uçuşta Yapılması Gereken FPV Kontrol Listesi',
        'intro': 'FPV drone kazaların çoğu küçük bir bakım eksikliğinden başlar. İşte her 10 uçuşta tekrarlaman gereken 5 adım:',
        'points': [
            "[KONTROL] Motor vidaları ve pervane somunlarını sıkılığını doğrula",
            "[KONTROL] Kablo lehimlerinde çatlak veya soğuk lehim ara",
            "[KONTROL] Frame çatlaklarını ve vidaların gevşemesini incele",
            "[KONTROL] Anten konnektörünü (UFL/MMCX) hafifçe yokla",
            "[KONTROL] Betaflight motor sıcaklığı ve RSSI değerlerini kontrol et"
        ],
        'tags': '#fpvbakim #dronebakim #kontrollistesi #pozitronmarket #fpvpilot'
    },
    {
        'title': '[BAKIM] Kışın FPV Drone İçin 5 Kritik Depolama Kuralı',
        'intro': 'Soğuk ve nemli havada yanlış depolama, bahara kadar donanımını bitirebilir. İşte kışlık bakım listesi:',
        'points': [
            "[KONTROL] Lipo pilleri 3.8V depolama voltajında sakla",
            "[KONTROL] Drone'u nem alıcı ile kapalı kutuda tut",
            "[KONTROL] Pilleri düşük sıcaklıkta şarj etme",
            "[KONTROL] Uçuş sonrası kondansatörleri birkaç saniye boşalt"
        ],
        'tags': '#lipobakimi #kisbakimi #fpvdepolama #pozitronmarket #dronetopla'
    }
]

BEGINNER_ROADMAP = [
    {
        'title': '[YOL HARITASI] Sıfırdan FPV Pilotu Olma Rehberi (5 Adım)',
        'intro': 'FPV dünyasına yeni mi başlıyorsun? Bu 5 adımı sırayla takip ederek ilk uçuşuna güvenle çık:',
        'steps': [
            "[ADIM 1] Simülatörde en az 10 saat pratik yap (Liftoff / Velocidrone)",
            "[ADIM 2] Küçük bir whoop veya 3 inç ile başla, 5 inç ile başlama",
            "[ADIM 3] Gözlük ve kumanda bağlantısını yerde test et",
            "[ADIM 4] Açık bir arazide, GPS ve failsafe ayarlarını doğrula",
            "[ADIM 5] İlk 20 uçuşu sakin uç, sadece hover ve temel manevralar"
        ],
        'tags': '#fpvbaslangic #yenibaslayan #fpvyolharitasi #pozitronmarket #dronebuild'
    },
    {
        'title': '[YOL HARITASI] İlk FPV Donanımını Seçerken 4 Altın Kural',
        'intro': 'İlk donanım seçimi toplam maliyetini ve öğrenme hızını doğrudan etkiler. Kolay bir başlangıç için:',
        'steps': [
            "[ADIM 1] Bütçeni önce gözlük ve kumandaya ayır",
            "[ADIM 2] Uyumlu stack + motor + pervane setini birlikte seç",
            "[ADIM 3] En az 4 adet yedek pervane ve 2 yedek Lipo al",
            "[ADIM 4] Yedek parça bulunabilirliği yüksek markaları tercih et"
        ],
        'tags': '#fpvdonanim #dronebuild #yenibaslayan #pozitronmarket #dronetopla'
    }
]

# --- Post Types & Reels Formats Metadata ---
ALL_POST_TYPES = [
    {"id": "product_spotlight", "name": "Ürün Spot Işığı & Detay", "icon": "📦", "desc": "Öne çıkan donanım ve teknik özellikleri"},
    {"id": "deal_drop", "name": "İndirim & Fırsat Alarmı", "icon": "🏷️", "desc": "Haftalık kupon ve indirim kodlu kampanya"},
    {"id": "pilot_tip", "name": "FPV Pilot İpuçları & Püf Noktaları", "icon": "💡", "desc": "Uçuş tekniği, lehim ve pratik saha taktikleri"},
    {"id": "hardware_battle", "name": "Donanım Karşılaştırması & Kıyas", "icon": "⚔️", "desc": "Analog vs Dijital, Motor boyutları ve stack karşılaştırması"},
    {"id": "drone_build_showcase", "name": "Drone Toplama & Build Rehberi", "icon": "🛠️", "desc": "Komple parça listesi ve montaj kılavuzu"},
    {"id": "carousel_guide", "name": "Çoklu Kaydırmalı Kılavuz (Carousel)", "icon": "📑", "desc": "4 slaytlık adım adım eğitim kartları"},
    {"id": "mistake_breakdown", "name": "Sık Yapılan FPV Hataları", "icon": "⚠️", "desc": "Motor yakma, ters pervane ve PID hataları analizi"},
    {"id": "community_quiz", "name": "Topluluk Soru & Quiz", "icon": "❓", "desc": "Pilotlara yönelik teknik soru ve etkileşim testi"},
    {"id": "myth_buster", "name": "FPV Efsaneleri ve Yanlışlar", "icon": "🔍", "desc": "LiPo, anten ve menzil hakkındaki yanlış inanışlar"},
    {"id": "maintenance_checklist", "name": "Uçuş Öncesi Bakım & Kontrol", "icon": "✅", "desc": "Saha hazırlığı ve donanım kontrol listesi"},
    {"id": "beginner_roadmap", "name": "Yeni Başlayan Yol Haritası", "icon": "🗺️", "desc": "Simülatörden ilk 5 inç freestyle uçuşa adımlar"},
    {"id": "flight_weather_radar", "name": "Uçuş Hava Durumu Radarı", "icon": "🌤️", "desc": "Rüzgar, sıcaklık ve FPV hava durumu değerlendirmesi"},
    {"id": "tool_showcase", "name": "Atölye ve Araç Tanıtımı", "icon": "🔧", "desc": "Lehim istasyonları, duman önleyiciler ve araçlar"},
    {"id": "spot_guide", "name": "Uçuş Noktaları Rehberi", "icon": "📍", "desc": "Türkiye'deki güvenli ve popüler uçuş lokasyonları"},
    {"id": "review_highlight", "name": "Kullanıcı Yorumları & Değerlendirme", "icon": "⭐", "desc": "Gerçek pilot deneyimleri ve parça incelemeleri"},
    {"id": "seo_article", "name": "Mühendislik & Teknik Rehber", "icon": "📘", "desc": "Derinlemesine motor dinamikleri ve elektronik makalesi"}
]

# 8 Distinct Reels Formats (including toggleable Real FPV Video Reels)
REELS_TYPES_METADATA = [
    {
        "id": "real_fpv_broll",
        "name": "Gerçek FPV Uçuş Videosu",
        "icon": "🎥",
        "desc": "Arka planda gerçek FPV uçuş b-roll çekimi ve üzerinde dinamik Pozitron bilgi katmanı",
        "default_enabled": True
    },
    {
        "id": "freestyle_acro",
        "name": "Akro & Hız Freestyle",
        "icon": "⚡",
        "desc": "Gap-dive, power loop, bando dalışları ve yüksek tempolu adrenalin kurgusu",
        "default_enabled": True
    },
    {
        "id": "hardware_vs",
        "name": "Donanım Karşılaştırma (VS)",
        "icon": "⚔️",
        "desc": "2207 vs 2306 motor, Analog vs HD veya Stack karşılaştırmalı hızlı karar videosu",
        "default_enabled": True
    },
    {
        "id": "quick_tip_fix",
        "name": "15 Saniyede Pratik İpucu",
        "icon": "💡",
        "desc": "Betaflight ince ayarları, motor yönü çevirme veya sahada hayat kurtaran lehim tüyosu",
        "default_enabled": True
    },
    {
        "id": "mistake_warning",
        "name": "Bu Hatayı Sakın Yapma!",
        "icon": "⚠️",
        "desc": "Antensiz VTX yakma, ters pervane kırımını ve failsafe felaketlerini önleyen uyarı",
        "default_enabled": True
    },
    {
        "id": "secret_spot",
        "name": "Gizli Uçuş Sahası & Spot",
        "icon": "📍",
        "desc": "Türkiye'nin terk edilmiş bando binaları, kanyonları ve tepe uçuş rotaları",
        "default_enabled": True
    },
    {
        "id": "product_cinematic",
        "name": "Sinematik Donanım Vitrini",
        "icon": "💎",
        "desc": "Makro karbon detayları, fırçasız motor sargıları, canlı fiyat ve stok kartı",
        "default_enabled": True
    },
    {
        "id": "flash_deal",
        "name": "Flaş Fırsat & Stok Alarmı",
        "icon": "🔥",
        "desc": "Sınırlı stok indirimleri, kupon çağrıları ve aciliyet hissi yüksek e-ticaret vitrini",
        "default_enabled": True
    }
]

ALL_REELS_TYPES = [t['id'] for t in REELS_TYPES_METADATA]

REELS_TYPE_THEME_MAP = {
    'real_fpv_broll': ['drone_build_showcase', 'spot_guide', 'product_spotlight', 'pilot_tip'],
    'freestyle_acro': ['drone_build_showcase', 'spot_guide', 'pilot_tip'],
    'hardware_vs': ['hardware_battle'],
    'quick_tip_fix': ['pilot_tip', 'tool_showcase'],
    'mistake_warning': ['mistake_breakdown', 'maintenance_checklist'],
    'secret_spot': ['spot_guide'],
    'product_cinematic': ['product_spotlight'],
    'flash_deal': ['deal_drop'],
}

# --- Reels theme rotation (fixes the 100% product_spotlight problem) ---
REELS_THEME_WEIGHTS = {
    'community_quiz': 0.14,
    'product_spotlight': 0.13,
    'hardware_battle': 0.11,
    'pilot_tip': 0.10,
    'mistake_breakdown': 0.10,
    'drone_build_showcase': 0.09,
    'myth_buster': 0.07,
    'spot_guide': 0.06,
    'flight_weather_radar': 0.05,
    'maintenance_checklist': 0.05,
    'deal_drop': 0.05,
    'tool_showcase': 0.03,
    'review_highlight': 0.02,
}

REELS_HOOKS = {
    'community_quiz': [
        "[REELS QUIZ] Bu FPV sorusunu 5 saniyede bilen gerçek pilot!",
        "[BILGI TESTI] Cevabı sonuna kadar izle, bilemezsen kaydet!",
        "[FPSORU] Yanlış cevap veren pilot sayısı azımsanmayacak kadar çok!"
    ],
    'product_spotlight': [
        "[REELS] Bu donanımı uçan pilotlar farkı hemen anlıyor!",
        "[STOK] Yeni sezonun en çok konuşulan FPV donanımı!",
        "[ONERI] Bütçeni zorlamadan performansını artırmanın yolu."
    ],
    'hardware_battle': [
        "[DUELLO] İki donanım, tek kazanan! Hangisini seçerdin?",
        "[KARSILASTIRMA] Aradaki farkı 10 saniyede anlıyorsun!",
        "[VS] Pilotlar ikiye bölündü: hangi taraf daha güçlü?"
    ],
    'pilot_tip': [
        "[PILOT TAVSIYESI] Bu ipucu uçuş süresini ciddi artırıyor!",
        "[TAKTIK] Ustaların sessizce kullandığı FPV ayarı!",
        "[IPUCU] Bunu erken bilseydim yüzlerce lira tasarruf ederdim."
    ],
    'mistake_breakdown': [
        "[HATA] Yeni pilotların %90'ının yaptığı bu hatayı sen de yapıyor musun?",
        "[UYARI] Bu hata drone'unu bir günde bitirebilir!",
        "[KIRIM] En pahalı FPV hatası ve nasıl önlenir?"
    ],
    'drone_build_showcase': [
        "[BUILD] Sıfırdan toplanan bu FPV canavarını incele!",
        "[ATOLYE] Parça parça güç katan bir build hikayesi!",
        "[SETUP] Bu build ile ulaşılan hız inanılmaz!"
    ],
    'myth_buster': [
        "[EFSANE AVCISI] FPV'de yayılan bu bilgi tamamen yanlış!",
        "[YANLIS BILINEN] Herkesin doğru sandığı büyük FPV efsanesi!",
        "[GERCEK] Bu iddiayı tarihe gömüyoruz!"
    ],
    'spot_guide': [
        "[SPOT] Türkiye'nin en iyi FPV uçuş noktalarından biri!",
        "[SAHA] Bu spotta uçan pilot bir daha başka yere gitmiyor!",
        "[ROTA] Hafta sonu için mükemmel FPV rotası!"
    ],
    'flight_weather_radar': [
        "[UCUS RADARI] Bugün uçmak için hava şartları nasıl?",
        "[HAVA DURUMU] Pilotlar bugün hangi saatte uçmalı?",
        "[RADAR] Rüzgar ve görüş şartları uçuşa uygun mu?"
    ],
    'maintenance_checklist': [
        "[BAKIM] Bu kontrol listesi sana yüzlerce lira kazandırır!",
        "[KONTROL] Her 10 uçuşta bu adımları atlıyorsan dur!",
        "[LISTE] Donanımını uzun yıllar koruyan adımlar!"
    ],
    'deal_drop': [
        "[FIRSAT] Bu indirim çok yakında bitecek, acele et!",
        "[KAMPANYA] Haftanın en iyi FPV fırsatı burada!",
        "[INDIRIM] Bu fiyata bir daha bulamayabilirsin!"
    ],
    'tool_showcase': [
        "[ARAC] Bu ücretsiz araç FPV toplamayı çocuk oyuncağına çeviriyor!",
        "[SIHIRBAZ] Motor-ESC uyumunu saniyeler içinde test et!",
        "[ONLINE ARAC] Yanlış parça siparişine son!"
    ],
    'review_highlight': [
        "[YORUM] Pilotların bu donanım hakkında söyledikleri!",
        "[DENEYIM] Gerçek kullanıcı deneyimi: fiyatına değer mi?",
        "[INCELEME] Alıp memnun kalanların ortak görüşü!"
    ],
    # 8 Reels Formats Hooks
    'real_fpv_broll': [
        "[GERCEK UCUS] Kokpitteymiş gibi hisset! Gerçek FPV uçuşu!",
        "[FPV ADRENALIN] Gözlüğü taktığın an dünya değişiyor!",
        "[PILOT GOZUNDEN] Gerçek FPV akrobasisi ve saf hız!"
    ],
    'freestyle_acro': [
        "[AKRO FREESTYLE] Bu gap'ten geçebilecek kaç pilot var?",
        "[HIZ & ADRENALIN] 150 km/s hızla engellerin arasından süzülüş!",
        "[PRO PILOT] Bu manevrayı simülatörde kaç saat çalıştın?"
    ],
    'hardware_vs': [
        "[DUELLO] İki efsane karşı karşıya! Hangisini seçerdin?",
        "[KARSILASTIRMA] Fiyat/performans farkını 10 saniyede gör!",
        "[SECIM] Pilotlar ikiye bölündü: Hangi taraf daha güçlü?"
    ],
    'quick_tip_fix': [
        "[15S IPUCU] Sahada hayat kurtaran o küçük ayar!",
        "[ATOLYE SIRRI] Motor yönünü BLHeli olmadan 10 saniyede çevir!",
        "[PILOT HILESI] Lehim yaparken bunu uygula, kopma derdini unut!"
    ],
    'mistake_warning': [
        "[UYARI] Bu hatayı sakın yapma! VTX anında çöp olur!",
        "[KIRIM ALARMI] Yeni pilotların %90'ının düştüğü büyük tuzak!",
        "[DIKKAT] Kalkıştan önce bu testi yapmadıysan quad'ı unut!"
    ],
    'secret_spot': [
        "[GIZLI SPOT] Türkiye'nin en iyi FPV uçuş noktalarından biri!",
        "[BANDO ROTA] Bu terk edilmiş mekanda uçmaya cesaretin var mı?",
        "[SAHA REHBERI] Hafta sonu için keşfedilmemiş FPV cenneti!"
    ],
    'product_cinematic': [
        "[DONANIM] 8K Makro detaylarla yeni sezon FPV canavarı!",
        "[VITRIN] Titreşimsiz uçuşun gizli kahramanı bu donanım!",
        "[KALITE] Pozitron vitrininin en çok konuşulan parçası!"
    ],
    'flash_deal': [
        "[FLAS FIRSAT] Stoklar sınırlı! Bu fiyata bir daha gelmez!",
        "[KAMPANYA] Haftanın en çok aranan FPV donanımında indirim!",
        "[STOK ALARMI] Tükenmeden yakala, aynı gün kargoda!"
    ]
}

REELS_CTA = {
    'community_quiz': "Cevabını yoruma yaz! Doğru cevabı story'de açıklıyoruz. Yeni başlayanlar için tüm donanım: pozitronmarket.com",
    'product_spotlight': "Detaylar ve fiyat için profildeki linke göz at. Yoruma 'LINK' yazarsan DM'den hemen gönderelim.",
    'hardware_battle': "Sen hangisini seçerdin? Yoruma yaz! İkisini de incelemek için: pozitronmarket.com",
    'pilot_tip': "Bu ipucunu kaydet, uçuşta işine yarayacak. Daha fazlası için takipte kal. pozitronmarket.com",
    'mistake_breakdown': "Başına geldi mi? Yorumlarda paylaş. Kırılmaz yedek parçalar: pozitronmarket.com",
    'drone_build_showcase': "Parça listesini yoruma istemeyi unutma. Tüm build donanımı: pozitronmarket.com",
    'myth_buster': "Sen bu efsaneye inanıyor muydun? Yoruma yaz! Doğrusunu öğrenmek için takipte kal.",
    'spot_guide': "Bu spotu kaydet, hafta sonu planına ekle. Uçuş donanımı: pozitronmarket.com",
    'flight_weather_radar': "Günlük uçuş radarı için takipte kal. Her koşul için donanım: pozitronmarket.com",
    'maintenance_checklist': "Bu listeyi kaydet! Yedek parça ve korumalar: pozitronmarket.com",
    'deal_drop': "Stoklar tükenmeden profildeki linki ziyaret et. Yoruma 'FIYAT' yaz, DM'den fiyat gönderelim.",
    'tool_showcase': "Aracı hemen dene: pozitronmarket.com/drone-toplama-sihirbazi",
    'review_highlight': "Sen de deneyimini paylaş. Binlerce pilot gibi sen de güvenle sipariş ver: pozitronmarket.com",
    # 8 Reels Formats CTAs
    'real_fpv_broll': "Bu hissi yaşamak istediğin arkadaşını etiketle! Hayalindeki FPV setup'ı topla: pozitronmarket.com",
    'freestyle_acro': "Senin en sevdiğin akro manevrası hangisi? Yoruma yaz! Dayanıklı freestyle parçaları: pozitronmarket.com",
    'hardware_vs': "Sen hangi tarafı seçerdin? Yoruma yaz! İkisini de incelemek için: pozitronmarket.com",
    'quick_tip_fix': "Bu taktiği kaydet, sahada çok lazım olacak. Pratik pilot aletleri: pozitronmarket.com",
    'mistake_warning': "Senin başına geldi mi? Yorumlarda anlat. Kırılmaz yedek parçalar: pozitronmarket.com",
    'secret_spot': "Bu spotu kaydet, hafta sonu ekiple git! Uçuş donanımı: pozitronmarket.com",
    'product_cinematic': "Detaylar ve canlı fiyat için profildeki linke göz at. Yoruma 'FIYAT' yaz, linki anında DM'den atalım.",
    'flash_deal': "Fırsatı kaçırmamak için hemen pozitronmarket.com'u ziyaret et. Yoruma 'KUPON' yaz!"
}

REELS_EXTRA_TAGS = "#reels #fpvreels #dronereels #fpvvideo #dronevideo"

# Theme-aware cinematic style presets so reel video prompts are not identical.
REEL_STYLE_PRESETS = {
    'studio_neon': "dark high-tech studio with neon cyan and amber rim lighting, macro carbon fiber detail",
    'golden_field': "sunny outdoor FPV field with warm golden-hour light, dynamic low-angle tracking shot",
    'holo_lab': "futuristic lab bench with blue holographic overlays, slow controlled dolly-in",
    'mountain_dawn': "misty mountain ridge at dawn with soft volumetric light, sweeping aerial reveal",
    'clean_stage': "clean white product stage with soft studio softbox lighting, elegant rotating pedestal",
    'workshop_grit': "moody workshop with sparks and warm tungsten light, gritty industrial macro pans",
    'night_city': "night city rooftop with bokeh lights and cool teal highlights, slow sweeping pan",
    'flatlay_slider': "bright tech table with top-down flat-lay, precise robotic slider movement",
}

# Backward-compatible flat list (used as fallback when no combo specifies a style).
REEL_VISUAL_STYLES = list(REEL_STYLE_PRESETS.values())

# Hook tone -> which of the 3 theme hooks to prefer (keeps hook variety controlled).
REEL_HOOK_TONES = {
    'question': 0,
    'bold': 1,
    'listicle': 2,
    'challenge': 0,
    'versus': 1,
    'warning': 1,
    'story': 2,
}

# Curated random combinations. Each Reel randomly draws ONE of these presets,
# bundling reels_type + theme + visual style + video mode + hook tone into a coherent look.
REEL_COMBINATIONS = [
    # Explicit 8 Reels Types Presets
    {'id': 'reels_real_broll',   'reels_type': 'real_fpv_broll',   'themes': ['spot_guide', 'drone_build_showcase', 'product_spotlight'], 'style': 'golden_field', 'video_mode': 'mode2', 'tone': 'story'},
    {'id': 'reels_acro_dawn',    'reels_type': 'freestyle_acro',   'themes': ['drone_build_showcase', 'spot_guide'], 'style': 'mountain_dawn', 'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'reels_acro_field',   'reels_type': 'freestyle_acro',   'themes': ['drone_build_showcase', 'pilot_tip'],  'style': 'golden_field',  'video_mode': 'mode1', 'tone': 'challenge'},
    {'id': 'reels_vs_stage',     'reels_type': 'hardware_vs',      'themes': ['hardware_battle'],       'style': 'clean_stage',    'video_mode': 'mode1', 'tone': 'versus'},
    {'id': 'reels_vs_neon',      'reels_type': 'hardware_vs',      'themes': ['hardware_battle'],       'style': 'studio_neon',    'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'reels_tip_workshop', 'reels_type': 'quick_tip_fix',    'themes': ['pilot_tip'],             'style': 'workshop_grit',  'video_mode': 'mode1', 'tone': 'listicle'},
    {'id': 'reels_tip_flatlay',  'reels_type': 'quick_tip_fix',    'themes': ['pilot_tip'],             'style': 'flatlay_slider', 'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'reels_warn_workshop','reels_type': 'mistake_warning',  'themes': ['mistake_breakdown'],     'style': 'workshop_grit',  'video_mode': 'mode1', 'tone': 'warning'},
    {'id': 'reels_warn_holo',    'reels_type': 'mistake_warning',  'themes': ['mistake_breakdown'],     'style': 'holo_lab',       'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'reels_spot_mountain','reels_type': 'secret_spot',      'themes': ['spot_guide'],            'style': 'mountain_dawn',  'video_mode': 'mode1', 'tone': 'story'},
    {'id': 'reels_spot_night',   'reels_type': 'secret_spot',      'themes': ['spot_guide'],            'style': 'night_city',     'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'reels_prod_neon',    'reels_type': 'product_cinematic','themes': ['product_spotlight'],     'style': 'studio_neon',    'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'reels_prod_stage',   'reels_type': 'product_cinematic','themes': ['product_spotlight'],     'style': 'clean_stage',    'video_mode': 'mode1', 'tone': 'listicle'},
    {'id': 'reels_deal_neon',    'reels_type': 'flash_deal',       'themes': ['deal_drop'],             'style': 'studio_neon',    'video_mode': 'mode1', 'tone': 'bold'},

    # Classic thematic rotation presets
    {'id': 'quiz_neon',          'reels_type': 'quick_tip_fix',    'themes': ['community_quiz'],        'style': 'studio_neon',    'video_mode': 'mode1', 'tone': 'question'},
    {'id': 'quiz_holo',          'reels_type': 'quick_tip_fix',    'themes': ['community_quiz'],        'style': 'holo_lab',       'video_mode': 'mode1', 'tone': 'challenge'},
    {'id': 'quiz_flatlay',       'reels_type': 'quick_tip_fix',    'themes': ['community_quiz'],        'style': 'flatlay_slider', 'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'battle_stage',       'reels_type': 'hardware_vs',      'themes': ['hardware_battle'],       'style': 'clean_stage',    'video_mode': 'mode1', 'tone': 'versus'},
    {'id': 'battle_neon',        'reels_type': 'hardware_vs',      'themes': ['hardware_battle'],       'style': 'studio_neon',    'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'tip_workshop',       'reels_type': 'quick_tip_fix',    'themes': ['pilot_tip'],             'style': 'workshop_grit',  'video_mode': 'mode1', 'tone': 'listicle'},
    {'id': 'tip_flatlay',        'reels_type': 'quick_tip_fix',    'themes': ['pilot_tip'],             'style': 'flatlay_slider', 'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'mistake_workshop',   'reels_type': 'mistake_warning',  'themes': ['mistake_breakdown'],     'style': 'workshop_grit',  'video_mode': 'mode1', 'tone': 'warning'},
    {'id': 'mistake_holo',       'reels_type': 'mistake_warning',  'themes': ['mistake_breakdown'],     'style': 'holo_lab',       'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'build_field',        'reels_type': 'freestyle_acro',   'themes': ['drone_build_showcase'],  'style': 'golden_field',   'video_mode': 'mode1', 'tone': 'story'},
    {'id': 'build_night',        'reels_type': 'freestyle_acro',   'themes': ['drone_build_showcase'],  'style': 'night_city',     'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'myth_holo',          'reels_type': 'quick_tip_fix',    'themes': ['myth_buster'],           'style': 'holo_lab',       'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'myth_workshop',      'reels_type': 'quick_tip_fix',    'themes': ['myth_buster'],           'style': 'workshop_grit',  'video_mode': 'mode1', 'tone': 'story'},
    {'id': 'maintenance_flatlay','reels_type': 'mistake_warning',  'themes': ['maintenance_checklist'],'style': 'flatlay_slider', 'video_mode': 'mode1', 'tone': 'listicle'},
    {'id': 'roadmap_holo',       'reels_type': 'quick_tip_fix',    'themes': ['beginner_roadmap'],      'style': 'holo_lab',       'video_mode': 'mode1', 'tone': 'listicle'},
    {'id': 'spot_mountain',      'reels_type': 'secret_spot',      'themes': ['spot_guide'],            'style': 'mountain_dawn',  'video_mode': 'mode1', 'tone': 'story'},
    {'id': 'spot_field',         'reels_type': 'secret_spot',      'themes': ['spot_guide'],            'style': 'golden_field',   'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'weather_dawn',       'reels_type': 'secret_spot',      'themes': ['flight_weather_radar'],  'style': 'mountain_dawn',  'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'weather_night',      'reels_type': 'secret_spot',      'themes': ['flight_weather_radar'],  'style': 'night_city',     'video_mode': 'mode1', 'tone': 'story'},
    {'id': 'deal_neon',          'reels_type': 'flash_deal',       'themes': ['deal_drop'],             'style': 'studio_neon',    'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'product_neon',       'reels_type': 'product_cinematic','themes': ['product_spotlight'],     'style': 'studio_neon',    'video_mode': 'mode1', 'tone': 'bold'},
    {'id': 'product_stage',      'reels_type': 'product_cinematic','themes': ['product_spotlight'],     'style': 'clean_stage',    'video_mode': 'mode1', 'tone': 'listicle'},
    {'id': 'product_night',      'reels_type': 'product_cinematic','themes': ['product_spotlight'],     'style': 'night_city',     'video_mode': 'mode1', 'tone': 'story'},
    {'id': 'tool_holo',          'reels_type': 'quick_tip_fix',    'themes': ['tool_showcase'],         'style': 'holo_lab',       'video_mode': 'mode1', 'tone': 'listicle'},
    {'id': 'review_stage',       'reels_type': 'product_cinematic','themes': ['review_highlight'],      'style': 'clean_stage',    'video_mode': 'mode1', 'tone': 'story'},
]

# --- Text diversity layer: hashtag sets, caption structures, CTA closers ---
HASHTAG_SETS = {
    'broad': '#fpv #drone #dronelife #fpvdrone #dronevideo #droneoftheday',
    'niche': '#fpvracing #fpvfreestyle #cinedrone #digitalfpv #fpvbuild #elrs #bfphoton',
    'local': '#türkiyefpv #istanbuldrone #ankarafpv #izmirfpv #teknofest #türkiyedrone',
    'product': '#dronetopla #dronehardware #fpvdonanim #droneparça #fpvmalzeme #droneaksesuar',
    'community': '#fpvpilot #fpvturkey #dronecommunity #fpvfamily #dronetürkiye #fpvakademi',
    'lifestyle': '#fpvlifestyle #makerlife #3dprinting #teknoloji #dronefotografi #havacilik',
}

CAPTION_STYLES = {
    'save_for_later': {
        'opener': 'KAYDET -> Bu içerik sonra lazım olacak.',
        'closer': 'Kaydet ki bir daha aramak zorunda kalmayasın.'
    },
    'share_with_friend': {
        'opener': "Bunu bir FPV'ci arkadaşına gönder!",
        'closer': 'Yeni başlayan bir arkadaşına gönder, ona zaman kazandır.'
    },
    'quick_read': {
        'opener': 'HIZLI OKU: 20 saniyede özet.',
        'closer': 'Faydalı bulduysan kaydet ve takipte kal.'
    },
    'expert_note': {
        'opener': 'PILOT NOTU: Tecrübeyle sabit bir detay.',
        'closer': 'Senin de bir notun varsa yoruma yaz.'
    },
    'debate': {
        'opener': 'Bu konuda pilotlar ikiye bölünmüş durumda.',
        'closer': 'Sen hangi taraftasın? Yoruma yaz.'
    },
}

CTA_CLOSERS = [
    "Ürün ve detaylar: pozitronmarket.com",
    "Profildeki linkten hemen incele: pozitronmarket.com",
    "Yoruma 'LINK' yaz, DM'den gönderelim.",
    "Tüm FPV donanımı: pozitronmarket.com",
    "Stokları kontrol et: pozitronmarket.com",
    "Daha fazlası için takipte kal | pozitronmarket.com",
]

BILINGUAL_TAGLINES = {
    'product_spotlight': "Power up your FPV fleet with pro-grade gear. Ship within Turkey.",
    'community_quiz': "Think you know FPV? Drop your answer below!",
    'hardware_battle': "Two setups, one winner. Which side are you on?",
    'pilot_tip': "A pro tip that saves you money and crashes.",
    'mistake_breakdown': "The FPV mistake that costs beginners the most.",
    'drone_build_showcase': "Screw-by-screw FPV build showcase.",
    'myth_buster': "The FPV myth everyone still believes.",
    'maintenance_checklist': "Keep your drone alive: maintenance checklist.",
    'beginner_roadmap': "From zero to FPV pilot: the step-by-step roadmap.",
    'spot_guide': "The best FPV flying spots in Turkey.",
    'flight_weather_radar': "Daily FPV flying weather radar.",
    'deal_drop': "This week's best FPV deal.",
    'tool_showcase': "Free FPV builder tool - test compatibility instantly.",
    'review_highlight': "What real pilots say before buying.",
}

class ContentGenerator:
    def __init__(self, gemini_api_key: str = ""):
        self.gemini_api_key = gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
        self.models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
        self._session_recent_titles = []
        self._session_recent_product_ids = []
        self._session_recent_caption_sigs = []
        self._session_recent_combo_ids = []
        self.bilingual_enabled = False

    def set_api_key(self, key: str):
        self.gemini_api_key = key

    def set_bilingual(self, enabled: bool):
        self.bilingual_enabled = bool(enabled)

    def _llm_available(self) -> bool:
        """True if any text LLM (unified gateway or legacy Gemini) can write copy."""
        try:
            from llm_client import get_llm
            if get_llm().is_configured():
                return True
        except Exception:
            pass
        return bool(self.gemini_api_key)

    def generate_content(self, content_type: str = None, product_id: str = None, allowed_types: list = None) -> dict:
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
            'spot_guide', 'deal_drop', 'seo_article', 'review_highlight',
            'hardware_battle', 'mistake_breakdown', 'community_quiz',
            'myth_buster', 'maintenance_checklist', 'beginner_roadmap'
        ]

        requested_product_id = product_id

        # Respect user-configured enabled post types if provided
        if allowed_types:
            active_allowed = [t for t in valid_types if t in allowed_types]
            if active_allowed:
                valid_types = active_allowed
        
        recent_types = get_recent_posted_content_types(limit=5)
        db_titles = set(get_recent_posted_titles(limit=40))
        all_recent_titles = db_titles.union(set(self._session_recent_titles[-30:]))

        # Near-duplicate caption signatures (first 60 normalized chars) to stop
        # repetitive text that Instagram de-ranks.
        recent_captions = get_recent_captions(limit=30)
        recent_caption_sigs = set()
        for cap in recent_captions:
            sig = self._caption_signature(cap)
            if sig:
                recent_caption_sigs.add(sig)
        recent_caption_sigs.update(self._session_recent_caption_sigs[-40:])

        explicit_type = content_type if (content_type and content_type in valid_types) else None

        # 1. Smart Pillar Selection (diverse PR feed: builds, weather, guides, products, tips, battles, quizzes)
        if not content_type or content_type not in valid_types:
            candidate_types = [t for t in valid_types if not (recent_types and t == recent_types[0])]
            if not candidate_types:
                candidate_types = valid_types

            # Balanced PR & e-commerce diversity weights (16 distinct formats)
            type_weights = {
                'product_spotlight': 0.13,
                'drone_build_showcase': 0.10,
                'carousel_guide': 0.09,
                'hardware_battle': 0.09,
                'mistake_breakdown': 0.08,
                'community_quiz': 0.09,
                'flight_weather_radar': 0.07,
                'pilot_tip': 0.07,
                'myth_buster': 0.07,
                'maintenance_checklist': 0.05,
                'beginner_roadmap': 0.05,
                'tool_showcase': 0.04,
                'spot_guide': 0.04,
                'seo_article': 0.03,
                'review_highlight': 0.03,
                'deal_drop': 0.03
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
                content = self._generate_drone_build_showcase(product_id)
            elif cur_type == 'carousel_guide':
                content = self._generate_carousel_guide()
            elif cur_type == 'flight_weather_radar':
                content = self._generate_flight_weather_radar()
            elif cur_type == 'spot_guide':
                content = self._generate_spot_guide()
            elif cur_type == 'tool_showcase':
                content = self._generate_tool_showcase(product_id)
            elif cur_type == 'deal_drop':
                content = self._generate_deal_drop(product_id)
            elif cur_type == 'pilot_tip':
                content = self._generate_pilot_tip(product_id)
            elif cur_type == 'seo_article':
                content = self._generate_seo_article()
            elif cur_type == 'review_highlight':
                content = self._generate_review_highlight(product_id)
            elif cur_type == 'hardware_battle':
                content = self._generate_hardware_battle(product_id)
            elif cur_type == 'mistake_breakdown':
                content = self._generate_mistake_breakdown(product_id)
            elif cur_type == 'community_quiz':
                content = self._generate_community_quiz()
            elif cur_type == 'myth_buster':
                content = self._generate_myth_buster()
            elif cur_type == 'maintenance_checklist':
                content = self._generate_maintenance_checklist(product_id)
            elif cur_type == 'beginner_roadmap':
                content = self._generate_beginner_roadmap()
            else:
                content = self._generate_product_spotlight(product_id)

            # Humanize BEFORE the duplicate check so titles that only differ by
            # machine-made tags ("[FREKANS] ...") are correctly seen as duplicates.
            if content:
                content = humanize_content(content)

            if content and content.get('title'):
                is_dup_title = content.get('title') in all_recent_titles
                is_dup_caption = self._caption_signature(content.get('caption', '')) in recent_caption_sigs
                if explicit_type or not (is_dup_title or is_dup_caption):
                    break

            # If candidate was recently posted and not explicitly requested, rotate to a
            # DIFFERENT pillar instead of collapsing everything into product_spotlight.
            if not explicit_type:
                alt_types = [t for t in valid_types if t != content_type and t != 'carousel_guide' and t != 'seo_article']
                if not alt_types:
                    alt_types = [t for t in valid_types if t != content_type]
                content_type = random.choice(alt_types)
                product_id = None

        # Explicit product selection (Post Studio) must be honoured for EVERY post
        # type, not only product_spotlight. Previously non-product generators
        # hard-coded product_data=None so the chosen product's photo never rendered.
        if content and requested_product_id:
            cur_pd = content.get('product_data') or {}
            if not cur_pd.get('image_url') or content.get('product_id') != requested_product_id:
                try:
                    chosen_prod = self._get_candidate_product(requested_product_id)
                except Exception:
                    chosen_prod = None
                if chosen_prod:
                    content['product_data'] = chosen_prod
                    content['product_id'] = chosen_prod.get('id')

        if content:
            # Ensure DM / Comment Call-To-Action is attached to caption
            content['caption'] = self._append_dm_cta(content['caption'])
            # Rotating hashtag sets, caption structure, CTA and optional English line.
            content['bilingual_enabled'] = self.bilingual_enabled
            content = self._apply_text_diversity(content, content.get('content_type', content_type))
            # Final human-voice pass: strip machine-made markers, brackets, ALL-CAPS.
            content = humanize_content(content)
            self._session_recent_titles.append(content['title'])
            if len(self._session_recent_titles) > 50:
                self._session_recent_titles = self._session_recent_titles[-50:]
            sig = self._caption_signature(content['caption'])
            if sig:
                self._session_recent_caption_sigs.append(sig)
                if len(self._session_recent_caption_sigs) > 60:
                    self._session_recent_caption_sigs = self._session_recent_caption_sigs[-60:]
            if content.get('product_id'):
                self._session_recent_product_ids.append(content['product_id'])
                if len(self._session_recent_product_ids) > 50:
                    self._session_recent_product_ids = self._session_recent_product_ids[-50:]

        return content

    @staticmethod
    def _caption_signature(caption: str) -> str:
        """Normalized first-60-char signature used for fuzzy near-duplicate detection."""
        if not caption:
            return ''
        text = re.sub(r'\s+', ' ', str(caption)).strip().lower()
        text = re.sub(r'[^a-z0-9çğıöşü ]', '', text)
        return text[:60]

    @staticmethod
    def _split_hashtags(tags_str: str) -> list:
        if not tags_str:
            return []
        return [t for t in re.split(r'\s+', str(tags_str).strip()) if t.startswith('#')]

    def _pick_hashtags(self, content_type: str, base_tags: str) -> str:
        """Rotates hashtag sets per theme and de-duplicates, capping the total count."""
        theme_sets = {
            'product_spotlight': ['product', 'broad', 'lifestyle'],
            'deal_drop': ['product', 'broad'],
            'tool_showcase': ['lifestyle', 'niche', 'broad'],
            'community_quiz': ['community', 'niche', 'broad'],
            'hardware_battle': ['niche', 'community', 'broad'],
            'mistake_breakdown': ['community', 'niche'],
            'pilot_tip': ['niche', 'community'],
            'myth_buster': ['community', 'niche'],
            'maintenance_checklist': ['community', 'product'],
            'beginner_roadmap': ['community', 'broad', 'lifestyle'],
            'drone_build_showcase': ['niche', 'product'],
            'spot_guide': ['local', 'lifestyle'],
            'flight_weather_radar': ['local', 'broad'],
            'review_highlight': ['product', 'community'],
        }
        candidates = theme_sets.get(content_type, ['broad', 'community'])
        picks = random.sample(candidates, k=min(2, len(candidates)))
        rotated = []
        for name in picks:
            rotated.extend(self._split_hashtags(HASHTAG_SETS.get(name, '')))

        merged = self._split_hashtags(base_tags) + rotated
        seen = set()
        unique = []
        for tag in merged:
            low = tag.lower()
            if low not in seen:
                seen.add(low)
                unique.append(tag)
        return ' '.join(unique[:22])

    def _apply_text_diversity(self, content: dict, content_type: str) -> dict:
        """
        Applies rotating caption structure, hook formula, CTA closer, hashtag set and
        (optionally) a bilingual English line so consecutive posts do not look templated.
        """
        caption = content.get('caption', '') or ''
        # 1. Caption structure style (applied with probability to preserve natural voice).
        if random.random() < 0.6:
            style_name = random.choice(list(CAPTION_STYLES.keys()))
            style = CAPTION_STYLES[style_name]
            if style['opener'] not in caption:
                caption = f"{style['opener']}\n\n{caption}"
            caption = f"{caption}\n\n{style['closer']}"
            content['caption_style'] = style_name
        else:
            content['caption_style'] = 'plain'

        # 2. Rotating CTA closer (skip if the caption already carries a DM call-to-action).
        if 'OTOMATIK DM' not in caption:
            closer = random.choice(CTA_CLOSERS)
            if closer not in caption:
                caption = f"{caption}\n\n{closer}"
            content['cta_variant'] = closer
        else:
            content['cta_variant'] = 'dm_auto'

        # 3. Optional bilingual English tagline.
        if content.get('bilingual_enabled'):
            en = BILINGUAL_TAGLINES.get(content_type)
            if en and en not in caption:
                caption = f"{caption}\n\n[EN] {en}"
                content['bilingual'] = True

        content['caption'] = caption.strip()

        # 4. Rotating hashtag sets.
        content['hashtags'] = self._pick_hashtags(content_type, content.get('hashtags', ''))
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
        if self._llm_available():
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

    def _generate_tool_showcase(self, product_id: str = None) -> dict:
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

        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('tool_showcase', {
                'tool_title': title, 'caption_draft': caption, 'visual_summary': visual_summary
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']

        prod = self._get_candidate_product(product_id) if product_id else None
        return {
            'content_type': 'tool_showcase',
            'product_id': prod.get('id') if prod else None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': prod if prod else None,
            'tool_info': tool_info
        }

    def _generate_deal_drop(self, product_id: str = None) -> dict:
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

        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('deal_drop', {
                'coupon_code': coupon_code, 'discount_desc': discount_desc
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']

        prod = self._get_candidate_product(product_id) if product_id else None
        if prod:
            p_name = prod.get('name_tr') or prod.get('name_en') or ''
            if p_name:
                title = f"[FIRSAT] {p_name} — {deal['code']} Kuponu Aktif!"
                visual_summary['subhead'] = f"{p_name[:32]} ve FPV parçalarında geçerli"

        return {
            'content_type': 'deal_drop',
            'product_id': prod.get('id') if prod else None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': prod if prod else None,
            'tool_info': {'coupon_code': coupon_code}
        }

    def _generate_pilot_tip(self, product_id: str = None) -> dict:
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
        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('pilot_tip', {
                'tip_title': tip['title'], 'tip_summary': tip['summary']
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']

        prod = self._get_candidate_product(product_id) if product_id else None
        return {
            'content_type': 'pilot_tip',
            'product_id': prod.get('id') if prod else None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': prod if prod else None,
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

    def _generate_review_highlight(self, product_id: str = None) -> dict:
        conn = get_db()
        cursor = conn.cursor()
        row = None
        if product_id:
            cursor.execute('''
                SELECT r.*, p.name_tr, p.name_en, p.brand, p.image_url, p.slug
                FROM reviews r
                JOIN products p ON r.product_id = p.id
                WHERE p.id = ? OR p.slug = ?
                ORDER BY r.rating DESC LIMIT 1
            ''', (product_id, product_id))
            row = cursor.fetchone()
            if not row:
                cursor.execute("SELECT * FROM products WHERE id = ? OR slug = ?", (product_id, product_id))
                p_row = cursor.fetchone()
                if p_row:
                    p_dict = dict(p_row)
                    row = {
                        'user_name': 'Doğrulanmış FPV Pilotu',
                        'comment': f"{p_dict.get('name_tr') or p_dict.get('name_en')} donanımını titizlikle test ettim. Pozitron Market kalitesi ve malzeme sağlamlığı harika!",
                        'rating': 5,
                        'name_tr': p_dict.get('name_tr'),
                        'name_en': p_dict.get('name_en'),
                        'brand': p_dict.get('brand'),
                        'slug': p_dict.get('slug'),
                        'product_id': p_dict.get('id'),
                        'image_url': p_dict.get('image_url')
                    }
        if not row:
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
        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('review_highlight', {
                'product': product_name, 'user_name': user_name, 'comment': comment
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']

        if r.get('product_id') and 'id' not in r:
            r['id'] = r.get('product_id')

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

    def _generate_hardware_battle(self, product_id: str = None) -> dict:
        recent_titles = set(get_recent_posted_titles(40))
        eligible = [b for b in HARDWARE_BATTLES if b['title'] not in recent_titles]
        if not eligible:
            eligible = HARDWARE_BATTLES
        battle = random.choice(eligible)
        title = battle['title']
        caption = f"""{battle['title']}

{battle['summary']}

[KIYASLAMA]
• {battle['points'][0]}
• {battle['points'][1]}
• {battle['points'][2]}

Sen hangi taraftasın? Tercihini ve tecrübeni yorumlarda FPV topluluğuyla paylaş!

> FPV donanım ve uyumluluk sihirbazı: pozitronmarket.com"""
        hashtags = f"{battle['tags']} #fpvturkey #dronetopla #pozitronmarket #teknofest"
        visual_summary = {
            'badge': 'DONANIM DUELLOSU',
            'headline': battle['headline'],
            'subhead': battle['subhead'],
            'key_points': battle['points'],
            'cta': '> SEN HANGİSİNİ TERCİH EDİYORSUN? YORUMA YAZ'
        }
        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('hardware_battle', {
                'title': title, 'summary': battle['summary']
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']
        prod = self._get_candidate_product(product_id) if product_id else None
        return {
            'content_type': 'hardware_battle',
            'product_id': prod.get('id') if prod else None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': prod if prod else None,
            'tool_info': None
        }

    def _generate_mistake_breakdown(self, product_id: str = None) -> dict:
        recent_titles = set(get_recent_posted_titles(40))
        eligible = [m for m in MISTAKE_BREAKDOWNS if m['title'] not in recent_titles]
        if not eligible:
            eligible = MISTAKE_BREAKDOWNS
        mistake = random.choice(eligible)
        title = mistake['title']
        caption = f"""{mistake['title']}

{mistake['summary']}

[KIRIM ONLEME REHBERI]
• {mistake['points'][0]}
• {mistake['points'][1]}
• {mistake['points'][2]}

Daha önce bu hatayı yaşadın mı? Deneyimini yorumlarda paylaş, yeni pilotlara rehber olalım!

> Kırılmaz FPV parçaları ve korumalar: pozitronmarket.com"""
        hashtags = f"{mistake['tags']} #fpvkaza #dronebakim #dronetamir #pozitronmarket"
        visual_summary = {
            'badge': 'KIRIM VE HATA ONLEME',
            'headline': mistake['headline'],
            'subhead': mistake['subhead'],
            'key_points': mistake['points'],
            'cta': '> SEN DE DENEYİMİNİ YORUMDA PAYLAŞ'
        }
        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('mistake_breakdown', {
                'title': title, 'summary': mistake['summary']
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']
        prod = self._get_candidate_product(product_id) if product_id else None
        return {
            'content_type': 'mistake_breakdown',
            'product_id': prod.get('id') if prod else None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': prod if prod else None,
            'tool_info': None
        }

    def _generate_community_quiz(self) -> dict:
        recent_titles = set(get_recent_posted_titles(40))
        eligible = [q for q in COMMUNITY_QUIZZES if q['title'] not in recent_titles]
        if not eligible:
            eligible = COMMUNITY_QUIZZES
        quiz = random.choice(eligible)
        title = quiz['title']
        caption = f"""{quiz['title']}

{quiz['summary']}

[SECENEKLER]
{quiz['points'][0]}
{quiz['points'][1]}
{quiz['points'][2]}
{quiz['points'][3]}

Doğru cevabını yorumlara yaz! Doğru yanıt günün sonunda hikayemizde ve yorumlarda sabitlenecektir.

> FPV Akademi ve Donanım: pozitronmarket.com"""
        hashtags = f"{quiz['tags']} #fpvsoru #dronebilgi #fpvpilot #pozitronmarket"
        visual_summary = {
            'badge': 'PILOT TOPLULUK ANKETI',
            'headline': quiz['headline'],
            'subhead': quiz['subhead'],
            'key_points': quiz['points'],
            'cta': '> CEVABINI YORUMA BIRAK!'
        }
        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('community_quiz', {
                'title': title, 'summary': quiz['summary'], 'options': quiz['points']
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']
        return {
            'content_type': 'community_quiz',
            'product_id': None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': None,
            'tool_info': None
        }

    def _generate_myth_buster(self) -> dict:
        recent_titles = set(get_recent_posted_titles(40))
        eligible = [m for m in MYTH_BUSTERS if m['title'] not in recent_titles]
        if not eligible:
            eligible = MYTH_BUSTERS
        myth = random.choice(eligible)
        title = myth['title']
        caption = f"""{myth['title']}

[YAYGIN INANIS]
{myth['myth']}

[GERCEK DURUM]
{myth['reality']}

[OZET]
• {myth['points'][0]}
• {myth['points'][1]}
• {myth['points'][2]}

Sen bu efsaneye inanıyor muydun? Yoruma yaz, doğruyu birlikte yayalım!

> Doğru donanım ve rehber: pozitronmarket.com"""
        hashtags = f"{myth['tags']} #fpvefsane #dogrubilgi #pozitronmarket"
        visual_summary = {
            'badge': 'FPV EFSANE AVCISI',
            'headline': 'EFSANE vs GERCEK',
            'subhead': myth['myth'][:70],
            'key_points': myth['points'],
            'cta': '> SEN DE GORUSUNU YORUMA YAZ'
        }
        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('myth_buster', {
                'title': title, 'myth': myth['myth'], 'reality': myth['reality']
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']
        return {
            'content_type': 'myth_buster',
            'product_id': None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': None,
            'tool_info': None
        }

    def _generate_maintenance_checklist(self, product_id: str = None) -> dict:
        recent_titles = set(get_recent_posted_titles(40))
        eligible = [m for m in MAINTENANCE_CHECKS if m['title'] not in recent_titles]
        if not eligible:
            eligible = MAINTENANCE_CHECKS
        chk = random.choice(eligible)
        title = chk['title']
        points_block = "\n".join(f"{i+1}. {p}" for i, p in enumerate(chk['points']))
        caption = f"""{chk['title']}

{chk['intro']}

{points_block}

Bu listeyi kaydet, sonraki bakımda tekrar kullan! Sorularını yoruma bırakabilirsin.

> Yedek parça ve koruma ürünleri: pozitronmarket.com"""
        hashtags = f"{chk['tags']} #fpvbakimlistesi #dronbakimi #pozitronmarket"
        visual_summary = {
            'badge': 'FPV BAKIM KONTROL LISTESI',
            'headline': 'BAKIM ADIMLARI',
            'subhead': chk['intro'][:70],
            'key_points': chk['points'][:4],
            'cta': '> LISTEYI KAYDET VE PAYLAS'
        }
        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('maintenance_checklist', {
                'title': title, 'intro': chk['intro'], 'steps': chk['points']
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']
        prod = self._get_candidate_product(product_id) if product_id else None
        return {
            'content_type': 'maintenance_checklist',
            'product_id': prod.get('id') if prod else None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': prod if prod else None,
            'tool_info': None
        }

    def _generate_beginner_roadmap(self) -> dict:
        recent_titles = set(get_recent_posted_titles(40))
        eligible = [r for r in BEGINNER_ROADMAP if r['title'] not in recent_titles]
        if not eligible:
            eligible = BEGINNER_ROADMAP
        road = random.choice(eligible)
        title = road['title']
        steps_block = "\n".join(road['steps'])
        caption = f"""{road['title']}

{road['intro']}

{steps_block}

Bu rehberi yeni başlayan bir arkadaşına gönder, ona zaman kazandır!

> Başlangıç için uygun donanımlar: pozitronmarket.com"""
        hashtags = f"{road['tags']} #fpvyenibaslayan #fpvrehberi #pozitronmarket"
        visual_summary = {
            'badge': 'YENI BASLAYAN YOL HARITASI',
            'headline': 'FPV BASLANGIC REHBERI',
            'subhead': road['intro'][:70],
            'key_points': road['steps'][:4],
            'cta': '> REHBERI ARKADASINA GONDER'
        }
        if self._llm_available():
            ai_data = self._call_gemini_post_and_summary('beginner_roadmap', {
                'title': title, 'intro': road['intro'], 'steps': road['steps']
            })
            if ai_data:
                caption = ai_data.get('caption', caption)
                hashtags = ai_data.get('hashtags', hashtags)
                title = ai_data.get('title', title)
                if ai_data.get('visual_summary'):
                    visual_summary = ai_data['visual_summary']
        return {
            'content_type': 'beginner_roadmap',
            'product_id': None,
            'title': title,
            'caption': caption.strip(),
            'hashtags': hashtags,
            'visual_summary': visual_summary,
            'product_data': None,
            'tool_info': None
        }

    def _call_gemini_post_and_summary(self, content_type: str, context: dict) -> dict:
        """
        Generates the Turkish Instagram caption + visual summary card.

        Primary: Flash 3.8 (Qwen 3.8 Flash Next / Gemini 3.8 Flash) via the unified OpenCode/Evren gateway.
        Fallback: legacy Gemini endpoint.
        """
        prompt = f"""Sen Pozitron Market (pozitronmarket.com) icin yazan, deneyimli bir Turk FPV pilotu ve icerik yazarisin.
Icerik Turu: {content_type}
Icerik Bilgileri:
{json.dumps(context, ensure_ascii=False, indent=2)}

En onemli kural: METIN INSAN YAZMIS GIBI OLMALI. Bir makine, bot veya reklam ajansi gibi DEGIL.
- Dogal, samimi, akici Turkce yaz. Konusuyormus gibi.
- KESINLIKLE: koseli parantezli etiket YOK ([FREKANS], [ONLINE ARAC], [GUC] gibi), EMOJI YOK, TAMAMI BUYUK HARF YOK, "->", ">>", "KAYDET", "HIZLI OKU", "PILOT NOTU" gibi kalip ifadeler YOK, "gonderi", "icerik", "slayt", "reels" kelimeleri YOK.
- Basliklar ve gorsel metinleri normal cumle duzeninde olsun; sadece ilk harf buyuk, gerisi kucuk (FPV, VTX, LiPo, GPS gibi kisaltmalar buyuk kalabilir).
- Abartili satis dili kullanma; gercek bir pilotun paylasacagi gibi sade ve guvenilir ol.
- Gereksiz uzatma; 2-4 kisa cumle yeterli.

Ayrica gorsele basilacak kisa bir ozet ("visual_summary") uret: rozet (kisa etiket), ana baslik, kisa alt aciklama, en fazla 3 madde ve tek satirlik davet.

SADECE gecerli bir JSON objesi dondur:
{{
  "title": "Kisa, dogal baslik (maks 60 karakter)",
  "caption": "Instagram icin insan gibi yazilmis Turkce metin",
  "hashtags": "#fpvturkey #pozitronmarket #dronetopla #fpvdrone #betaflight",
  "visual_summary": {{
    "badge": "Kisa etiket, normal cumle duzeni (maks 28 karakter)",
    "headline": "Gorselin ana basligi, normal cumle duzeni (maks 40 karakter)",
    "subhead": "Tek satir kisa aciklama (maks 55 karakter)",
    "key_points": [
      "1. kisa madde (maks 50 karakter)",
      "2. kisa madde (maks 50 karakter)",
      "3. kisa madde (maks 50 karakter)"
    ],
    "cta": "Tek satir davet, ornegin: Detaylar profildeki linkte"
  }}
}}"""

        # 1. Unified LLM (DeepSeek V4.1 Flash High via OpenCode/Evren)
        try:
            from llm_client import get_llm
            llm = get_llm()
            if llm.is_configured():
                data = llm.generate_json(prompt, max_tokens=8192, temperature=0.5)
                if isinstance(data, dict) and data.get('caption') and data.get('visual_summary'):
                    return data
        except Exception:
            pass

        # 2. Legacy Gemini fallback
        if not self.gemini_api_key:
            return None

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

    def _generate_drone_build_showcase(self, product_id: str = None) -> dict:
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

        prod = self._get_candidate_product(product_id) if product_id else None
        return {
            'content_type': 'drone_build_showcase',
            'media_type': 'IMAGE',
            'product_id': prod.get('id') if prod else None,
            'title': b['title'],
            'caption': caption.strip(),
            'hashtags': b['tags'],
            'visual_summary': visual_summary,
            'product_data': prod if prod else None,
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

    def generate_reels_content(self, content_type: str = None, product_id: str = None, allowed_reels_types: list = None, reels_type: str = None) -> dict:
        """
        Builds Reels-native content for one of the 8 distinct Reels formats:
        - real_fpv_broll (toggleable authentic FPV flight clip + brand overlay)
        - freestyle_acro (gap-dive, power loop, high speed acrobatics)
        - hardware_vs (component vs component comparison)
        - quick_tip_fix (15s quick pilot tip, soldering, Betaflight)
        - mistake_warning (preventing crashes, smoke stopper, failsafe)
        - secret_spot (Turkey's canyon/abandoned factory FPV spots)
        - product_cinematic (macro hardware, live price pill, stock)
        - flash_deal (limited coupon, urgency e-commerce vitrine)

        Strictly limits selection to allowed_reels_types if provided.
        """
        allowed = [t for t in (allowed_reels_types or ALL_REELS_TYPES) if t in ALL_REELS_TYPES]
        if not allowed:
            allowed = list(ALL_REELS_TYPES)

        # If user explicitly requested a reels_type, check if it's allowed or fallback to allowed
        if reels_type and reels_type in allowed:
            chosen_reels_type = reels_type
        elif reels_type and reels_type not in allowed:
            chosen_reels_type = random.choice(allowed)
        else:
            chosen_reels_type = None

        recent_reel_types = get_recent_posted_content_types_by_media('REEL', limit=6)
        recent_combos = set(get_recent_reel_combo_ids(limit=8))
        recent_combos.update(self._session_recent_combo_ids[-10:])

        # Filter combos: strictly match allowed reels types
        combos = [c for c in REEL_COMBINATIONS if c.get('reels_type') in allowed]
        if not combos:
            combos = list(REEL_COMBINATIONS)

        if chosen_reels_type:
            type_combos = [c for c in combos if c.get('reels_type') == chosen_reels_type]
            if type_combos:
                combos = type_combos

        if content_type:
            theme_combos = [c for c in combos if content_type in c['themes']]
            if theme_combos:
                combos = theme_combos
        else:
            preferred = [c for c in combos if all(t not in recent_reel_types[:2] for t in c['themes'])]
            if preferred:
                combos = preferred

        fresh = [c for c in combos if c['id'] not in recent_combos]
        pool = fresh if fresh else combos

        # Down-weight combos whose themes were used very recently
        weights = []
        for c in pool:
            w = 1.0
            if any(t in recent_reel_types[:3] for t in c['themes']):
                w *= 0.3
            weights.append(w)
        combo = random.choices(pool, weights=weights, k=1)[0]
        chosen_reels_type = combo.get('reels_type') or chosen_reels_type or 'product_cinematic'
        chosen = None

        content = None
        # Try themes corresponding to chosen_reels_type or combo themes
        target_themes = REELS_TYPE_THEME_MAP.get(chosen_reels_type, combo['themes'])
        theme_order = list(dict.fromkeys(target_themes + combo['themes'] + [t for c in REEL_COMBINATIONS for t in c['themes']]))
        for theme in theme_order:
            try:
                content = self.generate_content(content_type=theme, product_id=product_id)
            except Exception:
                content = None
            if content and content.get('title'):
                chosen = theme
                break
        if not content:
            content = self.generate_content(content_type='product_spotlight', product_id=product_id)
        if not content:
            return {}

        content['content_type'] = chosen
        content['media_type'] = 'REEL'
        content['reels_type'] = chosen_reels_type
        content['allowed_reels_types'] = allowed
        content['reel_combo'] = combo['id']
        content['visual_style_key'] = combo['style']
        content['visual_style'] = REEL_STYLE_PRESETS.get(combo['style'], random.choice(REEL_VISUAL_STYLES))
        content['video_mode'] = 'mode2' if chosen_reels_type == 'real_fpv_broll' else combo.get('video_mode', 'mode1')
        content['hook_tone'] = combo['tone']
        hooks = REELS_HOOKS.get(chosen_reels_type) or REELS_HOOKS.get(chosen) or REELS_HOOKS['product_spotlight']
        idx = REEL_HOOK_TONES.get(combo['tone'], random.randrange(len(hooks)))
        hook = hooks[idx % len(hooks)]
        cta = REELS_CTA.get(chosen_reels_type) or REELS_CTA.get(chosen) or REELS_CTA['product_spotlight']
        content['hook'] = hook
        content['cta'] = cta
        content['caption'] = self._build_reels_caption(chosen_reels_type, content.get('caption', ''), tone=combo['tone'], fallback_type=chosen, hook=hook, cta=cta)
        base_tags = content.get('hashtags', '') or ''
        content['hashtags'] = f"{base_tags} {REELS_EXTRA_TAGS}".strip()
        content = humanize_content(content)

        self._session_recent_combo_ids.append(combo['id'])
        if len(self._session_recent_combo_ids) > 20:
            self._session_recent_combo_ids = self._session_recent_combo_ids[-20:]
        return content

    def _build_reels_caption(self, content_type: str, base_caption: str, tone: str = None, fallback_type: str = None, hook: str = None, cta: str = None) -> str:
        """Wraps the informative body with a reels-native hook and theme-specific CTA."""
        if not hook:
            hooks = REELS_HOOKS.get(content_type) or REELS_HOOKS.get(fallback_type) or REELS_HOOKS['product_spotlight']
            idx = REEL_HOOK_TONES.get(tone, random.randrange(len(hooks)))
            hook = hooks[idx % len(hooks)]
        if not cta:
            cta = REELS_CTA.get(content_type) or REELS_CTA.get(fallback_type) or REELS_CTA['product_spotlight']

        body = (base_caption or '').strip()
        # Drop the generic feed DM CTA if present; Reels use their own CTA.
        for marker in ('[OTOMATIK DM ALARMI]', '[OTOMATIK DM ALARM]'):
            if marker in body:
                body = body.split(marker)[0].strip()
        # Trim overly long feed captions for Reels best practice (< ~1200 chars total).
        if len(body) > 900:
            body = body[:900].rstrip() + '...'

        parts = [hook]
        if body:
            parts.append(body)
        parts.append(cta)
        parts.append(f"Takip et: @pozitronmarket | Alışveriş: pozitronmarket.com")
        return "\n\n".join(parts)

    def generate_reels_video_prompt(self, post_data: dict) -> str:
        """
        Generates an optimized, cinematic video generation prompt for LTX-Video / Gemini Omni Flash.
        Theme-aware and style-rotating across all 8 distinct Reels formats.
        """
        title = post_data.get('title', 'FPV Drone & Maker Technology')
        content_type = post_data.get('content_type', 'product_spotlight')
        reels_type = post_data.get('reels_type') or content_type
        prod = post_data.get('product_data') or {}
        prod_name = prod.get('name_tr') or prod.get('name') or title
        category = prod.get('category', 'FPV Drone Components')
        description = prod.get('description_tr') or prod.get('description') or ''
        style = post_data.get('visual_style') or random.choice(REEL_VISUAL_STYLES)

        reels_type_prompts = {
            'freestyle_acro': f"High-speed acrobatic FPV drone performing an aggressive gap-dive and snappy power-loop, low ground skimming, motion blur, {style}",
            'hardware_vs': f"Side-by-side comparison of two high-performance FPV drone components on illuminated pedestals, macro rotating camera, brushed carbon and titanium, {style}",
            'quick_tip_fix': f"Extreme macro workshop shot of precision soldering tip touching gold ESC pad with light rosin flux smoke rising, professional clean tools, {style}",
            'mistake_warning': f"Dramatic slow-motion of drone electronics on bench, warning LED flashing red, smoke stopper safety test, intense cinematic lighting, {style}",
            'secret_spot': f"Sweeping cinematic aerial reveal flying low over a rugged hidden canyon and abandoned industrial structure, golden-hour volumetric mist, {style}",
            'product_cinematic': f"Ultra-detailed 360-degree turntable shot of {prod_name}, macro view of brushless copper stator windings and carbon fiber frame, {style}",
            'flash_deal': f"Futuristic neon-lit retail vitrine, glowing digital price tag and hologram discount aura around {prod_name}, cyber aesthetic, {style}",
            'real_fpv_broll': f"Authentic first-person-view drone camera flight racing fast across scenic terrain, smooth brushless stabilization, {style}"
        }
        reels_prompt_direction = reels_type_prompts.get(reels_type, f"Cinematic vertical 9:16 FPV video about {prod_name}, {style}")

        system_instruction = (
            "You are an award-winning cinematic director and prompt engineer for AI video generation (LTX-Video / Gemini Omni). "
            "Write a single concise video generation prompt (40-60 words) for a 9:16 vertical commercial video. "
            "Specify: subject, camera movement (slow orbit, macro pan, or aerial reveal), the given visual style/lighting, "
            "material textures (carbon fiber, copper windings, PCB traces, titanium hardware, or outdoor terrain), "
            "and a continuous unbroken shot. "
            "NO text, NO logo overlays, NO scene cuts, NO speech, photorealistic 8K."
        )
        user_msg = (
            f"Reels format: {reels_type}\nContent theme: {content_type}\nSubject: {prod_name}\nCategory: {category}\n"
            f"Details: {description[:200]}\nVisual style to follow: {style}\nFormat direction: {reels_prompt_direction}"
        )

        # 1. Unified LLM (DeepSeek V4.1 Flash High via OpenCode/Evren)
        try:
            from llm_client import get_llm
            llm = get_llm()
            if llm.is_configured():
                text = llm.generate_text(f"{system_instruction}\n\n{user_msg}", max_tokens=400, temperature=0.9)
                text = (text or "").strip().strip('"\'`')
                if len(text) > 20:
                    return text
        except Exception:
            pass

        # 2. Legacy Gemini fallback
        if self.gemini_api_key:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={self.gemini_api_key}"
            payload = {
                "contents": [
                    {"role": "user", "parts": [{"text": f"{system_instruction}\n\n{user_msg}"}]}
                ],
                "generationConfig": {
                    "temperature": 0.9,
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

        # High-quality rule-based fallback prompt (format-aware)
        return (
            f"Cinematic vertical 9:16 FPV video. {reels_prompt_direction}. "
            "Continuous unbroken single shot, photorealistic 8K, cinematic volumetric lighting, "
            "no text, no watermark, no overlays."
        )



