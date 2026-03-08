"""
agents/test_password.py
────────────────────────
Password policy + update feature — 50 tests.
Run: python agents/test_password.py
"""
import sys, types, ast, traceback
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Mock streamlit & externals ─────────────────────────────────────────
def _mock(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

_st = _mock("streamlit")
_st.session_state  = {}
_st.secrets        = {"supabase": {"url": "https://x.supabase.co", "anon_key": "key"}}
_st.cache_data     = lambda *a, **kw: (lambda f: f)
_st.cache_resource = lambda *a, **kw: (lambda f: f)
for attr in ("error","success","info","warning","spinner","markdown","text_input",
             "button","columns","expander","rerun","stop","caption"):
    setattr(_st, attr, MagicMock())
_st.spinner.__enter__ = lambda s, *a: None
_st.spinner.__exit__  = lambda s, *a: None
_st.expander.__enter__ = lambda s, *a: s
_st.expander.__exit__  = lambda s, *a: None

_mock("supabase"); _mock("yfinance")
_mock("plotly"); _mock("plotly.express"); _mock("plotly.graph_objects")

# ── Harness ────────────────────────────────────────────────────────────
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
test("SYNTAX — auth.py",      lambda: ast.parse((ROOT/"backend/auth.py").read_text()))
test("SYNTAX — auth_page.py", lambda: ast.parse((ROOT/"frontend/auth_page.py").read_text()))
test("SYNTAX — app.py",       lambda: ast.parse((ROOT/"app.py").read_text()))

# ══════════════════════════════════════════════════════════════════════
# SUITE 2 — validate_password
# ══════════════════════════════════════════════════════════════════════
from backend.auth import validate_password

def test_valid_strong():
    ok, fails = validate_password("Secure@99")
    expect(ok, f"Should pass: {fails}")
    expect(len(fails) == 0)

def test_valid_complex():
    ok, fails = validate_password("MyP@ssw0rd!")
    expect(ok, f"Should pass: {fails}")

def test_fail_too_short():
    ok, fails = validate_password("Ab1!")
    expect(not ok)
    expect(any("8" in f for f in fails), f"Missing length rule: {fails}")

def test_fail_no_upper():
    ok, fails = validate_password("secure@99abc")
    expect(not ok)
    expect(any("uppercase" in f.lower() for f in fails), f"Missing upper rule: {fails}")

def test_fail_no_lower():
    ok, fails = validate_password("SECURE@99ABC")
    expect(not ok)
    expect(any("lowercase" in f.lower() for f in fails), f"Missing lower rule: {fails}")

def test_fail_no_digit():
    ok, fails = validate_password("Secure@abcd")
    expect(not ok)
    expect(any("number" in f.lower() or "digit" in f.lower() for f in fails), f"Missing digit rule: {fails}")

def test_fail_no_special():
    ok, fails = validate_password("Secure99abc")
    expect(not ok)
    expect(any("special" in f.lower() for f in fails), f"Missing special rule: {fails}")

def test_fail_all_missing():
    ok, fails = validate_password("abc")
    expect(not ok)
    expect(len(fails) >= 4, f"Should have 4+ failures: {fails}")

def test_exactly_8_chars_passes_other_rules():
    ok, fails = validate_password("Abc@1234")   # exactly 8, all rules met
    expect(ok, f"Should pass: {fails}")

def test_special_chars_variety():
    # All these special chars should work
    for ch in "!@#$%^&*()_+-=[]{}|;:,./<>?":
        ok, fails = validate_password(f"Secure1{ch}")
        expect(ok, f"Char {ch!r} should satisfy special rule: {fails}")

def test_returns_tuple():
    result = validate_password("test")
    expect(isinstance(result, tuple))
    expect(len(result) == 2)
    ok, fails = result
    expect(isinstance(ok, bool))
    expect(isinstance(fails, list))

def test_empty_password_fails():
    ok, fails = validate_password("")
    expect(not ok)
    expect(len(fails) > 0)

def test_valid_returns_empty_list():
    ok, fails = validate_password("ValidP@ss1")
    expect(ok)
    expect(fails == [], f"Fails should be empty: {fails}")

test("VALIDATE — strong password passes",              test_valid_strong)
test("VALIDATE — complex password passes",             test_valid_complex)
test("VALIDATE — rejects < 8 chars",                   test_fail_too_short)
test("VALIDATE — rejects no uppercase",                test_fail_no_upper)
test("VALIDATE — rejects no lowercase",                test_fail_no_lower)
test("VALIDATE — rejects no digit",                    test_fail_no_digit)
test("VALIDATE — rejects no special char",             test_fail_no_special)
test("VALIDATE — rejects when all rules missing",      test_fail_all_missing)
test("VALIDATE — exactly 8 chars with all rules OK",   test_exactly_8_chars_passes_other_rules)
test("VALIDATE — accepts variety of special chars",    test_special_chars_variety)
test("VALIDATE — returns (bool, list) tuple",          test_returns_tuple)
test("VALIDATE — empty password fails",                test_empty_password_fails)
test("VALIDATE — valid returns empty fails list",      test_valid_returns_empty_list)

# ══════════════════════════════════════════════════════════════════════
# SUITE 3 — registration uses new policy
# ══════════════════════════════════════════════════════════════════════

def test_register_rejects_weak_local():
    from backend.auth import _local_register
    ok, msg = _local_register("testuser", "Test User", "t@t.com", "abc123")
    expect(not ok, "Weak password should be rejected")
    expect("weak" in msg.lower() or "password" in msg.lower(), f"Msg: {msg}")

def test_register_rejects_no_special_local():
    from backend.auth import _local_register
    ok, msg = _local_register("testuser", "Test User", "t@t.com", "Secure99abc")
    expect(not ok, "No special char should be rejected")

def test_register_rejects_no_upper_local():
    from backend.auth import _local_register
    ok, msg = _local_register("testuser", "Test User", "t@t.com", "secure@99abc")
    expect(not ok, "No uppercase should be rejected")

def test_register_rejects_no_digit_local():
    from backend.auth import _local_register
    ok, msg = _local_register("testuser", "Test User", "t@t.com", "Secure@abcd")
    expect(not ok, "No digit should be rejected")

def test_register_old_6char_now_fails():
    """Old 'min 6 chars' passwords are now rejected."""
    from backend.auth import _local_register
    ok, msg = _local_register("testuser", "Test User", "t@t.com", "Abc1@x")
    expect(not ok, "6-char password should now fail (min 8 required)")

def test_register_strong_passes_validation():
    """Strong password passes validation check (actual register may fail for other reasons)."""
    ok, fails = validate_password("StrongP@ss1")
    expect(ok, f"Strong password should pass validation: {fails}")

test("REGISTER — rejects weak password (local)",       test_register_rejects_weak_local)
test("REGISTER — rejects no special char (local)",     test_register_rejects_no_special_local)
test("REGISTER — rejects no uppercase (local)",        test_register_rejects_no_upper_local)
test("REGISTER — rejects no digit (local)",            test_register_rejects_no_digit_local)
test("REGISTER — old 6-char passwords now rejected",   test_register_old_6char_now_fails)
test("REGISTER — strong password passes validation",   test_register_strong_passes_validation)

# ══════════════════════════════════════════════════════════════════════
# SUITE 4 — update_password (local mode)
# ══════════════════════════════════════════════════════════════════════

def _make_local_user(username="alice", password="OldP@ss99"):
    from backend import auth as a
    import tempfile, json
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp())
    users = {
        username: {
            "username": username, "name": "Alice", "email": "a@a.com",
            "password_hash": a._hash(password), "is_admin": False, "created_at": "2025-01-01"
        }
    }
    users_file = tmp / "users.json"
    users_file.write_text(json.dumps(users))
    pf_dir = tmp / "portfolios"
    pf_dir.mkdir()
    orig_base = a._BASE
    a._BASE          = tmp
    a._USERS_FILE    = tmp / "users.json"
    a._PORTFOLIO_DIR = pf_dir
    return a, orig_base, tmp

def test_local_update_password_success():
    from backend import auth as a
    a_mod, orig, tmp = _make_local_user()
    try:
        ok, msg = a_mod._local_update_password(
            {"username": "alice"}, "OldP@ss99", "NewP@ss77!"
        )
        expect(ok, f"Should succeed: {msg}")
        expect("success" in msg.lower(), f"Msg: {msg}")
    finally:
        a_mod._BASE = orig; a_mod._USERS_FILE = orig / "users.json"
        a_mod._PORTFOLIO_DIR = orig / "portfolios"

def test_local_update_wrong_current():
    from backend import auth as a
    a_mod, orig, tmp = _make_local_user()
    try:
        ok, msg = a_mod._local_update_password(
            {"username": "alice"}, "WrongPassword1!", "NewP@ss77!"
        )
        expect(not ok, "Wrong current password should fail")
        expect("incorrect" in msg.lower(), f"Msg: {msg}")
    finally:
        a_mod._BASE = orig; a_mod._USERS_FILE = orig / "users.json"
        a_mod._PORTFOLIO_DIR = orig / "portfolios"

def test_local_update_weak_new_password():
    from backend import auth as a
    a_mod, orig, tmp = _make_local_user()
    try:
        ok, msg = a_mod._local_update_password(
            {"username": "alice"}, "OldP@ss99", "weakpass"
        )
        expect(not ok, "Weak new password should fail")
        expect("weak" in msg.lower() or "password" in msg.lower(), f"Msg: {msg}")
    finally:
        a_mod._BASE = orig; a_mod._USERS_FILE = orig / "users.json"
        a_mod._PORTFOLIO_DIR = orig / "portfolios"

def test_local_update_actually_changes_hash():
    from backend import auth as a
    a_mod, orig, tmp = _make_local_user()
    try:
        old_hash = a_mod._hash("OldP@ss99")
        a_mod._local_update_password({"username": "alice"}, "OldP@ss99", "NewP@ss77!")
        users = a_mod._load_users()
        new_hash = users["alice"]["password_hash"]
        expect(new_hash != old_hash, "Hash should change after update")
        expect(new_hash == a_mod._hash("NewP@ss77!"), "New hash should match new password")
    finally:
        a_mod._BASE = orig; a_mod._USERS_FILE = orig / "users.json"
        a_mod._PORTFOLIO_DIR = orig / "portfolios"

def test_local_update_user_not_found():
    from backend import auth as a
    a_mod, orig, tmp = _make_local_user()
    try:
        ok, msg = a_mod._local_update_password(
            {"username": "nobody"}, "OldP@ss99", "NewP@ss77!"
        )
        expect(not ok, "Unknown user should fail")
    finally:
        a_mod._BASE = orig; a_mod._USERS_FILE = orig / "users.json"
        a_mod._PORTFOLIO_DIR = orig / "portfolios"

test("UPDATE_LOCAL — success changes password",         test_local_update_password_success)
test("UPDATE_LOCAL — wrong current password fails",     test_local_update_wrong_current)
test("UPDATE_LOCAL — weak new password rejected",       test_local_update_weak_new_password)
test("UPDATE_LOCAL — hash actually changes in file",    test_local_update_actually_changes_hash)
test("UPDATE_LOCAL — unknown user returns error",       test_local_update_user_not_found)

# ══════════════════════════════════════════════════════════════════════
# SUITE 5 — update_password (Supabase mode)
# ══════════════════════════════════════════════════════════════════════

def _sb_user():
    return {"user_id": "uid-1", "email": "test@test.com", "access_token": "tok-abc"}

def test_sb_update_success():
    from backend.auth import _sb_update_password
    mc = MagicMock()
    mc.auth.sign_in_with_password.return_value = MagicMock(user=MagicMock(id="uid-1"))
    mc.auth.update_user.return_value = MagicMock()
    with patch("backend.auth._get_supabase_client", return_value=mc):
        ok, msg = _sb_update_password(_sb_user(), "OldP@ss99", "NewP@ss77!")
    expect(ok, f"Should succeed: {msg}")
    expect("success" in msg.lower(), f"Msg: {msg}")

def test_sb_update_wrong_current():
    from backend.auth import _sb_update_password
    mc = MagicMock()
    mc.auth.sign_in_with_password.side_effect = Exception("Invalid credentials")
    with patch("backend.auth._get_supabase_client", return_value=mc):
        ok, msg = _sb_update_password(_sb_user(), "WrongPass1!", "NewP@ss77!")
    expect(not ok)
    expect("incorrect" in msg.lower(), f"Msg: {msg}")

def test_sb_update_weak_new():
    from backend.auth import _sb_update_password
    ok, msg = _sb_update_password(_sb_user(), "OldP@ss99", "weak")
    expect(not ok)
    expect("weak" in msg.lower(), f"Msg: {msg}")

def test_sb_update_no_token():
    from backend.auth import _sb_update_password
    user = {"user_id": "uid-1", "email": "test@test.com"}  # no token
    ok, msg = _sb_update_password(user, "OldP@ss99", "NewP@ss77!")
    expect(not ok)
    expect("logged in" in msg.lower() or "token" in msg.lower(), f"Msg: {msg}")

def test_sb_update_verifies_before_changing():
    """Must call sign_in_with_password before update_user."""
    from backend.auth import _sb_update_password
    call_order = []
    mc = MagicMock()
    def mock_signin(*a, **kw):
        call_order.append("signin")
        return MagicMock(user=MagicMock(id="uid"))
    def mock_update(*a, **kw):
        call_order.append("update")
        return MagicMock()
    mc.auth.sign_in_with_password.side_effect = mock_signin
    mc.auth.update_user.side_effect = mock_update
    with patch("backend.auth._get_supabase_client", return_value=mc):
        _sb_update_password(_sb_user(), "OldP@ss99", "NewP@ss77!")
    expect(call_order.index("signin") < call_order.index("update"),
           f"signin must happen before update: {call_order}")

test("UPDATE_SB — success path works",                 test_sb_update_success)
test("UPDATE_SB — wrong current password rejected",    test_sb_update_wrong_current)
test("UPDATE_SB — weak new password rejected",         test_sb_update_weak_new)
test("UPDATE_SB — missing token returns error",        test_sb_update_no_token)
test("UPDATE_SB — verifies current before updating",   test_sb_update_verifies_before_changing)

# ══════════════════════════════════════════════════════════════════════
# SUITE 6 — public API + app wiring
# ══════════════════════════════════════════════════════════════════════

def test_public_update_password_exists():
    from backend.auth import update_password
    expect(callable(update_password))

def test_public_update_password_supabase_mode():
    from backend import auth
    called = []
    def mock_sb(*a): called.append("sb"); return True, "ok"
    with patch("backend.auth._use_supabase", return_value=True):
        with patch("backend.auth._sb_update_password", mock_sb):
            auth.update_password({}, "old", "new")
    expect(called == ["sb"], f"Should call sb version: {called}")

def test_public_update_password_local_mode():
    from backend import auth
    called = []
    def mock_local(*a): called.append("local"); return True, "ok"
    with patch("backend.auth._use_supabase", return_value=False):
        with patch("backend.auth._local_update_password", mock_local):
            auth.update_password({}, "old", "new")
    expect(called == ["local"], f"Should call local version: {called}")

def test_app_imports_update_password():
    src = (ROOT / "app.py").read_text()
    expect("update_password" in src, "app.py must import update_password")

def test_app_has_change_password_expander():
    src = (ROOT / "app.py").read_text()
    expect("Change Password" in src or "change_password" in src.lower(),
           "app.py must have Change Password expander")

def test_app_has_strength_meter():
    src = (ROOT / "app.py").read_text()
    expect("validate_password" in src, "app.py must use validate_password")
    expect("Strength" in src, "app.py must show strength indicator")

def test_auth_page_has_strength_meter():
    src = (ROOT / "frontend/auth_page.py").read_text()
    expect("validate_password" in src, "auth_page.py must use validate_password for strength")
    expect("Strength" in src, "auth_page.py must show strength bar")

def test_auth_page_updated_placeholder():
    src = (ROOT / "frontend/auth_page.py").read_text()
    expect("min 6" not in src.lower(), "Old 'min 6 chars' placeholder should be updated")

def test_app_checks_passwords_match():
    src = (ROOT / "app.py").read_text()
    expect("do not match" in src.lower() or "don't match" in src.lower(),
           "app.py should check if passwords match")

def test_app_checks_different_from_current():
    src = (ROOT / "app.py").read_text()
    expect("different" in src.lower() or "same" in src.lower(),
           "app.py should check new != current")

test("PUBLIC_API — update_password is callable",           test_public_update_password_exists)
test("PUBLIC_API — routes to Supabase in sb mode",         test_public_update_password_supabase_mode)
test("PUBLIC_API — routes to local in local mode",         test_public_update_password_local_mode)
test("APP_WIRING — imports update_password",               test_app_imports_update_password)
test("APP_WIRING — has Change Password expander",          test_app_has_change_password_expander)
test("APP_WIRING — has live strength meter",               test_app_has_strength_meter)
test("APP_WIRING — auth_page has strength meter",          test_auth_page_has_strength_meter)
test("APP_WIRING — placeholder updated from min 6",        test_auth_page_updated_placeholder)
test("APP_WIRING — checks passwords match",                test_app_checks_passwords_match)
test("APP_WIRING — checks new != current",                 test_app_checks_different_from_current)

# ══════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════
W = 66
print("\n" + "="*W)
print("  PASSWORD TEST AGENT — RESULTS")
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
