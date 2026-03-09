"""
frontend/auth_page.py  —  v5: CSS-layer card (Streamlit-safe)
──────────────────────────────────────────────────────────────
Root fix: Streamlit cannot nest widgets inside HTML divs across
markdown calls. Solution: the card is a pure CSS fixed overlay
(positioned, z-indexed). Streamlit widgets render in normal flow
but appear visually inside the card via CSS scoping.

Tabs: Sign In | Create Account | Reset Password
"""

import streamlit as st
from backend.auth import (
    login, register, load_user_portfolio,
    is_supabase_mode, request_password_reset,
)

# ── All CSS in one injection ──────────────────────────────────────────────────
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

*,*::before,*::after{box-sizing:border-box;}

html,body{height:100%;}
body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"]{
  background:#050508 !important;
  font-family:'Space Grotesk',sans-serif !important;
  color:#e8e8f0 !important;
}
[data-testid="stHeader"],[data-testid="stToolbar"],
[data-testid="stDecoration"],footer,.stDeployButton{
  display:none !important;
}

/* Push main block down so card top has room */
[data-testid="stMainBlockContainer"]{
  padding-top: 0 !important;
  max-width: 100% !important;
}

/* ── Particle canvas ── */
#nse-bg{
  position:fixed; inset:0; z-index:0;
  pointer-events:none;
}

/* ── Full-page auth centering shell ── */
.nse-page{
  position:relative; z-index:1;
  min-height:100vh;
  display:flex; flex-direction:column;
  align-items:center; justify-content:flex-start;
  padding:40px 16px 60px;
}

/* ── Card — purely visual, no DOM nesting needed ── */
.nse-card{
  width:100%; max-width:460px;
  background:rgba(9,9,18,0.95);
  backdrop-filter:blur(20px);
  border-radius:20px;
  border:1px solid rgba(255,255,255,0.07);
  overflow:hidden;
  box-shadow:
    0 0 0 1px rgba(0,230,160,0.07),
    0 28px 70px rgba(0,0,0,0.75),
    inset 0 1px 0 rgba(255,255,255,0.04);
  animation:cardIn .45s cubic-bezier(.16,1,.3,1) both;
}
@keyframes cardIn{
  from{opacity:0;transform:translateY(24px) scale(.97);}
  to  {opacity:1;transform:translateY(0)    scale(1);}
}

.nse-stripe{
  height:2px; width:100%;
  background:linear-gradient(90deg,
    transparent 0%,#00e6a0 20%,#4c8eff 40%,
    #00e6a0 60%,#7b4fff 80%,transparent 100%);
  background-size:400% 100%;
  animation:stripe 5s linear infinite;
}
@keyframes stripe{0%{background-position:100% 0}100%{background-position:-100% 0}}

.nse-card-body{padding:32px 32px 28px;}
@media(max-width:500px){.nse-card-body{padding:24px 18px 22px;}}

/* ── Logo ── */
.nse-logo{text-align:center;margin-bottom:26px;}
.nse-eyebrow{
  font-family:'JetBrains Mono',monospace;
  font-size:8px;letter-spacing:5px;text-transform:uppercase;
  color:#00e6a0;margin-bottom:10px;opacity:.8;
}
.nse-brand{
  font-size:clamp(20px,6vw,28px);font-weight:700;
  color:#fff;letter-spacing:-0.5px;line-height:1.1;
}
.nse-brand em{color:#00e6a0;font-style:normal;}
.nse-sub{font-size:12px;color:#44445a;margin-top:6px;}
.nse-chip{
  display:inline-flex;align-items:center;gap:5px;
  margin-top:11px;padding:4px 12px;border-radius:100px;
  font-family:'JetBrains Mono',monospace;
  font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
}
.chip-cloud{background:rgba(0,230,160,.06);border:1px solid rgba(0,230,160,.2);color:#00e6a0;}
.chip-local{background:rgba(245,166,35,.06);border:1px solid rgba(245,166,35,.2);color:#f5a623;}
.chip-dot{width:5px;height:5px;border-radius:50%;animation:blink 2s ease infinite;}
.chip-cloud .chip-dot{background:#00e6a0;}
.chip-local .chip-dot{background:#f5a623;}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.25}}

/* ── Tab strip ── */
.nse-tabs{
  display:grid;grid-template-columns:repeat(3,1fr);gap:3px;
  padding:3px;background:#0c0c14;
  border:1px solid rgba(255,255,255,.05);
  border-radius:12px;margin-bottom:24px;
}
.nse-tab{
  padding:10px 4px;text-align:center;
  cursor:pointer;border:none;border-radius:9px;
  background:transparent;
  font-family:'JetBrains Mono',monospace;
  font-size:9px;font-weight:500;letter-spacing:1px;
  text-transform:uppercase;color:#2e2e44;
  transition:all .18s ease;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.nse-tab:hover{color:#00e6a0;background:rgba(0,230,160,.05);}
.nse-tab.active{
  background:linear-gradient(135deg,#00e6a0,#009e70);
  color:#050508;font-weight:700;
  box-shadow:0 2px 14px rgba(0,230,160,.28);
}

/* ── Section label ── */
.nse-section{
  font-family:'JetBrains Mono',monospace;
  font-size:8px;letter-spacing:3px;text-transform:uppercase;
  color:#252536;margin-bottom:14px;
}

/* ── Hint boxes ── */
.nse-hint{
  background:rgba(0,230,160,.025);
  border:1px solid rgba(0,230,160,.08);
  border-radius:9px;padding:9px 13px;
  font-size:11px;color:#44445a;line-height:1.65;margin:8px 0;
}
.nse-hint-warn{
  background:rgba(245,166,35,.03);
  border-color:rgba(245,166,35,.15);
}

/* ── Streamlit widget overrides — scoped via page class ── */
[data-testid="stTextInput"] label{
  font-family:'JetBrains Mono',monospace !important;
  font-size:9px !important;letter-spacing:2px !important;
  text-transform:uppercase !important;color:#3a3a52 !important;
  margin-bottom:4px !important;
}
[data-testid="stTextInput"] input{
  background:#08080f !important;
  border:1px solid #1a1a28 !important;
  border-radius:10px !important;
  color:#e8e8f0 !important;
  font-family:'JetBrains Mono',monospace !important;
  font-size:13px !important;
  padding:12px 14px !important;
  transition:border-color .15s,box-shadow .15s !important;
}
[data-testid="stTextInput"] input:focus{
  border-color:#00e6a0 !important;
  box-shadow:0 0 0 3px rgba(0,230,160,.12) !important;
  outline:none !important;
}
[data-testid="stTextInput"] input::placeholder{color:#1c1c2a !important;}

[data-testid="stButton"]>button{
  font-family:'Space Grotesk',sans-serif !important;
  font-size:14px !important;font-weight:700 !important;
  height:48px !important;border-radius:10px !important;
  width:100% !important;
  transition:all .18s ease !important;
}
[data-testid="stButton"]>button[kind="primary"]{
  background:linear-gradient(135deg,#00e6a0,#009e70) !important;
  color:#050508 !important;border:none !important;
  box-shadow:0 2px 20px rgba(0,230,160,.3) !important;
}
[data-testid="stButton"]>button[kind="primary"]:hover{
  background:linear-gradient(135deg,#10ffb8,#00e6a0) !important;
  box-shadow:0 4px 32px rgba(0,230,160,.45) !important;
  transform:translateY(-1px) !important;
}
[data-testid="stButton"]>button:not([kind="primary"]){
  background:#0e0e1c !important;color:#3a3a52 !important;
  border:1px solid #1e1e30 !important;
}
[data-testid="stButton"]>button:not([kind="primary"]):hover{
  border-color:#00e6a0 !important;color:#00e6a0 !important;
  background:rgba(0,230,160,.04) !important;
}

/* ── Password strength ── */
.pw-strength{margin:8px 0 4px;}
.pw-strength-hd{
  display:flex;justify-content:space-between;
  font-family:'JetBrains Mono',monospace;
  font-size:8px;letter-spacing:2px;text-transform:uppercase;
  color:#252536;margin-bottom:5px;
}
.pw-track{height:2px;background:#181822;border-radius:2px;overflow:hidden;}
.pw-fill{height:100%;border-radius:2px;transition:width .3s,background .3s;}
.pw-req{font-size:10px;color:#252536;margin:3px 0;}
.pw-req.ok{color:#00e6a0;}

/* ── Success box ── */
.nse-ok{
  background:rgba(0,230,160,.04);
  border:1px solid rgba(0,230,160,.15);
  border-radius:12px;padding:26px 20px;
  text-align:center;margin:8px 0;
}
.nse-ok-icon{font-size:36px;margin-bottom:12px;}
.nse-ok-title{
  font-size:16px;font-weight:700;color:#00e6a0;margin-bottom:6px;
}
.nse-ok-body{font-size:12px;color:#44445a;line-height:1.65;}

/* ── Username chips ── */
.nse-chips{
  background:#08080f;border:1px solid #1a1a28;
  border-radius:10px;padding:12px 14px;margin-top:8px;
}
.nse-chips-lbl{
  font-family:'JetBrains Mono',monospace;
  font-size:8px;letter-spacing:2px;color:#3a3a52;
  text-transform:uppercase;margin-bottom:8px;
}
.nse-chip-item{
  display:inline-block;background:#0e0e1c;
  border:1px solid rgba(0,230,160,.2);border-radius:6px;
  padding:4px 10px;margin:3px;
  font-family:'JetBrains Mono',monospace;
  font-size:11px;color:#00e6a0;
}

/* ── Forgot link ── */
.nse-forgot{
  text-align:right;margin:3px 0 12px;
}
.nse-forgot button{
  background:none;border:none;cursor:pointer;
  font-family:'Space Grotesk',sans-serif;
  font-size:11px;color:#2a2a3e;
  transition:color .15s;padding:0;
}
.nse-forgot button:hover{color:#00e6a0;}

/* ── Footer ── */
.nse-footer{
  text-align:center;margin-top:20px;
  font-size:10px;color:#18182a;letter-spacing:.3px;
}

/* ── Mobile stacking for two-column form rows ── */
@media(max-width:440px){
  [data-testid="stHorizontalBlock"]{flex-direction:column !important;}
  [data-testid="stHorizontalBlock"]>div{
    width:100% !important;min-width:100% !important;
  }
  .nse-tab{font-size:8px;letter-spacing:.3px;}
}
</style>
"""

_CANVAS = """
<canvas id="nse-bg"></canvas>
<script>
(function(){
  var c=document.getElementById('nse-bg');
  if(!c)return;
  var x=c.getContext('2d'),W,H,pts=[];
  function rsz(){W=c.width=window.innerWidth;H=c.height=window.innerHeight;}
  rsz();window.addEventListener('resize',rsz,{passive:true});
  for(var i=0;i<65;i++) pts.push({
    x:Math.random()*2000,y:Math.random()*1200,
    vx:(Math.random()-.5)*.38,vy:(Math.random()-.5)*.38,
    r:Math.random()*1.4+.3,a:Math.random()*.4+.1
  });
  function draw(){
    x.clearRect(0,0,W,H);
    for(var i=0;i<pts.length;i++){
      var p=pts[i];
      p.x+=p.vx;p.y+=p.vy;
      if(p.x<0||p.x>W)p.vx*=-1;
      if(p.y<0||p.y>H)p.vy*=-1;
      x.beginPath();x.arc(p.x,p.y,p.r,0,Math.PI*2);
      x.fillStyle='rgba(0,230,160,'+p.a+')';x.fill();
      for(var j=i+1;j<pts.length;j++){
        var q=pts[j],dx=p.x-q.x,dy=p.y-q.y,d=Math.sqrt(dx*dx+dy*dy);
        if(d<140){
          x.beginPath();x.moveTo(p.x,p.y);x.lineTo(q.x,q.y);
          x.strokeStyle='rgba(0,230,160,'+(0.055*(1-d/140))+')';
          x.lineWidth=.5;x.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
})();
</script>
"""

_TAB_JS = """
<script>
(function(){
  /* Wire visual .nse-tab clicks → matching hidden st button by data-sw attr */
  function wire(){
    var tabs=document.querySelectorAll('.nse-tab[data-sw]');
    if(!tabs.length){setTimeout(wire,120);return;}
    tabs.forEach(function(tab){
      if(tab._wired) return; tab._wired=true;
      tab.addEventListener('click',function(){
        var key=tab.getAttribute('data-sw');
        var btn=document.querySelector('[data-sw-btn="'+key+'"] button');
        if(btn) btn.click();
      });
    });
  }
  wire();
  /* Wire forgot-password link */
  function wireForgot(){
    var el=document.getElementById('nse-forgot-btn');
    if(!el){setTimeout(wireForgot,120);return;}
    if(el._wired) return; el._wired=true;
    el.addEventListener('click',function(){
      var btn=document.querySelector('[data-sw-btn="forgot"] button');
      if(btn) btn.click();
    });
  }
  wireForgot();
})();
</script>
"""


def _init():
    for k,v in {"logged_in":False,"username":"","user_info":{},"auth_tab":"login","reset_sent":False}.items():
        if k not in st.session_state: st.session_state[k]=v


def _strength_html(pw: str) -> str:
    from backend.auth import validate_password
    _,fails=validate_password(pw)
    pct=(5-len(fails))/5
    col="#ef4444" if pct<=.4 else "#f5a623" if pct<1 else "#00e6a0"
    lbl="Weak" if pct<=.4 else "Fair" if pct<1 else "Strong ✓"
    checks=[
        ("8+ characters",        len(pw)>=8),
        ("Uppercase A–Z",        any(c.isupper() for c in pw)),
        ("Lowercase a–z",        any(c.islower() for c in pw)),
        ("Digit 0–9",            any(c.isdigit() for c in pw)),
        ("Special char !@#$…",   any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pw)),
    ]
    rows="".join(f'<div class="pw-req {"ok" if ok else ""}">{"✓" if ok else "○"} {lbl2}</div>' for lbl2,ok in checks)
    return (f'<div class="pw-strength">'
            f'<div class="pw-strength-hd"><span>Strength</span><span style="color:{col}">{lbl}</span></div>'
            f'<div class="pw-track"><div class="pw-fill" style="width:{int(pct*100)}%;background:{col}"></div></div>'
            f'<div style="margin-top:5px">{rows}</div></div>')


def _sw_btn(key: str):
    """Render a hidden switcher button tagged with data-sw-btn for JS targeting."""
    st.markdown(f'<div data-sw-btn="{key}" style="display:none">', unsafe_allow_html=True)
    if st.button(key, key=f"_sw_{key}"):
        st.session_state["auth_tab"] = key
        if key == "forgot": st.session_state["reset_sent"] = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _render_login(sb_mode: bool):
    st.markdown('<div class="nse-section">── Sign in to your account</div>', unsafe_allow_html=True)
    identifier=st.text_input("Email" if sb_mode else "Email or Username", placeholder="you@example.com", key="li_id")
    password  =st.text_input("Password", placeholder="••••••••", type="password", key="li_pw")

    # Forgot link — JS will click the hidden forgot switcher button
    st.markdown(
        '<div class="nse-forgot"><button id="nse-forgot-btn">Forgot password?</button></div>',
        unsafe_allow_html=True,
    )

    if st.button("Sign In →", type="primary", use_container_width=True, key="li_btn"):
        if not identifier or not password:
            st.error("⚠ Fill in both fields.")
        else:
            with st.spinner("Signing in…"):
                ok,msg,user_info=login(identifier,password)
            if ok:
                st.session_state.update({"logged_in":True,"username":user_info["username"],"user_info":user_info})
                with st.spinner("Loading portfolio…"):
                    st.session_state["portfolio"]=load_user_portfolio(user_info)
                st.rerun()
            else:
                st.error(f"⚠ {msg}")


def _render_register(sb_mode: bool):
    st.markdown('<div class="nse-section">── Create a new account</div>', unsafe_allow_html=True)
    ca,cb=st.columns(2)
    with ca: name =st.text_input("Full Name",  placeholder="Rahul Sharma",      key="rg_name")
    with cb: uname=st.text_input("Username",   placeholder="rahul_trades",      key="rg_user")
    email=st.text_input("Email",               placeholder="rahul@example.com", key="rg_email")
    cc,cd=st.columns(2)
    with cc: pw1=st.text_input("Password",         type="password", placeholder="Min 8 + symbols", key="rg_pw")
    with cd: pw2=st.text_input("Confirm Password", type="password", placeholder="Repeat",          key="rg_pw2")
    if pw1: st.markdown(_strength_html(pw1), unsafe_allow_html=True)
    st.markdown(
        f'<div class="nse-hint">{"☁ Stored in Supabase." if sb_mode else "⚡ Local mode — stored on disk."}'
        f' Username: 3–20 chars, letters/numbers/underscore.</div>',
        unsafe_allow_html=True)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if st.button("Create Account →", type="primary", use_container_width=True, key="rg_btn"):
        if not all([name,uname,email,pw1,pw2]):
            st.error("⚠ Fill in all fields.")
        elif pw1!=pw2:
            st.error("⚠ Passwords don't match.")
        else:
            with st.spinner("Creating account…"):
                ok,msg=register(uname,name,email,pw1)
            if ok:
                st.success("✅ Account created — sign in below.")
                st.session_state["auth_tab"]="login"; st.rerun()
            else:
                if msg.startswith("USERNAME_TAKEN:"):
                    sugg=[s for s in msg.split(":",1)[1].split(",") if s and s!="—"]
                    st.error(f"⚠ @{uname} is taken.")
                    if sugg:
                        chips="".join(f'<span class="nse-chip-item">@{s}</span>' for s in sugg)
                        st.markdown(f'<div class="nse-chips"><div class="nse-chips-lbl">Available</div>{chips}</div>', unsafe_allow_html=True)
                elif "EMAIL_EXISTS" in msg or "already registered" in msg.lower():
                    st.error("⚠ Email already registered — try signing in.")
                else:
                    st.error(f"⚠ {msg}")


def _render_forgot(sb_mode: bool):
    if st.session_state.get("reset_sent"):
        st.markdown("""<div class="nse-ok">
          <div class="nse-ok-icon">📬</div>
          <div class="nse-ok-title">Check your inbox</div>
          <div class="nse-ok-body">Reset link sent if that email is registered.<br>
          Check spam if it doesn't arrive in 2 minutes.</div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("← Back to Sign In", use_container_width=True, key="rst_back"):
            st.session_state.update({"auth_tab":"login","reset_sent":False}); st.rerun()
        return

    st.markdown('<div class="nse-section">── Reset password</div>', unsafe_allow_html=True)
    st.markdown('<div class="nse-hint">Enter your account email and we\'ll send a one-time reset link.</div>', unsafe_allow_html=True)
    if not sb_mode:
        st.markdown('<div class="nse-hint nse-hint-warn">⚡ Local mode: no email server. Ask your admin to reset your password via the Admin dashboard.</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    email=st.text_input("Email Address", placeholder="you@example.com", key="rst_email")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    ca,cb=st.columns([3,2])
    with ca:
        if st.button("Send Reset Link →", type="primary", use_container_width=True, key="rst_send"):
            if not email or "@" not in email:
                st.error("⚠ Enter a valid email.")
            else:
                with st.spinner("Sending…"):
                    ok,msg=request_password_reset(email)
                if ok:
                    st.session_state["reset_sent"]=True; st.rerun()
                else:
                    st.error(f"⚠ {msg}")
    with cb:
        if st.button("← Cancel", use_container_width=True, key="rst_cancel"):
            st.session_state.update({"auth_tab":"login","reset_sent":False}); st.rerun()


def render_auth_page() -> bool:
    _init()
    if st.session_state.get("logged_in"): return True

    sb_mode=is_supabase_mode()
    cur_tab=st.session_state["auth_tab"]

    # ── 1. Inject CSS ────────────────────────────────────────────────
    st.markdown(_CSS, unsafe_allow_html=True)

    # ── 2. Canvas (animated in step 6) ──────────────────────────────
    st.markdown(_CANVAS, unsafe_allow_html=True)

    # ── 3. Hidden switcher buttons (DOM-accessible by JS) ───────────
    _sw_btn("login"); _sw_btn("register"); _sw_btn("forgot")

    # ── 4. Page shell + card header (pure HTML, no widgets inside) ──
    badge_cls ="chip-cloud" if sb_mode else "chip-local"
    badge_txt ="Supabase Cloud" if sb_mode else "Local Mode"
    act={"login":"","register":"","forgot":""}; act[cur_tab]="active"

    st.markdown(f"""
    <div class="nse-page">
      <div class="nse-card">
        <div class="nse-stripe"></div>
        <div class="nse-card-body">

          <div class="nse-logo">
            <div class="nse-eyebrow">Quantitative &middot; Analytics</div>
            <div class="nse-brand">NSE <em>Market</em> Analyzer</div>
            <div class="nse-sub">ML-powered &middot; 500 stocks &middot; 5yr history</div>
            <div>
              <span class="nse-chip {badge_cls}">
                <span class="chip-dot"></span>{badge_txt}
              </span>
            </div>
          </div>

          <div class="nse-tabs">
            <button class="nse-tab {act['login']}"    data-sw="login">Sign In</button>
            <button class="nse-tab {act['register']}" data-sw="register">Create Account</button>
            <button class="nse-tab {act['forgot']}"   data-sw="forgot">Reset</button>
          </div>

        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 5. Form widgets (rendered by Streamlit in normal flow) ───────
    # We use CSS to visually merge them with the card via margin trickery.
    # A pseudo-card wraps only the widget area.
    st.markdown("""
    <style>
    /* Pull the widget area up to appear inside the card */
    [data-testid="stMainBlockContainer"] > div > div:nth-child(5) ~ div {
      max-width:460px !important;
      margin:0 auto !important;
      background:rgba(9,9,18,0.95) !important;
      border:1px solid rgba(255,255,255,0.07) !important;
      border-top:none !important;
      border-radius:0 0 20px 20px !important;
      padding:0 32px 28px !important;
    }
    @media(max-width:500px){
      [data-testid="stMainBlockContainer"] > div > div:nth-child(5) ~ div {
        padding:0 18px 22px !important;
      }
    }
    </style>
    """, unsafe_allow_html=True)

    if   cur_tab=="login":    _render_login(sb_mode)
    elif cur_tab=="register": _render_register(sb_mode)
    else:                     _render_forgot(sb_mode)

    st.markdown('<div class="nse-footer">⚠ Not financial advice &middot; Educational use only</div>', unsafe_allow_html=True)

    # ── 6. Tab-wiring JS ─────────────────────────────────────────────
    st.markdown(_TAB_JS, unsafe_allow_html=True)

    return False
