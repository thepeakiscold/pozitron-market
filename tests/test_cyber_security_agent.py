import unittest
import os
from orchestrator.subagent_security import CyberSecurityAgent
from database import is_subagent_enabled, set_subagent_enabled

class TestCyberSecurityAgent(unittest.TestCase):

    def setUp(self):
        self.agent = CyberSecurityAgent()

    def test_agent_initialization(self):
        self.assertEqual(self.agent.agent_id, "subagent_9_security")
        self.assertTrue(os.path.exists(self.agent.db_path))

    def test_subagent_enabled_in_db(self):
        self.assertTrue(is_subagent_enabled("subagent_9_security"))
        # Test toggle
        set_subagent_enabled("subagent_9_security", False)
        self.assertFalse(is_subagent_enabled("subagent_9_security"))
        set_subagent_enabled("subagent_9_security", True)
        self.assertTrue(is_subagent_enabled("subagent_9_security"))

    def test_full_security_audit_execution(self):
        report = self.agent.run_full_security_audit()
        self.assertIn("audit_id", report)
        self.assertIn("score", report)
        self.assertIn("status", report)
        self.assertGreaterEqual(report["score"], 0)
        self.assertLessEqual(report["score"], 100)
        self.assertGreaterEqual(report["probes_count"], 5)
        self.assertIsInstance(report["recommendations"], list)

    def test_sql_injection_defense_probe(self):
        probe = self.agent._probe_sql_injection_defense()
        self.assertIn("passed", probe)
        self.assertTrue(probe["passed"])

    def test_secret_leakage_probe(self):
        probe = self.agent._probe_secret_leakage()
        self.assertIn("passed", probe)
        self.assertTrue(probe["passed"])

    def test_get_latest_audit_retrieval(self):
        audit = self.agent.get_latest_audit()
        self.assertIsNotNone(audit)
        self.assertIn("score", audit)

if __name__ == "__main__":
    unittest.main()
