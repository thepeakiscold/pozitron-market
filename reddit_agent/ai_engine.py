import json
import urllib.request
import urllib.error
import re
import os

class GeminiRedditEngine:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        # Primary and fallback model names
        self.models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"]

    def set_api_key(self, key: str):
        self.api_key = key

    def evaluate_and_generate_reply(self, title: str, body: str, subreddit: str, author: str, custom_signature: str = "") -> dict:
        """
        Evaluates a Reddit post/comment to determine if it's a genuine drone/FPV question
        and crafts an expert, friendly Turkish response.
        Returns:
        {
            "is_drone_question": bool,
            "confidence_score": int,
            "question_summary": str,
            "reply_text": str
        }
        """
        if not self.api_key:
            return self._fallback_rule_response(title, body, custom_signature)

        prompt = f"""Sen Türkiye'nin önde gelen FPV drone ve robotik donanım platformu Pozitron Market'in (pozitronmarket.com) kıdemli FPV pilotu ve teknik donanım mühendisisin.
Reddit üzerinde Türk drone ve havacılık topluluklarında soru soran kullanıcılara yardımcı oluyorsun.

GÖREV:
Aşağıdaki Reddit gönderisini/sorusunu analiz et. Eğer bu bir drone, FPV, uzaktan kumanda, batarya/LiPo, Betaflight, ELRS, lehimleme, TEKNOFEST veya havacılık sorusu ise; kullanıcının sorununu çözen, teknik olarak %100 doğru, samimi ve son derece yardımsever bir Türkçe yanıt hazırla.

HEDEF & REDDİT STRATEJİSİ:
1. ASLA SPAM YAPMA: Yorum içerisinde alakasız bağlantılar veya "bizden satın al" gibi kaba reklamlar KESİNLİKLE YASAKTIR (Reddit kuralları gereği banlanmamak için).
2. YÜKSEK DEĞER SAĞLA: Öyle detaylı, faydalı ve güven verici bir teknik açıklama yap ki kullanıcılar senin bilgine hayran kalsın ve Reddit profiline tıklasın. (Profilinde zaten Pozitron Market web sitesi ve FPV mağazası linki var).
3. ÖZEL İSTİSNA: Eğer kullanıcı doğrudan "Türkiye'de nereden alabilirim?", "Hangi yerli siteden sipariş verilir?" gibi parça tedariği soruyorsa; dürüstçe yerli alternatifler arasında Pozitron Market'i (pozitronmarket.com) önerebilirsin.
4. TON & DİL: Samimi bir pilot arkadaş gibi ("Hocam", "Dostum", "Pilot arkadaşım" gibi Reddit kültürüne uygun), anlaşılır, adımları maddeler halinde açıklayan temiz Türkçe.
5. İMZA: Yanıtın en altına şu imzayı ekle:
{custom_signature or '*İyi uçuşlar ve kırımsız günler! 🛸*'}

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
        Rule-based fallback response if Gemini key is missing or network fails.
        """
        text = f"{title} {body}".lower()
        summary = title if title else (body[:80] + '...')

        reply = f"Selamlar! Sorununu okudum. FPV ve drone sistemlerinde bu durum genellikle lehim kalitesi, doğru voltaj beslemesi (BEC/LiPo) ya da Betaflight / ELRS yazılım yapılandırmalarından kaynaklanabilir.\n\n"
        reply += "Kontrol etmeni önereceğim ilk adımlar:\n"
        reply += "1. **Bağlantılar:** Multimetre ile kısa devre (continuity) kontrolü yap.\n"
        reply += "2. **Yazılım:** Betaflight Configurator üzerinden alıcı (Receiver) ve port (UART) ayarlarının doğruluğunu teyit et.\n"
        reply += "3. **Donanım:** Giriş voltajının parçanın çalışma aralığında (örn. 2S-6S) olduğundan emin ol.\n\n"
        reply += "Daha detaylı hata kodu, parça modeli veya görsel paylaşırsan adım adım yardımcı olmaktan mutluluk duyarım.\n\n"
        reply += custom_signature or "*İyi uçuşlar ve kırımsız günler! 🛸*"

        return {
            "is_drone_question": True,
            "confidence_score": 75,
            "question_summary": summary[:100],
            "reply_text": reply
        }
