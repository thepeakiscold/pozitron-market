import os
import time
import uuid
import random
import urllib.request
from datetime import datetime, timedelta
from .db import (
    get_agent_config, update_agent_config, save_instagram_post,
    update_instagram_post_status, get_instagram_posts,
    get_instagram_post_by_id, delete_instagram_post, init_instagram_tables,
    get_last_post_image_mode, get_recent_posted_content_types_by_media
)
from .content_generator import ContentGenerator
from .image_generator import ImageGenerator
from .image_generator import perceptual_hash, hamming_distance, VISUAL_PALETTES
from .stock_library import get_stock_image, resolve_path as resolve_stock_path, attribution_text as stock_attribution, recent_stock_files
from .flux_generator import FluxGenerator
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
        self.flux_gen = FluxGenerator()
        self.publisher = MetaPublisher(
            access_token=token,
            instagram_account_id=account_id,
            dry_run=is_dry_run,
            public_base_url=config.get('public_base_url', 'https://pozitronmarket.com')
        )
        self.scheduler = None
        self._last_palette = None
        self._last_combo_style = None

    # Coherent style -> palette mapping so visual theme and color palette match.
    STYLE_PALETTE = {
        'studio_neon': 'neon_purple',
        'golden_field': 'sunset_orange',
        'holo_lab': 'electric_blue',
        'mountain_dawn': 'forest_green',
        'clean_stage': 'mono_slate',
        'workshop_grit': 'sunset_orange',
        'night_city': 'neon_purple',
        'flatlay_slider': 'mono_slate',
    }

    def _pick_visual_palette(self, style_key: str = None) -> str:
        """Picks a background palette, avoiding the immediately previous one."""
        try:
            from .image_generator import VISUAL_PALETTES
            palettes = list(VISUAL_PALETTES.keys())
        except Exception:
            return 'carbon_cyan'
        if style_key and style_key in self.STYLE_PALETTE:
            return self.STYLE_PALETTE[style_key]
        options = [p for p in palettes if p != self._last_palette] or palettes
        chosen = random.choice(options)
        self._last_palette = chosen
        return chosen

    def _regenerate_if_duplicate(self, post_data: dict, img_rel_path: str, target_mode: str, gemini_key: str) -> str:
        """
        Computes an aHash for the generated image and, if it is too close to recent
        posts, regenerates once with a different palette. Returns the final hash.
        """
        try:
            current_hash = perceptual_hash(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), img_rel_path.lstrip('./').lstrip('/')))
            if not current_hash:
                return ''
            recent_hashes = []
            try:
                for p in get_instagram_posts(limit=15):
                    h = (p.get('metadata') or {}).get('image_hash')
                    if h:
                        recent_hashes.append(h)
            except Exception:
                recent_hashes = []

            min_dist = min([hamming_distance(current_hash, h) for h in recent_hashes], default=999)
            if post_data.get('content_form') == 'flux_photo':
                # FLUX images are unique per seed; skip the palette-based regen (expensive).
                return current_hash
            if min_dist <= 5:
                # Too similar -> try a different palette once.
                palettes = list(VISUAL_PALETTES.keys())
                alt = [p for p in palettes if p != post_data.get('visual_palette')]
                post_data['visual_palette'] = random.choice(alt) if alt else post_data.get('visual_palette')
                print(f"[CESITLILIK] Gorsel benzer bulundu (mesafe={min_dist}). Yeni palet ile yeniden uretiliyor: {post_data['visual_palette']}")
                try:
                    if post_data.get('content_form') == 'stock_photo':
                        alt_entry = get_stock_image(post_data.get('content_type', 'product_spotlight'), recent_files=recent_stock_files())
                        if alt_entry:
                            post_data['stock_file'] = alt_entry.get('file')
                            img_rel_path2 = self.image_gen.generate_stock_photo_post(post_data, resolve_stock_path(alt_entry))
                        else:
                            img_rel_path2 = self.image_gen.generate_post_image(post_data)
                    elif post_data.get('content_form') == 'text_poster':
                        img_rel_path2 = self.image_gen.generate_text_poster(post_data)
                    elif target_mode == 'gemini_image':
                        img_rel_path2 = self.image_gen.generate_gemini_ai_image(post_data, gemini_api_key=gemini_key)
                    else:
                        img_rel_path2 = self.image_gen.generate_post_image(post_data)
                    post_data['image_url'] = img_rel_path2
                    post_data['local_image_path'] = img_rel_path2
                    abs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), img_rel_path2.lstrip('./').lstrip('/'))
                    return perceptual_hash(abs_path) or current_hash
                except Exception:
                    return current_hash
            return current_hash
        except Exception:
            return ''

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
        self.content_gen.set_bilingual(self.config.get('bilingual_enabled', 0))
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
            "bilingual_enabled": bool(self.config.get('bilingual_enabled', 0)),
            "content_mix_enabled": bool(self.config.get('content_mix_enabled', 0)),
            "flux_enabled": bool(self.config.get('flux_enabled', 1)),
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
            target = calculate_next_peak_window(from_dt)
            # Human-like jitter (+/- up to 20 minutes) so posts never land on the exact same minute.
            target = target + timedelta(minutes=random.randint(-20, 20))
            return target.isoformat()
        freq_hours = self.config.get('posting_frequency_hours', 6)
        target = from_dt + timedelta(hours=freq_hours) + timedelta(minutes=random.randint(-10, 10))
        return target.isoformat()

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
            "bilingual_enabled": bool(self.config.get('bilingual_enabled', 0)),
            "content_mix_enabled": bool(self.config.get('content_mix_enabled', 0)),
            "flux_enabled": bool(self.config.get('flux_enabled', 1)),
            "last_run_at": self.config.get('last_run_at'),
            "next_run_at": self.config.get('next_run_at')
        }

    def update_config(self, updates: dict) -> dict:
        clean_updates = {}
        for k in [
            'instagram_account_id', 'is_autonomous_enabled', 'posting_frequency_hours',
            'dry_run_mode', 'public_base_url', 'preferred_language', 'default_hashtags',
            'story_enabled', 'carousel_enabled', 'dm_automation_enabled',
            'peak_scheduler_enabled', 'reels_enabled', 'bilingual_enabled', 'content_mix_enabled',
            'flux_enabled'
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
            'visual_palette': self._pick_visual_palette(content.get('visual_style_key')),
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

        # Visual form rotation: local FLUX AI photo, copyright-free stock photo,
        # bold typographic poster, or the standard product/info card.
        use_flux = False
        try:
            flux_prob = float(os.environ.get('FLUX_PROBABILITY') or self.config.get('flux_probability', 0.25))
        except Exception:
            flux_prob = 0.25
        flux_selected = self.config.get('flux_enabled', 1) and random.random() < flux_prob
        if flux_selected and self.flux_gen.ensure_server():
            use_flux = True

        stock_entry = None
        if not use_flux and random.random() < 0.30:
            stock_entry = get_stock_image(temp_post_data['content_type'], recent_files=recent_stock_files())
        use_text_poster = (not use_flux) and (not stock_entry) and (not temp_post_data.get('product_data')) and random.random() < 0.15
        temp_post_data['content_form'] = (
            'flux_photo' if use_flux else ('stock_photo' if stock_entry else ('text_poster' if use_text_poster else 'card'))
        )

        if use_flux:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [INSTAGRAM AJANI] Yerel FLUX AI ile gorsel uretiliyor (bu 40-90 sn surebilir)...")
            try:
                import os as _os
                flux_info = self.flux_gen.generate_for_post(temp_post_data, post_id, steps=int(_os.environ.get('FLUX_STEPS', '20')))
            except Exception as fe:
                flux_info = {"path": "", "prompt": "", "error": str(fe)}
            if flux_info.get('path') and _os.path.exists(flux_info['path']):
                img_rel_path = self.image_gen.generate_flux_photo_post(temp_post_data, flux_info['path'])
                try:
                    _os.remove(flux_info['path'])  # raw AI render not needed after overlay
                except Exception:
                    pass
                temp_post_data['flux_prompt'] = flux_info.get('prompt')
                if not isinstance(temp_post_data.get('metadata'), dict):
                    temp_post_data['metadata'] = {}
                temp_post_data['metadata']['flux_prompt'] = flux_info.get('prompt')
                # Meta AI-content disclosure
                temp_post_data['caption'] = f"{temp_post_data.get('caption', '').rstrip()}\n\n[AI GORSEL] Bu gorsel yapay zeka ile uretilmistir."
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [INSTAGRAM AJANI] FLUX uretimi basarisiz, standart karta donuluyor.")
                temp_post_data['content_form'] = 'card'
                img_rel_path = self.image_gen.generate_post_image(temp_post_data)
        elif stock_entry:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [INSTAGRAM AJANI] Telifsiz stok gorsel kullaniliyor ({stock_entry.get('category')}).")
            img_rel_path = self.image_gen.generate_stock_photo_post(temp_post_data, resolve_stock_path(stock_entry))
            temp_post_data['stock_file'] = stock_entry.get('file')
            temp_post_data['stock_license'] = stock_entry.get('license')
            temp_post_data['stock_source'] = stock_entry.get('source')
            credit = stock_attribution(stock_entry)
            if credit:
                temp_post_data['caption'] = f"{temp_post_data.get('caption', '').rstrip()}\n\n[GORSEL KAYNAK] {credit}"
        elif use_text_poster:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [INSTAGRAM AJANI] Tipografik poster formati secildi. Gorsel hazirlaniyor...")
            img_rel_path = self.image_gen.generate_text_poster(temp_post_data)
        elif target_mode == 'gemini_image':
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [INSTAGRAM AJANI] Gemini AI Image modu secildi (Her 2 postta bir). Gorsel uretiliyor...")
            img_rel_path = self.image_gen.generate_gemini_ai_image(temp_post_data, gemini_api_key=gemini_key)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [INSTAGRAM AJANI] Canvas Banner modu secildi. Gorsel hazirlaniyor...")
            img_rel_path = self.image_gen.generate_post_image(temp_post_data)

        temp_post_data['image_url'] = img_rel_path
        temp_post_data['local_image_path'] = img_rel_path

        # 2.05 Near-duplicate visual guard: if the aHash is too close to recent posts,
        # regenerate once with a different palette so the feed does not look identical.
        img_hash = self._regenerate_if_duplicate(temp_post_data, img_rel_path, target_mode, gemini_key)
        img_rel_path = temp_post_data.get('local_image_path', img_rel_path)
        if not isinstance(temp_post_data.get('metadata'), dict):
            temp_post_data['metadata'] = {}
        if img_hash:
            temp_post_data['image_hash'] = img_hash
            temp_post_data['metadata']['image_hash'] = img_hash
        if stock_entry:
            temp_post_data['metadata']['stock_file'] = stock_entry.get('file')
            temp_post_data['metadata']['stock_license'] = stock_entry.get('license')

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
            'visual_palette': self._pick_visual_palette('clean_stage'),
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
            story_candidate_types = [
                'deal_drop', 'pilot_tip', 'hardware_battle', 'mistake_breakdown',
                'community_quiz', 'product_spotlight', 'flight_weather_radar',
                'myth_buster', 'maintenance_checklist', 'beginner_roadmap', 'review_highlight'
            ]
            recent_story_types = get_recent_posted_content_types_by_media('STORIES', limit=3)
            candidates = [t for t in story_candidate_types if t not in recent_story_types[:2]] or story_candidate_types
            st_type = random.choice(candidates)
            content = self.content_gen.generate_content(content_type=st_type)
            post_data = {
                'id': post_id,
                'content_type': content.get('content_type', st_type),
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
        if not post_data.get('visual_palette'):
            post_data['visual_palette'] = self._pick_visual_palette()
        # Sometimes use a copyright-free photo as the story background.
        story_stock = None
        if random.random() < 0.40:
            story_stock = get_stock_image(post_data.get('content_type', 'product_spotlight'), recent_files=recent_stock_files())
        if story_stock:
            story_rel_path = self.image_gen.generate_stock_story(post_data, resolve_stock_path(story_stock))
            post_data['stock_file'] = story_stock.get('file')
        else:
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

        The Reel theme is now ROTATED across many pillars (quiz, battle, tip, build, myth-buster,
        maintenance, spot guide, weather, deal, etc.) instead of always being product_spotlight.
        """
        self.reload_config()
        post_id = f"ig_reel_{uuid.uuid4().hex[:12]}"

        if not post_data:
            content = self.content_gen.generate_reels_content()
            if not content:
                return {"success": False, "error": "Reels icerigi uretilemedi."}
            post_data = {
                'id': post_id,
                'content_type': content.get('content_type', 'product_spotlight'),
                'title': content['title'],
                'caption': content['caption'],
                'hashtags': content['hashtags'],
                'product_data': content.get('product_data'),
                'visual_summary': content.get('visual_summary'),
                'visual_style': content.get('visual_style'),
                'visual_style_key': content.get('visual_style_key'),
                'video_mode': content.get('video_mode'),
                'reel_combo': content.get('reel_combo'),
                'hook_tone': content.get('hook_tone'),
                'created_at': datetime.now().isoformat()
            }
        else:
            post_data = dict(post_data)
            post_data['id'] = post_id

        post_data['media_type'] = 'REEL'

        # Rotating palette + variable Reel length/transition for format diversity.
        if not post_data.get('visual_palette'):
            post_data['visual_palette'] = self._pick_visual_palette(post_data.get('visual_style_key'))
        if not post_data.get('reel_slide_dur'):
            post_data['reel_slide_dur'] = random.choice([2.5, 3.0, 3.5, 4.0])
        if not post_data.get('reel_transition'):
            post_data['reel_transition'] = random.choice(
                ['wipeleft', 'slideleft', 'smoothleft', 'circleopen', 'fade', 'wiperight']
            )

        # Apply the chosen combination's video mode as the generation engine.
        if not post_data.get('engine'):
            video_mode = post_data.get('video_mode')
            if video_mode:
                post_data['engine'] = video_mode
            elif not post_data.get('product_data'):
                # Themed (non-product) Reels have no product card, so use the multi-slide template.
                post_data['engine'] = 'mode1'

        # Persist combination info into metadata for later anti-repeat checks.
        meta = post_data.get('metadata') if isinstance(post_data.get('metadata'), dict) else {}
        meta['reel_combo'] = post_data.get('reel_combo')
        meta['visual_style'] = post_data.get('visual_style')
        meta['video_mode'] = post_data.get('video_mode')
        meta['hook_tone'] = post_data.get('hook_tone')
        post_data['metadata'] = meta

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

        # Optional content-mix mode: stagger Story/Reel instead of always posting all three,
        # so the account does not look like a repetitive trio-drop.
        mix_enabled = bool(self.config.get('content_mix_enabled', 0))

        # 2. Accompanying Story
        story_res = {}
        post_story = self.config.get('story_enabled', 1) and (not mix_enabled or random.random() < 0.75)
        if post_story:
            try:
                story_res = self.generate_and_publish_story()
            except Exception as se:
                story_res = {"success": False, "error": str(se)}

        # 3. Accompanying Reel
        reel_res = {}
        post_reel = self.config.get('reels_enabled', 1) and (not mix_enabled or random.random() < 0.85)
        if post_reel:
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
