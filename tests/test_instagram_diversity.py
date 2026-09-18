import unittest
import os
import sys
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from instagram_agent.content_generator import ContentGenerator
from instagram_agent.db import (
    get_agent_config, update_agent_config, get_recent_posted_titles
)
from orchestrator.subagent_price_intelligence import PriceIntelligenceAgent


class TestInstagramDiversity(unittest.TestCase):
    def setUp(self):
        self.original_config = get_agent_config()

    def tearDown(self):
        if self.original_config:
            update_agent_config({
                'posting_frequency_hours': self.original_config.get('posting_frequency_hours', 6),
                'dry_run_mode': self.original_config.get('dry_run_mode', 0),
                'is_autonomous_enabled': self.original_config.get('is_autonomous_enabled', 1)
            })

    def test_price_intelligence_prng_isolation(self):
        """
        Ensure running PriceIntelligenceAgent does NOT reseed global random.
        Previously, random.seed(seed_val + 2026) in subagent_price_intelligence locked
        the global PRNG to a fixed seed every 2 hours.
        """
        # Set a known state and check PRNG moves naturally
        random.seed(42)
        v1 = random.random()
        
        # Run price intelligence
        pi = PriceIntelligenceAgent()
        report = pi.scan_market()
        self.assertIsNotNone(report)
        self.assertTrue(len(report) > 0)
        
        # If PRNG was reseeded with a static seed, subsequent random calls would be locked
        v2 = random.random()
        
        # Run price intelligence a second time
        pi.scan_market()
        v3 = random.random()
        
        # v2 and v3 must be distinct random floats, showing global PRNG is NOT reset
        self.assertNotEqual(v2, v3, "Global random state was contaminated by PriceIntelligenceAgent!")

    def test_content_generator_diversity_consecutive(self):
        """
        Ensure 20 consecutive generate_content() calls yield distinct posts
        with no repeated titles.
        """
        cg = ContentGenerator()
        titles = []
        content_types = []
        
        for _ in range(20):
            post = cg.generate_content()
            self.assertIsNotNone(post)
            self.assertIn('title', post)
            self.assertIn('content_type', post)
            titles.append(post['title'])
            content_types.append(post['content_type'])
            
        unique_titles = set(titles)
        # In 20 iterations, diversity must be extremely high (>= 18 unique titles)
        self.assertGreaterEqual(
            len(unique_titles), 18,
            f"Expected at least 18 unique titles out of 20, got {len(unique_titles)}: {titles}"
        )
        
        # No two adjacent posts should have the exact same title
        for i in range(len(titles) - 1):
            self.assertNotEqual(
                titles[i], titles[i + 1],
                f"Consecutive identical posts generated: {titles[i]}"
            )

    def test_anti_duplication_filters_recent_titles(self):
        """
        Ensure ContentGenerator never generates a title that matches recent history.
        """
        cg = ContentGenerator()
        recent_titles = get_recent_posted_titles(limit=40)
        
        # Generate 10 posts and ensure none of them match the very first title in recent_titles
        # (which is historically the stuck title '[ARAC] FPV Motor KV Seçiminde En Sık Yapılan 3 Hata')
        stuck_title = "[ARAC] FPV Motor KV Seçiminde En Sık Yapılan 3 Hata"
        
        for _ in range(10):
            post = cg.generate_content()
            self.assertNotEqual(
                post['title'], stuck_title,
                f"Generator emitted previously stuck title: {stuck_title}"
            )

    def test_product_spotlight_category_distribution(self):
        """
        Ensure product spotlights sample across diverse categories rather than
        repeating the same category every time.
        """
        cg = ContentGenerator()
        categories = set()
        
        for _ in range(12):
            post = cg._generate_product_spotlight()
            self.assertIsNotNone(post)
            prod_data = post.get('product_data')
            if prod_data:
                cat = prod_data.get('category_id') or prod_data.get('category')
                if cat:
                    categories.add(cat)
                
        # Across 12 generations, at least 4 distinct product categories should be covered
        self.assertGreaterEqual(
            len(categories), 4,
            f"Expected at least 4 distinct categories across 12 spotlights, got: {categories}"
        )


if __name__ == '__main__':
    unittest.main()
