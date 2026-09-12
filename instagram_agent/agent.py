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

class InstagramPRAgent:
    def __init__(self):
        init_instagram_tables()
        config = get_agent_config()
        self.config = config

        self.content_gen = ContentGenerator(gemini_api_key=config.get('gemini_api_key', ''))
        self.image_gen = ImageGenerator(width=1080, height=1080)
        self.publisher = MetaPublisher(
            access_token=config.get('access_token', ''),
            instagram_account_id=config.get('instagram_account_id', ''),
            dry_run=bool(config.get('dry_run_mode', 1)),
            public_base_url=config.get('public_base_url', 'https://pozitronmarket.com')
        )
        self.scheduler = None

    def reload_config(self):
        self.config = get_agent_config()
        self.content_gen.set_api_key(self.config.get('gemini_api_key', ''))
        self.publisher.configure(
            access_token=self.config.get('access_token', ''),
            instagram_account_id=self.config.get('instagram_account_id', ''),
            dry_run=bool(self.config.get('dry_run_mode', 1)),
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

    def generate_post(self, content_type: str = None, product_id: str = None) -> dict:
        """
        Creates a new post draft with generated caption, hashtags, and 1080x1080 image.
        """
        post_id = f"ig_post_{uuid.uuid4().hex[:12]}"
        
        # 1. Generate text and metadata
        content = self.content_gen.generate_content(content_type=content_type, product_id=product_id)
        
        # 2. Package post data
        post_data = {
            'id': post_id,
            'content_type': content['content_type'],
            'product_id': content.get('product_id'),
            'title': content['title'],
            'caption': content['caption'],
            'hashtags': content['hashtags'],
            'status': 'draft',
            'product_data': content.get('product_data'),
            'tool_info': content.get('tool_info'),
            'created_at': datetime.now().isoformat()
        }

        # 3. Generate visual banner (1080x1080)
        img_rel_path = self.image_gen.generate_post_image(post_data)
        post_data['image_url'] = img_rel_path
        post_data['local_image_path'] = img_rel_path

        # 4. Save draft in database
        save_instagram_post(post_data)

        return post_data

    def publish_post(self, post_id: str = None) -> dict:
        """
        Publishes post either to Instagram or in dry-run mode.
        If post_id is None, finds the latest draft or generates a new one.
        """
        post = None
        if post_id:
            post = get_instagram_post_by_id(post_id)
        else:
            drafts = get_instagram_posts(limit=1, status='draft')
            if drafts:
                post = drafts[0]
            else:
                post = self.generate_post()

        if not post:
            return {"success": False, "error": "Paylaşılacak gönderi bulunamadı."}

        # Publish via MetaPublisher
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
            # Update next run calculation
            freq_hours = self.config.get('posting_frequency_hours', 12)
            next_run = (datetime.now() + timedelta(hours=freq_hours)).isoformat()
            update_agent_config({
                'last_run_at': now_iso,
                'next_run_at': next_run
            })
        else:
            update_instagram_post_status(
                post_id=post['id'],
                status='failed',
                error_message=result.get('error', 'Bilinmeyen hata')
            )

        result['post'] = get_instagram_post_by_id(post['id'])
        return result

    def run_autonomous_cycle(self) -> dict:
        """
        Executes a single autonomous run: picks candidate, generates post, and publishes.
        """
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🤖 Instagram PR Ajanı otonom döngü başlatıyor...")
        draft = self.generate_post()
        res = self.publish_post(draft['id'])
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ✅ Otonom döngü tamamlandı. Durum: {res.get('success')}")
        return res

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
