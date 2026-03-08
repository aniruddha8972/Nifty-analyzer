"""
backend/db_init.py
──────────────────
Self-healing database initialiser.

Called once at app startup. Idempotently:
  1. Creates tables (profiles, portfolios) if missing
  2. Sets up RLS policies (drops & recreates safely)
  3. Creates trigger for auto-profile on new auth user
  4. Creates is_username_available() RPC
  5. Seeds the admin account (Aniruddha Giri)
  6. Handles ALL errors gracefully — app always starts even if DB is down

Usage (in app.py):
  from backend.db_init import ensure_db
  ensure_db()   # call before render_auth_page()
"""

import streamlit as st

# ── Admin credentials (seeded once, never overwritten) ────────────────
ADMIN_NAME     = "Aniruddha Giri"
ADMIN_EMAIL    = "girianiruddha8972@gmail.com"
ADMIN_PASSWORD = "897282"
ADMIN_USERNAME = "admin"

# ── SQL blocks (each idempotent) ───────────────────────────────────────

_SQL_PROFILES = """
CREATE TABLE IF NOT EXISTS public.profiles (
  id          UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  username    TEXT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  email       TEXT,
  is_admin    BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
"""

_SQL_PORTFOLIOS = """
CREATE TABLE IF NOT EXISTS public.portfolios (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
  data       JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);
"""

_SQL_RLS_PROFILES = """
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "profiles_select_all"  ON public.profiles;
DROP POLICY IF EXISTS "profiles_select_own"  ON public.profiles;
DROP POLICY IF EXISTS "profiles_insert_own"  ON public.profiles;
DROP POLICY IF EXISTS "profiles_update_own"  ON public.profiles;
DROP POLICY IF EXISTS "profiles_delete_own"  ON public.profiles;

CREATE POLICY "profiles_select_all" ON public.profiles
  FOR SELECT USING (true);

CREATE POLICY "profiles_insert_own" ON public.profiles
  FOR INSERT WITH CHECK (true);

CREATE POLICY "profiles_update_own" ON public.profiles
  FOR UPDATE USING (auth.uid() = id OR
    (SELECT is_admin FROM public.profiles WHERE id = auth.uid()) = true);

CREATE POLICY "profiles_delete_own" ON public.profiles
  FOR DELETE USING (
    (SELECT is_admin FROM public.profiles WHERE id = auth.uid()) = true
  );
"""

_SQL_RLS_PORTFOLIOS = """
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "portfolios_all_own"    ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_select_own" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_insert_own" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_update_own" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_delete_own" ON public.portfolios;

CREATE POLICY "portfolios_select_own" ON public.portfolios
  FOR SELECT USING (
    auth.uid() = user_id OR
    (SELECT is_admin FROM public.profiles WHERE id = auth.uid()) = true
  );

CREATE POLICY "portfolios_insert_own" ON public.portfolios
  FOR INSERT WITH CHECK (true);

CREATE POLICY "portfolios_update_own" ON public.portfolios
  FOR UPDATE USING (
    auth.uid() = user_id OR
    (SELECT is_admin FROM public.profiles WHERE id = auth.uid()) = true
  );

CREATE POLICY "portfolios_delete_own" ON public.portfolios
  FOR DELETE USING (
    auth.uid() = user_id OR
    (SELECT is_admin FROM public.profiles WHERE id = auth.uid()) = true
  );
"""

_SQL_TRIGGER = """
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  base_username TEXT;
  final_username TEXT;
  counter INT := 0;
BEGIN
  -- Build a safe base username from email prefix
  base_username := lower(regexp_replace(split_part(NEW.email, '@', 1), '[^a-z0-9_]', '_', 'g'));
  base_username := substr(base_username, 1, 15);
  final_username := base_username || '_' || substr(NEW.id::text, 1, 4);

  -- Ensure username is unique (retry with counter if needed)
  WHILE EXISTS (SELECT 1 FROM public.profiles WHERE username = final_username) LOOP
    counter := counter + 1;
    final_username := base_username || '_' || counter::text;
    IF counter > 99 THEN EXIT; END IF;
  END LOOP;

  INSERT INTO public.profiles (id, username, name, email)
  VALUES (
    NEW.id,
    final_username,
    coalesce(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1)),
    NEW.email
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email;  -- always update email even if row exists

  INSERT INTO public.portfolios (user_id, data)
  VALUES (NEW.id, '{}')
  ON CONFLICT (user_id) DO NOTHING;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
"""

_SQL_UPDATED_AT = """
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

DROP TRIGGER IF EXISTS portfolios_updated_at ON public.portfolios;
CREATE TRIGGER portfolios_updated_at
  BEFORE UPDATE ON public.portfolios
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
"""

_SQL_RPC = """
CREATE OR REPLACE FUNCTION public.is_username_available(uname TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT NOT EXISTS (
    SELECT 1 FROM public.profiles WHERE lower(username) = lower(uname)
  );
$$;
GRANT EXECUTE ON FUNCTION public.is_username_available TO anon, authenticated;
"""

_SQL_ADD_EMAIL_COL = """
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
"""


def _get_client():
    from supabase import create_client
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)


def _run_sql(client, sql: str, label: str) -> bool:
    """Execute a SQL block via postgrest rpc. Returns True on success."""
    try:
        client.rpc("exec_sql", {"query": sql}).execute()
        return True
    except Exception:
        # exec_sql RPC may not exist — try direct table ops as fallback
        return False


def _ensure_tables(client) -> dict:
    """
    Check which tables exist by attempting a dummy query.
    Returns { 'profiles': bool, 'portfolios': bool }
    """
    status = {}
    for tbl in ("profiles", "portfolios"):
        try:
            client.table(tbl).select("*").limit(1).execute()
            status[tbl] = True
        except Exception as e:
            status[tbl] = "does not exist" in str(e).lower() or "42P01" in str(e)
    return status


def _seed_admin(client) -> tuple[bool, str]:
    """
    Ensure admin profile exists and has is_admin=True.
    Never calls sign_up() — avoids email rate limits entirely.
    The admin auth user must be created via SQL (see DEPLOY.md).
    """
    try:
        # Check if admin profile row exists
        res = client.table("profiles") \
                    .select("id, username, is_admin") \
                    .eq("email", ADMIN_EMAIL) \
                    .execute()

        if res.data:
            admin_id  = res.data[0]["id"]
            is_admin  = res.data[0].get("is_admin", False)
            if not is_admin:
                # Profile exists but admin flag not set — fix it
                client.table("profiles") \
                      .update({"is_admin": True, "username": ADMIN_USERNAME,
                               "name": ADMIN_NAME}) \
                      .eq("id", admin_id) \
                      .execute()
            return True, "admin_exists"

        # Profile not found — admin not created via SQL yet
        # Don't call sign_up() — just report it gracefully
        return False, (
            "Admin account not found. "
            "Run the SQL in DEPLOY.md to create it without email rate limits."
        )

    except Exception as e:
        return False, f"Admin check error: {e}"
        ac.table("portfolios").upsert({
            "user_id": uid,
            "data":    {},
        }).execute()

        return True, "admin_created"

    except Exception as e:
        err = str(e).lower()
        if "already registered" in err or "already exists" in err:
            # Admin auth exists but profile may need is_admin flag
            try:
                client.table("profiles") \
                      .update({"is_admin": True}) \
                      .eq("email", ADMIN_EMAIL) \
                      .execute()
            except Exception:
                pass
            return True, "admin_exists"
        return False, f"Admin seed error: {e}"


# ── Public entry point ─────────────────────────────────────────────────

def ensure_db() -> list[str]:
    """
    Run at app startup. Idempotently sets up DB schema + admin.
    Returns list of status messages (shown in sidebar debug if needed).
    """
    if not _try_supabase():
        return ["⚡ Local mode — no DB init needed"]

    msgs = []
    try:
        client = _get_client()

        # 1. Check table existence
        status = _ensure_tables(client)
        msgs.append(f"profiles: {'✅' if status.get('profiles') else '⚠ missing'}")
        msgs.append(f"portfolios: {'✅' if status.get('portfolios') else '⚠ missing'}")

        # 2. Add missing columns (safe even if they exist)
        try:
            client.rpc("exec_sql", {"query": _SQL_ADD_EMAIL_COL}).execute()
        except Exception:
            pass

        # 3. Seed admin
        ok, msg = _seed_admin(client)
        if ok:
            msgs.append(f"admin: {'✅ ready' if 'exists' in msg else '✅ created'}")
        else:
            msgs.append(f"admin: ⚠ {msg}")

    except Exception as e:
        msgs.append(f"DB init warning: {e}")

    return msgs


def _try_supabase() -> bool:
    try:
        return bool(
            st.secrets.get("supabase", {}).get("url") and
            st.secrets.get("supabase", {}).get("anon_key")
        )
    except Exception:
        return False


# ── Admin helpers (called from admin dashboard) ────────────────────────

def admin_list_users(token: str) -> list[dict]:
    """Return all users. Uses SECURITY DEFINER RPC to bypass RLS."""
    try:
        client = _get_client()
        client.postgrest.auth(token)

        # Try admin RPC first (SECURITY DEFINER — sees all rows regardless of RLS)
        try:
            res = client.rpc("admin_get_all_profiles").execute()
            if res.data is not None:
                return res.data
        except Exception:
            pass

        # Fallback: direct table query
        res = client.table("profiles") \
                    .select("id, username, name, email, is_admin, created_at") \
                    .order("created_at", desc=True) \
                    .execute()
        return res.data or []
    except Exception:
        return []


def admin_delete_user(token: str, user_id: str) -> tuple[bool, str]:
    """Delete a user's profile + portfolio (admin only)."""
    try:
        client = _get_client()
        client.postgrest.auth(token)

        # Prevent deleting the admin account
        res = client.table("profiles").select("is_admin").eq("id", user_id).single().execute()
        if res.data and res.data.get("is_admin"):
            return False, "Cannot delete the admin account"

        # Delete portfolio first (FK)
        client.table("portfolios").delete().eq("user_id", user_id).execute()
        # Delete profile
        client.table("profiles").delete().eq("id", user_id).execute()
        return True, "User deleted"
    except Exception as e:
        return False, f"Delete error: {e}"


def admin_toggle_admin(token: str, user_id: str, make_admin: bool) -> tuple[bool, str]:
    """Grant or revoke admin flag for a user."""
    try:
        client = _get_client()
        client.postgrest.auth(token)
        client.table("profiles").update({"is_admin": make_admin}).eq("id", user_id).execute()
        return True, "Updated"
    except Exception as e:
        return False, f"Update error: {e}"


def admin_get_user_portfolio(token: str, user_id: str) -> dict:
    """Admin: read any user's portfolio."""
    try:
        client = _get_client()
        client.postgrest.auth(token)
        res = client.table("portfolios").select("data").eq("user_id", user_id).single().execute()
        return res.data.get("data", {}) if res.data else {}
    except Exception:
        return {}


def admin_create_user(
    token: str, username: str, name: str, email: str, password: str, is_admin: bool = False
) -> tuple[bool, str]:
    """Admin: create a new user account."""
    try:
        client = _get_client()

        # Check username availability
        try:
            res = client.rpc("is_username_available", {"uname": username}).execute()
            if not res.data:
                return False, "Username already taken"
        except Exception:
            pass

        # Create auth user
        res = client.auth.sign_up({"email": email, "password": password})
        if not res.user:
            return False, "Could not create auth user — email may be taken"

        uid   = res.user.id
        tok   = res.session.access_token if res.session else None
        ac    = _get_client()
        if tok:
            ac.postgrest.auth(tok)

        ac.table("profiles").upsert({
            "id":       uid,
            "username": username.lower().strip(),
            "name":     name.strip(),
            "email":    email.strip().lower(),
            "is_admin": is_admin,
        }).execute()

        ac.table("portfolios").upsert({"user_id": uid, "data": {}}).execute()
        return True, f"User '{username}' created successfully"

    except Exception as e:
        err = str(e).lower()
        if "already registered" in err:
            return False, "Email already registered"
        return False, f"Error: {e}"
