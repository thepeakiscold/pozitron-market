import unittest

from orchestrator.duplicate_guard import (
    DuplicateGuard, title_signature, strip_counter, normalize_text, caption_signature,
)


class TestDuplicateGuard(unittest.TestCase):
    def test_strip_counter_and_signature(self):
        self.assertEqual(
            title_signature("İleri Düzey FPV Aviyonik Sistemleri (9265)"),
            title_signature("İleri Düzey FPV Aviyonik Sistemleri (8440)"),
        )
        self.assertEqual(strip_counter("Rehber Konusu #12"), "Rehber Konusu")
        self.assertEqual(strip_counter("Başlık (4096)"), "Başlık")
        # Meaningful numbers inside the title must be preserved
        self.assertIn("4s", title_signature("4S vs 6S Batarya"))

    def test_caption_signature_normalizes(self):
        a = caption_signature("Merhaba Dünya! Bu bir test metni.")
        b = caption_signature("merhaba   dünya bu bir test metni!!!")
        self.assertEqual(a, b)

    def test_scan_returns_schema(self):
        guard = DuplicateGuard()
        ig = guard.scan_instagram(limit=50)
        self.assertIn("duplicate_groups", ig)
        self.assertIn("duplicate_title_groups", ig)
        self.assertIn("duplicate_image_groups", ig)
        self.assertIn("groups", ig)

        seo = guard.scan_seo()
        self.assertIn("duplicate_groups", seo)
        self.assertIn("counter_clone_count", seo)
        self.assertIn("total_articles", seo)

    def test_scan_all_aggregates(self):
        guard = DuplicateGuard()
        report = guard.scan_all()
        self.assertIn("instagram", report)
        self.assertIn("seo", report)
        self.assertEqual(
            report["total_duplicate_groups"],
            report["instagram"]["duplicate_groups"] + report["seo"]["duplicate_groups"],
        )

    def test_qa_probe_integration(self):
        from orchestrator.subagent_qa import QASentinelAgent
        qa = QASentinelAgent.__new__(QASentinelAgent)
        res = QASentinelAgent.probe_duplicate_content(qa)
        self.assertEqual(res["channel"], "duplicate_content")
        self.assertIn("instagram_duplicate_groups", res)
        self.assertIn("seo_counter_clones", res)


if __name__ == '__main__':
    unittest.main()
