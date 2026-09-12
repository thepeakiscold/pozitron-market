#!/usr/bin/env python3
"""
Pozitron Market — Reddit Drone Assistant & Organic Traffic Agent CLI
Usage:
    python3 reddit_bot.py --status
    python3 reddit_bot.py --scan
    python3 reddit_bot.py --list [--status draft|published|all] [--limit N]
    python3 reddit_bot.py --approve ID
    python3 reddit_bot.py --reject ID
    python3 reddit_bot.py --seed
    python3 reddit_bot.py --toggle on|off
    python3 reddit_bot.py --daemon
"""

import sys
import os
import argparse
import time

# Ensure workspace root is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from reddit_agent.agent import RedditDroneAgent
from reddit_agent.scheduler import RedditScheduler
from reddit_agent.db import get_interactions

def print_banner():
    print("=" * 68)
    print("  🛸 POZITRON MARKET — Reddit Drone Asistanı & Organik PR Botu")
    print("  🌐 pozitronmarket.com | 🤖 Destekleyen: Google Gemini AI")
    print("=" * 68)

def cmd_status(agent: RedditDroneAgent):
    print_banner()
    status = agent.get_status()
    cfg = agent.get_safe_config()

    print(f"🔹 Otonom Mod:        {'[AKTİF]' if status['is_autonomous_enabled'] else '[KAPALI (Onay Kuyruğu Modu)]'}")
    print(f"🔹 Çalışma Modu:      {'[TEST / DRY-RUN SIMULATION]' if status['dry_run_mode'] else '[CANLI REDDIT API]'}")
    print(f"🔹 Tarama Sıklığı:    Her {status['scan_interval_minutes']} dakikada bir")
    print(f"🔹 Günlük Limit:      Maksimum {status['max_replies_per_day']} yanıt (Bugün gönderilen: {status['today_published_count']})")
    print(f"🔹 Son Tarama:        {status['last_scan_at'] or 'Henüz yapılmadı'}")
    print(f"🔹 Sonraki Tarama:    {status['next_scan_at'] or 'Planlanmadı'}")
    print("-" * 68)
    print(f"📊 İstatistikler:")
    print(f"   • Toplam Soru:     {status['total_questions_found']}")
    print(f"   • Bekleyen Taslak: {status['draft_count']}")
    print(f"   • Yayınlanan:      {status['published_count']}")
    print(f"   • Reddedilen:      {status['rejected_count']}")
    print(f"   • Hatalı:          {status['failed_count']}")
    print("-" * 68)
    print(f"🔑 Reddit Kullanıcı:  {cfg.get('username') or 'Tanımlanmadı'}")
    print(f"🔑 Reddit App ID:     {cfg.get('client_id') or 'Tanımlanmadı'}")
    print(f"🔑 Reddit Secret:     {cfg.get('client_secret_masked') or 'Tanımlanmadı'}")
    print(f"🤖 Gemini AI Anahtarı: {cfg.get('gemini_api_key_masked') or 'Tanımlanmadı (Kural motoru aktif)'}")
    print(f"🎯 Hedef Subredditler: {cfg.get('subreddits')}")
    print("=" * 68)

def cmd_scan(agent: RedditDroneAgent):
    print("🔍 Reddit toplulukları taranıyor ve drone soruları aranıyor...")
    res = agent.scan_and_process(autonomous=False)
    print(f"\n✅ Tarama Tamamlandı:")
    print(f"   • Taranan Subreddit Sayısı: {res['scanned_subreddits']}")
    print(f"   • Yeni Bulunan Soru Sayısı: {res['new_questions_found']}")

    if res['discovered']:
        print("\n📋 Bulunan Sorular ve Gemini'nin Hazırladığı Yanıtlar:")
        print("-" * 68)
        for q in res['discovered']:
            print(f"🆔 ID:         {q['id']}")
            print(f"📍 Subreddit:  r/{q['subreddit']} | Yazar: u/{q['author']}")
            print(f"❓ Başlık:     {q['title']}")
            print(f"🎯 Güven:      %{q['confidence_score']}")
            print(f"💬 Gemini Yanıt Taslağı:\n{q['gemini_reply'][:250]}...")
            print("-" * 68)
            print(f"👉 Yanıtı onaylayıp göndermek için: python3 reddit_bot.py --approve {q['id']}")
            print("-" * 68)
    else:
        print("💡 Bu döngüde yeni soru bulunamadı. Simülasyon soruları yüklemek için: python3 reddit_bot.py --seed")

def cmd_list(status_filter: str = "all", limit: int = 15):
    items = get_interactions(limit=limit, status=status_filter)
    print(f"\n📋 Reddit Soru & Yanıt Kuyruğu ({status_filter.upper()} - Son {len(items)} kayıt):")
    print("-" * 84)
    print(f"{'ID':<14} | {'DURUM':<10} | {'SUBREDDIT':<14} | {'GÜVEN':<6} | {'BAŞLIK'}")
    print("-" * 84)
    for it in items:
        st = it['status'].upper()
        sub = f"r/{it['subreddit']}"
        conf = f"%{it['confidence_score']}"
        title = it['title'][:32] + "..." if len(it['title']) > 32 else it['title']
        print(f"{it['id']:<14} | {st:<10} | {sub:<14} | {conf:<6} | {title}")
    print("-" * 84)

def cmd_approve(agent: RedditDroneAgent, interaction_id: str):
    print(f"🚀 {interaction_id} ID'li yanıt Reddit'e gönderiliyor...")
    res = agent.approve_reply(interaction_id)
    if res.get("success"):
        print(f"\n🎉 YANIT BAŞARIYLA GÖNDERİLDİ!")
        print(f"🔹 Mod:           {res.get('mode', 'dry_run').upper()}")
        print(f"🔹 Yorum Linki:   {res.get('permalink')}")
        print(f"🔹 Zaman:         {res.get('published_at')}")
    else:
        print(f"\n❌ GÖNDERME HATASI: {res.get('error')}")

def cmd_reject(agent: RedditDroneAgent, interaction_id: str):
    if agent.reject_reply(interaction_id):
        print(f"🗑️ {interaction_id} ID'li taslak reddedildi ve arşivlendi.")
    else:
        print(f"❌ Hata: {interaction_id} bulunamadı.")

def cmd_seed(agent: RedditDroneAgent):
    print("🌱 Gerçekçi Türk FPV/Drone topluluk soruları ve Gemini yanıtları simülasyona ekleniyor...")
    count = agent.seed_sample_questions()
    print(f"✅ {count} adet örnek soru ve Gemini yanıt taslağı onay kuyruğuna eklendi!")
    print("💡 İncelemek için: python3 reddit_bot.py --list")

def cmd_toggle(agent: RedditDroneAgent, mode: str):
    is_on = 1 if mode.lower() in ["on", "1", "true", "aktif"] else 0
    agent.update_config({"is_autonomous_enabled": is_on})
    print(f"⚙️ Otonom mod {'[AÇILDI]' if is_on else '[KAPATILDI]'}.")

def cmd_daemon(agent: RedditDroneAgent):
    print_banner()
    print("🚀 Pozitron Market Reddit Drone Botu DAEMON modunda başlatılıyor...")
    scheduler = RedditScheduler(agent)
    scheduler.start()
    print("Arka plan zamanlayıcı aktif. Çıkmak için Ctrl+C tuşlarına basın.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Kapatılıyor...")
        scheduler.stop()

def cmd_export_cookies():
    import json
    from reddit_agent.chrome_session import extract_chrome_reddit_session
    res = extract_chrome_reddit_session()
    if res.get("success") and res.get("cookies"):
        cookies_list = [{"name": k, "value": v, "domain": ".reddit.com", "path": "/"} for k, v in res["cookies"].items() if v]
        json_str = json.dumps(cookies_list)
        print("\n" + "=" * 68)
        print("🔑 REDDIT OTURUM ÇEREZLERİ (GitHub Secret İçin Hazır):")
        print("=" * 68)
        print(json_str)
        print("=" * 68)
        print("👉 Yukarıdaki JSON metnini kopyalayıp GitHub reponuzda:")
        print("   Settings -> Secrets and variables -> Actions -> New repository secret")
        print("   İsim: REDDIT_COOKIES_JSON olarak yapıştırabilirsiniz.\n")
    else:
        print(f"❌ Çerezler okunamadı: {res.get('error')}")

def cmd_auto_scan(agent: RedditDroneAgent):
    print("🚀 Otonom modda Reddit taraması başlatılıyor...")
    res = agent.scan_and_process(autonomous=True)
    print(f"\n✅ Otonom İşlem Tamamlandı:")
    print(f"   • Taranan Subreddit Sayısı: {res['scanned_subreddits']}")
    print(f"   • Yeni Bulunan Soru Sayısı: {res['new_questions_found']}")
    print(f"   • Otomatik Yayınlanan Yanıt: {res['auto_published_count']}")

def main():
    parser = argparse.ArgumentParser(description="Pozitron Market Reddit Drone Botu")
    parser.add_argument("--status", action="store_true", help="Bot durumu ve ayarları gösterir")
    parser.add_argument("--scan", action="store_true", help="Reddit'i hemen tara ve yanıt taslakları oluştur")
    parser.add_argument("--auto-scan", action="store_true", help="Reddit'i tara ve uygun soruları otomatik olarak yanıtla (CI/GitHub Actions)")
    parser.add_argument("--list", action="store_true", help="Kuyruktaki soru ve yanıtları listele")
    parser.add_argument("--filter", default="all", choices=["all", "draft", "published", "rejected", "failed"], help="Listeleme durum filtresi")
    parser.add_argument("--limit", type=int, default=15, help="Maksimum listelenecek kayıt sayısı")
    parser.add_argument("--approve", type=str, help="Belirtilen ID'li yanıt taslağını onaylayıp Reddit'e gönderir")
    parser.add_argument("--publish", type=str, help="--approve ile aynı")
    parser.add_argument("--reject", type=str, help="Belirtilen ID'li yanıt taslağını reddeder")
    parser.add_argument("--seed", action="store_true", help="Test ve simülasyon için örnek topluluk soruları ekler")
    parser.add_argument("--toggle", choices=["on", "off"], help="Otonom modu açar veya kapatır")
    parser.add_argument("--daemon", action="store_true", help="Sürekli arka planda tarama yapan zamanlayıcıyı çalıştırır")
    parser.add_argument("--export-cookies", action="store_true", help="GitHub Actions Secrets için Reddit çerezlerini JSON formatında dışa aktarır")

    args = parser.parse_args()

    if args.export_cookies:
        cmd_export_cookies()
        return

    agent = RedditDroneAgent()

    if args.status:
        cmd_status(agent)
    elif args.scan:
        cmd_scan(agent)
    elif args.auto_scan:
        cmd_auto_scan(agent)
    elif args.list:
        cmd_list(status_filter=args.filter, limit=args.limit)
    elif args.approve or args.publish:
        cmd_approve(agent, args.approve or args.publish)
    elif args.reject:
        cmd_reject(agent, args.reject)
    elif args.seed:
        cmd_seed(agent)
    elif args.toggle:
        cmd_toggle(agent, args.toggle)
    elif args.daemon:
        cmd_daemon(agent)
    else:
        cmd_status(agent)

if __name__ == "__main__":
    main()
