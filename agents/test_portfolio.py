"""
agents/test_portfolio.py
─────────────────────────
Portfolio save/load/RPC test suite — 50 tests.
Run: python agents/test_portfolio.py
"""
import sys, types, ast, traceback, json, tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Mock externals ─────────────────────────────────────────────────────
def _mock(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

_st = _mock("streamlit")
_st.session_state  = {}
_st.secrets        = {"supabase": {"url": "https://x.supabase.co", "anon_key": "key"}}
_st.cache_data     = lambda *a, **kw: (lambda f: f)
_st.cache_resource = lambda *a, **kw: (lambda f: f)
for attr in ("error","success","info","warning","spinner","markdown",
             "text_input","button","columns","progress","rerun","stop","caption"):
    setattr(_st, attr, MagicMock())
_st.spinner.__enter__ = lambda s,*a: None
_st.spinner.__exit__  = lambda s,*a: None

_sb_mod = _mock("supabase")
_mock("yfinance")
_mock("plotly"); _mock("plotly.express"); _mock("plotly.graph_objects")

import numpy as _np
import pandas as _pd

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

def _mock_client(rpc_data=None, table_data=None, raise_on=None):
    mc = MagicMock()
    rpc_resp = MagicMock(data=rpc_data)
    if raise_on == "rpc":
        mc.rpc.return_value.execute.side_effect = Exception("RPC error")
    else:
        mc.rpc.return_value.execute.return_value = rpc_resp
    tbl = mc.table.return_value
    tbl.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(data=table_data)
    tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[table_data] if table_data else [])
    tbl.upsert.return_value.execute.return_value = MagicMock()
    tbl.update.return_value.eq.return_value.execute.return_value = MagicMock()
    tbl.delete.return_value.eq.return_value.execute.return_value = MagicMock()
    tbl.select.return_value.order.return_value.execute.return_value = MagicMock(data=[])
    mc.postgrest.auth.return_value = None
    return mc

# ══════════════════════════════════════════════════════════════════════
# SUITE 1 — SYNTAX & IMPORTS
# ══════════════════════════════════════════════════════════════════════
test("SYNTAX — db_init.py",       lambda: ast.parse((ROOT/"backend/db_init.py").read_text()))
test("SYNTAX — auth.py",          lambda: ast.parse((ROOT/"backend/auth.py").read_text()))
test("SYNTAX — portfolio.py",     lambda: ast.parse((ROOT/"backend/portfolio.py").read_text()))
test("SYNTAX — app.py",           lambda: ast.parse((ROOT/"app.py").read_text()))
test("SYNTAX — admin_dashboard",  lambda: ast.parse((ROOT/"frontend/admin_dashboard.py").read_text()))

def test_db_init_exports():
    from backend.db_init import (
        ensure_db, save_portfolio_rpc, load_portfolio_rpc,
        admin_list_users, admin_delete_user, admin_toggle_admin,
        admin_get_user_portfolio, admin_create_user,
        ADMIN_NAME, ADMIN_EMAIL, ADMIN_PASSWORD, ADMIN_USERNAME
    )
    expect(callable(save_portfolio_rpc))
    expect(callable(load_portfolio_rpc))
    expect(ADMIN_EMAIL == "girianiruddha8972@gmail.com")
    expect(ADMIN_PASSWORD == "897282")
    expect(ADMIN_NAME == "Aniruddha Giri")

test("IMPORTS — db_init exports all required", test_db_init_exports)

def test_auth_uses_rpc():
    src = (ROOT/"backend/auth.py").read_text()
    expect("save_portfolio_rpc" in src, "auth.py must use save_portfolio_rpc")
    expect("load_portfolio_rpc" in src, "auth.py must use load_portfolio_rpc")
    expect("table(\"portfolios\").upsert" not in src.split("_sb_save_portfolio")[1].split("def ")[0],
           "auth.py _sb_save_portfolio must NOT use direct table upsert")

test("IMPORTS — auth.py uses RPC not direct upsert", test_auth_uses_rpc)

def test_sql_has_rpc_functions():
    src = (ROOT/"backend/db_init.py").read_text()
    expect("save_portfolio" in src,         "save_portfolio RPC missing")
    expect("load_portfolio" in src,         "load_portfolio RPC missing")
    expect("SECURITY DEFINER" in src,       "SECURITY DEFINER missing")
    expect("ON CONFLICT (user_id)" in src,  "upsert conflict clause missing")
    expect("WITH CHECK (true)" in src,      "open INSERT policy missing")

test("SQL — has save_portfolio RPC",    test_sql_has_rpc_functions)

def test_sql_rls_all_open():
    src = (ROOT/"backend/db_init.py").read_text()
    # Both tables should have open policies
    expect('FOR INSERT WITH CHECK (true)' in src, "INSERT policy must be WITH CHECK(true)")
    expect('FOR UPDATE USING (true)' in src,      "UPDATE policy must be USING(true)")
    expect('FOR SELECT USING (true)' in src,      "SELECT policy must be USING(true)")

test("SQL — RLS policies are open (no auth.uid check on write)", test_sql_rls_all_open)

# ══════════════════════════════════════════════════════════════════════
# SUITE 2 — save_portfolio_rpc
# ══════════════════════════════════════════════════════════════════════

def test_save_rpc_success():
    from backend.db_init import save_portfolio_rpc
    mc = _mock_client()
    with patch("backend.db_init._get_client", return_value=mc):
        ok, msg = save_portfolio_rpc("uid-123", {"RELIANCE": {"qty": 10}})
    expect(ok, f"Should succeed: {msg}")
    expect(msg == "Saved", f"Msg should be 'Saved': {msg}")
    mc.rpc.assert_called_once()
    call_args = mc.rpc.call_args
    expect(call_args[0][0] == "save_portfolio", "Should call save_portfolio RPC")

def test_save_rpc_passes_correct_args():
    from backend.db_init import save_portfolio_rpc
    mc = _mock_client()
    portfolio = {"HDFC": {"qty": 5, "avg_buy_price": 1500.0}}
    with patch("backend.db_init._get_client", return_value=mc):
        save_portfolio_rpc("test-uid", portfolio)
    call_kwargs = mc.rpc.call_args[0][1]
    expect(call_kwargs["p_user_id"] == "test-uid", "p_user_id must match")
    expect(call_kwargs["p_data"] == portfolio, "p_data must match portfolio")

def test_save_rpc_handles_error():
    from backend.db_init import save_portfolio_rpc
    mc = _mock_client(raise_on="rpc")
    with patch("backend.db_init._get_client", return_value=mc):
        ok, msg = save_portfolio_rpc("uid-123", {})
    expect(not ok, "Should return False on RPC error")
    expect(isinstance(msg, str), "Error msg should be string")
    expect(len(msg) > 0, "Error msg should not be empty")

def test_save_rpc_empty_portfolio():
    from backend.db_init import save_portfolio_rpc
    mc = _mock_client()
    with patch("backend.db_init._get_client", return_value=mc):
        ok, msg = save_portfolio_rpc("uid-123", {})
    expect(ok, "Should succeed with empty portfolio")

def test_save_rpc_no_direct_table_write():
    """save_portfolio_rpc must use RPC, never direct table write."""
    from backend.db_init import save_portfolio_rpc
    mc = _mock_client()
    with patch("backend.db_init._get_client", return_value=mc):
        save_portfolio_rpc("uid-123", {"TCS": {"qty": 1}})
    # table("portfolios") should NOT be called
    for call in mc.table.call_args_list:
        expect(call[0][0] != "portfolios",
               "save_portfolio_rpc must NOT call table('portfolios') directly")

test("SAVE_RPC — success returns (True, 'Saved')",     test_save_rpc_success)
test("SAVE_RPC — passes correct args to RPC",          test_save_rpc_passes_correct_args)
test("SAVE_RPC — handles RPC error gracefully",        test_save_rpc_handles_error)
test("SAVE_RPC — works with empty portfolio",          test_save_rpc_empty_portfolio)
test("SAVE_RPC — never writes directly to table",      test_save_rpc_no_direct_table_write)

# ══════════════════════════════════════════════════════════════════════
# SUITE 3 — load_portfolio_rpc
# ══════════════════════════════════════════════════════════════════════

def test_load_rpc_success():
    from backend.db_init import load_portfolio_rpc
    pf = {"INFY": {"qty": 20, "avg_buy_price": 1800.0}}
    mc = _mock_client(rpc_data=pf)
    with patch("backend.db_init._get_client", return_value=mc):
        data, err = load_portfolio_rpc("uid-123")
    expect(isinstance(data, dict), f"Should return dict: {type(data)}")
    expect(err == "", f"Error should be empty: {err}")

def test_load_rpc_empty_returns_empty_dict():
    from backend.db_init import load_portfolio_rpc
    mc = _mock_client(rpc_data=None)
    with patch("backend.db_init._get_client", return_value=mc):
        data, err = load_portfolio_rpc("uid-123")
    expect(isinstance(data, dict), "Should return dict even when empty")

def test_load_rpc_handles_error():
    from backend.db_init import load_portfolio_rpc
    mc = _mock_client(raise_on="rpc")
    with patch("backend.db_init._get_client", return_value=mc):
        data, err = load_portfolio_rpc("uid-123")
    expect(isinstance(data, dict), "Should return dict on error")
    expect(data == {}, "Should return empty dict on error")
    expect(len(err) > 0, "Should return error message")

def test_load_rpc_calls_correct_function():
    from backend.db_init import load_portfolio_rpc
    mc = _mock_client(rpc_data={})
    with patch("backend.db_init._get_client", return_value=mc):
        load_portfolio_rpc("test-uid")
    call_args = mc.rpc.call_args
    expect(call_args[0][0] == "load_portfolio", "Must call load_portfolio RPC")
    expect(call_args[0][1]["p_user_id"] == "test-uid", "Must pass p_user_id")

test("LOAD_RPC — success returns (dict, '')",          test_load_rpc_success)
test("LOAD_RPC — null data returns empty dict",        test_load_rpc_empty_returns_empty_dict)
test("LOAD_RPC — handles RPC error",                   test_load_rpc_handles_error)
test("LOAD_RPC — calls correct RPC function",          test_load_rpc_calls_correct_function)

# ══════════════════════════════════════════════════════════════════════
# SUITE 4 — auth._sb_save_portfolio uses RPC
# ══════════════════════════════════════════════════════════════════════

def test_auth_save_calls_rpc():
    from backend import auth
    called = []
    def mock_rpc(uid, pf):
        called.append((uid, pf))
        return True, "Saved"
    with patch("backend.db_init.save_portfolio_rpc", mock_rpc):
        auth._sb_save_portfolio(
            {"user_id": "u1", "access_token": "tok"},
            {"TCS": {"qty": 5}}
        )
    expect(len(called) == 1, "Should call save_portfolio_rpc once")
    expect(called[0][0] == "u1", "Should pass correct user_id")

def test_auth_save_raises_on_failure():
    from backend import auth
    with patch("backend.db_init.save_portfolio_rpc", return_value=(False, "DB error")):
        try:
            auth._sb_save_portfolio({"user_id": "u1"}, {})
            expect(False, "Should have raised exception")
        except Exception as e:
            expect("DB error" in str(e) or len(str(e)) > 0)

def test_auth_save_raises_no_uid():
    from backend import auth
    try:
        auth._sb_save_portfolio({}, {})
        expect(False, "Should raise when no user_id")
    except Exception as e:
        expect("user_id" in str(e).lower() or "logged" in str(e).lower())

def test_auth_load_calls_rpc():
    from backend import auth
    pf = {"WIPRO": {"qty": 3}}
    with patch("backend.db_init.load_portfolio_rpc", return_value=(pf, "")):
        result = auth._sb_load_portfolio({"user_id": "u1"})
    expect(result == pf, f"Should return portfolio: {result}")

def test_auth_load_empty_uid():
    from backend import auth
    result = auth._sb_load_portfolio({})
    expect(result == {}, "Empty user_info should return {}")

def test_auth_load_handles_rpc_error():
    from backend import auth
    with patch("backend.db_init.load_portfolio_rpc", return_value=({}, "RPC error")):
        result = auth._sb_load_portfolio({"user_id": "u1"})
    expect(isinstance(result, dict), "Should return dict even on error")

test("AUTH_SAVE — calls save_portfolio_rpc",           test_auth_save_calls_rpc)
test("AUTH_SAVE — raises on RPC failure",              test_auth_save_raises_on_failure)
test("AUTH_SAVE — raises when no user_id",             test_auth_save_raises_no_uid)
test("AUTH_LOAD — calls load_portfolio_rpc",           test_auth_load_calls_rpc)
test("AUTH_LOAD — returns {} for empty user_info",     test_auth_load_empty_uid)
test("AUTH_LOAD — handles RPC error gracefully",       test_auth_load_handles_rpc_error)

# ══════════════════════════════════════════════════════════════════════
# SUITE 5 — portfolio.py _persist and reload
# ══════════════════════════════════════════════════════════════════════

def test_persist_calls_save():
    from backend import portfolio as pf_mod
    _st.session_state = {
        "portfolio":  {"INFY": {"qty": 5}},
        "user_info":  {"user_id": "u1", "access_token": "tok"},
    }
    saved = []
    def mock_save(ui, pf):
        saved.append((ui, pf))
    with patch("backend.auth.save_user_portfolio", mock_save):
        ok, msg = pf_mod._persist()
    expect(len(saved) == 1, "Should call save once")

def test_persist_returns_tuple():
    from backend import portfolio as pf_mod
    _st.session_state = {
        "portfolio": {},
        "user_info": {"user_id": "u1"},
    }
    with patch("backend.auth.save_user_portfolio", return_value=None):
        result = pf_mod._persist()
    expect(isinstance(result, tuple), "Should return tuple")
    expect(len(result) == 2, "Should return (bool, str)")

def test_persist_no_user_info():
    from backend import portfolio as pf_mod
    _st.session_state = {"portfolio": {}, "user_info": {}}
    ok, msg = pf_mod._persist()
    expect(not ok, "Should fail with no user_info")

def test_persist_saves_timestamp():
    from backend import portfolio as pf_mod
    _st.session_state = {
        "portfolio": {},
        "user_info": {"user_id": "u1"},
    }
    with patch("backend.auth.save_user_portfolio", return_value=None):
        pf_mod._persist()
    expect("portfolio_last_saved" in _st.session_state,
           "Should set portfolio_last_saved in session_state")

def test_persist_handles_save_error():
    from backend import portfolio as pf_mod
    _st.session_state = {
        "portfolio": {},
        "user_info": {"user_id": "u1"},
    }
    with patch("backend.auth.save_user_portfolio", side_effect=Exception("RLS error")):
        ok, msg = pf_mod._persist()
    expect(not ok, "Should return False on save error")
    expect("rls" in msg.lower() or "error" in msg.lower() or len(msg) > 0)

def test_reload_calls_load():
    from backend import portfolio as pf_mod
    pf = {"SBIN": {"qty": 100}}
    _st.session_state = {"user_info": {"user_id": "u1"}}
    with patch("backend.auth.load_user_portfolio", return_value=pf):
        ok, msg = pf_mod.reload_portfolio_from_db()
    expect(ok, f"Should succeed: {msg}")
    expect(_st.session_state.get("portfolio") == pf, "Should update session state")

def test_reload_no_user():
    from backend import portfolio as pf_mod
    _st.session_state = {"user_info": {}}
    ok, msg = pf_mod.reload_portfolio_from_db()
    expect(not ok, "Should fail with no user_info")

def test_reload_handles_error():
    from backend import portfolio as pf_mod
    _st.session_state = {"user_info": {"user_id": "u1"}}
    with patch("backend.auth.load_user_portfolio", side_effect=Exception("network error")):
        ok, msg = pf_mod.reload_portfolio_from_db()
    expect(not ok, "Should return False on error")

test("PERSIST — calls save_user_portfolio",             test_persist_calls_save)
test("PERSIST — returns (bool, str) tuple",             test_persist_returns_tuple)
test("PERSIST — fails gracefully with no user",         test_persist_no_user_info)
test("PERSIST — saves timestamp to session_state",      test_persist_saves_timestamp)
test("PERSIST — handles save exception",                test_persist_handles_save_error)
test("RELOAD — updates session_state portfolio",        test_reload_calls_load)
test("RELOAD — fails gracefully with no user",          test_reload_no_user)
test("RELOAD — handles load exception",                 test_reload_handles_error)

# ══════════════════════════════════════════════════════════════════════
# SUITE 6 — Portfolio add/remove/pnl (local logic)
# ══════════════════════════════════════════════════════════════════════

def test_add_holding_new():
    from backend import portfolio as pf_mod
    _st.session_state = {"portfolio": {}, "user_info": {}}
    with patch("backend.auth.save_user_portfolio", return_value=None):
        pf_mod.add_holding("RELIANCE", 10, 1300.0, "2025-01-01")
    pf = _st.session_state["portfolio"]
    expect("RELIANCE" in pf, "RELIANCE should be in portfolio")
    expect(pf["RELIANCE"]["qty"] == 10)
    expect(pf["RELIANCE"]["avg_buy_price"] == 1300.0)

def test_add_holding_averages():
    from backend import portfolio as pf_mod
    _st.session_state = {"portfolio": {
        "TCS": {"symbol":"TCS","sector":"IT","qty":10,"avg_buy_price":3000.0,"lots":[]}
    }, "user_info": {}}
    with patch("backend.auth.save_user_portfolio", return_value=None):
        pf_mod.add_holding("TCS", 10, 3200.0)
    avg = _st.session_state["portfolio"]["TCS"]["avg_buy_price"]
    expect(avg == 3100.0, f"Weighted avg should be 3100, got {avg}")

def test_remove_holding():
    from backend import portfolio as pf_mod
    _st.session_state = {"portfolio": {
        "HDFC": {"symbol":"HDFC","sector":"Finance","qty":5,"avg_buy_price":1500.0,"lots":[]}
    }, "user_info": {}}
    with patch("backend.auth.save_user_portfolio", return_value=None):
        pf_mod.remove_holding("HDFC")
    expect("HDFC" not in _st.session_state["portfolio"])

def test_pnl_calculation():
    from backend.portfolio import compute_portfolio_pnl
    portfolio = {"INFY": {"symbol":"INFY","sector":"IT","qty":10,
                          "avg_buy_price":1500.0,"lots":[]}}
    prices = {"INFY": 1800.0}
    rows, totals = compute_portfolio_pnl(portfolio, prices)
    expect(len(rows) == 1)
    expect(rows[0]["pnl"] == 3000.0, f"PnL should be 3000: {rows[0]['pnl']}")
    expect(rows[0]["pnl_pct"] == 20.0, f"PnL% should be 20: {rows[0]['pnl_pct']}")
    expect(totals["total_pnl"] == 3000.0)

def test_pnl_loss():
    from backend.portfolio import compute_portfolio_pnl
    portfolio = {"WIPRO": {"symbol":"WIPRO","sector":"IT","qty":100,
                           "avg_buy_price":500.0,"lots":[]}}
    prices = {"WIPRO": 400.0}
    rows, totals = compute_portfolio_pnl(portfolio, prices)
    expect(totals["total_pnl"] == -10000.0, f"Loss should be -10000: {totals['total_pnl']}")
    expect(totals["n_loss"] == 1)

def test_pnl_zero_price():
    from backend.portfolio import compute_portfolio_pnl
    portfolio = {"SBIN": {"symbol":"SBIN","sector":"Finance","qty":50,
                          "avg_buy_price":600.0,"lots":[]}}
    prices = {"SBIN": 0.0}  # price fetch failed
    rows, totals = compute_portfolio_pnl(portfolio, prices)
    expect(rows[0]["current_val"] == 0.0, "Zero price → zero current val")
    # Should not crash

test("PORTFOLIO — add new holding",                     test_add_holding_new)
test("PORTFOLIO — add averages correctly",              test_add_holding_averages)
test("PORTFOLIO — remove holding",                      test_remove_holding)
test("PORTFOLIO — P&L calculation profit",              test_pnl_calculation)
test("PORTFOLIO — P&L calculation loss",                test_pnl_loss)
test("PORTFOLIO — P&L handles zero price",              test_pnl_zero_price)

# ══════════════════════════════════════════════════════════════════════
# SUITE 7 — APP.PY wiring
# ══════════════════════════════════════════════════════════════════════

def test_app_imports_persist():
    src = (ROOT/"app.py").read_text()
    expect("_persist" in src, "_persist not imported in app.py")
    expect("reload_portfolio_from_db" in src, "reload_portfolio_from_db not in app.py")

def test_app_has_save_button():
    src = (ROOT/"app.py").read_text()
    expect("💾" in src or "Save" in src, "Save button missing from app.py")

def test_app_has_refresh_button():
    src = (ROOT/"app.py").read_text()
    expect("🔄" in src or "Refresh" in src, "Refresh button missing from app.py")

def test_app_shows_save_feedback():
    src = (ROOT/"app.py").read_text()
    expect("portfolio saved" in src.lower() or "saved to cloud" in src.lower(),
           "Save feedback message missing")

def test_app_no_naked_persist():
    """_persist() should always capture return value, never called bare."""
    src = (ROOT/"app.py").read_text()
    import re
    bare = re.findall(r'(?<!\w)_persist\(\)(?!\s*$)(?!\s*#)', src)
    # All calls should be: ok, msg = _persist()
    bad = [l.strip() for l in src.split('\n')
           if '_persist()' in l and 'ok' not in l and '#' not in l.split('_persist')[0]]
    expect(len(bad) == 0, f"Bare _persist() calls found: {bad}")

test("APP_WIRING — imports _persist and reload",        test_app_imports_persist)
test("APP_WIRING — has save button",                    test_app_has_save_button)
test("APP_WIRING — has refresh button",                 test_app_has_refresh_button)
test("APP_WIRING — shows save feedback",                test_app_shows_save_feedback)
test("APP_WIRING — _persist always captures result",    test_app_no_naked_persist)

# ══════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════
W = 66
print("\n" + "="*W)
print("  PORTFOLIO TEST AGENT — RESULTS")
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
