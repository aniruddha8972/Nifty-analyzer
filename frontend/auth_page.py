"""
frontend/auth_page.py  — Login + Register page.
render_auth_page() → True if authenticated, False otherwise.
"""

import streamlit as st
from backend.auth import login, register, load_user_portfolio, is_supabase_mode

_AUTH_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');
body,[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stMainBlockContainer"]{
  background:#04040a!important;
}
.auth-shell{max-width:460px;margin:40px auto 0;padding:0 16px;}
.auth-card{
  background:#09090f;border:1px solid #1c1c2e;border-radius:14px;
  padding:36px 38px 30px;position:relative;overflow:hidden;
}
.auth-card::before{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  background:linear-gradient(90deg,#00e5a0,#006644,#00e5a0);
  background-size:200% 100%;animation:shimmer 3s linear infinite;
}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
.auth-logo{text-align:center;margin-bottom:28px;}
.auth-wordmark{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:6px;text-transform:uppercase;color:#00e5a0;margin-bottom:8px;}
.auth-appname{font-family:'IBM Plex Mono',monospace;font-size:26px;font-weight:700;color:#eeeef8;letter-spacing:-1px;line-height:1;}
.auth-tagline{font-family:'Inter',sans-serif;font-size:12px;color:#5a5a78;margin-top:6px;}
.auth-badge{
  display:inline-block;font-family:'IBM Plex Mono',monospace;font-size:8px;
  letter-spacing:2px;text-transform:uppercase;padding:3px 10px;border-radius:4px;margin-top:10px;
}
.badge-cloud{background:rgba(0,229,160,.08);border:1px solid rgba(0,229,160,.25);color:#00e5a0;}
.badge-local{background:rgba(245,166,35,.08);border:1px solid rgba(245,166,35,.2);color:#f5a623;}
.auth-section-label{
  font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:3px;
  text-transform:uppercase;color:#33334a;margin-bottom:14px;
}
.auth-hint{
  background:rgba(0,229,160,.03);border:1px solid rgba(0,229,160,.1);
  border-radius:8px;padding:9px 13px;
  font-family:'Inter',sans-serif;font-size:11px;color:#5a5a78;line-height:1.7;margin:8px 0;
}
.auth-footer{
  text-align:center;margin-top:18px;
  font-family:'Inter',sans-serif;font-size:10px;color:#1c1c2e;font-style:italic;
}
/* Input overrides for auth page */
.auth-shell [data-testid="stTextInput"] label{
  font-family:'IBM Plex Mono',monospace!important;font-size:8px!important;
  letter-spacing:2px!important;text-transform:uppercase!important;color:#5a5a78!important;
}
.auth-shell [data-testid="stTextInput"] input{
  background:#04040a!important;border:1px solid #1c1c2e!important;border-radius:8px!important;
  color:#eeeef8!important;font-family:'IBM Plex Mono',monospace!important;
  font-size:13px!important;padding:10px 14px!important;transition:border-color .15s,box-shadow .15s!important;
}
.auth-shell [data-testid="stTextInput"] input:focus{
  border-color:#00e5a0!important;box-shadow:0 0 0 3px rgba(0,229,160,.15)!important;
}
.auth-shell [data-testid="stTextInput"] input::placeholder{color:#1c1c2e!important;}
.auth-shell [data-testid="stButton"]>button{
  font-family:'IBM Plex Mono',monospace!important;font-size:10px!important;
  letter-spacing:2px!important;text-transform:uppercase!important;
  height:44px!important;border-radius:8px!important;width:100%;font-weight:700!important;
  transition:all .18s ease!important;
}
.auth-shell [data-testid="stButton"]>button[kind="primary"]{
  background:linear-gradient(135deg,#00e5a0,#00a370)!important;
  color:#030306!important;border:none!important;box-shadow:0 2px 18px rgba(0,229,160,.3)!important;
}
.auth-shell [data-testid="stButton"]>button[kind="primary"]:hover{
  background:linear-gradient(135deg,#00ffb3,#00e5a0)!important;
  box-shadow:0 4px 26px rgba(0,229,160,.45)!important;transform:translateY(-1px)!important;
}
.auth-shell [data-testid="stButton"]>button:not([kind="primary"]){
  background:#0e0e17!important;color:#5a5a78!important;border:1px solid #26263a!important;
}
.auth-shell [data-testid="stButton"]>button:not([kind="primary"]):hover{
  border-color:#00e5a0!important;color:#00e5a0!important;background:rgba(0,229,160,.04)!important;
}
</style>
"""


def _init():
    for k, v in {"logged_in": False, "username": "", "user_info": {}, "auth_tab": "login"}.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_auth_page() -> bool:
    _init()
    if st.session_state.get("logged_in"):
        return True

    sb_mode = is_supabase_mode()
    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)

    # ── Logo ───────────────────────────────────────────────────────────
    badge_cls  = "badge-cloud" if sb_mode else "badge-local"
    badge_text = "☁ Supabase Cloud" if sb_mode else "⚡ Local Mode"
    st.markdown(f"""
    <div class="auth-logo">
      <div class="auth-wordmark">Quantitative &middot; Analytics</div>
      <div class="auth-appname">Nifty 50 Analyzer</div>
      <div class="auth-tagline">ML-powered market intelligence</div>
      <div><span class="auth-badge {badge_cls}">{badge_text}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tab buttons ─────────────────────────────────────────────────────
    c1, c2, _ = st.columns([1.6, 2.2, 4])
    with c1:
        if st.button("→ Sign In",
                     type="primary" if st.session_state["auth_tab"] == "login" else "secondary",
                     key="tab_li"):
            st.session_state["auth_tab"] = "login"; st.rerun()
    with c2:
        if st.button("✦ Create Account",
                     type="primary" if st.session_state["auth_tab"] == "register" else "secondary",
                     key="tab_reg"):
            st.session_state["auth_tab"] = "register"; st.rerun()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    #  LOGIN
    # ══════════════════════════════════════════════
    if st.session_state["auth_tab"] == "login":
        st.markdown('<div class="auth-section-label">── Sign In</div>', unsafe_allow_html=True)

        identifier = st.text_input(
            "Email or Username" if not sb_mode else "Email Address",
            placeholder="you@example.com" if sb_mode else "email or username",
            key="li_id"
        )
        password = st.text_input("Password", placeholder="••••••••", type="password", key="li_pw")
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("→  Sign In", type="primary", use_container_width=True, key="li_btn"):
            if not identifier or not password:
                st.error("Please fill in both fields.")
            else:
                with st.spinner("Signing in…"):
                    ok, msg, user_info = login(identifier, password)
                if ok:
                    st.session_state["logged_in"]  = True
                    st.session_state["username"]   = user_info["username"]
                    st.session_state["user_info"]  = user_info
                    with st.spinner("Loading your portfolio…"):
                        st.session_state["portfolio"] = load_user_portfolio(user_info)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ══════════════════════════════════════════════
    #  REGISTER
    # ══════════════════════════════════════════════
    else:
        st.markdown('<div class="auth-section-label">── Create Account</div>', unsafe_allow_html=True)

        ca, cb = st.columns(2)
        with ca:
            reg_name = st.text_input("Full Name",  placeholder="Rahul Sharma", key="rg_name")
        with cb:
            reg_user = st.text_input("Username",   placeholder="rahul_trades", key="rg_user")

        reg_email = st.text_input("Email Address", placeholder="rahul@example.com", key="rg_email")

        cc, cd = st.columns(2)
        with cc:
            reg_pw  = st.text_input("Password",         type="password",
                                    placeholder="Min 8 + A-Z + 0-9 + symbol", key="rg_pw")
        with cd:
            reg_pw2 = st.text_input("Confirm Password", type="password",
                                    placeholder="Repeat password", key="rg_pw2")

        # Live strength meter
        if reg_pw:
            from backend.auth import validate_password
            _v, _f = validate_password(reg_pw)
            _pct   = (5 - len(_f)) / 5
            _col   = "#ef4444" if _pct <= 0.4 else "#f5a623" if _pct < 1.0 else "#00e5a0"
            _lbl   = "Weak" if _pct <= 0.4 else "Fair" if _pct < 1.0 else "Strong"
            st.markdown(
                f'<div style="margin:6px 0 4px">'
                f'<div style="display:flex;justify-content:space-between;'
                f'font-family:IBM Plex Mono,monospace;font-size:8px;letter-spacing:2px;'
                f'text-transform:uppercase;color:#33334a;margin-bottom:4px">'
                f'<span>Password Strength</span><span style="color:{_col}">{_lbl}</span></div>'
                f'<div style="background:#1c1c2e;border-radius:3px;height:3px">'
                f'<div style="background:{_col};width:{int(_pct*100)}%;height:3px;border-radius:3px;'
                f'transition:width .3s"></div></div></div>',
                unsafe_allow_html=True
            )
            for req in _f:
                st.markdown(
                    f'<div style="font-size:10px;color:#33334a;margin:1px 0">'
                    f'&#x2717;&nbsp; {req}</div>', unsafe_allow_html=True
                )
            if not _f:
                st.markdown(
                    '<div style="font-size:10px;color:#00e5a0;margin:1px 0">'
                    '&#x2713;&nbsp; All requirements met</div>', unsafe_allow_html=True
                )

        st.markdown(
            f'<div class="auth-hint">{"☁ Account stored securely in Supabase." if sb_mode else "⚡ Local mode."}'
            f' Username: 3–20 chars, letters/numbers/underscore.</div>',
            unsafe_allow_html=True
        )

        if st.button("✦  Create Account", type="primary", use_container_width=True, key="rg_btn"):
            if not all([reg_name, reg_user, reg_email, reg_pw, reg_pw2]):
                st.error("Please fill in all fields.")
            elif reg_pw != reg_pw2:
                st.error("Passwords don't match.")
            else:
                with st.spinner("Creating your account…"):
                    ok, msg = register(reg_user, reg_name, reg_email, reg_pw)
                if ok:
                    st.success(msg)
                    st.session_state["auth_tab"] = "login"
                    st.rerun()
                else:
                    if msg.startswith("USERNAME_TAKEN:"):
                        suggestions = [s for s in msg.split(":", 1)[1].split(",") if s and s != "—"]
                        st.error(f"Username **{reg_user}** is already taken.")
                        if suggestions:
                            chips = "".join(
                                f'<span style="display:inline-block;background:#09090f;'
                                f'border:1px solid rgba(0,229,160,.3);border-radius:5px;'
                                f'padding:3px 10px;margin:3px;font-family:IBM Plex Mono,monospace;'
                                f'font-size:12px;color:#00e5a0">@{s}</span>'
                                for s in suggestions
                            )
                            st.markdown(
                                f'<div style="background:#09090f;border:1px solid #1c1c2e;'
                                f'border-radius:8px;padding:12px 16px;margin-top:8px">'
                                f'<div style="font-family:IBM Plex Mono,monospace;font-size:9px;'
                                f'letter-spacing:2px;color:#5a5a78;margin-bottom:8px">AVAILABLE USERNAMES</div>'
                                f'{chips}</div>',
                                unsafe_allow_html=True
                            )
                    elif "EMAIL_EXISTS" in msg or "already registered" in msg.lower():
                        st.error("Email already registered.")
                        st.info("👉 Click **Sign In** to log in instead.")
                    else:
                        st.error(msg)

    # Footer
    st.markdown('<div class="auth-footer">&#9888; Not financial advice &middot; Educational use only</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    return False
