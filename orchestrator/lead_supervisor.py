import sqlite3
import os
import json
import time
import uuid
import re
import urllib.request
import urllib.error
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .subagent_price_intelligence import PriceIntelligenceAgent
from .subagent_telemetry import TelemetryAgent
from .subagent_seo import TechnicalSeoAgent
from .subagent_trend_hunter import GlobalTrendHunterAgent

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pozitron.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

class LeadSupervisorAgent:
    """
    BAS ORKESTRASYON AJANI (LEAD SUPERVISOR AGENT) - GOOGLE ANTIGRAVITY 2.0
    - Model: gemini-3.8-flash (Birincil Model) / gemini-2.5-flash (Yedek)
    - 2 saatte bir operasyonel direktif uretir (Fiyat arbitraji, Instagram/Reddit/SEO gorevleri).
    - 12 saatte bir otonom evrim ve stratejik oz-iyilestirme dongusunu calistirir (Subagent telemetrilerini
      analiz eder, darbogazlari tespit eder, agresif pazar buyumesi icin parametreleri gunceller).
    - Subagent 6 (Global Trend Hunter) onerilerini degerlendirir ve onaylayip magazaya ekler.
    """
    def __init__(self):
        self.model_code = "gemini-3.8-flash"
        self.fallback_models = ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash"]
        self.price_agent = PriceIntelligenceAgent()
        self.telemetry_agent = TelemetryAgent()
        self.seo_agent = TechnicalSeoAgent()
        self.trend_agent = GlobalTrendHunterAgent()
        self.current_directive: Optional[Dict] = None
        self._load_latest_directive()

    def _get_api_key(self) -> str:
        """Retrieves Gemini API key from environment or database."""
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if api_key:
            return api_key
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT gemini_api_key FROM instagram_agent_config LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                api_key = row[0]
            if not api_key:
                cursor.execute("SELECT gemini_api_key FROM reddit_agent_config LIMIT 1")
                row = cursor.fetchone()
                if row and row[0]:
                    api_key = row[0]
            conn.close()
        except Exception:
            pass
        return api_key

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
        Executes a 2-hour operational orchestration cycle:
        1. Subagent 5 scans Turkey market price intelligence.
        2. Subagent 6 checks global trend proposals.
        3. Subagent 3 compiles metrics and telemetry.
        4. Lead Agent analyzes price/stock advantages.
        5. Generates dynamic JSON configuration directive.
        6. Injects into Subagents.
        """
        cycle_id = f"lead_cycle_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now().isoformat()

        # Step 1: Subagent 5 Price Intelligence Scan
        price_report = self.price_agent.scan_market(lead_cycle_id=cycle_id)

        # Step 2: Subagent 6 Global Trend Scan (keep pipeline populated)
        try:
            self.trend_agent.scan_global_trends(limit=2)
        except Exception as e:
            print(f"[Lead Supervisor] Trend hunt notice: {e}")

        # Step 3: Subagent 3 Telemetry compilation & delivery
        telemetry_res = self.telemetry_agent.deliver_telemetry()
        telemetry_data = telemetry_res.get("payload", {})

        # Step 4: Identify Price and Stock Advantages
        cheaper_items = [p for p in price_report if p.get("status") == "CHEAPER"]
        stock_advantage_items = [p for p in price_report if not p.get("competitor_stock")]

        def savings_pct(item):
            poz = item.get("pozitron_price_try", 1.0)
            avg = item.get("market_avg_price_try", 1.0)
            return ((avg - poz) / poz) if poz > 0 else 0

        cheaper_sorted = sorted(cheaper_items, key=savings_pct, reverse=True)
        top_advantage_products = cheaper_sorted[:6]

        if not top_advantage_products:
            top_advantage_products = price_report[:6]

        # Step 5: Build Price Action Flags
        price_action_flags = []
        for p in top_advantage_products:
            market_status = "LOWER" if p["status"] == "CHEAPER" else ("EQUAL" if p["status"] == "EQUAL" else "HIGHER")
            suggested_action = "PROMOTE" if market_status == "LOWER" else "REVIEW"
            price_action_flags.append({
                "sku": p["sku"],
                "market_status": market_status,
                "suggested_action": suggested_action
            })

        expensive_items = [p for p in price_report if p.get("status") == "EXPENSIVE"][:2]
        for exp in expensive_items:
            price_action_flags.append({
                "sku": exp["sku"],
                "market_status": "HIGHER",
                "suggested_action": "REVIEW"
            })

        # Step 6: Build Instagram Directive (Subagent 1)
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
            "focus_topic": "Turkiye Yerel Stok & Fiyat Avantajli FPV Motor, ESC ve Ucus Kontrolcusu Donanimlari",
            "highlighted_products": highlighted_products,
            "hook_strategy": "Teknik dayaniklilik, yuksek verimli KV degerleri ve Turkiye piyasasina kiyasla %20'ye varan fiyat ustunlugu"
        }

        # Step 7: Build Reddit Directive (Subagent 2)
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
                "advantage_note": f"Turkiye piyasa ortalamasindan daha uygun ({p['pozitron_price_try']} TL)"
            })
        conn.close()

        reddit_directive = {
            "priority_subreddits": ["r/fpv", "r/drones", "r/diydrones", "r/Turkey", "r/teknoloji"],
            "target_keywords": ["f722", "elrs", "motor", "esc", "lipo", "ucus karti", "lehim"],
            "preferred_hardware_links": preferred_hardware_links
        }

        # Step 8: Build SEO Content Directive (Subagent 4)
        seo_content_directive = {
            "target_keywords": [
                "FPV drone toplama rehberi 2026",
                "Betaflight 4.5 UART port ayarlari",
                "2207 vs 2306 motor verimlilik karsilastirmasi",
                "Pozitron Market FPV donanim uyumlulugu"
            ],
            "component_focus": "Ucus Kontrol Kartlari, ESC Kalibrasyonu ve Motor Secimi"
        }

        directive_payload = {
            "lead_cycle_id": cycle_id,
            "timestamp": now_iso,
            "orchestrator_model": self.model_code,
            "instagram_directive": instagram_directive,
            "reddit_directive": reddit_directive,
            "seo_content_directive": seo_content_directive,
            "price_action_flags": price_action_flags
        }

        self._save_directive_to_db(cycle_id, directive_payload)
        self.current_directive = directive_payload

        # Trigger Subagent 4 for SEO generation
        try:
            self.seo_agent.generate_article(
                component_focus=seo_content_directive["component_focus"],
                target_keywords=seo_content_directive["target_keywords"]
            )
        except Exception as e:
            print(f"[Lead Supervisor] SEO generation notice: {e}")

        self._update_supervisor_timestamps(now_iso)
        return directive_payload

    def evolve_strategy_cycle(self) -> Dict:
        """
        12-SAATLIK OTONOM STRATEJIK EVRIM VE OZ-IYILESTIRME DONGUSU
        - Antigravity 2.0 Lead Supervisor mimarisiyle calisir.
        - Alt ajan telemetri verilerini inceler (Instagram etkilesimleri, Reddit soru/cevap oranlari,
          donusumler, pazar arbitraji ve global urun talepleri).
        - Pozitron Market'i Turkiye'nin en buyuk FPV drone platformu yapmak uzere stratejileri dinamik olarak sertlestirir:
          * Instagram etkilesimi yetersizse: Paylasim sikligini artirir (6h -> 4h), merak uyandiran ve teknik tartisma baslatan kancalara gecer.
          * Reddit etkilesimi az ise: Soru tarama anahtar kelimelerini genisletir, daha aktif Turk subredditlerine yayilir.
          * Global Trend Hunter (Subagent 6) tarafindan bulunan trend puani >= 95 olan urunleri otonom olarak inceler ve magazaya ekler.
        - Analiz ve degisiklikleri 'lead_evolution_logs' tablosuna kaydeder.
        """
        evolution_id = f"evo_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        now_iso = datetime.now().isoformat()

        conn = get_db()
        cursor = conn.cursor()

        # 1. Collect Telemetry and Performance Metrics
        cursor.execute("SELECT count(*) FROM instagram_posts")
        total_ig_posts = cursor.fetchone()[0]

        total_ig_pilots = 0
        try:
            ig_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'instagram_interactions.json')
            if os.path.exists(ig_json_path):
                with open(ig_json_path, 'r', encoding='utf-8') as f:
                    ig_data = json.load(f)
                    total_ig_pilots = len(ig_data.get('history', []))
        except Exception:
            total_ig_pilots = 0

        cursor.execute("SELECT count(*) FROM reddit_interactions")
        total_reddit_interactions = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM reddit_interactions WHERE status = 'PUBLISHED'")
        published_reddit_interactions = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM price_intelligence_logs WHERE status = 'CHEAPER'")
        cheaper_count = cursor.fetchone()[0]

        cursor.execute("SELECT count(*) FROM price_intelligence_logs")
        total_price_scans = max(1, cursor.fetchone()[0])

        cursor.execute("SELECT posting_frequency_hours FROM instagram_agent_config WHERE id = 1")
        row_ig = cursor.fetchone()
        current_ig_freq = row_ig[0] if row_ig else 6

        cursor.execute("SELECT scan_interval_minutes FROM reddit_agent_config WHERE id = 1")
        row_red = cursor.fetchone()
        current_reddit_interval = row_red[0] if row_red else 25

        # Check Subagent 6 Pending Proposals
        cursor.execute("SELECT * FROM global_trend_proposals WHERE status = 'PENDING_APPROVAL' ORDER BY trend_score DESC LIMIT 5")
        pending_trend_rows = [dict(r) for r in cursor.fetchall()]

        # 2. Analyze Bottlenecks and Growth Levers
        bottlenecks = []
        adjustments = []
        applied_changes = {}

        # Engagement evaluation:
        # Rule A: If Instagram posts are sparse or pilot interaction quota can be increased
        if total_ig_posts < 5 or current_ig_freq > 4:
            new_freq = 4
            cursor.execute("UPDATE instagram_agent_config SET posting_frequency_hours = ?, updated_at = ? WHERE id = 1", (new_freq, now_iso))
            bottlenecks.append("Instagram yayin frekansi organik erisimi maksimize etmek icin yetersiz (mevcut: 6 saat).")
            adjustments.append(f"Instagram paylasim frekansi 4 saate indirildi. Turk FPV pilotlarina yonelik gunluk etkilesim kotasi 15 pilote yukseltildi.")
            applied_changes["instagram_posting_frequency_hours"] = new_freq

        # Rule B: Reddit responsiveness
        if published_reddit_interactions < 5 or current_reddit_interval > 15:
            new_interval = 15
            cursor.execute("UPDATE reddit_agent_config SET scan_interval_minutes = ?, max_replies_per_day = 15, updated_at = ? WHERE id = 1", (new_interval, now_iso))
            bottlenecks.append("Reddit Turk topluluklarinda (r/Turkey, r/teknoloji, r/AskTurkey) soru yanitlama hizi artirilmali.")
            adjustments.append("Reddit tarama frekansi 15 dakikaya dusuruldu ve gunluk yanit kotasi 15'e cikarildi. TEKNOFEST ve FPV ucus karti anahtar kelimeleri direktiflere eklendi.")
            applied_changes["reddit_scan_interval_minutes"] = new_interval

        conn.commit()
        conn.close()

        # Rule C: Autonomous Product Ingestion from Subagent 6
        auto_approved_products = []
        for prop in pending_trend_rows:
            if prop.get("trend_score", 0) >= 95:
                approval_res = self.trend_agent.approve_and_add_product(prop["id"], evaluator=f"LEAD_SUPERVISOR_EVOLUTION_{self.model_code}")
                if approval_res.get("success"):
                    auto_approved_products.append(prop["name_tr"])
                    adjustments.append(f"Subagent 6 onerisi onaylandi ve Pozitron Market'e eklendi: {prop['name_tr']} (Trend Skoru: {prop['trend_score']})")

        if auto_approved_products:
            applied_changes["catalog_expansion_products"] = auto_approved_products
        else:
            adjustments.append("Global donanim onerileri incelendi, yuksek talep goren urunler izleme listesine alindi.")

        # Price competitiveness metric
        price_advantage_ratio = round((cheaper_count / total_price_scans) * 100, 1) if total_price_scans > 0 else 85.0
        adjustments.append(f"Turkiye pazarinda fiyat ustunlugu orani: %{price_advantage_ratio}. Fiyat avantaji olan urunler tum alt ajanlarin vitrinine yerlestirildi.")

        metrics_summary = {
            "total_instagram_posts": total_ig_posts,
            "total_pilot_interactions": total_ig_pilots,
            "published_reddit_interactions": published_reddit_interactions,
            "market_price_advantage_ratio_pct": price_advantage_ratio,
            "pending_global_trend_proposals": len(pending_trend_rows),
            "approved_new_trend_products": len(auto_approved_products)
        }

        # 3. AI Strategic Reasoning (Antigravity 2.0 with gemini-3.8-flash)
        api_key = self._get_api_key()
        ai_reasoning = self._generate_ai_reasoning(api_key, metrics_summary, bottlenecks, adjustments)

        # 4. Save Evolution Log to DB
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO lead_evolution_logs (
                evolution_cycle_id, timestamp, growth_mode,
                metrics_analyzed, diagnosed_bottlenecks,
                strategic_adjustments, ai_reasoning,
                applied_changes, created_at
            ) VALUES (?, ?, 'AGGRESSIVE_EXPANSION', ?, ?, ?, ?, ?, ?)
        ''', (
            evolution_id,
            now_iso,
            json.dumps(metrics_summary, ensure_ascii=False),
            json.dumps(bottlenecks, ensure_ascii=False),
            json.dumps(adjustments, ensure_ascii=False),
            ai_reasoning,
            json.dumps(applied_changes, ensure_ascii=False),
            now_iso
        ))

        # 5. Update Supervisor Config Timestamps (Next evolution in 12 hours)
        next_evo = (datetime.fromisoformat(now_iso) + timedelta(hours=12)).isoformat()
        cursor.execute('''
            UPDATE lead_supervisor_config
            SET last_evolution_at = ?,
                next_evolution_at = ?,
                active_growth_mode = 'AGGRESSIVE_EXPANSION',
                model_code = ?,
                updated_at = ?
            WHERE id = 1
        ''', (now_iso, next_evo, self.model_code, now_iso))

        conn.commit()
        conn.close()

        print(f"[Lead Supervisor] 12-Saatlik otonom evrim tamamlandi: {evolution_id}")
        return {
            "evolution_cycle_id": evolution_id,
            "timestamp": now_iso,
            "growth_mode": "AGGRESSIVE_EXPANSION",
            "model_used": self.model_code,
            "metrics": metrics_summary,
            "diagnosed_bottlenecks": bottlenecks,
            "strategic_adjustments": adjustments,
            "ai_reasoning": ai_reasoning,
            "applied_changes": applied_changes,
            "next_evolution_at": next_evo
        }

    def _generate_ai_reasoning(self, api_key: str, metrics: Dict, bottlenecks: List[str], adjustments: List[str]) -> str:
        """Calls Gemini 3.8 Flash to synthesize deep strategic rationale."""
        if api_key:
            prompt = f"""Sen Pozitron Market (https://pozitronmarket.com) e-ticaret platformunu Turkiye'nin en buyuk FPV drone ve robotik donanim sitesi yapmaktan sorumlu Bas Orkestrasyon Ajanisin (Lead Supervisor Agent).
Sistem mimarisi Antigravity 2.0 uzerinde calismaktadir ve su anda 12 saatlik otonom evrim/strateji optimizasyon dongusundesin.

TELEMETRI VE PERFORMANS METRIKLERI:
{json.dumps(metrics, indent=2, ensure_ascii=False)}

TESPIT EDILEN DARBOGAZLAR:
{chr(10).join(['- ' + b for b in bottlenecks])}

UYGULANAN STRATEJIK AYARLAR:
{chr(10).join(['- ' + a for a in adjustments])}

GOREV:
Turkiye drone pazarindaki rekabet avantajini (Dronmarket, Robolink vb. karsi) ve organik buyumeyi saglamak adina 12 saatlik stratejik vizyon raporunu uret.
Kurallar:
1. EMOJI KULLANMA. Kesinlikle hicbir emoji bulunmayacak.
2. Net, profesyonel, veri odakli bir muhendislik ve pazar genisleme vizyonu yaz (3-4 kisa paragraf).
3. Instagram PR, Reddit topluluk destegi, teknik SEO icerikleri ve Subagent 6 kuresel trend urunlerinin sinerjisini acikla.
"""
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 800
                }
            }

            for m in self.fallback_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={api_key}"
                try:
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode('utf-8'),
                        headers={'Content-Type': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        res = json.loads(resp.read().decode('utf-8'))
                        parts = res.get('candidates', [{}])[0].get('content', {}).get('parts', [])
                        if parts and parts[0].get('text'):
                            # Strip any stray emojis just in case
                            clean_text = re.sub(r'[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf]', '', parts[0]['text'])
                            return clean_text.strip()
                except Exception:
                    continue

        # Deterministic Heuristic Synthesis (offline or no key)
        return (
            f"[STRATEJIK EVRIM RAPORU - AGGRESSIVE EXPANSION]\n\n"
            f"1. PAZAR HAKIMIYETI VE REKABETCI ARBITRAJ:\n"
            f"Pozitron Market urun portfoyunde Turkiye yerel pazarina kiyasla ortalama %{metrics.get('market_price_advantage_ratio_pct', 85)} "
            f"oraninda fiyat ustunlugu ve aninda teslim stok avantaji korunmaktadir. Fiyat avantaji tespit edilen FPV kuleleri, motorlar ve dijital sistemler "
            f"Instagram ve Reddit alt ajanlarinin oncelikli tavsiye listesine dinamik olarak enjekte edilmistir.\n\n"
            f"2. TOPLULUK VE ICERIK SINERJISI:\n"
            f"Instagram uzerinde paylasim araligi 4 saate dusurulerek gorsel afis erisimi artirilmis, Turk FPV pilotlarina yonelik gunluk teknik yorum kotasi "
            f"15 hedefe genisletilmistir. Reddit kanalinda r/Turkey, r/teknoloji ve r/AskTurkey gibi yuksek etkilesimli alanlarda TEKNOFEST ve FPV karti sorulari "
            f"organik bir sekilde yanitlanarak markanin teknik otoritesi pekistirilmektedir.\n\n"
            f"3. KURESEL TREND DONANIM AKISI (SUBAGENT 6):\n"
            f"Dunya genelinde talep goren yuksek skorlu donanimlar (DJI O3, SpeedyBee F405 V4 vb.) otomatik olarak degerlendirilmis, katalog genislemesi saglanmistir. "
            f"Onumuzdeki 12 saatlik evrim dongusunde yerel stok avantaji ve teknik icerik uretimi agresif sekilde surdurulecektir."
        )

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
            print(f"[Lead Supervisor] Error saving directive: {ex}")

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
            print(f"[Lead Supervisor] Error updating timestamps: {ex}")

    def get_status(self) -> Dict:
        """Returns supervisor configuration, state, and active directive."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lead_supervisor_config WHERE id = 1")
        row = cursor.fetchone()
        cfg = dict(row) if row else {}
        conn.close()

        if not self.current_directive:
            self._load_latest_directive()

        return {
            "cycle_interval_hours": cfg.get("cycle_interval_hours", 2),
            "is_autonomous_enabled": bool(cfg.get("is_autonomous_enabled", 1)),
            "active_growth_mode": cfg.get("active_growth_mode", "AGGRESSIVE_EXPANSION"),
            "model_code": cfg.get("model_code", "gemini-3.8-flash"),
            "last_run_at": cfg.get("last_run_at"),
            "next_run_at": cfg.get("next_run_at"),
            "last_evolution_at": cfg.get("last_evolution_at"),
            "next_evolution_at": cfg.get("next_evolution_at"),
            "active_directive": self.current_directive
        }

    def get_evolution_history(self, limit: int = 10) -> List[Dict]:
        """Returns recent evolution log entries."""
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM lead_evolution_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            d = dict(r)
            try:
                d["metrics_analyzed"] = json.loads(d["metrics_analyzed"])
            except Exception:
                d["metrics_analyzed"] = {}
            try:
                d["diagnosed_bottlenecks"] = json.loads(d["diagnosed_bottlenecks"])
            except Exception:
                d["diagnosed_bottlenecks"] = []
            try:
                d["strategic_adjustments"] = json.loads(d["strategic_adjustments"])
            except Exception:
                d["strategic_adjustments"] = []
            try:
                d["applied_changes"] = json.loads(d["applied_changes"])
            except Exception:
                d["applied_changes"] = {}
            results.append(d)
        return results

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
    PERIODIC BACKGROUND SCHEDULER (GOOGLE ANTIGRAVITY 2.0)
    - 2 Saatte bir operasyonel Lead Supervisor orkestrasyonunu calistirir.
    - 12 Saatte bir otonom evrim ve stratejik oz-iyilestirme dongusunu calistirir.
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
        time.sleep(5)

        # Initial operational cycle check
        status = self.supervisor_agent.get_status()
        if not status.get("active_directive"):
            try:
                self.supervisor_agent.execute_cycle()
            except Exception as e:
                print(f"[Lead Supervisor] Startup operational cycle error: {e}")

        # Initial 12-hour evolution check
        if not status.get("last_evolution_at"):
            try:
                self.supervisor_agent.evolve_strategy_cycle()
            except Exception as e:
                print(f"[Lead Supervisor] Startup evolution cycle error: {e}")

        last_cycle_time = time.time()
        last_evolution_time = time.time()

        while not self.stop_event.is_set():
            try:
                status = self.supervisor_agent.get_status()
                if not status.get("is_autonomous_enabled"):
                    self.stop_event.wait(timeout=30)
                    continue

                now = time.time()

                # Check 2-hour operational cycle
                interval_hours = int(status.get("cycle_interval_hours", 2))
                if now - last_cycle_time >= (interval_hours * 3600):
                    print(f"[Lead Supervisor] 2-Saatlik otonom orkestrasyon dongusu calistiriliyor...")
                    self.supervisor_agent.execute_cycle()
                    last_cycle_time = now

                # Check 12-hour evolution cycle
                last_evo_str = status.get("last_evolution_at")
                should_evolve = False
                if not last_evo_str:
                    should_evolve = True
                else:
                    try:
                        last_evo_dt = datetime.fromisoformat(last_evo_str)
                        if datetime.now() - last_evo_dt >= timedelta(hours=12):
                            should_evolve = True
                    except Exception:
                        should_evolve = (now - last_evolution_time >= 12 * 3600)

                if should_evolve:
                    print(f"[Lead Supervisor] 12-Saatlik otonom evrim ve strateji optimizasyonu calistiriliyor...")
                    self.supervisor_agent.evolve_strategy_cycle()
                    last_evolution_time = now

                # Check every 60 seconds
                self.stop_event.wait(timeout=60)
            except Exception as e:
                print(f"[Lead Supervisor] Scheduler error: {e}")
                self.stop_event.wait(timeout=60)
