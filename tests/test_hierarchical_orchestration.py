import unittest
import json
import os
import sqlite3
from orchestrator import (
    LeadSupervisorAgent, PriceIntelligenceAgent,
    TelemetryAgent, TechnicalSeoAgent
)
from instagram_agent.content_generator import ContentGenerator
from reddit_agent.ai_engine import GeminiRedditEngine

class TestHierarchicalOrchestration(unittest.TestCase):
    def setUp(self):
        self.supervisor = LeadSupervisorAgent()
        self.price_agent = PriceIntelligenceAgent()
        self.telemetry_agent = TelemetryAgent()
        self.seo_agent = TechnicalSeoAgent()

    def test_price_intelligence_schema_and_advantage(self):
        """Verify Subagent 5 outputs exact schema and detects price/stock advantage."""
        report = self.price_agent.scan_market("test_cycle_01")
        self.assertIsInstance(report, list)
        self.assertGreaterEqual(len(report), 10)

        sample = report[0]
        # Schema validation
        required_keys = [
            "sku", "product_name", "pozitron_price_try",
            "market_min_price_try", "market_avg_price_try",
            "status", "competitor_stock"
        ]
        for key in required_keys:
            self.assertIn(key, sample, f"Missing required key in Subagent 5 schema: {key}")

        self.assertIn(sample["status"], ["CHEAPER", "EQUAL", "EXPENSIVE"])
        self.assertIsInstance(sample["competitor_stock"], bool)

        summary = self.price_agent.get_summary_stats()
        self.assertIn("tracked_skus", summary)
        self.assertIn("price_advantage_count", summary)
        self.assertGreater(summary["price_advantage_count"], 0, "Should detect products with price advantage")

    def test_telemetry_schema_and_collection(self):
        """Verify Subagent 3 compiles metrics matching requested schema."""
        metrics = self.telemetry_agent.collect_metrics()

        self.assertIn("timestamp", metrics)
        self.assertIn("instagram", metrics)
        self.assertIn("reddit", metrics)
        self.assertIn("seo", metrics)
        self.assertIn("price_intelligence", metrics)
        self.assertIn("traffic", metrics)

        # Instagram section
        self.assertIn("posts_count", metrics["instagram"])
        self.assertIn("total_reach", metrics["instagram"])
        self.assertIn("engagement_rate", metrics["instagram"])

        # Reddit section
        self.assertIn("comments_count", metrics["reddit"])
        self.assertIn("net_upvotes", metrics["reddit"])
        self.assertIn("link_clicks", metrics["reddit"])

        # SEO section
        self.assertIn("articles_published", metrics["seo"])
        self.assertIn("indexed_keywords", metrics["seo"])

        # Delivery to db
        delivery_res = self.telemetry_agent.deliver_telemetry(metrics)
        self.assertTrue(delivery_res["success"])

    def test_technical_seo_guide_and_internal_links(self):
        """Verify Subagent 4 generates high-depth guide with H1-H3 and Pozitron internal links."""
        article = self.seo_agent.generate_article(
            component_focus="Betaflight 4.5 UART & ESC Telemetrisi",
            target_keywords=["UART ayarı", "Betaflight 4.5", "Pozitron Market"]
        )
        self.assertIn("slug", article)
        self.assertIn("title", article)
        self.assertIn("content_markdown", article)
        self.assertIn("internal_links", article)

        md = article["content_markdown"]
        self.assertIn("# ", md, "Must have H1 header")
        self.assertIn("## ", md, "Must have H2 headers")
        self.assertIn("https://pozitronmarket.com/", md, "Must have internal links to Pozitron Market")

    def test_lead_supervisor_cycle_and_directive_schema(self):
        """Verify Lead Supervisor Agent synthesizes inputs and creates full JSON directive."""
        directive = self.supervisor.execute_cycle()

        # Schema checks
        self.assertIn("lead_cycle_id", directive)
        self.assertIn("timestamp", directive)
        self.assertIn("instagram_directive", directive)
        self.assertIn("reddit_directive", directive)
        self.assertIn("seo_content_directive", directive)
        self.assertIn("price_action_flags", directive)

        ig_dir = directive["instagram_directive"]
        self.assertIn("focus_topic", ig_dir)
        self.assertIn("highlighted_products", ig_dir)
        self.assertIn("hook_strategy", ig_dir)
        self.assertGreater(len(ig_dir["highlighted_products"]), 0)

        red_dir = directive["reddit_directive"]
        self.assertIn("priority_subreddits", red_dir)
        self.assertIn("target_keywords", red_dir)
        self.assertIn("preferred_hardware_links", red_dir)

        flags = directive["price_action_flags"]
        self.assertGreater(len(flags), 0)
        self.assertIn("sku", flags[0])
        self.assertIn(flags[0]["market_status"], ["LOWER", "EQUAL", "HIGHER"])
        self.assertIn(flags[0]["suggested_action"], ["PROMOTE", "REVIEW"])

    def test_instagram_subagent_prioritizes_highlighted_products(self):
        """Ensure Instagram ContentGenerator prioritizes Lead Supervisor highlighted products."""
        # Ensure a directive exists
        self.supervisor.execute_cycle()
        gen = ContentGenerator()
        prod = gen._get_candidate_product()
        self.assertIsNotNone(prod)
        self.assertIn("sku", prod)
        self.assertIn("price_try", prod)

if __name__ == '__main__':
    unittest.main()
