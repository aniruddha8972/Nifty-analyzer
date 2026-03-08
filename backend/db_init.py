"""
backend/db_init.py
──────────────────
Self-healing DB init + admin seed + portfolio RPC helpers.
Called once at app startup via ensure_db().
"""

import streamlit as st

ADMIN_NAME     = "Aniruddha Giri"
ADMIN_EMAIL    = "girianiruddha8972@gmail.com"
ADMIN_PASSWORD = "897282"
ADMIN_USERNAME = "admin"

# ─────────────────────────────────────────────────────────────────────
# SQL BLOCKS  (all idempotent)
# ─────────────────────────────────────────────────────────────────────

_SQL_SETUP = """
-- ── Tables ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS public.profiles (
  id         UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  username   TEXT UNIQUE NOT NULL,
  name       TEXT NOT NULL DEFAULT '',
  email      TEXT,
  is_admin   BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.portfolios (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id    UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
  data       JSONB NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ── Add columns if missing ────────────────────────────────────────────
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS email    TEXT;
ALTER TABLE public.profiles ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;

-- ── RLS on profiles ───────────────────────────────────────────────────
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "prof_sel"  ON public.profiles;
DROP POLICY IF EXISTS "prof_ins"  ON public.profiles;
DROP POLICY IF EXISTS "prof_upd"  ON public.profiles;
DROP POLICY IF EXISTS "prof_del"  ON public.profiles;
DROP POLICY IF EXISTS "profiles_select_all"  ON public.profiles;
DROP POLICY IF EXISTS "profiles_select_own"  ON public.profiles;
DROP POLICY IF EXISTS "profiles_insert_own"  ON public.profiles;
DROP POLICY IF EXISTS "profiles_update_own"  ON public.profiles;
DROP POLICY IF EXISTS "profiles_delete_own"  ON public.profiles;

CREATE POLICY "prof_sel" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "prof_ins" ON public.profiles FOR INSERT WITH CHECK (true);
CREATE POLICY "prof_upd" ON public.profiles FOR UPDATE USING (true);
CREATE POLICY "prof_del" ON public.profiles FOR DELETE USING (
  (SELECT is_admin FROM public.profiles WHERE id = auth.uid()) = true
);

-- ── RLS on portfolios ─────────────────────────────────────────────────
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "pf_sel"  ON public.portfolios;
DROP POLICY IF EXISTS "pf_ins"  ON public.portfolios;
DROP POLICY IF EXISTS "pf_upd"  ON public.portfolios;
DROP POLICY IF EXISTS "pf_del"  ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_all_own"    ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_select_own" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_insert_own" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_update_own" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_delete_own" ON public.portfolios;

CREATE POLICY "pf_sel" ON public.portfolios FOR SELECT USING (true);
CREATE POLICY "pf_ins" ON public.portfolios FOR INSERT WITH CHECK (true);
CREATE POLICY "pf_upd" ON public.portfolios FOR UPDATE USING (true);
CREATE POLICY "pf_del" ON public.portfolios FOR DELETE USING (true);

-- ── Auto-update updated_at ────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

DROP TRIGGER IF EXISTS portfolios_updated_at ON public.portfolios;
CREATE TRIGGER portfolios_updated_at
  BEFORE UPDATE ON public.portfolios
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- ── Trigger: auto-create profile+portfolio on new auth user ───────────
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  base_u  TEXT;
  final_u TEXT;
  n       INT := 0;
BEGIN
  base_u  := lower(regexp_replace(split_part(NEW.email,'@',1),'[^a-z0-9_]','_','g'));
  base_u  := substr(base_u, 1, 14);
  final_u := base_u || '_' || substr(replace(NEW.id::text,'-',''), 1, 4);
  WHILE EXISTS (SELECT 1 FROM public.profiles WHERE username = final_u) LOOP
    n := n + 1;
    final_u := base_u || '_' || n::text;
    IF n > 999 THEN EXIT; END IF;
  END LOOP;
  INSERT INTO public.profiles (id, username, name, email)
  VALUES (NEW.id, final_u,
    coalesce(NEW.raw_user_meta_data->>'name', split_part(NEW.email,'@',1)),
    NEW.email)
  ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;
  INSERT INTO public.portfolios (user_id, data)
  VALUES (NEW.id, '{}') ON CONFLICT (user_id) DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ── SECURITY DEFINER RPC: save portfolio (bypasses RLS) ───────────────
-- Called from Python with the user's own user_id.
-- Validates that caller is authenticated OR that user_id exists.
CREATE OR REPLACE FUNCTION public.save_portfolio(p_user_id UUID, p_data JSONB)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.portfolios (user_id, data, updated_at)
  VALUES (p_user_id, p_data, NOW())
  ON CONFLICT (user_id)
  DO UPDATE SET data = EXCLUDED.data, updated_at = NOW();
END;
$$;
GRANT EXECUTE ON FUNCTION public.save_portfolio TO anon, authenticated;

-- ── SECURITY DEFINER RPC: load portfolio ─────────────────────────────
CREATE OR REPLACE FUNCTION public.load_portfolio(p_user_id UUID)
RETURNS JSONB LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE
  result JSONB;
BEGIN
  SELECT data INTO result FROM public.portfolios WHERE user_id = p_user_id;
  RETURN COALESCE(result, '{}'::jsonb);
END;
$$;
GRANT EXECUTE ON FUNCTION public.load_portfolio TO anon, authenticated;

-- ── SECURITY DEFINER RPC: admin list all profiles ─────────────────────
CREATE OR REPLACE FUNCTION public.admin_get_all_profiles()
RETURNS TABLE(id UUID, username TEXT, name TEXT, email TEXT,
              is_admin BOOLEAN, created_at TIMESTAMPTZ)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  RETURN QUERY
  SELECT p.id, p.username, p.name, p.email, p.is_admin, p.created_at
  FROM public.profiles p ORDER BY p.created_at DESC;
END;
$$;
GRANT EXECUTE ON FUNCTION public.admin_get_all_profiles TO anon, authenticated;

-- ── is_username_available RPC ─────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.is_username_available(uname TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT NOT EXISTS (
    SELECT 1 FROM public.profiles WHERE lower(username) = lower(uname)
  );
$$;
GRANT EXECUTE ON FUNCTION public.is_username_available TO anon, authenticated;

-- Backfill missing emails
UPDATE public.profiles p
SET email = u.email
FROM auth.users u
WHERE p.id = u.id AND (p.email IS NULL OR p.email = '');

-- SECURITY DEFINER RPC: fully delete user from auth.users + profiles + portfolios
-- Requires admin. Runs as postgres so it can delete from auth.users.
CREATE OR REPLACE FUNCTION public.admin_delete_user_full(p_user_id UUID)
RETURNS TEXT LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, auth AS $$
DECLARE
  caller_is_admin BOOLEAN;
BEGIN
  SELECT is_admin INTO caller_is_admin
  FROM public.profiles WHERE id = auth.uid();
  IF caller_is_admin IS NOT TRUE THEN
    RAISE EXCEPTION 'Admin access required';
  END IF;
  IF EXISTS (SELECT 1 FROM public.profiles WHERE id = p_user_id AND is_admin = TRUE) THEN
    RAISE EXCEPTION 'Cannot delete an admin account';
  END IF;
  DELETE FROM public.portfolios WHERE user_id = p_user_id;
  DELETE FROM public.profiles WHERE id = p_user_id;
  DELETE FROM auth.users WHERE id = p_user_id;
  RETURN 'deleted';
END;
$$;
GRANT EXECUTE ON FUNCTION public.admin_delete_user_full TO authenticated;
"""


def _get_client():
    from supabase import create_client
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["anon_key"]
    return create_client(url, key)


def _get_service_client():
    """Service role client — full admin access, bypasses ALL RLS and auth restrictions."""
    from supabase import create_client
    url     = st.secrets["supabase"]["url"]
    svc_key = st.secrets.get("supabase", {}).get("service_role_key", "")
    if not svc_key:
        raise ValueError("service_role_key not set in .streamlit/secrets.toml")
    return create_client(url, svc_key)


def _delete_auth_user(user_id: str) -> None:
    """Delete a user from auth.users using service role key (Admin API)."""
    import urllib.request, json
    url     = st.secrets["supabase"]["url"]
    svc_key = st.secrets.get("supabase", {}).get("service_role_key", "")
    if not svc_key:
        raise ValueError("service_role_key not set in secrets.toml")
    req = urllib.request.Request(
        f"{url}/auth/v1/admin/users/{user_id}",
        method="DELETE",
        headers={
            "apikey":        svc_key,
            "Authorization": f"Bearer {svc_key}",
        }
    )
    with urllib.request.urlopen(req) as resp:
        if resp.status not in (200, 204):
            raise Exception(f"Auth delete failed: HTTP {resp.status}")


def _try_supabase() -> bool:
    try:
        return bool(
            st.secrets.get("supabase", {}).get("url") and
            st.secrets.get("supabase", {}).get("anon_key")
        )
    except Exception:
        return False


def _ensure_tables(client) -> dict:
    status = {}
    for tbl in ("profiles", "portfolios"):
        try:
            client.table(tbl).select("*").limit(1).execute()
            status[tbl] = True
        except Exception:
            status[tbl] = False
    return status


def _seed_admin(client) -> tuple[bool, str]:
    """Ensure admin profile exists with is_admin=True. Never calls sign_up()."""
    try:
        res = client.table("profiles").select("id, is_admin") \
                    .eq("email", ADMIN_EMAIL).execute()
        if res.data:
            if not res.data[0].get("is_admin"):
                client.table("profiles").update(
                    {"is_admin": True, "username": ADMIN_USERNAME, "name": ADMIN_NAME}
                ).eq("id", res.data[0]["id"]).execute()
            return True, "admin_exists"
        return False, "Admin not found — run SQL from DEPLOY.md to create it"
    except Exception as e:
        return False, f"Admin check: {e}"


def ensure_db() -> list[str]:
    """Run at app startup. Idempotently sets up schema + RPCs + admin."""
    if not _try_supabase():
        return ["⚡ Local mode — no DB init needed"]
    msgs = []
    try:
        client = _get_client()
        status = _ensure_tables(client)
        msgs.append(f"profiles: {'✅' if status.get('profiles') else '⚠ missing'}")
        msgs.append(f"portfolios: {'✅' if status.get('portfolios') else '⚠ missing'}")
        ok, msg = _seed_admin(client)
        msgs.append(f"admin: {'✅' if ok else '⚠'} {msg}")
    except Exception as e:
        msgs.append(f"DB init warning: {e}")
    return msgs


# ─────────────────────────────────────────────────────────────────────
# PORTFOLIO — use SECURITY DEFINER RPCs to bypass RLS completely
# ─────────────────────────────────────────────────────────────────────

def save_portfolio_rpc(user_id: str, portfolio: dict) -> tuple[bool, str]:
    """
    Save portfolio via SECURITY DEFINER RPC — bypasses all RLS.
    This is the ONLY save path needed. Works regardless of token state.
    """
    try:
        import json
        client = _get_client()
        client.rpc("save_portfolio", {
            "p_user_id": user_id,
            "p_data":    portfolio,
        }).execute()
        return True, "Saved"
    except Exception as e:
        return False, str(e)


def load_portfolio_rpc(user_id: str) -> tuple[dict, str]:
    """Load portfolio via SECURITY DEFINER RPC."""
    try:
        client = _get_client()
        res = client.rpc("load_portfolio", {"p_user_id": user_id}).execute()
        data = res.data if res.data else {}
        if isinstance(data, str):
            import json
            data = json.loads(data)
        return data or {}, ""
    except Exception as e:
        return {}, str(e)


# ─────────────────────────────────────────────────────────────────────
# ADMIN HELPERS
# ─────────────────────────────────────────────────────────────────────

def admin_list_users(token: str) -> list[dict]:
    try:
        client = _get_client()
        client.postgrest.auth(token)
        try:
            res = client.rpc("admin_get_all_profiles").execute()
            if res.data is not None:
                return res.data
        except Exception:
            pass
        res = client.table("profiles") \
                    .select("id, username, name, email, is_admin, created_at") \
                    .order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return []


def admin_delete_user(token: str, user_id: str) -> tuple[bool, str]:
    """
    Fully deletes a user: portfolios + profiles + auth.users.
    Uses service_role_key to call Supabase Admin API for auth deletion.
    """
    try:
        client = _get_client()
        client.postgrest.auth(token)

        # Block deleting admin accounts
        try:
            res = client.table("profiles").select("is_admin").eq("id", user_id).single().execute()
            if res.data and res.data.get("is_admin"):
                return False, "Cannot delete the admin account"
        except Exception:
            pass

        # Step 1: delete portfolio
        try:
            client.table("portfolios").delete().eq("user_id", user_id).execute()
        except Exception:
            pass

        # Step 2: delete profile
        try:
            client.table("profiles").delete().eq("id", user_id).execute()
        except Exception:
            pass

        # Step 3: delete from auth.users via Admin API (requires service_role_key)
        try:
            _delete_auth_user(user_id)
            return True, "auth"   # signals full deletion to UI
        except ValueError:
            # service_role_key not configured
            return True, ("profile_only — add service_role_key to secrets.toml "
                          "to also delete login credentials")
        except Exception as auth_err:
            return True, f"profile_only — auth delete failed: {auth_err}"

    except Exception as e:
        return False, f"Delete error: {e}"


def admin_toggle_admin(token: str, user_id: str, make_admin: bool) -> tuple[bool, str]:
    try:
        client = _get_client()
        client.postgrest.auth(token)
        client.table("profiles").update({"is_admin": make_admin}).eq("id", user_id).execute()
        return True, "Updated"
    except Exception as e:
        return False, f"Update error: {e}"


def admin_get_user_portfolio(token: str, user_id: str) -> dict:
    data, _ = load_portfolio_rpc(user_id)
    return data


def admin_create_user(token: str, username: str, name: str,
                      email: str, password: str, is_admin: bool = False) -> tuple[bool, str]:
    from backend.auth import _sb_register
    ok, msg = _sb_register(username, name, email, password)
    if ok and is_admin:
        try:
            client = _get_client()
            client.postgrest.auth(token)
            client.table("profiles").update({"is_admin": True}).eq("email", email).execute()
        except Exception:
            pass
    return ok, msg
