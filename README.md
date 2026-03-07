# 📊 Nifty 50 Market Analyzer

> ML-powered market intelligence for all 50 Nifty stocks — real NSE data, ensemble predictions, live portfolio tracker, and news sentiment. No paid API key required.

🔴 **Live App** → [niftyanalyzertop50vb2.streamlit.app](https://niftyanalyzertop50vb2.streamlit.app/)

---

## ✨ Features

| Feature | Description |
|---|---|
| 📈 Top Gainers | Stocks with highest return in selected date range |
| 📉 Top Losers | Stocks with biggest decline in selected date range |
| 🤖 AI Predictions | 17-feature ML ensemble scores every stock 0–100 |
| 📋 All Stocks | Full table with technicals, signals, sentiment for all 50 |
| 💼 My Portfolio | Live P&L tracker with ML-driven buy/hold/sell advice |
| 📥 Excel Export | One-click download — Gainers / Losers / Predictions / Summary |
| 🔐 Auth System | Register + login with Supabase cloud or local JSON fallback |

---

## 🗂 Project Structure

```
nifty50_pro/
│
├── app.py                          ← Entry point — auth gate, tabs, sidebar, refresh
├── requirements.txt                ← All Python dependencies (pinned)
├── README.md
├── DEPLOY.md                       ← Step-by-step Supabase + Streamlit Cloud guide
├── supabase_setup.sql              ← Run once in Supabase SQL Editor to create tables
├── .gitignore                      ← Protects secrets.toml from being committed
│
├── .streamlit/
│   ├── config.toml                 ← Dark theme + CORS/XSRF security settings
│   └── secrets.toml                ← (gitignored) Supabase URL + anon key
│
├── backend/
│   ├── __init__.py
│   ├── auth.py                     ← Unified auth — Supabase cloud OR local JSON fallback
│   ├── constants.py                ← STOCKS dict (50 symbols), SECTOR_SCORE, RSS feeds, word lists
│   ├── data.py                     ← yfinance OHLCV fetch + 17-feature computation
│   ├── ml.py                       ← RF + GB + Ridge ensemble, sentiment proxies, predict()
│   └── portfolio.py                ← Add/remove holdings, live P&L, ML advisor, auto-persist
│
├── frontend/
│   ├── __init__.py
│   ├── auth_page.py                ← Login + Register UI — adapts to Supabase or local mode
│   ├── styles.py                   ← Full CSS design system (Space Mono + DM Sans, dark theme)
│   ├── components.py               ← Header, stat bar, gainer/loser cards, prediction table
│   └── portfolio_components.py     ← Portfolio summary, holdings DataFrame, add form, advisor cards
│
├── pipeline/
│   ├── __init__.py
│   └── report.py                   ← Excel workbook generator (4 sheets, news headlines)
│
└── agents/
    ├── bug_fixer.py                ← Auto-patches deprecated APIs + known bug patterns
    ├── test_agent.py               ← 44 tests across 8 suites (Auth, Portfolio, Data, ML, Excel…)
    └── run_agents.sh               ← Orchestrator: Bug Fixer → Tests → repeat until all pass
```

---

## 🧠 How It Works

### Data Pipeline
`yfinance` downloads daily OHLCV for all 50 Nifty stocks plus the `^NSEI` index.

```
fetch_ohlcv(symbol, start, end)  →  compute_stats()  →  17 features per stock
```

- `change_pct` = `(last_close − first_close) / first_close × 100`
- Period High/Low = `df["High"].max()` / `df["Low"].min()` over selected range
- Nifty index fetched separately for market-relative features

### ML Ensemble — 17 Features

**Technical (8):** `rsi`, `macd_cross`, `bb_pos`, `pos_in_range`, `mom5`, `vol_ratio`, `volatility`, `sector_score`

**Sentiment Proxies (7):** `overnight_gap`, `intraday_range`, `close_loc`, `vol_surge`, `news_event`, `sentiment_3d`, `big_gap_5d`

**Market-Relative (2):** `stock_vs_mkt`, `stock_rs5`

Training: ~35,000 rows (50 stocks × 3 years daily OHLCV). Ensemble weights: **RF 40% + GB 40% + Ridge 20%** → normalised to 0–100.

| Score | Signal |
|---|---|
| ≥ 72 | 🟢 STRONG BUY |
| ≥ 55 | 🟢 BUY |
| ≥ 35 | 🟡 HOLD |
| < 35 | 🔴 AVOID |

### Portfolio ML Advisor

Each holding gets a live advice label combining your P&L position with the ML signal:

| ML Signal | Your P&L | Advice |
|---|---|---|
| STRONG BUY | any | 🟢 BUY MORE |
| BUY | loss > −5% | 🟢 AVERAGE DOWN |
| BUY | profit / flat | 🟢 HOLD / ADD |
| HOLD | profit > 12% | 🟡 BOOK PARTIAL |
| HOLD | any | 🟡 HOLD |
| AVOID | profit > 5% | 🔴 BOOK PROFIT |
| AVOID | loss < −8% | 🔴 STOP LOSS |
| AVOID | small loss | 🟠 REDUCE |

### Auth System — Dual Mode

The app auto-detects which backend to use:

| Mode | When | Storage |
|---|---|---|
| ☁ Supabase Cloud | `secrets.toml` has `[supabase]` keys | PostgreSQL with RLS |
| ⚡ Local JSON | No secrets configured | `data/users.json` + `data/portfolios/` |

---

## 🚀 Run Locally

```bash
git clone <your-repo>
cd nifty50_pro
pip install -r requirements.txt
streamlit run app.py
```

App runs in **Local JSON mode** out of the box — no Supabase needed.

---

## ☁ Deploy to Streamlit Cloud + Supabase

See **[DEPLOY.md](./DEPLOY.md)** for the full step-by-step guide. Quick summary:

1. Create a free project at [supabase.com](https://supabase.com)
2. Run `supabase_setup.sql` in the Supabase SQL Editor
3. Copy your **Project URL** and **anon key** from Project Settings → API
4. Push code to GitHub (`.gitignore` already excludes `secrets.toml`)
5. Deploy on [share.streamlit.io](https://share.streamlit.io) and add secrets:

```toml
[supabase]
url      = "https://your-project.supabase.co"
anon_key = "eyJ..."
```

---

## 🤖 Production Agents

Run the quality pipeline before every deploy:

```bash
cd nifty50_pro
bash agents/run_agents.sh
```

This runs **Bug Fixer → Tests → Bug Fixer → Tests** (up to 3 iterations) until all 44 tests pass.

| Agent | What it does |
|---|---|
| `bug_fixer.py` | Auto-patches deprecated APIs, import errors, logic holes, security issues |
| `test_agent.py` | 44 tests — Syntax, Imports, Auth, Portfolio, Data, ML, Excel, Config/Security |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit 1.32+, custom CSS (Space Mono + DM Sans) |
| Data | yfinance, pandas, numpy |
| ML | scikit-learn (RandomForest, GradientBoosting, Ridge) |
| Auth & DB | Supabase (PostgreSQL + Auth) / local JSON fallback |
| Reports | openpyxl (4-sheet Excel workbook) |
| News | BeautifulSoup4, lxml, free RSS feeds |

---

## ⚠ Disclaimer

This app is for **educational purposes only**. Nothing here constitutes financial advice. Always consult a SEBI-registered investment advisor before making any investment decisions.
