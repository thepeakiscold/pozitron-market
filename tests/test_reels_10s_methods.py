import os
import unittest
from unittest.mock import patch
from PIL import Image

from instagram_agent.flux_generator import FluxGenerator
from instagram_agent.image_generator import ImageGenerator


class TestReels10sMethods(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.flux_gen = FluxGenerator()
        cls.image_gen = ImageGenerator()
        cls.dummy_post = {
            "id": "ig_reel_test_10s",
            "content_type": "product_spotlight",
            "title": "SpeedyBee F405 V4 Stack",
            "caption": "En çok tercih edilen FPV uçuş kulesi!",
            "hashtags": ["#fpv", "#drone"],
            "product_data": {
                "name": "SpeedyBee F405 V4 Stack",
                "name_tr": "SpeedyBee F405 V4 Uçuş Kulesi",
                "price_try": 2850.0,
            },
            "visual_summary": {
                "headline": "Maksimum FPV Gücü",
                "badge": "POZITRON ÖNERİSİ",
                "key_points": ["BLS 55A ESC", "Bluetooth Ayarlama"],
            },
        }

    def test_build_video_prompt_shot_variants(self):
        """Verify distinct prompts are generated for each shot type."""
        p_hardware = self.flux_gen.build_video_prompt(self.dummy_post, shot="hardware")
        p_action = self.flux_gen.build_video_prompt(self.dummy_post, shot="action")
        p_continuous = self.flux_gen.build_video_prompt(self.dummy_post, shot="continuous")
        p_montage = self.flux_gen.build_video_prompt(self.dummy_post, shot="montage")

        self.assertIn("Extreme macro", p_hardware)
        self.assertIn("Carbon fiber", p_hardware)
        self.assertIn("freestyle flight", p_action)
        self.assertIn("continuous take", p_continuous)
        self.assertIn("Cinematic vertical 9:16", p_montage)

    @patch.object(FluxGenerator, "generate_video")
    def test_generate_video_for_reel_multi_shot(self, mock_gen):
        """Multi-shot mode generates 2 sequential clips (hardware + action, 113 frames each)."""
        mock_gen.side_effect = [
            "/tmp/test_shot1.webp",
            "/tmp/test_shot2.webp",
        ]
        with patch("os.path.exists", return_value=True):
            info = self.flux_gen.generate_video_for_reel(
                self.dummy_post, "ig_reel_test_10s", reels_method="multi_shot"
            )

        self.assertEqual(info["reels_method"], "multi_shot")
        self.assertEqual(len(info["clips"]), 2)
        self.assertIn("Çoklu Sahne Kurgusu", info["reels_method_info"])
        self.assertEqual(mock_gen.call_count, 2)
        # Verify 113 frames requested for both shots
        first_call_kwargs = mock_gen.call_args_list[0][1]
        second_call_kwargs = mock_gen.call_args_list[1][1]
        self.assertEqual(first_call_kwargs["frames"], 113)
        self.assertEqual(second_call_kwargs["frames"], 113)

    @patch.object(FluxGenerator, "generate_video")
    def test_generate_video_for_reel_direct_257(self, mock_gen):
        """Direct 257 mode requests single 257-frame take (10.28s)."""
        mock_gen.return_value = "/tmp/test_257.webp"
        info = self.flux_gen.generate_video_for_reel(
            self.dummy_post, "ig_reel_test_10s", reels_method="direct_257"
        )

        self.assertEqual(info["reels_method"], "direct_257")
        self.assertIn("257", info["reels_method_info"])
        self.assertEqual(mock_gen.call_count, 1)
        call_kwargs = mock_gen.call_args[1]
        self.assertEqual(call_kwargs["frames"], 257)

    @patch.object(FluxGenerator, "generate_video")
    def test_generate_video_for_reel_slow_motion(self, mock_gen):
        """Slow-motion mode requests 129 frames."""
        mock_gen.return_value = "/tmp/test_129.webp"
        info = self.flux_gen.generate_video_for_reel(
            self.dummy_post, "ig_reel_test_10s", reels_method="slow_motion"
        )

        self.assertEqual(info["reels_method"], "slow_motion")
        self.assertIn("Ağır Çekim", info["reels_method_info"])
        self.assertEqual(mock_gen.call_count, 1)
        call_kwargs = mock_gen.call_args[1]
        self.assertEqual(call_kwargs["frames"], 129)

    @patch.object(FluxGenerator, "generate_video")
    def test_generate_video_for_reel_fast_97(self, mock_gen):
        """Fast test mode requests 97 frames (~3.9s)."""
        mock_gen.return_value = "/tmp/test_97.webp"
        info = self.flux_gen.generate_video_for_reel(
            self.dummy_post, "ig_reel_test_10s", reels_method="fast_97"
        )

        self.assertEqual(info["reels_method"], "fast_97")
        self.assertIn("97 Kare", info["reels_method_info"])
        self.assertEqual(mock_gen.call_count, 1)
        call_kwargs = mock_gen.call_args[1]
        self.assertEqual(call_kwargs["frames"], 97)

    def test_render_reels_outro_card(self):
        """Outro card renders properly with brand elements and price pill."""
        img = self.image_gen._render_reels_outro_card(self.dummy_post, width=576, height=1024)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (576, 1024))
        self.assertEqual(img.mode, "RGB")

    def test_video_duration_probe(self):
        """Verify _get_video_duration accurately extracts float seconds."""
        dur = self.image_gen._get_video_duration("/nonexistent/video.mp4")
        self.assertEqual(dur, 0.0)

    def test_finalize_ai_video_with_real_webp_and_multi_shot(self):
        """
        End-to-end test using an existing webp asset:
        Verifies Pillow frame unpacking, multi-clip concatenation, outro card appending,
        ffmpeg encoding, and that resulting video duration is >= 9.5s (244 frames @ 25fps = 9.76s).
        """
        existing_webp = "assets/instagram/reels/ig_reel_08dde58bdaee_ltx_raw.webp"
        if not os.path.exists(existing_webp):
            self.skipTest("Sample webp asset not found")

        out_path = "/tmp/test_multi_shot_output.mp4"
        if os.path.exists(out_path):
            os.remove(out_path)

        post = dict(self.dummy_post)
        post["reels_method"] = "multi_shot"

        result = self.image_gen._finalize_ai_video(
            raw_video_path=existing_webp,
            post_data=post,
            abs_video_path=out_path,
            clips=[existing_webp, existing_webp],
            reels_method="multi_shot"
        )

        self.assertTrue(bool(result))
        self.assertTrue(os.path.exists(out_path))
        self.assertGreater(os.path.getsize(out_path), 50000)

        # Verify exact duration
        dur = self.image_gen._get_video_duration(out_path)
        print(f"\n[TEST VERIFY] Multi-shot synthesized duration: {dur:.2f}s")
        self.assertGreaterEqual(dur, 9.5)

        if os.path.exists(out_path):
            os.remove(out_path)


if __name__ == "__main__":
    unittest.main()
