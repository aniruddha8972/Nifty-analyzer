"""pages/2_Markets.py — Gainers, Losers, All Stocks"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
st.set_page_config(page_title="Markets — NSE Intelligence", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")
from frontend.design  import inject, render_page_hero, render_section
from frontend.session import init_defaults, is_authenticated, get_data
from frontend.sidebar import render_sidebar
inject(); init_defaults()
if not is_authenticated():
    st.error("⛔ Please log in — return to the main page.")
    st.stop()
render_sidebar("markets")
st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important}</style>', unsafe_allow_html=True)

render_page_hero("Market Overview", "Markets", "Top Gainers · Top Losers · All Stocks")

data = get_data()
if not data:
    st.markdown("""
    <div class="fin-empty">
      <div class="fin-empty-icon">📈</div>
      <div class="fin-empty-title">No Analysis Data</div>
      <div class="fin-empty-sub">Run analysis on the Dashboard first.</div>
    </div>""", unsafe_allow_html=True)
    if st.button("→ Go to Dashboard", type="primary"): st.switch_page("pages/1_Dashboard.py")
    st.stop()

from frontend.components import render_gainer_cards, render_loser_cards, render_movers_table, render_all_stocks_table
from_d = st.session_state.get("from_d")
to_d   = st.session_state.get("to_d")
label  = f"{from_d.strftime('%d %b %Y')} → {to_d.strftime('%d %b %Y')}" if from_d else ""

gainers = sorted(data, key=lambda x: x["change_pct"], reverse=True)
losers  = sorted(data, key=lambda x: x["change_pct"])

tab1, tab2, tab3 = st.tabs(["📈  Top Gainers", "📉  Top Losers", "📋  All Stocks"])

with tab1:
    render_section("TOP 10 GAINERS", label)
    render_gainer_cards(gainers[:10])
    st.markdown("<br>", unsafe_allow_html=True)
    render_movers_table(gainers[:10])

with tab2:
    render_section("TOP 10 LOSERS", label)
    render_loser_cards(losers[:10])
    st.markdown("<br>", unsafe_allow_html=True)
    render_movers_table(losers[:10])

with tab3:
    render_section(f"ALL {len(data)} STOCKS", "sorted by return")
    render_all_stocks_table(data)
