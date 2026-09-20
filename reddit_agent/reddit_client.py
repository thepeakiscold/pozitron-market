import requests
import time
import os
import re
from datetime import datetime
from .chrome_session import extract_chrome_reddit_session

class RedditClient:
    """
    Reddit API Client supporting:
    1. Direct Chrome Session Token (Zero API key needed, zero Developer setup)
    2. Official OAuth2 Script App Grant
    3. Public JSON fallback for read-only scanning
    """
    def __init__(self, client_id: str = "", client_secret: str = "", username: str = "", password: str = "",
                 user_agent: str = "", dry_run: bool = True, bearer_token: str = ""):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.username = username.strip()
        self.password = password.strip()
        self.bearer_token = bearer_token.strip()
        self.user_agent = user_agent.strip() or f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.dry_run = dry_run

        self.token_v2 = ""
        self.cookies = {}
        self.is_chrome_session = False
        self.access_token = None
        self.token_expires_at = 0

        # Auto-detect Chrome session if empty
        if not self.has_oauth():
            self._try_load_chrome_session()

    def _try_load_chrome_session(self) -> bool:
        """Attempts to load active Reddit session from Chrome."""
        try:
            res = extract_chrome_reddit_session()
            if res.get("success"):
                self.token_v2 = res.get("token_v2", "")
                self.cookies = res.get("cookies", {})
                self.is_chrome_session = True
                if not self.username:
                    self.username = res.get("username", "")
                return True
        except Exception:
            pass
        return False

    def configure(self, client_id: str = "", client_secret: str = "", username: str = "", password: str = "",
                  user_agent: str = "", dry_run: bool = True, bearer_token: str = ""):
        self.client_id = client_id.strip()
        self.client_secret = client_secret.strip()
        self.username = username.strip()
        self.password = password.strip()
        if bearer_token:
            self.bearer_token = bearer_token.strip()
            self.access_token = self.bearer_token
            self.token_expires_at = time.time() + 86400
        if user_agent:
            self.user_agent = user_agent.strip()
        self.dry_run = dry_run

        if not self.has_oauth():
            self._try_load_chrome_session()

    def has_oauth(self) -> bool:
        return bool(self.client_id and self.client_secret and self.username and self.password)

    def has_credentials(self) -> bool:
        if self.token_v2 or self.is_chrome_session:
            return True
        return self.has_oauth()

    def _authenticate(self) -> bool:
        """Acquires or refreshes official OAuth2 Bearer token from Reddit."""
        if not self.has_oauth():
            return False

        if self.access_token and time.time() < self.token_expires_at - 60:
            return True

        auth_url = "https://www.reddit.com/api/v1/access_token"
        headers = {"User-Agent": self.user_agent}
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password
        }

        try:
            res = requests.post(
                auth_url,
                headers=headers,
                data=data,
                auth=(self.client_id, self.client_secret),
                timeout=12
            )
            if res.status_code == 200:
                token_data = res.json()
                self.access_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expires_at = time.time() + expires_in
                return bool(self.access_token)
            else:
                return False
        except Exception:
            return False

    def search_drone_questions(self, subreddit: str, query: str = "drone OR fpv OR iha OR dji", limit: int = 15) -> list:
        """
        Searches a subreddit specifically for drone questions.
        Uses authenticated oauth.reddit.com if OAuth is configured;
        otherwise falls back to public Reddit search endpoint.
        """
        subreddit = subreddit.strip().lstrip("r/")
        if not subreddit:
            return []

        posts = []
        headers = {"User-Agent": self.user_agent}
        cookies = self.cookies if hasattr(self, 'cookies') and self.cookies else None

        data = None
        # Try OAuth if genuinely configured
        if self.has_oauth() and self._authenticate() and self.access_token:
            try:
                url = f"https://oauth.reddit.com/r/{subreddit}/search"
                oauth_headers = dict(headers)
                oauth_headers["Authorization"] = f"bearer {self.access_token}"
                res = requests.get(url, headers=oauth_headers, params={"q": query, "restrict_sr": "1", "sort": "new", "limit": limit}, timeout=12)
                if res.status_code == 200:
                    data = res.json()
            except Exception:
                pass

        # Fallback to public JSON endpoint
        if not data:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {"q": query, "restrict_sr": "1", "sort": "new", "limit": limit}
                res = requests.get(url, headers=headers, params=params, cookies=cookies, timeout=12)
                if res.status_code == 200:
                    data = res.json()
            except Exception:
                pass

        if data:
            children = data.get("data", {}).get("children", [])
            now_ts = time.time()
            for child in children:
                cdata = child.get("data", {})
                # Skip locked, archived, or posts older than 90 days
                if cdata.get("archived") or cdata.get("locked"):
                    continue
                post_ts = cdata.get("created_utc", 0)
                if post_ts and (now_ts - post_ts) > (90 * 86400):
                    continue

                posts.append({
                    "reddit_id": f"t3_{cdata.get('id')}",
                    "short_id": cdata.get("id"),
                    "reddit_type": "submission",
                    "title": cdata.get("title", ""),
                    "body": cdata.get("selftext", ""),
                    "author": cdata.get("author", ""),
                    "subreddit": cdata.get("subreddit", subreddit),
                    "url": cdata.get("url", ""),
                    "permalink": f"https://reddit.com{cdata.get('permalink', '')}",
                    "created_utc": post_ts,
                    "score": cdata.get("score", 0),
                    "num_comments": cdata.get("num_comments", 0)
                })

        return posts

    def fetch_recent_posts(self, subreddit: str, limit: int = 25, include_search: bool = True) -> list:
        """
        Fetches newest posts from a subreddit, optionally augmented with targeted drone search.
        Uses OAuth2 if configured; otherwise falls back to public Reddit JSON API.
        """
        subreddit = subreddit.strip().lstrip("r/")
        if not subreddit:
            return []

        posts = []
        seen_ids = set()
        headers = {"User-Agent": self.user_agent}
        cookies = self.cookies if hasattr(self, 'cookies') and self.cookies else None

        data = None
        # Try OAuth if genuinely configured
        if self.has_oauth() and self._authenticate() and self.access_token:
            try:
                url = f"https://oauth.reddit.com/r/{subreddit}/new"
                oauth_headers = dict(headers)
                oauth_headers["Authorization"] = f"bearer {self.access_token}"
                res = requests.get(url, headers=oauth_headers, params={"limit": limit}, timeout=12)
                if res.status_code == 200:
                    data = res.json()
            except Exception:
                pass

        # Fallback to public JSON endpoint
        if not data:
            try:
                url = f"https://www.reddit.com/r/{subreddit}/new.json"
                res = requests.get(url, headers=headers, params={"limit": limit}, cookies=cookies, timeout=12)
                if res.status_code == 200:
                    data = res.json()
            except Exception:
                pass

        if data:
            children = data.get("data", {}).get("children", [])
            now_ts = time.time()
            for child in children:
                cdata = child.get("data", {})
                # Skip locked, archived, or posts older than 90 days
                if cdata.get("archived") or cdata.get("locked"):
                    continue
                post_ts = cdata.get("created_utc", 0)
                if post_ts and (now_ts - post_ts) > (90 * 86400):
                    continue

                rid = f"t3_{cdata.get('id')}"
                seen_ids.add(rid)
                posts.append({
                    "reddit_id": rid,
                    "short_id": cdata.get("id"),
                    "reddit_type": "submission",
                    "title": cdata.get("title", ""),
                    "body": cdata.get("selftext", ""),
                    "author": cdata.get("author", ""),
                    "subreddit": cdata.get("subreddit", subreddit),
                    "url": cdata.get("url", ""),
                    "permalink": f"https://reddit.com{cdata.get('permalink', '')}",
                    "created_utc": post_ts,
                    "score": cdata.get("score", 0),
                    "num_comments": cdata.get("num_comments", 0)
                })

        # Augmented targeted search discovery
        if include_search:
            try:
                search_results = self.search_drone_questions(subreddit, query="drone OR fpv OR iha OR dji", limit=15)
                for sp in search_results:
                    if sp["reddit_id"] not in seen_ids:
                        seen_ids.add(sp["reddit_id"])
                        posts.append(sp)
            except Exception:
                pass

        return posts

    CORE_DRONE_KEYWORDS = [
        "drone", "dron", "fpv", "quadcopter", "multicopter", "iha", "siha",
        "dji", "betafpv", "betaflight", "inav", "elrs", "expresslrs",
        "crossfire", "tbs", "vtx", "vrx", "teknofest", "uçuş kartı", "f405",
        "f722", "cinewhoop", "whoop", "walksnail", "radiomaster", "jumper",
        "taranis", "mobula", "cetus", "lipo batarya", "fırçasız motor",
        "fırçasız", "brushless"
    ]

    DEDICATED_DRONE_SUBS = [
        "fpvturkey", "droneturkey", "multicopter", "fpv", "drones", "fpvracing"
    ]

    def is_question_matching_keywords(self, post: dict, keywords: list) -> bool:
        """
        Determines whether a post is a drone question matching the target keywords.
        In general Turkish subreddits (r/Turkey, r/teknoloji, etc.), strictly enforces
        at least one CORE_DRONE_KEYWORDS using word boundaries to avoid false positives.
        """
        # Don't answer our own bot
        if self.username and post.get("author", "").lower() == self.username.lower():
            return False

        title = post.get("title", "").lower()
        body = post.get("body", "").lower()
        subreddit = post.get("subreddit", "").lower().lstrip("r/").strip()

        # Strip URLs to avoid false matches (e.g. "?igsh=" query parameters triggering question intent)
        clean_title = re.sub(r'https?://\S+', '', title)
        clean_body = re.sub(r'https?://\S+', '', body)
        clean_full_text = f"{clean_title} {clean_body}".strip()

        # 0. Exclude non-drone audio/camera equipment (e.g. DJI Mic, Osmo Pocket)
        audio_video_gear_excludes = [
            "dji mic", "mic mini", "kablosuz mikrofon", "yaka mikrofonu", "osmo pocket",
            "osmo action", "action cam", "gopro hero", "insta360 go", "ronin sc", "ronin rs"
        ]
        if any(term in clean_full_text for term in audio_video_gear_excludes):
            if not any(t in clean_full_text for t in ["uçuş", "ucus", "lehim", "betaflight", "elrs", "esc", "lipo", "quad"]):
                return False

        # 1. Subreddit specific keyword check
        is_dedicated_drone_sub = any(ds in subreddit for ds in self.DEDICATED_DRONE_SUBS)

        if is_dedicated_drone_sub:
            # In dedicated drone subreddits, any drone-related keyword matches
            has_drone_keyword = False
            for kw in (keywords or self.CORE_DRONE_KEYWORDS):
                kw_clean = kw.strip().lower()
                if not kw_clean:
                    continue
                pattern = r'\b' + re.escape(kw_clean) + r'\b'
                if re.search(pattern, clean_full_text, re.IGNORECASE):
                    has_drone_keyword = True
                    break
            if not has_drone_keyword:
                return False
        else:
            # In general subreddits (r/Turkey, r/teknoloji, r/AskTurkey, etc.),
            # 1. Filter out military / political news topics
            political_or_military_excludes = [
                "bayraktar", "tb2", "tb3", "akıncı", "akinci", "kızılelma", "kizilelma",
                "anka", "aksungur", "ukrayna", "rusya", "israil", "gazze", "ordu", "tsk",
                "savunma sanayii", "milli savunma", "şehit", "sehit", "savaş", "savas",
                "harekat", "operasyon", "seçim", "secim", "hükümet", "hukumet"
            ]
            if any(term in clean_full_text for term in political_or_military_excludes):
                return False

            # 2. Filter out light shows, drone shows, ceremonies, racing horse events
            news_event_excludes = [
                "gösterisi", "gosterisi", "ışık gösterisi", "isik gosterisi", "silueti",
                "resepsiyonu", "yarış atı", "yaris ati", "gazi koşusu", "gazi kosusu",
                "emniyet müdürlüğü", "operasyonunda drone", "yakalandı", "gözaltına", "tutuklandı"
            ]
            if any(term in clean_full_text for term in news_event_excludes):
                return False

            # 3. MUST contain at least one CORE drone keyword with word boundary!
            has_core_keyword = False
            for ckw in self.CORE_DRONE_KEYWORDS:
                pattern = r'\b' + re.escape(ckw) + r'\b'
                if re.search(pattern, clean_full_text, re.IGNORECASE):
                    has_core_keyword = True
                    break

            if not has_core_keyword:
                return False

        # 2. Question / Help intent check
        question_indicators = [
            "?", "nasıl", "öneri", "tavsiye", "yardım", "çalışmıyor", "sorun", "neden",
            "bağlantı", "hangisi", "uyumlu mu", "başlangıç", "ne yapmalıyım", "hata",
            "arızalandı", "kurulum", "ayarı", "yardim", "destek", "anlamadım", "yardımcı",
            "önerseniz", "bilgisi olan", "tavsiyesi olan", "fikri olan", "alınır mı",
            "how to", "why", "issue", "help", "problem", "which", "recommend"
        ]

        if "?" in clean_full_text:
            return True

        for indicator in question_indicators:
            if indicator == "?":
                continue
            pattern = r'\b' + re.escape(indicator) + r'\b'
            if re.search(pattern, clean_full_text, re.IGNORECASE):
                return True

        return False

    def post_reply(self, thing_id: str, text: str, post_url: str = "") -> dict:
        """
        Submits a comment reply to a submission or comment.
        Uses automated stealth Chrome session for 100% reliable posting without API restrictions,
        or falls back to OAuth2 API if configured.
        """
        if self.dry_run:
            mock_id = f"sim_{int(time.time())}"
            return {
                "success": True,
                "mode": "dry_run",
                "comment_id": mock_id,
                "permalink": f"https://reddit.com/r/dryrun/comments/{thing_id}/comment/{mock_id}/",
                "published_at": datetime.now().isoformat()
            }

        chrome_err = ""
        # 1. Primary Method: Automated Chrome Posting via User's Authenticated Session
        if post_url:
            try:
                from .chrome_publisher import publish_via_chrome
                chrome_res = publish_via_chrome(post_url, text, username=self.username)
                if chrome_res.get("success"):
                    return {
                        "success": True,
                        "mode": "chrome_live",
                        "permalink": chrome_res.get("permalink") or post_url,
                        "published_at": datetime.now().isoformat()
                    }
                elif chrome_res.get("archived"):
                    return {
                        "success": False,
                        "archived": True,
                        "error": chrome_res.get("error", "Bu Reddit gonderisi arsivlenmis veya kilitlenmis, yeni yorum yapilamaz.")
                    }
                else:
                    chrome_err = chrome_res.get("error", "Chrome gonderim basarisiz")
            except Exception as ce:
                chrome_err = f"Chrome otomasyon hatasi: {str(ce)}"

        # 2. Secondary Method: Direct OAuth REST API (only if official OAuth app is configured)
        if not self.has_oauth() or not self._authenticate():
            err_details = chrome_err or "Reddit Chrome oturumu ile gonderilemedi ve OAuth2 yapilandirilmamis."
            return {
                "success": False,
                "error": err_details
            }

        url = "https://oauth.reddit.com/api/comment"
        headers = {
            "User-Agent": self.user_agent,
            "Authorization": f"bearer {self.access_token}"
        }
        data = {
            "thing_id": thing_id,
            "text": text,
            "api_type": "json"
        }

        try:
            res = requests.post(url, headers=headers, data=data, timeout=15)
            if res.status_code == 200:
                res_json = res.json()
                errors = res_json.get("json", {}).get("errors", [])
                if errors:
                    err_msg = ", ".join([str(e) for e in errors])
                    return {"success": False, "error": f"Reddit API Hatası: {err_msg}"}

                things = res_json.get("json", {}).get("data", {}).get("things", [])
                comment_data = things[0].get("data", {}) if things else {}
                comment_id = comment_data.get("id") or comment_data.get("name")
                permalink = f"https://reddit.com{comment_data.get('permalink', '')}"

                return {
                    "success": True,
                    "mode": "oauth_live",
                    "comment_id": comment_id,
                    "permalink": permalink,
                    "published_at": datetime.now().isoformat()
                }
            elif res.status_code == 429:
                return {"success": False, "error": "Reddit Hız Sınırı (Rate Limit 429). Lütfen bir süre bekleyin."}
            else:
                return {"success": False, "error": f"Reddit Yanıt Kodu {res.status_code}: {res.text}"}
        except Exception as e:
            return {"success": False, "error": f"Bağlantı hatası: {str(e)}"}
