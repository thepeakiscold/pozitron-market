import unittest
import os
import sys
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from instagram_agent.db import (
    init_instagram_tables, get_agent_config, update_agent_config,
    save_instagram_post, get_instagram_posts, delete_instagram_post,
    get_instagram_post_by_id
)
from instagram_agent.content_generator import ContentGenerator
from instagram_agent.image_generator import ImageGenerator
from instagram_agent.meta_publisher import MetaPublisher
from instagram_agent.agent import InstagramPRAgent

class TestInstagramPRAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_instagram_tables()
        cls.original_config = get_agent_config()

    @classmethod
    def tearDownClass(cls):
        if cls.original_config:
            update_agent_config({
                'posting_frequency_hours': cls.original_config.get('posting_frequency_hours', 6),
                'dry_run_mode': cls.original_config.get('dry_run_mode', 0),
                'preferred_language': cls.original_config.get('preferred_language', 'tr'),
                'is_autonomous_enabled': cls.original_config.get('is_autonomous_enabled', 1)
            })

    def test_01_db_config(self):
        cfg = get_agent_config()
        self.assertIsNotNone(cfg)
        self.assertIn('posting_frequency_hours', cfg)

        updated = update_agent_config({'posting_frequency_hours': 8, 'preferred_language': 'tr'})
        self.assertEqual(updated['posting_frequency_hours'], 8)
        self.assertEqual(updated['preferred_language'], 'tr')

    def test_02_content_generation_all_pillars(self):
        cg = ContentGenerator()
        pillars = ['product_spotlight', 'tool_showcase', 'deal_drop', 'pilot_tip', 'review_highlight']
        for p in pillars:
            content = cg.generate_content(content_type=p)
            self.assertEqual(content['content_type'], p)
            self.assertTrue(len(content['title']) > 0, f"Title empty for {p}")
            self.assertTrue(len(content['caption']) > 20, f"Caption too short for {p}")
            self.assertTrue(len(content['hashtags']) > 5, f"Hashtags empty for {p}")
            self.assertIn('#', content['hashtags'])

    def test_03_image_generation(self):
        ig = ImageGenerator(width=1080, height=1080)
        cg = ContentGenerator()
        
        # Test product spotlight graphic
        prod_content = cg.generate_content(content_type='product_spotlight')
        prod_content['id'] = 'test_post_spotlight'
        img_path = ig.generate_post_image(prod_content)
        
        full_path = os.path.join(BASE_DIR, img_path.lstrip('./'))
        self.assertTrue(os.path.exists(full_path), f"File not found: {full_path}")
        
        with Image.open(full_path) as im:
            self.assertEqual(im.size, (1080, 1080))
            self.assertEqual(im.mode, 'RGB')
            
        # Clean up test image
        try:
            os.remove(full_path)
        except Exception:
            pass

    def test_04_meta_publisher_dry_run(self):
        pub = MetaPublisher(dry_run=True, public_base_url="https://pozitronmarket.com")
        mock_post = {
            'id': 'test_mock_001',
            'caption': 'Test caption for FPV drone',
            'hashtags': '#fpv #pozitron',
            'image_url': './assets/instagram/posts/test_mock_001.jpg'
        }
        res = pub.publish_post(mock_post)
        self.assertTrue(res['success'])
        self.assertEqual(res['mode'], 'dry_run')
        self.assertTrue(res['ig_media_id'].startswith('sim_ig_'))
        self.assertTrue(res['ig_permalink'].startswith('https://www.instagram.com/p/'))

    def test_05_agent_lifecycle(self):
        agent = InstagramPRAgent()
        # Ensure dry run
        agent.update_config({'dry_run_mode': 1})
        
        # 1. Generate & publish post directly (no drafts)
        res = agent.generate_and_publish_now(content_type='product_spotlight')
        self.assertTrue(res['success'])
        post = res['post']
        self.assertIsNotNone(post['id'])
        self.assertEqual(post['status'], 'published')
        self.assertIsNotNone(post.get('published_at'))
        
        # 3. Check DB status
        stored = get_instagram_post_by_id(post['id'])
        self.assertEqual(stored['status'], 'published')
        self.assertIsNotNone(stored['published_at'])
        
        # 4. Check status report
        status = agent.get_status()
        self.assertTrue(status['published_count'] >= 1)
        
        # 5. Clean up
        agent.delete_post(post['id'])
        self.assertIsNone(get_instagram_post_by_id(post['id']))

    def test_06_meta_publisher_expired_token_graceful_fallback(self):
        pub = MetaPublisher(
            access_token="INVALID_OR_EXPIRED_TOKEN_190",
            instagram_account_id="17841430407836914",
            dry_run=False,
            public_base_url="https://pozitronmarket.com"
        )
        is_valid, reason = pub.test_token()
        self.assertFalse(is_valid)

        # Publishing with invalid/expired token must fall back gracefully rather than crash
        mock_post = {
            'id': 'test_fallback_002',
            'caption': 'Fallback test caption',
            'hashtags': '#fpv #test',
            'image_url': './assets/instagram/posts/test_fallback_002.jpg'
        }
        res = pub.publish_post(mock_post)
        self.assertTrue(res['success'])
        self.assertEqual(res['mode'], 'simulation_fallback')
        self.assertTrue(res.get('token_expired'))
        self.assertTrue(res['ig_media_id'].startswith('sim_ig_'))

if __name__ == '__main__':
    unittest.main()
