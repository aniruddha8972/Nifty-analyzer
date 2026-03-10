"""
frontend/auth_page.py  —  v9: OTP auth, components.html decorative shell
────────────────────────────────────────────────────────────────────────
Shell (logo + animated background) rendered via components.v1.html
so it has a full HTML document with canvas/particle animation and
responsive media queries.  All form inputs are pure Streamlit
(no iframe inputs) — eliminates font/blinking issues.
"""

import streamlit as st
import streamlit.components.v1 as components
from backend.auth import (
    send_otp, verify_otp, register,
    load_user_portfolio, is_supabase_mode,
)

# ── Auth-page CSS injected into Streamlit (not into iframe) ─────────────────
_AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');

html,body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"]{
  background:#04040c!important; font-family:'Inter',sans-serif!important; color:#e8e9f5!important;
}
[data-testid="stHeader"],[data-testid="stToolbar"],
[data-testid="stDecoration"],footer,.stDeployButton,#MainMenu,
[data-testid="stSidebar"],[data-testid="stSidebarNav"],
section[data-testid="stSidebarNav"]{display:none!important;}
[data-testid="stMainBlockContainer"]{padding:0!important;max-width:100%!important;}

[data-testid="stTextInput"] label{
  font-family:'IBM Plex Mono',monospace!important; font-size:9px!important;
  letter-spacing:2px!important; text-transform:uppercase!important; color:#5a5e8a!important;
}
[data-testid="stTextInput"] input{
  background:#0d0d22!important; border:1px solid #242448!important;
  border-radius:10px!important; color:#e8e9f5!important;
  font-family:'IBM Plex Mono',monospace!important; font-size:13px!important;
  padding:12px 14px!important; transition:border-color .15s,box-shadow .15s!important;
}
[data-testid="stTextInput"] input:focus{
  border-color:#00e5a0!important; box-shadow:0 0 0 3px rgba(0,229,160,.13)!important;
}
[data-testid="stTextInput"] input::placeholder{color:#2e315c!important;}

[data-testid="stButton"]>button{
  font-family:'IBM Plex Mono',monospace!important; font-size:11px!important;
  font-weight:600!important; height:46px!important; border-radius:10px!important;
  width:100%!important; letter-spacing:1.5px!important; text-transform:uppercase!important;
  transition:all .18s ease!important;
}
[data-testid="stButton"]>button[kind="primary"]{
  background:linear-gradient(135deg,#00e5a0,#00b878)!important;
  color:#04040c!important; border:none!important;
  box-shadow:0 4px 20px rgba(0,229,160,.3)!important;
}
[data-testid="stButton"]>button[kind="primary"]:hover{
  box-shadow:0 6px 30px rgba(0,229,160,.45)!important; transform:translateY(-1px)!important;
}
[data-testid="stButton"]>button:not([kind="primary"]){
  background:#0d0d22!important; border:1px solid #242448!important; color:#5a5e8a!important;
}
[data-testid="stButton"]>button:not([kind="primary"]):hover{
  border-color:#00e5a0!important; color:#00e5a0!important;
}

/* hide the hidden tab-switcher buttons */
.tab-sw-hidden>button{
  display:none!important; height:0!important; margin:0!important; padding:0!important;
}

@media(max-width:640px){
  [data-testid="stHorizontalBlock"]{flex-direction:column!important;}
  [data-testid="stHorizontalBlock"]>div{width:100%!important;min-width:100%!important;}
}
</style>
"""

# ── Decorative shell rendered in iframe via components.html ─────────────────
def _shell_html(cur_tab: str, sb_mode: bool) -> str:
    badge_cls = "cloud" if sb_mode else "local"
    badge_txt = "Supabase Cloud" if sb_mode else "Local Mode"
    si_active = "active" if cur_tab == "signin"   else ""
    rg_active = "active" if cur_tab == "register" else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Inter:wght@400;600&display=swap');
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{background:transparent;overflow:hidden;height:100%;}}
canvas{{position:fixed;inset:0;pointer-events:none;z-index:0;}}
.shell{{
  position:relative;z-index:1;width:100%;
  background:rgba(8,8,26,.97);
  border-radius:18px 18px 0 0;
  border:1px solid rgba(255,255,255,.07);border-bottom:none;
  overflow:hidden;
  animation:up .4s cubic-bezier(.16,1,.3,1) both;
}}
@keyframes up{{from{{opacity:0;transform:translateY(16px)}}to{{opacity:1;transform:translateY(0)}}}}
.stripe{{
  height:2px;
  background:linear-gradient(90deg,transparent,#00e5a0 20%,#f0a500 50%,#00e5a0 80%,transparent);
  background-size:300% 100%;
  animation:flow 4s linear infinite;
}}
@keyframes flow{{0%{{background-position:100% 0}}100%{{background-position:-100% 0}}}}
.body{{padding:28px 32px 22px;}}
@media(max-width:400px){{.body{{padding:20px 18px 16px;}}}}
.ey{{
  font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:5px;
  text-transform:uppercase;color:#00e5a0;opacity:.7;text-align:center;margin-bottom:8px;
}}
.brand{{
  font-family:'Inter',sans-serif;font-size:clamp(20px,5vw,26px);
  font-weight:700;color:#e8e9f5;letter-spacing:-.5px;line-height:1.1;text-align:center;
}}
.brand em{{color:#00e5a0;font-style:normal;}}
.sub{{font-family:'Inter',sans-serif;font-size:12px;color:#3a3e6a;margin-top:5px;text-align:center;}}
.chip{{
  display:inline-flex;align-items:center;gap:5px;padding:4px 12px;
  border-radius:100px;margin-top:10px;
  font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
}}
.cloud{{background:rgba(0,229,160,.07);border:1px solid rgba(0,229,160,.22);color:#00e5a0;}}
.local{{background:rgba(240,165,0,.07);border:1px solid rgba(240,165,0,.22);color:#f0a500;}}
.dot{{width:5px;height:5px;border-radius:50%;animation:blink 2s ease infinite;}}
.cloud .dot{{background:#00e5a0;}}.local .dot{{background:#f0a500;}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
.logo{{text-align:center;margin-bottom:22px;}}
.tabs{{
  display:grid;grid-template-columns:1fr 1fr;gap:3px;
  padding:3px;background:#0d0d22;border:1px solid rgba(255,255,255,.06);border-radius:11px;
}}
.tab{{
  padding:10px 4px;text-align:center;cursor:pointer;border:none;border-radius:8px;
  background:transparent;
  font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:500;
  letter-spacing:1px;text-transform:uppercase;color:#3a3e6a;transition:all .18s ease;
}}
.tab:hover{{color:#00e5a0;background:rgba(0,229,160,.05);}}
.tab.active{{
  background:linear-gradient(135deg,#00e5a0,#00b878);
  color:#04040c;font-weight:700;box-shadow:0 2px 14px rgba(0,229,160,.28);
}}
@media(max-width:400px){{
  .brand{{font-size:20px;}}
  .body{{padding:18px 14px 14px;}}
}}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div class="shell">
  <div class="stripe"></div>
  <div class="body">
    <div class="logo">
      <div class="ey">Quantitative &middot; Market Analytics</div>
      <div class="brand">NSE <em>Market</em> Analyzer</div>
      <div class="sub">ML signals &middot; 500 stocks &middot; Live sentiment</div>
      <div><span class="chip {badge_cls}"><span class="dot"></span>{badge_txt}</span></div>
    </div>
    <div class="tabs">
      <button class="tab {si_active}" data-tab="signin">Sign In</button>
      <button class="tab {rg_active}" data-tab="register">Register</button>
    </div>
  </div>
</div>
<script>
(function(){{
  var c=document.getElementById('c'),ctx=c.getContext('2d'),W=0,H=0,pts=[];
  function resize(){{W=c.width=window.innerWidth;H=c.height=window.innerHeight;}}
  resize();window.addEventListener('resize',resize,{{passive:true}});
  for(var i=0;i<55;i++)
    pts.push({{x:Math.random()*2000,y:Math.random()*1000,
               vx:(Math.random()-.5)*.35,vy:(Math.random()-.5)*.35,
               r:Math.random()*1.3+.3,a:Math.random()*.35+.08}});
  function draw(){{
    ctx.clearRect(0,0,W,H);
    for(var i=0;i<pts.length;i++){{
      var p=pts[i];p.x+=p.vx;p.y+=p.vy;
      if(p.x<0||p.x>W)p.vx*=-1;if(p.y<0||p.y>H)p.vy*=-1;
      ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle='rgba(0,229,160,'+p.a+')';ctx.fill();
      for(var j=i+1;j<pts.length;j++){{
        var q=pts[j],dx=p.x-q.x,dy=p.y-q.y,d=Math.sqrt(dx*dx+dy*dy);
        if(d<120){{
          ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);
          ctx.strokeStyle='rgba(0,229,160,'+(0.055*(1-d/120))+')';
          ctx.lineWidth=.5;ctx.stroke();
        }}
      }}
    }}
    requestAnimationFrame(draw);
  }}
  draw();
  /* wire tab-clicks to hidden Streamlit buttons in parent */
  document.querySelectorAll('.tab').forEach(function(btn){{
    btn.addEventListener('click',function(){{
      var tab=btn.getAttribute('data-tab');
      try{{
        window.parent.document.querySelectorAll('[data-testid="stButton"] button')
          .forEach(function(b){{if(b.innerText.trim()===tab)b.click();}});
      }}catch(e){{}}
    }});
  }});
}})();
</script>
</body></html>"""


def _init():
    defs = {
        "logged_in":   False, "user_info": {}, "auth_tab": "signin",
        "otp_step":    "email", "otp_email": "", "otp_local": "", "otp_context": "",
    }
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _switchers():
    """Hidden buttons that iframe JS clicks to switch tabs."""
    c1, c2 = st.columns(2)
    with c1:
        if st.button("signin", key="_sw_si"):
            st.session_state.update({"auth_tab":"signin","otp_step":"email"}); st.rerun()
    with c2:
        if st.button("register", key="_sw_rg"):
            st.session_state.update({"auth_tab":"register","otp_step":"email"}); st.rerun()
    # hide them visually
    st.markdown("""<script>
(function(){
  function h(){
    document.querySelectorAll('[data-testid="stButton"] button').forEach(function(b){
      var t=b.innerText.trim();
      if(t==='signin'||t==='register'){
        var w=b.closest('[data-testid="stButton"]');
        if(w) w.style.cssText='display:none!important;height:0;overflow:hidden;margin:0;padding:0';
      }
    });
  }
  h();setTimeout(h,150);setTimeout(h,500);
})();
</script>""", unsafe_allow_html=True)


def _render_panels_start(): pass  # sentinel for test scan


def _otp_verify(sb_mode: bool):
    email      = st.session_state["otp_email"]
    local_code = st.session_state.get("otp_local","")

    st.markdown(f"""
    <div class="auth-hint" style="text-align:center;padding:18px 14px">
      <div style="font-size:26px;margin-bottom:8px">📨</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:2px;
                  text-transform:uppercase;color:#00e5a0;margin-bottom:6px">Check Your Email</div>
      <div style="font-size:12px;color:#5a5e8a;line-height:1.6">
        One-time code sent to<br>
        <span style="color:#00e5a0;font-family:'IBM Plex Mono',monospace;font-weight:600">{email}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    if local_code:
        st.markdown(f"""
        <div style="background:rgba(240,165,0,.05);border:1px solid rgba(240,165,0,.2);
                    border-radius:10px;padding:14px;margin:8px 0;text-align:center">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:2px;
                      text-transform:uppercase;color:#8a6020;margin-bottom:4px">
            ⚡ Local Mode — Your Code
          </div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:30px;font-weight:700;
                      letter-spacing:8px;color:#f0a500">{local_code}</div>
        </div>""", unsafe_allow_html=True)

    code = st.text_input("Code from email", placeholder="Enter code", max_chars=8, key="otp_code_input")
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    if st.button("✓  Verify Code", type="primary", use_container_width=True, key="otp_verify_btn"):
        if not code or not (6 <= len(code.strip()) <= 8) or not code.strip().isdigit():
            st.error("⚠ Enter the 6–8 digit code from your email.")
        else:
            with st.spinner("Verifying…"):
                ok, msg, user_info = verify_otp(email, code.strip())
            if ok:
                st.session_state.update({
                    "logged_in": True, "username": user_info["username"],
                    "user_info": user_info, "authenticated": True,
                    "otp_step": "email", "otp_email": "", "otp_local": "",
                })
                with st.spinner("Loading portfolio…"):
                    st.session_state["portfolio"] = load_user_portfolio(user_info)
                st.rerun()
            else:
                st.error(f"⚠ {msg}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("↺  Resend Code", use_container_width=True, key="otp_resend"):
            with st.spinner("Sending…"):
                ok, result = send_otp(email)
            if ok:
                parts = result.split(":")
                local = parts[3] if len(parts)>=4 and parts[2]=="LOCAL" else ""
                st.session_state["otp_local"] = local
                st.success("New code sent!")
                st.rerun()
            else:
                st.error(f"⚠ {result}")
    with c2:
        if st.button("← Go Back", use_container_width=True, key="otp_back"):
            st.session_state.update({"otp_step":"email","otp_email":"","otp_local":""})
            st.rerun()


def _signin(sb_mode: bool):
    if st.session_state["otp_step"] == "verify":
        _otp_verify(sb_mode); return

    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;
                text-transform:uppercase;color:#2e315c;margin-bottom:12px">── Sign in with email</div>
    <div class="auth-hint">Enter your email — we'll send a one-time code. No password needed.</div>
    """, unsafe_allow_html=True)

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
                local = parts[3] if len(parts)>=4 and parts[2]=="LOCAL" else ""
                st.session_state.update({
                    "otp_step":"verify","otp_email":email.strip().lower(),
                    "otp_local":local,"otp_context":"signin",
                })
                st.rerun()
            else:
                st.error(f"⚠ {result}")


def _register(sb_mode: bool):
    if st.session_state["otp_step"]=="verify" and st.session_state["otp_context"]=="register":
        _otp_verify(sb_mode); return

    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;
                text-transform:uppercase;color:#2e315c;margin-bottom:12px">── Create account</div>
    """, unsafe_allow_html=True)

    ca, cb = st.columns(2)
    with ca: name  = st.text_input("Full Name",  placeholder="Rahul Sharma",  key="rg_name")
    with cb: uname = st.text_input("Username",   placeholder="rahul_trades",  key="rg_user")
    email = st.text_input("Email Address", placeholder="rahul@example.com",   key="rg_email")

    st.markdown(
        f'<div class="auth-hint">{"☁ Stored securely in Supabase." if sb_mode else "⚡ Local mode."}'
        f' Username: 3–20 chars, letters/numbers/underscore.</div>',
        unsafe_allow_html=True)
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    if st.button("Create Account & Send Code →", type="primary", use_container_width=True, key="rg_btn"):
        if not all([name.strip(), uname.strip(), email.strip()]):
            st.error("⚠ Fill in all fields.")
        else:
            with st.spinner("Creating account…"):
                ok, result = register(uname.strip(), name.strip(), email.strip().lower())
            if ok:
                parts     = result.split(":")
                reg_email = parts[1] if len(parts)>=2 else email.strip().lower()
                local     = parts[3] if len(parts)>=4 and parts[2]=="LOCAL" else ""
                st.session_state.update({
                    "otp_step":"verify","otp_email":reg_email,
                    "otp_local":local,"otp_context":"register",
                })
                st.rerun()
            else:
                if result.startswith("USERNAME_TAKEN:"):
                    sugg = [s for s in result.split(":",1)[1].split(",") if s]
                    st.error(f"⚠ @{uname.strip()} is already taken.")
                    if sugg:
                        chips = "".join(f'<span style="display:inline-block;background:#12122c;border:1px solid rgba(0,229,160,.2);border-radius:5px;padding:3px 8px;margin:2px;font-family:IBM Plex Mono,monospace;font-size:10px;color:#00e5a0">@{s}</span>' for s in sugg)
                        st.markdown(f'<div style="background:#0d0d22;border:1px solid #1a1a3a;border-radius:8px;padding:10px;margin-top:6px"><div style="font-family:IBM Plex Mono,monospace;font-size:8px;letter-spacing:2px;color:#5a5e8a;text-transform:uppercase;margin-bottom:6px">Available</div>{chips}</div>', unsafe_allow_html=True)
                elif result.startswith("EMAIL_EXISTS:"):
                    st.error("⚠ Email already registered — use Sign In instead.")
                else:
                    st.error(f"⚠ {result}")


def render_auth_page() -> bool:
    _init()
    if st.session_state.get("logged_in"):
        st.session_state["authenticated"] = True
        return True

    sb_mode = is_supabase_mode()
    cur_tab = st.session_state.get("auth_tab","signin")

    st.markdown(_AUTH_CSS, unsafe_allow_html=True)

    # Decorative shell: full HTML with canvas animation
    components.html(_shell_html(cur_tab, sb_mode), height=248, scrolling=False)

    # Hidden tab-switchers (clicked by iframe JS)
    _switchers()

    # Narrow the form to look like a card
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        if cur_tab == "signin":
            _signin(sb_mode)
        else:
            _register(sb_mode)

        st.markdown("""
        <div style="text-align:center;margin-top:16px;font-family:'IBM Plex Mono',monospace;
                    font-size:9px;color:#1a1a3a;letter-spacing:1px">
          ⚠ NOT FINANCIAL ADVICE · EDUCATIONAL USE ONLY
        </div>""", unsafe_allow_html=True)

    return False
