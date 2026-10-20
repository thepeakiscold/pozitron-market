import os
import unittest
from instagram_agent.flux_generator import FluxGenerator, find_flux_dir, LOGICAL_FLUX_TYPES
from instagram_agent.image_generator import ImageGenerator
from instagram_agent.content_generator import ContentGenerator
from instagram_agent.agent import InstagramPRAgent
from PIL import Image

class TestFluxAndProductPhotos(unittest.TestCase):
    def setUp(self):
        self.image_gen = ImageGenerator(width=1080, height=1080)
        self.content_gen = ContentGenerator()

    def test_flux_path_candidates(self):
        flux_dir = find_flux_dir()
        self.assertTrue(os.path.exists(flux_dir), f"FLUX directory {flux_dir} does not exist")
        self.assertTrue("FLUX" in flux_dir)

    def test_logical_flux_types_coverage(self):
        expected_types = [
            "product_spotlight", "deal_drop", "drone_build_showcase",
            "hardware_battle", "pilot_tip", "spot_guide", "flight_weather_radar"
        ]
        for t in expected_types:
            self.assertIn(t, LOGICAL_FLUX_TYPES)

    def test_product_path_multi_level_fallback(self):
        # 1. Direct valid path
        prod1 = {'image_url': './assets/products/PZT-MOTO-4307.jpg'}
        p1 = self.image_gen._resolve_product_path(prod1)
        self.assertIsNotNone(p1)
        self.assertTrue(os.path.exists(p1))

        # 2. Missing image_url but matching SKU
        prod2 = {'sku': 'PZT-MOTO-4307', 'image_url': 'non_existent_path.jpg'}
        p2 = self.image_gen._resolve_product_path(prod2)
        self.assertIsNotNone(p2)
        self.assertTrue(os.path.exists(p2))

        # 3. Category prefix fallback
        prod3 = {'category_id': 'motors', 'image_url': 'bogus.jpg'}
        p3 = self.image_gen._resolve_product_path(prod3)
        self.assertIsNotNone(p3)
        self.assertTrue(os.path.exists(p3))

        # 4. Global fallback when no specific category matched
        prod4 = {'name_tr': 'Özel Donanım'}
        p4 = self.image_gen._resolve_product_path(prod4)
        self.assertIsNotNone(p4)
        self.assertTrue(os.path.exists(p4))

    def test_pzt_5b66454b_motor_resolves_and_renders(self):
        prod = self.content_gen._get_candidate_product('pzt_5b66454b')
        self.assertIsNotNone(prod)
        self.assertEqual(prod['id'], 'pzt_5b66454b')
        resolved = self.image_gen._resolve_product_path(prod)
        self.assertIsNotNone(resolved)
        self.assertTrue(os.path.exists(resolved))

        post_data = {
            'id': 'test_unit_motor_render',
            'content_type': 'product_spotlight',
            'title': 'T-Motor Velox V3 V2207 1950KV',
            'product_data': prod,
            'visual_summary': {
                'headline': 'T-Motor Velox V3 1950KV',
                'subhead': 'Freestyle FPV Gücü',
                'key_points': ['2207 Stator Boyutu', '6S LiPo Desteği']
            }
        }
        rel_img = self.image_gen.generate_post_image(post_data)
        self.assertTrue(os.path.exists(rel_img))
        with Image.open(rel_img) as img:
            self.assertEqual(img.size, (1080, 1080))

    def test_generate_preview_post_fast_gradient(self):
        agent = InstagramPRAgent()
        res = agent.generate_preview_post(
            content_type='product_spotlight',
            product_id='pzt_5b66454b',
            use_flux=False
        )
        self.assertTrue(res.get('success'))
        self.assertFalse(res.get('used_flux'))
        self.assertIn('T-Motor', str(res.get('product_name')))
        self.assertTrue(os.path.exists(res['local_image_path']))

if __name__ == '__main__':
    unittest.main()
