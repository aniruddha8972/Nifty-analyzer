"""
frontend/styles.py
Full CSS design system — terminal-grade financial aesthetic.
Controls live in the main page (no sidebar dependency).
"""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600;700&display=swap');

:root {
  --bg:    #050508;
  --bg2:   #0c0c12;
  --bg3:   #12121a;
  --bdr:   #1e1e2e;
  --bdr2:  #2a2a3e;
  --green: #00e5a0;
  --gdim:  #00a370;
  --red:   #ff4560;
  --yel:   #f5a623;
  --white: #e8e8f0;
  --mid:   #8888a0;
  --dim:   #3a3a4e;
  --mono:  'Space Mono', monospace;
  --sans:  'DM Sans', sans-serif;
}

/* ── Base ─────────────────────────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
  background: var(--bg) !important;
  font-family: var(--sans) !important;
}

/* Scanline overlay */
[data-testid="stAppViewContainer"]::before {
  content: ''; position: fixed; inset: 0;
  background: repeating-linear-gradient(0deg, transparent, transparent 2px,
    rgba(0,0,0,0.025) 2px, rgba(0,0,0,0.025) 4px);
  pointer-events: none; z-index: 9998;
}

/* ── Hide chrome ──────────────────────────────────────────────────── */
[data-testid="stHeader"]            { background: transparent !important; }
[data-testid="stToolbar"]           { display: none !important; }
[data-testid="stDecoration"]        { display: none !important; }
footer                               { display: none !important; }
.stDeployButton                      { display: none !important; }
[data-testid="stMainBlockContainer"] { padding-top: 0.75rem !important; }

/* ── Sidebar (info only) ──────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: #08080e !important;
  border-right: 1px solid #1a1a28 !important;
}
[data-testid="stSidebar"] * { color: #4a4a60 !important; }

/* ── Selectbox ────────────────────────────────────────────────────── */
[data-testid="stSelectbox"] label {
  font-family: var(--mono) !important;
  font-size: 10px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  color: var(--mid) !important;
}
[data-testid="stSelectbox"] > div > div {
  background: var(--bg3) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 6px !important;
  color: var(--white) !important;
  font-family: var(--sans) !important;
}

/* ── Date inputs ──────────────────────────────────────────────────── */
[data-testid="stDateInput"] label {
  font-family: var(--mono) !important;
  font-size: 10px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  color: var(--mid) !important;
}
[data-testid="stDateInput"] input {
  background: var(--bg3) !important;
  border: 1px solid var(--bdr2) !important;
  border-radius: 6px !important;
  color: var(--white) !important;
  font-family: var(--mono) !important;
  font-size: 13px !important;
}
[data-testid="stDateInput"] input:focus {
  border-color: var(--green) !important;
  box-shadow: 0 0 0 2px rgba(0,229,160,0.15) !important;
}

/* ── Buttons ──────────────────────────────────────────────────────── */
[data-testid="stButton"] > button {
  font-family: var(--mono) !important;
  font-size: 11px !important;
  letter-spacing: 1.5px !important;
  text-transform: uppercase !important;
  border-radius: 6px !important;
  transition: all 0.18s ease !important;
  height: 42px !important;
}
/* Primary = ANALYSE */
[data-testid="stButton"] > button[kind="primary"] {
  background: var(--green) !important;
  color: #030306 !important;
  border: none !important;
  font-weight: 700 !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
  background: #00ffb3 !important;
  box-shadow: 0 0 20px rgba(0,229,160,0.35) !important;
  transform: translateY(-1px) !important;
}
/* Secondary = REFRESH */
[data-testid="stButton"] > button:not([kind="primary"]):not([kind="primaryFormSubmit"]) {
  background: var(--bg3) !important;
  color: var(--mid) !important;
  border: 1px solid var(--bdr2) !important;
}
[data-testid="stButton"] > button:not([kind="primary"]):hover {
  border-color: var(--green) !important;
  color: var(--green) !important;
  box-shadow: 0 0 12px rgba(0,229,160,0.12) !important;
}

/* ── Download button ──────────────────────────────────────────────── */
[data-testid="stDownloadButton"] > button {
  font-family: var(--mono) !important;
  font-size: 11px !important;
  letter-spacing: 1px !important;
  background: transparent !important;
  border: 1px solid var(--gdim) !important;
  color: var(--green) !important;
  border-radius: 6px !important;
  transition: all 0.18s ease !important;
}
[data-testid="stDownloadButton"] > button:hover {
  background: rgba(0,229,160,0.08) !important;
  box-shadow: 0 0 14px rgba(0,229,160,0.18) !important;
}

/* ── Tabs ─────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
  gap: 4px; border-bottom: 1px solid var(--bdr); padding-bottom: 0;
}
[data-testid="stTabs"] [role="tab"] {
  font-family: var(--mono) !important;
  font-size: 11px !important; letter-spacing: 1px !important;
  text-transform: uppercase !important;
  color: #555568 !important; background: var(--bg2) !important;
  border: 1px solid var(--bdr) !important; border-bottom: none !important;
  border-radius: 5px 5px 0 0 !important; padding: 8px 16px !important;
  transition: color 0.15s, background 0.15s !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color: var(--green) !important; background: var(--bg) !important;
  border-color: var(--gdim) !important;
}
[data-testid="stTabs"] [role="tab"]:hover { color: var(--white) !important; }

/* ── Progress ─────────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div { background: var(--bdr) !important; border-radius: 2px !important; }
[data-testid="stProgress"] > div > div > div {
  background: linear-gradient(90deg, var(--green), #00ffb3) !important; border-radius: 2px !important;
}
[data-testid="stProgress"] p {
  font-family: var(--mono) !important; font-size: 11px !important; color: var(--mid) !important;
}

/* ── Dataframe ────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--bdr) !important; border-radius: 8px !important; overflow: hidden !important;
}

/* ── Alerts ───────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: 6px !important; font-family: var(--sans) !important;
}

/* ── Divider ──────────────────────────────────────────────────────── */
hr { border-color: var(--bdr) !important; margin: 16px 0 !important; }

/* ── Typography ───────────────────────────────────────────────────── */
h1,h2,h3,h4 {
  font-family: var(--mono) !important; color: var(--white) !important;
}

/* ═══════════════════════════════════════════════
   CUSTOM COMPONENT CLASSES
   ═══════════════════════════════════════════════ */

/* App header */
.app-header {
  padding: 4px 0 20px; border-bottom: 1px solid var(--bdr); margin-bottom: 0;
}
.app-wordmark {
  font-family: var(--mono); font-size: 10px; letter-spacing: 4px;
  text-transform: uppercase; color: var(--green); margin-bottom: 4px;
}
.app-title {
  font-family: var(--mono); font-size: 30px; font-weight: 700;
  color: var(--white); letter-spacing: -1px; line-height: 1.1;
}
.app-subtitle {
  font-family: var(--sans); font-size: 13px; color: var(--mid); margin-top: 6px;
}
.app-range {
  font-family: var(--mono); font-size: 12px; color: var(--green);
  background: rgba(0,229,160,0.07); border: 1px solid rgba(0,229,160,0.18);
  padding: 4px 12px; border-radius: 4px; display: inline-block;
  margin-top: 8px; letter-spacing: 0.5px;
}

/* Stat bar */
.stat-bar {
  display: grid; grid-template-columns: repeat(4,1fr); gap: 12px; margin: 16px 0;
}
.stat-item {
  background: var(--bg2); border: 1px solid var(--bdr);
  border-radius: 8px; padding: 14px 18px; transition: border-color 0.18s;
}
.stat-item:hover { border-color: var(--bdr2); }
.stat-label {
  font-family: var(--mono); font-size: 9px; letter-spacing: 2px;
  text-transform: uppercase; color: var(--dim); margin-bottom: 6px;
}
.stat-value {
  font-family: var(--mono); font-size: 22px; font-weight: 700;
  color: var(--white); line-height: 1;
}
.stat-sub { font-family: var(--sans); font-size: 11px; color: var(--mid); margin-top: 4px; }
.stat-green { color: #00e5a0 !important; }
.stat-red   { color: #ff4560 !important; }
.stat-yellow{ color: #f5a623 !important; }

/* Stock cards */
.stock-card {
  background: var(--bg2); border: 1px solid var(--bdr); border-radius: 10px;
  padding: 16px; text-align: center; margin-bottom: 8px;
  transition: transform 0.15s, border-color 0.15s, box-shadow 0.15s;
  position: relative; overflow: hidden;
}
.stock-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
  background: var(--accent-color, var(--green));
}
.stock-card:hover {
  transform: translateY(-2px); border-color: var(--bdr2);
  box-shadow: 0 8px 32px rgba(0,0,0,0.5);
}
.card-symbol { font-family: var(--mono); font-size: 14px; font-weight: 700; color: var(--white); }
.card-sector {
  font-family: var(--sans); font-size: 10px; color: var(--dim);
  margin: 3px 0 10px; text-transform: uppercase; letter-spacing: 1px;
}
.card-change { font-family: var(--mono); font-size: 26px; font-weight: 700; line-height: 1; margin-bottom: 2px; }
.card-divider { border: none; border-top: 1px solid var(--bdr); margin: 10px 0; }
.card-detail { font-family: var(--mono); font-size: 10px; color: var(--mid); line-height: 1.8; }
.card-score  { font-family: var(--mono); font-size: 28px; font-weight: 700; line-height: 1; }
.card-signal { font-family: var(--sans); font-size: 11px; font-weight: 600; margin: 4px 0; }

/* Section header */
.section-header {
  display: flex; align-items: center; gap: 10px;
  margin: 24px 0 16px; padding-bottom: 10px; border-bottom: 1px solid var(--bdr);
}
.section-title {
  font-family: var(--mono); font-size: 12px; font-weight: 700;
  letter-spacing: 2px; text-transform: uppercase; color: var(--white);
}
.section-badge {
  font-family: var(--mono); font-size: 10px; background: var(--bg3);
  border: 1px solid var(--bdr2); color: var(--mid); padding: 2px 8px;
  border-radius: 3px; letter-spacing: 1px;
}

/* Empty state */
.empty-state { text-align: center; padding: 60px 24px; }
.empty-icon  { font-size: 52px; margin-bottom: 20px; opacity: 0.25; }
.empty-title {
  font-family: var(--mono); font-size: 20px; color: var(--dim);
  margin-bottom: 12px; letter-spacing: 1px;
}
.empty-sub {
  font-family: var(--sans); font-size: 14px; color: var(--dim); line-height: 1.8;
}
.empty-sub strong { color: var(--green); font-family: var(--mono); }
"""


def inject() -> None:
    import streamlit as st
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
