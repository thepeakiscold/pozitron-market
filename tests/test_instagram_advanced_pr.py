import os
import unittest
from datetime import datetime, timedelta
from instagram_agent.db import (
    init_instagram_tables, get_agent_config, update_agent_config,
    save_instagram_post, get_instagram_post_by_id,
    record_comment_interaction, is_comment_processed, get_recent_comment_interactions
)
from instagram_agent.content_generator import ContentGenerator
from instagram_agent.image_generator import ImageGenerator
from instagram_agent.meta_publisher import MetaPublisher
from instagram_agent.engagement import InstagramEngagementEngine
from instagram_agent.scheduler import calculate_next_peak_window
from instagram_agent.agent import InstagramPRAgent

class TestInstagramAdvancedPR(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_instagram_tables()
        cfg = get_agent_config()
        cls._orig_dry_run = cfg.get('dry_run_mode', 0)
        update_agent_config({'dry_run_mode': 1})

    @classmethod
    def tearDownClass(cls):
        update_agent_config({'dry_run_mode': getattr(cls, '_orig_dry_run', 0)})

    def setUp(self):
        init_instagram_tables()
        self.agent = InstagramPRAgent()
        self.content_gen = ContentGenerator()
        self.image_gen = ImageGenerator(width=1080, height=1080)
        self.publisher = MetaPublisher(dry_run=True)
        self.engagement_engine = InstagramEngagementEngine()

    def test_01_db_schema_and_config_fields(self):
        """Verify advanced PR config fields and comment interaction tracking."""
        updated = update_agent_config({
            'story_enabled': 1,
            'carousel_enabled': 1,
            'dm_automation_enabled': 1,
            'peak_scheduler_enabled': 1,
            'reels_enabled': 1
        })
        self.assertEqual(updated.get('story_enabled'), 1)
        self.assertEqual(updated.get('carousel_enabled'), 1)
        self.assertEqual(updated.get('dm_automation_enabled'), 1)
        self.assertEqual(updated.get('peak_scheduler_enabled'), 1)
        self.assertEqual(updated.get('reels_enabled'), 1)

        # Comment interaction recording
        test_c_id = f"test_comm_{int(datetime.now().timestamp())}"
        self.assertFalse(is_comment_processed(test_c_id))
        ok = record_comment_interaction(
            comment_id=test_c_id,
            user_id="12345",
            username="test_pilot",
            keyword="KUPON",
            reply_text="Harika! DM kutuna kupon gonderdik.",
            dm_status="sent"
        )
        self.assertTrue(ok)
        self.assertTrue(is_comment_processed(test_c_id))

        recent = get_recent_comment_interactions(limit=5)
        self.assertTrue(any(r['comment_id'] == test_c_id for r in recent))

    def test_02_carousel_content_and_image_generation(self):
        """Verify carousel_guide content and 4-slide image generation."""
        content = self.content_gen.generate_content(content_type='carousel_guide')
        self.assertEqual(content['content_type'], 'carousel_guide')
        self.assertEqual(content['media_type'], 'CAROUSEL')
        self.assertTrue(len(content['title']) > 5)
        self.assertIn("Yoruma", content['caption'])

        post_data = {
            'id': f"test_car_{int(datetime.now().timestamp())}",
            'content_type': 'carousel_guide',
            'media_type': 'CAROUSEL',
            'title': content['title'],
            'caption': content['caption'],
            'hashtags': content['hashtags'],
            'visual_summary': content.get('visual_summary'),
            'product_data': None,
            'created_at': datetime.now().isoformat()
        }

        slides = self.image_gen.generate_carousel_slides(post_data)
        self.assertEqual(len(slides), 4)
        for s in slides:
            clean_p = s.lstrip('./').lstrip('/')
            abs_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), clean_p)
            self.assertTrue(os.path.exists(abs_p), f"Slide file missing: {abs_p}")

    def test_03_story_image_generation(self):
        """Verify 9:16 vertical Story graphic generation."""
        post_data = {
            'id': f"test_story_{int(datetime.now().timestamp())}",
            'content_type': 'deal_drop',
            'title': '[KAMPANYA] FPV Donanim Firsati',
            'caption': 'Firsati kacirmayin!',
            'hashtags': '#fpvturkey',
            'visual_summary': {
                'key_points': [
                    '[ORIJINAL] 100% Orijinal Urun',
                    '[HIZLI] Ayni Gun Hizli Kargo',
                    '[DESTEK] Uzman Teknik Ekip'
                ]
            }
        }
        story_path = self.image_gen.generate_story_image(post_data)
        self.assertTrue(story_path.endswith('_story.jpg'))
        abs_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), story_path.lstrip('./').lstrip('/'))
        self.assertTrue(os.path.exists(abs_p), f"Story file missing: {abs_p}")

        # Check image dimensions
        from PIL import Image
        with Image.open(abs_p) as im:
            self.assertEqual(im.size, (1080, 1920))

    def test_04_reels_video_generation(self):
        """Verify 9:16 Reels video generation via ffmpeg."""
        post_data = {
            'id': f"test_reel_{int(datetime.now().timestamp())}",
            'content_type': 'pilot_tip',
            'title': '[REELS] FPV Motor Bakimi',
            'caption': 'Motorlarinizi koruyun!',
            'hashtags': '#fpvturkey',
            'visual_summary': {
                'key_points': ['[TEMIZLIK] Izopropil Alkol', '[YAGLAMA] Sentetik Yag']
            }
        }
        video_path = self.image_gen.generate_reels_video(post_data)
        if video_path:
            self.assertTrue(video_path.endswith('.mp4'))
            abs_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), video_path.lstrip('./').lstrip('/'))
            self.assertTrue(os.path.exists(abs_p))
            self.assertGreater(os.path.getsize(abs_p), 1000)

    def test_05_no_third_party_posts(self):
        """Verify 3rd-party community spotlights ('Pilot Masasi') are excluded and content focuses on 1st-party products/tools."""
        # Generate 15 random contents and verify none are pilot_spotlight / 3rd party
        for _ in range(15):
            content = self.content_gen.generate_content()
            self.assertNotEqual(content.get('content_type'), 'pilot_spotlight')
            self.assertNotIn("PILOT MASASI", content.get('title', ''))
            self.assertNotIn("Gokturk IHA Takimi", content.get('title', ''))

    def test_06_comment_and_dm_automation_engine(self):
        """Verify keyword detection and automatic DM dispatch."""
        test_c_id = f"kw_comm_{int(datetime.now().timestamp())}"
        test_comments = [
            {
                'id': test_c_id,
                'text': 'Kupon kodunu alabilir miyim? Harika setup!',
                'user_id': '987654321',
                'username': 'fpv_pilot_ali'
            },
            {
                'id': f"other_{int(datetime.now().timestamp())}",
                'text': 'Harika ucus elinize saglik',
                'user_id': '111222333',
                'username': 'mehmet_fpv'
            }
        ]

        res = self.engagement_engine.process_post_comments_and_dms(publisher=self.publisher, test_comments=test_comments)
        self.assertTrue(res['success'])
        self.assertEqual(res['processed_comments'], 1)
        self.assertEqual(res['replies_sent'], 1)
        self.assertEqual(res['dms_sent'], 1)
        self.assertTrue(is_comment_processed(test_c_id))

        # Second run should skip already processed comments
        res2 = self.engagement_engine.process_post_comments_and_dms(publisher=self.publisher, test_comments=test_comments)
        self.assertEqual(res2['processed_comments'], 0)

    def test_07_peak_time_scheduler(self):
        """Verify Turkish FPV community peak window calculation."""
        # Test from Monday 10:00 TRT
        monday_dt = datetime(2026, 9, 21, 10, 0, 0)
        next_peak = calculate_next_peak_window(monday_dt)
        self.assertGreater(next_peak, monday_dt)
        # Should target evening window (20:00) on Monday
        self.assertEqual(next_peak.hour, 20)
        self.assertEqual(next_peak.day, 21)

        # Test from Saturday 09:00 TRT
        sat_dt = datetime(2026, 9, 26, 9, 0, 0)
        next_sat_peak = calculate_next_peak_window(sat_dt)
        self.assertGreater(next_sat_peak, sat_dt)
        # Should target weekend midday window (12:30)
        self.assertEqual(next_sat_peak.hour, 12)
        self.assertEqual(next_sat_peak.minute, 30)

    def test_08_publisher_multimedia_publishing(self):
        """Verify MetaPublisher carousel, story, reel, reply, and DM dry-run methods."""
        post_data = {
            'id': 'test_pub_all',
            'caption': 'Test caption',
            'hashtags': '#test',
            'image_url': './assets/instagram/posts/test.jpg'
        }

        # Carousel
        car_res = self.publisher.publish_carousel(post_data, ['./assets/slide1.jpg', './assets/slide2.jpg'])
        self.assertTrue(car_res['success'])
        self.assertEqual(car_res['media_type'], 'CAROUSEL')

        # Story
        story_res = self.publisher.publish_story(post_data, './assets/story.jpg')
        self.assertTrue(story_res['success'])
        self.assertEqual(story_res['media_type'], 'STORIES')

        # Reel
        reel_res = self.publisher.publish_reel(post_data, './assets/reel.mp4')
        self.assertTrue(reel_res['success'])
        self.assertEqual(reel_res['media_type'], 'REELS')

        # Reply to comment
        reply_res = self.publisher.reply_to_comment('comm_123', 'Selam pilot!')
        self.assertTrue(reply_res['success'])

        # Send DM
        dm_res = self.publisher.send_direct_message('user_123', 'Kuponun: POZITRON10')
        self.assertTrue(dm_res['success'])

    def test_09_agent_direct_methods(self):
        """Verify agent carousel, story, reel, and dm processing methods."""
        # 1. Carousel
        car_res = self.agent.generate_and_publish_carousel()
        self.assertTrue(car_res['success'])
        self.assertIn('slides', car_res['post'].get('metadata', {}))

        # 2. Story
        story_res = self.agent.generate_and_publish_story()
        self.assertTrue(story_res['success'])
        self.assertEqual(story_res['post']['media_type'], 'STORIES')

        # 3. Comment Automations
        test_comments = [{
            'id': f"agent_comm_{int(datetime.now().timestamp())}",
            'text': 'Fiyat nedir acaba link atar misiniz',
            'user_id': '888777',
            'username': 'ahmet_pilot'
        }]
        dm_res = self.agent.process_comment_automations(test_comments=test_comments)
        self.assertTrue(dm_res['success'])
        self.assertEqual(dm_res['processed_comments'], 1)

    def test_10_autonomous_cycle_includes_reel_and_story(self):
        """Verify run_autonomous_cycle triggers reel and story when enabled."""
        update_agent_config({
            'story_enabled': 1,
            'reels_enabled': 1,
            'carousel_enabled': 0,
            'dm_automation_enabled': 0
        })
        cycle_res = self.agent.run_autonomous_cycle(run_engagement=False)
        self.assertTrue(cycle_res['success'])
        self.assertIn('story_result', cycle_res)
        self.assertIn('reel_result', cycle_res)
        self.assertTrue(cycle_res['story_result'].get('success'))
        self.assertTrue(cycle_res['reel_result'].get('success'))

    def test_11_sync_assets_to_repo(self):
        """Verify _sync_assets_to_repo helper handles empty and dry-run paths safely."""
        # Empty paths
        self.assertTrue(self.agent._sync_assets_to_repo([], "empty test"))
        # Dry run mode
        self.agent.config['dry_run_mode'] = 1
        self.assertTrue(self.agent._sync_assets_to_repo(['./assets/test.jpg'], "dry run test"))

    def test_12_token_expired_error_classification(self):
        """Verify _is_token_expired_error only flags actual token issues and not general 400s."""
        from urllib.error import HTTPError
        from io import BytesIO

        # Actual expired token (code 190)
        body_190 = b'{"error":{"message":"Error validating access token: Session has expired","code":190}}'
        err_190 = HTTPError('http://test', 400, 'Bad Request', {}, BytesIO(body_190))
        self.assertTrue(self.publisher._is_token_expired_error(err_190))

        # Image download error (code 2207001) - should NOT be treated as expired token
        body_img = b'{"error":{"message":"Failed to download media: 404 Not Found","code":2207001}}'
        err_img = HTTPError('http://test', 400, 'Bad Request', {}, BytesIO(body_img))
        self.assertFalse(self.publisher._is_token_expired_error(err_img))

    def test_13_new_content_types_and_visual_themes(self):
        """Verify drone_build_showcase, flight_weather_radar, and spot_guide generation and image rendering."""
        # 1. Drone Build Showcase
        build_content = self.content_gen.generate_content(content_type='drone_build_showcase')
        self.assertEqual(build_content['content_type'], 'drone_build_showcase')
        self.assertIn('visual_summary', build_content)
        build_post = {
            'id': f"test_build_{int(datetime.now().timestamp())}",
            'content_type': 'drone_build_showcase',
            'title': build_content['title'],
            'caption': build_content['caption'],
            'hashtags': build_content['hashtags'],
            'visual_summary': build_content['visual_summary'],
            'created_at': datetime.now().isoformat()
        }
        build_img_path = self.image_gen.generate_post_image(build_post)
        self.assertTrue(build_img_path.endswith('.jpg'))
        abs_build_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), build_img_path.lstrip('./').lstrip('/'))
        self.assertTrue(os.path.exists(abs_build_p))

        # 2. Flight Weather Radar
        weather_content = self.content_gen.generate_content(content_type='flight_weather_radar')
        self.assertEqual(weather_content['content_type'], 'flight_weather_radar')
        self.assertIn('RADARI', weather_content['title'])
        self.assertIn('visual_summary', weather_content)
        weather_post = {
            'id': f"test_weather_{int(datetime.now().timestamp())}",
            'content_type': 'flight_weather_radar',
            'title': weather_content['title'],
            'caption': weather_content['caption'],
            'hashtags': weather_content['hashtags'],
            'visual_summary': weather_content['visual_summary'],
            'created_at': datetime.now().isoformat()
        }
        weather_img_path = self.image_gen.generate_post_image(weather_post)
        self.assertTrue(weather_img_path.endswith('.jpg'))
        abs_weather_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), weather_img_path.lstrip('./').lstrip('/'))
        self.assertTrue(os.path.exists(abs_weather_p))

        # 3. Spot Guide
        spot_content = self.content_gen.generate_content(content_type='spot_guide')
        self.assertEqual(spot_content['content_type'], 'spot_guide')
        self.assertIn('visual_summary', spot_content)
        spot_post = {
            'id': f"test_spot_{int(datetime.now().timestamp())}",
            'content_type': 'spot_guide',
            'title': spot_content['title'],
            'caption': spot_content['caption'],
            'hashtags': spot_content['hashtags'],
            'visual_summary': spot_content['visual_summary'],
            'created_at': datetime.now().isoformat()
        }
        spot_img_path = self.image_gen.generate_post_image(spot_post)
        self.assertTrue(spot_img_path.endswith('.jpg'))

        # 4. Gemini AI Image fallback (offline / no key)
        ai_fallback_path = self.image_gen.generate_gemini_ai_image(build_post, gemini_api_key=None)
        self.assertTrue(ai_fallback_path.endswith('.jpg'))
        abs_fallback_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ai_fallback_path.lstrip('./').lstrip('/'))
        self.assertTrue(os.path.exists(abs_fallback_p))

if __name__ == '__main__':
    unittest.main()
