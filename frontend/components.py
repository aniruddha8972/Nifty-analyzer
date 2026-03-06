"""
frontend/components.py
───────────────────────
Reusable Streamlit UI rendering functions.
Keeps app.py clean — all HTML/CSS generation lives here.
"""

import streamlit as st
from typing import Dict, List
from backend.data_engine import StockData, trading_days_estimate
from backend.ai_model import StockAnalysis

# ── Colour map ────────────────────────────────────────────────────────────────
REC_COLORS = {
    "STRONG BUY":  "#10b981",
    "BUY":         "#34d399",
    "HOLD":        "#f59e0b",
    "SELL":        "#f87171",
    "STRONG SELL": "#ef4444",
}
RISK_COLORS = {
    "Low":      "#00e5a0",
    "Medium":   "#f59e0b",
    "Med-High": "#ff5472",
    "High":     "#ff5472",
}


# ── CSS injection ─────────────────────────────────────────────────────────────
def inject_css() -> None:
    st.markdown("""
    <style>
    /* ── Global ── */
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Space Grotesk', system-ui, sans-serif !important;
        background: #07080d !important;
    }
    .main { background: #07080d !important; }
    .block-container { padding-top: 1.5rem !important; max-width: 1200px !important; }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #0c0d14 !important;
        border-right: 1px solid rgba(255,255,255,0.07) !important;
    }
    [data-testid="stSidebar"] * { color: #e0e0e0 !important; }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 12px 16px !important;
    }
    [data-testid="stMetricValue"]  { color: #f0f0f0 !important; font-size: 1.3rem !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"]  { color: #555 !important; font-size: 0.75rem !important; letter-spacing: 1.5px; text-transform: uppercase; }
    [data-testid="stMetricDelta"]  { font-size: 0.8rem !important; font-weight: 700 !important; }

    /* ── Tabs ── */
    [data-testid="stTabs"] button {
        font-weight: 700 !important;
        color: #555 !important;
        border-radius: 8px 8px 0 0 !important;
        background: transparent !important;
    }
    [data-testid="stTabs"] button[aria-selected="true"] {
        color: #00e5a0 !important;
        border-bottom: 2px solid #00e5a0 !important;
        background: rgba(0,229,160,0.07) !important;
    }

    /* ── Date inputs ── */
    [data-testid="stDateInput"] input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 8px !important;
        color: #e0e0e0 !important;
    }
    [data-testid="stDateInput"] label { color: #666 !important; font-size: 0.75rem !important; }

    /* ── Buttons ── */
    .stButton button {
        background: linear-gradient(135deg, #0d5233, #00e5a0) !important;
        color: #040a07 !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 8px !important;
        letter-spacing: 0.4px !important;
        transition: all 0.2s !important;
        box-shadow: 0 3px 16px rgba(0,229,160,0.2) !important;
    }
    .stButton button:hover { box-shadow: 0 5px 22px rgba(0,229,160,0.38) !important; transform: translateY(-1px) !important; }

    /* ── Download button ── */
    [data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #155233, #00e5a0) !important;
        color: #040a07 !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0 3px 16px rgba(0,229,160,0.2) !important;
    }

    /* ── Select / Radio ── */
    [data-testid="stRadio"] label { color: #aaa !important; font-weight: 600 !important; }
    [data-testid="stSelectbox"] { background: rgba(255,255,255,0.04) !important; }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: rgba(255,255,255,0.025) !important;
        border: 1px solid rgba(255,255,255,0.07) !important;
        border-radius: 10px !important;
    }
    [data-testid="stExpander"] summary { color: #ccc !important; font-weight: 700 !important; }

    /* ── Divider ── */
    hr { border-color: rgba(255,255,255,0.07) !important; }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0a0b0f; }
    ::-webkit-scrollbar-thumb { background: #1f2937; border-radius: 3px; }

    /* ── Custom card ── */
    .nf-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
        border-radius: 12px; padding: 14px 16px; margin-bottom: 10px;
        position: relative; overflow: hidden;
        transition: transform 0.18s, box-shadow 0.18s;
    }
    .nf-card:hover { transform: translateY(-2px); }
    .nf-accent { position: absolute; top: 0; left: 0; width: 3px; height: 100%; border-radius: 3px 0 0 3px; }
    .nf-sym  { font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 700; color: #f0f0f0; }
    .nf-sect { background: rgba(255,255,255,0.07); color: #777; font-size: 10px; padding: 2px 8px; border-radius: 16px; font-weight: 600; margin-left: 6px; }
    .nf-pct  { font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 900; }
    .nf-met  { font-size: 11px; color: #888; }
    .nf-pill { display: inline-block; background: rgba(255,255,255,0.04); color: #555; font-size: 9.5px; padding: 2px 8px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.07); margin: 2px 2px 0 0; }
    .nf-rec  { display: inline-block; padding: 3px 11px; border-radius: 6px; font-size: 11px; font-weight: 800; }
    .nf-mval { font-size: 12px; font-weight: 700; color: #bbb; }
    .nf-mlbl { font-size: 9px; color: #444; text-transform: uppercase; letter-spacing: 0.5px; }
    </style>
    """, unsafe_allow_html=True)


# ── Header ────────────────────────────────────────────────────────────────────
def render_header(date_label: str = "", status: str = "IDLE") -> None:
    status_col = "#00e5a0" if status == "READY" else "#ff5472" if status == "ERROR" else "#555"
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;align-items:flex-start;
         padding:4px 0 18px;border-bottom:1px solid rgba(255,255,255,0.07);margin-bottom:20px">
      <div>
        <div style="display:flex;align-items:center;gap:8px;font-size:10px;font-weight:800;
             letter-spacing:3px;color:#00e5a0;text-transform:uppercase;margin-bottom:4px">
          <div style="width:7px;height:7px;border-radius:50%;background:#00e5a0;
               box-shadow:0 0 8px #00e5a0"></div>NSE India · Nifty 50
        </div>
        <h1 style="font-size:26px;font-weight:900;letter-spacing:-0.5px;color:#f0f0f0;margin:0">
          Market <span style="color:#00e5a0">Analyzer</span>
        </h1>
        <p style="color:#333;font-size:12px;margin:3px 0 0">
          Custom date range · AI scoring model · Excel export · No API key
        </p>
      </div>
      <div style="text-align:right">
        <div style="display:flex;align-items:center;gap:6px;font-size:11px;
             font-weight:800;letter-spacing:1.5px;color:{status_col};justify-content:flex-end">
          <div style="width:7px;height:7px;border-radius:50%;background:{status_col}"></div>
          {status}
        </div>
        {f'<div style="color:#444;font-size:11px;margin-top:4px">📅 {date_label}</div>' if date_label else ''}
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Stat bar ──────────────────────────────────────────────────────────────────
def render_stat_bar(
    gainers:  List[StockData],
    losers:   List[StockData],
    combined: List[StockData],
    analyses: Dict[str, StockAnalysis],
    days:     int,
) -> None:
    best = max(combined, key=lambda s: analyses[s.symbol].score)
    avg_g = sum(s.chg_pct for s in gainers) / len(gainers)
    avg_l = sum(s.chg_pct for s in losers)  / len(losers)
    td = trading_days_estimate(days)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📈 Top Gainer",  f"+{gainers[0].chg_pct:.2f}%",  gainers[0].symbol, delta_color="normal")
    with c2:
        st.metric("📉 Top Loser",   f"{losers[0].chg_pct:.2f}%",    losers[0].symbol,  delta_color="inverse")
    with c3:
        st.metric("🤖 AI Best Pick", best.symbol, f"Score {analyses[best.symbol].score}/100")
    with c4:
        st.metric("📅 Period",       f"{days}d · ~{td}T", f"Avg +{avg_g:.2f}% / {avg_l:.2f}%")


# ── Single stock card ─────────────────────────────────────────────────────────
def _stock_card_html(s: StockData, rank: int, a: StockAnalysis, card_type: str) -> str:
    col      = "#00e5a0" if card_type == "gain" else "#ff5472"
    bord     = "rgba(0,229,160,0.15)" if card_type == "gain" else "rgba(255,84,114,0.15)"
    pct_str  = f"+{s.chg_pct:.2f}%" if s.chg_pct >= 0 else f"{s.chg_pct:.2f}%"
    rsi_col  = "#00e5a0" if s.rsi < 35 else "#ff5472" if s.rsi > 70 else "#888"
    rec_col  = REC_COLORS.get(a.recommendation, "#f59e0b")
    risk_col = RISK_COLORS.get(a.risk_level, "#f59e0b")
    vol_m    = f"{s.volume/1e6:.1f}M"

    pills = " ".join(
        f'<span class="nf-pill">{sig}</span>' for sig in a.signals[:3]
    )

    return f"""
    <div class="nf-card" style="border:1px solid {bord}">
      <div class="nf-accent" style="background:{col}"></div>
      <div style="margin-left:10px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
          <div>
            <div style="display:flex;align-items:center;margin-bottom:7px">
              <span style="font-size:11px;color:#3a3a3a;font-weight:700;margin-right:6px">#{rank}</span>
              <span class="nf-sym">{s.symbol}</span>
              <span class="nf-sect">{s.sector}</span>
            </div>
            <div style="display:flex;gap:12px;flex-wrap:wrap">
              <div><div class="nf-mlbl">Close</div><div class="nf-mval">₹{s.close_price:,.2f}</div></div>
              <div><div class="nf-mlbl">Open</div><div class="nf-mval" style="color:#5a5a5a">₹{s.open_price:,.2f}</div></div>
              <div><div class="nf-mlbl">Vol</div><div class="nf-mval" style="color:#5a5a5a">{vol_m}</div></div>
              <div><div class="nf-mlbl">RSI</div><div class="nf-mval" style="color:{rsi_col}">{s.rsi}</div></div>
              <div><div class="nf-mlbl">P/E</div><div class="nf-mval" style="color:#5a5a5a">{s.pe_ratio}x</div></div>
              <div><div class="nf-mlbl">Beta</div><div class="nf-mval" style="color:#5a5a5a">{s.beta}</div></div>
            </div>
          </div>
          <div style="text-align:right;flex-shrink:0;padding-left:10px">
            <div class="nf-pct" style="color:{col}">{pct_str}</div>
            <div class="nf-rec" style="background:{rec_col}25;border:1px solid {rec_col}50;color:{rec_col};margin-top:5px">{a.recommendation}</div>
            <div style="color:#383838;font-size:10px;margin-top:3px">Score {a.score}/100 · <span style="color:{risk_col}">{a.risk_level}</span> risk</div>
          </div>
        </div>
        <div style="margin-top:8px">{pills}</div>
      </div>
    </div>"""


def render_stock_grid(
    stocks:   List[StockData],
    analyses: Dict[str, StockAnalysis],
    card_type: str,
    title:    str,
    title_color: str,
) -> None:
    st.markdown(
        f'<h3 style="color:{title_color};font-weight:800;margin-bottom:14px;font-size:15px">{title}</h3>',
        unsafe_allow_html=True,
    )
    cols = st.columns(2)
    for i, s in enumerate(stocks):
        with cols[i % 2]:
            st.markdown(
                _stock_card_html(s, i + 1, analyses[s.symbol], card_type),
                unsafe_allow_html=True,
            )


# ── AI suggestions tab ────────────────────────────────────────────────────────
def render_ai_tab(
    combined: List[StockData],
    analyses: Dict[str, StockAnalysis],
    date_label: str,
) -> None:
    st.markdown(f"""
    <div style="background:rgba(167,139,250,0.07);border:1px solid rgba(167,139,250,0.2);
         border-radius:11px;padding:15px 18px;margin-bottom:20px;display:flex;gap:11px">
      <div style="font-size:22px;flex-shrink:0">🤖</div>
      <div>
        <div style="color:#a78bfa;font-size:14px;font-weight:800;margin-bottom:3px">
          AI Scoring Model · {date_label}
        </div>
        <p style="color:#4a4a4a;font-size:13px;line-height:1.6;margin:0">
          Each stock scored 0–100 across 9 factors: RSI, momentum, 52W range, volume,
          P/E, beta, dividend, sector &amp; mean-reversion potential.
          <strong style="color:#3a3a3a">Fully self-contained · No API key · Not financial advice.</strong>
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    for rec in ["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]:
        col = REC_COLORS[rec]
        stocks_in_rec = [s for s in combined if analyses[s.symbol].recommendation == rec]
        if not stocks_in_rec:
            continue

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:9px;margin-bottom:10px">
          <div style="width:10px;height:10px;border-radius:50%;background:{col}"></div>
          <span style="color:{col};font-size:14px;font-weight:800">{rec}</span>
          <span style="color:#2e2e2e;font-size:13px">({len(stocks_in_rec)} stock{'s' if len(stocks_in_rec)>1 else ''})</span>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(min(len(stocks_in_rec), 3))
        for i, s in enumerate(stocks_in_rec):
            a = analyses[s.symbol]
            risk_col = RISK_COLORS.get(a.risk_level, "#f59e0b")
            pct = f"+{s.chg_pct:.2f}%" if s.chg_pct >= 0 else f"{s.chg_pct:.2f}%"
            pct_col = "#00e5a0" if s.chg_pct >= 0 else "#ff5472"
            pills = " ".join(f'<span class="nf-pill">{sg}</span>' for sg in a.signals)
            with cols[i % 3]:
                st.markdown(f"""
                <div style="background:rgba(255,255,255,0.03);border:1px solid {col}30;
                     border-radius:9px;padding:13px 15px;margin-bottom:9px">
                  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px">
                    <div>
                      <div style="display:flex;align-items:center;gap:7px;margin-bottom:5px">
                        <span class="nf-sym">{s.symbol}</span>
                        <span class="nf-sect">{s.sector}</span>
                      </div>
                      <div style="display:flex;gap:11px">
                        <span style="color:#888;font-size:12px">₹{s.close_price:,.2f}</span>
                        <span style="color:{pct_col};font-size:12px;font-weight:700">{pct}</span>
                        <span style="color:#383838;font-size:12px">Score: {a.score}/100</span>
                      </div>
                    </div>
                    <div style="text-align:right;flex-shrink:0;padding-left:8px">
                      <div style="font-size:11px;color:#383838">Risk: <span style="color:{risk_col};font-weight:700">{a.risk_level}</span></div>
                      <div style="color:#2a2a2a;font-size:11px;margin-top:2px">β {s.beta} · RSI {s.rsi}</div>
                      <div style="color:#2a2a2a;font-size:11px">P/E {s.pe_ratio}x · Div {s.div_yield}%</div>
                    </div>
                  </div>
                  <div>{pills}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:14px'></div>", unsafe_allow_html=True)
