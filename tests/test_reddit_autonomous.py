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

    def test_english_drone_posts_rejected(self):
        """Ensure English/foreign drone posts are strictly rejected even in drone subreddits."""
        english_posts = [
            {"title": "Best indoor rates for Meteor75 Pro II?", "body": "Looking for smooth indoor rates", "subreddit": "fpv", "author": "user1"},
            {"title": "How to bind ELRS receiver to RadioMaster Boxer?", "body": "Please help with receiver setup", "subreddit": "fpvturkey", "author": "user2"},
            {"title": "DJI Mini 3 Pro or Mini 4 Pro for beginner?", "body": "Which one should I buy? Thanks!", "subreddit": "drones", "author": "user3"},
            {"title": "ESC burned after crash, what should I do?", "body": "Need recommendation for replacement", "subreddit": "multicopter", "author": "user4"},
        ]
        for p in english_posts:
            self.assertFalse(self.client.is_question_matching_keywords(p, self.keywords), f"English post should be rejected: {p['title']}")

    def test_human_technician_reply_format(self):
        """
        Ensure generated replies follow the strict user requirements:
        1. English keyboard ASCII characters only (no ç, ğ, ı, ö, ş, ü).
        2. 100% lowercase.
        3. Zero punctuation marks.
        4. No bot/AI signature.
        """
        import re
        from reddit_agent.ai_engine import GeminiRedditEngine, format_human_reddit_reply
        engine = GeminiRedditEngine(api_key="")  # uses rule-based fallback

        sample_posts = [
            {"title": "5 inç freestyle FPV drone için 4S mi yoksa 6S batarya mı tercih etmeliyim?", "body": "Hangi voltaj daha mantıklı?", "subreddit": "fpvturkey", "author": "pilot1"},
            {"title": "Betaflight alıcıyı görmüyor", "body": "ELRS UART bağlantısı nasıl yapılır?", "subreddit": "teknoloji", "author": "pilot2"},
            {"title": "LiPo bataryaları kışın nasıl saklamalıyım?", "body": "Hücre voltajı kaç olmalı?", "subreddit": "Turkey", "author": "pilot3"},
            {"title": "500 gram altı drone uçurmak için SHGM kaydı gerekiyor mu?", "body": "İzin kuralları nasıl?", "subreddit": "AskTurkey", "author": "pilot4"},
        ]

        turkish_specific_chars = set("çğıöşüÇĞİÖŞÜ")

        for p in sample_posts:
            res = engine.evaluate_and_generate_reply(p["title"], p["body"], p["subreddit"], p["author"])
            self.assertTrue(res["is_drone_question"], f"Should be drone question: {p['title']}")
            reply = res["reply_text"]
            self.assertTrue(len(reply) > 0, "Reply text should not be empty")

            # 1. 100% lowercase
            self.assertEqual(reply, reply.lower(), "Reply must be 100% lowercase")

            # 2. English keyboard ASCII characters only
            for ch in reply:
                self.assertNotIn(ch, turkish_specific_chars, f"Special Turkish char found: '{ch}' in reply: {reply}")

            # 3. Zero punctuation marks
            invalid_chars = re.findall(r'[^a-z0-9\s]', reply)
            self.assertEqual(invalid_chars, [], f"Punctuation/invalid characters found: {invalid_chars} in reply: {reply}")

            # 4. No robot signature
            self.assertNotIn("pozitron market*", reply)
            self.assertNotIn("[pozitron market]", reply)
            self.assertNotIn("kırımsız günler", reply)

    def tearDown(self):
        from database import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reddit_interactions WHERE reddit_id LIKE 't3_drone_test_%'")
        conn.commit()
        conn.close()

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
        agent.update_config({
            "is_autonomous_enabled": 1,
            "dry_run_mode": 0,
            "auto_post_min_confidence": 70
        })

        result = agent.scan_and_process(autonomous=True)
        self.assertGreaterEqual(result["auto_published_count"], 1, "Should auto-publish the answer without manual approval")
        self.assertTrue(mock_post.called, "post_reply should be invoked directly")

    @patch("requests.get")
    def test_search_drone_questions(self, mock_get):
        """Ensure search_drone_questions queries reddit and parses results."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "data": {
                "children": [
                    {
                        "data": {
                            "id": "abc1234",
                            "title": "İlk drone için tercihiniz hangisi olurdu?",
                            "selftext": "DJI mı FPV mi önerirsiniz?",
                            "author": "fpv_user",
                            "subreddit": "teknoloji",
                            "permalink": "/r/teknoloji/comments/abc1234/",
                            "created_utc": 1787400000.0,
                            "score": 10,
                            "num_comments": 4,
                            "archived": False,
                            "locked": False
                        }
                    }
                ]
            }
        }
        res = self.client.search_drone_questions("teknoloji", query="drone", limit=5)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["short_id"], "abc1234")
        self.assertEqual(res[0]["title"], "İlk drone için tercihiniz hangisi olurdu?")

    def test_archived_or_too_old_posts_ignored(self):
        """Ensure archived or posts older than 90 days are excluded to avoid TOO_OLD errors."""
        import time
        old_time = time.time() - (120 * 86400)
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "data": {
                    "children": [
                        {
                            "data": {
                                "id": "old1",
                                "title": "Old drone question",
                                "selftext": "archived text",
                                "created_utc": old_time,
                                "archived": False
                            }
                        },
                        {
                            "data": {
                                "id": "archived1",
                                "title": "Archived drone question",
                                "selftext": "locked text",
                                "created_utc": time.time(),
                                "archived": True
                            }
                        }
                    ]
                }
            }
            res = self.client.search_drone_questions("teknoloji", query="drone")
            self.assertEqual(len(res), 0, "Archived and old posts should be ignored")

if __name__ == '__main__':
    unittest.main()

