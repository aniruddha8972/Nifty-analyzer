"""
frontend/sidebar.py
Shared sidebar. Uses st.page_link() for nav — no reruns, no blinking.
"""
import streamlit as st


def render_sidebar(current_page: str = "") -> None:
    from frontend.session import get_user
    from backend.auth import is_supabase_mode, is_admin, logout as auth_logout, save_user_portfolio

    user     = get_user()
    name     = user.get("name","—")
    username = user.get("username","")
    email    = user.get("email","")
    n_stocks = len(st.session_state.get("portfolio",{}))
    sb_mode  = is_supabase_mode()
    initials = "".join(w[0].upper() for w in name.split()[:2]) if name not in ("—","") else "?"
    _admin   = is_admin(user)
    mode_lbl = "☁ Cloud" if sb_mode else "⚡ Local"
    mode_cls = "badge-cloud" if sb_mode else "badge-local"

    with st.sidebar:
        # Logo
        st.markdown("""
        <div style="padding:18px 2px 14px">
          <div style="font-family:'IBM Plex Mono',monospace;font-size:16px;
                      font-weight:700;color:#e8e9f5;letter-spacing:-.3px">
            NSE <span style="color:#00e5a0">Market</span>
          </div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:7px;
                      letter-spacing:3px;text-transform:uppercase;color:#2e315c;margin-top:3px">
            Intelligence Platform
          </div>
        </div>
        <div style="height:1px;background:#1a1a3a;margin-bottom:12px"></div>
        """, unsafe_allow_html=True)

        # Suppress Streamlit's built-in page nav
        st.markdown("""
        <style>
        [data-testid="stSidebarNav"]{display:none!important;}
        section[data-testid="stSidebarNav"]{display:none!important;}
        [data-testid="stPageLink"]>div{
          padding:8px 10px!important; border-radius:8px!important;
          font-family:'IBM Plex Mono',monospace!important;
          font-size:10px!important; color:#5a5e8a!important;
          transition:all .15s!important; border:1px solid transparent!important;
          margin-bottom:1px!important;
        }
        [data-testid="stPageLink"]:hover>div{
          color:#00e5a0!important; background:rgba(0,229,160,.07)!important;
        }
        [data-testid="stPageLink"]>div>p{
          font-family:'IBM Plex Mono',monospace!important;
          font-size:10px!important; font-weight:500!important;
        }
        </style>""", unsafe_allow_html=True)

        # Nav
        PAGES = [
            ("app.py",                 "📊", "dashboard",   "Dashboard"),
            ("pages/2_Markets.py",     "📈", "markets",     "Markets"),
            ("pages/3_Predictions.py", "🤖", "predictions", "AI Signals"),
            ("pages/4_Portfolio.py",   "💼", "portfolio",   "Portfolio"),
            ("pages/5_Analytics.py",   "🗺", "analytics",   "Analytics"),
            ("pages/6_News.py",        "📰", "news",        "News & Macro"),
            ("pages/7_Charts.py",      "📉", "charts",      "Index Charts"),
        ]
        if _admin:
            PAGES.append(("pages/8_Admin.py","🛡","admin","Admin"))

        for path, icon, pid, label in PAGES:
            is_cur = current_page == pid
            if is_cur:
                st.markdown(f"""
                <div style="background:rgba(0,229,160,.07);border:1px solid rgba(0,229,160,.2);
                            border-radius:8px;padding:8px 10px;margin-bottom:1px">
                  <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;
                               font-weight:700;color:#00e5a0">{icon}  {label}</span>
                </div>""", unsafe_allow_html=True)
            else:
                st.page_link(path, label=f"{icon}  {label}")

        st.markdown('<div style="height:1px;background:#1a1a3a;margin:12px 0"></div>',
                    unsafe_allow_html=True)

        # Profile card
        st.markdown(f"""
        <div class="profile-card">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
            <div class="avatar">{initials}</div>
            <div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:13px;
                          font-weight:700;color:#e8e9f5;line-height:1.2">{name}</div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                          color:#3a3e6a;margin-top:1px">@{username}</div>
            </div>
          </div>
          <div style="font-family:'Inter',sans-serif;font-size:11px;color:#2e315c;
                      border-top:1px solid #1a1a3a;padding-top:8px;line-height:2.2">
            <div>✉ <span style="color:#3a3e6a">{email}</span></div>
            <div>💼 <span style="color:#00e5a0;font-family:'IBM Plex Mono',monospace;
                               font-size:12px;font-weight:600">{n_stocks}</span>
              <span style="color:#2e315c"> holding{"s" if n_stocks!=1 else ""}</span></div>
          </div>
          <div style="margin-top:8px">
            <span class="badge {mode_cls}">{mode_lbl}</span>
          </div>
        </div>""", unsafe_allow_html=True)

        # Change password
        with st.expander("🔑  Change Password"):
            from backend.auth import update_password, validate_password
            cur_pw  = st.text_input("Current",  type="password", key="sb_cur_pw")
            new_pw  = st.text_input("New",      type="password", key="sb_new_pw")
            conf_pw = st.text_input("Confirm",  type="password", key="sb_conf_pw")
            if new_pw:
                ok_v, fails = validate_password(new_pw)
                pct = (5 - len(fails)) / 5
                col = "#ff3d5a" if pct<=0.4 else "#f0a500" if pct<1.0 else "#00e5a0"
                lbl = "Weak"   if pct<=0.4 else "Fair"    if pct<1.0 else "Strong"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;font-size:9px;'
                    f'color:#5a5e8a;margin:2px 0 3px"><span>Strength</span>'
                    f'<span style="color:{col}">{lbl}</span></div>'
                    f'<div style="background:#1a1a3a;border-radius:2px;height:3px">'
                    f'<div style="background:{col};width:{int(pct*100)}%;height:3px;border-radius:2px"></div></div>',
                    unsafe_allow_html=True)
            if st.button("Update Password", key="sb_upd_pw", use_container_width=True, type="primary"):
                if not cur_pw or not new_pw or not conf_pw:
                    st.error("Fill all fields.")
                elif new_pw != conf_pw:
                    st.error("Passwords don't match.")
                else:
                    ok, msg = update_password(user, cur_pw, new_pw)
                    st.success(f"✅ {msg}") if ok else st.error(f"❌ {msg}")

        # Logout
        st.markdown("""
        <style>
        div[data-testid="stSidebar"] div[data-testid="stButton"]:last-of-type>button{
          background:transparent!important;
          border:1px solid rgba(255,61,90,0.3)!important;
          color:#ff3d5a!important; margin-top:8px!important;
        }
        div[data-testid="stSidebar"] div[data-testid="stButton"]:last-of-type>button:hover{
          background:rgba(255,61,90,0.08)!important; border-color:#ff3d5a!important;
        }
        </style>""", unsafe_allow_html=True)

        if st.button("⏻  SIGN OUT", use_container_width=True, key="sb_logout"):
            portfolio = st.session_state.get("portfolio",{})
            if user:
                save_user_portfolio(user, portfolio)
                auth_logout(user)
            for k in list(st.session_state.keys()): del st.session_state[k]
            st.rerun()

        st.markdown("""
        <div style="margin-top:12px;padding-top:10px;border-top:1px solid #1a1a3a;
                    font-family:'Inter',sans-serif;font-size:9px;color:#1a1a3a;
                    font-style:italic;line-height:1.7">
          ⚠ Not financial advice.<br>Consult a SEBI-registered advisor.
        </div>""", unsafe_allow_html=True)
