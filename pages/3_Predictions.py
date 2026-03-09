"""pages/3_Predictions.py — AI ML Signals"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import streamlit as st
st.set_page_config(page_title="AI Signals — NSE Intelligence", page_icon="🤖",
                   layout="wide", initial_sidebar_state="expanded")
from frontend.design  import inject, render_page_hero, render_section, sig_class
from frontend.session import init_defaults, is_authenticated, get_data, get_index
from frontend.sidebar import render_sidebar
inject(); init_defaults()
if not is_authenticated(): st.switch_page("app.py"); st.stop()
render_sidebar("predictions")
st.markdown('<style>[data-testid="stSidebarNav"]{display:none!important}</style>', unsafe_allow_html=True)

render_page_hero("AI / ML Engine", "Signals & Predictions",
                 "RandomForest 40% + GradientBoosting 40% + Ridge 20% · 5-year training")

data = get_data()
if not data:
    st.markdown("""<div class="fin-empty">
      <div class="fin-empty-icon">🤖</div>
      <div class="fin-empty-title">No Predictions Yet</div>
      <div class="fin-empty-sub">Run analysis on the Dashboard first.</div>
    </div>""", unsafe_allow_html=True)
    if st.button("→ Go to Dashboard", type="primary"): st.switch_page("pages/1_Dashboard.py")
    st.stop()

from frontend.components import render_prediction_cards, render_predictions_table

predictions = sorted(data, key=lambda x: x.get("final_score", 0), reverse=True)
n_rows   = data[0].get("training_rows", 0) if data else 0
n_feats  = data[0].get("n_features", 0) if data else 0
n_stocks = data[0].get("training_stocks", 0) if data else 0

# ML info banner
if n_rows:
    st.markdown(f"""
    <div style="background:#0c0d1a;border:1px solid #1f2240;border-left:3px solid #f0a500;
                border-radius:8px;padding:12px 18px;margin-bottom:20px;
                font-family:'JetBrains Mono',monospace;font-size:10px;color:#5a5e8a">
      <span style="color:#00d4aa">✓ {n_rows:,} training rows</span>
      &nbsp;·&nbsp; {n_stocks} stocks × 5yr OHLCV ({get_index()})
      &nbsp;·&nbsp; {n_feats} features
      &nbsp;·&nbsp; Target = 10-day forward return
      &nbsp;·&nbsp; <span style="color:#f0a500">RF 40% + GB 40% + Ridge 20%</span>
    </div>
    """, unsafe_allow_html=True)

# Signal filter
sig_filter = st.selectbox("Filter by Signal", ["All", "Strong Buy", "Buy", "Hold", "Avoid"], key="sig_fil")
filtered = predictions
if sig_filter != "All":
    filtered = [s for s in predictions if sig_filter.upper() in s.get("signal","").upper()]

# Signal summary
sig_counts = {}
for s in data:
    sig = s.get("signal","")
    for label in ["STRONG BUY","BUY","HOLD","AVOID"]:
        if label in sig:
            sig_counts[label] = sig_counts.get(label,0) + 1
            break

cols = st.columns(4)
for col, (lbl, color) in zip(cols, [
    ("STRONG BUY","#00d4aa"), ("BUY","#00a882"), ("HOLD","#f0a500"), ("AVOID","#ff3d5a")
]):
    cnt = sig_counts.get(lbl, 0)
    col.markdown(f"""
    <div style="background:#0c0d1a;border:1px solid #1f2240;border-top:2px solid {color};
                border-radius:8px;padding:14px;text-align:center">
      <div style="font-family:'JetBrains Mono',monospace;font-size:7px;letter-spacing:2px;
                  text-transform:uppercase;color:#3a3e6a;margin-bottom:6px">{lbl.replace(' ','_')}</div>
      <div style="font-family:'JetBrains Mono',monospace;font-size:28px;font-weight:700;
                  color:{color}">{cnt}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
buy_stocks = [s for s in filtered if "BUY" in s.get("signal","")]
if buy_stocks:
    render_section("TOP BUY SIGNALS", f"{len(buy_stocks)} stocks")
    render_prediction_cards(buy_stocks[:5])
    st.markdown("<br>", unsafe_allow_html=True)

render_section("ALL SIGNALS", f"{len(filtered)} stocks")
render_predictions_table(filtered)
