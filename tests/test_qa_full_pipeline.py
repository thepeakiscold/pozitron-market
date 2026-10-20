#!/usr/bin/env python3
"""
Unit tests for Subagent 7 QA Sentinel Full Subagent Pipeline Inspection & Auto-Healing.
STRICT ZERO EMOJIS in code, logs, and docstrings.
"""
import unittest
import os
import json
import sqlite3
from orchestrator.subagent_qa import QASentinelAgent
from export_data import export_static_data

class TestQAFullPipeline(unittest.TestCase):
    def setUp(self):
        export_static_data()
        self.agent = QASentinelAgent(check_interval_minutes=15)

    def test_probe_subagent_pipeline_outputs(self):
        result = self.agent.probe_subagent_pipeline_outputs()
        self.assertIn("channel", result)
        self.assertEqual(result["channel"], "subagent_pipeline")
        self.assertIn("subagents", result)

        subagents = result["subagents"]
        expected_keys = ["telemetry", "price_intelligence", "technical_seo", "lead_supervisor", "lead_evolution", "trend_hunter"]
        for k in expected_keys:
            self.assertIn(k, subagents)
            self.assertIn("status", subagents[k])
            self.assertIn("fresh", subagents[k])

    def test_probe_instagram_structure(self):
        ig = self.agent.probe_instagram()
        self.assertEqual(ig["channel"], "instagram")
        self.assertIn("token_valid", ig)
        self.assertIn("banner_images_intact", ig)
        self.assertIn("total_posts", ig)

    def test_probe_reddit_structure(self):
        red = self.agent.probe_reddit()
        self.assertEqual(red["channel"], "reddit")
        self.assertIn("session_valid", red)
        self.assertIn("search_endpoint_ok", red)

    def test_probe_database_and_cache(self):
        db = self.agent.probe_database_and_cache()
        self.assertEqual(db["channel"], "database_and_cache")
        self.assertGreater(db["tables_checked"], 0)
        self.assertTrue(db["cache_files_in_sync"])

    def test_run_probes_consolidated(self):
        probes = self.agent.run_probes()
        self.assertIn("overall_status", probes)
        self.assertIn("health_score", probes)
        self.assertGreaterEqual(probes["health_score"], 0)
        self.assertLessEqual(probes["health_score"], 100)
        self.assertIn("subagent_pipeline", probes["probes"])
        self.assertIn("instagram_engagement", probes["probes"])

    def test_analyze_engagement_detects_unused_follow_quota(self):
        """Detects the silent follow-quota failure (0 follows while comments flow)."""
        history = []
        for day in ("2026-10-08", "2026-10-09", "2026-10-10", "2026-10-11"):
            for i in range(10):
                history.append({
                    "type": "comment", "status": "success",
                    "timestamp": f"{day}T02:0{i}:00", "user_id": str(i)
                })
        data = {
            "today_date": "2026-10-12",
            "today_follows_count": 0,
            "today_comments_count": 10,
            "history": history,
            "follow_diagnostics": {}
        }
        analysis = self.agent._analyze_engagement_data(data)
        self.assertEqual(analysis["today_follows"], 0)
        self.assertEqual(analysis["today_comments"], 10)
        self.assertGreaterEqual(analysis["trailing_zero_follow_days"], 4)

    def test_analyze_engagement_detects_feedback_required_block(self):
        """Surfaces the recorded Instagram follow action-block reason."""
        data = {
            "today_date": "2026-10-12",
            "today_follows_count": 0,
            "today_comments_count": 10,
            "history": [],
            "follow_diagnostics": {
                "last_follow_error": "feedback_required",
                "last_follow_message": "We limit how often you can do certain things on Instagram",
                "follow_blocked": True,
                "follow_blocked_until": "2099-01-01T00:00:00"
            }
        }
        analysis = self.agent._analyze_engagement_data(data)
        self.assertTrue(analysis["follow_blocked"])
        self.assertEqual(analysis["last_follow_error"], "feedback_required")

if __name__ == "__main__":
    unittest.main()
