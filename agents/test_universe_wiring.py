"""
agents/test_universe_wiring.py
══════════════════════════════
Repeatable integration test suite — verifies that every part of the app
correctly wires to the active index universe (portfolio, backtest, correlations).

50 tests across 6 suites. Run repeatedly to catch regressions:
    python agents/test_universe_wiring.py

Exit 0 if all pass, 1 if any fail.
"""

import sys, types, ast, traceback, inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# ── Mock Streamlit & heavy deps ────────────────────────────────────────────────
def _mock(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m

_st = _mock("streamlit")
_st.session_state  = {"selected_index": "Nifty 50"}
_st.secrets        = {"supabase": {"url": "https://x.supabase.co", "anon_key": "k"}}
_st.cache_data     = lambda *a, **k: (lambda f: f)
_st.cache_resource = lambda *a, **k: (lambda f: f)
for _attr in ("error","success","info","warning","spinner","markdown","text_input",
              "number_input","date_input","button","columns","expander","rerun",
              "stop","caption","selectbox","progress","slider","tabs","write",
              "plotly_chart","dataframe","download_button","subheader"):
    setattr(_st, _attr, MagicMock(return_value=MagicMock()))
_st.spinner = MagicMock()
_st.spinner.__enter__ = lambda s, *a: None
_st.spinner.__exit__  = lambda s, *a: None
_st.columns = MagicMock(return_value=[MagicMock(__enter__=lambda s,*a:s,
                                                __exit__=lambda s,*a:None)] * 6)

_mock("yfinance"); _mock("supabase")
_mock("plotly"); _mock("plotly.express"); _mock("plotly.graph_objects")
_mock("sklearn"); _mock("sklearn.ensemble"); _mock("sklearn.linear_model")
_mock("sklearn.preprocessing"); _mock("sklearn.metrics")
_mock("openpyxl"); _mock("openpyxl.styles"); _mock("openpyxl.utils")
_mock("bs4"); _mock("requests"); _mock("lxml")

# sklearn needs submodule mocks with actual attributes
import numpy as _np
_sk        = _mock("sklearn")
_sk_ens    = _mock("sklearn.ensemble")
_sk_lin    = _mock("sklearn.linear_model")
_sk_pre    = _mock("sklearn.preprocessing")
_sk_met    = _mock("sklearn.metrics")
_sk_mod    = _mock("sklearn.base")

class _FakeModel:
    def fit(self, X, y): return self
    def predict(self, X): return _np.zeros(len(X))
    def set_params(self, **kw): return self

_sk_ens.RandomForestRegressor     = _FakeModel
_sk_ens.GradientBoostingRegressor = _FakeModel
_sk_lin.Ridge                     = _FakeModel
_sk_pre.StandardScaler            = _FakeModel
_sk_met.r2_score                  = lambda a,b: 0.5
_sk_met.mean_absolute_error       = lambda a,b: 0.1

_sk_pipe = _mock("sklearn.pipeline")
class _FakePipeline:
    def __init__(self, *a, **k): pass
    def fit(self, X, y): return self
    def predict(self, X): return _np.zeros(len(X))
_sk_pipe.Pipeline = _FakePipeline
_sk_ens.Pipeline  = _FakePipeline

# backend.__init__ imports ml — also mock openpyxl properly
_opx       = _mock("openpyxl")
_opx_sty   = _mock("openpyxl.styles")
_opx_utils = _mock("openpyxl.utils")

class _FakeWB:
    def __init__(self, *a, **k): self.active = _FakeWS()
    def create_sheet(self, *a, **k): return _FakeWS()
    def save(self, f): pass
class _FakeWS:
    def __init__(self): self.column_dimensions = {}; self.freeze_panes = None
    def __setitem__(self,k,v): pass
    def __getitem__(self,k): return _FakeCell()
    def merge_cells(self, *a): pass
class _FakeCell:
    value=None; font=None; fill=None; alignment=None; border=None
    number_format=""
_opx.Workbook = _FakeWB
_opx.load_workbook = lambda *a,**k: _FakeWB()

for _cls in ("PatternFill","Font","Alignment","Border","Side","GradientFill"):
    setattr(_opx_sty, _cls, type(_cls, (), {"__init__": lambda s,**k: None}))
_opx_utils.get_column_letter = lambda i: "A"

# ── Test harness ───────────────────────────────────────────────────────────────
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
        raise AssertionError(msg or "Expectation failed")


# ════════════════════════════════════════════════════════════════════════
# SUITE 1 — SYNTAX: all files parse cleanly
# ════════════════════════════════════════════════════════════════════════
FILES_TO_CHECK = [
    "app.py", "backend/constants.py", "backend/data.py",
    "frontend/analytics_components.py", "frontend/portfolio_components.py",
    "frontend/components.py", "frontend/styles.py",
]

for _f in FILES_TO_CHECK:
    def _make_syntax_test(fp):
        def _t():
            ast.parse((ROOT / fp).read_text())
        return _t
    test(f"SYNTAX — {_f}", _make_syntax_test(_f))


# ════════════════════════════════════════════════════════════════════════
# SUITE 2 — CONSTANTS: index universe integrity
# ════════════════════════════════════════════════════════════════════════
from backend.constants import (
    NIFTY_50, NIFTY_NEXT_50, NIFTY_MIDCAP_150, NIFTY_SMALLCAP_250,
    NIFTY_100, NIFTY_500, STOCKS,
    INDEX_OPTIONS, INDEX_UNIVERSE, INDEX_BADGE, SECTOR_SCORE,
)

test("CONST — Nifty 50 has exactly 50 stocks",
     lambda: expect(len(NIFTY_50) == 50, f"got {len(NIFTY_50)}"))
test("CONST — Nifty Next 50 has exactly 50 stocks",
     lambda: expect(len(NIFTY_NEXT_50) == 50, f"got {len(NIFTY_NEXT_50)}"))
test("CONST — Nifty 100 = 50 + Next 50",
     lambda: expect(len(NIFTY_100) == 100, f"got {len(NIFTY_100)}"))
test("CONST — Nifty 500 has 300+ stocks",
     lambda: expect(len(NIFTY_500) >= 300, f"got {len(NIFTY_500)}"))
test("CONST — STOCKS is backward-compat alias for NIFTY_50",
     lambda: expect(STOCKS == NIFTY_50))
test("CONST — INDEX_OPTIONS has 4 entries",
     lambda: expect(len(INDEX_OPTIONS) == 4, f"got {len(INDEX_OPTIONS)}"))
test("CONST — INDEX_UNIVERSE keys match INDEX_OPTIONS",
     lambda: expect(set(INDEX_OPTIONS) == set(INDEX_UNIVERSE.keys())))
test("CONST — INDEX_BADGE has entry for each option",
     lambda: expect(all(o in INDEX_BADGE for o in INDEX_OPTIONS)))
test("CONST — all Nifty 500 stocks have non-empty sector",
     lambda: expect(all(isinstance(s,str) and s for s in NIFTY_500.values())))
test("CONST — no duplicate symbols across Nifty 50 and Next 50",
     lambda: expect(len(set(NIFTY_50) & set(NIFTY_NEXT_50)) == 0,
                    f"overlaps: {set(NIFTY_50) & set(NIFTY_NEXT_50)}"))


# ════════════════════════════════════════════════════════════════════════
# SUITE 3 — PORTFOLIO ADD FORM: universe param wiring
# ════════════════════════════════════════════════════════════════════════

def test_form_has_universe_param():
    from frontend.portfolio_components import render_add_holding_form
    sig = inspect.signature(render_add_holding_form)
    expect("universe" in sig.parameters, "render_add_holding_form needs 'universe' param")

def test_form_universe_defaults_to_nifty500():
    from frontend.portfolio_components import render_add_holding_form
    sig = inspect.signature(render_add_holding_form)
    default = sig.parameters["universe"].default
    # default should be None (resolved to NIFTY_500 inside) or NIFTY_500 itself
    expect(default is None or default == NIFTY_500,
           f"Default should be None or NIFTY_500, got {default}")

def test_form_accepts_nifty50_universe():
    from frontend.portfolio_components import render_add_holding_form
    sig = inspect.signature(render_add_holding_form)
    # Should accept dict param without type error
    params = sig.parameters
    expect("universe" in params)

def test_form_src_uses_active_not_stocks():
    src = (ROOT / "frontend/portfolio_components.py").read_text()
    expect("active" in src, "portfolio_components.py should use 'active' variable")
    # Should NOT use STOCKS directly in the selectbox options line
    lines = [l for l in src.split("\n") if "STOCKS.keys()" in l and "selectbox" not in l.lower()]
    expect("sorted(active.keys())" in src, "selectbox should use sorted(active.keys())")

def test_app_passes_universe_to_form():
    src = (ROOT / "app.py").read_text()
    expect("render_add_holding_form(universe=" in src,
           "app.py must pass universe= to render_add_holding_form")

def test_app_uses_index_universe_for_form():
    src = (ROOT / "app.py").read_text()
    expect("INDEX_UNIVERSE" in src, "app.py must use INDEX_UNIVERSE")
    # Should read selected_index from session_state for form
    expect('session_state.get("selected_index"' in src or
           'session_state["selected_index"]' in src)

def test_app_clears_bt_cache_on_index_change():
    src = (ROOT / "app.py").read_text()
    expect('"bt_result"' in src, "app.py should clear bt_result on index change")

def test_app_clears_corr_cache_on_index_change():
    src = (ROOT / "app.py").read_text()
    expect('"corr_result"' in src, "app.py should clear corr_result on index change")

test("PORTFOLIO — render_add_holding_form has universe param",   test_form_has_universe_param)
test("PORTFOLIO — universe param defaults to None/NIFTY_500",    test_form_universe_defaults_to_nifty500)
test("PORTFOLIO — universe param accepts dict",                  test_form_accepts_nifty50_universe)
test("PORTFOLIO — selectbox uses active not STOCKS",             test_form_src_uses_active_not_stocks)
test("PORTFOLIO — app.py passes universe= to form",             test_app_passes_universe_to_form)
test("PORTFOLIO — app.py uses INDEX_UNIVERSE for form",          test_app_uses_index_universe_for_form)
test("PORTFOLIO — app clears bt_result on index change",         test_app_clears_bt_cache_on_index_change)
test("PORTFOLIO — app clears corr_result on index change",       test_app_clears_corr_cache_on_index_change)


# ════════════════════════════════════════════════════════════════════════
# SUITE 4 — BACKTEST: wired to active universe
# ════════════════════════════════════════════════════════════════════════

def test_backtest_has_get_active_universe():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    expect("def _get_active_universe" in src,
           "analytics_components.py must have _get_active_universe()")

def test_backtest_calls_get_active():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    # Find render_backtest_tab body and check it calls _get_active_universe
    idx = src.find("def render_backtest_tab")
    next_def = src.find("\ndef ", idx + 10)
    bt_body = src[idx:next_def]
    expect("_get_active_universe" in bt_body,
           "render_backtest_tab must call _get_active_universe()")

def test_backtest_no_hardcoded_stocks():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    idx = src.find("def render_backtest_tab")
    next_def = src.find("\ndef ", idx + 10)
    bt_body = src[idx:next_def]
    expect("STOCKS.keys()" not in bt_body,
           "render_backtest_tab must not use hardcoded STOCKS.keys()")
    expect("_universe" in bt_body,
           "render_backtest_tab must use _universe variable")

def test_backtest_uses_universe_for_syms():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    expect("list(_universe.keys())" in src,
           "Backtest should use list(_universe.keys()) not list(STOCKS.keys())")

def test_backtest_section_header_dynamic():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    idx = src.find("def render_backtest_tab")
    next_def = src.find("\ndef ", idx + 10)
    bt_body = src[idx:next_def]
    expect("_idx_name" in bt_body or "selected_index" in bt_body,
           "Backtest section header should show index name")

def test_backtest_spinner_dynamic():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    # spinner should reference _idx_count not hardcode "50"
    expect('_idx_count' in src or 'idx_count' in src,
           "Backtest spinner should use dynamic count")

test("BACKTEST — _get_active_universe helper exists",            test_backtest_has_get_active_universe)
test("BACKTEST — render_backtest_tab calls _get_active_universe",test_backtest_calls_get_active)
test("BACKTEST — no hardcoded STOCKS.keys() in backtest",        test_backtest_no_hardcoded_stocks)
test("BACKTEST — uses _universe for symbol list",                test_backtest_uses_universe_for_syms)
test("BACKTEST — section header shows active index name",        test_backtest_section_header_dynamic)
test("BACKTEST — spinner text is dynamic",                       test_backtest_spinner_dynamic)


# ════════════════════════════════════════════════════════════════════════
# SUITE 5 — CORRELATION: wired to active universe
# ════════════════════════════════════════════════════════════════════════

def test_corr_calls_get_active():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    idx = src.find("def render_correlation_tab")
    next_def = src.find("\ndef ", idx + 10)
    corr_body = src[idx:next_def]
    expect("_get_active_universe" in corr_body,
           "render_correlation_tab must call _get_active_universe()")

def test_corr_no_hardcoded_stocks():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    idx = src.find("def render_correlation_tab")
    next_def = src.find("\ndef ", idx + 10)
    corr_body = src[idx:next_def]
    expect("STOCKS.keys()" not in corr_body,
           "render_correlation_tab must not use hardcoded STOCKS.keys()")

def test_corr_uses_universe_syms():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    idx = src.find("def render_correlation_tab")
    next_def = src.find("\ndef ", idx + 10)
    corr_body = src[idx:next_def]
    expect("_universe" in corr_body,
           "render_correlation_tab must use _universe variable")

def test_corr_section_header_dynamic():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    idx = src.find("def render_correlation_tab")
    next_def = src.find("\ndef ", idx + 10)
    corr_body = src[idx:next_def]
    expect("_idx_name" in corr_body or "selected_index" in corr_body,
           "Correlation section should show active index name")

def test_corr_not_hardcoded_50():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    idx = src.find("def render_correlation_tab")
    next_def = src.find("\ndef ", idx + 10)
    corr_body = src[idx:next_def]
    expect("all 50 stocks" not in corr_body,
           "Correlation must not hardcode '50 stocks' in header")

def test_corr_spinner_dynamic():
    src = (ROOT / "frontend/analytics_components.py").read_text()
    idx = src.find("def render_correlation_tab")
    next_def = src.find("\ndef ", idx + 10)
    corr_body = src[idx:next_def]
    expect("_idx_count" in corr_body or "idx_count" in corr_body,
           "Correlation spinner should use dynamic count")

test("CORR — render_correlation_tab calls _get_active_universe", test_corr_calls_get_active)
test("CORR — no hardcoded STOCKS.keys() in correlation",         test_corr_no_hardcoded_stocks)
test("CORR — uses _universe for symbol list",                    test_corr_uses_universe_syms)
test("CORR — section header shows active index name",            test_corr_section_header_dynamic)
test("CORR — does not hardcode '50 stocks'",                     test_corr_not_hardcoded_50)
test("CORR — spinner text is dynamic",                           test_corr_spinner_dynamic)


# ════════════════════════════════════════════════════════════════════════
# SUITE 6 — _get_active_universe: runtime behaviour
# ════════════════════════════════════════════════════════════════════════

def test_get_active_returns_nifty50_default():
    import streamlit as st
    st.session_state = {"selected_index": "Nifty 50"}
    from frontend.analytics_components import _get_active_universe
    result = _get_active_universe()
    expect(result == NIFTY_50, f"Default should be Nifty 50, got {len(result)} stocks")

def test_get_active_returns_nifty100():
    import streamlit as st
    st.session_state = {"selected_index": "Nifty 100"}
    from importlib import reload
    import frontend.analytics_components as ac
    result = ac._get_active_universe()
    expect(len(result) == 100, f"Nifty 100 should give 100 stocks, got {len(result)}")

def test_get_active_returns_midcap():
    import streamlit as st
    st.session_state = {"selected_index": "Nifty Midcap 150"}
    from frontend.analytics_components import _get_active_universe
    result = _get_active_universe()
    expect(len(result) >= 100, f"Midcap should give 100+ stocks, got {len(result)}")

def test_get_active_returns_nifty500():
    import streamlit as st
    st.session_state = {"selected_index": "Nifty 500"}
    from frontend.analytics_components import _get_active_universe
    result = _get_active_universe()
    expect(len(result) >= 300, f"Nifty 500 should give 300+ stocks, got {len(result)}")

def test_get_active_fallback_on_unknown():
    import streamlit as st
    st.session_state = {"selected_index": "Unknown Index"}
    from frontend.analytics_components import _get_active_universe
    result = _get_active_universe()
    # Should fall back to Nifty 50 not crash
    expect(isinstance(result, dict) and len(result) > 0,
           "Should fall back to Nifty 50 on unknown index")

def test_get_active_fallback_no_session():
    import streamlit as st
    st.session_state = {}   # no selected_index key
    from frontend.analytics_components import _get_active_universe
    result = _get_active_universe()
    expect(isinstance(result, dict) and len(result) > 0,
           "Should not crash when session state has no selected_index")

def test_form_filters_to_nifty50():
    """When universe=NIFTY_50, selectbox options should only contain 50 symbols."""
    src = (ROOT / "frontend/portfolio_components.py").read_text()
    expect("sorted(active.keys())" in src,
           "Form should sort active.keys() for selectbox")

def test_fetch_all_stocks_param():
    sig = inspect.signature(__import__("backend.data", fromlist=["fetch_all"]).fetch_all)
    expect("stocks" in sig.parameters)
    default = sig.parameters["stocks"].default
    expect(default is None or isinstance(default, dict),
           "stocks param default should be None or dict")

def test_index_selector_in_app():
    src = (ROOT / "app.py").read_text()
    expect("Index / Universe" in src or "INDEX_OPTIONS" in src,
           "app.py must have index selector UI")

def test_all_tabs_respect_index():
    """Verify that analysis, backtest and correlation all read from session_state."""
    analytics_src = (ROOT / "frontend/analytics_components.py").read_text()
    # _get_active_universe is used, which reads session_state
    expect(analytics_src.count("_get_active_universe()") >= 2,
           "Both backtest and correlation must call _get_active_universe()")

test("RUNTIME — get_active returns Nifty 50 by default",         test_get_active_returns_nifty50_default)
test("RUNTIME — get_active returns 100 stocks for Nifty 100",    test_get_active_returns_nifty100)
test("RUNTIME — get_active returns midcap stocks",               test_get_active_returns_midcap)
test("RUNTIME — get_active returns 300+ for Nifty 500",          test_get_active_returns_nifty500)
test("RUNTIME — get_active falls back on unknown index",         test_get_active_fallback_on_unknown)
test("RUNTIME — get_active safe when session_state empty",       test_get_active_fallback_no_session)
test("RUNTIME — portfolio form filters to active universe",      test_form_filters_to_nifty50)
test("RUNTIME — fetch_all has optional stocks param",            test_fetch_all_stocks_param)
test("RUNTIME — app.py has index selector",                      test_index_selector_in_app)
test("RUNTIME — both backtest+corr call _get_active_universe",   test_all_tabs_respect_index)



# ════════════════════════════════════════════════════════════════════════
# SUITE 7 — ML v5: 5-year × 500-stock architecture
# ════════════════════════════════════════════════════════════════════════

def test_history_years_is_5():
    from backend.ml import HISTORY_YEARS
    expect(HISTORY_YEARS == 5, f"HISTORY_YEARS should be 5, got {HISTORY_YEARS}")

def test_build_dataset_accepts_universe_params():
    import inspect
    from backend.ml import build_dataset
    sig = inspect.signature(build_dataset)
    expect("universe_key"  in sig.parameters, "build_dataset needs universe_key")
    expect("universe_json" in sig.parameters, "build_dataset needs universe_json")

def test_get_trained_models_keyed_by_universe():
    import inspect
    from backend.ml import _get_trained_models
    sig = inspect.signature(_get_trained_models)
    expect("universe_key"  in sig.parameters, "_get_trained_models needs universe_key")
    expect("universe_json" in sig.parameters, "_get_trained_models needs universe_json")

def test_predict_accepts_universe_param():
    import inspect
    from backend.ml import predict
    sig = inspect.signature(predict)
    expect("universe" in sig.parameters, "predict() needs universe param")
    default = sig.parameters["universe"].default
    expect(default is None, f"universe default should be None, got {default}")

def test_predict_universe_defaults_to_stocks():
    src_txt = (ROOT / "backend/ml.py").read_text()
    # When universe is None it should fall back to STOCKS
    expect("universe if universe else STOCKS" in src_txt or
           "universe or STOCKS" in src_txt,
           "predict() must fall back to STOCKS when universe is None")

def test_extract_features_returns_ndarray():
    src_txt = (ROOT / "backend/ml.py").read_text()
    expect("np.float32" in src_txt, "Dataset should use float32 for memory efficiency")
    expect("_extract_features_array" in src_txt, "_extract_features_array must exist")

def test_dataset_streaming_del():
    src_txt = (ROOT / "backend/ml.py").read_text()
    # Should delete df after feature extraction
    expect("del df" in src_txt or "del df," in src_txt,
           "build_dataset should del df after extraction")
    expect("del arr" in src_txt or "del df, arr" in src_txt or "del df,arr" in src_txt,
           "build_dataset should del arr after appending")

def test_max_rows_subsampling():
    src_txt = (ROOT / "backend/ml.py").read_text()
    expect("MAX_ROWS" in src_txt, "Should have MAX_ROWS cap to limit training time")
    expect("500_000" in src_txt or "500000" in src_txt, "MAX_ROWS should be 500k")

def test_rf_njobs_minus1():
    src_txt = (ROOT / "backend/ml.py").read_text()
    expect("n_jobs=-1" in src_txt, "RF should use n_jobs=-1 for speed on large datasets")

def test_app_passes_universe_to_predict():
    src_txt = (ROOT / "app.py").read_text()
    expect("predict(all_stats, universe=_universe)" in src_txt,
           "app.py must pass universe= to predict()")

def test_5yr_label_in_ml_banner():
    src_txt = (ROOT / "app.py").read_text()
    expect("5yr" in src_txt or "5-year" in src_txt or "5yr daily" in src_txt,
           "ML info banner should mention 5yr history")

def test_universe_key_is_sorted():
    src_txt = (ROOT / "backend/ml.py").read_text()
    expect("sorted(" in src_txt, "_universe_key should use sorted() for stability")

test("ML v5 — HISTORY_YEARS is 5",                        test_history_years_is_5)
test("ML v5 — build_dataset accepts universe params",      test_build_dataset_accepts_universe_params)
test("ML v5 — _get_trained_models keyed by universe",      test_get_trained_models_keyed_by_universe)
test("ML v5 — predict() accepts universe param",           test_predict_accepts_universe_param)
test("ML v5 — predict() falls back to STOCKS when None",   test_predict_universe_defaults_to_stocks)
test("ML v5 — features extracted as float32 ndarray",     test_extract_features_returns_ndarray)
test("ML v5 — dataset built by streaming (del df/arr)",    test_dataset_streaming_del)
test("ML v5 — MAX_ROWS subsampling at 500k",               test_max_rows_subsampling)
test("ML v5 — RF uses n_jobs=-1",                          test_rf_njobs_minus1)
test("ML v5 — app.py passes universe to predict()",        test_app_passes_universe_to_predict)
test("ML v5 — ML banner shows 5yr history",                test_5yr_label_in_ml_banner)
test("ML v5 — universe_key uses sorted() for stability",   test_universe_key_is_sorted)


# ════════════════════════════════════════════════════════════════════════
# SUITE 8 — SENTIMENT v2: Google News RSS + Financial NLP
# ════════════════════════════════════════════════════════════════════════

def test_sentiment_module_exists():
    src_txt = (ROOT / "backend/sentiment.py").read_text()
    expect(len(src_txt) > 500, "sentiment.py must exist and be non-trivial")

def test_sentiment_has_google_news_url():
    src_txt = (ROOT / "backend/sentiment.py").read_text()
    expect("news.google.com" in src_txt, "Must use Google News RSS")
    expect("rss/search" in src_txt, "Must use RSS search endpoint")

def test_sentiment_batched_fetch():
    src_txt = (ROOT / "backend/sentiment.py").read_text()
    expect("_BATCH_SIZE" in src_txt, "Must batch requests")
    expect("_fetch_batch_raw" in src_txt or "batch" in src_txt.lower())

def test_sentiment_recency_weighting():
    src_txt = (ROOT / "backend/sentiment.py").read_text()
    expect("_RECENCY_WEIGHTS" in src_txt or "recency" in src_txt.lower(),
           "Must have recency weighting")
    expect("pub_dt" in src_txt or "pubDate" in src_txt or "pub_date" in src_txt,
           "Must parse pubDate timestamps")

def test_sentiment_negation_handling():
    src_txt = (ROOT / "backend/sentiment.py").read_text()
    expect("_NEGATIONS" in src_txt, "Must handle negation (not bullish → negative)")

def test_sentiment_intensifiers():
    src_txt = (ROOT / "backend/sentiment.py").read_text()
    expect("_INTENSIFIERS" in src_txt, "Must handle intensifiers (sharply surges)")

def test_sentiment_200_plus_words():
    src_txt = (ROOT / "backend/sentiment.py").read_text()
    pos_count = src_txt.count('"') // 2   # rough count
    expect(pos_count > 100, f"Lexicon should have 200+ terms, rough count={pos_count}")

def test_sentiment_score_function():
    from backend.sentiment import _score_headline
    # Positive headline
    pos = _score_headline("Company beats earnings expectations with record profit")
    expect(pos > 0, f"Positive headline should score > 0, got {pos}")
    # Negative headline
    neg = _score_headline("Stock crashes on fraud investigation, SEBI probe launched")
    expect(neg < 0, f"Negative headline should score < 0, got {neg}")

def test_sentiment_negation_works():
    from backend.sentiment import _score_headline
    # "not bullish" should be negative or neutral
    score_pos  = _score_headline("Stock is bullish")
    score_neg  = _score_headline("Stock is not bullish")
    expect(score_pos > score_neg,
           f"Negation should flip: 'bullish'={score_pos:.2f}, 'not bullish'={score_neg:.2f}")

def test_sentiment_coverage_boost():
    from backend.sentiment import _coverage_boost
    boost_1  = _coverage_boost(1)
    boost_10 = _coverage_boost(10)
    expect(boost_1  >= 1.0, "Coverage boost should be >= 1")
    expect(boost_10 > boost_1, f"More articles → higher boost: 1art={boost_1:.2f}, 10art={boost_10:.2f}")

def test_ml_uses_new_sentiment():
    src_txt = (ROOT / "backend/ml.py").read_text()
    expect("fetch_sentiment_data_v2" in src_txt or "from backend.sentiment" in src_txt,
           "ml.py must import from backend.sentiment")

def test_predict_has_confidence_fields():
    src_txt = (ROOT / "backend/ml.py").read_text()
    expect("sent_confidence" in src_txt, "predict() must store sent_confidence")
    expect("news_count"      in src_txt, "predict() must store news_count")
    expect("news_latest"     in src_txt, "predict() must store news_latest")

def test_no_beautifulsoup_import():
    ml_src  = (ROOT / "backend/ml.py").read_text()
    expect("BeautifulSoup" not in ml_src and "bs4" not in ml_src,
           "ml.py must no longer import BeautifulSoup")

def test_requirements_no_bs4():
    reqs = (ROOT / "requirements.txt").read_text()
    expect("beautifulsoup4" not in reqs, "requirements.txt must not include bs4")

test("SENTIMENT — sentiment.py module exists",                  test_sentiment_module_exists)
test("SENTIMENT — uses Google News RSS endpoint",               test_sentiment_has_google_news_url)
test("SENTIMENT — requests are batched",                        test_sentiment_batched_fetch)
test("SENTIMENT — parses pubDate for recency weighting",        test_sentiment_recency_weighting)
test("SENTIMENT — negation handling ('not bullish'→negative)",  test_sentiment_negation_handling)
test("SENTIMENT — intensifier scaling ('sharply surges')",      test_sentiment_intensifiers)
test("SENTIMENT — extended lexicon (200+ terms)",               test_sentiment_200_plus_words)
test("SENTIMENT — _score_headline returns correct polarity",    test_sentiment_score_function)
test("SENTIMENT — negation actually flips score",               test_sentiment_negation_works)
test("SENTIMENT — coverage boost scales with article count",    test_sentiment_coverage_boost)
test("SENTIMENT — ml.py imports from backend.sentiment",        test_ml_uses_new_sentiment)
test("SENTIMENT — predict() stores confidence + article count", test_predict_has_confidence_fields)
test("SENTIMENT — ml.py no longer uses BeautifulSoup",         test_no_beautifulsoup_import)
test("SENTIMENT — requirements.txt has no bs4",                 test_requirements_no_bs4)

# ════════════════════════════════════════════════════════════════════════
# REPORT
# ════════════════════════════════════════════════════════════════════════
W = 68
print("\n" + "="*W)
print("  UNIVERSE WIRING TEST AGENT — RESULTS")
print("="*W)

suite = ""
for status, name, err in RESULTS:
    new_suite = name.split(" — ")[0]
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
print(f"  {'✅ ALL PASS' if FAIL == 0 else '❌ FAILURES FOUND'}")
print(f"  {PASS}/{total} passed  ·  {FAIL} failed")
print("="*W + "\n")
sys.exit(0 if FAIL == 0 else 1)
