import ctypes
import hashlib
import sqlite3
import shutil
import os
import glob
from ctypes import c_char_p, c_void_p, c_int, Structure, POINTER
from Crypto.Cipher import AES


class SecretSchemaAttribute(Structure):
    _fields_ = [('name', c_char_p), ('type', c_int)]


class SecretSchema(Structure):
    _fields_ = [('name', c_char_p), ('flags', c_int), ('attributes', SecretSchemaAttribute * 32)]


# Chromium-based browsers on Linux store their cookie-encryption password in the
# GNOME keyring under different "application" attributes. We try each one.
_BROWSER_SECRET_APPS = ('brave', 'chrome', 'chromium', 'chromium-browser', 'vivaldi', 'opera')


def _key_from_secret(app: str):
    try:
        libsecret = ctypes.CDLL('libsecret-1.so.0')
        attrs = (SecretSchemaAttribute * 32)()
        attrs[0] = SecretSchemaAttribute(b'application', 0)
        s = SecretSchema(b'chrome_libsecret_os_crypt_password_v2', 0, attrs)
        libsecret.secret_password_lookup_sync.argtypes = [POINTER(SecretSchema), c_void_p, POINTER(c_void_p), c_char_p, c_char_p, c_void_p]
        libsecret.secret_password_lookup_sync.restype = c_char_p
        pwd = libsecret.secret_password_lookup_sync(ctypes.byref(s), None, None, b'application', app.encode(), None)
        if pwd:
            return hashlib.pbkdf2_hmac('sha1', pwd, b'saltysalt', 1, 16)
    except Exception:
        pass
    return None


def get_chrome_safe_storage_key() -> bytes:
    """Backwards-compatible: returns the first available browser key (Chrome first)."""
    return get_browser_storage_key('chrome')


def get_browser_storage_key(app: str = None) -> bytes:
    """
    Retrieves a Chromium-browser cookie key from the keyring. Tries the requested
    app first, then every known browser, then the legacy hard-coded fallbacks.
    """
    order = []
    if app:
        order.append(app)
    order.extend(a for a in _BROWSER_SECRET_APPS if a not in order)
    for name in order:
        key = _key_from_secret(name)
        if key:
            return key
    # Legacy Chromium fallbacks (older profiles / password-less keyrings).
    for pwd in (b'peanuts', b''):
        if pwd:
            try:
                return hashlib.pbkdf2_hmac('sha1', pwd, b'saltysalt', 1, 16)
            except Exception:
                continue
    return None


def get_browser_storage_keys() -> list:
    """Returns all available candidate keys (deduplicated) for decryption attempts."""
    keys = []
    for name in _BROWSER_SECRET_APPS:
        k = _key_from_secret(name)
        if k and k not in keys:
            keys.append(k)
    for pwd in (b'peanuts', b''):
        try:
            k = hashlib.pbkdf2_hmac('sha1', pwd, b'saltysalt', 1, 16)
            if k not in keys:
                keys.append(k)
        except Exception:
            continue
    return keys


def _candidate_cookie_paths() -> list:
    """
    Every plausible Chromium-family Cookies DB on this machine, newest first.
    Supports an explicit override via INSTAGRAM_COOKIE_DB / CHROME_COOKIE_DB.
    """
    home = os.path.expanduser('~')
    candidates = []

    env_override = (os.environ.get('INSTAGRAM_COOKIE_DB')
                    or os.environ.get('CHROME_COOKIE_DB')
                    or os.environ.get('BROWSER_COOKIE_DB'))
    if env_override:
        candidates.append(env_override)

    browser_roots = [
        os.path.join(home, '.config', 'google-chrome'),
        os.path.join(home, '.config', 'chromium'),
        os.path.join(home, '.config', 'BraveSoftware', 'Brave-Browser'),
        os.path.join(home, '.config', 'microsoft-edge'),
        os.path.join(home, '.config', 'vivaldi'),
        os.path.join(home, '.config', 'opera'),
        # Local control-panel managed profiles (ServerGUI).
        '/home/eyup/ServerGUI/data/chrome-profile',
        '/home/eyup/ServerGUI/data/brave-profile',
        os.path.join(home, 'ServerGUI', 'data', 'chrome-profile'),
        os.path.join(home, 'ServerGUI', 'data', 'brave-profile'),
    ]
    # Any other browser-looking profile under ~/.config (e.g. custom *-isolated).
    for extra in glob.glob(os.path.join(home, '.config', '*isolated*')):
        browser_roots.append(extra)

    for root in browser_roots:
        if not os.path.isdir(root):
            continue
        candidates.append(os.path.join(root, 'Default', 'Cookies'))
        for n in range(1, 5):
            candidates.append(os.path.join(root, f'Profile {n}', 'Cookies'))

    # De-dupe, keep only existing files, newest first.
    seen, existing = set(), []
    for c in candidates:
        if c and c not in seen and os.path.exists(c):
            seen.add(c)
            existing.append(c)
    existing.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return existing


def _decrypt_value(encrypted: bytes, keys: list):
    """Decrypts one Chromium cookie value, trying every key and both header layouts."""
    if not encrypted or not isinstance(encrypted, (bytes, bytearray)):
        return None
    if not (encrypted.startswith(b'v10') or encrypted.startswith(b'v11')):
        # Plain-text cookie (rare).
        try:
            return encrypted.decode('utf-8', errors='ignore').strip()
        except Exception:
            return None
    payload = encrypted[3:]
    best = None
    for key in keys:
        try:
            dec = AES.new(key, AES.MODE_CBC, b' ' * 16).decrypt(payload)
            pad = dec[-1]
            if isinstance(pad, int) and 0 < pad <= 16:
                dec = dec[:-pad]
        except Exception:
            continue
        # Newer Chromium prefixes a 32-byte SHA256 integrity header; older does not.
        for cand in (dec[32:], dec):
            text = cand.decode('utf-8', errors='ignore')
            clean = ''.join(c for c in text if 32 <= ord(c) < 127).strip()
            if not clean:
                continue
            # Prefer a value that looks like a real cookie (printable + high ratio).
            ratio = len(clean) / max(1, len(text))
            if best is None or (ratio > best[0]) or (ratio == best[0] and len(clean) > len(best[1])):
                best = (ratio, clean)
        if best and best[0] > 0.95:
            break
    return best[1] if best else None


def _extract_from_db(cookie_db_path: str, keys: list):
    tmp_path = f"/tmp/pozitron_chrome_cookies_{os.getpid()}_{abs(hash(cookie_db_path)) % 100000}.db"
    try:
        shutil.copy2(cookie_db_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        rows = conn.execute(
            "SELECT name, encrypted_value FROM cookies "
            "WHERE host_key LIKE '%instagram%' AND name IN "
            "('sessionid','ds_user_id','csrftoken','mid','ig_did','datr','rur')"
        ).fetchall()
        conn.close()
    except Exception:
        return None
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    decrypted = {}
    for name, val in rows:
        v = _decrypt_value(val, keys)
        if v:
            decrypted[name] = v

    if decrypted.get('sessionid') and decrypted.get('ds_user_id'):
        return decrypted
    return None


def extract_chrome_instagram_cookies(cookie_db_path: str = None) -> dict:
    """
    Extracts and decrypts Instagram session cookies from any local Chromium-family
    browser profile (Chrome, Brave, Chromium, Edge, Vivaldi, ServerGUI profiles).

    Returns:
    {
        'success': bool, 'user_id': str, 'cookies': dict,
        'cookie_header': str, 'browser_profile': str, 'error': str or None
    }
    """
    if cookie_db_path:
        candidates = [cookie_db_path]
    else:
        candidates = _candidate_cookie_paths()

    if not candidates:
        return {'success': False, 'error': 'Hiçbir tarayıcı Cookies veritabanı bulunamadı (Chrome/Brave/Chromium).'}

    keys = get_browser_storage_keys()
    if not keys:
        return {'success': False, 'error': 'Tarayıcı çerez anahtarı (keyring) okunamadı.'}

    tried = []
    for db in candidates:
        tried.append(db)
        try:
            decrypted = _extract_from_db(db, keys)
        except Exception as e:
            decrypted = None
            tried[-1] = f"{db} ({e})"
        if decrypted:
            sessionid = decrypted.get('sessionid', '')
            return {
                'success': True,
                'user_id': decrypted.get('ds_user_id', ''),
                'sessionid_masked': f"{sessionid[:6]}...{sessionid[-4:]}",
                'sessionid': sessionid,
                'csrftoken': decrypted.get('csrftoken', ''),
                'cookies': decrypted,
                'cookie_header': '; '.join(f'{k}={v}' for k, v in decrypted.items()),
                'browser_profile': db,
            }

    return {
        'success': False,
        'error': 'Instagram oturum çerezleri (sessionid, ds_user_id) hiçbir tarayıcı profilinde bulunamadı. '
                 'İlgili tarayıcıda Instagram hesabına giriş yapıldığından emin olun.',
        'tried_profiles': tried,
    }
