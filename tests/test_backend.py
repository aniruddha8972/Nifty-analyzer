"""
tests/test_backend.py
──────────────────────
╔══════════════════════════════════════════════════════════════════╗
║  CHANGED FROM PREVIOUS VERSION                                   ║
║  ─────────────────────────────────────────────────────────────   ║
║  OLD: tested deterministic fake data generator directly          ║
║  NEW: mocks yfinance so all tests run fully offline              ║
║                                                                  ║
║  Key changes:                                                    ║
║  1. Added MockTicker class to simulate yf.Ticker responses       ║
║  2. Added patch_yfinance() context manager                       ║
║  3. Replaced test_generate_stock_* with test_fetch_single_*     ║
║  4. Added RSI unit tests (_compute_rsi)                         ║
║  5. Added test for empty yfinance response → returns None        ║
║  6. Added test for status generator (progress bar support)       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from contextlib import contextmanager
from datetime import date
from unittest.mock import patch
import pandas as pd
import numpy as np


# ── yfinance mock ─────────────────────────────────────────────────────────────
def _make_mock_history(open_p=1800.0, close_p=1900.0,
                       high_p=1950.0, low_p=1750.0, vol=5_000_000, rows=30):
    idx    = pd.date_range("2025-01-01", periods=rows, freq="B")
    closes = np.linspace(open_p, close_p, rows)
    return pd.DataFrame({
        "Open":   [open_p]  * rows,
        "High":   [high_p]  * rows,
        "Low":    [low_p]   * rows,
        "Close":  closes,
        "Volume": [vol]     * rows,
    }, index=idx)


class MockTicker:
    def __init__(self, ticker_str):
        self._ticker = ticker_str
    def history(self, start=None, end=None, auto_adjust=True):
        rows = 400 if start and (date.fromisoformat(end[:10]) - date.fromisoformat(start[:10])).days > 100 else 30
        return _make_mock_history(rows=rows)
    @property
    def info(self):
        return {
            "trailingPE": 22.5, "beta": 1.1,
            "fiftyTwoWeekHigh": 2100.0, "fiftyTwoWeekLow": 1400.0,
            "marketCap": 5_000_000_000_000, "dividendYield": 0.015,
        }


@contextmanager
def patch_yfinance():
    with patch("backend.data_engine.yf.Ticker", MockTicker):
        yield


def _get_test_stocks(from_date=None, to_date=None):
    from backend.data_engine import fetch_all_stocks
    with patch_yfinance():
        return fetch_all_stocks(
            from_date or date(2025, 1, 1),
            to_date   or date(2025, 1, 31),
        )


# ── Data engine tests ─────────────────────────────────────────────────────────
class TestDataEngine:

    def test_fetch_returns_stocks(self):
        assert len(_get_test_stocks()) > 0

    def test_fetch_returns_up_to_50(self):
        assert len(_get_test_stocks()) <= 50

    def test_stock_fields_present(self):
        s = _get_test_stocks()[0]
        for f in ("symbol","sector","open_price","close_price","high","low",
                  "chg_pct","volume","avg_volume","pe_ratio","week52_high",
                  "week52_low","rsi","beta","div_yield","mkt_cap_b","days"):
            assert hasattr(s, f), f"Missing field: {f}"

    def test_ohlc_relationships(self):
        for s in _get_test_stocks():
            assert s.high  >= s.close_price
            assert s.low   <= s.close_price
            assert s.open_price  > 0
            assert s.close_price > 0
            assert s.volume > 0

    def test_rsi_in_range(self):
        for s in _get_test_stocks():
            assert 0 <= s.rsi <= 100

    def test_beta_positive(self):
        for s in _get_test_stocks():
            assert s.beta > 0

    def test_div_yield_non_negative(self):
        for s in _get_test_stocks():
            assert s.div_yield >= 0

    def test_sorted_descending(self):
        stocks = _get_test_stocks()
        for i in range(len(stocks)-1):
            assert stocks[i].chg_pct >= stocks[i+1].chg_pct

    def test_top_gainers_count(self):
        from backend.data_engine import get_top_gainers
        assert len(get_top_gainers(_get_test_stocks())) == 10

    def test_top_losers_count(self):
        from backend.data_engine import get_top_losers
        assert len(get_top_losers(_get_test_stocks())) == 10

    def test_gainers_losers_no_overlap(self):
        from backend.data_engine import get_top_gainers, get_top_losers
        s = _get_test_stocks()
        assert {x.symbol for x in get_top_gainers(s)}.isdisjoint(
               {x.symbol for x in get_top_losers(s)})

    def test_invalid_date_raises(self):
        from backend.data_engine import _fetch_single_stock
        raised = False
        with patch_yfinance():
            try:
                _fetch_single_stock("TCS", date(2025,2,1), date(2025,1,1))
            except ValueError:
                raised = True
        assert raised, "Expected ValueError for inverted dates"

    def test_none_on_empty_history(self):
        from backend.data_engine import _fetch_single_stock
        class EmptyTicker:
            def __init__(self, _): pass
            def history(self, **kw): return pd.DataFrame()
            @property
            def info(self): return {}
        with patch("backend.data_engine.yf.Ticker", EmptyTicker):
            result = _fetch_single_stock("TCS", date(2025,1,1), date(2025,1,31))
            assert result is None

    def test_date_range_label(self):
        from backend.data_engine import get_date_range_label
        label = get_date_range_label(date(2025,1,1), date(2025,1,31))
        assert "Jan" in label and "2025" in label

    def test_trading_days_estimate(self):
        from backend.data_engine import trading_days_estimate
        assert trading_days_estimate(7)  == 5
        assert trading_days_estimate(14) == 10
        assert trading_days_estimate(30) == 21

    def test_days_field_correct(self):
        for s in _get_test_stocks(date(2025,1,1), date(2025,1,31)):
            assert s.days == 30

    def test_sector_mapped(self):
        lookup = {s.symbol: s for s in _get_test_stocks()}
        if "RELIANCE" in lookup: assert lookup["RELIANCE"].sector == "Energy"
        if "TCS"      in lookup: assert lookup["TCS"].sector      == "IT"

    def test_compute_rsi_neutral_fallback(self):
        from backend.data_engine import _compute_rsi
        assert _compute_rsi(pd.Series([100.0, 101.0, 99.0])) == 50.0

    def test_compute_rsi_overbought(self):
        from backend.data_engine import _compute_rsi
        rsi = _compute_rsi(pd.Series([float(i) for i in range(1, 60)]))
        assert rsi > 70

    def test_compute_rsi_oversold(self):
        from backend.data_engine import _compute_rsi
        rsi = _compute_rsi(pd.Series([float(60-i) for i in range(60)]))
        assert rsi < 35

    def test_status_generator_all_symbols(self):
        from backend.data_engine import fetch_all_stocks_with_status, NIFTY50_SYMBOLS
        yielded = []
        with patch_yfinance():
            for sym, idx, data in fetch_all_stocks_with_status(date(2025,1,1), date(2025,1,31)):
                yielded.append(sym)
        assert yielded == NIFTY50_SYMBOLS


# ── AI model tests ─────────────────────────────────────────────────────────────
class TestAIModel:

    def setup_method(self):
        from backend.data_engine import get_top_gainers, get_top_losers
        from backend.ai_model import analyse_all
        s = _get_test_stocks()
        self.stocks   = get_top_gainers(s) + get_top_losers(s)
        self.analyses = analyse_all(self.stocks)

    def test_all_stocks_analysed(self):
        for s in self.stocks:
            assert s.symbol in self.analyses

    def test_score_in_range(self):
        for sym, a in self.analyses.items():
            assert 0 <= a.score <= 100

    def test_valid_recommendation(self):
        valid = {"STRONG BUY","BUY","HOLD","SELL","STRONG SELL"}
        for sym, a in self.analyses.items():
            assert a.recommendation in valid

    def test_valid_risk(self):
        for sym, a in self.analyses.items():
            assert a.risk_level in {"Low","Medium","Med-High","High"}

    def test_color_is_hex(self):
        for sym, a in self.analyses.items():
            assert a.rec_color.startswith("#") and len(a.rec_color) == 7

    def test_signals_non_empty(self):
        for sym, a in self.analyses.items():
            assert len(a.signals) > 0

    def test_strong_buy_threshold(self):
        from backend.ai_model import StockAnalysis
        assert StockAnalysis.from_score("T", 75, "Low",  ["x"]).recommendation == "STRONG BUY"

    def test_strong_sell_threshold(self):
        from backend.ai_model import StockAnalysis
        assert StockAnalysis.from_score("T", 20, "High", ["x"]).recommendation == "STRONG SELL"

    def test_hold_threshold(self):
        from backend.ai_model import StockAnalysis
        assert StockAnalysis.from_score("T", 50, "Medium", ["x"]).recommendation == "HOLD"

    def test_score_clamped(self):
        from backend.ai_model import StockAnalysis
        assert StockAnalysis.from_score("T", 999, "Low",  []).score == 100
        assert StockAnalysis.from_score("T", -50, "High", []).score == 0


# ── Report generator tests ─────────────────────────────────────────────────────
class TestReportGenerator:

    def _build(self):
        from backend.data_engine import get_top_gainers, get_top_losers
        from backend.ai_model import analyse_all
        from pipeline.report_generator import generate_excel_report
        s        = _get_test_stocks()
        gainers  = get_top_gainers(s)
        losers   = get_top_losers(s)
        analyses = analyse_all(gainers + losers)
        return generate_excel_report(gainers, losers, analyses, date(2025,1,1), date(2025,1,31))

    def test_returns_bytes(self):
        result = self._build()
        assert isinstance(result, bytes) and len(result) > 5000

    def test_four_sheets(self):
        import io, openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(self._build()))
        for name in ["Top 10 Gainers","Top 10 Losers","AI Analysis","Summary Dashboard"]:
            assert name in wb.sheetnames


# ── CLI runner ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    passed = failed = 0
    for cls in [TestDataEngine, TestAIModel, TestReportGenerator]:
        obj = cls()
        for name in sorted(dir(cls)):
            if not name.startswith("test_"): continue
            try:
                if hasattr(obj, "setup_method"): obj.setup_method()
                getattr(obj, name)()
                print(f"  PASS  {cls.__name__}::{name}")
                passed += 1
            except Exception as e:
                print(f"  FAIL  {cls.__name__}::{name}  →  {e}")
                failed += 1
    print(f"\n{passed+failed} tests | {passed} passed | {failed} failed")
    sys.exit(0 if failed == 0 else 1)
