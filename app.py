"""
app.py — Nifty 50 Market Analyzer
──────────────────────────────────
Entry point. Pure orchestration — no data logic, no ML, no styling here.

Auth flow:
  1. render_auth_page() — shows login/register; returns True if authenticated
  2. If not authenticated, st.stop() — nothing else renders
  3. If authenticated, portfolio is loaded from data/portfolios/<user>.json
  4. All portfolio changes auto-persist to that file

Project structure:
  app.py                         ← this file (wiring only)
  data/
    users.json                   ← all user accounts (SHA-256 hashed passwords)
    portfolios/<username>.json   ← per-user portfolio (persists until reboot)
  backend/
    auth.py        ← register, login, load/save portfolio files
    constants.py   ← stock universe, sector maps, word lists, RSS feeds
    data.py        ← yfinance fetch + technical indicator computation
    ml.py          ← ML ensemble + news sentiment
    portfolio.py   ← P&L calc, live prices, ML advisor
  frontend/
    auth_page.py   ← login + register UI
    styles.py      ← full CSS design system
    components.py  ← reusable HTML components
    portfolio_components.py ← portfolio tab components
  pipeline/
    report.py      ← Excel workbook generator (4 sheets)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta

import streamlit as st

# ── Page config — MUST be first Streamlit call ─────────────────────────────────
st.set_page_config(
    page_title="Nifty 50 Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Auth gate ──────────────────────────────────────────────────────────────────
from frontend.auth_page import render_auth_page
from frontend.styles    import inject
inject()

if not render_auth_page():
    st.stop()   # not logged in — show nothing else


# ── All other imports (only reached when logged in) ────────────────────────────
from backend.data      import fetch_all, fetch_ohlcv
from backend.ml        import predict, fetch_sentiment
from backend.portfolio import (
    add_holding, remove_holding, fetch_live_prices,
    compute_portfolio_pnl, get_portfolio_advice,
)
from backend.auth import save_user_portfolio, logout as auth_logout, is_supabase_mode
from frontend.portfolio_components import (
    render_portfolio_summary_v2, render_holdings_table,
    render_add_holding_form, render_manage_holdings,
    render_advice_cards, render_portfolio_io,
)
from frontend import (
    render_header, render_stat_bar, render_section,
    render_gainer_cards, render_loser_cards, render_prediction_cards,
    render_movers_table, render_predictions_table,
    render_all_stocks_table, render_empty_state,
)
from pipeline.report import generate


# ── Session state defaults ─────────────────────────────────────────────────────
if "data"   not in st.session_state: st.session_state["data"]   = None
if "from_d" not in st.session_state: st.session_state["from_d"] = None
if "to_d"   not in st.session_state: st.session_state["to_d"]   = None
# portfolio is already loaded from disk by render_auth_page → login


# ── Sidebar — user profile + info ─────────────────────────────────────────────
user = st.session_state.get("user_info", {})
with st.sidebar:
    st.markdown(f"""
    <div style="padding:16px 0 8px">
      <div style="font-family:'Space Mono',monospace;font-size:10px;
                  letter-spacing:3px;text-transform:uppercase;color:#00e5a0">
        Nifty 50 Analyzer
      </div>

      <div style="margin:18px 0 0;padding:14px;background:#08080e;
                  border:1px solid #1a1a28;border-radius:8px">
        <div style="font-family:'Space Mono',monospace;font-size:9px;
                    letter-spacing:2px;text-transform:uppercase;
                    color:#3a3a4e;margin-bottom:8px">LOGGED IN AS</div>
        <div style="font-family:'Space Mono',monospace;font-size:13px;
                    font-weight:700;color:#e8e8f0">{user.get('name','—')}</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:10px;
                    color:#3a3a4e;margin-top:3px">@{user.get('username','')}</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:10px;
                    color:#2a2a3e;margin-top:2px">{user.get('email','')}</div>
        <div style="font-family:'DM Sans',sans-serif;font-size:9px;
                    color:#2a2a3e;margin-top:6px">
          Member since {user.get('created_at','—')}
        </div>
      </div>

      <div style="font-family:'Space Mono',monospace;font-size:9px;
                  color:#3a3a4e;margin-top:16px;letter-spacing:1px;line-height:2">
        STACK<br>
        <span style="color:#2a2a3e">
          Python · Streamlit<br>
          yfinance · scikit-learn<br>
          openpyxl · BeautifulSoup<br>
          {'☁ Supabase' if is_supabase_mode() else '⚡ Local JSON'}
        </span>
      </div>

      <div style="margin-top:16px;padding-top:14px;border-top:1px solid #1a1a28;
                  font-family:'DM Sans',sans-serif;font-size:10px;
                  color:#2a2a3e;font-style:italic;line-height:1.6">
        ⚠ Not financial advice.<br>
        Consult a SEBI-registered advisor.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Logout button
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("⏻  Log Out", use_container_width=True, key="logout_btn"):
        user_info = st.session_state.get("user_info", {})
        portfolio = st.session_state.get("portfolio", {})
        # Save portfolio then sign out
        if user_info:
            save_user_portfolio(user_info, portfolio)
            auth_logout(user_info)
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ── App Header ─────────────────────────────────────────────────────────────────
label = ""
if st.session_state["from_d"] and st.session_state["to_d"]:
    f = st.session_state["from_d"]
    t = st.session_state["to_d"]
    label = f"{f.strftime('%d %b %Y')} → {t.strftime('%d %b %Y')}"
render_header(label)


# ══════════════════════════════════════════════════════════════════════
#  CONTROL PANEL — always visible
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

if from_d >= to_d:
    st.error("⚠ 'From' date must be before 'To' date.")
    st.stop()

if refresh:
    fetch_ohlcv.clear()
    fetch_sentiment.clear()
    # Keep auth + portfolio, clear only market data
    for key in ["data", "from_d", "to_d"]:
        st.session_state.pop(key, None)
    st.rerun()


# ── Run analysis ───────────────────────────────────────────────────────────────
if run:
    prog = st.progress(0, text="Initialising…")

    def on_progress(i: int, sym: str) -> None:
        prog.progress((i + 1) / 50, text=f"Fetching  {sym}.NS  ({i+1}/50)")

    all_stats = fetch_all(from_d, to_d, on_progress)
    prog.empty()

    if not all_stats:
        st.error("⚠ No data returned. Check internet connection or try a different date range.")
        st.stop()

    with st.spinner("Training ML on 3-year history (~35,000 rows, 17 features) — first run only, cached after…"):
        enriched = predict(all_stats)

    st.session_state["data"]   = enriched
    st.session_state["from_d"] = from_d
    st.session_state["to_d"]   = to_d
    st.rerun()


# ── Portfolio tab helper (shared between no-data and has-data paths) ───────────
def _render_portfolio_tab():
    render_section("My Portfolio", f"Live P&L · ML Advisor · {user.get('name','')}")

    portfolio = st.session_state.get("portfolio", {})

    # Add holding form
    result = render_add_holding_form()
    if result:
        sym, qty, price, buy_date = result
        add_holding(sym, qty, price, buy_date)
        st.success(f"✓  Added {qty} × {sym} @ ₹{price:,.2f}  —  portfolio saved")
        st.rerun()

    if not portfolio:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">💼</div>
          <div class="empty-title">Portfolio is empty</div>
          <div class="empty-sub">
            Use the form above to add your first holding.<br>
            Your portfolio is saved to your account automatically.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Fetch live prices
    with st.spinner("Fetching live prices…"):
        live_prices = fetch_live_prices(tuple(portfolio.keys()))

    # P&L
    pnl_rows, totals = compute_portfolio_pnl(portfolio, live_prices)

    # ML advice (uses market data if available)
    ml_stats = st.session_state.get("data")
    pnl_rows = get_portfolio_advice(pnl_rows, ml_stats)

    # Summary
    render_portfolio_summary_v2(totals)

    # Advice cards
    render_section("ML Advisor — Priority Actions", f"{len(pnl_rows)} holdings")
    if not ml_stats:
        st.info("💡  Run Market Analyzer (▶ ANALYSE) to get ML-powered advice for your holdings.")
    render_advice_cards(pnl_rows)

    # Holdings table
    st.markdown("<br>", unsafe_allow_html=True)
    render_section("Holdings Detail", "live prices · P&L · ML signal")
    render_holdings_table(pnl_rows)

    # Remove holdings
    to_remove = render_manage_holdings(pnl_rows)
    if to_remove:
        remove_holding(to_remove)
        st.success(f"✓  Removed {to_remove}  —  portfolio saved")
        st.rerun()

    # Import / Export
    st.markdown("<br>", unsafe_allow_html=True)
    render_portfolio_io(portfolio)


# ── No data yet ────────────────────────────────────────────────────────────────
if not st.session_state["data"]:
    _t1, _t2, _t3, _t4, _t5 = st.tabs([
        "📈  Top Gainers", "📉  Top Losers",
        "🤖  AI Predictions", "📋  All Stocks", "💼  My Portfolio",
    ])
    with _t1: render_empty_state()
    with _t2: render_empty_state()
    with _t3: render_empty_state()
    with _t4: render_empty_state()
    with _t5: _render_portfolio_tab()
    st.stop()


# ── Load data ──────────────────────────────────────────────────────────────────
data   = st.session_state["data"]
from_d = st.session_state["from_d"]
to_d   = st.session_state["to_d"]
label  = f"{from_d.strftime('%d %b %Y')} → {to_d.strftime('%d %b %Y')}"

gainers     = sorted(data, key=lambda x: x["change_pct"], reverse=True)
losers      = sorted(data, key=lambda x: x["change_pct"])
predictions = sorted(data, key=lambda x: x["final_score"], reverse=True)

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

with t1:
    render_section("Top 10 Gainers", label)
    render_gainer_cards(gainers[:10])
    st.markdown("<br>", unsafe_allow_html=True)
    render_movers_table(gainers[:10])

with t2:
    render_section("Top 10 Losers", label)
    render_loser_cards(losers[:10])
    st.markdown("<br>", unsafe_allow_html=True)
    render_movers_table(losers[:10])

with t3:
    render_section("AI Predictions", "RF + GB + Ridge · News Sentiment")
    n_rows  = data[0].get("training_rows", 0) if data else 0
    n_feats = data[0].get("n_features",    0) if data else 0
    if n_rows > 0:
        st.markdown(
            f'<div style="margin-bottom:16px;padding:10px 16px;'
            f'background:#0a1a10;border:1px solid #1a3a28;border-radius:6px;'
            f'font-family:\'Space Mono\',monospace;font-size:11px;color:#6b6b80">'
            f'<span style="color:#00e5a0">✓ {n_rows:,} real training rows</span>'
            f' &nbsp;·&nbsp; 50 stocks × 3yr daily OHLCV'
            f' &nbsp;·&nbsp; {n_feats} features'
            f' (8 technical + 7 sentiment proxies + 2 market-relative)'
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

with t4:
    render_section("All Stocks", f"{len(data)} · sorted by return")
    render_all_stocks_table(data)

with t5:
    _render_portfolio_tab()
