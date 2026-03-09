"""pages/7_Charts.py — Live Nifty Index Charts"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
st.set_page_config(page_title="Charts — NSE Intelligence", page_icon="📉",
                   layout="wide", initial_sidebar_state="expanded")
from frontend.design  import inject, render_page_hero
from frontend.session import init_defaults, is_authenticated
from frontend.sidebar import render_sidebar
inject(); init_defaults()
if not is_authenticated(): st.switch_page("app.py"); st.stop()
render_sidebar("charts")
st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important}</style>', unsafe_allow_html=True)

render_page_hero("Index Charts", "Live Market Charts",
                 "Nifty 50 · Next 50 · Midcap · Smallcap · Candlestick + Volume · 6 Timeframes")

from frontend.analytics_components import render_index_charts_tab
render_index_charts_tab()
