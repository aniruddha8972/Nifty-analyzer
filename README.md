# 📊 Nifty 50 Market Analyzer

A production-grade, ML-powered market intelligence platform for the **Nifty 50** index, built with Streamlit. Supports multi-user authentication, live portfolio tracking, AI predictions, backtesting, correlation analysis, and an admin dashboard — all in a dark terminal aesthetic.

> ⚠ **Not financial advice.** For educational purposes only.

---

## Features

| Tab | Description |
|---|---|
| 📈 Top Gainers | Top 10 gainers with price cards and movers table |
| 📉 Top Losers | Top 10 losers with price cards and movers table |
| 🤖 AI Predictions | RF + GB + Ridge ensemble · news sentiment · BUY/HOLD/SELL signals |
| 📋 All Stocks | Full Nifty 50 table sorted by daily return |
| 💼 My Portfolio | Add/remove holdings, live P&L, ML advisor, import/export JSON |
| 🗺 Heatmap | Sector heatmap with treemap and sector summary cards |
| 📊 Backtest | Strategy backtester with performance metrics and equity curve |
| 🔗 Correlations | Portfolio and market correlation matrix |
| 📅 Events | Corporate events calendar (earnings, ex-dividends, splits) |
| 🛡 Admin | User management, portfolio viewer, admin tools *(admin only)* |

---

## Tech Stack

```
Streamlit          — UI framework
yfinance           — Market data (OHLCV, live prices)
scikit-learn       — ML ensemble (RandomForest + GradientBoosting + Ridge)
pandas / numpy     — Data processing
plotly             — Interactive charts
openpyxl           — Excel report generation (4-sheet workbook)
Supabase           — Auth, user profiles, portfolio persistence (optional)
BeautifulSoup      — RSS news sentiment scraping
```

---

## Project Structure

```
nifty50_pro/
│
├── app.py                         # Entry point — orchestration only
│
├── backend/
│   ├── auth.py                    # Auth: register, login, password validation,
│   │                              #   portfolio save/load (Supabase + local)
│   ├── constants.py               # Stock universe (50 tickers), sector map,
│   │                              #   sentiment word lists, RSS feeds
│   ├── data.py                    # yfinance fetch, OHLCV, technical indicators
│   │                              #   (RSI, MACD, Bollinger, ATR, OBV…)
│   ├── ml.py                      # ML ensemble + news sentiment pipeline
│   │                              #   RF 40% + GB 40% + Ridge 20%
│   ├── portfolio.py               # P&L computation, live prices, ML advisor,
│   │                              #   add/remove/update holdings, import/export
│   ├── analytics.py               # Heatmap, backtest, correlation helpers
│   ├── db_init.py                 # Supabase table setup, SECURITY DEFINER RPCs,
│   │                              #   Admin API user delete, ensure_db()
│   ├── db_setup.py                # Legacy DB bootstrap (compat shim)
│   └── __init__.py
│
├── frontend/
│   ├── styles.py                  # Global CSS design system (IBM Plex Mono / Inter,
│   │                              #   dark palette, all Streamlit overrides)
│   ├── auth_page.py               # Login + Register UI, live password strength meter
│   ├── components.py              # Reusable HTML components (stat bars, cards,
│   │                              #   section headers, tables)
│   ├── portfolio_components.py    # Portfolio tab: summary, holdings table,
│   │                              #   add form, manage panel, advice cards, I/O
│   ├── analytics_components.py    # Heatmap, Backtest, Correlation, Events tabs
│   ├── admin_dashboard.py         # Admin dashboard: user list, delete, toggle admin,
│   │                              #   create user, view portfolios
│   └── __init__.py
│
├── pipeline/
│   ├── report.py                  # Excel workbook generator (Summary, Holdings,
│   │                              #   P&L, Predictions — 4 sheets)
│   └── __init__.py
│
├── agents/
│   ├── test_agent.py              # Auth pipeline tests (44 tests)
│   ├── test_admin.py              # Admin operations tests (44 tests)
│   ├── test_portfolio.py          # Portfolio tests (43 tests)
│   ├── test_analytics.py          # Analytics tests (46 tests)
│   ├── test_password.py           # Password policy + update tests (42 tests)
│   └── bug_fixer.py               # Automated bug detection utility
│
├── data/                          # Local-mode persistence (git-ignored)
│   ├── users.json                 # SHA-256 hashed user accounts
│   └── portfolios/
│       └── <username>.json        # Per-user portfolio JSON
│
├── .streamlit/
│   ├── config.toml                # Theme: dark, CORS off, XSRF on
│   └── secrets.toml               # ← NOT committed (see Secrets section)
│
├── requirements.txt
└── README.md
```

---

## Authentication

The app supports **two modes** selected automatically:

| Mode | When active | Storage |
|---|---|---|
| ☁ **Supabase** | `secrets.toml` has `[supabase]` section | Supabase Auth + PostgreSQL |
| ⚡ **Local** | No Supabase secrets | `data/users.json` + file system |

Both modes support the full feature set. Supabase mode is recommended for production.

### Password Policy

All passwords (registration and change-password) must satisfy **all 5 rules**:

- Minimum **8 characters**
- At least one **uppercase letter** (A–Z)
- At least one **lowercase letter** (a–z)
- At least one **number** (0–9)
- At least one **special character** (`!@#$%^&*()_+-=[]{}|;:,./<>?`)

A live strength meter (Weak → Fair → Strong) with a colour bar is shown as the user types.

---

## Setup

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd nifty50_pro
pip install -r requirements.txt
```

### 2. Secrets

Create `.streamlit/secrets.toml`:

```toml
[supabase]
url              = "https://YOUR_PROJECT.supabase.co"
anon_key         = "eyJ..."    # Project Settings → API → anon public
service_role_key = "eyJ..."    # Project Settings → API → service_role
```

> `service_role_key` is required for full user deletion (removes from `auth.users`).
> Without it, profile + portfolio are deleted but the auth account remains.
> In local mode, omit the entire `[supabase]` section.

### 3. Supabase Setup (Cloud mode only)

Run `SUPABASE_FULL_SETUP.sql` once in the **Supabase SQL Editor**.

What it does:
1. Creates `profiles` and `portfolios` tables
2. Sets fully-open RLS policies (security enforced via SECURITY DEFINER RPCs)
3. Creates `save_portfolio` and `load_portfolio` SECURITY DEFINER RPCs
4. Creates `admin_get_all_profiles`, `admin_delete_user_full`, `is_username_available` RPCs
5. Seeds the admin account (skips if already exists)
6. Backfills missing emails

### 4. Run

```bash
streamlit run app.py
```

---

## Admin Account

| Field | Value |
|---|---|
| Name | Aniruddha Giri |
| Email | girianiruddha8972@gmail.com |
| Username | admin |
| Password | *(set during Supabase seed or first local registration)* |

Admin users see an extra **🛡 Admin** tab with:
- Full user list with join date and portfolio count
- Toggle admin/user role
- Delete user (removes profile + portfolio + auth account)
- Create new user
- View any user's portfolio

---

## ML Pipeline

The AI Predictions tab uses a **3-model ensemble** trained on real OHLCV data:

```
Input features (17 total):
  Technical (8):   RSI, MACD signal, Bollinger %B, ATR%, OBV change,
                   return_5d, return_20d, volatility_20d
  Sentiment (7):   Positive/negative word counts from RSS headlines,
                   net sentiment, sector bias, volume-weighted scores
  Market (2):      Nifty 50 relative return, beta proxy

Models:
  RandomForest      40% weight
  GradientBoosting  40% weight
  Ridge Regression  20% weight

Target: actual 10-day forward return
Training: 50 stocks × 3 years daily OHLCV (~36,500 rows)
```

Signals: **STRONG BUY / BUY / HOLD / SELL / STRONG SELL**

---

## Portfolio Features

- Add holdings with symbol, quantity, buy price, and buy date
- Live price fetch via yfinance (cached 5 min)
- P&L: current value, unrealised gain/loss, XIRR (annualised return)
- **💾 Save** — explicit persist to Supabase / local file
- **🔄 Refresh** — reload from Supabase into session
- Last synced timestamp shown after every save/refresh
- ML advisor: per-stock BUY/SELL signal overlay on your holdings
- Export portfolio as JSON / import from JSON
- Download Excel report (4 sheets: Summary, Holdings, P&L, Predictions)

---

## Change Password

Users can update their password from the **🔑 Change Password** expander in the sidebar:

1. Enter current password (verified before any change)
2. Enter and confirm new password
3. Live strength meter enforces the password policy
4. New password must differ from current

Works in both Supabase and local mode.

---

## Test Suite

219 tests across 5 agents — run all:

```bash
python agents/test_agent.py       # 44 tests — auth pipelines
python agents/test_admin.py       # 44 tests — admin operations
python agents/test_portfolio.py   # 43 tests — portfolio CRUD + P&L
python agents/test_analytics.py   # 46 tests — heatmap, backtest, correlation
python agents/test_password.py    # 42 tests — password policy + update flow
```

Expected: **219/219 ✅ ALL PASS**

---

## Deployment (Streamlit Cloud)

1. Push repo to GitHub (exclude `data/`, `.streamlit/secrets.toml`)
2. Connect repo in [share.streamlit.io](https://share.streamlit.io)
3. Set **Secrets** in Streamlit Cloud → App Settings → Secrets (paste `secrets.toml` content)
4. Main file: `app.py`
5. Run `SUPABASE_FULL_SETUP.sql` in Supabase SQL Editor before first launch

**Live URL:** https://niftyanalyzertop50vb2.streamlit.app/

---

## `.gitignore` Recommendations

```gitignore
.streamlit/secrets.toml
data/users.json
data/portfolios/
__pycache__/
*.pyc
.env
```

---

## Requirements

```
streamlit>=1.32.0
yfinance>=0.2.40
pandas>=2.0.0
numpy>=1.26.0
scikit-learn>=1.3.0
openpyxl>=3.1.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
supabase>=2.3.0,<3.0.0
plotly>=5.18.0
matplotlib>=3.7.0
```

---

*Built with Streamlit · Data from Yahoo Finance · Not financial advice*
