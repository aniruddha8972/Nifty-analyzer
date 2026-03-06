"""
app.py — Nifty 50 Market Analyzer
───────────────────────────────────
Main Streamlit entry point.

Run locally:
    streamlit run app.py

Deploy to Streamlit Cloud:
    Push repo to GitHub → connect at share.streamlit.io

Architecture:
    app.py          ← Streamlit UI wiring (this file)
    backend/        ← data engine + AI scoring model
    frontend/       ← CSS + HTML component renderers
    pipeline/       ← Excel report generator
    tests/          ← unit tests
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from datetime import date, timedelta
import streamlit as st

from backend.data_engine import (
    clear_cache, get_cache_size,
    fetch_all_stocks, fetch_all_stocks_with_status,
    get_top_gainers, get_top_losers,
    get_date_range_label, trading_days_estimate,
    NIFTY50_SYMBOLS,
)
from backend.ai_model import analyse_all
from frontend.components import (
    inject_css, render_header, render_stat_bar,
    render_stock_grid, render_ai_tab,
)
from pipeline.report_generator import generate_excel_report


# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title  = "Nifty 50 Analyzer",
    page_icon   = "📊",
    layout      = "wide",
    initial_sidebar_state = "expanded",
)

inject_css()


# ── Session state defaults ────────────────────────────────────────────────────
if "results" not in st.session_state:
    st.session_state.results = None
if "status" not in st.session_state:
    st.session_state.status = "IDLE"


# ── Sidebar — Date Range Controls ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding:6px 0 16px">
      <div style="font-size:10px;font-weight:800;letter-spacing:3px;color:#00e5a0;
           text-transform:uppercase;margin-bottom:4px">Settings</div>
      <div style="font-size:18px;font-weight:900;color:#f0f0f0">Date Range</div>
    </div>
    """, unsafe_allow_html=True)

    # Quick presets
    st.markdown('<div style="font-size:11px;color:#444;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px">Quick Presets</div>', unsafe_allow_html=True)

    today = date.today()
    preset_map = {
        "Last Week":  today - timedelta(weeks=1),
        "2 Weeks":    today - timedelta(weeks=2),
        "1 Month":    today - timedelta(days=30),
        "3 Months":   today - timedelta(days=90),
        "6 Months":   today - timedelta(days=180),
        "1 Year":     today - timedelta(days=365),
        "YTD":        date(today.year, 1, 1),
    }

    preset_cols = st.columns(2)
    selected_preset = None
    preset_keys = list(preset_map.keys())
    for i, pkey in enumerate(preset_keys):
        with preset_cols[i % 2]:
            if st.button(pkey, key=f"preset_{pkey}", use_container_width=True):
                selected_preset = pkey

    st.markdown('<hr style="margin:14px 0">', unsafe_allow_html=True)
    st.markdown('<div style="font-size:11px;color:#444;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:8px">Custom Range</div>', unsafe_allow_html=True)

    # Initialise date inputs from preset or default
    if selected_preset:
        default_from = preset_map[selected_preset]
        default_to   = today
    else:
        default_from = st.session_state.get("from_date", today - timedelta(days=30))
        default_to   = st.session_state.get("to_date",   today)

    from_date = st.date_input("From", value=default_from, max_value=today - timedelta(days=1), key="from_date")
    to_date   = st.date_input("To",   value=default_to,   max_value=today, key="to_date")

    # Validate
    if from_date >= to_date:
        st.error("⚠ From date must be before To date")
        valid_range = False
    elif from_date > today:
        st.error("⚠ From date cannot be in the future")
        valid_range = False
    else:
        valid_range = True
        cal_days  = (to_date - from_date).days
        trad_days = trading_days_estimate(cal_days)
        st.markdown(f"""
        <div style="background:rgba(0,229,160,0.07);border:1px solid rgba(0,229,160,0.15);
             border-radius:8px;padding:10px 14px;margin:10px 0">
          <div style="color:#00e5a0;font-size:12px;font-weight:700">
            {cal_days} calendar days
          </div>
          <div style="color:#3a3a3a;font-size:11px;margin-top:2px">
            ~{trad_days} trading days
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr style="margin:14px 0">', unsafe_allow_html=True)

    # Analyse button
    analyse_clicked = st.button(
        "▶  Analyse",
        disabled = not valid_range,
        use_container_width = True,
        key = "analyse_btn",
    )

    # Cache status + Refresh button
    cached = get_cache_size()
    if cached > 0:
        st.markdown(
            f'''<div style="margin-top:8px;padding:8px 12px;background:rgba(0,229,160,0.06);
                border:1px solid rgba(0,229,160,0.12);border-radius:6px;font-size:11px;color:#3a3a3a">
                📦 {cached} ticker(s) cached — results are stable.<br>
                <span style="color:#2a2a2a">Same date range = same output.</span>
            </div>''',
            unsafe_allow_html=True,
        )
        if st.button("🔄  Refresh data", use_container_width=True, key="refresh_btn",
                     help="Clear cache and re-fetch fresh data from Yahoo Finance"):
            clear_cache()
            st.session_state.results = None
            st.session_state.status  = "IDLE"
            st.rerun()
    else:
        st.markdown(
            '<div style="margin-top:8px;font-size:11px;color:#2a2a2a">No cache yet — first run will fetch live data.</div>',
            unsafe_allow_html=True,
        )

    # About
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


# ── Main Area ─────────────────────────────────────────────────────────────────
render_header(
    date_label = get_date_range_label(from_date, to_date) if valid_range else "",
    status     = st.session_state.status,
)

# ── Run analysis when button clicked ─────────────────────────────────────────
# ── CHANGED: replaced st.spinner with a real per-stock progress bar ──────────
# fetch_all_stocks_with_status() is a generator that yields one stock at a time
# so we can show live progress while yfinance fetches each ticker from Yahoo.
if analyse_clicked and valid_range:
    total_syms  = len(NIFTY50_SYMBOLS)
    prog_bar    = st.progress(0, text="Connecting to Yahoo Finance...")
    status_text = st.empty()
    all_stocks  = []

    for sym, idx, data in fetch_all_stocks_with_status(from_date, to_date):
        pct  = (idx + 1) / total_syms
        prog_bar.progress(pct, text=f"Fetching {sym}.NS  ({idx + 1}/{total_syms})")
        status_text.markdown(
            f'<div style="color:#444;font-size:12px;text-align:center">'
            f'Fetching real NSE data via Yahoo Finance…</div>',
            unsafe_allow_html=True,
        )
        if data is not None:
            all_stocks.append(data)

    prog_bar.empty()
    status_text.empty()

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
            fetched   = len(all_stocks),       # how many tickers returned data
        )
        st.session_state.status = "READY"
        st.rerun()


# ── Render results ────────────────────────────────────────────────────────────
if st.session_state.results:
    r = st.session_state.results

    # Stat bar
    render_stat_bar(r["gainers"], r["losers"], r["combined"], r["analyses"], r["days"])

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    # Export button
    col_exp, col_spacer = st.columns([1, 3])
    with col_exp:
        with st.spinner(""):
            xlsx_bytes = generate_excel_report(
                r["gainers"], r["losers"], r["analyses"],
                r["from_date"], r["to_date"],
            )
        fname = f"Nifty50_{r['from_date'].isoformat()}_to_{r['to_date'].isoformat()}.xlsx"
        st.download_button(
            label     = "📥  Export Excel Report",
            data      = xlsx_bytes,
            file_name = fname,
            mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width = True,
        )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # Tabs
    tab_gain, tab_loss, tab_ai = st.tabs(["📈  Top Gainers", "📉  Top Losers", "🤖  AI Suggestions"])

    with tab_gain:
        render_stock_grid(
            r["gainers"], r["analyses"],
            card_type    = "gain",
            title        = f"📈 Top 10 Gainers · {r['label']}",
            title_color  = "#00e5a0",
        )

    with tab_loss:
        render_stock_grid(
            r["losers"], r["analyses"],
            card_type   = "loss",
            title       = f"📉 Top 10 Losers · {r['label']}",
            title_color = "#ff5472",
        )

    with tab_ai:
        render_ai_tab(r["combined"], r["analyses"], r["label"])

else:
    # Empty state
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
