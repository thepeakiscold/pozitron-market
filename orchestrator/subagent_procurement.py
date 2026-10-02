import sqlite3
import json
import uuid
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
from database import get_db

CURRENT_USD_RATE = 38.50  # USD to TRY reference

class ProcurementOrderAgent:
    """
    Subagent 8: Sipariş & Tedarik Optimizasyon Ajanı (Autonomous Procurement & Replenishment Agent)
    
    Çalışma Prensibi:
    1. Sitedeki mevcut ürünleri (stok = 0 olanlar, kritik stok seviyesindekiler, çok satanlar) tarar.
    2. Subagent 6 (Küresel Donanım Trend Avcısı) ile ortak çalışarak küresel trend önerilerini ve rakip stok açıklarını inceler.
    3. Hızlı satılacak (yüksek sirkülasyonlu) ve en yüksek kar marjı sağlayacak ürünleri tespit eder.
    4. Optimum sipariş adetleri (MOQ/parti büyüklüğü), tahmini yatırım tutarı ve beklenen net kar marjıyla tedarik planı üretir.
    5. Veritabanına (procurement_order_plans) ve data/ klasörüne JSON/CSV olarak kaydeder.
    """

    def __init__(self):
        self.model_code = "gemini-3.8-flash"
        self.usd_rate = CURRENT_USD_RATE
        self.usd_try_rate = CURRENT_USD_RATE

    def analyze_and_generate_order_plan(self, target_budget_try: float = 250000.0) -> Dict:
        """
        Runs comprehensive procurement intelligence scan across products, competitor trends,
        and global trend proposals to produce a prioritized purchase order plan.
        """
        conn = get_db()
        cursor = conn.cursor()

        # 1. Fetch site products with zero or low stock, or high popularity
        cursor.execute("""
            SELECT id, sku, name_tr, name_en, category_id, brand,
                   price_usd, price_try, stock, badge, rating, review_count, is_bestseller
            FROM products
            ORDER BY stock ASC, is_bestseller DESC, rating DESC
        """)
        products = [dict(r) for r in cursor.fetchall()]

        # 2. Fetch Trend Hunter global proposals (especially stock=0 items)
        cursor.execute("""
            SELECT id, name_tr, name_en, category_id, brand, price_usd, price_try,
                   trend_score, trend_reason, added_product_id, status
            FROM global_trend_proposals
            WHERE status = 'APPROVED' OR trend_score >= 80
            ORDER BY trend_score DESC
        """)
        trend_proposals = [dict(r) for r in cursor.fetchall()]

        # 3. Fetch competitor out-of-stock data from trend_price_comparisons
        cursor.execute("""
            SELECT product_id, product_name, turkey_min_price_try, in_stock_vendors_count, out_of_stock_vendors_count
            FROM trend_price_comparisons
            WHERE out_of_stock_vendors_count > 0 OR in_stock_vendors_count == 0
        """)
        competitor_stockouts = [dict(r) for r in cursor.fetchall()]
        stockout_product_ids = {c["product_id"] for c in competitor_stockouts if c.get("product_id")}

        conn.close()

        # Build candidate items for replenishment & procurement
        candidates = []
        seen_names = set()

        # A) Products from current catalog that are 0 stock or low stock (<= 5)
        for p in products:
            name = p["name_tr"] or p["name_en"]
            if name in seen_names:
                continue

            stock = p.get("stock", 0)
            price_try = float(p.get("price_try") or 0.0)
            price_usd = float(p.get("price_usd") or (price_try / self.usd_rate if price_try else 10.0))
            if price_try <= 0 and price_usd > 0:
                price_try = round(price_usd * self.usd_rate * 1.30, 2)

            # Estimated wholesale cost (typically 60-70% of retail price in FPV hardware)
            cost_try = round(price_usd * self.usd_rate * 0.72, 2) if price_usd > 0 else round(price_try * 0.65, 2)
            margin_try = max(price_try - cost_try, 50.0)
            margin_pct = round((margin_try / price_try) * 100, 1) if price_try > 0 else 30.0

            # Velocity scoring (1 - 100)
            velocity = 40
            cat_id = p.get("category_id") or ""
            is_consumable = any(k in cat_id.lower() or k in name.lower() for k in ["prop", "pervane", "batt", "pil", "lipo", "anten", "strap", "tpu", "vida"])
            
            if is_consumable:
                velocity += 25  # High-turnover consumables
            if p.get("is_bestseller"):
                velocity += 20
            if p.get("id") in stockout_product_ids:
                velocity += 15  # Competitors have no stock! Great sales opportunity
            if p.get("rating", 0) >= 4.8:
                velocity += 10
            if stock == 0:
                velocity += 15  # Immediate lost sales recovery

            velocity = min(velocity, 99)

            # Determine urgency
            if stock == 0 and (p.get("is_bestseller") or is_consumable or p.get("id") in stockout_product_ids):
                urgency = "KRİTİK"
            elif stock <= 3:
                urgency = "YÜKSEK"
            else:
                urgency = "ORTA"

            # Recommend quantity based on price and velocity
            if price_try < 300:
                qty = 80 if velocity >= 75 else 50
            elif price_try < 1200:
                qty = 30 if velocity >= 75 else 15
            elif price_try < 3500:
                qty = 12 if velocity >= 75 else 8
            else:
                qty = 6 if velocity >= 75 else 4

            # Prioritize zero-stock items and high-velocity items
            if stock <= 5 or p.get("is_bestseller") or p.get("id") in stockout_product_ids:
                candidates.append({
                    "product_id": p.get("id"),
                    "sku": p.get("sku"),
                    "name": name,
                    "brand": p.get("brand", "FPV"),
                    "category": cat_id,
                    "current_stock": stock,
                    "recommended_qty": qty,
                    "unit_cost_try": cost_try,
                    "unit_sale_price_try": price_try,
                    "unit_profit_try": margin_try,
                    "margin_pct": margin_pct,
                    "total_investment_try": round(cost_try * qty, 2),
                    "total_projected_profit_try": round(margin_try * qty, 2),
                    "velocity_score": velocity,
                    "urgency": urgency,
                    "source_type": "KATALOG_STOK_YENILEME",
                    "reason": f"Mevcut stok: {stock}. {'Rakipte stok yok. ' if p.get('id') in stockout_product_ids else ''}{'Çok satan ürün. ' if p.get('is_bestseller') else ''}{'Hızlı tükenen sarf malzeme.' if is_consumable else ''}".strip()
                })
                seen_names.add(name)

        # B) Candidates from Subagent 6 Global Trend Proposals (especially newly ingested stock=0 items)
        for tp in trend_proposals:
            name = tp["name_tr"] or tp["name_en"]
            if name in seen_names:
                continue

            price_usd = float(tp.get("price_usd") or 30.0)
            price_try = float(tp.get("price_try") or (price_usd * self.usd_rate * 1.30))
            cost_try = round(price_usd * self.usd_rate * 0.70, 2)
            margin_try = max(price_try - cost_try, 80.0)
            margin_pct = round((margin_try / price_try) * 100, 1)

            trend_score = tp.get("trend_score", 85)
            velocity = min(int(trend_score * 0.95), 98)
            urgency = "YÜKSEK" if trend_score >= 88 else "ORTA"

            if price_try < 500:
                qty = 40
            elif price_try < 2000:
                qty = 20
            elif price_try < 5000:
                qty = 8
            else:
                qty = 4

            candidates.append({
                "product_id": tp.get("added_product_id"),
                "sku": f"TREND-{tp['category_id'][:4].upper()}",
                "name": name,
                "brand": tp.get("brand", "Global Trend"),
                "category": tp.get("category_id"),
                "current_stock": 0,
                "recommended_qty": qty,
                "unit_cost_try": cost_try,
                "unit_sale_price_try": price_try,
                "unit_profit_try": margin_try,
                "margin_pct": margin_pct,
                "total_investment_try": round(cost_try * qty, 2),
                "total_projected_profit_try": round(margin_try * qty, 2),
                "velocity_score": velocity,
                "urgency": urgency,
                "source_type": "KURESEL_TREND_AVCISI",
                "reason": f"Trend Skoru: {trend_score}/100. {tp.get('trend_reason', 'Küresel talep zirvede.')}"
            })
            seen_names.add(name)

        # Sort candidates by Urgency (KRİTİK -> YÜKSEK -> ORTA) and Velocity Score
        urgency_weights = {"KRİTİK": 3, "YÜKSEK": 2, "ORTA": 1}
        candidates.sort(
            key=lambda x: (urgency_weights.get(x["urgency"], 0), x["velocity_score"], x["margin_pct"]),
            reverse=True
        )

        # Select top items within target budget or top 25 items
        selected_items = []
        running_budget = 0.0

        for item in candidates:
            item_inv = item["total_investment_try"]
            if running_budget + item_inv <= target_budget_try or len(selected_items) < 12:
                selected_items.append(item)
                running_budget += item_inv
            if len(selected_items) >= 25:
                break

        # Calculate Totals
        total_items_count = sum(it["recommended_qty"] for it in selected_items)
        total_investment = round(sum(it["total_investment_try"] for it in selected_items), 2)
        total_profit = round(sum(it["total_projected_profit_try"] for it in selected_items), 2)
        avg_margin = round(sum(it["margin_pct"] for it in selected_items) / len(selected_items), 1) if selected_items else 0.0
        roi_pct = round((total_profit / total_investment) * 100, 1) if total_investment > 0 else 0.0

        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        plan_id = f"plan_{uuid.uuid4().hex[:8]}"
        plan_title = f"Otonom Tedarik & Satınalma Planı — {now_str}"

        # Build Markdown Executive Summary
        md_summary = f"""# {plan_title}

**Hazırlayan:** Pozitron Subagent 8: Sipariş & Tedarik Optimizasyonu Ajanı  
**Ortak İstihbarat:** Subagent 6 Küresel Donanım Trend Avcısı + Rakip Fiyat Karşılaştırma Masası  
**Tarih:** {now_str}  
**Döviz Kuru Referansı:** 1 USD = {self.usd_rate} TL  

---

## 1. Yönetici Özeti & Finansal Projeksiyon

- **Toplam Sipariş Edilecek SKU (Ürün Çeşidi):** {len(selected_items)} Adet
- **Toplam Fiziksel Adet:** {total_items_count} Adet
- **Gereken Toplam Tedarik Yatırımı:** {total_investment:,.2f} TL
- **Beklenen Net Satış Karı:** {total_profit:,.2f} TL
- **Ortalama Brüt Kar Marjı:** %{avg_margin}
- **Yatırım Getirisi (ROI):** %{roi_pct}

---

## 2. Öncelikli Tedarik Listesi (Adet ve Karlılık Dağılımı)

| Öncelik | Ürün Adı | Kategori | Mevcut Stok | Önerilen Adet | Birim Maliyet | Satış Fiyatı | Kar Marjı | Toplam Yatırım | Beklenen Kar |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
"""
        for it in selected_items:
            md_summary += f"| **{it['urgency']}** | {it['name'][:42]} | {it['category'][:15]} | {it['current_stock']} | **{it['recommended_qty']}** | {it['unit_cost_try']} TL | {it['unit_sale_price_try']} TL | %{it['margin_pct']} | {it['total_investment_try']:,.0f} TL | **{it['total_projected_profit_try']:,.0f} TL** |\n"

        md_summary += f"""
---

## 3. Stratejik Tedarik Tavsiyeleri
1. **Sıfır Stok Aciliyeti:** Listede yer alan 0 stoklu donanımlar (özellikle T-Motor, SpeedyBee kuleleri ve LiPo bataryalar) organik aramalardan gelen müşterilerin dönüşüm kaybetmesine neden olmaktadır. Bu ürünlerin siparişi ivedilikle geçilmelidir.
2. **Rakip Açığı Avantajı:** Rakip firmalarda stokta bulunmayan ürünlerde Pozitron Market olarak stok açarak pazar payı hızla artırılabilir.
3. **Küresel Trend Entegrasyonu:** Trend avcısının tespit ettiği yeni donanımlar kataloğa 0 stokla eklenmiştir. Bu sipariş listesindeki adetlerle stoğa girdiğinde doğrudan satışa açılacaktır.
"""

        # Save to database
        now_iso = datetime.now().isoformat()
        projected_revenue = round(total_investment + total_profit, 2)
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO procurement_order_plans (
                id, title, status, total_items_count, total_units_count,
                estimated_investment_try, projected_revenue_try, projected_profit_try,
                projected_roi_pct, items_json, strategy_summary, created_at
            ) VALUES (?, ?, 'ACTIVE', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            plan_id, plan_title, len(selected_items), total_items_count,
            total_investment, projected_revenue, total_profit,
            roi_pct, json.dumps(selected_items, ensure_ascii=False), md_summary, now_iso
        ))
        conn.commit()
        conn.close()

        # Save to static JSON in data/
        plan_dict = {
            "id": plan_id,
            "plan_id": plan_id,
            "title": plan_title,
            "plan_title": plan_title,
            "total_skus": len(selected_items),
            "total_items_count": len(selected_items),
            "total_quantity": total_items_count,
            "total_units_count": total_items_count,
            "total_investment_try": total_investment,
            "estimated_investment_try": total_investment,
            "projected_revenue_try": projected_revenue,
            "total_profit_try": total_profit,
            "projected_profit_try": total_profit,
            "average_margin_pct": avg_margin,
            "roi_pct": roi_pct,
            "projected_roi_pct": roi_pct,
            "created_at": now_iso,
            "items": selected_items,
            "strategy_summary": md_summary
        }

        os.makedirs("data", exist_ok=True)
        with open("data/latest_procurement_plan.json", "w", encoding="utf-8") as f:
            json.dump(plan_dict, f, ensure_ascii=False, indent=2)

        # Generate CSV for supplier purchase order
        csv_path = "data/latest_procurement_order.csv"
        with open(csv_path, "w", encoding="utf-8-sig") as f:
            f.write("Oncelik,Urun Adi,Kategori,Mevcut Stok,Onerilen Adet,Birim Maliyet (TL),Satis Fiyati (TL),Kar Marji (%),Toplam Yatirim (TL),Beklenen Net Kar (TL),Hiz Skoru,Tedarik Nedeni\n")
            for it in selected_items:
                f.write(f'"{it["urgency"]}","{it["name"]}","{it["category"]}",{it["current_stock"]},{it["recommended_qty"]},{it["unit_cost_try"]},{it["unit_sale_price_try"]},{it["margin_pct"]},{it["total_investment_try"]},{it["total_projected_profit_try"]},{it["velocity_score"]},"{it["reason"]}"\n')

        return {
            "success": True,
            "id": plan_id,
            "plan_id": plan_id,
            "title": plan_title,
            "plan_title": plan_title,
            "total_skus": len(selected_items),
            "total_items_count": len(selected_items),
            "total_quantity": total_items_count,
            "total_units_count": total_items_count,
            "total_investment_try": total_investment,
            "estimated_investment_try": total_investment,
            "projected_revenue_try": projected_revenue,
            "total_profit_try": total_profit,
            "projected_profit_try": total_profit,
            "average_margin_pct": avg_margin,
            "roi_pct": roi_pct,
            "projected_roi_pct": roi_pct,
            "created_at": now_iso,
            "items": selected_items,
            "strategy_summary": md_summary,
            "recommendations_markdown": md_summary,
            "csv_file": csv_path
        }

    def get_latest_plan(self) -> Optional[Dict]:
        """Fetches the latest procurement plan from database or JSON."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM procurement_order_plans ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row:
            d = dict(row)
            try:
                d["items"] = json.loads(d["items_json"])
            except Exception:
                d["items"] = []
            return d

        # Fallback to JSON
        if os.path.exists("data/latest_procurement_plan.json"):
            try:
                with open("data/latest_procurement_plan.json", "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        return None
