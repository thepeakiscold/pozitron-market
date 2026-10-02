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

        summary = self.agent.get_price_warning_summary()
        self.assertEqual(summary["total_products"], 506)
        self.assertGreater(summary["total_stale_prices_ignored"], 0)

    def test_auto_update_too_cheap_products_to_five_percent_below_market(self):
        """
        Kullanıcı Kuralı Doğrulaması:
        Fiyatı çok düşük/aşırı ucuz olan ürünler her tespit edildiğinde,
        Trend Avcısı ürünün fiyatını otomatik olarak piyasa en ucuzunun %5 altına günceller.
        """
        conn = sqlite3.connect('pozitron.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Test ürünü olarak PZTR-MOT-0009 seçelim ve piyasanın çok altına çekelim
        cursor.execute("SELECT turkey_min_price_try FROM trend_price_comparisons WHERE sku = 'PZTR-MOT-0009'")
        row = cursor.fetchone()
        turkey_min = float(row['turkey_min_price_try']) if row and row['turkey_min_price_try'] else 2144.35

        # Fiyatı piyasanın %40 altına (aşırı ucuz) ayarlayalım
        artificially_low_price = round(turkey_min * 0.60, 2)
        cursor.execute("UPDATE products SET price_try = ?, price_usd = 10.0 WHERE sku = 'PZTR-MOT-0009'", (artificially_low_price,))
        conn.commit()
        conn.close()

        # Otomatik güncelleme ile taramayı çalıştır
        res = self.agent.scan_store_price_comparison(auto_update_too_cheap=True)
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["too_cheap_alerts"], 1)
        self.assertGreaterEqual(res["auto_updated_count"], 1)

        # Ürünün yeni fiyatının piyasanın tam %5 altı olduğunu doğrula
        conn = sqlite3.connect('pozitron.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT price_try FROM products WHERE sku = 'PZTR-MOT-0009'")
        new_prod_price = float(cursor.fetchone()['price_try'])

        cursor.execute("SELECT * FROM trend_price_comparisons WHERE sku = 'PZTR-MOT-0009'")
        comp = dict(cursor.fetchone())
        conn.close()

        expected_five_pct_below = round(turkey_min * 0.95, 2)
        self.assertEqual(new_prod_price, expected_five_pct_below)
        self.assertEqual(comp["status"], "COMPETITIVE")
        self.assertEqual(comp["price_diff_pct"], 5.0)
        self.assertIn("Otomatik Fiyat Güncellendi", comp["warning_message"])

    def test_too_cheap_alert_detection_and_warning_dry_run(self):
        """
        auto_update_too_cheap=False (kuru çalışma/sadece uyarı) durumunda
        fiyatı değiştirmeden TOO_CHEAP_ALERT oluşturduğunu ve önerilen fiyatın
        piyasanın %5 altı olduğunu doğrular.
        """
        conn = sqlite3.connect('pozitron.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT turkey_min_price_try FROM trend_price_comparisons WHERE sku = 'PZTR-PRO-0111'")
        row = cursor.fetchone()
        turkey_min = float(row['turkey_min_price_try']) if row and row['turkey_min_price_try'] else 297.25

        artificially_low_price = round(turkey_min * 0.50, 2)
        cursor.execute("UPDATE products SET price_try = ?, price_usd = 5.0 WHERE sku = 'PZTR-PRO-0111'", (artificially_low_price,))
        conn.commit()
        conn.close()

        # Otomatik güncelleme kapalıyken tara
        res = self.agent.scan_store_price_comparison(auto_update_too_cheap=False)
        self.assertGreaterEqual(res["too_cheap_alerts"], 1)

        report = self.agent.get_price_comparison_report(warning_only=True, limit=20)
        self.assertGreater(len(report["items"]), 0, "Aşırı ucuz uyarıları listelenmeli.")

        target = [it for it in report["items"] if it["sku"] == "PZTR-PRO-0111"][0]
        self.assertEqual(target["status"], "TOO_CHEAP_ALERT")
        expected_rec_price = round(turkey_min * 0.95, 2)
        self.assertEqual(target["recommended_price_try"], expected_rec_price)

        # Temizlik: Otomatik güncelleme ile düzelt
        self.agent.scan_store_price_comparison(auto_update_too_cheap=True)

    def test_update_product_price_and_status_resolution(self):
        """
        Manuel fiyat güncelleme metodunun (update_product_price) önerilen tutara çekildiğinde
        kataloğu ve durumu COMPETITIVE olarak güncellediğini doğrular.
        """
        sku = "PZTR-MOT-0009"
        conn = sqlite3.connect('pozitron.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT turkey_min_price_try FROM trend_price_comparisons WHERE sku = ?", (sku,))
        turkey_min = float(cursor.fetchone()['turkey_min_price_try'])
        conn.close()

        rec_price = round(turkey_min * 0.95, 2)

        update_res = self.agent.update_product_price(sku, rec_price)
        self.assertTrue(update_res["success"])
        self.assertEqual(update_res["new_status"], "COMPETITIVE")
        self.assertEqual(update_res["price_diff_pct"], 5.0)

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
