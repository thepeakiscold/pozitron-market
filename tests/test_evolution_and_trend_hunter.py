import unittest
import sqlite3
import os
import json
from orchestrator.subagent_trend_hunter import GlobalTrendHunterAgent
from orchestrator.lead_supervisor import LeadSupervisorAgent

class TestEvolutionAndTrendHunter(unittest.TestCase):
    def setUp(self):
        self.trend_agent = GlobalTrendHunterAgent()
        self.supervisor = LeadSupervisorAgent()

    def test_trend_hunter_pricing_logic(self):
        pricing = self.trend_agent.calculate_competitive_pricing(
            global_price_usd=69.99,
            turkish_market_price_try=3750.0
        )
        self.assertIn("price_usd", pricing)
        self.assertIn("price_try", pricing)
        self.assertIn("savings_try", pricing)
        self.assertLess(pricing["price_try"], 3750.0)
        self.assertGreater(pricing["savings_try"], 0)

    def test_trend_hunter_proposals_flow(self):
        new_proposals = self.trend_agent.scan_global_trends(limit=3)
        self.assertIsInstance(new_proposals, list)
        
        all_proposals = self.trend_agent.get_proposals()
        self.assertGreater(len(all_proposals), 0)

    def test_supervisor_evolution_cycle(self):
        evo = self.supervisor.evolve_strategy_cycle()
        self.assertIn("evolution_cycle_id", evo)
        self.assertEqual(evo["growth_mode"], "AGGRESSIVE_EXPANSION")
        self.assertEqual(evo["model_used"], "gemini-3.8-flash")
        self.assertIn("diagnosed_bottlenecks", evo)
        self.assertIn("strategic_adjustments", evo)
        self.assertIn("ai_reasoning", evo)
        self.assertGreater(len(evo["ai_reasoning"]), 50)

    def test_evolution_history_saved(self):
        history = self.supervisor.get_evolution_history(limit=5)
        self.assertGreater(len(history), 0)
        first = history[0]
        self.assertIn("evolution_cycle_id", first)
        self.assertIn("growth_mode", first)

if __name__ == "__main__":
    unittest.main()
