#!/usr/bin/env python3
"""
Pozitron Market - Reddit Drone Asistani ve Organik PR Botu CLI
Usage:
    python3 reddit_bot.py --status
    python3 reddit_bot.py --scan
    python3 reddit_bot.py --auto-scan
    python3 reddit_bot.py --list [--filter draft|published|all] [--limit N]
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
    print("  [POZITRON MARKET] Reddit Drone Asistani ve Organik PR Botu")
    print("  pozitronmarket.com | Destekleyen: Google Gemini AI")
    print("=" * 68)

def cmd_status(agent: RedditDroneAgent):
    print_banner()
    status = agent.get_status()
    cfg = agent.get_safe_config()

    print(f"[*] Otonom Mod:        {'[AKTIF]' if status['is_autonomous_enabled'] else '[KAPALI (Onay Kuyrugu Modu)]'}")
    print(f"[*] Calisma Modu:      {'[TEST / DRY-RUN SIMULATION]' if status['dry_run_mode'] else '[CANLI REDDIT API]'}")
    print(f"[*] Tarama Sikligi:    Her {status['scan_interval_minutes']} dakikada bir")
    print(f"[*] Gunluk Limit:      Maksimum {status['max_replies_per_day']} yanit (Bugun gonderilen: {status['today_published_count']})")
    print(f"[*] Son Tarama:        {status['last_scan_at'] or 'Henuz yapilmadi'}")
    print(f"[*] Sonraki Tarama:    {status['next_scan_at'] or 'Planlanmadi'}")
    print("-" * 68)
    print("[-] Istatistikler:")
    print(f"   - Toplam Soru:     {status['total_questions_found']}")
    print(f"   - Bekleyen Taslak: {status['draft_count']}")
    print(f"   - Yayinlanan:      {status['published_count']}")
    print(f"   - Reddedilen:      {status['rejected_count']}")
    print(f"   - Hatali:          {status['failed_count']}")
    print("-" * 68)
    print(f"[AUTH] Reddit Kullanici:  {cfg.get('username') or 'Tanimlanmadi'}")
    print(f"[AUTH] Reddit App ID:     {cfg.get('client_id') or 'Tanimlanmadi'}")
    print(f"[AUTH] Reddit Secret:     {cfg.get('client_secret_masked') or 'Tanimlanmadi'}")
    print(f"[AI]   Gemini AI Modeli:  {cfg.get('gemini_api_key_masked') or 'Tanimlanmadi (Kural motoru aktif)'}")
    print(f"[HEDEF] Subredditler:     {cfg.get('subreddits')}")
    print("=" * 68)

def cmd_scan(agent: RedditDroneAgent):
    print("[INFO] Reddit topluluklari taraniyor ve drone sorulari araniyor...")
    res = agent.scan_and_process(autonomous=False)
    print("\n[TAMAMLANDI] Tarama Raporu:")
    print(f"   - Taranan Subreddit Sayisi: {res['scanned_subreddits']}")
    print(f"   - Yeni Bulunan Soru Sayisi: {res['new_questions_found']}")

    if res['discovered']:
        print("\n[BULUNAN SORULAR] Gemini tarafindan hazirlanan yanit taslaklari:")
        print("-" * 68)
        for q in res['discovered']:
            print(f"ID:           {q['id']}")
            print(f"Subreddit:    r/{q['subreddit']} | Yazar: u/{q['author']}")
            print(f"Baslik:       {q['title']}")
            print(f"Guven Skoru:  %{q['confidence_score']}")
            print(f"Yanit Taslagi:\n{q['gemini_reply'][:250]}...")
            print("-" * 68)
            print(f"Onaylayip yayinlamak icin: python3 reddit_bot.py --approve {q['id']}")
            print("-" * 68)
    else:
        print("[BILGI] Bu dongude yeni soru bulunamadi. Simulasyon sorulari yuklemek icin: python3 reddit_bot.py --seed")

def cmd_list(status_filter: str = "all", limit: int = 15):
    items = get_interactions(limit=limit, status=status_filter)
    print(f"\n[KUYRUK] Reddit Soru ve Yanit Listesi ({status_filter.upper()} - Son {len(items)} kayit):")
    print("-" * 84)
    print(f"{'ID':<14} | {'DURUM':<10} | {'SUBREDDIT':<14} | {'GUVEN':<6} | {'BASLIK'}")
    print("-" * 84)
    for it in items:
        st = it['status'].upper()
        sub = f"r/{it['subreddit']}"
        conf = f"%{it['confidence_score']}"
        title = it['title'][:32] + "..." if len(it['title']) > 32 else it['title']
        print(f"{it['id']:<14} | {st:<10} | {sub:<14} | {conf:<6} | {title}")
    print("-" * 84)

def cmd_approve(agent: RedditDroneAgent, interaction_id: str):
    print(f"[ISLEM] {interaction_id} ID'li yanit Reddit'e gonderiliyor...")
    res = agent.approve_reply(interaction_id)
    if res.get("success"):
        print("\n[BASARILI] Yanit Reddit'e iletildi.")
        print(f"- Mod:         {res.get('mode', 'dry_run').upper()}")
        print(f"- Yorum Linki: {res.get('permalink')}")
        print(f"- Zaman:       {res.get('published_at')}")
    else:
        print(f"\n[HATA] Gonderim basarisiz: {res.get('error')}")

def cmd_reject(agent: RedditDroneAgent, interaction_id: str):
    if agent.reject_reply(interaction_id):
        print(f"[BILGI] {interaction_id} ID'li taslak reddedildi ve arsivlendi.")
    else:
        print(f"[HATA] {interaction_id} bulunamadi.")

def cmd_seed(agent: RedditDroneAgent):
    print("[ISLEM] Gercekci Turk FPV/Drone topluluk sorulari ve Gemini yanitlari yukleniyor...")
    count = agent.seed_sample_questions()
    print(f"[BASARILI] {count} adet ornek soru ve Gemini yanit taslagi onay kuyruguna eklendi.")
    print("Incelemek icin: python3 reddit_bot.py --list")

def cmd_toggle(agent: RedditDroneAgent, mode: str):
    is_on = 1 if mode.lower() in ["on", "1", "true", "aktif"] else 0
    agent.update_config({"is_autonomous_enabled": is_on})
    print(f"[AYAR] Otonom mod {'[ACILDI]' if is_on else '[KAPATILDI]'}.")

def cmd_daemon(agent: RedditDroneAgent):
    print_banner()
    print("[BASLATILDI] Pozitron Market Reddit Drone Botu DAEMON modunda calisiyor...")
    scheduler = RedditScheduler(agent)
    scheduler.start()
    print("Arka plan zamanlayici aktif. Durdurmak icin Ctrl+C tuslarina basin.\n")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[KAPATILIYOR] Daemon durduruldu.")
        scheduler.stop()

def cmd_export_cookies():
    import json
    from reddit_agent.chrome_session import extract_chrome_reddit_session
    res = extract_chrome_reddit_session()
    if res.get("success") and res.get("cookies"):
        cookies_list = [{"name": k, "value": v, "domain": ".reddit.com", "path": "/"} for k, v in res["cookies"].items() if v]
        json_str = json.dumps(cookies_list)
        print("\n" + "=" * 68)
        print("[AUTH] REDDIT OTURUM CEREZLERI (GitHub Secret Icin Hazir):")
        print("=" * 68)
        print(json_str)
        print("=" * 68)
        print("[TALIMAT] Yukaridaki JSON metnini GitHub reponuzda:")
        print("Settings -> Secrets and variables -> Actions -> New repository secret")
        print("Isim: REDDIT_COOKIES_JSON olarak kaydedebilirsiniz.\n")
    else:
        print(f"[HATA] Cerezler okunamadi: {res.get('error')}")

def cmd_auto_scan(agent: RedditDroneAgent):
    print("[BASLATILDI] Otonom modda Reddit taramasi yurutuluyor...")
    res = agent.scan_and_process(autonomous=True)
    print("\n[TAMAMLANDI] Otonom Islem Raporu:")
    print(f"- Taranan Subreddit Sayisi: {res['scanned_subreddits']}")
    print(f"- Yeni Bulunan Soru Sayisi: {res['new_questions_found']}")
    print(f"- Otomatik Yayinlanan Yanit: {res['auto_published_count']}")

def main():
    parser = argparse.ArgumentParser(description="Pozitron Market Reddit Drone Botu CLI")
    parser.add_argument("--status", action="store_true", help="Bot durumu ve ayarlarini gosterir")
    parser.add_argument("--scan", action="store_true", help="Reddit'i hemen tara ve taslaklar olustur")
    parser.add_argument("--auto-scan", action="store_true", help="Reddit'i tara ve uygun sorulari otomatik yanitla")
    parser.add_argument("--list", action="store_true", help="Kuyruktaki soru ve yanitlari listele")
    parser.add_argument("--filter", default="all", choices=["all", "draft", "published", "rejected", "failed"], help="Listeleme durum filtresi")
    parser.add_argument("--limit", type=int, default=15, help="Maksimum listelenecek kayit sayisi")
    parser.add_argument("--approve", type=str, help="Belirtilen ID'li yanit taslagini onaylayip gonderir")
    parser.add_argument("--publish", type=str, help="--approve ile ayni")
    parser.add_argument("--reject", type=str, help="Belirtilen ID'li yanit taslagini reddeder")
    parser.add_argument("--seed", action="store_true", help="Test ve simulasyon icin ornek topluluk sorulari ekler")
    parser.add_argument("--toggle", choices=["on", "off"], help="Otonom modu acar veya kapatir")
    parser.add_argument("--daemon", action="store_true", help="Surekli arka planda tarama yapan zamanlayiciyi calistirir")
    parser.add_argument("--export-cookies", action="store_true", help="GitHub Actions Secrets icin Reddit cerezlerini JSON formatinda aktarir")

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
