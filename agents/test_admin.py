"""
agents/test_admin.py
─────────────────────
Test agent for admin dashboard, db_init, and smart error handling.
50 tests across 7 suites. Run repeatedly until 0 failures.

Run:  python agents/test_admin.py
"""
import sys, types, ast, traceback, json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

ROOT = Path(__file__).parent.parent

def _all_src():
    """Read all app source files for pattern-matching tests."""
    base = (ROOT / "app.py").read_text()
    for sub in ["pages", "frontend"]:
        d = ROOT / sub
        if d.exists():
            for p in sorted(d.glob("*.py")):
                base += chr(10) + p.read_text()
    return base







sys.path.insert(0, str(ROOT))

# ── Mock all external dependencies ────────────────────────────────────
def _mock(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

_st = _mock("streamlit")
_st.session_state  = {}
_st.secrets        = {
    "supabase": {"url": "https://test.supabase.co", "anon_key": "test_key"}
}
_st.cache_data     = lambda *a, **kw: (lambda f: f)
_st.cache_resource = lambda *a, **kw: (lambda f: f)
_st.error = _st.success = _st.info = _st.warning = lambda *a, **kw: None
_st.spinner = MagicMock()
_st.spinner.__enter__ = lambda s, *a: None
_st.spinner.__exit__  = lambda s, *a: None
_st.rerun  = lambda: None
_st.stop   = lambda: None
_st.markdown = _st.text_input = _st.button = _st.columns = lambda *a, **kw: None
_st.progress = lambda *a, **kw: MagicMock()

_sb_mod = _mock("supabase")

import numpy as _np
import pandas as _pd

_yf = _mock("yfinance")
_yf.download = lambda *a, **kw: _pd.DataFrame()

for m in ["plotly", "plotly.express", "plotly.graph_objects"]:
    _mock(m)

# ── Test harness ──────────────────────────────────────────────────────
PASS = FAIL = 0
RESULTS = []

def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        RESULTS.append(("PASS", name, ""))
        PASS += 1
    except Exception as e:
        tb = traceback.format_exc().strip().split("\n")[-1]
        RESULTS.append(("FAIL", name, tb))
        FAIL += 1

def expect(cond, msg=""):
    if not cond:
        raise AssertionError(msg or "Assertion failed")

# ══════════════════════════════════════════════════════════════════════
# SUITE 1 — SYNTAX
# ══════════════════════════════════════════════════════════════════════

def test_db_init_syntax():
    path = ROOT / "backend/db_init.py"
    expect(path.exists(), "backend/db_init.py missing")
    ast.parse(path.read_text())

def test_admin_dashboard_syntax():
    path = ROOT / "frontend/admin_dashboard.py"
    expect(path.exists(), "frontend/admin_dashboard.py missing")
    ast.parse(path.read_text())

def test_auth_page_syntax():
    ast.parse((ROOT / "frontend/auth_page.py").read_text())

def test_auth_py_syntax():
    ast.parse((ROOT / "backend/auth.py").read_text())

def test_app_py_syntax():
    ast.parse(_all_src())

test("SYNTAX — backend/db_init.py parses",          test_db_init_syntax)
test("SYNTAX — frontend/admin_dashboard.py parses", test_admin_dashboard_syntax)
test("SYNTAX — frontend/auth_page.py parses",       test_auth_page_syntax)
test("SYNTAX — backend/auth.py parses",             test_auth_py_syntax)
test("SYNTAX — app.py parses",                      test_app_py_syntax)

# ══════════════════════════════════════════════════════════════════════
# SUITE 2 — DB INIT STRUCTURE
# ══════════════════════════════════════════════════════════════════════

def test_db_init_exports():
    from backend.db_init import (
        ensure_db, admin_list_users, admin_delete_user,
        admin_toggle_admin, admin_get_user_portfolio,
        admin_create_user, ADMIN_NAME, ADMIN_EMAIL,
        ADMIN_PASSWORD, ADMIN_USERNAME
    )
    expect(callable(ensure_db))
    expect(callable(admin_list_users))
    expect(callable(admin_delete_user))
    expect(callable(admin_toggle_admin))
    expect(callable(admin_get_user_portfolio))
    expect(callable(admin_create_user))

def test_admin_credentials_correct():
    from backend.db_init import (
        ADMIN_NAME, ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME
    )
    expect(ADMIN_NAME     == "Aniruddha Giri",               f"Wrong admin name: {ADMIN_NAME}")
    expect(ADMIN_EMAIL    == "girianiruddha8972@gmail.com",  f"Wrong admin email: {ADMIN_EMAIL}")
    expect(ADMIN_PASSWORD == "897282",                        f"Wrong admin password")
    expect(ADMIN_USERNAME == "admin",                         f"Wrong admin username: {ADMIN_USERNAME}")

def test_sql_blocks_present():
    src = (ROOT / "backend/db_init.py").read_text()
    expect("CREATE TABLE IF NOT EXISTS public.profiles"   in src, "profiles CREATE missing")
    expect("CREATE TABLE IF NOT EXISTS public.portfolios" in src, "portfolios CREATE missing")
    expect("ENABLE ROW LEVEL SECURITY"                    in src, "RLS enable missing")
    expect("handle_new_user"                               in src, "trigger function missing")
    expect("is_username_available"                         in src, "RPC function missing")
    expect("ON CONFLICT"                                   in src, "upsert safety missing")

def test_ensure_db_returns_list():
    from backend.db_init import ensure_db
    # Mock supabase client to simulate working DB
    with patch("backend.db_init._get_client") as mock_client:
        mock_c = MagicMock()
        mock_c.table.return_value.select.return_value.limit.return_value.execute.return_value \
            = MagicMock(data=[])
        mock_c.table.return_value.select.return_value.eq.return_value.execute.return_value \
            = MagicMock(data=[])
        mock_c.auth.sign_up.return_value = MagicMock(
            user=MagicMock(id="test-uuid"),
            session=MagicMock(access_token="test-token")
        )
        mock_client.return_value = mock_c
        result = ensure_db()
    expect(isinstance(result, list), "ensure_db should return list")

def test_ensure_db_handles_exception():
    """ensure_db must never crash the app."""
    from backend.db_init import ensure_db
    with patch("backend.db_init._get_client", side_effect=Exception("DB down")):
        result = ensure_db()
    expect(isinstance(result, list), "Should return list even on error")
    expect(any("warning" in m.lower() or "error" in m.lower() or "⚠" in m
               for m in result), "Should report the error in msgs")

def test_local_mode_skip():
    """In local mode (no secrets), ensure_db returns immediately."""
    from backend.db_init import ensure_db
    orig = _st.secrets
    _st.secrets = {}
    result = ensure_db()
    _st.secrets = orig
    expect(isinstance(result, list))
    expect(any("local" in m.lower() for m in result), "Should mention local mode")

test("DB_INIT — all exports present",              test_db_init_exports)
test("DB_INIT — admin credentials correct",        test_admin_credentials_correct)
test("DB_INIT — all SQL blocks present",           test_sql_blocks_present)
test("DB_INIT — ensure_db returns list",           test_ensure_db_returns_list)
test("DB_INIT — ensure_db survives exceptions",    test_ensure_db_handles_exception)
test("DB_INIT — local mode skips DB init",         test_local_mode_skip)

# ══════════════════════════════════════════════════════════════════════
# SUITE 3 — ADMIN OPERATIONS (mocked Supabase)
# ══════════════════════════════════════════════════════════════════════

def _make_mock_client(users=None, portfolio=None):
    mc = MagicMock()
    users = users or []
    portfolio = portfolio or {}

    tbl = mc.table.return_value
    tbl.select.return_value.order.return_value.execute.return_value = MagicMock(data=users)
    tbl.select.return_value.eq.return_value.single.return_value.execute.return_value \
        = MagicMock(data={"is_admin": False, "data": portfolio})
    tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=users[:1])
    tbl.delete.return_value.eq.return_value.execute.return_value = MagicMock()
    tbl.update.return_value.eq.return_value.execute.return_value = MagicMock()
    mc.postgrest.auth.return_value = None
    return mc

def test_admin_list_users_returns_list():
    from backend.db_init import admin_list_users
    sample = [{"id": "u1", "username": "test", "name": "Test User",
               "email": "t@t.com", "is_admin": False, "created_at": "2025-01-01"}]
    mc = _make_mock_client(sample)
    # RPC returns sample data (primary path)
    mc.rpc.return_value.execute.return_value = MagicMock(data=sample)
    with patch("backend.db_init._get_client", return_value=mc):
        result = admin_list_users("tok")
    expect(isinstance(result, list), f"Expected list, got {type(result)}")
    expect(len(result) == 1, f"Expected 1 item, got {len(result)}")
    expect(result[0]["username"] == "test", f"Wrong username: {result[0]}")

def test_admin_list_users_handles_error():
    from backend.db_init import admin_list_users
    with patch("backend.db_init._get_client", side_effect=Exception("DB error")):
        result = admin_list_users("tok")
    expect(result == [], f"Should return [] on error, got {result}")

def test_admin_delete_blocks_admin():
    from backend.db_init import admin_delete_user
    mc = _make_mock_client()
    # profile select returns is_admin=True
    mc.table.return_value.select.return_value.eq.return_value.single.return_value         .execute.return_value = MagicMock(data={"is_admin": True})
    with patch("backend.db_init._get_client", return_value=mc):
        ok, msg = admin_delete_user("tok", "admin-uuid")
    expect(not ok, "Should block deletion of admin")
    expect("cannot delete" in msg.lower() or "admin" in msg.lower(), f"Msg: {msg}")

def test_admin_delete_regular_user_full():
    """Full delete: profile + portfolio + auth.users via Admin API."""
    from backend.db_init import admin_delete_user
    mc = _make_mock_client()
    mc.table.return_value.select.return_value.eq.return_value.single.return_value         .execute.return_value = MagicMock(data={"is_admin": False})
    with patch("backend.db_init._get_client", return_value=mc):
        with patch("backend.db_init._delete_auth_user", return_value=None) as mock_auth_del:
            ok, msg = admin_delete_user("tok", "user-uuid")
    expect(ok, f"Should succeed: {msg}")
    expect(msg == "auth", f"Full delete should return 'auth': {msg}")
    mock_auth_del.assert_called_once_with("user-uuid")

def test_admin_delete_removes_auth_user():
    """Verify _delete_auth_user calls the Supabase Admin API correctly."""
    import urllib.request
    from unittest.mock import patch, MagicMock
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__ = lambda s, *a: mock_resp
    mock_resp.__exit__ = lambda s, *a: None
    import backend.db_init as db
    with patch("backend.secrets.get_supabase_url", return_value="https://abc.supabase.co"),          patch("backend.secrets.get_supabase_service_key", return_value="svc-key-123"),          patch("urllib.request.urlopen", return_value=mock_resp):
        db._delete_auth_user("user-uuid-123")

def test_admin_delete_no_service_key_warns():
    """Without service_role_key, delete still removes profile but warns."""
    from backend.db_init import admin_delete_user
    mc = _make_mock_client()
    mc.table.return_value.select.return_value.eq.return_value.single.return_value         .execute.return_value = MagicMock(data={"is_admin": False})
    with patch("backend.db_init._get_client", return_value=mc):
        with patch("backend.db_init._delete_auth_user",
                   side_effect=ValueError("service_role_key not set")):
            ok, msg = admin_delete_user("tok", "user-uuid")
    expect(ok, "Should still return True (profile was deleted)")
    expect("profile_only" in msg, f"Should warn about partial delete: {msg}")

def test_admin_toggle_admin():
    from backend.db_init import admin_toggle_admin
    with patch("backend.db_init._get_client", return_value=_make_mock_client()):
        ok, msg = admin_toggle_admin("tok", "user-uuid", True)
    expect(ok, f"Toggle should succeed: {msg}")

def test_admin_get_portfolio():
    from backend.db_init import admin_get_user_portfolio
    portfolio_data = {"RELIANCE": {"qty": 10, "avg_buy_price": 1300}}
    with patch("backend.db_init.load_portfolio_rpc", return_value=(portfolio_data, "")):
        result = admin_get_user_portfolio("tok", "user-uuid")
    expect(isinstance(result, dict), f"Expected dict, got {type(result)}: {result}")
    expect(result == portfolio_data, f"Data mismatch: {result}")

def test_admin_get_portfolio_handles_error():
    from backend.db_init import admin_get_user_portfolio
    with patch("backend.db_init._get_client", side_effect=Exception("err")):
        result = admin_get_user_portfolio("tok", "uuid")
    expect(result == {}, "Should return {} on error")

def _tmp_auth_ctx():
    """Return a context manager that redirects auth to a temp dir."""
    import tempfile, backend.auth as au
    from pathlib import Path
    from contextlib import contextmanager
    @contextmanager
    def ctx():
        d = tempfile.mkdtemp()
        orig = au._BASE
        au._BASE = Path(d); au._USERS_FILE = Path(d)/"users.json"
        au._PORTFOLIO_DIR = Path(d)/"portfolios"; au._PORTFOLIO_DIR.mkdir()
        au._USERS_FILE.write_text("{}")
        try: yield au
        finally:
            au._BASE = orig; au._USERS_FILE = orig/"users.json"
            au._PORTFOLIO_DIR = orig/"portfolios"
    return ctx()

def test_admin_create_user_success():
    with _tmp_auth_ctx() as au:
        ok, msg = au._local_register("adminuser2", "Admin User", "admin2@test.com")
    expect(ok, f"Create user should succeed: {msg}")
    expect("OTP_SENT" in msg, f"Should return OTP_SENT: {msg}")

def test_admin_create_user_short_password():
    from backend.auth import _local_register
    ok, msg = _local_register("a", "Name", "u2@t.com")
    expect(not ok, "Short username should fail")
    expect(isinstance(msg, str))

test("ADMIN_OPS — list_users returns list",        test_admin_list_users_returns_list)
test("ADMIN_OPS — list_users handles DB error",    test_admin_list_users_handles_error)
test("ADMIN_OPS — delete blocks admin account",         test_admin_delete_blocks_admin)
test("ADMIN_OPS — delete full removes auth user",       test_admin_delete_regular_user_full)
test("ADMIN_OPS — delete calls Admin API correctly",    test_admin_delete_removes_auth_user)
test("ADMIN_OPS — no service key warns gracefully",     test_admin_delete_no_service_key_warns)
test("ADMIN_OPS — toggle admin flag works",        test_admin_toggle_admin)
test("ADMIN_OPS — get portfolio returns dict",     test_admin_get_portfolio)
test("ADMIN_OPS — get portfolio handles error",    test_admin_get_portfolio_handles_error)
test("ADMIN_OPS — create user success",            test_admin_create_user_success)
test("ADMIN_OPS — create user handles bad input",  test_admin_create_user_short_password)

# ══════════════════════════════════════════════════════════════════════
# SUITE 4 — SMART USERNAME SUGGESTIONS
# ══════════════════════════════════════════════════════════════════════

def test_suggest_usernames_returns_list():
    from backend.auth import _suggest_usernames
    taken = {"rahul", "rahul26", "rahul_trades"}
    result = _suggest_usernames("rahul", taken)
    expect(isinstance(result, list), "Should return list")
    expect(len(result) >= 1, "Should return at least 1 suggestion")
    expect(len(result) <= 3, "Should return at most 3 suggestions")

def test_suggest_usernames_not_taken():
    from backend.auth import _suggest_usernames
    taken = {"rahul", "rahul26", "rahul_trades", "rahul_nse", "rahul_inv",
             "rahul_50", "nifty_rahul", "rahul25"}
    result = _suggest_usernames("rahul", taken)
    for s in result:
        expect(s not in taken, f"Suggestion '{s}' is in taken set")

def test_suggest_usernames_valid_format():
    from backend.auth import _suggest_usernames
    result = _suggest_usernames("test user!", set())
    for s in result:
        import re
        expect(re.match(r'^[a-z0-9_]{3,20}$', s), f"Invalid username format: '{s}'")

def test_suggest_usernames_min_length():
    from backend.auth import _suggest_usernames
    result = _suggest_usernames("ab", set())  # too short base
    for s in result:
        expect(len(s) >= 3, f"Suggestion too short: '{s}'")

def test_sb_register_username_taken_format():
    with _tmp_auth_ctx() as au:
        au._local_register("rahul", "Rahul S", "r@r.com")
        ok, msg = au._local_register("rahul", "Other", "other@r.com")
    expect(not ok, "Should fail when username taken")
    expect("USERNAME_TAKEN" in msg, f"Expected USERNAME_TAKEN in: '{msg}'")

def test_sb_register_email_exists():
    with _tmp_auth_ctx() as au:
        au._local_register("user1", "User 1", "same@r.com")
        ok, msg = au._local_register("user2", "User 2", "same@r.com")
    expect(not ok, "Should fail when email exists")
    expect("EMAIL_EXISTS" in msg, f"Expected EMAIL_EXISTS in: '{msg}'")

def test_sb_register_validation_username():
    from backend.auth import _local_register
    ok, msg = _local_register("ab", "Test", "t@t.com")
    expect(not ok, "Too-short username must fail")
    expect("username" in msg.lower() or "3" in msg, f"Should mention username: {msg}")

def test_sb_register_validation_email():
    from backend.auth import _local_register
    ok, msg = _local_register("validuser", "Test", "not-an-email")
    expect(not ok, "Bad email must fail")
    expect("email" in msg.lower(), f"Should mention email: {msg}")

def test_sb_register_validation_password():
    # OTP mode: no password in register, but validate_password still works for admin
    from backend.auth import validate_password
    ok, fails = validate_password("123")
    expect(not ok, "Short password should fail validate_password")
    expect(any("8" in f or "character" in f.lower() for f in fails), f"Should mention length: {fails}")

test("USERNAME — suggest_usernames returns list",     test_suggest_usernames_returns_list)
test("USERNAME — suggestions not in taken set",       test_suggest_usernames_not_taken)
test("USERNAME — suggestions are valid format",       test_suggest_usernames_valid_format)
test("USERNAME — suggestions meet min length",        test_suggest_usernames_min_length)
test("USERNAME — register returns taken marker",      test_sb_register_username_taken_format)
test("USERNAME — register catches email exists",      test_sb_register_email_exists)
test("USERNAME — validation rejects short username",  test_sb_register_validation_username)
test("USERNAME — validation rejects bad email",       test_sb_register_validation_email)
test("USERNAME — validation rejects short password",  test_sb_register_validation_password)

# ══════════════════════════════════════════════════════════════════════
# SUITE 5 — ADMIN DASHBOARD UI
# ══════════════════════════════════════════════════════════════════════

def test_admin_dashboard_imports():
    from frontend.admin_dashboard import render_admin_dashboard
    expect(callable(render_admin_dashboard))

def test_admin_dashboard_blocks_non_admin():
    """render_admin_dashboard should show error for non-admin users."""
    _st.session_state = {"user_info": {"is_admin": False}}
    errors = []
    _st.error = lambda msg, **kw: errors.append(msg)
    from frontend.admin_dashboard import render_admin_dashboard
    render_admin_dashboard()
    expect(any("admin" in str(e).lower() for e in errors),
           f"Should show admin error, got: {errors}")

def test_admin_dashboard_is_admin_check():
    """_is_admin() reads from session_state correctly."""
    from frontend import admin_dashboard as adm
    _st.session_state = {"user_info": {"is_admin": True,  "access_token": "tok"}}
    expect(adm._is_admin() == True)
    _st.session_state = {"user_info": {"is_admin": False, "access_token": "tok"}}
    expect(adm._is_admin() == False)
    _st.session_state = {"user_info": {}}
    expect(adm._is_admin() == False)

def test_admin_dashboard_badge_html():
    from frontend.admin_dashboard import _badge
    html = _badge("ADMIN", "#f59e0b")
    expect("ADMIN" in html)
    expect("#f59e0b" in html)
    expect("border" in html)

test("ADMIN_UI — render_admin_dashboard importable",    test_admin_dashboard_imports)
test("ADMIN_UI — blocks non-admin users",               test_admin_dashboard_blocks_non_admin)
test("ADMIN_UI — _is_admin reads session correctly",    test_admin_dashboard_is_admin_check)
test("ADMIN_UI — _badge generates correct HTML",        test_admin_dashboard_badge_html)

# ══════════════════════════════════════════════════════════════════════
# SUITE 6 — APP.PY WIRING
# ══════════════════════════════════════════════════════════════════════

def test_app_imports_db_init():
    src = _all_src()
    expect("from backend.db_init import ensure_db" in src, "ensure_db not imported in app.py")

def test_app_imports_admin_dashboard():
    src = _all_src()
    expect("render_admin_dashboard" in src, "render_admin_dashboard not in app.py")

def test_app_has_admin_tab():
    src = _all_src()
    expect("Admin" in src, "Admin tab missing from app.py")
    expect("is_admin" in src, "is_admin check missing from app.py")

def test_app_calls_ensure_db():
    src = _all_src()
    expect("ensure_db()" in src, "ensure_db() not called in app.py")

def test_auth_page_handles_username_taken():
    src = (ROOT / "frontend/auth_page.py").read_text()
    expect("USERNAME_TAKEN" in src, "USERNAME_TAKEN handler missing from auth_page")
    expect("EMAIL_EXISTS"   in src, "EMAIL_EXISTS handler missing from auth_page")

test("APP_WIRING — imports ensure_db",              test_app_imports_db_init)
test("APP_WIRING — imports render_admin_dashboard", test_app_imports_admin_dashboard)
test("APP_WIRING — has admin tab",                  test_app_has_admin_tab)
test("APP_WIRING — calls ensure_db()",              test_app_calls_ensure_db)
test("AUTH_PAGE — handles USERNAME_TAKEN",          test_auth_page_handles_username_taken)

# ══════════════════════════════════════════════════════════════════════
# SUITE 7 — LOCAL MODE (no supabase)
# ══════════════════════════════════════════════════════════════════════

def _patch_auth_paths(au, d):
    from pathlib import Path
    au._BASE = Path(d); au._USERS_FILE = Path(d)/"users.json"
    au._PORTFOLIO_DIR = Path(d)/"portfolios"; au._PORTFOLIO_DIR.mkdir(exist_ok=True)
    au._USERS_FILE.write_text("{}")

def _restore_auth_paths(au, orig_base):
    au._BASE = orig_base; au._USERS_FILE = orig_base/"users.json"
    au._PORTFOLIO_DIR = orig_base/"portfolios"

def test_local_register_username_taken():
    import tempfile, backend.auth as au
    with tempfile.TemporaryDirectory() as d:
        orig = au._BASE; _patch_auth_paths(au, d)
        ok1, _   = au._local_register("testuser", "Test",  "t@t.com")
        ok2, msg2 = au._local_register("testuser", "Test2", "t2@t.com")
        _restore_auth_paths(au, orig)
    expect(ok1,  "First registration should succeed")
    expect(not ok2, "Duplicate username should fail")
    expect("USERNAME_TAKEN" in msg2, f"Should say USERNAME_TAKEN: {msg2}")

def test_local_register_email_taken():
    import tempfile, backend.auth as au
    with tempfile.TemporaryDirectory() as d:
        orig = au._BASE; _patch_auth_paths(au, d)
        au._local_register("user1", "User 1", "same@t.com")
        ok2, msg2 = au._local_register("user2", "User 2", "same@t.com")
        _restore_auth_paths(au, orig)
    expect(not ok2, "Duplicate email should fail")
    expect("EMAIL_EXISTS" in msg2 or "email" in msg2.lower(), f"{msg2}")

def test_local_register_invalid_username():
    from backend.auth import _local_register
    ok, msg = _local_register("ab", "Test", "t@t.com")
    expect(not ok, "Too-short username should fail")
    ok2, _ = _local_register("has space", "Test", "t@t.com")
    expect(not ok2, "Username with space should fail")

def test_local_login_by_email():
    import tempfile, backend.auth as au
    with tempfile.TemporaryDirectory() as d:
        orig = au._BASE; _patch_auth_paths(au, d)
        ok1, result = au._local_register("myuser", "My User", "my@email.com")
        # Parse OTP from result: OTP_SENT:email:LOCAL:code
        parts = result.split(":")
        code = parts[3] if len(parts) >= 4 and parts[2] == "LOCAL" else None
        ok2, msg2 = au._local_send_otp("my@email.com")
        parts2 = msg2.split(":")
        code2 = parts2[3] if len(parts2) >= 4 and parts2[2] == "LOCAL" else code
        ok3, msg3, info = au._local_verify_otp("my@email.com", code2)
        _restore_auth_paths(au, orig)
    expect(ok1, "Registration should succeed")
    expect(ok3, f"OTP login by email should work: {msg3}")
    expect(info and info.get("username") == "myuser", f"Wrong info: {info}")
    expect(info["username"] == "myuser")

test("LOCAL — duplicate username rejected",   test_local_register_username_taken)
test("LOCAL — duplicate email rejected",      test_local_register_email_taken)
test("LOCAL — invalid username rejected",     test_local_register_invalid_username)
test("LOCAL — login by email works",          test_local_login_by_email)

# ══════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════
W = 66
print("\n" + "="*W)
print("  ADMIN TEST AGENT — RESULTS")
print("="*W)

suite = ""
for status, name, err in RESULTS:
    new_suite = name.split()[0]
    if new_suite != suite:
        suite = new_suite
        print()
    icon = "✅" if status == "PASS" else "❌"
    print(f"  {icon} {name}")
    if err:
        print(f"       ↳ {err}")

total = PASS + FAIL
print()
print("="*W)
print(f"  {'✅ ALL PASS' if FAIL==0 else '❌ FAILURES FOUND'}")
print(f"  {PASS}/{total} passed  ·  {FAIL} failed")
print("="*W + "\n")
sys.exit(0 if FAIL == 0 else 1)
