"""
app.py — NSE Market Analyzer
Entry point. Handles auth gate; if authenticated, shows full sidebar app.
No st.switch_page() here — prevents redirect/blinking loops.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(
    page_title="NSE Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from frontend.styles  import inject
from frontend.session import init_defaults, is_authenticated

inject()
init_defaults()

# DB init (idempotent)
if not st.session_state.get("db_ready"):
    from backend.db_init import ensure_db
    ensure_db()
    st.session_state["db_ready"] = True

# ── Auth gate ─────────────────────────────────────────────────────────────────
if not is_authenticated():
    from frontend.auth_page import render_auth_page
    # Hide sidebar on login page
    st.markdown("""
    <style>
    [data-testid="stSidebar"]{display:none!important;}
    [data-testid="stSidebarNav"]{display:none!important;}
    section[data-testid="stSidebarNav"]{display:none!important;}
    </style>""", unsafe_allow_html=True)
    if render_auth_page():
        st.rerun()
    st.stop()

# ── Authenticated — full app ───────────────────────────────────────────────────
from datetime import date, timedelta
from backend.data      import fetch_all, fetch_ohlcv
from backend.constants import INDEX_OPTIONS, INDEX_UNIVERSE
from backend.ml        import predict, fetch_sentiment_data
from backend.portfolio import (
    add_holding, remove_holding, fetch_live_prices,
    compute_portfolio_pnl, get_portfolio_advice,
    _persist, reload_portfolio_from_db,
)
from backend.auth import (
    save_user_portfolio, logout as auth_logout,
    is_supabase_mode, update_password, validate_password, is_admin,
)
from frontend.sidebar  import render_sidebar
from frontend.session  import get_user, get_data, get_index, set_data, clear_analysis
from frontend import (
    render_header, render_stat_bar, render_section,
    render_gainer_cards, render_loser_cards, render_prediction_cards,
    render_movers_table, render_predictions_table,
    render_all_stocks_table, render_empty_state,
)
from frontend.portfolio_components import (
    render_portfolio_summary_v2, render_holdings_table,
    render_add_holding_form, render_manage_holdings,
    render_advice_cards, render_portfolio_io,
)
from frontend.analytics_components import (
    render_heatmap_tab, render_backtest_tab,
    render_correlation_tab, render_events_tab, render_news_tab,
    render_index_charts_tab, render_global_sentiment_section,
)
from frontend.admin_dashboard import render_admin_dashboard
from pipeline.report import generate

render_sidebar("dashboard")

user = get_user()

# ── Session defaults ──────────────────────────────────────────────────────────
if "selected_index" not in st.session_state: st.session_state["selected_index"] = "Nifty 50"
if "from_d"         not in st.session_state: st.session_state["from_d"] = None
if "to_d"           not in st.session_state: st.session_state["to_d"]   = None

# ── Logout helper ──────────────────────────────────────────────────────────────
def _do_logout():
    portfolio = st.session_state.get("portfolio", {})
    if user:
        save_user_portfolio(user, portfolio)
        auth_logout(user)
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# ── Header row ─────────────────────────────────────────────────────────────────
hcol1, hcol2 = st.columns([7, 3])
label = ""
if st.session_state["from_d"] and st.session_state["to_d"]:
    label = f"{st.session_state['from_d'].strftime('%d %b %Y')} → {st.session_state['to_d'].strftime('%d %b %Y')}"
with hcol1:
    _cur_idx = st.session_state.get("selected_index","Nifty 50")
    render_header(label, index_name=_cur_idx, stock_count=len(INDEX_UNIVERSE.get(_cur_idx,{})))
with hcol2:
    name     = user.get("name","")
    username = user.get("username","")
    initials = "".join(w[0].upper() for w in name.split()[:2]) if name else "?"
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:flex-end;
                gap:10px;padding-top:18px">
      <div style="text-align:right">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;
                    font-weight:700;color:#e8e9f5">{name}</div>
        <div style="font-family:'Inter',sans-serif;font-size:10px;color:#5a5e8a">@{username}</div>
      </div>
      <div class="avatar">{initials}</div>
    </div>""", unsafe_allow_html=True)
    if st.button("⏻ Log Out", key="logout_header", use_container_width=True):
        _do_logout()

# ── Control panel ──────────────────────────────────────────────────────────────
today = date.today()
st.markdown('<div class="ctrl-panel">', unsafe_allow_html=True)
c0,c1,c2,c3,c4,c5 = st.columns([2.2,2,2,2,1.4,1.4])
with c0:
    prev_idx = st.session_state.get("selected_index","Nifty 50")
    sel_idx  = st.selectbox("Index / Universe", INDEX_OPTIONS,
                             index=INDEX_OPTIONS.index(prev_idx), key="idx_sel")
    if sel_idx != prev_idx:
        for k in ["data","from_d","to_d","bt_result","corr_result"]:
            st.session_state.pop(k, None)
        st.session_state["selected_index"] = sel_idx
        st.rerun()
with c1:
    preset = st.selectbox("Quick Preset",
        ["1 Month","1 Week","2 Weeks","3 Months","6 Months","YTD","Custom"])
preset_map = {"1 Week":timedelta(weeks=1),"2 Weeks":timedelta(weeks=2),
              "1 Month":timedelta(days=30),"3 Months":timedelta(days=90),"6 Months":timedelta(days=180)}
dfrom = date(today.year,1,1) if preset=="YTD" else today-preset_map.get(preset,timedelta(days=30))
with c2:
    from_d = st.date_input("From", value=dfrom, max_value=today-timedelta(days=2))
with c3:
    to_d = st.date_input("To", value=today, max_value=today)
with c4:
    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    run = st.button("▶  ANALYSE", use_container_width=True, type="primary")
with c5:
    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    refresh = st.button("⟳  REFRESH", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if from_d >= to_d:
    st.error("⚠ 'From' date must be before 'To' date.")
    st.stop()

if refresh:
    fetch_ohlcv.clear(); fetch_sentiment_data.clear()
    for k in ["data","from_d","to_d"]: st.session_state.pop(k,None)
    st.rerun()

# ── Run analysis ───────────────────────────────────────────────────────────────
if run:
    _universe = INDEX_UNIVERSE.get(st.session_state.get("selected_index","Nifty 50"), INDEX_UNIVERSE["Nifty 50"])
    total     = len(_universe)
    prog = st.progress(0, text=f"Initialising ({total} stocks)…")
    def on_progress(i,sym,tot=total): prog.progress((i+1)/tot,text=f"Fetching {sym}.NS ({i+1}/{tot})")
    all_stats = fetch_all(from_d, to_d, on_progress, stocks=_universe)
    prog.empty()
    if not all_stats:
        st.error("⚠ No data returned. Check internet or try a different date range.")
        st.stop()
    with st.spinner(f"Training ML · {total} stocks · first run ~60s…"):
        enriched = predict(all_stats, universe=_universe)
    set_data(enriched, from_d, to_d)
    st.rerun()

# ── Portfolio render helper ────────────────────────────────────────────────────
def _render_portfolio_tab():
    h_col,save_col,ref_col = st.columns([6,1.2,1.2])
    with h_col: render_section("My Portfolio", f"Live P&L · ML Advisor · {user.get('name','')}")
    with save_col:
        st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
        if st.button("💾  Save", key="pf_save_btn", use_container_width=True, type="primary"):
            ok,msg = _persist()
            st.success("✅ Portfolio saved to cloud!") if ok else st.error(f"❌ {msg}")
    with ref_col:
        st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
        if st.button("🔄  Refresh", key="pf_refresh_btn", use_container_width=True):
            with st.spinner("Loading from cloud…"):
                ok,msg = reload_portfolio_from_db()
            st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")
            if ok: st.rerun()
    last_saved = st.session_state.get("portfolio_last_saved")
    if last_saved: st.caption(f"Last synced: {last_saved}")
    portfolio = st.session_state.get("portfolio",{})
    _active_uni = INDEX_UNIVERSE.get(st.session_state.get("selected_index","Nifty 50"), INDEX_UNIVERSE["Nifty 50"])
    result = render_add_holding_form(universe=_active_uni)
    if result:
        sym,qty,price,buy_date = result
        add_holding(sym,qty,price,buy_date)
        ok,msg = _persist()
        st.success(f"✅ Added {qty}×{sym} @ ₹{price:,.2f} — saved to cloud") if ok else st.warning(f"Added locally. {msg}")
        st.rerun()
    if not portfolio:
        render_empty_state(); return
    with st.spinner("Fetching live prices…"):
        live_prices = fetch_live_prices(tuple(portfolio.keys()))
    pnl_rows,totals = compute_portfolio_pnl(portfolio,live_prices)
    pnl_rows = get_portfolio_advice(pnl_rows,st.session_state.get("data"))
    render_portfolio_summary_v2(totals)
    render_section("ML Advisor — Priority Actions", f"{len(pnl_rows)} holdings")
    if not st.session_state.get("data"): st.info("💡 Run ▶ ANALYSE to get ML-powered advice.")
    render_advice_cards(pnl_rows)
    st.markdown("<br>", unsafe_allow_html=True)
    render_section("Holdings Detail", "live prices · P&L · ML signal")
    render_holdings_table(pnl_rows)
    to_remove = render_manage_holdings(pnl_rows)
    if to_remove:
        remove_holding(to_remove)
        ok,msg = _persist()
        st.success(f"✅ Removed {to_remove} — saved to cloud") if ok else st.warning(f"Removed locally. {msg}")
        st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    render_portfolio_io(portfolio)

# ── Tabs ──────────────────────────────────────────────────────────────────────
_is_admin = is_admin(user)
_tabs_def = [
    "📈  Top Gainers","📉  Top Losers","🤖  AI Predictions","📋  All Stocks",
    "💼  My Portfolio","🗺  Heatmap","📊  Backtest","🔗  Correlations",
    "📅  Events","📰  News Feed","📈  Index Charts","🌍  Global Sentiment",
]
if _is_admin: _tabs_def.append("🛡  Admin")
_tab_objs = st.tabs(_tabs_def)
t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12 = _tab_objs[:12]
tadmin = _tab_objs[12] if _is_admin else None

data = st.session_state.get("data")
from_d_s = st.session_state.get("from_d")
to_d_s   = st.session_state.get("to_d")
label    = f"{from_d_s.strftime('%d %b %Y')} → {to_d_s.strftime('%d %b %Y')}" if from_d_s else ""

if not data:
    for tab in [t1,t2,t3,t4]: 
        with tab: render_empty_state()
    with t5:  _render_portfolio_tab()
    with t6:  render_heatmap_tab([])
    with t7:  render_backtest_tab()
    with t8:  render_correlation_tab()
    with t9:  render_events_tab()
    with t10: render_news_tab([])
    with t11: render_index_charts_tab()
    with t12: render_global_sentiment_section()
    if tadmin:
        with tadmin: render_admin_dashboard()
    st.stop()

gainers     = sorted(data, key=lambda x: x["change_pct"], reverse=True)
losers      = sorted(data, key=lambda x: x["change_pct"])
predictions = sorted(data, key=lambda x: x.get("final_score",0), reverse=True)
render_stat_bar(data)

# Download
xlsx  = generate(data, gainers[:10], losers[:10], predictions, from_d_s, to_d_s)
dc,ic,_ = st.columns([2,5,3])
with dc:
    st.download_button("📥  Download Excel Report", data=xlsx,
        file_name=f"NSE_{from_d_s}_{to_d_s}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True)
with ic:
    st.markdown(f'<div style="padding-top:10px;font-family:IBM Plex Mono,monospace;font-size:10px;color:#5a5e8a">6 sheets · {label}</div>', unsafe_allow_html=True)

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
    render_section("AI Predictions","RF + GB + Ridge · News Sentiment")
    n_rows  = data[0].get("training_rows",0) if data else 0
    n_feats = data[0].get("n_features",0)    if data else 0
    n_stks  = data[0].get("training_stocks",0) if data else 0
    _cur    = st.session_state.get("selected_index","Nifty 50")
    if n_rows:
        st.markdown(f'<div style="margin-bottom:16px;padding:10px 16px;background:#0a1a10;border:1px solid #1a3a28;border-radius:6px;font-family:IBM Plex Mono,monospace;font-size:11px;color:#6b6b80"><span style="color:#00e5a0">✓ {n_rows:,} training rows</span> · {n_stks} stocks × 5yr ({_cur}) · {n_feats} features · RF 40% + GB 40% + Ridge 20%</div>', unsafe_allow_html=True)
    buy_stocks = [s for s in predictions if "BUY" in s.get("signal","")]
    if buy_stocks:
        render_section("Top Buy Signals",f"{len(buy_stocks)} stocks")
        render_prediction_cards(buy_stocks[:5])
        st.markdown("<br>", unsafe_allow_html=True)
    render_predictions_table(predictions)
with t4:
    render_section("All Stocks",f"{len(data)} · sorted by return")
    render_all_stocks_table(data)
with t5:  _render_portfolio_tab()
with t6:  render_heatmap_tab(data)
with t7:  render_backtest_tab()
with t8:  render_correlation_tab(portfolio_symbols=list(st.session_state.get("portfolio",{}).keys()))
with t9:  render_events_tab()
with t10: render_news_tab(data)
with t11: render_index_charts_tab()
with t12: render_global_sentiment_section()
if tadmin:
    with tadmin: render_admin_dashboard()
