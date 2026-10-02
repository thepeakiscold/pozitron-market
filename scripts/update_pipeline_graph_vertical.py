#!/usr/bin/env python3
import sys

new_graph_code = '''            sec_audit = cyber_security_agent.get_latest_audit() or {}
            media_audit = media_inspector_agent.get_latest_audit() or {}
            sec_enabled = is_subagent_enabled("subagent_9_security")
            media_enabled = is_subagent_enabled("subagent_10_media")

            graph = {
                "version": "4.0",
                "engine": "Antigravity 2.0 Vertical Subgroup Architecture",
                "layout": "vertical",
                "last_cycle_at": sup_status.get("last_run_at"),
                "next_cycle_at": sup_status.get("next_run_at"),
                "subgroups": [
                    {
                        "id": "grp_triggers",
                        "name": "1. GİRİŞ & DIŞ TETİKLEYİCİLER",
                        "badge": "3 Tetikleyici",
                        "desc": "Müşteri Trafiği, Sistem Cron & GitHub Actions CI/CD Tetikleyicileri",
                        "accent": "#10b981",
                        "node_ids": ["client_customer", "trigger_cron_2h", "trigger_github_dispatch"]
                    },
                    {
                        "id": "grp_infrastructure",
                        "name": "2. BULUT & SUNUCU ALTYAPISI",
                        "badge": "4 Sunucu & Veri",
                        "desc": "GitHub Pages CDN, Hetzner VPS (Ubuntu 24.04), Nginx SSL Proxy & SQLite Veritabanı",
                        "accent": "#0284c7",
                        "node_ids": ["srv_github_platform", "srv_hetzner_cloud", "srv_nginx_proxy", "db_sqlite"]
                    },
                    {
                        "id": "grp_security_services",
                        "name": "3. SİBER GÜVENLİK & DIŞ SERVİSLER",
                        "badge": "4 Güvenlik & Servis",
                        "desc": "Siber Güvenlik Sentineli, PayTR Sanal POS, Google Gemini 3.8 Flash AI & Gmail SMTP",
                        "accent": "#f59e0b",
                        "node_ids": ["subagent_9_security", "svc_paytr", "svc_gemini_ai", "svc_smtp_mail"]
                    },
                    {
                        "id": "grp_orchestration_quality",
                        "name": "4. MERKEZİ İSTİHBARAT & KALİTE GÜVENCESİ",
                        "badge": "4 Yönetim & Kalite",
                        "desc": "Lead Supervisor, QA Sentinel, Ürün Medya & İçerik Denetleyicisi, Telemetri Toplayıcı",
                        "accent": "#0ea5e9",
                        "node_ids": ["lead_supervisor", "subagent_7_qa", "subagent_10_media", "subagent_3_telemetry"]
                    },
                    {
                        "id": "grp_commerce_supply",
                        "name": "5. TİCARET, TEDARİK & FİYATLANDIRMA",
                        "badge": "3 Ticari Ajan",
                        "desc": "Sipariş & Tedarik Optimizasyonu, Dinamik Fiyatlandırma & Küresel Trend Avcısı",
                        "accent": "#8b5cf6",
                        "node_ids": ["subagent_8_procurement", "subagent_5_price", "subagent_6_trend"]
                    },
                    {
                        "id": "grp_marketing_distribution",
                        "name": "6. PAZARLAMA & DIŞ DAĞITIM KANALLARI",
                        "badge": "4 Yayın Kanalı",
                        "desc": "Instagram PR & Reels, SEO Dokümantasyon, Reddit Asistanı & Google Merchant Center",
                        "accent": "#f43f5e",
                        "node_ids": ["subagent_1_instagram", "subagent_4_seo", "subagent_2_reddit", "svc_google_merchant"]
                    }
                ],
                "nodes": [
                    # KATMAN 1: GİRİŞ & DIŞ TETİKLEYİCİLER
                    {
                        "id": "client_customer",
                        "label": "Müşteri & Ziyaretçi",
                        "tag": "[CLIENT]",
                        "subgroup": "grp_triggers",
                        "layer": 1,
                        "type": "client",
                        "category": "Son Kullanıcı / Tarayıcı",
                        "status": "active",
                        "status_text": "Web Gezinme & Alışveriş",
                        "description": "FPV pilotları ve müşteriler: Ürün inceler, sepete ekler, 3D Secure ödeme yapar ve ürün yorumu bırakır",
                        "payload_preview": {
                            "traffic_channel": "Direct, Organic Search, Instagram PR",
                            "actions": ["Product Browsing", "Cart Checkout", "Review Submission"],
                            "target_domain": "https://pozitronmarket.com"
                        }
                    },
                    {
                        "id": "trigger_cron_2h",
                        "label": "2 Saatlik Zamanlayıcı",
                        "tag": "[TRIGGER]",
                        "subgroup": "grp_triggers",
                        "layer": 1,
                        "type": "trigger",
                        "category": "Zamanlayıcı (Cron)",
                        "status": "active",
                        "status_text": "Aktif (Tetikliyor)",
                        "description": "Antigravity 2.0 periyodik cron tetikleyicisi: 2 saatte bir pazar istihbaratı ve orkestrasyonu tetikler",
                        "payload_preview": {
                            "trigger_type": "PERIODIC_CRON",
                            "interval_hours": 2,
                            "last_tick": sup_status.get("last_run_at"),
                            "next_tick": sup_status.get("next_run_at")
                        }
                    },
                    {
                        "id": "trigger_github_dispatch",
                        "label": "GitHub Webhook (Envanter)",
                        "tag": "[WEBHOOK]",
                        "subgroup": "grp_triggers",
                        "layer": 1,
                        "type": "trigger",
                        "category": "Sipariş / Envanter Olayı",
                        "status": "ready",
                        "status_text": "repository_dispatch",
                        "description": "Sipariş verildiğinde anlık stok düşümü ve Git senkronizasyonu için GitHub Actions tetikleyicisi",
                        "payload_preview": {
                            "event_type": "market_order",
                            "workflow": ".github/workflows/market_order_sync.yml",
                            "action": "scripts/cloud_market_sync.py"
                        }
                    },

                    # KATMAN 2: BULUT & SUNUCU ALTYAPISI
                    {
                        "id": "srv_github_platform",
                        "label": "GitHub Server & CDN",
                        "tag": "[GITHUB]",
                        "subgroup": "grp_infrastructure",
                        "layer": 2,
                        "type": "server",
                        "category": "Statik CDN & CI/CD",
                        "status": "connected",
                        "status_text": "Pages CDN & Actions",
                        "description": "pozitronmarket.com statik sayfalarını barındırır (GitHub Pages Edge CDN) ve Actions CI/CD dağıtımını yürütür",
                        "payload_preview": {
                            "server_role": "Static Site Hosting & CI/CD Engine",
                            "domain": "https://pozitronmarket.com",
                            "provider": "GitHub, Inc.",
                            "repository": "thepeakiscold/pozitron-market",
                            "edge_ssl": "Let's Encrypt / GitHub TLS Certificate"
                        }
                    },
                    {
                        "id": "srv_hetzner_cloud",
                        "label": "Hetzner Cloud VPS",
                        "tag": "[HETZNER]",
                        "subgroup": "grp_infrastructure",
                        "layer": 2,
                        "type": "server",
                        "category": "Merkezi Bulut & API",
                        "status": "connected",
                        "status_text": "Ubuntu 24.04 • Nginx SSL",
                        "description": "api.pozitronmarket.com ana sunucusu: Systemd servisi, ters proxy, ACID veritabanı ve otonom arka plan işçilerini çalıştırır",
                        "payload_preview": {
                            "server_role": "Backend API Server, DB & Autonomous Orchestrator",
                            "api_domain": "https://api.pozitronmarket.com",
                            "datacenter": "Hetzner Cloud (Falkenstein/Nuremberg)",
                            "os": "Ubuntu 24.04 LTS",
                            "port": 8000,
                            "proxy_port": 443
                        }
                    },
                    {
                        "id": "srv_nginx_proxy",
                        "label": "Nginx SSL Ters Proxy",
                        "tag": "[PROXY]",
                        "subgroup": "grp_infrastructure",
                        "layer": 2,
                        "type": "server",
                        "category": "Ağ & Güvenlik Ağ Geçidi",
                        "status": "active",
                        "status_text": "Port 443 • Let's Encrypt",
                        "description": "HTTPS trafiğini karşılar, SSL/TLS sonlandırır ve yerel port 8000 Systemd Python servisine ters proxy yapar",
                        "payload_preview": {
                            "service": "nginx/1.24.0 (Ubuntu)",
                            "ssl_cert": "Let's Encrypt Authority X3",
                            "upstream": "http://127.0.0.1:8000"
                        }
                    },
                    {
                        "id": "db_sqlite",
                        "label": "SQLite ACID Veritabanı",
                        "tag": "[DATABASE]",
                        "subgroup": "grp_infrastructure",
                        "layer": 2,
                        "type": "server",
                        "category": "Kalıcı Veri Deposu",
                        "status": "active",
                        "status_text": "pozitron.db • 508 Ürün",
                        "description": "Ürünler, stoklar, siparişler, müşteri yorumları, SEO makaleleri ve güvenlik günlüklerini ACID garantisiyle saklar",
                        "payload_preview": {
                            "file": "pozitron.db",
                            "products_count": 508,
                            "wal_mode": "WAL Enabled",
                            "integrity": "OK"
                        }
                    },

                    # KATMAN 3: SİBER GÜVENLİK & DIŞ SERVİSLER
                    {
                        "id": "subagent_9_security",
                        "label": "Subagent 9: Siber Güvenlik",
                        "tag": "[SECURITY]",
                        "subgroup": "grp_security_services",
                        "layer": 3,
                        "type": "security",
                        "category": "WAF & Savunma Sentineli",
                        "status": "active" if sec_enabled else "disabled",
                        "status_text": f"Skor: %{sec_audit.get('score', 100)} • {sec_audit.get('status', 'SECURE')}",
                        "description": "WAF, rate limit, brute-force koruması, SQLi/XSS filtre denetimi, PayTR HMAC-SHA256 ve SSL süre takibi",
                        "payload_preview": {
                            "security_score": sec_audit.get('score', 100),
                            "probes_passed": sec_audit.get('probes_passed', 6),
                            "findings_count": sec_audit.get('findings_count', 0),
                            "status": sec_audit.get('status', 'SECURE')
                        }
                    },
                    {
                        "id": "svc_paytr",
                        "label": "PayTR Sanal POS (Ödeme)",
                        "tag": "[PAYMENT]",
                        "subgroup": "grp_security_services",
                        "layer": 3,
                        "type": "payment",
                        "category": "Ödeme Ağ Geçidi",
                        "status": "connected",
                        "status_text": "3D Secure • Token & Webhook",
                        "description": "Kredi/banka kartı ile güvenli 3D Secure ödeme alımı, iframe token üretimi ve anlık webhook onayı sağlar",
                        "payload_preview": {
                            "provider": "PayTR Ödeme ve Elektronik Para Kuruluşu A.Ş.",
                            "integration": "Direct 3D Secure Webhook",
                            "currency": "TL (Türk Lirası)"
                        }
                    },
                    {
                        "id": "svc_gemini_ai",
                        "label": "Google Gemini 3.8 Flash AI",
                        "tag": "[GEMINI AI]",
                        "subgroup": "grp_security_services",
                        "layer": 3,
                        "type": "ai",
                        "category": "Bilişsel Zeka & Vizyon",
                        "status": "connected",
                        "status_text": "gemini-3.8-flash & 2.5-flash",
                        "description": "Stratejik karar motoru, teknik SEO yazarı, Instagram afiş metinleri ve çok modlu görsel doğrulama zekası",
                        "payload_preview": {
                            "primary_model": "gemini-3.8-flash",
                            "fallback_model": "gemini-2.5-flash",
                            "capabilities": ["Vision Verification", "Content Synthesis", "Market Reasoning"]
                        }
                    },
                    {
                        "id": "svc_smtp_mail",
                        "label": "SMTP E-Posta Sunucusu",
                        "tag": "[SMTP MAIL]",
                        "subgroup": "grp_security_services",
                        "layer": 3,
                        "type": "service",
                        "category": "İşlemsel E-Posta",
                        "status": "connected",
                        "status_text": "STARTTLS Port 587",
                        "description": "Sipariş onayı, kargo takip linki ve yönetici güvenlik alarmlarını STARTTLS şifrelemeyle gönderir",
                        "payload_preview": {
                            "host": "smtp.gmail.com",
                            "port": 587,
                            "encryption": "STARTTLS",
                            "sender": "destek@pozitronmarket.com"
                        }
                    },

                    # KATMAN 4: MERKEZİ İSTİHBARAT & KALİTE GÜVENCESİ
                    {
                        "id": "lead_supervisor",
                        "label": "Baş Orkestrasyon (Supervisor)",
                        "tag": "[SUPERVISOR]",
                        "subgroup": "grp_orchestration_quality",
                        "layer": 4,
                        "type": "supervisor",
                        "category": "Karar & Direktif Motoru",
                        "status": "running" if sup_status.get("is_autonomous_enabled") else "idle",
                        "status_text": f"Model: {sup_status.get('model', 'gemini-3.8-flash')}",
                        "description": "2 saatte bir alt ajanları yönetir, pazar istihbaratını işler, 12 saatte bir evrim döngüsüyle strateji günceller",
                        "payload_preview": {
                            "mode": sup_status.get("evolution_mode", "BALANCED_GROWTH"),
                            "cycle_count": sup_status.get("evolution_cycle_count", 0),
                            "active_subagents": 9
                        }
                    },
                    {
                        "id": "subagent_7_qa",
                        "label": "Subagent 7: QA & Sağlık Sentineli",
                        "tag": "[SUBAGENT 7]",
                        "subgroup": "grp_orchestration_quality",
                        "layer": 4,
                        "type": "sentinel",
                        "category": "Tanı, QA & Otonom Onarım",
                        "status": "running" if qa_status.get("is_autonomous_enabled") else "idle",
                        "status_text": f"Sağlık: %{qa_status.get('last_health_score', 100)} • 8 Prob",
                        "description": "Kritik pipeline sağlık denetimi, oturum ve token doğrulama ile Gemini 3.8 Flash otonom iyileştirme",
                        "payload_preview": {
                            "health_score": qa_status.get("last_health_score", 100),
                            "probes_count": 8,
                            "auto_heal": qa_status.get("auto_heal_enabled", True)
                        }
                    },
                    {
                        "id": "subagent_10_media",
                        "label": "Subagent 10: Medya & İçerik Denetimi",
                        "tag": "[SUBAGENT 10]",
                        "subgroup": "grp_orchestration_quality",
                        "layer": 4,
                        "type": "media",
                        "category": "Görsel Kalite & Karantina",
                        "status": "active" if media_enabled else "disabled",
                        "status_text": f"Görsel Sağlık: %{media_audit.get('visual_health_score', 100)}",
                        "description": "508 ürünün görsel çözünürlük, pHash kopya ve kategori uyumsuzluğunu denetler; stüdyo görselleriyle onarır",
                        "payload_preview": {
                            "scanned_products": media_audit.get('total_products_scanned', 508),
                            "quarantine_count": media_audit.get('quarantine_candidates_count', 0),
                            "issues": media_audit.get('issues_summary', {})
                        }
                    },
                    {
                        "id": "subagent_3_telemetry",
                        "label": "Subagent 3: Telemetri Toplayıcı",
                        "tag": "[SUBAGENT 3]",
                        "subgroup": "grp_orchestration_quality",
                        "layer": 4,
                        "type": "worker",
                        "category": "Metrik / Telemetri",
                        "status": "ready",
                        "status_text": "Aktif Metrik Kaydı",
                        "description": "Satışlar, ürün görüntülenmeleri, stok devir hızı ve sepet hareketlerini derleyip Supervisor'a sunar",
                        "payload_preview": tel
                    },

                    # KATMAN 5: TİCARET, TEDARİK & FİYATLANDIRMA
                    {
                        "id": "subagent_8_procurement",
                        "label": "Subagent 8: Sipariş & Tedarik",
                        "tag": "[SUBAGENT 8]",
                        "subgroup": "grp_commerce_supply",
                        "layer": 5,
                        "type": "procurement",
                        "category": "Satınalma & Tedarik Optimizasyonu",
                        "status": "ready",
                        "status_text": f"{proc_plan.get('total_items_count', 17)} SKU • %{round(proc_plan.get('projected_roi_pct', 80.4), 1)} ROI",
                        "description": "0-stoklu ürünleri, tükenen sarf malzemelerini ve rakip stok açıklarını analiz ederek en karlı sipariş planını hazırlar",
                        "payload_preview": {
                            "investment_try": proc_plan.get('estimated_investment_try', 0),
                            "projected_profit_try": proc_plan.get('projected_profit_try', 0),
                            "total_units": proc_plan.get('total_units_count', 0)
                        }
                    },
                    {
                        "id": "subagent_5_price",
                        "label": "Subagent 5: Fiyat & Rekabet",
                        "tag": "[SUBAGENT 5]",
                        "subgroup": "grp_commerce_supply",
                        "layer": 5,
                        "type": "price",
                        "category": "İstihbarat / Arbitraj",
                        "status": "ready",
                        "status_text": f"{summary.get('total_tracked', 508)} SKU Taranıyor",
                        "description": "Türkiye FPV pazarını tarar, rakiplerin fiyatlarını analiz eder ve Pozitron'un karlı fiyat stratejisini belirler",
                        "payload_preview": summary
                    },
                    {
                        "id": "subagent_6_trend",
                        "label": "Subagent 6: Küresel Trend Avcısı",
                        "tag": "[SUBAGENT 6]",
                        "subgroup": "grp_commerce_supply",
                        "layer": 5,
                        "type": "trend",
                        "category": "Trend & Ürün Keşfi",
                        "status": "ready",
                        "status_text": f"{len(trend_props)} Trend Takipte",
                        "description": "AliExpress, Banggood ve global FPV platformlarını tarayarak yeni donanımları otomatik sıfır stokla kataloğa ekler",
                        "payload_preview": {"proposals_count": len(trend_props)}
                    },

                    # KATMAN 6: PAZARLAMA & DAĞITIM KANALLARI
                    {
                        "id": "subagent_1_instagram",
                        "label": "Subagent 1: Instagram PR",
                        "tag": "[SUBAGENT 1]",
                        "subgroup": "grp_marketing_distribution",
                        "layer": 6,
                        "type": "marketing",
                        "category": "İçerik & Topluluk",
                        "status": "running" if ig_status.get("is_autonomous_enabled") else "idle",
                        "status_text": "8-10 Format • Afiş & Hikaye",
                        "description": "Donanım savaşları, hata analizleri ve anketlerle Meta Graph API üzerinden otonom paylaşım yapar",
                        "payload_preview": active_dir.get("instagram_directive", {})
                    },
                    {
                        "id": "subagent_4_seo",
                        "label": "Subagent 4: SEO & Dokümantasyon",
                        "tag": "[SUBAGENT 4]",
                        "subgroup": "grp_marketing_distribution",
                        "layer": 6,
                        "type": "marketing",
                        "category": "İçerik Otoritesi",
                        "status": "ready",
                        "status_text": f"{tel.get('seo', {}).get('articles_published', 11)} Teknik Rehber",
                        "description": "Derin mühendislik rehberleri üretir, pinout tabloları ve Pozitron ürünlerine iç linkleme yapar",
                        "payload_preview": active_dir.get("seo_content_directive", {})
                    },
                    {
                        "id": "subagent_2_reddit",
                        "label": "Subagent 2: Reddit Etkileşim",
                        "tag": "[SUBAGENT 2]",
                        "subgroup": "grp_marketing_distribution",
                        "layer": 6,
                        "type": "marketing",
                        "category": "Organik PR / Q&A",
                        "status": "running" if (rd_status.get("is_autonomous_enabled") and reddit_enabled) else "disabled",
                        "status_text": "DEVREDIŞI (Kapalı)" if not reddit_enabled else "Aktif Otomasyon",
                        "description": "Topluluk sorularını Gemini ile yanıtlar (Subagent Açma/Kapama matrisi ile yönetilir)",
                        "payload_preview": active_dir.get("reddit_directive", {})
                    },
                    {
                        "id": "svc_google_merchant",
                        "label": "Google Merchant & Sitemap",
                        "tag": "[DESTINATION]",
                        "subgroup": "grp_marketing_distribution",
                        "layer": 6,
                        "type": "destination",
                        "category": "Arama Motoru Feed",
                        "status": "connected",
                        "status_text": "513 URL • XML/TSV",
                        "description": "Google Alışveriş sekmesi için ürün envanteri XML beslemesi ve tüm arama motorları için sitemap.xml sağlar",
                        "payload_preview": {
                            "feed_xml": "https://pozitronmarket.com/google_merchant_feed.xml",
                            "sitemap": "https://pozitronmarket.com/sitemap.xml"
                        }
                    }
                ],
                "connections": [
                    # KATMAN 1 -> KATMAN 2: Giriş ve Altyapı
                    {"from": "client_customer", "to": "srv_github_platform", "label": "Statik Sayfalar & CDN Gezinme", "type": "network"},
                    {"from": "client_customer", "to": "srv_hetzner_cloud", "label": "Dinamik API İstekleri (Sepet/Stok)", "type": "network"},
                    {"from": "trigger_cron_2h", "to": "srv_hetzner_cloud", "label": "2 Saatlik Periyodik Watchdog", "type": "trigger"},
                    {"from": "trigger_github_dispatch", "to": "srv_github_platform", "label": "Actions CI/CD Dağıtım Emri", "type": "trigger"},

                    # KATMAN 2 -> KATMAN 3: Sunucu -> Güvenlik & Dış Servisler
                    {"from": "srv_hetzner_cloud", "to": "subagent_9_security", "label": "Trafik & WAF Güvenlik Denetimi", "type": "probe"},
                    {"from": "srv_hetzner_cloud", "to": "svc_paytr", "label": "3D Secure Ödeme & Webhook Doğrulama", "type": "payment"},
                    {"from": "srv_hetzner_cloud", "to": "svc_gemini_ai", "label": "Gemini API Akıl Yürütme Talepleri", "type": "data"},
                    {"from": "srv_hetzner_cloud", "to": "svc_smtp_mail", "label": "İşlemsel Sipariş & Güvenlik Maili", "type": "payment"},

                    # KATMAN 3 -> KATMAN 4: Güvenlik/Dış Servisler -> Merkezi İstihbarat
                    {"from": "subagent_9_security", "to": "lead_supervisor", "label": "Güvenlik Skoru & Tehdit Telemetrisi", "type": "data"},
                    {"from": "svc_paytr", "to": "lead_supervisor", "label": "Ödeme Başarı & Finansal Rapor", "type": "data"},
                    {"from": "svc_gemini_ai", "to": "lead_supervisor", "label": "Bilişsel Çıkarım & Karar Desteği", "type": "data"},

                    # KATMAN 4 İÇ BAĞLANTILARI: Kalite, QA & Telemetri
                    {"from": "lead_supervisor", "to": "subagent_7_qa", "label": "Sistem Sağlık Yoklama Direktifi", "type": "directive"},
                    {"from": "subagent_7_qa", "to": "lead_supervisor", "label": "Sağlık Raporu (100/100)", "type": "probe"},
                    {"from": "lead_supervisor", "to": "subagent_10_media", "label": "Ürün Medya & Açıklama Denetim Emri", "type": "directive"},
                    {"from": "subagent_10_media", "to": "db_sqlite", "label": "Karantina & Görsel Düzeltme Güncellemesi", "type": "data"},
                    {"from": "lead_supervisor", "to": "subagent_3_telemetry", "label": "Telemetri Derleme Direktifi", "type": "directive"},
                    {"from": "subagent_3_telemetry", "to": "lead_supervisor", "label": "Katalog & Satış Telemetri Beslemesi", "type": "data"},

                    # KATMAN 4 -> KATMAN 5: İstihbarat -> Ticaret & Tedarik
                    {"from": "lead_supervisor", "to": "subagent_8_procurement", "label": "Sipariş & Stok Yenileme Direktifi", "type": "directive"},
                    {"from": "lead_supervisor", "to": "subagent_5_price", "label": "Pazar Fiyat & Arbitraj Tarama Emri", "type": "directive"},
                    {"from": "lead_supervisor", "to": "subagent_6_trend", "label": "Küresel Trend Keşif Emri", "type": "directive"},
                    {"from": "subagent_6_trend", "to": "subagent_8_procurement", "label": "Trend Donanım Tedarik Girdisi", "type": "data"},
                    {"from": "subagent_5_price", "to": "subagent_8_procurement", "label": "Rakip Stok Açığı & Maliyet Verisi", "type": "data"},
                    {"from": "subagent_8_procurement", "to": "db_sqlite", "label": "Tedarik Planı Kaydı (JSON/CSV)", "type": "data"},

                    # KATMAN 5/4 -> KATMAN 6: Pazarlama & Dağıtım Kanalları
                    {"from": "lead_supervisor", "to": "subagent_1_instagram", "label": "Instagram PR & Kampanya Direktifi", "type": "directive"},
                    {"from": "lead_supervisor", "to": "subagent_4_seo", "label": "Teknik SEO & Rehber Yazım Direktifi", "type": "directive"},
                    {"from": "lead_supervisor", "to": "subagent_2_reddit", "label": "Reddit Destek Direktifi (Kapalı)", "type": "directive"},
                    {"from": "subagent_1_instagram", "to": "client_customer", "label": "Sosyal Medya Trafiği & Müşteri Çekme", "type": "publish"},
                    {"from": "subagent_4_seo", "to": "srv_github_platform", "label": "SEO Makaleleri Statik HTML Yayını", "type": "publish"},
                    {"from": "subagent_5_price", "to": "svc_google_merchant", "label": "XML/TSV Feed & Fiyat Entegrasyonu", "type": "publish"}
                ],
                "ecosystem_services": [
                    {
                        "id": "srv_hetzner",
                        "name": "Hetzner Cloud VPS",
                        "category": "Bulut & Sunucu",
                        "provider": "Hetzner Online GmbH",
                        "role": "Pozitron Market Ana Backend Sunucusu, API Gateway ve Otonom İşçi Motoru",
                        "endpoints": ["https://api.pozitronmarket.com", "213.133.104.148 (Falkenstein/Nuremberg)"],
                        "protocols": ["HTTPS (Port 443)", "HTTP Python Backend (Port 8000)", "SSH (Port 22)"],
                        "status": "OPERATIONAL",
                        "badge": "UBUNTU 24.04 VPS",
                        "details": "Ubuntu 24.04 LTS üzerinde çalışan Nginx ters proxy, Systemd pozitron.service, SQLite veritabanı ve 10 otonom alt ajanı 7/24 kesintisiz barındırır."
                    },
                    {
                        "id": "srv_github",
                        "name": "GitHub Server (Platform)",
                        "category": "Bulut & Sunucu",
                        "provider": "GitHub Inc. / Microsoft",
                        "role": "Kaynak Kod Havuzu, GitHub Pages CDN Statik Dağıtımı ve GitHub Actions CI/CD",
                        "endpoints": ["https://pozitronmarket.com", "thepeakiscold/pozitron-market", "GitHub Actions Runner"],
                        "protocols": ["HTTPS (Port 443)", "Git over SSH", "GitHub REST API v3 / Dispatch"],
                        "status": "OPERATIONAL",
                        "badge": "PAGES CDN & CI/CD",
                        "details": "Pozitron Market'in 508 ürün sayfasını, anasayfasını ve statik varlıklarını küresel CDN üzerinde sıfır gecikmeyle ziyaretçilere sunar."
                    },
                    {
                        "id": "subagent_9_security_svc",
                        "name": "Siber Güvenlik & Savunma Altyapısı",
                        "category": "Güvenlik & Savunma",
                        "provider": "Pozitron Otonom Sentineli",
                        "role": "WAF, Brute-Force Koruması, SQLi/XSS Filtreleri, PayTR İmza ve SSL Süre Denetimi",
                        "endpoints": ["/api/security/status", "/api/security/scan"],
                        "protocols": ["HMAC-SHA256", "TLS 1.3 Audit", "Heuristic WAF"],
                        "status": "OPERATIONAL",
                        "badge": "GÜVENLİK: %100",
                        "details": "Pozitron Market'in tüm API uç noktalarını, ödeme bildirimlerini ve şifrelenmiş kimlik doğrulama mekanizmalarını sürekli denetler."
                    },
                    {
                        "id": "subagent_10_media_svc",
                        "name": "Ürün Medya & İçerik Kalite Altyapısı",
                        "category": "Kalite Güvencesi",
                        "provider": "Pozitron Vision AI Asset Sourcing",
                        "role": "508 Ürün Görseli, Çözünürlük, pHash Kopya ve Kategori Uyumsuzluğu Denetimi & Onarımı",
                        "endpoints": ["/api/media/audit", "/api/media/scan", "/api/media/fix"],
                        "protocols": ["Multimodal Vision AI", "Perceptual Hash (pHash)", "Pillow Engine"],
                        "status": "OPERATIONAL",
                        "badge": "MEDYA DENETÇİSİ",
                        "details": "Üretici resmi kaynaklarından stüdyo fotoğraflarını eşleştirir; kategorisiyle uyuşmayan yanlış görselleri otomatik karantinaya alır."
                    },
                    {
                        "id": "svc_paytr",
                        "name": "PayTR Sanal POS Ödeme Altyapısı",
                        "category": "Dış Servisler & Ödeme",
                        "provider": "PayTR Ödeme ve Elektronik Para Kuruluşu A.Ş.",
                        "role": "3D Secure Güvenli Kredi Kartı Tahsilatı, iFrame Entegrasyonu ve Webhook Onayı",
                        "endpoints": ["https://www.paytr.com/odeme/api/get-token", "/api/paytr/callback"],
                        "protocols": ["HTTPS REST API", "HMAC-SHA256 Tokenization & Webhook"],
                        "status": "OPERATIONAL",
                        "badge": "3D SECURE POS",
                        "details": "Müşterilerin güvenle sipariş vermesini sağlar; ödeme tamamlandığında Hetzner sunucusundaki /api/paytr/callback uç noktasına HMAC-SHA256 imzalı onay iletir."
                    },
                    {
                        "id": "svc_gemini",
                        "name": "Google Gemini Yapay Zeka Bulutu",
                        "category": "Dış Servisler & Ödeme",
                        "provider": "Google DeepMind / Google Cloud",
                        "role": "Çok Modlu Muhakeme, Pazar Fiyat Arbitrajı, SEO İçerik Sentezi ve Instagram PR Üretimi",
                        "endpoints": ["generativelanguage.googleapis.com/v1beta/models"],
                        "protocols": ["HTTPS REST (JSON / Ephemeral RPC)"],
                        "status": "OPERATIONAL",
                        "badge": "GEMINI 3.8 FLASH",
                        "details": "Antigravity 2.0 orkestrasyon motorunun beynidir. gemini-3.8-flash (ana) ve gemini-2.5-flash (yedek) modelleriyle alt ajanların kararlarını yönlendirir."
                    },
                    {
                        "id": "svc_smtp",
                        "name": "Gmail Güvenli SMTP Sunucusu",
                        "category": "Dış Servisler & Ödeme",
                        "provider": "Google Workspace / Gmail",
                        "role": "Sipariş Onay E-Postaları, E-Fatura Bildirimi ve Yönetici Güvenlik Alarmları",
                        "endpoints": ["smtp.gmail.com:587"],
                        "protocols": ["SMTP over STARTTLS"],
                        "status": "OPERATIONAL",
                        "badge": "STARTTLS PORT 587",
                        "details": "Başarılı siparişlerde müşteriye anında sipariş özeti ve kargo takip numarası gönderir; kritik sistem alarmlarını yöneticiye iletir."
                    },
                    {
                        "id": "svc_instagram",
                        "name": "Meta Graph API (Instagram)",
                        "category": "Dağıtım & Kanallar",
                        "provider": "Meta Platforms, Inc.",
                        "role": "Otonom Gönderi, Reels ve Hikaye Yayını (@pozitronmarket)",
                        "endpoints": ["graph.facebook.com/v19.0/17841430407836914"],
                        "protocols": ["HTTPS REST OAuth 2.0 Bearer Token"],
                        "status": "OPERATIONAL",
                        "badge": "GRAPH API & REELS",
                        "details": "Pozitron'un 8-10 farklı içerik formatındaki (Donanım Kıyaslamaları, Hata Analizleri, Anketler) 1080x1080 afişlerini Instagram hesabında otomatik yayınlar."
                    },
                    {
                        "id": "svc_reddit",
                        "name": "Reddit Web Otomasyonu",
                        "category": "Dağıtım & Kanallar",
                        "provider": "Reddit Inc.",
                        "role": "Hedef Subredditlerde Organik FPV Teknik Desteği (r/Turkey, r/teknoloji)",
                        "endpoints": ["u/Aggravating_End_1105", "Chrome Decrypted Session"],
                        "protocols": ["HTTPS Web Automation"],
                        "status": "MANAGED (Kapalı)" if not reddit_enabled else "OPERATIONAL",
                        "badge": "SUBAGENT 2",
                        "details": "Türk drone meraklılarına spam yapmadan sıfır yönlendirmeli teknik yardım sunar. Kullanıcı talebi üzerine Subagents Toggle Matrisi ile şu anda güvenli biçimde kapalı tutulmaktadır."
                    },
                    {
                        "id": "svc_google_merchant",
                        "name": "Google Merchant Center & Arama Motorları",
                        "category": "Dağıtım & Kanallar",
                        "provider": "Google LLC",
                        "role": "Google Alışveriş Sekmesi Envanter Akışı, Schema.org ve Otomatik Sitemap",
                        "endpoints": ["/google_merchant_feed.xml", "/google_merchant_feed.tsv", "/sitemap.xml"],
                        "protocols": ["HTTP(S) XML / TSV Feed Crawling"],
                        "status": "OPERATIONAL",
                        "badge": "513 URL SITEMAP",
                        "details": "508 FPV donanım ürününü Google Merchant Center ile otomatik senkronize eder. Fiyat, stok ve kargo bilgilerini Google Alışveriş sekmesinde yayınlar, 513 URL'li sitemap ile SEO otoritesi sağlar."
                    },
                    {
                        "id": "db_sqlite",
                        "name": "SQLite İlişkisel Veritabanı",
                        "category": "Bulut & Sunucu",
                        "provider": "Yerel Dosya Tabanlı ACID Veritabanı",
                        "role": "Ürün Kataloğu, Siparişler, Yorumlar, SEO Makaleleri ve Ajan Durumları",
                        "endpoints": ["pozitron.db (Hetzner VPS & Yerel)"],
                        "protocols": ["SQLite3 Native Socket"],
                        "status": "HEALTHY",
                        "badge": "ACID VERİTABANI",
                        "details": "508 ürün kaydı, siparişler, müşteri yorumları, fiyat takip logları, global trend önerileri ve Subagent 8 toptan sipariş planlarını güvenli ACID işlemleriyle saklar."
                    }
                ]
            }
'''

with open('server.py', 'r', encoding='utf-8') as f:
    code = f.read()

start_marker = '            sec_audit = cyber_security_agent.get_latest_audit() or {}\n'
if start_marker not in code:
    start_marker = '            graph = {\n'

start_idx = code.find(start_marker)
end_marker = '            self.send_json(200, graph)\n            return'
end_idx = code.find(end_marker)

if start_idx != -1 and end_idx != -1:
    code = code[:start_idx] + new_graph_code + code[end_idx:]
    with open('server.py', 'w', encoding='utf-8') as f:
        f.write(code)
    print('Updated server.py pipeline graph to vertical architecture successfully!')
else:
    print('ERROR: could not find start or end marker!', start_idx, end_idx)
    sys.exit(1)
