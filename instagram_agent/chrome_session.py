import ctypes
import hashlib
import sqlite3
import shutil
import os
from ctypes import c_char_p, c_void_p, c_int, Structure, POINTER
from Crypto.Cipher import AES

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

def extract_chrome_instagram_cookies(cookie_db_path: str = None) -> dict:
    """
    Extracts decrypted Instagram session cookies from the local Chrome profile.
    Returns:
    {
        'success': bool,
        'user_id': str,
        'cookies': dict,
        'cookie_header': str,
        'error': str or None
    }
    """
    if not cookie_db_path:
        home = os.path.expanduser('~')
        cookie_db_path = os.path.join(home, '.config', 'google-chrome', 'Default', 'Cookies')

    if not os.path.exists(cookie_db_path):
        return {'success': False, 'error': f'Chrome Cookies dosyası bulunamadı: {cookie_db_path}'}

    key = get_chrome_safe_storage_key()
    if not key:
        return {'success': False, 'error': 'libsecret üzerinden Chrome anahtarı okunamadı.'}

    tmp_path = f"/tmp/pozitron_chrome_cookies_{os.getpid()}.db"
    try:
        shutil.copy2(cookie_db_path, tmp_path)
        conn = sqlite3.connect(tmp_path)
        c = conn.cursor()
        c.execute("SELECT name, encrypted_value FROM cookies WHERE host_key LIKE '%instagram%'")
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
        return {'success': False, 'error': 'Chrome profilinde Instagram çerezi bulunamadı.'}

    decrypted = {}
    for name, val in rows:
        if val.startswith(b'v11') or val.startswith(b'v10'):
            try:
                c_cbc = AES.new(key, AES.MODE_CBC, b' ' * 16)
                dec = c_cbc.decrypt(val[3:])
                pad = dec[-1]
                if isinstance(pad, int) and pad <= 16:
                    dec = dec[:-pad]
                # In v11, first 32 bytes are the integrity header
                cookie_val = dec[32:].decode('utf-8', errors='ignore')
                decrypted[name] = cookie_val
            except Exception:
                pass

    user_id = decrypted.get('ds_user_id', '')
    sessionid = decrypted.get('sessionid', '')

    if not sessionid or not user_id:
        return {'success': False, 'error': 'Instagram oturum çerezleri (sessionid, ds_user_id) bulunamadı veya oturum kapalı.'}

    cookie_header = '; '.join([f'{k}={v}' for k, v in decrypted.items()])

    return {
        'success': True,
        'user_id': user_id,
        'sessionid_masked': f"{sessionid[:6]}...{sessionid[-4:]}",
        'sessionid': sessionid,
        'csrftoken': decrypted.get('csrftoken', ''),
        'cookies': decrypted,
        'cookie_header': cookie_header
    }
