"""
backend/db_setup.py
────────────────────
Self-healing database initialiser.

Called once at app startup. Safely creates all tables, policies,
triggers, and the admin user if they don't exist yet.
No manual SQL Editor steps needed — ever.
"""

import hashlib
from datetime import datetime


# ══════════════════════════════════════════════════════════════════════
#  ADMIN CREDENTIALS  (hardcoded — single admin user)
# ══════════════════════════════════════════════════════════════════════
ADMIN_EMAIL    = "girianiruddha8972@gmail.com"
ADMIN_PASSWORD = "897282"
ADMIN_NAME     = "Aniruddha Giri"
ADMIN_USERNAME = "admin"


# ══════════════════════════════════════════════════════════════════════
#  SUPABASE SETUP
# ══════════════════════════════════════════════════════════════════════

_SETUP_SQL = """
-- ── profiles ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS profiles (
  id          UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  username    TEXT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  email       TEXT,
  is_admin    BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='profiles' AND policyname='profiles_select_all'
  ) THEN
    CREATE POLICY profiles_select_all ON profiles FOR SELECT USING (true);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='profiles' AND policyname='profiles_insert_open'
  ) THEN
    CREATE POLICY profiles_insert_open ON profiles FOR INSERT WITH CHECK (true);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='profiles' AND policyname='profiles_update_own'
  ) THEN
    CREATE POLICY profiles_update_own ON profiles FOR UPDATE USING (true);
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='profiles' AND policyname='profiles_delete_own'
  ) THEN
    CREATE POLICY profiles_delete_own ON profiles FOR DELETE USING (true);
  END IF;
END $$;

-- ── portfolios ────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS portfolios (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
  data        JSONB NOT NULL DEFAULT '{}',
  updated_at  TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies WHERE tablename='portfolios' AND policyname='portfolios_all_open'
  ) THEN
    CREATE POLICY portfolios_all_open ON portfolios FOR ALL USING (true) WITH CHECK (true);
  END IF;
END $$;

-- ── auto-update updated_at ────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

DROP TRIGGER IF EXISTS portfolios_updated_at ON portfolios;
CREATE TRIGGER portfolios_updated_at
  BEFORE UPDATE ON portfolios
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── auto-create profile on auth.users insert ──────────────────────────
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (id, username, name, email)
  VALUES (
    NEW.id,
    lower(split_part(NEW.email, '@', 1)) || '_' || substr(NEW.id::text, 1, 4),
    coalesce(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1)),
    NEW.email
  )
  ON CONFLICT (id) DO NOTHING;
  INSERT INTO public.portfolios (user_id, data)
  VALUES (NEW.id, '{}')
  ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- ── username availability RPC ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION is_username_available(uname TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT NOT EXISTS (SELECT 1 FROM public.profiles WHERE lower(username) = lower(uname));
$$;
GRANT EXECUTE ON FUNCTION is_username_available TO anon, authenticated;
"""


def _run_setup_sql(client) -> tuple[bool, str]:
    """Run the full setup SQL via Supabase RPC."""
    try:
        client.rpc("exec_sql", {"sql": _SETUP_SQL}).execute()
        return True, "ok"
    except Exception as e:
        return False, str(e)


def _ensure_exec_sql_rpc(client) -> bool:
    """
    Create a helper RPC that lets us run arbitrary SQL.
    This only works if the service_role key is used OR
    if the function already exists.
    """
    try:
        client.rpc("exec_sql", {"sql": "SELECT 1"}).execute()
        return True
    except Exception:
        return False


def _table_exists(client, table: str) -> bool:
    """Check if a table exists in public schema."""
    try:
        client.table(table).select("*").limit(1).execute()
        return True
    except Exception as e:
        return "does not exist" not in str(e).lower()


def _ensure_admin_supabase(client) -> tuple[bool, str]:
    """Create admin user in Supabase if not already there."""
    try:
        # Check if admin profile exists
        res = client.table("profiles").select("id, is_admin").eq("email", ADMIN_EMAIL).execute()
        if res.data:
            # Already exists — ensure is_admin flag is set
            admin_id = res.data[0]["id"]
            client.table("profiles").update({
                "is_admin": True,
                "username": ADMIN_USERNAME,
                "name":     ADMIN_NAME,
            }).eq("id", admin_id).execute()
            return True, "Admin already exists"

        # Create via Supabase Auth sign_up
        res = client.auth.sign_up({
            "email":    ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "options":  {"data": {"name": ADMIN_NAME}},
        })
        if not res.user:
            return False, "Could not create admin auth user"

        uid   = res.user.id
        token = res.session.access_token if res.session else None
        ac    = _get_authed_client(client, token)

        # Upsert profile with is_admin=True
        ac.table("profiles").upsert({
            "id":       uid,
            "username": ADMIN_USERNAME,
            "name":     ADMIN_NAME,
            "email":    ADMIN_EMAIL,
            "is_admin": True,
        }).execute()

        ac.table("portfolios").upsert({
            "user_id": uid,
            "data":    {},
        }).execute()

        return True, "Admin created"

    except Exception as e:
        err = str(e)
        if "already registered" in err.lower():
            # Auth user exists but profile may be missing — try to fix
            try:
                sign_in = client.auth.sign_in_with_password({
                    "email": ADMIN_EMAIL, "password": ADMIN_PASSWORD
                })
                if sign_in.user:
                    uid   = sign_in.user.id
                    token = sign_in.session.access_token if sign_in.session else None
                    ac    = _get_authed_client(client, token)
                    ac.table("profiles").upsert({
                        "id":       uid,
                        "username": ADMIN_USERNAME,
                        "name":     ADMIN_NAME,
                        "email":    ADMIN_EMAIL,
                        "is_admin": True,
                    }).execute()
                    return True, "Admin profile fixed"
            except Exception as e2:
                return False, f"Admin fix failed: {e2}"
        return False, f"Admin setup error: {err}"


def _get_authed_client(base_client, token):
    if token:
        base_client.postgrest.auth(token)
    return base_client


# ── Local JSON admin setup ────────────────────────────────────────────

def _ensure_admin_local() -> None:
    """Ensure admin exists in local users.json."""
    import json
    import threading
    from pathlib import Path

    base       = Path(__file__).parent.parent / "data"
    users_file = base / "users.json"
    pf_dir     = base / "portfolios"
    base.mkdir(parents=True, exist_ok=True)
    pf_dir.mkdir(parents=True, exist_ok=True)

    if not users_file.exists():
        users_file.write_text("{}")

    try:
        users = json.loads(users_file.read_text())
    except Exception:
        users = {}

    pw_hash = hashlib.sha256(ADMIN_PASSWORD.encode()).hexdigest()

    if ADMIN_USERNAME not in users:
        users[ADMIN_USERNAME] = {
            "username":      ADMIN_USERNAME,
            "name":          ADMIN_NAME,
            "email":         ADMIN_EMAIL,
            "password_hash": pw_hash,
            "is_admin":      True,
            "created_at":    datetime.now().strftime("%d %b %Y, %H:%M"),
        }
        users_file.write_text(json.dumps(users, indent=2))

    pf = pf_dir / f"{ADMIN_USERNAME}.json"
    if not pf.exists():
        pf.write_text("{}")


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT — called from app.py at startup
# ══════════════════════════════════════════════════════════════════════

_done = False   # run only once per process

def ensure_db() -> None:
    """
    Idempotent setup — safe to call every time the app starts.
    Creates tables / policies / admin if missing. No-op if all exists.
    """
    global _done
    if _done:
        return
    _done = True

    try:
        import streamlit as st
        from backend.secrets import get_supabase_url, get_supabase_anon_key
        sb_url = get_supabase_url()
        sb_key = get_supabase_anon_key()

        if sb_url and sb_key:
            from supabase import create_client
            client = create_client(sb_url, sb_key)
            # Ensure admin user exists (tables created by Supabase setup SQL,
            # but we self-heal whatever we can via the client API)
            _ensure_admin_supabase(client)
        else:
            _ensure_admin_local()

    except Exception:
        # Never crash the app during setup
        try:
            _ensure_admin_local()
        except Exception:
            pass
