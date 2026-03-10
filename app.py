"""
app.py — NSE Market Analyzer  (single-file entry point)
────────────────────────────────────────────────────────
Auth gate: unauthenticated → login page → st.stop()
           authenticated   → full dashboard (no redirect, no switch_page)
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="NSE Market Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

from frontend.styles  import inject, CSS
from frontend.session import init_defaults, is_authenticated

inject()
init_defaults()

# DB init (idempotent, once per session)
if not st.session_state.get("db_ready"):
    from backend.db_init import ensure_db
    ensure_db()
    st.session_state["db_ready"] = True

# ── MAGIC LINK CALLBACK (Supabase redirects here with tokens in URL) ─────────
# Supabase appends ?access_token=...&refresh_token=...&type=signup to the URL
# st.query_params captures these on page load.
if not is_authenticated():
    try:
        _qp = st.query_params
        _at = _qp.get("access_token", "")
        _rt = _qp.get("refresh_token", "")
        _tp = _qp.get("type", "")
        if _at and _tp in ("signup", "magiclink", "email"):
            from backend.auth import verify_magic_link, load_user_portfolio
            _ok, _msg, _uinfo = verify_magic_link(_at, _rt)
            if _ok and _uinfo:
                st.session_state.update({
                    "logged_in":     True,
                    "authenticated": True,
                    "username":      _uinfo["username"],
                    "user_info":     _uinfo,
                })
                st.session_state["portfolio"] = load_user_portfolio(_uinfo)
                # Clear tokens from URL to avoid re-processing on refresh
                st.query_params.clear()
                st.rerun()
    except Exception:
        pass

# ── AUTH GATE ─────────────────────────────────────────────────────────────────
if not is_authenticated():
    st.markdown("""<style>
    [data-testid="stSidebar"]    { display:none !important; }
    [data-testid="stSidebarNav"] { display:none !important; }
    section[data-testid="stSidebarNav"] { display:none !important; }
    </style>""", unsafe_allow_html=True)

    from frontend.auth_page import render_auth_page
    authed = render_auth_page()
    if authed:
        st.rerun()   # one clean rerun after login — loads dashboard
    st.stop()        # stay on login page

# ── AUTHENTICATED: full app below ─────────────────────────────────────────────
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
from frontend.session  import get_user, get_data, set_data
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

# Session defaults
for k, v in [("selected_index","Nifty 50"), ("from_d",None), ("to_d",None)]:
    if k not in st.session_state:
        st.session_state[k] = v

def _do_logout():
    save_user_portfolio(user, st.session_state.get("portfolio",{}))
    auth_logout(user)
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# ── Header (full-width, self-contained) ───────────────────────────────────────
_idx = st.session_state.get("selected_index","Nifty 50")
_lbl = ""
if st.session_state.get("from_d") and st.session_state.get("to_d"):
    _lbl = f"{st.session_state['from_d'].strftime('%d %b %Y')} → {st.session_state['to_d'].strftime('%d %b %Y')}"
render_header(_lbl, index_name=_idx,
              stock_count=len(INDEX_UNIVERSE.get(_idx,{})),
              user=user)
_, _logout_col = st.columns([9, 1])
with _logout_col:
    if st.button("⏻ Logout", key="logout_header", use_container_width=True):
        _do_logout()

# ── Analysis controls ─────────────────────────────────────────────────────────
today = date.today()
st.markdown('<div class="ctrl-panel">', unsafe_allow_html=True)
c0,c1,c2,c3,c4,c5 = st.columns([2.2,2,2,2,1.4,1.4])
with c0:
    prev = st.session_state.get("selected_index","Nifty 50")
    sel  = st.selectbox("Index / Universe", INDEX_OPTIONS,
                        index=INDEX_OPTIONS.index(prev), key="idx_sel")
    if sel != prev:
        for k in ["data","from_d","to_d","bt_result","corr_result"]:
            st.session_state.pop(k, None)
        st.session_state["selected_index"] = sel
        st.rerun()
with c1:
    preset = st.selectbox("Quick Preset",
        ["1 Month","1 Week","2 Weeks","3 Months","6 Months","YTD","Custom"])
_pm = {"1 Week":timedelta(7),"2 Weeks":timedelta(14),"1 Month":timedelta(30),
       "3 Months":timedelta(90),"6 Months":timedelta(180)}
dfrom = date(today.year,1,1) if preset=="YTD" else today-_pm.get(preset,timedelta(30))
with c2:
    from_d = st.date_input("From", value=dfrom, max_value=today-timedelta(days=2))
with c3:
    to_d   = st.date_input("To",   value=today,  max_value=today)
with c4:
    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    run = st.button("▶  ANALYSE", use_container_width=True, type="primary")
with c5:
    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
    refresh = st.button("⟳  REFRESH", use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

if from_d >= to_d:
    st.error("⚠  'From' date must be before 'To'.")
    st.stop()

if refresh:
    fetch_ohlcv.clear(); fetch_sentiment_data.clear()
    for k in ["data","from_d","to_d"]: st.session_state.pop(k,None)
    st.rerun()

if run:
    _uni   = INDEX_UNIVERSE.get(st.session_state.get("selected_index","Nifty 50"),
                                 INDEX_UNIVERSE["Nifty 50"])
    total  = len(_uni)
    prog   = st.progress(0, text=f"Fetching {total} stocks…")
    def _prog(i,sym,tot=total): prog.progress((i+1)/tot, text=f"Fetching {sym}.NS ({i+1}/{tot})")
    stats  = fetch_all(from_d, to_d, _prog, stocks=_uni)
    prog.empty()
    if not stats:
        st.error("⚠  No data returned. Check connection or try different dates.")
        st.stop()
    with st.spinner(f"Training ML model ({total} stocks)…"):
        enriched = predict(stats, universe=_uni)
    set_data(enriched, from_d, to_d)
    st.rerun()

# ── Portfolio tab ─────────────────────────────────────────────────────────────
def _portfolio_tab():
    h,sc,rc = st.columns([6,1.2,1.2])
    with h:  render_section("My Portfolio", f"Live P&L · {user.get('name','')}")
    with sc:
        st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
        if st.button("💾 Save", key="pf_save", use_container_width=True, type="primary"):
            ok,msg = _persist()
            st.success("✅ Saved!") if ok else st.error(f"❌ {msg}")
    with rc:
        st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Reload", key="pf_reload", use_container_width=True):
            ok,msg = reload_portfolio_from_db()
            st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")
            if ok: st.rerun()

    pf   = st.session_state.get("portfolio",{})
    _uni = INDEX_UNIVERSE.get(st.session_state.get("selected_index","Nifty 50"),
                               INDEX_UNIVERSE["Nifty 50"])
    res  = render_add_holding_form(universe=_uni)
    if res:
        sym,qty,price,bdate = res
        add_holding(sym,qty,price,bdate)
        ok,msg = _persist()
        st.success(f"✅ Added {qty}×{sym}") if ok else st.warning(f"Added locally. {msg}")
        st.rerun()

    if not pf:
        render_empty_state(); return

    with st.spinner("Live prices…"):
        live = fetch_live_prices(tuple(pf.keys()))
    rows,totals = compute_portfolio_pnl(pf,live)
    rows = get_portfolio_advice(rows, st.session_state.get("data"))
    render_portfolio_summary_v2(totals)
    render_section("ML Advisor", f"{len(rows)} holdings")
    if not st.session_state.get("data"):
        st.info("💡 Run ▶ ANALYSE for ML-powered advice.")
    render_advice_cards(rows)
    st.markdown("<br>", unsafe_allow_html=True)
    render_section("Holdings Detail")
    render_holdings_table(rows)
    rm = render_manage_holdings(rows)
    if rm:
        remove_holding(rm)
        ok, msg = _persist()
        st.success(f"✅ Removed {rm}") if ok else st.warning(f"Removed. {msg}")
        st.rerun()
    st.markdown("<br>", unsafe_allow_html=True)
    render_portfolio_io(pf)

# ── Tabs ──────────────────────────────────────────────────────────────────────
_adm  = is_admin(user)
_tdefs = ["📈  Gainers","📉  Losers","🤖  AI Signals","📋  All Stocks",
          "💼  Portfolio","🗺  Heatmap","📊  Backtest","🔗  Correlations",
          "📅  Events","📰  News","📈  Index Charts","🌍  Global Sentiment"]
if _adm: _tdefs.append("🛡  Admin")
_tabs = st.tabs(_tdefs)
t1,t2,t3,t4,t5,t6,t7,t8,t9,t10,t11,t12 = _tabs[:12]
tadm  = _tabs[12] if _adm else None

data    = st.session_state.get("data")
from_ds = st.session_state.get("from_d")
to_ds   = st.session_state.get("to_d")
lbl     = f"{from_ds.strftime('%d %b %Y')} → {to_ds.strftime('%d %b %Y')}" if from_ds else ""

if not data:
    for t in [t1,t2,t3,t4]:
        with t: render_empty_state()
    with t5:  _portfolio_tab()
    with t6:  render_heatmap_tab([])
    with t7:  render_backtest_tab()
    with t8:  render_correlation_tab()
    with t9:  render_events_tab()
    with t10: render_news_tab([])
    with t11: render_index_charts_tab()
    with t12: render_global_sentiment_section()
    if tadm:
        with tadm: render_admin_dashboard()
    st.stop()

gainers = sorted(data, key=lambda x: x["change_pct"], reverse=True)
losers  = sorted(data, key=lambda x: x["change_pct"])
preds   = sorted(data, key=lambda x: x.get("final_score",0), reverse=True)
render_stat_bar(data)

xlsx = generate(data, gainers[:10], losers[:10], preds, from_ds, to_ds)
dc,ic,_ = st.columns([2,5,3])
with dc:
    st.download_button("📥 Download Excel",data=xlsx,
        file_name=f"NSE_{from_ds}_{to_ds}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True)
with ic:
    st.markdown(f'<div style="padding-top:10px;font-family:IBM Plex Mono,monospace;'
                f'font-size:10px;color:#5a5e8a">6 sheets · {lbl}</div>',
                unsafe_allow_html=True)

with t1:
    render_section("Top Gainers", lbl); render_gainer_cards(gainers[:10])
    st.markdown("<br>",unsafe_allow_html=True); render_movers_table(gainers[:10])
with t2:
    render_section("Top Losers", lbl); render_loser_cards(losers[:10])
    st.markdown("<br>",unsafe_allow_html=True); render_movers_table(losers[:10])
with t3:
    render_section("AI Predictions","RF+GB+Ridge · Sentiment")
    n_rows = data[0].get("training_rows",0) if data else 0
    if n_rows:
        n_stk = data[0].get("training_stocks",0)
        n_ft  = data[0].get("n_features",0)
        _ci   = st.session_state.get("selected_index","Nifty 50")
        st.markdown(
            f'<div style="margin-bottom:16px;padding:10px 16px;background:#0a1a10;'
            f'border:1px solid #1a3a28;border-radius:6px;font-family:IBM Plex Mono,monospace;'
            f'font-size:11px;color:#6b6b80"><span style="color:#00e5a0">✓ {n_rows:,} rows</span>'
            f' · {n_stk} stocks × 5yr ({_ci}) · {n_ft} features · RF 40%+GB 40%+Ridge 20%</div>',
            unsafe_allow_html=True)
    buys = [s for s in preds if "BUY" in s.get("signal","")]
    if buys:
        render_section("Top Buy Signals",f"{len(buys)} stocks")
        render_prediction_cards(buys[:5])
        st.markdown("<br>",unsafe_allow_html=True)
    render_predictions_table(preds)
with t4:
    render_section("All Stocks",f"{len(data)} stocks")
    render_all_stocks_table(data)
with t5:  _portfolio_tab()
with t6:  render_heatmap_tab(data)
with t7:  render_backtest_tab()
with t8:  render_correlation_tab(portfolio_symbols=list(st.session_state.get("portfolio",{}).keys()))
with t9:  render_events_tab()
with t10: render_news_tab(data)
with t11: render_index_charts_tab()
with t12: render_global_sentiment_section()
if tadm:
    with tadm: render_admin_dashboard()
