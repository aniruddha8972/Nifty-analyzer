"""
pages/1_Dashboard.py — Main dashboard with analysis controls
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
st.set_page_config(page_title="Dashboard — NSE Intelligence", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

from frontend.design   import inject, render_page_hero, render_section, render_stat_cards
from frontend.session  import (init_defaults, is_authenticated, get_user, get_data,
                                get_index, set_data, clear_analysis)
from frontend.sidebar  import render_sidebar

inject()
init_defaults()

if not is_authenticated():
    st.switch_page("app.py")
    st.stop()

render_sidebar("dashboard")

from datetime import date, timedelta
from backend.data      import fetch_all, fetch_ohlcv
from backend.constants import INDEX_OPTIONS, INDEX_UNIVERSE, INDEX_BADGE
from backend.ml        import predict, fetch_sentiment_data
from pipeline.report   import generate

st.markdown("""
<style>
[data-testid="stSidebarNav"] { display:none !important; }
section[data-testid="stSidebarNav"] { display:none !important; }
</style>
""", unsafe_allow_html=True)

# ── Page hero ──────────────────────────────────────────────────────────────────
render_page_hero(
    "NSE Market Intelligence",
    "Dashboard",
    "Run analysis · View results · Download report"
)

# ── Ticker strip (top indices) ─────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def _quick_indices():
    import yfinance as yf, pandas as pd
    tickers = {"NIFTY 50": "^NSEI", "BANK NIFTY": "^NSEBANK",
               "NIFTY IT": "^CNXIT", "SENSEX": "^BSESN"}
    out = []
    for name, t in tickers.items():
        try:
            df = yf.download(t, period="2d", interval="1d", auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            cl = df["Close"].squeeze().astype(float)
            if len(cl) >= 2:
                last, prev = float(cl.iloc[-1]), float(cl.iloc[-2])
                chg = (last - prev) / prev * 100
                out.append({"name": name, "val": last, "chg": chg})
        except Exception:
            pass
    return out

with st.spinner(""):
    indices = _quick_indices()

if indices:
    items_html = ""
    for idx in indices:
        chg_cls = "ticker-chg-pos" if idx["chg"] >= 0 else "ticker-chg-neg"
        arrow   = "▲" if idx["chg"] >= 0 else "▼"
        items_html += f"""
        <div class="ticker-item">
          <span class="ticker-sym">{idx['name']}</span>
          <span class="ticker-val">{idx['val']:,.0f}</span>
          <span class="{chg_cls}">{arrow} {idx['chg']:+.2f}%</span>
        </div>
        <div style="width:1px;height:20px;background:#1f2240;flex-shrink:0"></div>
        """
    st.markdown(f'<div class="ticker-strip">{items_html}</div>', unsafe_allow_html=True)

# ── Control panel ──────────────────────────────────────────────────────────────
st.markdown('<div class="control-panel">', unsafe_allow_html=True)

today = date.today()
c0, c1, c2, c3, c4, c5 = st.columns([2.4, 2, 1.8, 1.8, 1.3, 1.3])

with c0:
    prev_idx = get_index()
    sel_idx  = st.selectbox("Index / Universe", INDEX_OPTIONS,
                             index=INDEX_OPTIONS.index(prev_idx), key="idx_sel")
    if sel_idx != prev_idx:
        clear_analysis()
        st.session_state["selected_index"] = sel_idx
        st.rerun()

with c1:
    preset = st.selectbox("Quick Preset",
                           ["1 Month","1 Week","2 Weeks","3 Months","6 Months","YTD","Custom"])

preset_map = {"1 Week": timedelta(weeks=1), "2 Weeks": timedelta(weeks=2),
              "1 Month": timedelta(days=30), "3 Months": timedelta(days=90),
              "6 Months": timedelta(days=180)}
if preset == "YTD":     dfrom = date(today.year, 1, 1)
elif preset in preset_map: dfrom = today - preset_map[preset]
else:                   dfrom = today - timedelta(days=30)

with c2:
    from_d = st.date_input("From", value=dfrom, max_value=today - timedelta(days=2))
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
    fetch_ohlcv.clear()
    fetch_sentiment_data.clear()
    clear_analysis()
    st.rerun()

# ── Run analysis ───────────────────────────────────────────────────────────────
if run:
    __universe  = INDEX_UNIVERSE.get(sel_idx, INDEX_UNIVERSE["Nifty 50"])
    total     = len(universe)
    prog = st.progress(0, text=f"Initialising {sel_idx} ({total} stocks)…")

    def _prog(i, sym, tot=total):
        prog.progress((i+1)/tot, text=f"Fetching {sym}.NS ({i+1}/{tot})")

    all_stats = fetch_all(from_d, to_d, _prog, stocks=_universe)
    prog.empty()
    if not all_stats:
        st.error("⚠ No data. Check internet or try a different date range.")
        st.stop()

    with st.spinner(f"Training ML · {sel_idx} · {total} stocks · first run ~60s…"):
        enriched = predict(all_stats, universe=_universe)

    set_data(enriched, from_d, to_d)
    st.rerun()

# ── If data exists — show summary dashboard ───────────────────────────────────
data   = get_data()
from_d = st.session_state.get("from_d")
to_d   = st.session_state.get("to_d")

if not data:
    st.markdown("""
    <div class="fin-empty">
      <div class="fin-empty-icon">📊</div>
      <div class="fin-empty-title">No Analysis Yet</div>
      <div class="fin-empty-sub">
        Select an index, set a date range, and click
        <strong style="color:#f0a500">▶ ANALYSE</strong> to run
        ML-powered market analysis.
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Summary stats
label    = f"{from_d.strftime('%d %b %Y')} → {to_d.strftime('%d %b %Y')}"
changes  = [s["change_pct"] for s in data]
gainers  = sum(1 for c in changes if c > 0)
losers   = sum(1 for c in changes if c < 0)
avg_ret  = sum(changes) / len(changes)
buys     = sum(1 for s in data if "BUY" in s.get("signal", ""))
tg       = max(data, key=lambda x: x["change_pct"])
tl       = min(data, key=lambda x: x["change_pct"])

render_stat_cards([
    {"label": "Stocks Analysed", "value": len(data),
     "delta": label, "accent": "amber"},
    {"label": "Avg Return",
     "value": f"{avg_ret:+.2f}%",
     "delta": f"Period performance",
     "val_color": "var(--teal)" if avg_ret >= 0 else "var(--red)",
     "accent": "teal" if avg_ret >= 0 else "red"},
    {"label": "Gainers / Losers",
     "value": f"{gainers} / {losers}",
     "delta": f"{gainers/(gainers+losers)*100:.0f}% bullish",
     "accent": "teal"},
    {"label": "Buy Signals",
     "value": buys,
     "delta": f"Strong Buy: {sum(1 for s in data if 'STRONG BUY' in s.get('signal',''))}",
     "val_color": "var(--teal)",
     "accent": "teal"},
])

# Top movers mini-section
render_section("TOP MOVERS", label)
mcol1, mcol2 = st.columns(2)

with mcol1:
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:8px;
                letter-spacing:2px;text-transform:uppercase;color:#00d4aa;
                margin-bottom:10px">▲ Top Gainers</div>
    """, unsafe_allow_html=True)
    for s in sorted(data, key=lambda x: x["change_pct"], reverse=True)[:5]:
        chg = s["change_pct"]
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:10px 14px;background:#0c0d1a;border:1px solid #1f2240;
                    border-left:2px solid #00d4aa;border-radius:8px;margin-bottom:6px">
          <div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;
                        font-weight:700;color:#e8e9f5">{s['symbol']}</div>
            <div style="font-family:'DM Sans',sans-serif;font-size:9px;color:#3a3e6a">{s['sector']}</div>
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:16px;
                      font-weight:700;color:#00d4aa">{chg:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

with mcol2:
    st.markdown("""
    <div style="font-family:'JetBrains Mono',monospace;font-size:8px;
                letter-spacing:2px;text-transform:uppercase;color:#ff3d5a;
                margin-bottom:10px">▼ Top Losers</div>
    """, unsafe_allow_html=True)
    for s in sorted(data, key=lambda x: x["change_pct"])[:5]:
        chg = s["change_pct"]
        st.markdown(f"""
        <div style="display:flex;justify-content:space-between;align-items:center;
                    padding:10px 14px;background:#0c0d1a;border:1px solid #1f2240;
                    border-left:2px solid #ff3d5a;border-radius:8px;margin-bottom:6px">
          <div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;
                        font-weight:700;color:#e8e9f5">{s['symbol']}</div>
            <div style="font-family:'DM Sans',sans-serif;font-size:9px;color:#3a3e6a">{s['sector']}</div>
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:16px;
                      font-weight:700;color:#ff3d5a">{chg:+.2f}%</div>
        </div>
        """, unsafe_allow_html=True)

# Quick nav to other pages
render_section("QUICK ACCESS", "Navigate to detailed views")
qc = st.columns(5)
page_links = [
    ("pages/2_Markets.py",     "📈", "Markets",    "Gainers · Losers · All Stocks"),
    ("pages/3_Predictions.py", "🤖", "AI Signals", "ML Buy/Sell Signals"),
    ("pages/4_Portfolio.py",   "💼", "Portfolio",  "P&L · Advisor"),
    ("pages/5_Analytics.py",   "🗺", "Analytics",  "Heatmap · Backtest"),
    ("pages/6_News.py",        "📰", "News",       "Sentiment · Global"),
]
for col, (pg, ic, lbl, desc) in zip(qc, page_links):
    with col:
        st.markdown(f"""
        <div style="background:#0c0d1a;border:1px solid #1f2240;border-radius:10px;
                    padding:16px;text-align:center;margin-bottom:8px">
          <div style="font-size:24px;margin-bottom:8px">{ic}</div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                      font-weight:700;color:#e8e9f5;margin-bottom:4px">{lbl}</div>
          <div style="font-family:'DM Sans',sans-serif;font-size:9px;color:#3a3e6a">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"Open {lbl}", key=f"ql_{lbl}", use_container_width=True):
            st.switch_page(pg)

# ── Download report ────────────────────────────────────────────────────────────
render_section("EXPORT", "Excel report with all data")
sorted_data = sorted(data, key=lambda x: x["change_pct"], reverse=True)
xlsx  = generate(data, sorted_data[:10], sorted_data[-10:],
                 sorted(data, key=lambda x: x.get("final_score",0), reverse=True),
                 from_d, to_d)
dcol, icol, _ = st.columns([2, 5, 3])
with dcol:
    st.download_button(
        "📥  Download Excel Report",
        data=xlsx,
        file_name=f"NSE_{get_index().replace(' ','_')}_{from_d}_{to_d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
with icol:
    st.markdown(
        f'<div style="padding-top:12px;font-family:\'JetBrains Mono\',monospace;'
        f'font-size:10px;color:#3a3e6a">6 sheets · Gainers · Losers · '
        f'Predictions · Charts · News · Summary · {label}</div>',
        unsafe_allow_html=True,
    )
