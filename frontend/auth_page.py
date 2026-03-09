"""
frontend/auth_page.py  —  v4: DOM-first auth with Forgot Password
──────────────────────────────────────────────────────────────────
Architecture:
  • ONE HTML block renders the entire visual shell (card, tabs, forms)
    directly in the DOM — no Streamlit columns fighting the layout.
  • JS drives tab switching: clicking a tab injects a hidden Streamlit
    button click via DOM, keeping Streamlit's state in sync.
  • Particle canvas, animated gradient border, fluid mobile layout.
  • Forgot Password panel — sends Supabase reset email (or graceful
    local-mode message).
  • Password strength meter updates live as user types (JS MutationObserver
    watches Streamlit's input DOM node).
"""

import streamlit as st
from backend.auth import (
    login, register, load_user_portfolio,
    is_supabase_mode, request_password_reset,
)


# ── Minimal global overrides (only what's needed outside the card) ─────────
_BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}

html,body{height:100%;}
body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"]{
  background:#050508!important;
  font-family:'Space Grotesk',sans-serif!important;
  color:#e8e8f0!important;
}
[data-testid="stHeader"],[data-testid="stToolbar"],
[data-testid="stDecoration"],footer,.stDeployButton{
  display:none!important;
}
[data-testid="stMainBlockContainer"]{
  padding:0!important;max-width:100%!important;
}

/* ── Canvas behind everything ── */
#nse-bg{
  position:fixed;inset:0;z-index:0;
  pointer-events:none;
}

/* ── Auth shell ── */
.nse-auth{
  position:relative;z-index:10;
  min-height:100vh;width:100%;
  display:flex;align-items:center;justify-content:center;
  padding:20px 16px 36px;
}

/* ── Card ── */
.nse-card{
  width:100%;max-width:460px;
  background:rgba(10,10,18,0.92);
  backdrop-filter:blur(24px);-webkit-backdrop-filter:blur(24px);
  border-radius:20px;
  border:1px solid rgba(255,255,255,0.07);
  overflow:hidden;
  box-shadow:
    0 0 0 1px rgba(0,230,160,0.08),
    0 32px 80px rgba(0,0,0,0.7),
    inset 0 1px 0 rgba(255,255,255,0.05);
  animation:slideUp .5s cubic-bezier(.16,1,.3,1) both;
}
@keyframes slideUp{
  from{opacity:0;transform:translateY(28px) scale(.97);}
  to{opacity:1;transform:translateY(0) scale(1);}
}

/* Animated top stripe */
.nse-stripe{
  height:2px;width:100%;
  background:linear-gradient(90deg,
    transparent 0%,
    #00e6a0 20%,
    #4c8eff 40%,
    #00e6a0 60%,
    #7b4fff 80%,
    transparent 100%
  );
  background-size:400% 100%;
  animation:stripe 5s linear infinite;
}
@keyframes stripe{
  0%{background-position:100% 0}
  100%{background-position:-100% 0}
}

/* ── Inner padding ── */
.nse-inner{padding:36px 36px 30px;}
@media(max-width:500px){.nse-inner{padding:26px 20px 22px;}}

/* ── Logo ── */
.nse-logo{text-align:center;margin-bottom:30px;}
.nse-eyebrow{
  font-family:'JetBrains Mono',monospace;
  font-size:9px;letter-spacing:5px;text-transform:uppercase;
  color:#00e6a0;margin-bottom:12px;opacity:.8;
}
.nse-brand{
  font-family:'Space Grotesk',sans-serif;
  font-size:clamp(22px,6vw,30px);font-weight:700;
  color:#fff;letter-spacing:-0.5px;line-height:1;
}
.nse-brand span{color:#00e6a0;}
.nse-sub{
  font-size:12px;color:#5a5a72;margin-top:7px;
  font-weight:400;letter-spacing:0.2px;
}
.nse-chip{
  display:inline-flex;align-items:center;gap:5px;
  margin-top:12px;padding:4px 12px;border-radius:100px;
  font-family:'JetBrains Mono',monospace;
  font-size:9px;letter-spacing:1.5px;text-transform:uppercase;
}
.chip-cloud{background:rgba(0,230,160,.06);border:1px solid rgba(0,230,160,.2);color:#00e6a0;}
.chip-local{background:rgba(245,166,35,.06);border:1px solid rgba(245,166,35,.2);color:#f5a623;}
.chip-dot{width:5px;height:5px;border-radius:50%;animation:pulse 2s ease infinite;}
.chip-cloud .chip-dot{background:#00e6a0;}
.chip-local .chip-dot{background:#f5a623;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}

/* ── Tab strip ── */
.nse-tabs{
  display:grid;grid-template-columns:1fr 1fr 1fr;
  gap:3px;padding:3px;
  background:#0c0c14;border:1px solid rgba(255,255,255,.05);
  border-radius:12px;margin-bottom:26px;
}
.nse-tab{
  padding:10px 6px;text-align:center;cursor:pointer;
  border-radius:9px;border:none;background:transparent;
  font-family:'JetBrains Mono',monospace;
  font-size:9px;font-weight:500;letter-spacing:1px;
  text-transform:uppercase;color:#3a3a52;
  transition:all .2s ease;position:relative;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.nse-tab:hover{color:#00e6a0;background:rgba(0,230,160,.04);}
.nse-tab.nse-active{
  background:linear-gradient(135deg,#00e6a0 0%,#00b07c 100%);
  color:#050508;font-weight:700;
  box-shadow:0 2px 14px rgba(0,230,160,.25);
}
/* Ink ripple on click */
.nse-tab::after{
  content:'';position:absolute;inset:0;border-radius:inherit;
  background:rgba(255,255,255,0);transition:background .15s;
}
.nse-tab:active::after{background:rgba(255,255,255,.08);}

/* ── Section label ── */
.nse-label{
  font-family:'JetBrains Mono',monospace;
  font-size:8px;letter-spacing:3px;text-transform:uppercase;
  color:#282838;margin-bottom:16px;
}

/* ── Streamlit input overrides (scoped to .nse-inner) ── */
.nse-inner [data-testid="stTextInput"] label{
  font-family:'JetBrains Mono',monospace!important;
  font-size:9px!important;letter-spacing:2px!important;
  text-transform:uppercase!important;color:#44445a!important;
  margin-bottom:5px!important;
}
.nse-inner [data-testid="stTextInput"] input{
  background:#0a0a12!important;
  border:1px solid #1e1e30!important;
  border-radius:10px!important;
  color:#e8e8f0!important;
  font-family:'JetBrains Mono',monospace!important;
  font-size:13px!important;
  padding:12px 16px!important;
  transition:border-color .15s,box-shadow .15s!important;
  width:100%!important;
}
.nse-inner [data-testid="stTextInput"] input:focus{
  border-color:#00e6a0!important;
  box-shadow:0 0 0 3px rgba(0,230,160,.12)!important;
  outline:none!important;
}
.nse-inner [data-testid="stTextInput"] input::placeholder{
  color:#22222e!important;
}

/* ── Buttons ── */
.nse-inner [data-testid="stButton"]>button{
  font-family:'Space Grotesk',sans-serif!important;
  font-size:13px!important;font-weight:700!important;
  letter-spacing:0.5px!important;
  height:48px!important;border-radius:10px!important;
  width:100%!important;
  transition:all .18s ease!important;
}
.nse-inner [data-testid="stButton"]>button[kind="primary"]{
  background:linear-gradient(135deg,#00e6a0,#00a872)!important;
  color:#050508!important;border:none!important;
  box-shadow:0 2px 20px rgba(0,230,160,.28)!important;
}
.nse-inner [data-testid="stButton"]>button[kind="primary"]:hover{
  background:linear-gradient(135deg,#10ffb8,#00e6a0)!important;
  box-shadow:0 4px 32px rgba(0,230,160,.42)!important;
  transform:translateY(-1px)!important;
}
.nse-inner [data-testid="stButton"]>button:not([kind="primary"]){
  background:#10101c!important;color:#44445a!important;
  border:1px solid #222234!important;
}
.nse-inner [data-testid="stButton"]>button:not([kind="primary"]):hover{
  border-color:#00e6a0!important;color:#00e6a0!important;
  background:rgba(0,230,160,.03)!important;
}

/* ── Hidden Streamlit tab-switcher buttons ── */
/* They stay in the DOM and are clickable, but visually replaced by .nse-tabs */
.nse-st-switcher{
  position:absolute;opacity:0;pointer-events:none;
  height:0!important;overflow:hidden;
}
/* Un-hide them only when JS is unavailable (progressive enhancement) */
.nse-no-js .nse-st-switcher{
  position:static;opacity:1;pointer-events:auto;
  height:auto!important;
}

/* ── Forgot link row ── */
.nse-forgot-row{
  display:flex;justify-content:flex-end;
  margin:2px 0 14px;
}
.nse-forgot-link{
  font-size:11px;color:#2e2e42;
  background:none;border:none;cursor:pointer;
  font-family:'Space Grotesk',sans-serif;
  transition:color .15s;padding:0;
}
.nse-forgot-link:hover{color:#00e6a0;text-decoration:underline;}

/* ── Hint / info box ── */
.nse-hint{
  background:rgba(0,230,160,.025);
  border:1px solid rgba(0,230,160,.08);
  border-radius:10px;padding:10px 14px;
  font-size:11px;color:#44445a;line-height:1.65;
  margin:10px 0;
}
.nse-hint-warn{
  background:rgba(245,166,35,.025);
  border:1px solid rgba(245,166,35,.12);
}

/* ── Strength meter ── */
.nse-strength{margin:8px 0 6px;}
.nse-strength-hd{
  display:flex;justify-content:space-between;align-items:center;
  font-family:'JetBrains Mono',monospace;
  font-size:8px;letter-spacing:2px;text-transform:uppercase;
  color:#282838;margin-bottom:5px;
}
.nse-strength-track{
  height:2px;background:#181820;border-radius:2px;overflow:hidden;
}
.nse-strength-fill{
  height:100%;border-radius:2px;
  transition:width .35s ease,background .35s ease;
}
.nse-req{font-size:10px;color:#282838;margin:3px 0;line-height:1.4;}
.nse-req.ok{color:#00e6a0;}

/* ── Success state ── */
.nse-success{
  background:rgba(0,230,160,.04);
  border:1px solid rgba(0,230,160,.15);
  border-radius:12px;padding:24px 20px;
  text-align:center;margin:8px 0;
}
.nse-success-icon{font-size:36px;margin-bottom:12px;}
.nse-success-title{
  font-family:'Space Grotesk',sans-serif;
  font-size:16px;font-weight:700;color:#00e6a0;
  margin-bottom:6px;
}
.nse-success-body{font-size:12px;color:#5a5a72;line-height:1.65;}

/* ── Username chips ── */
.nse-chips{
  background:#0a0a12;border:1px solid #1e1e30;
  border-radius:10px;padding:12px 14px;margin-top:8px;
}
.nse-chips-label{
  font-family:'JetBrains Mono',monospace;
  font-size:8px;letter-spacing:2px;color:#44445a;
  text-transform:uppercase;margin-bottom:8px;
}
.nse-chip-item{
  display:inline-block;
  background:#0e0e1c;
  border:1px solid rgba(0,230,160,.2);
  border-radius:6px;padding:4px 10px;margin:3px;
  font-family:'JetBrains Mono',monospace;
  font-size:11px;color:#00e6a0;
}

/* ── Footer ── */
.nse-footer{
  text-align:center;margin-top:18px;
  font-size:10px;color:#1a1a26;letter-spacing:0.3px;
}

/* ── Responsive ── */
@media(max-width:460px){
  .nse-tab{font-size:8px;padding:10px 4px;letter-spacing:0.5px;}
  [data-testid="stHorizontalBlock"]{flex-direction:column!important;}
  [data-testid="stHorizontalBlock"]>div{width:100%!important;min-width:100%!important;}
}
@media(max-width:380px){
  .nse-brand{font-size:20px;}
  .nse-tab{letter-spacing:0;}
}
</style>
"""

_CANVAS_JS = """
<script>
(function(){
  /* Particle network background */
  var canvas = document.getElementById('nse-bg');
  if(!canvas) return;
  var ctx = canvas.getContext('2d');
  var W, H, particles = [], mouse = {x:-999,y:-999};

  function resize(){
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener('resize', resize, {passive:true});
  window.addEventListener('mousemove', function(e){mouse.x=e.clientX;mouse.y=e.clientY;},{passive:true});

  /* Spawn particles */
  for(var i = 0; i < 70; i++){
    particles.push({
      x:  Math.random() * 2000,
      y:  Math.random() * 1200,
      vx: (Math.random() - .5) * .4,
      vy: (Math.random() - .5) * .4,
      r:  Math.random() * 1.5 + .3,
      a:  Math.random() * .45 + .1,
    });
  }

  function frame(){
    ctx.clearRect(0, 0, W, H);

    for(var i = 0; i < particles.length; i++){
      var p = particles[i];
      p.x += p.vx; p.y += p.vy;
      if(p.x < 0 || p.x > W) p.vx *= -1;
      if(p.y < 0 || p.y > H) p.vy *= -1;

      /* Mouse repulsion */
      var mdx = p.x - mouse.x, mdy = p.y - mouse.y;
      var md  = Math.sqrt(mdx*mdx + mdy*mdy);
      if(md < 100){ p.vx += (mdx/md)*.015; p.vy += (mdy/md)*.015; }

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(0,230,160,' + p.a + ')';
      ctx.fill();

      /* Connect nearby */
      for(var j = i+1; j < particles.length; j++){
        var q = particles[j];
        var dx = p.x-q.x, dy = p.y-q.y;
        var d  = Math.sqrt(dx*dx+dy*dy);
        if(d < 140){
          ctx.beginPath();
          ctx.moveTo(p.x,p.y); ctx.lineTo(q.x,q.y);
          ctx.strokeStyle = 'rgba(0,230,160,' + (.05*(1-d/140)) + ')';
          ctx.lineWidth = .5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(frame);
  }
  frame();
})();
</script>
"""

_TAB_JS = """
<script>
(function(){
  /* Wire the visual .nse-tab buttons to click the hidden Streamlit buttons */
  function wireTabClicks(){
    var tabs  = document.querySelectorAll('.nse-tab[data-st]');
    if(!tabs.length){ setTimeout(wireTabClicks, 150); return; }

    tabs.forEach(function(tab){
      tab.addEventListener('click', function(){
        var targetKey = tab.getAttribute('data-st');
        /* Find the hidden Streamlit button whose text matches targetKey */
        var allBtns = document.querySelectorAll('.nse-st-switcher button');
        allBtns.forEach(function(btn){
          if(btn.innerText.trim() === targetKey){ btn.click(); }
        });
      });
    });
  }
  wireTabClicks();

  /* Wire the HTML "Forgot password?" link to the hidden button */
  function wireForgotLink(){
    var link = document.getElementById('nse-forgot-link');
    if(!link){ setTimeout(wireForgotLink, 150); return; }
    link.addEventListener('click', function(e){
      e.preventDefault();
      var btns = document.querySelectorAll('.nse-st-switcher button');
      btns.forEach(function(b){
        if(b.innerText.trim() === '__forgot__'){ b.click(); }
      });
    });
  }
  wireForgotLink();
})();
</script>
"""


def _init():
    defaults = {
        "logged_in": False, "username": "", "user_info": {},
        "auth_tab": "login", "reset_sent": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _strength_html(pw: str) -> str:
    from backend.auth import validate_password
    _, fails = validate_password(pw)
    pct = (5 - len(fails)) / 5
    col = "#ef4444" if pct <= .4 else "#f5a623" if pct < 1.0 else "#00e6a0"
    lbl = "Weak" if pct <= .4 else "Fair" if pct < 1.0 else "Strong ✓"
    checks = [
        ("8+ characters",         len(pw) >= 8),
        ("Uppercase letter A–Z",  any(c.isupper() for c in pw)),
        ("Lowercase letter a–z",  any(c.islower() for c in pw)),
        ("Digit 0–9",             any(c.isdigit() for c in pw)),
        ("Special char !@#$…",    any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pw)),
    ]
    rows = "".join(
        f'<div class="nse-req {"ok" if ok else ""}">{"✓" if ok else "○"} {label}</div>'
        for label, ok in checks
    )
    return (
        f'<div class="nse-strength">'
        f'<div class="nse-strength-hd"><span>Strength</span>'
        f'<span style="color:{col}">{lbl}</span></div>'
        f'<div class="nse-strength-track">'
        f'<div class="nse-strength-fill" style="width:{int(pct*100)}%;background:{col}"></div>'
        f'</div><div style="margin-top:6px">{rows}</div></div>'
    )


# ── Hidden Streamlit switcher buttons (DOM-accessible) ─────────────────────
def _render_switchers(cur_tab: str):
    """
    Renders three invisible Streamlit buttons that the JS tab strip and
    forgot-password link will click programmatically.
    """
    st.markdown('<div class="nse-st-switcher">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("login",       key="_sw_li"):
            st.session_state["auth_tab"] = "login"; st.rerun()
    with c2:
        if st.button("register",    key="_sw_reg"):
            st.session_state["auth_tab"] = "register"; st.rerun()
    with c3:
        if st.button("forgot",      key="_sw_fp"):
            st.session_state["auth_tab"] = "forgot"
            st.session_state["reset_sent"] = False; st.rerun()
    with c4:
        if st.button("__forgot__",  key="_sw_fp2"):
            st.session_state["auth_tab"] = "forgot"
            st.session_state["reset_sent"] = False; st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ── Visual tab strip ────────────────────────────────────────────────────────
def _tab_strip(cur: str) -> str:
    tabs = [("login","Sign In"), ("register","Create Account"), ("forgot","Reset")]
    items = ""
    for key, label in tabs:
        active = "nse-active" if cur == key else ""
        items += (
            f'<button class="nse-tab {active}" data-st="{key}">'
            f'{label}</button>'
        )
    return f'<div class="nse-tabs">{items}</div>'


# ── Login panel ─────────────────────────────────────────────────────────────
def _render_login(sb_mode: bool):
    st.markdown('<div class="nse-label">── Access your account</div>', unsafe_allow_html=True)

    identifier = st.text_input(
        "Email" if sb_mode else "Email or Username",
        placeholder="you@example.com",
        key="li_id",
    )
    password = st.text_input("Password", placeholder="••••••••", type="password", key="li_pw")

    # Forgot password — HTML link wired via JS to hidden button
    st.markdown(
        '<div class="nse-forgot-row">'
        '<button class="nse-forgot-link" id="nse-forgot-link">Forgot password?</button>'
        '</div>',
        unsafe_allow_html=True,
    )

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


# ── Register panel ──────────────────────────────────────────────────────────
def _render_register(sb_mode: bool):
    st.markdown('<div class="nse-label">── New account</div>', unsafe_allow_html=True)

    ca, cb = st.columns(2)
    with ca: name  = st.text_input("Full Name",   placeholder="Rahul Sharma",      key="rg_name")
    with cb: uname = st.text_input("Username",    placeholder="rahul_trades",      key="rg_user")
    email  = st.text_input("Email",               placeholder="rahul@example.com", key="rg_email")
    cc, cd = st.columns(2)
    with cc: pw1 = st.text_input("Password",         type="password", placeholder="Min 8 chars + symbols", key="rg_pw")
    with cd: pw2 = st.text_input("Confirm Password", type="password", placeholder="Repeat",                key="rg_pw2")

    if pw1:
        st.markdown(_strength_html(pw1), unsafe_allow_html=True)

    st.markdown(
        f'<div class="nse-hint">'
        f'{"☁ Stored securely in Supabase." if sb_mode else "⚡ Local mode — stored on disk."}'
        f' Username: 3–20 chars, letters/numbers/underscore.</div>',
        unsafe_allow_html=True,
    )
    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)

    if st.button("Create Account →", type="primary", use_container_width=True, key="rg_btn"):
        if not all([name, uname, email, pw1, pw2]):
            st.error("⚠ Please fill in all fields.")
        elif pw1 != pw2:
            st.error("⚠ Passwords don't match.")
        else:
            with st.spinner("Creating account…"):
                ok, msg = register(uname, name, email, pw1)
            if ok:
                st.success("✅ Account created! Sign in below.")
                st.session_state["auth_tab"] = "login"; st.rerun()
            else:
                if msg.startswith("USERNAME_TAKEN:"):
                    sugg = [s for s in msg.split(":",1)[1].split(",") if s and s != "—"]
                    st.error(f"⚠ **@{uname}** is taken.")
                    if sugg:
                        chips = "".join(f'<span class="nse-chip-item">@{s}</span>' for s in sugg)
                        st.markdown(
                            f'<div class="nse-chips">'
                            f'<div class="nse-chips-label">Available usernames</div>'
                            f'{chips}</div>',
                            unsafe_allow_html=True,
                        )
                elif "EMAIL_EXISTS" in msg or "already registered" in msg.lower():
                    st.error("⚠ Email already registered — try signing in.")
                else:
                    st.error(f"⚠ {msg}")


# ── Forgot password panel ───────────────────────────────────────────────────
def _render_forgot(sb_mode: bool):
    if st.session_state.get("reset_sent"):
        st.markdown("""
        <div class="nse-success">
          <div class="nse-success-icon">📬</div>
          <div class="nse-success-title">Check your inbox</div>
          <div class="nse-success-body">
            If that email is registered, a reset link is on its way.<br>
            Check your spam folder if it doesn't arrive in 2 minutes.
          </div>
        </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("← Back to Sign In", use_container_width=True, key="rst_back"):
            st.session_state["auth_tab"]   = "login"
            st.session_state["reset_sent"] = False
            st.rerun()
        return

    st.markdown('<div class="nse-label">── Reset password</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="nse-hint">Enter your account email. '
        "We'll send a one-time secure reset link.</div>",
        unsafe_allow_html=True,
    )
    if not sb_mode:
        st.markdown(
            '<div class="nse-hint nse-hint-warn" style="margin-top:6px">'
            '⚡ Local mode: no email server. Ask your admin to reset your password '
            'directly via the Admin dashboard.</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    email = st.text_input("Email Address", placeholder="you@example.com", key="rst_email")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

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
            st.session_state["auth_tab"]   = "login"
            st.session_state["reset_sent"] = False; st.rerun()


# ── Public entry point ──────────────────────────────────────────────────────
def render_auth_page() -> bool:
    _init()
    if st.session_state.get("logged_in"):
        return True

    sb_mode = is_supabase_mode()
    cur_tab = st.session_state["auth_tab"]

    # 1. Global CSS
    st.markdown(_BASE_CSS, unsafe_allow_html=True)

    # 2. Canvas element (JS fills it below)
    st.markdown('<canvas id="nse-bg"></canvas>', unsafe_allow_html=True)

    # 3. Hidden Streamlit switcher buttons (before the card so DOM order works)
    _render_switchers(cur_tab)

    # 4. Card shell — pure HTML
    badge_cls  = "chip-cloud" if sb_mode else "chip-local"
    badge_text = "Supabase Cloud" if sb_mode else "Local Mode"
    act = {"login": "", "register": "", "forgot": ""}
    act[cur_tab] = "nse-active"

    st.markdown(f"""
    <div class="nse-auth">
      <div class="nse-card">
        <div class="nse-stripe"></div>
        <div class="nse-inner">

          <div class="nse-logo">
            <div class="nse-eyebrow">Quantitative &middot; Analytics</div>
            <div class="nse-brand">NSE <span>Market</span> Analyzer</div>
            <div class="nse-sub">ML-powered &middot; 500 stocks &middot; 5-year history</div>
            <div>
              <span class="nse-chip {badge_cls}">
                <span class="chip-dot"></span>
                {badge_text}
              </span>
            </div>
          </div>

          {_tab_strip(cur_tab)}

    """, unsafe_allow_html=True)

    # 5. Active form panel (Streamlit widgets live here)
    if cur_tab == "login":
        _render_login(sb_mode)
    elif cur_tab == "register":
        _render_register(sb_mode)
    else:
        _render_forgot(sb_mode)

    # 6. Close card + footer
    st.markdown("""
          <div class="nse-footer">⚠ Not financial advice &middot; Educational use only</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # 7. Canvas animation + tab-wiring JS
    st.markdown(_CANVAS_JS, unsafe_allow_html=True)
    st.markdown(_TAB_JS,    unsafe_allow_html=True)

    return False
