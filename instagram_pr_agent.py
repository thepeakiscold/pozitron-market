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
    print("  ⚡ POZITRON MARKET — Otonom Instagram PR Ajanı & Robotu")
    print("  🌐 pozitronmarket.com | 📱 @pozitronmarket")
    print("=" * 64)

def cmd_status(agent: InstagramPRAgent):
    print_banner()
    status = agent.get_status()
    cfg = agent.get_safe_config()
    print(f"🔹 Otonom Mod:       {'[AKTİF]' if status['is_autonomous_enabled'] else '[KAPALI]'}")
    print(f"🔹 Çalışma Modu:     {'[TEST / DRY-RUN SIMULATION]' if status['dry_run_mode'] else '[CANLI META API]'}")
    print(f"🔹 Paylaşım Sıklığı: Her {status['posting_frequency_hours']} saatte bir")
    print(f"🔹 Son Paylaşım:     {status['last_run_at'] or 'Henüz yapılmadı'}")
    print(f"🔹 Sonraki Paylaşım: {status['next_run_at'] or 'Planlanmadı'}")
    print(f"🔹 Toplam Gönderi:   {status['total_posts']} (Yayınlanan: {status['published_count']}, Taslak: {status['draft_count']}, Hata: {status['failed_count']})")
    print("-" * 64)
    print(f"🔑 Meta Access Token: {cfg['access_token_masked'] or 'Tanımlanmadı'}")
    print(f"🔑 IG Account ID:     {cfg['instagram_account_id'] or 'Tanımlanmadı'}")
    print(f"🤖 Gemini AI Anahtarı: {cfg['gemini_api_key_masked'] or 'Tanımlanmadı (Kural motoru aktif)'}")
    print(f"🌐 Genel Web URL'si:   {cfg['public_base_url']}")
    print("=" * 64)

def cmd_generate(agent: InstagramPRAgent, content_type: str = None, product_id: str = None):
    print("🎨 Yeni Instagram gönderisi ve 1080x1080 görsel üretiliyor...")
    post = agent.generate_post(content_type=content_type, product_id=product_id)
    print("\n✅ GÖNDERİ BAŞARIYLA ÜRETİLDİ:")
    print(f"📌 Gönderi ID:   {post['id']}")
    print(f"🏷️ Konsept:      {post['content_type']}")
    print(f"🖼️ Görsel Dosyası: {post['local_image_path']}")
    print("-" * 64)
    print(f"📝 BAŞLIK: {post['title']}")
    print("\n📄 METİN (CAPTION):")
    print(post['caption'])
    print("\n🏷️ HASHTAG'LER:")
    print(post['hashtags'])
    print("-" * 64)
    print("💡 Paylaşmak için: python3 instagram_pr_agent.py --publish --id " + post['id'])

def cmd_publish(agent: InstagramPRAgent, post_id: str = None):
    print("🚀 Gönderi Instagram'a aktarılıyor...")
    res = agent.publish_post(post_id=post_id)
    if res.get('success'):
        print("\n🎉 GÖNDERİ BAŞARIYLA YAYINLANDI!")
        print(f"🔹 Mod:           {res.get('mode', 'dry_run').upper()}")
        print(f"🔹 IG Media ID:   {res.get('ig_media_id')}")
        print(f"🔹 Gönderi Linki: {res.get('ig_permalink')}")
        print(f"🔹 Zaman:         {res.get('published_at')}")
    else:
        print(f"\n❌ YAYINLAMA HATASI: {res.get('error')}")

def cmd_list(agent: InstagramPRAgent, limit: int = 15):
    posts = agent.get_posts(limit=limit)
    print(f"\n📋 Son {len(posts)} Instagram Gönderisi:")
    print("-" * 80)
    print(f"{'ID':<18} | {'DURUM':<10} | {'TİP':<18} | {'TARİH':<16} | {'BAŞLIK'}")
    print("-" * 80)
    for p in posts:
        dt = p['created_at'][:16].replace('T', ' ')
        print(f"{p['id']:<18} | {p['status'].upper():<10} | {p['content_type']:<18} | {dt:<16} | {p['title'][:25]}")
    print("-" * 80)

def cmd_daemon(agent: InstagramPRAgent):
    print_banner()
    print("🚀 Pozitron Market Instagram PR Ajanı DAEMON modunda başlatılıyor...")
    scheduler = InstagramScheduler(agent)
    scheduler.start()
    print("Arka plan planlayıcı çalışıyor. Çıkmak için Ctrl+C tuşlarına basın.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Kapatılıyor...")
        scheduler.stop()

def cmd_direct_publish(agent: InstagramPRAgent, content_type: str = None, product_id: str = None):
    print("⚡ Yeni Instagram gönderisi ve 1080x1080 afiş üretilip doğrudan canlı yayına aktarılıyor (Taslaksız)...")
    res = agent.generate_and_publish_now(content_type=content_type, product_id=product_id)
    if res.get('success'):
        print("\n🎉 GÖNDERİ BAŞARIYLA YAYINLANDI!")
        print(f"🔹 Mod:           {res.get('mode', 'live').upper()}")
        print(f"🔹 Gönderi ID:    {res.get('post', {}).get('id')}")
        print(f"🔹 Başlık:        {res.get('post', {}).get('title')}")
        print(f"🔹 IG Permalink:  {res.get('ig_permalink')}")
    else:
        print(f"\n❌ YAYINLAMA HATASI: {res.get('error')}")
        sys.exit(1)

def cmd_engage():
    from instagram_agent.engagement import InstagramEngagementEngine
    print("🛸 Drone Topluluğu Etkileşim Motoru Başlatılıyor (Hedef: 10 Takip & 10 Yorum)...")
    engine = InstagramEngagementEngine()
    res = engine.run_daily_drone_engagement(target_count=10)
    print("\n" + "=" * 60)
    print("📊 ETKİLEŞİM RAPORU:")
    print(f"👤 Yeni Takip Edilen Pilot: +{res.get('new_follows', 0)} (Bugün Toplam: {res.get('today_follows', 0)}/10)")
    print(f"💬 Yapılan Yeni Yorum:       +{res.get('new_comments', 0)} (Bugün Toplam: {res.get('today_comments', 0)}/10)")
    if res.get('interacted_pilots'):
        print("\nEtkileşime Geçilen Pilotlar:")
        for p in res['interacted_pilots']:
            print(f"  • @{p['username']}: {p['post_url']}")
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
                    print(f"ℹ️ Son paylaşımdan bu yana {hours_passed:.1f} saat geçti (Aralık: {freq_hours} saat). Paylaşım henüz beklenmiyor.")
            except Exception:
                should_post = True

    if should_post:
        print(f"🚀 Paylaşım periyodu ({freq_hours} saat) geldi! Doğrudan gönderi üretilip yayınlanıyor...")
        cmd_direct_publish(agent)
    
    # Run daily engagement
    print("\n🛸 Günlük drone topluluğu etkileşimi yürütülüyor...")
    cmd_engage()

def cmd_auto_cycle(agent: InstagramPRAgent):
    print("🚀 Pozitron Market Instagram PR Robotu Otonom Döngüsü Başlatılıyor...")
    res = agent.run_autonomous_cycle(run_engagement=True)
    if res.get('success'):
        print("\n🎉 OTONOM GÖNDERİ DÖNGÜSÜ BAŞARIYLA TAMAMLANDI!")
        print(f"🔹 Gönderi ID:    {res.get('post_result', {}).get('post', {}).get('id')}")
        print(f"🔹 Başlık:        {res.get('post_result', {}).get('post', {}).get('title')}")
        print(f"🔹 IG Permalink:  {res.get('post_result', {}).get('ig_permalink')}")
    else:
        print(f"\n❌ OTONOM GÖNDERİ HATASI: {res.get('post_result', {}).get('error')}")

def cmd_export_cookies():
    import json
    from instagram_agent.chrome_session import extract_chrome_instagram_cookies
    res = extract_chrome_instagram_cookies()
    if res.get("success") and res.get("cookies"):
        cookies_list = [{"name": k, "value": v, "domain": ".instagram.com", "path": "/"} for k, v in res["cookies"].items() if v]
        json_str = json.dumps(cookies_list)
        print("\n" + "=" * 68)
        print("🔑 INSTAGRAM OTURUM ÇEREZLERİ (GitHub Secret İçin Hazır):")
        print("=" * 68)
        print(json_str)
        print("=" * 68)
        print("👉 Yukarıdaki JSON metnini kopyalayıp GitHub reponuzda:")
        print("   Settings -> Secrets and variables -> Actions -> New repository secret")
        print("   İsim: INSTAGRAM_COOKIES_JSON olarak yapıştırabilirsiniz.\n")
    else:
        print(f"❌ Çerezler okunamadı: {res.get('error')}")

def main():
    parser = argparse.ArgumentParser(description="Pozitron Market Autonomous Instagram PR Agent CLI")
    parser.add_argument('--status', action='store_true', help="Ajan durumunu ve ayarlarını gösterir")
    parser.add_argument('--direct-publish', action='store_true', help="Taslaksız: Tek adımda gönderi üretip canlı yayınlar")
    parser.add_argument('--engage', action='store_true', help="Drone meraklısı pilotları takip eder ve destek yorumu atar (Günde 10)")
    parser.add_argument('--auto', action='store_true', help="Belirtilen aralık geldiyse direkt paylaşır + drone etkileşimi yapar")
    parser.add_argument('--force', action='store_true', help="Aralığı beklemeden --auto modunu hemen tetikler")
    parser.add_argument('--set-freq', type=int, help="Paylaşım sıklığını saat olarak ayarlar (ör: 3, 6, 12, 24)")
    parser.add_argument('--generate', action='store_true', help="Yeni bir gönderi üretip yayınlar (Taslaksız)")
    parser.add_argument('--publish', action='store_true', help="Doğrudan yayınlar")
    parser.add_argument('--auto-cycle', action='store_true', help="Tek adımda görsel ve içerik üretip paylaşır ve etkileşime geçer")
    parser.add_argument('--export-cookies', action='store_true', help="GitHub Actions Secrets için Instagram oturum çerezlerini JSON olarak dışa aktarır")
    parser.add_argument('--id', type=str, help="Yayınlanacak gönderi ID'si")
    parser.add_argument('--type', type=str, choices=['product_spotlight', 'tool_showcase', 'deal_drop', 'pilot_tip', 'review_highlight'], help="İçerik sütunu/tipi")
    parser.add_argument('--product', type=str, help="Öne çıkarılacak ürün ID'si veya slug")
    parser.add_argument('--list', action='store_true', help="Kayıtlı yayınlanan gönderileri listeler")
    parser.add_argument('--limit', type=int, default=15, help="Listelenecek gönderi sayısı")
    parser.add_argument('--daemon', action='store_true', help="Sürekli arka plan planlayıcısı olarak çalıştırır")
    parser.add_argument('--toggle', type=str, choices=['on', 'off'], help="Otonom yayınlamayı açar veya kapatır")

    args = parser.parse_args()
    agent = InstagramPRAgent()

    if args.set_freq:
        agent.update_config({'posting_frequency_hours': args.set_freq})
        print(f"✅ Paylaşım sıklığı güncellendi: Her {args.set_freq} saatte bir")
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
        print(f"✅ Otonom mod: {'[AÇIK]' if enable else '[KAPALI]'}")
    else:
        cmd_status(agent)

if __name__ == '__main__':
    main()
