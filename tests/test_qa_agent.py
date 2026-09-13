import unittest
import json
import urllib.request
import urllib.error
from unittest.mock import patch, MagicMock
from orchestrator.subagent_qa import QASentinelAgent, init_qa_tables
from orchestrator.qa_scheduler import QAScheduler

class TestQASentinelAgent(unittest.TestCase):
    def setUp(self):
        init_qa_tables()
        self.agent = QASentinelAgent(check_interval_minutes=30)

    def test_probe_database_and_cache(self):
        """Ensures database tables and cache parity are checked."""
        res = self.agent.probe_database_and_cache()
        self.assertEqual(res["channel"], "database_and_cache")
        self.assertGreater(res["tables_checked"], 0)
        self.assertIn("cache_files_in_sync", res)

    @patch("urllib.request.urlopen")
    def test_probe_instagram_token_expired_detection(self, mock_urlopen):
        """Ensures expired Meta access token raises error and degrades status."""
        # Mock HTTPError 400 (OAuth token expired)
        fp = MagicMock()
        fp.read.return_value = b'{"error":{"message":"Invalid OAuth access token - Cannot parse access token","type":"OAuthException","code":190}}'
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://graph.facebook.com/v19.0/me",
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=fp
        )
        with patch.object(self.agent, "_get_instagram_config", return_value={"meta_access_token": "sample_token"}):
            res = self.agent.probe_instagram()
            self.assertEqual(res["channel"], "instagram")
            self.assertFalse(res["token_valid"])
            self.assertEqual(res["token_mode"], "expired")

    def test_probe_reddit_inactivity_alert(self):
        """Ensures 0 published comments triggers inactivity alert."""
        with patch("reddit_agent.db.get_interactions", return_value=[]):
            with patch("reddit_agent.db.get_daily_replies_count", return_value=0):
                res = self.agent.probe_reddit()
                self.assertEqual(res["channel"], "reddit")
                self.assertTrue(res["inactivity_alert"])
                self.assertIn("Sifir Yorum Uyarisi", " ".join(res["issues"]))

    def test_probe_schedulers_and_threads(self):
        """Ensures scheduler thread liveness check runs without crashing."""
        res = self.agent.probe_schedulers_and_threads()
        self.assertEqual(res["channel"], "schedulers_and_threads")
        self.assertIn("schedulers_status", res)
        self.assertIn("instagram", res["schedulers_status"])
        self.assertIn("reddit", res["schedulers_status"])
        self.assertIn("lead_supervisor", res["schedulers_status"])

    def test_probe_assets_and_catalog(self):
        """Ensures product assets and catalog images are verified."""
        res = self.agent.probe_assets_and_catalog()
        self.assertEqual(res["channel"], "catalog_assets")
        self.assertIn("total_products_checked", res)
        self.assertIn("missing_images_count", res)

    def test_ai_analysis_fallback_zero_emojis(self):
        """Ensures RCA synthesis operates cleanly with zero emojis."""
        probes = self.agent.run_probes()
        analysis = self.agent.analyze_with_gemini(probes)
        self.assertIn("executive_summary", analysis)
        self.assertIn("root_causes", analysis)
        self.assertIn("auto_heal_actions_recommended", analysis)

        # Check for emojis in all string values
        all_text = json.dumps(analysis, ensure_ascii=False)
        for ch in all_text:
            code = ord(ch)
            # Common emoji unicode ranges
            is_emoji = (
                0x1F600 <= code <= 0x1F64F or
                0x1F300 <= code <= 0x1F5FF or
                0x1F680 <= code <= 0x1F6FF or
                0x1F700 <= code <= 0x1F77F or
                0x1F900 <= code <= 0x1F9FF or
                0x2600 <= code <= 0x26FF or
                0x2700 <= code <= 0x27BF
            )
            self.assertFalse(is_emoji, f"Emoji detected in AI analysis: {ch} (code {hex(code)})")

    def test_auto_heal_and_incident_logging(self):
        """Ensures auto_heal remedies are executed and logged."""
        probes = {
            "overall_status": "DEGRADED",
            "health_score": 70,
            "total_issues_count": 1,
            "all_issues": ["Meta token expired"],
            "probes": {
                "instagram": {"token_valid": False, "issues": ["Meta token expired"]},
                "reddit": {"inactivity_alert": False, "total_questions": 10, "issues": []},
                "database_and_cache": {"cache_files_in_sync": True, "issues": []},
                "schedulers_and_threads": {"dead_schedulers": [], "issues": []},
                "catalog_assets": {"missing_images_count": 0, "issues": []}
            }
        }
        healed = self.agent.auto_heal(probes, {})
        self.assertGreaterEqual(len(healed), 1)
        self.assertEqual(healed[0]["channel"], "instagram")

        incidents = self.agent.get_incidents(limit=5)
        self.assertGreaterEqual(len(incidents), 1)
        self.assertEqual(incidents[0]["channel"], "instagram")

    def test_qa_scheduler_start_stop(self):
        """Ensures background watchdog scheduler can start and stop cleanly."""
        sched = QAScheduler(self.agent)
        self.assertFalse(sched.is_running())
        sched.start()
        self.assertTrue(sched.is_running())
        sched.stop()
        self.assertFalse(sched.is_running())

if __name__ == "__main__":
    unittest.main()
