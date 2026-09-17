#!/usr/bin/env python3
"""
Unit tests for Autonomous Cloud Market Stock Deduction & Inventory Sync.
STRICT ZERO EMOJIS in code, logs, and docstrings.
"""
import unittest
import os
import json
import tempfile
import shutil
from scripts.cloud_market_sync import parse_order_items, process_order

class TestCloudMarketSync(unittest.TestCase):
    def setUp(self):
        self.mock_catalog = [
            {
                "id": 101,
                "sku": "GEP-MK5-O3",
                "name_tr": "GEPRC Mark5 O3 6S FPV Drone",
                "name_en": "GEPRC Mark5 O3 6S FPV Drone",
                "stock": 10,
                "in_stock": True,
                "price_try": 18500.0,
                "price_usd": 480.0
            },
            {
                "id": 102,
                "sku": "TMOT-F40-PRO",
                "name_tr": "T-Motor F40 PRO V 1950KV Motor",
                "name_en": "T-Motor F40 PRO V 1950KV Motor",
                "stock": 1,
                "in_stock": True,
                "price_try": 950.0,
                "price_usd": 28.0
            }
        ]

    def test_parse_structured_items_detail(self):
        order_data = {
            "order_number": "PZT-TEST-001",
            "items_detail": [
                {"id": 101, "sku": "GEP-MK5-O3", "quantity": 2, "name": "GEPRC Mark5"},
                {"id": 102, "sku": "TMOT-F40-PRO", "quantity": 1, "name": "T-Motor F40"}
            ]
        }
        parsed = parse_order_items(order_data, self.mock_catalog)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["id"], 101)
        self.assertEqual(parsed[0]["quantity"], 2)
        self.assertEqual(parsed[1]["id"], 102)
        self.assertEqual(parsed[1]["quantity"], 1)

    def test_parse_string_items_fallback(self):
        order_data = {
            "order_number": "PZT-TEST-002",
            "items": "2x GEPRC Mark5 O3, 1x T-Motor F40"
        }
        parsed = parse_order_items(order_data, self.mock_catalog)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["quantity"], 2)
        self.assertEqual(parsed[0]["id"], 101)
        self.assertEqual(parsed[1]["quantity"], 1)
        self.assertEqual(parsed[1]["id"], 102)

    def test_process_order_dry_run(self):
        order_data = {
            "order_number": "PZT-DRYRUN-001",
            "name": "Ahmet Yilmaz",
            "total_try": "19450.00",
            "total_usd": "508.00",
            "items_detail": [
                {"id": 101, "sku": "GEP-MK5-O3", "quantity": 3}
            ]
        }
        res = process_order(order_data, catalog=self.mock_catalog, dry_run=True)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["dry_run"])
        self.assertEqual(res["products_updated_count"], 1)
        deducted = res["items_deducted"][0]
        self.assertEqual(deducted["deducted_quantity"], 3)
        self.assertEqual(deducted["stock_after"], 7)

    def test_zero_stock_boundary_protection(self):
        # Purchasing more than available stock should clamp to 0 and not become negative
        order_data = {
            "order_number": "PZT-OVERFLOW-001",
            "items_detail": [
                {"id": 102, "sku": "TMOT-F40-PRO", "quantity": 99}
            ]
        }
        res = process_order(order_data, catalog=self.mock_catalog, dry_run=True)
        self.assertEqual(res["status"], "success")
        deducted = res["items_deducted"][0]
        self.assertEqual(deducted["stock_after"], 0)
        self.assertGreaterEqual(deducted["stock_after"], 0)

if __name__ == "__main__":
    unittest.main()
