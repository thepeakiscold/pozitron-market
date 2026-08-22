import sqlite3
import json
import random
import uuid
from datetime import datetime, timedelta
from database import get_db, init_db, hash_password

CATEGORIES = [
    {
        "id": "motors",
        "slug": "brushless-motors",
        "name_en": "Brushless Motors",
        "name_tr": "Fırçasız Motorlar",
        "icon": "⚡",
        "description_en": "High-efficiency brushless motors for freestyle, racing, cinewhoop, and long-range drones.",
        "description_tr": "Freestyle, yarış, cinewhoop ve uzun menzil dronlar için yüksek verimli fırçasız motorlar."
    },
    {
        "id": "esc",
        "slug": "electronic-speed-controllers",
        "name_en": "Electronic Speed Controllers (ESC)",
        "name_tr": "Elektronik Hız Kontrolcüleri (ESC)",
        "icon": "🚀",
        "description_en": "High-current 4-in-1 and single ESCs with BLHeli_32, BLHeli_S, and AM32 firmware.",
        "description_tr": "BLHeli_32, BLHeli_S ve AM32 yazılımlı yüksek akım 4'ü 1 arada ve tekli ESC'ler."
    },
    {
        "id": "propellers",
        "slug": "propellers",
        "name_en": "Propellers",
        "name_tr": "Pervaneler & Bıçaklar",
        "icon": "🌀",
        "description_en": "Durable polycarbonate tri-blade, bi-blade, and cinewhoop ducted propellers.",
        "description_tr": "Dayanıklı polikarbonat 3 palli, 2 palli ve kanallı cinewhoop pervaneleri."
    },
    {
        "id": "converters",
        "slug": "power-converters-bec",
        "name_en": "Power & Voltage Converters (BEC/PDB)",
        "name_tr": "Güç ve Voltaj Dönüştürücüler (BEC/PDB)",
        "icon": "🔋",
        "description_en": "Step-down/step-up BEC voltage regulators, power distribution boards, and LC filters.",
        "description_tr": "Voltaj düşürücü/yükseltici BEC regülatörleri, güç dağıtım kartları ve LC filtreleri."
    },
    {
        "id": "flight_controllers",
        "slug": "flight-controllers",
        "name_en": "Flight Controllers (FC)",
        "name_tr": "Uçuş Kontrol Kartları (FC)",
        "icon": "🧠",
        "description_en": "F405, F722, and H743 flight controllers supporting Betaflight, INAV, and ArduPilot.",
        "description_tr": "Betaflight, INAV ve ArduPilot destekli F405, F722 ve H743 uçuş kontrol kartları."
    },
    {
        "id": "cameras",
        "slug": "fpv-cameras-digital-units",
        "name_en": "FPV Cameras & Digital Systems",
        "name_tr": "FPV Kameralar ve Dijital Sistemler",
        "icon": "📷",
        "description_en": "Analog FPV cameras, DJI O3/O4 Air Units, Walksnail Avatar HD, and HDZero systems.",
        "description_tr": "Analog FPV kameralar, DJI O3/O4 Air Unit, Walksnail Avatar HD ve HDZero dijital sistemler."
    },
    {
        "id": "vtx",
        "slug": "video-transmitters",
        "name_en": "Video Transmitters (VTX)",
        "name_tr": "Video Vericiler (VTX)",
        "icon": "📡",
        "description_en": "High-power 5.8GHz and 1.2GHz video transmitters up to 2500mW with smart audio.",
        "description_tr": "SmartAudio destekli 2500mW'a kadar yüksek güçlü 5.8GHz ve 1.2GHz video vericileri."
    },
    {
        "id": "transmitters_receivers",
        "slug": "transmitters-receivers",
        "name_en": "Radio Transmitters & Receivers",
        "name_tr": "Kumanda ve Alıcı Sistemleri",
        "icon": "🎮",
        "description_en": "ExpressLRS 2.4GHz/915MHz and TBS Crossfire radios, micro receivers, and modules.",
        "description_tr": "ExpressLRS 2.4GHz/915MHz ve TBS Crossfire kumandalar, mikro alıcılar ve modüller."
    },
    {
        "id": "batteries_chargers",
        "slug": "lipo-batteries-chargers",
        "name_en": "LiPo Batteries & Smart Chargers",
        "name_tr": "LiPo Bataryalar ve Akıllı Şarj Cihazları",
        "icon": "⚡",
        "description_en": "High-discharge 4S/6S LiPo & Li-ion battery packs and multi-channel smart chargers.",
        "description_tr": "Yüksek deşarjlı 4S/6S LiPo & Li-ion bataryalar ve çok kanallı akıllı şarj cihazları."
    },
    {
        "id": "frames",
        "slug": "drone-frames-carbon-fiber",
        "name_en": "Drone Frames & Carbon Fiber",
        "name_tr": "Drone Gövdeleri ve Karbon Fiber",
        "icon": "🛸",
        "description_en": "Premium 3K carbon fiber freestyle, racing, cinewhoop, and long-range drone frames.",
        "description_tr": "Birinci sınıf 3K karbon fiber freestyle, yarış, cinewhoop ve uzun menzil drone gövdeleri."
    },
    {
        "id": "antennas",
        "slug": "fpv-antennas",
        "name_en": "FPV Antennas & RF Modules",
        "name_tr": "FPV Antenleri ve RF Modülleri",
        "icon": "📶",
        "description_en": "RHCP/LHCP omnidirectional antennas, directional patch antennas, and dual-band arrays.",
        "description_tr": "RHCP/LHCP çok yönlü antenler, yönlü yama antenleri ve çift bantlı dizi antenler."
    },
    {
        "id": "gps_telemetry",
        "slug": "gps-telemetry-sensors",
        "name_en": "GPS, Compass & Telemetry",
        "name_tr": "GPS, Pusula ve Telemetri",
        "icon": "📍",
        "description_en": "High-precision u-blox M10/M8 GPS modules with integrated compass and optical flow.",
        "description_tr": "Entegre pusulalı ve optik akışlı yüksek hassasiyetli u-blox M10/M8 GPS modülleri."
    },
    {
        "id": "tools_accessories",
        "slug": "tools-hardware-accessories",
        "name_en": "Tools, Hardware & Accessories",
        "name_tr": "Montaj Aletleri, Hırdavat ve Aksesuar",
        "icon": "🛠️",
        "description_en": "Portable soldering irons, titanium hex tools, smoke stoppers, silicone wire, and TPU parts.",
        "description_tr": "Taşınabilir havya istasyonları, titanyum alyan takımları, smoke stopper ve TPU parçalar."
    }
]

# Generator templates for realistic 500 items
BRANDS = {
    "motors": ["T-Motor", "EMAX", "BrotherHobby", "BetaFPV", "Flywoo", "iFlight", "GEPRC", "Sunnysky", "AxisFlyer", "FlashHobby", "MEPSKing", "Racerstar"],
    "esc": ["SpeedyBee", "Holybro", "T-Motor", "Foxeer", "Skystars", "FETtec", "Spedix", "Hobbywing", "BetaFPV", "Flywoo", "iFlight", "MAMBA"],
    "propellers": ["Gemfan", "HQProp", "Dalprop", "Azure Power", "EMAX Avan", "Ethix", "Master Airscrew", "T-Motor", "Lumenier"],
    "converters": ["Matek Systems", "Holybro", "Caddx", "Pololu", "iFlight", "GEPRC", "BetaFPV", "Flywoo", "Diatone"],
    "flight_controllers": ["SpeedyBee", "Holybro", "Matek Systems", "Foxeer", "BetaFPV", "iFlight", "GEPRC", "Flywoo", "Kakute", "Skystars", "Diatone"],
    "cameras": ["DJI", "Walksnail", "Caddx", "Foxeer", "RunCam", "HDZero", "BetaFPV", "Flywoo"],
    "vtx": ["TBS (Team BlackSheep)", "RushFPV", "Foxeer", "SpeedyBee", "Walksnail", "DJI", "AKK", "PandaRC", "Flywoo", "iFlight"],
    "transmitters_receivers": ["Radiomaster", "TBS (Team BlackSheep)", "Happymodel", "BetaFPV", "Jumper", "FrSky", "Flysky", "Foxeer"],
    "batteries_chargers": ["Tattu", "GNB (Gaoneng)", "CNHL", "ISDT", "ToolkitRC", "HOTA", "SkyRC", "BetaFPV", "Auline", "Ovonic"],
    "frames": ["iFlight", "GEPRC", "TBS (Team BlackSheep)", "ImpulseRC", "BetaFPV", "Flywoo", "Lumenier", "SpeedyBee", "Diatone", "Sub250"],
    "antennas": ["Foxeer", "TBS (Team BlackSheep)", "TrueRC", "VAS (Video Aerial Systems)", "MenaceRC", "RushFPV", "Flywoo", "Lumenier"],
    "gps_telemetry": ["Matek Systems", "Holybro", "Beitian", "CUAV", "Radiolink", "Flywoo", "iFlight", "GEPRC"],
    "tools_accessories": ["Miniware", "Pine64", "TBS", "Sequre", "Ethix", "Vifly", "RDQ", "ToolkitRC", "ISDT", "Flywoo"]
}

ITEM_CONFIGS = [
    # Motors (55 items)
    {
        "cat": "motors",
        "count": 55,
        "types": [
            ("F60 PRO V", "2207.5", ["1750KV", "1950KV", "2020KV", "2550KV"], "6S / 4S Freestyle & Racing Motor", "6S / 4S Freestyle & Yarış Motoru", 26.90, 940, "6S/4S", "16x16mm M3"),
            ("ECO II", "2207", ["1700KV", "1900KV", "2400KV"], "Durable High Value Brushless Motor", "Yüksek Fiyat/Performans Fırçasız Motor", 15.99, 560, "6S/4S", "16x16mm M3"),
            ("XING2", "2207", ["1855KV", "2755KV"], "Unibell Smooth Freestyle Motor with N52H Curved Magnets", "N52H Kavisli Mıknatıslı Unibell Freestyle Motor", 24.50, 855, "6S/4S", "16x16mm M3"),
            ("SPEEDX2", "2105.5", ["2650KV", "3450KV"], "Ultralight Cinewhoop & 3.5-inch Quad Motor", "Ultra Hafif Cinewhoop ve 3.5 inç Motoru", 18.90, 660, "4S/6S", "12x12mm M2"),
            ("Avenger V3", "2306.5", ["1750KV", "1950KV", "2450KV"], "Titanium Shaft High Power FPV Motor", "Titanyum Şaftlı Yüksek Güçlü FPV Motoru", 27.99, 980, "6S/4S", "16x16mm M3"),
            ("Velox V3", "2207", ["1750KV", "1950KV", "2450KV"], "Precision Aerodynamic Cooling Motor", "Hassas Aerodinamik Soğutmalı Motor", 17.50, 610, "6S/4S", "16x16mm M3"),
            ("NINJA", "1404", ["2750KV", "3800KV", "4600KV"], "Micro Long Range & Toothpick Motor", "Mikro Uzun Menzil ve Toothpick Motoru", 14.50, 505, "3S/4S", "9x9mm M2"),
            ("ROBO RB", "1202.5", ["6000KV", "11500KV"], "Ultralight Tiny Whoop Brushless Motor", "Ultra Hafif Tiny Whoop Fırçasız Motor", 12.90, 450, "1S/2S", "9x9mm M2"),
            ("C2807", "2807", ["1300KV", "1500KV", "1700KV"], "7-inch Long Range Mountain Cruiser Motor", "7 inç Uzun Menzil Dağ Uçuşu Motoru", 29.90, 1045, "6S", "19x19mm M3"),
            ("U8 II Heavy Lift", "8515", ["85KV", "100KV"], "Industrial Drone Heavy Payload Brushless Motor", "Endüstriyel Yüksek Taşıma Kapasiteli Motor", 249.00, 8700, "12S", "30x30mm M4"),
            ("V2207.5", "2207.5", ["1960KV", "2550KV"], "Veloce Performance Pro Drone Motor", "Veloce Performans Pro Drone Motoru", 21.00, 735, "6S/4S", "16x16mm M3")
        ]
    },
    # ESCs (45 items)
    {
        "cat": "esc",
        "count": 45,
        "types": [
            ("F405 V4 55A", "55A BLHeli_S", ["30.5x30.5mm"], "4-in-1 DShot600 ESC with Heatsink", "Soğutucu Bloklu 4'ü 1 Arada DShot600 ESC", 52.00, 1820, "3-6S LiPo", "55A Cont / 70A Burst"),
            ("Reaper 65A", "65A BLHeli_32", ["30.5x30.5mm"], "High Current 128K PWM 8-Layer PCB ESC", "Yüksek Akımlı 128K PWM 8 Katmanlı PCB ESC", 79.99, 2795, "3-8S LiPo", "65A Cont / 85A Burst"),
            ("Tekko32 F4 4in1 50A", "50A BLHeli_32", ["20x20mm"], "Compact High-End Racing ESC", "Kompakt Üst Seviye Yarış ESC'si", 68.50, 2395, "3-6S LiPo", "50A Cont / 60A Burst"),
            ("F55A PRO II", "55A BLHeli_32", ["30.5x30.5mm"], "Ultra Stable Telemetry Output ESC", "Ultra Kararlı Telemetri Çıkışlı ESC", 84.00, 2940, "3-6S LiPo", "55A Cont / 75A Burst"),
            ("AM32 45A Mini", "45A AM32", ["20x20mm"], "Open Source AM32 Sine Wave Drive ESC", "Açık Kaynak AM32 Sinüs Sürücülü ESC", 46.00, 1610, "2-6S LiPo", "45A Cont / 55A Burst"),
            ("Crossfire 4in1 60A", "60A BLHeli_32", ["30.5x30.5mm"], "Industrial Grade High Amp ESC", "Endüstriyel Sınıf Yüksek Amper ESC", 89.00, 3115, "3-6S LiPo", "60A Cont / 80A Burst"),
            ("GOKU Versatile 40A", "40A BLHeli_S", ["25.5x25.5mm"], "AIO Toothpick & Cinewhoop ESC", "AIO Toothpick ve Cinewhoop ESC", 42.00, 1470, "2-6S LiPo", "40A Cont / 45A Burst"),
            ("Single 32Bit 45A ESC", "45A Single", ["Single Arm"], "Individual Arm Mount Racing ESC", "Kollara Monte Edilebilir Tekli Yarış ESC'si", 16.50, 575, "3-6S LiPo", "45A Cont / 55A Burst")
        ]
    },
    # Propellers (50 items)
    {
        "cat": "propellers",
        "count": 50,
        "types": [
            ("Hurricane 51466 V2", "5.1x4.66x3", ["Clear Grey", "Neon Yellow", "Cyan Blue", "Midnight Black"], "Durable Tri-Blade Freestyle Propeller (Set of 4)", "Dayanıklı 3 Palli Freestyle Pervane (4'lü Set)", 3.99, 140, "5mm Shaft", "Polycarbonate"),
            ("Ethix S3 Watermelon", "5x3.1x3", ["Watermelon Pink/Green"], "Ultra Smooth Responsive Propeller Set", "Ultra Pürüzsüz Tepkili Pervane Seti", 4.20, 147, "5mm Shaft", "Polycarbonate"),
            ("Cinewhoop D90S Ducted", "3.5x3x3", ["Clear Black", "Transparent Blue"], "3-Blade Low Noise Ducted Props", "3 Palli Düşük Gürültülü Kanallı Pervane", 3.80, 133, "5mm / T-Mount", "High Impact PC"),
            ("7040 7-Inch Tri-Blade", "7x4x3", ["Black", "Clear", "Neon Green"], "Long Range High Efficiency Propellers", "Uzun Menzil Yüksek Verimli Pervaneler", 5.50, 192, "5mm Shaft", "Reinforced PC"),
            ("Ethix P3 Peanut Butter", "5.1x3x3", ["Peanut Butter Brown"], "Crisp Cornering Cinematic Propeller", "Keskin Dönüşlü Sinematik Pervane", 4.30, 150, "5mm Shaft", "Polycarbonate"),
            ("Flash 5152", "5.1x5.2x3", ["Crystal Red", "Crystal Blue"], "High Pitch High Speed Racing Propellers", "Yüksek Hızlı Yarış Pervaneleri", 3.90, 136, "5mm Shaft", "Polycarbonate"),
            ("Foldable 1045", "10x4.5", ["Carbon Black"], "Folding Carbon-Reinforced Propeller Pair", "Katlanabilir Karbon Takviyeli Pervane Çifti", 14.50, 505, "Direct Mount", "Carbon Fiber Composite"),
            ("Micro 31mm 4-Blade", "31mm 4-Blade", ["Clear", "Purple", "Blue"], "Tiny Whoop Micro Props 0.8/1.0mm Shaft", "Tiny Whoop Mikro Pervaneler 0.8/1.0mm", 2.90, 100, "0.8mm/1.0mm", "Polycarbonate")
        ]
    },
    # Converters & Power (40 items)
    {
        "cat": "converters",
        "count": 40,
        "types": [
            ("Micro BEC Step-Down 5V/9V/12V", "1.5A - 3A", ["Adjustable Output"], "Synchronous Step-Down Voltage Converter", "Senkron Voltaj Düşürücü Regülatör Modülü", 8.90, 310, "6V - 36V In", "5V/9V/12V Out 3A"),
            ("PDB-XT60 Dual BEC", "Dual 5V & 12V", ["XT60 Direct Solder"], "Power Distribution Board with Dual BEC Regulators", "Çift BEC Çıkışlı Güç Dağıtım Kartı", 12.50, 435, "3-6S LiPo", "5V@2A & 12V@0.5A"),
            ("Low Noise LC Filter 3A", "3A Filter", ["High Frequency Choke"], "FPV Video Ripple & Noise Suppression Filter", "FPV Video Parazit ve Dalgalanma Önleyici Filtre", 6.50, 225, "2-6S LiPo", "3A Max Current"),
            ("Buck-Boost Converter 12V 2A", "12V 2A", ["Regulated Output"], "Constant 12V Output for VTX & Digital Systems", "VTX ve Dijital Sistemler İçin Sabit 12V Regülatör", 11.00, 385, "4V - 30V In", "12V @ 2A Constant"),
            ("Current Sensor Board 150A", "150A Hall Sensor", ["Analog/Digital Telemetry"], "High Precision Drone Current Sensing Module", "Yüksek Hassasiyetli Drone Akım Ölçüm Kartı", 14.90, 520, "2-12S LiPo", "150A Continuous"),
            ("Power Hub PDB with 5V/9V BEC", "180A PDB", ["Heavy Copper 4-Layer"], "Clean Power Hub with Integrated Filtering", "Entegre Filtreli Temiz Güç Dağıtım Kartı", 16.90, 590, "3-8S LiPo", "5V@3A / 9V@2A BEC")
        ]
    },
    # Flight Controllers (40 items)
    {
        "cat": "flight_controllers",
        "count": 40,
        "types": [
            ("F405 V4 Master FC", "STM32F405", ["30.5x30.5mm"], "Betaflight FC with Bluetooth & MicroSD Blackbox", "Bluetooth ve MicroSD Blackbox Destekli Betaflight FC", 42.00, 1470, "ICM42688P Gyro", "5x UARTs, Barometer"),
            ("F722 Dual Gyro Pro", "STM32F722", ["30.5x30.5mm"], "High-Speed Processor with Dual ICM Gyros", "Çift Gyro ve Yüksek Hızlı İşlemcili FC", 58.00, 2030, "Dual Gyro ICM42688", "6x UARTs, DPS310 Baro"),
            ("H743-WING V3", "STM32H743", ["Wing / Plane / Multi"], "ArduPilot & INAV Autonomous Navigation FC", "ArduPilot ve INAV Otonom Seyrüsefer FC", 98.00, 3430, "Dual Gyro + Dual Baro", "8x UARTs, CAN Bus, MicroSD"),
            ("Pixhawk 6C Autopilot Flight Controller", "STM32H753", ["Standard Carrier"], "Industrial PX4 / ArduPilot Autopilot System", "Endüstriyel PX4 / ArduPilot Otonom Uçuş Kartı", 189.00, 6615, "Triple Redundant IMU", "Ethernet, CAN, RTK GPS"),
            ("F722 Mini AIO 40A", "STM32F722", ["20x20mm"], "All-In-One Compact FC with Integrated 40A ESC", "Entegre 40A ESC'li Kompakt FC Kartı", 82.00, 2870, "BMI270 Gyro", "5x UARTs, 40A ESC"),
            ("G473 High Performance FC", "STM32G473", ["20x20mm / 30.5x30.5mm"], "Math-Accelerator Flight Controller", "Matematik Hızlandırıcılı Yeni Nesil FC", 49.00, 1715, "ICM42688-P", "5x UARTs, 16MB Blackbox")
        ]
    },
    # FPV Cameras & Digital Systems (35 items)
    {
        "cat": "cameras",
        "count": 35,
        "types": [
            ("O3 Air Unit Camera & VTX Module", "4K 60FPS Digital", ["DJI Digital FPV"], "Ultra Low Latency 4K 60FPS Stabilized Transmission System", "Ultra Düşük Gecikmeli 4K 60FPS Dijital Video İletim Sistemi", 229.00, 8015, "1/1.7-inch Sensor", "RockSteady EIS, 4K/60fps"),
            ("Avatar HD Pro Camera Kit", "1080P OLED Sony Starvis II", ["Walksnail Digital"], "Night Vision Low-Light FPV Digital Camera", "Gece Görüşlü Düşük Işık Sony Starvis II FPV Kamera", 159.00, 5565, "Sony 1/1.8\" Sensor", "1080P/120fps, GyroFlow"),
            ("Ratel 2 Micro FPV Camera", "1200TVL Analog", ["19x19mm Micro"], "Low Light Starlight HDR Analog FPV Camera", "Yıldız Işığı HDR Düşük Işık Analog FPV Kamera", 29.99, 1050, "1/1.8\" Starlight HDR", "Day/Night Auto Switch"),
            ("Predator 5 Nano FPV Camera", "1000TVL Analog", ["14x14mm Nano"], "Super Low Latency 4ms Racing Camera", "4ms Ultra Düşük Gecikmeli Yarış Kamerası", 32.50, 1135, "1/3\" CMOS", "Super WDR, 4ms Latency"),
            ("HDZero Nano 90 Camera", "720p 90fps Zero Latency", ["14x14mm Nano"], "Digital Uncompressed High Framerate Racing Camera", "Sıfır Gecikmeli Yüksek Kare Hızlı Dijital Kamera", 69.90, 2445, "HDZero Digital", "720p 90fps / 540p 90fps"),
            ("Thumb Pro 4K Action Camera", "4K 30fps Wide", ["Ultra Lightweight 16g"], "16g Action Camera with Gyroflow Support", "16g Ağırlığında Gyroflow Destekli Aksiyon Kamerası", 89.00, 3115, "4K Wide FOV", "16 Grams, ND Filters Inc.")
        ]
    },
    # Video Transmitters (VTX) (35 items)
    {
        "cat": "vtx",
        "count": 35,
        "types": [
            ("Unify Pro32 HV 5.8GHz 1000mW", "1000mW High Power", ["MMCX Connector"], "Long Range Bulletproof Analog VTX with SmartAudio", "SmartAudio Destekli Uzun Menzil Analog VTX", 49.99, 1750, "5.8GHz 40CH", "25-1000mW Variable"),
            ("Reaper Extreme 2.5W VTX", "2500mW Monster Power", ["Aluminium Heatsink"], "2.5W Maximum Range Video Transmitter", "2.5 Watt Maksimum Güçte Video Vericisi", 64.90, 2270, "5.8GHz Pit/25/2500mW", "CNC Metal Case"),
            ("Tank II Ultimate 1W VTX", "1000mW / 1W", ["Lock-R MMCX"], "Durable Metal Shielding Freestyle VTX", "Metal Korumalı Dayanıklı Freestyle VTX", 44.00, 1540, "5.8GHz SmartAudio", "25/200/500/800/1000mW"),
            ("TX800 VTX 800mW Mini", "800mW 20x20mm", ["IPEX / MMCX"], "Ultralight 20x20 Stack Video Transmitter", "Ultra Hafif 20x20 Kule Uyumlu Video Verici", 21.90, 765, "5.8GHz IRC Tramp", "25-800mW Adjustable"),
            ("Walksnail Avatar GT VTX 2W", "2000mW Digital HD", ["Dual Antenna"], "Long Range Digital High Power Video Transmitter", "Uzun Menzil Dijital Yüksek Güçlü VTX Modülü", 119.00, 4165, "Walksnail HD System", "Dual Antennas, 2000mW")
        ]
    },
    # Radio Receivers & Transmitters (40 items)
    {
        "cat": "transmitters_receivers",
        "count": 40,
        "types": [
            ("TX16S MKII MAX Radio Transmitter", "EdgeTX / ELRS 2.4GHz", ["Hall Gimbals V4"], "Flagship 16-Channel Radio Controller with Color Touchscreen", "Renkli Dokunmatik Ekranlı Amiral Gemisi 16 Kanallı Kumanda", 289.00, 10115, "EdgeTX / ELRS", "AG01 CNC Hall Gimbals"),
            ("Boxer Radio Controller M2", "ExpressLRS 2.4GHz 1W", ["Full Size Gimbals"], "High Ergonomic 1W Internal ELRS Radio Controller", "Ergonomik Dahili 1W ELRS Vericili Kumanda", 139.00, 4865, "EdgeTX / ELRS 1000mW", "High Capacity Battery Bay"),
            ("Pocket Radio Controller", "ELRS 2.4GHz", ["Removable Stick Ends"], "Ultra-Portable Foldable Pocket Radio Transmitter", "Ultra Taşınabilir Katlanabilir Cep Kumandası", 64.99, 2275, "EdgeTX / ELRS", "USB-C Charging, 18650 Bay"),
            ("RP1 ExpressLRS 2.4GHz Nano Receiver", "ELRS 2.4GHz", ["TCXO Crystal"], "High Sensitivity 2.4GHz Nano Receiver with T-Antenna", "T-Antenli Yüksek Hassasiyetli 2.4GHz Nano Alıcı", 15.90, 555, "ExpressLRS Protocol", "0.53g Ultra Lightweight"),
            ("Crossfire Nano RX Pro", "915MHz / 868MHz Long Range", ["Immortal-T V2"], "500mW Telemetry Long Range Receiver", "500mW Telemetrili Uzun Menzil Alıcı", 39.90, 1395, "TBS CRSF Protocol", "50km+ Range Capability"),
            ("SuperD ELRS 2.4GHz Diversity Receiver", "Dual TCXO Diversity", ["Dual T-Antenna"], "Dual Radio Frequency True Diversity Receiver", "Çift Antenli Gerçek Diversity ELRS Alıcısı", 21.50, 750, "ExpressLRS 2.4G", "Dual SX1280 Chips")
        ]
    },
    # LiPo Batteries & Chargers (45 items)
    {
        "cat": "batteries_chargers",
        "count": 45,
        "types": [
            ("R-Line Version 5.0 1400mAh 6S 150C", "6S 22.2V 1400mAh 150C", ["XT60 Plug"], "Competition High Discharge LiPo Battery Pack", "Yarışma Seviyesi Yüksek Deşarjlı LiPo Batarya", 38.50, 1345, "150C Discharge / 300C Burst", "XT60 Connector"),
            ("Black Series 1500mAh 4S 100C", "4S 14.8V 1500mAh 100C", ["XT60 Plug"], "Reliable Freestyle 4S High Performance LiPo", "Güvenilir Yüksek Performanslı Freestyle 4S LiPo", 21.00, 735, "100C Continuous", "XT60 Connector"),
            ("Long Range 21700 6S2P 8000mAh Li-ion", "6S 22.2V 8000mAh", ["XT60 Plug"], "Ultra Long Flight Endurance Li-ion Battery Pack", "Ultra Uzun Uçuş Süreli Li-ion Batarya Paketi", 78.00, 2730, "Molicel P42A Cells", "45+ Mins Flight Time"),
            ("K4 Smart Dual Channel AC/DC Charger", "AC 400W / DC 600Wx2", ["Dual Output"], "Color IPS Screen Smart Balance Fast Charger", "IPS Renkli Ekranlı Akıllı Çift Kanallı Hızlı Şarj Cihazı", 179.00, 6265, "1-8S LiPo/LiFe/Li-ion", "OTA Firmware Upgrade"),
            ("608AC Smart Pocket Charger 200W", "AC 50W / DC 200W", ["Detachable Power Supply"], "Compact Travel AC/DC Smart Balance Charger", "Kompakt Seyahat Tipi AC/DC Akıllı Denge Şarj Cihazı", 62.00, 2170, "1-6S LiPo", "BattGo Support"),
            ("M6D Dual Smart Charger 500W", "Dual 250W DC", ["USB Fast Charge"], "Ultra Compact Dual Output DC Field Charger", "Ultra Kompakt Çift Çıkışlı DC Saha Şarj Aleti", 54.00, 1890, "1-6S LiPo", "Dual Channel 15A")
        ]
    },
    # Drone Frames (35 items)
    {
        "cat": "frames",
        "count": 35,
        "types": [
            ("Nazgul5 V3 HD 5-Inch Frame Kit", "5-Inch Freestyle", ["3K Carbon Fiber"], "Reinforced True-X Freestyle Carbon Fiber Frame with TPU Mounts", "Güçlendirilmiş True-X Karbon Fiber Gövde ve TPU Parçalar", 49.99, 1750, "5mm Arms, 3K Carbon", "Compatible DJI O3 / Analog"),
            ("Mark5 O3 Freestyle Frame Kit", "5-Inch Deadcat / X", ["7075 Aluminium Camera Cage"], "Aerospace Aluminum Protected Freestyle Frame", "Havacılık Sınıfı Alüminyum Korumalı Freestyle Gövde", 68.00, 2380, "5mm Quick-Release Arms", "Optimized for DJI O3"),
            ("Source One V5 5-Inch Frame", "5-Inch Freestyle", ["Open Source Design"], "Heavy Duty Crash-Resistant Community Frame", "Darbe Dayanımlı Açık Kaynak Topluluk Gövdesi", 29.90, 1045, "5mm Carbon Arms", "Standard 30.5/20mm Mount"),
            ("Apex 5-Inch Freestyle Frame", "5-Inch High Durability", ["Arm Interlocking"], "Legendary Low Resonance Freestyle Frame", "Efsanevi Düşük Rezonanslı Freestyle Drone Gövdesi", 89.00, 3115, "5.5mm Chamfered Carbon", "Custom Keyed Arm Joint"),
            ("Pavo25 V2 Cinewhoop Frame Kit", "2.5-Inch Ducted Whoop", ["Injection Molded Ducts"], "Ultra Quiet Indoor & Cinematic Whoop Frame", "Ultra Sessiz İç Mekan ve Sinematik Whoop Gövdesi", 34.90, 1220, "PA12 Ducts + Carbon", "Supports DJI O3 & Naked GoPro"),
            ("Explorer LR 4 HD Long Range Frame", "4-Inch Ultralight Long Range", ["Sub250g Class"], "Sub-250g Capable Long Range Cruiser Frame", "250 Gram Altı Uzun Menzil Keşif Gövdesi", 39.00, 1365, "3mm Carbon Plate", "GPS & Dual Antenna Mounts")
        ]
    },
    # Antennas (30 items)
    {
        "cat": "antennas",
        "count": 30,
        "types": [
            ("Lollipop 4 Plus 5.8GHz Antenna (2-Pack)", "5.8GHz RHCP/LHCP", ["SMA / RP-SMA / U.FL / MMCX"], "Durable High Gain Omnidirectional FPV Antenna", "Dayanıklı Yüksek Kazançlı Çok Yönlü FPV Anteni (2'li Paket)", 19.99, 700, "2.6dBi Gain, RHCP", "Impact Resistant Polycarbonate"),
            ("Triumph Pro 5.8GHz RHCP Antenna", "5.8GHz Omnidirectional", ["Ultra Compact Stubby"], "Micro High Performance Circular Polarized Antenna", "Mikro Yüksek Performanslı Dairesel Polarize Anten", 18.50, 645, "1.26dBi Gain", "Ultralight Ultrasonic Welded"),
            ("Singularity 5.8GHz Directional Patch", "5.8GHz 9.4dBi Patch", ["SMA High Gain"], "Long Range High Gain Goggle Receiver Antenna", "Uzun Menzil Yüksek Kazançlı Gözlük Alıcı Yama Anteni", 32.00, 1120, "9.4dBi Beamwidth 85 deg", "RHCP / LHCP Available"),
            ("Matchstick 5.8GHz Carbon Antenna", "5.8GHz High Axil", ["Carbon Fiber Tube"], "Low Drag Aerodynamic Racing Antenna", "Düşük Sürtünmeli Aerodinamik Yarış Anteni", 16.90, 590, "1.9dBi Gain", "Rigid Carbon Shaft")
        ]
    },
    # GPS & Telemetry (25 items)
    {
        "cat": "gps_telemetry",
        "count": 25,
        "types": [
            ("M10-5883 High Precision GPS Module", "u-blox M10 GNSS", ["QMC5883L Compass"], "Multi-Constellation Fast Lock GPS & Magnetic Compass", "Çoklu Uydu Hızlı Kilitlenen GPS ve Manyetik Pusula", 29.50, 1030, "GPS, GLONASS, Galileo, BeiDou", "Concurrent 4 GNSS Reception"),
            ("Micro M8N GPS Module with Active Patch", "u-blox M8N", ["Ceramic Antenna"], "Reliable Rescue Mode Return-To-Home GPS", "Güvenilir Eve Dönüş (RTH) ve Kurtarma Modu GPS'i", 18.90, 660, "72-Channel Receiver", "Up to 10Hz Update Rate"),
            ("Optical Flow & Lidar Sensor Board", "PMW3901 + VL53L1X", ["Indoor Hover"], "Indoor Position Hold Precision Optical Sensor", "İç Mekan Hassas Sabitlenme Optik Akış ve Lidar Sensörü", 24.90, 870, "UART Interface", "Ground Tracking without GPS")
        ]
    },
    # Tools & Accessories (40 items)
    {
        "cat": "tools_accessories",
        "count": 40,
        "types": [
            ("TS101 Smart Digital Soldering Iron 65W", "65W USB-C / DC", ["OLED Screen & Temperature Control"], "Portable Precision Soldering Iron for Field Repairs", "Saha Tamirleri İçin Taşınabilir Akıllı Dijital Havya", 58.00, 2030, "100-400 C Temp Range", "USB-C PD & DC5525 Input"),
            ("Titanium Hex Screwdriver Tool Set (4-Piece)", "1.5mm, 2.0mm, 2.5mm, 3.0mm", ["HSS Titanium Coated"], "Hardened Titanium Hex Driver Set for Drone Assembly", "Drone Montajı İçin Sertleştirilmiş Titanyum Alyan Seti", 22.50, 785, "Ultra Grip CNC Handle", "Replaceable Tips"),
            ("Smart Smoke Stopper XT60 & XT30", "0.5A / 1.0A Trip", ["Dual Connector"], "Electronic Fuse Short Circuit & Reverse Polarity Protector", "Kısa Devre ve Ters Kutup Koruyucu Elektronik Sigorta", 11.50, 400, "Fast 1ms Response", "Dual XT30 / XT60 In/Out"),
            ("High Purity 60/40 Rosin Core Solder Wire", "0.8mm 100g", ["Rosin Core 2.0%"], "Premium Low Melting Point Lead Solder Wire", "Düşük Erime Noktalı Kaliteli Lehim Teli", 9.90, 345, "0.8mm Diameter", "Flux 2.0%"),
            ("M2 & M3 Black Nylon & Steel Standoff Kit (300Pcs)", "M2 / M3 Assortment", ["Plastic Organizer Box"], "Complete Hardware Screw, Nut & Standoff Assortment", "Kapsamlı Drone Montaj Civata, Somun ve Yükseltici Seti", 15.00, 525, "M2 & M3 Sizes", "High Tensile 12.9 Steel & Nylon")
        ]
    }
]

CATEGORY_PHOTOS = {
    "motors": [
        "/assets/products/motor.png",
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=600&q=80"
    ],
    "esc": [
        "/assets/products/esc.png",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1597733336794-12d05021d510?auto=format&fit=crop&w=600&q=80"
    ],
    "propellers": [
        "/assets/products/prop.png",
        "https://images.unsplash.com/photo-1527977966376-1c8408f9f108?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1506947411487-a56738267384?auto=format&fit=crop&w=600&q=80"
    ],
    "converters": [
        "/assets/products/bec.png",
        "https://images.unsplash.com/photo-1555680202-c86f0e12f086?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1563770660941-20978e870e26?auto=format&fit=crop&w=600&q=80"
    ],
    "flight_controllers": [
        "/assets/products/fc.png",
        "https://images.unsplash.com/photo-1580894732444-8ecded7900cd?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1587202372775-e229f172b9d7?auto=format&fit=crop&w=600&q=80"
    ],
    "cameras": [
        "/assets/products/cam.png",
        "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?auto=format&fit=crop&w=600&q=80"
    ],
    "vtx": [
        "/assets/products/vtx.png",
        "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1550009158-9ebf69173e03?auto=format&fit=crop&w=600&q=80"
    ],
    "transmitters_receivers": [
        "/assets/products/radio.png",
        "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=600&q=80"
    ],
    "batteries_chargers": [
        "/assets/products/lipo.png",
        "https://images.unsplash.com/photo-1619725002198-6a689b72f41d?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1584438784894-089d6a62b8fa?auto=format&fit=crop&w=600&q=80"
    ],
    "frames": [
        "/assets/products/frame.png",
        "https://images.unsplash.com/photo-1508614589041-895b88991e3e?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1521405924368-64c5b84bec60?auto=format&fit=crop&w=600&q=80"
    ],
    "antennas": [
        "/assets/products/antenna.png",
        "https://images.unsplash.com/photo-1541872703-74c5e44368f9?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80"
    ],
    "gps_telemetry": [
        "/assets/products/fc.png",
        "https://images.unsplash.com/photo-1526778548025-fa2f459cd5c1?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1580894732444-8ecded7900cd?auto=format&fit=crop&w=600&q=80"
    ],
    "tools_accessories": [
        "/assets/products/frame.png",
        "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=600&q=80",
        "https://images.unsplash.com/photo-1581092335397-9583fe92d232?auto=format&fit=crop&w=600&q=80"
    ]
}

def get_product_images(cat_id, product_idx, brand):
    photos = CATEGORY_PHOTOS.get(cat_id, CATEGORY_PHOTOS["motors"])
    primary_idx = (product_idx - 1) % len(photos)
    primary_url = photos[primary_idx]
    
    # Create gallery with 2-3 photos from same category
    gallery = [primary_url]
    for offset in [1, 2]:
        sec_idx = (primary_idx + offset) % len(photos)
        if photos[sec_idx] not in gallery:
            gallery.append(photos[sec_idx])
            
    return primary_url, gallery

def seed_database():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear existing data safely
    cursor.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("DELETE FROM reviews")
    cursor.execute("DELETE FROM orders")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM categories")
    cursor.execute("DELETE FROM users")
    cursor.execute("PRAGMA foreign_keys = ON;")

    # Insert Categories
    print("Inserting categories...")
    for cat in CATEGORIES:
        cursor.execute('''
            INSERT INTO categories (id, slug, name_en, name_tr, icon, description_en, description_tr, item_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (cat["id"], cat["slug"], cat["name_en"], cat["name_tr"], cat["icon"], cat["description_en"], cat["description_tr"]))

    # Generate 500 Realistic Drone Items
    print("Generating 500 curated drone items...")
    products = []
    total_needed = 500
    category_counts = {cat["id"]: 0 for cat in CATEGORIES}

    # Desired distribution across 13 categories (sum = 500)
    target_distribution = {
        "motors": 55,
        "esc": 45,
        "propellers": 50,
        "converters": 35,
        "flight_controllers": 40,
        "cameras": 35,
        "vtx": 30,
        "transmitters_receivers": 40,
        "batteries_chargers": 45,
        "frames": 35,
        "antennas": 30,
        "gps_telemetry": 25,
        "tools_accessories": 35
    }

    # Verify total
    assert sum(target_distribution.values()) == 500, f"Distribution total is {sum(target_distribution.values())}, expected 500"

    product_idx = 1
    now = datetime.now()

    for cat_id, target_count in target_distribution.items():
        cat_conf = next(c for c in ITEM_CONFIGS if c["cat"] == cat_id)
        templates = cat_conf["types"]
        brands = BRANDS[cat_id]

        for i in range(target_count):
            tpl = templates[i % len(templates)]
            brand = brands[(i + (i // len(templates))) % len(brands)]
            
            base_model_name = tpl[0]
            spec_variant = tpl[1]
            options = tpl[2]
            desc_en_core = tpl[3]
            desc_tr_core = tpl[4]
            base_usd = tpl[5]
            base_try = tpl[6]
            spec1 = tpl[7]
            spec2 = tpl[8]

            selected_opt = options[i % len(options)]
            
            # Variations in model naming to ensure rich diversity
            sub_id = (i // len(templates)) + 1
            version_suffix = f"V{sub_id}" if sub_id > 1 else "PRO"
            
            # Product Names
            name_en = f"{brand} {base_model_name} {version_suffix} ({selected_opt})"
            name_tr = f"{brand} {base_model_name} {version_suffix} ({selected_opt})"

            slug = f"{brand.lower().replace(' ', '-').replace('(', '').replace(')', '')}-{base_model_name.lower().replace(' ', '-').replace('/', '-')}-{version_suffix.lower()}-{i+1}"
            sku = f"PZTR-{cat_id[:3].upper()}-{product_idx:04d}"

            # Pricing with minor realistic variations
            price_variance = round(random.uniform(0.90, 1.15), 2)
            price_usd = round(base_usd * price_variance, 2)
            price_try = round(price_usd * 47.0, 2)
            original_price_usd = None
            original_price_try = None
            if random.random() > 0.7:  # 30% chance of being on sale
                original_price_usd = round(price_usd * random.uniform(1.1, 1.5), 2)
                original_price_try = round(original_price_usd * 47.0, 2)
            else:
                original_price_usd = None
                original_price_try = None

            discount_pct = round(((original_price_usd - price_usd) / original_price_usd) * 100) if original_price_usd else 0

            rating = round(random.uniform(4.4, 5.0), 1)
            review_count = random.randint(5, 180)
            stock = random.randint(8, 120)

            # Badges
            badge = None
            if i % 7 == 0:
                badge = "BESTSELLER"
            elif i % 11 == 0:
                badge = "NEW"
            elif discount_pct >= 15:
                badge = f"-{discount_pct}% OFF"

            featured = 1 if (i % 12 == 0) else 0
            is_bestseller = 1 if (badge == "BESTSELLER" or rating >= 4.9) else 0

            # Technical Specs JSON
            specs = {
                "brand": brand,
                "model": f"{base_model_name} {version_suffix}",
                "spec_variant": spec_variant,
                "option": selected_opt,
                "input_voltage": spec1,
                "mounting_spec": spec2,
                "weight_g": round(random.uniform(3.5, 140.0), 1),
                "dimensions_mm": f"{random.randint(14, 45)}x{random.randint(14, 45)}x{random.randint(5, 30)}",
                "warranty_months": 12,
                "origin": "Pozitron Certified Genuine OEM",
                "in_the_box": f"1x {brand} {base_model_name} {version_suffix}, Mounting Hardware Pack, Quick Manual"
            }

            # Tags JSON
            tags = [
                cat_id,
                brand.lower(),
                "fpv",
                "drone",
                "high-performance",
                spec_variant.lower()
            ]
            if "6S" in spec1:
                tags.append("6s")
            if "4S" in spec1:
                tags.append("4s")

            # Dual Language Descriptions
            desc_en = f"The {brand} {base_model_name} {version_suffix} is engineered for peak drone performance. Featuring {spec_variant} with {selected_opt} specifications, {desc_en_core}. Built with aerospace-grade components for extreme durability, low noise, and maximum efficiency. Compatible with standard FPV drone stacks and power setups."
            desc_tr = f"{brand} {base_model_name} {version_suffix}, en yüksek drone performansı için tasarlanmıştır. {spec_variant} ve {selected_opt} özelliklerine sahip olup, {desc_tr_core}. Aşırı dayanıklılık, düşük gürültü ve maksimum verimlilik için havacılık sınıfı bileşenlerle üretilmiştir. Standart FPV drone montajları ve güç sistemleriyle tam uyumludur."

            image_url, gallery = get_product_images(cat_id, product_idx, brand)

            # Compatibility metadata (e.g. for Drone Builder Checker)
            compat = {
                "voltage": "6S" if "6S" in spec1 else ("4S" if "4S" in spec1 else "Universal"),
                "mount": spec2,
                "size_class": "5-inch" if "2207" in name_en or "5" in name_en else ("3-inch" if "1404" in name_en or "whoop" in name_en.lower() else "Universal")
            }

            created_date = (now - timedelta(days=random.randint(1, 180))).isoformat()

            products.append((
                str(uuid.uuid4()),
                slug,
                sku,
                name_en,
                name_tr,
                cat_id,
                brand,
                price_usd,
                price_try,
                original_price_usd,
                original_price_try,
                discount_pct,
                rating,
                review_count,
                stock,
                badge,
                json.dumps(specs),
                json.dumps(tags),
                image_url,
                json.dumps(gallery),
                desc_en,
                desc_tr,
                json.dumps(compat),
                featured,
                is_bestseller,
                created_date
            ))

            category_counts[cat_id] += 1
            product_idx += 1

    # Bulk insert products
    cursor.executemany('''
        INSERT INTO products (
            id, slug, sku, name_en, name_tr, category_id, brand,
            price_usd, price_try, original_price_usd, original_price_try,
            discount_pct, rating, review_count, stock, badge,
            specs_json, tags_json, image_url, gallery_json,
            description_en, description_tr, compatibility_json,
            featured, is_bestseller, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', products)

    # Update category item counts
    for cat_id, count in category_counts.items():
        cursor.execute("UPDATE categories SET item_count = ? WHERE id = ?", (count, cat_id))

    # Seed Admin & Demo Users (Google Demo + Manual Demo)
    print("Seeding demo users...")
    demo_users = [
        (
            str(uuid.uuid4()),
            "eyup@pozitron.com",
            hash_password("pozitron2026"),
            "Eyüp Yılmaz",
            "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=150&q=80",
            "manual",
            "admin",
            "+90 555 123 4567",
            "Teknokent Ar-Ge Binası No: 42",
            "Istanbul",
            "Turkey",
            now.isoformat()
        ),
        (
            str(uuid.uuid4()),
            "demo.pilot@gmail.com",
            None,
            "Alex FPV Pilot",
            "https://images.unsplash.com/photo-1570295999919-56ceb5ecca61?auto=format&fit=crop&w=150&q=80",
            "gmail",
            "customer",
            "+1 555 987 6543",
            "742 Evergreen Terrace",
            "San Francisco",
            "United States",
            now.isoformat()
        ),
        (
            str(uuid.uuid4()),
            "drone.tr@gmail.com",
            None,
            "Can Demir",
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&q=80",
            "gmail",
            "customer",
            "+90 532 999 8877",
            "Karaköy Rıhtım Cad. No: 15",
            "Istanbul",
            "Turkey",
            now.isoformat()
        )
    ]

    cursor.executemany('''
        INSERT INTO users (id, email, password_hash, full_name, avatar_url, provider, role, phone, address, city, country, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', demo_users)

    # Seed sample authentic reviews for top products
    print("Seeding authentic pilot reviews...")
    cursor.execute("SELECT id, name_en FROM products LIMIT 50")
    sample_prods = cursor.fetchall()
    
    review_comments = [
        ("Mert K.", 5, "Incredible response and low vibration!", "İnanılmaz tepki süresi ve sıfır titreşim. 6S pille tam bir canavar, kesinlikle tavsiye ederim!"),
        ("David R.", 5, "Best performance upgrade on my 5-inch quad", "High build quality, extremely smooth power delivery on Betaflight 4.4."),
        ("Selim A.", 5, "Kargo çok hızlı geldi, orijinal ürün", "Paketleme harika, kutu içeriğinde montaj vidaları tam çıktı. Pozitron ekibine teşekkürler."),
        ("Carlos M.", 4, "Great efficiency and durability", "Survived several harsh crashes with only minor scratches. Solid engineering."),
        ("Burak Y.", 5, "Fiyat/Performans lideri", "Bu fiyata bu kalite inanılmaz. Telemetri verileri çok net ve kararlı.")
    ]

    reviews_to_insert = []
    for prod in sample_prods:
        p_id = prod[0]
        for idx, (uname, r_val, r_title, r_text) in enumerate(review_comments):
            r_date = (now - timedelta(days=random.randint(2, 60))).isoformat()
            reviews_to_insert.append((
                str(uuid.uuid4()),
                p_id,
                uname,
                f"https://api.dicebear.com/7.x/bottts/svg?seed={uname}",
                r_val,
                r_title,
                r_text,
                1,
                r_date
            ))

    cursor.executemany('''
        INSERT INTO reviews (id, product_id, user_name, user_avatar, rating, title, comment, verified_purchase, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', reviews_to_insert)

    conn.commit()
    conn.close()
    print(f"Successfully seeded database with {len(products)} products, {len(CATEGORIES)} categories, {len(demo_users)} users, and {len(reviews_to_insert)} reviews!")

if __name__ == '__main__':
    seed_database()
