import unittest
import sqlite3
import json
import os
from orchestrator.subagent_trend_hunter import GlobalTrendHunterAgent
from orchestrator.lead_supervisor import LeadSupervisorAgent

class TestTrendHunterPriceComparison(unittest.TestCase):
    def setUp(self):
        self.agent = GlobalTrendHunterAgent()
        self.supervisor = LeadSupervisorAgent()

    def test_out_of_stock_prices_are_strictly_ignored(self):
        """
        Kullanıcı Kuralı Doğrulaması:
        Stokta olmayan satıcıların fiyatları eski/bayat olabileceğinden KESİNLİKLE dikkate alınmamalıdır.
        """
        conn = sqlite3.connect('pozitron.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT sku, price_try FROM products LIMIT 15")
        products = cursor.fetchall()
        conn.close()

        total_stale_found = 0
        for p in products:
            sku = p['sku']
            poz_price = float(p['price_try'])
            offers = self.agent._simulate_market_offers(sku, poz_price)
            
            # Tekliflerin içinde hem stoklu hem stoksuz olanlar var mı incele
            active_in_stock = [o for o in offers if o["in_stock"]]
            out_of_stock = [o for o in offers if not o["in_stock"]]
            
            if out_of_stock:
                total_stale_found += len(out_of_stock)
                # Stokta olmayan tekliflerin hepsi in_stock=False ve stock_note bayat fiyat açıklamalı olmalı
                for stale in out_of_stock:
                    self.assertFalse(stale["in_stock"])
                    self.assertIn("Dikkate alınmadı", stale["stock_note"])

        self.assertGreater(total_stale_found, 0, "En az bir stoksuz/bayat teklif üretilmeli ve elenmeli.")

    def test_scan_store_price_comparison_populates_database(self):
        """
        Tüm kataloğu tarayıp trend_price_comparisons tablosuna yazıldığını doğrular.
        """
        res = self.agent.scan_store_price_comparison()
        self.assertTrue(res["success"])
        self.assertEqual(res["total_scanned"], 506)
        self.assertGreater(res["total_stale_prices_ignored"], 0, "Stoksuz eski fiyatlar elenmiş olmalı.")
        self.assertGreater(res["too_cheap_alerts"], 0, "Aşırı ucuz uyarıları üretilmiş olmalı.")

        summary = self.agent.get_price_warning_summary()
        self.assertEqual(summary["total_products"], 506)
        self.assertGreater(summary["too_cheap_count"], 0)
        self.assertGreater(summary["total_stale_prices_ignored"], 0)

    def test_too_cheap_alert_detection_and_warning(self):
        """
        Pozitron fiyatı Türkiye en ucuzundan %25+ daha ucuzsa TOO_CHEAP_ALERT uyarısı verilmelidir.
        """
        report = self.agent.get_price_comparison_report(warning_only=True, limit=20)
        self.assertGreater(len(report["items"]), 0, "Aşırı ucuz uyarıları listelenmeli.")

        first_warning = report["items"][0]
        self.assertEqual(first_warning["status"], "TOO_CHEAP_ALERT")
        self.assertIn(first_warning["warning_level"], ["WARNING", "CRITICAL"])
        self.assertGreaterEqual(first_warning["price_diff_pct"], 25.0)
        self.assertIn("AŞIRI UCUZ", first_warning["warning_message"])
        self.assertIsNotNone(first_warning["recommended_price_try"])
        self.assertGreater(first_warning["recommended_price_try"], first_warning["pozitron_price_try"])

    def test_update_product_price_and_status_resolution(self):
        """
        Aşırı ucuz olan bir ürünün fiyatı önerilen tutara çekildiğinde uyarının çözüldüğünü
        ve durumun COMPETITIVE olduğunu doğrular.
        """
        warnings = self.agent.get_price_comparison_report(warning_only=True, limit=5)
        self.assertTrue(len(warnings["items"]) > 0)
        target = warnings["items"][0]
        sku = target["sku"]
        old_price = target["pozitron_price_try"]
        rec_price = target["recommended_price_try"]

        # Fiyatı önerilen tutara çek
        update_res = self.agent.update_product_price(sku, rec_price)
        self.assertTrue(update_res["success"])
        self.assertEqual(update_res["new_status"], "COMPETITIVE")
        self.assertLess(update_res["price_diff_pct"], 25.0)

        # Geri al (orijinal fiyata döndür)
        restore_res = self.agent.update_product_price(sku, old_price)
        self.assertTrue(restore_res["success"])

    def test_market_out_of_stock_scenario(self):
        """
        Tüm piyasada stok yoksa OUT_OF_STOCK_MARKET verilmeli ve eski fiyatlar yok sayılmalıdır.
        """
        report = self.agent.get_price_comparison_report(status_filter="OUT_OF_STOCK_MARKET", limit=10)
        if report["items"]:
            item = report["items"][0]
            self.assertEqual(item["status"], "OUT_OF_STOCK_MARKET")
            self.assertIsNone(item["turkey_min_price_try"])
            self.assertIn("yok sayıldı", item["warning_message"])

if __name__ == "__main__":
    unittest.main()
