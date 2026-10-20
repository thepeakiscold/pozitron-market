# ⚡ Pozitron Market — Technical Architecture & LLM Operating Manual

> **Comprehensive Technical Specification & Architecture Manual**  
> *Target Audience:* Autonomous AI Agents, Large Language Models (LLMs), Systems Engineers, and DevOps Operators.  
> *Language:* English  
> *Repository:* `thepeakiscold/pozitron-market`  
> *Platform Version:* 3.8.0-PROD  

---

## 1. Executive Summary & Architecture Philosophy

**Pozitron Market** is a dual-tier e-commerce platform and autonomous multi-agent ecosystem engineered for high-performance FPV (First Person View) racing drones, commercial UAV hardware, and robotic electronics.

The platform is built on an **Edge-Hybrid Dual Storefront Architecture**:
1. **Tier 1 (Static Edge Storefront - GitHub Pages Compatible):**
   - Fully client-side responsive SPA (`index.html`, `styles.css`, `app.js`, `i18n.js`).
   - Zero-latency product catalog powered by pre-compiled JSON bundles (`data/pozitron_data.js` and `data/products.json`).
   - Runs independently without server dependencies for 100% uptime, global CDN distribution, and static deployment.
2. **Tier 2 (Autonomous Python Backend - Hetzner Cloud VPS / Local Systemd):**
   - Production multithreaded HTTP REST server (`server.py`) serving dynamic e-commerce, checkout, PayTR payment gateway, coupon engine, email dispatch, and admin APIs.
   - Persistence powered by SQLite 3 running in high-concurrency **Write-Ahead Logging (WAL)** mode (`pozitron.db`).
   - An autonomous **Multi-Agent Orchestration Engine** (`orchestrator/`) comprising a **Lead Supervisor** and **10 specialized subagents** executing continuous intelligence, SEO, inventory procurement, cyber defense, dynamic pricing, and automated media repair.

```
                              POZITRON ECOSYSTEM TOPOLOGY
                              
    +-------------------------------------------------------------------------+
    |                             CLIENT LAYER                                |
    |   [Browser / Mobile] <====== HTTPS ======> [GitHub Pages / CDN Edge]    |
    |   (app.js + i18n.js)                       (Static Bundle: pozitron_data)|
    +------------------------------------+------------------------------------+
                                         | REST / WebSockets
                                         v
    +-------------------------------------------------------------------------+
    |                    HETZNER CLOUD VPS (Ubuntu 24.04 LTS)                 |
    |                                                                         |
    |   [Firewall: UFW + Fail2ban]                                            |
    |             |                                                           |
    |   [Nginx Reverse Proxy] (SSL Termination: Let's Encrypt Certbot)        |
    |             | Port 8000 Proxy                                           |
    |             v                                                           |
    |   [Python 3.12+ Server: server.py] (Systemd: pozitron.service)          |
    |   * Endpoints: /api/products, /api/orders, /api/coupons, /api/pipeline   |
    |             |                                                           |
    |   +---------+--------------------+-------------------+                  |
    |   |                              |                   |                  |
    |   v                              v                   v                  |
    | [SQLite WAL Engine]        [Multi-Agent]      [External Services]       |
    | (pozitron.db)              [Orchestrator]     * SMTP (Port 587)         |
    | * 25 Normalized Tables     * Lead Supervisor  * PayTR Gateway           |
    | * ACID / WAL Concurrency   * 10 Subagents     * Gemini 3.8 Flash AI     |
    +-------------------------------------------------------------------------+
```

---

## 2. Repository Directory & Component Layout

```
Pozitron/
├── README.md                      # This technical master specification
├── index.html                     # Primary storefront (Bilingual TR/EN, Drone Compatibility Engine, Cart)
├── bots.html                      # Unified Autonomous Bot & Multi-Agent Operations Command Center
├── styles.css                     # Design system (cyberpunk/clean industrial aesthetics, responsive layout)
├── app.js                         # Core client-side MVC controller, dynamic search, cart & checkout logic
├── i18n.js                        # Localization engine (Turkish / English dictionary & currency converter)
├── server.py                      # Multi-threaded Python HTTP REST API server & webhook handler
├── database.py                    # SQLite schema definitions, connection pool, migrations & seeders
├── coupons.py                     # Secure coupon validation, redemption, email normalization & clamping engine
├── content_generator.py           # Multi-modal poster & social graphic generation engine (Brand Template)
├── export_data.py                 # SQLite-to-static bridge (exports pozitron.db to static JS/JSON)
├── seed_data.py                   # Catalog seeder (500+ authentic FPV components with specs)
├── requirements.txt               # Python production dependencies (Pillow, requests, pycryptodome, etc.)
├── render.yaml                    # Cloud blueprint for Render.com deployment fallback
│
├── orchestrator/                  # Multi-Agent Autonomous Intelligence Engine
│   ├── lead_supervisor.py         # Lead Autonomous Supervisor (11-step cycle, AI Meta-Evolution)
│   ├── subagent_telemetry.py      # Subagent 3: System Telemetry & Performance Prober
│   ├── subagent_seo.py            # Subagent 4: Technical SEO & Guide Generator
│   ├── subagent_price_intelligence.py # Subagent 5: Dynamic Price & Margin Intelligence
│   ├── subagent_trend_hunter.py   # Subagent 6: Global Drone Hardware & Trend Hunter
│   ├── subagent_qa.py             # Subagent 7: Autonomous QA & Synthetic Order Prober
│   ├── subagent_procurement.py    # Subagent 8: Procurement & Restocking Optimization Desk
│   ├── subagent_security.py       # Subagent 9: Cyber Security Sentinel & Honeypot Monitor
│   ├── subagent_media_inspector.py# Subagent 10: Product Media Auditor & Auto-Remediation Engine
│   ├── qa_scheduler.py            # Background QA scheduler daemon
│   └── duplicate_guard.py         # pHash & perceptual image duplicate prevention
│
├── instagram_agent/               # Subagent 1: Instagram Visual PR & Reel Generation
│   ├── agent.py                   # Instagram post scheduler & Graph API publisher
│   └── db.py                      # Instagram operational state & schedule persistence
│
├── reddit_agent/                  # Subagent 2: Reddit Community & Technical Engagement
│   └── agent.py                   # Reddit autonomous thread generator & comment monitor
│
├── scripts/                       # DevOps, Migration, Cloud & Provisioning Scripts
│   ├── setup_hetzner.sh           # One-touch automated VPS provisioning for Hetzner Cloud
│   ├── cloud_market_sync.py       # Autonomous cloud inventory synchronizer & merchant feed updater
│   ├── normalize_product_images.py# Image normalization utility (AVIF/WebP -> Progressive JPEG)
│   ├── rollback_catalog.py        # Disaster recovery one-click rollback script
│   ├── download_free_images.py    # Unsplash / Pexels fallback asset downloader
│   ├── product_review.py          # Synthetic review engine
│   └── google_apps_script_market_relay.js # Google Sheets / Apps Script relay fallback
│
├── data/                          # Shared State, Logs & Static Catalog Exports
│   ├── pozitron_data.js           # Static JavaScript bundle for GitHub Pages (window.__POZITRON_DATA__)
│   ├── products.json              # Structured JSON catalog (500+ SKUs with technical specs)
│   ├── latest_media_audit.json    # Subagent 10 visual health report & quarantine candidate cache
│   └── orders_log.json            # Rolling ledger of the latest 500 completed transactions
│
├── backups/                       # Snapshot Backups & Disaster Recovery Storage
│   ├── pre_authentic_catalog_backup/ # Pristine database & JSON bundle backup
│   └── backup_before_revert_to_google_images/
│
├── assets/                        # Static Visual Assets, Logos & Media
│   ├── logo.svg / logo.png        # Brand identity vector and raster assets
│   ├── favicon.svg                # Browser favicon
│   ├── placeholder.svg            # Fallback image placeholder
│   └── products/                  # 508 verified product studio photos (1080x1080 JPEG)
│       └── _originals/            # Master uncompressed original assets
│
└── tests/                         # Comprehensive Pytest & Unittest Verification Suite
    ├── test_coupon_security_and_quarantine_flow.py # Security regression & auto-fix tests
    ├── test_coupons.py            # Coupon service, limits, and domain logic
    ├── test_media_inspector_agent.py # Subagent 10 vision audits & semantic mismatch checks
    ├── test_post_studio_visual_enhancements.py # Brand template rendering & normalization
    ├── test_cyber_security_agent.py # Subagent 9 honeypot & intrusion detection
    ├── test_procurement_agent.py  # Subagent 8 replenishment calculations
    ├── test_qa_agent.py           # Subagent 7 synthetic purchasing & link checking
    └── ... (30+ test suites ensuring 100% regression coverage)
```

---

## 3. Database Architecture & Storage Mechanics (`pozitron.db`)

### 3.1 SQLite Engine Configuration
The persistence layer is implemented in `database.py` via SQLite 3 configured with enterprise concurrency pragmas:

```sql
PRAGMA journal_mode = WAL;         -- Write-Ahead Logging allows concurrent readers and writers
PRAGMA foreign_keys = ON;          -- Strict referential integrity enforcement
PRAGMA busy_timeout = 30000;       -- 30-second lock timeout prevents "database is locked" errors
PRAGMA synchronous = NORMAL;       -- Safe durability with maximum SSD write throughput
```

### 3.2 Relational Entity Schema Breakdown

```
+-------------------------------------------------------------------------------------------+
|                                    DATABASE SCHEMAS                                       |
+------------------------------------+------------------------------------------------------+
| Domain / Module                    | Tables & Responsibilities                            |
+------------------------------------+------------------------------------------------------+
| Core E-Commerce Catalog            | - categories (id, slug, name_en, name_tr, icon)      |
|                                    | - products (sku, slug, prices, stock, specs_json,    |
|                                    |   compatibility_json, image_url, is_bestseller)      |
|                                    | - product_quality_checks (reviewer, content_hash)    |
+------------------------------------+------------------------------------------------------+
| User Management & Addresses        | - users (email, password_hash, role, provider)       |
|                                    | - user_addresses (user_id, title, city, address)     |
|                                    | - password_resets (token, expires_at)                |
+------------------------------------+------------------------------------------------------+
| Orders & Checkout                  | - orders (order_number, total_try, status, items_json|
|                                    |   payment_method, shipping_address, tracking_code)   |
|                                    | - reviews (product_id, user_id, rating, comment)     |
+------------------------------------+------------------------------------------------------+
| Coupon & Anti-Fraud Engine         | - coupons (code, discount_type, discount_value,      |
|                                    |   min_order_try, per_user_limit, max_uses, is_active)|
|                                    | - coupon_redemptions (coupon_code, user_key, order_id|
|                                    |   UNIQUE(coupon_code, user_key, order_id))           |
|                                    | - coupon_logs (coupon_code, event, details, actor)   |
+------------------------------------+------------------------------------------------------+
| Lead Supervisor & Meta-Evolution   | - lead_supervisor_config (model, auto_evolve, cadence|
|                                    | - lead_supervisor_directives (cycle_id, payload_json)|
|                                    | - lead_evolution_logs (mutations, fitness_delta)     |
+------------------------------------+------------------------------------------------------+
| Autonomous Subagent Intelligence   | - subagents_config (subagent_id, is_enabled, cadence)|
|                                    | - telemetry_history (cpu, latency, error_count)      |
|                                    | - price_intelligence_logs (market_avg, margins)      |
|                                    | - trend_price_comparisons (sku, competitor_price)    |
|                                    | - global_trend_proposals (brand, source_url, status) |
|                                    | - seo_articles (slug, markdown, keywords_json)       |
|                                    | - procurement_order_plans (supplier, total_cost)     |
|                                    | - security_audit_logs (ip, threat_level, payload)    |
|                                    | - product_media_audits (sku, issue_type, status)     |
|                                    | - settings (key, value)                              |
+------------------------------------+------------------------------------------------------+
```

### 3.3 Data Integrity & Schema Migration Pattern
Migrations are handled programmatically in `database.py:init_db()`. If tables exist from legacy versions, migrations run dynamically:
- Example: `coupon_redemptions` was migrated from `UNIQUE(coupon_code, user_key)` to `UNIQUE(coupon_code, user_key, order_id)` to allow `per_user_limit > 1` multi-use coupons without SQLite constraint crashes.

---

## 4. Multi-Agent Autonomous Orchestration Ecosystem

The platform operates on a hierarchical multi-agent framework governed by the **Lead Supervisor Agent** (`orchestrator/lead_supervisor.py`) running an autonomous loop.

```
                            [LEAD SUPERVISOR]
                    (Gemini 3.8 Flash / Pro Engine)
                                   |
         +-------------------------+-------------------------+
         |                         |                         |
  [Customer Facing]         [Intelligence]            [Security & QA]
  Subagent 1: Instagram     Subagent 3: Telemetry     Subagent 7: QA Sentinel
  Subagent 2: Reddit        Subagent 5: Pricing       Subagent 9: Cyber Sec
  Subagent 4: Tech SEO      Subagent 6: Trend Hunter  Subagent 10: Media Fix
                            Subagent 8: Procurement
```

### 4.1 The 11-Step Lead Supervisor Cycle (`execute_cycle()`)
Every cycle executes the following sequence:
1. **Audit Logs & Telemetry:** Reads Subagent 3 server metrics and DB health.
2. **Catalog Health & Stock Check:** Identifies 0-stock and low-stock SKUs.
3. **Price & Margin Intelligence:** Analyzes Subagent 5 competitor scraping; raises alerts on underpriced items.
4. **Global Trend Ingestion:** Pulls Subagent 6 new hardware discoveries.
5. **Procurement Optimization:** Runs Subagent 8 restocking models; suggests wholesale supplier purchase orders.
6. **SEO Generation Directive:** Commands Subagent 4 to generate high-ranking technical guides for high-margin parts.
7. **Social Media Directives:** Dispatches topic guidance to Subagents 1 (Instagram) and 2 (Reddit).
8. **Cyber Threat Assessment:** Ingests Subagent 9 security logs, banning abusive IP addresses.
9. **Automatic Promotion:** Selects top price-advantage products and marks them `is_bestseller = 1`.
10. **Directive Persistence:** Serializes all decisions into `lead_supervisor_directives`.
11. **Autonomous Media Remediation:** Invokes Subagent 10 (`auto_fix_quarantined_products(dry_run=False)`) to automatically replace quarantined product photos with verified manufacturer studio assets.

### 4.2 Subagent Directory & Responsibilities

| Subagent ID | Name / Role | Model / Tech Stack | Primary Capabilities |
| :--- | :--- | :--- | :--- |
| **`lead_supervisor`** | **Lead Autonomous Supervisor** | Gemini 3.8 Flash / Pro | Coordinates entire network, evaluates KPIs, mutates strategies, triggers subagents. |
| **`subagent_1_instagram`**| **Instagram Growth & Visual PR** | Pillow + FLUX.1 + LTX-Video | Renders 1080x1080 Brand Template posters, 10s FPV Reels, automated captioning & posting. |
| **`subagent_2_reddit`**   | **Reddit Community Specialist** | Python PRAW / Gemini Flash | Publishes technical build logs, answers drone questions on r/fpv, tracks karma. |
| **`subagent_3_telemetry`**| **System Telemetry & Health** | Python Psutil + SQLite | Monitors CPU, RAM, SQLite file locks, endpoint latency, and network traffic. |
| **`subagent_4_seo`**      | **Technical SEO & Guide Author**| Gemini 3.8 Flash | Generates 1500+ word markdown build guides with TF-IDF semantic deduplication. |
| **`subagent_5_price`**    | **Dynamic Price Intelligence** | Requests + BeautifulSoup | Scrapes global competitors (GetFPV, Banggood, DroneMarket), tracks USD/TRY FX rates. |
| **`subagent_6_trend`**    | **Global Trend Hunter** | Web Scraper / RSS Parser | Detects newly announced motors, flight controllers, and video transmitters globally. |
| **`subagent_7_qa`**       | **Autonomous QA Sentinel** | Synthetic Client Engine | Performs automated checkout, probes API health, validates shopping cart math. |
| **`subagent_8_procurement`**| **Procurement & Restock Desk** | Inventory Math Engine | Computes safety stock, reorder thresholds, and calculates wholesale margin targets. |
| **`subagent_9_security`** | **Cyber Security Sentinel** | WAF & Log Analyzer | Traps SQLi/XSS attacks, monitors honeypot endpoints (`/wp-login.php`, etc.), blocks IPs. |
| **`subagent_10_media`**   | **Media Inspector & Auto-Fix** | Vision AI + pHash Engine | Detects corrupted images (AVIF/0-byte), flags category mismatches, auto-patches studio DAM. |

---

## 5. Cloud Deployment & Hetzner Infrastructure

The system is engineered for automated bare-metal or VPS deployment on **Hetzner Cloud** (e.g. CPX21 / CPX31 instances running Ubuntu 22.04 or 24.04 LTS).

### 5.1 One-Touch Automated Provisioning (`scripts/setup_hetzner.sh`)
The automated script sets up the entire production runtime:
```bash
sudo bash scripts/setup_hetzner.sh
```

**Key Provisioning Steps Executed:**
1. Installs system packages: `python3-venv`, `sqlite3`, `ffmpeg`, `nginx`, `certbot`, `python3-certbot-nginx`, `ufw`, `fail2ban`.
2. Clones or synchronizes repository to `/var/www/pozitron`.
3. Creates dedicated virtual environment (`/var/www/pozitron/venv`) and installs `requirements.txt`.
4. Creates secure environment file at `/etc/pozitron/pozitron.env` with restricted 600 permissions.
5. Configures systemd unit `/etc/systemd/system/pozitron.service` with automatic respawn (`Restart=always`, `RestartSec=5`).
6. Configures Nginx reverse proxy with HTTP/1.1 WebSocket forwarding, timeouts, and security headers.
7. Configures UFW firewall and obtains automated SSL certificates via Let's Encrypt Certbot.

### 5.2 Systemd Production Service Definition
```ini
[Unit]
Description=Pozitron Market Backend API Service
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/pozitron
EnvironmentFile=-/etc/pozitron/pozitron.env
Environment=PYTHONUNBUFFERED=1
Environment=POZITRON_ENV=production
Environment=PORT=8000
ExecStart=/var/www/pozitron/venv/bin/python3 /var/www/pozitron/server.py
Restart=always
RestartSec=5
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
```

*Note on Local Development / Workstation:*  
On the current development machine, the server runs under user systemd at:  
`/home/eyup/.config/systemd/user/pozitron-server.service`  
Controlled via: `systemctl --user restart pozitron-server.service`.

### 5.3 Nginx Reverse Proxy Architecture
```nginx
server {
    listen 80;
    listen [::]:80;
    server_name api.pozitronmarket.com;

    client_max_body_size 100M;
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options SAMEORIGIN always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

### 5.4 Networking, Firewall & Direct SMTP Relay
- **Inbound Ports:**
  - `22/tcp` -> SSH
  - `80/tcp` -> HTTP (Nginx / ACME Challenge)
  - `443/tcp` -> HTTPS (TLS 1.3 / SSL)
- **Internal Port:**
  - `8000/tcp` -> Python REST API (`server.py`) bound to `127.0.0.1`
- **Outbound Email:**
  - Unlike AWS EC2 (which blocks port 25/587 by default), **Hetzner Cloud supports direct outbound SMTP over Port 587 (TLS/STARTTLS)**.
  - Pozitron utilizes direct SMTP relay (`smtp.gmail.com:587`) for automated order confirmations, password reset tokens, and security alert dispatches.

---

## 6. Data Synchronization & Dual-Mode Hosting Bridge

Pozitron seamlessly unifies static hosting with dynamic server persistence:

```
               [SQLite Database: pozitron.db]
                              |
                     (export_data.py)
                              |
         +--------------------+--------------------+
         |                                         |
         v                                         v
 [data/products.json]                    [data/pozitron_data.js]
  (Structured JSON)                       (window.__POZITRON_DATA__)
         |                                         |
         +--------------------+--------------------+
                              |
                 (Git Commit / Push / Webhook)
                              v
                [GitHub Pages Static Edge]
```

### 6.1 `export_data.py` (The Synchronization Engine)
Whenever an administrator adds a product, or an autonomous agent modifies prices or fixes media:
1. `export_data.py` queries `pozitron.db`.
2. Serializes categories, products, technical specs, compatibility matrices, reviews, and SEO guides.
3. Generates `data/pozitron_data.js` for zero-lag browser consumption.
4. Generates `data/products.json` for external integrations and feeds.

### 6.2 `scripts/cloud_market_sync.py` (CI/CD Inventory Daemon)
When operating in pure GitHub Pages mode without an active VPS backend:
- Orders placed on the edge invoke an API relay (or serverless webhook).
- `cloud_market_sync.py` runs inside GitHub Actions, decrements inventory in `data/products.json` and `data/pozitron_data.js`, records `data/orders_log.json`, and commits back to `main`.

---

## 7. Backup, Rollback & Disaster Recovery Protocol

### 7.1 Snapshot Backup Directories
The repository maintains clean, version-controlled backup points:
- `backups/pre_authentic_catalog_backup/`:
  - `pozitron.db`: Reference SQLite database.
  - `products.json`: Canonical catalog.
  - `pozitron_data.js`: Verified static client bundle.
- `assets/products/_originals/`:
  - Pristine original uncompressed imagery before normalization.

### 7.2 One-Click Catalog & DB Rollback (`scripts/rollback_catalog.py`)
If an automated scrape, faulty agent cycle, or user error corrupts the catalog:
```bash
python3 scripts/rollback_catalog.py
```
**Execution Flow:**
1. Validates existence of snapshot directory `backups/pre_authentic_catalog_backup`.
2. Atomically replaces `pozitron.db`, `data/products.json`, and `data/pozitron_data.js`.
3. Invokes `export_static_data()` to guarantee client-side bundles match the restored database.
4. Returns catalog to a known 100% verified state.

### 7.3 Automated SQLite Backup Routine (Recommended Cron)
For production deployments on Hetzner, the following cronjob performs live, lock-free SQLite backups via `sqlite3 .backup`:
```bash
# Add to crontab: crontab -e
0 3 * * * sqlite3 /var/www/pozitron/pozitron.db ".backup '/var/www/pozitron/backups/daily_$(date +\%Y\%m\%d).db'"
```

---

## 8. Security, Anti-Fraud & Coupon Engine

Pozitron features a hardened security model tested against penetration vectors:

### 8.1 Coupon Security Guarantees (`coupons.py`)
1. **Cross-Identity Abuse Prevention:**
   - Evaluates both `user_id` and normalized `email`.
   - Prevents a user from redeeming a coupon logged-in, then checking out as a guest with the same email to bypass `per_user_limit`.
2. **Gmail / Googlemail Canonicalization:**
   - Normalizes emails via `normalize_email()`.
   - Strips dot variations (`p.i.l.o.t@gmail.com` -> `pilot@gmail.com`).
   - Strips plus tags (`pilot+promo1@gmail.com` -> `pilot@gmail.com`).
   - Blocks alias-based infinite coupon farming.
3. **Multi-Use Per-User Limit Support:**
   - Schema uses `UNIQUE(coupon_code, user_key, order_id)`.
   - Allows legitimate multi-use coupons (`per_user_limit = 2` allows 2 separate orders and strictly blocks the 3rd).
4. **Discount Clamping & Bounds Protection:**
   - Fixed discounts cannot exceed cart `subtotal` (no negative total orders).
   - Percentage discounts are clamped to `100.0%`.
   - API rejects negative values for `min_order_try` or `discount_value`.

### 8.2 Cyber Security Sentinel (`subagent_security.py`)
- Emits decoy honeypots for automated vulnerability scanners (`/admin.php`, `/wp-login.php`, `/.env`).
- Evaluates incoming request headers for SQL injection (`UNION SELECT`) and XSS payloads.
- Automatically records offenders into `security_audit_logs`.

---

## 9. Media Pipeline & Brand Template Engine

### 9.1 Image Format Normalization
- Previously, 63 vendor images with `.jpg` extensions were actually encoded as Google AVIF images, causing Pillow `UnidentifiedImageError` failures.
- `scripts/normalize_product_images.py` converted 100% of the 508 catalog items into progressive standard JPEG (`1080x1080`), with master originals preserved in `assets/products/_originals/`.

### 9.2 Brand Template Architecture (`content_generator.py`)
Generates social media assets with standard corporate design:
- **Pedestal Lighting (`_draw_product_pedestal`):** Radial studio cyan/blue glow anchoring the product.
- **Glassmorphic Stage:** Semi-transparent Gaussian dark stage with cybernetic border.
- **Numbered Feature Chips (`_draw_feature_chips`):** `01`, `02`, `03` glowing counters with technical specs.
- **Dynamic Category Badges:** Color-coded cyber hap badges.
- **Vertical Balancing:** Automatically centers layout when rendering non-product guides or text checklists.

---

## 10. Operations & Developer Cheatsheet (For AI Agents & Engineers)

### 10.1 Service Management Commands
```bash
# Check service status
systemctl --user status pozitron-server.service       # Local dev
sudo systemctl status pozitron                        # Hetzner VPS

# Restart service after code changes
systemctl --user restart pozitron-server.service      # Local dev
sudo systemctl restart pozitron                       # Hetzner VPS

# Stream live server logs
journalctl --user -u pozitron-server.service -f       # Local dev
sudo journalctl -u pozitron -f                        # Hetzner VPS
```

### 10.2 Testing & Quality Assurance Suite
```bash
# Run complete test suite (all 30+ tests must pass)
pytest tests/ -v

# Run specific domain test suites
pytest tests/test_coupon_security_and_quarantine_flow.py -v
pytest tests/test_media_inspector_agent.py -v
pytest tests/test_post_studio_visual_enhancements.py -v
```

### 10.3 Key HTTP API Endpoints
- `GET  /api/health` — System status and database responsiveness.
- `GET  /api/subagents/status` — Status matrix of all 10 subagents.
- `GET  /api/pipeline/graph` — Interactive n8n-style workflow graph nodes and wire definitions.
- `POST /api/supervisor/cycle` — Triggers an immediate 11-step autonomous cycle.
- `GET  /api/media/audit` — Returns latest visual health score and quarantine candidate count.
- `POST /api/media/fix` — Executes autonomous quarantine repair (`{dry_run: false}`).
- `POST /api/coupons/validate` — Validates coupon codes against order total and user identity.
- `GET  /api/products` — Full e-commerce product catalog with specs.

---

## 11. Summary for LLMs Reading This Repository
When generating code or debugging Pozitron:
1. Always preserve the dual-mode integrity: if changes are made to `pozitron.db`, run `export_data.py` to keep static files in sync.
2. Maintain strict coupon validation logic in `coupons.py` (`normalize_email`, identity cross-checks).
3. Do not remove or alter `PRAGMA journal_mode = WAL` in `database.py`.
4. Ensure all new worker subagents are registered in `server.py:/api/pipeline/graph` and `database.py:subagents_config`.
5. Keep all 30 tests in `tests/` green (`pytest tests/ -v`).

---
© 2026 Pozitron Market. Engineered for High-Performance Autonomous FPV Commerce.


## 12. Release notes — 20 October 2026

- The merchant is a sole proprietorship. Public pages use the Pozitron Market brand and the supplied Ankara address/tax details. Personal proprietor names are intentionally omitted at the owner's request; this leaves the official seller-identity prerequisite unresolved for payment-provider approval.
- iyzico and PayTR artwork and prerequisite pages are present. Neither card provider is connected to a verified charge/callback flow. Card collection and simulated approval are disabled; transfer notices remain pending until actual receipt is verified. See `docs/iyzico-hazirlik.md` and `docs/paytr-hazirlik.md`.
- Admin review moderation requires an authenticated administrator. Deleted reviews are recoverable and excluded from public review lists and rating aggregates (`reviews.deleted_at`).
- `product_quality_checks` stores pending/checked/issues state, notes, sources, reviewer and a fingerprint of technical product content. Admin checkboxes and `scripts/product_review.py` share this table. Specification/image changes invalidate old approval; price and stock updates do not. See `docs/URUN_KONTROL_AJANI.md`.
- Product review records in a workstation database do not automatically synchronize with the production database.
- Production deployment must preserve the VPS database, uploads, environment secrets and operational assets. Back up SQLite with its backup API before schema migration; never deploy a workstation database over production.
