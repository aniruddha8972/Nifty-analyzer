"""
app.py — Nifty 50 Market Analyzer
──────────────────────────────────
Entry point. Pure orchestration — no data logic, no ML, no styling here.

Project structure:
  app.py               ← this file (wiring only)
  backend/
    constants.py       ← stock universe, sector maps, word lists, RSS feeds
    data.py            ← yfinance fetch + technical indicator computation
    ml.py              ← ML ensemble + news sentiment
  frontend/
    styles.py          ← full CSS design system (Space Mono + DM Sans)
    components.py      ← all reusable HTML components
  pipeline/
    report.py          ← Excel workbook generator (4 sheets)
  .streamlit/
    config.toml        ← dark theme
  requirements.txt

Run locally:
  pip install -r requirements.txt
  streamlit run app.py

Deploy:
  Push to GitHub → connect at share.streamlit.io
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta

import streamlit as st

from backend.data import fetch_all
from backend.ml   import predict
from frontend     import (
    inject, render_header, render_stat_bar, render_section,
    render_gainer_cards, render_loser_cards, render_prediction_cards,
    render_movers_table, render_predictions_table,
    render_all_stocks_table, render_empty_state,
)
from pipeline.report import generate


# ── Page config (must be first Streamlit call) ─────────────────────────────────
st.set_page_config(
    page_title="Nifty 50 Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject()


# ── Session state defaults ─────────────────────────────────────────────────────
if "data"   not in st.session_state: st.session_state["data"]   = None
if "from_d" not in st.session_state: st.session_state["from_d"] = None
if "to_d"   not in st.session_state: st.session_state["to_d"]   = None


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="app-wordmark" style="padding:12px 0 4px">Nifty 50 Analyzer</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-section"></div>', unsafe_allow_html=True)

    # Quick presets
    st.markdown('<div class="sidebar-label">Quick Preset</div>', unsafe_allow_html=True)
    today = date.today()
    preset = st.selectbox(
        "Preset",
        ["Custom", "1 Week", "2 Weeks", "1 Month", "3 Months", "6 Months", "YTD"],
        label_visibility="collapsed",
    )

    preset_map = {
        "1 Week":   timedelta(weeks=1),
        "2 Weeks":  timedelta(weeks=2),
        "1 Month":  timedelta(days=30),
        "3 Months": timedelta(days=90),
        "6 Months": timedelta(days=180),
    }

    if preset == "YTD":
        default_from = date(today.year, 1, 1)
    elif preset in preset_map:
        default_from = today - preset_map[preset]
    else:
        default_from = today - timedelta(days=30)

    # Date inputs
    st.markdown('<div class="sidebar-label">Date Range</div>', unsafe_allow_html=True)
    from_d = st.date_input("From", value=default_from,
                            max_value=today - timedelta(days=2), label_visibility="visible")
    to_d   = st.date_input("To",   value=today,
                            max_value=today, label_visibility="visible")

    if from_d >= to_d:
        st.error("⚠ From date must be before To date")
        st.stop()

    days = (to_d - from_d).days
    st.markdown(
        f'<div class="stat-sub" style="margin:6px 0 12px;padding:8px 12px;'
        f'background:var(--bg3);border:1px solid var(--border);border-radius:4px;">'
        f'<span style="color:var(--green);font-family:var(--mono);font-size:11px">'
        f'{days}d</span> &nbsp;·&nbsp; ~{round(days*5/7)}T</div>',
        unsafe_allow_html=True,
    )

    # Analyse button
    st.markdown('<div class="sidebar-section"></div>', unsafe_allow_html=True)
    run = st.button("▶  ANALYSE", use_container_width=True, type="primary")

    # Refresh cache
    if st.button("⟳  REFRESH DATA", use_container_width=True):
        from backend.data import fetch_ohlcv
        from backend.ml   import fetch_sentiment
        fetch_ohlcv.clear()
        fetch_sentiment.clear()
        st.session_state.clear()
        st.rerun()

    # Footer
    st.markdown("""
    <div style="margin-top:24px;padding-top:16px;border-top:1px solid var(--border)">
      <div style="font-family:var(--mono);font-size:9px;letter-spacing:1.5px;
                  color:var(--dim);line-height:2">
        STACK<br>
        <span style="color:var(--mid)">
          Python · Streamlit<br>
          yfinance · scikit-learn<br>
          openpyxl · BeautifulSoup
        </span>
      </div>
      <div style="margin-top:12px;font-family:var(--sans);font-size:9px;
                  color:var(--dim);line-height:1.6;font-style:italic">
        ⚠ Not financial advice.<br>
        Consult a SEBI-registered advisor.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Header ─────────────────────────────────────────────────────────────────────
label = ""
if st.session_state["from_d"] and st.session_state["to_d"]:
    f = st.session_state["from_d"]
    t = st.session_state["to_d"]
    label = f"{f.strftime('%d %b %Y')} → {t.strftime('%d %b %Y')}"
render_header(label)


# ── Run analysis on button click ───────────────────────────────────────────────
if run:
    prog = st.progress(0, text="Initialising…")

    def on_progress(i: int, sym: str) -> None:
        prog.progress((i + 1) / 50, text=f"Fetching  {sym}.NS  ({i+1}/50)")

    all_stats = fetch_all(from_d, to_d, on_progress)
    prog.empty()

    if not all_stats:
        st.error("⚠ No data returned from Yahoo Finance. Try a wider date range.")
        st.stop()

    with st.spinner("Running ML ensemble + fetching news sentiment…"):
        enriched = predict(all_stats)

    st.session_state["data"]   = enriched
    st.session_state["from_d"] = from_d
    st.session_state["to_d"]   = to_d
    st.rerun()


# ── No data yet ────────────────────────────────────────────────────────────────
if not st.session_state["data"]:
    render_empty_state()
    st.stop()


# ── Load data ──────────────────────────────────────────────────────────────────
data   = st.session_state["data"]
from_d = st.session_state["from_d"]
to_d   = st.session_state["to_d"]
label  = f"{from_d.strftime('%d %b %Y')} → {to_d.strftime('%d %b %Y')}"

gainers     = sorted(data, key=lambda x: x["change_pct"], reverse=True)
losers      = sorted(data, key=lambda x: x["change_pct"])
predictions = sorted(data, key=lambda x: x["final_score"], reverse=True)


# ── Stat bar ───────────────────────────────────────────────────────────────────
render_stat_bar(data)


# ── Download report ────────────────────────────────────────────────────────────
xlsx  = generate(data, gainers[:10], losers[:10], predictions, from_d, to_d)
fname = f"Nifty50_{from_d}_{to_d}.xlsx"

col_dl, col_info, _ = st.columns([2, 4, 4])
with col_dl:
    st.download_button(
        "📥  Download Excel Report",
        data=xlsx, file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with col_info:
    st.markdown(
        f'<div class="stat-sub" style="padding-top:8px">'
        f'4 sheets: Gainers · Losers · Predictions · Summary · {label}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────
t1, t2, t3, t4 = st.tabs([
    "📈  Top Gainers",
    "📉  Top Losers",
    "🤖  AI Predictions",
    "📋  All Stocks",
])


# ── Tab 1: Top Gainers ─────────────────────────────────────────────────────────
with t1:
    render_section("Top 10 Gainers", label)
    render_gainer_cards(gainers[:10])
    st.markdown("<br>", unsafe_allow_html=True)
    render_movers_table(gainers[:10])


# ── Tab 2: Top Losers ──────────────────────────────────────────────────────────
with t2:
    render_section("Top 10 Losers", label)
    render_loser_cards(losers[:10])
    st.markdown("<br>", unsafe_allow_html=True)
    render_movers_table(losers[:10])


# ── Tab 3: AI Predictions ─────────────────────────────────────────────────────
with t3:
    render_section("AI Predictions", "RF + GB + Ridge · News Sentiment")
    st.markdown(
        '<div class="stat-sub" style="margin-bottom:16px">'
        'Ensemble: RandomForest 40% + GradientBoosting 40% + Ridge 20% &nbsp;·&nbsp; '
        'Sentiment: free RSS feeds, no API key</div>',
        unsafe_allow_html=True,
    )
    buy_stocks = [s for s in predictions if "BUY" in s.get("signal", "")]
    if buy_stocks:
        render_section("Top Buy Signals", f"{len(buy_stocks)} stocks")
        render_prediction_cards(buy_stocks[:5])
        st.markdown("<br>", unsafe_allow_html=True)
    render_predictions_table(predictions)


# ── Tab 4: All Stocks ──────────────────────────────────────────────────────────
with t4:
    render_section("All Stocks", f"{len(data)} · sorted by return")
    render_all_stocks_table(data)
