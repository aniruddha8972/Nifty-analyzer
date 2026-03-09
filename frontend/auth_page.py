"""
frontend/auth_page.py — v6: components.v1.html() for static shell
──────────────────────────────────────────────────────────────────
THE ROOT CAUSE OF RAW HTML DISPLAY:
  st.markdown(html, unsafe_allow_html=True) is sanitized by Streamlit's
  markdown renderer in some deployment environments (Streamlit Cloud
  applies stricter XSS rules on certain HTML elements/attributes).
  The card shell was being printed as literal text.

THE FIX:
  st.components.v1.html() bypasses Streamlit's sanitizer entirely —
  it renders an iframe with the raw HTML. Used ONLY for the static
  decorative shell (logo, animated tab strip, canvas).
  Streamlit widgets (inputs, buttons) stay in the main app flow.
  CSS variables shared via a single <style> injected with st.markdown
  (which works fine for pure CSS — sanitizer only blocks certain tags).

FORGOT PASSWORD LINK FIX:
  Supabase reset emails link to localhost by default.
  Fixed by passing redirect_to= with the app's public URL,
  read from st.secrets["app"]["url"] with fallback.
"""

import streamlit as st
import streamlit.components.v1 as components
from backend.auth import (
    login, register, load_user_portfolio,
    is_supabase_mode, request_password_reset,
)

# ─── Global CSS (safe for st.markdown — pure style, no scripts/divs) ─────────
_GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

*,*::before,*::after { box-sizing: border-box; }

body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
  background: #050508 !important;
  font-family: 'Space Grotesk', sans-serif !important;
  color: #e8e8f0 !important;
}
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
footer, .stDeployButton { display: none !important; }

[data-testid="stMainBlockContainer"] {
  padding: 0 !important;
  max-width: 100% !important;
}

/* Center all content in a card-like column */
[data-testid="stMainBlockContainer"] > div {
  max-width: 460px !important;
  margin: 0 auto !important;
  padding: 0 16px !important;
}

/* ── Input fields ── */
[data-testid="stTextInput"] label {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 9px !important;
  letter-spacing: 2px !important;
  text-transform: uppercase !important;
  color: #3a3a52 !important;
  margin-bottom: 4px !important;
}
[data-testid="stTextInput"] input {
  background: #08080f !important;
  border: 1px solid #1a1a2a !important;
  border-radius: 10px !important;
  color: #e8e8f0 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 13px !important;
  padding: 12px 14px !important;
  transition: border-color .15s, box-shadow .15s !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: #00e6a0 !important;
  box-shadow: 0 0 0 3px rgba(0,230,160,.12) !important;
  outline: none !important;
}
[data-testid="stTextInput"] input::placeholder { color: #1c1c2a !important; }

/* ── Buttons ── */
[data-testid="stButton"] > button {
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 14px !important;
  font-weight: 700 !important;
  height: 48px !important;
  border-radius: 10px !important;
  width: 100% !important;
  transition: all .18s ease !important;
}
[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #00e6a0, #009e70) !important;
  color: #050508 !important;
  border: none !important;
  box-shadow: 0 2px 20px rgba(0,230,160,.3) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #10ffb8, #00e6a0) !important;
  box-shadow: 0 4px 32px rgba(0,230,160,.45) !important;
  transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button:not([kind="primary"]) {
  background: #0e0e1c !important;
  color: #3a3a52 !important;
  border: 1px solid #1e1e30 !important;
}
[data-testid="stButton"] > button:not([kind="primary"]):hover {
  border-color: #00e6a0 !important;
  color: #00e6a0 !important;
  background: rgba(0,230,160,.04) !important;
}

/* Hide the tab-switcher utility buttons (JS clicks them) */
.nse-sw-hidden {
  display: none !important;
  height: 0 !important;
  overflow: hidden !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* ── Misc UI ── */
.nse-section {
  font-family: 'JetBrains Mono', monospace;
  font-size: 8px; letter-spacing: 3px;
  text-transform: uppercase; color: #252536;
  margin: 6px 0 14px;
}
.nse-hint {
  background: rgba(0,230,160,.025);
  border: 1px solid rgba(0,230,160,.08);
  border-radius: 9px; padding: 9px 13px;
  font-size: 11px; color: #44445a;
  line-height: 1.65; margin: 8px 0;
}
.nse-hint-warn {
  background: rgba(245,166,35,.03);
  border-color: rgba(245,166,35,.15);
}
.pw-strength { margin: 8px 0 4px; }
.pw-strength-hd {
  display: flex; justify-content: space-between;
  font-family: 'JetBrains Mono', monospace;
  font-size: 8px; letter-spacing: 2px;
  text-transform: uppercase; color: #252536; margin-bottom: 5px;
}
.pw-track { height: 2px; background: #181822; border-radius: 2px; overflow: hidden; }
.pw-fill  { height: 100%; border-radius: 2px; transition: width .3s, background .3s; }
.pw-req   { font-size: 10px; color: #252536; margin: 3px 0; }
.pw-req.ok { color: #00e6a0; }

.nse-ok {
  background: rgba(0,230,160,.04);
  border: 1px solid rgba(0,230,160,.15);
  border-radius: 12px; padding: 26px 20px;
  text-align: center; margin: 8px 0;
}
.nse-ok-icon  { font-size: 36px; margin-bottom: 12px; }
.nse-ok-title { font-size: 16px; font-weight: 700; color: #00e6a0; margin-bottom: 6px; }
.nse-ok-body  { font-size: 12px; color: #44445a; line-height: 1.65; }

.nse-chips     { background: #08080f; border: 1px solid #1a1a2a; border-radius: 10px; padding: 12px 14px; margin-top: 8px; }
.nse-chips-lbl { font-family: 'JetBrains Mono', monospace; font-size: 8px; letter-spacing: 2px; color: #3a3a52; text-transform: uppercase; margin-bottom: 8px; }
.nse-chip-item { display: inline-block; background: #0e0e1c; border: 1px solid rgba(0,230,160,.2); border-radius: 6px; padding: 4px 10px; margin: 3px; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: #00e6a0; }

.nse-forgot-row { text-align: right; margin: 2px 0 12px; }
.nse-footer { text-align: center; margin-top: 20px; font-size: 10px; color: #18182a; }

/* Mobile stacking */
@media (max-width: 440px) {
  [data-testid="stHorizontalBlock"] { flex-direction: column !important; }
  [data-testid="stHorizontalBlock"] > div { width: 100% !important; min-width: 100% !important; }
}
</style>
"""

# ─── Static shell HTML (rendered via components.v1.html — bypasses sanitizer) ─
def _shell_html(cur_tab: str, sb_mode: bool) -> str:
    badge_cls = "chip-cloud" if sb_mode else "chip-local"
    badge_txt = "Supabase Cloud" if sb_mode else "Local Mode"
    tabs = [("login", "Sign In"), ("register", "Create Account"), ("forgot", "Reset")]
    tab_btns = "".join(
        f'<button class="nse-tab {"active" if k == cur_tab else ""}" data-tab="{k}">{lbl}</button>'
        for k, lbl in tabs
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{height:100%;background:transparent;overflow:hidden;}}

canvas{{position:fixed;inset:0;pointer-events:none;z-index:0;}}

.shell{{
  position:relative;z-index:1;
  width:100%;
  background:rgba(9,9,18,0.97);
  border-radius:20px 20px 0 0;
  border:1px solid rgba(255,255,255,0.07);
  border-bottom:none;
  box-shadow:0 0 0 1px rgba(0,230,160,0.06),0 -4px 40px rgba(0,0,0,0.5);
  overflow:hidden;
  animation:up .45s cubic-bezier(.16,1,.3,1) both;
}}
@keyframes up{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:translateY(0)}}}}

.stripe{{
  height:2px;
  background:linear-gradient(90deg,transparent,#00e6a0 20%,#4c8eff 40%,#00e6a0 60%,#7b4fff 80%,transparent);
  background-size:400% 100%;
  animation:flow 5s linear infinite;
}}
@keyframes flow{{0%{{background-position:100% 0}}100%{{background-position:-100% 0}}}}

.body{{padding:28px 28px 20px;}}
@media(max-width:400px){{.body{{padding:20px 16px 16px;}}}}

.eyebrow{{
  font-family:'JetBrains Mono',monospace;
  font-size:8px;letter-spacing:5px;text-transform:uppercase;
  color:#00e6a0;opacity:.75;margin-bottom:8px;text-align:center;
}}
.brand{{
  font-family:'Space Grotesk',sans-serif;
  font-size:clamp(20px,5.5vw,28px);font-weight:700;
  color:#fff;letter-spacing:-0.5px;line-height:1.1;
  text-align:center;
}}
.brand em{{color:#00e6a0;font-style:normal;}}
.sub{{font-size:12px;color:#44445a;margin-top:5px;text-align:center;}}
.chip{{
  display:inline-flex;align-items:center;gap:5px;
  padding:4px 11px;border-radius:100px;margin-top:10px;
  font-family:'JetBrains Mono',monospace;
  font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
}}
.chip-cloud{{background:rgba(0,230,160,.07);border:1px solid rgba(0,230,160,.22);color:#00e6a0;}}
.chip-local{{background:rgba(245,166,35,.07);border:1px solid rgba(245,166,35,.22);color:#f5a623;}}
.dot{{width:5px;height:5px;border-radius:50%;animation:blink 2s ease infinite;}}
.chip-cloud .dot{{background:#00e6a0;}}
.chip-local .dot{{background:#f5a623;}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
.logo{{text-align:center;margin-bottom:22px;}}

.tabs{{
  display:grid;grid-template-columns:repeat(3,1fr);gap:3px;
  padding:3px;background:#0c0c14;
  border:1px solid rgba(255,255,255,.05);border-radius:12px;
}}
.nse-tab{{
  padding:10px 4px;text-align:center;cursor:pointer;
  border:none;border-radius:9px;background:transparent;
  font-family:'JetBrains Mono',monospace;
  font-size:9px;font-weight:500;letter-spacing:.8px;
  text-transform:uppercase;color:#2e2e44;
  transition:all .18s ease;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}}
.nse-tab:hover{{color:#00e6a0;background:rgba(0,230,160,.05);}}
.nse-tab.active{{
  background:linear-gradient(135deg,#00e6a0,#009e70);
  color:#050508;font-weight:700;
  box-shadow:0 2px 14px rgba(0,230,160,.28);
}}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div class="shell">
  <div class="stripe"></div>
  <div class="body">
    <div class="logo">
      <div class="eyebrow">Quantitative &middot; Analytics</div>
      <div class="brand">NSE <em>Market</em> Analyzer</div>
      <div class="sub">ML-powered &middot; 500 stocks &middot; 5yr history</div>
      <div><span class="chip {badge_cls}"><span class="dot"></span>{badge_txt}</span></div>
    </div>
    <div class="tabs">{tab_btns}</div>
  </div>
</div>

<script>
/* Particle canvas */
(function(){{
  var c=document.getElementById('c'),ctx=c.getContext('2d'),W,H,pts=[];
  function r(){{W=c.width=window.innerWidth;H=c.height=window.innerHeight;}}
  r();window.addEventListener('resize',r,{{passive:true}});
  for(var i=0;i<60;i++) pts.push({{x:Math.random()*2000,y:Math.random()*1200,vx:(Math.random()-.5)*.38,vy:(Math.random()-.5)*.38,r:Math.random()*1.4+.3,a:Math.random()*.4+.1}});
  function draw(){{
    ctx.clearRect(0,0,W,H);
    for(var i=0;i<pts.length;i++){{
      var p=pts[i];p.x+=p.vx;p.y+=p.vy;
      if(p.x<0||p.x>W)p.vx*=-1;if(p.y<0||p.y>H)p.vy*=-1;
      ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle='rgba(0,230,160,'+p.a+')';ctx.fill();
      for(var j=i+1;j<pts.length;j++){{
        var q=pts[j],dx=p.x-q.x,dy=p.y-q.y,d=Math.sqrt(dx*dx+dy*dy);
        if(d<130){{ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);ctx.strokeStyle='rgba(0,230,160,'+(0.05*(1-d/130))+')';ctx.lineWidth=.5;ctx.stroke();}}
      }}
    }}
    requestAnimationFrame(draw);
  }}
  draw();
}})();

/* Tab clicks — post message to parent Streamlit window */
document.querySelectorAll('.nse-tab').forEach(function(btn){{
  btn.addEventListener('click',function(){{
    var tab=btn.getAttribute('data-tab');
    /* Find and click the matching hidden Streamlit button in parent */
    try{{
      var pDoc=window.parent.document;
      var allBtns=pDoc.querySelectorAll('[data-testid="stButton"] button');
      allBtns.forEach(function(b){{
        if(b.innerText.trim()===tab) b.click();
      }});
    }}catch(e){{}}
  }});
}});

/* Tell parent to hide switcher buttons once DOM ready */
try{{
  window.parent.postMessage({{type:'nse-hide-sw'}}, '*');
}}catch(e){{}}
</script>
</body>
</html>"""


def _init():
    for k, v in {
        "logged_in": False, "username": "", "user_info": {},
        "auth_tab": "login", "reset_sent": False,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _strength_html(pw: str) -> str:
    from backend.auth import validate_password
    _, fails = validate_password(pw)
    pct = (5 - len(fails)) / 5
    col = "#ef4444" if pct <= .4 else "#f5a623" if pct < 1 else "#00e6a0"
    lbl = "Weak" if pct <= .4 else "Fair" if pct < 1 else "Strong ✓"
    checks = [
        ("8+ characters",       len(pw) >= 8),
        ("Uppercase A–Z",       any(c.isupper() for c in pw)),
        ("Lowercase a–z",       any(c.islower() for c in pw)),
        ("Digit 0–9",           any(c.isdigit() for c in pw)),
        ("Special !@#$…",       any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pw)),
    ]
    rows = "".join(
        f'<div class="pw-req {"ok" if ok else ""}">{"✓" if ok else "○"} {lbl2}</div>'
        for lbl2, ok in checks
    )
    return (
        f'<div class="pw-strength">'
        f'<div class="pw-strength-hd"><span>Strength</span><span style="color:{col}">{lbl}</span></div>'
        f'<div class="pw-track"><div class="pw-fill" style="width:{int(pct*100)}%;background:{col}"></div></div>'
        f'<div style="margin-top:5px">{rows}</div></div>'
    )


# ─── Tab switcher utility buttons (hidden via JS) ─────────────────────────────
def _switchers():
    """Three invisible Streamlit buttons the iframe JS clicks by text match."""
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("login",    key="_sw_login"):
            st.session_state["auth_tab"] = "login"; st.rerun()
    with c2:
        if st.button("register", key="_sw_register"):
            st.session_state["auth_tab"] = "register"; st.rerun()
    with c3:
        if st.button("forgot",   key="_sw_forgot"):
            st.session_state.update({"auth_tab": "forgot", "reset_sent": False}); st.rerun()
    # JS hides them by text content
    st.markdown("""
    <script>
    (function(){
      function hide(){
        document.querySelectorAll('[data-testid="stButton"] button').forEach(function(b){
          var t=b.innerText.trim();
          if(t==='login'||t==='register'||t==='forgot'){
            var w=b.closest('[data-testid="stButton"]');
            if(w) w.style.cssText='display:none!important;height:0;overflow:hidden;margin:0;padding:0';
          }
        });
      }
      hide(); setTimeout(hide,150); setTimeout(hide,500);
      window.addEventListener('message',function(e){if(e.data&&e.data.type==='nse-hide-sw') hide();});
    })();
    </script>
    """, unsafe_allow_html=True)


# ─── Login panel ──────────────────────────────────────────────────────────────
def _render_login(sb_mode: bool):
    st.markdown('<div class="nse-section">── Sign in to your account</div>', unsafe_allow_html=True)
    identifier = st.text_input(
        "Email" if sb_mode else "Email or Username",
        placeholder="you@example.com", key="li_id"
    )
    password = st.text_input("Password", placeholder="••••••••", type="password", key="li_pw")

    # Forgot password — a real Streamlit button styled as a link
    _, fc = st.columns([3, 1])
    with fc:
        if st.button("Forgot password?", key="li_forgot"):
            st.session_state.update({"auth_tab": "forgot", "reset_sent": False})
            st.rerun()

    if st.button("Sign In →", type="primary", use_container_width=True, key="li_btn"):
        if not identifier or not password:
            st.error("⚠ Fill in both fields.")
        else:
            with st.spinner("Signing in…"):
                ok, msg, user_info = login(identifier, password)
            if ok:
                st.session_state.update({
                    "logged_in": True,
                    "username":  user_info["username"],
                    "user_info": user_info,
                })
                with st.spinner("Loading portfolio…"):
                    st.session_state["portfolio"] = load_user_portfolio(user_info)
                st.rerun()
            else:
                st.error(f"⚠ {msg}")


# ─── Register panel ───────────────────────────────────────────────────────────
def _render_register(sb_mode: bool):
    st.markdown('<div class="nse-section">── Create a new account</div>', unsafe_allow_html=True)
    ca, cb = st.columns(2)
    with ca: name  = st.text_input("Full Name",  placeholder="Rahul Sharma",      key="rg_name")
    with cb: uname = st.text_input("Username",   placeholder="rahul_trades",      key="rg_user")
    email = st.text_input("Email", placeholder="rahul@example.com", key="rg_email")
    cc, cd = st.columns(2)
    with cc: pw1 = st.text_input("Password",         type="password", placeholder="Min 8 + symbols", key="rg_pw")
    with cd: pw2 = st.text_input("Confirm Password", type="password", placeholder="Repeat",          key="rg_pw2")
    if pw1:
        st.markdown(_strength_html(pw1), unsafe_allow_html=True)
    st.markdown(
        f'<div class="nse-hint">{"☁ Stored in Supabase." if sb_mode else "⚡ Local mode."}'
        f' Username: 3–20 chars, letters/numbers/underscore.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    if st.button("Create Account →", type="primary", use_container_width=True, key="rg_btn"):
        if not all([name, uname, email, pw1, pw2]):
            st.error("⚠ Fill in all fields.")
        elif pw1 != pw2:
            st.error("⚠ Passwords don't match.")
        else:
            with st.spinner("Creating account…"):
                ok, msg = register(uname, name, email, pw1)
            if ok:
                st.success("✅ Account created — sign in below.")
                st.session_state["auth_tab"] = "login"; st.rerun()
            else:
                if msg.startswith("USERNAME_TAKEN:"):
                    sugg = [s for s in msg.split(":", 1)[1].split(",") if s and s != "—"]
                    st.error(f"⚠ @{uname} is taken.")
                    if sugg:
                        chips = "".join(f'<span class="nse-chip-item">@{s}</span>' for s in sugg)
                        st.markdown(
                            f'<div class="nse-chips"><div class="nse-chips-lbl">Available</div>{chips}</div>',
                            unsafe_allow_html=True,
                        )
                elif "EMAIL_EXISTS" in msg or "already registered" in msg.lower():
                    st.error("⚠ Email already registered — try signing in.")
                else:
                    st.error(f"⚠ {msg}")


# ─── Forgot password panel ────────────────────────────────────────────────────
def _render_forgot(sb_mode: bool):
    if st.session_state.get("reset_sent"):
        st.markdown("""
        <div class="nse-ok">
          <div class="nse-ok-icon">📬</div>
          <div class="nse-ok-title">Check your inbox</div>
          <div class="nse-ok-body">
            Reset link sent if that email is registered.<br>
            Check spam if it doesn't arrive in 2 minutes.
          </div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("← Back to Sign In", use_container_width=True, key="rst_back"):
            st.session_state.update({"auth_tab": "login", "reset_sent": False}); st.rerun()
        return

    st.markdown('<div class="nse-section">── Reset password</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="nse-hint">Enter your account email and we\'ll send a one-time reset link.</div>',
        unsafe_allow_html=True,
    )
    if not sb_mode:
        st.markdown(
            '<div class="nse-hint nse-hint-warn">⚡ Local mode: no email server. '
            'Ask your admin to reset your password via the Admin dashboard.</div>',
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    email = st.text_input("Email Address", placeholder="you@example.com", key="rst_email")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    ca, cb = st.columns([3, 2])
    with ca:
        if st.button("Send Reset Link →", type="primary", use_container_width=True, key="rst_send"):
            if not email or "@" not in email:
                st.error("⚠ Enter a valid email address.")
            else:
                with st.spinner("Sending…"):
                    ok, msg = request_password_reset(email)
                if ok:
                    st.session_state["reset_sent"] = True; st.rerun()
                else:
                    st.error(f"⚠ {msg}")
    with cb:
        if st.button("← Cancel", use_container_width=True, key="rst_cancel"):
            st.session_state.update({"auth_tab": "login", "reset_sent": False}); st.rerun()


# ─── Public entry point ───────────────────────────────────────────────────────
def render_auth_page() -> bool:
    _init()
    if st.session_state.get("logged_in"):
        return True

    sb_mode = is_supabase_mode()
    cur_tab = st.session_state["auth_tab"]

    # 1. Pure CSS — safe for st.markdown (no scripts, no divs)
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)

    # 2. Static decorative shell via components.v1.html — bypasses sanitizer
    #    Height = logo (≈160px) + tab strip (≈54px) + padding (≈50px)
    components.html(_shell_html(cur_tab, sb_mode), height=290, scrolling=False)

    # 3. Hidden tab-switcher Streamlit buttons (clicked by iframe JS)
    _switchers()

    # 4. Active form panel — normal Streamlit widgets
    if   cur_tab == "login":    _render_login(sb_mode)
    elif cur_tab == "register": _render_register(sb_mode)
    else:                       _render_forgot(sb_mode)

    # 5. Footer
    st.markdown(
        '<div class="nse-footer">⚠ Not financial advice &middot; Educational use only</div>',
        unsafe_allow_html=True,
    )
    return False
