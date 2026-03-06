import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import date, timedelta

st.set_page_config(page_title="Nifty 50 Analyzer", page_icon="📊", layout="wide")

# ── All 50 Nifty symbols with .NS suffix for Yahoo Finance ────────────────────
STOCKS = {
    "RELIANCE":"Energy",   "TCS":"IT",             "HDFCBANK":"Banking",
    "BHARTIARTL":"Telecom","ICICIBANK":"Banking",   "INFOSYS":"IT",
    "SBIN":"Banking",      "HINDUNILVR":"FMCG",     "ITC":"FMCG",
    "LICI":"Insurance",    "LT":"Infra",            "BAJFINANCE":"NBFC",
    "HCLTECH":"IT",        "KOTAKBANK":"Banking",   "MARUTI":"Auto",
    "AXISBANK":"Banking",  "TITAN":"Consumer",      "SUNPHARMA":"Pharma",
    "ONGC":"Energy",       "NTPC":"Power",          "ADANIENT":"Conglomerate",
    "WIPRO":"IT",          "ULTRACEMCO":"Cement",   "POWERGRID":"Power",
    "NESTLEIND":"FMCG",    "BAJAJFINSV":"NBFC",     "JSWSTEEL":"Metals",
    "TATAMOTORS":"Auto",   "TECHM":"IT",            "INDUSINDBK":"Banking",
    "TATACONSUM":"FMCG",   "COALINDIA":"Mining",    "ASIANPAINT":"Paint",
    "HINDALCO":"Metals",   "CIPLA":"Pharma",        "DRREDDY":"Pharma",
    "BPCL":"Energy",       "GRASIM":"Cement",       "ADANIPORTS":"Infra",
    "EICHERMOT":"Auto",    "HEROMOTOCO":"Auto",     "BAJAJ-AUTO":"Auto",
    "BRITANNIA":"FMCG",    "SBILIFE":"Insurance",   "APOLLOHOSP":"Healthcare",
    "DIVISLAB":"Pharma",   "HDFCLIFE":"Insurance",  "M&M":"Auto",
    "SHRIRAMFIN":"NBFC",   "BEL":"Defence",
}

# ── Cache the yfinance fetch so re-clicks never re-fetch ──────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def fetch(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Single source of truth: one yfinance call per (symbol, start, end).
    Returns daily OHLCV DataFrame, or empty DataFrame on any error.
    """
    try:
        df = yf.download(
            f"{symbol}.NS",
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
        )
        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception:
        return pd.DataFrame()


def analyse(symbol: str, sector: str, df: pd.DataFrame) -> dict | None:
    """
    Given a clean OHLCV DataFrame for a date range, compute:
      - period_high    : highest High in range
      - period_low     : lowest  Low  in range
      - first_close    : close on first trading day of range
      - last_close     : close on last  trading day of range
      - change_pct     : (last_close - first_close) / first_close * 100
      - avg_volume     : mean daily volume over range
      - rsi14          : RSI(14) using full history
      - score          : simple buy score 0-100 from 5 factors
      - recommendation : BUY / HOLD / AVOID based on score
    """
    if df.empty or len(df) < 2:
        return None

    # ── Core OHLCV stats from the period ──────────────────────────────────────
    period_high  = round(float(df["High"].max()),     2)
    period_low   = round(float(df["Low"].min()),      2)
    first_close  = round(float(df["Close"].iloc[0]),  2)
    last_close   = round(float(df["Close"].iloc[-1]), 2)
    avg_volume   = int(df["Volume"].mean())
    last_volume  = int(df["Volume"].iloc[-1])

    if first_close == 0:
        return None

    change_pct = round((last_close - first_close) / first_close * 100, 2)

    # ── RSI(14) ───────────────────────────────────────────────────────────────
    closes = df["Close"].dropna()
    rsi = 50.0
    if len(closes) >= 15:
        delta    = closes.diff().dropna()
        gain     = delta.clip(lower=0).rolling(14).mean().iloc[-1]
        loss     = (-delta).clip(lower=0).rolling(14).mean().iloc[-1]
        if loss > 0:
            rsi = round(100 - 100 / (1 + gain / loss), 1)
        else:
            rsi = 100.0

    # ── 52-week position: where is last_close in the period range? ───────────
    rng = period_high - period_low
    position_in_range = ((last_close - period_low) / rng * 100) if rng > 0 else 50.0

    # ── Volume strength: last day vs average ─────────────────────────────────
    vol_ratio = last_volume / avg_volume if avg_volume > 0 else 1.0

    # ────────────────────────────────────────────────────────────────────────
    # SCORING (0-100): 5 simple factors, each contributes up to 20 pts
    # ────────────────────────────────────────────────────────────────────────
    score = 0

    # 1. RSI — lower is more oversold = more buyable
    if   rsi < 30:  score += 20   # very oversold — strong buy signal
    elif rsi < 45:  score += 15   # mildly oversold
    elif rsi < 60:  score += 10   # neutral
    elif rsi < 70:  score += 5    # slightly overbought
    else:           score += 0    # overbought — avoid

    # 2. Price position in period range — lower = better value
    if   position_in_range < 20:  score += 20  # near period low = value zone
    elif position_in_range < 40:  score += 15
    elif position_in_range < 60:  score += 10
    elif position_in_range < 80:  score += 5
    else:                         score += 0   # near period high

    # 3. Price change — down more = more recovery potential
    if   change_pct < -10: score += 20   # big drop = high recovery potential
    elif change_pct < -5:  score += 15
    elif change_pct < 0:   score += 10
    elif change_pct < 5:   score += 5
    else:                  score += 0    # already pumped

    # 4. Volume on last day vs average — high volume = conviction
    if   vol_ratio > 2.0:  score += 20
    elif vol_ratio > 1.5:  score += 15
    elif vol_ratio > 1.0:  score += 10
    elif vol_ratio > 0.7:  score += 5
    else:                  score += 0

    # 5. Sector bonus — defensive sectors are safer buys
    if sector in ("Pharma", "FMCG", "Healthcare", "IT"):
        score += 20
    elif sector in ("Banking", "NBFC", "Insurance"):
        score += 15
    elif sector in ("Auto", "Consumer", "Cement"):
        score += 10
    elif sector in ("Energy", "Power", "Infra"):
        score += 5
    else:
        score += 0

    # ── Recommendation ────────────────────────────────────────────────────────
    if   score >= 75: rec = "🟢 STRONG BUY"
    elif score >= 55: rec = "🟡 BUY"
    elif score >= 35: rec = "🟠 HOLD"
    else:             rec = "🔴 AVOID"

    return {
        "symbol":    symbol,
        "sector":    sector,
        "high":      period_high,
        "low":       period_low,
        "last":      last_close,
        "change":    change_pct,
        "rsi":       rsi,
        "pos":       round(position_in_range, 1),
        "vol_ratio": round(vol_ratio, 2),
        "score":     score,
        "rec":       rec,
    }


# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("## 📊 Nifty 50 Analyzer")
st.caption("Fetches real NSE data · Finds period high/low · Scores each stock for future buy potential")
st.divider()

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    from_date = st.date_input("From", value=date.today() - timedelta(days=30),
                               max_value=date.today() - timedelta(days=2))
with col2:
    to_date = st.date_input("To", value=date.today(),
                             max_value=date.today())
with col3:
    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("▶ Analyse", use_container_width=True, type="primary")

if from_date >= to_date:
    st.error("From date must be before To date.")
    st.stop()

if run:
    results = []
    prog = st.progress(0, text="Starting…")

    for i, (sym, sec) in enumerate(STOCKS.items()):
        prog.progress((i + 1) / len(STOCKS), text=f"Fetching {sym}.NS…")
        df = fetch(sym, str(from_date), str(date(to_date.year, to_date.month, to_date.day) + timedelta(days=1)))
        row = analyse(sym, sec, df)
        if row:
            results.append(row)

    prog.empty()

    if not results:
        st.error("No data returned. Try a different date range.")
        st.stop()

    df_all = pd.DataFrame(results).sort_values("score", ascending=False)
    st.session_state["results"] = df_all
    st.session_state["range"]   = f"{from_date.strftime('%d %b %Y')} → {to_date.strftime('%d %b %Y')}"

if "results" not in st.session_state:
    st.info("Select a date range and click ▶ Analyse")
    st.stop()

df_all  = st.session_state["results"]
rng_lbl = st.session_state["range"]

st.markdown(f"### Results · {rng_lbl} · {len(df_all)} stocks")
st.divider()

# ── Top 5 Buy Recommendations ─────────────────────────────────────────────────
st.markdown("#### 🏆 Top 5 Stocks to Buy")
top5 = df_all[df_all["rec"].str.contains("BUY")].head(5)

if top5.empty:
    st.warning("No BUY signals found in this date range.")
else:
    cols = st.columns(len(top5))
    for col, (_, row) in zip(cols, top5.iterrows()):
        with col:
            st.markdown(f"""
            <div style="background:#111;border:1px solid #00e5a0;border-radius:10px;
                        padding:16px;text-align:center">
                <div style="font-size:18px;font-weight:900;color:#fff">{row['symbol']}</div>
                <div style="font-size:11px;color:#666;margin-bottom:8px">{row['sector']}</div>
                <div style="font-size:22px;font-weight:900;color:#00e5a0">{row['score']}/100</div>
                <div style="font-size:12px;color:#aaa;margin:4px 0">{row['rec']}</div>
                <hr style="border-color:#222;margin:8px 0">
                <div style="font-size:11px;color:#888">
                    High ₹{row['high']:,.0f} · Low ₹{row['low']:,.0f}<br>
                    Last ₹{row['last']:,.0f} &nbsp;
                    <span style="color:{'#00e5a0' if row['change']>=0 else '#ff5472'}">
                        {row['change']:+.2f}%
                    </span><br>
                    RSI {row['rsi']} · In range {row['pos']}%
                </div>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# ── Full Table ────────────────────────────────────────────────────────────────
st.markdown("#### 📋 All 50 Stocks")

def color_rec(val):
    if "STRONG BUY" in val: return "background-color:#052e1a;color:#00e5a0"
    if "BUY"        in val: return "background-color:#0a2a0a;color:#4ade80"
    if "HOLD"       in val: return "background-color:#1a1500;color:#f59e0b"
    return                         "background-color:#1a0505;color:#f87171"

def color_change(val):
    return f"color:{'#00e5a0' if val >= 0 else '#ff5472'}"

display = df_all[[
    "symbol","sector","high","low","last","change","rsi","pos","vol_ratio","score","rec"
]].rename(columns={
    "symbol":"Symbol","sector":"Sector",
    "high":"Period High","low":"Period Low","last":"Last Close",
    "change":"Change %","rsi":"RSI(14)","pos":"In Range %",
    "vol_ratio":"Vol Ratio","score":"Score","rec":"Signal"
})

styled = (
    display.style
    .applymap(color_rec,       subset=["Signal"])
    .applymap(color_change,    subset=["Change %"])
    .format({
        "Period High": "₹{:,.0f}", "Period Low": "₹{:,.0f}",
        "Last Close":  "₹{:,.0f}", "Change %": "{:+.2f}%",
        "RSI(14)": "{:.1f}", "In Range %": "{:.1f}%",
        "Vol Ratio": "{:.2f}x", "Score": "{}/100",
    })
    .set_properties(**{"font-size": "13px"})
)

st.dataframe(styled, use_container_width=True, height=600)

# ── Refresh button ─────────────────────────────────────────────────────────────
if st.button("🔄 Clear cache & fetch fresh data"):
    fetch.clear()
    st.session_state.clear()
    st.rerun()
