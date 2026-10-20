"""
Stock image library for Instagram posts.

Uses copyright-free / freely-licensed images downloaded from Wikimedia Commons
(see scripts/download_free_images.py) as ambient backgrounds for selected posts.

Images carrying CC BY / CC BY-SA licenses require attribution; when such an image
is used, `attribution_text()` produces the credit line that is appended to the caption.
"""
import os
import json
import random

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STOCK_DIR = os.path.join(BASE_DIR, 'assets', 'instagram', 'stock')
MANIFEST_PATH = os.path.join(STOCK_DIR, 'manifest.json')

# Which stock categories fit which content pillar.
CATEGORY_BY_CONTENT = {
    'spot_guide': ['nature', 'drone'],
    'flight_weather_radar': ['nature', 'city'],
    'pilot_tip': ['workshop', 'electronics', 'tech_abstract'],
    'mistake_breakdown': ['workshop', 'electronics'],
    'drone_build_showcase': ['workshop', 'electronics'],
    'myth_buster': ['electronics', 'tech_abstract'],
    'maintenance_checklist': ['workshop', 'electronics'],
    'beginner_roadmap': ['drone', 'nature'],
    'community_quiz': ['drone', 'tech_abstract'],
    'hardware_battle': ['electronics', 'tech_abstract'],
    'review_highlight': ['drone', 'city'],
    'product_spotlight': ['drone', 'tech_abstract'],
    'deal_drop': ['tech_abstract', 'city'],
    'tool_showcase': ['tech_abstract', 'electronics'],
    'carousel_guide': ['electronics', 'tech_abstract'],
}

_cache = None


def load_manifest():
    global _cache
    if _cache is not None:
        return _cache
    if not os.path.exists(MANIFEST_PATH):
        _cache = []
        return _cache
    try:
        with open(MANIFEST_PATH, 'r', encoding='utf-8') as f:
            _cache = json.load(f)
    except Exception:
        _cache = []
    return _cache


def get_stock_image(content_type: str, recent_files=None, prefer_free: bool = True):
    """
    Returns a stock image entry for the given content type, avoiding recently used files.
    Prefers CC0 / Public-Domain images when available.
    """
    entries = load_manifest()
    if not entries:
        return None
    recent_files = set(recent_files or [])

    cats = CATEGORY_BY_CONTENT.get(content_type, ['tech_abstract', 'drone'])
    pool = [e for e in entries if e.get('category') in cats]
    if not pool:
        pool = entries

    fresh = [e for e in pool if e.get('file') not in recent_files]
    if fresh:
        pool = fresh

    if prefer_free:
        free = [e for e in pool if not e.get('requires_attribution')]
        if free:
            pool = free

    return random.choice(pool)


def resolve_path(entry) -> str:
    if not entry or not entry.get('file'):
        return ''
    return os.path.join(BASE_DIR, entry['file'].lstrip('./').lstrip('/'))


def attribution_text(entry) -> str:
    """Credit line for attribution-required images; empty for CC0/PD."""
    if not entry:
        return ''
    if not entry.get('requires_attribution'):
        return ''
    artist = (entry.get('artist') or '').strip()
    license_name = (entry.get('license') or '').strip()
    title = (entry.get('title') or '').strip()
    parts = []
    if artist:
        parts.append(f"Görsel: {artist}")
    if title:
        parts.append(f'"{title}"')
    if license_name:
        parts.append(license_name)
    parts.append('via Wikimedia Commons')
    return " | ".join(parts)


def recent_stock_files(limit: int = 20):
    """Best-effort list of recently used stock files from the post history."""
    try:
        from .db import get_instagram_posts
        files = []
        for p in get_instagram_posts(limit=limit):
            f = (p.get('metadata') or {}).get('stock_file')
            if f:
                files.append(f)
        return files
    except Exception:
        return []
