"""
app.py — Nifty 50 Market Analyzer
──────────────────────────────────
Entry point. Pure orchestration — no data logic, no ML, no styling here.
All controls live in the main page (visible on mobile + desktop).
Sidebar is kept for extra info only so it doesn't block anything.

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
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta

import streamlit as st

from backend.data      import fetch_all, fetch_ohlcv
from backend.ml        import predict, fetch_sentiment
from backend.portfolio import (
    add_holding, remove_holding, fetch_live_prices,
    compute_portfolio_pnl, get_portfolio_advice,
)
from frontend.portfolio_components import (
    render_portfolio_summary_v2, render_holdings_table,
    render_add_holding_form, render_manage_holdings,
    render_advice_cards, render_portfolio_io,
)
from frontend     import (
    inject, render_header, render_stat_bar, render_section,
    render_gainer_cards, render_loser_cards, render_prediction_cards,
    render_movers_table, render_predictions_table,
    render_all_stocks_table, render_empty_state,
)
from pipeline.report import generate


# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nifty 50 Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",   # collapsed by default — controls are on main page
)
inject()


# ── Session state defaults ─────────────────────────────────────────────────────
if "data"      not in st.session_state: st.session_state["data"]      = None
if "portfolio" not in st.session_state: st.session_state["portfolio"]  = {}
if "from_d" not in st.session_state: st.session_state["from_d"] = None
if "to_d"   not in st.session_state: st.session_state["to_d"]   = None


# ── Sidebar — info only, no required controls ──────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:16px 0 8px">
      <div style="font-family:'Space Mono',monospace;font-size:10px;
                  letter-spacing:3px;text-transform:uppercase;color:#00e5a0">
        Nifty 50 Analyzer
      </div>
      <div style="font-family:'Space Mono',monospace;font-size:9px;
                  color:#3a3a4e;margin-top:8px;letter-spacing:1px;line-height:2">
        STACK<br>
        <span style="color:#6b6b80">
          Python · Streamlit<br>
          yfinance · scikit-learn<br>
          openpyxl · BeautifulSoup
        </span>
      </div>
      <div style="margin-top:16px;padding-top:14px;border-top:1px solid #1e1e2e;
                  font-family:'DM Sans',sans-serif;font-size:10px;
                  color:#3a3a4e;font-style:italic;line-height:1.6">
        ⚠ Not financial advice.<br>
        Consult a SEBI-registered advisor.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── App Header ─────────────────────────────────────────────────────────────────
label = ""
if st.session_state["from_d"] and st.session_state["to_d"]:
    f = st.session_state["from_d"]
    t = st.session_state["to_d"]
    label = f"{f.strftime('%d %b %Y')} → {t.strftime('%d %b %Y')}"
render_header(label)


# ══════════════════════════════════════════════════════════════════════
#  CONTROL PANEL — always visible in the main page
# ══════════════════════════════════════════════════════════════════════
today = date.today()

st.markdown("""
<div style="background:#0c0c12;border:1px solid #1e1e2e;border-radius:10px;
            padding:20px 24px 16px;margin-bottom:20px">
  <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:3px;
              text-transform:uppercase;color:#4a4a60;margin-bottom:14px">
    ⚙ &nbsp; ANALYSIS CONTROLS
  </div>
""", unsafe_allow_html=True)

# Row 1: Preset selector + date range + action buttons — all in one row
ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4, ctrl_col5 = st.columns([2, 2, 2, 1.4, 1.4])

with ctrl_col1:
    preset = st.selectbox(
        "Quick Preset",
        ["1 Month", "1 Week", "2 Weeks", "3 Months", "6 Months", "YTD", "Custom"],
        index=0,
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

with ctrl_col2:
    from_d = st.date_input("From", value=default_from,
                            max_value=today - timedelta(days=2))

with ctrl_col3:
    to_d = st.date_input("To", value=today, max_value=today)

with ctrl_col4:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    run = st.button("▶  ANALYSE", use_container_width=True, type="primary")

with ctrl_col5:
    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
    refresh = st.button("⟳  REFRESH", use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

# Validate dates
if from_d >= to_d:
    st.error("⚠ 'From' date must be before 'To' date.")
    st.stop()

# Handle refresh
if refresh:
    fetch_ohlcv.clear()
    fetch_sentiment.clear()
    st.session_state.clear()
    st.rerun()


# ── Run analysis ───────────────────────────────────────────────────────────────
if run:
    prog = st.progress(0, text="Initialising…")

    def on_progress(i: int, sym: str) -> None:
        prog.progress((i + 1) / 50, text=f"Fetching  {sym}.NS  ({i+1}/50)")

    all_stats = fetch_all(from_d, to_d, on_progress)
    prog.empty()

    if not all_stats:
        st.error("⚠ No data returned from Yahoo Finance. Check your internet connection or try a different date range.")
        st.stop()

    with st.spinner("Training ML on 3 years of history (~35,000 rows) — first run only, then cached…"):
        enriched = predict(all_stats)

    st.session_state["data"]   = enriched
    st.session_state["from_d"] = from_d
    st.session_state["to_d"]   = to_d
    st.rerun()


# ── No data yet — show empty state but still allow portfolio tab ──────────────
if not st.session_state["data"]:
    # Show tabs so portfolio is always accessible
    _t1, _t2, _t3, _t4, _t5 = st.tabs([
        "📈  Top Gainers", "📉  Top Losers",
        "🤖  AI Predictions", "📋  All Stocks", "💼  My Portfolio",
    ])
    with _t1: render_empty_state()
    with _t2: render_empty_state()
    with _t3: render_empty_state()
    with _t4: render_empty_state()
    with _t5:
        render_section("My Portfolio", "Live P&L · ML Advisor")
        portfolio = st.session_state.get("portfolio", {})
        result = render_add_holding_form()
        if result:
            sym, qty, price, buy_date = result
            add_holding(sym, qty, price, buy_date)
            st.success(f"Added {qty} × {sym} @ ₹{price:,.2f}")
            st.rerun()
        if not portfolio:
            st.markdown('''<div class="empty-state">
              <div class="empty-icon">💼</div>
              <div class="empty-title">Portfolio is empty</div>
              <div class="empty-sub">Use the form above to add your first holding.</div>
            </div>''', unsafe_allow_html=True)
        else:
            with st.spinner("Fetching live prices…"):
                live_prices = fetch_live_prices(tuple(portfolio.keys()))
            pnl_rows, totals = compute_portfolio_pnl(portfolio, live_prices)
            pnl_rows = get_portfolio_advice(pnl_rows, None)
            render_portfolio_summary_v2(totals)
            render_section("ML Advisor — Priority Actions", f"{len(pnl_rows)} holdings")
            st.info("💡 Run the Market Analyzer (click ▶ ANALYSE) to get ML-powered advice.")
            render_advice_cards(pnl_rows)
            st.markdown("<br>", unsafe_allow_html=True)
            render_section("Holdings Detail", "live prices · P&L")
            render_holdings_table(pnl_rows)
            to_remove = render_manage_holdings(pnl_rows)
            if to_remove:
                remove_holding(to_remove)
                st.rerun()
            st.markdown("<br>", unsafe_allow_html=True)
            render_portfolio_io(portfolio)
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

col_dl, col_info, _ = st.columns([2, 5, 3])
with col_dl:
    st.download_button(
        "📥  Download Excel Report",
        data=xlsx, file_name=fname,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with col_info:
    st.markdown(
        f'<div style="padding-top:10px;font-family:\'Space Mono\',monospace;'
        f'font-size:10px;color:#4a4a60">'
        f'4 sheets · Gainers · Losers · Predictions · Summary · {label}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────
t1, t2, t3, t4, t5 = st.tabs([
    "📈  Top Gainers",
    "📉  Top Losers",
    "🤖  AI Predictions",
    "📋  All Stocks",
    "💼  My Portfolio",
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
    n_rows  = data[0].get("training_rows", 0) if data else 0
    n_feats = data[0].get("n_features", 0)    if data else 0
    if n_rows > 0:
        st.markdown(
            f'<div style="margin-bottom:16px;padding:10px 16px;'
            f'background:#0a1a10;border:1px solid #1a3a28;border-radius:6px;'
            f'font-family:\'Space Mono\',monospace;font-size:11px;color:#6b6b80">'
            f'<span style="color:#00e5a0">✓ {n_rows:,} real training rows</span>'
            f' &nbsp;·&nbsp; 50 stocks × 3yr daily OHLCV'
            f' &nbsp;·&nbsp; {n_feats} features (8 technical + 7 sentiment proxies + 2 market-relative)'
            f' &nbsp;·&nbsp; Target = actual 10-day forward return'
            f' &nbsp;·&nbsp; RF 40% + GB 40% + Ridge 20%</div>',
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


# ── Tab 5: My Portfolio ────────────────────────────────────────────────────────
with t5:
    render_section("My Portfolio", "Live P&L · ML Advisor")

    portfolio = st.session_state.get("portfolio", {})

    # ── Add new holding form ───────────────────────────────────────────
    result = render_add_holding_form()
    if result:
        sym, qty, price, buy_date = result
        add_holding(sym, qty, price, buy_date)
        st.success(f"Added {qty} × {sym} @ ₹{price:,.2f}")
        st.rerun()

    if not portfolio:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">💼</div>
          <div class="empty-title">Portfolio is empty</div>
          <div class="empty-sub">
            Use the form above to add your first holding.<br>
            Enter the stock, quantity, buy price and date.
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── Fetch live prices ──────────────────────────────────────────
        with st.spinner("Fetching live prices…"):
            live_prices = fetch_live_prices(tuple(portfolio.keys()))

        # ── Compute P&L ────────────────────────────────────────────────
        pnl_rows, totals = compute_portfolio_pnl(portfolio, live_prices)

        # ── Attach ML advice if market data is available ───────────────
        ml_stats = st.session_state.get("data")
        pnl_rows = get_portfolio_advice(pnl_rows, ml_stats)

        # ── Summary bar ────────────────────────────────────────────────
        render_portfolio_summary_v2(totals)

        # ── Priority advice cards ──────────────────────────────────────
        render_section("ML Advisor — Priority Actions", f"{len(pnl_rows)} holdings")
        if not ml_stats:
            st.info("💡 Run the Market Analyzer (click ▶ ANALYSE) to get ML-powered advice for your holdings.")
        render_advice_cards(pnl_rows)

        # ── Full holdings table ────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        render_section("Holdings Detail", "live prices · P&L · ML signal")
        render_holdings_table(pnl_rows)

        # ── Remove holdings ────────────────────────────────────────────
        to_remove = render_manage_holdings(pnl_rows)
        if to_remove:
            remove_holding(to_remove)
            st.success(f"Removed {to_remove} from portfolio")
            st.rerun()

        # ── Import / Export ────────────────────────────────────────────
        st.markdown("<br>", unsafe_allow_html=True)
        render_portfolio_io(portfolio)
