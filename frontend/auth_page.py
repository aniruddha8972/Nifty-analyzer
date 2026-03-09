"""
frontend/auth_page.py  —  v7: OTP-based auth UI
─────────────────────────────────────────────────
Two tabs:
  Sign In:  email → [Send Code] → 6-digit OTP input → [Verify]
  Register: name + username + email → [Create & Send Code] → OTP → [Verify]

Shell rendered via st.components.v1.html() — bypasses Streamlit's
HTML sanitizer (fixes the raw-HTML display bug).

Local mode: OTP code is shown on screen with a warning banner
(no email server available).
"""

import streamlit as st
import streamlit.components.v1 as components
from backend.auth import (
    send_otp, verify_otp, register,
    load_user_portfolio, is_supabase_mode,
)


# ── Global CSS (pure style — safe for st.markdown) ────────────────────────────
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
[data-testid="stHeader"],[data-testid="stToolbar"],
[data-testid="stDecoration"],footer,.stDeployButton { display:none !important; }
[data-testid="stMainBlockContainer"] { padding:0 !important; max-width:100% !important; }
[data-testid="stMainBlockContainer"] > div {
  max-width: 460px !important;
  margin: 0 auto !important;
  padding: 0 16px !important;
}

/* Inputs */
[data-testid="stTextInput"] label {
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 9px !important; letter-spacing: 2px !important;
  text-transform: uppercase !important; color: #3a3a52 !important;
  margin-bottom: 4px !important;
}
[data-testid="stTextInput"] input {
  background: #08080f !important; border: 1px solid #1a1a2a !important;
  border-radius: 10px !important; color: #e8e8f0 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 13px !important; padding: 12px 14px !important;
  transition: border-color .15s, box-shadow .15s !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: #00e6a0 !important;
  box-shadow: 0 0 0 3px rgba(0,230,160,.12) !important; outline: none !important;
}
[data-testid="stTextInput"] input::placeholder { color: #1c1c2a !important; }

/* OTP input — big centered digits */
[data-testid="stTextInput"].otp-input input {
  font-size: 28px !important; text-align: center !important;
  letter-spacing: 10px !important; padding: 14px !important;
  font-weight: 700 !important;
}

/* Buttons */
[data-testid="stButton"] > button {
  font-family: 'Space Grotesk', sans-serif !important;
  font-size: 14px !important; font-weight: 700 !important;
  height: 48px !important; border-radius: 10px !important;
  width: 100% !important; transition: all .18s ease !important;
}
[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #00e6a0, #009e70) !important;
  color: #050508 !important; border: none !important;
  box-shadow: 0 2px 20px rgba(0,230,160,.3) !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #10ffb8, #00e6a0) !important;
  box-shadow: 0 4px 32px rgba(0,230,160,.45) !important;
  transform: translateY(-1px) !important;
}
[data-testid="stButton"] > button:not([kind="primary"]) {
  background: #0e0e1c !important; color: #3a3a52 !important;
  border: 1px solid #1e1e30 !important;
}
[data-testid="stButton"] > button:not([kind="primary"]):hover {
  border-color: #00e6a0 !important; color: #00e6a0 !important;
  background: rgba(0,230,160,.04) !important;
}

/* Hide tab-switcher utility buttons */
.nse-sw-hidden {
  display:none !important; height:0 !important;
  overflow:hidden !important; margin:0 !important; padding:0 !important;
}

/* Misc UI */
.nse-section {
  font-family: 'JetBrains Mono', monospace;
  font-size: 8px; letter-spacing: 3px; text-transform: uppercase;
  color: #252536; margin: 6px 0 14px;
}
.nse-hint {
  background: rgba(0,230,160,.025); border: 1px solid rgba(0,230,160,.08);
  border-radius: 9px; padding: 9px 13px;
  font-size: 11px; color: #44445a; line-height: 1.65; margin: 8px 0;
}
.nse-hint-warn { background: rgba(245,166,35,.04); border-color: rgba(245,166,35,.2); color: #b07010; }
.nse-hint-info { background: rgba(76,142,255,.04); border-color: rgba(76,142,255,.2); }

/* OTP step card */
.otp-step {
  background: rgba(0,230,160,.03);
  border: 1px solid rgba(0,230,160,.12);
  border-radius: 12px; padding: 20px 20px 16px;
  margin: 4px 0 12px; text-align: center;
}
.otp-step-icon { font-size: 32px; margin-bottom: 8px; }
.otp-step-title {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; letter-spacing: 2px; text-transform: uppercase;
  color: #00e6a0; margin-bottom: 4px;
}
.otp-step-sub { font-size: 12px; color: #44445a; line-height: 1.5; }
.otp-email-highlight {
  font-family: 'JetBrains Mono', monospace;
  color: #00e6a0; font-weight: 600;
}

/* Local mode OTP banner */
.otp-local-banner {
  background: rgba(245,166,35,.06); border: 1px solid rgba(245,166,35,.25);
  border-radius: 10px; padding: 14px 16px; margin: 10px 0; text-align:center;
}
.otp-local-code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 32px; font-weight: 700; letter-spacing: 8px;
  color: #f5a623; margin: 8px 0;
}
.otp-local-label { font-size: 10px; color: #8a6020; letter-spacing: 1px; text-transform: uppercase; }

/* Username chips */
.nse-chips { background:#08080f; border:1px solid #1a1a2a; border-radius:10px; padding:12px 14px; margin-top:8px; }
.nse-chips-lbl { font-family:'JetBrains Mono',monospace; font-size:8px; letter-spacing:2px; color:#3a3a52; text-transform:uppercase; margin-bottom:8px; }
.nse-chip-item { display:inline-block; background:#0e0e1c; border:1px solid rgba(0,230,160,.2); border-radius:6px; padding:4px 10px; margin:3px; font-family:'JetBrains Mono',monospace; font-size:11px; color:#00e6a0; }

.nse-footer { text-align:center; margin-top:20px; font-size:10px; color:#18182a; }

/* Mobile stacking */
@media (max-width:440px) {
  [data-testid="stHorizontalBlock"] { flex-direction:column !important; }
  [data-testid="stHorizontalBlock"] > div { width:100% !important; min-width:100% !important; }
}
</style>
"""


# ── Shell HTML (via components.v1.html — bypasses Streamlit sanitizer) ─────────
def _shell_html(cur_tab: str, sb_mode: bool) -> str:
    tabs = [("signin", "Sign In"), ("register", "Register")]
    tab_btns = "".join(
        f'<button class="tab {"active" if k == cur_tab else ""}" data-tab="{k}">{lbl}</button>'
        for k, lbl in tabs
    )
    badge_cls = "cloud" if sb_mode else "local"
    badge_txt = "Supabase Cloud" if sb_mode else "Local Mode"
    return f"""<!DOCTYPE html><html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{background:transparent;overflow:hidden;height:100%;}}
canvas{{position:fixed;inset:0;pointer-events:none;z-index:0;}}
.shell{{
  position:relative;z-index:1;width:100%;
  background:rgba(9,9,18,.97);
  border-radius:20px 20px 0 0;
  border:1px solid rgba(255,255,255,.07);border-bottom:none;
  overflow:hidden;animation:up .45s cubic-bezier(.16,1,.3,1) both;
}}
@keyframes up{{from{{opacity:0;transform:translateY(20px)}}to{{opacity:1;transform:translateY(0)}}}}
.stripe{{height:2px;background:linear-gradient(90deg,transparent,#00e6a0 20%,#4c8eff 40%,#00e6a0 60%,#7b4fff 80%,transparent);background-size:400% 100%;animation:flow 5s linear infinite;}}
@keyframes flow{{0%{{background-position:100% 0}}100%{{background-position:-100% 0}}}}
.body{{padding:28px 28px 20px;}}
@media(max-width:400px){{.body{{padding:20px 16px 16px;}}}}
.ey{{font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:5px;text-transform:uppercase;color:#00e6a0;opacity:.7;text-align:center;margin-bottom:8px;}}
.brand{{font-family:'Space Grotesk',sans-serif;font-size:clamp(20px,5.5vw,28px);font-weight:700;color:#fff;letter-spacing:-.5px;line-height:1.1;text-align:center;}}
.brand em{{color:#00e6a0;font-style:normal;}}
.sub{{font-size:12px;color:#44445a;margin-top:5px;text-align:center;}}
.chip{{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;border-radius:100px;margin-top:10px;font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;}}
.cloud{{background:rgba(0,230,160,.07);border:1px solid rgba(0,230,160,.22);color:#00e6a0;}}
.local{{background:rgba(245,166,35,.07);border:1px solid rgba(245,166,35,.22);color:#f5a623;}}
.dot{{width:5px;height:5px;border-radius:50%;animation:blink 2s ease infinite;}}
.cloud .dot{{background:#00e6a0;}}.local .dot{{background:#f5a623;}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
.logo{{text-align:center;margin-bottom:22px;}}
.tabs{{display:grid;grid-template-columns:1fr 1fr;gap:3px;padding:3px;background:#0c0c14;border:1px solid rgba(255,255,255,.05);border-radius:12px;}}
.tab{{padding:11px 4px;text-align:center;cursor:pointer;border:none;border-radius:9px;background:transparent;font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:500;letter-spacing:1px;text-transform:uppercase;color:#2e2e44;transition:all .18s ease;}}
.tab:hover{{color:#00e6a0;background:rgba(0,230,160,.05);}}
.tab.active{{background:linear-gradient(135deg,#00e6a0,#009e70);color:#050508;font-weight:700;box-shadow:0 2px 14px rgba(0,230,160,.28);}}
</style>
</head><body>
<canvas id="c"></canvas>
<div class="shell">
  <div class="stripe"></div>
  <div class="body">
    <div class="logo">
      <div class="ey">Quantitative &middot; Analytics</div>
      <div class="brand">NSE <em>Market</em> Analyzer</div>
      <div class="sub">ML-powered &middot; 500 stocks &middot; 5yr history</div>
      <div><span class="chip {badge_cls}"><span class="dot"></span>{badge_txt}</span></div>
    </div>
    <div class="tabs">{tab_btns}</div>
  </div>
</div>
<script>
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
  /* Wire tab clicks to hidden Streamlit buttons in parent */
  document.querySelectorAll('.tab').forEach(function(btn){{
    btn.addEventListener('click',function(){{
      var tab=btn.getAttribute('data-tab');
      try{{
        window.parent.document.querySelectorAll('[data-testid="stButton"] button').forEach(function(b){{
          if(b.innerText.trim()===tab) b.click();
        }});
      }}catch(e){{}}
    }});
  }});
}})();
</script>
</body></html>"""


# ── Init ──────────────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "logged_in":   False,
        "username":    "",
        "user_info":   {},
        "auth_tab":    "signin",   # signin | register
        # OTP flow state (shared across both tabs)
        "otp_email":   "",         # email waiting for OTP
        "otp_step":    "email",    # email | verify
        "otp_local":   "",         # local mode: code shown on screen
        "otp_context": "",         # "signin" | "register"
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── Hidden tab-switcher buttons (iframe JS clicks these) ──────────────────────
def _switchers():
    c1, c2 = st.columns(2)
    with c1:
        if st.button("signin",   key="_sw_signin"):
            st.session_state.update({"auth_tab": "signin",   "otp_step": "email"}); st.rerun()
    with c2:
        if st.button("register", key="_sw_register"):
            st.session_state.update({"auth_tab": "register", "otp_step": "email"}); st.rerun()
    st.markdown("""<script>
(function(){
  function hide(){
    document.querySelectorAll('[data-testid="stButton"] button').forEach(function(b){
      var t=b.innerText.trim();
      if(t==='signin'||t==='register'){
        var w=b.closest('[data-testid="stButton"]');
        if(w) w.style.cssText='display:none!important;height:0;overflow:hidden;margin:0;padding:0';
      }
    });
  }
  hide(); setTimeout(hide,150); setTimeout(hide,500);
})();
</script>""", unsafe_allow_html=True)


# ── OTP verify panel (shared between sign-in and register) ───────────────────
def _render_otp_verify(sb_mode: bool):
    email   = st.session_state["otp_email"]
    context = st.session_state["otp_context"]
    local_code = st.session_state.get("otp_local", "")

    # Step card
    st.markdown(f"""
    <div class="otp-step">
      <div class="otp-step-icon">📨</div>
      <div class="otp-step-title">Check your email</div>
      <div class="otp-step-sub">
        We sent a 6-digit code to<br>
        <span class="otp-email-highlight">{email}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    # Local mode: show OTP on screen
    if local_code:
        st.markdown(f"""
        <div class="otp-local-banner">
          <div class="otp-local-label">⚡ Local mode — your code</div>
          <div class="otp-local-code">{local_code}</div>
          <div style="font-size:10px;color:#8a6020">No email server — use this code above</div>
        </div>""", unsafe_allow_html=True)

    code = st.text_input(
        "Enter 6-digit code",
        placeholder="• • • • • •",
        max_chars=6,
        key="otp_code_input",
    )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if st.button("✓  Verify Code", type="primary", use_container_width=True, key="otp_verify_btn"):
        if not code or len(code) != 6 or not code.isdigit():
            st.error("⚠ Enter the 6-digit number from your email.")
        else:
            with st.spinner("Verifying…"):
                ok, msg, user_info = verify_otp(email, code)
            if ok:
                st.session_state.update({
                    "logged_in":  True,
                    "username":   user_info["username"],
                    "user_info":  user_info,
                    "otp_step":   "email",
                    "otp_email":  "",
                    "otp_local":  "",
                })
                with st.spinner("Loading portfolio…"):
                    st.session_state["portfolio"] = load_user_portfolio(user_info)
                st.rerun()
            else:
                st.error(f"⚠ {msg}")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    col_resend, col_back = st.columns(2)
    with col_resend:
        if st.button("↺  Resend Code", use_container_width=True, key="otp_resend"):
            with st.spinner("Sending…"):
                ok, result = send_otp(email)
            if ok:
                # Parse local code if present
                parts = result.split(":")
                local = parts[3] if len(parts) >= 4 and parts[2] == "LOCAL" else ""
                st.session_state["otp_local"] = local
                st.success("New code sent!")
                st.rerun()
            else:
                st.error(f"⚠ {result}")
    with col_back:
        if st.button("← Go Back", use_container_width=True, key="otp_back"):
            st.session_state.update({"otp_step": "email", "otp_email": "", "otp_local": ""})
            st.rerun()


# ── Sign In panel ─────────────────────────────────────────────────────────────
def _render_signin(sb_mode: bool):
    if st.session_state["otp_step"] == "verify":
        _render_otp_verify(sb_mode)
        return

    st.markdown('<div class="nse-section">── Sign in with your email</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="nse-hint">Enter your registered email — we\'ll send a one-time code. No password needed.</div>',
        unsafe_allow_html=True,
    )

    email = st.text_input("Email Address", placeholder="you@example.com", key="si_email")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    if st.button("Send One-Time Code →", type="primary", use_container_width=True, key="si_send"):
        if not email or "@" not in email:
            st.error("⚠ Enter a valid email address.")
        else:
            with st.spinner("Sending code…"):
                ok, result = send_otp(email.strip().lower())
            if ok:
                parts = result.split(":")
                local = parts[3] if len(parts) >= 4 and parts[2] == "LOCAL" else ""
                st.session_state.update({
                    "otp_step":    "verify",
                    "otp_email":   email.strip().lower(),
                    "otp_local":   local,
                    "otp_context": "signin",
                })
                st.rerun()
            else:
                st.error(f"⚠ {result}")


# ── Register panel ────────────────────────────────────────────────────────────
def _render_register(sb_mode: bool):
    if st.session_state["otp_step"] == "verify" and st.session_state["otp_context"] == "register":
        _render_otp_verify(sb_mode)
        return

    st.markdown('<div class="nse-section">── Create a new account</div>', unsafe_allow_html=True)

    ca, cb = st.columns(2)
    with ca: name  = st.text_input("Full Name",  placeholder="Rahul Sharma",  key="rg_name")
    with cb: uname = st.text_input("Username",   placeholder="rahul_trades",  key="rg_user")
    email = st.text_input("Email Address", placeholder="rahul@example.com",   key="rg_email")

    st.markdown(
        f'<div class="nse-hint">{"☁ Stored securely in Supabase." if sb_mode else "⚡ Local mode."}'
        f' Username: 3–20 chars, letters/numbers/underscore.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    if st.button("Create Account & Send Code →", type="primary", use_container_width=True, key="rg_btn"):
        if not all([name, uname, email]):
            st.error("⚠ Fill in all fields.")
        else:
            with st.spinner("Creating account…"):
                ok, result = register(uname, name, email)
            if ok:
                # result = "OTP_SENT:<email>" or "OTP_SENT:<email>:LOCAL:<code>"
                parts     = result.split(":")
                reg_email = parts[1] if len(parts) >= 2 else email.strip().lower()
                local     = parts[3] if len(parts) >= 4 and parts[2] == "LOCAL" else ""
                st.session_state.update({
                    "otp_step":    "verify",
                    "otp_email":   reg_email,
                    "otp_local":   local,
                    "otp_context": "register",
                })
                st.rerun()
            else:
                if result.startswith("USERNAME_TAKEN:"):
                    sugg = [s for s in result.split(":", 1)[1].split(",") if s]
                    st.error(f"⚠ @{uname} is already taken.")
                    if sugg:
                        chips = "".join(f'<span class="nse-chip-item">@{s}</span>' for s in sugg)
                        st.markdown(
                            f'<div class="nse-chips"><div class="nse-chips-lbl">Available</div>{chips}</div>',
                            unsafe_allow_html=True,
                        )
                elif result.startswith("EMAIL_EXISTS:"):
                    st.error("⚠ Email already registered — use Sign In instead.")
                else:
                    st.error(f"⚠ {result}")


# ── Public entry point ────────────────────────────────────────────────────────
def render_auth_page() -> bool:
    _init()
    if st.session_state.get("logged_in"):
        return True

    sb_mode = is_supabase_mode()
    cur_tab = st.session_state["auth_tab"]

    # 1. Global CSS
    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)

    # 2. Decorative shell (logo + tabs) via iframe — bypasses Streamlit sanitizer
    shell_height = 265
    components.html(_shell_html(cur_tab, sb_mode), height=shell_height, scrolling=False)

    # 3. Hidden tab-switcher buttons (iframe JS clicks by text match)
    _switchers()

    # 4. Active panel
    if cur_tab == "signin":
        _render_signin(sb_mode)
    else:
        _render_register(sb_mode)

    # 5. Footer
    st.markdown(
        '<div class="nse-footer">⚠ Not financial advice &middot; Educational use only</div>',
        unsafe_allow_html=True,
    )
    return False
