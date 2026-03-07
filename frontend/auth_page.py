"""
frontend/auth_page.py
─────────────────────
Login + Register page — works in both Supabase mode and local JSON mode.

Supabase mode:  email + password  (Supabase Auth handles everything)
Local mode:     username/email + password  (local JSON file)

render_auth_page() → True  if user is logged in (proceed to app)
                  → False if not yet (stop rendering)
"""

import streamlit as st
from backend.auth import login, register, load_user_portfolio, is_supabase_mode


_AUTH_CSS = """
<style>
.auth-wrap {
  max-width: 480px;
  margin: 48px auto 0;
  padding: 0 16px;
}
.auth-card {
  background: #0c0c12;
  border: 1px solid #1e1e2e;
  border-radius: 14px;
  padding: 36px 40px 32px;
  position: relative;
  overflow: hidden;
}
.auth-card::before {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, #00e5a0, #00a370);
}
.auth-logo { text-align: center; margin-bottom: 28px; }
.auth-wordmark {
  font-family: 'Space Mono', monospace;
  font-size: 9px; letter-spacing: 5px;
  text-transform: uppercase; color: #00e5a0; margin-bottom: 6px;
}
.auth-appname {
  font-family: 'Space Mono', monospace;
  font-size: 24px; font-weight: 700; color: #e8e8f0; letter-spacing: -0.5px;
}
.auth-tagline {
  font-family: 'DM Sans', sans-serif;
  font-size: 12px; color: #3a3a4e; margin-top: 4px;
}
.auth-badge {
  display: inline-block;
  font-family: 'Space Mono', monospace; font-size: 9px;
  letter-spacing: 2px; text-transform: uppercase;
  padding: 3px 10px; border-radius: 3px; margin-top: 8px;
}
.auth-badge-cloud {
  background: rgba(0,229,160,0.08);
  border: 1px solid rgba(0,229,160,0.25);
  color: #00e5a0;
}
.auth-badge-local {
  background: rgba(245,166,35,0.08);
  border: 1px solid rgba(245,166,35,0.2);
  color: #f5a623;
}
.auth-hint {
  font-family: 'DM Sans', sans-serif; font-size: 10px;
  color: #2a2a3e; margin: 6px 0 12px; line-height: 1.6;
}
.auth-footer {
  text-align: center; margin-top: 20px;
  font-family: 'DM Sans', sans-serif; font-size: 11px;
  color: #2a2a3e; font-style: italic;
}
/* Input overrides */
.auth-wrap [data-testid="stTextInput"] label {
  font-family: 'Space Mono', monospace !important;
  font-size: 9px !important; letter-spacing: 2px !important;
  text-transform: uppercase !important; color: #4a4a60 !important;
}
.auth-wrap [data-testid="stTextInput"] input {
  background: #08080e !important;
  border: 1px solid #1e1e2e !important;
  border-radius: 7px !important; color: #e8e8f0 !important;
  font-family: 'Space Mono', monospace !important;
  font-size: 13px !important; padding: 10px 14px !important;
}
.auth-wrap [data-testid="stTextInput"] input:focus {
  border-color: #00e5a0 !important;
  box-shadow: 0 0 0 2px rgba(0,229,160,0.12) !important;
}
.auth-wrap [data-testid="stButton"] > button {
  font-family: 'Space Mono', monospace !important;
  font-size: 11px !important; letter-spacing: 2px !important;
  text-transform: uppercase !important; height: 44px !important;
  border-radius: 7px !important; width: 100%;
}
.auth-wrap [data-testid="stButton"] > button[kind="primary"] {
  background: #00e5a0 !important; color: #030306 !important;
  border: none !important; font-weight: 700 !important;
}
.auth-wrap [data-testid="stButton"] > button[kind="primary"]:hover {
  background: #00ffb3 !important;
  box-shadow: 0 0 22px rgba(0,229,160,0.3) !important;
}
</style>
"""


def _init():
    defaults = {
        "logged_in": False,
        "username":  "",
        "user_info": {},
        "auth_tab":  "login",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def render_auth_page() -> bool:
    """
    Renders login/register. Returns True if authenticated.
    Handles both Supabase and local JSON modes transparently.
    """
    _init()

    if st.session_state.get("logged_in"):
        return True

    sb_mode = is_supabase_mode()

    st.markdown(_AUTH_CSS, unsafe_allow_html=True)
    st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)

    # ── Logo ──────────────────────────────────────────────────────────
    badge_cls  = "auth-badge-cloud" if sb_mode else "auth-badge-local"
    badge_text = "☁ Supabase Cloud"  if sb_mode else "⚡ Local Mode"
    st.markdown(f"""
    <div class="auth-logo">
      <div class="auth-wordmark">QUANTITATIVE · ANALYTICS</div>
      <div class="auth-appname">Nifty 50 Analyzer</div>
      <div class="auth-tagline">ML-powered market intelligence · Nifty 50</div>
      <div><span class="auth-badge {badge_cls}">{badge_text}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Tab switcher ──────────────────────────────────────────────────
    col1, col2, _ = st.columns([1.6, 2.0, 4])
    with col1:
        if st.button("→  Sign In",
                     type="primary" if st.session_state["auth_tab"] == "login" else "secondary",
                     key="tab_li"):
            st.session_state["auth_tab"] = "login"
            st.rerun()
    with col2:
        if st.button("✦  Create Account",
                     type="primary" if st.session_state["auth_tab"] == "register" else "secondary",
                     key="tab_reg"):
            st.session_state["auth_tab"] = "register"
            st.rerun()

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════
    #  LOGIN
    # ══════════════════════════════════════════════════════════════════
    if st.session_state["auth_tab"] == "login":
        st.markdown("""
        <div style="font-family:'Space Mono',monospace;font-size:9px;
                    letter-spacing:3px;text-transform:uppercase;color:#4a4a60;margin-bottom:14px">
          ── SIGN IN
        </div>
        """, unsafe_allow_html=True)

        id_label = "Email Address" if sb_mode else "Email or Username"
        id_ph    = "you@example.com" if sb_mode else "you@example.com or your_username"

        identifier = st.text_input(id_label, placeholder=id_ph, key="li_id")
        password   = st.text_input("Password", placeholder="••••••••",
                                   type="password", key="li_pw")

        if sb_mode:
            st.markdown("""
            <div class="auth-hint">
              Use the email address you registered with.
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        do_login = st.button("→  Sign In", type="primary",
                             use_container_width=True, key="li_btn")

        if do_login:
            if not identifier or not password:
                st.error("Please fill in both fields.")
            else:
                with st.spinner("Signing in…"):
                    ok, msg, user_info = login(identifier, password)
                if ok:
                    st.session_state["logged_in"] = True
                    st.session_state["username"]  = user_info["username"]
                    st.session_state["user_info"] = user_info
                    # Load portfolio from Supabase / local file
                    with st.spinner("Loading your portfolio…"):
                        st.session_state["portfolio"] = load_user_portfolio(user_info)
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)

    # ══════════════════════════════════════════════════════════════════
    #  REGISTER
    # ══════════════════════════════════════════════════════════════════
    else:
        st.markdown("""
        <div style="font-family:'Space Mono',monospace;font-size:9px;
                    letter-spacing:3px;text-transform:uppercase;color:#4a4a60;margin-bottom:14px">
          ── CREATE ACCOUNT
        </div>
        """, unsafe_allow_html=True)

        col_a, col_b = st.columns(2)
        with col_a:
            reg_name = st.text_input("Full Name", placeholder="Rahul Sharma",  key="rg_name")
        with col_b:
            reg_user = st.text_input("Username",  placeholder="rahul_trades",  key="rg_user")

        reg_email = st.text_input("Email Address", placeholder="rahul@example.com", key="rg_email")

        col_c, col_d = st.columns(2)
        with col_c:
            reg_pw  = st.text_input("Password",         placeholder="min 6 chars",
                                    type="password", key="rg_pw")
        with col_d:
            reg_pw2 = st.text_input("Confirm Password", placeholder="repeat password",
                                    type="password", key="rg_pw2")

        if sb_mode:
            st.markdown("""
            <div class="auth-hint">
              ☁ Your account is stored securely in Supabase.<br>
              Username: 3–20 chars, letters / numbers / underscore.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="auth-hint">
              ⚡ Local mode — data stored on server until reboot.<br>
              Username: 3–20 chars, letters / numbers / underscore.
            </div>
            """, unsafe_allow_html=True)

        do_register = st.button("✦  Create Account", type="primary",
                                use_container_width=True, key="rg_btn")

        if do_register:
            if not all([reg_name, reg_user, reg_email, reg_pw, reg_pw2]):
                st.error("Please fill in all fields.")
            elif reg_pw != reg_pw2:
                st.error("Passwords don't match.")
            else:
                with st.spinner("Creating your account…"):
                    ok, msg = register(reg_user, reg_name, reg_email, reg_pw)
                if ok:
                    st.success(msg)
                    if sb_mode:
                        st.info("✉ Check your email to confirm your address, then sign in.")
                    else:
                        st.info("Account created — you can now sign in.")
                    st.session_state["auth_tab"] = "login"
                    st.rerun()
                else:
                    st.error(msg)

    # ── Footer ────────────────────────────────────────────────────────
    st.markdown("""
    <div class="auth-footer">⚠ Not financial advice · For educational use only</div>
    """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    return False
