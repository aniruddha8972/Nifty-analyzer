"""
frontend/admin_dashboard.py
────────────────────────────
Full admin dashboard — only visible to users with is_admin = True.

Features:
  • User list — see all registered users
  • Create user — add new user directly from UI
  • Delete user — remove any non-admin user
  • Toggle admin — grant/revoke admin rights
  • View portfolio — inspect any user's holdings
  • Stats panel — total users, admins, active portfolios
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def _is_admin() -> bool:
    return st.session_state.get("user_info", {}).get("is_admin", False)


def _token() -> str:
    return st.session_state.get("user_info", {}).get("access_token", "")


def _section(title: str, sub: str = "") -> None:
    sub_html = f'<span style="font-size:11px;color:#5a5a78;margin-left:10px">{sub}</span>' if sub else ""
    st.markdown(
        f'<div style="font-family:IBM Plex Mono,monospace;font-size:13px;'
        f'font-weight:700;color:#eeeef8;margin:20px 0 14px">{title}{sub_html}</div>',
        unsafe_allow_html=True,
    )


def _badge(text: str, color: str) -> str:
    return (
        f'<span style="display:inline-block;background:{color}18;'
        f'border:1px solid {color}44;border-radius:3px;padding:1px 7px;'
        f'font-size:9px;letter-spacing:1px;color:{color};'
        f'font-family:IBM Plex Mono,monospace;text-transform:uppercase">{text}</span>'
    )


def render_admin_dashboard() -> None:
    """Main entry — renders full admin UI."""
    if not _is_admin():
        st.error("🔒 Admin access required.")
        return

    from backend.db_init import (
        admin_list_users, admin_delete_user,
        admin_toggle_admin, admin_get_user_portfolio,
        admin_create_user,
    )

    # ── Header ─────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:linear-gradient(135deg,#0a1a10,#080814);
                border:1px solid #1a3a28;border-radius:12px;
                padding:20px 24px;margin-bottom:20px">
      <div style="font-family:IBM Plex Mono,monospace;font-size:9px;
                  letter-spacing:4px;color:#00e5a0;text-transform:uppercase">
        ADMIN DASHBOARD
      </div>
      <div style="font-family:IBM Plex Mono,monospace;font-size:20px;
                  font-weight:700;color:#eeeef8;margin-top:4px">
        User Management
      </div>
      <div style="font-family:Inter,sans-serif;font-size:12px;
                  color:#5a5a78;margin-top:4px">
        Full access to all user accounts and portfolios
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Fetch all users ─────────────────────────────────────────────────
    token = _token()
    users = admin_list_users(token)

    # ── Stats row ───────────────────────────────────────────────────────
    total     = len(users)
    admins    = sum(1 for u in users if u.get("is_admin"))
    regulars  = total - admins

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, color in [
        (c1, "Total Users",    total,    "#00e5a0"),
        (c2, "Regular Users",  regulars, "#eeeef8"),
        (c3, "Admins",         admins,   "#f59e0b"),
        (c4, "Mode",           "Supabase ☁", "#8b5cf6"),
    ]:
        with col:
            st.markdown(
                f'<div style="background:#09090f;border:1px solid #1c1c2e;'
                f'border-radius:8px;padding:14px 16px;text-align:center">'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:9px;'
                f'letter-spacing:1px;color:#5a5a78;text-transform:uppercase;'
                f'margin-bottom:6px">{label}</div>'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:20px;'
                f'font-weight:700;color:{color}">{val}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Tabs: Users | Create | Portfolios ──────────────────────────────
    tab_users, tab_create, tab_ports = st.tabs([
        "👥  All Users", "➕  Create User", "💼  Portfolios"
    ])

    # ══════════════════════════════════════════════════════════════════
    # TAB 1 — ALL USERS
    # ══════════════════════════════════════════════════════════════════
    with tab_users:
        _section("All Users", f"{total} accounts")

        if not users:
            st.info("No users found.")
        else:
            for u in users:
                uid      = u.get("id", "")
                uname    = u.get("username", "—")
                name     = u.get("name", "—")
                email    = u.get("email", "—")
                is_adm   = u.get("is_admin", False)
                joined   = u.get("created_at", "")[:10] if u.get("created_at") else "—"
                me       = uid == st.session_state.get("user_info", {}).get("user_id", "")

                badge_html = _badge("ADMIN", "#f59e0b") if is_adm else _badge("USER", "#5a5a78")
                me_html    = _badge("YOU", "#00e5a0") if me else ""

                with st.container():
                    st.markdown(
                        f'<div style="background:#09090f;border:1px solid #1c1c2e;'
                        f'border-left:3px solid {"#f59e0b" if is_adm else "#1c1c2e"};'
                        f'border-radius:8px;padding:12px 16px;margin-bottom:8px">'
                        f'<div style="display:flex;justify-content:space-between;align-items:center">'
                        f'<div>'
                        f'<span style="font-family:IBM Plex Mono,monospace;font-size:13px;'
                        f'font-weight:700;color:#eeeef8">{name}</span>'
                        f'&nbsp;&nbsp;{badge_html}&nbsp;{me_html}'
                        f'<div style="font-family:Inter,sans-serif;font-size:11px;'
                        f'color:#5a5a78;margin-top:3px">'
                        f'@{uname} · {email} · Joined {joined}</div>'
                        f'</div>'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

                    # Action buttons — not for self
                    if not me:
                        col_a, col_b, col_c, _ = st.columns([1.2, 1.4, 1.2, 4])

                        with col_a:
                            # Toggle admin
                            btn_label = "Revoke Admin" if is_adm else "Make Admin"
                            if st.button(btn_label, key=f"adm_{uid}", use_container_width=True):
                                ok, msg = admin_toggle_admin(token, uid, not is_adm)
                                if ok:
                                    st.success(f"{'Revoked' if is_adm else 'Granted'} admin for @{uname}")
                                    st.rerun()
                                else:
                                    st.error(msg)

                        with col_b:
                            # View portfolio
                            if st.button(f"View Portfolio", key=f"pf_{uid}", use_container_width=True):
                                st.session_state[f"view_pf_{uid}"] = not st.session_state.get(f"view_pf_{uid}", False)

                        with col_c:
                            # Delete — only non-admins
                            if not is_adm:
                                if st.button("🗑 Delete", key=f"del_{uid}", use_container_width=True,
                                             type="secondary"):
                                    st.session_state[f"confirm_del_{uid}"] = True

                        # Confirm delete
                        if st.session_state.get(f"confirm_del_{uid}"):
                            st.warning(f"⚠ Delete **{name}** (@{uname})? This cannot be undone.")
                            cy, cn, _ = st.columns([1, 1, 6])
                            with cy:
                                if st.button("Yes, delete", key=f"yes_{uid}", type="primary"):
                                    ok, msg = admin_delete_user(token, uid)
                                    if ok:
                                        if msg == "auth":
                                            st.success(f"✅ @{uname} fully deleted — profile, portfolio and login credentials removed")
                                        elif "profile_only" in msg:
                                            st.warning(
                                                f"⚠️ @{uname} profile & portfolio deleted but **login credentials still exist** in Supabase Auth. "
                                                f"To fix: add `service_role_key` to your Streamlit secrets. "
                                                f"Get it from Supabase → Project Settings → API → service_role."
                                            )
                                        else:
                                            st.success(f"✅ @{uname} deleted")
                                        st.session_state.pop(f"confirm_del_{uid}", None)
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            with cn:
                                if st.button("Cancel", key=f"no_{uid}"):
                                    st.session_state.pop(f"confirm_del_{uid}", None)
                                    st.rerun()

                        # Inline portfolio view
                        if st.session_state.get(f"view_pf_{uid}"):
                            portfolio = admin_get_user_portfolio(token, uid)
                            if not portfolio:
                                st.info(f"@{uname} has no holdings.")
                            else:
                                rows = []
                                for sym, h in portfolio.items():
                                    rows.append({
                                        "Symbol": sym,
                                        "Qty": h.get("qty", 0),
                                        "Avg Price": h.get("avg_buy_price", 0),
                                        "Sector": h.get("sector", "—"),
                                    })
                                pf_df = pd.DataFrame(rows)
                                st.dataframe(pf_df, width="stretch", hide_index=True)

                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════
    # TAB 2 — CREATE USER
    # ══════════════════════════════════════════════════════════════════
    with tab_create:
        _section("Create New User", "Admin can create accounts directly")

        c1, c2 = st.columns(2)
        with c1:
            new_name  = st.text_input("Full Name",    placeholder="Rahul Sharma",   key="adm_new_name")
            new_email = st.text_input("Email",        placeholder="rahul@gmail.com", key="adm_new_email")
            new_admin = st.checkbox("Grant admin access", key="adm_new_is_admin")
        with c2:
            new_uname = st.text_input("Username",     placeholder="rahul_trades",    key="adm_new_uname")
            new_pw    = st.text_input("Password",     placeholder="Min 8 + A-Z + 0-9 + symbol",
                                      type="password", key="adm_new_pw")

        # Suggest username based on name
        if new_name and not new_uname:
            suggestion = new_name.lower().replace(" ", "_")[:15]
            st.caption(f"💡 Suggested username: `{suggestion}`")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button("➕  Create User", type="primary", key="adm_create_btn"):
            if not all([new_name, new_uname, new_email, new_pw]):
                st.error("Please fill in all fields.")
            elif len(new_uname) < 3:
                st.error("Username must be at least 3 characters.")
            else:
                from backend.auth import validate_password
                pw_ok, pw_fails = validate_password(new_pw)
                if not pw_ok:
                    st.error("Weak password: " + " · ".join(pw_fails))
                    st.stop()
                with st.spinner("Creating user…"):
                    ok, msg = admin_create_user(
                        token, new_uname, new_name,
                        new_email, new_pw, is_admin=new_admin
                    )
                if ok:
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    # Smart username suggestions on conflict
                    if "username already taken" in msg.lower():
                        base = new_uname.lower()
                        suggestions = [f"{base}2", f"{base}_01", f"{base}_{new_name.split()[0].lower()}"]
                        st.error(f"❌ {msg}")
                        st.info(f"💡 Try instead: **{' · '.join(suggestions)}**")
                    else:
                        st.error(f"❌ {msg}")

    # ══════════════════════════════════════════════════════════════════
    # TAB 3 — PORTFOLIOS OVERVIEW
    # ══════════════════════════════════════════════════════════════════
    with tab_ports:
        ph_col, ref_col = st.columns([8, 1.5])
        with ph_col:
            _section("All Portfolios", "Admin view of every user's holdings")
        with ref_col:
            st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)
            do_refresh = st.button("🔄  Refresh", key="adm_pf_refresh", use_container_width=True)
            if do_refresh:
                # Clear cached portfolio data so it reloads below
                for k in list(st.session_state.keys()):
                    if k.startswith("adm_pf_cache_"):
                        del st.session_state[k]
                st.rerun()

        rows = []
        for u in users:
            uid = u.get("id", "")
            cache_key = f"adm_pf_cache_{uid}"
            # Cache per user so refresh is explicit, not on every rerun
            if cache_key not in st.session_state:
                st.session_state[cache_key] = admin_get_user_portfolio(token, uid)
            pf = st.session_state[cache_key]

            holdings = len(pf)
            total_val = sum(
                h.get("qty", 0) * h.get("avg_buy_price", 0)
                for h in pf.values()
            )
            rows.append({
                "User":         u.get("name", "—"),
                "Username":     "@" + u.get("username", "—"),
                "Email":        u.get("email", "—"),
                "Holdings":     holdings,
                "Approx Value": f"₹{total_val:,.0f}" if total_val else "—",
                "Role":         "Admin" if u.get("is_admin") else "User",
            })

        if rows:
            port_df = pd.DataFrame(rows)
            def _role_color(val):
                return "color:#f59e0b;font-weight:700" if val == "Admin" else "color:#eeeef8"
            def _val_color(val):
                return "color:#00e5a0" if val != "—" else "color:#5a5a78"
            styled = (
                port_df.style
                .map(_role_color, subset=["Role"])
                .map(_val_color,  subset=["Approx Value"])
                .set_properties(**{
                    "background-color": "#09090f",
                    "color": "#eeeef8",
                    "border": "1px solid #1c1c2e",
                })
            )
            st.dataframe(styled, width="stretch", hide_index=True)
        else:
            st.info("No portfolio data found.")
