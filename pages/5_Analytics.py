"""pages/5_Analytics.py — Heatmap, Backtest, Correlations, Events"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
st.set_page_config(page_title="Analytics — NSE Intelligence", page_icon="🗺",
                   layout="wide", initial_sidebar_state="expanded")
from frontend.design  import inject, render_page_hero
from frontend.session import init_defaults, is_authenticated, get_data
from frontend.sidebar import render_sidebar
inject(); init_defaults()
if not is_authenticated():
    st.error("⛔ Please log in — return to the main page.")
    st.stop()
render_sidebar("analytics")
st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important}</style>', unsafe_allow_html=True)

render_page_hero("Deep Analytics", "Analytics Suite",
                 "Sector Heatmap · Strategy Backtest · Correlations · Event Calendar")

from frontend.analytics_components import (
    render_heatmap_tab, render_backtest_tab,
    render_correlation_tab, render_events_tab,
)
data = get_data() or []
portfolio_syms = list(st.session_state.get("portfolio", {}).keys())

tab1, tab2, tab3, tab4 = st.tabs([
    "🗺  Sector Heatmap", "📊  Strategy Backtest",
    "🔗  Correlations",   "📅  Economic Events",
])
with tab1: render_heatmap_tab(data)
with tab2: render_backtest_tab()
with tab3: render_correlation_tab(portfolio_symbols=portfolio_syms)
with tab4: render_events_tab()
