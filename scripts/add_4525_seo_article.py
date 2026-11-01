import sqlite3
import json
from datetime import datetime
from database import get_db

conn = get_db()
cursor = conn.cursor()

slug = 'rehber-4525-3-pervane-gemfan-hurricane-fpv-aerodinamigi'
title = '4525-3 Pervane Nedir? Gemfan Hurricane 4525-3 FPV Drone Aerodinamiği ve Motor Seçimi Rehberi'
component_focus = 'propellers'
target_keywords = '4525-3 pervane, 4525 pervane, gemfan 4525, gemfan hurricane 4525-3, 4.5 inç drone pervanesi, sub-250g pervane, FPV drone pervanesi, Pozitron Market'

internal_links = [
    {
        'sku': 'PZTR-PRO-0151',
        'name': "Gemfan Hurricane 4525-3 3 Kanatlı Dayanıklı FPV Drone Pervanesi (Clear Gray - 4'lü Set)",
        'slug': 'gemfan-hurricane-4525-3',
        'url': 'https://pozitronmarket.com/products/gemfan-hurricane-4525-3'
    }
]

content_markdown = """# 4525-3 Pervane Nedir? Gemfan Hurricane 4525-3 FPV Drone Aerodinamiği ve Motor Seçimi Rehberi

**Yazar:** Pozitron Market FPV Donanım & Aerodinamik Laboratuvarı  
**Hedef Arama Terimleri:** `4525-3 pervane, 4525 pervane, gemfan 4525, gemfan hurricane 4525-3, 4.5 inç drone pervanesi, sub-250g pervane, Pozitron Market`  
**Yayın Tarihi:** 01.11.2026

---

## 1. 4525-3 Pervane Kodu Ne Anlama Gelir?

FPV drone dünyasında pervaneler endüstri standardı olan **[Çap][Hatve]-[Kanat Sayısı]** geometrisiyle kodlanır:
- **45:** Pervane diskinin toplam dış çapını temsil eder: **4.5 inç (yaklaşık 114.8 mm)**.
- **25:** Pervanenin hatvesi / adımı (pitch): **2.5 inç**. Yani teorik olarak pervanenin kayma (slip) olmadan tek bir tam devrinde kat edeceği mesafedir.
- **-3:** Pervane üzerindeki kanat sayısını gösterir: **3 kanat (Tri-Blade)**.

Arama motorlarında veya FPV pilot topluluklarında **4525-3 pervane** veya **4525 pervane** olarak aratılan bu model, özellikle **Gemfan Hurricane** serisiyle küresel üne kavuşmuştur.

---

## 2. Neden 4.5 İnç Hibrit Ölçü? (4" vs 4.5" vs 5")

Standart 5 inç FPV pervaneleri (örneğin 51466 veya 51433) yüksek son hız ve itki sunsa da ağır motorlar ve 6S bataryalar gerektirir. Bu da hava aracının toplam uçuş ağırlığını (AUW) genellikle 600g - 750g seviyesine taşır. Öte yandan klasik 4 inç (4025) pervaneler hafif platformlarda viraj tutuşunda ve ani gaz kesme (propwash) manevralarında yeterli dikey çekiş üretemeyebilir.

İşte tam bu noktada **Gemfan Hurricane 4525-3**, 4 inç ile 5 inç arasındaki aerodinamik boşluğu doldurur:
1. **Ultra Düşük Ataletsel Moment (Inertia):** Sadece **2.22 gram** ağırlığındaki polikarbonat gövde, fırçasız motorun mikrosaniyeler içinde devirlenmesini sağlar. Gaz kolu tepkisi gecikmesizdir.
2. **Sub-250g ve Mikro Long-Range Uyumu:** 250 gram altı yasal sınırda kalan hafif yarış ve freestyle quadcopter tasarımlarında maksimum verimlilik ve uçuş süresi sunar.
3. **Propwash Eliminasyonu:** Yüksek mukavemetli havacılık sınıfı polikarbonat (PC) malzeme, sert dalış çıkışlarında kanat bükülmesini (blade flutter) engelleyerek pürüzsüz HD/O3 kamera görüntüleri sağlar.

---

## 3. Uyumlu Motor ve Gövde Seçimi

Gemfan Hurricane 4525-3 pervanesi şu donanım mimarileriyle mükemmel uyum sağlar:
- **Tavsiye Edilen Stator Ölçüleri:** 2004, 1505, 1606, 1408 fırçasız motorlar.
- **Voltaj ve KV Değeri:**
  - 4S LiPo kurulumlarda: **3000KV - 3800KV**
  - 6S LiPo ultralight kurulumlarda: **1950KV - 2450KV**
- **Çift Montaj Desteği (Dual Hub):** Hem geleneksel **5mm vida mili (M5)** hem de ultralight motorların **1.5mm / 2mm T-Mount (çift vida)** montaj deseniyle doğrudan uyumludur.

---

## 4. Orijinal Gemfan Hurricane 4525-3 Nereden Temin Edilir?

Pozitron Market stoklarında orijinal Gemfan onaylı [Gemfan Hurricane 4525-3 3 Kanatlı Dayanıklı FPV Drone Pervanesi](https://pozitronmarket.com/products/gemfan-hurricane-4525-3) (Stok Kodu: `PZTR-PRO-0151`) 4'lü set halinde (2 CW, 2 CCW) aynı gün kargo ve teknik destek güvencesiyle sunulmaktadır.
"""

cursor.execute('DELETE FROM seo_articles WHERE slug = ?', (slug,))
cursor.execute('''
    INSERT INTO seo_articles (slug, title, component_focus, target_keywords, internal_links_json, content_markdown, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
''', (slug, title, component_focus, target_keywords, json.dumps(internal_links), content_markdown, datetime.now().isoformat()))

conn.commit()
conn.close()
print("Successfully inserted 4525-3 SEO Guide into database!")
