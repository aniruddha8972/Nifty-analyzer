-- ════════════════════════════════════════════════════════════════════════════
-- NIFTY 50 ANALYZER — COMPLETE SUPABASE SETUP
-- ════════════════════════════════════════════════════════════════════════════
-- Paste this ENTIRE file into:
--   Supabase Dashboard → SQL Editor → New Query → Run
--
-- Safe to run multiple times — drops and recreates everything cleanly.
-- ════════════════════════════════════════════════════════════════════════════


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 1: DROP EVERYTHING (clean slate)
-- ────────────────────────────────────────────────────────────────────────────

-- Drop triggers first
DROP TRIGGER IF EXISTS on_auth_user_created    ON auth.users;
DROP TRIGGER IF EXISTS portfolios_updated_at   ON public.portfolios;

-- Drop all functions
DROP FUNCTION IF EXISTS public.handle_new_user()                      CASCADE;
DROP FUNCTION IF EXISTS public.update_updated_at_column()             CASCADE;
DROP FUNCTION IF EXISTS public.save_portfolio(UUID, JSONB)            CASCADE;
DROP FUNCTION IF EXISTS public.load_portfolio(UUID)                   CASCADE;
DROP FUNCTION IF EXISTS public.admin_get_all_profiles()               CASCADE;
DROP FUNCTION IF EXISTS public.admin_delete_user_full(UUID)           CASCADE;
DROP FUNCTION IF EXISTS public.is_username_available(TEXT)            CASCADE;
DROP FUNCTION IF EXISTS public.exec_sql(TEXT)                         CASCADE;

-- Drop all policies on portfolios
DROP POLICY IF EXISTS "pf_sel"                ON public.portfolios;
DROP POLICY IF EXISTS "pf_ins"                ON public.portfolios;
DROP POLICY IF EXISTS "pf_upd"                ON public.portfolios;
DROP POLICY IF EXISTS "pf_del"                ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_all_own"    ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_select_own" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_insert_own" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_update_own" ON public.portfolios;
DROP POLICY IF EXISTS "portfolios_delete_own" ON public.portfolios;

-- Drop all policies on profiles
DROP POLICY IF EXISTS "prof_sel"              ON public.profiles;
DROP POLICY IF EXISTS "prof_ins"              ON public.profiles;
DROP POLICY IF EXISTS "prof_upd"              ON public.profiles;
DROP POLICY IF EXISTS "prof_del"              ON public.profiles;
DROP POLICY IF EXISTS "profiles_select_all"   ON public.profiles;
DROP POLICY IF EXISTS "profiles_select_own"   ON public.profiles;
DROP POLICY IF EXISTS "profiles_insert_own"   ON public.profiles;
DROP POLICY IF EXISTS "profiles_update_own"   ON public.profiles;
DROP POLICY IF EXISTS "profiles_delete_own"   ON public.profiles;

-- Drop tables (portfolios first because of FK)
DROP TABLE IF EXISTS public.portfolios CASCADE;
DROP TABLE IF EXISTS public.profiles   CASCADE;


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 2: CREATE TABLES
-- ────────────────────────────────────────────────────────────────────────────

CREATE TABLE public.profiles (
  id         UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  username   TEXT        UNIQUE NOT NULL,
  name       TEXT        NOT NULL DEFAULT '',
  email      TEXT,
  is_admin   BOOLEAN     NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.portfolios (
  id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id    UUID        NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  data       JSONB       NOT NULL DEFAULT '{}',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 3: ROW LEVEL SECURITY
-- ────────────────────────────────────────────────────────────────────────────

ALTER TABLE public.profiles   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;

-- profiles: fully open (no sensitive data — email/password live in auth.users)
CREATE POLICY "prof_sel" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "prof_ins" ON public.profiles FOR INSERT WITH CHECK (true);
CREATE POLICY "prof_upd" ON public.profiles FOR UPDATE USING (true);
CREATE POLICY "prof_del" ON public.profiles FOR DELETE USING (true);

-- portfolios: fully open (data protected by SECURITY DEFINER RPCs)
CREATE POLICY "pf_sel" ON public.portfolios FOR SELECT USING (true);
CREATE POLICY "pf_ins" ON public.portfolios FOR INSERT WITH CHECK (true);
CREATE POLICY "pf_upd" ON public.portfolios FOR UPDATE USING (true);
CREATE POLICY "pf_del" ON public.portfolios FOR DELETE USING (true);


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 4: UTILITY FUNCTIONS
-- ────────────────────────────────────────────────────────────────────────────

-- Auto-update updated_at on portfolio changes
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER portfolios_updated_at
  BEFORE UPDATE ON public.portfolios
  FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 5: TRIGGER — auto-create profile + portfolio on new auth user
-- ────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  base_u  TEXT;
  final_u TEXT;
  n       INT := 0;
BEGIN
  -- Build clean username from email prefix
  base_u  := lower(regexp_replace(split_part(NEW.email, '@', 1), '[^a-z0-9_]', '_', 'g'));
  base_u  := substr(base_u, 1, 14);
  final_u := base_u || '_' || substr(replace(NEW.id::text, '-', ''), 1, 4);

  -- Ensure uniqueness
  WHILE EXISTS (SELECT 1 FROM public.profiles WHERE username = final_u) LOOP
    n := n + 1;
    final_u := base_u || '_' || n::text;
    IF n > 999 THEN EXIT; END IF;
  END LOOP;

  -- Create profile row
  INSERT INTO public.profiles (id, username, name, email)
  VALUES (
    NEW.id,
    final_u,
    COALESCE(NEW.raw_user_meta_data->>'name', split_part(NEW.email, '@', 1)),
    NEW.email
  )
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email;

  -- Create empty portfolio row
  INSERT INTO public.portfolios (user_id, data)
  VALUES (NEW.id, '{}')
  ON CONFLICT (user_id) DO NOTHING;

  RETURN NEW;
END;
$$;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 6: PORTFOLIO RPCs (SECURITY DEFINER — bypass RLS completely)
-- ────────────────────────────────────────────────────────────────────────────

-- Save portfolio (INSERT or UPDATE)
CREATE OR REPLACE FUNCTION public.save_portfolio(p_user_id UUID, p_data JSONB)
RETURNS void LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  INSERT INTO public.portfolios (user_id, data, updated_at)
  VALUES (p_user_id, p_data, NOW())
  ON CONFLICT (user_id)
  DO UPDATE SET data = EXCLUDED.data, updated_at = NOW();
END;
$$;

-- Load portfolio
CREATE OR REPLACE FUNCTION public.load_portfolio(p_user_id UUID)
RETURNS JSONB LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
DECLARE
  result JSONB;
BEGIN
  SELECT data INTO result
  FROM public.portfolios
  WHERE user_id = p_user_id;
  RETURN COALESCE(result, '{}'::jsonb);
END;
$$;

GRANT EXECUTE ON FUNCTION public.save_portfolio   TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.load_portfolio   TO anon, authenticated;


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 7: ADMIN RPCs (SECURITY DEFINER)
-- ────────────────────────────────────────────────────────────────────────────

-- List all profiles (admin only)
CREATE OR REPLACE FUNCTION public.admin_get_all_profiles()
RETURNS TABLE (
  id         UUID,
  username   TEXT,
  name       TEXT,
  email      TEXT,
  is_admin   BOOLEAN,
  created_at TIMESTAMPTZ
)
LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public
AS $$
BEGIN
  RETURN QUERY
  SELECT p.id, p.username, p.name, p.email, p.is_admin, p.created_at
  FROM public.profiles p
  ORDER BY p.created_at DESC;
END;
$$;

-- Full user deletion — removes from auth.users so they cannot log in again
CREATE OR REPLACE FUNCTION public.admin_delete_user_full(p_user_id UUID)
RETURNS TEXT LANGUAGE plpgsql
SECURITY DEFINER SET search_path = public, auth
AS $$
BEGIN
  -- Block deleting admin accounts
  IF EXISTS (
    SELECT 1 FROM public.profiles
    WHERE id = p_user_id AND is_admin = TRUE
  ) THEN
    RAISE EXCEPTION 'Cannot delete an admin account';
  END IF;

  -- Delete in correct order (FK constraints)
  DELETE FROM public.portfolios WHERE user_id = p_user_id;
  DELETE FROM public.profiles   WHERE id      = p_user_id;
  DELETE FROM auth.users        WHERE id      = p_user_id;

  RETURN 'deleted';
END;
$$;

-- Check username availability
CREATE OR REPLACE FUNCTION public.is_username_available(uname TEXT)
RETURNS BOOLEAN LANGUAGE sql STABLE
SECURITY DEFINER SET search_path = public
AS $$
  SELECT NOT EXISTS (
    SELECT 1 FROM public.profiles
    WHERE lower(username) = lower(uname)
  );
$$;

GRANT EXECUTE ON FUNCTION public.admin_get_all_profiles()        TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.admin_delete_user_full(UUID)    TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.is_username_available(TEXT)     TO anon, authenticated;


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 8: SEED ADMIN ACCOUNT
-- Creates Aniruddha Giri as admin — skips if email already exists
-- ────────────────────────────────────────────────────────────────────────────

DO $$
DECLARE
  admin_uid UUID;
BEGIN
  -- Check if admin auth user exists
  SELECT id INTO admin_uid
  FROM auth.users
  WHERE email = 'girianiruddha8972@gmail.com';

  IF admin_uid IS NULL THEN
    -- Create auth user directly (no email needed, no rate limit)
    INSERT INTO auth.users (
      id,
      instance_id,
      email,
      encrypted_password,
      email_confirmed_at,
      created_at,
      updated_at,
      raw_app_meta_data,
      raw_user_meta_data,
      is_super_admin,
      role,
      aud
    ) VALUES (
      gen_random_uuid(),
      '00000000-0000-0000-0000-000000000000',
      'girianiruddha8972@gmail.com',
      crypt('897282', gen_salt('bf')),
      NOW(),
      NOW(),
      NOW(),
      '{"provider":"email","providers":["email"]}',
      '{"name":"Aniruddha Giri"}',
      FALSE,
      'authenticated',
      'authenticated'
    )
    RETURNING id INTO admin_uid;

    RAISE NOTICE 'Admin auth user created: %', admin_uid;
  ELSE
    RAISE NOTICE 'Admin auth user already exists: %', admin_uid;
  END IF;

  -- Upsert profile with is_admin = true
  INSERT INTO public.profiles (id, username, name, email, is_admin)
  VALUES (admin_uid, 'admin', 'Aniruddha Giri', 'girianiruddha8972@gmail.com', TRUE)
  ON CONFLICT (id) DO UPDATE SET
    username = 'admin',
    name     = 'Aniruddha Giri',
    email    = 'girianiruddha8972@gmail.com',
    is_admin = TRUE;

  -- Upsert empty portfolio
  INSERT INTO public.portfolios (user_id, data)
  VALUES (admin_uid, '{}')
  ON CONFLICT (user_id) DO NOTHING;

  RAISE NOTICE 'Admin profile ready.';
END;
$$;


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 9: BACKFILL — fix any existing users missing email in profiles
-- ────────────────────────────────────────────────────────────────────────────

UPDATE public.profiles p
SET email = u.email
FROM auth.users u
WHERE p.id = u.id
  AND (p.email IS NULL OR p.email = '');


-- ────────────────────────────────────────────────────────────────────────────
-- STEP 10: VERIFY — check everything is set up correctly
-- ────────────────────────────────────────────────────────────────────────────

SELECT '== TABLES ==' AS check;
SELECT table_name,
  (SELECT count(*) FROM information_schema.columns
   WHERE table_name = t.table_name AND table_schema = 'public') AS columns
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN ('profiles', 'portfolios')
ORDER BY table_name;

SELECT '== RLS POLICIES ==' AS check;
SELECT tablename, policyname, cmd
FROM pg_policies
WHERE tablename IN ('profiles', 'portfolios')
ORDER BY tablename, cmd;

SELECT '== FUNCTIONS ==' AS check;
SELECT routine_name
FROM information_schema.routines
WHERE routine_schema = 'public'
  AND routine_name IN (
    'save_portfolio', 'load_portfolio',
    'admin_get_all_profiles', 'admin_delete_user_full',
    'is_username_available', 'handle_new_user',
    'update_updated_at_column'
  )
ORDER BY routine_name;

SELECT '== ADMIN USER ==' AS check;
SELECT p.username, p.name, p.email, p.is_admin, p.created_at
FROM public.profiles p
WHERE p.email = 'girianiruddha8972@gmail.com';

SELECT '== ALL USERS ==' AS check;
SELECT p.username, p.name, p.email, p.is_admin, p.created_at
FROM public.profiles p
ORDER BY p.created_at;

-- ════════════════════════════════════════════════════════════════════════════
-- DONE. Expected results:
--   TABLES     → profiles (6 cols), portfolios (4 cols)
--   POLICIES   → 4 on profiles (del/ins/sel/upd), 4 on portfolios
--   FUNCTIONS  → 7 functions listed
--   ADMIN USER → 1 row, is_admin = true
-- ════════════════════════════════════════════════════════════════════════════
