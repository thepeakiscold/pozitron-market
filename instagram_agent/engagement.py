import os
import json
import time
import random
import requests
from datetime import datetime, date
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

    def _get_headers(self, referer: str = 'https://www.instagram.com/') -> dict:
        csrf = self.csrf_token or self.session_cookies.get('csrftoken', '')
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
            "max_daily_limit": self.max_daily,
            "followed_user_ids": [],
            "commented_media_ids": [],
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

        if self.gemini_api_key:
            models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-2.0-flash"]
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

    def follow_user(self, user_id: str, username: str) -> bool:
        """Sends follow request to an Instagram user via GraphQL mutation."""
        if not self.session_cookies or not self.session_cookies.get('sessionid'):
            return False

        url = 'https://www.instagram.com/graphql/query'
        headers = self._get_headers(referer=f"https://www.instagram.com/{username}/")
        
        payload = {
            'doc_id': '27767812149509802',
            'variables': json.dumps({
                'target_user_id': str(user_id),
                'data': {
                    'include_follow_friction_check': True
                }
            })
        }

        try:
            res = requests.post(url, headers=headers, cookies=self.session_cookies, data=payload, timeout=12)
            if res.status_code == 200:
                body = res.json()
                friendship = body.get('data', {}).get('xdt_create_friendship', {}).get('friendship_status', {})
                return friendship.get('following') is True or friendship.get('outgoing_request') is True
        except Exception as e:
            print(f"Follow error for {username}: {e}")
        return False

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
        
        follows_needed = max(0, min(self.max_daily, target_count) - data.get('today_follows_count', 0))
        comments_needed = max(0, min(self.max_daily, target_count) - data.get('today_comments_count', 0))

        if follows_needed == 0 and comments_needed == 0:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [KOTA DOLU] Bugünün 10 takip ve 10 yorum kotası zaten tamamlandı.")
            return {
                "success": True,
                "completed_already": True,
                "today_follows": data.get('today_follows_count', 0),
                "today_comments": data.get('today_comments_count', 0),
                "message": "Bugünkü 10 takip ve yorum kotası dolu."
            }

        followed_ids = set(data.get('followed_user_ids', []))
        commented_media_ids = set(data.get('commented_media_ids', []))

        # Randomize hashtag order for natural engagement
        shuffled_tags = list(TARGET_HASHTAGS)
        random.shuffle(shuffled_tags)

        new_follows = 0
        new_comments = 0
        interacted_pilots = []

        my_user_id = str(self.session_cookies.get('ds_user_id', '30375317594'))

        print(f"[{datetime.now().strftime('%H:%M:%S')}] [ETKİLEŞİM BAŞLADI] Drone topluluğu etkileşim döngüsü başladı. Hedef: {follows_needed} takip, {comments_needed} yorum.")

        for tag in shuffled_tags:
            if follows_needed <= 0 and comments_needed <= 0:
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
                if follows_needed > 0 and u_id not in followed_ids:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [PILOT TAKIP] Pilot takip ediliyor: @{u_name} (ID: {u_id})")
                    ok = self.follow_user(u_id, u_name)
                    if ok:
                        followed_ids.add(u_id)
                        data['followed_user_ids'].append(u_id)
                        data['today_follows_count'] += 1
                        new_follows += 1
                        follows_needed -= 1
                        did_something = True
                        data['history'].append({
                            "type": "follow",
                            "username": u_name,
                            "user_id": u_id,
                            "timestamp": datetime.now().isoformat(),
                            "status": "success"
                        })
                    time.sleep(random.uniform(5, 10))

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

                if did_something:
                    interacted_pilots.append({
                        "username": u_name,
                        "post_url": f"https://www.instagram.com/p/{m_code}/"
                    })
                    # Delay between different accounts (natural human pacing)
                    time.sleep(random.uniform(8, 16))

                if follows_needed <= 0 and comments_needed <= 0:
                    break

        self.save_interactions_data(data)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [TAMAMLANDI] Etkilesim tamamlandi: +{new_follows} takip, +{new_comments} yorum.")

        return {
            "success": True,
            "new_follows": new_follows,
            "new_comments": new_comments,
            "today_follows": data.get('today_follows_count', 0),
            "today_comments": data.get('today_comments_count', 0),
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

