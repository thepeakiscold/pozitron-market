import unittest
from datetime import datetime, timedelta

from llm_client import LLMClient, resolve_config, DEFAULT_MODEL, DEFAULT_EFFORT
from orchestrator.subagent_qa import QASentinelAgent


class TestLLMClient(unittest.TestCase):
    def test_default_model_and_effort(self):
        base, key, model, effort = resolve_config()
        self.assertEqual(model, DEFAULT_MODEL)
        self.assertEqual(effort, DEFAULT_EFFORT)
        self.assertTrue(base.startswith("http"))
        self.assertTrue(key)

    def test_disabled_during_tests(self):
        # Real network LLM must be disabled while the test suite runs.
        c = LLMClient()
        self.assertFalse(c.is_configured())


class TestFollowRateLimitAnalysis(unittest.TestCase):
    def _agent(self):
        return QASentinelAgent.__new__(QASentinelAgent)

    def test_high_risk_burst_detection(self):
        agent = self._agent()
        base = datetime(2026, 10, 12, 20, 0, 0)
        history = []
        for i in range(10):
            history.append({
                "type": "follow",
                "status": "success",
                "timestamp": (base + timedelta(seconds=17 * i)).isoformat(),
            })
        data = {"history": history}
        analysis = {"follow_blocked": True, "today_follows": 10, "today_comments": 10}
        res = agent._analyze_follow_rate_limit(data, analysis)
        self.assertEqual(res["rate_limit_risk"], "HIGH")
        self.assertEqual(res["max_follows_per_hour"], 10)
        self.assertIsNotNone(res["min_follow_gap_seconds"])
        self.assertGreaterEqual(len(res["rate_limit_root_causes"]), 3)
        self.assertGreaterEqual(len(res["rate_limit_recommendations"]), 3)

    def test_low_risk_spaced_follows(self):
        agent = self._agent()
        base = datetime(2026, 10, 12, 9, 0, 0)
        history = []
        for i in range(3):
            history.append({
                "type": "follow",
                "status": "success",
                "timestamp": (base + timedelta(hours=i, minutes=7 * i)).isoformat(),
            })
        data = {"history": history}
        analysis = {"follow_blocked": False, "today_follows": 3, "today_comments": 2}
        res = agent._analyze_follow_rate_limit(data, analysis)
        self.assertEqual(res["rate_limit_risk"], "LOW")


if __name__ == "__main__":
    unittest.main()
