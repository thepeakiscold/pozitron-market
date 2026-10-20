"""
Coupon / promotion domain logic for Pozitron Market.

Rules implemented here:
  * A coupon has an optional start/end window. When the end time passes it is
    automatically deactivated — even if nobody touches the system.
  * Fixed-amount coupons are expressed in TRY (the store's primary currency);
    the USD discount is derived with the live USD/TRY rate.
  * A coupon can be used only ONCE per account. This is enforced at the database
    level by the UNIQUE(coupon_code, user_key) constraint on coupon_redemptions,
    so even concurrent checkouts cannot double-spend it.
  * Every lifecycle event (created / validated / redeemed / expired / updated /
    deleted) is written to coupon_logs, giving a full audit trail.
"""
import os
import re
import random
import string
import sqlite3
from datetime import datetime, timedelta

from database import get_db

# Fixed discounts are TRY-based; convert to USD with this rate when needed.
def _exchange_rate() -> float:
    try:
        return float(os.environ.get("USD_TRY_RATE", "35.5"))
    except Exception:
        return 35.5

VALID_TYPES = ("percent", "fixed")


def _now() -> datetime:
    return datetime.now()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def log_event(cursor, code: str, action: str, detail: str = "", actor: str = "system"):
    cursor.execute(
        "INSERT INTO coupon_logs (coupon_code, action, detail, actor, created_at) VALUES (?, ?, ?, ?, ?)",
        (code, action, detail or "", actor or "system", _iso(_now())),
    )


def normalize_email(email: str) -> str:
    """
    Canonically normalizes email addresses:
    - strips leading/trailing whitespace
    - converts to lowercase
    - for Gmail/Googlemail: removes dots from local part and strips +alias tags
    """
    if not email or not isinstance(email, str):
        return ""
    clean = email.strip().lower()
    if "@" not in clean:
        return clean
    parts = clean.split("@", 1)
    local_part, domain = parts[0], parts[1]
    if domain in ("gmail.com", "googlemail.com"):
        local_part = local_part.split("+")[0].replace(".", "")
        domain = "gmail.com"
    return f"{local_part}@{domain}"


def make_user_key(user_id: str = None, email: str = None) -> str:
    """Stable identity for the once-per-account rule (account id preferred, else normalized email)."""
    if user_id and str(user_id).strip():
        return f"uid:{str(user_id).strip()}"
    norm = normalize_email(email)
    if norm:
        return f"email:{norm}"
    return ""


# ---------------------------------------------------------------------------
# Expiry
# ---------------------------------------------------------------------------
def expire_coupons(conn=None, commit: bool = True) -> int:
    """
    Deactivates every coupon whose end time has passed. Idempotent and cheap, so
    it can be called on every read and by the background scheduler.
    Returns the number of coupons expired in this call.
    """
    own = conn is None
    if own:
        conn = get_db()
    try:
        cur = conn.cursor()
        now = _iso(_now())
        rows = cur.execute(
            "SELECT code FROM coupons WHERE is_active = 1 AND expires_at IS NOT NULL "
            "AND expires_at != '' AND expires_at <= ?",
            (now,),
        ).fetchall()
        for r in rows:
            cur.execute("UPDATE coupons SET is_active = 0 WHERE code = ?", (r["code"],))
            log_event(cur, r["code"], "expired", f"ended at {now}")
        if own or commit:
            conn.commit()
        return len(rows)
    finally:
        if own:
            conn.close()


def is_expired(coupon: dict, at: datetime = None) -> bool:
    at = at or _now()
    exp = (coupon or {}).get("expires_at")
    if not exp:
        return False
    try:
        return at >= datetime.fromisoformat(exp)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------
def generate_code(prefix: str = "FIRSAT", length: int = 3) -> str:
    suffix = "".join(random.choice(string.digits) for _ in range(length))
    return f"{prefix}{suffix}"


def create_coupon(code, discount_type, discount_value, min_order_usd=0, min_order_try=0,
                  description_tr="", description_en="", starts_at=None, expires_at=None,
                  max_uses=None, per_user_limit=1, source="manual", campaign_id=None,
                  actor="admin", conn=None, commit=True):
    """Creates a coupon. Raises ValueError on invalid input or duplicate code."""
    own = conn is None
    if own:
        conn = get_db()
    code = (code or "").strip().upper()
    if not re.match(r"^[A-Z0-9_-]{3,32}$", code):
        if own:
            conn.close()
        raise ValueError("Kupon kodu 3-32 karakter, sadece A-Z, 0-9, - ve _ olabilir.")
    if discount_type not in VALID_TYPES:
        if own:
            conn.close()
        raise ValueError("İndirim tipi 'percent' veya 'fixed' olmalı.")
    try:
        discount_value = float(discount_value)
    except Exception:
        if own:
            conn.close()
        raise ValueError("İndirim değeri sayısal olmalı.")
    if discount_value <= 0:
        if own:
            conn.close()
        raise ValueError("İndirim değeri 0'dan büyük olmalı.")
    if discount_type == "percent" and discount_value > 100:
        if own:
            conn.close()
        raise ValueError("Yüzde indirim 100'den büyük olamaz.")
    if expires_at and starts_at and starts_at > expires_at:
        if own:
            conn.close()
        raise ValueError("Bitiş tarihi başlangıçtan önce olamaz.")

    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO coupons
               (code, discount_type, discount_value, min_order_usd, min_order_try,
                description_en, description_tr, is_active, starts_at, expires_at,
                max_uses, per_user_limit, used_count, created_at, source, campaign_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, 0, ?, ?, ?)""",
            (code, discount_type, discount_value, float(min_order_usd or 0), float(min_order_try or 0),
             description_en or "", description_tr or "", starts_at, expires_at,
             int(max_uses) if max_uses not in (None, "", 0) else None,
             int(per_user_limit if per_user_limit not in (None, "") else 1),
             _iso(_now()), source or "manual", campaign_id),
        )
    except sqlite3.IntegrityError:
        if own:
            conn.close()
        raise ValueError(f"'{code}' kodu zaten mevcut.")
    log_event(cur, code, "created",
              f"{discount_type} {discount_value}"
              + (f" | bitiş {expires_at}" if expires_at else ""), actor)
    if own or commit:
        conn.commit()
    if own:
        conn.close()
    return code


def update_coupon(code, actor="admin", conn=None, **fields):
    """Updates allowed coupon fields. Pass expires_at=None to clear it."""
    own = conn is None
    if own:
        conn = get_db()
    code = (code or "").strip().upper()
    allowed = {"discount_type", "discount_value", "min_order_usd", "min_order_try",
               "description_tr", "description_en", "starts_at", "expires_at",
               "max_uses", "per_user_limit", "is_active"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        if own:
            conn.close()
        return False

    # Validation
    if "discount_type" in updates and updates["discount_type"] not in VALID_TYPES:
        if own:
            conn.close()
        raise ValueError("İndirim tipi 'percent' veya 'fixed' olmalı.")
    if "discount_value" in updates:
        try:
            val = float(updates["discount_value"])
            updates["discount_value"] = val
        except Exception:
            if own:
                conn.close()
            raise ValueError("İndirim değeri sayısal olmalı.")
        if val <= 0:
            if own:
                conn.close()
            raise ValueError("İndirim değeri 0'dan büyük olmalı.")
        d_type = updates.get("discount_type")
        if not d_type:
            # fetch existing
            row_dt = conn.execute("SELECT discount_type FROM coupons WHERE code = ?", (code,)).fetchone()
            d_type = row_dt["discount_type"] if row_dt else None
        if d_type == "percent" and val > 100:
            if own:
                conn.close()
            raise ValueError("Yüzde indirim 100'den büyük olamaz.")

    for num_field in ("min_order_usd", "min_order_try"):
        if num_field in updates:
            try:
                nv = float(updates[num_field])
                if nv < 0:
                    if own:
                        conn.close()
                    raise ValueError(f"{num_field} negatif olamaz.")
                updates[num_field] = nv
            except ValueError:
                raise
            except Exception:
                if own:
                    conn.close()
                raise ValueError(f"{num_field} sayısal olmalı.")

    for int_field in ("max_uses", "per_user_limit"):
        if int_field in updates and updates[int_field] is not None:
            try:
                iv = int(updates[int_field])
                if iv <= 0:
                    if own:
                        conn.close()
                    raise ValueError(f"{int_field} 0 veya daha küçük olamaz.")
                updates[int_field] = iv
            except ValueError:
                raise
            except Exception:
                if own:
                    conn.close()
                raise ValueError(f"{int_field} tam sayı olmalı.")

    cur = conn.cursor()
    if not cur.execute("SELECT 1 FROM coupons WHERE code = ?", (code,)).fetchone():
        if own:
            conn.close()
        raise ValueError("Kupon bulunamadı.")
    sets = ", ".join(f"{k} = ?" for k in updates)
    cur.execute(f"UPDATE coupons SET {sets} WHERE code = ?", list(updates.values()) + [code])
    log_event(cur, code, "updated", ", ".join(f"{k}={v}" for k, v in updates.items()), actor)
    conn.commit()
    if own:
        conn.close()
    return True


def set_coupon_active(code, active: bool, actor="admin", conn=None):
    return update_coupon(code, actor=actor, conn=conn, is_active=1 if active else 0)


def delete_coupon(code, actor="admin", conn=None):
    own = conn is None
    if own:
        conn = get_db()
    code = (code or "").strip().upper()
    cur = conn.cursor()
    cur.execute("DELETE FROM coupons WHERE code = ?", (code,))
    log_event(cur, code, "deleted", "", actor)
    if own:
        conn.commit()
        conn.close()
    return True


def get_coupon(code, conn=None):
    own = conn is None
    if own:
        conn = get_db()
    row = conn.execute("SELECT * FROM coupons WHERE code = ?", ((code or "").strip().upper(),)).fetchone()
    if own:
        conn.close()
    return dict(row) if row else None


def list_coupons(conn=None, include_inactive=True, source=None):
    own = conn is None
    if own:
        conn = get_db()
        expire_coupons(conn)
    q = "SELECT * FROM coupons"
    conds, args = [], []
    if not include_inactive:
        conds.append("is_active = 1")
    if source:
        conds.append("source = ?")
        args.append(source)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY (created_at IS NULL), created_at DESC, code ASC"
    rows = conn.execute(q, args).fetchall()
    if own:
        conn.close()
    return [dict(r) for r in rows]


def get_redemptions(code=None, limit=200, conn=None):
    own = conn is None
    if own:
        conn = get_db()
    if code:
        rows = conn.execute(
            "SELECT * FROM coupon_redemptions WHERE coupon_code = ? ORDER BY redeemed_at DESC LIMIT ?",
            ((code or "").strip().upper(), limit)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM coupon_redemptions ORDER BY redeemed_at DESC LIMIT ?", (limit,)).fetchall()
    if own:
        conn.close()
    return [dict(r) for r in rows]


def get_logs(code=None, limit=300, conn=None):
    own = conn is None
    if own:
        conn = get_db()
    if code:
        rows = conn.execute(
            "SELECT * FROM coupon_logs WHERE coupon_code = ? ORDER BY created_at DESC LIMIT ?",
            ((code or "").strip().upper(), limit)).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM coupon_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    if own:
        conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Validation / redemption
# ---------------------------------------------------------------------------
def compute_discount(coupon: dict, subtotal_usd: float, subtotal_try: float):
    rate = _exchange_rate()
    subtotal_usd = max(0.0, float(subtotal_usd or 0))
    subtotal_try = max(0.0, float(subtotal_try or 0))

    if coupon["discount_type"] == "percent":
        val = min(100.0, max(0.0, float(coupon.get("discount_value") or 0)))
        d_usd = round(min(subtotal_usd, subtotal_usd * (val / 100.0)), 2)
        d_try = round(min(subtotal_try, subtotal_try * (val / 100.0)), 2)
    else:
        # fixed amount is in TRY
        val = max(0.0, float(coupon.get("discount_value") or 0))
        d_try = round(min(subtotal_try, val), 2)
        d_usd = round(min(subtotal_usd, val / rate), 2)
    return d_usd, d_try


def _fail(error_tr, error_en=None, code="invalid"):
    return {"valid": False, "error": error_tr, "error_en": error_en or error_tr, "reason": code}


def validate_coupon(code, subtotal_usd=0.0, subtotal_try=0.0,
                    user_id=None, email=None, conn=None, commit=True, count_usage=True):
    """
    Full validation. Returns a dict:
      {"valid": bool, "reason": ..., "error": ..., plus coupon/discount fields}
    """
    own = conn is None
    if own:
        conn = get_db()
    try:
        expire_coupons(conn, commit=False)
        code = (code or "").strip().upper()
        row = conn.execute("SELECT * FROM coupons WHERE code = ?", (code,)).fetchone()
        if not row:
            return _fail("Bu kupon kodu geçerli değil.", "Invalid coupon code.", "invalid")
        c = dict(row)

        if not c.get("is_active"):
            return _fail("Bu kuponun süresi doldu veya devre dışı.", "Coupon expired or inactive.", "inactive")

        now = _now()
        if c.get("starts_at"):
            try:
                if now < datetime.fromisoformat(c["starts_at"]):
                    return _fail("Bu kupon henüz başlamadı.", "Coupon not started yet.", "not_started")
            except Exception:
                pass
        if c.get("expires_at"):
            try:
                if now >= datetime.fromisoformat(c["expires_at"]):
                    return _fail("Bu kuponun süresi doldu.", "Coupon expired.", "expired")
            except Exception:
                pass

        if c.get("max_uses") is not None and int(c.get("used_count") or 0) >= int(c["max_uses"]):
            return _fail("Bu kupon maksimum kullanım sayısına ulaştı.", "Coupon usage limit reached.", "usage_limit")

        # A minimum is only enforced for currencies where a threshold is set (>0).
        # We also convert equivalent currencies if one is omitted to prevent accidental blocks.
        rate = _exchange_rate()
        effective_usd = subtotal_usd if subtotal_usd > 0 else round(subtotal_try / rate, 2)
        effective_try = subtotal_try if subtotal_try > 0 else round(subtotal_usd * rate, 2)

        min_usd = float(c.get("min_order_usd") or 0)
        min_try = float(c.get("min_order_try") or 0)
        reqs = []
        if min_try > 0:
            reqs.append(effective_try >= min_try)
        if min_usd > 0:
            reqs.append(effective_usd >= min_usd)
        if reqs and not any(reqs):
            min_txt = []
            if min_try > 0:
                min_txt.append(f"{int(min_try)}₺")
            if min_usd > 0:
                min_txt.append(f"${int(min_usd)}")
            joined = " / ".join(min_txt)
            return _fail(
                f"Bu kupon için minimum sepet tutarı {joined}.",
                f"Minimum order amount is {joined}.", "min_order")

        per_user = int(c.get("per_user_limit") or 1)
        user_key = make_user_key(user_id, email)
        norm_email = normalize_email(email)
        str_uid = str(user_id).strip() if user_id and str(user_id).strip() else None

        # Cross-identity check: blocks users attempting to double-spend by toggling
        # between logged-in user_id and guest checkout with the same email.
        if count_usage and per_user > 0 and (user_key or str_uid or norm_email):
            raw_email = (email or "").strip().lower() if email else None
            q = """
                SELECT COUNT(*) AS n FROM coupon_redemptions
                WHERE coupon_code = ? AND (
                    user_key = ?
                    OR (? IS NOT NULL AND user_id = ?)
                    OR (? IS NOT NULL AND (customer_email = ? OR customer_email = ?))
                )
            """
            used = conn.execute(q, (code, user_key, str_uid, str_uid, norm_email, norm_email, raw_email)).fetchone()["n"]
            if used >= per_user:
                return _fail("Bu kuponu daha önce kullandınız. Her hesap yalnızca belirlenen limit kadar yararlanabilir.",
                             "You have already reached the usage limit for this coupon.", "already_used")

        d_usd, d_try = compute_discount(c, subtotal_usd, subtotal_try)
        if commit:
            conn.commit()
        return {
            "valid": True,
            "code": code,
            "discount_type": c["discount_type"],
            "discount_value": c["discount_value"],
            "discount_usd": d_usd,
            "discount_try": d_try,
            "description_tr": c.get("description_tr"),
            "description_en": c.get("description_en"),
            "expires_at": c.get("expires_at"),
            "min_order_usd": c.get("min_order_usd"),
            "min_order_try": c.get("min_order_try"),
            "source": c.get("source"),
        }
    finally:
        if own:
            conn.close()


def redeem_coupon(conn, code, user_id=None, email=None, order_id=None, order_number=None,
                  discount_usd=0.0, discount_try=0.0):
    """
    Atomically records a redemption. MUST be called inside the order transaction
    (same conn). Returns (ok, reason). Supports multi-use per_user_limit and protects
    against cross-identity reuse.
    """
    code = (code or "").strip().upper()
    user_key = make_user_key(user_id, email)
    norm_email = normalize_email(email)
    str_uid = str(user_id).strip() if user_id and str(user_id).strip() else None

    if not user_key:
        return False, "login_required"
    cur = conn.cursor()
    row = cur.execute("SELECT * FROM coupons WHERE code = ?", (code,)).fetchone()
    if not row:
        return False, "invalid"
    c = dict(row)
    if not c.get("is_active"):
        return False, "inactive"
    if is_expired(c):
        return False, "expired"
    if c.get("max_uses") is not None and int(c.get("used_count") or 0) >= int(c["max_uses"]):
        return False, "usage_limit"

    # Enforce per_user_limit across user_key, user_id, and normalized email
    per_user = int(c.get("per_user_limit") or 1)
    if per_user > 0:
        raw_email = (email or "").strip().lower() if email else None
        q = """
            SELECT COUNT(*) AS n FROM coupon_redemptions
            WHERE coupon_code = ? AND (
                user_key = ?
                OR (? IS NOT NULL AND user_id = ?)
                OR (? IS NOT NULL AND (customer_email = ? OR customer_email = ?))
            )
        """
        used = cur.execute(q, (code, user_key, str_uid, str_uid, norm_email, norm_email, raw_email)).fetchone()["n"]
        if used >= per_user:
            return False, "already_used"

    # Reserve a global usage slot atomically. The conditional UPDATE guarantees the
    # max_uses ceiling cannot be exceeded even by concurrent checkouts.
    cur.execute(
        "UPDATE coupons SET used_count = used_count + 1 "
        "WHERE code = ? AND (max_uses IS NULL OR used_count < max_uses)",
        (code,),
    )
    if cur.rowcount == 0:
        return False, "usage_limit"
    try:
        cur.execute(
            """INSERT INTO coupon_redemptions
               (coupon_code, user_key, user_id, customer_email, order_id, order_number,
                discount_try, discount_usd, redeemed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (code, user_key, str_uid, norm_email or None, order_id, order_number,
             float(discount_try or 0), float(discount_usd or 0), _iso(_now())),
        )
    except sqlite3.IntegrityError:
        # Duplicate redemption for this specific order or conflict
        cur.execute("UPDATE coupons SET used_count = MAX(0, used_count - 1) WHERE code = ?", (code,))
        return False, "already_used"
    log_event(cur, code, "redeemed",
              f"order={order_number} user={user_key} discount={discount_try}₺", user_key)
    return True, None


# ---------------------------------------------------------------------------
# Weekly deal generation (used by the Instagram PR agent)
# ---------------------------------------------------------------------------
def build_weekly_deal(template: dict = None):
    """
    Produces the parameters of this week's one-day deal. `template` may override
    any field (e.g. {"code_prefix": "HAFTA", "discount_type": "percent", ...}).
    """
    t = dict(template or {})
    discount_type = t.get("discount_type", "percent")
    if discount_type == "percent":
        discount_value = t.get("discount_value", random.choice([10, 12, 15, 20]))
        min_order_try = t.get("min_order_try", random.choice([1500, 2000, 2500, 3000]))
        description_tr = t.get("description_tr") or \
            f"{int(min_order_try)}₺ ve üzeri alışverişlerde %{int(discount_value)} indirim"
    else:
        discount_value = t.get("discount_value", random.choice([250, 300, 400, 500]))
        min_order_try = t.get("min_order_try", max(1000, int(discount_value * 8)))
        description_tr = t.get("description_tr") or \
            f"{int(min_order_try)}₺ ve üzeri alışverişlerde {int(discount_value)}₺ indirim"
    return {
        "code_prefix": t.get("code_prefix", "FIRSAT"),
        "discount_type": discount_type,
        "discount_value": discount_value,
        "min_order_try": min_order_try,
        "min_order_usd": t.get("min_order_usd", 0),
        "description_tr": description_tr,
        "description_en": t.get("description_en",
                                f"One-day deal: {description_tr}"),
        "valid_hours": int(t.get("valid_hours", 24)),
    }


def create_weekly_deal(template: dict = None, actor="instagram_agent"):
    """Creates a fresh one-day coupon and returns its full row (with generated code)."""
    spec = build_weekly_deal(template)
    now = _now()
    expires = now + timedelta(hours=spec["valid_hours"])
    conn = get_db()
    code = None
    # Retry on the rare collision.
    for _ in range(6):
        candidate = generate_code(spec["code_prefix"], 3)
        try:
            create_coupon(
                candidate, spec["discount_type"], spec["discount_value"],
                min_order_usd=spec["min_order_usd"], min_order_try=spec["min_order_try"],
                description_tr=spec["description_tr"], description_en=spec["description_en"],
                starts_at=_iso(now), expires_at=_iso(expires),
                max_uses=None, per_user_limit=1, source="weekly_deal",
                campaign_id=f"weekly_{now.strftime('%Y%m%d')}", actor=actor, conn=conn, commit=False,
            )
            code = candidate
            break
        except ValueError:
            continue
    conn.commit()
    row = conn.execute("SELECT * FROM coupons WHERE code = ?", (code,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_active_deal(conn=None):
    """Returns the currently valid weekly deal, if any."""
    own = conn is None
    if own:
        conn = get_db()
    expire_coupons(conn, commit=False)
    if own:
        conn.commit()
    rows = conn.execute(
        "SELECT * FROM coupons WHERE is_active = 1 AND source = 'weekly_deal' "
        "AND expires_at IS NOT NULL AND expires_at > ? ORDER BY created_at DESC LIMIT 1",
        (_iso(_now()),)).fetchall()
    if own:
        conn.close()
    return dict(rows[0]) if rows else None
