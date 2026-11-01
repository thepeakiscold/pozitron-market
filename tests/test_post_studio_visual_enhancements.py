import os
import pytest
from PIL import Image
from instagram_agent.content_generator import ContentGenerator
from instagram_agent.image_generator import (
    ImageGenerator,
    _load_product_image
)
from instagram_agent.db import get_db

class TestPostStudioVisualEnhancements:

    def test_normalized_avif_products_load_cleanly(self):
        """Verify that products that were previously AVIF now decode as valid RGBA PIL Images."""
        sample_avif_filenames = ['PZTR-CON-0180.jpg', 'PZTR-MOT-0004.jpg', 'PZTR-MOT-0015.jpg']
        for fname in sample_avif_filenames:
            full_path = os.path.join('assets/products', fname)
            assert os.path.exists(full_path), f"File {full_path} must exist"
            img = _load_product_image(full_path)
            assert img is not None, f"Failed to load normalized image {full_path}"
            assert img.width > 100
            assert img.height > 100
            assert img.mode == 'RGBA'

    def test_product_attachment_across_all_content_types(self):
        """Verify that when a user selects a product_id in Post Studio, all hardware and guide content types attach product_data."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name_tr, image_url FROM products WHERE image_url IS NOT NULL LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        assert row is not None
        target_product_id = row['id']

        gen = ContentGenerator()
        types_to_test = [
            'product_spotlight',
            'drone_build_showcase',
            'tool_showcase',
            'deal_drop',
            'pilot_tip',
            'review_highlight',
            'hardware_battle',
            'mistake_breakdown',
            'maintenance_checklist'
        ]

        for c_type in types_to_test:
            post = gen.generate_content(product_id=target_product_id, content_type=c_type)
            assert post['content_type'] == c_type
            assert post['product_id'] == target_product_id, f"Type {c_type} did not retain product_id"
            assert post.get('product_data') is not None, f"Type {c_type} did not attach product_data"
            assert post['product_data']['id'] == target_product_id

    def test_render_brand_template_with_product(self, tmp_path):
        """Test rendering the new visual template for a product post."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE image_url IS NOT NULL LIMIT 1")
        p_row = dict(cursor.fetchone())
        conn.close()

        post_data = {
            'content_type': 'product_spotlight',
            'title': 'Test Showcase Post',
            'product_id': p_row['id'],
            'product_data': p_row,
            'visual_summary': {
                'badge': 'POZITRON OZEL DONANIM',
                'headline': p_row.get('name_tr', 'Test Product'),
                'subhead': 'Ustun tork ve yuksek verim sunan yeni nesil FPV motoru',
                'key_points': [
                    'Titanyum alasimli mil ve N52H miknatislar',
                    '4S ve 6S LiPo tam uyumluluk',
                    'Dusuk sicaklikta %15 daha fazla itis gucu'
                ],
                'cta': 'HEMEN INCELE & SATIN AL'
            }
        }

        output_path = str(tmp_path / "test_with_product.jpg")
        img_gen = ImageGenerator()
        rendered = img_gen.render_brand_template(post_data)
        assert isinstance(rendered, Image.Image)
        assert rendered.size == (1080, 1080)
        assert rendered.mode == 'RGB'
        rendered.save(output_path, quality=95)
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 10000

    def test_render_brand_template_without_product(self, tmp_path):
        """Test rendering the new visual template for a non-product educational guide post (vertically balanced)."""
        post_data = {
            'content_type': 'maintenance_checklist',
            'title': 'Test Non-Product Checklist',
            'product_id': None,
            'product_data': None,
            'visual_summary': {
                'badge': 'FPV BAKIM KONTROL LISTESI',
                'headline': 'HER UCUS ONCESI 5 KRITIK KONTROL',
                'subhead': 'Kirim yasamadan once mutlaka uygulaman gereken hayati kontroller',
                'key_points': [
                    'Pervane somunlarinin sikiligini kontrol et',
                    'Anten konnektorlerinin saglamligini dogrula',
                    'Motor vidalarinda gevseme veya bosluk testi yap',
                    'Batarya cirt bandini ve silikon korumayi kontrol et'
                ],
                'cta': 'KAYDET VE GUVENLE UC'
            }
        }

        output_path = str(tmp_path / "test_non_product.jpg")
        img_gen = ImageGenerator()
        rendered = img_gen.render_brand_template(post_data)
        assert isinstance(rendered, Image.Image)
        assert rendered.size == (1080, 1080)
        assert rendered.mode == 'RGB'
        rendered.save(output_path, quality=95)
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 10000
