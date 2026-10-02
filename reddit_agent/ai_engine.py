import json
import urllib.request
import urllib.error
import re
import os

def is_turkish_text(text: str) -> bool:
    """
    Strictly determines whether the text is written in Turkish.
    Rejects English or other foreign language posts.
    """
    if not text:
        return False

    text_lower = text.lower()

    # 1. Turkish specific characters
    turkish_specific_chars = set("çğıöşü")
    has_turkish_chars = any(c in text_lower for c in turkish_specific_chars)

    # 2. Common Turkish vocabulary / tokens
    turkish_vocab = {
        "ve", "bir", "bu", "da", "de", "mi", "mu", "mı", "mü", "ne", "nasıl", "nasil",
        "için", "icin", "hangi", "tavsiye", "öneri", "oneri", "arıza", "ariza", "lehim",
        "pervane", "uçuş", "ucus", "batarya", "motor", "kumanda", "gözlük", "gozluk",
        "ayar", "ayarı", "ayari", "bağlantı", "baglanti", "arkadaşlar", "arkadaslar",
        "merhaba", "selam", "teşekkürler", "tesekkurler", "yardım", "yardim", "lazım",
        "lazim", "çalışmıyor", "calismiyor", "neden", "niye", "var", "yok", "mıdır",
        "midir", "almak", "alınır", "alinir", "istiyorum", "bakar", "sorun", "sıkıntı",
        "sikinti", "gerek", "bence", "sizce", "fiyat", "bütçe", "butce", "deneyim",
        "önerirsiniz", "onerirsiniz", "gider", "giderilir", "olur", "yaparım", "yaparim",
        "alacağım", "alacagim", "aldım", "aldim", "eder", "ederim", "etmeliyim",
        "kullanıyorum", "kullaniyorum", "takım", "takim", "şunu", "bunu", "hangisi",
        "topluyorum", "toplamak", "başlangıç", "baslangic", "nereden", "nerede"
    }

    # Check English stopwords to reject English posts
    english_stopwords = {
        "the", "and", "this", "that", "with", "from", "for", "what", "which",
        "your", "have", "would", "should", "could", "anyone", "looking", "please",
        "about", "does", "been", "there", "their", "where", "when", "using"
    }

    words = set(re.findall(r'[a-zçğıöşü]+', text_lower))

    tr_matches = words.intersection(turkish_vocab)
    en_matches = words.intersection(english_stopwords)

    # If English stopwords dominate and no Turkish indicators exist, reject
    if len(en_matches) >= 2 and len(tr_matches) == 0 and not has_turkish_chars:
        return False

    # If it contains Turkish specific characters
    if has_turkish_chars:
        if len(en_matches) >= 3 and len(tr_matches) == 0:
            return False
        return True

    # If typed on English keyboard, require at least 2 distinct Turkish words
    if len(tr_matches) >= 2:
        return True

    return False


def format_human_reddit_reply(text: str) -> str:
    """
    Transforms any reply text into a natural human Reddit comment written by
    a Pozitron Market technician/employee on an English keyboard:
    - English keyboard ASCII characters only (ç->c, ğ->g, ı/İ/I->i, ö->o, ş->s, ü->u)
    - Entire text in lowercase (all lowercase)
    - Zero punctuation marks (no commas, periods, question marks, exclamation marks,
      hyphens, colons, quotes, parentheses, brackets, etc.)
    - Clean natural single-spaced words
    """
    if not text:
        return ""

    # 1. Clean markdown links: [label](url) -> label
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Strip standalone URLs or domains (e.g. pozitronmarket.com -> pozitron market)
    text = re.sub(r'https?://(?:www\.)?(\S+)', r'\1', text)
    text = text.replace("pozitronmarket.com", "pozitron market")

    # 2. Map Turkish and accented characters to English keyboard equivalents
    char_map = {
        'ç': 'c', 'Ç': 'c',
        'ğ': 'g', 'Ğ': 'g',
        'ı': 'i', 'İ': 'i', 'I': 'i',
        'ö': 'o', 'Ö': 'o',
        'ş': 's', 'Ş': 's',
        'ü': 'u', 'Ü': 'u',
        'â': 'a', 'Â': 'a',
        'î': 'i', 'Î': 'i',
        'û': 'u', 'Û': 'u'
    }
    for tr_c, en_c in char_map.items():
        text = text.replace(tr_c, en_c)

    # 3. Convert to lowercase
    text = text.lower()

    # 4. Remove formal signatures or bot disclaimers if present
    text = re.sub(r'iyi ucuslar.*pozitron.*', '', text)
    text = re.sub(r'pozitron market\s*\]', '', text)

    # 5. Replace separators (hyphens, slashes, newlines, tabs) with spaces
    text = re.sub(r'[\r\n\t\-/\\]+', ' ', text)

    # 6. Remove all punctuation marks (only keep ASCII a-z, 0-9, and space)
    text = re.sub(r'[^a-z0-9\s]', '', text)

    # 7. Collapse multiple spaces into single space
    text = re.sub(r'\s+', ' ', text).strip()

    return text


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
        Evaluates a Reddit post/comment to determine if it's a genuine Turkish drone/FPV question
        and crafts an authentic, human response in the voice of a Pozitron Market technician.
        """
        full_text = f"{title} {body}".strip()

        # 1. STRICT TURKISH LANGUAGE ENFORCEMENT: Only Turkish drone posts!
        if not is_turkish_text(full_text):
            return {
                "is_drone_question": False,
                "confidence_score": 0,
                "question_summary": title[:100],
                "reply_text": ""
            }

        self._ensure_api_key()
        if not self.api_key:
            return self._fallback_rule_response(title, body, custom_signature)

        prompt = f"""Sen Pozitron Market drone ve FPV atolyesinde calisan tecrubeli bir drone teknisyeni ve FPV pilotusun.
Reddit'te Turk drone ve havacilik topluluklarinda gezinirken karsina cikan kullanici sorusuna gercek bir insan gibi samimi ve yardimsever bir dille cevap veriyorsun.

KESIN VE TAVIZSIZ KURALLAR:
1. SADECE TURKCE DRONE SORULARI: Eger gonderi Turkce degilse veya drone/FPV ile alakali degilse kesinlikle "is_drone_question": false ve "confidence_score": 0 dondur.
2. ASLA YAPAY ZEKA GIBI YAZMA:
   - Kesinlikle yapay zeka oldugunu belli etme ("Merhaba degerli pilot", "Harika bir soru", "Size yardimci olmaktan mutluluk duyarim" gibi robotik kaliplar KESINLIKLE YASAKTIR).
   - Asla maddeler halinde listeleme yapma (1. 2. 3. veya - veya * gibi listelemeler YASAKTIR).
   - Asla kalin yazi (bold), italik veya markdown formati kullanma.
   - Asla emoji kullanma.
   - Asla bot imzasi veya resmi sirket slogani ekleme.
3. POZITRON MARKET CALISANI GIBI YAZ:
   - Atolyede her gun lehim yapan, drone toplayan, ucus yapan gercek bir teknisyen gibi konus.
   - Konuyla ilgili pratik tecrubeni aktar (ornegin "biz atolyede genelde...", "parca veya kumanda lazim olursa pozitron markette stok var oraya da bakabilirsin" gibi dogal sekilde).
4. INGILIZCE KLAVYE VE SIFIR NOKTALAMA:
   - Sadece ingilizce klavye karakterleri kullan (c, g, i, o, s, u). Asla turkce ozel karakter kullanma.
   - Butun cumleyi tamamen KUCUK HARFLERLE yaz, asla buyuk harf kullanma.
   - Kesinlikle hicbir noktalama isareti KULLANMA (nokta, virgul, soru isareti, unlem, tire, kesme isareti, parantez dahil hicbir noktalama isareti olmamali).
5. KISA VE NET OL:
   - 2-4 cumleyi gecmeyen, sorunun tam cevabini veren, arkadasca bir dille yazilmis olsun.

GONDERI BILGILERI:
- Subreddit: r/{subreddit}
- Yazar: u/{author}
- Baslik: {title}
- Icerik/Metin: {body}

CIKTI FORMATI:
SADECE asagidaki JSON formatinda gecerli bir JSON ciktisi uret:
{{
  "is_drone_question": true,
  "confidence_score": 90,
  "question_summary": "sorunun kisa ozeti",
  "reply_text": "ingilizce klavye ile kucuk harflerle ve noktalama isaretsiz gercek insan cevabi"
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
                            is_drone = bool(parsed.get('is_drone_question', True))
                            if not is_drone:
                                return {
                                    "is_drone_question": False,
                                    "confidence_score": 0,
                                    "question_summary": parsed.get('question_summary', title[:100]),
                                    "reply_text": ""
                                }
                            clean_reply = format_human_reddit_reply(parsed.get('reply_text', ''))
                            return {
                                "is_drone_question": True,
                                "confidence_score": int(parsed.get('confidence_score', 85)),
                                "question_summary": parsed.get('question_summary', title[:100]),
                                "reply_text": clean_reply
                            }
            except urllib.error.HTTPError as e:
                continue
            except Exception:
                continue

        return self._fallback_rule_response(title, body, custom_signature)

    def _clean_and_parse_json(self, text: str) -> dict:
        """Strips markdown fences and parses json."""
        if not text:
            return None
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
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass
        return None

    def _fallback_rule_response(self, title: str, body: str, custom_signature: str = "") -> dict:
        """
        Context-aware, intent-classified rule-based response generator.
        Strictly rejects non-Turkish and non-drone posts.
        Formats replies like a real Pozitron Market employee on an English keyboard.
        """
        text = f"{title} {body}".lower()
        summary = title if title else (body[:80] + '...')

        # Strictly reject non-Turkish posts
        if not is_turkish_text(text):
            return {
                "is_drone_question": False,
                "confidence_score": 0,
                "question_summary": summary[:100],
                "reply_text": ""
            }

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

        # Intent 1: Buying / Recommendation Advice
        buying_terms = [
            "almak mantıklı", "alınır mı", "alinir mi", "tavsiye", "öneri", "oneri",
            "hangi drone", "başlangıç", "baslangic", "ilk drone", "bütçe", "butce",
            "fiyat", "tercihiniz", "k arası", "k arasi", "ne kadara", "önerirsiniz", "onerirsiniz"
        ]
        if any(term in text for term in buying_terms):
            reply = "dji mi fpv mi dersen amaca gore degisir sadece manzara cekimi istiyorsan mini serisi iyi ama akrobasi ve ucus hissi istiyorsan once radiomaster pocket gibi bir elrs kumanda alip bilgisayarda velocidrone veya liftoff ile calis kaza masrafindan kurtulursun sonrasinda meteor75 gibi 1s whoop ile baslarsin parca veya kumanda icin pozitron markete de bakabilirsin"
            return {
                "is_drone_question": True,
                "confidence_score": 88,
                "question_summary": summary[:100],
                "reply_text": format_human_reddit_reply(reply)
            }

        # Intent 2: Battery / LiPo Care
        battery_terms = ["lipo", "batarya", "pil", "şarj", "sarj", "voltaj", "1s", "2s", "3s", "4s", "6s", "mah", "c rating", "depolama", "storage"]
        if any(term in text for term in battery_terms):
            reply = "lipo pillerde hucre basina voltaji 35v altina dusurme ideal inis 36v 37v civaridir tam sarj 420v olmali pilleri bir iki gunden fazla tam dolu veya bos birakma sarj aletinden storage moduna alip 385v seviyesine getir sarj ederken de 1c akimi gecme pilin omru uzun olsun"
            return {
                "is_drone_question": True,
                "confidence_score": 88,
                "question_summary": summary[:100],
                "reply_text": format_human_reddit_reply(reply)
            }

        # Intent 3: Regulation / SHGM Flying Rules
        regulation_terms = ["shgm", "mevzuat", "ceza", "izin", "kayıt", "kayit", "yasak", "nerede uçulur", "nerede uculur", "yeşil alan", "yesil alan", "kırmızı alan", "kirmizi alan"]
        if any(term in text for term in regulation_terms):
            reply = "500 gram alti cihazlarda shgm kayit zorunlulugu yok ama kalabalik uzeri veya kirmizi ucus yasakli bolgelerde ucuramazsin max irtifa 120 metre ve cihazi gorus acinda tutman lazim 500 gram ustu ise iha kayit sistemine kayit sart"
            return {
                "is_drone_question": True,
                "confidence_score": 85,
                "question_summary": summary[:100],
                "reply_text": format_human_reddit_reply(reply)
            }

        # Intent 4: Technical Troubleshooting / Hardware / Betaflight
        tech_terms = ["betaflight", "lehim", "uart", "elrs", "crossfire", "esc", "motor", "vtx", "vrx", "bağlantı", "baglanti", "çalışmıyor", "calismiyor", "arızalandı", "arizalandi", "hata", "port", "f405", "f722", "dshot", "alici", "alıcı", "verici", "bind", "binding"]
        if any(term in text for term in tech_terms):
            reply = "betaflight aliciyi veya karti gormuyorsa once impulse rc driver fixer indirip calistir stm32 suruculeri duzelsin kablonun sadece sarj degil data kablosu oldugundan emin ol elrs alicida da ports kisminda serial rx acik olmali ve crsf protokolu secilmeli lehim noktalarinda kisa devre var mi multimetre ile bak"
            return {
                "is_drone_question": True,
                "confidence_score": 88,
                "question_summary": summary[:100],
                "reply_text": format_human_reddit_reply(reply)
            }

        # Intent 5: Flight Showcase / Video
        showcase_terms = ["nasıl olmuş", "nasil olmus", "ilk uçuşum", "ilk ucusum", "video", "gösteri", "gosteri", "freestyle"]
        if any(term in text for term in showcase_terms):
            reply = "eline saglik hatlar ve throttle kontrolu gayet akici olmus kirimsiz ucuslar"
            return {
                "is_drone_question": True,
                "confidence_score": 80,
                "question_summary": summary[:100],
                "reply_text": format_human_reddit_reply(reply)
            }

        # If it doesn't match any drone problem or inquiry, strictly reject
        return {
            "is_drone_question": False,
            "confidence_score": 0,
            "question_summary": summary[:100],
            "reply_text": ""
        }
