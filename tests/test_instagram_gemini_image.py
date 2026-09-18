import unittest
import os
import sys
from PIL import Image

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from instagram_agent.agent import InstagramPRAgent
from instagram_agent.image_generator import ImageGenerator
from instagram_agent.db import get_last_post_image_mode, get_instagram_posts, init_instagram_tables

class TestInstagramGeminiImage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_instagram_tables()
        cls.agent = InstagramPRAgent()
        cls.agent.update_config({'dry_run_mode': 1})
        cls.image_gen = ImageGenerator()

    def test_01_gemini_ai_image_generation(self):
        sample_post = {
            'id': 'test_gemini_img_001',
            'title': 'SpeedyBee F405 V4 55A BLS 30x30 FPV Uçuş Kontrolcüsü',
            'content_type': 'product_spotlight',
            'product_data': {
                'name_en': 'SpeedyBee F405 V4 Flight Controller',
                'name_tr': 'SpeedyBee F405 V4 Uçuş Kontrolcüsü',
                'brand': 'SpeedyBee',
                'price_try': 2450.00,
                'price_usd': 52.00
            }
        }
        rel_path = self.image_gen.generate_gemini_ai_image(sample_post)
        self.assertTrue(rel_path.endswith('.jpg'))

        abs_path = os.path.join(BASE_DIR, rel_path.lstrip('./').lstrip('/'))
        self.assertTrue(os.path.exists(abs_path))
        
        # Verify resolution & image integrity
        with Image.open(abs_path) as im:
            self.assertEqual(im.size, (1080, 1080))
            self.assertEqual(im.format, 'JPEG')

        # Clean up test file
        try:
            os.remove(abs_path)
        except Exception:
            pass

    def test_02_alternating_image_modes(self):
        """
        Verifies that every other post strictly alternates between gemini_image and canvas.
        (Her iki postta bir, gemini image ile uretilmis gorselli post atsin.)
        """
        # Generate 4 consecutive posts
        modes_sequence = []
        created_post_ids = []

        for i in range(4):
            res = self.agent.generate_and_publish_now(content_type='product_spotlight')
            self.assertTrue(res.get('success'), f"Post {i+1} generation failed: {res.get('error')}")
            post = res.get('post')
            self.assertIsNotNone(post)
            created_post_ids.append(post['id'])
            mode = post.get('image_mode')
            modes_sequence.append(mode)

            # Verify image file exists and is 1080x1080
            img_path = os.path.join(BASE_DIR, post['local_image_path'].lstrip('./').lstrip('/'))
            self.assertTrue(os.path.exists(img_path))
            with Image.open(img_path) as im:
                self.assertEqual(im.size, (1080, 1080))

        # Check alternation: adjacent modes MUST be different
        self.assertEqual(len(modes_sequence), 4)
        for i in range(len(modes_sequence) - 1):
            self.assertNotEqual(
                modes_sequence[i],
                modes_sequence[i+1],
                f"Consecutive posts {i} and {i+1} did not alternate: {modes_sequence}"
            )

        # Check that both modes are represented equally
        self.assertEqual(modes_sequence.count('gemini_image'), 2)
        self.assertEqual(modes_sequence.count('canvas'), 2)

if __name__ == '__main__':
    unittest.main()
