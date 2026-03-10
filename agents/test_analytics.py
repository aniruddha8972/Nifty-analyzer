"""
agents/test_analytics.py
─────────────────────────
Dedicated test agent for the 4 Analytics & Intelligence features.
Runs 40+ tests across:
  Suite 1: Heatmap data builder
  Suite 2: Backtesting engine
  Suite 3: Correlation matrix
  Suite 4: Events calendar
  Suite 5: Frontend component syntax + imports
  Suite 6: Integration (data flow end-to-end)

Run:  python agents/test_analytics.py
"""

import sys, types, ast, traceback
from pathlib import Path
from datetime import date, timedelta

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

# ── Mocks ─────────────────────────────────────────────────────────────────────
def _mock(name):
    m = types.ModuleType(name)
    sys.modules[name] = m
    return m

import numpy as _np
import pandas as _pd

_st = _mock("streamlit")
_st.session_state  = {}
_st.cache_data     = lambda *a, **kw: (lambda f: f)
_st.cache_resource = lambda *a, **kw: (lambda f: f)
_st.secrets        = {}

_yf = _mock("yfinance")
def _yf_dl(*a, **kw):
    n = 250
    dates = _pd.date_range("2024-01-01", periods=n, freq="B")
    c = 1000 * _np.cumprod(1 + _np.random.normal(0.001, 0.015, n))
    return _pd.DataFrame({
        "Open":c*0.99,"High":c*1.01,"Low":c*0.99,
        "Close":c,"Volume":_np.ones(n)*1e6
    }, index=dates)
_yf.download = _yf_dl

_sb = _mock("supabase")
_sb.create_client = lambda u,k: None

_px_mod  = _mock("plotly.express")
_go_mod  = _mock("plotly.graph_objects")
_plotly  = _mock("plotly")

# ── Test harness ──────────────────────────────────────────────────────────────
PASS, FAIL = 0, 0
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

# ── Synthetic data helpers ────────────────────────────────────────────────────
from backend.constants import STOCKS, NIFTY_500, INDEX_UNIVERSE, INDEX_OPTIONS

def _make_stock_data(n=20):
    syms = list(STOCKS.keys())[:n]
    return [{
        "symbol":     sym,
        "sector":     STOCKS[sym],
        "change_pct": float(_np.random.normal(0, 2)),
        "last_close": float(1000 + _np.random.rand()*500),
        "first_close":float(1000 + _np.random.rand()*500),
        "rsi":        float(30 + _np.random.rand()*40),
        "signal":     _np.random.choice(["🟢 BUY","🟡 HOLD","🔴 AVOID"]),
        "final_score":float(40 + _np.random.rand()*40),
        "mom5":       float(_np.random.normal(0,1)),
        "vol_ratio":  float(0.8 + _np.random.rand()*0.5),
        "volatility": float(1 + _np.random.rand()*2),
    } for sym in syms]

def _make_ohlcv(n=250, trend=0.001):
    dates = _pd.date_range("2024-01-01", periods=n, freq="B")
    c = 1000 * _np.cumprod(1 + _np.random.normal(trend, 0.015, n))
    return _pd.DataFrame({
        "Open":c*0.99,"High":c*1.01,"Low":c*0.985,
        "Close":c,"Volume":_np.ones(n)*1e6
    }, index=dates)

def _make_ohlcv_cache(n_stocks=10, n_days=500):
    syms = list(STOCKS.keys())[:n_stocks]
    return {sym: _make_ohlcv(n_days) for sym in syms}

# ══════════════════════════════════════════════════════════════════════
# SUITE 1: HEATMAP
# ══════════════════════════════════════════════════════════════════════
from backend.analytics import build_heatmap_data, get_sector_summary

def test_heatmap_basic():
    data = _make_stock_data(20)
    df   = build_heatmap_data(data)
    expect(not df.empty,              "build_heatmap_data returned empty df")
    expect("symbol" in df.columns,   "symbol column missing")
    expect("sector" in df.columns,   "sector column missing")
    expect("change_pct" in df.columns,"change_pct missing")
    expect("abs_change" in df.columns,"abs_change missing")
    expect(len(df) == 20,             f"Expected 20 rows, got {len(df)}")

def test_heatmap_abs_change_positive():
    data = _make_stock_data(20)
    df   = build_heatmap_data(data)
    expect((df["abs_change"] > 0).all(), "abs_change must always be positive")

def test_heatmap_sector_aggregates():
    data = _make_stock_data(20)
    df   = build_heatmap_data(data)
    expect("sector_avg_change"   in df.columns, "sector_avg_change missing")
    expect("sector_stock_count"  in df.columns, "sector_stock_count missing")
    expect("sector_gainers"      in df.columns, "sector_gainers missing")
    expect("sector_losers"       in df.columns, "sector_losers missing")

def test_heatmap_empty_input():
    df = build_heatmap_data([])
    expect(df.empty, "Empty input should return empty DataFrame")

def test_heatmap_single_stock():
    data = _make_stock_data(1)
    df   = build_heatmap_data(data)
    expect(len(df) == 1, "Single stock should return 1 row")

def test_sector_summary():
    data    = _make_stock_data(30)
    df      = build_heatmap_data(data)
    summary = get_sector_summary(df)
    expect(isinstance(summary, list),   "get_sector_summary should return list")
    expect(len(summary) > 0,            "Should have at least 1 sector")
    for sec in summary:
        expect("sector"           in sec, f"sector key missing in {sec}")
        expect("sector_avg_change" in sec, f"sector_avg_change missing")
        expect("sector_gainers"    in sec, "sector_gainers missing")

def test_sector_summary_sorted():
    data    = _make_stock_data(40)
    df      = build_heatmap_data(data)
    summary = get_sector_summary(df)
    changes = [s["sector_avg_change"] for s in summary]
    expect(changes == sorted(changes, reverse=True),
           "Sector summary should be sorted by avg_change descending")

test("HEATMAP — build_heatmap_data basic structure",    test_heatmap_basic)
test("HEATMAP — abs_change always positive",            test_heatmap_abs_change_positive)
test("HEATMAP — sector aggregates present",             test_heatmap_sector_aggregates)
test("HEATMAP — empty input → empty DataFrame",         test_heatmap_empty_input)
test("HEATMAP — single stock handled",                  test_heatmap_single_stock)
test("HEATMAP — get_sector_summary returns list",       test_sector_summary)
test("HEATMAP — sector summary sorted by return",       test_sector_summary_sorted)

# ══════════════════════════════════════════════════════════════════════
# SUITE 2: BACKTESTING
# ══════════════════════════════════════════════════════════════════════
from backend.analytics import run_backtest

def test_backtest_returns_structure():
    cache  = _make_ohlcv_cache(5, 500)
    result = run_backtest(cache, hold_days=20, min_score=40)
    expect("trades"       in result, "trades key missing")
    expect("summary"      in result, "summary key missing")
    expect("equity_curve" in result, "equity_curve key missing")
    expect("by_symbol"    in result, "by_symbol key missing")

def test_backtest_summary_keys():
    cache  = _make_ohlcv_cache(5, 500)
    result = run_backtest(cache, hold_days=20, min_score=40)
    s      = result["summary"]
    required = ["total_trades","win_rate","avg_return","sharpe",
                "max_drawdown","best_trade","worst_trade"]
    for k in required:
        expect(k in s, f"summary key missing: {k}")

def test_backtest_win_rate_range():
    cache  = _make_ohlcv_cache(5, 500)
    result = run_backtest(cache, hold_days=20, min_score=40)
    wr = result["summary"].get("win_rate", 0)
    expect(0 <= wr <= 100, f"Win rate out of range: {wr}")

def test_backtest_trades_have_required_keys():
    cache  = _make_ohlcv_cache(5, 500)
    result = run_backtest(cache, hold_days=20, min_score=40)
    for t in result["trades"][:5]:
        for k in ["symbol","entry_date","entry_price","exit_price",
                  "return_pct","hold_days","win"]:
            expect(k in t, f"trade key missing: {k}")

def test_backtest_no_future_leak():
    """Entry price must be > 0 and exit price must be > 0."""
    cache  = _make_ohlcv_cache(5, 500)
    result = run_backtest(cache, hold_days=20, min_score=40)
    for t in result["trades"][:20]:
        expect(t["entry_price"] > 0, "Entry price must be > 0")
        expect(t["exit_price"]  > 0, "Exit price must be > 0")

def test_backtest_equity_curve_ordered():
    cache  = _make_ohlcv_cache(5, 500)
    result = run_backtest(cache, hold_days=20, min_score=40)
    curve  = result["equity_curve"]
    if len(curve) > 1:
        dates = [c["date"] for c in curve]
        expect(dates == sorted(dates), "Equity curve should be in date order")

def test_backtest_empty_cache():
    result = run_backtest({})
    expect(result["trades"] == [],    "Empty cache → empty trades")
    expect(result["summary"] == {},   "Empty cache → empty summary")

def test_backtest_too_little_data():
    cache = {"RELIANCE": _make_ohlcv(30)}   # only 30 rows — below 60 minimum
    result = run_backtest(cache)
    expect(result["trades"] == [], "Too little data → no trades")

def test_backtest_stop_loss_respected():
    """With very tight stop loss (-0.1%), most trades should exit via stop."""
    cache  = _make_ohlcv_cache(3, 300)
    result = run_backtest(cache, hold_days=30, min_score=40, stop_loss=-0.1)
    sl_exits = [t for t in result["trades"] if t["exit_reason"] == "stop_loss"]
    # With -0.1% SL, many trades should exit via stop
    if result["trades"]:
        sl_ratio = len(sl_exits) / len(result["trades"])
        expect(sl_ratio > 0, "No stop loss exits with tight SL — check stop loss logic")

test("BACKTEST — result structure complete",          test_backtest_returns_structure)
test("BACKTEST — summary has all keys",               test_backtest_summary_keys)
test("BACKTEST — win rate is 0-100",                  test_backtest_win_rate_range)
test("BACKTEST — individual trades have all keys",    test_backtest_trades_have_required_keys)
test("BACKTEST — no zero prices (data integrity)",    test_backtest_no_future_leak)
test("BACKTEST — equity curve in date order",         test_backtest_equity_curve_ordered)
test("BACKTEST — empty cache → empty result",         test_backtest_empty_cache)
test("BACKTEST — insufficient data → no trades",      test_backtest_too_little_data)
test("BACKTEST — stop loss exits work",               test_backtest_stop_loss_respected)

# ══════════════════════════════════════════════════════════════════════
# SUITE 3: CORRELATION MATRIX
# ══════════════════════════════════════════════════════════════════════
from backend.analytics import (
    build_correlation_matrix, get_top_correlations,
    get_portfolio_diversification
)

def test_corr_matrix_shape():
    cache = _make_ohlcv_cache(10, 300)
    corr, rets = build_correlation_matrix(cache, min_overlap=50)
    expect(not corr.empty,           "Correlation matrix should not be empty")
    n = len(corr)
    expect(corr.shape == (n, n),     f"Matrix should be square, got {corr.shape}")

def test_corr_matrix_diagonal():
    cache = _make_ohlcv_cache(8, 300)
    corr, _ = build_correlation_matrix(cache, min_overlap=50)
    if not corr.empty:
        diag = [corr.iloc[i, i] for i in range(len(corr))]
        for v in diag:
            expect(abs(v - 1.0) < 0.001, f"Diagonal should be 1.0, got {v}")

def test_corr_matrix_symmetric():
    cache = _make_ohlcv_cache(8, 300)
    corr, _ = build_correlation_matrix(cache, min_overlap=50)
    if not corr.empty:
        diff = (corr - corr.T).abs().max().max()
        expect(diff < 0.0001, f"Correlation matrix not symmetric: max diff={diff}")

def test_corr_values_range():
    cache = _make_ohlcv_cache(8, 300)
    corr, _ = build_correlation_matrix(cache, min_overlap=50)
    if not corr.empty:
        expect(corr.min().min() >= -1.001, "Correlation below -1")
        expect(corr.max().max() <= 1.001,  "Correlation above +1")

def test_corr_empty_cache():
    corr, rets = build_correlation_matrix({})
    expect(corr.empty, "Empty cache → empty correlation matrix")

def test_corr_too_few_stocks():
    cache = {"RELIANCE": _make_ohlcv(300)}   # only 1 stock
    corr, _ = build_correlation_matrix(cache, min_overlap=50)
    expect(corr.empty, "Single stock → cannot compute pairwise correlations")

def test_top_correlations_structure():
    cache = _make_ohlcv_cache(10, 300)
    corr, _ = build_correlation_matrix(cache, min_overlap=50)
    if not corr.empty:
        most, least = get_top_correlations(corr, top_n=5)
        expect(len(most) <= 5,  "Should return at most 5 most-correlated")
        expect(len(least) <= 5, "Should return at most 5 least-correlated")
        for p in most:
            expect("stock_a"     in p, "stock_a missing")
            expect("stock_b"     in p, "stock_b missing")
            expect("correlation" in p, "correlation missing")

def test_top_correlations_ordering():
    cache = _make_ohlcv_cache(10, 300)
    corr, _ = build_correlation_matrix(cache, min_overlap=50)
    if not corr.empty:
        most, _ = get_top_correlations(corr, top_n=5)
        if len(most) > 1:
            vals = [p["correlation"] for p in most]
            expect(vals == sorted(vals, reverse=True),
                   "Most correlated pairs should be sorted descending")

def test_diversification_score_range():
    cache = _make_ohlcv_cache(10, 300)
    corr, _ = build_correlation_matrix(cache, min_overlap=50)
    syms = list(STOCKS.keys())[:5]
    result = get_portfolio_diversification(corr, syms)
    if result.get("score") is not None:
        expect(0 <= result["score"] <= 100,
               f"Diversification score out of range: {result['score']}")

def test_diversification_single_holding():
    cache = _make_ohlcv_cache(5, 300)
    corr, _ = build_correlation_matrix(cache, min_overlap=50)
    result = get_portfolio_diversification(corr, ["RELIANCE"])
    expect("message" in result, "Should return message for single holding")

test("CORRELATION — matrix is correct shape",               test_corr_matrix_shape)
test("CORRELATION — diagonal is all 1.0",                   test_corr_matrix_diagonal)
test("CORRELATION — matrix is symmetric",                   test_corr_matrix_symmetric)
test("CORRELATION — all values in [-1, 1]",                 test_corr_values_range)
test("CORRELATION — empty cache → empty matrix",            test_corr_empty_cache)
test("CORRELATION — single stock → empty matrix",           test_corr_too_few_stocks)
test("CORRELATION — top pairs have correct structure",       test_top_correlations_structure)
test("CORRELATION — top pairs sorted correctly",            test_top_correlations_ordering)
test("CORRELATION — diversification score 0-100",           test_diversification_score_range)
test("CORRELATION — single holding handled gracefully",     test_diversification_single_holding)

# ══════════════════════════════════════════════════════════════════════
# SUITE 4: EVENTS CALENDAR
# ══════════════════════════════════════════════════════════════════════
from backend.analytics import (
    build_events_calendar, get_upcoming_events, get_fo_expiry_dates
)

def test_fo_expiry_is_thursday():
    for year in [2025, 2026]:
        for month in range(1, 13):
            dates = get_fo_expiry_dates(year, month)
            for d in dates:
                expect(d.weekday() == 3,
                       f"{d} is not a Thursday (weekday={d.weekday()})")

def test_fo_expiry_is_last_thursday():
    """Verify it's the LAST Thursday, not any Thursday."""
    from datetime import date, timedelta
    for year in [2025]:
        for month in range(1, 13):
            exp_dates = get_fo_expiry_dates(year, month)
            for exp_d in exp_dates:
                # Next Thursday should be in a different month
                next_thu = exp_d + timedelta(days=7)
                expect(next_thu.month != month,
                       f"{exp_d} is not the LAST Thursday of {year}-{month:02d}")

def test_calendar_returns_dict():
    events = build_events_calendar(months_ahead=2)
    expect(isinstance(events, dict), "build_events_calendar should return dict")
    expect(len(events) > 0,          "Calendar should have at least some events")

def test_calendar_event_structure():
    events = build_events_calendar(months_ahead=2)
    for d_str, evts in list(events.items())[:5]:
        expect(isinstance(evts, list), f"Events for {d_str} should be a list")
        for evt in evts:
            expect("type"  in evt, f"type missing in event: {evt}")
            expect("title" in evt, f"title missing in event: {evt}")
            expect("color" in evt, f"color missing in event: {evt}")

def test_calendar_has_fo_expiry():
    events = build_events_calendar(months_ahead=3)
    fo_found = any(
        any(e["type"] == "fo_expiry" for e in evts)
        for evts in events.values()
    )
    expect(fo_found, "Calendar should contain at least one F&O expiry event")

def test_calendar_has_market_holidays():
    events = build_events_calendar(months_ahead=12)
    closed_found = any(
        any(e["type"] == "market_closed" for e in evts)
        for evts in events.values()
    )
    expect(closed_found, "Calendar should contain market closed events")

def test_calendar_date_format():
    """All keys should be valid ISO date strings."""
    events = build_events_calendar(months_ahead=2)
    for d_str in events.keys():
        try:
            date.fromisoformat(d_str)
        except ValueError:
            raise AssertionError(f"Invalid date format: {d_str}")

def test_upcoming_events_sorted():
    events   = build_events_calendar(months_ahead=3)
    upcoming = get_upcoming_events(events, days_ahead=60)
    dates    = [u["date"] for u in upcoming]
    expect(dates == sorted(dates), "Upcoming events should be sorted by date")

def test_upcoming_events_in_range():
    events   = build_events_calendar(months_ahead=3)
    upcoming = get_upcoming_events(events, days_ahead=30)
    today    = date.today()
    cutoff   = today + timedelta(days=30)
    for u in upcoming:
        d = date.fromisoformat(u["date"])
        expect(today <= d <= cutoff,
               f"Event {u['date']} outside requested range")

def test_upcoming_events_structure():
    events   = build_events_calendar(months_ahead=2)
    upcoming = get_upcoming_events(events, days_ahead=45)
    for u in upcoming:
        expect("date"      in u, "date key missing")
        expect("date_obj"  in u, "date_obj key missing")
        expect("days_away" in u, "days_away key missing")
        expect("events"    in u, "events key missing")
        expect(u["days_away"] >= 0, "days_away should be >= 0")

test("CALENDAR — F&O expiry is always a Thursday",        test_fo_expiry_is_thursday)
test("CALENDAR — F&O expiry is the LAST Thursday",        test_fo_expiry_is_last_thursday)
test("CALENDAR — build_events_calendar returns dict",     test_calendar_returns_dict)
test("CALENDAR — events have required keys",              test_calendar_event_structure)
test("CALENDAR — contains F&O expiry events",             test_calendar_has_fo_expiry)
test("CALENDAR — contains market holiday events",         test_calendar_has_market_holidays)
test("CALENDAR — all keys are valid ISO dates",           test_calendar_date_format)
test("CALENDAR — upcoming events sorted by date",         test_upcoming_events_sorted)
test("CALENDAR — upcoming events within requested range", test_upcoming_events_in_range)
test("CALENDAR — upcoming event items have all keys",     test_upcoming_events_structure)

# ══════════════════════════════════════════════════════════════════════
# SUITE 5: SYNTAX + IMPORTS
# ══════════════════════════════════════════════════════════════════════

def test_analytics_backend_syntax():
    path = ROOT / "backend/analytics.py"
    expect(path.exists(), "backend/analytics.py missing")
    ast.parse(path.read_text())

def test_analytics_frontend_syntax():
    path = ROOT / "frontend/analytics_components.py"
    expect(path.exists(), "frontend/analytics_components.py missing")
    ast.parse(path.read_text())

def test_analytics_backend_imports():
    from backend.analytics import (
        build_heatmap_data, get_sector_summary,
        run_backtest, build_correlation_matrix,
        get_top_correlations, get_portfolio_diversification,
        build_events_calendar, get_upcoming_events,
        get_fo_expiry_dates
    )
    for fn in [build_heatmap_data, get_sector_summary, run_backtest,
               build_correlation_matrix, get_top_correlations,
               get_portfolio_diversification, build_events_calendar,
               get_upcoming_events, get_fo_expiry_dates]:
        expect(callable(fn), f"{fn.__name__} is not callable")

def test_app_py_has_analytics_tabs():
    app_src = _all_src()
    expect("render_heatmap_tab"     in app_src, "render_heatmap_tab not in app.py")
    expect("render_backtest_tab"    in app_src, "render_backtest_tab not in app.py")
    expect("render_correlation_tab" in app_src, "render_correlation_tab not in app.py")
    expect("render_events_tab"      in app_src, "render_events_tab not in app.py")
    expect("Heatmap"    in app_src, "Heatmap tab missing from app.py")
    expect("Backtest"   in app_src, "Backtest tab missing from app.py")
    expect("Events"     in app_src, "Events tab missing from app.py")

def test_plotly_in_requirements():
    req = (ROOT / "requirements.txt").read_text()
    expect("plotly" in req, "plotly missing from requirements.txt")

test("SYNTAX  — backend/analytics.py parses cleanly",    test_analytics_backend_syntax)
test("SYNTAX  — frontend/analytics_components.py clean", test_analytics_frontend_syntax)
test("IMPORTS — all analytics functions callable",        test_analytics_backend_imports)
test("APP.PY  — all 4 analytics tabs wired in",          test_app_py_has_analytics_tabs)
test("CONFIG  — plotly in requirements.txt",             test_plotly_in_requirements)

# ══════════════════════════════════════════════════════════════════════
# SUITE 6: INTEGRATION
# ══════════════════════════════════════════════════════════════════════

def test_heatmap_to_sector_summary_pipeline():
    """Full heatmap data pipeline from stock_data to sector summary."""
    data    = _make_stock_data(50)
    df      = build_heatmap_data(data)
    summary = get_sector_summary(df)
    expect(len(df) == 50,   f"All 50 stocks in heatmap, got {len(df)}")
    expect(len(summary) > 0, "Sector summary produced from 50 stocks")
    total_stocks_in_summary = sum(s["sector_stock_count"] for s in summary)
    expect(total_stocks_in_summary == 50,
           f"Sector counts should sum to 50, got {total_stocks_in_summary}")

def test_backtest_with_real_stock_symbols():
    """Backtest should work with actual Nifty symbols."""
    from backend.analytics import run_backtest
    cache = {sym: _make_ohlcv(500) for sym in list(STOCKS.keys())[:5]}
    result = run_backtest(cache, hold_days=10, min_score=40)
    expect(isinstance(result["trades"], list),    "trades should be a list")
    expect(isinstance(result["by_symbol"], dict), "by_symbol should be a dict")

def test_correlation_to_diversification_pipeline():
    """Full correlation pipeline → diversification score."""
    cache = _make_ohlcv_cache(8, 300)
    corr, _ = build_correlation_matrix(cache, min_overlap=50)
    syms    = list(STOCKS.keys())[:4]
    result  = get_portfolio_diversification(corr, syms)
    expect("score"   in result, "score key missing in diversification result")
    expect("message" in result, "message key missing in diversification result")

def test_events_calendar_full_pipeline():
    """Calendar build → upcoming events → structure check."""
    events   = build_events_calendar(months_ahead=3)
    upcoming = get_upcoming_events(events, days_ahead=90)
    total_events = sum(len(u["events"]) for u in upcoming)
    expect(total_events > 0, "Should have at least some upcoming events in 90 days")

def test_all_files_syntax_clean():
    """Final check — all new files parse without SyntaxError."""
    new_files = [
        ROOT / "backend/analytics.py",
        ROOT / "frontend/analytics_components.py",
    ]
    for fpath in new_files:
        ast.parse(fpath.read_text())

test("INTEGRATION — heatmap → sector summary pipeline",         test_heatmap_to_sector_summary_pipeline)
test("INTEGRATION — backtest with real Nifty symbols",          test_backtest_with_real_stock_symbols)
test("INTEGRATION — correlation → diversification pipeline",    test_correlation_to_diversification_pipeline)
test("INTEGRATION — events calendar full pipeline",             test_events_calendar_full_pipeline)
test("INTEGRATION — all new files syntax clean",                test_all_files_syntax_clean)

# ══════════════════════════════════════════════════════════════════════
# REPORT
# ══════════════════════════════════════════════════════════════════════
W = 64
print("\n" + "="*W)
print("  ANALYTICS TEST AGENT — RESULTS")
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
print(f"  {'✅ ALL PASS' if FAIL==0 else '❌ FAILURES'}")
print(f"  {PASS}/{total} passed  ·  {FAIL} failed")
print("="*W + "\n")
sys.exit(0 if FAIL == 0 else 1)
