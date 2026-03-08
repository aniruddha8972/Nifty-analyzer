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
    initial_sidebar_state="expanded",   # open so user can see profile + logout
)

# ── Auth gate ──────────────────────────────────────────────────────────────────
from frontend.auth_page import render_auth_page
from frontend.styles    import inject
inject()

# ── Self-healing DB init (creates tables + admin if missing) ──────────────────
from backend.db_init import ensure_db
if "db_ready" not in __import__("streamlit").session_state:
    ensure_db()
    __import__("streamlit").session_state["db_ready"] = True

if not render_auth_page():
    st.stop()   # not logged in — show nothing else


# ── All other imports (only reached when logged in) ────────────────────────────
from backend.data      import fetch_all, fetch_ohlcv
from backend.ml        import predict, fetch_sentiment, fetch_sentiment_data
from backend.portfolio import (
    add_holding, remove_holding, fetch_live_prices,
    compute_portfolio_pnl, get_portfolio_advice,
    _persist, reload_portfolio_from_db,
)
from backend.auth import save_user_portfolio, logout as auth_logout, is_supabase_mode, update_password
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
from frontend.admin_dashboard import render_admin_dashboard
from backend.auth import is_admin
from frontend.analytics_components import (
    render_heatmap_tab, render_backtest_tab,
    render_correlation_tab, render_events_tab,
)


# ── Session state defaults ─────────────────────────────────────────────────────
if "data"   not in st.session_state: st.session_state["data"]   = None
if "from_d" not in st.session_state: st.session_state["from_d"] = None
if "to_d"   not in st.session_state: st.session_state["to_d"]   = None
# portfolio is already loaded from disk by render_auth_page → login


# ── Sidebar — user profile + logout ───────────────────────────────────────────
user = st.session_state.get("user_info", {})

def _do_logout():
    """Save portfolio, sign out of Supabase if needed, clear session."""
    user_info = st.session_state.get("user_info", {})
    portfolio = st.session_state.get("portfolio", {})
    if user_info:
        save_user_portfolio(user_info, portfolio)
        auth_logout(user_info)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

with st.sidebar:
    # App name
    st.markdown("""
    <div style="padding:12px 0 0">
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                  letter-spacing:3px;text-transform:uppercase;color:#00e5a0;
                  margin-bottom:16px">
        📊 &nbsp;Nifty 50 Analyzer
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── User profile card ──────────────────────────────────────────────
    name     = user.get("name", "—")
    username = user.get("username", "")
    email    = user.get("email", "")
    joined   = user.get("created_at", "")
    n_stocks = len(st.session_state.get("portfolio", {}))
    mode_badge = "☁ Supabase" if is_supabase_mode() else "⚡ Local"

    # Avatar initials
    initials = "".join(w[0].upper() for w in name.split()[:2]) if name != "—" else "?"

    st.markdown(f"""
    <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:12px;
                padding:16px;margin-bottom:12px;position:relative;overflow:hidden">
      <div style="position:absolute;top:0;left:0;right:0;height:2px;
                  background:linear-gradient(90deg,#00e5a0,#00a370)"></div>

      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
        <div style="width:40px;height:40px;border-radius:50%;flex-shrink:0;
                    background:linear-gradient(135deg,#00e5a0,#00a370);
                    display:flex;align-items:center;justify-content:center;
                    font-family:'IBM Plex Mono',monospace;font-size:14px;
                    font-weight:700;color:#030306;letter-spacing:-1px">
          {initials}
        </div>
        <div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:13px;
                      font-weight:700;color:#eeeef8;line-height:1.2">{name}</div>
          <div style="font-family:'Inter',sans-serif;font-size:10px;
                      color:#5a5a78;margin-top:2px">@{username}</div>
        </div>
      </div>

      <div style="font-family:'Inter',sans-serif;font-size:11px;
                  color:#33334a;line-height:2;border-top:1px solid #1c1c2e;padding-top:10px">
        <span style="color:#26263a">✉</span>&nbsp;
          <span style="color:#5a5a78">{email}</span><br>
        <span style="color:#26263a">💼</span>&nbsp;
          <span style="color:#00e5a0;font-family:'IBM Plex Mono',monospace;font-size:12px;font-weight:600">
            {n_stocks}
          </span>
          <span style="color:#33334a"> holding{"s" if n_stocks != 1 else ""}</span>
      </div>

      <div style="margin-top:10px">
        <span style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                     letter-spacing:2px;text-transform:uppercase;
                     background:rgba(0,229,160,.06);border:1px solid rgba(0,229,160,.18);
                     color:#00a370;padding:2px 8px;border-radius:4px">
          {mode_badge}
        </span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Update Password ────────────────────────────────────────────────
    with st.expander("\U0001f511  Change Password", expanded=False):
        st.markdown(
            "<div style=\"font-family:IBM Plex Mono,monospace;font-size:9px;"
            "letter-spacing:2px;text-transform:uppercase;color:#5a5a78;margin-bottom:10px\">"
            "Update your login password</div>",
            unsafe_allow_html=True
        )
        cur_pw  = st.text_input("Current Password",     type="password", key="upd_cur_pw",
                                 placeholder="Your current password")
        new_pw  = st.text_input("New Password",         type="password", key="upd_new_pw",
                                 placeholder="Min 8 chars + A-Z + 0-9 + symbol")
        conf_pw = st.text_input("Confirm New Password", type="password", key="upd_conf_pw",
                                 placeholder="Repeat new password")

        if new_pw:
            from backend.auth import validate_password
            _v, _f = validate_password(new_pw)
            _pct   = (5 - len(_f)) / 5
            _col   = "#ef4444" if _pct <= 0.4 else "#f59e0b" if _pct < 1.0 else "#00e5a0"
            _lbl   = "Weak" if _pct <= 0.4 else "Fair" if _pct < 1.0 else "Strong"
            st.markdown(
                f"<div style=\"display:flex;justify-content:space-between;"
                f"font-size:10px;color:#5a5a78;margin:2px 0 3px\">"
                f"<span>Strength</span>"
                f"<span style=\"color:{_col}\">{_lbl}</span></div>"
                f"<div style=\"background:#1c1c2e;border-radius:3px;height:3px\">"
                f"<div style=\"background:{_col};width:{int(_pct*100)}%;height:3px;border-radius:3px\"></div>"
                f"</div>",
                unsafe_allow_html=True
            )
            for _req in _f:
                st.markdown(
                    f"<div style=\"font-size:10px;color:#5a5a78;margin:1px 0\">\u2717 {_req}</div>",
                    unsafe_allow_html=True
                )
            if not _f:
                st.markdown(
                    "<div style=\"font-size:10px;color:#00e5a0;margin:1px 0\">\u2713 All requirements met</div>",
                    unsafe_allow_html=True
                )

        if st.button("Update Password", use_container_width=True,
                     type="primary", key="upd_pw_btn"):
            if not cur_pw or not new_pw or not conf_pw:
                st.error("Please fill in all three fields.")
            elif new_pw != conf_pw:
                st.error("New passwords do not match.")
            elif new_pw == cur_pw:
                st.error("New password must be different from current.")
            else:
                with st.spinner("Updating..."):
                    _ok, _msg = update_password(
                        st.session_state.get("user_info", {}),
                        cur_pw, new_pw
                    )
                if _ok:
                    st.success("\u2705 " + _msg)
                    for _k in ("upd_cur_pw", "upd_new_pw", "upd_conf_pw"):
                        st.session_state.pop(_k, None)
                    st.rerun()
                else:
                    st.error("\u274c " + _msg)

    # ── Logout button — big, red, unmissable ───────────────────────────
    st.markdown("""
    <style>
    div[data-testid="stSidebar"] div[data-testid="stButton"]:last-of-type > button {
      background: transparent !important;
      border: 1px solid #3a1a1a !important;
      color: #ff4560 !important;
      font-family: 'IBM Plex Mono', monospace !important;
      font-size: 11px !important;
      letter-spacing: 2px !important;
      height: 42px !important;
      border-radius: 7px !important;
      transition: all 0.18s ease !important;
    }
    div[data-testid="stSidebar"] div[data-testid="stButton"]:last-of-type > button:hover {
      background: rgba(255,69,96,0.1) !important;
      border-color: #ff4560 !important;
      box-shadow: 0 0 14px rgba(255,69,96,0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if st.button("⏻  LOG OUT", use_container_width=True, key="logout_btn"):
        _do_logout()

    # ── Disclaimer ─────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-top:20px;padding-top:14px;border-top:1px solid #1c1c2e;
                font-family:'Inter',sans-serif;font-size:10px;
                color:#1c1c2e;font-style:italic;line-height:1.7">
      ⚠ Not financial advice.<br>
      Consult a SEBI-registered advisor<br>
      before making any investment.
    </div>
    """, unsafe_allow_html=True)


# ── App Header ─────────────────────────────────────────────────────────────────
label = ""
if st.session_state["from_d"] and st.session_state["to_d"]:
    f = st.session_state["from_d"]
    t = st.session_state["to_d"]
    label = f"{f.strftime('%d %b %Y')} → {t.strftime('%d %b %Y')}"

# Header row: title left, user info + logout right
hcol1, hcol2 = st.columns([7, 3])
with hcol1:
    render_header(label)
with hcol2:
    name     = user.get("name", "")
    username = user.get("username", "")
    initials = "".join(w[0].upper() for w in name.split()[:2]) if name else "?"
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:flex-end;
                gap:10px;padding-top:18px">
      <div style="text-align:right">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;
                    font-weight:700;color:#e8e8f0">{name}</div>
        <div style="font-family:'Inter',sans-serif;font-size:10px;
                    color:#5a5a78">@{username}</div>
      </div>
      <div style="width:36px;height:36px;border-radius:50%;flex-shrink:0;
                  background:linear-gradient(135deg,#00e5a0,#00a370);
                  display:flex;align-items:center;justify-content:center;
                  font-family:'IBM Plex Mono',monospace;font-size:13px;
                  font-weight:700;color:#04040a">
        {initials}
      </div>
    </div>
    """, unsafe_allow_html=True)
    # Small inline logout button
    st.markdown("""
    <style>
    div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button[key="logout_header"] {
      height:32px !important; font-size:10px !important;
    }
    </style>
    """, unsafe_allow_html=True)
    if st.button("⏻ Log Out", key="logout_header", use_container_width=True):
        _do_logout()


# ══════════════════════════════════════════════════════════════════════
#  CONTROL PANEL — always visible
# ══════════════════════════════════════════════════════════════════════
today = date.today()

st.markdown("""
<div style="background:#0c0c12;border:1px solid #1e1e2e;border-radius:10px;
            padding:20px 24px 16px;margin-bottom:20px">
  <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:3px;
              text-transform:uppercase;color:#5a5a78;margin-bottom:14px">
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
    fetch_sentiment_data.clear()
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
    # ── Header row with Save + Refresh buttons ────────────────────────
    h_col, save_col, refresh_col = st.columns([6, 1.2, 1.2])
    with h_col:
        render_section("My Portfolio", f"Live P&L · ML Advisor · {user.get('name','')}")
    with save_col:
        st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
        if st.button("💾  Save", key="pf_save_btn", use_container_width=True, type="primary"):
            ok, msg = _persist()
            if ok:
                st.success(f"✅ Portfolio saved!")
            else:
                st.error(f"❌ {msg}")
    with refresh_col:
        st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
        if st.button("🔄  Refresh", key="pf_refresh_btn", use_container_width=True):
            with st.spinner("Loading from cloud…"):
                ok, msg = reload_portfolio_from_db()
            if ok:
                st.success(f"✅ {msg}")
                st.rerun()
            else:
                st.error(f"❌ {msg}")

    # Last saved timestamp
    last_saved = st.session_state.get("portfolio_last_saved")
    if last_saved:
        st.caption(f"Last synced: {last_saved}")

    portfolio = st.session_state.get("portfolio", {})

    # ── Add holding form ──────────────────────────────────────────────
    result = render_add_holding_form()
    if result:
        sym, qty, price, buy_date = result
        add_holding(sym, qty, price, buy_date)
        ok, msg = _persist()
        if ok:
            st.success(f"✅  Added {qty} × {sym} @ ₹{price:,.2f} — saved to cloud")
        else:
            st.warning(f"Added {qty} × {sym} locally. Save failed: {msg}")
        st.rerun()

    if not portfolio:
        st.markdown("""
        <div class="empty-state">
          <div class="empty-icon">💼</div>
          <div class="empty-title">Portfolio is empty</div>
          <div class="empty-sub">
            Add your first stock using the form above.<br>
            Click <strong>🔄 Refresh</strong> if you have holdings saved in the cloud.
          </div>
        </div>
        """, unsafe_allow_html=True)
        return

    # ── Live prices ───────────────────────────────────────────────────
    with st.spinner("Fetching live prices…"):
        live_prices = fetch_live_prices(tuple(portfolio.keys()))

    pnl_rows, totals = compute_portfolio_pnl(portfolio, live_prices)
    ml_stats = st.session_state.get("data")
    pnl_rows = get_portfolio_advice(pnl_rows, ml_stats)

    # ── Summary bar ───────────────────────────────────────────────────
    render_portfolio_summary_v2(totals)

    # ── ML advice cards ───────────────────────────────────────────────
    render_section("ML Advisor — Priority Actions", f"{len(pnl_rows)} holdings")
    if not ml_stats:
        st.info("💡  Run Market Analyzer (▶ ANALYSE) to get ML-powered advice.")
    render_advice_cards(pnl_rows)

    # ── Holdings table ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    render_section("Holdings Detail", "live prices · P&L · ML signal")
    render_holdings_table(pnl_rows)

    # ── Remove holdings ───────────────────────────────────────────────
    to_remove = render_manage_holdings(pnl_rows)
    if to_remove:
        remove_holding(to_remove)
        ok, msg = _persist()
        if ok:
            st.success(f"✅  Removed {to_remove} — saved to cloud")
        else:
            st.warning(f"Removed {to_remove} locally. Save failed: {msg}")
        st.rerun()

    # ── Import / Export ───────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    render_portfolio_io(portfolio)


# ── No data yet ────────────────────────────────────────────────────────────────
if not st.session_state["data"]:
    _user_info = st.session_state.get("user_info", {})
    _is_admin  = is_admin(_user_info)
    _tabs_def  = [
        "📈  Top Gainers", "📉  Top Losers",
        "🤖  AI Predictions", "📋  All Stocks", "💼  My Portfolio",
        "🗺  Heatmap", "📊  Backtest", "🔗  Correlations", "📅  Events",
    ]
    if _is_admin:
        _tabs_def.append("🛡  Admin")
    _tab_objs = st.tabs(_tabs_def)
    _t1,_t2,_t3,_t4,_t5,_t6,_t7,_t8,_t9 = _tab_objs[:9]
    _tadmin = _tab_objs[9] if _is_admin else None
    with _t1: render_empty_state()
    with _t2: render_empty_state()
    with _t3: render_empty_state()
    with _t4: render_empty_state()
    with _t5: _render_portfolio_tab()
    with _t6: render_heatmap_tab([])
    with _t7: render_backtest_tab()
    with _t8: render_correlation_tab()
    with _t9: render_events_tab()
    if _tadmin:
        with _tadmin: render_admin_dashboard()
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
        f'<div style="padding-top:10px;font-family:\'IBM Plex Mono\',monospace;'
        f'font-size:10px;color:#5a5a78">'
        f'4 sheets · Gainers · Losers · Predictions · Summary · {label}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<hr>", unsafe_allow_html=True)


# ── Tabs ───────────────────────────────────────────────────────────────────────
_user_info = st.session_state.get("user_info", {})
_is_admin  = is_admin(_user_info)
_tabs_main = [
    "📈  Top Gainers", "📉  Top Losers",
    "🤖  AI Predictions", "📋  All Stocks", "💼  My Portfolio",
    "🗺  Heatmap", "📊  Backtest", "🔗  Correlations", "📅  Events",
]
if _is_admin:
    _tabs_main.append("🛡  Admin")
_main_objs = st.tabs(_tabs_main)
t1,t2,t3,t4,t5,t6,t7,t8,t9 = _main_objs[:9]
tadmin = _main_objs[9] if _is_admin else None

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
            f'font-family:\'IBM Plex Mono\',monospace;font-size:11px;color:#6b6b80">'
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

with t6:
    render_heatmap_tab(data)

with t7:
    render_backtest_tab()

with t8:
    render_correlation_tab(portfolio_symbols=list(st.session_state.get('portfolio', {}).keys()))

with t9:
    render_events_tab()

if tadmin:
    with tadmin:
        render_admin_dashboard()
