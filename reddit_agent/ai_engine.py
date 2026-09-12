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
Aşağıdaki Reddit gönderisini/sorusunu analiz et. Eğer bu bir drone, FPV, uzaktan kumanda, batarya/LiPo, Betaflight, ELRS, lehimleme, TEKNOFEST veya havacılık sorusu ise; kullanıcının sorununu çözen, teknik olarak %100 doğru, samimi ve son derece yardımsever bir Türkçe yanıt hazırla.

HEDEF & REDDİT STRATEJİSİ:
1. ASLA DOĞRUDAN SPAM YAPMA: Yorum içerisinde alakasız bağlantılar veya "bizden satın al" gibi kaba reklamlar KESİNLİKLE YASAKTIR. Teknik çözüm ve mühendislik yaklaşımı her zaman önceliklidir.
2. YÜKSEK DEĞER SAĞLA: Detaylı, faydalı ve güven verici teknik açıklama yap (UART, CRSF, LiPo voltajı, Betaflight portları).
3. ORGANİK KAYNAK GÖSTERME: https://pozitronmarket.com/ linkini veya yerel stok ürünlerini YALNIZCA kullanıcı doğrudan bir ürün temin kaynağı, parça uyumluluğu veya alternatif donanım sorduğunda organik olarak ekle.
4. FİYAT AVANTAJLI YEREL STOK: Fiyat avantajı bulunan yerel stok ürünlerini kullanıcıya tarafsız bir donanım geliştiricisi üslubuyla aktar.
5. TON & DİL: Samimi bir pilot arkadaş gibi ("Hocam", "Dostum", "Pilot arkadaşım" gibi Reddit kültürüne uygun), anlaşılır, adımları maddeler halinde açıklayan temiz Türkçe.
6. İMZA: Yanıtın en altına şu imzayı ekle:
{custom_signature or '*İyi uçuşlar ve kırımsız günler! 🛸*'}
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

        # Verify it has at least some drone/electronics context
        core_terms = ["drone", "dron", "fpv", "quad", "lehim", "motor", "esc", "vtx", "betaflight", "elrs", "dji", "teknofest", "lipo", "batarya", "pervane", "kumanda"]
        has_drone_context = any(term in text for term in core_terms)
        if not has_drone_context:
            return {
                "is_drone_question": False,
                "confidence_score": 0,
                "question_summary": summary[:100],
                "reply_text": ""
            }

        reply = "Selamlar! Sorununu okudum. FPV ve drone sistemlerinde bu durum genellikle lehim kalitesi, doğru voltaj beslemesi (BEC/LiPo) ya da Betaflight / ELRS yazılım yapılandırmalarından kaynaklanabilir.\n\n"
        reply += "Kontrol etmeni önereceğim ilk adımlar:\n"
        reply += "1. **Bağlantılar & Donanım:** Multimetre ile kısa devre (continuity) kontrolü yap. Lehim noktalarının parlak ve temiz olduğundan emin ol.\n"
        reply += "2. **Yazılım & Portlar:** Betaflight Configurator üzerinden Ports sekmesinde doğru UART ve Receiver protokolünü (örn. CRSF / Serial) kontrol et.\n"
        reply += "3. **Güç:** Giriş voltajının parçanın çalışma voltaj aralığıyla (örn. 1S-6S) tam uyumlu olduğunu doğrula.\n\n"
        reply += "Daha detaylı hata kodu, kullandığın parçaların modelleri veya görsel paylaşırsan adım adım çözmeye yardımcı olurum.\n\n"
        reply += custom_signature or "*İyi uçuşlar ve kırımsız günler! 🛸*"

        return {
            "is_drone_question": True,
            "confidence_score": 85,
            "question_summary": summary[:100],
            "reply_text": reply
        }
