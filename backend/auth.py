"""
backend/auth.py  —  Unified auth: Supabase cloud + local JSON fallback.

Public API:
  register(username, name, email, password) → (bool, str)
  login(identifier, password)               → (bool, str, user_info|None)
  logout(user_info)                         → None
  load_user_portfolio(user_info)            → dict
  save_user_portfolio(user_info, portfolio) → None
  is_supabase_mode()                        → bool
  is_admin(user_info)                       → bool

  # Admin only
  admin_list_users()                        → list[dict]
  admin_delete_user(user_id, mode)          → (bool, str)
  admin_create_user(username,name,email,pw) → (bool, str)
  admin_update_user(user_id, fields, mode)  → (bool, str)
"""

import hashlib, json, re, threading
from datetime import datetime
from pathlib import Path


# ══════════════════════════════════════════════════════════════════════
#  MODE DETECTION
# ══════════════════════════════════════════════════════════════════════

def _use_supabase() -> bool:
    try:
        import streamlit as st
        return bool(
            st.secrets.get("supabase", {}).get("url") and
            st.secrets.get("supabase", {}).get("anon_key")
        )
    except Exception:
        return False


def _get_supabase_client(access_token: str | None = None):
    import streamlit as st
    from supabase import create_client
    url    = st.secrets["supabase"]["url"]
    key    = st.secrets["supabase"]["anon_key"]
    client = create_client(url, key)
    if access_token:
        client.postgrest.auth(access_token)
    return client


# ══════════════════════════════════════════════════════════════════════
#  USERNAME SUGGESTION HELPER
# ══════════════════════════════════════════════════════════════════════

def _suggest_usernames(base: str, taken: set[str]) -> list[str]:
    """Return up to 3 available username suggestions based on base."""
    import random
    base   = re.sub(r'[^a-z0-9_]', '', base.lower())[:12] or "user"
    year   = str(datetime.now().year)[2:]
    trades = ["_trades", "_nse", "_inv", "_50"]
    nums   = [str(random.randint(10, 99)) for _ in range(6)]

    candidates = [
        f"{base}{year}",
        f"{base}_trades",
        f"{base}_nse",
        f"{base}{nums[0]}",
        f"{base}{nums[1]}",
        f"nifty_{base}",
        f"{base}_{nums[2]}",
    ]
    return [c for c in candidates if c not in taken and len(c) >= 3][:3]


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE — REGISTER
# ══════════════════════════════════════════════════════════════════════

def _sb_get_taken_usernames(client) -> set[str]:
    try:
        res = client.table("profiles").select("username").execute()
        return {r["username"].lower() for r in (res.data or [])}
    except Exception:
        return set()


def _sb_register(username: str, name: str, email: str, password: str) -> tuple[bool, str]:
    # ── Validation first — no network calls ──────────────────────────
    username = username.strip().lower()
    email    = email.strip().lower()

    if not re.match(r'^[a-z0-9_]{3,20}$', username):
        return False, "Username: 3–20 chars, letters/numbers/underscore only"
    if len(name.strip()) < 2:
        return False, "Please enter your full name"
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return False, "Enter a valid email address"
    if len(password.strip()) < 6:
        return False, "Password must be at least 6 characters"

    client = _get_supabase_client()

    # ── Check username ────────────────────────────────────────────────
    try:
        res = client.table("profiles").select("username").eq("username", username).execute()
        if res.data:
            taken   = _sb_get_taken_usernames(client)
            suggest = _suggest_usernames(username, taken)
            s_str   = "  ·  ".join(suggest) if suggest else ""
            hint    = f"\n💡 Try: {s_str}" if s_str else ""
            return False, f"Username **{username}** is already taken.{hint}"
    except Exception:
        pass  # table may not exist yet — let it proceed

    # ── Check email ───────────────────────────────────────────────────
    try:
        res = client.table("profiles").select("email").eq("email", email).execute()
        if res.data:
            return False, "Email already registered — try signing in"
    except Exception:
        pass

    # ── Create auth user ──────────────────────────────────────────────
    try:
        res = client.auth.sign_up({"email": email, "password": password,
                                   "options": {"data": {"name": name.strip()}}})
    except Exception as e:
        err = str(e)
        if "already registered" in err.lower():
            return False, "Email already registered — try signing in"
        return False, f"Could not create account: {err}"

    if not res.user:
        return False, "Could not create account — email may already be registered"

    uid   = res.user.id
    token = res.session.access_token if res.session else None

    # ── Update profile with real username + name + email ─────────────
    # Trigger already created a placeholder row — we overwrite it.
    # Try 3 strategies so email is ALWAYS saved regardless of token state.
    profile_payload = {
        "id":       uid,
        "username": username,
        "name":     name.strip(),
        "email":    email,
        "is_admin": False,
    }

    saved = False

    # Strategy 1: authenticated client (token available)
    if token:
        try:
            ac = _get_supabase_client(token)
            ac.table("profiles").upsert(profile_payload).execute()
            saved = True
        except Exception:
            pass

    # Strategy 2: anon client upsert (RLS insert policy is WITH CHECK(true))
    if not saved:
        try:
            client.table("profiles").upsert(profile_payload).execute()
            saved = True
        except Exception:
            pass

    # Strategy 3: UPDATE only (no id conflict) — works even without token
    if not saved:
        try:
            client.table("profiles")                   .update({"username": username, "name": name.strip(), "email": email})                   .eq("id", uid).execute()
        except Exception:
            pass

    # Portfolio row
    try:
        pf = _get_supabase_client(token) if token else client
        pf.table("portfolios").upsert({"user_id": uid, "data": {}}).execute()
    except Exception:
        pass

    if token:
        return True, f"Welcome, {name.strip()}! Account created."
    return True, "Account created! Check your email to confirm, then sign in."


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE — LOGIN
# ══════════════════════════════════════════════════════════════════════

def _sb_login(identifier: str, password: str) -> tuple[bool, str, dict | None]:
    client = _get_supabase_client()
    identifier = identifier.strip()
    email      = identifier.lower()

    # Username → email lookup
    if "@" not in email:
        try:
            res = client.table("profiles").select("email, username, name") \
                        .eq("username", email).single().execute()
            if not res.data:
                return False, "Username not found — try your email address", None
            email = res.data["email"] or ""
            if not email:
                return False, "Please sign in with your email address", None
        except Exception:
            return False, "Username not found", None

    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        err = str(e).lower()
        if "invalid" in err or "credentials" in err or "password" in err:
            return False, "Incorrect email or password", None
        return False, f"Login error: {e}", None

    if not res.user:
        return False, "Incorrect email or password", None

    uid   = res.user.id
    token = res.session.access_token

    try:
        prof = _get_supabase_client(token).table("profiles") \
                    .select("username, name, email, is_admin, created_at") \
                    .eq("id", uid).single().execute().data or {}
    except Exception:
        prof = {}

    user_info = {
        "user_id":       uid,
        "username":      prof.get("username", email.split("@")[0]),
        "name":          prof.get("name", "User"),
        "email":         prof.get("email", res.user.email),
        "is_admin":      prof.get("is_admin", False),
        "created_at":    prof.get("created_at", ""),
        "access_token":  token,
        "refresh_token": res.session.refresh_token if res.session else "",
    }
    return True, f"Welcome back, {user_info['name']}!", user_info


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE — ADMIN OPERATIONS
# ══════════════════════════════════════════════════════════════════════

def _sb_list_users(token: str) -> list[dict]:
    try:
        res = _get_supabase_client(token).table("profiles") \
                  .select("id, username, name, email, is_admin, created_at") \
                  .order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        return []


def _sb_delete_user(admin_token: str, user_id: str) -> tuple[bool, str]:
    try:
        client = _get_supabase_client(admin_token)
        # Delete portfolio first (FK)
        client.table("portfolios").delete().eq("user_id", user_id).execute()
        # Delete profile
        client.table("profiles").delete().eq("id", user_id).execute()
        # Note: auth.users row remains but is harmless — user can't log in
        # without a profile. Full deletion requires service_role key.
        return True, "User removed"
    except Exception as e:
        return False, f"Delete error: {e}"


def _sb_admin_create_user(admin_token: str, username: str, name: str,
                          email: str, password: str) -> tuple[bool, str]:
    return _sb_register(username, name, email, password)


def _sb_update_user(admin_token: str, user_id: str, fields: dict) -> tuple[bool, str]:
    try:
        client = _get_supabase_client(admin_token)
        client.table("profiles").update(fields).eq("id", user_id).execute()
        return True, "User updated"
    except Exception as e:
        return False, f"Update error: {e}"


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE — PORTFOLIO
# ══════════════════════════════════════════════════════════════════════

def _sb_logout(user_info: dict) -> None:
    try:
        _get_supabase_client(user_info.get("access_token")).auth.sign_out()
    except Exception:
        pass


def _sb_load_portfolio(user_info: dict) -> dict:
    """Load portfolio — tries with auth token, falls back to anon."""
    uid   = user_info.get("user_id", "")
    token = user_info.get("access_token", "")
    if not uid:
        return {}
    for client in [_get_supabase_client(token), _get_supabase_client()]:
        try:
            res = client.table("portfolios").select("data") \
                        .eq("user_id", uid).single().execute()
            if res.data:
                return res.data.get("data", {}) or {}
        except Exception:
            continue
    return {}


def _sb_save_portfolio(user_info: dict, portfolio: dict) -> None:
    """Save portfolio — raises exception on failure so caller can report it."""
    uid   = user_info.get("user_id", "")
    token = user_info.get("access_token", "")
    if not uid:
        raise ValueError("No user_id in user_info — not logged in")

    last_err = None
    for client in [_get_supabase_client(token), _get_supabase_client()]:
        try:
            client.table("portfolios").upsert({
                "user_id": uid,
                "data":    portfolio,
            }).execute()
            return   # success
        except Exception as e:
            last_err = e
            continue
    raise last_err or Exception("Portfolio save failed — both auth and anon client failed")


# ══════════════════════════════════════════════════════════════════════
#  LOCAL JSON MODE
# ══════════════════════════════════════════════════════════════════════

_BASE          = Path(__file__).parent.parent / "data"
_USERS_FILE    = _BASE / "users.json"
_PORTFOLIO_DIR = _BASE / "portfolios"
_LOCK          = threading.Lock()


def _ensure_local_dirs():
    _USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    if not _USERS_FILE.exists():
        _USERS_FILE.write_text("{}")


def _hash(p: str) -> str:
    return hashlib.sha256(p.strip().encode()).hexdigest()


def _load_users() -> dict:
    _ensure_local_dirs()
    with _LOCK:
        try:    return json.loads(_USERS_FILE.read_text())
        except: return {}


def _save_users(u: dict):
    _ensure_local_dirs()
    with _LOCK:
        _USERS_FILE.write_text(json.dumps(u, indent=2))


def _local_pf_path(username: str) -> Path:
    return _PORTFOLIO_DIR / f"{(username or 'anon').lower()}.json"


def _local_register(username: str, name: str, email: str, password: str) -> tuple[bool, str]:
    username = username.strip().lower()
    email    = email.strip().lower()

    if not re.match(r'^[a-z0-9_]{3,20}$', username):
        return False, "Username: 3–20 chars, letters/numbers/underscore only"
    if len(name.strip()) < 2:
        return False, "Please enter your full name"
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return False, "Enter a valid email address"
    if len(password.strip()) < 6:
        return False, "Password must be at least 6 characters"

    users = _load_users()

    if username in users:
        taken   = set(users.keys())
        suggest = _suggest_usernames(username, taken)
        s_str   = "  ·  ".join(suggest) if suggest else ""
        hint    = f"\n💡 Try: {s_str}" if s_str else ""
        return False, f"Username **{username}** is already taken.{hint}"

    if any(u.get("email") == email for u in users.values()):
        return False, "Email already registered — try signing in"

    users[username] = {
        "username":      username,
        "name":          name.strip(),
        "email":         email,
        "password_hash": _hash(password),
        "is_admin":      False,
        "created_at":    datetime.now().strftime("%d %b %Y, %H:%M"),
    }
    _save_users(users)
    p = _local_pf_path(username)
    if not p.exists():
        p.write_text("{}")
    return True, f"Welcome, {name.strip()}! Account created."


def _local_login(identifier: str, password: str) -> tuple[bool, str, dict | None]:
    identifier = identifier.strip().lower()
    users      = _load_users()
    user       = users.get(identifier) or next(
        (u for u in users.values() if u.get("email") == identifier), None
    )
    if not user:
        return False, "Username / email not found", None
    if user["password_hash"] != _hash(password):
        return False, "Incorrect password", None
    info = {k: v for k, v in user.items() if k != "password_hash"}
    info["user_id"] = info["username"]
    return True, f"Welcome back, {user['name']}!", info


# ── Local admin ops ───────────────────────────────────────────────────

def _local_list_users() -> list[dict]:
    users = _load_users()
    return [
        {k: v for k, v in u.items() if k != "password_hash"}
        for u in users.values()
    ]


def _local_delete_user(user_id: str) -> tuple[bool, str]:
    users = _load_users()
    if user_id not in users:
        return False, "User not found"
    if users[user_id].get("is_admin"):
        return False, "Cannot delete the admin account"
    del users[user_id]
    _save_users(users)
    pf = _local_pf_path(user_id)
    if pf.exists():
        pf.unlink()
    return True, f"User {user_id} deleted"


def _local_update_user(user_id: str, fields: dict) -> tuple[bool, str]:
    users = _load_users()
    if user_id not in users:
        return False, "User not found"
    for k, v in fields.items():
        if k not in ("password_hash",):   # never overwrite hash via admin
            users[user_id][k] = v
    _save_users(users)
    return True, "User updated"


def _local_load_portfolio(user_info: dict) -> dict:
    path = _local_pf_path(user_info.get("username", ""))
    if not path.exists():
        return {}
    with _LOCK:
        try:    return json.loads(path.read_text())
        except: return {}


def _local_save_portfolio(user_info: dict, portfolio: dict):
    _ensure_local_dirs()
    path = _local_pf_path(user_info.get("username", ""))
    with _LOCK:
        path.write_text(json.dumps(portfolio, indent=2, default=str))


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def register(username: str, name: str, email: str, password: str) -> tuple[bool, str]:
    if _use_supabase():
        return _sb_register(username, name, email, password)
    return _local_register(username, name, email, password)


def login(identifier: str, password: str) -> tuple[bool, str, dict | None]:
    if _use_supabase():
        return _sb_login(identifier, password)
    return _local_login(identifier, password)


def logout(user_info: dict) -> None:
    if _use_supabase():
        _sb_logout(user_info)


def load_user_portfolio(user_info: dict) -> dict:
    if _use_supabase():
        return _sb_load_portfolio(user_info)
    return _local_load_portfolio(user_info)


def save_user_portfolio(user_info: dict, portfolio: dict) -> None:
    if _use_supabase():
        _sb_save_portfolio(user_info, portfolio)
    else:
        _local_save_portfolio(user_info, portfolio)


def is_supabase_mode() -> bool:
    return _use_supabase()


def is_admin(user_info: dict) -> bool:
    return bool(user_info.get("is_admin", False))


# ── Admin operations (safe to call; check is_admin first in UI) ───────

def admin_list_users() -> list[dict]:
    if _use_supabase():
        token = _get_admin_token()
        return _sb_list_users(token) if token else []
    return _local_list_users()


def admin_delete_user(user_id: str) -> tuple[bool, str]:
    if _use_supabase():
        token = _get_admin_token()
        return _sb_delete_user(token, user_id) if token else (False, "Not authorised")
    return _local_delete_user(user_id)


def admin_create_user(username: str, name: str, email: str, password: str) -> tuple[bool, str]:
    return register(username, name, email, password)


def admin_update_user(user_id: str, fields: dict) -> tuple[bool, str]:
    if _use_supabase():
        token = _get_admin_token()
        return _sb_update_user(token, user_id, fields) if token else (False, "Not authorised")
    return _local_update_user(user_id, fields)


def _get_admin_token() -> str | None:
    """Get the current user's token from session (must be admin)."""
    try:
        import streamlit as st
        user = st.session_state.get("user_info", {})
        if user.get("is_admin"):
            return user.get("access_token", "")
        return None
    except Exception:
        return None
