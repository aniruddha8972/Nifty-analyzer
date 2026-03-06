"""
app.py — Nifty 50 Market Analyzer
───────────────────────────────────
@st.cache_data is the ONLY cache that works reliably on Streamlit Cloud.

Streamlit Cloud load-balances across multiple worker processes.
An in-memory dict in data_engine.py is per-worker — different workers
have different caches so the same date range hits Yahoo Finance again
and gets slightly different data back each time.

@st.cache_data is Streamlit's shared cross-worker cache. It serializes
the return value and stores it centrally, keyed by function + arguments.
Same (symbol, from_date, to_date) = identical StockData, guaranteed.
TTL=3600 means data auto-refreshes every hour.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
import streamlit as st

from backend.data_engine import (
    _fetch_single_stock_raw,
    get_top_gainers, get_top_losers,
    get_date_range_label, trading_days_estimate,
    NIFTY50_SYMBOLS, StockData,
)
from backend.ai_model import analyse_all
from frontend.components import (
    inject_css, render_header, render_stat_bar,
    render_stock_grid, render_ai_tab,
)
from pipeline.report_generator import generate_excel_report


# ── THE REAL FIX: @st.cache_data wraps the yfinance fetch ─────────────────────
# This cache is shared across ALL Streamlit Cloud workers for this app.
# Calling fetch_stock("TCS", date(2026,2,4), date(2026,3,6)) twice,
# even from different workers, always returns the exact same StockData.
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock(symbol: str, from_date: date, to_date: date):
    """Cached single-stock fetch. TTL=1hr keeps data fresh but stable."""
    return _fetch_single_stock_raw(symbol, from_date, to_date)


def fetch_all_with_progress(from_date: date, to_date: date):
    """Fetch all 50 stocks with a live progress bar. Uses cached fetch_stock."""
    prog  = st.progress(0, text="Connecting to Yahoo Finance…")
    empty = st.empty()
    stocks = []
    for i, sym in enumerate(NIFTY50_SYMBOLS):
        pct = (i + 1) / len(NIFTY50_SYMBOLS)
        prog.progress(pct, text=f"Fetching {sym}.NS  ({i+1}/{len(NIFTY50_SYMBOLS)})")
        empty.markdown(
            '<div style="color:#444;font-size:12px;text-align:center">'
            'Fetching real NSE data via Yahoo Finance…</div>',
            unsafe_allow_html=True,
        )
        data = fetch_stock(sym, from_date, to_date)
        if data is not None:
            stocks.append(data)
    prog.empty()
    empty.empty()
    return stocks


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nifty 50 Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

if "results" not in st.session_state:
    st.session_state.results = None
if "status" not in st.session_state:
    st.session_state.status = "IDLE"


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:6px 0 16px">
      <div style="font-size:10px;font-weight:800;letter-spacing:3px;color:#00e5a0;
           text-transform:uppercase;margin-bottom:4px">Settings</div>
      <div style="font-size:18px;font-weight:900;color:#f0f0f0">Date Range</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="font-size:11px;color:#444;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px">Quick Presets</div>', unsafe_allow_html=True)

    today = date.today()
    preset_map = {
        "Last Week": today - timedelta(weeks=1),
        "2 Weeks":   today - timedelta(weeks=2),
        "1 Month":   today - timedelta(days=30),
        "3 Months":  today - timedelta(days=90),
        "6 Months":  today - timedelta(days=180),
        "1 Year":    today - timedelta(days=365),
        "YTD":       date(today.year, 1, 1),
    }

    preset_cols = st.columns(2)
    selected_preset = None
    for i, pkey in enumerate(preset_map):
        with preset_cols[i % 2]:
            if st.button(pkey, key=f"preset_{pkey}", use_container_width=True):
                selected_preset = pkey

    st.markdown('<hr style="margin:14px 0">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#444;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px">Custom Range</div>', unsafe_allow_html=True)

    if selected_preset:
        default_from = preset_map[selected_preset]
        default_to   = today
    else:
        default_from = st.session_state.get("from_date", today - timedelta(days=30))
        default_to   = st.session_state.get("to_date",   today)

    from_date = st.date_input("From", value=default_from, max_value=today - timedelta(days=1), key="from_date")
    to_date   = st.date_input("To",   value=default_to,   max_value=today, key="to_date")

    if from_date >= to_date:
        st.error("⚠ From date must be before To date")
        valid_range = False
    elif from_date > today:
        st.error("⚠ From date cannot be in the future")
        valid_range = False
    else:
        valid_range  = True
        cal_days     = (to_date - from_date).days
        trad_days    = trading_days_estimate(cal_days)
        st.markdown(f"""
        <div style="background:rgba(0,229,160,0.07);border:1px solid rgba(0,229,160,0.15);
             border-radius:8px;padding:10px 14px;margin:10px 0">
          <div style="color:#00e5a0;font-size:12px;font-weight:700">{cal_days} calendar days</div>
          <div style="color:#3a3a3a;font-size:11px;margin-top:2px">~{trad_days} trading days</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="margin:14px 0">', unsafe_allow_html=True)

    analyse_clicked = st.button(
        "▶  Analyse",
        disabled=not valid_range,
        use_container_width=True,
        key="analyse_btn",
    )

    # Refresh button — clears st.cache_data so fresh data is fetched
    if st.button("🔄  Refresh data", use_container_width=True, key="refresh_btn",
                 help="Clear cached data and re-fetch fresh prices from Yahoo Finance"):
        fetch_stock.clear()
        st.session_state.results = None
        st.session_state.status  = "IDLE"
        st.rerun()

    st.markdown("""
    <div style="margin-top:16px;padding-top:14px;border-top:1px solid rgba(255,255,255,0.07)">
      <div style="font-size:10px;color:#2a2a2a;line-height:1.7">
        <strong style="color:#444">Nifty 50 Analyzer</strong><br>
        Real NSE data via yfinance<br>
        AI scoring · Excel export<br><br>
        <strong style="color:#444">Stack</strong><br>
        Python · Streamlit · yfinance<br>
        pandas · openpyxl<br><br>
        <strong style="color:#ff7755">⚠ Disclaimer</strong><br>
        Data sourced from Yahoo Finance.<br>
        Not financial advice. Always consult
        a SEBI-registered advisor.
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
render_header(
    date_label=get_date_range_label(from_date, to_date) if valid_range else "",
    status=st.session_state.status,
)

# ── Run analysis ──────────────────────────────────────────────────────────────
if analyse_clicked and valid_range:
    all_stocks = fetch_all_with_progress(from_date, to_date)

    if not all_stocks:
        st.error("⚠ No data returned from Yahoo Finance. Check your internet connection or try a different date range.")
    else:
        all_stocks.sort(key=lambda s: s.chg_pct, reverse=True)
        gainers  = get_top_gainers(all_stocks)
        losers   = get_top_losers(all_stocks)
        combined = gainers + losers
        analyses = analyse_all(combined)
        cal_days = (to_date - from_date).days

        st.session_state.results = dict(
            gainers   = gainers,
            losers    = losers,
            combined  = combined,
            analyses  = analyses,
            from_date = from_date,
            to_date   = to_date,
            days      = cal_days,
            label     = get_date_range_label(from_date, to_date),
        )
        st.session_state.status = "READY"
        st.rerun()


# ── Render results ─────────────────────────────────────────────────────────────
if st.session_state.results:
    r = st.session_state.results

    render_stat_bar(r["gainers"], r["losers"], r["combined"], r["analyses"], r["days"])
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    col_exp, col_spacer = st.columns([1, 3])
    with col_exp:
        xlsx_bytes = generate_excel_report(
            r["gainers"], r["losers"], r["analyses"],
            r["from_date"], r["to_date"],
        )
        fname = f"Nifty50_{r['from_date'].isoformat()}_to_{r['to_date'].isoformat()}.xlsx"
        st.download_button(
            label="📥  Export Excel Report",
            data=xlsx_bytes,
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    tab_gain, tab_loss, tab_ai = st.tabs(["📈  Top Gainers", "📉  Top Losers", "🤖  AI Suggestions"])
    with tab_gain:
        render_stock_grid(r["gainers"], r["analyses"], card_type="gain",
                          title=f"📈 Top 10 Gainers · {r['label']}", title_color="#00e5a0")
    with tab_loss:
        render_stock_grid(r["losers"], r["analyses"], card_type="loss",
                          title=f"📉 Top 10 Losers · {r['label']}", title_color="#ff5472")
    with tab_ai:
        render_ai_tab(r["combined"], r["analyses"], r["label"])

else:
    st.markdown("""
    <div style="text-align:center;padding:80px 20px">
      <div style="font-size:58px;margin-bottom:16px">📅</div>
      <h2 style="color:#222;font-size:21px;font-weight:800;margin-bottom:8px">
        Select a date range &amp; click Analyse
      </h2>
      <p style="color:#2e2e2e;font-size:14px;line-height:1.7">
        Use the <strong style="color:#00e5a0">sidebar</strong> to pick a quick preset<br>
        or set a custom <strong style="color:#00e5a0">From → To</strong> date range,<br>
        then click <strong style="color:#00e5a0">▶ Analyse</strong>
      </p>
    </div>
    """, unsafe_allow_html=True)
