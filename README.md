---
title: NSE Market Analyzer
emoji: 📊
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.32.0
app_file: app.py
pinned: false
license: mit
---

# NSE Market Analyzer

Quantitative ML-powered analytics for NSE/BSE Indian equity markets.

## Features
- 500+ stocks across Nifty 50, Nifty Next 50, Nifty 100, Nifty 200, Nifty 500
- ML ensemble predictions (Random Forest + Gradient Boosting + Ridge)
- Live news sentiment analysis
- Portfolio tracker with live P&L
- Heatmap, backtest, correlation, events, index charts
- Supabase auth with magic-link email verification

## Setup (Hugging Face Spaces)

### 1. Add Repository Secrets
Go to **Space Settings → Repository secrets** and add:

| Secret Name | Where to find it |
|---|---|
| `SUPABASE_URL` | Supabase Dashboard → Project Settings → API → Project URL |
| `SUPABASE_ANON_KEY` | Supabase Dashboard → Project Settings → API → anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Project Settings → API → service_role key |
| `APP_URL` | Your HF Space URL e.g. `https://your-name-nse-market-analyzer.hf.space` |

### 2. Supabase Redirect URL
In **Supabase Dashboard → Authentication → URL Configuration**, add your Space URL to **Redirect URLs**:
```
https://your-name-nse-market-analyzer.hf.space
```

### 3. Database
On first run the app auto-creates required tables. Or run `SUPABASE_FULL_SETUP.sql` manually in the Supabase SQL editor.

## Local Development
```bash
pip install -r requirements.txt
# Add .streamlit/secrets.toml (see template below)
streamlit run app.py
```

secrets.toml template:
```toml
[supabase]
url              = "https://YOUR_PROJECT.supabase.co"
anon_key         = "eyJ..."
service_role_key = "eyJ..."

[app]
url = "http://localhost:8501"
```

## Disclaimer
Not financial advice. Educational use only.
