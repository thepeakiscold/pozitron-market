import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'pozitron.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_reddit_tables():
    conn = get_db()
    cursor = conn.cursor()

    # Reddit Agent Configuration Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reddit_agent_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            client_id TEXT,
            client_secret TEXT,
            username TEXT,
            password TEXT,
            user_agent TEXT DEFAULT 'python:pozitron.drone.assistant:v1.0 (by /u/PozitronMarket)',
            gemini_api_key TEXT,
            subreddits TEXT DEFAULT 'Turkey, teknoloji, bilim, AskTurkey, fpvturkey, droneturkey',
            keywords TEXT DEFAULT 'drone, fpv, quadcopter, betafpv, dji, kumanda, lehim, motor, esc, vtx, gözlük, batarya, lipo, teknofest, betaflight, inav, elrs, crossfire, shg, pervane, frame, uçuş, alıcı, verici',
            is_autonomous_enabled INTEGER DEFAULT 0,
            dry_run_mode INTEGER DEFAULT 1,
            scan_interval_minutes INTEGER DEFAULT 30,
            max_replies_per_day INTEGER DEFAULT 10,
            auto_post_min_confidence INTEGER DEFAULT 85,
            custom_signature TEXT DEFAULT 'İyi uçuşlar ve kırımsız günler! [POZİTRON MARKET]',
            last_scan_at TEXT,
            next_scan_at TEXT,
            updated_at TEXT
        )
    ''')

    # Seed default config if empty
    cursor.execute("SELECT count(*) FROM reddit_agent_config")
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT INTO reddit_agent_config (
                id, client_id, client_secret, username, password,
                user_agent, gemini_api_key, subreddits, keywords,
                is_autonomous_enabled, dry_run_mode, scan_interval_minutes,
                max_replies_per_day, auto_post_min_confidence, custom_signature,
                last_scan_at, next_scan_at, updated_at
            ) VALUES (
                1, '', '', '', '',
                'python:pozitron.drone.assistant:v1.0 (by /u/PozitronMarket)',
                '',
                'Turkey, teknoloji, bilim, AskTurkey, fpvturkey, droneturkey',
                'drone, fpv, quadcopter, betafpv, dji, kumanda, lehim, motor, esc, vtx, gözlük, batarya, lipo, teknofest, betaflight, inav, elrs, crossfire, shg, pervane, frame, uçuş, alıcı, verici',
                0, 1, 30, 10, 85, 'İyi uçuşlar ve kırımsız günler! [POZİTRON MARKET]',
                NULL, NULL, ?
            )
        ''', (datetime.now().isoformat(),))

    # Reddit Questions & Interactions History Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reddit_interactions (
            id TEXT PRIMARY KEY,
            reddit_id TEXT UNIQUE NOT NULL,
            reddit_type TEXT DEFAULT 'submission', -- 'submission' or 'comment'
            title TEXT,
            body TEXT,
            author TEXT,
            subreddit TEXT NOT NULL,
            url TEXT,
            permalink TEXT,
            question_summary TEXT,
            gemini_reply TEXT NOT NULL,
            status TEXT DEFAULT 'draft', -- 'draft', 'published', 'rejected', 'failed'
            confidence_score INTEGER DEFAULT 80,
            upvotes INTEGER DEFAULT 0,
            error_message TEXT,
            published_at TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

def get_agent_config() -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reddit_agent_config WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {}

def update_agent_config(new_config: dict) -> dict:
    conn = get_db()
    cursor = conn.cursor()

    allowed_fields = [
        'client_id', 'client_secret', 'username', 'password', 'user_agent',
        'gemini_api_key', 'subreddits', 'keywords', 'is_autonomous_enabled',
        'dry_run_mode', 'scan_interval_minutes', 'max_replies_per_day',
        'auto_post_min_confidence', 'custom_signature', 'last_scan_at', 'next_scan_at'
    ]

    updates = []
    values = []
    for field in allowed_fields:
        if field in new_config:
            updates.append(f"{field} = ?")
            values.append(new_config[field])

    if updates:
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
        values.append(1)

        query = f"UPDATE reddit_agent_config SET {', '.join(updates)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()

    conn.close()
    return get_agent_config()

def save_interaction(data: dict) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO reddit_interactions (
                id, reddit_id, reddit_type, title, body, author,
                subreddit, url, permalink, question_summary, gemini_reply,
                status, confidence_score, upvotes, error_message, published_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data['id'],
            data['reddit_id'],
            data.get('reddit_type', 'submission'),
            data.get('title', ''),
            data.get('body', ''),
            data.get('author', ''),
            data.get('subreddit', ''),
            data.get('url', ''),
            data.get('permalink', ''),
            data.get('question_summary', ''),
            data.get('gemini_reply', ''),
            data.get('status', 'draft'),
            data.get('confidence_score', 80),
            data.get('upvotes', 0),
            data.get('error_message', None),
            data.get('published_at', None),
            data.get('created_at', datetime.now().isoformat())
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

    try:
        record_history_id(data.get('reddit_id'))
    except Exception:
        pass

HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "reddit_history.json")

def load_history_ids() -> set:
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def record_history_id(reddit_id: str):
    if not reddit_id:
        return
    ids = load_history_ids()
    ids.add(reddit_id)
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(sorted(list(ids)), f, indent=2)
    except Exception:
        pass

def get_interaction_by_id(interaction_id: str) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reddit_interactions WHERE id = ?", (interaction_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_interaction_by_reddit_id(reddit_id: str) -> dict:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reddit_interactions WHERE reddit_id = ?", (reddit_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    if reddit_id in load_history_ids():
        return {"reddit_id": reddit_id, "status": "processed"}
    return None

def update_interaction_status(interaction_id: str, status: str, error_message: str = None, published_at: str = None) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    updates = ["status = ?"]
    params = [status]

    if error_message is not None:
        updates.append("error_message = ?")
        params.append(error_message)

    if published_at is not None:
        updates.append("published_at = ?")
        params.append(published_at)

    params.append(interaction_id)
    query = f"UPDATE reddit_interactions SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, params)
    conn.commit()
    rows = cursor.rowcount
    conn.close()
    return rows > 0

def update_interaction_reply(interaction_id: str, reply_text: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE reddit_interactions SET gemini_reply = ? WHERE id = ?", (reply_text, interaction_id))
    conn.commit()
    rows = cursor.rowcount
    conn.close()
    return rows > 0

def delete_interaction(interaction_id: str) -> bool:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reddit_interactions WHERE id = ?", (interaction_id,))
    conn.commit()
    rows = cursor.rowcount
    conn.close()
    return rows > 0

def get_interactions(limit: int = 50, offset: int = 0, status: str = None, subreddit: str = None) -> list:
    conn = get_db()
    cursor = conn.cursor()
    query = "SELECT * FROM reddit_interactions WHERE 1=1"
    params = []

    if status and status != 'all':
        query += " AND status = ?"
        params.append(status)
    elif not status:
        # Default: exclude rejected items so only genuine published comments/drafts are loaded
        query += " AND status != 'rejected'"

    if subreddit and subreddit != 'all':
        query += " AND subreddit = ?"
        params.append(subreddit)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_daily_replies_count() -> int:
    conn = get_db()
    cursor = conn.cursor()
    today_start = datetime.now().strftime("%Y-%m-%d") + "T00:00:00"
    cursor.execute("SELECT count(*) FROM reddit_interactions WHERE status = 'published' AND published_at >= ?", (today_start,))
    count = cursor.fetchone()[0]
    conn.close()
    return count
