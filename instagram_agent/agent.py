import os
import time
import uuid
import urllib.request
from datetime import datetime, timedelta
from .db import (
    get_agent_config, update_agent_config, save_instagram_post,
    update_instagram_post_status, get_instagram_posts,
    get_instagram_post_by_id, delete_instagram_post, init_instagram_tables,
    get_last_post_image_mode
)
from .content_generator import ContentGenerator
from .image_generator import ImageGenerator
from .meta_publisher import MetaPublisher
from .engagement import InstagramEngagementEngine
from .scheduler import calculate_next_peak_window

class InstagramPRAgent:
    def __init__(self):
        init_instagram_tables()
        config = get_agent_config()
        self.config = config

        env_token = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
        env_account_id = os.environ.get('INSTAGRAM_ACCOUNT_ID')
        env_gemini = os.environ.get('GEMINI_API_KEY')
        env_dry_run = os.environ.get('INSTAGRAM_DRY_RUN')

        token = env_token if env_token is not None else config.get('access_token', '')
        account_id = env_account_id if env_account_id is not None else config.get('instagram_account_id', '')
        gemini_key = env_gemini if env_gemini is not None else config.get('gemini_api_key', '')

        if env_dry_run is not None:
            is_dry_run = env_dry_run.strip().lower() in ('1', 'true', 'yes')
        else:
            is_dry_run = bool(config.get('dry_run_mode', 1))

        self.content_gen = ContentGenerator(gemini_api_key=gemini_key)
        self.image_gen = ImageGenerator(width=1080, height=1080, gemini_api_key=gemini_key)
        self.publisher = MetaPublisher(
            access_token=token,
            instagram_account_id=account_id,
            dry_run=is_dry_run,
            public_base_url=config.get('public_base_url', 'https://pozitronmarket.com')
        )
        self.scheduler = None

    def reload_config(self):
        self.config = get_agent_config()
        env_token = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
        env_account_id = os.environ.get('INSTAGRAM_ACCOUNT_ID')
        env_gemini = os.environ.get('GEMINI_API_KEY')
        env_dry_run = os.environ.get('INSTAGRAM_DRY_RUN')

        token = env_token if env_token is not None else self.config.get('access_token', '')
        account_id = env_account_id if env_account_id is not None else self.config.get('instagram_account_id', '')
        gemini_key = env_gemini if env_gemini is not None else self.config.get('gemini_api_key', '')

        if env_dry_run is not None:
            is_dry_run = env_dry_run.strip().lower() in ('1', 'true', 'yes')
        else:
            is_dry_run = bool(self.config.get('dry_run_mode', 1))

        self.content_gen.set_api_key(gemini_key)
        self.image_gen.set_api_key(gemini_key)
        self.publisher.configure(
            access_token=token,
            instagram_account_id=account_id,
            dry_run=is_dry_run,
            public_base_url=self.config.get('public_base_url', 'https://pozitronmarket.com')
        )

    def get_status(self) -> dict:
        self.reload_config()
        posts = get_instagram_posts(limit=100)
        published_count = sum(1 for p in posts if p.get('status') == 'published')
        draft_count = sum(1 for p in posts if p.get('status') == 'draft')
        failed_count = sum(1 for p in posts if p.get('status') == 'failed')

        is_running = bool(self.scheduler and self.scheduler.is_running()) if self.scheduler else bool(self.config.get('is_autonomous_enabled', 0))

        return {
            "is_autonomous_enabled": bool(self.config.get('is_autonomous_enabled', 0)),
            "is_scheduler_running": is_running,
            "dry_run_mode": bool(self.config.get('dry_run_mode', 1)),
            "posting_frequency_hours": self.config.get('posting_frequency_hours', 12),
            "story_enabled": bool(self.config.get('story_enabled', 1)),
            "carousel_enabled": bool(self.config.get('carousel_enabled', 1)),
            "dm_automation_enabled": bool(self.config.get('dm_automation_enabled', 1)),
            "peak_scheduler_enabled": bool(self.config.get('peak_scheduler_enabled', 0)),
            "reels_enabled": bool(self.config.get('reels_enabled', 1)),
            "last_run_at": self.config.get('last_run_at'),
            "next_run_at": self.config.get('next_run_at'),
            "total_posts": len(posts),
            "published_count": published_count,
            "draft_count": draft_count,
            "failed_count": failed_count,
            "has_credentials": bool(self.config.get('access_token') and self.config.get('instagram_account_id'))
        }

    def calculate_next_run(self, from_dt: datetime = None) -> str:
        """
        Calculates the next scheduled run timestamp.
        Uses calculate_next_peak_window if peak_scheduler_enabled is True,
        otherwise calculates next_run based on posting_frequency_hours.
        """
        if from_dt is None:
            from_dt = datetime.now()
        if self.config.get('peak_scheduler_enabled', 0):
            return calculate_next_peak_window(from_dt).isoformat()
        freq_hours = self.config.get('posting_frequency_hours', 6)
        return (from_dt + timedelta(hours=freq_hours)).isoformat()

    def get_safe_config(self) -> dict:
        self.reload_config()
        token = self.config.get('access_token', '')
        masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else ("***" if token else "")
        gemini_key = self.config.get('gemini_api_key', '')
        masked_gemini = f"{gemini_key[:4]}...{gemini_key[-4:]}" if len(gemini_key) > 8 else ("***" if gemini_key else "")
        token_valid, token_msg = self.publisher.test_token()

        return {
            "access_token_masked": masked_token,
            "has_access_token": bool(token),
            "token_valid": token_valid,
            "token_status_msg": token_msg,
            "instagram_account_id": self.config.get('instagram_account_id', ''),
            "gemini_api_key_masked": masked_gemini,
            "has_gemini_key": bool(gemini_key),
            "is_autonomous_enabled": bool(self.config.get('is_autonomous_enabled', 0)),
            "posting_frequency_hours": self.config.get('posting_frequency_hours', 12),
            "dry_run_mode": bool(self.config.get('dry_run_mode', 1)),
            "public_base_url": self.config.get('public_base_url', 'https://pozitronmarket.com'),
            "preferred_language": self.config.get('preferred_language', 'tr'),
            "default_hashtags": self.config.get('default_hashtags', ''),
            "story_enabled": bool(self.config.get('story_enabled', 1)),
            "carousel_enabled": bool(self.config.get('carousel_enabled', 1)),
            "dm_automation_enabled": bool(self.config.get('dm_automation_enabled', 1)),
            "peak_scheduler_enabled": bool(self.config.get('peak_scheduler_enabled', 0)),
            "reels_enabled": bool(self.config.get('reels_enabled', 1)),
            "last_run_at": self.config.get('last_run_at'),
            "next_run_at": self.config.get('next_run_at')
        }

    def update_config(self, updates: dict) -> dict:
        clean_updates = {}
        for k in [
            'instagram_account_id', 'is_autonomous_enabled', 'posting_frequency_hours',
            'dry_run_mode', 'public_base_url', 'preferred_language', 'default_hashtags',
            'story_enabled', 'carousel_enabled', 'dm_automation_enabled',
            'peak_scheduler_enabled', 'reels_enabled'
        ]:
            if k in updates:
                clean_updates[k] = updates[k]

        # Only update tokens if non-empty and not masked
        if 'access_token' in updates and updates['access_token'] and '...' not in updates['access_token']:
            clean_updates['access_token'] = updates['access_token']
        if 'gemini_api_key' in updates and '...' not in str(updates['gemini_api_key']):
            clean_updates['gemini_api_key'] = updates['gemini_api_key']

        # If user explicitly sets an hourly posting frequency and didn't specify peak_scheduler_enabled,
        # disable peak_scheduler_enabled so the requested hourly schedule is strictly honored.
        if 'posting_frequency_hours' in clean_updates and 'peak_scheduler_enabled' not in updates:
            clean_updates['peak_scheduler_enabled'] = 0

        # Recalculate next_run_at immediately if frequency or peak scheduler mode changed
        if 'posting_frequency_hours' in clean_updates or 'peak_scheduler_enabled' in clean_updates:
            now = datetime.now()
            is_peak = bool(clean_updates.get('peak_scheduler_enabled', self.config.get('peak_scheduler_enabled', 0)))
            if is_peak:
                clean_updates['next_run_at'] = calculate_next_peak_window(now).isoformat()
            else:
                freq_hours = clean_updates.get('posting_frequency_hours', self.config.get('posting_frequency_hours', 6))
                last_run_str = self.config.get('last_run_at')
                if last_run_str:
                    try:
                        last_run_dt = datetime.fromisoformat(last_run_str)
                        target_dt = last_run_dt + timedelta(hours=freq_hours)
                        if target_dt > now:
                            clean_updates['next_run_at'] = target_dt.isoformat()
                        else:
                            clean_updates['next_run_at'] = (now + timedelta(seconds=10)).isoformat()
                    except Exception:
                        clean_updates['next_run_at'] = (now + timedelta(hours=freq_hours)).isoformat()
                else:
                    clean_updates['next_run_at'] = (now + timedelta(hours=freq_hours)).isoformat()

        res = update_agent_config(clean_updates)
        self.reload_config()

        # Update scheduler state if changed
        if self.scheduler:
            if clean_updates.get('is_autonomous_enabled'):
                self.scheduler.start()
            elif clean_updates.get('is_autonomous_enabled') is False:
                self.scheduler.stop()

        return self.get_safe_config()

    def _sync_assets_to_repo(self, asset_rel_paths: list, commit_subject: str) -> bool:
        """
        Synchronizes media assets (images, slides, reels videos) to the GitHub repository
        so that Meta Graph API can download them from the public raw URL.
        """
        if self.config.get('dry_run_mode', 0):
            return True

        clean_paths = []
        for p in asset_rel_paths:
            if p:
                clean_p = p.lstrip('./').lstrip('/')
                clean_paths.append(clean_p)

        if not clean_paths:
            return True

        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            import subprocess
            cmd_add = ["git", "add"] + clean_paths
            subprocess.run(cmd_add, cwd=repo_root, check=False, timeout=10)
            subprocess.run(["git", "commit", "-m", f"chore(assets): auto-sync {commit_subject} [skip ci] [skip render]"], cwd=repo_root, check=False, timeout=10)
            subprocess.run(["git", "push", "origin", "main"], cwd=repo_root, check=False, timeout=20)

            # Wait for GitHub CDN to return HTTP 200 for public raw url
            for clean_p in clean_paths:
                pub_url = f"{self.publisher.public_base_url}/{clean_p}"
                for attempt in range(6):
                    try:
                        req_chk = urllib.request.Request(pub_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req_chk, timeout=4) as r_chk:
                            if r_chk.status == 200:
                                break
                    except Exception:
                        time.sleep(2)
            return True
        except Exception as sync_e:
            print(f"[UYARI] Medya senkronizasyon uyarisi: {sync_e}")
            return False

    def generate_and_publish_now(self, content_type: str = None, product_id: str = None) -> dict:
        """
        Creates a new post and DIRECTLY publishes it to Instagram (Meta API or dry-run).
        Never leaves a draft behind.
        """
        self.reload_config()

        # If carousel_guide requested, route to carousel publisher
        if content_type == 'carousel_guide':
            return self.generate_and_publish_carousel(content_type=content_type, product_id=product_id)

        post_id = f"ig_post_{uuid.uuid4().hex[:12]}"
        
        # 1. Generate text and metadata
        content = self.content_gen.generate_content(content_type=content_type, product_id=product_id)
        if not content:
            return {"success": False, "error": "İçerik üretilemedi veya aday ürün bulunamadı."}

        if content.get('content_type') == 'carousel_guide':
            return self.generate_and_publish_carousel(content_type='carousel_guide', product_id=product_id)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] [INSTAGRAM AJANI] Yeni gönderi hazırlandı: {content['title']} (Tip: {content['content_type']})")

        # 2. Determine Image Mode (Alternating: canvas vs gemini_image every other post)
        last_mode = get_last_post_image_mode()
        target_mode = 'gemini_image' if last_mode != 'gemini_image' else 'canvas'

        temp_post_data = {
            'id': post_id,
            'content_type': content['content_type'],
            'media_type': content.get('media_type', 'IMAGE'),
            'image_mode': target_mode,
            'product_id': content.get('product_id'),
            'title': content['title'],
            'caption': content['caption'],
            'hashtags': content['hashtags'],
            'product_data': content.get('product_data'),
            'tool_info': content.get('tool_info'),
            'visual_summary': content.get('visual_summary'),
            'created_at': datetime.now().isoformat()
        }

        gemini_key = self.config.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY', '')

        if target_mode == 'gemini_image':
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [INSTAGRAM AJANI] Gemini AI Image modu secildi (Her 2 postta bir). Gorsel uretiliyor...")
            img_rel_path = self.image_gen.generate_gemini_ai_image(temp_post_data, gemini_api_key=gemini_key)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [INSTAGRAM AJANI] Canvas Banner modu secildi. Gorsel hazirlaniyor...")
            img_rel_path = self.image_gen.generate_post_image(temp_post_data)

        temp_post_data['image_url'] = img_rel_path
        temp_post_data['local_image_path'] = img_rel_path

        # 2.1 Multimodal Visual Quality & Safety Audit via Gemini 3.8 Flash Vision
        gemini_key = self.config.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY', '')
        audit_res = self.image_gen.audit_generated_image(img_rel_path, gemini_api_key=gemini_key, context=temp_post_data)
        temp_post_data['visual_audit'] = audit_res
        if not temp_post_data.get('metadata'):
            temp_post_data['metadata'] = {}
        temp_post_data['metadata']['visual_audit'] = audit_res

        # 2.2 Sync newly generated image to repo so Meta Graph API can download it
        self._sync_assets_to_repo([img_rel_path], f"instagram post image {post_id}")

        # 3. Publish immediately to Meta Graph API
        result = self.publisher.publish_post(temp_post_data)

        if result.get('success'):
            now_iso = datetime.now().isoformat()
            temp_post_data['status'] = 'published'
            temp_post_data['ig_media_id'] = result.get('ig_media_id')
            temp_post_data['ig_permalink'] = result.get('ig_permalink')
            temp_post_data['published_at'] = now_iso
            
            # Save strictly published post to SQLite and JSON
            save_instagram_post(temp_post_data)

            # Update schedule timings (smart peak-time window or frequency hours)
            next_run = self.calculate_next_run()

            update_agent_config({
                'last_run_at': now_iso,
                'next_run_at': next_run
            })
            result['post'] = temp_post_data
            return result
        else:
            # Do NOT persist as draft on failure
            print(f"[HATA] Paylasim basarisiz oldu: {result.get('error')}")
            return result

    def generate_and_publish_carousel(self, content_type: str = 'carousel_guide', product_id: str = None) -> dict:
        """
        Creates a 4-slide carousel guide post and publishes it directly.
        """
        self.reload_config()
        post_id = f"ig_post_{uuid.uuid4().hex[:12]}"

        content = self.content_gen.generate_content(content_type='carousel_guide', product_id=product_id)
        if not content:
            return {"success": False, "error": "Carousel icerigi uretilemedi."}

        temp_post_data = {
            'id': post_id,
            'content_type': 'carousel_guide',
            'media_type': 'CAROUSEL',
            'image_mode': 'canvas',
            'product_id': content.get('product_id'),
            'title': content['title'],
            'caption': content['caption'],
            'hashtags': content['hashtags'],
            'product_data': content.get('product_data'),
            'tool_info': content.get('tool_info'),
            'visual_summary': content.get('visual_summary'),
            'created_at': datetime.now().isoformat()
        }

        # Generate 4 slides
        slide_paths = self.image_gen.generate_carousel_slides(temp_post_data)
        temp_post_data['image_url'] = slide_paths[0]
        temp_post_data['local_image_path'] = slide_paths[0]
        temp_post_data['slides'] = slide_paths
        if not temp_post_data.get('metadata'):
            temp_post_data['metadata'] = {}
        temp_post_data['metadata']['slides'] = slide_paths

        # Sync carousel slide images to repo for Meta Graph API access
        self._sync_assets_to_repo(slide_paths, f"instagram carousel slides {post_id}")

        # Publish carousel
        result = self.publisher.publish_carousel(temp_post_data, slide_paths)

        if result.get('success'):
            now_iso = datetime.now().isoformat()
            temp_post_data['status'] = 'published'
            temp_post_data['ig_media_id'] = result.get('ig_media_id')
            temp_post_data['ig_permalink'] = result.get('ig_permalink')
            temp_post_data['published_at'] = now_iso

            save_instagram_post(temp_post_data)

            next_run = self.calculate_next_run()

            update_agent_config({
                'last_run_at': now_iso,
                'next_run_at': next_run
            })
            result['post'] = temp_post_data
            return result
        else:
            return result

    def generate_and_publish_story(self, post_data: dict = None) -> dict:
        """
        Creates a 9:16 vertical story graphic and publishes it to Instagram Stories.
        """
        self.reload_config()
        post_id = f"ig_story_{uuid.uuid4().hex[:12]}"

        if not post_data:
            content = self.content_gen.generate_content(content_type='deal_drop')
            post_data = {
                'id': post_id,
                'content_type': 'deal_drop',
                'title': content['title'],
                'caption': content['caption'],
                'hashtags': content['hashtags'],
                'product_data': content.get('product_data'),
                'visual_summary': content.get('visual_summary'),
                'created_at': datetime.now().isoformat()
            }
        else:
            post_data = dict(post_data)
            post_data['id'] = post_id

        post_data['media_type'] = 'STORIES'
        story_rel_path = self.image_gen.generate_story_image(post_data)
        post_data['image_url'] = story_rel_path
        post_data['local_image_path'] = story_rel_path

        # Sync story image to repo for Meta Graph API access
        self._sync_assets_to_repo([story_rel_path], f"instagram story image {post_id}")

        result = self.publisher.publish_story(post_data, story_rel_path)
        if result.get('success'):
            now_iso = datetime.now().isoformat()
            post_data['status'] = 'published'
            post_data['ig_media_id'] = result.get('ig_media_id')
            post_data['published_at'] = now_iso
            save_instagram_post(post_data)
            result['post'] = post_data
        return result

    def generate_and_publish_reel(self, post_data: dict = None) -> dict:
        """
        Creates a 9:16 vertical Reels video using Gemini Omni Flash (gemini-omni-1.1-flash) AI video
        generation with ffmpeg fallback, and publishes it.
        """
        self.reload_config()
        post_id = f"ig_reel_{uuid.uuid4().hex[:12]}"

        if not post_data:
            content = self.content_gen.generate_content(content_type='product_spotlight')
            post_data = {
                'id': post_id,
                'content_type': 'product_spotlight',
                'title': content['title'],
                'caption': content['caption'],
                'hashtags': content['hashtags'],
                'product_data': content.get('product_data'),
                'visual_summary': content.get('visual_summary'),
                'created_at': datetime.now().isoformat()
            }
        else:
            post_data = dict(post_data)
            post_data['id'] = post_id

        post_data['media_type'] = 'REEL'

        # Generate cinematic video prompt via ContentGenerator
        video_prompt = self.content_gen.generate_reels_video_prompt(post_data)

        video_rel_path = self.image_gen.generate_reels_video(post_data, prompt=video_prompt)
        if not video_rel_path:
            return {"success": False, "error": "Reels videosu olusturulamadi (Gemini ve ffmpeg bos dondu)."}

        video_engine = post_data.get('video_engine', 'unknown')
        post_data['video_url'] = video_rel_path
        post_data['local_image_path'] = video_rel_path
        post_data['image_url'] = post_data.get('image_url') or video_rel_path

        # Sync reels video to repo for Meta Graph API access
        self._sync_assets_to_repo([video_rel_path], f"instagram reels video {post_id}")

        result = self.publisher.publish_reel(post_data, video_rel_path)
        if result.get('success'):
            now_iso = datetime.now().isoformat()
            post_data['status'] = 'published'
            post_data['ig_media_id'] = result.get('ig_media_id')
            post_data['ig_permalink'] = result.get('ig_permalink')
            post_data['published_at'] = now_iso
            save_instagram_post(post_data)
            result['post'] = post_data
        result['video_engine'] = video_engine
        result['video_prompt'] = post_data.get('video_prompt', '')
        return result

    def process_comment_automations(self, test_comments: list = None) -> dict:
        """
        Processes comments on recent posts: auto-detects 'KUPON', 'LINK', 'FIYAT',
        replies publicly and sends custom direct messages.
        """
        self.reload_config()
        engine = InstagramEngagementEngine(gemini_api_key=self.config.get('gemini_api_key'))
        return engine.process_post_comments_and_dms(publisher=self.publisher, test_comments=test_comments)

    def generate_post(self, content_type: str = None, product_id: str = None) -> dict:
        """Alias for direct generation & immediate publishing (no drafts)."""
        res = self.generate_and_publish_now(content_type=content_type, product_id=product_id)
        return res.get('post') or {}

    def publish_post(self, post_id: str = None) -> dict:
        """
        Publishes an existing post if post_id is provided, otherwise generates and publishes directly.
        """
        if not post_id:
            return self.generate_and_publish_now()

        post = get_instagram_post_by_id(post_id)
        if not post:
            return {"success": False, "error": f"Gönderi bulunamadı: {post_id}"}

        self.reload_config()
        if not self.config.get('dry_run_mode', 0):
            paths_to_sync = post.get('slides') or [post.get('local_image_path')]
            self._sync_assets_to_repo(paths_to_sync, f"instagram post {post['id']}")

        # Ensure video_url is set for REEL posts (fallback to image_url for older posts without video_url column)
        if post.get('media_type') == 'REEL' and not post.get('video_url'):
            post['video_url'] = post.get('image_url', '')

        result = self.publisher.publish_post(post)
        now_iso = datetime.now().isoformat()
        if result.get('success'):
            update_instagram_post_status(
                post_id=post['id'],
                status='published',
                ig_media_id=result.get('ig_media_id'),
                ig_permalink=result.get('ig_permalink'),
                published_at=now_iso
            )
            next_run = self.calculate_next_run()

            update_agent_config({
                'last_run_at': now_iso,
                'next_run_at': next_run
            })
        result['post'] = get_instagram_post_by_id(post['id'])
        return result

    def run_autonomous_cycle(self, run_engagement: bool = True) -> dict:
        """
        Executes a complete autonomous cycle:
        1. Directly generates and publishes a new post (carousel or single).
        2. Publishes an accompanying 9:16 Story if enabled.
        3. Publishes an accompanying 9:16 Reel if enabled.
        4. Processes comment & DM automations ('KUPON', 'LINK', 'FIYAT').
        5. Engages with the drone community (follows up to 10 pilots & posts 10 comments).
        """
        self.reload_config()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INSTAGRAM AJANI] Instagram PR Ajani otonom dongu baslatiyor...")
        
        # 1. Post & Publish (with carousel support)
        import random
        if self.config.get('carousel_enabled', 1) and random.random() < 0.30:
            post_res = self.generate_and_publish_carousel()
        else:
            post_res = self.generate_and_publish_now()

        # 2. Accompanying Story
        story_res = {}
        if self.config.get('story_enabled', 1):
            try:
                story_res = self.generate_and_publish_story()
            except Exception as se:
                story_res = {"success": False, "error": str(se)}

        # 3. Accompanying Reel
        reel_res = {}
        if self.config.get('reels_enabled', 1):
            try:
                reel_res = self.generate_and_publish_reel()
            except Exception as re:
                reel_res = {"success": False, "error": str(re)}

        # 4. Comment & DM Automations
        dm_res = {}
        if self.config.get('dm_automation_enabled', 1):
            try:
                dm_res = self.process_comment_automations()
            except Exception as dme:
                dm_res = {"success": False, "error": str(dme)}

        # 5. Drone Community Engagement
        engagement_res = {}
        if run_engagement:
            try:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [TOPLULUK ETKİLEŞİMİ] Drone toplulugu etkilesim dongusu baslatiliyor (Hedef: 10 takip & 10 yorum)...")
                engine = InstagramEngagementEngine(gemini_api_key=self.config.get('gemini_api_key'))
                engagement_res = engine.run_daily_drone_engagement(target_count=10)
            except Exception as e:
                print(f"[UYARI] Etkilesim dongusu hatasi: {e}")
                engagement_res = {"success": False, "error": str(e)}

        # Ensure next_run_at is always pushed forward to prevent rapid re-trigger loops on API errors
        now_iso = datetime.now().isoformat()
        next_run = self.calculate_next_run()
        update_agent_config({
            'last_run_at': now_iso,
            'next_run_at': next_run
        })

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [TAMAMLANDI] Otonom dongu tamamlandi. Gonderi Durumu: {post_res.get('success')}. Sonraki plan: {next_run}")
        return {
            "success": post_res.get('success', False),
            "post_result": post_res,
            "story_result": story_res,
            "reel_result": reel_res,
            "dm_result": dm_res,
            "engagement_result": engagement_res
        }

    def get_posts(self, limit: int = 50, offset: int = 0, status: str = None) -> list:
        return get_instagram_posts(limit=limit, offset=offset, status=status)

    def delete_post(self, post_id: str) -> bool:
        post = get_instagram_post_by_id(post_id)
        if post and post.get('local_image_path'):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            file_path = os.path.join(base_dir, post['local_image_path'].lstrip('./'))
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
        return delete_instagram_post(post_id)
