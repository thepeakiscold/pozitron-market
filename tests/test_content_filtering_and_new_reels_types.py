from datetime import datetime
import json
import os
import unittest
from unittest.mock import MagicMock, patch

from instagram_agent.agent import InstagramPRAgent
from instagram_agent.content_generator import (
    ALL_POST_TYPES,
    ALL_REELS_TYPES,
    REELS_TYPES_METADATA,
    ContentGenerator,
)
from instagram_agent.db import get_agent_config, update_agent_config
from instagram_agent.image_generator import ImageGenerator


class TestContentFilteringAndNewReelsTypes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.agent = InstagramPRAgent()
        cls.image_gen = ImageGenerator()
        cls.content_gen = ContentGenerator()

    def test_post_types_and_reels_types_metadata(self):
        """Verify metadata definitions for post types (16) and reels types (8)."""
        self.assertGreaterEqual(len(ALL_POST_TYPES), 16)
        post_type_ids = [pt["id"] for pt in ALL_POST_TYPES]
        self.assertIn("product_spotlight", post_type_ids)
        self.assertIn("deal_drop", post_type_ids)
        self.assertIn("pilot_tip", post_type_ids)

        self.assertEqual(len(ALL_REELS_TYPES), 8)
        self.assertEqual(len(REELS_TYPES_METADATA), 8)
        reels_type_ids = [rt["id"] for rt in REELS_TYPES_METADATA]
        expected_reels = [
            "real_fpv_broll",
            "freestyle_acro",
            "hardware_vs",
            "quick_tip_fix",
            "mistake_warning",
            "secret_spot",
            "product_cinematic",
            "flash_deal",
        ]
        for expected in expected_reels:
            self.assertIn(expected, reels_type_ids)
            self.assertIn(expected, ALL_REELS_TYPES)

    def test_config_db_persistence_and_safe_config(self):
        """Verify DB persistence of enabled_post_types and enabled_reels_types."""
        sample_post_types = ["product_spotlight", "deal_drop", "pilot_tip"]
        sample_reels_types = ["freestyle_acro", "secret_spot"]

        # Persist as python lists
        update_agent_config(
            enabled_post_types=sample_post_types,
            enabled_reels_types=sample_reels_types,
        )

        cfg = get_agent_config()
        self.assertTrue(isinstance(cfg.get("enabled_post_types"), str))
        self.assertTrue(isinstance(cfg.get("enabled_reels_types"), str))
        self.assertEqual(json.loads(cfg["enabled_post_types"]), sample_post_types)
        self.assertEqual(json.loads(cfg["enabled_reels_types"]), sample_reels_types)

        safe_cfg = self.agent.get_safe_config()
        self.assertEqual(safe_cfg["enabled_post_types"], sample_post_types)
        self.assertEqual(safe_cfg["enabled_reels_types"], sample_reels_types)

        eff_posts = self.agent.get_effective_enabled_post_types()
        eff_reels = self.agent.get_effective_enabled_reels_types()
        self.assertEqual(eff_posts, sample_post_types)
        self.assertEqual(eff_reels, sample_reels_types)

    def test_generate_content_respects_allowed_types(self):
        """Verify generate_content strictly limits generated content_type to allowed_types."""
        allowed = ["deal_drop", "pilot_tip"]
        for _ in range(10):
            post = self.content_gen.generate_content(allowed_types=allowed)
            self.assertIn(post["content_type"], allowed)

    def test_generate_reels_content_all_8_types_and_allowed_filter(self):
        """Verify each of the 8 reels types can be generated and allowed_reels_types is respected."""
        for r_type in ALL_REELS_TYPES:
            reel = self.content_gen.generate_reels_content(reels_type=r_type)
            self.assertEqual(reel["reels_type"], r_type)
            self.assertTrue(bool(reel.get("hook")))
            self.assertTrue(bool(reel.get("cta")))
            self.assertTrue(bool(reel.get("caption")))

        # Test filtering with subset
        allowed = ["mistake_warning", "flash_deal"]
        for _ in range(10):
            reel = self.content_gen.generate_reels_content(allowed_reels_types=allowed)
            self.assertIn(reel["reels_type"], allowed)

    def test_generate_reels_video_prompt_formats(self):
        """Verify cinematic prompt generator creates customized prompts for all 8 formats."""
        for r_type in ALL_REELS_TYPES:
            dummy_reel = {
                "reels_type": r_type,
                "title": f"Test Title {r_type}",
                "hook": "FPV Tutkusu",
                "product_data": {"name": "Test Drone", "price_try": 1999.0},
            }
            prompt = self.content_gen.generate_reels_video_prompt(dummy_reel)
            self.assertTrue(isinstance(prompt, str))
            self.assertGreater(len(prompt), 30)
            self.assertIn("9:16", prompt)

    @patch.object(ImageGenerator, "_get_broll_clip")
    @patch.object(ImageGenerator, "_fallback_single_slide_video")
    def test_real_fpv_broll_toggle_suppresses_broll(self, mock_fallback, mock_get_broll):
        """Verify that when real_fpv_broll is unselected/disabled, b-roll is never queried or used."""
        mock_fallback.return_value = "/tmp/mock_fallback.mp4"
        mock_get_broll.return_value = "/tmp/real_flight.mp4"

        # Explicitly allowed_reels_types without real_fpv_broll
        post_data = {
            "id": "reel_no_broll_test",
            "reels_type": "hardware_vs",
            "allowed_reels_types": ["freestyle_acro", "hardware_vs"],
            "title": "Hardware VS",
            "caption": "Test caption",
        }

        # Mock DB config returning only freestyle_acro
        with patch("instagram_agent.image_generator.get_agent_config", return_value={"enabled_reels_types": json.dumps(["freestyle_acro"])}):
            out = self.image_gen._generate_ffmpeg_reels_video(post_data, "/tmp/reel_test.mp4", "reel_test.mp4")
            self.assertEqual(out, "/tmp/mock_fallback.mp4")
            mock_get_broll.assert_not_called()
            mock_fallback.assert_called_once()

    def test_agent_autonomous_cycle_passes_effective_filters(self):
        """Verify agent.run_autonomous_cycle calls generate_and_publish with effective filters."""
        with patch.object(self.agent, "get_effective_enabled_post_types", return_value=["deal_drop"]), \
             patch.object(self.agent, "get_effective_enabled_reels_types", return_value=["quick_tip_fix"]), \
             patch.object(self.agent, "generate_and_publish_now") as mock_pub_post, \
             patch.object(self.agent, "generate_and_publish_reel") as mock_pub_reel, \
             patch.object(self.agent, "reload_config"), \
             patch("database.get_setting", return_value=datetime.now().isoformat()):

            self.agent.config = {
                "carousel_enabled": 0,
                "story_enabled": 0,
                "reels_enabled": 1,
                "content_mix_enabled": 0,
            }
            res = self.agent.run_autonomous_cycle(run_engagement=False)
            mock_pub_post.assert_called_once_with(allowed_types=["deal_drop"])
            mock_pub_reel.assert_called_once_with(allowed_reels_types=["quick_tip_fix"])


if __name__ == "__main__":
    unittest.main()
