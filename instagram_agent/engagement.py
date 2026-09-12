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
    'fpv',
    'fpvdrone',
    'teknofest',
    'teknofestiha',
    'fpvfreestyle',
    'fpvracing'
]

FPV_WARM_COMMENTS = [
    "Harika uçuş! Kırımsız ve keyifli uçuşlar dileriz 🛸",
    "Setup ve motor tepkisi çok iyi görünüyor, elinize sağlık! ⚡",
    "Tebrikler, çok akıcı ve temiz bir uçuş olmuş! Gökyüzünde başarılar 🚀",
    "Süper akıcı freestyle hatları, keyifle izledik! Kırımsız günler 🛸",
    "Görüntü netliği ve PID ayarları şahane oturmuş! Pozitron Market FPV ekibinden selamlar 🛸",
    "Elinize sağlık, kırımsız ve bol irtifalı uçuşlar dileriz! ⚡",
    "Çok temiz bir build ve uçuş performansı! Tebrikler 🛸",
    "Drone hakimiyeti harika, gökyüzünde bol kırımsız uçuşlar! 🚀",
    "Renkler ve hatlar müthiş! İyi uçuşlar pilot 🛸",
    "Harika video! Pozitron FPV ailesi olarak selamlar ve kırımsız günler dileriz 🛸"
]

class InstagramEngagementEngine:
    def __init__(self, session_cookies: dict = None, csrf_token: str = None, gemini_api_key: str = None):
        self.session_cookies = session_cookies or {}
        self.csrf_token = csrf_token or ''
        self.gemini_api_key = gemini_api_key or os.environ.get('GEMINI_API_KEY', '')
        self.max_daily = 10
        self._load_session_if_needed()

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

    def generate_friendly_comment(self, username: str, caption: str = '') -> str:
        """Generates a warm, supportive FPV comment (via Gemini or curated pool)."""
        if self.gemini_api_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.gemini_api_key}"
                prompt = f"""Bir Türk FPV drone pilotunun Instagram gönderisine Pozitron Market FPV ekibi olarak samimi, motive edici, nazik ve kırımsız uçuşlar dileyen TEK CÜMLELİK kısa bir yorum yaz.
Pilot Kullanıcı Adı: @{username}
Gönderi Metni: {caption[:200]}

Kurallar:
1. Reklam/pazarlama kokmasın, samimi bir FPV topluluk üyesi gibi yaz.
2. 1 cümle olsun, max 15 kelime.
3. Uygun bir drone/uçuş emojisi (🛸 veya ⚡) ekle.
4. Sadece yorum metnini döndür."""

                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                res = requests.post(url, json=payload, timeout=6)
                if res.status_code == 200:
                    text = res.json()['candidates'][0]['content']['parts'][0]['text'].strip().strip('"')
                    if text and len(text) < 120:
                        return text
            except Exception:
                pass
        return random.choice(FPV_WARM_COMMENTS)

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
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Bugünün 10 takip ve 10 yorum kotası zaten tamamlandı.")
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

        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛸 Drone topluluğu etkileşim döngüsü başladı. Hedef: {follows_needed} takip, {comments_needed} yorum.")

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

                did_something = False

                # 1. Follow Pilot
                if follows_needed > 0 and u_id not in followed_ids:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 👤 Pilot takip ediliyor: @{u_name} (ID: {u_id})")
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
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] 💬 Gönderiye yorum yapılıyor (@{u_name} / https://instagram.com/p/{m_code}/): \"{comment_text}\"")
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
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Etkileşim tamamlandı: +{new_follows} takip, +{new_comments} yorum.")

        return {
            "success": True,
            "new_follows": new_follows,
            "new_comments": new_comments,
            "today_follows": data.get('today_follows_count', 0),
            "today_comments": data.get('today_comments_count', 0),
            "interacted_pilots": interacted_pilots
        }
