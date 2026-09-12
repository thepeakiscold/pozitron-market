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

def main():
    parser = argparse.ArgumentParser(description="Pozitron Market Autonomous Instagram PR Agent CLI")
    parser.add_argument('--status', action='store_true', help="Ajan durumunu ve ayarlarını gösterir")
    parser.add_argument('--generate', action='store_true', help="Yeni bir gönderi taslağı ve 1080x1080 görsel üretir")
    parser.add_argument('--publish', action='store_true', help="Taslağı Instagram'da yayınlar (veya simüle eder)")
    parser.add_argument('--id', type=str, help="Yayınlanacak veya görüntülenecek gönderi ID'si")
    parser.add_argument('--type', type=str, choices=['product_spotlight', 'tool_showcase', 'deal_drop', 'pilot_tip', 'review_highlight'], help="İçerik sütunu/tipi")
    parser.add_argument('--product', type=str, help="Öne çıkarılacak ürün ID'si veya slug")
    parser.add_argument('--list', action='store_true', help="Kayıtlı gönderileri listeler")
    parser.add_argument('--limit', type=int, default=15, help="Listelenecek gönderi sayısı")
    parser.add_argument('--daemon', action='store_true', help="Sürekli arka plan planlayıcısı olarak çalıştırır")
    parser.add_argument('--toggle', type=str, choices=['on', 'off'], help="Otonom yayınlamayı açar veya kapatır")

    args = parser.parse_args()
    agent = InstagramPRAgent()

    if args.status:
        cmd_status(agent)
    elif args.generate:
        cmd_generate(agent, content_type=args.type, product_id=args.product)
    elif args.publish:
        cmd_publish(agent, post_id=args.id)
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
