-- ══════════════════════════════════════════════════════════════════════
-- Nifty 50 Analyzer — Supabase Setup SQL
-- ══════════════════════════════════════════════════════════════════════
-- Paste this entire file into:
--   Supabase Dashboard → SQL Editor → New Query → Run
-- ══════════════════════════════════════════════════════════════════════


-- ── 1. Profiles table ─────────────────────────────────────────────────
-- Extends Supabase auth.users with username + display name.
-- id = same UUID as auth.users so they join seamlessly.

CREATE TABLE IF NOT EXISTS profiles (
  id          UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
  username    TEXT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  email       TEXT,
  is_admin    BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Row Level Security: users can only see/edit their own profile
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "profiles_select_own"
  ON profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "profiles_insert_own"
  ON profiles FOR INSERT
  WITH CHECK (auth.uid() = id);

CREATE POLICY "profiles_update_own"
  ON profiles FOR UPDATE
  USING (auth.uid() = id);


-- ── 2. Portfolios table ────────────────────────────────────────────────
-- One JSONB blob per user. Upserted on every portfolio change.
-- Structure of 'data' column:
--   {
--     "RELIANCE": {
--       "symbol": "RELIANCE", "sector": "Energy",
--       "qty": 50, "avg_buy_price": 1320.0,
--       "lots": [{"date":"2025-01-15","qty":30,"price":1280.0}, ...]
--     },
--     ...
--   }

CREATE TABLE IF NOT EXISTS portfolios (
  id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  data        JSONB NOT NULL DEFAULT '{}',
  updated_at  TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id)
);

-- Row Level Security: users can only manage their own portfolio
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;

CREATE POLICY "portfolios_all_own"
  ON portfolios FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);


-- ── 3. Auto-update updated_at on portfolio changes ─────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS portfolios_updated_at ON portfolios;
CREATE TRIGGER portfolios_updated_at
  BEFORE UPDATE ON portfolios
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();


-- ── 4. Helper: check username availability (called before sign-up) ──────
-- This is a public function (no auth needed) so the sign-up form
-- can check if a username is already taken before creating the account.

CREATE OR REPLACE FUNCTION is_username_available(uname TEXT)
RETURNS BOOLEAN
LANGUAGE sql STABLE
AS $$
  SELECT NOT EXISTS (
    SELECT 1 FROM profiles WHERE username = lower(uname)
  );
$$;

-- Grant execute to anon and authenticated roles
GRANT EXECUTE ON FUNCTION is_username_available TO anon, authenticated;


-- ── 5. Verify setup ────────────────────────────────────────────────────
SELECT
  table_name,
  (SELECT count(*) FROM information_schema.columns
   WHERE table_name = t.table_name
   AND table_schema = 'public') AS column_count
FROM information_schema.tables t
WHERE table_schema = 'public'
  AND table_name IN ('profiles', 'portfolios')
ORDER BY table_name;

-- Expected output:
--  table_name  | column_count
-- -------------+--------------
--  portfolios  |      4
--  profiles    |      4
