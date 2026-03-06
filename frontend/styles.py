"""
frontend/styles.py
Complete CSS design system for the Nifty 50 Analyzer.

Aesthetic: Terminal-grade financial intelligence.
Inspired by Bloomberg Terminal, trading desks, and quant dashboards.
Monospaced data, neon accents on deep black, scan-line texture.
Font pairing: 'Space Mono' (display) + 'DM Sans' (body).
"""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');

/* ── Reset & Base ─────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:          #050508;
  --bg2:         #0c0c12;
  --bg3:         #12121a;
  --border:      #1e1e2e;
  --border2:     #2a2a3e;
  --green:       #00e5a0;
  --green-dim:   #00a370;
  --green-glow:  rgba(0,229,160,0.12);
  --red:         #ff4560;
  --red-dim:     #cc2040;
  --red-glow:    rgba(255,69,96,0.12);
  --yellow:      #f5a623;
  --yellow-glow: rgba(245,166,35,0.10);
  --blue:        #4e8cff;
  --white:       #e8e8f0;
  --mid:         #6b6b80;
  --dim:         #3a3a4e;
  --mono:        'Space Mono', monospace;
  --sans:        'DM Sans', sans-serif;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  color: var(--white);
  font-family: var(--sans);
}

/* Scanline texture overlay */
[data-testid="stAppViewContainer"]::before {
  content: '';
  position: fixed;
  inset: 0;
  background: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 2px,
    rgba(0,0,0,0.03) 2px,
    rgba(0,0,0,0.03) 4px
  );
  pointer-events: none;
  z-index: 9999;
}

/* ── Sidebar ──────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--bg2) !important;
  border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { font-family: var(--sans) !important; }

/* ── Streamlit element cleanup ────────────────────────────────────── */
[data-testid="stHeader"]          { background: transparent !important; }
[data-testid="stToolbar"]         { display: none !important; }
[data-testid="stDecoration"]      { display: none !important; }
footer                             { display: none !important; }
.stDeployButton                    { display: none !important; }
[data-testid="stMainBlockContainer"] { padding-top: 1rem !important; }

/* ── Typography ───────────────────────────────────────────────────── */
h1, h2, h3, h4 { font-family: var(--mono) !important; color: var(--white) !important; letter-spacing: -0.5px; }
p, span, label  { font-family: var(--sans) !important; }

/* ── Tab styling ──────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
  gap: 4px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 0;
}
[data-testid="stTabs"] [role="tab"] {
  font-family: var(--mono) !important;
  font-size: 12px !important;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--mid) !important;
  background: var(--bg3) !important;
  border: 1px solid var(--border) !important;
  border-bottom: none !important;
  border-radius: 4px 4px 0 0 !important;
  padding: 8px 20px !important;
  transition: all 0.2s ease;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color: var(--green) !important;
  background: var(--bg) !important;
  border-color: var(--green-dim) !important;
  border-bottom: 1px solid var(--bg) !important;
}
[data-testid="stTabs"] [role="tab"]:hover {
  color: var(--white) !important;
}

/* ── Buttons ──────────────────────────────────────────────────────── */
[data-testid="stButton"] > button {
  font-family: var(--mono) !important;
  font-size: 12px !important;
  letter-spacing: 1px;
  text-transform: uppercase;
  background: var(--bg3) !important;
  border: 1px solid var(--border2) !important;
  color: var(--mid) !important;
  border-radius: 4px !important;
  transition: all 0.2s ease !important;
}
[data-testid="stButton"] > button:hover {
  border-color: var(--green) !important;
  color: var(--green) !important;
  box-shadow: 0 0 12px var(--green-glow) !important;
}
[data-testid="stButton"] > button[kind="primary"] {
  background: var(--green) !important;
  color: #050508 !important;
  border-color: var(--green) !important;
  font-weight: 700 !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
  background: #00ffb3 !important;
  box-shadow: 0 0 24px var(--green-glow) !important;
}

/* ── Download button ──────────────────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
  font-family: var(--mono) !important;
  font-size: 12px !important;
  letter-spacing: 1px;
  background: transparent !important;
  border: 1px solid var(--green-dim) !important;
  color: var(--green) !important;
  border-radius: 4px !important;
  transition: all 0.2s ease !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background: var(--green-glow) !important;
  box-shadow: 0 0 16px var(--green-glow) !important;
}

/* ── Date inputs ──────────────────────────────────────────────────── */
[data-testid="stDateInput"] input {
  font-family: var(--mono) !important;
  font-size: 13px !important;
  background: var(--bg3) !important;
  border: 1px solid var(--border2) !important;
  color: var(--white) !important;
  border-radius: 4px !important;
}
[data-testid="stDateInput"] label {
  font-family: var(--mono) !important;
  font-size: 11px !important;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--mid) !important;
}

/* ── Select box ───────────────────────────────────────────────────── */
[data-testid="stSelectbox"] > div > div {
  background: var(--bg3) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 4px !important;
  font-family: var(--mono) !important;
  font-size: 12px !important;
  color: var(--white) !important;
}

/* ── Progress bar ─────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div {
  background: var(--border) !important;
  border-radius: 2px !important;
}
[data-testid="stProgress"] > div > div > div {
  background: linear-gradient(90deg, var(--green), #00ffb3) !important;
  border-radius: 2px !important;
}

/* ── Dataframe ────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--border) !important;
  border-radius: 6px !important;
  overflow: hidden;
}
[data-testid="stDataFrame"] th {
  background: var(--bg3) !important;
  font-family: var(--mono) !important;
  font-size: 11px !important;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--mid) !important;
  border-bottom: 1px solid var(--border2) !important;
}
[data-testid="stDataFrame"] td {
  font-family: var(--mono) !important;
  font-size: 12px !important;
  background: var(--bg2) !important;
  border-bottom: 1px solid var(--border) !important;
  color: var(--white) !important;
}

/* ── Divider ──────────────────────────────────────────────────────── */
hr { border-color: var(--border) !important; }

/* ── Spinner ──────────────────────────────────────────────────────── */
[data-testid="stSpinner"] { color: var(--green) !important; }

/* ── Metric ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 16px;
}
[data-testid="stMetricLabel"] { font-family: var(--mono) !important; font-size: 10px !important; color: var(--mid) !important; letter-spacing: 1.5px; text-transform: uppercase; }
[data-testid="stMetricValue"] { font-family: var(--mono) !important; color: var(--white) !important; }

/* ── Custom component classes ─────────────────────────────────────── */

/* Stat bar */
.stat-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin: 16px 0;
}
.stat-item {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 14px 18px;
  transition: border-color 0.2s;
}
.stat-item:hover { border-color: var(--border2); }
.stat-label {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--mid);
  margin-bottom: 6px;
}
.stat-value {
  font-family: var(--mono);
  font-size: 22px;
  font-weight: 700;
  color: var(--white);
  line-height: 1;
}
.stat-sub {
  font-family: var(--sans);
  font-size: 11px;
  color: var(--mid);
  margin-top: 4px;
}
.stat-green { color: var(--green) !important; }
.stat-red   { color: var(--red)   !important; }
.stat-yellow{ color: var(--yellow)!important; }

/* Stock cards */
.stock-card {
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
  text-align: center;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  position: relative;
  overflow: hidden;
}
.stock-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--accent-color, var(--green));
}
.stock-card:hover {
  transform: translateY(-2px);
  border-color: var(--border2);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
.card-symbol {
  font-family: var(--mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--white);
  letter-spacing: 0.5px;
}
.card-sector {
  font-family: var(--sans);
  font-size: 10px;
  color: var(--mid);
  margin: 3px 0 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.card-change {
  font-family: var(--mono);
  font-size: 26px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 2px;
}
.card-divider {
  border: none;
  border-top: 1px solid var(--border);
  margin: 10px 0;
}
.card-detail {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--mid);
  line-height: 1.8;
}
.card-score {
  font-family: var(--mono);
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
}
.card-signal {
  font-family: var(--sans);
  font-size: 11px;
  font-weight: 600;
  margin: 4px 0;
  letter-spacing: 0.5px;
}

/* Section headers */
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 24px 0 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.section-title {
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--white);
}
.section-badge {
  font-family: var(--mono);
  font-size: 10px;
  background: var(--bg3);
  border: 1px solid var(--border2);
  color: var(--mid);
  padding: 2px 8px;
  border-radius: 3px;
  letter-spacing: 1px;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 80px 24px;
}
.empty-icon {
  font-size: 52px;
  margin-bottom: 20px;
  opacity: 0.4;
}
.empty-title {
  font-family: var(--mono);
  font-size: 18px;
  color: var(--mid);
  margin-bottom: 10px;
  letter-spacing: 1px;
}
.empty-sub {
  font-family: var(--sans);
  font-size: 13px;
  color: var(--dim);
  line-height: 1.7;
}
.empty-sub strong { color: var(--green); font-family: var(--mono); }

/* App header */
.app-header {
  padding: 8px 0 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}
.app-wordmark {
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: var(--green);
  margin-bottom: 4px;
}
.app-title {
  font-family: var(--mono);
  font-size: 28px;
  font-weight: 700;
  color: var(--white);
  letter-spacing: -1px;
  line-height: 1.1;
}
.app-subtitle {
  font-family: var(--sans);
  font-size: 13px;
  color: var(--mid);
  margin-top: 6px;
}
.app-range {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--green);
  background: var(--green-glow);
  border: 1px solid rgba(0,229,160,0.2);
  padding: 4px 12px;
  border-radius: 3px;
  display: inline-block;
  margin-top: 8px;
  letter-spacing: 0.5px;
}

/* Sidebar label */
.sidebar-label {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--dim);
  padding: 16px 0 6px;
}
.sidebar-section {
  border-top: 1px solid var(--border);
  margin: 12px 0 4px;
}

/* Tag/badge */
.tag {
  display: inline-block;
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 3px 8px;
  border-radius: 3px;
  border: 1px solid currentColor;
  opacity: 0.8;
}
"""


def inject() -> None:
    """Inject the CSS into the Streamlit page."""
    import streamlit as st
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
