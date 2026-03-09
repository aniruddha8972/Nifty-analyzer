"""
app.py — NSE Market Intelligence
Entry point / Auth gate.
• Not authenticated → shows premium two-column login page
• Authenticated     → redirects to Dashboard
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

st.set_page_config(
    page_title="NSE Market Intelligence — Login",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

from frontend.design  import inject
from frontend.session import init_defaults, is_authenticated

inject()
init_defaults()

if not st.session_state.get("db_ready"):
    from backend.db_init import ensure_db
    ensure_db()
    st.session_state["db_ready"] = True

if is_authenticated():
    st.switch_page("pages/1_Dashboard.py")
    st.stop()

from frontend.auth_page import render_auth_page

st.markdown("""
<style>
[data-testid="stSidebar"],[data-testid="stSidebarNav"] { display:none !important; }
section[data-testid="stSidebarNav"] { display:none !important; }
[data-testid="stMainBlockContainer"] { max-width:100%!important; padding:0!important; }
</style>
""", unsafe_allow_html=True)

left, gap, right = st.columns([5, 1, 4])

with left:
    st.markdown("""
    <div style="min-height:100vh;display:flex;flex-direction:column;
                justify-content:center;padding:60px 40px 60px 60px;
                background:linear-gradient(135deg,rgba(240,165,0,0.03) 0%,transparent 60%)">
      <div style="font-family:'JetBrains Mono',monospace;font-size:9px;
                  letter-spacing:3px;text-transform:uppercase;color:#f0a500;
                  margin-bottom:20px;display:flex;align-items:center;gap:10px">
        <div style="width:28px;height:1px;background:#f0a500;opacity:.5"></div>
        NSE · Market Intelligence Platform
      </div>
      <div style="font-family:'Syne',sans-serif;font-size:52px;font-weight:800;
                  line-height:1.05;letter-spacing:-1.5px;color:#e8e9f5;margin-bottom:24px">
        Institutional<br><span style="color:#f0a500">Grade</span> Market<br>Intelligence
      </div>
      <div style="font-family:'DM Sans',sans-serif;font-size:15px;color:#5a5e8a;
                  line-height:1.8;max-width:420px;margin-bottom:40px">
        ML ensemble signals · Live sentiment analysis · Portfolio management
        for India's top 500 stocks. Built for serious traders.
      </div>
      <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:48px">
        <span style="background:rgba(240,165,0,0.08);border:1px solid rgba(240,165,0,0.2);
                     border-radius:20px;padding:6px 14px;font-family:'JetBrains Mono',monospace;
                     font-size:9px;letter-spacing:1.5px;color:#f0a500">📊 Nifty 50 / 500</span>
        <span style="background:rgba(0,212,170,0.07);border:1px solid rgba(0,212,170,0.2);
                     border-radius:20px;padding:6px 14px;font-family:'JetBrains Mono',monospace;
                     font-size:9px;letter-spacing:1.5px;color:#00d4aa">🤖 ML Signals</span>
        <span style="background:rgba(91,143,255,0.08);border:1px solid rgba(91,143,255,0.2);
                     border-radius:20px;padding:6px 14px;font-family:'JetBrains Mono',monospace;
                     font-size:9px;letter-spacing:1.5px;color:#5b8fff">📰 Live Sentiment</span>
        <span style="background:rgba(240,165,0,0.06);border:1px solid rgba(240,165,0,0.15);
                     border-radius:20px;padding:6px 14px;font-family:'JetBrains Mono',monospace;
                     font-size:9px;letter-spacing:1.5px;color:#cc8800">💼 Portfolio P&L</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;max-width:360px">
        <div style="background:#0c0d1a;border:1px solid #1f2240;border-radius:8px;padding:12px 14px">
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:2px;
                      color:#2e315c;text-transform:uppercase;margin-bottom:4px">Universe</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;
                      color:#f0a500">Nifty 500</div>
          <div style="font-size:9px;color:#3a3e6a;margin-top:2px">407 stocks tracked</div>
        </div>
        <div style="background:#0c0d1a;border:1px solid #1f2240;border-radius:8px;padding:12px 14px">
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:2px;
                      color:#2e315c;text-transform:uppercase;margin-bottom:4px">ML Engine</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;
                      color:#00d4aa">RF + GB + Ridge</div>
          <div style="font-size:9px;color:#3a3e6a;margin-top:2px">Ensemble model</div>
        </div>
        <div style="background:#0c0d1a;border:1px solid #1f2240;border-radius:8px;padding:12px 14px">
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:2px;
                      color:#2e315c;text-transform:uppercase;margin-bottom:4px">History</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;
                      color:#5b8fff">5 Years</div>
          <div style="font-size:9px;color:#3a3e6a;margin-top:2px">Daily OHLCV</div>
        </div>
        <div style="background:#0c0d1a;border:1px solid #1f2240;border-radius:8px;padding:12px 14px">
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:2px;
                      color:#2e315c;text-transform:uppercase;margin-bottom:4px">Sentiment</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;
                      color:#f0a500">8 Feeds</div>
          <div style="font-size:9px;color:#3a3e6a;margin-top:2px">Reuters · BBC · ET …</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

with right:
    # Vertical center spacer
    st.markdown('<div style="height:8vh"></div>', unsafe_allow_html=True)
    if render_auth_page():
        st.switch_page("pages/1_Dashboard.py")
