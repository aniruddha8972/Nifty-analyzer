"""pages/6_News.py — News Feed + Global Sentiment"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
st.set_page_config(page_title="News — NSE Intelligence", page_icon="📰",
                   layout="wide", initial_sidebar_state="expanded")
from frontend.design  import inject, render_page_hero
from frontend.session import init_defaults, is_authenticated, get_data
from frontend.sidebar import render_sidebar
inject(); init_defaults()
if not is_authenticated(): st.switch_page("app.py"); st.stop()
render_sidebar("news")
st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important}</style>', unsafe_allow_html=True)

render_page_hero("Market Intelligence", "News & Sentiment",
                 "Stock news feed · Global macro sentiment · 8 RSS sources")

from frontend.analytics_components import render_news_tab, render_global_sentiment_section
data = get_data() or []

tab1, tab2 = st.tabs(["📰  Stock News Feed", "🌍  Global Macro Sentiment"])
with tab1: render_news_tab(data)
with tab2: render_global_sentiment_section()
