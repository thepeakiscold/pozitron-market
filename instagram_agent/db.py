import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pozitron.db')
JSON_POSTS_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'instagram_posts.json')
JSON_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'instagram_config.json')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def sync_posts_from_json(cursor):
    """Imports posts from data/instagram_posts.json if SQLite table is fresh."""
    if os.path.exists(JSON_POSTS_PATH):
        try:
            with open(JSON_POSTS_PATH, 'r', encoding='utf-8') as f:
                posts = json.load(f)
            for p in posts:
                cursor.execute('''
                    INSERT OR IGNORE INTO instagram_posts (
                        id, content_type, product_id, title, caption, hashtags,
                        image_url, local_image_path, status, ig_media_id, ig_permalink,
                        error_message, scheduled_at, published_at, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    p['id'], p.get('content_type', 'product_spotlight'), p.get('product_id'),
                    p.get('title', ''), p.get('caption', ''), p.get('hashtags', ''),
                    p.get('image_url', ''), p.get('local_image_path', ''), p.get('status', 'published'),
                    p.get('ig_media_id'), p.get('ig_permalink'), p.get('error_message'),
                    p.get('scheduled_at'), p.get('published_at'),
                    json.dumps(p.get('metadata', {}), ensure_ascii=False) if isinstance(p.get('metadata'), dict) else p.get('metadata_json', '{}'),
                    p.get('created_at', datetime.now().isoformat())
                ))
        except Exception:
            pass

def sync_posts_to_json():
    """Exports SQLite published posts to data/instagram_posts.json for Git persistence. Drafts are never exported."""
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM instagram_posts WHERE status = 'published' ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        posts = [dict(r) for r in rows]
        os.makedirs(os.path.dirname(JSON_POSTS_PATH), exist_ok=True)
        with open(JSON_POSTS_PATH, 'w', encoding='utf-8') as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def init_instagram_tables():
    conn = get_db()
    cursor = conn.cursor()

    # Instagram Agent Configuration
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS instagram_agent_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            access_token TEXT,
            instagram_account_id TEXT,
            gemini_api_key TEXT,
            is_autonomous_enabled INTEGER DEFAULT 0,
            posting_frequency_hours INTEGER DEFAULT 12,
            dry_run_mode INTEGER DEFAULT 1,
            public_base_url TEXT DEFAULT 'https://raw.githubusercontent.com/thepeakiscold/pozitron-market/main',
            preferred_language TEXT DEFAULT 'tr',
            default_hashtags TEXT DEFAULT '#fpvturkey #fpvdrone #pozitronmarket #dronetopla #fpvpilot #fpvracing',
            last_run_at TEXT,
            next_run_at TEXT,
            updated_at TEXT
        )
    ''')

    # Seed default config if empty
    cursor.execute("SELECT count(*) FROM instagram_agent_config")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO instagram_agent_config (
                id, access_token, instagram_account_id, gemini_api_key,
                is_autonomous_enabled, posting_frequency_hours, dry_run_mode,
                public_base_url, preferred_language, default_hashtags,
                last_run_at, next_run_at, updated_at
            ) VALUES (
                1, '', '', '', 0, 12, 1, 'https://raw.githubusercontent.com/thepeakiscold/pozitron-market/main', 'tr',
                '#fpvturkey #fpvdrone #pozitronmarket #dronetopla #fpvpilot #fpvracing #betafpv #iflight #tmotor',
                NULL, NULL, ?
            )
        ''', (datetime.now().isoformat(),))

    # Instagram Posts History & Queue
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS instagram_posts (
            id TEXT PRIMARY KEY,
            content_type TEXT NOT NULL, -- 'product_spotlight', 'tool_showcase', 'deal_drop', 'pilot_tip', 'review_highlight'
            product_id TEXT,
            title TEXT NOT NULL,
            caption TEXT NOT NULL,
            hashtags TEXT NOT NULL,
            image_url TEXT NOT NULL,
            local_image_path TEXT NOT NULL,
            status TEXT NOT NULL, -- 'draft', 'scheduled', 'published', 'failed'
            ig_media_id TEXT,
            ig_permalink TEXT,
            error_message TEXT,
            scheduled_at TEXT,
            published_at TEXT,
            metadata_json TEXT,
            image_mode TEXT DEFAULT 'canvas', -- 'canvas' or 'gemini_image'
            created_at TEXT NOT NULL,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE SET NULL
        )
    ''')

    # Migration: Ensure image_mode exists
    cursor.execute("PRAGMA table_info(instagram_posts)")
    ig_cols = [c[1] for c in cursor.fetchall()]
    if 'image_mode' not in ig_cols:
        cursor.execute("ALTER TABLE instagram_posts ADD COLUMN image_mode TEXT DEFAULT 'canvas'")

    # Seed from data/instagram_posts.json if present
    sync_posts_from_json(cursor)

    conn.commit()
    conn.close()

def get_agent_config():
    init_instagram_tables()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM instagram_agent_config WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    db_cfg = dict(row) if row else {}

    cfg = {}
    # Base configuration from json if available
    if os.path.exists(JSON_CONFIG_PATH):
        try:
            with open(JSON_CONFIG_PATH, 'r', encoding='utf-8') as f:
                json_cfg = json.load(f)
            cfg.update(json_cfg)
        except Exception:
            pass

    # Ensure SQLite operational settings take absolute precedence
    cfg.update(db_cfg)
    return cfg

def update_agent_config(updates: dict):
    init_instagram_tables()
    allowed_fields = [
        'access_token', 'instagram_account_id', 'gemini_api_key',
        'is_autonomous_enabled', 'posting_frequency_hours', 'dry_run_mode',
        'public_base_url', 'preferred_language', 'default_hashtags',
        'last_run_at', 'next_run_at'
    ]
    fields = []
    params = []
    for k, v in updates.items():
        if k in allowed_fields:
            fields.append(f"{k} = ?")
            params.append(v)

    if fields:
        fields.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(1)

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE instagram_agent_config SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
        conn.close()

    # Also persist to data/instagram_config.json
    try:
        json_cfg = {}
        if os.path.exists(JSON_CONFIG_PATH):
            with open(JSON_CONFIG_PATH, 'r', encoding='utf-8') as f:
                json_cfg = json.load(f)
        for k, v in updates.items():
            if k not in ('access_token', 'gemini_api_key'):  # Don't leak raw secrets to git json
                json_cfg[k] = v
        json_cfg['updated_at'] = datetime.now().isoformat()
        os.makedirs(os.path.dirname(JSON_CONFIG_PATH), exist_ok=True)
        with open(JSON_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(json_cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving to JSON_CONFIG_PATH: {e}")

    return get_agent_config()

def save_instagram_post(post_data: dict):
    init_instagram_tables()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO instagram_posts (
            id, content_type, product_id, title, caption, hashtags,
            image_url, local_image_path, status, ig_media_id, ig_permalink,
            error_message, scheduled_at, published_at, metadata_json, image_mode, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        post_data['id'],
        post_data.get('content_type', 'product_spotlight'),
        post_data.get('product_id'),
        post_data.get('title', ''),
        post_data.get('caption', ''),
        post_data.get('hashtags', ''),
        post_data.get('image_url', ''),
        post_data.get('local_image_path', ''),
        post_data.get('status', 'draft'),
        post_data.get('ig_media_id'),
        post_data.get('ig_permalink'),
        post_data.get('error_message'),
        post_data.get('scheduled_at'),
        post_data.get('published_at'),
        json.dumps(post_data.get('metadata', {}), ensure_ascii=False) if isinstance(post_data.get('metadata'), dict) else post_data.get('metadata_json', '{}'),
        post_data.get('image_mode', 'canvas'),
        post_data.get('created_at', datetime.now().isoformat())
    ))
    conn.commit()
    conn.close()
    sync_posts_to_json()

def get_last_post_image_mode() -> str:
    init_instagram_tables()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT image_mode FROM instagram_posts WHERE status IN ('published', 'draft', 'scheduled') ORDER BY created_at DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row and row[0]:
        return row[0]
    return 'canvas'

def update_instagram_post_status(post_id: str, status: str, ig_media_id: str = None, ig_permalink: str = None, error_message: str = None, published_at: str = None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE instagram_posts
        SET status = ?, ig_media_id = COALESCE(?, ig_media_id),
            ig_permalink = COALESCE(?, ig_permalink),
            error_message = ?, published_at = COALESCE(?, published_at)
        WHERE id = ?
    ''', (status, ig_media_id, ig_permalink, error_message, published_at, post_id))
    conn.commit()
    conn.close()
    sync_posts_to_json()

def get_instagram_posts(limit: int = 50, offset: int = 0, status: str = None):
    init_instagram_tables()
    conn = get_db()
    cursor = conn.cursor()
    if status:
        cursor.execute("SELECT * FROM instagram_posts WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?", (status, limit, offset))
    else:
        cursor.execute("SELECT * FROM instagram_posts ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
    rows = cursor.fetchall()
    conn.close()
    posts = []
    for r in rows:
        d = dict(r)
        if d.get('metadata_json'):
            try:
                meta = json.loads(d['metadata_json'])
                d['metadata'] = meta
                if 'visual_audit' in meta:
                    d['visual_audit'] = meta['visual_audit']
            except Exception:
                d['metadata'] = {}
        posts.append(d)
    return posts

def get_instagram_post_by_id(post_id: str):
    init_instagram_tables()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM instagram_posts WHERE id = ?", (post_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        if d.get('metadata_json'):
            try:
                meta = json.loads(d['metadata_json'])
                d['metadata'] = meta
                if 'visual_audit' in meta:
                    d['visual_audit'] = meta['visual_audit']
            except Exception:
                d['metadata'] = {}
        return d
    return None

def delete_instagram_post(post_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM instagram_posts WHERE id = ?", (post_id,))
    conn.commit()
    count = cursor.rowcount
    conn.close()
    if count > 0:
        sync_posts_to_json()
    return count > 0

def get_recent_posted_product_ids(limit: int = 50):
    init_instagram_tables()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT product_id FROM instagram_posts WHERE product_id IS NOT NULL AND status IN ('published', 'draft', 'scheduled') ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]

def get_recent_posted_titles(limit: int = 40) -> list:
    init_instagram_tables()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM instagram_posts WHERE status IN ('published', 'draft', 'scheduled') ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]

def get_recent_posted_content_types(limit: int = 10) -> list:
    init_instagram_tables()
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT content_type FROM instagram_posts WHERE status IN ('published', 'draft', 'scheduled') ORDER BY created_at DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [r[0] for r in rows if r[0]]
