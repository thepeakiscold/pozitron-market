import os
import json
import unittest
import urllib.request
from database import is_subagent_enabled, set_subagent_enabled, get_all_subagents_config
from orchestrator.subagent_qa import QASentinelAgent

class TestSubagentsToggle(unittest.TestCase):

    def setUp(self):
        # Ensure reddit is disabled as requested
        set_subagent_enabled("subagent_2_reddit", False)

    def test_default_subagents_config_seeded(self):
        configs = get_all_subagents_config()
        self.assertGreaterEqual(len(configs), 9)
        sub_ids = [c["subagent_id"] for c in configs]
        self.assertIn("subagent_1_instagram", sub_ids)
        self.assertIn("subagent_2_reddit", sub_ids)
        self.assertIn("subagent_3_telemetry", sub_ids)
        self.assertIn("subagent_4_seo", sub_ids)
        self.assertIn("subagent_5_price", sub_ids)
        self.assertIn("subagent_6_trend", sub_ids)
        self.assertIn("subagent_7_qa", sub_ids)
        self.assertIn("subagent_8_procurement", sub_ids)
        self.assertIn("lead_supervisor", sub_ids)

    def test_reddit_bot_disabled_by_default(self):
        self.assertFalse(is_subagent_enabled("subagent_2_reddit"))

    def test_toggle_functionality(self):
        original_state = is_subagent_enabled("subagent_3_telemetry")
        try:
            ok = set_subagent_enabled("subagent_3_telemetry", False)
            self.assertTrue(ok)
            self.assertFalse(is_subagent_enabled("subagent_3_telemetry"))

            ok = set_subagent_enabled("subagent_3_telemetry", True)
            self.assertTrue(ok)
            self.assertTrue(is_subagent_enabled("subagent_3_telemetry"))
        finally:
            set_subagent_enabled("subagent_3_telemetry", original_state)

    def test_server_status_api(self):
        url = "http://localhost:8000/api/subagents/status"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data.get("success"))
            subagents = data.get("subagents", [])
            self.assertGreaterEqual(len(subagents), 9)

            reddit = next((s for s in subagents if s["subagent_id"] == "subagent_2_reddit"), None)
            self.assertIsNotNone(reddit)
            self.assertEqual(reddit["is_enabled"], 0)

    def test_server_toggle_api(self):
        url = "http://localhost:8000/api/subagents/toggle"
        # Test toggling telemetry off
        req = urllib.request.Request(
            url,
            data=json.dumps({"subagent_id": "subagent_3_telemetry", "is_enabled": 0}).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data.get("success"))
        self.assertFalse(is_subagent_enabled("subagent_3_telemetry"))

        # Re-enable
        req = urllib.request.Request(
            url,
            data=json.dumps({"subagent_id": "subagent_3_telemetry", "is_enabled": 1}).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data.get("success"))
        self.assertTrue(is_subagent_enabled("subagent_3_telemetry"))

    def test_qa_sentinel_with_disabled_reddit(self):
        qa = QASentinelAgent()
        probes = qa.run_probes()
        self.assertIn("reddit", probes["probes"])
        reddit_probe = probes["probes"]["reddit"]
        self.assertEqual(reddit_probe["status"], "DISABLED")
        self.assertFalse(reddit_probe["inactivity_alert"])
        self.assertNotIn("reddit", probes["probes"]["schedulers_and_threads"]["dead_schedulers"])
        self.assertEqual(probes["overall_status"], "HEALTHY")

if __name__ == '__main__':
    unittest.main()
