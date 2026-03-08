"""
backend/auth.py
───────────────
Unified auth backend — Supabase (cloud) with local JSON fallback.

MODE DETECTION (automatic):
  • If st.secrets has [supabase] url + anon_key  → Supabase mode
  • Otherwise                                     → Local JSON mode

SUPABASE MODE
─────────────
  Auth:      Supabase Auth (email + password, JWT tokens)
  Users:     auth.users  (managed by Supabase)
  Profiles:  public.profiles  (username, name — our table)
  Portfolio: public.portfolios  (JSONB blob per user — our table)
  RLS:       Row Level Security enforces per-user isolation

LOCAL JSON MODE  (fallback — works without Supabase)
─────────────────
  Auth:      SHA-256 password hash in data/users.json
  Portfolio: data/portfolios/<username>.json

PUBLIC API (same regardless of mode):
  register(username, name, email, password) → (bool, str)
  login(username_or_email, password)        → (bool, str, user_info | None)
  logout(session)                           → None
  load_user_portfolio(user_info)            → dict
  save_user_portfolio(user_info, portfolio) → None
"""

import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path


# ══════════════════════════════════════════════════════════════════════
#  MODE DETECTION
# ══════════════════════════════════════════════════════════════════════

def _use_supabase() -> bool:
    """Return True if Supabase credentials are configured in st.secrets."""
    try:
        import streamlit as st
        return bool(
            st.secrets.get("supabase", {}).get("url") and
            st.secrets.get("supabase", {}).get("anon_key")
        )
    except Exception:
        return False


def _get_supabase_client(access_token: str | None = None):
    """
    Return a Supabase client.
    If access_token is provided, the client makes requests as that user
    (respecting RLS). Otherwise uses the anon key.
    """
    import streamlit as st
    from supabase import create_client

    url      = st.secrets["supabase"]["url"]
    anon_key = st.secrets["supabase"]["anon_key"]
    client   = create_client(url, anon_key)

    if access_token:
        # Set the user's JWT so all queries run under their identity
        client.postgrest.auth(access_token)  # supabase-py v2: set JWT on postgrest

    return client


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE AUTH
# ══════════════════════════════════════════════════════════════════════

def _sb_register(username: str, name: str, email: str, password: str) -> tuple[bool, str]:
    """Register via Supabase Auth + insert into profiles."""
    try:
        client = _get_supabase_client()

        # 1. Check username availability (public RPC — no auth needed)
        try:
            res = client.rpc("is_username_available", {"uname": username}).execute()
            if not res.data:
                return False, "Username already taken — try another"
        except Exception:
            # RPC may not exist yet — skip and let DB unique constraint catch it
            pass

        # 2. Create auth user (Supabase manages the password)
        res = client.auth.sign_up({"email": email, "password": password})
        if not res.user:
            return False, "Could not create account — email may already be registered"

        uid   = res.user.id
        token = res.session.access_token if res.session else None

        # 3. Insert profile row
        # Use authenticated client if we have a token (email confirmation OFF)
        # Fall back to anon client if no session (email confirmation ON) —
        # the RLS policy now allows insert for any valid auth.users id.
        insert_client = _get_supabase_client(token) if token else client

        insert_client.table("profiles").insert({
            "id":       uid,
            "username": username.lower().strip(),
            "name":     name.strip(),
        }).execute()

        # 4. Create empty portfolio row
        insert_client.table("portfolios").insert({
            "user_id": uid,
            "data":    {},
        }).execute()

        if token:
            return True, f"Welcome, {name}! Account created. You can sign in now."
        else:
            return True, (
                f"Account created! Check your email to confirm, "
                f"then sign in with your email and password."
            )

    except Exception as e:
        err = str(e)
        if "already registered" in err.lower() or "already exists" in err.lower():
            return False, "Email already registered — try signing in"
        if "username" in err.lower() and "unique" in err.lower():
            return False, "Username already taken — try another"
        return False, f"Registration error: {err}"


def _sb_login(email_or_username: str, password: str) -> tuple[bool, str, dict | None]:
    """
    Login via Supabase Auth.
    Accepts email OR username (looks up email from profiles if username given).
    """
    try:
        client = _get_supabase_client()
        email  = email_or_username.strip().lower()

        # If input looks like a username (no @), resolve to email
        if "@" not in email:
            res = client.table("profiles") \
                        .select("id, username, name") \
                        .eq("username", email) \
                        .single() \
                        .execute()
            if not res.data:
                return False, "Username not found", None
            # Get the email from auth.users — use admin API via anon key can't do this.
            # Workaround: ask users to enter email, or store email in profiles.
            # Simple fix: store email in profiles too.
            # For now: tell user to use their email for login.
            return False, "Please use your email address to sign in", None

        # Sign in with email + password
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if not res.user:
            return False, "Incorrect email or password", None

        uid   = res.user.id
        token = res.session.access_token

        # Fetch profile (username, name)
        prof_res = _get_supabase_client(token) \
                        .table("profiles") \
                        .select("username, name, created_at") \
                        .eq("id", uid) \
                        .single() \
                        .execute()

        prof = prof_res.data or {}
        user_info = {
            "user_id":    uid,
            "username":   prof.get("username", email.split("@")[0]),
            "name":       prof.get("name", "User"),
            "email":      res.user.email,
            "created_at": prof.get("created_at", ""),
            # Store tokens so we can make authenticated requests later
            "access_token":  token,
            "refresh_token": res.session.refresh_token if res.session else "",
        }
        return True, f"Welcome back, {user_info['name']}!", user_info

    except Exception as e:
        err = str(e)
        if "invalid" in err.lower() or "credentials" in err.lower():
            return False, "Incorrect email or password", None
        return False, f"Login error: {err}", None


def _sb_logout(user_info: dict) -> None:
    try:
        token  = user_info.get("access_token", "")
        client = _get_supabase_client(token)
        client.auth.sign_out()
    except Exception:
        pass


def _sb_load_portfolio(user_info: dict) -> dict:
    try:
        token  = user_info.get("access_token", "")
        uid    = user_info.get("user_id", "")
        client = _get_supabase_client(token)
        res    = client.table("portfolios") \
                       .select("data") \
                       .eq("user_id", uid) \
                       .single() \
                       .execute()
        return res.data.get("data", {}) if res.data else {}
    except Exception:
        return {}


def _sb_save_portfolio(user_info: dict, portfolio: dict) -> None:
    try:
        token  = user_info.get("access_token", "")
        uid    = user_info.get("user_id", "")
        client = _get_supabase_client(token)
        client.table("portfolios").upsert({
            "user_id": uid,
            "data":    portfolio,
        }).execute()
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════
#  LOCAL JSON AUTH (fallback)
# ══════════════════════════════════════════════════════════════════════

_BASE         = Path(__file__).parent.parent / "data"
_USERS_FILE   = _BASE / "users.json"
_PORTFOLIO_DIR= _BASE / "portfolios"
_LOCK         = threading.Lock()

def _ensure_local_dirs():
    _USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
    if not _USERS_FILE.exists():
        _USERS_FILE.write_text("{}")

def _hash(plain: str) -> str:
    return hashlib.sha256(plain.strip().encode()).hexdigest()

def _load_users() -> dict:
    _ensure_local_dirs()
    with _LOCK:
        try:    return json.loads(_USERS_FILE.read_text())
        except: return {}

def _save_users(users: dict):
    _ensure_local_dirs()
    with _LOCK:
        _USERS_FILE.write_text(json.dumps(users, indent=2))

def _local_pf_path(username: str) -> Path:
    safe = (username or "anonymous").lower()
    return _PORTFOLIO_DIR / f"{safe}.json"


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
        return False, "Username already taken — try another"
    if any(u["email"] == email for u in users.values()):
        return False, "Email already registered — try signing in"

    users[username] = {
        "username":      username,
        "name":          name.strip(),
        "email":         email,
        "password_hash": _hash(password),
        "created_at":    datetime.now().strftime("%d %b %Y, %H:%M"),
    }
    _save_users(users)
    p = _local_pf_path(username)
    if not p.exists():
        p.write_text("{}")
    return True, f"Welcome, {name.strip()}! Account created."


def _local_login(identifier: str, password: str) -> tuple[bool, str, dict | None]:
    identifier = identifier.strip().lower()
    users = _load_users()

    # Accept username OR email
    user = users.get(identifier) or next(
        (u for u in users.values() if u["email"] == identifier), None
    )
    if not user:
        return False, "Username or email not found", None
    if user["password_hash"] != _hash(password):
        return False, "Incorrect password", None

    info = {k: v for k, v in user.items() if k != "password_hash"}
    info["user_id"] = info["username"]   # local mode: user_id = username
    return True, f"Welcome back, {user['name']}!", info


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
#  PUBLIC API — auto-dispatches to Supabase or Local
# ══════════════════════════════════════════════════════════════════════

def register(username: str, name: str, email: str, password: str) -> tuple[bool, str]:
    """Register a new user. Returns (success, message)."""
    if _use_supabase():
        return _sb_register(username.strip().lower(), name.strip(),
                            email.strip().lower(), password.strip())
    return _local_register(username, name, email, password)


def login(identifier: str, password: str) -> tuple[bool, str, dict | None]:
    """
    Authenticate. identifier = email (Supabase) or username/email (local).
    Returns (success, message, user_info | None).
    """
    if _use_supabase():
        return _sb_login(identifier, password)
    return _local_login(identifier, password)


def logout(user_info: dict) -> None:
    """Sign out. Clears Supabase session if in cloud mode."""
    if _use_supabase():
        _sb_logout(user_info)


def load_user_portfolio(user_info: dict) -> dict:
    """Load the user's portfolio from Supabase or local file."""
    if _use_supabase():
        return _sb_load_portfolio(user_info)
    return _local_load_portfolio(user_info)


def save_user_portfolio(user_info: dict, portfolio: dict) -> None:
    """Persist the user's portfolio to Supabase or local file."""
    if _use_supabase():
        _sb_save_portfolio(user_info, portfolio)
    else:
        _local_save_portfolio(user_info, portfolio)


def is_supabase_mode() -> bool:
    """Return True if running with Supabase backend."""
    return _use_supabase()
