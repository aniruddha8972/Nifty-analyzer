# Deployment Guide — Nifty 50 Analyzer

This app runs in two modes:
- **☁ Supabase Mode** — persistent cloud database, works across devices, survives redeployments
- **⚡ Local Mode** — no setup needed, data lives in JSON files until server restarts

---

## Option A — Deploy to Streamlit Cloud + Supabase (Recommended)

### Step 1 — Set up Supabase (free)

1. Go to [supabase.com](https://supabase.com) → **Start for free**
2. Create a new project (note your project password)
3. Wait ~2 minutes for the project to provision

### Step 2 — Run the SQL setup

1. In Supabase Dashboard → **SQL Editor** → **New Query**
2. Paste the entire contents of `supabase_setup.sql`
3. Click **Run** — you should see:

   ```
   table_name  | column_count
   ------------+--------------
   portfolios  |      4
   profiles    |      4
   ```

### Step 3 — Disable email confirmation (optional but recommended for testing)

1. Supabase Dashboard → **Authentication** → **Providers** → **Email**
2. Toggle off **Confirm email** (so users can log in immediately after registration)
3. Click **Save**

### Step 4 — Get your API keys

1. Supabase Dashboard → **Project Settings** → **API**
2. Copy:
   - **Project URL** → looks like `https://abcdefgh.supabase.co`
   - **anon / public key** → long JWT string starting with `eyJ...`

### Step 5 — Deploy to Streamlit Cloud

1. Push your code to GitHub (make sure `secrets.toml` is in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Connect your GitHub repo → set main file: `app.py`
4. Click **Advanced settings** → **Secrets** → paste:

   ```toml
   [supabase]
   url      = "https://YOUR_PROJECT_ID.supabase.co"
   anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
   ```

5. Click **Deploy**

---

## Option B — Run Locally with Supabase

1. Create `.streamlit/secrets.toml`:
   ```toml
   [supabase]
   url      = "https://YOUR_PROJECT_ID.supabase.co"
   anon_key = "eyJ..."
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run:
   ```bash
   streamlit run app.py
   ```

---

## Option C — Run Locally without Supabase (Local JSON mode)

No setup needed. Just:
```bash
pip install -r requirements.txt
streamlit run app.py
```

Data is stored in `data/users.json` and `data/portfolios/` until the server restarts.
The app shows **⚡ Local Mode** badge on the login page.

---

## Supabase Free Tier Limits

| Resource       | Free Tier Limit     | Sufficient for?          |
|----------------|---------------------|--------------------------|
| Database       | 500 MB PostgreSQL   | ~50,000 users easily     |
| Auth users     | Unlimited           | ✓                        |
| API requests   | 500,000 / month     | ✓ for personal use       |
| Storage        | 1 GB                | ✓ (no files stored)      |
| Project pauses | After 1 week idle   | Reactivate in dashboard  |

> **Note:** Free Supabase projects pause after 1 week of inactivity.
> You'll get an email — just click "Restore project" to reactivate in seconds.

---

## Database Tables

### `profiles`
| Column     | Type        | Description                    |
|------------|-------------|--------------------------------|
| id         | UUID        | = auth.users.id (primary key)  |
| username   | TEXT        | unique display handle          |
| name       | TEXT        | full name                      |
| created_at | TIMESTAMPTZ | auto-set on insert             |

### `portfolios`
| Column     | Type        | Description                          |
|------------|-------------|--------------------------------------|
| id         | UUID        | auto-generated                       |
| user_id    | UUID        | references auth.users, UNIQUE        |
| data       | JSONB       | entire portfolio as JSON blob        |
| updated_at | TIMESTAMPTZ | auto-updated on every save           |

Row Level Security (RLS) is enabled — users can only read/write their own rows.

---

## Security Notes

- Passwords are managed entirely by Supabase Auth (bcrypt hashed internally)
- In local mode, passwords are SHA-256 hashed in `data/users.json`
- Never commit `secrets.toml` to git (it's in `.gitignore`)
- The Supabase `anon_key` is safe to use client-side — RLS enforces row-level isolation
