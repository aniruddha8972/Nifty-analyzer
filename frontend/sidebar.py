"""
frontend/sidebar.py
─────────────────────────────────────────────────────────────────────
Shared sidebar rendered on every authenticated page.
Shows: logo, nav links, user profile, page links, logout.
"""

import streamlit as st


def render_sidebar(current_page: str = "") -> None:
    """
    Render the full sidebar.
    current_page: 'dashboard' | 'markets' | 'predictions' |
                  'portfolio' | 'analytics' | 'news' | 'charts' | 'admin'
    """
    from frontend.session import get_user, is_authenticated
    from backend.auth import is_supabase_mode, is_admin, logout as auth_logout
    from backend.portfolio import _persist

    user     = get_user()
    name     = user.get("name", "—")
    username = user.get("username", "")
    email    = user.get("email", "")
    n_stocks = len(st.session_state.get("portfolio", {}))
    mode_cls = "mode-cloud" if is_supabase_mode() else "mode-local"
    mode_lbl = "☁ Supabase Cloud" if is_supabase_mode() else "⚡ Local Mode"
    initials = "".join(w[0].upper() for w in name.split()[:2]) if name != "—" else "?"
    _is_admin = is_admin(user)

    with st.sidebar:
        # ── Wordmark ──────────────────────────────────────────────────
        st.markdown("""
        <div style="padding:20px 0 16px">
          <div style="font-family:'Syne',sans-serif;font-size:20px;font-weight:800;
                      letter-spacing:-0.3px;color:#e8e9f5;margin-bottom:4px">
            <span style="color:#f0a500">NSE</span> Intelligence
          </div>
          <div style="font-family:'JetBrains Mono',monospace;font-size:8px;
                      letter-spacing:3px;text-transform:uppercase;color:#5a5e8a">
            Market · AI · Portfolio
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div style="height:1px;background:var(--line,#1f2240);margin-bottom:16px"></div>',
                    unsafe_allow_html=True)

        # ── Navigation ────────────────────────────────────────────────
        NAV_PAGES = [
            ("dashboard",   "📊",  "Dashboard",    "Overview & Analysis"),
            ("markets",     "📈",  "Markets",       "Gainers · Losers · All"),
            ("predictions", "🤖",  "AI Signals",    "ML Buy/Sell signals"),
            ("portfolio",   "💼",  "Portfolio",     "P&L · Advisor"),
            ("analytics",   "🗺",  "Analytics",     "Heatmap · Backtest"),
            ("news",        "📰",  "News & Macro",  "Global sentiment"),
            ("charts",      "📉",  "Index Charts",  "Live Nifty charts"),
        ]
        if _is_admin:
            NAV_PAGES.append(("admin", "🛡", "Admin", "User management"))

        st.markdown("""
        <div style="font-family:'JetBrains Mono',monospace;font-size:7px;
                    letter-spacing:3px;text-transform:uppercase;color:#2e315c;
                    margin-bottom:8px;padding-left:4px">Navigation</div>
        """, unsafe_allow_html=True)

        PAGE_MAP = {
            "dashboard":   "1_Dashboard",
            "markets":     "2_Markets",
            "predictions": "3_Predictions",
            "portfolio":   "4_Portfolio",
            "analytics":   "5_Analytics",
            "news":        "6_News",
            "charts":      "7_Charts",
            "admin":       "8_Admin",
        }

        for page_id, icon, label, desc in NAV_PAGES:
            is_cur = current_page == page_id
            bg     = "background:rgba(240,165,0,0.08);border:1px solid rgba(240,165,0,0.2);" if is_cur else "background:transparent;border:1px solid transparent;"
            col    = "#f0a500" if is_cur else "#9fa3c4"
            ic_col = "#f0a500" if is_cur else "#5a5e8a"

            st.markdown(f"""
            <div style="{bg}border-radius:8px;padding:9px 12px;
                        margin-bottom:3px;cursor:pointer;transition:all .15s"
                 onmouseenter="this.style.background='rgba(240,165,0,0.05)'"
                 onmouseleave="this.style.background='{'rgba(240,165,0,0.08)' if is_cur else 'transparent'}'">
              <div style="display:flex;align-items:center;gap:10px">
                <span style="font-size:14px;width:18px;text-align:center">{icon}</span>
                <div>
                  <div style="font-family:'JetBrains Mono',monospace;font-size:10px;
                              font-weight:600;color:{col};letter-spacing:0.5px">{label}</div>
                  <div style="font-family:'DM Sans',sans-serif;font-size:9px;
                              color:#3a3e6a">{desc}</div>
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # Hidden Streamlit button for actual navigation
            if st.button(f"{icon} {label}", key=f"nav_{page_id}",
                         use_container_width=True,
                         help=f"Go to {label}"):
                st.switch_page(f"pages/{PAGE_MAP[page_id]}.py")

        st.markdown('<div style="height:1px;background:var(--line,#1f2240);margin:16px 0"></div>',
                    unsafe_allow_html=True)

        # ── Profile card ──────────────────────────────────────────────
        st.markdown(f"""
        <div class="profile-card">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px">
            <div class="fin-avatar" style="width:36px;height:36px;font-size:12px">{initials}</div>
            <div>
              <div style="font-family:'JetBrains Mono',monospace;font-size:12px;
                          font-weight:700;color:#e8e9f5;line-height:1.2">{name}</div>
              <div style="font-family:'DM Sans',sans-serif;font-size:10px;
                          color:#5a5e8a">@{username}</div>
            </div>
          </div>
          <div style="font-family:'DM Sans',sans-serif;font-size:11px;
                      color:#3a3e6a;border-top:1px solid #1f2240;padding-top:10px;
                      line-height:2.2">
            <div>✉ <span style="color:#5a5e8a">{email}</span></div>
            <div>💼 <span style="color:#f0a500;font-family:'JetBrains Mono',monospace;
                               font-size:12px;font-weight:600">{n_stocks}</span>
              <span style="color:#3a3e6a"> holding{"s" if n_stocks != 1 else ""}</span>
            </div>
          </div>
          <div style="margin-top:10px">
            <span class="mode-badge {mode_cls}">{mode_lbl}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Change password ───────────────────────────────────────────
        with st.expander("🔑  Change Password"):
            from backend.auth import update_password, validate_password
            cur_pw  = st.text_input("Current", type="password", key="sb_cur_pw")
            new_pw  = st.text_input("New",     type="password", key="sb_new_pw")
            conf_pw = st.text_input("Confirm", type="password", key="sb_conf_pw")
            if new_pw:
                ok_v, fails = validate_password(new_pw)
                pct  = (5 - len(fails)) / 5
                col  = "#ff3d5a" if pct <= 0.4 else "#f0a500" if pct < 1.0 else "#00d4aa"
                lbl  = "Weak" if pct <= 0.4 else "Fair" if pct < 1.0 else "Strong"
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'font-size:9px;color:#5a5e8a;margin:2px 0 3px">'
                    f'<span>Strength</span><span style="color:{col}">{lbl}</span></div>'
                    f'<div style="background:#1f2240;border-radius:2px;height:3px">'
                    f'<div style="background:{col};width:{int(pct*100)}%;'
                    f'height:3px;border-radius:2px"></div></div>',
                    unsafe_allow_html=True,
                )
            if st.button("Update Password", key="sb_upd_pw", use_container_width=True, type="primary"):
                if not cur_pw or not new_pw or not conf_pw:
                    st.error("Fill all fields.")
                elif new_pw != conf_pw:
                    st.error("Passwords don't match.")
                else:
                    ok, msg = update_password(user, cur_pw, new_pw)
                    if ok: st.success(f"✅ {msg}")
                    else:  st.error(f"❌ {msg}")

        # ── Logout ────────────────────────────────────────────────────
        st.markdown("""
        <style>
        div[data-testid="stSidebar"] div[data-testid="stButton"]:last-of-type > button {
          background: transparent !important;
          border: 1px solid rgba(255,61,90,0.3) !important;
          color: #ff3d5a !important;
          font-family: 'JetBrains Mono', monospace !important;
          font-size: 10px !important;
          letter-spacing: 2px !important;
          margin-top: 8px !important;
        }
        div[data-testid="stSidebar"] div[data-testid="stButton"]:last-of-type > button:hover {
          background: rgba(255,61,90,0.08) !important;
          border-color: #ff3d5a !important;
        }
        </style>
        """, unsafe_allow_html=True)

        if st.button("⏻  SIGN OUT", use_container_width=True, key="sb_logout"):
            portfolio = st.session_state.get("portfolio", {})
            from backend.auth import save_user_portfolio
            if user:
                save_user_portfolio(user, portfolio)
                auth_logout(user)
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.switch_page("app.py")

        # ── Disclaimer ────────────────────────────────────────────────
        st.markdown("""
        <div style="margin-top:16px;padding-top:12px;border-top:1px solid #1f2240;
                    font-family:'DM Sans',sans-serif;font-size:9px;
                    color:#2e315c;font-style:italic;line-height:1.7">
          ⚠ Not financial advice.<br>
          Consult a SEBI-registered advisor.
        </div>
        """, unsafe_allow_html=True)
