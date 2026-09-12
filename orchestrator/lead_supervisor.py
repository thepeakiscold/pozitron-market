import sqlite3
import os
import json
import time
import uuid
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .subagent_price_intelligence import PriceIntelligenceAgent
from .subagent_telemetry import TelemetryAgent
from .subagent_seo import TechnicalSeoAgent

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pozitron.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

class LeadSupervisorAgent:
    """
    BAŞ ORKESTRASYON AJANI (LEAD SUPERVISOR AGENT)
    - Antigravity 2.0 otomasyonu ve 2 saatlik zamanlayıcı ile çalışır.
    - Subagent 3 (Telemetri) ve Subagent 5 (Fiyat/Arbitraj) girdilerini harmanlar.
    - Fiyat avantajı ve stok üstünlüğü olan donanımları tespit eder.
    - Subagent 1 (Instagram), Subagent 2 (Reddit) ve Subagent 4 (SEO) için dinamik direktif üretir.
    """
    def __init__(self):
        self.price_agent = PriceIntelligenceAgent()
        self.telemetry_agent = TelemetryAgent()
        self.seo_agent = TechnicalSeoAgent()
        self.current_directive: Optional[Dict] = None
        self._load_latest_directive()

    def _load_latest_directive(self):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT directive_json FROM lead_supervisor_directives ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row and row['directive_json']:
                self.current_directive = json.loads(row['directive_json'])
        except Exception:
            self.current_directive = None

    def execute_cycle(self) -> Dict:
        """
        Executes a full 2-hour orchestration cycle:
        1. Subagent 5 scans Turkey market price intelligence.
        2. Subagent 3 compiles metrics and posts to http://localhost:8000/bots.
        3. Lead Agent analyzes price/stock advantages.
        4. Lead Agent generates dynamic JSON configuration directive.
        5. Saves directive and injects into Subagents.
        """
        cycle_id = f"lead_cycle_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now().isoformat()

        # Step 1: Subagent 5 Price Intelligence Scan
        price_report = self.price_agent.scan_market(lead_cycle_id=cycle_id)

        # Step 2: Subagent 3 Telemetry compilation & delivery
        telemetry_res = self.telemetry_agent.deliver_telemetry()
        telemetry_data = telemetry_res.get("payload", {})

        # Step 3: Identify Price and Stock Advantages
        cheaper_items = [p for p in price_report if p.get("status") == "CHEAPER"]
        stock_advantage_items = [p for p in price_report if not p.get("competitor_stock")]

        # Sort products by highest price savings percentage
        def savings_pct(item):
            poz = item.get("pozitron_price_try", 1.0)
            avg = item.get("market_avg_price_try", 1.0)
            return ((avg - poz) / poz) if poz > 0 else 0

        cheaper_sorted = sorted(cheaper_items, key=savings_pct, reverse=True)
        top_advantage_products = cheaper_sorted[:6]

        if not top_advantage_products:
            top_advantage_products = price_report[:6]

        # Step 4: Build Price Action Flags
        price_action_flags = []
        for p in top_advantage_products:
            market_status = "LOWER" if p["status"] == "CHEAPER" else ("EQUAL" if p["status"] == "EQUAL" else "HIGHER")
            suggested_action = "PROMOTE" if market_status == "LOWER" else "REVIEW"
            price_action_flags.append({
                "sku": p["sku"],
                "market_status": market_status,
                "suggested_action": suggested_action
            })

        # Append any items that are EXPENSIVE for price review
        expensive_items = [p for p in price_report if p.get("status") == "EXPENSIVE"][:2]
        for exp in expensive_items:
            price_action_flags.append({
                "sku": exp["sku"],
                "market_status": "HIGHER",
                "suggested_action": "REVIEW"
            })

        # Step 5: Build Instagram Directive (Subagent 1)
        highlighted_products = []
        for p in top_advantage_products[:4]:
            highlighted_products.append({
                "sku": p["sku"],
                "name": p["product_name"],
                "price_try": p["pozitron_price_try"],
                "market_min_price_try": p["market_min_price_try"],
                "advantage": "PRICE_ADVANTAGE" if p["status"] == "CHEAPER" else "STOCK_ADVANTAGE"
            })

        instagram_directive = {
            "focus_topic": "Türkiye Yerel Stok & Fiyat Avantajlı FPV Motor, ESC ve Uçuş Kontrolcüsü Donanımları",
            "highlighted_products": highlighted_products,
            "hook_strategy": "Teknik dayanıklılık, yüksek verimli KV değerleri ve Türkiye piyasasına kıyasla %20'ye varan fiyat üstünlüğü"
        }

        # Step 6: Build Reddit Directive (Subagent 2)
        preferred_hardware_links = []
        conn = get_db()
        cursor = conn.cursor()
        for p in top_advantage_products[:3]:
            cursor.execute("SELECT slug FROM products WHERE sku = ?", (p["sku"],))
            s_row = cursor.fetchone()
            slug = s_row["slug"] if s_row else p["sku"].lower()
            preferred_hardware_links.append({
                "sku": p["sku"],
                "name": p["product_name"],
                "url": f"https://pozitronmarket.com/products/{slug}",
                "advantage_note": f"Türkiye piyasa ortalamasından daha uygun ({p['pozitron_price_try']} ₺)"
            })
        conn.close()

        reddit_directive = {
            "priority_subreddits": ["r/fpv", "r/drones", "r/diydrones", "r/Turkey", "r/teknoloji"],
            "target_keywords": ["f722", "elrs", "motor", "esc", "lipo", "uçuş kartı", "lehim"],
            "preferred_hardware_links": preferred_hardware_links
        }

        # Step 7: Build SEO Content Directive (Subagent 4)
        seo_content_directive = {
            "target_keywords": [
                "FPV drone toplama rehberi 2026",
                "Betaflight 4.5 UART port ayarları",
                "2207 vs 2306 motor verimlilik karşılaştırması",
                "Pozitron Market FPV donanım uyumluluğu"
            ],
            "component_focus": "Uçuş Kontrol Kartları, ESC Kalibrasyonu ve Motor Seçimi"
        }

        # Synthesize Full JSON Directive (Strictly following user schema)
        directive_payload = {
            "lead_cycle_id": cycle_id,
            "timestamp": now_iso,
            "instagram_directive": instagram_directive,
            "reddit_directive": reddit_directive,
            "seo_content_directive": seo_content_directive,
            "price_action_flags": price_action_flags
        }

        # Persist Directive in Database
        self._save_directive_to_db(cycle_id, directive_payload)
        self.current_directive = directive_payload

        # Trigger Subagent 4 to generate an SEO guide if needed
        try:
            self.seo_agent.generate_article(
                component_focus=seo_content_directive["component_focus"],
                target_keywords=seo_content_directive["target_keywords"]
            )
        except Exception as e:
            print(f"SEO article generation notice: {e}")

        # Update Supervisor Config timestamps
        self._update_supervisor_timestamps(now_iso)

        return directive_payload

    def _save_directive_to_db(self, cycle_id: str, directive: Dict):
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO lead_supervisor_directives (lead_cycle_id, directive_json, created_at)
                VALUES (?, ?, ?)
            """, (cycle_id, json.dumps(directive, ensure_ascii=False), datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"Error saving directive: {ex}")

    def _update_supervisor_timestamps(self, last_run_iso: str):
        try:
            next_run = (datetime.fromisoformat(last_run_iso) + timedelta(hours=2)).isoformat()
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE lead_supervisor_config
                SET last_run_at = ?, next_run_at = ?, updated_at = ?
                WHERE id = 1
            """, (last_run_iso, next_run, datetime.now().isoformat()))
            conn.commit()
            conn.close()
        except Exception as ex:
            print(f"Error updating supervisor timestamps: {ex}")

    def get_status(self) -> Dict:
        """Returns supervisor configuration, state and active directive."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lead_supervisor_config WHERE id = 1")
        cfg = dict(cursor.fetchone() or {})
        conn.close()

        if not self.current_directive:
            self._load_latest_directive()

        return {
            "cycle_interval_hours": cfg.get("cycle_interval_hours", 2),
            "is_autonomous_enabled": bool(cfg.get("is_autonomous_enabled", 1)),
            "last_run_at": cfg.get("last_run_at"),
            "next_run_at": cfg.get("next_run_at"),
            "active_directive": self.current_directive
        }

    def get_directives_history(self, limit: int = 10) -> List[Dict]:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lead_supervisor_directives ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        results = []
        for r in rows:
            try:
                results.append({
                    "id": r["id"],
                    "lead_cycle_id": r["lead_cycle_id"],
                    "directive": json.loads(r["directive_json"]),
                    "created_at": r["created_at"]
                })
            except Exception:
                pass
        return results


class SupervisorScheduler:
    """
    2-HOUR PERIODIC BACKGROUND SCHEDULER
    Orchestrates the Lead Supervisor Agent every 2 hours continuously.
    """
    def __init__(self, supervisor_agent: LeadSupervisorAgent):
        self.supervisor_agent = supervisor_agent
        self.stop_event = threading.Event()
        self.thread: Optional[threading.Thread] = None
        self._is_running = False

    def is_running(self) -> bool:
        return self._is_running and self.thread is not None and self.thread.is_alive()

    def start(self):
        if self.is_running():
            return
        self.stop_event.clear()
        self._is_running = True
        self.thread = threading.Thread(target=self._loop, name="LeadSupervisorSchedulerThread", daemon=True)
        self.thread.start()

    def stop(self):
        self._is_running = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.thread = None

    def _loop(self):
        # Short initial delay on server launch
        time.sleep(5)

        # Run an initial cycle on startup if not run recently
        status = self.supervisor_agent.get_status()
        if not status.get("active_directive"):
            try:
                self.supervisor_agent.execute_cycle()
            except Exception as e:
                print(f"[Lead Supervisor] Startup cycle error: {e}")

        while not self.stop_event.is_set():
            try:
                status = self.supervisor_agent.get_status()
                if not status.get("is_autonomous_enabled"):
                    self.stop_event.wait(timeout=30)
                    continue

                interval_hours = int(status.get("cycle_interval_hours", 2))
                interval_seconds = interval_hours * 3600

                # Run cycle
                print(f"[Lead Supervisor] 2-Saatlik otonom orkestrasyon döngüsü çalıştırılıyor...")
                self.supervisor_agent.execute_cycle()

                # Sleep until next cycle or stop requested
                self.stop_event.wait(timeout=interval_seconds)
            except Exception as e:
                print(f"[Lead Supervisor] Scheduler error: {e}")
                self.stop_event.wait(timeout=60)
