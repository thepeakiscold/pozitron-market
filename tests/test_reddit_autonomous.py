import unittest
from unittest.mock import patch
from reddit_agent.reddit_client import RedditClient
from reddit_agent.agent import RedditDroneAgent

class TestRedditAutonomousBot(unittest.TestCase):
    def setUp(self):
        self.client = RedditClient(dry_run=True)
        self.keywords = [
            "drone", "fpv", "quadcopter", "betafpv", "dji", "kumanda", "lehim",
            "motor", "esc", "vtx", "gözlük", "batarya", "lipo", "teknofest",
            "betaflight", "inav", "elrs", "crossfire", "uçuş", "alıcı", "verici"
        ]
        from database import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reddit_interactions WHERE reddit_id LIKE 't3_drone_test_%'")
        conn.commit()
        conn.close()

    def test_false_positive_prevention_in_general_subreddits(self):
        """Ensure general subreddits only match posts with core drone keywords and question intent."""
        false_positive_posts = [
            {"title": "Samsungdan iphone'a geçiş?", "body": "Yeni alıcılar ne düşünüyor?", "subreddit": "teknoloji", "author": "user1"},
            {"title": "Hollandaya ticari gönderim", "body": "Alıcı gümrük öder mi?", "subreddit": "Turkey", "author": "user2"},
            {"title": "Astsubaylığı bırakıp İtalya’ya taşınmayı düşünüyorum", "body": "Uçuş tazminatı nedir?", "subreddit": "AskTurkey", "author": "user3"},
            {"title": "Bugün uçuş yaptım harikaydı", "body": "İstanbul'a uçakla gittim", "subreddit": "Turkey", "author": "user4"},
        ]
        for p in false_positive_posts:
            self.assertFalse(self.client.is_question_matching_keywords(p, self.keywords), f"Should not match: {p['title']}")

    def test_genuine_drone_questions_matched(self):
        """Ensure genuine drone questions are matched properly."""
        drone_posts = [
            {"title": "DJI Mini 4 Pro almayı düşünüyorum, bataryası kaç dakika gidiyor?", "body": "Başlangıç için tavsiye eder misiniz?", "subreddit": "Turkey", "author": "user1"},
            {"title": "Teknofest İHA serbest görev için F405 uçuş kartı önerisi", "body": "Hangi kartı önerirsiniz?", "subreddit": "teknoloji", "author": "user2"},
            {"title": "Betaflight alıcıyı görmüyor", "body": "ELRS UART bağlantısı nasıl yapılır?", "subreddit": "fpvturkey", "author": "user3"},
            {"title": "FPV drone motoru lehimlerken pad koptu ne yapmalıyım?", "body": "Tamir edilebilir mi?", "subreddit": "bilim", "author": "user4"},
        ]
        for p in drone_posts:
            self.assertTrue(self.client.is_question_matching_keywords(p, self.keywords), f"Should match: {p['title']}")

    @patch("reddit_agent.agent.RedditClient.post_reply")
    @patch("reddit_agent.agent.RedditClient.fetch_recent_posts")
    def test_autonomous_posting_without_approval(self, mock_fetch, mock_post):
        """Ensure questions found in autonomous mode are immediately posted without waiting for user approval."""
        mock_fetch.return_value = [
            {
                "reddit_id": "t3_drone_test_99",
                "short_id": "drone_test_99",
                "reddit_type": "submission",
                "title": "DJI drone motor arızası nasıl giderilir?",
                "body": "Pervane dönmüyor yardım lütfen",
                "author": "drone_pilot_tr",
                "subreddit": "teknoloji",
                "url": "https://reddit.com/r/teknoloji/comments/drone_test_99/",
                "permalink": "https://reddit.com/r/teknoloji/comments/drone_test_99/",
                "score": 5,
                "num_comments": 1
            }
        ]
        mock_post.return_value = {
            "success": True,
            "mode": "live_test",
            "comment_id": "cm_drone_99",
            "permalink": "https://reddit.com/r/teknoloji/comments/drone_test_99/comment/cm_drone_99/"
        }

        agent = RedditDroneAgent()
        agent.config["is_autonomous_enabled"] = 1
        agent.config["dry_run_mode"] = 0
        agent.config["auto_post_min_confidence"] = 70

        result = agent.scan_and_process(autonomous=True)
        self.assertGreaterEqual(result["auto_published_count"], 1, "Should auto-publish the answer without manual approval")
        self.assertTrue(mock_post.called, "post_reply should be invoked directly")

if __name__ == '__main__':
    unittest.main()
