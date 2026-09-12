import os
import uuid
from datetime import datetime, timedelta
from .db import (
    get_agent_config, update_agent_config, save_instagram_post,
    update_instagram_post_status, get_instagram_posts,
    get_instagram_post_by_id, delete_instagram_post, init_instagram_tables
)
from .content_generator import ContentGenerator
from .image_generator import ImageGenerator
from .meta_publisher import MetaPublisher
from .engagement import InstagramEngagementEngine

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
        self.image_gen = ImageGenerator(width=1080, height=1080)
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
            "last_run_at": self.config.get('last_run_at'),
            "next_run_at": self.config.get('next_run_at'),
            "total_posts": len(posts),
            "published_count": published_count,
            "draft_count": draft_count,
            "failed_count": failed_count,
            "has_credentials": bool(self.config.get('access_token') and self.config.get('instagram_account_id'))
        }

    def get_safe_config(self) -> dict:
        self.reload_config()
        token = self.config.get('access_token', '')
        masked_token = f"{token[:6]}...{token[-4:]}" if len(token) > 10 else ("***" if token else "")
        gemini_key = self.config.get('gemini_api_key', '')
        masked_gemini = f"{gemini_key[:4]}...{gemini_key[-4:]}" if len(gemini_key) > 8 else ("***" if gemini_key else "")

        return {
            "access_token_masked": masked_token,
            "has_access_token": bool(token),
            "instagram_account_id": self.config.get('instagram_account_id', ''),
            "gemini_api_key_masked": masked_gemini,
            "has_gemini_key": bool(gemini_key),
            "is_autonomous_enabled": bool(self.config.get('is_autonomous_enabled', 0)),
            "posting_frequency_hours": self.config.get('posting_frequency_hours', 12),
            "dry_run_mode": bool(self.config.get('dry_run_mode', 1)),
            "public_base_url": self.config.get('public_base_url', 'https://pozitronmarket.com'),
            "preferred_language": self.config.get('preferred_language', 'tr'),
            "default_hashtags": self.config.get('default_hashtags', '')
        }

    def update_config(self, updates: dict) -> dict:
        clean_updates = {}
        for k in ['instagram_account_id', 'is_autonomous_enabled', 'posting_frequency_hours', 'dry_run_mode', 'public_base_url', 'preferred_language', 'default_hashtags']:
            if k in updates:
                clean_updates[k] = updates[k]

        # Only update tokens if non-empty and not masked
        if 'access_token' in updates and updates['access_token'] and '...' not in updates['access_token']:
            clean_updates['access_token'] = updates['access_token']
        if 'gemini_api_key' in updates and updates['gemini_api_key'] and '...' not in updates['gemini_api_key']:
            clean_updates['gemini_api_key'] = updates['gemini_api_key']

        res = update_agent_config(clean_updates)
        self.reload_config()

        # Update scheduler state if changed
        if self.scheduler:
            if clean_updates.get('is_autonomous_enabled'):
                self.scheduler.start()
            elif clean_updates.get('is_autonomous_enabled') is False:
                self.scheduler.stop()

        return self.get_safe_config()

    def generate_and_publish_now(self, content_type: str = None, product_id: str = None) -> dict:
        """
        Creates a new post and DIRECTLY publishes it to Instagram (Meta API or dry-run).
        Never leaves a draft behind.
        """
        post_id = f"ig_post_{uuid.uuid4().hex[:12]}"
        
        # 1. Generate text and metadata
        content = self.content_gen.generate_content(content_type=content_type, product_id=product_id)
        
        # 2. Generate visual banner (1080x1080)
        temp_post_data = {
            'id': post_id,
            'content_type': content['content_type'],
            'product_id': content.get('product_id'),
            'title': content['title'],
            'caption': content['caption'],
            'hashtags': content['hashtags'],
            'product_data': content.get('product_data'),
            'tool_info': content.get('tool_info'),
            'created_at': datetime.now().isoformat()
        }
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

            # Update schedule timings
            freq_hours = self.config.get('posting_frequency_hours', 6)
            next_run = (datetime.now() + timedelta(hours=freq_hours)).isoformat()
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
            freq_hours = self.config.get('posting_frequency_hours', 6)
            next_run = (datetime.now() + timedelta(hours=freq_hours)).isoformat()
            update_agent_config({
                'last_run_at': now_iso,
                'next_run_at': next_run
            })
        result['post'] = get_instagram_post_by_id(post['id'])
        return result

    def run_autonomous_cycle(self, run_engagement: bool = True) -> dict:
        """
        Executes a complete autonomous cycle:
        1. Directly generates and publishes a new post (no drafts).
        2. Engages with the drone community (follows up to 10 pilots & posts 10 comments).
        """
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [INSTAGRAM AJANI] Instagram PR Ajani otonom dongu baslatiyor...")
        
        # 1. Direct Post & Publish
        post_res = self.generate_and_publish_now()
        
        # 2. Drone Community Engagement
        engagement_res = {}
        if run_engagement:
            try:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [TOPLULUK ETKİLEŞİMİ] Drone toplulugu etkilesim dongusu baslatiliyor (Hedef: 10 takip & 10 yorum)...")
                engine = InstagramEngagementEngine(gemini_api_key=self.config.get('gemini_api_key'))
                engagement_res = engine.run_daily_drone_engagement(target_count=10)
            except Exception as e:
                print(f"[UYARI] Etkilesim dongusu hatasi: {e}")
                engagement_res = {"success": False, "error": str(e)}

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [TAMAMLANDI] Otonom dongu tamamlandi. Gonderi Durumu: {post_res.get('success')}")
        return {
            "success": post_res.get('success', False),
            "post_result": post_res,
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
