import unittest
from instagram_agent.engagement import InstagramEngagementEngine, TARGET_HASHTAGS
from reddit_agent.db import get_agent_config

class TestTurkishTargeting(unittest.TestCase):
    def setUp(self):
        self.engine = InstagramEngagementEngine()

    def test_turkish_drone_profile_validation(self):
        # Turkish pilot profiles should pass
        self.assertTrue(self.engine.is_turkish_drone_profile("fpv_pilot_ali", "Harika bir uçuş günü, kırımsız geçtik!"))
        self.assertTrue(self.engine.is_turkish_drone_profile("teknofest_iha_takimi", "Yeni quadcopter prototipimizin test uçuşları"))
        self.assertTrue(self.engine.is_turkish_drone_profile("istanbul_drone", "İstanbul semalarında gün batımı kadrajı"))
        self.assertTrue(self.engine.is_turkish_drone_profile("mehmet_fpvtr", "Yeni lehimleme ve motor montajı bitti"))
        
        # Foreign language profiles should be strictly rejected
        self.assertFalse(self.engine.is_turkish_drone_profile("carlos_fpv", "Muchas gracias por el apoyo, buen vuelo"))
        self.assertFalse(self.engine.is_turkish_drone_profile("lucas_drones", "Obrigado pelo voo incrivel amigo"))
        self.assertFalse(self.engine.is_turkish_drone_profile("jean_pilot", "Merci pour la video bon vol mon ami"))
        self.assertFalse(self.engine.is_turkish_drone_profile("hans_drone", "Danke schoen fuer das tolle video"))

    def test_target_hashtags_are_turkish(self):
        expected_tags = {'fpvturkey', 'droneturkey', 'turkeyfpv', 'teknofest', 'teknofestiha', 'fpvtürkiye', 'dronetürkiye', 'turkdrone'}
        self.assertEqual(set(TARGET_HASHTAGS), expected_tags)

    def test_reddit_configured_subreddits_include_turkish(self):
        cfg = get_agent_config()
        subreddits = cfg.get("subreddits", "").lower()
        self.assertIn("turkey", subreddits)
        self.assertIn("teknoloji", subreddits)
        self.assertIn("bilim", subreddits)
        self.assertIn("askturkey", subreddits)

if __name__ == '__main__':
    unittest.main()
