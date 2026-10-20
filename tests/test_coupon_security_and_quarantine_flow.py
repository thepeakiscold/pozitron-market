import os
import sys
import json
import unittest
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import database
import coupons as coupon_service
from database import get_db
from orchestrator.subagent_media_inspector import ProductMediaInspectorAgent
from orchestrator.lead_supervisor import LeadSupervisorAgent


class TestCouponSecurityAndQuarantineFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        database.init_db()
        cls.test_coupons = []

    @classmethod
    def tearDownClass(cls):
        conn = get_db()
        for code in cls.test_coupons:
            conn.execute("DELETE FROM coupon_redemptions WHERE coupon_code = ?", (code,))
            conn.execute("DELETE FROM coupon_logs WHERE coupon_code = ?", (code,))
            conn.execute("DELETE FROM coupons WHERE code = ?", (code,))
        conn.commit()
        conn.close()

    def _create_coupon(self, code, **kwargs):
        self.test_coupons.append(code)
        return coupon_service.create_coupon(code, source="security_test", **kwargs)

    # --------------------------------------------------------------------------
    # 1. Coupon Security Tests
    # --------------------------------------------------------------------------

    def test_coupon_cross_identity_abuse_blocked(self):
        """A user cannot redeem once with user_id, and then redeem again as guest using the same email."""
        code = "SECCROSS1"
        self._create_coupon(code, discount_type="percent", discount_value=15, per_user_limit=1)

        conn = get_db()
        # 1. First redemption: logged in user 'pilot_123' with email 'ace@fpv.com'
        ok1, reason1 = coupon_service.redeem_coupon(
            conn, code, user_id="pilot_123", email="ace@fpv.com",
            order_id="ord-001", order_number="PZT-001", discount_try=150.0
        )
        conn.commit()
        self.assertTrue(ok1, f"First redemption failed: {reason1}")

        # 2. Validation check for guest checkout with the same email should fail
        val_guest = coupon_service.validate_coupon(code, subtotal_try=1000, email="ace@fpv.com")
        self.assertFalse(val_guest["valid"])
        self.assertEqual(val_guest["reason"], "already_used")

        # 3. Second redemption attempt: guest checkout without user_id, same email
        ok2, reason2 = coupon_service.redeem_coupon(
            conn, code, user_id=None, email="ace@fpv.com",
            order_id="ord-002", order_number="PZT-002", discount_try=150.0
        )
        conn.rollback()
        conn.close()
        self.assertFalse(ok2, "Guest checkout with same email was not blocked!")
        self.assertEqual(reason2, "already_used")

    def test_gmail_alias_normalization(self):
        """Gmail address dot tricks and plus addressing cannot bypass redemption limits."""
        code = "SECGMAIL1"
        self._create_coupon(code, discount_type="fixed", discount_value=100, min_order_try=500, per_user_limit=1)

        conn = get_db()
        # First redemption: user uses fpv.pilot@gmail.com
        ok1, _ = coupon_service.redeem_coupon(
            conn, code, email="fpv.pilot@gmail.com",
            order_id="ord-gm1", order_number="PZT-GM1", discount_try=100.0
        )
        conn.commit()
        self.assertTrue(ok1)

        # Attempt with plus alias: fpvpilot+discount@gmail.com
        val_plus = coupon_service.validate_coupon(code, subtotal_try=600, email="fpvpilot+discount@gmail.com")
        self.assertFalse(val_plus["valid"])
        self.assertEqual(val_plus["reason"], "already_used")

        # Attempt with dots: f.p.v.p.i.l.o.t@googlemail.com
        val_dots = coupon_service.validate_coupon(code, subtotal_try=600, email="f.p.v.p.i.l.o.t@googlemail.com")
        self.assertFalse(val_dots["valid"])
        self.assertEqual(val_dots["reason"], "already_used")

        # Second redemption blocked
        ok2, reason2 = coupon_service.redeem_coupon(
            conn, code, email="fpvpilot+test@gmail.com",
            order_id="ord-gm2", order_number="PZT-GM2", discount_try=100.0
        )
        conn.rollback()
        conn.close()
        self.assertFalse(ok2)
        self.assertEqual(reason2, "already_used")

    def test_multi_use_per_user_limit(self):
        """per_user_limit = 2 permits two redemptions and correctly blocks the third."""
        code = "SECMULTI2"
        self._create_coupon(code, discount_type="percent", discount_value=10, per_user_limit=2)

        conn = get_db()
        # 1st order
        ok1, _ = coupon_service.redeem_coupon(
            conn, code, user_id="racer_77", email="racer77@sky.org",
            order_id="ord-m1", order_number="PZT-M1", discount_try=50.0
        )
        conn.commit()
        self.assertTrue(ok1)

        # 2nd order: still valid
        val2 = coupon_service.validate_coupon(code, subtotal_try=500, user_id="racer_77", email="racer77@sky.org")
        self.assertTrue(val2["valid"])

        ok2, _ = coupon_service.redeem_coupon(
            conn, code, user_id="racer_77", email="racer77@sky.org",
            order_id="ord-m2", order_number="PZT-M2", discount_try=50.0
        )
        conn.commit()
        self.assertTrue(ok2)

        # 3rd order: must be blocked
        val3 = coupon_service.validate_coupon(code, subtotal_try=500, user_id="racer_77", email="racer77@sky.org")
        self.assertFalse(val3["valid"])
        self.assertEqual(val3["reason"], "already_used")

        ok3, reason3 = coupon_service.redeem_coupon(
            conn, code, user_id="racer_77", email="racer77@sky.org",
            order_id="ord-m3", order_number="PZT-M3", discount_try=50.0
        )
        conn.rollback()
        conn.close()
        self.assertFalse(ok3)
        self.assertEqual(reason3, "already_used")

    def test_discount_clamping_and_validation(self):
        """Fixed discounts cannot exceed subtotal; percentage discounts cannot exceed 100%."""
        fixed_coupon = {"discount_type": "fixed", "discount_value": 800.0, "max_discount_try": None}
        # Subtotal 500 TRY, fixed discount 800 TRY -> Clamped to 500 TRY
        d_usd, d_try = coupon_service.compute_discount(fixed_coupon, 0.0, 500.0)
        self.assertEqual(d_try, 500.0)

        pct_coupon = {"discount_type": "percent", "discount_value": 150.0, "max_discount_try": None}
        # 150% discount -> Clamped to 100% of subtotal (1000 TRY)
        d_usd, d_try = coupon_service.compute_discount(pct_coupon, 0.0, 1000.0)
        self.assertEqual(d_try, 1000.0)

        # Update coupon validation prevents corrupt values
        code = "SECVAL1"
        self._create_coupon(code, discount_type="percent", discount_value=10)
        with self.assertRaises(ValueError):
            coupon_service.update_coupon(code, discount_value=-20)
        with self.assertRaises(ValueError):
            coupon_service.update_coupon(code, discount_type="invalid_type")
        with self.assertRaises(ValueError):
            coupon_service.update_coupon(code, min_order_try=-10)

    # --------------------------------------------------------------------------
    # 2. Quarantine Auto-Remediation & Pipeline Flow Tests
    # --------------------------------------------------------------------------

    def test_quarantine_auto_remediation_dry_run_and_execution(self):
        """ProductMediaInspectorAgent detects quarantine candidates and auto-fixes them."""
        agent = ProductMediaInspectorAgent()

        # Step 1: Dry run
        dry_report = agent.auto_fix_quarantined_products(dry_run=True)
        self.assertTrue(dry_report["dry_run"])
        self.assertIn("candidates_found", dry_report)

        # Step 2: Target a specific candidate or dry run test
        if dry_report["candidates_found"] > 0:
            candidate = dry_report["fixes"][0]
            target_sku = candidate["sku"]
            new_img = candidate["new_image"]

            # Execute real fix on this single SKU
            real_report = agent.auto_fix_quarantined_products(dry_run=False, sku=target_sku)
            self.assertFalse(real_report["dry_run"])
            self.assertEqual(real_report["applied_fixes_count"], 1)

            # Verify database product record updated
            conn = get_db()
            row = conn.execute("SELECT image_url FROM products WHERE sku = ?", (target_sku,)).fetchone()
            conn.close()
            self.assertIsNotNone(row)
            self.assertEqual(row["image_url"], new_img)

            # Verify latest audit JSON synced
            with open(agent.audit_json_path, "r", encoding="utf-8") as f:
                audit_data = json.load(f)
            self.assertIn("last_auto_fix_at", audit_data)
            # The fixed SKU should no longer be in findings
            skus_in_findings = [item["sku"] for item in audit_data.get("findings", [])]
            self.assertNotIn(target_sku, skus_in_findings)

    def test_lead_supervisor_auto_remediation_step(self):
        """LeadSupervisorAgent includes step 11 for media auto-remediation in autonomous cycle."""
        supervisor = LeadSupervisorAgent()
        self.assertIsNotNone(supervisor.media_agent)

        # Verify step 11 exists in cycle method
        import inspect
        source = inspect.getsource(supervisor.execute_cycle)
        self.assertIn("subagent_10_media", source)
        self.assertIn("auto_fix_quarantined_products", source)


if __name__ == "__main__":
    unittest.main()
