# 📊 Nifty 50 Market Analyzer

Real NSE data · ML ensemble prediction · News sentiment · No API key
live link - https://niftyanalyzertop50vb2.streamlit.app/

## Project Structure

```
nifty50_pro/
├── app.py                  ← Entry point (orchestration only)
├── requirements.txt
├── README.md
├── .streamlit/
│   └── config.toml         ← Dark theme
├── backend/
│   ├── __init__.py
│   ├── constants.py        ← Stock universe, sector maps, RSS feeds, word lists
│   ├── data.py             ← yfinance fetch + RSI, MACD, Bollinger, etc.
│   └── ml.py               ← RandomForest + GradientBoosting + Ridge ensemble + sentiment
├── frontend/
│   ├── __init__.py
│   ├── styles.py           ← Full CSS design system (Space Mono + DM Sans)
│   └── components.py       ← All reusable HTML components
└── pipeline/
    ├── __init__.py
    └── report.py           ← Excel workbook (4 sheets)
```

## Features

- **Top Gainers** — stocks with highest return in your date range
- **Top Losers** — stocks with biggest decline in your date range
- **AI Predictions** — ML ensemble scores every stock for buy potential
- **News Sentiment** — scraped from free RSS feeds, no API key
- **Excel Report** — one-click download with Gainers / Losers / Predictions / Summary

## How it works

### Data
`yfinance` downloads daily OHLCV for all 50 Nifty stocks.
- `change_pct` = `(last_close - first_close) / first_close * 100`
- Period High = `df["High"].max()` over the range
- Period Low  = `df["Low"].min()` over the range

### ML Model
Three models trained on 9 technical features:
- RSI(14), MACD cross, Bollinger Band position, period range position
- Period return, 5-day momentum, volume ratio, volatility, sector score

Ensemble: **RF 40% + GB 40% + Ridge 20%** → normalised to 0–100

### News Sentiment
Scraped from free RSS feeds (ET Markets, Moneycontrol, Dow Jones).
Simple positive/negative word matching → score −1 to +1.
Final score = `ML * 0.80 + sentiment_boost * 0.20`

### Caching
`@st.cache_data(ttl=3600)` on every yfinance call — works across all
Streamlit Cloud workers. Same date range = identical results every time.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. New app → select repo → `app.py` → Deploy

⚠ **Disclaimer**: For educational purposes only. Not financial advice.
