import unittest
import sqlite3
import json
import re
from orchestrator.subagent_seo import TechnicalSeoAgent, TOPIC_REPOSITORY, turkish_to_slug, normalize_topic_keywords

class TestSeoDeduplicationAndTurkishTargeting(unittest.TestCase):
    def setUp(self):
        self.agent = TechnicalSeoAgent()

    def test_topic_covered_detection(self):
        """Verifies that an already covered topic is accurately detected."""
        # LiPo topic was inserted
        is_covered = self.agent.is_topic_covered("LiPo Batarya Güvenliği ve Şarj Kuralları")
        self.assertTrue(is_covered, "Previously covered LiPo topic must be detected as covered")

        # Fake new topic should not be covered
        is_covered_fake = self.agent.is_topic_covered("Mars Kolonisi FPV İyon Motoru Plazma İticisi")
        self.assertFalse(is_covered_fake, "Non-existent futuristic topic should not be marked as covered")

    def test_get_next_unwritten_topic(self):
        """Verifies that next unwritten topic is dynamic and not already covered."""
        next_topic = self.agent.get_next_unwritten_topic()
        self.assertIsInstance(next_topic, dict)
        self.assertIn("component_focus", next_topic)
        self.assertIn("target_keywords", next_topic)

        # Ensure the topic picked is NOT already published in seo_articles
        covered = self.agent.is_topic_covered(next_topic["component_focus"])
        self.assertFalse(covered, f"Next topic '{next_topic['component_focus']}' should not be already covered!")

    def test_generate_article_avoids_duplication(self):
        """Ensures calling generate_article on an existing topic automatically switches to an unwritten topic."""
        # Provide an existing covered topic without force
        article = self.agent.generate_article(
            component_focus="LiPo Batarya Güvenliği ve Şarj Kuralları",
            force=False
        )
        self.assertIsNotNone(article)
        # Because LiPo is already covered, it must not repeat LiPo
        self.assertNotIn("LiPo Batarya Güvenliği ve Şarj Kuralları", article["component_focus"])

    def test_turkish_characters_present_in_all_guides(self):
        """Verifies that all stored articles have proper Turkish characters and no broken ASCII words."""
        articles = self.agent.get_articles(limit=100)
        self.assertGreaterEqual(len(articles), 5, "Should have at least 5 distinct articles")

        turkish_chars = set("çğışöüÇĞİŞÖÜ")
        for art in articles:
            title = art["title"]
            content = art["content_markdown"]

            # Must contain Turkish characters
            has_tr_title = any(c in turkish_chars for c in title)
            has_tr_content = any(c in turkish_chars for c in content)
            self.assertTrue(has_tr_title or has_tr_content, f"Article '{title}' should contain Turkish characters")

            # Must not contain common broken ASCII headers
            self.assertNotIn("Ucus Kontrol", title, f"Title has ASCII 'Ucus': {title}")
            self.assertNotIn("Secimi", title, f"Title has ASCII 'Secimi': {title}")
            self.assertNotIn("[IPUCU]", content, "Content has ASCII '[IPUCU]' instead of '[İPUCU]'")
            self.assertNotIn("Tum donanim", content, "Content has ASCII 'Tum donanim' instead of 'Tüm donanım'")

    def test_no_duplicate_titles_or_focuses_in_database(self):
        """Verifies that every article in the database has a unique title and focus."""
        articles = self.agent.get_articles(limit=100)
        titles = [a["title"] for a in articles]
        focuses = [a["component_focus"] for a in articles]

        self.assertEqual(len(titles), len(set(titles)), f"Duplicate titles found in database: {titles}")
        self.assertEqual(len(focuses), len(set(focuses)), f"Duplicate focuses found in database: {focuses}")

    def test_static_json_and_db_parity(self):
        """Verifies that data/seo_articles.json has all the articles present in database."""
        with open("data/seo_articles.json", "r", encoding="utf-8") as f:
            json_articles = json.load(f)

        db_articles = self.agent.get_articles(limit=100)
        self.assertEqual(len(json_articles), len(db_articles), "JSON export and DB article counts must match")

if __name__ == '__main__':
    unittest.main()
