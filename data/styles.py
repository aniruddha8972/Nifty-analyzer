"""
frontend/styles.py
Premium dark terminal design system. Inject once via inject().
"""

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');

:root {
  --bg:    #04040a;  --bg2:  #09090f;  --bg3:  #0e0e17;  --bg4:  #141420;
  --bdr:   #1c1c2e;  --bdr2: #26263a;  --bdr3: #323248;
  --green: #00e5a0;  --glow: rgba(0,229,160,0.18);
  --gdim:  #00a370;  --gdark:#006644;
  --red:   #ff4560;  --rdim: #cc2040;
  --yel:   #f5a623;  --blue: #4c8eff;
  --white: #eeeef8;  --light:#9090aa;  --mid:  #5a5a78;  --dim:  #33334a;
  --mono:  'IBM Plex Mono', monospace;
  --sans:  'Inter', sans-serif;
  --rad:   10px;
}

html,body,[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{
  background:var(--bg)!important; font-family:var(--sans)!important; color:var(--white)!important;
}
[data-testid="stAppViewContainer"]::before {
  content:''; position:fixed; inset:0; pointer-events:none; z-index:0;
  background-image:linear-gradient(rgba(0,229,160,.012) 1px,transparent 1px),
    linear-gradient(90deg,rgba(0,229,160,.012) 1px,transparent 1px);
  background-size:40px 40px;
}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],footer,.stDeployButton{display:none!important;}
[data-testid="stMainBlockContainer"]{padding-top:1rem!important;}

/* Sidebar */
[data-testid="stSidebar"]{background:var(--bg2)!important;border-right:1px solid var(--bdr)!important;}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p,
[data-testid="stSidebar"] [data-testid="stMarkdown"] div{color:var(--mid)!important;}
[data-testid="stSidebar"] [data-testid="stExpander"]{
  background:var(--bg3)!important;border:1px solid var(--bdr)!important;
  border-radius:var(--rad)!important;margin-bottom:8px!important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary{
  font-family:var(--mono)!important;font-size:11px!important;
  letter-spacing:1px!important;color:var(--light)!important;padding:12px 16px!important;
}
[data-testid="stSidebar"] [data-testid="stExpander"] summary:hover{color:var(--green)!important;}

/* Text input */
[data-testid="stTextInput"] label{
  font-family:var(--mono)!important;font-size:9px!important;letter-spacing:2px!important;
  text-transform:uppercase!important;color:var(--mid)!important;margin-bottom:4px!important;
}
[data-testid="stTextInput"] input{
  background:var(--bg3)!important;border:1px solid var(--bdr2)!important;border-radius:8px!important;
  color:var(--white)!important;font-family:var(--mono)!important;font-size:13px!important;
  padding:10px 14px!important;transition:border-color .15s,box-shadow .15s!important;
}
[data-testid="stTextInput"] input:focus{
  border-color:var(--green)!important;box-shadow:0 0 0 3px var(--glow)!important;
}
[data-testid="stTextInput"] input::placeholder{color:var(--dim)!important;}

/* Number input */
[data-testid="stNumberInput"] label{
  font-family:var(--mono)!important;font-size:9px!important;letter-spacing:2px!important;
  text-transform:uppercase!important;color:var(--mid)!important;
}
[data-testid="stNumberInput"] input{
  background:var(--bg3)!important;border:1px solid var(--bdr2)!important;border-radius:8px!important;
  color:var(--white)!important;font-family:var(--mono)!important;font-size:13px!important;
}
[data-testid="stNumberInput"] input:focus{border-color:var(--green)!important;box-shadow:0 0 0 3px var(--glow)!important;}

/* Selectbox */
[data-testid="stSelectbox"] label{
  font-family:var(--mono)!important;font-size:9px!important;letter-spacing:2px!important;
  text-transform:uppercase!important;color:var(--mid)!important;
}
[data-testid="stSelectbox"]>div>div{
  background:var(--bg3)!important;border:1px solid var(--bdr2)!important;
  border-radius:8px!important;color:var(--white)!important;font-family:var(--sans)!important;
}

/* Date input */
[data-testid="stDateInput"] label{
  font-family:var(--mono)!important;font-size:9px!important;letter-spacing:2px!important;
  text-transform:uppercase!important;color:var(--mid)!important;
}
[data-testid="stDateInput"] input{
  background:var(--bg3)!important;border:1px solid var(--bdr2)!important;border-radius:8px!important;
  color:var(--white)!important;font-family:var(--mono)!important;font-size:13px!important;
}

/* Buttons */
[data-testid="stButton"]>button{
  font-family:var(--mono)!important;font-size:10px!important;letter-spacing:1.5px!important;
  text-transform:uppercase!important;border-radius:8px!important;
  transition:all .18s ease!important;height:42px!important;font-weight:600!important;
}
[data-testid="stButton"]>button[kind="primary"]{
  background:linear-gradient(135deg,var(--green),var(--gdim))!important;
  color:#030306!important;border:none!important;font-weight:700!important;
  box-shadow:0 2px 16px rgba(0,229,160,.25)!important;
}
[data-testid="stButton"]>button[kind="primary"]:hover{
  background:linear-gradient(135deg,#00ffb3,var(--green))!important;
  box-shadow:0 4px 24px rgba(0,229,160,.4)!important;transform:translateY(-1px)!important;
}
[data-testid="stButton"]>button:not([kind="primary"]){
  background:var(--bg3)!important;color:var(--light)!important;border:1px solid var(--bdr2)!important;
}
[data-testid="stButton"]>button:not([kind="primary"]):hover{
  border-color:var(--green)!important;color:var(--green)!important;
  background:rgba(0,229,160,.05)!important;box-shadow:0 0 14px rgba(0,229,160,.1)!important;
}

/* Download button */
[data-testid="stDownloadButton"]>button{
  font-family:var(--mono)!important;font-size:10px!important;letter-spacing:1px!important;
  background:transparent!important;border:1px solid var(--gdim)!important;
  color:var(--green)!important;border-radius:8px!important;transition:all .18s ease!important;
}
[data-testid="stDownloadButton"]>button:hover{
  background:rgba(0,229,160,.08)!important;box-shadow:0 0 16px rgba(0,229,160,.2)!important;
}

/* Tabs */
[data-testid="stTabs"] [role="tablist"]{
  gap:2px;border-bottom:1px solid var(--bdr);padding-bottom:0;background:transparent;
}
[data-testid="stTabs"] [role="tab"]{
  font-family:var(--mono)!important;font-size:10px!important;letter-spacing:1px!important;
  text-transform:uppercase!important;color:var(--mid)!important;background:transparent!important;
  border:1px solid transparent!important;border-bottom:none!important;
  border-radius:6px 6px 0 0!important;padding:8px 14px!important;transition:color .15s,background .15s!important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"]{
  color:var(--green)!important;background:var(--bg3)!important;
  border-color:var(--bdr2)!important;
}
[data-testid="stTabs"] [role="tab"]:hover:not([aria-selected="true"]){
  color:var(--light)!important;background:var(--bg3)!important;
}

/* Progress */
[data-testid="stProgress"]>div>div{background:var(--bdr)!important;border-radius:3px!important;}
[data-testid="stProgress"]>div>div>div{
  background:linear-gradient(90deg,var(--green),#00ffb3)!important;border-radius:3px!important;
  box-shadow:0 0 8px rgba(0,229,160,.4)!important;
}
[data-testid="stProgress"] p{font-family:var(--mono)!important;font-size:10px!important;color:var(--mid)!important;}

/* Dataframe */
[data-testid="stDataFrame"]{border:1px solid var(--bdr)!important;border-radius:var(--rad)!important;overflow:hidden!important;}

/* Alerts */
[data-testid="stAlert"]{border-radius:8px!important;font-family:var(--sans)!important;font-size:13px!important;}

/* Expander */
[data-testid="stExpander"]{border:1px solid var(--bdr)!important;border-radius:var(--rad)!important;background:var(--bg2)!important;}
[data-testid="stExpander"] summary{font-family:var(--mono)!important;font-size:11px!important;letter-spacing:1px!important;color:var(--light)!important;}

/* Caption */
[data-testid="stCaption"]{font-family:var(--mono)!important;font-size:10px!important;color:var(--dim)!important;letter-spacing:.5px!important;}

/* Scrollbar */
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:var(--bg2);}
::-webkit-scrollbar-thumb{background:var(--bdr2);border-radius:3px;}
::-webkit-scrollbar-thumb:hover{background:var(--bdr3);}

hr{border-color:var(--bdr)!important;margin:20px 0!important;}
h1,h2,h3,h4{font-family:var(--mono)!important;color:var(--white)!important;}

/* ═══════════ CUSTOM CLASSES ═══════════ */

.app-wordmark{font-family:var(--mono);font-size:9px;letter-spacing:5px;text-transform:uppercase;color:var(--green);margin-bottom:4px;}
.app-title{font-family:var(--mono);font-size:28px;font-weight:700;color:var(--white);letter-spacing:-1px;line-height:1.1;}
.app-subtitle{font-family:var(--sans);font-size:13px;color:var(--mid);margin-top:6px;}
.app-range{
  font-family:var(--mono);font-size:11px;color:var(--green);
  background:rgba(0,229,160,.06);border:1px solid rgba(0,229,160,.2);
  padding:4px 12px;border-radius:6px;display:inline-block;margin-top:8px;letter-spacing:.5px;
}

.stat-bar{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0;}
.stat-item{
  background:var(--bg2);border:1px solid var(--bdr);border-radius:var(--rad);
  padding:14px 18px;transition:border-color .18s,box-shadow .18s;
}
.stat-item:hover{border-color:var(--bdr2);box-shadow:0 4px 20px rgba(0,0,0,.4);}
.stat-label{font-family:var(--mono);font-size:8px;letter-spacing:2.5px;text-transform:uppercase;color:var(--dim);margin-bottom:8px;}
.stat-value{font-family:var(--mono);font-size:22px;font-weight:700;color:var(--white);line-height:1;}
.stat-sub{font-family:var(--sans);font-size:11px;color:var(--mid);margin-top:5px;}
.stat-green{color:#00e5a0!important;} .stat-red{color:#ff4560!important;} .stat-yellow{color:#f5a623!important;}

.stock-card{
  background:var(--bg2);border:1px solid var(--bdr);border-radius:var(--rad);
  padding:18px 14px;text-align:center;
  transition:transform .15s,border-color .15s,box-shadow .15s;
  position:relative;overflow:hidden;
}
.stock-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:var(--accent-color,var(--green));opacity:.85;}
.stock-card:hover{transform:translateY(-3px);border-color:var(--bdr2);box-shadow:0 12px 40px rgba(0,0,0,.6);}
.card-symbol{font-family:var(--mono);font-size:15px;font-weight:700;color:var(--white);letter-spacing:.5px;}
.card-sector{font-family:var(--sans);font-size:9px;color:var(--dim);margin:3px 0 10px;text-transform:uppercase;letter-spacing:1.5px;}
.card-change{font-family:var(--mono);font-size:28px;font-weight:700;line-height:1;margin-bottom:2px;}
.card-divider{border:none;border-top:1px solid var(--bdr);margin:10px 0;}
.card-detail{font-family:var(--mono);font-size:10px;color:var(--mid);line-height:2;}
.card-score{font-family:var(--mono);font-size:30px;font-weight:700;line-height:1;}
.card-signal{font-family:var(--sans);font-size:11px;font-weight:600;margin:4px 0;}

.section-header{display:flex;align-items:center;gap:10px;margin:24px 0 14px;padding-bottom:10px;border-bottom:1px solid var(--bdr);}
.section-title{font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:2.5px;text-transform:uppercase;color:var(--white);}
.section-badge{font-family:var(--mono);font-size:9px;background:var(--bg4);border:1px solid var(--bdr2);color:var(--mid);padding:2px 8px;border-radius:4px;letter-spacing:1px;}

.empty-state{text-align:center;padding:64px 24px;}
.empty-icon{font-size:56px;margin-bottom:20px;opacity:.18;}
.empty-title{font-family:var(--mono);font-size:18px;color:var(--mid);margin-bottom:12px;letter-spacing:2px;text-transform:uppercase;}
.empty-sub{font-family:var(--sans);font-size:14px;color:var(--dim);line-height:1.9;max-width:380px;margin:0 auto;}
.empty-sub strong{color:var(--green);font-family:var(--mono);}

.auth-hint{
  background:rgba(0,229,160,.03);border:1px solid rgba(0,229,160,.1);
  border-radius:8px;padding:10px 14px;
  font-family:var(--sans);font-size:12px;color:var(--mid);line-height:1.7;margin:10px 0;
}

.badge{display:inline-block;font-family:var(--mono);font-size:8px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:2px 8px;border-radius:4px;}
.badge-admin{background:rgba(245,166,35,.12);border:1px solid rgba(245,166,35,.3);color:#f5a623;}
.badge-user{background:rgba(76,142,255,.1);border:1px solid rgba(76,142,255,.25);color:#4c8eff;}
"""


def inject() -> None:
    import streamlit as st
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)
