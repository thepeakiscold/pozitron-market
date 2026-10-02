import unittest
import os
from orchestrator.subagent_media_inspector import ProductMediaInspectorAgent
from database import is_subagent_enabled, set_subagent_enabled

class TestMediaInspectorAgent(unittest.TestCase):

    def setUp(self):
        self.agent = ProductMediaInspectorAgent()

    def test_agent_initialization(self):
        self.assertEqual(self.agent.agent_id, "subagent_10_media")
        self.assertTrue(os.path.exists(self.agent.db_path))

    def test_subagent_enabled_in_db(self):
        self.assertTrue(is_subagent_enabled("subagent_10_media"))
        set_subagent_enabled("subagent_10_media", False)
        self.assertFalse(is_subagent_enabled("subagent_10_media"))
        set_subagent_enabled("subagent_10_media", True)
        self.assertTrue(is_subagent_enabled("subagent_10_media"))

    def test_semantic_mismatch_detection(self):
        # FC category with prop name should trigger mismatch
        issue = self.agent._check_semantic_mismatch("HQProp 5146 Tri-blade Propeller", "flight_controllers")
        self.assertIsNotNone(issue)
        self.assertIn("FC", issue)

        # Normal product should not trigger mismatch
        clean = self.agent._check_semantic_mismatch("SpeedyBee F405 V4 Flight Controller", "flight_controllers")
        self.assertIsNone(clean)

    def test_suggested_asset_fallback(self):
        asset = self.agent._get_suggested_asset("betafpv", "flight_controllers")
        self.assertIsNotNone(asset)
        self.assertTrue(asset.endswith(".jpg"))

    def test_scan_products_sample(self):
        # Scan a limited batch of 15 products for quick testing
        report = self.agent.scan_all_products(limit=15)
        self.assertIn("total_products_scanned", report)
        self.assertEqual(report["total_products_scanned"], 15)
        self.assertIn("visual_health_score", report)
        self.assertIn("issues_summary", report)

    def test_auto_fix_dry_run(self):
        fix_report = self.agent.auto_fix_quarantined_products(dry_run=True)
        self.assertTrue(fix_report["dry_run"])
        self.assertIn("candidates_found", fix_report)
        self.assertIn("applied_fixes_count", fix_report)

if __name__ == "__main__":
    unittest.main()
