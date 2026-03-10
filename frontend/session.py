"""
frontend/session.py
─────────────────────────────────────────────────────────────────────
Shared session state helpers used by every page.
All pages import from here to guarantee consistent key names.
"""

import streamlit as st


# ── Keys ───────────────────────────────────────────────────────────────────────
AUTH_KEY       = "authenticated"
USER_KEY       = "user_info"
PORTFOLIO_KEY  = "portfolio"
DATA_KEY       = "data"
FROM_D_KEY     = "from_d"
TO_D_KEY       = "to_d"
INDEX_KEY      = "selected_index"
DB_READY_KEY   = "db_ready"
LAST_PAGE_KEY  = "last_page"
NOTIF_KEY      = "notifications"


def is_authenticated() -> bool:
    return bool(st.session_state.get(AUTH_KEY))


def get_user() -> dict:
    return st.session_state.get(USER_KEY, {})


def get_portfolio() -> dict:
    return st.session_state.get(PORTFOLIO_KEY, {})


def get_data() -> list | None:
    return st.session_state.get(DATA_KEY)


def get_index() -> str:
    return st.session_state.get(INDEX_KEY, "Nifty 50")


def set_data(data: list, from_d, to_d) -> None:
    st.session_state[DATA_KEY]  = data
    st.session_state[FROM_D_KEY] = from_d
    st.session_state[TO_D_KEY]   = to_d


def clear_analysis() -> None:
    for k in [DATA_KEY, FROM_D_KEY, TO_D_KEY, "bt_result", "corr_result"]:
        st.session_state.pop(k, None)


def add_notification(msg: str, kind: str = "info") -> None:
    """kind: 'success' | 'error' | 'info' | 'warning'"""
    notifs = st.session_state.get(NOTIF_KEY, [])
    notifs.append({"msg": msg, "kind": kind})
    st.session_state[NOTIF_KEY] = notifs


def pop_notifications() -> list:
    notifs = st.session_state.pop(NOTIF_KEY, [])
    return notifs


def init_defaults() -> None:
    """Call once per page to ensure all keys exist."""
    defaults = {
        AUTH_KEY:      False,
        USER_KEY:      {},
        PORTFOLIO_KEY: {},
        DATA_KEY:      None,
        FROM_D_KEY:    None,
        TO_D_KEY:      None,
        INDEX_KEY:     "Nifty 50",
        DB_READY_KEY:  False,
        NOTIF_KEY:     [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
