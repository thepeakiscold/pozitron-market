import ctypes
import hashlib
import sqlite3
import shutil
import os
from ctypes import c_char_p, c_void_p, c_int, Structure, POINTER
from Crypto.Cipher import AES
import requests

class SecretSchemaAttribute(Structure):
    _fields_ = [('name', c_char_p), ('type', c_int)]

class SecretSchema(Structure):
    _fields_ = [('name', c_char_p), ('flags', c_int), ('attributes', SecretSchemaAttribute * 32)]

def get_chrome_safe_storage_key() -> bytes:
    """Retrieves the Chrome Safe Storage master key from GNOME Keyring / libsecret."""
    try:
        libsecret = ctypes.CDLL('libsecret-1.so.0')
        attrs = (SecretSchemaAttribute * 32)()
        attrs[0] = SecretSchemaAttribute(b'application', 0)
        s = SecretSchema(b'chrome_libsecret_os_crypt_password_v2', 0, attrs)
        libsecret.secret_password_lookup_sync.argtypes = [POINTER(SecretSchema), c_void_p, POINTER(c_void_p), c_char_p, c_char_p, c_void_p]
        libsecret.secret_password_lookup_sync.restype = c_char_p

        pwd = libsecret.secret_password_lookup_sync(ctypes.byref(s), None, None, b'application', b'chrome', None)
        if not pwd:
            return None
        return hashlib.pbkdf2_hmac('sha1', pwd, b'saltysalt', 1, 16)
    except Exception:
        return None

def extract_chrome_reddit_session(cookie_db_path: str = None) -> dict:
    """
    Extracts decrypted Reddit session tokens and cookies.
    Supports:
    1. Online / CI / Cloud: REDDIT_COOKIES_JSON or REDDIT_COOKIES_FILE environment variable
    2. Local Linux Desktop: Local Chrome Cookies database via GNOME Keyring
    """
    import json

    # 1. Check environment variable for online execution (GitHub Actions, Docker, Cloud)
    env_cookies_json = os.environ.get('REDDIT_COOKIES_JSON', '').strip()
    env_cookies_file = os.environ.get('REDDIT_COOKIES_FILE', '').strip()

    raw_cookies_data = None
    if env_cookies_json:
        try:
            raw_cookies_data = json.loads(env_cookies_json)
        except Exception:
            pass
    elif env_cookies_file and os.path.exists(env_cookies_file):
        try:
            with open(env_cookies_file, 'r', encoding='utf-8') as f:
                raw_cookies_data = json.load(f)
        except Exception:
            pass

    if raw_cookies_data:
        cookies_dict = {}
        if isinstance(raw_cookies_data, list):
            for c in raw_cookies_data:
                if isinstance(c, dict) and 'name' in c and 'value' in c:
                    cookies_dict[c['name']] = c['value']
        elif isinstance(raw_cookies_data, dict):
            cookies_dict = raw_cookies_data

        token_v2 = cookies_dict.get('token_v2', '')
        csrf_token = cookies_dict.get('csrf_token', '')

        # Verify session with Reddit
        username = os.environ.get('REDDIT_USERNAME', 'Aggravating_End_1105')
        if token_v2:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Authorization': f'Bearer {token_v2}'
                }
                r = requests.get('https://oauth.reddit.com/api/v1/me', headers=headers, timeout=8)
                if r.status_code == 200:
                    username = r.json().get('name', username)
            except Exception:
                pass

            return {
                'success': True,
                'username': username,
                'token_v2': token_v2,
                'csrf_token': csrf_token,
                'cookies': cookies_dict
            }

    # 2. Local Linux Chrome Profile fallback
    if not cookie_db_path:
        home = os.path.expanduser('~')
        cookie_db_path = os.path.join(home, '.config', 'google-chrome', 'Default', 'Cookies')

    if not os.path.exists(cookie_db_path):
        return {'success': False, 'error': f'Chrome Cookies dosyası veya REDDIT_COOKIES_JSON ortam değişkeni bulunamadı.'}

    key = get_chrome_safe_storage_key()
    if not key:
        return {'success': False, 'error': 'libsecret üzerinden Chrome anahtarı okunamadı.'}

    tmp_path = f"/tmp/pozitron_chrome_reddit_{os.getpid()}.db"
    try:
        shutil.copy2(cookie_db_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        c = conn.cursor()
        c.execute("SELECT name, encrypted_value FROM cookies WHERE host_key LIKE '%reddit.com%'")
        rows = c.fetchall()
        conn.close()
    except Exception as e:
        return {'success': False, 'error': f'Cookies okuma hatası: {str(e)}'}
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    if not rows:
        return {'success': False, 'error': 'Chrome profilinde Reddit çerezi bulunamadı.'}

    cookies = {}
    for name, val in rows:
        if val.startswith(b'v11') or val.startswith(b'v10'):
            try:
                c_cbc = AES.new(key, AES.MODE_CBC, b' ' * 16)
                dec = c_cbc.decrypt(val[3:])
                plain = dec[32:] if val.startswith(b'v11') else dec
                pad = plain[-1]
                if isinstance(pad, int) and 0 < pad <= 16:
                    plain = plain[:-pad]
                cookies[name] = plain.decode('utf-8', errors='ignore')
            except Exception:
                pass

    token_v2 = cookies.get('token_v2', '')
    csrf_token = cookies.get('csrf_token', '')

    if not token_v2:
        return {'success': False, 'error': 'Reddit token_v2 oturum anahtarı bulunamadı.'}

    # Verify session with Reddit API
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Authorization': f'Bearer {token_v2}'
    }

    try:
        r = requests.get('https://oauth.reddit.com/api/v1/me', headers=headers, timeout=8)
        if r.status_code == 200:
            username = r.json().get('name', 'user')
            return {
                'success': True,
                'username': username,
                'token_v2': token_v2,
                'csrf_token': csrf_token,
                'cookies': cookies
            }
        else:
            return {'success': False, 'error': f'Reddit oturum doğrulaması başarısız (HTTP {r.status_code})'}
    except Exception as e:
        return {'success': False, 'error': f'Doğrulama bağlantı hatası: {str(e)}'}
