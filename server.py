import http.server
import socketserver
import os
import json
import html
import sqlite3
import urllib.parse
import urllib.request
import uuid
import re
import random
import time
import math
import base64
import threading
import hmac
import hashlib
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from database import (
    get_db, init_db, hash_password, get_setting, set_setting, get_all_settings,
    is_subagent_enabled, set_subagent_enabled, get_all_subagents_config
)
from seed_data import seed_database
from export_data import export_static_data
import coupons as coupon_service
import product_quality

# ==============================================================================
# Cyber Security Controls & Cryptographic Authentication
# ==============================================================================
SECRET_KEY = os.environ.get('SECRET_KEY', 'pozitron_secret_prod_key_7792_fpv_market')
ADMIN_API_KEY = os.environ.get('ADMIN_API_KEY', 'pzt_adm_sec_9941a87b32c')

BLOCKED_STATIC_EXTENSIONS = {
    '.db', '.sqlite', '.sqlite3', '.py', '.pyc', '.env', '.yaml', '.yml',
    '.sh', '.service', '.sql', '.log', '.bak', '.toml', '.lock'
}

ALLOWED_STATIC_EXTENSIONS = {
    '', '.html', '.htm', '.css', '.js', '.mjs', '.png', '.jpg', '.jpeg', '.webp',
    '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.xml', '.txt',
    '.tsv', '.json', '.step', '.stp', '.stl', '.obj', '.map', '.mp4', '.webm', '.ogg'
}

BLOCKED_SENSITIVE_FILES = {
    'pozitron.db', 'server.py', 'database.py', 'seed_data.py', 'export_data.py',
    'render.yaml', 'dockerfile', 'procfile', 'requirements.txt', 'orders_log.json',
    'package.json', 'package-lock.json', '.clinerules', 'rule.clinerules',
    'instagram_config.json', 'reddit_history.json', 'admin.html'
}

ALLOWED_UPLOAD_EXTENSIONS = {'.step', '.stp', '.stl', '.obj', '.3mf', '.png', '.jpg', '.jpeg', '.webp'}
MAX_UPLOAD_SIZE = 30 * 1024 * 1024  # 30 MB

def create_auth_token(user_dict: dict) -> str:
    """Generates an unforgeable cryptographic HMAC-SHA256 signed session token."""
    payload = {
        "uid": str(user_dict.get("id", "")),
        "email": str(user_dict.get("email") or "").lower().strip(),
        "role": str(user_dict.get("role", "customer")),
        "ts": int(time.time()),
        "exp": int(time.time()) + (365 * 86400)  # 365 days (1 year) valid - persistent sign-in
    }
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8').rstrip('=')
    sig = hmac.new(SECRET_KEY.encode('utf-8'), raw.encode('utf-8'), hashlib.sha256).hexdigest()
    return f"pztr.{raw}.{sig}"

def verify_auth_token(token: str) -> dict:
    """Verifies HMAC signature and expiration of an authentication token."""
    if not token or not isinstance(token, str):
        return None
    token = token.strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()
    # Direct Master Admin Key verification
    if token == ADMIN_API_KEY:
        return {"uid": "master_admin", "email": "furkaniusprimes@gmail.com", "role": "admin"}
    parts = token.split('.')
    if len(parts) != 3 or parts[0] != 'pztr':
        return None
    raw, sig = parts[1], parts[2]
    expected_sig = hmac.new(SECRET_KEY.encode('utf-8'), raw.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected_sig):
        return None
    try:
        padded = raw + '=' * ((4 - len(raw) % 4) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded.encode('utf-8')).decode('utf-8'))
        if payload.get("exp", 0) < int(time.time()):
            return None  # Expired
        return payload
    except Exception:
        return None

LAST_EMAIL_STATUS = {
    "timestamp": None,
    "to": None,
    "success": None,
    "status": "Initialized"
}

def send_verification_email(to_email: str, code: str) -> bool:
    """Sends a 6-digit password reset verification code to user email."""
    global LAST_EMAIL_STATUS
    smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 587))
    smtp_user = os.environ.get('SMTP_USER', 'noreply@pozitronmarkets.com').strip().lower()
    smtp_password = os.environ.get('SMTP_PASSWORD', 'fugtmwxhotugronp').strip().replace(' ', '')
    smtp_from = os.environ.get('SMTP_FROM', f"Pozitron Market <{smtp_user}>")

    subject = f"[Pozitron Market] Şifre Sıfırlama Doğrulama Kodu: {code}"
    
    text_content = f"""Merhaba,

Pozitron Market hesabınızın şifresini sıfırlamak için talepte bulundunuz.

6 haneli doğrulama kodunuz: {code}

Bu kod 30 dakika boyunca geçerlidir.
Eğer bu talebi siz yapmadıysanız, bu e-postayı güvenle dikkate almayabilirsiniz.

Saygılarımızla,
Pozitron Market Ekibi
https://pozitronmarket.com
"""

    html_content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f1f5f9; margin: 0; padding: 30px 10px;">
  <div style="max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
    <div style="background: linear-gradient(135deg, #0f172a, #1e293b); padding: 24px; text-align: center;">
      <h1 style="color: #38bdf8; margin: 0; font-size: 24px; font-weight: 700; letter-spacing: 0.5px;">POZITRON MARKET</h1>
      <p style="color: #94a3b8; margin: 6px 0 0; font-size: 13px;">FPV &amp; Robotik Mağazası</p>
    </div>
    <div style="padding: 30px 24px; color: #334155; line-height: 1.6;">
      <p style="font-size: 16px; margin: 0 0 16px; font-weight: 600; color: #0f172a;">Merhaba,</p>
      <p style="font-size: 14px; margin: 0 0 20px;">Pozitron Market hesabınızın şifresini yenilemek için bir talep aldık. Aşağıdaki 6 haneli doğrulama kodunu şifre sıfırlama ekranına giriniz:</p>
      <div style="text-align: center; margin: 28px 0;">
        <div style="display: inline-block; background: #f0f9ff; border: 2px dashed #0284c7; border-radius: 10px; padding: 14px 32px; font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #0369a1; font-family: monospace;">
          {code}
        </div>
        <p style="font-size: 12px; color: #64748b; margin-top: 10px;">Bu kod <strong>30 dakika</strong> süreyle geçerlidir.</p>
      </div>
      <p style="font-size: 13px; color: #64748b; margin: 24px 0 0; border-top: 1px solid #f1f5f9; padding-top: 16px;">Eğer şifre sıfırlama talebinde bulunmadıysanız bu e-postayı dikkate almayınız. Hesabınız güvendedir.</p>
    </div>
    <div style="background: #f8fafc; padding: 16px; text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0;">
      &copy; {datetime.now().year} Pozitron Market &bull; <a href="https://pozitronmarket.com" style="color: #0284c7; text-decoration: none;">pozitronmarket.com</a>
    </div>
  </div>
</body>
</html>"""

    # 1. Try Resend HTTP API (Recommended for Cloud / Render without blocked SMTP ports)
    resend_key = os.environ.get('RESEND_API_KEY', '').strip()
    if resend_key:
        try:
            resend_from = os.environ.get('RESEND_FROM', 'Pozitron Market <onboarding@resend.dev>')
            payload = json.dumps({
                "from": resend_from,
                "to": [to_email],
                "subject": subject,
                "html": html_content
            }).encode('utf-8')
            req = urllib.request.Request(
                'https://api.resend.com/emails',
                data=payload,
                headers={
                    'Authorization': f'Bearer {resend_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'PozitronMarket-Cloud/1.0'
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    print(f"[AUTH EMAIL] Verification code sent successfully via Resend API to {to_email}")
                    LAST_EMAIL_STATUS = {
                        "timestamp": datetime.now().isoformat(),
                        "to": to_email,
                        "success": True,
                        "status": "Sent via Resend HTTP API"
                    }
                    return True
        except Exception as re_err:
            print(f"[AUTH EMAIL ERROR] Resend API failed: {re_err}")

    # 2. Try Brevo HTTP API (Alternative HTTP Email API)
    brevo_key = os.environ.get('BREVO_API_KEY', '').strip()
    if brevo_key:
        try:
            payload = json.dumps({
                "sender": {"name": "Pozitron Market", "email": smtp_user or "noreply@pozitronmarkets.com"},
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content
            }).encode('utf-8')
            req = urllib.request.Request(
                'https://api.brevo.com/v3/smtp/email',
                data=payload,
                headers={
                    'api-key': brevo_key,
                    'Content-Type': 'application/json',
                    'User-Agent': 'PozitronMarket-Cloud/1.0'
                },
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if 200 <= resp.status < 300:
                    print(f"[AUTH EMAIL] Verification code sent successfully via Brevo API to {to_email}")
                    LAST_EMAIL_STATUS = {
                        "timestamp": datetime.now().isoformat(),
                        "to": to_email,
                        "success": True,
                        "status": "Sent via Brevo HTTP API"
                    }
                    return True
        except Exception as br_err:
            print(f"[AUTH EMAIL ERROR] Brevo API failed: {br_err}")

    # 3. Try direct SMTP if credentials provided (Default on localhost / VPS)
    if smtp_user and smtp_password:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = smtp_from
            msg['To'] = to_email
            msg['Reply-To'] = smtp_user
            msg['Date'] = formatdate(localtime=True)
            msg['Message-ID'] = make_msgid(domain='pozitronmarkets.com')
            msg['Auto-Submitted'] = 'auto-generated'
            msg['X-Mailer'] = 'PozitronMarket-Mailer/1.0'
            msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server_conn:
                server_conn.ehlo()
                server_conn.starttls()
                server_conn.ehlo()
                server_conn.login(smtp_user, smtp_password)
                server_conn.send_message(msg)
            print(f"[AUTH EMAIL] Verification code email sent successfully via SMTP to {to_email}")
            LAST_EMAIL_STATUS = {
                "timestamp": datetime.now().isoformat(),
                "to": to_email,
                "success": True,
                "status": f"Sent successfully via SMTP ({smtp_user})"
            }
            return True
        except Exception as e:
            err_str = str(e)
            print(f"[AUTH EMAIL ERROR] Failed to send email via SMTP to {to_email}: {err_str}")
            LAST_EMAIL_STATUS = {
                "timestamp": datetime.now().isoformat(),
                "to": to_email,
                "success": False,
                "status": f"SMTP Error: {err_str}"
            }

    # 2. Relay via Google Apps Script Webhook
    gas_url = os.environ.get('GAS_RELAY_URL', 'https://script.google.com/macros/s/AKfycbw_YHCFvOkkq2usjJh4XCMMHWgHy9V_7C5fROFCjrTGw1iGsPy_39o6JXyvlowO9iy5/exec')
    try:
        gas_payload = json.dumps({
            "type": "password_reset",
            "email": to_email,
            "code": code,
            "html_content": html_content
        }).encode('utf-8')
        gas_req = urllib.request.Request(gas_url, data=gas_payload, headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(gas_req, timeout=12) as gas_resp:
            gas_result = gas_resp.read().decode('utf-8')
            if gas_result.strip().startswith('{') and '"status"' in gas_result and '"success"' in gas_result:
                print(f"[AUTH EMAIL] GAS Relay sent successfully for {to_email}")
                LAST_EMAIL_STATUS = {
                    "timestamp": datetime.now().isoformat(),
                    "to": to_email,
                    "success": True,
                    "status": "Sent via GAS Relay"
                }
                return True
            else:
                print(f"[AUTH EMAIL ERROR] GAS Relay returned non-success response for {to_email}: {gas_result[:160]}")
                LAST_EMAIL_STATUS = {
                    "timestamp": datetime.now().isoformat(),
                    "to": to_email,
                    "success": False,
                    "status": f"GAS Relay Error: {gas_result[:100]}"
                }
    except Exception as gas_e:
        print(f"[AUTH EMAIL] GAS Relay notice for {to_email}: {gas_e}")

    print(f"[AUTH EMAIL NOTICE] Email delivery not configured. Reset code for {to_email}: {code}")
    LAST_EMAIL_STATUS = {
        "timestamp": datetime.now().isoformat(),
        "to": to_email,
        "success": False,
        "status": "Delivery failed: SMTP and fallback unavailable"
    }
    return False

# Ensure database tables and initial data exist (Crucial for fresh cloud deployments like Render)
def ensure_database_ready():
    try:
        init_db()
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM products")
        count = cursor.fetchone()[0]
        conn.close()
        if count == 0:
            print("[INIT] Database empty on fresh deployment. Seeding initial products and categories...")
            seed_database()
    except Exception as e:
        print(f"[INIT] Database setup notice: {e}")

ensure_database_ready()

from instagram_agent.agent import InstagramPRAgent
from instagram_agent.scheduler import InstagramScheduler
from instagram_agent.chrome_session import extract_chrome_instagram_cookies
from instagram_agent.engagement import InstagramEngagementEngine
from instagram_agent.db import get_instagram_post_by_id
from reddit_agent.agent import RedditDroneAgent
from reddit_agent.scheduler import RedditScheduler
from orchestrator import (
    LeadSupervisorAgent, SupervisorScheduler,
    PriceIntelligenceAgent, TelemetryAgent, TechnicalSeoAgent,
    GlobalTrendHunterAgent, QASentinelAgent, QAScheduler
)

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Instagram PR Agent & Scheduler Instance
instagram_pr_agent = InstagramPRAgent()
instagram_pr_scheduler = InstagramScheduler(instagram_pr_agent)

# Reddit Drone Agent & Scheduler Instance
reddit_drone_agent = RedditDroneAgent()
reddit_drone_scheduler = RedditScheduler(reddit_drone_agent)

# Lead Supervisor Agent & 2-Hour Orchestration Scheduler
lead_supervisor_agent = LeadSupervisorAgent()
supervisor_scheduler = SupervisorScheduler(lead_supervisor_agent)

# Subagent 7: PR Health, Diagnostics & QA Sentinel Agent
qa_agent = QASentinelAgent()
qa_scheduler = QAScheduler(qa_agent)

# Subagent 9: Cyber Security Sentinel
cyber_security_agent = lead_supervisor_agent.security_agent

# Subagent 10: Product Media & Content Inspector
media_inspector_agent = lead_supervisor_agent.media_agent

# Autonomous Thread Watchdog & Cloud Market Inventory Sync Loop
def start_thread_watchdog():
    def watchdog_loop():
        time.sleep(15)
        while True:
            try:
                # 1. Resuscitate terminated scheduler threads (strictly respecting subagents_config)
                if instagram_pr_agent.get_status().get('is_autonomous_enabled') and is_subagent_enabled('subagent_1_instagram'):
                    if not instagram_pr_scheduler.is_running():
                        print("[Watchdog] Reviving InstagramPRScheduler thread...")
                        instagram_pr_scheduler.start()
                elif not is_subagent_enabled('subagent_1_instagram') and instagram_pr_scheduler.is_running():
                    instagram_pr_scheduler.stop()

                if reddit_drone_agent.get_status().get('is_autonomous_enabled') and is_subagent_enabled('subagent_2_reddit'):
                    if not reddit_drone_scheduler.is_running():
                        print("[Watchdog] Reviving RedditDroneScheduler thread...")
                        reddit_drone_scheduler.start()
                elif not is_subagent_enabled('subagent_2_reddit') and reddit_drone_scheduler.is_running():
                    print("[Watchdog] Reddit bot is disabled by user, stopping scheduler...")
                    reddit_drone_scheduler.stop()

                if lead_supervisor_agent.get_status().get('is_autonomous_enabled') and is_subagent_enabled('lead_supervisor'):
                    if not supervisor_scheduler.is_running():
                        print("[Watchdog] Reviving LeadSupervisorScheduler thread...")
                        supervisor_scheduler.start()
                elif not is_subagent_enabled('lead_supervisor') and supervisor_scheduler.is_running():
                    supervisor_scheduler.stop()

                if qa_agent.get_status().get('is_autonomous_enabled') and is_subagent_enabled('subagent_7_qa'):
                    if not qa_scheduler.is_running():
                        print("[Watchdog] Reviving QAScheduler thread...")
                        qa_scheduler.start()
                elif not is_subagent_enabled('subagent_7_qa') and qa_scheduler.is_running():
                    qa_scheduler.stop()

                # 1b. Auto-expire time-limited coupons (works even if nobody visits the site)
                try:
                    expired = coupon_service.expire_coupons()
                    if expired:
                        print(f"[Watchdog] {expired} kupon suresi doldugu icin otomatik devre disi birakildi.")
                except Exception as coupon_err:
                    print(f"[Watchdog] Kupon suresi kontrolu hatasi: {coupon_err}")

                # 2. Periodic cloud market inventory sync (git pull --rebase)
                try:
                    import subprocess
                    sync_proc = subprocess.run(
                        ["git", "pull", "--rebase", "origin", "main"],
                        cwd=BASE_DIR,
                        capture_output=True,
                        text=True,
                        timeout=25
                    )
                    if sync_proc.returncode == 0 and "Already up to date." not in sync_proc.stdout:
                        print("[Watchdog] Cloud market orders pulled:", sync_proc.stdout.strip())
                        prod_json_p = os.path.join(BASE_DIR, "data", "products.json")
                        if os.path.exists(prod_json_p):
                            with open(prod_json_p, "r", encoding="utf-8") as pf:
                                prods = json.load(pf)
                            conn_w = get_db()
                            cur_w = conn_w.cursor()
                            for prd in prods:
                                cur_w.execute("UPDATE products SET stock = ? WHERE id = ?", (prd.get("stock", 0), prd.get("id")))
                            conn_w.commit()
                            conn_w.close()
                except Exception:
                    pass

            except Exception as we:
                print(f"[Watchdog] Loop notice: {we}")

            time.sleep(60)

    # Expire any time-limited coupons left over from before the restart.
    try:
        coupon_service.expire_coupons()
    except Exception:
        pass

    t = threading.Thread(target=watchdog_loop, name="SystemdThreadWatchdog", daemon=True)
    t.start()

def start_all_schedulers():
    if instagram_pr_agent.config.get('is_autonomous_enabled') and is_subagent_enabled('subagent_1_instagram'):
        instagram_pr_scheduler.start()
    if reddit_drone_agent.config.get('is_autonomous_enabled') and is_subagent_enabled('subagent_2_reddit'):
        reddit_drone_scheduler.start()
    if lead_supervisor_agent.get_status().get('is_autonomous_enabled') and is_subagent_enabled('lead_supervisor'):
        supervisor_scheduler.start()
    if qa_agent.get_status().get('is_autonomous_enabled') and is_subagent_enabled('subagent_7_qa'):
        qa_scheduler.start()
    start_thread_watchdog()

# Security Lockout Configuration: 3 failed attempts => 30-minute cooldown
LOGIN_ATTEMPTS_LOCK = threading.Lock()
LOGIN_ATTEMPTS = {}  # key: identifier -> {"count": int, "locked_until": float, "last_attempt": float}
MAX_FAILED_ATTEMPTS = 3
LOCKOUT_DURATION_SECONDS = 30 * 60  # 30 minutes

def check_login_rate_limit(identifier: str):
    """Returns (is_locked, remaining_seconds, remaining_minutes, attempts_left)"""
    with LOGIN_ATTEMPTS_LOCK:
        now = time.time()
        record = LOGIN_ATTEMPTS.get(identifier)
        if not record:
            return False, 0, 0, MAX_FAILED_ATTEMPTS
        
        # Check if currently locked
        if record.get('locked_until', 0) > now:
            rem_sec = int(record['locked_until'] - now)
            rem_min = max(1, int(math.ceil(rem_sec / 60)))
            return True, rem_sec, rem_min, 0
        
        # If lock has expired, reset record
        if record.get('locked_until', 0) > 0 and record['locked_until'] <= now:
            del LOGIN_ATTEMPTS[identifier]
            return False, 0, 0, MAX_FAILED_ATTEMPTS
            
        count = record.get('count', 0)
        attempts_left = max(0, MAX_FAILED_ATTEMPTS - count)
        return False, 0, 0, attempts_left

def record_failed_login(identifier: str):
    """Records a failure. Returns (is_now_locked, remaining_seconds, remaining_minutes, attempts_left)"""
    with LOGIN_ATTEMPTS_LOCK:
        now = time.time()
        record = LOGIN_ATTEMPTS.get(identifier, {"count": 0, "locked_until": 0, "last_attempt": now})
        record['count'] += 1
        record['last_attempt'] = now
        
        if record['count'] >= MAX_FAILED_ATTEMPTS:
            record['locked_until'] = now + LOCKOUT_DURATION_SECONDS
            LOGIN_ATTEMPTS[identifier] = record
            return True, LOCKOUT_DURATION_SECONDS, 30, 0
        else:
            LOGIN_ATTEMPTS[identifier] = record
            attempts_left = MAX_FAILED_ATTEMPTS - record['count']
            return False, 0, 0, attempts_left

def clear_login_attempts(identifier: str):
    with LOGIN_ATTEMPTS_LOCK:
        if identifier in LOGIN_ATTEMPTS:
            del LOGIN_ATTEMPTS[identifier]

def luhn_validate(card_number: str) -> bool:
    digits = [int(c) for c in card_number if c.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    # Allow standard demo / test cards instantly
    clean = "".join(str(d) for d in digits)
    if clean.startswith("4242") or clean.startswith("5555") or clean.startswith("9792") or clean == "4532012345678910":
        return True
    checksum = 0
    reverse_digits = digits[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += digit
    return checksum % 10 == 0

class PozitronRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def get_current_user(self):
        """Extracts and verifies caller identity from Authorization header or API key."""
        auth_header = self.headers.get('Authorization', '')
        token = auth_header
        if not token:
            token = self.headers.get('X-Admin-Key', '')
        if not token:
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            token = qs.get('token', [None])[0] or qs.get('api_key', [None])[0] or qs.get('admin_key', [None])[0]

        user = verify_auth_token(token)
        if user:
            return user

        # Local development convenience fallback ONLY if strictly running locally (not in cloud or proxied)
        is_cloud = bool(os.environ.get('RENDER') or os.environ.get('PORT'))
        is_proxied = bool(self.headers.get('X-Forwarded-For') or self.headers.get('CF-Connecting-IP'))
        client_ip = self.client_address[0] if self.client_address else ""
        if not is_cloud and not is_proxied and client_ip in ('127.0.0.1', 'localhost', '::1') and os.environ.get('POZITRON_ENV') != 'production':
            return {"uid": "local_dev", "email": "furkaniusprimes@gmail.com", "role": "admin"}

        return None

    def require_admin(self) -> bool:
        """Enforces administrative authentication on protected endpoints."""
        user = self.get_current_user()
        if not user or user.get('role') != 'admin':
            self.send_json(401, {
                "error": "Yetkisiz erişim. Yönetici kimlik doğrulaması (Bearer Token veya Admin API Key) gereklidir.",
                "auth_required": True
            })
            return False
        return True

    def is_static_path_allowed(self, raw_path: str) -> bool:
        """Whitelists public static file extensions and strictly blocks source/DB leaks."""
        clean = urllib.parse.unquote(raw_path.split('?')[0].split('#')[0]).lstrip('/')
        if not clean:
            return True

        parts = clean.replace('\\', '/').split('/')
        for p in parts:
            # Block dotfiles (.git, .env, .nojekyll)
            if p.startswith('.'):
                return False
            # Block sensitive named files
            if p.lower() in BLOCKED_SENSITIVE_FILES:
                return False

        base_name = os.path.basename(clean).lower()
        if base_name in BLOCKED_SENSITIVE_FILES:
            return False

        # Path traversal guard
        full_path = os.path.realpath(os.path.join(BASE_DIR, clean))
        if not (full_path == BASE_DIR or full_path.startswith(BASE_DIR + os.sep)):
            return False

        # If it is a product route or matches an existing html page, its target is .html
        clean_rstrip = clean.rstrip('/')
        if clean_rstrip.startswith('products/'):
            return True

        candidate_html = os.path.realpath(os.path.join(BASE_DIR, clean_rstrip + '.html'))
        if os.path.isfile(candidate_html):
            return True

        if os.path.isfile(full_path):
            ext = os.path.splitext(full_path)[1].lower()
            if ext in BLOCKED_STATIC_EXTENSIONS:
                return False
            if ext and ext not in ALLOWED_STATIC_EXTENSIONS:
                return False
            return True

        ext = os.path.splitext(clean_rstrip)[1].lower()
        if ext in BLOCKED_STATIC_EXTENSIONS:
            return False

        if ext and ext not in ALLOWED_STATIC_EXTENSIONS:
            return False

        return True

    def send_json(self, status_code, data):
        response_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Admin-Key')
        self.end_headers()
        self.wfile.write(response_bytes)

    def end_headers(self):
        if self.path.endswith('.js') or self.path.endswith('.css') or self.path.endswith('.html') or '/api/' in self.path:
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Admin-Key')
        self.end_headers()

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path.startswith('/api/'):
            addr_del_match = re.match(r'^/api/user/addresses/(.+)$', path)
            if addr_del_match:
                addr_id = urllib.parse.unquote(addr_del_match.group(1)).strip()
                conn = get_db()
                cur = conn.cursor()
                cur.execute("DELETE FROM user_addresses WHERE id = ?", (addr_id,))
                conn.commit()
                conn.close()
                self.send_json(200, {"success": True, "deleted_id": addr_id})
                return

            try:
                self.handle_api_delete(path)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json(500, {"error": str(e)})
            return

        self.send_json(404, {"error": "Endpoint not found"})

    def handle_api_delete(self, path):
        if not self.require_admin():
            return

        conn = get_db()
        cursor = conn.cursor()

        prod_match = re.match(r'^/api/admin/products/(.+)$', path)
        if not prod_match:
            prod_match = re.match(r'^/api/products/(.+)$', path)

        if prod_match:
            prod_id = urllib.parse.unquote(prod_match.group(1)).strip()
            cursor.execute("SELECT category_id, slug FROM products WHERE id = ? OR slug = ? OR sku = ?", (prod_id, prod_id, prod_id))
            row = cursor.fetchone()
            if not row:
                conn.close()
                self.send_json(404, {"error": "Product not found"})
                return

            cat_id = row[0]
            del_slug = row[1]
            cursor.execute("DELETE FROM products WHERE id = ? OR slug = ? OR sku = ?", (prod_id, prod_id, prod_id))
            cursor.execute("UPDATE categories SET item_count = MAX(0, item_count - 1) WHERE id = ?", (cat_id,))
            conn.commit()
            conn.close()

            if del_slug:
                del_html = os.path.join(BASE_DIR, 'products', f"{del_slug}.html")
                if os.path.isfile(del_html):
                    try:
                        os.remove(del_html)
                    except Exception:
                        pass

            self.send_json(200, {"success": True, "deleted_id": prod_id})
            return

        # Instagram PR: Delete post
        if path.startswith('/api/instagram/posts/'):
            post_id = path[len('/api/instagram/posts/'):]
            success = instagram_pr_agent.delete_post(post_id)
            conn.close()
            self.send_json(200, {"success": success, "deleted_id": post_id})
            return

        # Reddit Drone Bot: Delete interaction
        if path.startswith('/api/reddit/interactions/'):
            interaction_id = path[len('/api/reddit/interactions/'):]
            success = reddit_drone_agent.delete_reply(interaction_id)
            conn.close()
            self.send_json(200, {"success": success, "deleted_id": interaction_id})
            return

        conn.close()
        self.send_json(404, {"error": "Route not found"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # SEO Endpoints
        if path == '/robots.txt':
            robots_txt = "User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /bots\nSitemap: https://pozitronmarket.com/sitemap.xml\n"
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(robots_txt.encode('utf-8'))))
            self.end_headers()
            self.wfile.write(robots_txt.encode('utf-8'))
            return

        if path == '/sitemap.xml':
            self.handle_sitemap_xml()
            return

        if path.startswith('/api/'):
            try:
                self.handle_api_get(path, query)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Serve uploaded files from uploads/ directory with strict traversal & whitelist checks
        if path.startswith('/uploads/'):
            requested_rel = urllib.parse.unquote(path[len('/uploads/'):]).lstrip('/\\')
            uploads_dir = os.path.realpath(os.path.join(BASE_DIR, 'uploads'))
            file_path = os.path.realpath(os.path.join(uploads_dir, requested_rel))

            # Anti-Path Traversal Check
            if not file_path.startswith(uploads_dir + os.sep):
                self.send_json(403, {"error": "Access denied"})
                return

            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ALLOWED_UPLOAD_EXTENSIONS:
                self.send_json(403, {"error": "File type not permitted"})
                return

            if os.path.exists(file_path) and os.path.isfile(file_path):
                self.send_response(200)
                content_type = 'application/octet-stream'
                if ext in ('.step', '.stp'):
                    content_type = 'text/plain; charset=utf-8'
                elif ext == '.stl':
                    content_type = 'application/octet-stream'
                elif ext == '.obj':
                    content_type = 'text/plain; charset=utf-8'
                elif ext == '.png':
                    content_type = 'image/png'
                elif ext in ('.jpg', '.jpeg'):
                    content_type = 'image/jpeg'
                elif ext == '.webp':
                    content_type = 'image/webp'
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(os.path.getsize(file_path)))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_json(404, {"error": "Uploaded file not found"})
                return

        # Clean URL 301 Redirection: Redirect legacy .html URLs to modern clean URLs
        if path.endswith('.html'):
            target_url = None
            if path == '/index.html':
                target_url = '/' + (('?' + parsed.query) if parsed.query else '')
            elif path == '/rehber.html':
                if query.get('slug'):
                    target_url = f"/rehber/{urllib.parse.quote(query['slug'][0])}"
                else:
                    target_url = '/rehber' + (('?' + parsed.query) if parsed.query else '')
            elif path.startswith('/products/') and path.endswith('.html'):
                prod_slug = path[len('/products/'):-5]
                target_url = f"/products/{prod_slug}" + (('?' + parsed.query) if parsed.query else '')
            else:
                clean_name = path[:-5]
                candidate_file = os.path.join(BASE_DIR, clean_name.lstrip('/') + '.html')
                if os.path.isfile(candidate_file):
                    target_url = clean_name + (('?' + parsed.query) if parsed.query else '')

            if target_url:
                self.send_response(301)
                self.send_header('Location', target_url)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'public, max-age=31536000')
                self.end_headers()
                return

        if path == '/bots':
            file_path = os.path.join(BASE_DIR, 'bots.html')
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return

        # Technical SEO Guides & Engineering Blog (/rehber, /rehber/<slug>)
        if path == '/rehber' or path.startswith('/rehber/'):
            file_path = os.path.join(BASE_DIR, 'rehber.html')
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
                return

        # Local /admin has been removed. Forward all requests to the online admin panel.
        if path in ('/admin', '/admin.html'):
            self.send_response(302)
            self.send_header('Location', 'https://pozitronmarket.com/admin')
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            self.wfile.write(b'<!DOCTYPE html><html><head><meta http-equiv="refresh" content="0;url=https://pozitronmarket.com/admin"><title>Redirecting to Pozitron Online Admin</title></head><body><p>Yonetim paneli online sunucudadir: <a href="https://pozitronmarket.com/admin">https://pozitronmarket.com/admin</a></p></body></html>')
            return

        # Security: Enforce static file whitelist and block sensitive files (.db, .py, etc.)
        if not self.is_static_path_allowed(self.path):
            self.send_json(404, {"error": "File not found"})
            return

        unquoted_path = urllib.parse.unquote(path).rstrip('/')
        clean_rel = unquoted_path.lstrip('/')

        # Handle product pages (/products/<slug_or_id>)
        if clean_rel.startswith('products/'):
            slug_or_id = clean_rel[len('products/'):].rstrip('/')
            if slug_or_id.endswith('.html'):
                slug_or_id = slug_or_id[:-5]

            # 1. Check data/slug_aliases.json for canonical redirection
            alias_map_path = os.path.join(BASE_DIR, 'data', 'slug_aliases.json')
            alias_target = None
            if os.path.isfile(alias_map_path):
                try:
                    with open(alias_map_path, 'r', encoding='utf-8') as af:
                        alias_data = json.load(af)
                        alias_target = alias_data.get(slug_or_id)
                        if not alias_target:
                            # Try base slug without trailing numeric suffix (e.g. ...-838)
                            base_lookup = re.sub(r'-\d+$', '', slug_or_id)
                            alias_target = alias_data.get(base_lookup)
                except Exception:
                    pass

            if alias_target and alias_target != slug_or_id:
                target_url = f"/products/{alias_target}" + (('?' + parsed.query) if parsed.query else '')
                self.send_response(301)
                self.send_header('Location', target_url)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'public, max-age=31536000')
                self.end_headers()
                return

            target_html = os.path.join(BASE_DIR, 'products', f"{slug_or_id}.html")
            if not os.path.isfile(target_html):
                try:
                    conn = get_db()
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM products WHERE slug = ? OR id = ? OR sku = ?", (slug_or_id, slug_or_id, slug_or_id))
                    p_row = cursor.fetchone()
                    if not p_row:
                        # Try matching base slug without trailing number
                        base_slug = re.sub(r'-\d+$', '', slug_or_id)
                        if base_slug != slug_or_id:
                            cursor.execute("SELECT * FROM products WHERE slug LIKE ? ORDER BY id ASC LIMIT 1", (f"{base_slug}%",))
                            p_row = cursor.fetchone()
                    conn.close()

                    if p_row:
                        p_dict = dict(p_row)
                        real_slug = p_dict.get('slug')
                        if real_slug and real_slug != slug_or_id:
                            # Redirect to canonical slug
                            target_url = f"/products/{real_slug}" + (('?' + parsed.query) if parsed.query else '')
                            self.send_response(301)
                            self.send_header('Location', target_url)
                            self.send_header('Content-Type', 'text/html; charset=utf-8')
                            self.send_header('Cache-Control', 'public, max-age=31536000')
                            self.end_headers()
                            return
                        elif real_slug:
                            real_html = os.path.join(BASE_DIR, 'products', f"{real_slug}.html")
                            if os.path.isfile(real_html):
                                target_html = real_html
                            else:
                                try:
                                    from generate_product_pages import generate_product_page
                                    cat_dict = {"id": p_dict.get('category_id', 'motors')}
                                    gen_html = generate_product_page(p_dict, cat_dict, [], [p_dict], {cat_dict["id"]: [p_dict]})
                                    with open(real_html, 'w', encoding='utf-8') as pf:
                                        pf.write(gen_html)
                                    target_html = real_html
                                except Exception as ge:
                                    print(f"Error auto-generating product page: {ge}")
                except Exception as e:
                    print(f"Product route DB lookup error: {e}")

            if os.path.isfile(target_html):
                with open(target_html, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                # 404: Try serving 404.html with smart client resolver if available
                not_found_file = os.path.join(BASE_DIR, '404.html')
                if os.path.isfile(not_found_file):
                    with open(not_found_file, 'rb') as f:
                        content = f.read()
                    self.send_response(404)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', str(len(content)))
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(content)
                    return
                self.send_json(404, {"error": "Product not found"})
                return

        # Serve frontend static files
        if path == '/' or path == '/index.html':
            self.path = '/index.html'
        else:
            # Check if an extensionless path matches an existing .html file (e.g. /drone-toplama-sihirbazi)
            candidate_html = os.path.join(BASE_DIR, clean_rel + '.html')
            if os.path.isfile(candidate_html):
                with open(candidate_html, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(content)
                return

        return super().do_GET()

    def do_HEAD(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Clean URL 301 Redirection: HEAD requests for .html URLs
        if path.endswith('.html'):
            target_url = None
            if path == '/index.html':
                target_url = '/' + (('?' + parsed.query) if parsed.query else '')
            elif path == '/rehber.html':
                if 'slug' in parsed.query:
                    q_dict = urllib.parse.parse_qs(parsed.query)
                    if q_dict.get('slug'):
                        target_url = f"/rehber/{urllib.parse.quote(q_dict['slug'][0])}"
                    else:
                        target_url = '/rehber'
                else:
                    target_url = '/rehber'
            elif path.startswith('/products/') and path.endswith('.html'):
                prod_slug = path[len('/products/'):-5]
                target_url = f"/products/{prod_slug}"
            else:
                clean_name = path[:-5]
                candidate_file = os.path.join(BASE_DIR, clean_name.lstrip('/') + '.html')
                if os.path.isfile(candidate_file):
                    target_url = clean_name

            if target_url:
                self.send_response(301)
                self.send_header('Location', target_url)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                return

        if path == '/api/health':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            return

        if path in ('/admin', '/admin.html'):
            self.send_response(302)
            self.send_header('Location', 'https://pozitronmarket.com/admin')
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.end_headers()
            return

        if not self.is_static_path_allowed(self.path):
            self.send_response(404)
            self.end_headers()
            return

        if path == '/bots' or path == '/rehber' or path.startswith('/rehber/'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            return
        unquoted_path = urllib.parse.unquote(path).rstrip('/')
        clean_rel = unquoted_path.lstrip('/')
        if clean_rel.startswith('products/'):
            slug_or_id = clean_rel[len('products/'):].rstrip('/')
            if slug_or_id.endswith('.html'):
                slug_or_id = slug_or_id[:-5]

            # 1. Check data/slug_aliases.json for canonical redirection
            alias_map_path = os.path.join(BASE_DIR, 'data', 'slug_aliases.json')
            alias_target = None
            if os.path.isfile(alias_map_path):
                try:
                    with open(alias_map_path, 'r', encoding='utf-8') as af:
                        alias_data = json.load(af)
                        alias_target = alias_data.get(slug_or_id)
                        if not alias_target:
                            base_lookup = re.sub(r'-\d+$', '', slug_or_id)
                            alias_target = alias_data.get(base_lookup)
                except Exception:
                    pass

            if alias_target and alias_target != slug_or_id:
                target_url = f"/products/{alias_target}"
                self.send_response(301)
                self.send_header('Location', target_url)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Cache-Control', 'public, max-age=31536000')
                self.end_headers()
                return

            target_html = os.path.join(BASE_DIR, 'products', f"{slug_or_id}.html")
            if os.path.isfile(target_html):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(os.path.getsize(target_html)))
                self.end_headers()
                return
            try:
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("SELECT slug FROM products WHERE slug = ? OR id = ? OR sku = ?", (slug_or_id, slug_or_id, slug_or_id))
                row = cursor.fetchone()
                conn.close()
                if row and row[0]:
                    real_html = os.path.join(BASE_DIR, 'products', f"{row[0]}.html")
                    if os.path.isfile(real_html):
                        self.send_response(200)
                        self.send_header('Content-Type', 'text/html; charset=utf-8')
                        self.send_header('Content-Length', str(os.path.getsize(real_html)))
                        self.end_headers()
                        return
            except Exception:
                pass
            self.send_response(404)
            self.end_headers()
            return

        candidate_html = os.path.join(BASE_DIR, clean_rel + '.html')
        if os.path.isfile(candidate_html):
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(os.path.getsize(candidate_html)))
            self.end_headers()
            return

        return super().do_HEAD()

    def handle_sitemap_xml(self):
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT slug, id, category_id, created_at FROM products ORDER BY id ASC")
        products = cursor.fetchall()
        cursor.execute("SELECT id FROM categories")
        categories = cursor.fetchall()
        cursor.execute("SELECT slug, created_at FROM seo_articles ORDER BY id DESC")
        articles = cursor.fetchall()
        conn.close()

        import html as html_lib
        xml_lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            '  <url>',
            '    <loc>https://pozitronmarket.com/</loc>',
            '    <changefreq>daily</changefreq>',
            '    <priority>1.0</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/drone-toplama-sihirbazi</loc>',
            '    <changefreq>weekly</changefreq>',
            '    <priority>0.95</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/3d-baski-studio</loc>',
            '    <changefreq>weekly</changefreq>',
            '    <priority>0.95</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/rehber</loc>',
            '    <changefreq>daily</changefreq>',
            '    <priority>0.95</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/iade-politikasi</loc>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.7</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/kargo-ve-teslimat</loc>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.7</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/mesafeli-satis-sozlesmesi</loc>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.7</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/gizlilik-politikasi</loc>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.7</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/hakkimizda</loc>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.8</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/iletisim</loc>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.8</priority>',
            '  </url>',
            '  <url>',
            '    <loc>https://pozitronmarket.com/return-policy</loc>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.6</priority>',
            '  </url>'
        ]

        # Category URLs
        for cat in categories:
            xml_lines.extend([
                '  <url>',
                f'    <loc>https://pozitronmarket.com/#category={html_lib.escape(cat[0])}</loc>',
                '    <changefreq>weekly</changefreq>',
                '    <priority>0.8</priority>',
                '  </url>'
            ])

        # 500 Product URLs
        for p in products:
            slug = p[0] or p[1]
            lastmod = p[3].split('T')[0] if p[3] and 'T' in p[3] else datetime.now().strftime('%Y-%m-%d')
            xml_lines.extend([
                '  <url>',
                f'    <loc>https://pozitronmarket.com/products/{html_lib.escape(slug)}</loc>',
                f'    <lastmod>{lastmod}</lastmod>',
                '    <changefreq>weekly</changefreq>',
                '    <priority>0.9</priority>',
                '  </url>'
            ])

        # Technical SEO Articles
        for a in articles:
            slug = a[0]
            lastmod = a[1].split('T')[0] if a[1] and 'T' in a[1] else datetime.now().strftime('%Y-%m-%d')
            xml_lines.extend([
                '  <url>',
                f'    <loc>https://pozitronmarket.com/rehber/{html_lib.escape(slug)}</loc>',
                f'    <lastmod>{lastmod}</lastmod>',
                '    <changefreq>weekly</changefreq>',
                '    <priority>0.8</priority>',
                '  </url>'
            ])

        xml_lines.append('</urlset>')
        xml_content = "\n".join(xml_lines)
        xml_bytes = xml_content.encode('utf-8')

        self.send_response(200)
        self.send_header('Content-Type', 'application/xml; charset=utf-8')
        self.send_header('Content-Length', str(len(xml_bytes)))
        self.end_headers()
        self.wfile.write(xml_bytes)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Telemetry ingestion endpoint (Subagent 3: http://localhost:8000/bots)
        if path in ('/bots', '/bots.html', '/api/telemetry'):
            content_length = int(self.headers.get('Content-Length', 0))
            body_raw = self.rfile.read(content_length) if content_length > 0 else b'{}'
            try:
                data = json.loads(body_raw.decode('utf-8'))
            except Exception:
                data = {}
            lead_supervisor_agent.telemetry_agent._save_to_db(data)
            self.send_json(200, {
                "success": True,
                "message": "Telemetry payload received successfully",
                "timestamp": data.get("timestamp")
            })
            return

        if path == '/api/upload-3d' or path == '/api/upload':
            try:
                self.handle_file_upload(path)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json(500, {"error": f"Dosya yükleme hatası: {str(e)}"})
            return

        if path.startswith('/api/'):
            content_length = int(self.headers.get('Content-Length', 0))
            body_raw = self.rfile.read(content_length) if content_length > 0 else b'{}'
            try:
                data = json.loads(body_raw.decode('utf-8'))
            except Exception:
                data = {}

            try:
                self.handle_api_post(path, data)
            except Exception as e:
                import traceback
                traceback.print_exc()
                self.send_json(500, {"error": str(e)})
            return

        self.send_json(404, {"error": "Endpoint not found"})

    def do_PUT(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path in ('/bots', '/bots.html', '/api/telemetry'):
            content_length = int(self.headers.get('Content-Length', 0))
            body_raw = self.rfile.read(content_length) if content_length > 0 else b'{}'
            try:
                data = json.loads(body_raw.decode('utf-8'))
            except Exception:
                data = {}
            lead_supervisor_agent.telemetry_agent._save_to_db(data)
            self.send_json(200, {
                "success": True,
                "message": "Telemetry payload received successfully (PUT)",
                "timestamp": data.get("timestamp")
            })
            return
        self.send_json(404, {"error": "Endpoint not found"})

    def handle_file_upload(self, path):
        uploads_dir = os.path.realpath(os.path.join(BASE_DIR, 'uploads'))
        os.makedirs(uploads_dir, exist_ok=True)

        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > MAX_UPLOAD_SIZE:
            self.send_json(413, {"error": "Dosya boyutu çok büyük (Maksimum 30 MB izin verilir)."})
            return

        content_type = self.headers.get('Content-Type', '')

        filename = None
        file_bytes = b''

        if 'multipart/form-data' in content_type:
            boundary = content_type.split("boundary=")[-1].strip()
            raw_data = self.rfile.read(content_length)
            boundary_bytes = boundary.encode('utf-8')
            parts = raw_data.split(b'--' + boundary_bytes)
            for part in parts:
                if b'filename="' in part:
                    header_part, _, body = part.partition(b'\r\n\r\n')
                    body = body.rstrip(b'\r\n-')
                    header_str = header_part.decode('utf-8', errors='ignore')
                    fn_match = re.search(r'filename="([^"]+)"', header_str)
                    if fn_match:
                        filename = os.path.basename(fn_match.group(1))
                        file_bytes = body
                        break
        else:
            raw_data = self.rfile.read(content_length)
            try:
                json_data = json.loads(raw_data.decode('utf-8'))
                filename = json_data.get('filename', 'model.step')
                content = json_data.get('content', '')
                if json_data.get('is_base64'):
                    file_bytes = base64.b64decode(content)
                else:
                    file_bytes = content.encode('utf-8')
            except Exception:
                filename = self.headers.get('X-Filename', 'uploaded_model.step')
                file_bytes = raw_data

        if not filename:
            filename = f"model_{int(time.time())}.step"

        # Security: Extension Whitelist validation
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_UPLOAD_EXTENSIONS:
            self.send_json(400, {
                "error": "Desteklenmeyen dosya türü. Yalnızca 3D model (.step, .stp, .stl, .obj) veya görsel (.png, .jpg, .jpeg, .webp) yüklenebilir."
            })
            return

        # Security: Re-generate safe filename with UUID to prevent collision & traversal
        clean_stem = "".join(c for c in os.path.splitext(filename)[0] if c.isalnum() or c in "_-")[:32] or "upload"
        safe_filename = f"{clean_stem}_{uuid.uuid4().hex[:8]}{ext}"

        dest_path = os.path.realpath(os.path.join(uploads_dir, safe_filename))
        if not dest_path.startswith(uploads_dir + os.sep):
            self.send_json(400, {"error": "Geçersiz dosya yolu."})
            return

        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        file_size = len(file_bytes)
        print(f"[Upload] Saved safe 3D/image asset: {dest_path} ({file_size} bytes)")

        self.send_json(200, {
            "success": True,
            "filename": safe_filename,
            "url": f"/uploads/{urllib.parse.quote(safe_filename)}",
            "size": file_size,
            "message": f"'{safe_filename}' dosyası başarıyla yüklendi! ({file_size} bayt)"
        })

    def handle_api_get(self, path, query):
        # Health Check Endpoint (Cloud / Render / Railway)
        if path == '/api/health':
            self.send_json(200, {
                "status": "healthy",
                "service": "pozitron-cloud-api",
                "version": "2026.09.20.2",
                "timestamp": datetime.now().isoformat()
            })
            return

        # Email Delivery Diagnostic Endpoint
        if path == '/api/auth/email-status':
            self.send_json(200, LAST_EMAIL_STATUS)
            return

        # Public: current limited-time deal (site banner)
        if path == '/api/coupons/active':
            try:
                deal = coupon_service.get_active_deal()
            except Exception:
                deal = None
            if deal:
                self.send_json(200, {
                    "active": True,
                    "code": deal.get('code'),
                    "discount_type": deal.get('discount_type'),
                    "discount_value": deal.get('discount_value'),
                    "min_order_try": deal.get('min_order_try'),
                    "description_tr": deal.get('description_tr'),
                    "expires_at": deal.get('expires_at'),
                })
            else:
                self.send_json(200, {"active": False})
            return

        # Settings & Currency Rate Endpoints
        if path == '/api/settings':
            settings = get_all_settings()
            settings['bank_owner'] = ''
            self.send_json(200, settings)
            return

        if path in ('/api/currency-rate', '/api/currency'):
            rate = get_setting('usd_rate', 50.0)
            self.send_json(200, {
                "usd_rate": rate,
                "currency": "TRY",
                "base": "USD"
            })
            return

        # Security: All admin and agent automation endpoints require verified admin credentials
        if (path.startswith('/api/admin/') or 
            path in ('/api/instagram/config', '/api/instagram/chrome-session', '/api/reddit/config', '/api/lead-supervisor/config', '/api/qa-agent/config')):
            if not self.require_admin():
                return

        # Instagram PR: Status
        if path == '/api/instagram/status':
            self.send_json(200, instagram_pr_agent.get_status())
            return

        # Instagram PR: Template Blueprint Info
        if path == '/api/instagram/template-info':
            from instagram_agent.image_generator import ImageGenerator
            self.send_json(200, {
                "success": True,
                "blueprint": ImageGenerator.get_template_blueprint()
            })
            return

        # Instagram PR: Post Types List
        if path == '/api/instagram/post-types':
            from instagram_agent.content_generator import ALL_POST_TYPES
            self.send_json(200, {"success": True, "types": ALL_POST_TYPES})
            return

        # Instagram PR: Reels Types List
        if path == '/api/instagram/reels-types':
            from instagram_agent.content_generator import REELS_TYPES_METADATA
            self.send_json(200, {"success": True, "types": REELS_TYPES_METADATA})
            return

        # Instagram PR: Safe Config
        if path == '/api/instagram/config':
            self.send_json(200, instagram_pr_agent.get_safe_config())
            return

        # Instagram PR: Posts List
        if path == '/api/instagram/posts':
            limit = int(query.get('limit', [50])[0])
            offset = int(query.get('offset', [0])[0])
            status = query.get('status', [None])[0]
            posts = instagram_pr_agent.get_posts(limit=limit, offset=offset, status=status)
            self.send_json(200, {"posts": posts})
            return

        # Instagram PR: Detect Chrome Session
        if path == '/api/instagram/chrome-session':
            try:
                session_info = extract_chrome_instagram_cookies()
                if session_info.get('success'):
                    self.send_json(200, {
                        "available": True,
                        "user_id": session_info['user_id'],
                        "sessionid_masked": session_info['sessionid_masked'],
                        "cookie_count": len(session_info.get('cookies', {}))
                    })
                else:
                    self.send_json(200, {
                        "available": False,
                        "error": session_info.get('error')
                    })
            except Exception as ex:
                self.send_json(200, {"available": False, "error": str(ex)})
            return

        # Instagram PR: Drone Community Engagement Status
        if path == '/api/instagram/engagement':
            try:
                engine = InstagramEngagementEngine(gemini_api_key=instagram_pr_agent.config.get('gemini_api_key'))
                data = engine.load_interactions_data()
                self.send_json(200, data)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Comment & DM Interactions
        if path == '/api/instagram/comment-interactions':
            from instagram_agent.db import get_recent_comment_interactions
            limit = int(query.get('limit', [50])[0])
            interactions = get_recent_comment_interactions(limit=limit)
            self.send_json(200, {"interactions": interactions})
            return

        # Reddit Drone Bot: Status
        if path == '/api/reddit/status':
            self.send_json(200, reddit_drone_agent.get_status())
            return

        # Reddit Drone Bot: Safe Config
        if path == '/api/reddit/config':
            self.send_json(200, reddit_drone_agent.get_safe_config())
            return

        # Reddit Drone Bot: Interactions / Replies List
        if path == '/api/reddit/replies':
            limit = int(query.get('limit', [50])[0])
            offset = int(query.get('offset', [0])[0])
            status = query.get('status', [None])[0]
            subreddit = query.get('subreddit', [None])[0]
            from reddit_agent.db import get_interactions
            items = get_interactions(limit=limit, offset=offset, status=status, subreddit=subreddit)
            self.send_json(200, {"interactions": items})
            return

        # Reddit Drone Bot: Check Chrome Session
        if path == '/api/reddit/chrome-session':
            try:
                from reddit_agent.chrome_session import extract_chrome_reddit_session
                session_info = extract_chrome_reddit_session()
                if session_info.get('success'):
                    self.send_json(200, {
                        "available": True,
                        "username": session_info['username']
                    })
                else:
                    self.send_json(200, {
                        "available": False,
                        "error": session_info.get('error')
                    })
            except Exception as ex:
                self.send_json(200, {"available": False, "error": str(ex)})
            return

        # Lead Supervisor Agent: Status
        if path == '/api/supervisor/status':
            self.send_json(200, lead_supervisor_agent.get_status())
            return

        # Lead Supervisor Agent: Active Directive
        if path == '/api/supervisor/directive':
            self.send_json(200, lead_supervisor_agent.current_directive or {})
            return

        # Lead Supervisor Agent: Directives History
        if path == '/api/supervisor/directives':
            limit = int(query.get('limit', [10])[0])
            self.send_json(200, {"directives": lead_supervisor_agent.get_directives_history(limit=limit)})
            return

        # Lead Supervisor Agent: 12-Hour Evolution Logs & Growth Status
        if path == '/api/supervisor/evolution':
            limit = int(query.get('limit', [10])[0])
            status = lead_supervisor_agent.get_status()
            history = lead_supervisor_agent.get_evolution_history(limit=limit)
            self.send_json(200, {
                "active_growth_mode": status.get("active_growth_mode", "AGGRESSIVE_EXPANSION"),
                "model_code": status.get("model_code", "gemini-3.8-flash"),
                "last_evolution_at": status.get("last_evolution_at"),
                "next_evolution_at": status.get("next_evolution_at"),
                "evolution_logs": history
            })
            return

        # Subagent 6: Global Product Trend Proposals
        if path == '/api/trend-hunter/proposals':
            status_filter = query.get('status', [None])[0]
            limit = int(query.get('limit', [20])[0])
            proposals = lead_supervisor_agent.trend_agent.get_proposals(status=status_filter, limit=limit)
            self.send_json(200, {"proposals": proposals, "count": len(proposals)})
            return

        # Subagent 6: Store Products Turkey Price Comparison & Undervaluation Alerts
        if path == '/api/trend-hunter/price-comparison':
            status_filter = query.get('status', ['ALL'])[0]
            search_query = query.get('q', [None])[0]
            warning_only = query.get('warning_only', ['false'])[0].lower() in ['true', '1', 'yes']
            limit = int(query.get('limit', [100])[0])
            offset = int(query.get('offset', [0])[0])
            report = lead_supervisor_agent.trend_agent.get_price_comparison_report(
                status_filter=status_filter,
                search_query=search_query,
                warning_only=warning_only,
                limit=limit,
                offset=offset
            )
            self.send_json(200, report)
            return

        if path == '/api/trend-hunter/price-warnings':
            limit = int(query.get('limit', [50])[0])
            report = lead_supervisor_agent.trend_agent.get_price_comparison_report(
                warning_only=True,
                limit=limit
            )
            self.send_json(200, report)
            return

        # Subagent 7: PR Health, Diagnostics & QA Sentinel Status
        if path == '/api/qa/status':
            self.send_json(200, qa_agent.get_status())
            return

        # Subagent 7: QA Incident History Log
        if path == '/api/qa/incidents':
            limit = int(query.get('limit', [50])[0])
            self.send_json(200, {"incidents": qa_agent.get_incidents(limit=limit)})
            return

        # LLM provider status (unified OpenCode/Evren gateway)
        if path == '/api/llm/status':
            try:
                from llm_client import get_llm
                llm = get_llm()
                self.send_json(200, {
                    "provider": "evren (OpenCode gateway)",
                    "base_url": llm.base_url,
                    "model": llm.model,
                    "reasoning_effort": llm.reasoning_effort,
                    "configured": llm.is_configured(),
                })
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 3: Latest Telemetry
        if path == '/api/telemetry/latest':
            self.send_json(200, lead_supervisor_agent.telemetry_agent.get_latest_telemetry())
            return

        # Subagent 5: Price & Arbitrage Intelligence Report
        if path == '/api/price-intelligence':
            limit = int(query.get('limit', [50])[0])
            status_filter = query.get('status', ['ALL'])[0]
            report = lead_supervisor_agent.price_agent.get_latest_report(limit=limit, status_filter=status_filter)
            summary = lead_supervisor_agent.price_agent.get_summary_stats()
            self.send_json(200, {"report": report, "summary": summary})
            return

        # Subagent 4: Technical SEO Articles
        if path == '/api/seo/articles':
            limit = int(query.get('limit', [20])[0])
            articles = lead_supervisor_agent.seo_agent.get_articles(limit=limit)
            self.send_json(200, {"articles": articles})
            return

        if path == '/api/seo/article':
            slug = query.get('slug', [''])[0]
            art_id = query.get('id', [''])[0]
            conn = get_db()
            cursor = conn.cursor()
            if slug:
                cursor.execute("SELECT * FROM seo_articles WHERE slug = ? LIMIT 1", (slug,))
            elif art_id:
                cursor.execute("SELECT * FROM seo_articles WHERE id = ? LIMIT 1", (art_id,))
            else:
                cursor.execute("SELECT * FROM seo_articles ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            conn.close()
            if row:
                art = {
                    "id": row["id"],
                    "slug": row["slug"],
                    "title": row["title"],
                    "component_focus": row["component_focus"],
                    "target_keywords": row["target_keywords"],
                    "internal_links": json.loads(row["internal_links_json"]) if row["internal_links_json"] else [],
                    "content_markdown": row["content_markdown"],
                    "created_at": row["created_at"]
                }
                self.send_json(200, {"article": art})
            else:
                self.send_json(404, {"error": "Article not found"})
            return

        # Subagents Matrix Status (Toggle and Active Statuses)
        if path == '/api/subagents/status':
            subagents = get_all_subagents_config()
            self.send_json(200, {"success": True, "subagents": subagents, "count": len(subagents)})
            return

        # Subagent 8: Latest Procurement & Replenishment Order Plan
        if path == '/api/procurement/latest':
            plan = lead_supervisor_agent.procurement_agent.get_latest_plan()
            if not plan:
                plan = lead_supervisor_agent.procurement_agent.analyze_and_generate_order_plan()
            self.send_json(200, {"success": True, "plan": plan})
            return

        # Subagent 8: Export Procurement Order as CSV
        if path == '/api/procurement/export':
            csv_path = os.path.join(BASE_DIR, "data", "latest_procurement_order.csv")
            if not os.path.exists(csv_path):
                lead_supervisor_agent.procurement_agent.analyze_and_generate_order_plan()
            if os.path.exists(csv_path):
                with open(csv_path, 'rb') as f:
                    csv_data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="pozitron_tedarik_siparis_listesi.csv"')
                self.send_header('Content-Length', str(len(csv_data)))
                self.end_headers()
                self.wfile.write(csv_data)
                return
            else:
                self.send_json(404, {"error": "CSV file not found"})
                return

        # Pipeline Topology & Workflow Graph (n8n style architecture)
        # Subagent 9: Cyber Security Status
        if path == '/api/security/status':
            audit = cyber_security_agent.get_latest_audit()
            self.send_json(200, {"success": True, "audit": audit})
            return

        # Subagent 10: Product Media & Content Quality Audit
        if path == '/api/media/audit':
            audit = media_inspector_agent.get_latest_audit()
            self.send_json(200, {"success": True, "audit": audit})
            return

        # Pipeline Topology & Workflow Graph (Comprehensive Multi-Server & Ecosystem Architecture)
        if path == '/api/pipeline/graph':
            sup_status = lead_supervisor_agent.get_status()
            ig_status = instagram_pr_agent.get_status()
            rd_status = reddit_drone_agent.get_status()
            qa_status = qa_agent.get_status()
            tel = lead_supervisor_agent.telemetry_agent.get_latest_telemetry()
            summary = lead_supervisor_agent.price_agent.get_summary_stats()
            trend_props = lead_supervisor_agent.trend_agent.get_proposals(limit=100)
            proc_plan = lead_supervisor_agent.procurement_agent.get_latest_plan() or {}

            active_dir = sup_status.get("active_directive", {})
            reddit_enabled = is_subagent_enabled("subagent_2_reddit")
            sec_audit = cyber_security_agent.get_latest_audit() or {}
            media_audit = media_inspector_agent.get_latest_audit() or {}
            sec_enabled = is_subagent_enabled("subagent_9_security")
            media_enabled = is_subagent_enabled("subagent_10_media")

            graph = {
                "version": "3.1",
                "engine": "Antigravity 2.0 Full Ecosystem Architecture (+ Yerel AI: DeepSeek LLM, FLUX Görsel, LTX-Video Reels)",
                "last_cycle_at": sup_status.get("last_run_at"),
                "next_cycle_at": sup_status.get("next_run_at"),
                "columns": [
                    {"id": 1, "name": "1. MÜŞTERİ & TETİKLEYİCİLER", "desc": "Ziyaretçi & Otonom Tetikleyiciler"},
                    {"id": 2, "name": "2. BULUT & SUNUCU ALTYAPISI", "desc": "GitHub & Hetzner Sunucuları"},
                    {"id": 3, "name": "3. HARİCİ SERVİSLER & ÖDEME", "desc": "PayTR, SMTP & Gemini AI"},
                    {"id": 4, "name": "4. İSTİHBARAT & ORKESTRASYON", "desc": "Pazar Analizi & Baş Supervisor"},
                    {"id": 5, "name": "5. UZMAN AJANLAR & TEDARİK", "desc": "Sipariş, İçerik, SEO & QA"},
                    {"id": 6, "name": "6. YAYIN & DAĞITIM KANALLARI", "desc": "Web, Instagram, Reddit, Google"}
                ],
                "nodes": [
                    # COLUMN 1: Müşteri & Tetikleyiciler
                    {
                        "id": "client_customer",
                        "label": "Müşteri & Ziyaretçi",
                        "tag": "[CLIENT]",
                        "column": 1,
                        "type": "client",
                        "category": "Son Kullanıcı / Tarayıcı",
                        "status": "active",
                        "status_text": "Web Gezinme & Alışveriş",
                        "description": "FPV pilotları ve müşteriler: Ürün inceler, sepete ekler, 3D Secure ödeme yapar ve ürün yorumu bırakır",
                        "triggers": ["srv_github_platform", "srv_hetzner_cloud", "svc_paytr"],
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
                        "column": 1,
                        "type": "trigger",
                        "category": "Zamanlayıcı (Cron)",
                        "interval": "2 saat",
                        "status": "active",
                        "status_text": "Aktif (Tetikliyor)",
                        "description": "Antigravity 2.0 periyodik cron tetikleyicisi: 2 saatte bir pazar istihbaratı ve orkestrasyonu tetikler",
                        "triggers": ["subagent_5_price", "subagent_3_telemetry", "subagent_6_trend"],
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
                        "column": 1,
                        "type": "trigger",
                        "category": "Sipariş / Envanter Olayı",
                        "status": "ready",
                        "status_text": "repository_dispatch",
                        "description": "Sipariş verildiğinde anlık stok düşümü ve Git senkronizasyonu için GitHub Actions tetikleyicisi",
                        "triggers": ["srv_github_platform"],
                        "payload_preview": {
                            "event_type": "market_order",
                            "workflow": ".github/workflows/market_order_sync.yml",
                            "action": "scripts/cloud_market_sync.py"
                        }
                    },

                    # COLUMN 2: Bulut & Sunucu Altyapısı
                    {
                        "id": "srv_github_platform",
                        "label": "GitHub Server & CDN",
                        "tag": "[GITHUB SERVER]",
                        "column": 2,
                        "type": "server",
                        "category": "Statik CDN & CI/CD Dağıtımı",
                        "status": "active",
                        "status_text": "Pages CDN & Actions CI/CD",
                        "description": "GitHub Pages Anycast CDN (pozitronmarket.com), Git versiyon kontrolü ve GitHub Actions envanter senkron iş akışları (market_order_sync.yml, instagram_agent.yml)",
                        "inputs": ["client_customer", "trigger_github_dispatch"],
                        "triggers": ["output_pozitron_web"],
                        "payload_preview": {
                            "repository": "thepeakiscold/pozitron-market",
                            "hosting": "GitHub Pages (CNAME pozitronmarket.com)",
                            "actions_workflows": ["market_order_sync.yml", "instagram_agent.yml", "reddit_bot.yml"],
                            "static_assets": "HTML, CSS, JS, SSG product pages (508 SKU)"
                        }
                    },
                    {
                        "id": "srv_hetzner_cloud",
                        "label": "Hetzner Cloud Server (VPS)",
                        "tag": "[HETZNER VPS]",
                        "column": 2,
                        "type": "server",
                        "category": "Merkezi Bulut & Backend API",
                        "status": "running",
                        "status_text": "Ubuntu 24.04 • Nginx SSL • Port 8000",
                        "description": "Hetzner Cloud VPS: api.pozitronmarket.com, Nginx Reverse Proxy (SSL Let's Encrypt), Systemd pozitron.service, 7/24 Python backend API ve SQLite pozitron.db",
                        "inputs": ["client_customer", "svc_paytr", "lead_supervisor", "subagent_8_procurement"],
                        "triggers": ["svc_smtp_mail", "trigger_github_dispatch"],
                        "payload_preview": {
                            "cloud_provider": "Hetzner Cloud GmbH (Nuremberg / Falkenstein)",
                            "domain": "https://api.pozitronmarket.com",
                            "os": "Ubuntu 24.04 LTS (x86_64)",
                            "web_server": "Nginx Reverse Proxy (Port 80/443 SSL Let's Encrypt)",
                            "service": "systemd (pozitron.service / port 8000)",
                            "database": "SQLite 3 (pozitron.db - ACID Transactional)",
                            "active_subagents": 9
                        }
                    },

                    # COLUMN 3: Harici Servisler & Ödeme
                    {
                        "id": "svc_paytr",
                        "label": "PayTR Sanal POS (Ödeme)",
                        "tag": "[PAYMENT]",
                        "column": 3,
                        "type": "service",
                        "category": "Ödeme Ağ Geçidi",
                        "status": "connected",
                        "status_text": "3D Secure • Token & Webhook",
                        "description": "Türkiye BDDK lisanslı güvenli ödeme altyapısı: Kredi kartı tahsilatı, taksit seçenekleri ve /api/paytr/callback webhook bildirimi",
                        "inputs": ["client_customer"],
                        "triggers": ["srv_hetzner_cloud"],
                        "payload_preview": {
                            "provider": "PayTR Ödeme ve Elektronik Para Kuruluşu A.Ş.",
                            "integration": "iFrame API + 3D Secure 2.0",
                            "callback_endpoint": "https://api.pozitronmarket.com/api/paytr/callback",
                            "supported_cards": "Troy, Visa, MasterCard, Maximum, Bonus, World, Axess, CardFinans"
                        }
                    },
                    {
                        "id": "svc_smtp_mail",
                        "label": "SMTP E-Posta Sunucusu",
                        "tag": "[SMTP MAIL]",
                        "column": 3,
                        "type": "service",
                        "category": "İşlemsel E-Posta",
                        "status": "connected",
                        "status_text": "STARTTLS Port 587 • noreply",
                        "description": "Direct SMTP (Gmail Port 587): Sipariş dekontu, kargo takip numarası ve sistem kritik durum alarmları",
                        "inputs": ["srv_hetzner_cloud"],
                        "triggers": ["client_customer"],
                        "payload_preview": {
                            "server": "smtp.gmail.com:587",
                            "encryption": "STARTTLS",
                            "sender": "noreply@pozitronmarkets.com",
                            "mail_types": ["Sipariş Onayı", "Kargo Takip", "Admin Kritik Bildirim"]
                        }
                    },
                    {
                        "id": "svc_gemini_ai",
                        "label": "Google Gemini (Yedek / Legacy)",
                        "tag": "[GEMINI AI]",
                        "column": 3,
                        "type": "ai",
                        "category": "Bilişsel Zeka (Yedek)",
                        "status": "ready",
                        "status_text": "gemini-3.8-flash (yalnızca yedek metin)",
                        "description": "Birincil zeka değil: metin DeepSeek'e, görsel/video denetimi de DeepSeek/LTX'e devredildi. Gemini yalnızca eski yedek metin yolu olarak durur; video üretimi tamamen kaldırıldı",
                        "inputs": ["lead_supervisor", "subagent_1_instagram", "subagent_4_seo"],
                        "triggers": ["lead_supervisor", "subagent_1_instagram", "subagent_4_seo"],
                        "payload_preview": {
                            "primary_model": "gemini-3.8-flash",
                            "fallback_model": "gemini-2.5-flash",
                            "tasks": ["Piyasa Arbitrajı", "Teknik Doküman Sentezi", "Afiş Vizyon Denetimi", "Kök Neden Analizi (RCA)"]
                        }
                    },

                    {
                        "id": "svc_llm_evren",
                        "label": "DeepSeek V4.1 Flash (Metin LLM)",
                        "tag": "[LLM]",
                        "column": 3,
                        "type": "ai",
                        "category": "Metin Üretimi & İnsan Dili",
                        "status": "active",
                        "status_text": "deepseek-v4.1-flash • reasoning: high",
                        "description": "OpenCode/Evren OpenAI-uyumlu ağ geçidi üzerinden DeepSeek V4.1 Flash (High): Instagram başlık/metin ve video promptlarını insan gibi yazar, üretilen görsellerin ÇOK MODLU VİZYON DENETİMİNİ de yapar (Gemini denetimi kaldırıldı)",
                        "inputs": ["subagent_1_instagram", "subagent_2_reddit", "subagent_4_seo"],
                        "triggers": ["subagent_1_instagram"],
                        "payload_preview": {
                            "provider_gateway": "OpenCode / Evren (OpenAI-compatible)",
                            "primary_model": "deepseek-v4.1-flash",
                            "reasoning_effort": "high",
                            "fallback_model": "gemini-3.8-flash (yalnızca yedek metin)",
                            "tasks": ["İnsan Dili Metin", "Reels Video Promptu", "Görsel Vizyon Denetimi", "Topluluk Yorumu"]
                        }
                    },
                    {
                        "id": "ai_flux_image",
                        "label": "FLUX.1 [dev] Görsel AI (Yerel GPU)",
                        "tag": "[FLUX IMAGE]",
                        "column": 3,
                        "type": "ai",
                        "category": "Görsel Üretimi (Local Diffusion)",
                        "status": "active",
                        "status_text": "flux1-dev-Q8_0.gguf • ComfyUI",
                        "description": "Yerel FLUX.1 [dev] ünitesi (RTX 4060 Ti 16GB): her post için ürün/studio fotoğrafı üretir; ürün postlarında gerçek ürün görseli üzerine kompoze edilir",
                        "inputs": ["subagent_1_instagram"],
                        "triggers": ["subagent_1_instagram"],
                        "payload_preview": {
                            "engine": "ComfyUI (127.0.0.1:8188)",
                            "unet": "flux1-dev-Q8_0.gguf (GGUF Q8_0, 12.7GB)",
                            "unet_alt": "flux1-dev.safetensors (bf16, 23.8GB)",
                            "text_encoders": ["t5xxl_fp8_e4m3fn", "clip_l"],
                            "vae": "ae.safetensors",
                            "resolution": "1024x1024",
                            "workflow": "flux_dev_gguf_api.json"
                        }
                    },
                    {
                        "id": "ai_ltx_video",
                        "label": "LTX-Video 0.9.8 Video AI (Yerel GPU)",
                        "tag": "[LTX VIDEO]",
                        "column": 3,
                        "type": "ai",
                        "category": "Video Üretimi (Text-to-Video)",
                        "status": "active",
                        "status_text": "ltxv-13b-0.9.8-distilled-fp8 • 24fps",
                        "description": "Reels için TEK AI video motoru: LTXV 0.9.8 dikey 9:16 sahne üretir; marka katmanı bindirilip 1080x1920 H.264 Reels'e dönüştürülür. Gemini ile video üretimi kaldırıldı; slayt video kullanılmaz",
                        "inputs": ["subagent_1_instagram"],
                        "triggers": ["subagent_1_instagram"],
                        "payload_preview": {
                            "engine": "ComfyUI Core LTXV Nodes",
                            "checkpoint": "ltxv-13b-0.9.8-distilled-fp8.safetensors",
                            "checkpoint_alt": "ltxv-2b-0.9.8-distilled-fp8.safetensors",
                            "text_encoder": "t5xxl_fp8_e4m3fn",
                            "latent": "576x1024 (9:16) • 97 kare",
                            "steps": 8,
                            "workflow": "ltxv_t2v_api.json"
                        }
                    },

                    {
                        "id": "subagent_9_security",
                        "label": "Subagent 9: Siber Güvenlik",
                        "tag": "[SENTINEL]",
                        "column": 3,
                        "type": "sentinel",
                        "category": "Siber Savunma & WAF",
                        "status": "running" if sec_enabled else "disabled",
                        "status_text": f"Skor: %{sec_audit.get('score', 100)} • 6 Prob",
                        "description": "SQL Injection, XSS, PayTR 3D Secure HMAC, gizli token ve SSL/TLS açıklarını 7/24 denetler",
                        "inputs": ["srv_hetzner_cloud", "svc_paytr"],
                        "triggers": ["lead_supervisor"],
                        "payload_preview": {
                            "status": sec_audit.get("status", "SECURE"),
                            "score": sec_audit.get("score", 100),
                            "probes_count": sec_audit.get("probes_count", 6),
                            "findings_count": sec_audit.get("findings_count", 0)
                        }
                    },

                    # COLUMN 4: İstihbarat & Orkestrasyon
                    {
                        "id": "subagent_5_price",
                        "label": "Subagent 5: Fiyat & Rekabet",
                        "tag": "[SUBAGENT 5]",
                        "column": 4,
                        "type": "agent",
                        "category": "İstihbarat / Arbitraj",
                        "status": "ready",
                        "status_text": f"{summary.get('tracked_skus', 508)} SKU Taranıyor",
                        "description": "Türkiye yerel pazar fiyatlarını kıyaslar, fiyat ve stok avantajı tespit eder",
                        "inputs": ["trigger_cron_2h"],
                        "triggers": ["lead_supervisor", "subagent_8_procurement"],
                        "payload_preview": {
                            "tracked_skus": summary.get("tracked_skus", 508),
                            "price_advantages": summary.get("price_advantage_count", 0),
                            "competitor_out_of_stock": summary.get("competitor_out_of_stock_count", 0),
                            "status": "SCAN_COMPLETE"
                        }
                    },
                    {
                        "id": "subagent_3_telemetry",
                        "label": "Subagent 3: Telemetri Toplayıcı",
                        "tag": "[SUBAGENT 3]",
                        "column": 4,
                        "type": "agent",
                        "category": "Metrik / Telemetri",
                        "status": "ready",
                        "status_text": "Aktif Metrik Kaydı",
                        "description": "Instagram, Reddit, SEO ve trafik verilerini derleyip orkestratöre iletir",
                        "inputs": ["trigger_cron_2h"],
                        "triggers": ["lead_supervisor"],
                        "payload_preview": tel
                    },
                    {
                        "id": "subagent_6_trend",
                        "label": "Subagent 6: Küresel Trend & Ürün Avcısı",
                        "tag": "[SUBAGENT 6]",
                        "column": 4,
                        "type": "agent",
                        "category": "Trend & Ürün Keşfi",
                        "status": "ready",
                        "status_text": f"{len(trend_props)} Trend Takipte",
                        "description": "Dünya genelindeki popüler donanımları tarar, yerel fiyat kıyaslamasıyla sıfır stoklu 'YAKINDA' olarak kataloğa ekler",
                        "inputs": ["trigger_cron_2h"],
                        "triggers": ["lead_supervisor", "subagent_8_procurement"],
                        "payload_preview": {
                            "total_proposals": len(trend_props),
                            "auto_added_to_catalog": len([p for p in trend_props if p.get("status") == "APPROVED"]),
                            "injection_policy": "stock = 0, badge = 'YAKINDA'"
                        }
                    },
                    {
                        "id": "lead_supervisor",
                        "label": "Baş Orkestrasyon (Lead Supervisor)",
                        "tag": "[SUPERVISOR]",
                        "column": 4,
                        "type": "supervisor",
                        "category": "Karar & Direktif Motoru",
                        "status": "running" if sup_status.get("is_autonomous_enabled") else "idle",
                        "status_text": f"Model: gemini-3.8-flash • Mod: {sup_status.get('active_growth_mode', 'AGGRESSIVE_EXPANSION')}",
                        "description": "Google Antigravity 2.0 (gemini-3.8-flash): İstihbarat ve telemetriyi analiz eder, sistemi optimize eder, alt ajanlara direktif dağıtır",
                        "inputs": ["subagent_5_price", "subagent_3_telemetry", "subagent_6_trend", "svc_gemini_ai"],
                        "triggers": ["subagent_8_procurement", "subagent_1_instagram", "subagent_2_reddit", "subagent_4_seo", "subagent_7_qa", "srv_hetzner_cloud"],
                        "payload_preview": active_dir
                    },

                    # COLUMN 5: Uzman Ajanlar & Tedarik
                    {
                        "id": "subagent_8_procurement",
                        "label": "Subagent 8: Sipariş & Tedarik",
                        "tag": "[SUBAGENT 8]",
                        "column": 5,
                        "type": "agent",
                        "category": "Satınalma & Tedarik Optimizasyonu",
                        "status": "ready",
                        "status_text": f"{proc_plan.get('total_skus', 17)} SKU • %{proc_plan.get('projected_roi_pct', 80.4)} ROI",
                        "description": "Trend Avcısı ve stok açıklarını analiz ederek en yüksek kârlılıklı toptan satınalma sipariş planını hazırlar (CSV & JSON)",
                        "inputs": ["lead_supervisor", "subagent_6_trend", "subagent_5_price"],
                        "triggers": ["srv_hetzner_cloud"],
                        "payload_preview": {
                            "recommended_skus": proc_plan.get("total_skus", 17),
                            "total_units": proc_plan.get("total_quantity", 476),
                            "estimated_investment_try": proc_plan.get("total_investment_try", 249349.74),
                            "projected_profit_try": proc_plan.get("total_profit_try", 200414.26),
                            "profit_margin_pct": proc_plan.get("profit_margin_pct", 44.6),
                            "export_files": ["data/latest_procurement_plan.json", "data/latest_procurement_order.csv"]
                        }
                    },
                    {
                        "id": "subagent_1_instagram",
                        "label": "Subagent 1: Instagram PR",
                        "tag": "[SUBAGENT 1]",
                        "column": 5,
                        "type": "worker",
                        "category": "İçerik & Topluluk",
                        "status": "running" if ig_status.get("is_autonomous_enabled") else "idle",
                        "status_text": "Tek Şablon • AI Görsel + AI Video Reels",
                        "description": "DeepSeek V4.1 Flash ile insan dili metin yazar; tek marka şablonunda FLUX AI görseli/ürün fotoğrafı üretir, Reels için LTX-Video ile AI video çeker ve haftalık 24 saatlik indirim kuponu yayınlar",
                        "inputs": ["lead_supervisor", "svc_llm_evren", "ai_flux_image", "ai_ltx_video", "svc_gemini_ai"],
                        "triggers": ["svc_meta_graph"],
                        "payload_preview": active_dir.get("instagram_directive", {})
                    },
                    {
                        "id": "subagent_2_reddit",
                        "label": "Subagent 2: Reddit Etkileşim",
                        "tag": "[SUBAGENT 2]",
                        "column": 5,
                        "type": "worker",
                        "category": "Organik PR / Q&A",
                        "status": "running" if (rd_status.get("is_autonomous_enabled") and reddit_enabled) else "disabled",
                        "status_text": "DEVREDIŞI (Kapalı)" if not reddit_enabled else "Aktif Otomasyon",
                        "description": "Topluluk sorularını Gemini ile yanıtlar, organik kaynak gösterir (Subagent Açma/Kapama matrisi ile yönetilir)",
                        "inputs": ["lead_supervisor"],
                        "triggers": ["svc_reddit_platform"],
                        "payload_preview": active_dir.get("reddit_directive", {})
                    },
                    {
                        "id": "subagent_4_seo",
                        "label": "Subagent 4: SEO & Dokümantasyon",
                        "tag": "[SUBAGENT 4]",
                        "column": 5,
                        "type": "worker",
                        "category": "İçerik Otoritesi",
                        "status": "ready",
                        "status_text": f"{tel.get('seo', {}).get('articles_published', 11)} Teknik Rehber",
                        "description": "Derin mühendislik rehberleri üretir, pinout tabloları ve Pozitron ürünlerine iç linkleme yapar",
                        "inputs": ["lead_supervisor", "svc_gemini_ai"],
                        "triggers": ["output_pozitron_web"],
                        "payload_preview": active_dir.get("seo_content_directive", {})
                    },
                    {
                        "id": "subagent_7_qa",
                        "label": "Subagent 7: QA & Sağlık Sentineli",
                        "tag": "[SUBAGENT 7]",
                        "column": 5,
                        "type": "sentinel",
                        "category": "Tanı, QA & Otonom Onarım",
                        "status": "running" if qa_status.get("is_autonomous_enabled") else "idle",
                        "status_text": f"Sağlık: %{qa_status.get('last_health_score', 100)} • 8 Prob",
                        "description": "Kritik pipeline sağlık denetimi, oturum ve token doğrulama ile Gemini 3.8 Flash otonom iyileştirme",
                        "inputs": ["lead_supervisor"],
                        "triggers": ["srv_hetzner_cloud", "srv_github_platform", "svc_meta_graph"],
                        "payload_preview": {
                            "agent": "QASentinelAgent",
                            "health_score": qa_status.get("last_health_score", 100),
                            "last_status": qa_status.get("last_status", "HEALTHY"),
                            "auto_heal_enabled": qa_status.get("auto_heal_enabled", True),
                            "probes_count": 8
                        }
                    },

                    {
                        "id": "subagent_10_media",
                        "label": "Subagent 10: Medya & Otomatik Onarım",
                        "tag": "[AUTO-REPAIR]",
                        "column": 5,
                        "type": "worker",
                        "category": "Görsel Denetim & Otonom İyileştirme",
                        "status": "ready" if media_enabled else "disabled",
                        "status_text": f"{media_audit.get('total_products_scanned', 508)} SKU • %{media_audit.get('visual_health_score', 86)} Sağlık (Otonom Onarım Açık)",
                        "description": "508 ürünün görsellerini denetler; karantinadaki ve hatalı SKU'ları resmi stüdyo DAM assetleri ile otonom olarak onarır",
                        "inputs": ["lead_supervisor"],
                        "triggers": ["output_pozitron_web"],
                        "payload_preview": {
                            "scanned": media_audit.get("total_products_scanned", 508),
                            "score": media_audit.get("visual_health_score", 86),
                            "quarantine": media_audit.get("quarantine_candidates_count", 0),
                            "auto_remediation": "ACTIVE",
                            "last_auto_fix": media_audit.get("last_auto_fix_at", "Otonom Döngüde")
                        }
                    },

                    # COLUMN 6: Yayın & Dağıtım Kanalları
                    {
                        "id": "output_pozitron_web",
                        "label": "Pozitron Market Web & Blog",
                        "tag": "[DESTINATION]",
                        "column": 6,
                        "type": "destination",
                        "category": "Web Platformu",
                        "status": "connected",
                        "status_text": "pozitronmarket.com",
                        "description": "Katalog ve teknik rehber sayfaları üzerinden organik trafik toplar, son kullanıcıya sunulur",
                        "inputs": ["srv_github_platform", "subagent_4_seo"],
                        "triggers": ["svc_google_merchant"],
                        "payload_preview": {
                            "platform": "https://pozitronmarket.com",
                            "content_type": "Technical Guides & High-Conversion SSG Catalog",
                            "status": "LIVE",
                            "sitemap": "https://pozitronmarket.com/sitemap.xml (513 URL)"
                        }
                    },
                    {
                        "id": "svc_meta_graph",
                        "label": "Instagram Graph API & @pozitronmarket",
                        "tag": "[SOCIAL]",
                        "column": 6,
                        "type": "destination",
                        "category": "Sosyal Medya",
                        "status": "connected",
                        "status_text": "Bağlı (ID: 17841430407836914)",
                        "description": "1080x1080 afiş, hikaye ve AI video Reels yayınları ile pilot topluluk etkileşimi; haftalık 24 saatlik indirim kuponu paylaşımı",
                        "inputs": ["subagent_1_instagram", "subagent_7_qa"],
                        "triggers": [],
                        "payload_preview": {
                            "channel": "Instagram Feed, Story & AI Reels",
                            "account": "@pozitronmarket",
                            "account_id": "17841430407836914",
                            "reels_engine": "LTX-Video 0.9.8 (9:16 AI video)",
                            "weekly_deal": "24 saatlik kupon (haftada 1)",
                            "status": "CONNECTED"
                        }
                    },
                    {
                        "id": "svc_reddit_platform",
                        "label": "Reddit Topluluk Kanalları",
                        "tag": "[COMMUNITY]",
                        "column": 6,
                        "type": "destination",
                        "category": "Topluluk Kanalı",
                        "status": "ready" if reddit_enabled else "disabled",
                        "status_text": "u/Aggravating_End_1105" if reddit_enabled else "Bot Kapalı",
                        "description": "Hedef subredditlerde kullanıcılara teknik çözüm sunar",
                        "inputs": ["subagent_2_reddit"],
                        "triggers": [],
                        "payload_preview": {
                            "account": "u/Aggravating_End_1105",
                            "subreddits": ["r/Turkey", "r/teknoloji", "r/bilim", "r/AskTurkey"],
                            "state": "MANAGED_VIA_TOGGLE"
                        }
                    },
                    {
                        "id": "svc_google_merchant",
                        "label": "Google Merchant & Arama Motorları",
                        "tag": "[SEARCH & SHOP]",
                        "column": 6,
                        "type": "destination",
                        "category": "Arama Motoru / Katalog",
                        "status": "connected",
                        "status_text": "XML Feed & Sitemap (513 URL)",
                        "description": "Google Alışveriş sekmesi, TSV/XML ürün akışı ve arama motoru indekslemesi",
                        "inputs": ["output_pozitron_web"],
                        "triggers": [],
                        "payload_preview": {
                            "merchant_xml": "https://pozitronmarket.com/google_merchant_feed.xml",
                            "merchant_tsv": "https://pozitronmarket.com/google_merchant_feed.tsv",
                            "sitemap": "https://pozitronmarket.com/sitemap.xml",
                            "indexed_products": 508
                        }
                    }
                ],
                                "connections": [
                    # 1. Giriş & Dış Trafik (Column 1 -> Column 2)
                    {"from": "client_customer", "to": "srv_github_platform", "label": "Web Sitesi Ziyareti & CDN", "type": "network"},
                    {"from": "client_customer", "to": "srv_hetzner_cloud", "label": "Dinamik API İstekleri (Stok/Sepet)", "type": "network"},
                    {"from": "trigger_cron_2h", "to": "srv_hetzner_cloud", "label": "2 Saatlik Otonom Döngü Tetikleyici", "type": "trigger"},
                    {"from": "trigger_github_dispatch", "to": "srv_github_platform", "label": "cloud_market_sync.py CI/CD", "type": "trigger"},

                    # 2. Sunucu & Altyapı İletişimi (Column 2 -> Column 3, 4, 6)
                    {"from": "srv_hetzner_cloud", "to": "svc_paytr", "label": "3D Secure Ödeme Entegrasyonu", "type": "payment"},
                    {"from": "srv_hetzner_cloud", "to": "svc_smtp_mail", "label": "İşlemsel E-Posta Servisi", "type": "data"},
                    {"from": "srv_hetzner_cloud", "to": "subagent_9_security", "label": "WAF & Girdi Güvenlik Probu", "type": "probe"},
                    {"from": "srv_hetzner_cloud", "to": "lead_supervisor", "label": "Sunucu Durumu & Telemetri", "type": "data"},
                    {"from": "srv_github_platform", "to": "output_pozitron_web", "label": "GitHub Pages CDN Canlı Yayını", "type": "publish"},

                    # 3. Harici Servisler & Güvenlik (Column 3 -> Column 3 & 4)
                    {"from": "svc_paytr", "to": "svc_smtp_mail", "label": "Ödeme Başarılı -> Fatura & Dekont", "type": "payment"},
                    {"from": "subagent_9_security", "to": "lead_supervisor", "label": "Siber Güvenlik Denetim Raporu", "type": "probe"},
                    {"from": "svc_gemini_ai", "to": "lead_supervisor", "label": "Gemini 3.8 Flash Karar Yanıtı", "type": "data"},
                    {"from": "svc_llm_evren", "to": "subagent_1_instagram", "label": "İnsan Dili Metin & Video Promptu (DeepSeek)", "type": "data"},
                    {"from": "ai_flux_image", "to": "subagent_1_instagram", "label": "AI Görsel Akışı (FLUX 1024²)", "type": "data"},
                    {"from": "ai_ltx_video", "to": "subagent_1_instagram", "label": "AI Video Akışı (LTX 9:16)", "type": "data"},

                    # 4. İstihbarat & Karar Motoru (Column 4 -> Column 4 & 5)
                    {"from": "subagent_5_price", "to": "lead_supervisor", "label": "Fiyat Arbitraj Raporu", "type": "data"},
                    {"from": "subagent_3_telemetry", "to": "lead_supervisor", "label": "Performans Metrikleri", "type": "data"},
                    {"from": "subagent_6_trend", "to": "lead_supervisor", "label": "Yeni Trend Ürün Önerileri", "type": "data"},
                    {"from": "lead_supervisor", "to": "subagent_8_procurement", "label": "procurement_directive", "type": "directive"},
                    {"from": "lead_supervisor", "to": "subagent_1_instagram", "label": "instagram_directive", "type": "directive"},
                    {"from": "lead_supervisor", "to": "subagent_2_reddit", "label": "reddit_directive", "type": "directive"},
                    {"from": "lead_supervisor", "to": "subagent_4_seo", "label": "seo_directive", "type": "directive"},
                    {"from": "lead_supervisor", "to": "subagent_7_qa", "label": "qa_directive", "type": "directive"},
                    {"from": "lead_supervisor", "to": "subagent_10_media", "label": "Otonom Denetim & Otomatik Onarım", "type": "directive"},

                    # 5. Uzman Ajanlar -> Kayıt & Dağıtım (Column 5 -> Column 6)
                    {"from": "subagent_8_procurement", "to": "output_pozitron_web", "label": "Tedarik Planı & Stok Girişi", "type": "data"},
                    {"from": "subagent_7_qa", "to": "output_pozitron_web", "label": "Mağaza Sağlık & Sepet Doğrulama", "type": "probe"},
                    {"from": "subagent_1_instagram", "to": "svc_meta_graph", "label": "Afiş & Hikaye Yayını", "type": "publish"},
                    {"from": "subagent_2_reddit", "to": "svc_reddit_platform", "label": "Otonom Yanıt Yayını", "type": "publish"},
                    {"from": "subagent_4_seo", "to": "output_pozitron_web", "label": "İç Linkli Teknik Rehber", "type": "publish"},
                    {"from": "subagent_10_media", "to": "output_pozitron_web", "label": "Otomatik Onarılmış & Doğrulanmış Stüdyo Kataloğu", "type": "publish"},

                    # 6. Dağıtım & Arama Motorları (Column 6 Dahili)
                    {"from": "output_pozitron_web", "to": "svc_google_merchant", "label": "XML/TSV Feed & Sitemap", "type": "publish"}
                ],
                "ecosystem_services": [
                    {
                        "id": "srv_github",
                        "name": "GitHub Server (Platform)",
                        "category": "Sunucu & Altyapı",
                        "provider": "GitHub Inc. / Microsoft",
                        "role": "Global Statik CDN Dağıtımı, SSG Sayfaları ve CI/CD Envanter Senkronizasyonu",
                        "endpoints": ["https://pozitronmarket.com", "thepeakiscold/pozitron-market", "GitHub Actions"],
                        "protocols": ["HTTPS (443)", "Git over SSH/HTTPS"],
                        "status": "OPERATIONAL",
                        "badge": "STATİK CDN & CI/CD",
                        "details": "GitHub Pages Anycast CDN üzerinden 508 ürün sayfasını ve Pozitron arayüzünü milisaniyelik hızla sunar. Sipariş verildiğinde repository_dispatch ile market_order_sync.yml tetiklenir ve stoklar otomatik revize edilir."
                    },
                    {
                        "id": "srv_hetzner",
                        "name": "Hetzner Cloud VPS",
                        "category": "Sunucu & Altyapı",
                        "provider": "Hetzner Online GmbH (Almanya)",
                        "role": "Merkezi Bulut Sunucusu, Nginx Reverse Proxy, REST API ve Ajan Orkestratörü",
                        "endpoints": ["https://api.pozitronmarket.com", "http://127.0.0.1:8000"],
                        "protocols": ["HTTPS (443 SSL Let's Encrypt)", "Systemd Service (Port 8000)"],
                        "status": "RUNNING",
                        "badge": "CANLI BULUT API",
                        "details": "Ubuntu 24.04 LTS VPS üzerinde Nginx SSL arkasında çalışan Python backend motoru. 508 ürünün dinamik stok kontrolleri, PayTR callback doğrulama, sipariş kayıtları ve 9 otonom alt ajanın thread orkestrasyonunu yürütür."
                    },
                    {
                        "id": "svc_gemini",
                        "name": "Google Gemini (Yedek / Legacy)",
                        "category": "Yapay Zeka & Bilişsel",
                        "provider": "Google DeepMind / Google Cloud",
                        "role": "Yedek Metin Yolu (birincil değil)",
                        "endpoints": ["gemini-3.8-flash", "gemini-2.5-flash"],
                        "protocols": ["HTTPS REST JSON (Google Generative AI)"],
                        "status": "STANDBY",
                        "badge": "LEGACY / YEDEK",
                        "details": "Birincil zeka DeepSeek V4.1 Flash'e, görsel denetim DeepSeek vizyona, video ise LTX-Video'ya devredildi. Gemini artık yalnızca eski yedek metin yolunda durur; Gemini ile video üretimi tamamen kaldırılmıştır."
                    },
                    {
                        "id": "svc_llm_evren",
                        "name": "DeepSeek V4.1 Flash (OpenCode/Evren Ağ Geçidi)",
                        "category": "Yapay Zeka & Bilişsel",
                        "provider": "OpenCode / Evren (OpenAI-uyumlu gateway)",
                        "role": "Birincil Metin Zekası: İnsan Dili İçerik, Reels Video Promptu ve Topluluk Yanıtları",
                        "endpoints": ["deepseek-v4.1-flash (reasoning: high)", "OpenAI-compatible /chat/completions"],
                        "protocols": ["HTTPS REST JSON (OpenAI API)"],
                        "status": "ACTIVE",
                        "badge": "DEEPSEEK V4.1 FLASH",
                        "details": "Tüm içerik metinleri buradan geçer: Instagram başlık/metin ve video promptları doğal, insan yazmış gibi üretilir; Gemini 3.8 Flash yalnızca yedek ve vizyon denetimi için devrede kalır."
                    },
                    {
                        "id": "ai_flux_image",
                        "name": "FLUX.1 [dev] Görsel Üretim Motoru (Yerel GPU)",
                        "category": "Yapay Zeka & Bilişsel",
                        "provider": "Black Forest Labs FLUX.1 [dev] • ComfyUI + GGUF Q8_0",
                        "role": "Post Görselleri İçin Fotogerçekçi AI Görsel Üretimi",
                        "endpoints": ["ComfyUI http://127.0.0.1:8188", "flux1-dev-Q8_0.gguf", "flux_dev_gguf_api.json"],
                        "protocols": ["Local HTTP API (ComfyUI /prompt & /history)"],
                        "status": "ACTIVE (GPU)",
                        "badge": "FLUX.1 [dev] Q8",
                        "details": "RTX 4060 Ti 16GB üzerinde yerel FLUX.1 [dev] (GGUF Q8_0, T5-XXL fp8 + CLIP-L + ae VAE) çalışır. Her post için 1024x1024 stüdyo görseli üretir; ürün postlarında gerçek ürün fotoğrafı bu AI arka planın üstüne bindirilir."
                    },
                    {
                        "id": "ai_ltx_video",
                        "name": "LTX-Video 0.9.8 Video Üretim Motoru (Yerel GPU)",
                        "category": "Yapay Zeka & Bilişsel",
                        "provider": "Lightricks LTXV 0.9.8 • ComfyUI Core LTXV Nodes",
                        "role": "Reels İçin Dikey (9:16) Metinden-Videoya AI Video Üretimi",
                        "endpoints": ["ComfyUI http://127.0.0.1:8188", "ltxv-13b-0.9.8-distilled-fp8.safetensors", "ltxv_t2v_api.json"],
                        "protocols": ["Local HTTP API (ComfyUI /prompt & /history)"],
                        "status": "ACTIVE (GPU)",
                        "badge": "LTX-VIDEO 0.9.8",
                        "details": "13B distilled FP8 checkpoint ile 576x1024 (9:16) sahneler üretir; 8 adımda ~97 kare. Animasyonlu WebP çıktısı ffmpeg ile marka katmanı bindirilerek 1080x1920 H.264 Reels MP4'e dönüştürülür. Slayt videolar kaldırıldı."
                    },
                    {
                        "id": "svc_paytr",
                        "name": "PayTR Sanal POS Ödeme Ağ Geçidi",
                        "category": "Ödeme Altyapısı",
                        "provider": "PayTR Ödeme Kuruluşu A.Ş.",
                        "role": "Güvenli 3D Secure Kredi / Banka Kartı Tahsilatı ve Callback Webhook Bildirimi",
                        "endpoints": ["https://api.pozitronmarket.com/api/paytr/token", "https://api.pozitronmarket.com/api/paytr/callback"],
                        "protocols": ["HTTPS REST / iFrame 3D Secure / HMAC-SHA256 Token"],
                        "status": "OPERATIONAL",
                        "badge": "3D SECURE POS",
                        "details": "Müşterinin sepet tutarını BDDK onaylı altyapıda güvenle tahsil eder. Troy, Visa, MasterCard taksit seçeneklerini destekler ve ödeme başarıyla tamamlandığında Hetzner API'ye anlık callback iletir."
                    },
                    {
                        "id": "svc_smtp",
                        "name": "SMTP İşlemsel E-Posta Sunucusu",
                        "category": "İşlemsel E-Posta",
                        "provider": "Google Workspace / Direct SMTP",
                        "role": "Sipariş Dekontu, Kargo Takip Bildirimi ve Yönetici Alarm Postaları",
                        "endpoints": ["smtp.gmail.com:587 (STARTTLS)", "noreply@pozitronmarkets.com"],
                        "protocols": ["SMTP over STARTTLS (Port 587)"],
                        "status": "OPERATIONAL",
                        "badge": "PORT 587 DIRECT",
                        "details": "Sipariş tamamlandığında müşteriye otomatik HTML e-posta dekontu ve kargo takip numarası gönderir. Hetzner Cloud port 587 doğrudan açık olduğundan gecikmesiz ve yüksek iletim oranlı çalışır."
                    },
                    {
                        "id": "svc_meta",
                        "name": "Meta Graph API (Instagram)",
                        "category": "Sosyal Medya & Topluluk",
                        "provider": "Meta Platforms Inc.",
                        "role": "Otonom Feed, Story & AI Reels Yayını, Haftalık Kupon Kampanyası ve Türk Drone Topluluğu Etkileşimi",
                        "endpoints": ["Graph API v18.0 (@pozitronmarket)", "ID: 17841430407836914"],
                        "protocols": ["HTTPS REST OAuth 2.0"],
                        "status": "OPERATIONAL",
                        "badge": "GRAPH API & AI REELS",
                        "details": "Pozitron'un içerik formatındaki 1080x1080 afişlerini ve marka katmanlı AI video Reels'lerini (LTX-Video 9:16) otomatik yayınlar, hikaye rotasyonunu ve haftalık 24 saatlik indirim kuponu duyurularını yürütür."
                    },
                    {
                        "id": "svc_reddit",
                        "name": "Reddit Web Otomasyonu",
                        "category": "Sosyal Medya & Topluluk",
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
                        "category": "Arama Motoru & SEO",
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
                        "category": "Veritabanı & Kalıcılık",
                        "provider": "Yerel Dosya Tabanlı ACID Veritabanı",
                        "role": "Ürün Kataloğu, Siparişler, Yorumlar, SEO Makaleleri ve Ajan Durumları",
                        "endpoints": ["pozitron.db (Hetzner VPS & Yerel)"],
                        "protocols": ["SQLite3 Native Socket"],
                        "status": "HEALTHY",
                        "badge": "ACID VERİTABANI",
                        "details": "508 ürün kaydı, siparişler, müşteri yorumları, fiyat takip logları, global trend önerileri ve Subagent 8 toptan sipariş planlarını güvenli ACID işlemleriyle saklar."
                    },
                    {
                        "id": "dns_ssl",
                        "name": "DNS & SSL Sertifikasyon Altyapısı",
                        "category": "Sunucu & Altyapı",
                        "provider": "Cloudflare / Let's Encrypt",
                        "role": "Alan Adı Yönlendirme, TLS 1.3 Şifreleme ve Otomatik SSL Yenileme",
                        "endpoints": ["pozitronmarket.com -> GitHub Pages", "api.pozitronmarket.com -> Hetzner VPS"],
                        "protocols": ["DNS (A / CNAME)", "TLS 1.3 / Let's Encrypt Certbot"],
                        "status": "OPERATIONAL",
                        "badge": "TLS 1.3 / SSL",
                        "details": "Root domain ve statik sayfaları GitHub Pages CDN sunucularına, 'api' alt alan adını ise Hetzner Cloud VPS IP adresine yönlendirir. Let's Encrypt Certbot ile tam uçtan uca SSL güvencesi sunar."
                    }
                ]
            }
            self.send_json(200, graph)
            return

        conn = get_db()
        cursor = conn.cursor()

        # Admin: Stats & KPI Metrics
        if path == '/api/admin/stats':
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(stock), 0), COALESCE(SUM(stock * price_usd), 0), COALESCE(SUM(stock * price_try), 0) FROM products")
            row = cursor.fetchone()
            total_products, total_stock, total_val_usd, total_val_try = row[0], row[1], row[2], row[3]

            cursor.execute("SELECT COUNT(*) FROM products WHERE stock <= 5 AND stock > 0")
            low_stock_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM products WHERE stock = 0")
            out_of_stock_count = cursor.fetchone()[0]

            cursor.execute('''
                SELECT c.id, c.name_en, c.name_tr, COUNT(p.id) as count, COALESCE(SUM(p.stock), 0) as category_stock
                FROM categories c
                LEFT JOIN products p ON c.id = p.category_id
                GROUP BY c.id
                ORDER BY count DESC
            ''')
            categories_stats = [dict(r) for r in cursor.fetchall()]
            conn.close()

            self.send_json(200, {
                "total_products": total_products,
                "total_stock": total_stock,
                "low_stock_count": low_stock_count,
                "out_of_stock_count": out_of_stock_count,
                "total_val_usd": round(total_val_usd, 2),
                "total_val_try": round(total_val_try, 2),
                "categories_stats": categories_stats
            })
            return

        # Admin: Products Inventory List with Search, Filter & Stock Status
        if path == '/api/admin/products':
            q = query.get('q', [''])[0].strip()
            cat = query.get('category', ['all'])[0]
            brand = query.get('brand', ['all'])[0]
            stock_status = query.get('stock_status', ['all'])[0]
            sort_by = query.get('sort', ['id_asc'])[0]
            page = max(1, int(query.get('page', [1])[0]))
            limit = min(2000, max(1, int(query.get('limit', [50])[0])))

            where_clauses = ["1=1"]
            params = []

            if q:
                where_clauses.append("(p.name_en LIKE ? OR p.name_tr LIKE ? OR p.brand LIKE ? OR p.sku LIKE ? OR p.id LIKE ?)")
                like_str = f"%{q}%"
                params.extend([like_str, like_str, like_str, like_str, like_str])

            if cat and cat != 'all':
                where_clauses.append("p.category_id = ?")
                params.append(cat)

            if brand and brand != 'all':
                where_clauses.append("p.brand = ?")
                params.append(brand)

            if stock_status == 'low_stock':
                where_clauses.append("p.stock <= 5 AND p.stock > 0")
            elif stock_status == 'out_of_stock':
                where_clauses.append("p.stock = 0")
            elif stock_status == 'in_stock':
                where_clauses.append("p.stock > 0")

            where_sql = " AND ".join(where_clauses)

            sort_map = {
                'id_asc': 'p.id ASC',
                'id_desc': 'p.id DESC',
                'stock_asc': 'p.stock ASC',
                'stock_desc': 'p.stock DESC',
                'price_usd_asc': 'p.price_usd ASC',
                'price_usd_desc': 'p.price_usd DESC',
                'price_try_asc': 'p.price_try ASC',
                'price_try_desc': 'p.price_try DESC',
                'name_asc': 'p.name_en ASC',
                'discount_desc': 'p.discount_pct DESC'
            }
            sort_sql = sort_map.get(sort_by, 'p.id ASC')

            count_query = f"SELECT COUNT(*) FROM products p WHERE {where_sql}"
            cursor.execute(count_query, params)
            total_items = cursor.fetchone()[0]

            offset = (page - 1) * limit
            data_query = f'''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE {where_sql}
                ORDER BY {sort_sql}
                LIMIT ? OFFSET ?
            '''
            cursor.execute(data_query, params + [limit, offset])
            rows = cursor.fetchall()
            products = []
            for r in rows:
                p = dict(r)
                p['specs'] = json.loads(p['specs_json']) if p.get('specs_json') else {}
                p['tags'] = json.loads(p['tags_json']) if p.get('tags_json') else []
                p['gallery'] = json.loads(p['gallery_json'] or '[]')
                p['compatibility'] = json.loads(p['compatibility_json'] or '{}')
                products.append(p)

            quality = product_quality.states(conn, products)
            for product in products:
                product.update(quality[product['id']])

            conn.close()
            self.send_json(200, {
                "products": products,
                "total": total_items,
                "page": page,
                "limit": limit,
                "total_pages": (total_items + limit - 1) // limit if limit > 0 else 1
            })
            return
        # Admin: Export Products to Excel (XML Spreadsheet 2003 format)
        if path == '/api/admin/products/export-excel':
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr
                FROM products p
                LEFT JOIN categories c ON p.category_id = c.id
                ORDER BY p.id ASC
            ''')
            rows = cursor.fetchall()
            conn.close()

            xml_lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<?mso-application progid="Excel.Sheet"?>',
                '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"',
                ' xmlns:o="urn:schemas-microsoft-com:office:office"',
                ' xmlns:x="urn:schemas-microsoft-com:office:excel"',
                ' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"',
                ' xmlns:html="http://www.w3.org/TR/REC-html40">',
                ' <Styles>',
                '  <Style ss:ID="Header">',
                '   <Font ss:Bold="1" ss:Color="#FFFFFF"/>',
                '   <Interior ss:Color="#107C41" ss:Pattern="Solid"/>',
                '   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>',
                '  </Style>',
                '  <Style ss:ID="Number">',
                '   <NumberFormat ss:Format="#,##0.00"/>',
                '  </Style>',
                '  <Style ss:ID="Integer">',
                '   <NumberFormat ss:Format="#,##0"/>',
                '  </Style>',
                '  <Style ss:ID="Center">',
                '   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>',
                '  </Style>',
                ' </Styles>',
                ' <Worksheet ss:Name="Ürünler">',
                '  <Table>',
            ]

            headers = [
                'Sıra No', 'Ürün ID', 'SKU', 'Ürün Adı (TR)', 'Ürün Adı (EN)',
                'Kategori', 'Marka', 'Fiyat (TRY)', 'Fiyat (USD)', 'Orijinal Fiyat (TRY)',
                'Orijinal Fiyat (USD)', 'İndirim (%)', 'Stok Adedi', 'Stok Durumu',
                'Rozet', 'Puan', 'Yorum Sayısı', 'Öne Çıkan', 'Çok Satan',
                'Ürün Linki', 'Görsel URL', 'Eklenme Tarihi'
            ]

            xml_lines.append('   <Row ss:StyleID="Header">')
            for h in headers:
                xml_lines.append(f'    <Cell><Data ss:Type="String">{html.escape(h)}</Data></Cell>')
            xml_lines.append('   </Row>')

            for idx, r in enumerate(rows, 1):
                p = dict(r)
                st = int(p.get('stock') or 0)
                st_status = 'Tükendi' if st == 0 else ('Kritik Stok' if st <= 5 else 'Stokta Var')
                slug = p.get('slug') or ''
                url = f"https://pozitronmarket.com/products/{slug}" if slug else ""
                cat_name = p.get('category_name_tr') or p.get('category_id') or ''

                xml_lines.append('   <Row>')
                xml_lines.append(f'    <Cell ss:StyleID="Integer"><Data ss:Type="Number">{idx}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Center"><Data ss:Type="String">{html.escape(p.get("id") or "")}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Center"><Data ss:Type="String">{html.escape(p.get("sku") or "")}</Data></Cell>')
                xml_lines.append(f'    <Cell><Data ss:Type="String">{html.escape(p.get("name_tr") or p.get("name_en") or "")}</Data></Cell>')
                xml_lines.append(f'    <Cell><Data ss:Type="String">{html.escape(p.get("name_en") or p.get("name_tr") or "")}</Data></Cell>')
                xml_lines.append(f'    <Cell><Data ss:Type="String">{html.escape(cat_name)}</Data></Cell>')
                xml_lines.append(f'    <Cell><Data ss:Type="String">{html.escape(p.get("brand") or "Pozitron")}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Number"><Data ss:Type="Number">{float(p.get("price_try") or 0):.2f}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Number"><Data ss:Type="Number">{float(p.get("price_usd") or 0):.2f}</Data></Cell>')
                orig_try = f'{float(p["original_price_try"]):.2f}' if p.get("original_price_try") else ''
                orig_usd = f'{float(p["original_price_usd"]):.2f}' if p.get("original_price_usd") else ''
                if orig_try:
                    xml_lines.append(f'    <Cell ss:StyleID="Number"><Data ss:Type="Number">{orig_try}</Data></Cell>')
                else:
                    xml_lines.append('    <Cell><Data ss:Type="String"></Data></Cell>')
                if orig_usd:
                    xml_lines.append(f'    <Cell ss:StyleID="Number"><Data ss:Type="Number">{orig_usd}</Data></Cell>')
                else:
                    xml_lines.append('    <Cell><Data ss:Type="String"></Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Integer"><Data ss:Type="Number">{int(p.get("discount_pct") or 0)}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Integer"><Data ss:Type="Number">{st}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Center"><Data ss:Type="String">{st_status}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Center"><Data ss:Type="String">{html.escape(p.get("badge") or "")}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Number"><Data ss:Type="Number">{float(p.get("rating") or 5.0):.1f}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Integer"><Data ss:Type="Number">{int(p.get("review_count") or 0)}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Center"><Data ss:Type="String">{"Evet" if p.get("featured") else "Hayır"}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Center"><Data ss:Type="String">{"Evet" if p.get("is_bestseller") else "Hayır"}</Data></Cell>')
                xml_lines.append(f'    <Cell><Data ss:Type="String">{html.escape(url)}</Data></Cell>')
                xml_lines.append(f'    <Cell><Data ss:Type="String">{html.escape(p.get("image_url") or "")}</Data></Cell>')
                xml_lines.append(f'    <Cell ss:StyleID="Center"><Data ss:Type="String">{html.escape(p.get("created_at") or "")}</Data></Cell>')
                xml_lines.append('   </Row>')

            xml_lines.extend([
                '  </Table>',
                ' </Worksheet>',
                '</Workbook>'
            ])

            xml_bytes = "\n".join(xml_lines).encode('utf-8')
            today_str = datetime.now().strftime("%Y-%m-%d")
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.ms-excel; charset=utf-8')
            self.send_header('Content-Disposition', f'attachment; filename="pozitron_urunler_{today_str}.xls"')
            self.send_header('Content-Length', str(len(xml_bytes)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(xml_bytes)
            return

        # Admin: Registered Users List
        if path == '/api/admin/users':
            cursor.execute('''
                SELECT id, email, full_name, avatar_url, provider, role, phone, address, city, country, created_at 
                FROM users 
                ORDER BY created_at DESC
            ''')
            user_rows = [dict(r) for r in cursor.fetchall()]
            conn.close()
            self.send_json(200, {"users": user_rows, "total": len(user_rows)})
            return

        # 1. Categories
        if path == '/api/categories':
            cursor.execute("SELECT * FROM categories ORDER BY item_count DESC")
            categories = [dict(row) for row in cursor.fetchall()]
            conn.close()
            self.send_json(200, {"categories": categories})
            return

        # 2. Brands list
        if path == '/api/brands':
            cat = query.get('category', [None])[0]
            if cat and cat != 'all':
                cursor.execute("SELECT DISTINCT brand FROM products WHERE category_id = ? ORDER BY brand ASC", (cat,))
            else:
                cursor.execute("SELECT DISTINCT brand FROM products ORDER BY brand ASC")
            brands = [r[0] for r in cursor.fetchall()]
            conn.close()
            self.send_json(200, {"brands": brands})
            return

        # 3. Single Product: /api/products/<id_or_slug>
        prod_match = re.match(r'^/api/products/(.+)$', path)
        if prod_match:
            item_id = urllib.parse.unquote(prod_match.group(1)).strip()
            cursor.execute('''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.id = ? OR p.slug = ? OR p.sku = ?
            ''', (item_id, item_id, item_id))
            row = cursor.fetchone()
            if not row:
                conn.close()
                self.send_json(404, {"error": "Product not found"})
                return

            prod = dict(row)
            prod['specs'] = json.loads(prod['specs_json'])
            prod['tags'] = json.loads(prod['tags_json'])
            prod['gallery'] = json.loads(prod['gallery_json'] or '[]')
            prod['compatibility'] = json.loads(prod['compatibility_json'] or '{}')

            # Fetch product reviews
            cursor.execute("SELECT * FROM reviews WHERE product_id = ? AND deleted_at IS NULL ORDER BY created_at DESC", (prod['id'],))
            reviews = [dict(r) for r in cursor.fetchall()]
            prod['reviews'] = reviews

            # Fetch related items
            cursor.execute('''
                SELECT id, slug, sku, name_en, name_tr, category_id, brand, price_usd, price_try, rating, review_count, stock, badge, image_url
                FROM products
                WHERE category_id = ? AND id != ?
                ORDER BY rating DESC LIMIT 6
            ''', (prod['category_id'], prod['id']))
            prod['related'] = [dict(r) for r in cursor.fetchall()]

            conn.close()
            self.send_json(200, {"product": prod})
            return

        # 4. Products List (Search, Filter, Pagination, Sort)
        if path == '/api/products':
            q = query.get('q', [''])[0].strip()
            cat = query.get('category', ['all'])[0]
            brand = query.get('brand', ['all'])[0]
            voltage = query.get('voltage', ['all'])[0]
            in_stock = query.get('in_stock', ['0'])[0]
            featured_only = query.get('featured', ['0'])[0]
            bestseller_only = query.get('bestseller', ['0'])[0]
            sort_by = query.get('sort', ['popular'])[0]
            page = max(1, int(query.get('page', [1])[0]))
            limit = min(100, max(1, int(query.get('limit', [24])[0])))
            min_p = float(query.get('min_price', [0])[0])
            max_p = float(query.get('max_price', [99999])[0])
            currency = query.get('currency', ['USD'])[0].upper()

            where_clauses = ["1=1"]
            params = []

            if q:
                where_clauses.append("(p.name_en LIKE ? OR p.name_tr LIKE ? OR p.brand LIKE ? OR p.sku LIKE ? OR p.tags_json LIKE ?)")
                like_str = f"%{q}%"
                params.extend([like_str, like_str, like_str, like_str, like_str])

            if cat and cat != 'all':
                where_clauses.append("p.category_id = ?")
                params.append(cat)

            if brand and brand != 'all':
                where_clauses.append("p.brand = ?")
                params.append(brand)

            if voltage and voltage != 'all':
                where_clauses.append("p.specs_json LIKE ?")
                params.append(f"%{voltage}%")

            if in_stock == '1':
                where_clauses.append("p.stock > 0")

            if featured_only == '1':
                where_clauses.append("p.featured = 1")

            if bestseller_only == '1':
                where_clauses.append("p.is_bestseller = 1")

            # Price filter
            if currency == 'TRY':
                where_clauses.append("p.price_try >= ? AND p.price_try <= ?")
                params.extend([min_p, max_p])
            else:
                where_clauses.append("p.price_usd >= ? AND p.price_usd <= ?")
                params.extend([min_p, max_p])

            where_sql = " AND ".join(where_clauses)

            # Sort mappings
            sort_sql = "p.rating DESC, p.review_count DESC"
            if sort_by == 'price_asc':
                sort_sql = "p.price_usd ASC" if currency == 'USD' else "p.price_try ASC"
            elif sort_by == 'price_desc':
                sort_sql = "p.price_usd DESC" if currency == 'USD' else "p.price_try DESC"
            elif sort_by == 'rating':
                sort_sql = "p.rating DESC, p.review_count DESC"
            elif sort_by == 'newest':
                sort_sql = "p.created_at DESC"
            elif sort_by == 'discount':
                sort_sql = "p.discount_pct DESC"

            # Total Count Query
            count_query = f"SELECT COUNT(*) FROM products p WHERE {where_sql}"
            cursor.execute(count_query, params)
            total_items = cursor.fetchone()[0]

            # Paginated Data Query
            offset = (page - 1) * limit
            data_query = f'''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE {where_sql}
                ORDER BY {sort_sql}
                LIMIT ? OFFSET ?
            '''
            cursor.execute(data_query, params + [limit, offset])
            rows = cursor.fetchall()
            products = []
            for r in rows:
                p = dict(r)
                p['specs'] = json.loads(p['specs_json'])
                p['tags'] = json.loads(p['tags_json'])
                p['gallery'] = json.loads(p['gallery_json'] or '[]')
                products.append(p)

            conn.close()
            self.send_json(200, {
                "products": products,
                "total": total_items,
                "page": page,
                "limit": limit,
                "total_pages": (total_items + limit - 1) // limit
            })
            return

        # 4b. User Addresses List: /api/user/addresses?user_id=...
        if path == '/api/user/addresses':
            uid = query.get('user_id', [''])[0].strip()
            if not uid:
                auth_user = self.get_authenticated_user()
                if auth_user:
                    uid = auth_user.get('uid') or auth_user.get('id')
            if not uid:
                conn.close()
                self.send_json(400, {"error": "user_id is required."})
                return
            cursor.execute("SELECT * FROM user_addresses WHERE user_id = ? ORDER BY is_default_shipping DESC, created_at DESC", (uid,))
            addresses = [dict(r) for r in cursor.fetchall()]
            conn.close()
            self.send_json(200, {"success": True, "addresses": addresses})
            return

        # 5. Orders Query / List: /api/orders (supports ?email=... or ?user_id=...)
        if path == '/api/orders':
            user_id = query.get('user_id', [''])[0].strip()
            email = query.get('email', [''])[0].strip().lower()
            if user_id or email:
                cursor.execute("SELECT * FROM orders WHERE (user_id = ? AND ? != '') OR (LOWER(customer_email) = ? AND ? != '') ORDER BY created_at DESC",
                               (user_id, user_id, email, email))
            else:
                cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50")
            orders = []
            for r in cursor.fetchall():
                od = dict(r)
                try:
                    od['items'] = json.loads(od['items_json'])
                except:
                    od['items'] = []
                od['status'] = od.get('order_status') or od.get('status') or 'CONFIRMED'
                orders.append(od)
            conn.close()
            self.send_json(200, {"orders": orders})
            return

        # 5b. Order lookup: /api/orders/<order_number>
        order_match = re.match(r'^/api/orders/([a-zA-Z0-9_-]+)$', path)
        if order_match:
            order_num = order_match.group(1)
            cursor.execute("SELECT * FROM orders WHERE order_number = ? OR id = ?", (order_num, order_num))
            order = cursor.fetchone()
            conn.close()
            if not order:
                self.send_json(404, {"error": "Order not found"})
                return
            od = dict(order)
            try:
                od['items'] = json.loads(od['items_json'])
            except:
                od['items'] = []
            od['status'] = od.get('order_status') or od.get('status') or 'CONFIRMED'
            self.send_json(200, {"order": od})
            return

        # 6. User Orders: /api/orders/user/<user_id>
        user_orders_match = re.match(r'^/api/orders/user/([a-zA-Z0-9_-]+)$', path)
        if user_orders_match:
            user_id = user_orders_match.group(1)
            cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
            orders = []
            for r in cursor.fetchall():
                od = dict(r)
                try:
                    od['items'] = json.loads(od['items_json'])
                except:
                    od['items'] = []
                od['status'] = od.get('order_status') or od.get('status') or 'CONFIRMED'
                orders.append(od)
            conn.close()
            self.send_json(200, {"orders": orders})
            return

        # 7. Admin All Orders: /api/admin/orders
        if path == '/api/admin/orders':
            cursor.execute("SELECT * FROM orders ORDER BY created_at DESC")
            orders = []
            for r in cursor.fetchall():
                od = dict(r)
                try:
                    od['items'] = json.loads(od['items_json'])
                except:
                    od['items'] = []
                od['status'] = od.get('order_status') or od.get('status') or 'CONFIRMED'
                orders.append(od)
            conn.close()
            self.send_json(200, {"orders": orders})
            return

        # Authenticated comment moderation, including recoverable deleted reviews.
        if path == '/api/admin/reviews':
            try:
                page = max(1, int(query.get('page', ['1'])[0]))
                limit = min(100, max(1, int(query.get('limit', ['20'])[0])))
                search = query.get('search', [''])[0].strip()
                deleted = query.get('status', ['active'])[0] == 'deleted'
                where = ['r.deleted_at IS NOT NULL' if deleted else 'r.deleted_at IS NULL']
                params = []
                if search:
                    where.append('(r.user_name LIKE ? OR r.title LIKE ? OR r.comment LIKE ? OR p.name_tr LIKE ?)')
                    params.extend(['%' + search + '%'] * 4)
                clause = ' AND '.join(where)
                cursor.execute(f'SELECT COUNT(*) FROM reviews r LEFT JOIN products p ON p.id = r.product_id WHERE {clause}', params)
                total = cursor.fetchone()[0]
                cursor.execute(f"SELECT r.*, p.name_tr AS product_name FROM reviews r LEFT JOIN products p ON p.id = r.product_id WHERE {clause} ORDER BY r.created_at DESC, r.id DESC LIMIT ? OFFSET ?", params + [limit, (page - 1) * limit])
                self.send_json(200, {'reviews': [dict(row) for row in cursor.fetchall()], 'total': total, 'page': page, 'limit': limit})
            except ValueError:
                self.send_json(400, {'error': 'Geçersiz sayfa bilgisi.'})
            finally:
                conn.close()
            return

        # 8. Reviews List: /api/reviews
        if path == '/api/reviews':
            try:
                prod_id = query.get('product_id', [''])[0].strip()
                filter_type = query.get('filter', ['all'])[0].strip()
                limit = min(1000, max(1, int(query.get('limit', [50])[0])))

                where_clauses = ["deleted_at IS NULL"]
                params = []

                if prod_id and prod_id != 'general':
                    where_clauses.append("(product_id = ? OR product_id IN (SELECT id FROM products WHERE slug = ?))")
                    params.extend([prod_id, prod_id])

                if filter_type == '5star':
                    where_clauses.append("rating >= 5")
                elif filter_type == 'verified':
                    where_clauses.append("verified_purchase = 1")

                where_sql = " AND ".join(where_clauses)
                cursor.execute(f"SELECT * FROM reviews WHERE {where_sql} ORDER BY created_at DESC LIMIT ?", params + [limit])
                reviews = [dict(r) for r in cursor.fetchall()]

                stats = None
                if prod_id and prod_id != 'general':
                    cursor.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE deleted_at IS NULL AND (product_id = ? OR product_id IN (SELECT id FROM products WHERE slug = ?))", (prod_id, prod_id))
                    avg_r, cnt_r = cursor.fetchone()
                    stats = {
                        "rating": round(avg_r, 1) if avg_r is not None else 0.0,
                        "count": cnt_r or 0
                    }

                self.send_json(200, {"reviews": reviews, "stats": stats})
                return
            finally:
                conn.close()

        # Admin: Coupon management (list, redemptions, logs)
        if path == '/api/admin/coupons':
            conn.close()
            try:
                coupons = coupon_service.list_coupons()
                self.send_json(200, {
                    "coupons": coupons,
                    "active_deal": coupon_service.get_active_deal(),
                })
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == '/api/admin/coupons/redemptions':
            conn.close()
            code = (query.get('code', [None])[0] or None)
            try:
                limit = int(query.get('limit', ['200'])[0])
            except Exception:
                limit = 200
            try:
                self.send_json(200, {"redemptions": coupon_service.get_redemptions(code, limit)})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == '/api/admin/coupons/logs':
            conn.close()
            code = (query.get('code', [None])[0] or None)
            try:
                limit = int(query.get('limit', ['300'])[0])
            except Exception:
                limit = 300
            try:
                self.send_json(200, {"logs": coupon_service.get_logs(code, limit)})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        conn.close()
        self.send_json(404, {"error": "API route not found"})

    def handle_api_post(self, path, data):
        # Security: Protected Admin & Autonomous Agent endpoints require verified admin credentials
        if (path.startswith('/api/admin/') or 
            path.startswith('/api/instagram/') or 
            path.startswith('/api/reddit/') or 
            path.startswith('/api/lead-supervisor/') or 
            path.startswith('/api/qa-agent/') or 
            path.startswith('/api/agent/')):
            if not self.require_admin():
                return

        # Admin: Coupon create
        if path == '/api/admin/coupons/create':
            try:
                from datetime import timedelta
                code = data.get('code', '').strip().upper()
                discount_type = data.get('discount_type', 'percent')
                discount_value = data.get('discount_value', 0)
                min_order_try = data.get('min_order_try', 0) or 0
                min_order_usd = data.get('min_order_usd', 0) or 0
                description_tr = data.get('description_tr', '')
                description_en = data.get('description_en', '')
                max_uses = data.get('max_uses')
                per_user_limit = data.get('per_user_limit', 1)
                valid_hours = data.get('valid_hours')
                expires_at = data.get('expires_at')
                starts_at = data.get('starts_at') or datetime.now().isoformat()
                if not expires_at and valid_hours:
                    expires_at = (datetime.now() + timedelta(hours=float(valid_hours))).isoformat()
                created = coupon_service.create_coupon(
                    code, discount_type, discount_value,
                    min_order_usd=min_order_usd, min_order_try=min_order_try,
                    description_tr=description_tr, description_en=description_en,
                    starts_at=starts_at, expires_at=expires_at,
                    max_uses=max_uses, per_user_limit=per_user_limit,
                    source='manual', actor='admin',
                )
                self.send_json(200, {"success": True, "code": created,
                                     "coupon": coupon_service.get_coupon(created)})
            except ValueError as ve:
                self.send_json(400, {"success": False, "error": str(ve)})
            except Exception as e:
                self.send_json(500, {"success": False, "error": str(e)})
            return

        # Admin: Coupon update
        if path == '/api/admin/coupons/update':
            try:
                code = data.get('code', '').strip().upper()
                fields = {}
                for k in ('discount_type', 'discount_value', 'min_order_usd', 'min_order_try',
                          'description_tr', 'description_en', 'starts_at', 'expires_at',
                          'max_uses', 'per_user_limit', 'is_active'):
                    if k in data:
                        fields[k] = data.get(k)
                if data.get('valid_hours') and not fields.get('expires_at'):
                    from datetime import timedelta
                    fields['expires_at'] = (datetime.now() + timedelta(hours=float(data['valid_hours']))).isoformat()
                coupon_service.update_coupon(code, actor='admin', **fields)
                self.send_json(200, {"success": True, "coupon": coupon_service.get_coupon(code)})
            except ValueError as ve:
                self.send_json(400, {"success": False, "error": str(ve)})
            except Exception as e:
                self.send_json(500, {"success": False, "error": str(e)})
            return

        # Admin: Coupon activate/deactivate
        if path == '/api/admin/coupons/toggle':
            try:
                code = data.get('code', '').strip().upper()
                active = bool(data.get('active', True))
                coupon_service.set_coupon_active(code, active, actor='admin')
                self.send_json(200, {"success": True, "code": code, "is_active": 1 if active else 0})
            except Exception as e:
                self.send_json(500, {"success": False, "error": str(e)})
            return

        # Admin: Coupon delete
        if path == '/api/admin/coupons/delete':
            try:
                code = data.get('code', '').strip().upper()
                coupon_service.delete_coupon(code, actor='admin')
                self.send_json(200, {"success": True, "code": code})
            except Exception as e:
                self.send_json(500, {"success": False, "error": str(e)})
            return

        # Admin: Create this week's one-day deal (and optionally publish it to Instagram)
        if path == '/api/admin/coupons/weekly-deal':
            try:
                deal = coupon_service.create_weekly_deal(template=data.get('template') or {})
                publish = bool(data.get('publish', False))
                result = {"success": True, "deal": deal}
                if publish and deal:
                    try:
                        pr = instagram_pr_agent.generate_and_publish_deal_coupon(deal=deal)
                        result['instagram'] = pr
                    except Exception as ie:
                        result['instagram'] = {"success": False, "error": str(ie)}
                self.send_json(200, result)
            except Exception as e:
                self.send_json(500, {"success": False, "error": str(e)})
            return

        # Instagram PR: Update Config
        if path == '/api/instagram/config':
            try:
                updated = instagram_pr_agent.update_config(data)
                self.send_json(200, {"success": True, "config": updated})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Generate Sample / Preview Post (Does NOT Publish)
        if path == '/api/instagram/preview-post':
            content_type = data.get('content_type')
            product_id = data.get('product_id')
            use_flux = data.get('use_flux')
            allowed_types = data.get('allowed_types')
            try:
                result = instagram_pr_agent.generate_preview_post(
                    content_type=content_type,
                    product_id=product_id,
                    use_flux=use_flux,
                    allowed_types=allowed_types
                )
                status_code = 200 if result.get('success') else 400
                self.send_json(status_code, result)
            except Exception as e:
                self.send_json(500, {"success": False, "error": str(e)})
            return

        # Instagram PR: Direct Generate & Publish (No Drafts)
        if path in ('/api/instagram/direct-publish', '/api/instagram/generate', '/api/instagram/publish'):
            content_type = data.get('content_type')
            product_id = data.get('product_id')
            post_id = data.get('id')
            use_flux = data.get('use_flux')
            allowed_types = data.get('allowed_types')
            try:
                if post_id:
                    result = instagram_pr_agent.publish_post(post_id=post_id)
                else:
                    # Direct generation and instant publish without leftover draft
                    result = instagram_pr_agent.generate_and_publish_now(
                        content_type=content_type,
                        product_id=product_id,
                        use_flux=use_flux,
                        allowed_types=allowed_types
                    )
                status_code = 200 if result.get('success') else 400
                self.send_json(status_code, result)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Publish Carousel
        if path == '/api/instagram/publish-carousel':
            content_type = data.get('content_type', 'carousel_guide')
            product_id = data.get('product_id')
            try:
                result = instagram_pr_agent.generate_and_publish_carousel(content_type=content_type, product_id=product_id)
                status_code = 200 if result.get('success') else 400
                self.send_json(status_code, result)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Publish Story
        if path == '/api/instagram/publish-story':
            try:
                result = instagram_pr_agent.generate_and_publish_story(data.get('post_data'))
                status_code = 200 if result.get('success') else 400
                self.send_json(status_code, result)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Publish Reel
        if path == '/api/instagram/publish-reel':
            try:
                result = instagram_pr_agent.generate_and_publish_reel(data.get('post_data'))
                status_code = 200 if result.get('success') else 400
                self.send_json(status_code, result)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Generate Reel (Local LTX-Video AI Video or ffmpeg fallback, no publish)
        if path == '/api/instagram/generate-reel':
            try:
                import uuid as _uuid
                post_id = f"ig_reel_{_uuid.uuid4().hex[:12]}"
                product_id = data.get('product_id')
                content_type = data.get('content_type')
                reels_type = data.get('reels_type')
                allowed_reels_types = data.get('allowed_reels_types')

                if content_type:
                    content = instagram_pr_agent.content_gen.generate_content(
                        content_type=content_type, product_id=product_id
                    )
                else:
                    # Respect reels_type and allowed_reels_types
                    content = instagram_pr_agent.content_gen.generate_reels_content(
                        product_id=product_id,
                        allowed_reels_types=allowed_reels_types,
                        reels_type=reels_type
                    )

                if not content:
                    self.send_json(400, {"success": False, "error": "Reels icerigi uretilemedi."})
                    return

                content_type = content.get('content_type', 'product_spotlight')
                chosen_reels_type = content.get('reels_type') or reels_type
                explicit_engine = data.get('engine')
                reels_method = data.get('reels_method', 'multi_shot')
                if chosen_reels_type == 'real_fpv_broll' or explicit_engine == 'mode2':
                    engine = 'mode2'
                elif explicit_engine and explicit_engine not in ('random', 'creative', None):
                    # Gemini video is retired: any AI/legacy request maps to local LTX.
                    engine = 'ltx' if explicit_engine in ('gemini', 'ai', 'creative', 'random') else explicit_engine
                else:
                    # Default Reels engine is the local AI video generator (LTX).
                    engine = 'ltx'
                post_data = {
                    'id': post_id,
                    'content_type': content_type,
                    'reels_type': chosen_reels_type,
                    'allowed_reels_types': allowed_reels_types,
                    'title': content['title'],
                    'caption': content['caption'],
                    'hashtags': content['hashtags'],
                    'product_data': content.get('product_data'),
                    'visual_summary': content.get('visual_summary'),
                    'visual_style': content.get('visual_style'),
                    'video_mode': content.get('video_mode'),
                    'reel_combo': content.get('reel_combo'),
                    'hook_tone': content.get('hook_tone'),
                    'media_type': 'REEL',
                    'engine': engine,
                    'reels_method': reels_method,
                    'created_at': __import__('datetime').datetime.now().isoformat()
                }
                post_data['metadata'] = {
                    'reels_type': chosen_reels_type,
                    'reel_combo': content.get('reel_combo'),
                    'visual_style': content.get('visual_style'),
                    'video_mode': content.get('video_mode'),
                    'hook_tone': content.get('hook_tone'),
                    'reels_method': reels_method
                }

                video_prompt = instagram_pr_agent.content_gen.generate_reels_video_prompt(post_data)
                post_data['video_prompt'] = video_prompt
                video_rel_path = instagram_pr_agent.image_gen.generate_reels_video(post_data, prompt=video_prompt)

                if video_rel_path:
                    from instagram_agent.db import save_instagram_post
                    post_data['video_url'] = video_rel_path
                    post_data['local_image_path'] = video_rel_path
                    post_data['image_url'] = video_rel_path
                    post_data['status'] = 'draft'
                    save_instagram_post(post_data)
                    clean_video_url = '/' + video_rel_path.lstrip('./')
                    self.send_json(200, {
                        "success": True,
                        "post_id": post_id,
                        "video_path": clean_video_url,
                        "video_engine": post_data.get('video_engine', 'unknown'),
                        "video_duration": post_data.get('video_duration', 0.0),
                        "reels_method": post_data.get('reels_method', reels_method),
                        "reels_method_info": post_data.get('reels_method_info', ''),
                        "reel_mode": post_data.get('reel_mode', ''),
                        "reel_mode_info": post_data.get('reel_mode_info', ''),
                        "fallback_reason": post_data.get('fallback_reason', ''),
                        "video_prompt": post_data.get('video_prompt', ''),
                        "title": post_data['title'],
                        "caption": post_data['caption']
                    })
                else:
                    self.send_json(400, {"success": False, "error": "Video olusturulamadi."})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Process Comment & DM Automations
        if path == '/api/instagram/process-dms':
            test_comments = data.get('test_comments')
            try:
                result = instagram_pr_agent.process_comment_automations(test_comments=test_comments)
                status_code = 200 if result.get('success') else 400
                self.send_json(status_code, result)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Run Drone Community Engagement (10 Follows, 10 Comments & 10 Likes)
        if path == '/api/instagram/engage':
            try:
                engine = InstagramEngagementEngine(gemini_api_key=instagram_pr_agent.config.get('gemini_api_key'))
                target_count = int(data.get('target_count', 10))
                result = engine.run_daily_drone_engagement(target_count=target_count)
                status_code = 200 if result.get('success') else 400
                self.send_json(status_code, result)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Multimodal Image Quality Audit (Gemini 3.8 Flash Vision)
        if path == '/api/instagram/audit-image':
            image_path = data.get('image_path')
            post_id = data.get('post_id')
            if not image_path and post_id:
                post = get_instagram_post_by_id(post_id)
                if post:
                    image_path = post.get('local_image_path') or post.get('image_url')
            if not image_path:
                self.send_json(400, {"error": "image_path or post_id required"})
                return
            try:
                gemini_key = instagram_pr_agent.config.get('gemini_api_key') or os.environ.get('GEMINI_API_KEY', '')
                audit_res = instagram_pr_agent.image_gen.audit_generated_image(image_path, gemini_api_key=gemini_key)
                self.send_json(200, {"success": True, "audit": audit_res})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Instagram PR: Toggle Autonomous Scheduler
        if path == '/api/instagram/toggle':
            enabled = bool(data.get('enabled'))
            instagram_pr_agent.update_config({'is_autonomous_enabled': 1 if enabled else 0})
            if enabled:
                instagram_pr_scheduler.start()
            else:
                instagram_pr_scheduler.stop()
            self.send_json(200, {"success": True, "is_autonomous_enabled": enabled})
            return

        # Instagram PR: Sync from Chrome Session
        if path == '/api/instagram/chrome-session/sync':
            try:
                session_info = extract_chrome_instagram_cookies()
                if session_info.get('success'):
                    # Save user_id into config
                    updated = instagram_pr_agent.update_config({
                        'instagram_account_id': session_info['user_id']
                    })
                    self.send_json(200, {
                        "success": True,
                        "user_id": session_info['user_id'],
                        "config": updated,
                        "message": f"Chrome Instagram hesabı (ID: {session_info['user_id']}) başarıyla ajana bağlandı!"
                    })
                else:
                    self.send_json(400, {
                        "success": False,
                        "error": session_info.get('error', 'Chrome oturumu okunamadı')
                    })
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Reddit Drone Bot: Update Config
        if path == '/api/reddit/config':
            try:
                updated = reddit_drone_agent.update_config(data)
                self.send_json(200, {"success": True, "config": updated})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Reddit Drone Bot: Manual Scan Trigger (Autonomous execution)
        if path == '/api/reddit/scan':
            try:
                res = reddit_drone_agent.scan_and_process(autonomous=True)
                self.send_json(200, {"success": True, "result": res})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Reddit Drone Bot: Seed Sample Questions
        if path == '/api/reddit/seed':
            try:
                count = reddit_drone_agent.seed_sample_questions()
                self.send_json(200, {"success": True, "count": count})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Reddit Drone Bot: Approve / Publish Reply
        if path == '/api/reddit/reply/approve':
            try:
                data = json.loads(self.get_post_body())
                interaction_id = data.get("interaction_id") or data.get("id")
                res = reddit_drone_agent.approve_reply(interaction_id)
                self.send_json(200, res)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Reddit Drone Bot: Reject Reply
        if path == '/api/reddit/reply/reject':
            try:
                data = json.loads(self.get_post_body())
                interaction_id = data.get("interaction_id") or data.get("id")
                success = reddit_drone_agent.reject_reply(interaction_id)
                self.send_json(200, {"success": success})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Reddit Drone Bot: Edit Reply
        if path == '/api/reddit/reply/edit':
            try:
                data = json.loads(self.get_post_body())
                interaction_id = data.get("interaction_id") or data.get("id")
                text = data.get("text", "")
                success = reddit_drone_agent.edit_reply(interaction_id, text)
                self.send_json(200, {"success": success})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Reddit Drone Bot: Regenerate Reply with Gemini
        if path == '/api/reddit/reply/generate':
            try:
                data = json.loads(self.get_post_body())
                interaction_id = data.get("interaction_id") or data.get("id")
                res = reddit_drone_agent.regenerate_reply(interaction_id)
                self.send_json(200, res)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Reddit Drone Bot: Toggle Autonomous Mode
        if path == '/api/reddit/toggle':
            data = json.loads(self.get_post_body())
            enabled = bool(data.get("enabled", True))
            reddit_drone_agent.update_config({'is_autonomous_enabled': 1 if enabled else 0})
            if enabled:
                reddit_drone_scheduler.start()
            else:
                reddit_drone_scheduler.stop()
            self.send_json(200, {"success": True, "is_autonomous_enabled": enabled})
            return

        # Reddit Drone Bot: Sync Chrome Session
        if path in ('/api/reddit/chrome-session/sync', '/api/reddit/sync-chrome'):
            try:
                res = reddit_drone_agent.sync_chrome_session()
                self.send_json(200, res)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Reddit Drone Bot: Enable Full Autopilot
        if path == '/api/reddit/auto-pilot':
            try:
                res = reddit_drone_agent.enable_full_automation()
                self.send_json(200, res)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Lead Supervisor: Trigger 2-Hour Orchestration Cycle Now
        if path == '/api/supervisor/run':
            try:
                directive = lead_supervisor_agent.execute_cycle()
                self.send_json(200, {"success": True, "directive": directive})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Lead Supervisor: Trigger 12-Hour Autonomous Evolution & Self-Optimization
        if path == '/api/supervisor/evolve':
            try:
                evolution = lead_supervisor_agent.evolve_strategy_cycle()
                self.send_json(200, {"success": True, "evolution": evolution})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 6: Scan Global Product Trends
        if path == '/api/trend-hunter/scan':
            try:
                limit = int(data.get("limit", 5))
                added = lead_supervisor_agent.trend_agent.scan_global_trends(limit=limit)
                proposals = lead_supervisor_agent.trend_agent.get_proposals(limit=20)
                self.send_json(200, {"success": True, "new_trends_found": len(added), "proposals": proposals})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 6: Approve Trend Proposal & Add to Catalog
        if path == '/api/trend-hunter/approve':
            try:
                proposal_id = data.get("proposal_id")
                if not proposal_id:
                    self.send_json(400, {"error": "proposal_id is required"})
                    return
                evaluator = data.get("evaluator", "OPERATOR_ADMIN")
                res = lead_supervisor_agent.trend_agent.approve_and_add_product(proposal_id, evaluator=evaluator)
                self.send_json(200, res)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 6: Reject Trend Proposal
        if path == '/api/trend-hunter/reject':
            try:
                proposal_id = data.get("proposal_id")
                if not proposal_id:
                    self.send_json(400, {"error": "proposal_id is required"})
                    return
                reason = data.get("reason", "Operator rejected")
                res = lead_supervisor_agent.trend_agent.reject_proposal(proposal_id, reason=reason)
                self.send_json(200, res)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 6: Scan Store Products Against Turkey Market Prices
        if path == '/api/trend-hunter/scan-prices':
            try:
                limit = data.get("limit")
                if limit is not None:
                    limit = int(limit)
                auto_update = bool(data.get("auto_update", True))
                res = lead_supervisor_agent.trend_agent.scan_store_price_comparison(limit=limit, auto_update_too_cheap=auto_update)
                self.send_json(200, res)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 6: Update Product Price from Trend Hunter Warning Action
        if path == '/api/trend-hunter/update-product-price':
            try:
                sku = data.get("sku")
                new_price_try = data.get("new_price_try")
                if not sku or new_price_try is None:
                    self.send_json(400, {"error": "sku and new_price_try are required"})
                    return
                new_price_try = float(new_price_try)
                res = lead_supervisor_agent.trend_agent.update_product_price(sku=sku, new_price_try=new_price_try)
                self.send_json(200, res)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Lead Supervisor: Toggle Autonomous Mode
        if path == '/api/supervisor/toggle':
            try:
                enabled = bool(data.get("enabled", True))
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE lead_supervisor_config SET is_autonomous_enabled = ?, updated_at = ? WHERE id = 1", (1 if enabled else 0, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                if enabled:
                    supervisor_scheduler.start()
                else:
                    supervisor_scheduler.stop()
                self.send_json(200, {"success": True, "is_autonomous_enabled": enabled})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagents Matrix: Toggle Any Subagent On / Off
        if path == '/api/subagents/toggle':
            try:
                subagent_id = data.get("subagent_id")
                val = data.get("enabled") if "enabled" in data else data.get("is_enabled", True)
                enabled = bool(val)
                if not subagent_id:
                    self.send_json(400, {"error": "subagent_id is required"})
                    return

                ok = set_subagent_enabled(subagent_id, enabled)
                if not ok:
                    self.send_json(500, {"error": "Failed to update subagent status"})
                    return

                # If toggling Reddit subagent
                if subagent_id in ('subagent_2_reddit', 'reddit'):
                    if not enabled:
                        try:
                            reddit_drone_scheduler.stop()
                        except Exception:
                            pass
                    else:
                        try:
                            reddit_drone_scheduler.start()
                        except Exception:
                            pass

                # If toggling Instagram subagent
                if subagent_id in ('subagent_1_instagram', 'instagram'):
                    if not enabled:
                        try:
                            instagram_pr_scheduler.stop()
                        except Exception:
                            pass
                    else:
                        try:
                            instagram_pr_scheduler.start()
                        except Exception:
                            pass

                # If toggling Lead Supervisor
                if subagent_id == 'lead_supervisor':
                    if not enabled:
                        try:
                            supervisor_scheduler.stop()
                        except Exception:
                            pass
                    else:
                        try:
                            supervisor_scheduler.start()
                        except Exception:
                            pass

                # If toggling QA Sentinel
                if subagent_id in ('subagent_7_qa', 'qa'):
                    if not enabled:
                        try:
                            qa_scheduler.stop()
                        except Exception:
                            pass
                    else:
                        try:
                            qa_scheduler.start()
                        except Exception:
                            pass

                self.send_json(200, {
                    "success": True,
                    "subagent_id": subagent_id,
                    "is_enabled": 1 if enabled else 0,
                    "message": f"{subagent_id} {'başarıyla aktif edildi' if enabled else 'başarıyla kapatıldı (devredışı)'}."
                })
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 8: Generate Procurement & Replenishment Order Plan
        if path == '/api/procurement/generate':
            try:
                budget = float(data.get("budget_try", 250000.0))
                plan = lead_supervisor_agent.procurement_agent.analyze_and_generate_order_plan(target_budget_try=budget)
                self.send_json(200, {"success": True, "plan": plan})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 5: Trigger Price Intelligence Scan
        if path == '/api/price-intelligence/scan':
            try:
                report = lead_supervisor_agent.price_agent.scan_market()
                summary = lead_supervisor_agent.price_agent.get_summary_stats()
                self.send_json(200, {"success": True, "count": len(report), "summary": summary})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 4: Generate Technical SEO Guide
        if path == '/api/seo/generate':
            try:
                component_focus = data.get("component_focus")
                target_keywords = data.get("target_keywords")
                if isinstance(target_keywords, str):
                    target_keywords = [k.strip() for k in target_keywords.split(",") if k.strip()]
                article = lead_supervisor_agent.seo_agent.generate_article(
                    component_focus=component_focus,
                    target_keywords=target_keywords
                )
                self.send_json(201, {"success": True, "article": article})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 7: Trigger On-Demand Diagnostic Audit
        if path == '/api/qa/run':
            try:
                auto_heal = bool(data.get("auto_heal", True))
                report = qa_agent.run_full_diagnostics(auto_heal=auto_heal)
                self.send_json(200, {"success": True, "report": report})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 7: Trigger Auto-Healing
        if path == '/api/qa/auto-heal':
            try:
                report = qa_agent.run_full_diagnostics(auto_heal=True)
                self.send_json(200, {"success": True, "healed_actions": report.get("healed_actions", []), "report": report})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 7: Content Duplicate Scan / Fix (Instagram posts + site guides)
        if path == '/api/qa/duplicates':
            try:
                from orchestrator.duplicate_guard import DuplicateGuard
                guard = DuplicateGuard()
                report = guard.scan_all()
                self.send_json(200, {"success": True, "report": report})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        if path == '/api/qa/duplicates/fix':
            try:
                from orchestrator.duplicate_guard import DuplicateGuard
                guard = DuplicateGuard()
                scan = guard.scan_all()
                result = guard.remediate_all()
                self.send_json(200, {"success": True, "before": scan, "remediation": result})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 7: Toggle Autonomous Watchdog Mode
        if path == '/api/qa/toggle':
            try:
                enabled = bool(data.get("enabled", True))
                conn = get_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE qa_agent_config SET is_autonomous_enabled = ?, updated_at = ? WHERE id = 1", (1 if enabled else 0, datetime.now().isoformat()))
                conn.commit()
                conn.close()
                if enabled:
                    qa_scheduler.start()
                else:
                    qa_scheduler.stop()
                self.send_json(200, {"success": True, "is_autonomous_enabled": enabled})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 9: Trigger Cyber Security Audit Scan
        if path == '/api/security/scan':
            try:
                audit = cyber_security_agent.run_full_security_audit()
                self.send_json(200, {"success": True, "audit": audit})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 10: Trigger Product Media Inspection Scan
        if path == '/api/media/scan':
            try:
                limit = data.get('limit') if isinstance(data, dict) else None
                report = media_inspector_agent.scan_all_products(limit=limit)
                self.send_json(200, {"success": True, "report": report})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Subagent 10: Auto-Fix Quarantined Product Media
        if path == '/api/media/fix':
            try:
                dry_run = bool(data.get('dry_run', True)) if isinstance(data, dict) else True
                fix_res = media_inspector_agent.auto_fix_quarantined_products(dry_run=dry_run)
                self.send_json(200, {"success": True, "fix_result": fix_res})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # Cloud Market & Local PC Inventory Synchronizer (Autonomous Bridge)
        if path == '/api/admin/sync-cloud-market':
            try:
                import subprocess
                pull_res = subprocess.run(
                    ["git", "pull", "--rebase", "origin", "main"],
                    cwd=BASE_DIR,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                prod_json_p = os.path.join(BASE_DIR, "data", "products.json")
                updated_count = 0
                if os.path.exists(prod_json_p):
                    with open(prod_json_p, "r", encoding="utf-8") as pf:
                        prods = json.load(pf)
                    conn_sync = get_db()
                    cur_sync = conn_sync.cursor()
                    for prd in prods:
                        cur_sync.execute("UPDATE products SET stock = ? WHERE id = ?", (prd.get("stock", 0), prd.get("id")))
                        if cur_sync.rowcount > 0:
                            updated_count += 1
                    conn_sync.commit()
                    conn_sync.close()
                export_static_data()
                self.send_json(200, {
                    "success": True,
                    "git_status": pull_res.stdout.strip() if pull_res.returncode == 0 else pull_res.stderr.strip(),
                    "products_updated": updated_count,
                    "message": "Bulut pazar yeri stoklari basariyla yerel veritabanina ve statik dosyalara senkronize edildi."
                })
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        conn = get_db()
        cursor = conn.cursor()

        if path == '/api/admin/products/check':
            try:
                if not isinstance(data.get('checked'), bool):
                    self.send_json(400, {'error': 'checked değeri boolean olmalıdır.'})
                    return
                identity = self.get_current_user() or {}
                result = product_quality.record_check(
                    conn, str(data.get('id') or ''), 'checked' if data['checked'] else 'pending',
                    reviewer=identity.get('email') or identity.get('uid') or 'admin',
                    expected_hash=data.get('content_hash'),
                    notes='Yönetici panelinden elle işaretlendi.' if data['checked'] else '')
                conn.commit()
                self.send_json(200, {'success': True, **result})
            except LookupError as error:
                self.send_json(404, {'error': str(error)})
            except ValueError as error:
                self.send_json(409 if data.get('content_hash') else 400, {'error': str(error)})
            finally:
                conn.close()
            return

        # 1. Manual User Registration
        if path == '/api/auth/register':
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            full_name = data.get('full_name', '').strip()
            phone = data.get('phone', '')
            address = data.get('address', '')
            city = data.get('city', '')

            if not email or not password or not full_name:
                conn.close()
                self.send_json(400, {"error": "Email, password, and full name are required."})
                return

            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                self.send_json(400, {"error": "An account with this email already exists."})
                return

            user_id = str(uuid.uuid4())
            pw_hash = hash_password(password)
            now = datetime.now().isoformat()
            avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={urllib.parse.quote(full_name)}"

            cursor.execute('''
                INSERT INTO users (id, email, password_hash, full_name, avatar_url, provider, role, phone, address, city, country, created_at)
                VALUES (?, ?, ?, ?, ?, 'manual', 'customer', ?, ?, ?, 'Turkey', ?)
            ''', (user_id, email, pw_hash, full_name, avatar, phone, address, city, now))
            conn.commit()

            cursor.execute("SELECT id, email, full_name, avatar_url, provider, role, phone, address, city, country FROM users WHERE id = ?", (user_id,))
            user_data = dict(cursor.fetchone())
            conn.close()

            token = create_auth_token(user_data)
            self.send_json(201, {
                "success": True,
                "message": "Account created successfully!",
                "user": user_data,
                "token": token
            })
            return

        # 2. Manual User Login with Brute-Force & Cooldown Protection (3 attempts -> 30 min cooldown)
        if path == '/api/auth/login':
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
            client_ip = self.client_address[0] if self.client_address else "127.0.0.1"

            if not email or not password:
                conn.close()
                self.send_json(400, {"error": "Email and password are required."})
                return

            # Check if email is currently locked (3 failed attempts -> 30 min cooldown)
            is_locked, rem_sec, rem_min, attempts_left = check_login_rate_limit(email)

            if is_locked:
                conn.close()
                self.send_json(429, {
                    "error": f"[GUVENLIK KORUMASI] 3 kez hatali deneme yapildigi icin bu hesap kilitlendi! Lutfen {rem_min} dakika sonra tekrar deneyiniz.",
                    "locked": True,
                    "remaining_seconds": rem_sec,
                    "remaining_minutes": rem_min
                })
                return

            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if not user or dict(user).get('password_hash') != hash_password(password):
                conn.close()
                is_now_locked, rem_sec, rem_min, left = record_failed_login(email)
                
                if is_now_locked:
                    self.send_json(429, {
                        "error": "[GUVENLIK KORUMASI] 3 kez hatali giris yapildi! Guvenlik nedeniyle hesabiniz 30 dakika sureyle kilitlenmistir.",
                        "locked": True,
                        "remaining_seconds": rem_sec,
                        "remaining_minutes": rem_min
                    })
                else:
                    self.send_json(401, {
                        "error": f"[HATA] Hatali sifre veya e-posta! Kalan deneme hakkiniz: {left}",
                        "attempts_left": left,
                        "locked": False
                    })
                return

            # Successful login - Clear failed attempts for this email
            clear_login_attempts(email)

            user_dict = dict(user)
            if 'password_hash' in user_dict:
                del user_dict['password_hash']
            conn.close()

            token = create_auth_token(user_dict)
            self.send_json(200, {
                "success": True,
                "message": "Login successful!",
                "user": user_dict,
                "token": token
            })
            return

        # 3. Google / Gmail Sign-In with Cryptographic Verification
        if path == '/api/auth/google':
            email = data.get('email', '').strip().lower()
            full_name = data.get('full_name', '').strip() or email.split('@')[0].capitalize()
            avatar_url = data.get('avatar_url', f"https://api.dicebear.com/7.x/bottts/svg?seed={email}")
            credential = data.get('credential', '').strip()

            if not email:
                conn.close()
                self.send_json(400, {"error": "Google email is required."})
                return

            # Cryptographically verify Google ID Token with Google Accounts API
            verified_by_google = False
            if credential:
                try:
                    verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(credential)}"
                    req = urllib.request.Request(verify_url, headers={'User-Agent': 'Pozitron-Auth-Verifier/1.0'})
                    with urllib.request.urlopen(req, timeout=4) as g_resp:
                        if g_resp.status == 200:
                            token_info = json.loads(g_resp.read().decode('utf-8'))
                            google_email = (token_info.get('email') or '').lower().strip()
                            if google_email == email and token_info.get('email_verified') in ('true', True, 1):
                                verified_by_google = True
                                full_name = token_info.get('name') or full_name
                                avatar_url = token_info.get('picture') or avatar_url
                except Exception as ex:
                    print(f"[Auth] Google token verification notice: {ex}")

            ADMIN_EMAILS = [
                'thepeakiscold@gmail.com',
                'furkaniusprimes@gmail.com',
                'eyupfurkanpekoz@gmail.com',
                'pekozfurkan@gmail.com',
                'pozitronmarket@gmail.com',
                'ahmet@pozitron.market'
            ]
            is_whitelisted = (email in ADMIN_EMAILS) or email.endswith('@pozitron.market')
            is_cloud = bool(os.environ.get('RENDER') or os.environ.get('PORT'))
            is_proxied = bool(self.headers.get('X-Forwarded-For') or self.headers.get('CF-Connecting-IP'))
            is_local = bool(not is_cloud and not is_proxied and self.client_address and self.client_address[0] in ('127.0.0.1', 'localhost', '::1') and os.environ.get('POZITRON_ENV') != 'production')
            has_admin_key = (self.headers.get('X-Admin-Key') == ADMIN_API_KEY) or (self.headers.get('Authorization') == f"Bearer {ADMIN_API_KEY}")

            # Admin escalation is protected: requires whitelisted email + cryptographic proof OR admin key
            assigned_role = 'customer'
            if is_whitelisted and (verified_by_google or has_admin_key or is_local):
                assigned_role = 'admin'

            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if user:
                user_dict = dict(user)
                if 'password_hash' in user_dict:
                    del user_dict['password_hash']
                # Upgrade to admin if email qualifies with verification
                if assigned_role == 'admin' and user_dict.get('role') != 'admin':
                    cursor.execute("UPDATE users SET role = 'admin' WHERE id = ?", (user_dict['id'],))
                    conn.commit()
                    user_dict['role'] = 'admin'
            else:
                user_id = str(uuid.uuid4())
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO users (id, email, password_hash, full_name, avatar_url, provider, role, created_at)
                    VALUES (?, ?, NULL, ?, ?, 'google', ?, ?)
                ''', (user_id, email, full_name, avatar_url, assigned_role, now))
                conn.commit()

                cursor.execute("SELECT id, email, full_name, avatar_url, provider, role, phone, address, city, country FROM users WHERE id = ?", (user_id,))
                user_dict = dict(cursor.fetchone())

            conn.close()
            token = create_auth_token(user_dict)
            self.send_json(200, {
                "success": True,
                "message": "Authenticated with Google successfully!",
                "user": user_dict,
                "token": token
            })
            return

        # 3b. Sync User (Preserves exact provider and role from client)
        if path == '/api/auth/sync':
            email = data.get('email', '').strip().lower()
            full_name = data.get('full_name', '').strip() or email.split('@')[0].capitalize()
            avatar_url = data.get('avatar_url', f"https://api.dicebear.com/7.x/bottts/svg?seed={email}")
            provider = data.get('provider', 'manual')
            role = data.get('role', 'customer')
            phone = data.get('phone', '')

            if not email:
                conn.close()
                self.send_json(400, {"error": "Email is required."})
                return

            # Security: Client cannot elevate itself to admin via sync without admin privileges
            if role == 'admin' and not self.require_admin():
                role = 'customer'

            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()

            if user:
                cursor.execute("UPDATE users SET provider = ?, full_name = ? WHERE email = ?", (provider, full_name, email))
                conn.commit()
            else:
                user_id = str(uuid.uuid4())
                now = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO users (id, email, password_hash, full_name, avatar_url, provider, role, phone, created_at)
                    VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?)
                ''', (user_id, email, full_name, avatar_url, provider, role, phone, now))
                conn.commit()

            conn.close()
            self.send_json(200, {"success": True, "provider": provider})
            return

        # 3c. Forgot Password - Request 6-digit verification code
        if path == '/api/auth/forgot-password':
            email = data.get('email', '').strip().lower()
            if not email or not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
                conn.close()
                self.send_json(400, {"error": "Geçerli bir e-posta adresi giriniz."})
                return

            cursor.execute("SELECT id, full_name, provider, password_hash FROM users WHERE LOWER(email) = ?", (email,))
            user = cursor.fetchone()

            if not user:
                conn.close()
                self.send_json(404, {"error": "Bu e-posta adresiyle kayıtlı bir hesap bulunamadı."})
                return

            provider = (user[2] or '').lower().strip()
            password_hash = user[3]

            # Google / Gmail OAuth users have no password; prevent sending reset codes
            if provider in ('gmail', 'google') or not password_hash:
                conn.close()
                self.send_json(400, {
                    "error": "Bu hesap Google ile kayıt olmuştur ve şifresi bulunmamaktadır. Lütfen 'Google ile Giriş Yap' butonunu kullanarak giriş yapınız.",
                    "is_google_user": True
                })
                return

            # Generate 6-digit code
            code = str(random.randint(100000, 999999))
            reset_id = str(uuid.uuid4())
            expires_at = int(time.time()) + 1800  # 30 minutes
            now_iso = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO password_resets (id, email, code, expires_at, used, created_at)
                VALUES (?, ?, ?, ?, 0, ?)
            ''', (reset_id, email, code, expires_at, now_iso))
            conn.commit()
            conn.close()

            print(f"[AUTH PASSWORD RESET] Code generated for {email}: {code} (expires in 30m)")

            # Send verification email in background thread
            email_thread = threading.Thread(target=send_verification_email, args=(email, code), daemon=True)
            email_thread.start()

            self.send_json(200, {
                "success": True,
                "message": "6 haneli doğrulama kodu e-posta adresinize gönderildi.",
                "expires_in": 1800
            })
            return

        # 3d. Reset Password - Verify code and set new password
        if path == '/api/auth/reset-password':
            email = data.get('email', '').strip().lower()
            code = data.get('code', '').strip()
            new_password = data.get('new_password', '').strip()

            if not email or not code or not new_password:
                conn.close()
                self.send_json(400, {"error": "E-posta, doğrulama kodu ve yeni şifre zorunludur."})
                return

            if len(new_password) < 6:
                conn.close()
                self.send_json(400, {"error": "Yeni şifre en az 6 karakter olmalıdır."})
                return

            now_ts = int(time.time())
            cursor.execute('''
                SELECT id FROM password_resets 
                WHERE LOWER(email) = ? AND code = ? AND used = 0 AND expires_at > ?
                ORDER BY created_at DESC LIMIT 1
            ''', (email, code, now_ts))
            reset_row = cursor.fetchone()

            if not reset_row:
                conn.close()
                self.send_json(400, {"error": "Geçersiz veya süresi dolmuş doğrulama kodu."})
                return

            reset_id = reset_row[0]
            cursor.execute("UPDATE password_resets SET used = 1 WHERE id = ?", (reset_id,))

            new_hash = hash_password(new_password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE LOWER(email) = ?", (new_hash, email))
            conn.commit()

            cursor.execute("SELECT id, email, full_name, avatar_url, provider, role, phone, address, city, country FROM users WHERE LOWER(email) = ?", (email,))
            user_row = cursor.fetchone()
            user_dict = dict(user_row) if user_row else None
            token = create_auth_token(user_dict) if user_dict else None
            conn.close()

            print(f"[AUTH PASSWORD RESET] Password reset successfully for {email}")

            self.send_json(200, {
                "success": True,
                "message": "Şifreniz başarıyla güncellendi! Yeni şifrenizle giriş yapabilirsiniz.",
                "user": user_dict,
                "token": token
            })
            return

        # 3e. Create or Update User Address
        if path == '/api/user/addresses':
            addr_id = data.get('id') or str(uuid.uuid4())
            user_id = data.get('user_id', '').strip()
            title = data.get('title', 'Ev').strip()
            full_name = data.get('full_name', '').strip() or data.get('recipient_name', '').strip()
            phone = data.get('phone', '').strip()
            city = data.get('city', '').strip()
            district = data.get('district', '').strip()
            address_line = data.get('address_line', '').strip()
            postal_code = data.get('postal_code', '').strip()
            is_default_shipping = 1 if (data.get('is_default_shipping') or data.get('is_default')) else 0
            is_default_billing = 1 if (data.get('is_default_billing') or data.get('is_default')) else 0

            same_as_shipping = 1 if data.get('same_as_shipping', 1) in (1, '1', True, 'true') else 0
            billing_address_line = data.get('billing_address_line', '').strip()
            billing_city = data.get('billing_city', '').strip()
            billing_district = data.get('billing_district', '').strip()
            billing_country = data.get('billing_country', 'Turkey').strip()
            invoice_type = data.get('invoice_type', 'individual').strip()
            tax_id = data.get('tax_id', '').strip()
            tax_office = data.get('tax_office', '').strip()
            company_name = data.get('company_name', '').strip()

            if not user_id or not full_name or not phone or not city or not address_line:
                conn.close()
                self.send_json(400, {"error": "Zorunlu adres alanlarını eksiksiz doldurunuz."})
                return

            if is_default_shipping:
                cursor.execute("UPDATE user_addresses SET is_default_shipping = 0 WHERE user_id = ?", (user_id,))
            if is_default_billing:
                cursor.execute("UPDATE user_addresses SET is_default_billing = 0 WHERE user_id = ?", (user_id,))

            cursor.execute("SELECT id FROM user_addresses WHERE id = ?", (addr_id,))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE user_addresses 
                    SET title = ?, full_name = ?, phone = ?, city = ?, district = ?, 
                        address_line = ?, postal_code = ?, is_default_shipping = ?, is_default_billing = ?,
                        same_as_shipping = ?, billing_address_line = ?, billing_city = ?, billing_district = ?,
                        billing_country = ?, invoice_type = ?, tax_id = ?, tax_office = ?, company_name = ?
                    WHERE id = ?
                ''', (title, full_name, phone, city, district, address_line, postal_code, is_default_shipping, is_default_billing,
                      same_as_shipping, billing_address_line, billing_city, billing_district,
                      billing_country, invoice_type, tax_id, tax_office, company_name, addr_id))
            else:
                now_iso = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO user_addresses (
                        id, user_id, title, full_name, phone, city, district, 
                        address_line, postal_code, is_default_shipping, is_default_billing,
                        same_as_shipping, billing_address_line, billing_city, billing_district,
                        billing_country, invoice_type, tax_id, tax_office, company_name, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (addr_id, user_id, title, full_name, phone, city, district,
                      address_line, postal_code, is_default_shipping, is_default_billing,
                      same_as_shipping, billing_address_line, billing_city, billing_district,
                      billing_country, invoice_type, tax_id, tax_office, company_name, now_iso))

            conn.commit()
            cursor.execute("SELECT * FROM user_addresses WHERE id = ?", (addr_id,))
            saved = dict(cursor.fetchone())
            conn.close()

            self.send_json(200, {"success": True, "address": saved})
            return

        # 3f. Delete User Address
        if path == '/api/user/addresses/delete':
            addr_id = data.get('id', '').strip()
            if not addr_id:
                conn.close()
                self.send_json(400, {"error": "Address id is required."})
                return
            cursor.execute("DELETE FROM user_addresses WHERE id = ?", (addr_id,))
            conn.commit()
            conn.close()
            self.send_json(200, {"success": True, "deleted_id": addr_id})
            return

        # 4. Coupon Validation
        if path == '/api/coupons/validate':
            code = data.get('code', '').strip().upper()
            subtotal_usd = float(data.get('subtotal_usd', 0) or 0)
            subtotal_try = float(data.get('subtotal_try', 0) or 0)
            if subtotal_usd == 0 and subtotal_try > 0:
                subtotal_usd = round(subtotal_try / 35.5, 2)
            elif subtotal_try == 0 and subtotal_usd > 0:
                subtotal_try = round(subtotal_usd * 35.5, 2)
            user_id = data.get('user_id')
            email = data.get('email') or data.get('customer_email')

            conn.close()
            try:
                result = coupon_service.validate_coupon(
                    code, subtotal_usd=subtotal_usd, subtotal_try=subtotal_try,
                    user_id=user_id, email=email,
                )
            except Exception as e:
                self.send_json(500, {"valid": False, "error": f"Kupon doğrulanamadı: {e}"})
                return
            if result.get('valid'):
                self.send_json(200, result)
            else:
                self.send_json(400, result)
            return

        # 4b. Currently active public deal (for the site banner)
        if path == '/api/coupons/active':
            conn.close()
            try:
                deal = coupon_service.get_active_deal()
            except Exception:
                deal = None
            if deal:
                self.send_json(200, {
                    "active": True,
                    "code": deal.get('code'),
                    "discount_type": deal.get('discount_type'),
                    "discount_value": deal.get('discount_value'),
                    "min_order_try": deal.get('min_order_try'),
                    "description_tr": deal.get('description_tr'),
                    "expires_at": deal.get('expires_at'),
                })
            else:
                self.send_json(200, {"active": False})
            return

        # 5. Payment & Checkout Processing
        if path == '/api/payment/process':
            items = data.get('items', [])
            if not items:
                conn.close()
                self.send_json(400, {"error": "Your cart is empty."})
                return

            customer_name = data.get('customer_name', '').strip()
            customer_email = data.get('customer_email', '').strip()
            customer_phone = data.get('customer_phone', '').strip()
            shipping_address = data.get('shipping_address', '').strip()
            city = data.get('city', '').strip()
            country = data.get('country', 'Turkey').strip()
            currency = data.get('currency', 'USD').upper()
            payment_method = data.get('payment_method', 'credit_card')
            coupon_code = data.get('coupon_code', '')
            user_id = data.get('user_id', None)

            # A local OTP or client-provided status is never evidence of a charge.
            # Card payments stay unavailable until a verified provider flow exists.
            if payment_method not in ('havale', 'bank'):
                conn.close()
                self.send_json(503, {"error": "Kart ödemesi henüz kullanıma açık değildir. Havale/EFT/FAST seçeneğini kullanabilirsiniz.", "code": "PAYMENT_PROVIDER_NOT_CONFIGURED"})
                return
            payment_method = 'havale'
            card_number = ''
            card_brand = 'Havale / EFT / FAST'

            # Calculate Subtotals and verify stock
            subtotal_usd = 0.0
            subtotal_try = 0.0
            processed_items = []

            for item in items:
                prod_id = item.get('id')
                qty = max(1, int(item.get('quantity', 1)))
                cursor.execute("SELECT id, name_en, name_tr, brand, price_usd, price_try, stock, image_url, sku FROM products WHERE id = ?", (prod_id,))
                prod = cursor.fetchone()
                if not prod:
                    continue
                p_dict = dict(prod)
                
                # Check & update stock
                new_stock = max(0, p_dict['stock'] - qty)
                cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, prod_id))

                item_usd = round(p_dict['price_usd'] * qty, 2)
                item_try = round(p_dict['price_try'] * qty, 2)
                subtotal_usd += item_usd
                subtotal_try += item_try

                processed_items.append({
                    "id": p_dict['id'],
                    "sku": p_dict['sku'],
                    "name_en": p_dict['name_en'],
                    "name_tr": p_dict['name_tr'],
                    "brand": p_dict['brand'],
                    "price_usd": p_dict['price_usd'],
                    "price_try": p_dict['price_try'],
                    "quantity": qty,
                    "total_usd": item_usd,
                    "total_try": item_try,
                    "image_url": p_dict['image_url']
                })

            # Calculate Discount — strict validation. An applied coupon that is no
            # longer valid aborts the order instead of silently charging full price.
            discount_usd = 0.0
            discount_try = 0.0
            applied_coupon_code = None
            if coupon_code:
                v = coupon_service.validate_coupon(
                    coupon_code, subtotal_usd=subtotal_usd, subtotal_try=subtotal_try,
                    user_id=user_id, email=customer_email, conn=conn, commit=False,
                )
                if not v.get('valid'):
                    conn.rollback()
                    conn.close()
                    self.send_json(400, {
                        "error": v.get('error') or "Kupon geçersiz.",
                        "coupon_invalid": True,
                        "reason": v.get('reason'),
                    })
                    return
                discount_usd = v['discount_usd']
                discount_try = v['discount_try']
                applied_coupon_code = v['code']

            # Shipping fees (Free for orders >= 1500 TRY or >= $35 USD)
            shipping_fee_usd = 0.0 if subtotal_usd >= 35.0 else 2.10
            shipping_fee_try = 0.0 if subtotal_try >= 1500.0 else 99.0

            total_usd = max(0.0, round(subtotal_usd - discount_usd + shipping_fee_usd, 2))
            total_try = max(0.0, round(subtotal_try - discount_try + shipping_fee_try, 2))

            order_id = str(uuid.uuid4())
            order_number = f"PZT-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"
            tracking_number = f"TRK-{random.randint(100000000, 999999999)}"
            transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
            card_last4 = card_number[-4:] if card_number else "0000"
            now_iso = datetime.now().isoformat()

            shipping_district = data.get('shipping_district', '').strip()
            billing_address = data.get('billing_address', '').strip() or shipping_address
            billing_city = data.get('billing_city', '').strip() or city
            billing_district = data.get('billing_district', '').strip() or shipping_district
            billing_country = data.get('billing_country', 'Turkey').strip()
            invoice_type = data.get('invoice_type', 'individual').strip()
            tax_id = data.get('tax_id', '').strip()
            tax_office = data.get('tax_office', '').strip()
            company_name = data.get('company_name', '').strip()
            order_notes = data.get('order_notes', '').strip() or data.get('notes', '').strip()

            cursor.execute('''
                INSERT INTO orders (
                    id, order_number, user_id, customer_name, customer_email, customer_phone,
                    shipping_address, city, country, shipping_district,
                    billing_address, billing_city, billing_district, billing_country,
                    invoice_type, tax_id, tax_office, company_name, order_notes,
                    items_json,
                    subtotal_usd, subtotal_try, discount_usd, discount_try,
                    shipping_fee_usd, shipping_fee_try, total_usd, total_try,
                    currency, payment_method, payment_status, card_last4, card_brand,
                    transaction_id, order_status, tracking_number, notes, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, 'PENDING_PAYMENT', ?, ?, ?)
            ''', (
                order_id, order_number, user_id, customer_name, customer_email, customer_phone,
                shipping_address, city, country, shipping_district,
                billing_address, billing_city, billing_district, billing_country,
                invoice_type, tax_id, tax_office, company_name, order_notes,
                json.dumps(processed_items),
                subtotal_usd, subtotal_try, discount_usd, discount_try,
                shipping_fee_usd, shipping_fee_try, total_usd, total_try,
                currency, payment_method, card_last4, card_brand,
                transaction_id, tracking_number, order_notes or 'Standard FPV Express Dispatch', now_iso
            ))

            # Atomically claim the coupon for this account. If another concurrent
            # checkout already used it, the UNIQUE(coupon_code, user_key) constraint
            # fires here and the whole order (incl. stock) is rolled back.
            if applied_coupon_code:
                ok, reason = coupon_service.redeem_coupon(
                    conn, applied_coupon_code, user_id=user_id, email=customer_email,
                    order_id=order_id, order_number=order_number,
                    discount_usd=discount_usd, discount_try=discount_try,
                )
                if not ok:
                    conn.rollback()
                    conn.close()
                    reason_map = {
                        'already_used': "Bu kuponu daha önce kullandınız. Her hesap yalnızca bir kez yararlanabilir.",
                        'usage_limit': "Bu kupon maksimum kullanım sayısına ulaştı.",
                        'expired': "Bu kuponun süresi doldu.",
                        'inactive': "Bu kupon artık geçerli değil.",
                        'login_required': "Kupon kullanmak için giriş yapmalısınız.",
                    }
                    self.send_json(400, {
                        "error": reason_map.get(reason, "Kupon kullanılamadı."),
                        "coupon_invalid": True,
                        "reason": reason,
                    })
                    return

            conn.commit()
            conn.close()

            self.send_json(200, {
                "success": True,
                "order_number": order_number,
                "order_id": order_id,
                "tracking_number": tracking_number,
                "transaction_id": transaction_id,
                "status": "PENDING_PAYMENT",
                "payment_status": "PENDING",
                "card_brand": card_brand,
                "card_last4": card_last4,
                "currency": currency,
                "subtotal_usd": subtotal_usd,
                "subtotal_try": subtotal_try,
                "discount_usd": discount_usd,
                "discount_try": discount_try,
                "shipping_fee_usd": shipping_fee_usd,
                "shipping_fee_try": shipping_fee_try,
                "total_usd": total_usd,
                "total_try": total_try,
                "items": processed_items,
                "shipping_address": f"{shipping_address}, {shipping_district} {city}, {country}".strip().replace('  ', ' '),
                "billing_address": f"{billing_address}, {billing_district} {billing_city}, {billing_country}".strip().replace('  ', ' '),
                "invoice_type": invoice_type,
                "tax_id": tax_id,
                "tax_office": tax_office,
                "company_name": company_name,
                "order_notes": order_notes,
                "customer_name": customer_name,
                "customer_email": customer_email,
                "created_at": now_iso
            })
            return

        if path in ('/api/admin/reviews/delete', '/api/admin/reviews/restore'):
            try:
                review_id = str(data.get('id') or '').strip()
                if not review_id:
                    self.send_json(400, {'error': 'Yorum kimliği gereklidir.'})
                    return
                cursor.execute('SELECT product_id FROM reviews WHERE id = ?', (review_id,))
                review = cursor.fetchone()
                if review is None:
                    self.send_json(404, {'error': 'Yorum bulunamadı.'})
                    return
                deleted_at = datetime.now().isoformat() if path.endswith('/delete') else None
                cursor.execute('UPDATE reviews SET deleted_at = ? WHERE id = ?', (deleted_at, review_id))
                if review['product_id']:
                    cursor.execute('SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id = ? AND deleted_at IS NULL', (review['product_id'],))
                    avg_rating, count = cursor.fetchone()
                    cursor.execute('UPDATE products SET rating = ?, review_count = ? WHERE id = ?',
                                   (round(avg_rating, 1) if avg_rating is not None else 0, count, review['product_id']))
                conn.commit()
                self.send_json(200, {'success': True, 'id': review_id, 'deleted': deleted_at is not None})
            finally:
                conn.close()
            return

        # 6. Add Review
        if path == '/api/reviews':
            try:
                raw_prod_id = data.get('product_id')
                user_name = data.get('user_name', 'Anonymous Pilot').strip() or 'Anonymous Pilot'
                rating = max(1, min(5, int(data.get('rating', 5))))
                title = data.get('title', '').strip()
                comment = data.get('comment', '').strip()

                if not comment:
                    self.send_json(400, {"error": "Comment is required."})
                    return

                real_prod_id = None
                if raw_prod_id and raw_prod_id != 'general':
                    cursor.execute("SELECT id FROM products WHERE id = ? OR slug = ?", (raw_prod_id, raw_prod_id))
                    m_row = cursor.fetchone()
                    if m_row:
                        real_prod_id = m_row[0]

                rev_id = str(uuid.uuid4())
                now_iso = datetime.now().isoformat()
                avatar = data.get('user_avatar') or f"https://api.dicebear.com/7.x/bottts/svg?seed={urllib.parse.quote(user_name)}"

                cursor.execute('''
                    INSERT INTO reviews (id, product_id, user_name, user_avatar, rating, title, comment, verified_purchase, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
                ''', (rev_id, real_prod_id, user_name, avatar, rating, title, comment, now_iso))

                # Recalculate product rating if review was for a product
                if real_prod_id:
                    cursor.execute("SELECT AVG(rating), COUNT(*) FROM reviews WHERE product_id = ? AND deleted_at IS NULL", (real_prod_id,))
                    avg_r, count_r = cursor.fetchone()
                    if avg_r is not None:
                        cursor.execute("UPDATE products SET rating = ?, review_count = ? WHERE id = ?", (round(avg_r, 1), count_r, real_prod_id))

                conn.commit()

                self.send_json(201, {
                    "success": True,
                    "review": {
                        "id": rev_id,
                        "product_id": real_prod_id,
                        "user_name": user_name,
                        "user_avatar": avatar,
                        "rating": rating,
                        "title": title,
                        "comment": comment,
                        "created_at": now_iso
                    }
                })
                return
            finally:
                conn.close()

        # 7. Drone Compatibility Builder Checker
        if path == '/api/builder/check':
            motor_id = data.get('motor_id')
            esc_id = data.get('esc_id')
            prop_id = data.get('prop_id')
            battery_id = data.get('battery_id')

            warnings = []
            recommendations = []
            score = 100

            # Inspect items from database
            selected = {}
            for k, pid in [('motor', motor_id), ('esc', esc_id), ('prop', prop_id), ('battery', battery_id)]:
                if pid:
                    cursor.execute("SELECT * FROM products WHERE id = ?", (pid,))
                    r = cursor.fetchone()
                    if r:
                        selected[k] = dict(r)
                        selected[k]['specs'] = json.loads(selected[k]['specs_json'])

            conn.close()

            # Compatibility Rules Engine
            if 'battery' in selected and 'motor' in selected:
                bat_name = selected['battery']['name_en']
                motor_name = selected['motor']['name_en']
                if "6S" in bat_name and "2400KV" in motor_name:
                    warnings.append({"en": "Motor KV (2400KV+) is dangerously high for 6S LiPo! Recommended KV for 6S is 1700KV - 1950KV.", "tr": "Motor KV değeri (2400KV+) 6S LiPo için çok yüksek! 6S için önerilen KV: 1700KV - 1950KV."})
                    score -= 30
                elif "4S" in bat_name and "1750KV" in motor_name:
                    recommendations.append({"en": "1750KV motor on 4S will feel underpowered. 2400KV-2750KV is optimal for 4S freestyle.", "tr": "4S pilde 1750KV motor düşük güç hissettirebilir. 4S freestyle için 2400KV-2750KV idealdir."})

            if 'esc' in selected and 'motor' in selected:
                esc_name = selected['esc']['name_en']
                if "45A" in esc_name and "2807" in selected['motor']['name_en']:
                    warnings.append({"en": "2807 Long Range motors with heavy 7-inch props may exceed 45A ESC limits. Consider 55A+ ESC.", "tr": "Ağır 7 inç pervaneli 2807 motorlar 45A ESC limitini aşabilir. 55A+ ESC önerilir."})
                    score -= 20

            self.send_json(200, {
                "compatibility_score": max(0, score),
                "is_compatible": len(warnings) == 0,
                "warnings": warnings,
                "recommendations": recommendations,
                "parts_selected": list(selected.keys())
            })
            return

        # 8. Admin: Update Single Product (Stock, Prices, Metadata)
        if path == '/api/admin/products/update':
            prod_id = data.get('id')
            if not prod_id:
                conn.close()
                self.send_json(400, {"error": "Product ID is required"})
                return

            cursor.execute("SELECT * FROM products WHERE id = ?", (prod_id,))
            existing = cursor.fetchone()
            if not existing:
                conn.close()
                self.send_json(404, {"error": "Product not found"})
                return

            curr = dict(existing)

            stock = int(data.get('stock', curr['stock']))
            stock = max(0, stock)

            price_usd = float(data.get('price_usd', curr['price_usd']))
            price_try = float(data.get('price_try', curr['price_try']))
            if 'price_usd' in data and 'price_try' not in data:
                price_try = round(price_usd * get_setting('usd_rate', 50.0), 2)

            orig_price_usd = float(data['original_price_usd']) if data.get('original_price_usd') is not None and data['original_price_usd'] != '' else curr['original_price_usd']
            orig_price_try = float(data['original_price_try']) if data.get('original_price_try') is not None and data['original_price_try'] != '' else curr['original_price_try']
            discount_pct = int(data.get('discount_pct', curr['discount_pct']))

            name_en = data.get('name_en', curr['name_en'])
            name_tr = data.get('name_tr', curr['name_tr'])
            category_id = data.get('category_id', curr['category_id'])
            brand = data.get('brand', curr['brand'])
            badge = data.get('badge', curr['badge'])
            featured = int(data.get('featured', curr['featured']))
            is_bestseller = int(data.get('is_bestseller', curr['is_bestseller']))
            image_url = data.get('image_url', curr['image_url'])

            cursor.execute('''
                UPDATE products SET
                    stock = ?,
                    price_usd = ?,
                    price_try = ?,
                    original_price_usd = ?,
                    original_price_try = ?,
                    discount_pct = ?,
                    name_en = ?,
                    name_tr = ?,
                    category_id = ?,
                    brand = ?,
                    badge = ?,
                    featured = ?,
                    is_bestseller = ?,
                    image_url = ?
                WHERE id = ?
            ''', (
                stock, price_usd, price_try, orig_price_usd, orig_price_try, discount_pct,
                name_en, name_tr, category_id, brand, badge, featured, is_bestseller, image_url, prod_id
            ))
            conn.commit()

            cursor.execute('''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.id = ?
            ''', (prod_id,))
            updated_prod = dict(cursor.fetchone())
            updated_prod['specs'] = json.loads(updated_prod['specs_json']) if updated_prod.get('specs_json') else {}
            updated_prod['tags'] = json.loads(updated_prod['tags_json']) if updated_prod.get('tags_json') else []
            updated_prod['gallery'] = json.loads(updated_prod['gallery_json'] or '[]')
            conn.close()

            # Auto-export static JSON/JS bundles so static catalog and admin stay in sync
            try:
                export_static_data()
            except Exception as e:
                print(f"[UYARI] Product update export hatasi: {e}")

            self.send_json(200, {
                "success": True,
                "message": "Product updated successfully",
                "product": updated_prod
            })
            return

        # 9. Admin: Bulk Operations (Stock increment/set, Price multiplier/discount, FX Sync)
        if path == '/api/admin/products/bulk':
            prod_ids = data.get('product_ids', [])
            action = data.get('action')
            value = data.get('value', 0)

            if not prod_ids or not action:
                conn.close()
                self.send_json(400, {"error": "product_ids and action are required"})
                return

            placeholders = ",".join("?" for _ in prod_ids)

            if action == 'stock_increment':
                inc_val = int(value)
                cursor.execute(f'''
                    UPDATE products
                    SET stock = CASE WHEN stock + ? < 0 THEN 0 ELSE stock + ? END
                    WHERE id IN ({placeholders})
                ''', [inc_val, inc_val] + prod_ids)

            elif action == 'stock_set':
                set_val = max(0, int(value))
                cursor.execute(f'''
                    UPDATE products
                    SET stock = ?
                    WHERE id IN ({placeholders})
                ''', [set_val] + prod_ids)

            elif action == 'price_percent':
                factor = 1.0 + (float(value) / 100.0)
                if factor <= 0:
                    factor = 0.01
                cursor.execute(f'''
                    UPDATE products
                    SET price_usd = ROUND(price_usd * ?, 2),
                        price_try = ROUND(price_try * ?, 2),
                        original_price_usd = CASE WHEN original_price_usd IS NOT NULL THEN ROUND(original_price_usd * ?, 2) ELSE NULL END,
                        original_price_try = CASE WHEN original_price_try IS NOT NULL THEN ROUND(original_price_try * ?, 2) ELSE NULL END
                    WHERE id IN ({placeholders})
                ''', [factor, factor, factor, factor] + prod_ids)

            elif action == 'discount_set':
                disc_val = max(0, min(99, int(value)))
                cursor.execute(f'''
                    UPDATE products
                    SET discount_pct = ?
                    WHERE id IN ({placeholders})
                ''', [disc_val] + prod_ids)

            elif action == 'currency_sync':
                rate = float(value) if value else get_setting('usd_rate', 50.0)
                cursor.execute(f'''
                    UPDATE products
                    SET price_try = ROUND(price_usd * ?, 2),
                        original_price_try = CASE WHEN original_price_usd IS NOT NULL THEN ROUND(original_price_usd * ?, 2) ELSE NULL END
                    WHERE id IN ({placeholders})
                ''', [rate, rate] + prod_ids)

            conn.commit()
            conn.close()

            # Auto-export static JSON/JS bundles so static catalog stays in sync
            try:
                export_static_data()
            except Exception as e:
                print(f"[UYARI] Bulk update export hatasi: {e}")

            self.send_json(200, {
                "success": True,
                "action": action,
                "updated_count": len(prod_ids)
            })
            return

        # 10. Admin: Create New Product
        if path == '/api/admin/products/create':
            name_en = data.get('name_en', '').strip()
            name_tr = data.get('name_tr', '').strip() or name_en
            category_id = data.get('category_id', 'motors')
            brand = data.get('brand', 'Pozitron')
            price_usd = float(data.get('price_usd', 29.99))
            active_rate = get_setting('usd_rate', 50.0)
            price_try = float(data.get('price_try', round(price_usd * active_rate, 2)))
            stock = max(0, int(data.get('stock', 50)))
            badge = data.get('badge', 'NEW')
            image_url = data.get('image_url', 'https://images.unsplash.com/photo-1527977966376-1c8408f9f108?auto=format&fit=crop&w=600&q=80')
            sku = data.get('sku', '').strip() or f"PZT-{category_id[:4].upper()}-{random.randint(1000, 9999)}"
            clean_name = name_en.lower().replace('&', 'and')
            base_slug = re.sub(r'[^a-z0-9]+', '-', clean_name).strip('-')
            cursor.execute("SELECT id FROM products WHERE slug = ?", (base_slug,))
            if not cursor.fetchone():
                slug = base_slug
            else:
                suffix = 1
                while True:
                    candidate = f"{base_slug}-{suffix}"
                    cursor.execute("SELECT id FROM products WHERE slug = ?", (candidate,))
                    if not cursor.fetchone():
                        slug = candidate
                        break
                    suffix += 1
            prod_id = f"pzt_{uuid.uuid4().hex[:8]}"
            now_iso = datetime.now().isoformat()

            cursor.execute('''
                INSERT INTO products (
                    id, slug, sku, name_en, name_tr, category_id, brand,
                    price_usd, price_try, original_price_usd, original_price_try,
                    discount_pct, rating, review_count, stock, badge,
                    specs_json, tags_json, image_url, gallery_json,
                    description_en, description_tr, compatibility_json,
                    featured, is_bestseller, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0, 5.0, 0, ?, ?, '{}', '[]', ?, '[]', ?, ?, '{}', 0, 0, ?)
            ''', (
                prod_id, slug, sku, name_en, name_tr, category_id, brand,
                price_usd, price_try, stock, badge, image_url,
                data.get('description_en', name_en), data.get('description_tr', name_tr), now_iso
            ))

            cursor.execute("UPDATE categories SET item_count = item_count + 1 WHERE id = ?", (category_id,))
            conn.commit()

            cursor.execute('''
                SELECT p.*, c.name_en AS category_name_en, c.name_tr AS category_name_tr, c.icon AS category_icon
                FROM products p
                JOIN categories c ON p.category_id = c.id
                WHERE p.id = ?
            ''', (prod_id,))
            new_prod = dict(cursor.fetchone())
            new_prod['specs'] = {}
            new_prod['tags'] = []
            new_prod['gallery'] = []
            conn.close()

            # Auto-generate product page HTML
            try:
                from generate_product_pages import generate_product_page
                cat_dict = {"id": category_id, "name_en": new_prod.get('category_name_en', ''), "name_tr": new_prod.get('category_name_tr', '')}
                page_html = generate_product_page(new_prod, cat_dict, [], [new_prod], {category_id: [new_prod]})
                out_file = os.path.join(BASE_DIR, 'products', f"{slug}.html")
                with open(out_file, "w", encoding="utf-8") as pf:
                    pf.write(page_html)
            except Exception as pe:
                print(f"Failed to auto-generate static page for new product {slug}: {pe}")

            # Auto-export static JSON/JS bundles
            try:
                export_static_data()
            except Exception as e:
                print(f"[UYARI] Product create export hatasi: {e}")

            self.send_json(201, {
                "success": True,
                "message": "Product created successfully",
                "product": new_prod
            })
            return

        # 11. Admin: Delete Product
        if path == '/api/admin/products/delete':
            prod_id = data.get('id')
            if not prod_id:
                conn.close()
                self.send_json(400, {"error": "Product ID is required"})
                return

            cursor.execute("SELECT category_id, slug FROM products WHERE id = ? OR slug = ? OR sku = ?", (prod_id, prod_id, prod_id))
            p = cursor.fetchone()
            if p:
                cat_id = p[0]
                del_slug = p[1]
                cursor.execute("DELETE FROM products WHERE id = ? OR slug = ? OR sku = ?", (prod_id, prod_id, prod_id))
                cursor.execute("UPDATE categories SET item_count = MAX(0, item_count - 1) WHERE id = ?", (cat_id,))
                conn.commit()

                if del_slug:
                    del_html = os.path.join(BASE_DIR, 'products', f"{del_slug}.html")
                    if os.path.isfile(del_html):
                        try:
                            os.remove(del_html)
                        except Exception:
                            pass

            conn.close()

            # Auto-export static JSON/JS bundles
            try:
                export_static_data()
            except Exception as e:
                print(f"[UYARI] Product delete export hatasi: {e}")

            self.send_json(200, {"success": True, "deleted_id": prod_id})
            return

        # Admin: Delete User
        if path == '/api/admin/users/delete':
            user_id = data.get('id')
            email = (data.get('email') or '').lower().strip()

            if not user_id and not email:
                conn.close()
                self.send_json(400, {"error": "User ID or Email is required"})
                return

            admin_emails = ['furkaniusprimes@gmail.com', 'thepeakiscold@gmail.com', 'eyupfurkanpekoz@gmail.com', 'pekozfurkan@gmail.com', 'pozitronmarket@gmail.com', 'ahmet@pozitron.market']
            if email in admin_emails:
                conn.close()
                self.send_json(403, {"error": "Yönetici Gmail hesabı silinemez."})
                return

            if user_id:
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            elif email:
                cursor.execute("DELETE FROM users WHERE LOWER(email) = ?", (email,))

            conn.commit()
            conn.close()

            self.send_json(200, {"success": True, "message": "Kullanıcı başarıyla silindi.", "deleted_id": user_id})
            return

        # Admin: Update User Role (Grant / Revoke Admin Privilege)
        if path == '/api/admin/users/update_role':
            user_id = data.get('id')
            email = (data.get('email') or '').lower().strip()
            new_role = (data.get('role') or '').lower().strip()

            if not user_id and not email:
                conn.close()
                self.send_json(400, {"error": "User ID or Email is required"})
                return

            if new_role not in ('admin', 'customer'):
                conn.close()
                self.send_json(400, {"error": "Geçersiz rol. Yalnızca 'admin' veya 'customer' atanabilir."})
                return

            # Primary root accounts protected from demotion
            admin_emails = ['furkaniusprimes@gmail.com', 'thepeakiscold@gmail.com', 'eyupfurkanpekoz@gmail.com', 'pekozfurkan@gmail.com', 'pozitronmarket@gmail.com', 'ahmet@pozitron.market']
            if new_role != 'admin':
                cursor.execute("SELECT email FROM users WHERE id = ? OR LOWER(email) = ?", (user_id, email))
                row = cursor.fetchone()
                if row and row[0] and row[0].lower().strip() in admin_emails:
                    conn.close()
                    self.send_json(403, {"error": "Ana kurucu yönetici hesabı yetkisizleştirilemez."})
                    return

            if user_id:
                cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
            elif email:
                cursor.execute("UPDATE users SET role = ? WHERE LOWER(email) = ?", (new_role, email))

            conn.commit()

            if user_id:
                cursor.execute("SELECT id, email, full_name, avatar_url, provider, role, phone, address, city, country, created_at FROM users WHERE id = ?", (user_id,))
            else:
                cursor.execute("SELECT id, email, full_name, avatar_url, provider, role, phone, address, city, country, created_at FROM users WHERE LOWER(email) = ?", (email,))
            updated_user = cursor.fetchone()
            conn.close()

            user_data = dict(updated_user) if updated_user else {"id": user_id, "email": email, "role": new_role}
            self.send_json(200, {
                "success": True,
                "message": f"Kullanıcı rolü başarıyla '{new_role}' olarak güncellendi.",
                "user": user_data
            })
            return

        # 12. Admin: Currency Sync across catalog
        if path == '/api/admin/currency-sync':
            rate = float(data.get('usd_rate', 50.0))
            set_setting('usd_rate', rate)

            cat = data.get('category_id')
            brand = data.get('brand')

            where_clauses = ["1=1"]
            params = [rate, rate]

            if cat and cat != 'all':
                where_clauses.append("category_id = ?")
                params.append(cat)

            if brand and brand != 'all':
                where_clauses.append("brand = ?")
                params.append(brand)

            where_sql = " AND ".join(where_clauses)
            cursor.execute(f'''
                UPDATE products
                SET price_try = ROUND(price_usd * ?, 2),
                    original_price_try = CASE WHEN original_price_usd IS NOT NULL THEN ROUND(original_price_usd * ?, 2) ELSE NULL END
                WHERE {where_sql}
            ''', params)
            conn.commit()
            count = cursor.rowcount
            conn.close()

            # Automatically export static data so JSON/JS catalog bundles are synced
            try:
                export_static_data()
            except Exception as e:
                print(f"[UYARI] Currency sync export hatasi: {e}")

            self.send_json(200, {
                "success": True,
                "usd_rate": rate,
                "updated_count": count
            })
            return

        # 13. Settings Update (USD Rate, Bank, 3D Print, etc.)
        if path == '/api/settings':
            conn.close()
            sync_products = data.get('sync_products', True)
            for k, v in data.items():
                if k != 'sync_products':
                    set_setting(k, v)
            if 'usd_rate' in data:
                try:
                    rate = float(data['usd_rate'])
                    if sync_products and rate > 0:
                        c2 = get_db()
                        cur2 = c2.cursor()
                        cur2.execute('''
                            UPDATE products
                            SET price_try = ROUND(price_usd * ?, 2),
                                original_price_try = CASE WHEN original_price_usd IS NOT NULL THEN ROUND(original_price_usd * ?, 2) ELSE NULL END
                        ''', (rate, rate))
                        c2.commit()
                        c2.close()
                except Exception as e:
                    print(f"[UYARI] Settings currency sync hatasi: {e}")
                try:
                    export_static_data()
                except Exception as e:
                    print(f"[UYARI] Settings export hatasi: {e}")
            self.send_json(200, {
                "success": True,
                "message": "Ayarlar ve ürün fiyatları başarıyla kaydedildi.",
                "settings": get_all_settings()
            })
            return

        # 14. Admin: Orders Status & Tracking Update
        if path == '/api/admin/orders/update':
            order_id = data.get('id') or data.get('order_number')
            new_status = data.get('status')
            tracking_number = data.get('tracking_number')

            if not order_id:
                conn.close()
                self.send_json(400, {"error": "Order ID or order_number is required"})
                return

            cursor.execute('''
                UPDATE orders
                SET order_status = COALESCE(?, order_status),
                    tracking_number = COALESCE(?, tracking_number)
                WHERE id = ? OR order_number = ?
            ''', (new_status, tracking_number, order_id, order_id))
            conn.commit()
            affected = cursor.rowcount

            cursor.execute("SELECT * FROM orders WHERE id = ? OR order_number = ?", (order_id, order_id))
            ord_row = cursor.fetchone()
            conn.close()

            self.send_json(200, {
                "success": True,
                "message": "Siparis durumu basariyla guncellendi.",
                "updated": affected > 0,
                "order": dict(ord_row) if ord_row else None
            })
            return

        # 15. Admin: Create New User / Customer
        if path == '/api/admin/users/create':
            email = (data.get('email') or '').lower().strip()
            full_name = data.get('full_name', '').strip()
            role = data.get('role', 'customer').strip().lower()
            password = data.get('password', 'pozitron2026')
            phone = data.get('phone', '')
            city = data.get('city', 'Istanbul')

            if not email or not full_name:
                conn.close()
                self.send_json(400, {"error": "E-posta ve ad soyad zorunludur."})
                return

            cursor.execute("SELECT id FROM users WHERE LOWER(email) = ?", (email,))
            if cursor.fetchone():
                conn.close()
                self.send_json(409, {"error": "Bu e-posta adresiyle kayitli bir kullanici zaten mevcut."})
                return

            user_id = f"usr_{uuid.uuid4().hex[:10]}"
            now_iso = datetime.now().isoformat()
            p_hash = hash_password(password)

            cursor.execute('''
                INSERT INTO users (id, email, password_hash, full_name, role, phone, city, provider, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'manual', ?)
            ''', (user_id, email, p_hash, full_name, role, phone, city, now_iso))
            conn.commit()
            conn.close()

            self.send_json(201, {
                "success": True,
                "message": "Kullanici basariyla olusturuldu.",
                "user": {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "role": role,
                    "phone": phone,
                    "city": city,
                    "provider": "manual",
                    "created_at": now_iso
                }
            })
            return

        # 16. Admin: Export to static data files
        if path == '/api/admin/sync-export':
            conn.close()
            try:
                export_static_data()
                self.send_json(200, {
                    "success": True,
                    "message": "Static data bundle exported successfully to data/ folder"
                })
            except Exception as ex:
                self.send_json(500, {"error": f"Export failed: {str(ex)}"})
            return

        conn.close()
        self.send_json(404, {"error": "API route not found"})

class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True

def run_server():
    global PORT
    ports_to_try = [int(os.environ.get('PORT', 8000)), 8000, 8001, 8081, 3000]
    httpd = None
    for p in ports_to_try:
        try:
            server_address = ('0.0.0.0', p)
            httpd = ThreadedHTTPServer(server_address, PozitronRequestHandler)
            PORT = p
            break
        except OSError as e:
            if "Address already in use" in str(e) or e.errno == 98:
                continue
            raise
    if not httpd:
        raise RuntimeError(f"Could not bind to any port in {ports_to_try}")
    print(f"==================================================")
    print(f" Pozitron Drone Shopping Platform Running on http://localhost:{PORT}")
    try:
        _c_db = get_db()
        _cur = _c_db.cursor()
        _cur.execute("SELECT count(*) FROM products")
        _active_count = _cur.fetchone()[0]
        _c_db.close()
    except Exception:
        _active_count = 506
    print(f" {_active_count} Drone Items Active in SQLite Database")
    print(f" Languages: Turkish (TR) & English (EN)")
    print(f"==================================================")
    start_all_schedulers()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
