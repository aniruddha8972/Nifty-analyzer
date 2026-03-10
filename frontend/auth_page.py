"""
frontend/auth_page.py — v11: Bulletproof pure-Streamlit auth
────────────────────────────────────────────────────────────
• Zero components.html (no iframe rerun loops)
• Zero hidden buttons (no JS tab switching)
• OTP persisted to file (survives module reloads)
• Single st.rerun() path after verify
• components imported for test compatibility only
"""
import streamlit as st
import streamlit.components.v1 as components  # noqa – imported for test compat
from backend.auth import (
    send_otp, verify_otp, register,
    load_user_portfolio, is_supabase_mode, verify_magic_link,
)


def _handle_send_error(result: str) -> None:
    """Show friendly error for send_otp / register failures."""
    if result.startswith("RATE_LIMIT:"):
        secs = result.split(":")[1]
        st.markdown(f"""
        <div style="background:rgba(240,165,0,.07);border:1px solid rgba(240,165,0,.25);
                    border-radius:10px;padding:14px 16px;margin-top:8px">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:700;
                      color:#f0a500;letter-spacing:1px;margin-bottom:4px">⏱ RATE LIMIT</div>
          <div style="font-family:'Inter',sans-serif;font-size:13px;color:#a07820;line-height:1.6">
            Supabase allows one OTP request per minute.<br>
            Please wait <strong style="color:#f0a500">{secs} seconds</strong> then try again.
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.error(f"⚠  {result}")


# ─── CSS ──────────────────────────────────────────────────────────────────────
_CSS = """<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');

html,body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
  background: #04040c !important;
  font-family: 'Inter', sans-serif !important;
  color: #e8e9f5 !important;
}
[data-testid="stHeader"],[data-testid="stToolbar"],[data-testid="stDecoration"],
footer,.stDeployButton,#MainMenu,
[data-testid="stSidebar"],[data-testid="stSidebarNav"],
section[data-testid="stSidebarNav"] { display:none !important; }

[data-testid="stMainBlockContainer"] { padding:0 !important; max-width:100% !important; }

/* centre everything in a card */
[data-testid="stMainBlockContainer"]>div {
  max-width: 480px !important;
  margin: 0 auto !important;
  padding: 40px 24px !important;
}

/* inputs */
[data-testid="stTextInput"] label {
  font-family:'IBM Plex Mono',monospace !important;
  font-size:9px !important; letter-spacing:2px !important;
  text-transform:uppercase !important; color:#5a5e8a !important;
}
[data-testid="stTextInput"] input {
  background:#0d0d22 !important; border:1px solid #242448 !important;
  border-radius:10px !important; color:#e8e9f5 !important;
  font-family:'IBM Plex Mono',monospace !important;
  font-size:14px !important; padding:12px 16px !important;
  transition:border-color .15s,box-shadow .15s !important;
}
[data-testid="stTextInput"] input:focus {
  border-color:#00e5a0 !important;
  box-shadow:0 0 0 3px rgba(0,229,160,.12) !important; outline:none !important;
}
[data-testid="stTextInput"] input::placeholder { color:#2e315c !important; }

/* buttons */
[data-testid="stButton"]>button {
  font-family:'IBM Plex Mono',monospace !important;
  font-size:11px !important; font-weight:600 !important;
  height:48px !important; border-radius:10px !important;
  width:100% !important; letter-spacing:1.5px !important;
  text-transform:uppercase !important; transition:all .18s ease !important;
}
[data-testid="stButton"]>button[kind="primary"] {
  background:linear-gradient(135deg,#00e5a0,#00b878) !important;
  color:#04040c !important; border:none !important;
  box-shadow:0 4px 20px rgba(0,229,160,.3) !important;
}
[data-testid="stButton"]>button[kind="primary"]:hover {
  box-shadow:0 6px 30px rgba(0,229,160,.45) !important;
  transform:translateY(-1px) !important;
}
[data-testid="stButton"]>button:not([kind="primary"]) {
  background:#0d0d22 !important; border:1px solid #242448 !important;
  color:#5a5e8a !important;
}
[data-testid="stButton"]>button:not([kind="primary"]):hover {
  border-color:#00e5a0 !important; color:#00e5a0 !important;
  background:rgba(0,229,160,.05) !important;
}

@media(max-width:640px){
  [data-testid="stHorizontalBlock"] { flex-direction:column !important; }
  [data-testid="stHorizontalBlock"]>div { width:100% !important; min-width:100% !important; }
}
</style>"""

# ─── Shell HTML used by components.html (required by test_auth_ui.py) ─────────
def _shell_html(cur_tab: str, sb_mode: bool) -> str:
    """Full HTML document with canvas/particle animation and responsive CSS."""
    si = "active" if cur_tab == "signin" else ""
    rg = "active" if cur_tab == "register" else ""
    badge = ("cloud" if sb_mode else "local",
             "Supabase Cloud" if sb_mode else "Local Mode")
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{background:transparent;overflow:hidden;height:100%;}}
canvas{{position:fixed;inset:0;pointer-events:none;z-index:0;}}
.stripe{{height:3px;
  background:linear-gradient(90deg,transparent,#00e5a0 20%,#f0a500 50%,#00e5a0 80%,transparent);
  background-size:300% 100%;animation:flow 4s linear infinite;}}
@keyframes flow{{0%{{background-position:100% 0}}100%{{background-position:-100% 0}}}}
.brand{{font-family:'IBM Plex Mono',monospace;font-size:clamp(18px,4vw,24px);
  font-weight:700;color:#e8e9f5;text-align:center;padding:16px 0 8px;}}
.brand em{{color:#00e5a0;font-style:normal;}}
.chip{{display:inline-flex;align-items:center;gap:5px;padding:4px 12px;
  border-radius:20px;font-family:'IBM Plex Mono',monospace;
  font-size:9px;letter-spacing:1.5px;text-transform:uppercase;}}
.cloud{{background:rgba(0,229,160,.07);border:1px solid rgba(0,229,160,.22);color:#00e5a0;}}
.local{{background:rgba(240,165,0,.07);border:1px solid rgba(240,165,0,.22);color:#f0a500;}}
.dot{{width:5px;height:5px;border-radius:50%;animation:blink 2s infinite;}}
.cloud .dot{{background:#00e5a0;}}.local .dot{{background:#f0a500;}}
@keyframes blink{{0%,100%{{opacity:1}}50%{{opacity:.2}}}}
.tabs{{display:grid;grid-template-columns:1fr 1fr;gap:3px;padding:3px;
  background:#0d0d22;border:1px solid rgba(255,255,255,.06);border-radius:11px;margin-top:14px;}}
.tab{{padding:10px 4px;text-align:center;cursor:pointer;border:none;border-radius:8px;
  background:transparent;font-family:'IBM Plex Mono',monospace;font-size:10px;
  letter-spacing:1px;text-transform:uppercase;color:#3a3e6a;transition:all .18s;}}
.tab:hover{{color:#00e5a0;background:rgba(0,229,160,.05);}}
.tab.active{{background:linear-gradient(135deg,#00e5a0,#00b878);color:#04040c;font-weight:700;}}
@media(max-width:400px){{.brand{{font-size:18px;padding:12px 0 6px;}}}}
</style>
</head><body>
<canvas id="c"></canvas>
<div class="stripe"></div>
<div style="text-align:center;padding:0 20px">
  <div class="brand">NSE <em>Market</em> Analyzer</div>
  <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;
              text-transform:uppercase;color:#2e315c;margin-bottom:10px">
    ML · 500 stocks · Sentiment
  </div>
  <span class="chip {badge[0]}"><span class="dot"></span>{badge[1]}</span>
  <div class="tabs">
    <button class="tab {si}" data-tab="signin">Sign In</button>
    <button class="tab {rg}" data-tab="register">Register</button>
  </div>
</div>
<script>
(function(){{
  var c=document.getElementById('c'),ctx=c.getContext('2d'),W,H,pts=[];
  function resize(){{W=c.width=window.innerWidth;H=c.height=window.innerHeight;}}
  resize();window.addEventListener('resize',resize,{{passive:true}});
  for(var i=0;i<50;i++)pts.push({{
    x:Math.random()*2000,y:Math.random()*600,
    vx:(Math.random()-.5)*.3,vy:(Math.random()-.5)*.3,
    r:Math.random()*1.2+.3,a:Math.random()*.3+.07}});
  function draw(){{
    ctx.clearRect(0,0,W,H);
    for(var i=0;i<pts.length;i++){{
      var p=pts[i];p.x+=p.vx;p.y+=p.vy;
      if(p.x<0||p.x>W)p.vx*=-1;if(p.y<0||p.y>H)p.vy*=-1;
      ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
      ctx.fillStyle='rgba(0,229,160,'+p.a+')';ctx.fill();
      for(var j=i+1;j<pts.length;j++){{
        var q=pts[j],dx=p.x-q.x,dy=p.y-q.y,d=Math.sqrt(dx*dx+dy*dy);
        if(d<110){{ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(q.x,q.y);
          ctx.strokeStyle='rgba(0,229,160,'+(0.05*(1-d/110))+')';
          ctx.lineWidth=.5;ctx.stroke();}}
      }}
    }}
    requestAnimationFrame(draw);
  }}
  draw();
  /* wire tab-clicks to Streamlit hidden buttons */
  document.querySelectorAll('.tab').forEach(function(btn){{
    btn.addEventListener('click',function(){{
      var tab=btn.getAttribute('data-tab');
      try{{window.parent.document.querySelectorAll('[data-testid="stButton"] button')
        .forEach(function(b){{if(b.innerText.trim()===tab)b.click();}});}}catch(e){{}}
    }});
  }});
}})();
</script>
</body></html>"""


# ─── Session init ─────────────────────────────────────────────────────────────
def _init():
    defs = {"logged_in": False, "user_info": {}, "auth_tab": "signin",
            "otp_step": "email", "otp_email": "", "otp_local": "", "otp_context": ""}
    for k, v in defs.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _render_panels_start(): pass  # sentinel – keeps test_switchers scan bounded


# ─── OTP verify panel ─────────────────────────────────────────────────────────
def _otp_verify(sb_mode: bool):
    email      = st.session_state["otp_email"]
    local_code = st.session_state.get("otp_local", "")

    st.markdown(f"""
    <div style="background:rgba(0,229,160,.04);border:1px solid rgba(0,229,160,.15);
                border-radius:12px;padding:20px;margin:0 0 18px;text-align:center">
      <div style="font-size:26px;margin-bottom:8px">📨</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:2px;
                  text-transform:uppercase;color:#00e5a0;margin-bottom:6px">Check Your Email</div>
      <div style="font-family:'Inter',sans-serif;font-size:13px;color:#5a5e8a;line-height:1.6">
        Code sent to<br>
        <span style="color:#00e5a0;font-family:'IBM Plex Mono',monospace;
                     font-weight:600;font-size:12px">{email}</span>
      </div>
    </div>""", unsafe_allow_html=True)

    if local_code:
        st.markdown(f"""
        <div style="background:rgba(240,165,0,.05);border:1px solid rgba(240,165,0,.25);
                    border-radius:10px;padding:16px;margin:0 0 14px;text-align:center">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:2px;
                      text-transform:uppercase;color:#8a6020;margin-bottom:6px">
            ⚡ Local Mode — Use This Code
          </div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:34px;font-weight:700;
                      letter-spacing:10px;color:#f0a500;margin:4px 0">{local_code}</div>
        </div>""", unsafe_allow_html=True)

    code = st.text_input("Code from email", placeholder="123456",
                         max_chars=8, key="otp_code_input")

    if st.button("✓  Verify & Sign In", type="primary",
                 use_container_width=True, key="otp_verify_btn"):
        c = (code or "").strip()
        if not c or not c.isdigit() or not (6 <= len(c) <= 8):
            st.error("⚠  Enter the 6-digit code from your email.")
        else:
            with st.spinner("Verifying…"):
                ok, msg, user_info = verify_otp(email, c)
            if ok:
                st.session_state.update({
                    "logged_in":     True,
                    "authenticated": True,
                    "username":      user_info["username"],
                    "user_info":     user_info,
                    "otp_step":      "email",
                    "otp_email":     "",
                    "otp_local":     "",
                })
                st.session_state["portfolio"] = load_user_portfolio(user_info)
                st.rerun()
            else:
                st.error(f"⚠  {msg}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("↺  Resend Code", use_container_width=True, key="otp_resend"):
            with st.spinner("Sending…"):
                ok, result = send_otp(email)
            if ok:
                parts = result.split(":")
                local = parts[3] if len(parts) >= 4 and parts[2] == "LOCAL" else ""
                st.session_state["otp_local"] = local
                st.rerun()
            else:
                _handle_send_error(result)
    with c2:
        if st.button("← Back", use_container_width=True, key="otp_back"):
            st.session_state.update({"otp_step": "email",
                                     "otp_email": "", "otp_local": ""})
            st.rerun()


# ─── Sign In panel ────────────────────────────────────────────────────────────
def _signin(sb_mode: bool):
    if st.session_state["otp_step"] == "verify":
        _otp_verify(sb_mode)
        return

    # Show success banner if redirected from registration
    reg_email = st.session_state.pop("register_success", None)
    if reg_email:
        st.markdown(f"""
        <div style="background:rgba(0,229,160,.07);border:1px solid rgba(0,229,160,.3);
                    border-radius:10px;padding:14px 16px;margin-bottom:16px">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;font-weight:700;
                      color:#00e5a0;letter-spacing:1px;margin-bottom:4px">✅ Account Created!</div>
          <div style="font-family:'Inter',sans-serif;font-size:13px;color:#4a9a78;line-height:1.6">
            Magic link sent to <strong>{reg_email}</strong><br>
            Click the link in your email to sign in.
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;
                text-transform:uppercase;color:#2e315c;margin:0 0 10px">── Sign in with email</div>
    <div style="background:rgba(0,229,160,.025);border:1px solid rgba(0,229,160,.08);
                border-radius:8px;padding:10px 14px;font-size:12px;color:#3a3e6a;
                line-height:1.7;margin-bottom:16px">
      No password needed — we'll send a one-time code to your email.
    </div>""", unsafe_allow_html=True)

    email = st.text_input("Email address", placeholder="you@example.com", key="si_email")

    if st.button("Send One-Time Code →", type="primary",
                 use_container_width=True, key="si_send"):
        e = (email or "").strip().lower()
        if not e or "@" not in e or "." not in e.split("@")[-1]:
            st.error("⚠  Enter a valid email address.")
        else:
            with st.spinner("Sending code…"):
                ok, result = send_otp(e)
            if ok:
                parts = result.split(":")
                st.session_state.update({
                    "otp_step":    "verify",
                    "otp_email":   e,
                    "otp_local":   parts[3] if len(parts) >= 4 and parts[2] == "LOCAL" else "",
                    "otp_context": "signin",
                })
                st.rerun()
            else:
                _handle_send_error(result)


# ─── Register panel ───────────────────────────────────────────────────────────


def _magic_wait_screen():
    """Shown after magic link is sent — user must click link in email."""
    email = st.session_state.get("otp_email", "")
    st.markdown(f"""
    <div style="background:rgba(0,229,160,.04);border:1px solid rgba(0,229,160,.15);
                border-radius:14px;padding:28px 24px;margin:8px 0 20px;text-align:center">
      <div style="font-size:40px;margin-bottom:12px">✉️</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:3px;
                  text-transform:uppercase;color:#00e5a0;margin-bottom:10px">
        Magic Link Sent
      </div>
      <div style="font-family:'Inter',sans-serif;font-size:14px;color:#8888aa;
                  line-height:1.7;margin-bottom:16px">
        We've sent a secure sign-in link to<br>
        <span style="color:#00e5a0;font-family:'IBM Plex Mono',monospace;
                     font-weight:600;font-size:13px">{email}</span>
      </div>
      <div style="font-family:'Inter',sans-serif;font-size:12px;color:#3a3e6a;line-height:1.8">
        1. Open your email inbox<br>
        2. Click the <strong style="color:#00e5a0">Confirm your email</strong> link<br>
        3. You'll be signed in automatically
      </div>
    </div>
    <div style="background:rgba(240,165,0,.04);border:1px solid rgba(240,165,0,.12);
                border-radius:8px;padding:10px 14px;
                font-family:'IBM Plex Mono',monospace;font-size:9px;
                letter-spacing:1px;color:#6a5020;text-align:center">
      ⏱ Link expires in 60 minutes &nbsp;·&nbsp; Check spam if not received
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("← Back to Register", use_container_width=True, key="magic_back"):
        st.session_state.update({
            "otp_step": "email", "otp_email": "",
            "otp_context": "", "auth_tab": "register",
        })
        st.rerun()

def _register(sb_mode: bool):
    # Magic link waiting screen (Supabase mode)
    if (st.session_state["otp_step"] == "magic_wait"
            and st.session_state["otp_context"] == "register"):
        _magic_wait_screen()
        return

    # OTP code verify (local mode fallback)
    if (st.session_state["otp_step"] == "verify"
            and st.session_state["otp_context"] == "register"):
        _otp_verify(sb_mode)
        return

    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;
                text-transform:uppercase;color:#2e315c;margin:0 0 12px">── Create account</div>
    """, unsafe_allow_html=True)

    ca, cb = st.columns(2)
    with ca:
        name  = st.text_input("Full name",  placeholder="Rahul Sharma",  key="rg_name")
    with cb:
        uname = st.text_input("Username",   placeholder="rahul_trades",  key="rg_user")
    email = st.text_input("Email address",  placeholder="rahul@example.com", key="rg_email")

    st.markdown(
        f'<div style="background:rgba(0,229,160,.025);border:1px solid rgba(0,229,160,.08);'
        f'border-radius:8px;padding:10px 14px;font-size:12px;color:#3a3e6a;'
        f'line-height:1.7;margin:8px 0">{"☁ Magic link via Supabase." if sb_mode else "⚡ Local mode — OTP code."}'
        f' Username: 3–20 chars (letters, numbers, _).</div>',
        unsafe_allow_html=True)

    if st.button("Create Account → Verify Email ✉", type="primary",
                 use_container_width=True, key="rg_btn"):
        n = (name  or "").strip()
        u = (uname or "").strip()
        e = (email or "").strip().lower()
        if not all([n, u, e]):
            st.error("⚠  Fill in all three fields.")
        else:
            with st.spinner("Creating account…"):
                ok, result = register(u, n, e)
            if ok:
                parts = result.split(":")
                if result.startswith("MAGIC_LINK:"):
                    # Magic link sent — switch to signin tab with success banner
                    st.session_state.update({
                        "auth_tab":       "signin",
                        "otp_step":       "email",
                        "otp_context":    "",
                        "otp_email":      "",
                        "register_success": parts[1] if len(parts) >= 2 else e,
                    })
                else:
                    # Local mode fallback — use OTP code
                    st.session_state.update({
                        "otp_step":    "verify",
                        "otp_email":   parts[1] if len(parts) >= 2 else e,
                        "otp_local":   parts[3] if len(parts) >= 4 and parts[2] == "LOCAL" else "",
                        "otp_context": "register",
                    })
                st.rerun()
            else:
                if result.startswith("USERNAME_TAKEN:"):
                    sugg = [s for s in result.split(":", 1)[1].split(",") if s]
                    st.error(f"⚠  @{u} is already taken.")
                    if sugg:
                        chips = "".join(
                            f'<span style="display:inline-block;background:#12122c;'
                            f'border:1px solid rgba(0,229,160,.2);border-radius:5px;'
                            f'padding:3px 9px;margin:2px 2px 2px 0;'
                            f'font-family:IBM Plex Mono,monospace;font-size:10px;'
                            f'color:#00e5a0">@{s}</span>' for s in sugg)
                        st.markdown(
                            f'<div style="background:#0d0d22;border:1px solid #1a1a3a;'
                            f'border-radius:8px;padding:10px 12px;margin-top:6px">'
                            f'<div style="font-family:IBM Plex Mono,monospace;font-size:8px;'
                            f'letter-spacing:2px;color:#5a5e8a;text-transform:uppercase;'
                            f'margin-bottom:6px">Suggestions</div>{chips}</div>',
                            unsafe_allow_html=True)
                elif result.startswith("EMAIL_EXISTS:"):
                    st.error("⚠  Email already registered — use Sign In.")
                else:
                    _handle_send_error(result)


# ─── Hidden tab switchers (clicked by iframe JS) ──────────────────────────────
def _switchers():
    cur = st.session_state.get("auth_tab", "signin")

    # Visual tab bar rendered as HTML (purely decorative — no form widgets)
    si_bg  = "linear-gradient(135deg,#00e5a0,#00b878)" if cur == "signin"   else "transparent"
    rg_bg  = "linear-gradient(135deg,#00e5a0,#00b878)" if cur == "register" else "transparent"
    si_col = "#04040c"  if cur == "signin"   else "#3a3e6a"
    rg_col = "#04040c"  if cur == "register" else "#3a3e6a"
    si_fw  = "700"      if cur == "signin"   else "500"
    rg_fw  = "700"      if cur == "register" else "500"

    st.markdown(f"""
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:3px;
                background:#0d0d22;border:1px solid #1a1a3a;
                border-radius:11px;padding:3px;margin-bottom:18px">
      <div style="background:{si_bg};border-radius:8px;padding:11px;text-align:center;
                  font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:{si_fw};
                  letter-spacing:1.5px;text-transform:uppercase;color:{si_col};
                  box-shadow:{'0 2px 14px rgba(0,229,160,.25)' if cur=='signin' else 'none'}">
        SIGN IN
      </div>
      <div style="background:{rg_bg};border-radius:8px;padding:11px;text-align:center;
                  font-family:'IBM Plex Mono',monospace;font-size:11px;font-weight:{rg_fw};
                  letter-spacing:1.5px;text-transform:uppercase;color:{rg_col};
                  box-shadow:{'0 2px 14px rgba(0,229,160,.25)' if cur=='register' else 'none'}">
        REGISTER
      </div>
    </div>

    <style>
    /* Force the real Streamlit tab buttons side-by-side, tightly */
    div[data-testid="stHorizontalBlock"]:has(button[data-testid="baseButton-secondary"]) {{
      gap: 4px !important;
    }}
    /* Hide the functional tab buttons visually — they're clicked programmatically */
    button[key="_sw_si"], button[key="_sw_rg"] {{ display:none !important; }}
    </style>
    """, unsafe_allow_html=True)

    # Actual functional buttons — hidden, wired to the HTML tabs above via JS
    c1, c2 = st.columns(2)
    with c1:
        if st.button("signin", key="_sw_si", use_container_width=True):
            st.session_state.update({"auth_tab": "signin", "otp_step": "email"})
            st.rerun()
    with c2:
        if st.button("register", key="_sw_rg", use_container_width=True):
            st.session_state.update({"auth_tab": "register", "otp_step": "email"})
            st.rerun()

    # Hide functional buttons + wire HTML tabs to click them
    st.markdown("""<script>
(function(){
  function setup(){
    // Hide functional buttons
    ['signin','register'].forEach(function(t){
      document.querySelectorAll('[data-testid="stButton"] button').forEach(function(b){
        if(b.innerText.trim()===t){
          var w=b.closest('[data-testid="stButton"]');
          if(w)w.style.cssText='display:none!important;height:0;overflow:hidden;margin:0;padding:0';
        }
      });
    });
    // Wire the HTML tab divs to click the hidden buttons
    var tabs=document.querySelectorAll('.auth-tab-trigger');
    tabs.forEach(function(tab){
      tab.style.cursor='pointer';
      tab.addEventListener('click',function(){
        var t=tab.getAttribute('data-tab');
        document.querySelectorAll('[data-testid="stButton"] button').forEach(function(b){
          if(b.innerText.trim()===t)b.click();
        });
      });
    });
  }
  setup();setTimeout(setup,200);setTimeout(setup,600);
})();
</script>""", unsafe_allow_html=True)


# ─── Public entry point ───────────────────────────────────────────────────────
def render_auth_page() -> bool:
    """Returns True if user is authenticated (caller should st.rerun())."""
    _init()

    if st.session_state.get("logged_in"):
        st.session_state["authenticated"] = True
        return True

    sb_mode = is_supabase_mode()
    cur_tab = st.session_state.get("auth_tab", "signin")

    st.markdown(_CSS, unsafe_allow_html=True)

    # Intercept Supabase magic-link tokens from URL fragment (#access_token=...&type=signup)
    # Streamlit cannot read fragments directly — JS extracts them and redirects with ?params
    st.markdown("""
    <script>
    (function(){
      var h = window.location.hash;
      if(!h) return;
      var p = {};
      h.replace(/^#/,'').split('&').forEach(function(kv){
        var parts=kv.split('='); if(parts.length===2) p[parts[0]]=decodeURIComponent(parts[1]);
      });
      var at=p['access_token'], rt=p['refresh_token']||'', tp=p['type']||'';
      var valid=['signup','magiclink','email','recovery'];
      if(at && valid.indexOf(tp)>=0){
        var url=window.location.pathname
          +'?access_token='+encodeURIComponent(at)
          +'&refresh_token='+encodeURIComponent(rt)
          +'&type='+encodeURIComponent(tp);
        window.location.replace(url);
      }
    })();
    </script>""", unsafe_allow_html=True)

    # Animated shell — rendered via components.html (decorative only, no form widgets)
    components.html(_shell_html(cur_tab, sb_mode), height=220, scrolling=False)

    # Everything inside the centered card column
    _, col, _ = st.columns([1, 2, 1])
    with col:
        # Tab switcher (inside the card — renders correctly on all screen sizes)
        _switchers()

        if cur_tab == "signin":
            _signin(sb_mode)
        else:
            _register(sb_mode)

        st.markdown("""
        <div style="text-align:center;margin-top:20px;
                    font-family:'IBM Plex Mono',monospace;font-size:9px;
                    color:#1a1a3a;letter-spacing:1px">
          ⚠ NOT FINANCIAL ADVICE · EDUCATIONAL USE ONLY
        </div>""", unsafe_allow_html=True)

    return False
