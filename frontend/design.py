"""
frontend/design.py
─────────────────────────────────────────────────────────────────────
Premium Bloomberg-inspired financial UI design system.
Dark slate base · Amber + Electric-teal accents · Geometric precision.

Fonts: Syne (display) + JetBrains Mono (data) + DM Sans (body)
Palette: Deep navy blacks, warm amber, electric teal, signal red
"""

import streamlit as st

# ─────────────────────────────────────────────────────────────────────
FINANCE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=JetBrains+Mono:wght@300;400;500;600;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
  /* Core palette */
  --ink:    #070810;
  --ink2:   #0c0d1a;
  --ink3:   #111224;
  --ink4:   #161830;
  --ink5:   #1e2040;

  /* Borders */
  --line:   #1f2240;
  --line2:  #2a2d55;
  --line3:  #363a6e;

  /* Accents */
  --amber:  #f0a500;
  --amber2: #cc8800;
  --amber3: rgba(240,165,0,0.12);
  --teal:   #00d4aa;
  --teal2:  #00a882;
  --teal3:  rgba(0,212,170,0.10);
  --red:    #ff3d5a;
  --red2:   rgba(255,61,90,0.12);
  --blue:   #5b8fff;
  --blue2:  rgba(91,143,255,0.12);

  /* Text */
  --fg:     #e8e9f5;
  --fg2:    #9fa3c4;
  --fg3:    #5a5e8a;
  --fg4:    #2e315c;

  /* Fonts */
  --display: 'Syne', sans-serif;
  --mono:    'JetBrains Mono', monospace;
  --body:    'DM Sans', sans-serif;

  /* Misc */
  --radius:  8px;
  --radius2: 12px;
  --shadow:  0 8px 32px rgba(0,0,0,0.6);
}

/* ── Reset & Base ──────────────────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
  background: var(--ink) !important;
  font-family: var(--body) !important;
  color: var(--fg) !important;
}

/* Subtle grid texture */
[data-testid="stAppViewContainer"]::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image:
    linear-gradient(rgba(240,165,0,.025) 1px, transparent 1px),
    linear-gradient(90deg, rgba(240,165,0,.025) 1px, transparent 1px);
  background-size: 48px 48px;
}

/* Hide Streamlit chrome */
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
footer, .stDeployButton,
#MainMenu { display: none !important; }

[data-testid="stMainBlockContainer"] { padding-top: 0 !important; }

/* ── Sidebar ───────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: var(--ink2) !important;
  border-right: 1px solid var(--line) !important;
}
[data-testid="stSidebar"]::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--amber), var(--teal));
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p,
[data-testid="stSidebar"] [data-testid="stMarkdown"] div {
  color: var(--fg3) !important;
}

/* ── Form Inputs ───────────────────────────────────────────────────── */
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label {
  font-family: var(--mono) !important;
  font-size: 9px !important;
  letter-spacing: 2.5px !important;
  text-transform: uppercase !important;
  color: var(--fg3) !important;
  margin-bottom: 4px !important;
}

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
  background: var(--ink3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--radius) !important;
  color: var(--fg) !important;
  font-family: var(--mono) !important;
  font-size: 13px !important;
  padding: 10px 14px !important;
  transition: border-color .15s, box-shadow .15s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stDateInput"] input:focus {
  border-color: var(--amber) !important;
  box-shadow: 0 0 0 3px var(--amber3) !important;
}
[data-testid="stTextInput"] input::placeholder { color: var(--fg4) !important; }

[data-testid="stSelectbox"] > div > div {
  background: var(--ink3) !important;
  border: 1px solid var(--line2) !important;
  border-radius: var(--radius) !important;
  color: var(--fg) !important;
  font-family: var(--body) !important;
}

/* ── Buttons ───────────────────────────────────────────────────────── */
[data-testid="stButton"] > button {
  font-family: var(--mono) !important;
  font-size: 10px !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  border-radius: var(--radius) !important;
  height: 42px !important;
  font-weight: 600 !important;
  transition: all .18s ease !important;
}
[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, var(--amber), var(--amber2)) !important;
  border: none !important;
  color: var(--ink) !important;
  box-shadow: 0 4px 16px rgba(240,165,0,0.28) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
  box-shadow: 0 6px 24px rgba(240,165,0,0.45) !important;
  transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button[kind="secondary"],
[data-testid="stButton"] > button:not([kind]) {
  background: var(--ink3) !important;
  border: 1px solid var(--line2) !important;
  color: var(--fg2) !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover,
[data-testid="stButton"] > button:not([kind]):hover {
  border-color: var(--amber) !important;
  color: var(--amber) !important;
  background: var(--amber3) !important;
}

/* ── Progress bar ──────────────────────────────────────────────────── */
[data-testid="stProgress"] > div > div > div {
  background: linear-gradient(90deg, var(--amber), var(--teal)) !important;
}

/* ── Tabs ──────────────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"] {
  border-bottom: 1px solid var(--line) !important;
  gap: 0 !important;
}
[data-testid="stTabs"] [role="tab"] {
  font-family: var(--mono) !important;
  font-size: 9px !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  color: var(--fg3) !important;
  padding: 10px 18px !important;
  border-radius: 0 !important;
  transition: all .15s !important;
}
[data-testid="stTabs"] [role="tab"]:hover { color: var(--amber) !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  color: var(--amber) !important;
  border-bottom: 2px solid var(--amber) !important;
  background: transparent !important;
}

/* ── Dataframe / Table ─────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important;
}

/* ── Expander ──────────────────────────────────────────────────────── */
[data-testid="stExpander"] {
  background: var(--ink3) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius2) !important;
}
[data-testid="stExpander"] summary {
  font-family: var(--mono) !important;
  font-size: 10px !important;
  letter-spacing: 1.5px !important;
  color: var(--fg2) !important;
}

/* ── Metrics ───────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--ink3) !important;
  border: 1px solid var(--line) !important;
  border-radius: var(--radius) !important;
  padding: 12px !important;
}
[data-testid="stMetric"] label {
  font-family: var(--mono) !important;
  font-size: 9px !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  color: var(--fg3) !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-family: var(--mono) !important;
  font-size: 22px !important;
  color: var(--fg) !important;
}

/* ── Alerts ────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: var(--radius) !important;
  font-family: var(--body) !important;
  font-size: 13px !important;
}

/* ── Scrollbar ─────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--ink2); }
::-webkit-scrollbar-thumb { background: var(--line2); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: var(--amber2); }

/* ── Divider ───────────────────────────────────────────────────────── */
hr { border: none; border-top: 1px solid var(--line) !important; margin: 20px 0 !important; }

/* ─────────────────────────────────────────────────
   COMPONENT CLASSES
───────────────────────────────────────────────── */

/* Navigation bar */
.fin-nav {
  background: var(--ink2);
  border-bottom: 1px solid var(--line);
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 60px;
  position: relative;
  margin-bottom: 0;
}
.fin-nav::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--amber), transparent);
  opacity: 0.4;
}
.fin-logo {
  font-family: var(--display);
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: var(--fg);
  display: flex;
  align-items: center;
  gap: 10px;
}
.fin-logo-accent { color: var(--amber); }
.fin-logo-dot {
  width: 6px; height: 6px;
  background: var(--teal);
  border-radius: 50%;
  display: inline-block;
  box-shadow: 0 0 8px var(--teal);
  animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.85); }
}
.fin-nav-links {
  display: flex;
  gap: 2px;
  align-items: center;
}
.fin-nav-link {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--fg3);
  padding: 6px 14px;
  border-radius: 6px;
  cursor: pointer;
  transition: all .15s;
  white-space: nowrap;
}
.fin-nav-link:hover { color: var(--amber); background: var(--amber3); }
.fin-nav-link.active {
  color: var(--amber);
  background: var(--amber3);
  border: 1px solid rgba(240,165,0,0.25);
}
.fin-nav-user {
  display: flex;
  align-items: center;
  gap: 10px;
}
.fin-avatar {
  width: 32px; height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--amber), var(--amber2));
  display: flex; align-items: center; justify-content: center;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
  color: var(--ink);
  flex-shrink: 0;
}
.fin-user-name {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--fg);
}
.fin-user-sub {
  font-family: var(--body);
  font-size: 10px;
  color: var(--fg3);
}

/* Page hero */
.page-hero {
  padding: 32px 0 24px;
  border-bottom: 1px solid var(--line);
  margin-bottom: 28px;
}
.page-eyebrow {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--amber);
  margin-bottom: 8px;
}
.page-title {
  font-family: var(--display);
  font-size: 32px;
  font-weight: 700;
  color: var(--fg);
  letter-spacing: -0.5px;
  line-height: 1.1;
}
.page-subtitle {
  font-family: var(--body);
  font-size: 14px;
  color: var(--fg3);
  margin-top: 6px;
}

/* Ticker strip */
.ticker-strip {
  background: var(--ink3);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 10px 20px;
  display: flex;
  gap: 32px;
  overflow: hidden;
  margin-bottom: 24px;
}
.ticker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.ticker-sym {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.5px;
  color: var(--fg2);
}
.ticker-val {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 700;
  color: var(--fg);
}
.ticker-chg-pos { color: var(--teal); font-size: 10px; font-family: var(--mono); }
.ticker-chg-neg { color: var(--red);  font-size: 10px; font-family: var(--mono); }

/* Stat cards row */
.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }
.stat-card {
  background: var(--ink2);
  border: 1px solid var(--line);
  border-radius: var(--radius2);
  padding: 18px 20px;
  position: relative;
  overflow: hidden;
  transition: border-color .18s, box-shadow .18s;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--accent-top, var(--amber));
}
.stat-card:hover { border-color: var(--line2); box-shadow: var(--shadow); }
.stat-label {
  font-family: var(--mono);
  font-size: 8px;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: var(--fg3);
  margin-bottom: 8px;
}
.stat-value {
  font-family: var(--mono);
  font-size: 26px;
  font-weight: 700;
  color: var(--fg);
  line-height: 1;
}
.stat-delta {
  font-family: var(--body);
  font-size: 11px;
  color: var(--fg3);
  margin-top: 5px;
}

/* Section heading */
.sec-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 28px 0 16px;
}
.sec-line { flex: 1; height: 1px; background: var(--line); }
.sec-title {
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--fg3);
  white-space: nowrap;
}
.sec-badge {
  font-family: var(--mono);
  font-size: 8px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--ink4);
  border: 1px solid var(--line2);
  color: var(--fg3);
  letter-spacing: 1px;
}

/* Control panel */
.control-panel {
  background: var(--ink2);
  border: 1px solid var(--line);
  border-radius: var(--radius2);
  padding: 20px 24px 18px;
  margin-bottom: 24px;
  position: relative;
}
.control-panel::before {
  content: 'ANALYSIS CONTROLS';
  position: absolute;
  top: -1px; left: 20px;
  font-family: var(--mono);
  font-size: 7px;
  letter-spacing: 2.5px;
  color: var(--amber);
  background: var(--ink2);
  padding: 0 8px;
  transform: translateY(-50%);
}

/* Stock cards */
.fin-card {
  background: var(--ink2);
  border: 1px solid var(--line);
  border-radius: var(--radius2);
  padding: 18px 16px;
  position: relative;
  overflow: hidden;
  transition: transform .15s, border-color .15s, box-shadow .15s;
  text-align: center;
}
.fin-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: var(--card-accent, var(--amber));
}
.fin-card:hover {
  transform: translateY(-3px);
  border-color: var(--line3);
  box-shadow: 0 16px 48px rgba(0,0,0,0.7);
}
.fin-card-sym {
  font-family: var(--mono);
  font-size: 14px;
  font-weight: 700;
  color: var(--fg);
  letter-spacing: 0.5px;
}
.fin-card-sector {
  font-family: var(--body);
  font-size: 9px;
  color: var(--fg4);
  text-transform: uppercase;
  letter-spacing: 1.5px;
  margin: 3px 0 12px;
}
.fin-card-chg {
  font-family: var(--mono);
  font-size: 30px;
  font-weight: 700;
  line-height: 1;
}
.fin-card-divider { border: none; border-top: 1px solid var(--line); margin: 12px 0; }
.fin-card-detail {
  font-family: var(--mono);
  font-size: 10px;
  color: var(--fg3);
  line-height: 2;
}

/* Signal badges */
.sig-strong-buy { background: rgba(0,212,170,0.12); border: 1px solid rgba(0,212,170,0.3); color: #00d4aa; }
.sig-buy        { background: rgba(0,212,170,0.07); border: 1px solid rgba(0,212,170,0.2); color: #00a882; }
.sig-hold       { background: rgba(240,165,0,0.1);  border: 1px solid rgba(240,165,0,0.25); color: #f0a500; }
.sig-avoid      { background: rgba(255,61,90,0.1);  border: 1px solid rgba(255,61,90,0.25); color: #ff3d5a; }
.sig-badge {
  display: inline-block;
  font-family: var(--mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 3px 10px;
  border-radius: 4px;
}

/* Empty state */
.fin-empty {
  text-align: center;
  padding: 80px 24px;
}
.fin-empty-icon { font-size: 48px; opacity: 0.15; margin-bottom: 20px; }
.fin-empty-title {
  font-family: var(--mono);
  font-size: 14px;
  letter-spacing: 3px;
  text-transform: uppercase;
  color: var(--fg3);
  margin-bottom: 10px;
}
.fin-empty-sub {
  font-family: var(--body);
  font-size: 13px;
  color: var(--fg4);
  line-height: 1.8;
  max-width: 360px;
  margin: 0 auto;
}

/* Auth page */
.auth-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--ink);
  position: relative;
}
.auth-wrap::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 60% at 10% 40%, rgba(240,165,0,0.04) 0%, transparent 60%),
    radial-gradient(ellipse 60% 80% at 90% 60%, rgba(0,212,170,0.03) 0%, transparent 60%);
  pointer-events: none;
}
.auth-card {
  background: var(--ink2);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 48px 52px;
  width: 100%;
  max-width: 460px;
  position: relative;
  overflow: hidden;
  box-shadow: 0 24px 80px rgba(0,0,0,0.8);
}
.auth-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--amber), var(--teal));
}
.auth-brand {
  text-align: center;
  margin-bottom: 32px;
}
.auth-brand-name {
  font-family: var(--display);
  font-size: 22px;
  font-weight: 800;
  color: var(--fg);
  letter-spacing: -0.3px;
}
.auth-brand-tagline {
  font-family: var(--mono);
  font-size: 9px;
  letter-spacing: 2.5px;
  color: var(--fg3);
  text-transform: uppercase;
  margin-top: 4px;
}

/* Profile card in sidebar */
.profile-card {
  background: var(--ink3);
  border: 1px solid var(--line);
  border-radius: var(--radius2);
  padding: 16px;
  margin-bottom: 14px;
  position: relative;
  overflow: hidden;
}
.profile-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--amber), var(--teal));
}

/* Mode badge */
.mode-badge {
  font-family: var(--mono);
  font-size: 8px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  padding: 2px 8px;
  border-radius: 4px;
}
.mode-cloud { background: var(--teal3); border: 1px solid rgba(0,212,170,0.25); color: var(--teal); }
.mode-local { background: var(--blue2); border: 1px solid rgba(91,143,255,0.25); color: var(--blue); }

/* Notification banners */
.notif { border-radius: var(--radius); padding: 10px 16px; margin-bottom: 10px; font-family: var(--body); font-size: 13px; }
.notif-success { background: rgba(0,212,170,0.08); border: 1px solid rgba(0,212,170,0.25); color: var(--teal); }
.notif-error   { background: var(--red2); border: 1px solid rgba(255,61,90,0.3); color: var(--red); }
.notif-info    { background: var(--blue2); border: 1px solid rgba(91,143,255,0.25); color: var(--blue); }
.notif-warning { background: var(--amber3); border: 1px solid rgba(240,165,0,0.3); color: var(--amber); }

/* Table override */
.fin-table { width: 100%; border-collapse: collapse; font-family: var(--mono); font-size: 12px; }
.fin-table th {
  font-size: 8px; letter-spacing: 2px; text-transform: uppercase;
  color: var(--fg3); border-bottom: 1px solid var(--line);
  padding: 8px 12px; text-align: left; font-weight: 500;
}
.fin-table td {
  padding: 10px 12px; border-bottom: 1px solid var(--line);
  color: var(--fg2); transition: background .12s;
}
.fin-table tr:hover td { background: var(--ink3); }
.fin-table .pos { color: var(--teal); font-weight: 600; }
.fin-table .neg { color: var(--red);  font-weight: 600; }
"""


def inject() -> None:
    """Inject design system CSS. Call once per page at the top."""
    st.markdown(f"<style>{FINANCE_CSS}</style>", unsafe_allow_html=True)


def page_config(title: str = "NSE Market Intelligence") -> None:
    """Set page config. Must be FIRST Streamlit call."""
    st.set_page_config(
        page_title=title,
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def render_topnav(current_page: str = "") -> None:
    """
    Render top navigation bar with logo, page links, and user info.
    Uses Streamlit buttons rendered inside a styled HTML shell.
    current_page: one of 'dashboard', 'markets', 'predictions',
                  'portfolio', 'analytics', 'news', 'charts'
    """
    from frontend.session import get_user, is_authenticated
    from backend.auth import is_supabase_mode

    user     = get_user()
    name     = user.get("name", "")
    username = user.get("username", "")
    initials = "".join(w[0].upper() for w in name.split()[:2]) if name else "?"
    mode     = "cloud" if is_supabase_mode() else "local"
    mode_lbl = "☁ Cloud" if mode == "cloud" else "⚡ Local"

    pages = [
        ("dashboard",   "📊 Dashboard"),
        ("markets",     "📈 Markets"),
        ("predictions", "🤖 Signals"),
        ("portfolio",   "💼 Portfolio"),
        ("analytics",   "🗺 Analytics"),
        ("news",        "📰 News"),
        ("charts",      "📉 Charts"),
    ]

    links_html = ""
    for page_id, label in pages:
        cls = "fin-nav-link active" if current_page == page_id else "fin-nav-link"
        links_html += f'<span class="{cls}">{label}</span>'

    st.markdown(f"""
    <div class="fin-nav">
      <div class="fin-logo">
        <span class="fin-logo-accent">NSE</span>&nbsp;Intelligence
        <span class="fin-logo-dot"></span>
      </div>
      <div class="fin-nav-links">{links_html}</div>
      <div class="fin-nav-user">
        <div style="text-align:right">
          <div class="fin-user-name">{name}</div>
          <div class="fin-user-sub">@{username}</div>
        </div>
        <div class="fin-avatar">{initials}</div>
        <span class="mode-badge mode-{mode}">{mode_lbl}</span>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_page_hero(eyebrow: str, title: str, subtitle: str = "") -> None:
    sub_html = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(f"""
    <div class="page-hero">
      <div class="page-eyebrow">{eyebrow}</div>
      <div class="page-title">{title}</div>
      {sub_html}
    </div>
    """, unsafe_allow_html=True)


def render_section(title: str, badge: str = "") -> None:
    badge_html = f'<span class="sec-badge">{badge}</span>' if badge else ""
    st.markdown(f"""
    <div class="sec-head">
      <div class="sec-line"></div>
      <div class="sec-title">{title}</div>
      {badge_html}
      <div class="sec-line"></div>
    </div>
    """, unsafe_allow_html=True)


def render_notifications() -> None:
    """Render any queued notifications and clear them."""
    from frontend.session import pop_notifications
    for n in pop_notifications():
        st.markdown(
            f'<div class="notif notif-{n["kind"]}">{n["msg"]}</div>',
            unsafe_allow_html=True,
        )


def render_stat_cards(stats: list[dict]) -> None:
    """
    Render a row of 4 stat cards.
    Each dict: {label, value, delta?, accent?}
    accent: 'amber' | 'teal' | 'red' | 'blue'
    """
    accent_map = {
        "amber": "var(--amber)",
        "teal":  "var(--teal)",
        "red":   "var(--red)",
        "blue":  "var(--blue)",
    }
    cols = st.columns(len(stats))
    for col, s in zip(cols, stats):
        accent = accent_map.get(s.get("accent", "amber"), "var(--amber)")
        delta_html = f'<div class="stat-delta">{s["delta"]}</div>' if s.get("delta") else ""
        val_color  = s.get("val_color", "var(--fg)")
        col.markdown(f"""
        <div class="stat-card" style="--accent-top:{accent}">
          <div class="stat-label">{s['label']}</div>
          <div class="stat-value" style="color:{val_color}">{s['value']}</div>
          {delta_html}
        </div>
        """, unsafe_allow_html=True)


def sig_color(signal: str) -> str:
    if "STRONG BUY" in signal: return "var(--teal)"
    if "BUY" in signal:        return "var(--teal2)"
    if "HOLD" in signal:       return "var(--amber)"
    return "var(--red)"


def sig_class(signal: str) -> str:
    if "STRONG BUY" in signal: return "sig-strong-buy"
    if "BUY" in signal:        return "sig-buy"
    if "HOLD" in signal:       return "sig-hold"
    return "sig-avoid"


def chg_color(v) -> str:
    try:
        return "var(--teal)" if float(v) >= 0 else "var(--red)"
    except Exception:
        return "var(--fg3)"
