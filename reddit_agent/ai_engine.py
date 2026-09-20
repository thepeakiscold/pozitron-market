import json
import urllib.request
import urllib.error
import re
import os

class GeminiRedditEngine:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        # Primary and fallback model names (Gemini 3.8 Flash primary)
        self.models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        self._ensure_api_key()

    def _ensure_api_key(self):
        if not self.api_key:
            try:
                from database import get_db
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT gemini_api_key FROM reddit_agent_config LIMIT 1")
                row = cursor.fetchone()
                if row and row[0]:
                    self.api_key = row[0].strip()
                if not self.api_key:
                    cursor.execute("SELECT gemini_api_key FROM instagram_agent_config LIMIT 1")
                    row2 = cursor.fetchone()
                    if row2 and row2[0]:
                        self.api_key = row2[0].strip()
                conn.close()
            except Exception:
                pass

    def set_api_key(self, key: str):
        self.api_key = key

    def evaluate_and_generate_reply(self, title: str, body: str, subreddit: str, author: str, custom_signature: str = "") -> dict:
        """
        Evaluates a Reddit post/comment to determine if it's a genuine drone/FPV question
        and crafts an expert, friendly Turkish response strictly matching the post topic.
        """
        self._ensure_api_key()
        if not self.api_key:
            return self._fallback_rule_response(title, body, custom_signature)

        # Load active Lead Supervisor directive links if available
        lead_links_context = ""
        try:
            from database import get_db
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT directive_json FROM lead_supervisor_directives ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                d_data = json.loads(row[0])
                pref_links = d_data.get("reddit_directive", {}).get("preferred_hardware_links", [])
                if pref_links:
                    lines = [f"- {item['name']}: {item['url']} ({item.get('advantage_note', '')})" for item in pref_links]
                    lead_links_context = "\nÖNCELİKLİ YEREL STOK VE FİYAT AVANTAJLI DONANIMLAR (Yalnızca kullanıcı doğrudan parça/tedarik kaynağı sorarsa tarafsız mühendis üslubuyla aktar):\n" + "\n".join(lines)
        except Exception:
            pass

        prompt = f"""Sen Türkiye'nin önde gelen FPV drone ve robotik donanım platformu Pozitron Market'in (pozitronmarket.com) kıdemli FPV pilotu ve teknik donanım mühendisisin.
Reddit üzerinde Türk ve global drone/havacılık topluluklarında soru soran kullanıcılara yardımcı oluyorsun.

GÖREV:
Aşağıdaki Reddit gönderisini ve kullanıcının sorusunu analiz et. Gönderinin konusuna %100 ODAKLANARAK doğrudan kullanıcının sorduğu şeyi yanıtlayan, teknik olarak doğru, samimi ve son derece yardımsever bir Türkçe yanıt hazırla.

KRİTİK UYARI VE İÇERİK UYUMU:
1. GÖNDERİ KONUSUNA %100 SADIK KAL: Kullanıcı satın alma tavsiyesi veya hobiye başlama soruyorsa ("Drone almak mantıklı mı?", "tavsiye", "fiyat"); SADECE satın alma, simülatör ve model seçimi tavsiyesi ver. Asla lehimleme, Betaflight portu gibi alakasız teknik detaylar anlatma!
2. TEKNİK ARIZA SORULARI: Kullanıcı Betaflight, lehim, ELRS, ESC, motor arızası soruyorsa doğrudan arıza çözüm adımlarını aktar.
3. BATARYA / LiPo SORULARI: Kullanıcı batarya soruyorsa LiPo hücre voltajı ve güvenli şarj/depolama adımlarını aktar.
4. MEVZUAT / İZİN SORULARI: Kullanıcı uçuş izni, SHGM kuralları veya ceza soruyorsa 500g kuralı ve yasal çerçeveyi aktar.
5. DRONE İLE ALAKASIZ KONULAR: Eğer gönderi doğrudan bir drone/FPV/havacılık konusu değilse (örneğin sadece mikrofon incelemesi, aksiyon kamera, genel siyaset veya haber), kesinlikle 'is_drone_question: false' ve 'confidence_score: 0' döndür.
6. ASLA DOĞRUDAN SPAM YAPMA: Kaba reklam ve alakasız ürün linki yasaktır.
7. TON: Samimi bir pilot arkadaş gibi ("Hocam", "Dostum" gibi Reddit üslubuyla), anlaşılır, adımları maddeler halinde listeleyen temiz Türkçe.
8. SIFIR EMOJİ KURALI: Kesinlikle hiçbir emoji kullanma.
9. İMZA: Yanıtın en altına şu imzayı ekle:
{custom_signature or '*İyi uçuşlar ve kırımsız günler! [POZİTRON MARKET]*'}
{lead_links_context}

GÖNDERİ BİLGİLERİ:
- Subreddit: r/{subreddit}
- Yazar: u/{author}
- Başlık: {title}
- İçerik/Metin: {body}

ÇIKTI FORMATI:
SADECE aşağıdaki JSON formatında geçerli bir JSON çıktısı üret, markdown kod bloğu dışında ek metin yazma:
{{
  "is_drone_question": true,
  "confidence_score": 90,
  "question_summary": "Kullanıcının sorduğu sorunun 1 cümlelik Türkçe özeti",
  "reply_text": "Reddit'te paylaşılacak markdown formatında Türkçe yanıt metni"
}}
"""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1000,
                "responseMimeType": "application/json"
            }
        }

        # Try models in order
        for model in self.models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=15) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                    candidate = res_data.get('candidates', [{}])[0]
                    content_parts = candidate.get('content', {}).get('parts', [])
                    if content_parts:
                        raw_text = content_parts[0].get('text', '').strip()
                        parsed = self._clean_and_parse_json(raw_text)
                        if parsed and 'reply_text' in parsed:
                            return {
                                "is_drone_question": bool(parsed.get('is_drone_question', True)),
                                "confidence_score": int(parsed.get('confidence_score', 85)),
                                "question_summary": parsed.get('question_summary', title[:100]),
                                "reply_text": parsed.get('reply_text', '').strip()
                            }
            except urllib.error.HTTPError as e:
                err_content = ""
                try:
                    err_content = e.read().decode('utf-8')
                except Exception:
                    pass
                # If model not found or deprecated, fallback to next model
                continue
            except Exception:
                continue

        return self._fallback_rule_response(title, body, custom_signature)

    def _clean_and_parse_json(self, text: str) -> dict:
        """Strips markdown fences and parses json."""
        if not text:
            return None
        # Clean any stray emojis
        text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]', '', text)
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except Exception:
            # Try regex extraction
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return None

    def _fallback_rule_response(self, title: str, body: str, custom_signature: str) -> dict:
        """
        Context-aware, intent-classified rule-based response generator.
        Accurately distinguishes buying advice, technical troubleshooting,
        battery questions, legal regulations, and flight showcases.
        Strictly rejects non-drone or mismatched topics.
        """
        text = f"{title} {body}".lower()
        summary = title if title else (body[:80] + '...')

        # Verify it has at least some drone/FPV context
        core_terms = ["drone", "dron", "fpv", "quad", "lehim", "motor", "esc", "vtx", "betaflight", "elrs", "dji", "teknofest", "lipo", "batarya", "pervane", "kumanda"]
        has_drone_context = any(term in text for term in core_terms)
        if not has_drone_context:
            return {
                "is_drone_question": False,
                "confidence_score": 0,
                "question_summary": summary[:100],
                "reply_text": ""
            }

        # Exclude non-drone camera/audio accessories
        audio_gear = ["mic", "mikrofon", "osmo pocket", "action cam", "gimbal", "ronin"]
        if any(term in text for term in audio_gear):
            if not any(d in text for d in ["uçuş", "ucus", "fpv", "quad", "lehim", "betaflight", "elrs", "esc", "motor"]):
                return {
                    "is_drone_question": False,
                    "confidence_score": 0,
                    "question_summary": summary[:100],
                    "reply_text": ""
                }

        sig = custom_signature or "*İyi uçuşlar ve kırımsız günler! [POZİTRON MARKET]*"
        clean_sig_tr = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]', '', sig).strip()
        clean_sig_en = "*Fly safe and happy flying! [POZITRON MARKET]*"

        # Language detection (English vs Turkish)
        turkish_chars = set("çğıöşüÇĞİÖŞÜ")
        has_tr_chars = any(c in text for c in turkish_chars)
        tr_indicators = ["nasıl", "neden", "hangisi", "tavsiye", "öneri", "almak", "arkadaşlar", "merhaba", "selam", "uçuş", "kullanıcı", "arızalandı", "çalışmıyor", "bağlantı"]
        is_turkish = has_tr_chars or any(w in text for w in tr_indicators)

        # Intent 1: Buying / Recommendation Advice
        buying_terms = [
            "almak mantıklı", "alınır mı", "alinir mi", "tavsiye", "öneri", "oneri",
            "hangi drone", "başlangıç", "baslangic", "ilk drone", "bütçe", "butce",
            "fiyat", "tercihiniz", "k arası", "k arasi", "ne kadara", "önerirsiniz", "onerirsiniz",
            "first fpv", "first drone", "buying", "recommend", "choice", "which drone", "budget", "worth it"
        ]
        if any(term in text for term in buying_terms):
            if is_turkish:
                reply = "Selamlar! Drone dünyasına adım atarken ya da bütçene en uygun tercihi yaparken dikkat etmeni önereceğim temel noktalar:\n\n"
                reply += "1. **Kullanım Amacı & Sınıf:** Amacın sabit kadraj, manzara ve pratik video çekimi ise hazır GPS/gimbal donanımlı modeller (örneğin DJI Mini serisi) uygundur. Eğer serbest akrobasi, hız ve tam kontrol (FPV) istiyorsan kapalı mekanlarda kırılmadan antrenman yaptıran bir Whoop kiti (örneğin BetaFPV Cetus / Meteor serisi) çok daha doğru bir ilk adımdır.\n"
                reply += "2. **Simülatör Önceliği:** FPV uçuşu düşünüyorsan drone'dan önce bilgisayara bağlanan ELRS destekli bir kumanda edinip (RadioMaster Pocket vb.) simülatörde (Velocidrone, Liftoff) 15-20 saat uçmak kırım masraflarını sıfıra indirir.\n"
                reply += "3. **500 Gram Kuralı:** 500g altı mikro modeller hobi uçuşlarında SHGM kayıt zorunluluğu bakımından çok daha esnektir.\n\n"
                reply += "Tam olarak bütçeni ve nasıl bir uçuş deneyimi hedeflediğini paylaşırsan doğrudan parça veya model bazında liste çıkarabilirim.\n\n" + clean_sig_tr
            else:
                reply = "Hey there! If you are getting started or picking your first drone setup, here are key tips:\n\n"
                reply += "1. **Simulator First:** Before buying a complete quad, get an ELRS radio controller (e.g. RadioMaster Pocket) and log 15-20 hours in a simulator (Liftoff, Velocidrone). It saves a lot of repair money.\n"
                reply += "2. **Tiny Whoop vs 5-inch:** For indoor practice and durability, a 1S Tiny Whoop (like BetaFPV Meteor65/75 or Mobula6/7) is the safest starting point.\n"
                reply += "3. **Weight & Regulations:** Sub-250g quads have fewer regulatory restrictions in most countries.\n\n"
                reply += "Feel free to share your budget and what kind of flying you want to do!\n\n" + clean_sig_en
            return {
                "is_drone_question": True,
                "confidence_score": 88,
                "question_summary": summary[:100],
                "reply_text": reply
            }

        # Intent 2: Battery / LiPo Care
        battery_terms = ["lipo", "batarya", "pil", "şarj", "sarj", "voltaj", "1s", "2s", "3s", "4s", "6s", "mah", "c rating", "depolama", "storage", "battery", "voltage", "charger"]
        if any(term in text for term in battery_terms):
            if is_turkish:
                reply = "Selamlar! Drone ve FPV bataryalarının güvenliği ve uzun ömrü için dikkat edilmesi gereken kritik noktalar:\n\n"
                reply += "1. **Hücre Başına Voltaj:** Uçuş sırasında hücre voltajını asla 3.5V altına düşürme (ideal iniş 3.6V-3.7V). Tam dolu hücre 4.20V (LiHV ise 4.35V) olmalıdır.\n"
                reply += "2. **Depolama (Storage):** Bataryaları birkaç günden fazla tam dolu ya da tamamen boş bırakma. Şarj aletinden 'Storage' modunu açarak hücreleri 3.80V-3.85V seviyesine getir.\n"
                reply += "3. **Şarj Akımı:** Pil sağlığı için standart olarak 1C şarj akımını geçmemeye özen göster (örneğin 1500mAh bir batarya için en fazla 1.5A).\n\n"
                reply += "Balans kablolarını ve hücreler arası voltaj farkını düzenli kontrol etmeyi unutma.\n\n" + clean_sig_tr
            else:
                reply = "Hey! For LiPo battery safety and longevity, keep these guidelines in mind:\n\n"
                reply += "1. **Per-Cell Voltage:** Never discharge below 3.5V per cell (aim to land around 3.6V-3.7V). Full charge is 4.20V (or 4.35V for LiHV).\n"
                reply += "2. **Storage Charge:** Don't leave packs fully charged or depleted for more than 48 hours. Charge or discharge them to 3.80V-3.85V per cell.\n"
                reply += "3. **Charge Rate:** Stick to 1C charge rate for longest cycle life (e.g. 1.5A for a 1500mAh pack).\n\n" + clean_sig_en
            return {
                "is_drone_question": True,
                "confidence_score": 88,
                "question_summary": summary[:100],
                "reply_text": reply
            }

        # Intent 3: Regulation / SHGM Flying Rules
        regulation_terms = ["shgm", "mevzuat", "ceza", "izin", "kayıt", "kayit", "yasak", "nerede uçulur", "nerede uculur", "yeşil alan", "yesil alan", "kırmızı alan", "kirmizi alan", "faa", "easa", "regulation", "249g"]
        if any(term in text for term in regulation_terms):
            if is_turkish:
                reply = "Selamlar! Türkiye'de drone uçuş kuralları ve SHGM mevzuatı hakkında temel rehber:\n\n"
                reply += "1. **500 Gram Sınırı:** Azami kalkış ağırlığı 500 gram ve üzeri olan tüm cihazlar ve pilotları SHGM İHA Kayıt Sistemi'ne (iha.shgm.gov.tr) kaydolmak zorundadır. 500g altındaki mikro cihazlar kayıt gerektirmese de genel uçuş kurallarına tabidir.\n"
                reply += "2. **Hava Sahası & İzinler:** SHGM haritasındaki kırmızı/uçuşa yasak bölgelerde (havalimanı yaklaşma hatları, askeri üsler, kamu binaları) izinsiz uçuş kesinlikle yasaktır. Yeşil alanlarda hobi amaçlı görerek uçuş (VLOS) yapılabilir.\n"
                reply += "3. **Maksimum İrtifa:** Yasal tavan irtifası 120 metredir (400 feet). Kalabalıkların ve otoyolların doğrudan üzerinden uçulmamalıdır.\n\n" + clean_sig_tr
            else:
                reply = "Hey! For drone regulations and sub-250g rules:\n\n"
                reply += "1. **Sub-250g Category:** Under most civil aviation frameworks (FAA, EASA, SHGM), drones weighing under 250g enjoy simplified registration and more flexible recreational flying permissions.\n"
                reply += "2. **Airspace & Altitude:** Standard legal ceiling is 120m (400ft) AGL. Always steer clear of airport controlled airspaces and emergency zones.\n"
                reply += "3. **Visual Line of Sight (VLOS):** Recreational flights generally require direct line-of-sight unless flying with a dedicated spotter for FPV goggles.\n\n" + clean_sig_en
            return {
                "is_drone_question": True,
                "confidence_score": 85,
                "question_summary": summary[:100],
                "reply_text": reply
            }

        # Intent 4: Technical Troubleshooting / Hardware / Betaflight
        tech_terms = ["betaflight", "lehim", "uart", "elrs", "crossfire", "esc", "motor", "vtx", "vrx", "bağlantı", "baglanti", "çalışmıyor", "calismiyor", "arızalandı", "arizalandi", "hata", "port", "f405", "f722", "dshot", "alici", "alıcı", "verici", "bind", "binding", "desync", "filter", "rpm", "inav", "solder", "troubleshoot", "desyncing"]
        if any(term in text for term in tech_terms):
            if is_turkish:
                reply = "Selamlar! FPV donanım ve yazılım arızalarında adım adım çözüm adımları:\n\n"
                reply += "1. **Bağlantılar & Donanım:** Multimetre ile kısa devre (continuity) kontrolü yap. Lehim noktalarının parlak, temiz ve komşu pinlerle temas etmediğinden emin ol.\n"
                reply += "2. **Betaflight Ports & Alıcı:** Ports sekmesinde alıcının bağlı olduğu UART portunda 'Serial RX' açık olmalı. Receiver sekmesinde doğru protokolün (CRSF/SBUS vb.) seçildiğini doğrula.\n"
                reply += "3. **Güç & Duman Testi:** İlk güç vermeden önce mutlaka duman önleyici (Smoke Stopper) kullan. Parçaların çalışma voltaj aralığının (örn. 1S-6S) besleme kaynağıyla tam uyumlu olduğunu kontrol et.\n\n"
                reply += "Kullandığın uçuş kartı modelini veya hata detayını paylaşırsan adım adım çözüme ulaşabiliriz.\n\n" + clean_sig_tr
            else:
                reply = "Hey! For FPV hardware & Betaflight troubleshooting, here are the step-by-step checks:\n\n"
                reply += "1. **Continuity & Soldering:** Check with a multimeter continuity buzzer to ensure no solder bridges between VTX, ESC, or battery pads.\n"
                reply += "2. **Betaflight Ports & Receiver:** Verify that 'Serial RX' is enabled on the exact UART port the receiver is wired to (TX to RX, RX to TX). Check that CRSF/ELRS protocol is selected in the Receiver tab.\n"
                reply += "3. **Power & Smoke Stopper:** Always use a smoke stopper on the first power-up. Check that your FC and ESC firmware match your hardware target.\n\n"
                reply += "Let us know your FC/ESC model or what error you see if you need more help!\n\n" + clean_sig_en
            return {
                "is_drone_question": True,
                "confidence_score": 88,
                "question_summary": summary[:100],
                "reply_text": reply
            }

        # Intent 5: Flight Showcase / Video
        showcase_terms = ["nasıl olmuş", "nasil olmus", "ilk uçuşum", "ilk ucusum", "video", "gösteri", "gosteri", "freestyle", "gap", "dive", "flight clip"]
        if any(term in text for term in showcase_terms):
            if is_turkish:
                reply = "Tebrikler, elinize ve emeğinize sağlık! Uçuş hattı ve drone hakimiyeti oldukça akıcı görünüyor. Kırımsız ve keyifli uçuşlar dilerim!\n\n" + clean_sig_tr
            else:
                reply = "Awesome flying! Smooth lines and great throttle control. Keep ripping and fly safe!\n\n" + clean_sig_en
            return {
                "is_drone_question": True,
                "confidence_score": 80,
                "question_summary": summary[:100],
                "reply_text": reply
            }

        # If it doesn't match any drone problem or inquiry, strictly reject
        return {
            "is_drone_question": False,
            "confidence_score": 0,
            "question_summary": summary[:100],
            "reply_text": ""
        }
