import os
import uuid
import time
from datetime import datetime
from .db import (
    init_reddit_tables, get_agent_config, update_agent_config,
    save_interaction, get_interaction_by_id, get_interaction_by_reddit_id,
    update_interaction_status, update_interaction_reply, delete_interaction,
    get_interactions, get_daily_replies_count, get_db
)
from .reddit_client import RedditClient
from .ai_engine import GeminiRedditEngine
from .chrome_session import extract_chrome_reddit_session

class RedditDroneAgent:
    def __init__(self):
        init_reddit_tables()
        self.config = get_agent_config()

        # Fallback Gemini key from instagram_agent or env if empty
        gemini_key = self.config.get("gemini_api_key", "").strip()
        if not gemini_key:
            gemini_key = self._find_fallback_gemini_key()
            if gemini_key:
                update_agent_config({"gemini_api_key": gemini_key})
                self.config["gemini_api_key"] = gemini_key

        self.ai_engine = GeminiRedditEngine(api_key=gemini_key)

        # Check Chrome Reddit session for auto-authentication
        bearer_token = ""
        try:
            chrome_res = extract_chrome_reddit_session()
            if chrome_res.get("success"):
                bearer_token = chrome_res.get("token_v2", "")
                if not self.config.get("username") and chrome_res.get("username"):
                    update_agent_config({"username": chrome_res["username"]})
                    self.config["username"] = chrome_res["username"]
        except Exception:
            pass

        self.reddit_client = RedditClient(
            client_id=self.config.get("client_id", ""),
            client_secret=self.config.get("client_secret", ""),
            username=self.config.get("username", ""),
            password=self.config.get("password", ""),
            user_agent=self.config.get("user_agent", ""),
            dry_run=bool(self.config.get("dry_run_mode", 1)),
            bearer_token=bearer_token
        )
        self.scheduler = None

    def _find_fallback_gemini_key(self) -> str:
        """Looks for an existing Gemini key in instagram_agent_config or env."""
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if env_key:
            return env_key

        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT gemini_api_key FROM instagram_agent_config WHERE id=1")
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                return row[0].strip()
        except Exception:
            pass
        return ""

    def reload_config(self):
        self.config = get_agent_config()
        self.ai_engine.set_api_key(self.config.get("gemini_api_key", ""))
        self.reddit_client.configure(
            client_id=self.config.get("client_id", ""),
            client_secret=self.config.get("client_secret", ""),
            username=self.config.get("username", ""),
            password=self.config.get("password", ""),
            user_agent=self.config.get("user_agent", ""),
            dry_run=bool(self.config.get("dry_run_mode", 1))
        )

    def update_config(self, new_cfg: dict) -> dict:
        updated = update_agent_config(new_cfg)
        self.reload_config()
        return updated

    def get_status(self) -> dict:
        self.reload_config()
        all_items = get_interactions(limit=1000)
        draft_count = sum(1 for i in all_items if i.get("status") == "draft")
        published_count = sum(1 for i in all_items if i.get("status") == "published")
        rejected_count = sum(1 for i in all_items if i.get("status") == "rejected")
        failed_count = sum(1 for i in all_items if i.get("status") == "failed")
        today_published = get_daily_replies_count()

        is_running = bool(self.scheduler and self.scheduler.is_running()) if self.scheduler else bool(self.config.get("is_autonomous_enabled", 0))

        chrome_res = extract_chrome_reddit_session()
        chrome_available = bool(chrome_res.get("success"))
        chrome_username = chrome_res.get("username", "")

        return {
            "is_autonomous_enabled": bool(self.config.get("is_autonomous_enabled", 0)),
            "is_scheduler_running": is_running,
            "dry_run_mode": bool(self.config.get("dry_run_mode", 1)),
            "has_reddit_credentials": self.reddit_client.has_credentials(),
            "chrome_session_available": chrome_available,
            "chrome_username": chrome_username,
            "active_username": self.reddit_client.username or chrome_username,
            "has_gemini_key": bool(self.config.get("gemini_api_key")),
            "scan_interval_minutes": self.config.get("scan_interval_minutes", 30),
            "max_replies_per_day": self.config.get("max_replies_per_day", 10),
            "today_published_count": today_published,
            "total_questions_found": len(all_items),
            "draft_count": draft_count,
            "published_count": published_count,
            "rejected_count": rejected_count,
            "failed_count": failed_count,
            "last_scan_at": self.config.get("last_scan_at"),
            "next_scan_at": self.config.get("next_scan_at")
        }

    def sync_chrome_session(self) -> dict:
        """Syncs active Reddit login from Google Chrome."""
        res = extract_chrome_reddit_session()
        if res.get("success"):
            username = res.get("username", "")
            if username:
                self.update_config({"username": username})
            self.reddit_client.configure(
                username=username,
                bearer_token=res.get("token_v2", ""),
                dry_run=bool(self.config.get("dry_run_mode", 1))
            )
            return {
                "success": True,
                "username": username,
                "message": f"Chrome Reddit hesabı (u/{username}) başarıyla bağlandı!"
            }
        return {"success": False, "error": res.get("error", "Chrome oturumu okunamadı")}

    def enable_full_automation(self) -> dict:
        """Enables full autonomy without dry-run and starts scheduler."""
        self.sync_chrome_session()
        self.update_config({
            "is_autonomous_enabled": 1,
            "dry_run_mode": 0
        })
        if self.scheduler:
            self.scheduler.start()
        # Trigger immediate scan in autonomous mode
        scan_res = self.scan_and_process(autonomous=True)
        return {
            "success": True,
            "status": self.get_status(),
            "scan_result": scan_res
        }

    def get_safe_config(self) -> dict:
        self.reload_config()
        cfg = dict(self.config)

        # Mask sensitive keys
        if cfg.get("password"):
            cfg["password_masked"] = "••••••••"
        else:
            cfg["password_masked"] = ""

        if cfg.get("client_secret"):
            s = cfg["client_secret"]
            cfg["client_secret_masked"] = f"{s[:3]}••••{s[-3:]}" if len(s) > 6 else "••••"
        else:
            cfg["client_secret_masked"] = ""

        if cfg.get("gemini_api_key"):
            k = cfg["gemini_api_key"]
            cfg["gemini_api_key_masked"] = f"{k[:4]}••••{k[-4:]}" if len(k) > 8 else "••••"
        else:
            cfg["gemini_api_key_masked"] = ""

        return cfg

    def scan_and_process(self, autonomous: bool = None) -> dict:
        """
        Scans configured subreddits for drone questions,
        generates Gemini answer drafts, and automatically posts to Reddit
        without requiring manual approval when autonomous mode is enabled.
        """
        self.reload_config()
        if autonomous is None:
            autonomous = bool(self.config.get("is_autonomous_enabled", 1))

        subreddits_str = self.config.get("subreddits", "Turkey, teknoloji, bilim, AskTurkey, fpvturkey, droneturkey")
        subreddits = [s.strip() for s in subreddits_str.split(",") if s.strip()]

        keywords_str = self.config.get("keywords", "")
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]

        custom_sig = self.config.get("custom_signature", "İyi uçuşlar ve kırımsız günler! 🛸")
        min_conf = int(self.config.get("auto_post_min_confidence", 70))
        max_daily = int(self.config.get("max_replies_per_day", 10))
        dry_run = bool(self.config.get("dry_run_mode", 0))

        discovered = []
        new_questions_count = 0
        published_count = 0

        for sub in subreddits:
            posts = self.reddit_client.fetch_recent_posts(sub, limit=20)
            for p in posts:
                # Check if already processed
                existing = get_interaction_by_reddit_id(p["reddit_id"])
                if existing:
                    continue

                # Check if it matches keywords & question intent
                if not self.reddit_client.is_question_matching_keywords(p, keywords):
                    continue

                # Evaluate with Gemini
                ai_res = self.ai_engine.evaluate_and_generate_reply(
                    title=p["title"],
                    body=p["body"],
                    subreddit=p["subreddit"],
                    author=p["author"],
                    custom_signature=custom_sig
                )

                if not ai_res.get("is_drone_question", True):
                    continue

                interaction_id = uuid.uuid4().hex[:12]
                interaction_data = {
                    "id": interaction_id,
                    "reddit_id": p["reddit_id"],
                    "reddit_type": p.get("reddit_type", "submission"),
                    "title": p["title"],
                    "body": p["body"],
                    "author": p["author"],
                    "subreddit": p["subreddit"],
                    "url": p.get("url", ""),
                    "permalink": p.get("permalink", ""),
                    "question_summary": ai_res.get("question_summary", p["title"]),
                    "gemini_reply": ai_res.get("reply_text", ""),
                    "status": "draft",
                    "confidence_score": ai_res.get("confidence_score", 85),
                    "upvotes": p.get("score", 0),
                    "created_at": datetime.now().isoformat()
                }

                saved = save_interaction(interaction_data)
                if saved:
                    new_questions_count += 1
                    discovered.append(interaction_data)

                    # Auto-publish immediately without waiting for user approval
                    if autonomous and not dry_run:
                        daily_count = get_daily_replies_count()
                        if daily_count < max_daily and interaction_data["confidence_score"] >= min_conf:
                            print(f"[Reddit Bot] Otomatik onaylandı: {interaction_data['title'][:60]} -> Yayınlanıyor...")
                            pub_res = self.publish_reply(interaction_id)
                            if pub_res.get("success"):
                                published_count += 1
                                interaction_data["status"] = "published"
                                interaction_data["permalink"] = pub_res.get("permalink", interaction_data["permalink"])
                                print(f"[Reddit Bot] ✅ Başarıyla yayınlandı: {interaction_data['permalink']}")
                            else:
                                print(f"[Reddit Bot] ❌ Yayınlanamadı: {pub_res.get('error')}")

        # Update last scan timestamp
        self.update_config({
            "last_scan_at": datetime.now().isoformat()
        })

        return {
            "scanned_subreddits": len(subreddits),
            "new_questions_found": new_questions_count,
            "auto_published_count": published_count,
            "discovered": discovered
        }

    def publish_reply(self, interaction_id: str) -> dict:
        """Publishes a draft reply to Reddit via automated Chrome session."""
        self.reload_config()
        item = get_interaction_by_id(interaction_id)
        if not item:
            return {"success": False, "error": "Kayıt bulunamadı."}

        post_url = item.get("permalink") or item.get("url") or ""
        reply_text = item.get("gemini_reply") or ""

        res = self.reddit_client.post_reply(
            thing_id=item["reddit_id"],
            text=reply_text,
            post_url=post_url
        )
        if res.get("success"):
            update_interaction_status(
                interaction_id,
                status="published",
                published_at=datetime.now().isoformat()
            )
            return {
                "success": True,
                "mode": res.get("mode", "chrome_live"),
                "comment_id": res.get("comment_id"),
                "permalink": res.get("permalink") or post_url,
                "published_at": datetime.now().isoformat()
            }
        else:
            update_interaction_status(
                interaction_id,
                status="failed",
                error_message=res.get("error", "Bilinmeyen hata")
            )
            return {"success": False, "error": res.get("error")}

    def approve_reply(self, interaction_id: str) -> dict:
        """Alias for publish_reply used by manual review."""
        return self.publish_reply(interaction_id)

    def reject_reply(self, interaction_id: str) -> bool:
        """Marks a draft as rejected."""
        return update_interaction_status(interaction_id, status="rejected")

    def edit_reply(self, interaction_id: str, new_text: str) -> bool:
        """Edits the reply text before posting."""
        return update_interaction_reply(interaction_id, new_text)

    def regenerate_reply(self, interaction_id: str) -> dict:
        """Re-generates reply with Gemini."""
        self.reload_config()
        item = get_interaction_by_id(interaction_id)
        if not item:
            return {"success": False, "error": "Kayıt bulunamadı."}

        custom_sig = self.config.get("custom_signature", "İyi uçuşlar ve kırımsız günler! 🛸")
        ai_res = self.ai_engine.evaluate_and_generate_reply(
            title=item.get("title", ""),
            body=item.get("body", ""),
            subreddit=item.get("subreddit", ""),
            author=item.get("author", ""),
            custom_signature=custom_sig
        )

        new_reply = ai_res.get("reply_text", "")
        if new_reply:
            update_interaction_reply(interaction_id, new_reply)
            return {"success": True, "gemini_reply": new_reply, "confidence_score": ai_res.get("confidence_score", 85)}
        return {"success": False, "error": "Yanıt üretilemedi."}

    def delete_reply(self, interaction_id: str) -> bool:
        return delete_interaction(interaction_id)

    def seed_sample_questions(self) -> int:
        """
        Seeds realistic FPV & drone community questions for testing/demo in dry-run mode.
        """
        samples = [
            {
                "reddit_id": f"t3_sample_{int(time.time())}_1",
                "title": "5 inç freestyle FPV drone için 4S mi yoksa 6S batarya mı tercih etmeliyim?",
                "body": "Yeni başlayan bir pilotum. Betaflight üzerinden 5 inçlik bir quad topluyorum. Motor KV değerleri ile batarya voltajı ilişkisini tam oturtamadım. Sizce 4S 2400KV mi yoksa 6S 1750KV mi toplamalıyım? Avantaj ve dezavantajları nelerdir?",
                "author": "PilotCenk_FPV",
                "subreddit": "fpvturkey",
                "permalink": "https://reddit.com/r/fpvturkey/comments/sample_1",
                "url": "https://reddit.com/r/fpvturkey/comments/sample_1"
            },
            {
                "reddit_id": f"t3_sample_{int(time.time())}_2",
                "title": "RadioMaster Pocket ile BetaFPV ELRS alıcıyı eşleştiremiyorum (binding sorunu)",
                "body": "Merhabalar, ExpressLRS 2.4GHz alıcımda ve kumandamda aynı binding phrase'i tanımlamama rağmen alıcı yeşil ışığı hızlı yanıp sönüyor ve bağlanmıyor. Alıcı firmware sürümü 3.x, kumanda da 3.3. UART portları doğru TX->RX lehimlendi. Neyi atlıyor olabilirim?",
                "author": "GokturkDrone",
                "subreddit": "droneturkey",
                "permalink": "https://reddit.com/r/droneturkey/comments/sample_2",
                "url": "https://reddit.com/r/droneturkey/comments/sample_2"
            },
            {
                "reddit_id": f"t3_sample_{int(time.time())}_3",
                "title": "TEKNOFEST İHA kategorisi için hafif karbon fiber frame ve motor önerisi olan var mı?",
                "body": "Takım olarak bu seneki TEKNOFEST yarışmasına hazırlanıyoruz. 500 gram altı kalacak şekilde güçlü itki veren motor ve dayanıklı frame arıyoruz. Türkiye'de parça tedariğini hızlı yapabileceğimiz güvenilir yerli kaynak ve önerileriniz var mıdır?",
                "author": "MuhendisAdayi24",
                "subreddit": "teknoloji",
                "permalink": "https://reddit.com/r/teknoloji/comments/sample_3",
                "url": "https://reddit.com/r/teknoloji/comments/sample_3"
            }
        ]

        count = 0
        custom_sig = self.config.get("custom_signature", "İyi uçuşlar ve kırımsız günler! 🛸")
        for s in samples:
            if get_interaction_by_reddit_id(s["reddit_id"]):
                continue

            ai_res = self.ai_engine.evaluate_and_generate_reply(
                title=s["title"],
                body=s["body"],
                subreddit=s["subreddit"],
                author=s["author"],
                custom_signature=custom_sig
            )

            item = {
                "id": uuid.uuid4().hex[:12],
                "reddit_id": s["reddit_id"],
                "reddit_type": "submission",
                "title": s["title"],
                "body": s["body"],
                "author": s["author"],
                "subreddit": s["subreddit"],
                "url": s["url"],
                "permalink": s["permalink"],
                "question_summary": ai_res.get("question_summary", s["title"]),
                "gemini_reply": ai_res.get("reply_text", ""),
                "status": "draft",
                "confidence_score": ai_res.get("confidence_score", 90),
                "upvotes": 5,
                "created_at": datetime.now().isoformat()
            }
            if save_interaction(item):
                count += 1
        return count
