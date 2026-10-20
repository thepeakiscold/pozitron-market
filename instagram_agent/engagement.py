import os
import re
import json
import time
import random
import requests
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional

INTERACTIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'instagram_interactions.json')
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'instagram_config.json')

TARGET_HASHTAGS = [
    'fpvturkey',
    'droneturkey',
    'turkeyfpv',
    'teknofest',
    'teknofestiha',
    'fpvtürkiye',
    'dronetürkiye',
    'turkdrone'
]

TURKISH_CHARS = set('çğıöşüİĞŞÇÖÜ')
TURKISH_KEYWORDS = [
    'türkiye', 'turkiye', 'turk', 'türk', 'turkey', 'teknofest', 'iha', 'siha',
    'kırım', 'kirim', 'uçuş', 'ucus', 'havacılık', 'havacilik',
    'pervane', 'batarya', 'kumanda', 'atölye', 'atolye', 'antrenman',
    'gökyüzü', 'gokyuzu', 'yarış', 'yaris', 'kadraj', 'lehim', 'lehimleme',
    'fırçasız', 'fircasiz', 'takım', 'takim', 'ekip', 'pozitron',
    'istanbul', 'ankara', 'izmir', 'bursa', 'antalya', 'adana', 'konya',
    'kocaeli', 'eskisehir', 'eskişehir', 'trabzon', 'gaziantep', 'samsun', 'kayseri'
]

NON_TURKISH_REJECT_WORDS = [
    'gracias', 'vuelo', 'piloto', 'obrigado', 'voo', 'merci', 'spasibo',
    'bonjour', 'danke', 'amigo', 'hola', 'hermoso', 'bienvenido'
]

FPV_WARM_COMMENTS = [
    "Harika uçuş! Kırımsız ve keyifli uçuşlar dileriz. [Pozitron Market]",
    "Setup ve motor tepkisi çok iyi görünüyor, elinize sağlık!",
    "Tebrikler, çok akıcı ve temiz bir uçuş olmuş! Gökyüzünde başarılar.",
    "Süper akıcı freestyle hatları, keyifle izledik! Kırımsız günler dileriz.",
    "Görüntü netliği ve PID ayarları şahane oturmuş! Pozitron Market FPV ekibinden selamlar.",
    "Elinize sağlık, kırımsız ve bol irtifalı uçuşlar dileriz!",
    "Çok temiz bir build ve uçuş performansı! Tebrikler.",
    "Drone hakimiyeti harika, gökyüzünde bol kırımsız uçuşlar!",
    "Renkler ve hatlar müthiş! İyi uçuşlar pilot.",
    "Harika video! Pozitron FPV ailesi olarak selamlar ve kırımsız günler dileriz."
]

class InstagramEngagementEngine:
    def __init__(self, session_cookies: dict = None, csrf_token: str = None, gemini_api_key: str = None):
        self.session_cookies = session_cookies or {}
        self.csrf_token = csrf_token or ''
        self.gemini_api_key = gemini_api_key or os.environ.get('GEMINI_API_KEY', '')
        self.max_daily = 10
        # Anti-rate-limit pacing: never burst-follow. Drip a few follows per run
        # with human-like 45-120s gaps so Instagram's follow action-block
        # ("feedback_required") is not triggered.
        try:
            self.per_run_follow_cap = int(os.environ.get('IG_PER_RUN_FOLLOW_CAP', '4'))
        except Exception:
            self.per_run_follow_cap = 4
        try:
            self.follow_delay_range = (
                float(os.environ.get('IG_FOLLOW_MIN_DELAY', '45')),
                float(os.environ.get('IG_FOLLOW_MAX_DELAY', '120')),
            )
        except Exception:
            self.follow_delay_range = (45.0, 120.0)
        # Likes are lighter than follows; drip a larger batch per run with short
        # human-like 5-12s gaps to keep the daily 10-like quota natural.
        try:
            self.per_run_like_cap = int(os.environ.get('IG_PER_RUN_LIKE_CAP', '6'))
        except Exception:
            self.per_run_like_cap = 6
        try:
            self.like_delay_range = (
                float(os.environ.get('IG_LIKE_MIN_DELAY', '5')),
                float(os.environ.get('IG_LIKE_MAX_DELAY', '12')),
            )
        except Exception:
            self.like_delay_range = (5.0, 12.0)
        self._web_tokens = None
        self._load_gemini_key_if_needed()
        self._load_session_if_needed()

    def _load_gemini_key_if_needed(self):
        if not self.gemini_api_key:
            try:
                import sqlite3
                db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pozitron.db')
                conn = sqlite3.connect(db_path)
                c = conn.cursor()
                c.execute("SELECT gemini_api_key FROM instagram_agent_config WHERE id = 1")
                row = c.fetchone()
                if row and row[0]:
                    self.gemini_api_key = row[0].strip()
                if not self.gemini_api_key:
                    c.execute("SELECT gemini_api_key FROM reddit_agent_config WHERE id = 1")
                    row2 = c.fetchone()
                    if row2 and row2[0]:
                        self.gemini_api_key = row2[0].strip()
                conn.close()
            except Exception:
                pass

    def _load_session_if_needed(self):
        """Loads Chrome session or ENV session if not provided."""
        if not self.session_cookies:
            # 1. Try ENV
            env_cookies_json = os.environ.get('INSTAGRAM_COOKIES_JSON')
            env_sessionid = os.environ.get('INSTAGRAM_SESSIONID')
            env_csrftoken = os.environ.get('INSTAGRAM_CSRFTOKEN')

            if env_cookies_json:
                try:
                    self.session_cookies = json.loads(env_cookies_json)
                    self.csrf_token = self.session_cookies.get('csrftoken', '')
                except Exception:
                    pass

            if not self.session_cookies and env_sessionid:
                self.session_cookies = {
                    'sessionid': env_sessionid,
                    'csrftoken': env_csrftoken or ''
                }
                self.csrf_token = env_csrftoken or ''

            # 2. Try Chrome extraction locally
            if not self.session_cookies or not self.session_cookies.get('sessionid'):
                try:
                    from .chrome_session import extract_chrome_instagram_cookies
                    info = extract_chrome_instagram_cookies()
                    if info.get('success') and info.get('cookies'):
                        self.session_cookies = info['cookies']
                        self.csrf_token = info.get('csrftoken', '')
                except Exception:
                    pass

        # Strict ASCII sanitization: strip any non-printable or >127 chars that crash requests latin-1 encoding
        if self.session_cookies:
            clean_cookies = {}
            for k, v in self.session_cookies.items():
                if isinstance(v, str):
                    clean_v = ''.join(c for c in v if 32 <= ord(c) < 127).strip()
                    if clean_v:
                        clean_cookies[k] = clean_v
                else:
                    clean_cookies[k] = str(v)
            self.session_cookies = clean_cookies
        if self.csrf_token:
            self.csrf_token = ''.join(c for c in str(self.csrf_token) if 32 <= ord(c) < 127).strip()

    def _get_headers(self, referer: str = 'https://www.instagram.com/') -> dict:
        raw_csrf = self.csrf_token or (self.session_cookies.get('csrftoken', '') if self.session_cookies else '')
        csrf = ''.join(c for c in str(raw_csrf) if 32 <= ord(c) < 127).strip()
        return {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
            'X-CSRFToken': csrf,
            'X-IG-App-ID': '936619743392459',
            'X-ASBD-ID': '129477',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://www.instagram.com',
            'Referer': referer,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

    def load_interactions_data(self) -> dict:
        today_str = date.today().isoformat()
        default_data = {
            "today_date": today_str,
            "today_follows_count": 0,
            "today_comments_count": 0,
            "today_likes_count": 0,
            "max_daily_limit": self.max_daily,
            "followed_user_ids": [],
            "commented_media_ids": [],
            "liked_media_ids": [],
            "history": []
        }

        if os.path.exists(INTERACTIONS_FILE):
            try:
                with open(INTERACTIONS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Reset counters if date changed
                if data.get('today_date') != today_str:
                    data['today_date'] = today_str
                    data['today_follows_count'] = 0
                    data['today_comments_count'] = 0
                    data['today_likes_count'] = 0
                # Backfill newer keys for older interaction files
                data.setdefault('today_likes_count', 0)
                data.setdefault('liked_media_ids', [])
                return data
            except Exception:
                return default_data
        return default_data

    def save_interactions_data(self, data: dict):
        try:
            os.makedirs(os.path.dirname(INTERACTIONS_FILE), exist_ok=True)
            with open(INTERACTIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Interactions save error: {e}")

    def is_turkish_drone_profile(self, username: str, caption: str = '') -> bool:
        """
        Validates whether a user / post belongs to the Turkish drone & FPV community.
        Only Turkish pilots, TEKNOFEST UAV teams, and domestic hobbyists are engaged.
        """
        combined = f"{username} {caption}".lower()

        # 1. Reject foreign language posts (Spanish, Portuguese, Russian, French, etc.)
        for bad_word in NON_TURKISH_REJECT_WORDS:
            if bad_word in combined:
                return False

        # 2. Check for Turkish unique characters (ç, ğ, ı, ö, ş, ü)
        has_tr_char = any(ch in combined for ch in TURKISH_CHARS)

        # 3. Check for Turkish drone/location keywords
        has_tr_keyword = any(kw in combined for kw in TURKISH_KEYWORDS)

        # 4. Check for Turkish username markers (word boundary / explicit prefixes/suffixes)
        u_lower = username.lower()
        has_tr_prefix_or_suffix = (
            u_lower.endswith(('_tr', '.tr')) or
            u_lower.startswith('tr_') or
            '_tr_' in u_lower or
            '.tr.' in u_lower
        )
        has_tr_user = has_tr_prefix_or_suffix or any(marker in u_lower for marker in ['turk', 'turkey', 'iha', 'teknofest', 'havacilik', 'ucus', 'fpvturk'])

        return has_tr_char or has_tr_keyword or has_tr_user

    def generate_friendly_comment(self, username: str, caption: str = '') -> str:
        """Generates a warm, supportive FPV comment strictly matched to the post context."""
        cap_lower = caption.lower()
        self._load_gemini_key_if_needed()

        prompt = f"""Bir Türk FPV drone pilotunun Instagram gönderisine Pozitron Market FPV ekibi olarak samimi, motive edici, nazik TEK CÜMLELİK kısa bir yorum yaz.
Pilot Kullanıcı Adı: @{username}
Gönderi Metni: {caption[:300]}

KRİTİK UYARI VE İÇERİK UYUMU:
1. GÖNDERİ KONUSUNA TAM UYUMLU OL:
   - Eğer gönderide kırım, kaza, yanan motor/ESC veya hasar varsa: Geçmiş olsun dile, moral ver ("Büyük geçmiş olsun, en kısa sürede göklere dönmen dileğiyle"). ASLA kaza gönderisine "Harika uçuş!" deme!
   - Eğer gönderi yeni bir drone toplama/build/lehimleme ise: Temiz işçiliği ve build kalitesini öv ("Elinize sağlık, çok temiz bir build olmuş, ilk uçuşta başarılar").
   - Eğer gönderi yarış/Teknofest ise: Parkurda ve yarışta başarılar dile.
   - Eğer gönderi freestyle veya akrobasi uçuşu ise: Akıcı hatları ve kontrolü tebrik et.
2. 1 cümle olsun, maksimum 15 kelime.
3. KESİNLİKLE HİÇBİR EMOJİ KULLANMA.
4. Sadece yorum metnini döndür."""

        # 1. Unified LLM (DeepSeek V4.1 Flash High via OpenCode/Evren)
        try:
            from llm_client import get_llm
            llm = get_llm()
            if llm.is_configured():
                text = llm.generate_text(prompt, max_tokens=1024, temperature=0.6)
                import re as _re
                text = (text or "").strip().strip('"')
                text = _re.sub(r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]', '', text).strip()
                if text and len(text) < 160:
                    return text
        except Exception:
            pass

        # 2. Legacy Gemini fallback
        if self.gemini_api_key:
            models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            import re
            for m in models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.gemini_api_key}"
                    res = requests.post(url, json=payload, timeout=6)
                    if res.status_code == 200:
                        text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip().strip('"')
                        text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]', '', text).strip()
                        if text and len(text) < 120:
                            return text
                except Exception:
                    continue

        # Intelligent context-aware rule-based fallback
        crash_words = ['kırım', 'kirim', 'kırdım', 'kirdim', 'yandı', 'yandi', 'hasar', 'patladı', 'patladi', 'çöp', 'cop', 'crash', 'geçmiş olsun']
        if any(w in cap_lower for w in crash_words):
            return random.choice([
                "Büyük geçmiş olsun pilot, FPV'nin doğasında kırım var. En kısa sürede göklere dönmen dileğiyle!",
                "Geçmiş olsun, toparlayıp en kısa sürede tekrar gökyüzüne dönmeniz dileğiyle.",
                "Geçmiş olsun dostum, kırımsız günlere en kısa sürede dönüş dileriz."
            ])

        build_words = ['build', 'lehim', 'lehimleme', 'toplama', 'f405', 'f722', 'frame', 'atölye', 'atolye', 'setup', 'motor montaj']
        if any(w in cap_lower for w in build_words):
            return random.choice([
                "Elinize sağlık, lehimler ve kablolama gayet temiz görünüyor. İlk uçuşta başarılar!",
                "Çok temiz ve özenli bir build olmuş, elinize sağlık! Maiden uçuşunda başarılar.",
                "Build çok şık ve düzenli duruyor, gökyüzünde kırımsız uçuşlar dileriz!"
            ])

        race_words = ['yarış', 'yaris', 'teknofest', 'turnuva', 'sıralama', 'siralama', 'track', 'gate']
        if any(w in cap_lower for w in race_words):
            return random.choice([
                "Tebrikler ve başarılar! Parkurda bol podyumlu ve kırımsız yarışlar dileriz.",
                "Tebrikler pilot, yarış parkurunda başarılarının devamını dileriz!"
            ])

        flight_words = ['freestyle', 'uçuş', 'ucus', 'dive', 'gap', 'akrobasi', 'kadraj', 'gökyüzü']
        if any(w in cap_lower for w in flight_words):
            return random.choice([
                "Harika uçuş! Akıcı hatlar ve temiz kontrol, kırımsız ve keyifli uçuşlar dileriz.",
                "Setup ve motor tepkisi çok iyi görünüyor, elinize sağlık!",
                "Tebrikler, çok akıcı ve temiz bir uçuş olmuş! Gökyüzünde başarılar.",
                "Süper akıcı freestyle hatları, keyifle izledik! Kırımsız günler dileriz."
            ])

        return random.choice([
            "Elinize sağlık, kırımsız ve bol irtifalı keyifli uçuşlar dileriz!",
            "Tebrikler, gökyüzünde bol kırımsız ve keyifli uçuşlar dileriz."
        ])

    def _fetch_web_tokens(self) -> dict:
        """
        Fetches the LSD token and rollout hash (X-Instagram-AJAX) that the current
        Instagram web app sends with every GraphQL mutation. Without these headers
        Instagram answers /graphql/query with the HTML app shell instead of JSON,
        which silently breaks every follow mutation.
        """
        tokens = {"lsd": "", "rollout_hash": ""}
        if not self.session_cookies:
            return tokens
        try:
            ua = self._get_headers().get('User-Agent')
            res = requests.get(
                'https://www.instagram.com/',
                headers={'User-Agent': ua},
                cookies=self.session_cookies,
                timeout=12
            )
            if res.status_code == 200:
                m_lsd = re.search(r'"LSD",\[\],\{"token":"(.*?)"\}', res.text)
                if m_lsd:
                    tokens["lsd"] = m_lsd.group(1)
                m_roll = re.search(r'rollout_hash":"(\d+)"', res.text)
                if m_roll:
                    tokens["rollout_hash"] = m_roll.group(1)
        except Exception:
            pass
        return tokens

    def follow_user(self, user_id: str, username: str) -> dict:
        """
        Sends a follow request to an Instagram user via the web GraphQL mutation.

        Returns a diagnostic dictionary so callers (and the QA Sentinel agent) can
        distinguish a real follow, a silent HTML/non-JSON response, and an Instagram
        action-block ("feedback_required" / "Try Again Later"):
            {"success": bool, "status_code": int, "error": str|None,
             "message": str, "blocked": bool}
        """
        detail = {"success": False, "status_code": 0, "error": None, "message": "", "blocked": False}

        if not self.session_cookies or not self.session_cookies.get('sessionid'):
            detail["error"] = "no_session"
            detail["message"] = "Instagram oturum cerezi (sessionid) bulunamadi."
            return detail

        if self._web_tokens is None:
            self._web_tokens = self._fetch_web_tokens()
        tokens = self._web_tokens or {}

        headers = self._get_headers(referer=f"https://www.instagram.com/{username}/")
        if tokens.get("rollout_hash"):
            headers["X-Instagram-AJAX"] = tokens["rollout_hash"]
        if tokens.get("lsd"):
            headers["X-FB-LSD"] = tokens["lsd"]
        headers["X-IG-WWW-Claim"] = "0"
        if self.session_cookies.get("mid"):
            headers["X-Mid"] = self.session_cookies["mid"]
        if self.session_cookies.get("ig_did"):
            headers["X-Web-Device-Id"] = self.session_cookies["ig_did"]

        url = 'https://www.instagram.com/graphql/query'
        payload = {
            'doc_id': '27767812149509802',
            'variables': json.dumps({
                'target_user_id': str(user_id),
                'data': {
                    'include_follow_friction_check': True
                }
            }),
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'usePolarisFollowUserFollowMutation',
            'server_timestamps': 'true'
        }
        if tokens.get("lsd"):
            payload['lsd'] = tokens["lsd"]

        try:
            res = requests.post(url, headers=headers, cookies=self.session_cookies, data=payload, timeout=12)
            detail["status_code"] = res.status_code

            content_type = (res.headers.get('content-type') or '').lower()
            if 'json' not in content_type:
                detail["error"] = "non_json_response"
                detail["message"] = "Instagram JSON yerine HTML uygulama kabugu dondurdu (istek API olarak kabul edilmedi)."
                return detail

            try:
                body = res.json()
            except Exception as jerr:
                detail["error"] = "json_parse_error"
                detail["message"] = str(jerr)[:200]
                return detail

            if res.status_code != 200:
                msg = str(body.get('message') or body.get('error') or '')
                feedback_msg = str(body.get('feedback_message') or '')
                detail["message"] = (feedback_msg or msg)[:300]
                if (msg == 'feedback_required' or body.get('spam') is True
                        or 'limit how often' in feedback_msg.lower()
                        or body.get('feedback_title')):
                    detail["error"] = "feedback_required"
                    detail["blocked"] = True
                else:
                    detail["error"] = f"http_{res.status_code}"
                return detail

            friendship = (body.get('data', {}) or {}).get('xdt_create_friendship', {}).get('friendship_status', {}) or {}
            if friendship.get('following') is True or friendship.get('outgoing_request') is True:
                detail["success"] = True
                return detail

            detail["error"] = "not_following"
            detail["message"] = json.dumps(body.get('data', {}), ensure_ascii=False)[:200]
            return detail
        except Exception as e:
            detail["error"] = "exception"
            detail["message"] = str(e)[:200]
            print(f"Follow error for {username}: {e}")
            return detail

    def diagnose_follow_capability(self) -> dict:
        """
        Performs a single, idempotent follow probe against an account the bot already
        follows (no real side effect) to capture the live Instagram response, then
        persists the diagnostic state into data/instagram_interactions.json.
        Throttled to at most once every 12 hours. Used by the QA Sentinel agent.
        """
        data = self.load_interactions_data()
        diag = data.get('follow_diagnostics') or {}

        last_probe = diag.get('last_follow_probe_at')
        if last_probe:
            try:
                if (datetime.now() - datetime.fromisoformat(last_probe)).total_seconds() < 12 * 3600:
                    return diag
            except Exception:
                pass

        my_id = str(self.session_cookies.get('ds_user_id', '')) if self.session_cookies else ''
        target_id = ''
        for uid in reversed(data.get('followed_user_ids', [])):
            if uid and str(uid) != my_id:
                target_id = str(uid)
                break
        if not target_id:
            target_id = my_id or '0'

        res = self.follow_user(target_id, 'pozitron_diagnostic')
        now_iso = datetime.now().isoformat()
        diag['last_follow_probe_at'] = now_iso
        diag['last_follow_attempt_at'] = now_iso
        diag['last_follow_error'] = res.get('error')
        diag['last_follow_message'] = res.get('message')
        diag['last_follow_status_code'] = res.get('status_code')
        diag['follow_blocked'] = bool(res.get('blocked'))
        if res.get('blocked') and not diag.get('follow_blocked_until'):
            diag['follow_blocked_until'] = (datetime.now() + timedelta(hours=24)).isoformat()
        data['follow_diagnostics'] = diag
        self.save_interactions_data(data)
        return diag

    def post_comment(self, media_id: str, media_code: str, comment_text: str) -> bool:
        """Adds a comment to an Instagram media post."""
        if not self.session_cookies or not self.session_cookies.get('sessionid'):
            return False

        # Clean numeric media ID
        clean_id = media_id.split('_')[0] if '_' in str(media_id) else str(media_id)
        url = f"https://www.instagram.com/api/v1/web/comments/{clean_id}/add/"
        headers = self._get_headers(referer=f"https://www.instagram.com/p/{media_code}/")
        payload = {'comment_text': comment_text}

        try:
            res = requests.post(url, headers=headers, cookies=self.session_cookies, data=payload, timeout=12)
            if res.status_code == 200:
                body = res.json()
                return body.get('status') == 'ok' or bool(body.get('id'))
        except Exception as e:
            print(f"Comment error on {media_code}: {e}")
        return False

    def like_media(self, media_id: str, media_code: str) -> dict:
        """
        Likes an Instagram media via the web API.

        Returns a diagnostic dictionary so callers can distinguish a real like,
        a silent HTML/non-JSON response, and an Instagram action-block
        ("feedback_required" / "Try Again Later"):
            {"success": bool, "status_code": int, "error": str|None,
             "message": str, "blocked": bool}
        """
        detail = {"success": False, "status_code": 0, "error": None, "message": "", "blocked": False}

        if not self.session_cookies or not self.session_cookies.get('sessionid'):
            detail["error"] = "no_session"
            detail["message"] = "Instagram oturum cerezi (sessionid) bulunamadi."
            return detail

        # Clean numeric media ID (strip any "userid_mediaid" composite form)
        clean_id = media_id.split('_')[0] if '_' in str(media_id) else str(media_id)
        url = f"https://www.instagram.com/api/v1/web/likes/{clean_id}/like/"
        headers = self._get_headers(referer=f"https://www.instagram.com/p/{media_code}/")
        headers["X-IG-WWW-Claim"] = "0"

        try:
            res = requests.post(url, headers=headers, cookies=self.session_cookies, data={}, timeout=12)
            detail["status_code"] = res.status_code

            content_type = (res.headers.get('content-type') or '').lower()
            if 'json' not in content_type:
                detail["error"] = "non_json_response"
                detail["message"] = "Instagram JSON yerine HTML uygulama kabugu dondurdu (istek API olarak kabul edilmedi)."
                return detail

            try:
                body = res.json()
            except Exception as jerr:
                detail["error"] = "json_parse_error"
                detail["message"] = str(jerr)[:200]
                return detail

            if res.status_code != 200:
                msg = str(body.get('message') or body.get('error') or '')
                feedback_msg = str(body.get('feedback_message') or '')
                detail["message"] = (feedback_msg or msg)[:300]
                if (msg == 'feedback_required' or body.get('spam') is True
                        or 'limit how often' in feedback_msg.lower()
                        or body.get('feedback_title')):
                    detail["error"] = "feedback_required"
                    detail["blocked"] = True
                else:
                    detail["error"] = f"http_{res.status_code}"
                return detail

            if body.get('status') == 'ok' or body.get('id'):
                detail["success"] = True
                return detail

            detail["error"] = "not_liked"
            detail["message"] = json.dumps(body, ensure_ascii=False)[:200]
            return detail
        except Exception as e:
            detail["error"] = "exception"
            detail["message"] = str(e)[:200]
            print(f"Like error on {media_code}: {e}")
            return detail

    def search_recent_drone_posts(self, target_tag: str = 'fpvturkey') -> List[Dict]:
        """Finds recent posts from pilots under drone hashtags."""
        if not self.session_cookies or not self.session_cookies.get('sessionid'):
            return []

        url = f"https://www.instagram.com/api/v1/tags/web_info/?tag_name={target_tag}"
        headers = self._get_headers(referer=f"https://www.instagram.com/explore/tags/{target_tag}/")

        posts = []
        try:
            res = requests.get(url, headers=headers, cookies=self.session_cookies, timeout=12)
            if res.status_code == 200:
                data = res.json().get('data', {})
                # Look inside sections (both top and recent)
                for group_key in ['top', 'recent']:
                    sections = data.get(group_key, {}).get('sections', [])
                    for sec in sections:
                        for item in sec.get('layout_content', {}).get('medias', []):
                            m = item.get('media', {})
                            u = m.get('user', {})
                            if u and m.get('id'):
                                posts.append({
                                    'media_id': str(m.get('id')),
                                    'media_code': m.get('code', ''),
                                    'user_id': str(u.get('pk')),
                                    'username': u.get('username', ''),
                                    'caption': (m.get('caption') or {}).get('text', ''),
                                    'is_private': bool(u.get('is_private', False))
                                })
        except Exception as e:
            print(f"Tag search error for #{target_tag}: {e}")
        return posts

    def run_daily_drone_engagement(self, target_count: int = 10) -> dict:
        """
        Engages with drone community: follows up to target_count (max 10) drone pilots
        and leaves friendly, supportive comments on their posts.
        """
        self._load_session_if_needed()
        if not self.session_cookies or not self.session_cookies.get('sessionid'):
            return {
                "success": False,
                "error": "Instagram Chrome oturumu veya INSTAGRAM_SESSIONID bulunamadı. Lütfen oturum çerezlerini bağlayın."
            }

        data = self.load_interactions_data()

        follow_diag = data.get('follow_diagnostics') or {}
        follows_blocked = False
        
        follows_needed = max(0, min(self.max_daily, target_count) - data.get('today_follows_count', 0))
        comments_needed = max(0, min(self.max_daily, target_count) - data.get('today_comments_count', 0))
        likes_needed = max(0, min(self.max_daily, target_count) - data.get('today_likes_count', 0))

        # Anti-burst: cap follows per run so the daily quota drips across several cycles.
        follows_needed = min(follows_needed, max(1, self.per_run_follow_cap))
        likes_needed = min(likes_needed, max(1, self.per_run_like_cap))

        # Respect any active Instagram follow action-block cooldown. Instagram returns
        # "feedback_required" ("Try Again Later") for follow mutations while the account
        # is rate-limited, so we must not keep hammering the endpoint.
        blocked_until_str = follow_diag.get('follow_blocked_until')
        if blocked_until_str and follows_needed > 0:
            try:
                if datetime.now() < datetime.fromisoformat(blocked_until_str):
                    follows_blocked = True
                    follows_needed = 0
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [TAKIP BEKLEMEDE] Takip aksiyonu Instagram tarafindan kisitli "
                          f"(son hata: {follow_diag.get('last_follow_error')}). Tekrar deneme zamani: {blocked_until_str}")
            except Exception:
                pass

        # Respect any active Instagram like action-block cooldown (likes are lighter
        # than follows but Instagram can still rate-limit them).
        like_diag = data.get('like_diagnostics') or {}
        likes_blocked = False
        like_blocked_until_str = like_diag.get('like_blocked_until')
        if like_blocked_until_str and likes_needed > 0:
            try:
                if datetime.now() < datetime.fromisoformat(like_blocked_until_str):
                    likes_blocked = True
                    likes_needed = 0
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [BEGENI BEKLEMEDE] Begeni aksiyonu Instagram tarafindan kisitli "
                          f"(son hata: {like_diag.get('last_like_error')}). Tekrar deneme zamani: {like_blocked_until_str}")
            except Exception:
                pass

        if follows_needed == 0 and comments_needed == 0 and likes_needed == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [KOTA DOLU] Bugünün 10 takip, 10 yorum ve 10 beğeni kotası zaten tamamlandı.")
            return {
                "success": True,
                "completed_already": True,
                "today_follows": data.get('today_follows_count', 0),
                "today_comments": data.get('today_comments_count', 0),
                "today_likes": data.get('today_likes_count', 0),
                "message": "Bugünkü 10 takip, 10 yorum ve 10 beğeni kotası dolu."
            }

        followed_ids = set(data.get('followed_user_ids', []))
        commented_media_ids = set(data.get('commented_media_ids', []))
        liked_media_ids = set(data.get('liked_media_ids', []))

        # Randomize hashtag order for natural engagement
        shuffled_tags = list(TARGET_HASHTAGS)
        random.shuffle(shuffled_tags)

        new_follows = 0
        new_comments = 0
        new_likes = 0
        follow_attempts = 0
        follow_failures = 0
        liked_media_attempts = 0
        interacted_pilots = []

        my_user_id = str(self.session_cookies.get('ds_user_id', '30375317594'))

        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ETKİLEŞİM BAŞLADI] Drone topluluğu etkileşim döngüsü başladı. Hedef: {follows_needed} takip, {comments_needed} yorum, {likes_needed} beğeni.")

        for tag in shuffled_tags:
            if follows_needed <= 0 and comments_needed <= 0 and likes_needed <= 0:
                break

            candidates = self.search_recent_drone_posts(tag)
            for c in candidates:
                u_id = c['user_id']
                u_name = c['username']
                m_id = c['media_id']
                m_code = c['media_code']

                # Avoid interacting with ourselves or duplicate accounts
                if u_id == my_user_id or u_name.lower() in ('pozitronmarket', 'thepeakiscold'):
                    continue
                if c.get('is_private'):
                    continue

                # Strictly verify Turkish drone community profile
                if not self.is_turkish_drone_profile(u_name, c.get('caption', '')):
                    continue

                did_something = False

                # 1. Follow Pilot
                if follows_needed > 0 and not follows_blocked and u_id not in followed_ids:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [PILOT TAKIP] Pilot takip ediliyor: @{u_name} (ID: {u_id})")
                    follow_attempts += 1
                    f_res = self.follow_user(u_id, u_name)
                    if f_res.get('success'):
                        followed_ids.add(u_id)
                        data['followed_user_ids'].append(u_id)
                        data['today_follows_count'] += 1
                        new_follows += 1
                        follows_needed -= 1
                        follow_failures = 0
                        did_something = True
                        follow_diag['follow_failure_streak'] = 0
                        follow_diag['follow_blocked'] = False
                        follow_diag['follow_blocked_until'] = None
                        data['history'].append({
                            "type": "follow",
                            "username": u_name,
                            "user_id": u_id,
                            "timestamp": datetime.now().isoformat(),
                            "status": "success"
                        })
                    else:
                        follow_failures += 1
                        err_code = f_res.get('error')
                        err_msg = f_res.get('message')
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [TAKIP HATASI] @{u_name} takip edilemedi "
                              f"(error={err_code}, status={f_res.get('status_code')}): {err_msg}")
                        follow_diag['last_follow_attempt_at'] = datetime.now().isoformat()
                        follow_diag['last_follow_error'] = err_code
                        follow_diag['last_follow_message'] = err_msg
                        follow_diag['last_follow_status_code'] = f_res.get('status_code')
                        follow_diag['follow_failure_streak'] = follow_diag.get('follow_failure_streak', 0) + 1
                        data['history'].append({
                            "type": "follow",
                            "username": u_name,
                            "user_id": u_id,
                            "timestamp": datetime.now().isoformat(),
                            "status": "failed",
                            "error": err_code,
                            "message": err_msg
                        })
                        if f_res.get('blocked'):
                            # Instagram action-block: stop follow attempts for a full day
                            follow_diag['follow_blocked'] = True
                            follow_diag['follow_blocked_until'] = (datetime.now() + timedelta(hours=24)).isoformat()
                            follows_blocked = True
                            follows_needed = 0
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] [TAKIP ENGELLENDI] Instagram takip aksiyonunu kisitladi "
                                  f"(feedback_required). 24 saat boyunca takip denemesi yapilmayacak.")
                        elif follow_failures >= 3:
                            # Repeated non-block failures: back off so we do not spam the API or history
                            follow_diag['follow_blocked'] = True
                            follow_diag['follow_blocked_until'] = (datetime.now() + timedelta(hours=6)).isoformat()
                            follows_blocked = True
                            follows_needed = 0
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] [TAKIP GERI CEKILME] Ust uste 3 takip hatasi alindi, "
                                  f"6 saat boyunca takip denemesi durduruldu.")
                        data['follow_diagnostics'] = follow_diag
                        self.save_interactions_data(data)
                    time.sleep(random.uniform(*self.follow_delay_range))

                # 2. Leave Encouraging Drone Comment
                if comments_needed > 0 and m_id not in commented_media_ids:
                    comment_text = self.generate_friendly_comment(u_name, c.get('caption', ''))
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [YORUM PAYLASIMI] Gonderiye yorum yapiliyor (@{u_name} / https://instagram.com/p/{m_code}/): \"{comment_text}\"")
                    ok = self.post_comment(m_id, m_code, comment_text)
                    if ok:
                        commented_media_ids.add(m_id)
                        data['commented_media_ids'].append(m_id)
                        data['today_comments_count'] += 1
                        new_comments += 1
                        comments_needed -= 1
                        did_something = True
                        data['history'].append({
                            "type": "comment",
                            "username": u_name,
                            "user_id": u_id,
                            "media_id": m_id,
                            "media_code": m_code,
                            "comment": comment_text,
                            "timestamp": datetime.now().isoformat(),
                            "status": "success"
                        })
                    time.sleep(random.uniform(8, 14))

                # 3. Like the Pilot's Post (daily 10-like quota, like the comments)
                if likes_needed > 0 and not likes_blocked and m_id not in liked_media_ids:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [BEGENI] Gonderi begeniliyor (@{u_name} / https://instagram.com/p/{m_code}/)")
                    liked_media_attempts += 1
                    l_res = self.like_media(m_id, m_code)
                    if l_res.get('success'):
                        liked_media_ids.add(m_id)
                        data['liked_media_ids'].append(m_id)
                        data['today_likes_count'] += 1
                        new_likes += 1
                        likes_needed -= 1
                        did_something = True
                        like_diag['like_blocked'] = False
                        like_diag['like_blocked_until'] = None
                        like_diag['like_failure_streak'] = 0
                        data['history'].append({
                            "type": "like",
                            "username": u_name,
                            "user_id": u_id,
                            "media_id": m_id,
                            "media_code": m_code,
                            "timestamp": datetime.now().isoformat(),
                            "status": "success"
                        })
                    else:
                        err_code = l_res.get('error')
                        err_msg = l_res.get('message')
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] [BEGENI HATASI] @{u_name} gonderisi begenilemedi "
                              f"(error={err_code}, status={l_res.get('status_code')}): {err_msg}")
                        like_diag['last_like_attempt_at'] = datetime.now().isoformat()
                        like_diag['last_like_error'] = err_code
                        like_diag['last_like_message'] = err_msg
                        like_diag['last_like_status_code'] = l_res.get('status_code')
                        like_diag['like_failure_streak'] = like_diag.get('like_failure_streak', 0) + 1
                        data['history'].append({
                            "type": "like",
                            "username": u_name,
                            "user_id": u_id,
                            "media_id": m_id,
                            "media_code": m_code,
                            "timestamp": datetime.now().isoformat(),
                            "status": "failed",
                            "error": err_code,
                            "message": err_msg
                        })
                        if l_res.get('blocked'):
                            like_diag['like_blocked'] = True
                            like_diag['like_blocked_until'] = (datetime.now() + timedelta(hours=24)).isoformat()
                            likes_blocked = True
                            likes_needed = 0
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] [BEGENI ENGELLENDI] Instagram begeni aksiyonunu kisitladi "
                                  f"(feedback_required). 24 saat boyunca begeni denemesi yapilmayacak.")
                        elif like_diag.get('like_failure_streak', 0) >= 3:
                            like_diag['like_blocked'] = True
                            like_diag['like_blocked_until'] = (datetime.now() + timedelta(hours=6)).isoformat()
                            likes_blocked = True
                            likes_needed = 0
                            print(f"[{datetime.now().strftime('%H:%M:%S')}] [BEGENI GERI CEKILME] Ust uste 3 begeni hatasi alindi, "
                                  f"6 saat boyunca begeni denemesi durduruldu.")
                        data['like_diagnostics'] = like_diag
                        self.save_interactions_data(data)
                    time.sleep(random.uniform(*self.like_delay_range))

                if did_something:
                    interacted_pilots.append({
                        "username": u_name,
                        "post_url": f"https://www.instagram.com/p/{m_code}/"
                    })
                    # Delay between different accounts (natural human pacing)
                    time.sleep(random.uniform(8, 16))

                if follows_needed <= 0 and comments_needed <= 0 and likes_needed <= 0:
                    break

        follow_diag['follow_diagnostics_updated_at'] = datetime.now().isoformat()
        data['follow_diagnostics'] = follow_diag
        like_diag['like_diagnostics_updated_at'] = datetime.now().isoformat()
        data['like_diagnostics'] = like_diag
        self.save_interactions_data(data)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [TAMAMLANDI] Etkilesim tamamlandi: "
              f"+{new_follows} takip ({follow_attempts} deneme), +{new_comments} yorum, +{new_likes} begeni.")

        return {
            "success": True,
            "new_follows": new_follows,
            "new_comments": new_comments,
            "new_likes": new_likes,
            "follow_attempts": follow_attempts,
            "follow_failed": max(0, follow_attempts - new_follows),
            "follow_blocked": bool(follow_diag.get('follow_blocked')),
            "follow_last_error": follow_diag.get('last_follow_error'),
            "follow_message": follow_diag.get('last_follow_message'),
            "like_attempts": liked_media_attempts,
            "like_failed": max(0, liked_media_attempts - new_likes),
            "like_blocked": bool(like_diag.get('like_blocked')),
            "like_last_error": like_diag.get('last_like_error'),
            "like_message": like_diag.get('last_like_message'),
            "today_follows": data.get('today_follows_count', 0),
            "today_comments": data.get('today_comments_count', 0),
            "today_likes": data.get('today_likes_count', 0),
            "interacted_pilots": interacted_pilots
        }

    def process_post_comments_and_dms(self, publisher=None, test_comments: list = None) -> dict:
        """
        Scans comments on recent Pozitron posts for engagement keywords ('KUPON', 'LINK', 'FIYAT', 'PARCA').
        Replies publicly to the comment and dispatches a personalized DM with discount code & product link.
        Guarantees zero duplicate DMs using instagram_comment_interactions.
        """
        from .db import is_comment_processed, record_comment_interaction
        from .meta_publisher import MetaPublisher

        if publisher is None:
            publisher = MetaPublisher(dry_run=True)

        target_keywords = ['kupon', 'link', 'fiyat', 'parca', 'parça', 'indirim', 'kod']
        
        comments_to_process = []
        if test_comments is not None:
            comments_to_process = test_comments
        else:
            # If live, query recent media comments via Meta Graph API
            from .db import get_instagram_posts
            recent_posts = get_instagram_posts(limit=5, status='published')
            if not publisher.dry_run and publisher.access_token:
                for p in recent_posts:
                    m_id = p.get('ig_media_id')
                    if m_id and not m_id.startswith('sim_'):
                        try:
                            c_url = f"https://graph.facebook.com/{publisher.graph_api_version}/{m_id}/comments?fields=id,text,from,timestamp&access_token={publisher.access_token}"
                            import urllib.request
                            req = urllib.request.Request(c_url)
                            with urllib.request.urlopen(req, timeout=10) as resp:
                                c_data = json.loads(resp.read().decode('utf-8'))
                                for c_item in c_data.get('data', []):
                                    comments_to_process.append({
                                        'id': c_item.get('id'),
                                        'text': c_item.get('text', ''),
                                        'user_id': (c_item.get('from') or {}).get('id', 'unknown_user'),
                                        'username': (c_item.get('from') or {}).get('username', 'pilot')
                                    })
                        except Exception:
                            pass

        processed_count = 0
        replies_sent = 0
        dms_sent = 0
        interactions = []

        for c in comments_to_process:
            c_id = str(c.get('id'))
            text = c.get('text', '').lower()
            u_id = str(c.get('user_id', 'unknown_user'))
            u_name = c.get('username', 'pilot')

            # Skip if already processed
            if is_comment_processed(c_id):
                continue

            matched_kw = next((kw for kw in target_keywords if kw in text), None)
            if not matched_kw:
                continue

            # 1. Public comment reply
            reply_text = f"@{u_name} Harika! Ozel indirim kodunu ve urun baglantisini DM kutuna ilettik. Keyifli ve kirimsiz ucuslar dileriz!"
            reply_res = publisher.reply_to_comment(c_id, reply_text)
            if reply_res.get('success'):
                replies_sent += 1

            # 2. Private direct message
            dm_text = (
                f"Selam @{u_name}! Pozitron Market FPV ailesine hos geldin.\n\n"
                f"[KUPON] Sana ozel %10 indirim kodun: POZITRON10\n"
                f"[LINK] Dogrudan alisveris ve urun linki: https://pozitronmarket.com\n\n"
                f"Teknik sorularin ve donanim secimi icin bize buradan her zaman yazabilirsin. Kirimsiz ucuslar dileriz!"
            )
            dm_res = publisher.send_direct_message(u_id, dm_text)
            dm_status = 'sent' if dm_res.get('success') else 'failed'
            if dm_res.get('success'):
                dms_sent += 1

            # 3. Record interaction in database
            record_comment_interaction(
                comment_id=c_id,
                user_id=u_id,
                username=u_name,
                keyword=matched_kw.upper(),
                reply_text=reply_text,
                dm_status=dm_status
            )

            processed_count += 1
            interactions.append({
                'comment_id': c_id,
                'username': u_name,
                'keyword': matched_kw.upper(),
                'reply': reply_text,
                'dm_status': dm_status
            })

        return {
            "success": True,
            "processed_comments": processed_count,
            "replies_sent": replies_sent,
            "dms_sent": dms_sent,
            "interactions": interactions
        }

