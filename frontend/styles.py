"""
frontend/styles.py  ─  canonical CSS for NSE Market Analyzer
All component classes live here; design.py imports + re-exports.
"""
import streamlit as st

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg:    #04040c; --bg2: #08081a; --bg3: #0d0d22; --bg4: #12122c; --bg5: #181836;
  --bdr:   #1a1a3a; --bdr2:#242448; --bdr3:#303060;
  --green: #00e5a0; --green2:#00b878; --glow:rgba(0,229,160,0.15);
  --amber: #f0a500; --amber2:rgba(240,165,0,0.12);
  --red:   #ff3d5a; --red2:rgba(255,61,90,0.12);
  --blue:  #4c8eff;
  --fg:    #e8e9f5; --fg2:#9fa3c4; --fg3:#5a5e8a; --fg4:#2e315c;
  --mono: 'IBM Plex Mono', monospace;
  --sans: 'Inter', sans-serif;
  --r:10px; --r2:14px;
}

/* ── Base ───────────────────────────────────────────────── */
html,body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
  background:var(--bg)!important; font-family:var(--sans)!important; color:var(--fg)!important;
}
[data-testid="stAppViewContainer"]::before {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:
    linear-gradient(rgba(0,229,160,.013) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,229,160,.013) 1px,transparent 1px);
  background-size:44px 44px;
}
[data-testid="stHeader"],[data-testid="stToolbar"],
[data-testid="stDecoration"],footer,.stDeployButton,#MainMenu{display:none!important;}
[data-testid="stMainBlockContainer"]{padding-top:0!important;}

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"]{background:var(--bg2)!important;border-right:1px solid var(--bdr)!important;}
[data-testid="stSidebar"]::before{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,var(--green),var(--amber));
}
[data-testid="stSidebarNav"]{display:none!important;}
section[data-testid="stSidebarNav"]{display:none!important;}

/* ── Inputs ──────────────────────────────────────────────── */
[data-testid="stTextInput"] label,
[data-testid="stNumberInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stDateInput"] label {
  font-family:var(--mono)!important; font-size:9px!important;
  letter-spacing:2px!important; text-transform:uppercase!important; color:var(--fg3)!important;
}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] input {
  background:var(--bg3)!important; border:1px solid var(--bdr2)!important;
  border-radius:var(--r)!important; color:var(--fg)!important;
  font-family:var(--mono)!important; font-size:13px!important;
  padding:10px 14px!important; transition:border-color .15s,box-shadow .15s!important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus,
[data-testid="stDateInput"] input:focus {
  border-color:var(--green)!important; box-shadow:0 0 0 3px var(--glow)!important;
}
[data-testid="stTextInput"] input::placeholder{color:var(--fg4)!important;}
[data-testid="stSelectbox"]>div>div{
  background:var(--bg3)!important;border:1px solid var(--bdr2)!important;
  border-radius:var(--r)!important;color:var(--fg)!important;
}

/* ── Buttons ─────────────────────────────────────────────── */
[data-testid="stButton"]>button{
  font-family:var(--mono)!important; font-size:10px!important;
  letter-spacing:2px!important; text-transform:uppercase!important;
  border-radius:var(--r)!important; height:42px!important;
  font-weight:600!important; transition:all .18s ease!important;
}
[data-testid="stButton"]>button[kind="primary"]{
  background:linear-gradient(135deg,var(--green),var(--green2))!important;
  border:none!important; color:var(--bg)!important;
  box-shadow:0 4px 18px var(--glow)!important;
}
[data-testid="stButton"]>button[kind="primary"]:hover{
  box-shadow:0 6px 28px rgba(0,229,160,0.35)!important; transform:translateY(-1px)!important;
}
[data-testid="stButton"]>button:not([kind="primary"]){
  background:var(--bg3)!important; border:1px solid var(--bdr2)!important; color:var(--fg3)!important;
}
[data-testid="stButton"]>button:not([kind="primary"]):hover{
  border-color:var(--green)!important; color:var(--green)!important; background:var(--glow)!important;
}

/* ── Page links ──────────────────────────────────────────── */
[data-testid="stPageLink"]>div{
  padding:9px 12px!important; border-radius:8px!important;
  font-family:var(--mono)!important; font-size:10px!important;
  color:var(--fg3)!important; transition:all .15s!important;
  border:1px solid transparent!important;
}
[data-testid="stPageLink"]:hover>div{color:var(--green)!important;background:var(--glow)!important;}
[data-testid="stPageLink"]>div>p{
  font-family:var(--mono)!important;font-size:10px!important;font-weight:500!important;
}

/* ── Tabs ────────────────────────────────────────────────── */
[data-testid="stTabs"] [role="tablist"]{border-bottom:1px solid var(--bdr)!important;gap:0!important;}
[data-testid="stTabs"] [role="tab"]{
  font-family:var(--mono)!important;font-size:9px!important;
  letter-spacing:2px!important;text-transform:uppercase!important;
  color:var(--fg3)!important;padding:10px 16px!important;
  border-radius:0!important;transition:all .15s!important;
}
[data-testid="stTabs"] [role="tab"]:hover{color:var(--green)!important;}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{
  color:var(--green)!important;border-bottom:2px solid var(--green)!important;
  background:transparent!important;
}

/* ── Progress ────────────────────────────────────────────── */
[data-testid="stProgress"]>div>div>div{
  background:linear-gradient(90deg,var(--green),var(--amber))!important;
}

/* ── Scrollbar ───────────────────────────────────────────── */
::-webkit-scrollbar{width:4px;height:4px;}
::-webkit-scrollbar-track{background:var(--bg2);}
::-webkit-scrollbar-thumb{background:var(--bdr2);border-radius:2px;}
::-webkit-scrollbar-thumb:hover{background:var(--green2);}
hr{border:none;border-top:1px solid var(--bdr)!important;margin:16px 0!important;}

/* ════════════════════════════════════════════════════════
   COMPONENT CLASSES  (required by test_pipeline.py)
═══════════════════════════════════════════════════════ */

/* stat-bar — 4 KPI cards row */
.stat-bar{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:22px;}
.stat-item{
  background:var(--bg2);border:1px solid var(--bdr);border-radius:var(--r2);
  padding:16px 18px;position:relative;overflow:hidden;
  transition:border-color .18s,box-shadow .18s;
}
.stat-item::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:var(--stat-accent,var(--green));
}
.stat-item:hover{border-color:var(--bdr2);box-shadow:0 8px 32px rgba(0,0,0,.5);}
.stat-label{font-family:var(--mono);font-size:8px;letter-spacing:2.5px;text-transform:uppercase;color:var(--fg3);margin-bottom:8px;}
.stat-value{font-family:var(--mono);font-size:24px;font-weight:700;color:var(--fg);line-height:1;}
.stat-sub{font-family:var(--sans);font-size:11px;color:var(--fg3);margin-top:5px;}
.stat-green{color:var(--green)!important;}.stat-red{color:var(--red)!important;}.stat-yellow{color:var(--amber)!important;}

/* stock-card */
.stock-card{
  background:var(--bg2);border:1px solid var(--bdr);border-radius:var(--r2);
  padding:18px 14px;text-align:center;
  transition:transform .15s,border-color .15s,box-shadow .15s;
  position:relative;overflow:hidden;
}
.stock-card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:var(--accent-color,var(--green));opacity:.85;
}
.stock-card:hover{transform:translateY(-3px);border-color:var(--bdr2);box-shadow:0 12px 40px rgba(0,0,0,.6);}
.card-symbol{font-family:var(--mono);font-size:14px;font-weight:700;color:var(--fg);letter-spacing:.5px;}
.card-sector{font-family:var(--sans);font-size:9px;color:var(--fg4);margin:3px 0 10px;text-transform:uppercase;letter-spacing:1.5px;}
.card-change{font-family:var(--mono);font-size:28px;font-weight:700;line-height:1;margin-bottom:2px;}
.card-divider{border:none;border-top:1px solid var(--bdr);margin:10px 0;}
.card-detail{font-family:var(--mono);font-size:10px;color:var(--fg3);line-height:2;}
.card-score{font-family:var(--mono);font-size:30px;font-weight:700;line-height:1;}
.card-signal{font-family:var(--sans);font-size:11px;font-weight:600;margin:4px 0;}

/* section-header */
.section-header{display:flex;align-items:center;gap:10px;margin:24px 0 14px;padding-bottom:10px;border-bottom:1px solid var(--bdr);}
.section-title{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--fg);}
.section-badge{font-family:var(--mono);font-size:9px;background:var(--bg4);border:1px solid var(--bdr2);color:var(--fg3);padding:2px 8px;border-radius:4px;letter-spacing:1px;}

/* empty-state */
.empty-state{text-align:center;padding:64px 24px;}
.empty-icon{font-size:56px;margin-bottom:20px;opacity:.18;}
.empty-title{font-family:var(--mono);font-size:16px;color:var(--fg3);margin-bottom:12px;letter-spacing:2px;text-transform:uppercase;}
.empty-sub{font-family:var(--sans);font-size:14px;color:var(--fg4);line-height:1.9;max-width:380px;margin:0 auto;}
.empty-sub strong{color:var(--green);font-family:var(--mono);}

/* auth-hint */
.auth-hint{
  background:rgba(0,229,160,.03);border:1px solid rgba(0,229,160,.1);
  border-radius:8px;padding:10px 14px;
  font-family:var(--sans);font-size:12px;color:var(--fg3);line-height:1.7;margin:10px 0;
}

/* badge */
.badge{display:inline-block;font-family:var(--mono);font-size:8px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:2px 8px;border-radius:4px;}
.badge-admin{background:rgba(240,165,0,.12);border:1px solid rgba(240,165,0,.3);color:var(--amber);}
.badge-user{background:rgba(76,142,255,.1);border:1px solid rgba(76,142,255,.25);color:var(--blue);}
.badge-cloud{background:var(--glow);border:1px solid rgba(0,229,160,.25);color:var(--green);}
.badge-local{background:rgba(76,142,255,.1);border:1px solid rgba(76,142,255,.25);color:var(--blue);}

/* profile-card */
.profile-card{
  background:var(--bg3);border:1px solid var(--bdr);border-radius:var(--r2);
  padding:14px;margin-bottom:12px;position:relative;overflow:hidden;
}
.profile-card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,var(--green),var(--amber));
}
.avatar{
  width:36px;height:36px;border-radius:50%;flex-shrink:0;
  background:linear-gradient(135deg,var(--green),var(--green2));
  display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-size:12px;font-weight:700;color:var(--bg);
}

/* ctrl-panel */
.ctrl-panel{
  background:var(--bg2);border:1px solid var(--bdr);
  border-radius:var(--r2);padding:18px 22px 16px;margin-bottom:22px;
  position:relative;
}
.ctrl-panel::before{
  content:'ANALYSIS CONTROLS';
  position:absolute;top:-1px;left:18px;
  font-family:var(--mono);font-size:7px;letter-spacing:2.5px;
  color:var(--green);background:var(--bg2);padding:0 8px;transform:translateY(-50%);
}

/* sig badges */
.sig{display:inline-block;font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:3px 10px;border-radius:4px;}
.sig-sb{background:rgba(0,229,160,.12);border:1px solid rgba(0,229,160,.3);color:#00e5a0;}
.sig-b{background:rgba(0,229,160,.07);border:1px solid rgba(0,229,160,.2);color:#00b878;}
.sig-h{background:rgba(240,165,0,.1);border:1px solid rgba(240,165,0,.25);color:#f0a500;}
.sig-a{background:rgba(255,61,90,.1);border:1px solid rgba(255,61,90,.25);color:#ff3d5a;}

/* page-hero */
.page-hero{padding:28px 0 20px;border-bottom:1px solid var(--bdr);margin-bottom:24px;}
.page-eye{font-family:var(--mono);font-size:8px;letter-spacing:3px;text-transform:uppercase;color:var(--green);margin-bottom:8px;}
.page-h1{font-family:var(--sans);font-size:28px;font-weight:700;color:var(--fg);letter-spacing:-.5px;line-height:1.1;}
.page-sub{font-family:var(--sans);font-size:13px;color:var(--fg3);margin-top:5px;}

/* sec-wrap */
.sec-wrap{display:flex;align-items:center;gap:12px;margin:24px 0 14px;}
.sec-line{flex:1;height:1px;background:var(--bdr);}
.sec-title{font-family:var(--mono);font-size:9px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:var(--fg3);white-space:nowrap;}
.sec-badge{font-family:var(--mono);font-size:8px;padding:2px 8px;border-radius:4px;background:var(--bg4);border:1px solid var(--bdr2);color:var(--fg3);letter-spacing:1px;}

/* ticker bar */
.ticker-bar{background:var(--bg2);border:1px solid var(--bdr);border-radius:var(--r);padding:10px 18px;display:flex;gap:28px;overflow:hidden;margin-bottom:22px;align-items:center;}
.ti{display:flex;align-items:center;gap:8px;flex-shrink:0;}
.ti-sym{font-family:var(--mono);font-size:9px;letter-spacing:1.5px;color:var(--fg2);}
.ti-val{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--fg);}
.ti-pos{font-family:var(--mono);font-size:10px;color:var(--green);}
.ti-neg{font-family:var(--mono);font-size:10px;color:var(--red);}

/* Mobile */
@media(max-width:768px){
  .stat-bar{grid-template-columns:repeat(2,1fr)!important;}
  [data-testid="stHorizontalBlock"]{flex-direction:column!important;}
  [data-testid="stHorizontalBlock"]>div{width:100%!important;min-width:100%!important;}
}
"""


def inject() -> None:
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
