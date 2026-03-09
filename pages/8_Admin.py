"""pages/8_Admin.py — Admin Dashboard (admin only)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
st.set_page_config(page_title="Admin — NSE Intelligence", page_icon="🛡",
                   layout="wide", initial_sidebar_state="expanded")
from frontend.design  import inject, render_page_hero
from frontend.session import init_defaults, is_authenticated, get_user
from frontend.sidebar import render_sidebar
from backend.auth     import is_admin
inject(); init_defaults()
if not is_authenticated(): st.switch_page("app.py"); st.stop()
if not is_admin(get_user()):
    st.error("⛔ Access denied — Admins only.")
    st.stop()
render_sidebar("admin")
st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important}</style>', unsafe_allow_html=True)
render_page_hero("Administration", "Admin Dashboard", "User management · System overview")
from frontend.admin_dashboard import render_admin_dashboard
render_admin_dashboard()
