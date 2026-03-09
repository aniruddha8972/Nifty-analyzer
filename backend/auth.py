"""
backend/auth.py  —  OTP-based auth (no passwords).

Public API:
  register(username, name, email)           → (bool, str)
  send_otp(email)                           → (bool, str)
  verify_otp(email, token)                  → (bool, str, user_info|None)
  logout(user_info)                         → None
  load_user_portfolio(user_info)            → dict
  save_user_portfolio(user_info, portfolio) → None
  is_supabase_mode()                        → bool
  is_admin(user_info)                       → bool

  # Kept for backward compat (admin dashboard uses these)
  validate_password(pw)                     → (bool, list)
  update_password(user_info, cur, new)      → (bool, str)
  admin_list_users()                        → list[dict]
  admin_delete_user(user_id)               → (bool, str)
  admin_create_user(u,n,e,pw)              → (bool, str)
  admin_update_user(user_id, fields)       → (bool, str)

OTP flow (Supabase):
  send_otp   → client.auth.sign_in_with_otp({"email": email})
  verify_otp → client.auth.verify_otp({"email": email, "token": code, "type": "email"})

Local fallback:
  Generates a 6-digit OTP, stores it in memory (60s TTL), emails not sent
  — shows OTP on screen with a warning banner.
"""

import hashlib, json, re, threading, random, time
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
#  PASSWORD VALIDATION (kept for admin dashboard / backward compat)
# ══════════════════════════════════════════════════════════════════════

def validate_password(password: str) -> tuple[bool, list[str]]:
    SPECIAL = set("!@#$%^&*()_+-=[]{}|;:,./<>?")
    rules = []
    if len(password) < 8:            rules.append("At least 8 characters")
    if not any(c.isupper() for c in password): rules.append("At least one uppercase letter (A-Z)")
    if not any(c.islower() for c in password): rules.append("At least one lowercase letter (a-z)")
    if not any(c.isdigit() for c in password): rules.append("At least one number (0-9)")
    if not any(c in SPECIAL for c in password): rules.append("At least one special character (!@#$%...)")
    return (len(rules) == 0), rules


# ══════════════════════════════════════════════════════════════════════
#  USERNAME SUGGESTION HELPER
# ══════════════════════════════════════════════════════════════════════

def _suggest_usernames(base: str, taken: set[str]) -> list[str]:
    base = re.sub(r'[^a-z0-9_]', '', base.lower())[:12] or "user"
    year = str(datetime.now().year)[2:]
    nums = [str(random.randint(10, 99)) for _ in range(6)]
    candidates = [
        f"{base}{year}", f"{base}_trades", f"{base}_nse",
        f"{base}{nums[0]}", f"{base}{nums[1]}", f"nifty_{base}", f"{base}_{nums[2]}",
    ]
    return [c for c in candidates if c not in taken and len(c) >= 3][:3]


# ══════════════════════════════════════════════════════════════════════
#  LOCAL OTP STORE (in-memory, 60s TTL)
# ══════════════════════════════════════════════════════════════════════

_LOCAL_OTP: dict[str, tuple[str, float]] = {}   # email → (code, expires_at)
_OTP_TTL = 300   # 5 minutes


def _local_generate_otp(email: str) -> str:
    code = str(random.randint(100000, 999999))
    _LOCAL_OTP[email] = (code, time.time() + _OTP_TTL)
    return code


def _local_verify_otp_code(email: str, code: str) -> bool:
    entry = _LOCAL_OTP.get(email)
    if not entry:
        return False
    stored_code, expires_at = entry
    if time.time() > expires_at:
        del _LOCAL_OTP[email]
        return False
    if stored_code != code.strip():
        return False
    del _LOCAL_OTP[email]
    return True


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE — REGISTER (no password)
# ══════════════════════════════════════════════════════════════════════

def _sb_get_taken_usernames(client) -> set[str]:
    try:
        res = client.table("profiles").select("username").execute()
        return {r["username"].lower() for r in (res.data or [])}
    except Exception:
        return set()


def _sb_register(username: str, name: str, email: str) -> tuple[bool, str]:
    """
    Create profile row for a new user (no password).
    Supabase Auth user is created lazily on first OTP verify.
    We pre-validate the username and email here, then upsert the profile.
    """
    username = username.strip().lower()
    email    = email.strip().lower()

    if not re.match(r'^[a-z0-9_]{3,20}$', username):
        return False, "Username: 3–20 chars, letters/numbers/underscore only"
    if len(name.strip()) < 2:
        return False, "Please enter your full name"
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return False, "Enter a valid email address"

    client = _get_supabase_client()

    # Username taken?
    try:
        res = client.table("profiles").select("username").eq("username", username).execute()
        if res.data:
            taken   = _sb_get_taken_usernames(client)
            suggest = _suggest_usernames(username, taken)
            s_str   = "  ·  ".join(suggest) if suggest else ""
            hint    = f"\n💡 Try: {s_str}" if s_str else ""
            return False, f"USERNAME_TAKEN:{','.join(suggest)}"
    except Exception:
        pass

    # Email taken?
    try:
        res = client.table("profiles").select("email").eq("email", email).execute()
        if res.data:
            return False, "EMAIL_EXISTS:Email already registered — sign in instead"
    except Exception:
        pass

    # Send OTP — Supabase will create the auth user on first verify
    # We store the intended username+name in a pending_profiles table or
    # just pass them via Supabase sign_up metadata.
    try:
        client.auth.sign_up({
            "email": email,
            "password": _random_password(),   # required by sign_up API; user never sees it
            "options": {
                "data": {"name": name.strip(), "username": username},
            },
        })
    except Exception as e:
        err = str(e).lower()
        if "already registered" in err:
            return False, "EMAIL_EXISTS:Email already registered — sign in instead"
        # If sign_up fails (user may already exist from prior attempt), proceed
        pass

    # Send OTP
    try:
        client.auth.sign_in_with_otp({
            "email": email,
            "options": {"should_create_user": True},
        })
    except Exception as e:
        return False, f"Could not send OTP: {e}"

    # Store name/username in profiles so verify_otp can upsert it
    # We use a temporary record with no id (will be filled on verify)
    try:
        # Store as pending — will be completed on OTP verify
        import streamlit as st
        if "pending_profiles" not in st.session_state:
            st.session_state["pending_profiles"] = {}
        st.session_state["pending_profiles"][email] = {
            "username": username,
            "name":     name.strip(),
            "email":    email,
        }
    except Exception:
        pass

    return True, f"OTP_SENT:{email}"


def _random_password() -> str:
    """Generate a random strong password (never shown to user)."""
    import secrets, string
    chars = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(chars) for _ in range(24))


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE — SEND OTP (sign in)
# ══════════════════════════════════════════════════════════════════════

def _sb_send_otp(email: str) -> tuple[bool, str]:
    email = email.strip().lower()
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return False, "Enter a valid email address"
    try:
        client = _get_supabase_client()
        client.auth.sign_in_with_otp({
            "email": email,
            "options": {"should_create_user": False},
        })
        return True, f"OTP_SENT:{email}"
    except Exception as e:
        err = str(e).lower()
        if "not found" in err or "not registered" in err or "no user" in err:
            return False, "No account found for that email. Please register first."
        return False, f"Could not send OTP: {e}"


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE — VERIFY OTP
# ══════════════════════════════════════════════════════════════════════

def _sb_verify_otp(email: str, token: str) -> tuple[bool, str, dict | None]:
    email = email.strip().lower()
    token = token.strip()
    if not token or not (6 <= len(token) <= 8) or not token.isdigit():
        return False, "Enter the code from your email (6–8 digits)", None

    try:
        client = _get_supabase_client()
        res = client.auth.verify_otp({
            "email": email,
            "token": token,
            "type":  "email",
        })
    except Exception as e:
        err = str(e).lower()
        if "invalid" in err or "expired" in err or "otp" in err:
            return False, "Invalid or expired code — request a new one", None
        return False, f"Verification error: {e}", None

    if not res or not res.user:
        return False, "Invalid or expired code — request a new one", None

    uid          = res.user.id
    access_token = res.session.access_token if res.session else None
    authed       = _get_supabase_client(access_token)

    # Fetch or build profile
    try:
        prof_res = authed.table("profiles") \
                         .select("username, name, email, is_admin, created_at") \
                         .eq("id", uid).single().execute()
        prof = prof_res.data or {}
    except Exception:
        prof = {}

    # If this is a new registration, upsert the profile with pending data
    try:
        import streamlit as st
        pending = st.session_state.get("pending_profiles", {}).get(email)
    except Exception:
        pending = None

    if pending or not prof.get("username"):
        payload = pending or {
            "username": email.split("@")[0][:20],
            "name":     res.user.user_metadata.get("name", "User"),
            "email":    email,
        }
        payload["id"]       = uid
        payload["is_admin"] = prof.get("is_admin", False)
        try:
            authed.table("profiles").upsert(payload).execute()
            prof.update(payload)
        except Exception:
            pass
        # Clear pending
        try:
            st.session_state.get("pending_profiles", {}).pop(email, None)
        except Exception:
            pass
        # Create portfolio row if missing
        try:
            authed.table("portfolios").upsert({"user_id": uid, "data": {}}).execute()
        except Exception:
            pass

    user_info = {
        "user_id":       uid,
        "username":      prof.get("username", email.split("@")[0]),
        "name":          prof.get("name", "User"),
        "email":         prof.get("email", email),
        "is_admin":      prof.get("is_admin", False),
        "created_at":    prof.get("created_at", ""),
        "access_token":  access_token or "",
        "refresh_token": res.session.refresh_token if res.session else "",
    }
    return True, f"Welcome, {user_info['name']}!", user_info


# ══════════════════════════════════════════════════════════════════════
#  LOCAL JSON MODE — OTP
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


def _local_register(username: str, name: str, email: str) -> tuple[bool, str]:
    username = username.strip().lower()
    email    = email.strip().lower()

    if not re.match(r'^[a-z0-9_]{3,20}$', username):
        return False, "Username: 3–20 chars, letters/numbers/underscore only"
    if len(name.strip()) < 2:
        return False, "Please enter your full name"
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return False, "Enter a valid email address"

    users = _load_users()

    if username in users:
        taken   = set(users.keys())
        suggest = _suggest_usernames(username, taken)
        return False, f"USERNAME_TAKEN:{','.join(suggest)}"

    if any(u.get("email") == email for u in users.values()):
        return False, "EMAIL_EXISTS:Email already registered — sign in instead"

    # Create user (no password — OTP based)
    users[username] = {
        "username":   username,
        "name":       name.strip(),
        "email":      email,
        "is_admin":   False,
        "created_at": datetime.now().strftime("%d %b %Y, %H:%M"),
    }
    _save_users(users)
    pf = _local_pf_path(username)
    if not pf.exists():
        pf.write_text("{}")

    code = _local_generate_otp(email)
    return True, f"OTP_SENT:{email}:LOCAL:{code}"


def _local_send_otp(email: str) -> tuple[bool, str]:
    email = email.strip().lower()
    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
        return False, "Enter a valid email address"
    users = _load_users()
    user  = next((u for u in users.values() if u.get("email") == email), None)
    if not user:
        return False, "No account found for that email. Please register first."
    code = _local_generate_otp(email)
    return True, f"OTP_SENT:{email}:LOCAL:{code}"


def _local_verify_otp(email: str, token: str) -> tuple[bool, str, dict | None]:
    email = email.strip().lower()
    if not token or not (6 <= len(token) <= 8) or not token.isdigit():
        return False, "Enter the code shown on screen (6–8 digits)", None
    if not _local_verify_otp_code(email, token):
        return False, "Invalid or expired code — request a new one", None
    users = _load_users()
    user  = next((u for u in users.values() if u.get("email") == email), None)
    if not user:
        return False, "Account not found", None
    info = {k: v for k, v in user.items()}
    info["user_id"] = info["username"]
    return True, f"Welcome, {user['name']}!", info


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE — ADMIN / PORTFOLIO / MISC (unchanged)
# ══════════════════════════════════════════════════════════════════════

def _sb_list_users(token: str) -> list[dict]:
    try:
        res = _get_supabase_client(token).table("profiles") \
                  .select("id, username, name, email, is_admin, created_at") \
                  .order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []


def _sb_delete_user(admin_token: str, user_id: str) -> tuple[bool, str]:
    try:
        client = _get_supabase_client(admin_token)
        client.table("portfolios").delete().eq("user_id", user_id).execute()
        client.table("profiles").delete().eq("id", user_id).execute()
        return True, "User removed"
    except Exception as e:
        return False, f"Delete error: {e}"


def _sb_update_user(admin_token: str, user_id: str, fields: dict) -> tuple[bool, str]:
    try:
        _get_supabase_client(admin_token).table("profiles").update(fields).eq("id", user_id).execute()
        return True, "User updated"
    except Exception as e:
        return False, f"Update error: {e}"


def _sb_logout(user_info: dict) -> None:
    try:
        _get_supabase_client(user_info.get("access_token")).auth.sign_out()
    except Exception:
        pass


def _sb_update_password(user_info: dict, current_pw: str, new_pw: str) -> tuple[bool, str]:
    """Update password via Supabase. OTP users: current_pw is ignored (they have none)."""
    valid, fails = validate_password(new_pw.strip())
    if not valid:
        return False, "Weak password: " + " · ".join(fails)
    token = user_info.get("access_token", "")
    if not token:
        return False, "Not logged in"
    try:
        _get_supabase_client(token).auth.update_user({"password": new_pw.strip()})
        return True, "Password updated successfully"
    except Exception as e:
        return False, f"Update failed: {e}"


def _sb_load_portfolio(user_info: dict) -> dict:
    uid = user_info.get("user_id", "")
    if not uid: return {}
    from backend.db_init import load_portfolio_rpc
    data, _ = load_portfolio_rpc(uid)
    return data


def _sb_save_portfolio(user_info: dict, portfolio: dict) -> None:
    uid = user_info.get("user_id", "")
    if not uid: raise ValueError("No user_id")
    from backend.db_init import save_portfolio_rpc
    ok, msg = save_portfolio_rpc(uid, portfolio)
    if not ok: raise Exception(msg)


def _local_list_users() -> list[dict]:
    return [{k: v for k, v in u.items() if k != "password_hash"} for u in _load_users().values()]


def _local_delete_user(user_id: str) -> tuple[bool, str]:
    users = _load_users()
    if user_id not in users: return False, "User not found"
    if users[user_id].get("is_admin"): return False, "Cannot delete admin account"
    del users[user_id]
    _save_users(users)
    pf = _local_pf_path(user_id)
    if pf.exists(): pf.unlink()
    return True, f"User {user_id} deleted"


def _local_update_user(user_id: str, fields: dict) -> tuple[bool, str]:
    users = _load_users()
    if user_id not in users: return False, "User not found"
    for k, v in fields.items():
        if k != "password_hash":
            users[user_id][k] = v
    _save_users(users)
    return True, "User updated"


def _local_update_password(user_info: dict, current_pw: str, new_pw: str) -> tuple[bool, str]:
    # In OTP mode passwords are not required for login, but admin dashboard
    # may still set/verify passwords. Check current hash if one exists.
    valid, fails = validate_password(new_pw.strip())
    if not valid:
        return False, "Weak password: " + " · ".join(fails)
    username = user_info.get("username", "")
    users = _load_users()
    if username not in users: return False, "User not found"
    stored_hash = users[username].get("password_hash")
    if stored_hash and stored_hash != _hash(current_pw):
        return False, "Current password is incorrect"
    users[username]["password_hash"] = _hash(new_pw.strip())
    _save_users(users)
    return True, "Password updated successfully"


def _local_load_portfolio(user_info: dict) -> dict:
    path = _local_pf_path(user_info.get("username", ""))
    if not path.exists(): return {}
    with _LOCK:
        try:    return json.loads(path.read_text())
        except: return {}


def _local_save_portfolio(user_info: dict, portfolio: dict):
    _ensure_local_dirs()
    path = _local_pf_path(user_info.get("username", ""))
    with _LOCK:
        path.write_text(json.dumps(portfolio, indent=2, default=str))


def _get_admin_token() -> str | None:
    try:
        import streamlit as st
        user = st.session_state.get("user_info", {})
        return user.get("access_token", "") if user.get("is_admin") else None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════

def register(username: str, name: str, email: str, password: str = "") -> tuple[bool, str]:
    """Register new user (password param ignored — OTP only)."""
    if _use_supabase():
        return _sb_register(username, name, email)
    return _local_register(username, name, email)


def send_otp(email: str) -> tuple[bool, str]:
    """
    Send a 6-digit OTP to email.
    Returns (True, "OTP_SENT:<email>") on success.
    Returns (True, "OTP_SENT:<email>:LOCAL:<code>") in local mode.
    """
    if _use_supabase():
        return _sb_send_otp(email)
    return _local_send_otp(email)


def verify_otp(email: str, token: str) -> tuple[bool, str, dict | None]:
    """Verify 6-digit OTP code. Returns (ok, message, user_info|None)."""
    if _use_supabase():
        return _sb_verify_otp(email, token)
    return _local_verify_otp(email, token)


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


def update_password(user_info: dict, current_pw: str, new_pw: str) -> tuple[bool, str]:
    if _use_supabase():
        return _sb_update_password(user_info, current_pw, new_pw)
    return _local_update_password(user_info, current_pw, new_pw)


def is_supabase_mode() -> bool:
    return _use_supabase()


def is_admin(user_info: dict) -> bool:
    return bool(user_info.get("is_admin", False))


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


def admin_create_user(username: str, name: str, email: str, password: str = "") -> tuple[bool, str]:
    return register(username, name, email, password)


def admin_update_user(user_id: str, fields: dict) -> tuple[bool, str]:
    if _use_supabase():
        token = _get_admin_token()
        return _sb_update_user(token, user_id, fields) if token else (False, "Not authorised")
    return _local_update_user(user_id, fields)


# Backward compat alias
def login(identifier: str, password: str = "") -> tuple[bool, str, dict | None]:
    """
    Legacy alias — now sends OTP instead of password login.
    UI should use send_otp() + verify_otp() directly.
    """
    return False, "Use OTP login: call send_otp(email) then verify_otp(email, code)", None


def request_password_reset(email: str) -> tuple[bool, str]:
    """Legacy alias — OTP is now used instead of password reset."""
    return send_otp(email)
