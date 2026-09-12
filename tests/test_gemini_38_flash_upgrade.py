import unittest
import os
import json
import sqlite3
from PIL import Image

from reddit_agent.ai_engine import GeminiRedditEngine
from instagram_agent.content_generator import ContentGenerator
from instagram_agent.image_generator import ImageGenerator
from instagram_agent.agent import InstagramPRAgent
from instagram_agent.db import get_instagram_posts, save_instagram_post, init_instagram_tables
from orchestrator.lead_supervisor import LeadSupervisorAgent

class TestGemini38FlashUpgrade(unittest.TestCase):
    def setUp(self):
        init_instagram_tables()

    def test_all_agents_use_gemini_38_flash_as_primary(self):
        # 1. Lead Supervisor
        sup = LeadSupervisorAgent()
        self.assertEqual(sup.fallback_models[0], "gemini-3.8-flash")

        # 2. Reddit Engine
        reddit_engine = GeminiRedditEngine()
        self.assertEqual(reddit_engine.models[0], "gemini-3.8-flash")

        # 3. Instagram Content Generator
        content_gen = ContentGenerator()
        self.assertEqual(content_gen.models[0], "gemini-3.8-flash")

    def test_image_generator_audit_valid_banner(self):
        image_gen = ImageGenerator(width=1080, height=1080)
        post_data = {
            'id': 'test_audit_banner',
            'content_type': 'product_spotlight',
            'title': 'DJI O3 Air Unit HD Modul',
            'caption': '4K 60fps sinematik FPV goruntu iletimi stoklarda.',
            'hashtags': '#fpv #dji #pozitronmarket',
            'product_data': {
                'name_tr': 'DJI O3 Air Unit Dijital HD Modul',
                'brand': 'DJI',
                'price_try': 9950.0,
                'price_usd': 290.0,
                'discount_pct': 10,
                'specs': {'Sensör': '1/1.7 CMOS', 'Video': '4K@60fps'}
            },
            'visual_summary': {
                'badge': '[ONE CIKAN DONANIM]',
                'headline': 'DJI O3 Air Unit 4K HD',
                'subhead': 'Sinematik FPV Standartlarini Belirleyen Guc',
                'key_points': [
                    '[•] 4K@60fps Dahili RockSteady Kayit',
                    '[•] 10 km Dusuk Gecikmeli O3 Iletim',
                    '[•] Turkiye Yerel Stok & Hizli Kargo'
                ],
                'cta': '[PROFILDEKI LINKTEN HEMEN INCELE]'
            }
        }

        # Generate image
        img_rel_path = image_gen.generate_post_image(post_data)
        self.assertTrue(os.path.exists(img_rel_path))

        # Perform Gemini 3.8 Flash Vision Audit
        audit = image_gen.audit_generated_image(img_rel_path)
        self.assertIsInstance(audit, dict)
        self.assertEqual(audit.get("status"), "APPROVED")
        self.assertTrue(audit.get("is_valid"))
        self.assertEqual(audit.get("resolution"), "1080x1080")
        self.assertGreaterEqual(audit.get("quality_score", 0), 90)
        self.assertFalse(audit.get("emoji_detected"))
        self.assertIn("gemini-3.8-flash", audit.get("model_used"))

    def test_image_generator_audit_missing_file(self):
        image_gen = ImageGenerator()
        audit = image_gen.audit_generated_image("non_existent_file.jpg")
        self.assertEqual(audit.get("status"), "ERROR")
        self.assertFalse(audit.get("is_valid"))
        self.assertEqual(audit.get("quality_score"), 0)

    def test_visual_audit_persistence_in_db(self):
        post_data = {
            'id': 'test_audit_persistence_99',
            'content_type': 'product_spotlight',
            'title': 'SpeedyBee F405 V4 Stack',
            'caption': '55A ESC ve dahili Bluetooth ile sahada ayar.',
            'hashtags': '#speedybee #f405 #fpv',
            'image_url': './assets/instagram/posts/test_audit_persistence_99.jpg',
            'status': 'published',
            'metadata': {
                'visual_audit': {
                    'status': 'APPROVED',
                    'quality_score': 98,
                    'is_valid': True,
                    'model_used': 'gemini-3.8-flash'
                }
            }
        }
        save_instagram_post(post_data)

        posts = get_instagram_posts(limit=10)
        found = next((p for p in posts if p['id'] == 'test_audit_persistence_99'), None)
        self.assertIsNotNone(found)
        self.assertIn('visual_audit', found)
        self.assertEqual(found['visual_audit']['quality_score'], 98)
        self.assertEqual(found['visual_audit']['model_used'], 'gemini-3.8-flash')

if __name__ == '__main__':
    unittest.main()
