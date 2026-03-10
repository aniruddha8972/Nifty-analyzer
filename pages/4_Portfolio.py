"""pages/4_Portfolio.py — Portfolio Manager"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
st.set_page_config(page_title="Portfolio — NSE Intelligence", page_icon="💼",
                   layout="wide", initial_sidebar_state="expanded")
from frontend.design  import inject, render_page_hero, render_section
from frontend.session import init_defaults, is_authenticated, get_user, get_data
from frontend.sidebar import render_sidebar
inject(); init_defaults()
if not is_authenticated():
    st.error("⛔ Please log in — return to the main page.")
    st.stop()
render_sidebar("portfolio")
st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important}</style>', unsafe_allow_html=True)

render_page_hero("My Portfolio", "Portfolio Manager", "Live P&L · ML Advisor · Import/Export")

from backend.constants import INDEX_UNIVERSE
from backend.portfolio import (add_holding, remove_holding, fetch_live_prices,
                                compute_portfolio_pnl, get_portfolio_advice, _persist,
                                reload_portfolio_from_db)
from backend.auth import save_user_portfolio
from frontend.portfolio_components import (
    render_portfolio_summary_v2, render_holdings_table,
    render_add_holding_form, render_manage_holdings,
    render_advice_cards, render_portfolio_io,
)

user = get_user()

# ── Action bar ─────────────────────────────────────────────────────────────────
hcol, scol, rcol = st.columns([6, 1.3, 1.3])
with hcol:
    last_saved = st.session_state.get("portfolio_last_saved")
    if last_saved:
        st.caption(f"Last synced: {last_saved}")
with scol:
    if st.button("💾 Save", key="pf_save", use_container_width=True, type="primary"):
        ok, msg = _persist()
        st.success("✅ Portfolio saved to cloud!") if ok else st.error(f"❌ {msg}")
with rcol:
    if st.button("🔄 Refresh", key="pf_ref", use_container_width=True):
        with st.spinner("Syncing…"):
            ok, msg = reload_portfolio_from_db()
        (st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}"))
        if ok: st.rerun()

# ── Add holding ────────────────────────────────────────────────────────────────
active_uni = INDEX_UNIVERSE.get(st.session_state.get("selected_index","Nifty 50"),
                                 INDEX_UNIVERSE["Nifty 50"])
result = render_add_holding_form(universe=active_uni)
if result:
    sym, qty, price, buy_date = result
    add_holding(sym, qty, price, buy_date)
    ok, msg = _persist()
    st.success(f"✅ Added {qty}×{sym} @ ₹{price:,.2f}") if ok else st.warning(f"Added locally. {msg}")
    st.rerun()

portfolio = st.session_state.get("portfolio", {})
if not portfolio:
    st.markdown("""
    <div class="fin-empty">
      <div class="fin-empty-icon">💼</div>
      <div class="fin-empty-title">Portfolio is Empty</div>
      <div class="fin-empty-sub">
        Add your first stock above, or click
        <strong style="color:#f0a500">🔄 Refresh</strong> to load cloud holdings.
      </div>
    </div>""", unsafe_allow_html=True)
    st.stop()

with st.spinner("Fetching live prices…"):
    live_prices = fetch_live_prices(tuple(portfolio.keys()))

pnl_rows, totals = compute_portfolio_pnl(portfolio, live_prices)
pnl_rows = get_portfolio_advice(pnl_rows, get_data())

render_portfolio_summary_v2(totals)

render_section("ML ADVISOR — PRIORITY ACTIONS", f"{len(pnl_rows)} holdings")
if not get_data():
    st.info("💡 Run Market Analysis on the Dashboard to get ML-powered advice.")
render_advice_cards(pnl_rows)

st.markdown("<br>", unsafe_allow_html=True)
render_section("HOLDINGS DETAIL", "Live prices · P&L · ML signal")
render_holdings_table(pnl_rows)

to_remove = render_manage_holdings(pnl_rows)
if to_remove:
    remove_holding(to_remove)
    ok, msg = _persist()
    st.success(f"✅ Removed {to_remove}") if ok else st.warning(f"Removed locally. {msg}")
    st.rerun()

st.markdown("<br>", unsafe_allow_html=True)
render_portfolio_io(portfolio)
