#!/usr/bin/env python3
"""
Pozitron Market — Autonomous Instagram PR Agent CLI
Usage:
    python3 instagram_pr_agent.py --status
    python3 instagram_pr_agent.py --generate [--type TYPE] [--product ID]
    python3 instagram_pr_agent.py --publish [--id POST_ID]
    python3 instagram_pr_agent.py --daemon
    python3 instagram_pr_agent.py --toggle on|off
    python3 instagram_pr_agent.py --list [--limit N]
"""

import sys
import os
import argparse
import time
from datetime import datetime

# Ensure root directory is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from instagram_agent.agent import InstagramPRAgent
from instagram_agent.scheduler import InstagramScheduler

def print_banner():
    print("=" * 64)
    print("  POZITRON MARKET - Otonom Instagram PR Ajani & Robotu")
    print("  pozitronmarket.com | @pozitronmarket")
    print("=" * 64)

def cmd_status(agent: InstagramPRAgent):
    print_banner()
    status = agent.get_status()
    cfg = agent.get_safe_config()

    token_status = "Tanimlanmadi"
    if cfg.get('has_access_token'):
        is_valid, reason = agent.publisher.test_token()
        token_status = "Gecerli ve Aktif" if is_valid else f"Suresi Dolmus / Gecersiz ({reason})"

    print(f"[-] Otonom Mod:       {'[AKTIF]' if status['is_autonomous_enabled'] else '[KAPALI]'}")
    print(f"[-] Calisma Modu:     {'[TEST / DRY-RUN SIMULASYON]' if status['dry_run_mode'] else '[CANLI META API]'}")
    print(f"[-] Paylasim Sikligi: Her {status['posting_frequency_hours']} saatte bir")
    print(f"[-] Son Paylasim:     {status['last_run_at'] or 'Henuz yapilmadi'}")
    print(f"[-] Sonraki Paylasim: {status['next_run_at'] or 'Planlanmadi'}")
    print(f"[-] Toplam Gonderi:   {status['total_posts']} (Yayinlanan: {status['published_count']}, Taslak: {status['draft_count']}, Hata: {status['failed_count']})")
    print("-" * 64)
    print(f"[-] Meta Access Token: {cfg['access_token_masked'] or 'Tanimlanmadi'} -> {token_status}")
    print(f"[-] IG Account ID:     {cfg['instagram_account_id'] or 'Tanimlanmadi'}")
    print(f"[-] Gemini AI Key:     {cfg['gemini_api_key_masked'] or 'Tanimlanmadi (Kural motoru aktif)'}")
    print(f"[-] Genel Web URL:     {cfg['public_base_url']}")
    print("=" * 64)

def cmd_generate(agent: InstagramPRAgent, content_type: str = None, product_id: str = None):
    print("[BILGI] Yeni Instagram gonderisi ve 1080x1080 gorsel uretiliyor...")
    post = agent.generate_post(content_type=content_type, product_id=product_id)
    print("\n[BASARILI] Gonderi basariyla uretildi:")
    print(f"[-] Gonderi ID:    {post['id']}")
    print(f"[-] Konsept:       {post['content_type']}")
    print(f"[-] Gorsel Dosya:  {post['local_image_path']}")
    print("-" * 64)
    print(f"[-] BASLIK: {post['title']}")
    print("\n[-] METIN (CAPTION):")
    print(post['caption'])
    print("\n[-] HASHTAGLER:")
    print(post['hashtags'])
    print("-" * 64)
    print("[-] Paylasmak icin: python3 instagram_pr_agent.py --publish --id " + post['id'])

def cmd_publish(agent: InstagramPRAgent, post_id: str = None):
    print("[BILGI] Gonderi Instagram'a aktariliyor...")
    res = agent.publish_post(post_id=post_id)
    if res.get('success'):
        print("\n[BASARILI] Gonderi basariyla yayinlandi!")
        print(f"[-] Mod:           {res.get('mode', 'dry_run').upper()}")
        print(f"[-] IG Media ID:   {res.get('ig_media_id')}")
        print(f"[-] Gonderi Linki: {res.get('ig_permalink')}")
        print(f"[-] Zaman:         {res.get('published_at')}")
    else:
        print(f"\n[HATA] Yayinlama hatasi: {res.get('error')}")

def cmd_list(agent: InstagramPRAgent, limit: int = 15):
    posts = agent.get_posts(limit=limit)
    print(f"\n[-] Son {len(posts)} Instagram Gonderisi:")
    print("-" * 80)
    print(f"{'ID':<18} | {'DURUM':<10} | {'TIP':<18} | {'TARIH':<16} | {'BASLIK'}")
    print("-" * 80)
    for p in posts:
        dt = p['created_at'][:16].replace('T', ' ')
        print(f"{p['id']:<18} | {p['status'].upper():<10} | {p['content_type']:<18} | {dt:<16} | {p['title'][:25]}")
    print("-" * 80)

def cmd_daemon(agent: InstagramPRAgent):
    print_banner()
    print("[BILGI] Pozitron Market Instagram PR Ajani DAEMON modunda baslatiliyor...")
    scheduler = InstagramScheduler(agent)
    scheduler.start()
    print("Arka plan planlayici calisiyor. Cikmak icin Ctrl+C tuslarina basin.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[BILGI] Kapatiliyor...")
        scheduler.stop()

def cmd_direct_publish(agent: InstagramPRAgent, content_type: str = None, product_id: str = None):
    print("[BILGI] Yeni Instagram gonderisi ve 1080x1080 afis uretilip dogrudan yayina aktariliyor...")
    res = agent.generate_and_publish_now(content_type=content_type, product_id=product_id)
    if res.get('success'):
        print("\n[BASARILI] Gonderi basariyla yayinlandi!")
        print(f"[-] Mod:          {res.get('mode', 'live').upper()}")
        print(f"[-] Gonderi ID:   {res.get('post', {}).get('id')}")
        print(f"[-] Baslik:       {res.get('post', {}).get('title')}")
        print(f"[-] IG Permalink: {res.get('ig_permalink')}")
        if res.get('token_expired'):
            print("\n[UYARI] Meta Access Token suresi dolmus. Gonderi simulasyon (dry-run) modunda guvenle kaydedildi.")
            print("[ONERI] Canli Meta yayini icin Meta Developer panelinden yeni bir Access Token tanimlayiniz.")
    else:
        print(f"\n[HATA] Yayinlama hatasi: {res.get('error')}")
        if os.environ.get('CI') == 'true':
            print("[UYARI] CI ortaminda harici API hatasi nedeniyle is akisi durdurulmadi, sonraki adimlara devam ediliyor.")
        else:
            sys.exit(1)

def cmd_engage():
    from instagram_agent.engagement import InstagramEngagementEngine
    print("[BILGI] Drone Toplulugu Etkilesim Motoru Baslatiliyor (Hedef: 10 Takip & 10 Yorum)...")
    engine = InstagramEngagementEngine()
    res = engine.run_daily_drone_engagement(target_count=10)
    print("\n" + "=" * 60)
    print("ETKİLESİM RAPORU:")
    print(f"[-] Yeni Takip Edilen Pilot: +{res.get('new_follows', 0)} (Bugun Toplam: {res.get('today_follows', 0)}/10)")
    print(f"[-] Yapilan Yeni Yorum:       +{res.get('new_comments', 0)} (Bugun Toplam: {res.get('today_comments', 0)}/10)")
    if res.get('interacted_pilots'):
        print("\nEtkilesime Gecilen Pilotlar:")
        for p in res['interacted_pilots']:
            print(f"  * @{p['username']}: {p['post_url']}")
    print("=" * 60)

def cmd_auto(agent: InstagramPRAgent, force: bool = False):
    cfg = agent.get_safe_config()
    freq_hours = cfg.get('posting_frequency_hours', 6)
    last_run_str = agent.config.get('last_run_at')
    should_post = force
    
    if not should_post:
        if not last_run_str:
            should_post = True
        else:
            try:
                last_dt = datetime.fromisoformat(last_run_str)
                hours_passed = (datetime.now() - last_dt).total_seconds() / 3600.0
                if hours_passed >= freq_hours:
                    should_post = True
                else:
                    print(f"[BILGI] Son paylasimdan bu yana {hours_passed:.1f} saat gecti (Aralik: {freq_hours} saat). Paylasim henuz beklenmiyor.")
            except Exception:
                should_post = True

    if should_post:
        print(f"[BASLATILIYOR] Paylasim periyodu ({freq_hours} saat) geldi! Dogrudan gonderi uretilip yayinlaniyor...")
        cmd_direct_publish(agent)
    
    # Run daily engagement
    print("\n[ETKİLESİM] Gunluk drone toplulugu etkilesimi yurutuluyor...")
    try:
        cmd_engage()
    except Exception as e:
        print(f"[UYARI] Topluluk etkilesimi sirasinda hata olustu: {e}")

def cmd_auto_cycle(agent: InstagramPRAgent):
    print("[BILGI] Pozitron Market Instagram PR Robotu Otonom Dongusu Baslatiliyor...")
    res = agent.run_autonomous_cycle(run_engagement=True)
    if res.get('success'):
        print("\n[BASARILI] OTONOM GONDERİ DONGUSU BASARIYLA TAMAMLANDI!")
        print(f"[-] Gonderi ID:    {res.get('post_result', {}).get('post', {}).get('id')}")
        print(f"[-] Baslik:        {res.get('post_result', {}).get('post', {}).get('title')}")
        print(f"[-] IG Permalink:  {res.get('post_result', {}).get('ig_permalink')}")
    else:
        print(f"\n[HATA] Otonom gonderi hatasi: {res.get('post_result', {}).get('error')}")

def cmd_export_cookies():
    import json
    from instagram_agent.chrome_session import extract_chrome_instagram_cookies
    res = extract_chrome_instagram_cookies()
    if res.get("success") and res.get("cookies"):
        cookies_list = [{"name": k, "value": v, "domain": ".instagram.com", "path": "/"} for k, v in res["cookies"].items() if v]
        json_str = json.dumps(cookies_list)
        print("\n" + "=" * 68)
        print("INSTAGRAM OTURUM CEREZLERI (GitHub Secret Icin Hazir):")
        print("=" * 68)
        print(json_str)
        print("=" * 68)
        print("Yukarıdaki JSON metnini kopyalayip GitHub reponuzda:")
        print("   Settings -> Secrets and variables -> Actions -> New repository secret")
        print("   Isim: INSTAGRAM_COOKIES_JSON olarak yapistirabilirsiniz.\n")
    else:
        print(f"[HATA] Cerezler okunamadi: {res.get('error')}")

def main():
    parser = argparse.ArgumentParser(description="Pozitron Market Autonomous Instagram PR Agent CLI")
    parser.add_argument('--status', action='store_true', help="Ajan durumunu ve ayarlarini gosterir")
    parser.add_argument('--direct-publish', action='store_true', help="Taslaksiz: Tek adimda gonderi uretip canli yayinlar")
    parser.add_argument('--engage', action='store_true', help="Drone meraklisi pilotlari takip eder ve destek yorumu atar (Gunde 10)")
    parser.add_argument('--auto', action='store_true', help="Belirtilen aralik geldiyse direkt paylasir + drone etkilesimi yapar")
    parser.add_argument('--force', action='store_true', help="Araligi beklemeden --auto modunu hemen tetikler")
    parser.add_argument('--set-freq', type=int, help="Paylasim sikligini saat olarak ayarlar (or: 3, 6, 12, 24)")
    parser.add_argument('--generate', action='store_true', help="Yeni bir gonderi uretip yayinlar (Taslaksiz)")
    parser.add_argument('--publish', action='store_true', help="Dogrudan yayinlar")
    parser.add_argument('--auto-cycle', action='store_true', help="Tek adimda gorsel ve icerik uretip paylasir ve etkilesime gecer")
    parser.add_argument('--export-cookies', action='store_true', help="GitHub Actions Secrets icin Instagram oturum cerezlerini JSON olarak disa aktarir")
    parser.add_argument('--id', type=str, help="Yayinlanacak gonderi ID'si")
    parser.add_argument('--type', type=str, choices=['product_spotlight', 'tool_showcase', 'deal_drop', 'pilot_tip', 'review_highlight'], help="Icerik sutunu/tipi")
    parser.add_argument('--product', type=str, help="One cikarilacak urun ID'si veya slug")
    parser.add_argument('--list', action='store_true', help="Kayitli yayinlanan gonderileri listeler")
    parser.add_argument('--limit', type=int, default=15, help="Listelenecek gonderi sayisi")
    parser.add_argument('--daemon', action='store_true', help="Surekli arka plan planlayicisi olarak calistirir")
    parser.add_argument('--toggle', type=str, choices=['on', 'off'], help="Otonom yayinlamayi acar veya kapatir")

    args = parser.parse_args()
    agent = InstagramPRAgent()

    if args.set_freq:
        agent.update_config({'posting_frequency_hours': args.set_freq})
        print(f"[BASARILI] Paylasim sikligi guncellendi: Her {args.set_freq} saatte bir")
    elif args.status:
        cmd_status(agent)
    elif args.direct_publish or args.generate or args.publish:
        cmd_direct_publish(agent, content_type=args.type, product_id=args.product)
    elif args.engage:
        cmd_engage()
    elif args.auto:
        cmd_auto(agent, force=args.force)
    elif args.auto_cycle:
        cmd_auto_cycle(agent)
    elif args.export_cookies:
        cmd_export_cookies()
    elif args.list:
        cmd_list(agent, limit=args.limit)
    elif args.daemon:
        cmd_daemon(agent)
    elif args.toggle:
        enable = (args.toggle.lower() == 'on')
        agent.update_config({'is_autonomous_enabled': 1 if enable else 0})
        print(f"[BASARILI] Otonom mod: {'[ACIK]' if enable else '[KAPALI]'}")
    else:
        cmd_status(agent)

if __name__ == '__main__':
    main()
