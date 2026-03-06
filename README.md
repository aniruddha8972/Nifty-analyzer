# 📊 Nifty 50 Market Analyzer

A full-stack market analysis tool for Nifty 50 stocks with a custom date range picker,
internal AI scoring model, and one-click Excel report export.

**Live on:** [Streamlit Cloud](https://share.streamlit.io) (free)

---

## 🗂️ Project Structure

```
nifty50_analyzer/
├── app.py                        ← Streamlit entry point
├── requirements.txt              ← Python dependencies
├── .streamlit/
│   └── config.toml               ← Dark theme + server config
│
├── backend/                      ← Data + AI layer
│   ├── __init__.py
│   ├── data_engine.py            ← Stock data generation (swap for real API)
│   └── ai_model.py               ← 9-factor scoring model (0–100)
│
├── frontend/                     ← UI components
│   ├── __init__.py
│   └── components.py             ← CSS injection + HTML card renderers
│
├── pipeline/                     ← Report generation
│   ├── __init__.py
│   └── report_generator.py       ← 4-sheet formatted Excel export
│
└── tests/                        ← Unit tests
    └── test_backend.py           ← 20+ tests for engine + model + report
```

---

## 🚀 Deploy to Streamlit Cloud (Free — 5 minutes)

### Step 1 — Push to GitHub
```bash
# Create a new GitHub repo, then:
git init
git add .
git commit -m "Initial commit: Nifty 50 Analyzer"
git remote add origin https://github.com/YOUR_USERNAME/nifty50-analyzer.git
git push -u origin main
```

### Step 2 — Connect to Streamlit Cloud
1. Go to **[share.streamlit.io](https://share.streamlit.io)**
2. Sign in with GitHub
3. Click **"New app"**
4. Select your repo → branch: `main` → main file: `app.py`
5. Click **"Deploy!"**

Your app will be live at:
```
https://YOUR_USERNAME-nifty50-analyzer-app-XXXX.streamlit.app
```

That's it. Free hosting, auto-deploys on every `git push`.

---

## 💻 Run Locally

```bash
# 1. Clone / unzip the project
cd nifty50_analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
streamlit run app.py
```

Opens at `http://localhost:8501`

---

## 🧪 Run Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## ⚙️ Features

| Feature | Detail |
|---|---|
| **Date Presets** | Last Week, 2W, 1M, 3M, 6M, 1Y, YTD |
| **Custom Range** | Any From → To date in the past |
| **Data** | All 50 Nifty stocks, OHLCV + metrics |
| **AI Model** | 9-factor internal scoring (0–100), no API key |
| **Recommendations** | Strong Buy / Buy / Hold / Sell / Strong Sell |
| **Risk Levels** | Low / Medium / Med-High / High |
| **Excel Export** | 4-sheet .xlsx: Gainers, Losers, AI Analysis, Summary |

---

## 🤖 AI Scoring Model

Each stock is scored 0–100 across 9 independent factors:

| Factor | Signal | Impact |
|---|---|---|
| RSI | < 35 oversold | +15 pts |
| RSI | > 70 overbought | -15 pts |
| Period Momentum | Strong gain (scales with period) | +4 to +13 pts |
| 52W Range | Near 52W low | +14 pts |
| 52W Range | Near 52W high | -11 pts |
| Volume | > 1.6× average | +9 pts |
| P/E Ratio | < 12 deeply undervalued | +10 pts |
| P/E Ratio | > 55 very expensive | -9 pts |
| Beta | < 0.65 defensive | +6 pts |
| Beta | > 1.5 volatile | -6 pts |
| Dividend Yield | > 2.5% | +6 pts |
| Sector | FMCG/Pharma/IT/Healthcare | +3 pts |
| Mean Reversion | 60+ day period + decline > 5% | +4 pts |

**Score thresholds:**
- `≥ 72` → STRONG BUY
- `58–71` → BUY
- `43–57` → HOLD
- `29–42` → SELL
- `≤ 28` → STRONG SELL

---

## 🔌 Plugging in Real Data

The data engine (`backend/data_engine.py`) uses deterministic simulation by default.
To use live NSE data, replace the body of `generate_stock()` with your broker API:

```python
# Example with Zerodha Kite Connect
from kiteconnect import KiteConnect

kite = KiteConnect(api_key="YOUR_API_KEY")

def generate_stock(symbol, from_date, to_date):
    hist = kite.historical_data(
        instrument_token = INSTRUMENT_TOKENS[symbol],
        from_date        = from_date,
        to_date          = to_date,
        interval         = "day",
    )
    # Map hist → StockData(...)
```

The rest of the app (AI model, UI, export) works unchanged.

---

## ⚠️ Disclaimer

This tool uses **simulated data** and is for **educational/informational purposes only**.
It does **not** constitute financial advice. Always consult a SEBI-registered investment
advisor before making investment decisions.

---

## 📄 License

MIT
