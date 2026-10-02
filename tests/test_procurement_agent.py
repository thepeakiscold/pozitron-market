import os
import json
import unittest
import urllib.request
from orchestrator.subagent_procurement import ProcurementOrderAgent

class TestProcurementOrderAgent(unittest.TestCase):

    def setUp(self):
        self.agent = ProcurementOrderAgent()

    def test_agent_initialization(self):
        self.assertEqual(self.agent.model_code, "gemini-3.8-flash")
        self.assertGreater(self.agent.usd_try_rate, 30.0)

    def test_analyze_and_generate_order_plan(self):
        plan = self.agent.analyze_and_generate_order_plan(target_budget_try=150000.0)
        self.assertTrue(plan.get("success"))
        self.assertTrue(plan.get("id") or plan.get("plan_id"))
        self.assertGreater(plan.get("total_skus", 0), 0)
        self.assertGreater(plan.get("total_quantity", 0), 0)
        self.assertGreater(plan.get("total_investment_try", 0), 0)
        self.assertGreater(plan.get("total_profit_try", 0), 0)
        self.assertGreater(plan.get("average_margin_pct", 0), 30.0)

        # Check items structure
        items = plan.get("items", [])
        self.assertGreater(len(items), 0)
        first = items[0]
        self.assertIn("sku", first)
        self.assertIn("name", first)
        self.assertIn("unit_cost_try", first)
        self.assertIn("unit_sale_price_try", first)
        self.assertIn("margin_pct", first)
        self.assertIn("recommended_qty", first)
        self.assertIn("urgency", first)
        self.assertIn(first["urgency"], ["KRİTİK", "YÜKSEK", "ORTA"])

        # Check file outputs
        json_path = "data/latest_procurement_plan.json"
        self.assertTrue(os.path.exists(json_path))
        with open(json_path, "r", encoding="utf-8") as f:
            saved_json = json.load(f)
            self.assertEqual(saved_json["id"], plan["id"])

        csv_path = "data/latest_procurement_order.csv"
        self.assertTrue(os.path.exists(csv_path))
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 1)
            self.assertIn("Oncelik", lines[0])

    def test_get_latest_plan(self):
        latest = self.agent.get_latest_plan()
        self.assertIsNotNone(latest)
        self.assertIn("id", latest)
        self.assertIn("items", latest)

    def test_api_procurement_latest(self):
        url = "http://localhost:8000/api/procurement/latest"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data.get("success"))
            self.assertIn("plan", data)
            self.assertGreater(len(data["plan"]["items"]), 0)

    def test_api_procurement_generate(self):
        url = "http://localhost:8000/api/procurement/generate"
        req = urllib.request.Request(
            url,
            data=json.dumps({"budget_try": 200000.0}).encode('utf-8'),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode('utf-8'))
            self.assertTrue(data.get("success"))
            self.assertIn("plan", data)
            self.assertGreater(data["plan"]["total_skus"], 0)

    def test_api_procurement_export_csv(self):
        url = "http://localhost:8000/api/procurement/export"
        with urllib.request.urlopen(url, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Type"), "text/csv; charset=utf-8")
            csv_content = resp.read().decode('utf-8-sig')
            self.assertIn("Oncelik", csv_content)
            self.assertIn("Urun Adi", csv_content)

if __name__ == '__main__':
    unittest.main()
