"""
backend/data_engine.py
──────────────────────
╔══════════════════════════════════════════════════════════════════╗
║  BUG FIXES — v3 (stability patch)                               ║
║  ─────────────────────────────────────────────────────────────  ║
║                                                                  ║
║  BUG 1 FIXED — chg_pct formula was WRONG                        ║
║    Old: (last_close - first_open) / first_open                  ║
║         first_open is from a different day than last_close.     ║
║         Yahoo sometimes returns a different first row between   ║
║         calls → chg_pct flips on the same date range.           ║
║    New: (last_close - first_close) / first_close                ║
║         Both are closing prices → stable & consistent.          ║
║                                                                  ║
║  BUG 2 FIXED — non-deterministic Yahoo row count                ║
║    Old: end = to_date + 1 day                                   ║
║         Yahoo sometimes included the extra day → 21 rows one   ║
║         call, 22 rows next → different last_close →             ║
║         different sort → different top loser shown.             ║
║    New: end = to_date (exact), then hard-filter rows to         ║
║         hist.index.date <= to_date to clip any overflow.        ║
║                                                                  ║
║  BUG 3 FIXED — no caching, Yahoo returns stale/fresh mix        ║
║    Old: every Analyse click fires 100 fresh HTTP requests.      ║
║         Rapid re-clicks got different CDN-cached responses.     ║
║    New: _FETCH_CACHE keyed by (symbol, from_date, to_date).     ║
║         Same date range = identical StockData every time.       ║
╚══════════════════════════════════════════════════════════════════╝
"""

from datetime import date, timedelta
from typing import Dict, Generator, List, Optional, Tuple
import warnings

import yfinance as yf
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

# ── In-process fetch cache ────────────────────────────────────────────────────
# Keyed by (symbol, from_date, to_date). Guarantees same date range = same data.
# Cleared only when the Python process restarts (i.e. per Streamlit session).
_FETCH_CACHE: Dict[Tuple, Optional[object]] = {}


# ── Nifty 50 universe ────────────────────────────────────────────────────────
NIFTY50_SYMBOLS: List[str] = [
    "RELIANCE", "TCS", "HDFCBANK", "BHARTIARTL", "ICICIBANK",
    "INFOSYS", "SBIN", "HINDUNILVR", "ITC", "LICI",
    "LT", "BAJFINANCE", "HCLTECH", "KOTAKBANK", "MARUTI",
    "AXISBANK", "TITAN", "SUNPHARMA", "ONGC", "NTPC",
    "ADANIENT", "WIPRO", "ULTRACEMCO", "POWERGRID", "NESTLEIND",
    "BAJAJFINSV", "JSWSTEEL", "TATAMOTORS", "TECHM", "INDUSINDBK",
    "TATACONSUM", "COALINDIA", "ASIANPAINT", "HINDALCO", "CIPLA",
    "DRREDDY", "BPCL", "GRASIM", "ADANIPORTS", "EICHERMOT",
    "HEROMOTOCO", "BAJAJ-AUTO", "BRITANNIA", "SBILIFE", "APOLLOHOSP",
    "DIVISLAB", "HDFCLIFE", "M&M", "SHRIRAMFIN", "BEL",
]

SECTOR_MAP: Dict[str, str] = {
    "RELIANCE": "Energy",        "TCS": "IT",              "HDFCBANK": "Banking",
    "BHARTIARTL": "Telecom",     "ICICIBANK": "Banking",   "INFOSYS": "IT",
    "SBIN": "Banking",           "HINDUNILVR": "FMCG",     "ITC": "FMCG",
    "LICI": "Insurance",         "LT": "Infrastructure",   "BAJFINANCE": "NBFC",
    "HCLTECH": "IT",             "KOTAKBANK": "Banking",   "MARUTI": "Auto",
    "AXISBANK": "Banking",       "TITAN": "Consumer",      "SUNPHARMA": "Pharma",
    "ONGC": "Energy",            "NTPC": "Power",          "ADANIENT": "Conglomerate",
    "WIPRO": "IT",               "ULTRACEMCO": "Cement",   "POWERGRID": "Power",
    "NESTLEIND": "FMCG",         "BAJAJFINSV": "NBFC",     "JSWSTEEL": "Metals",
    "TATAMOTORS": "Auto",        "TECHM": "IT",            "INDUSINDBK": "Banking",
    "TATACONSUM": "FMCG",        "COALINDIA": "Mining",    "ASIANPAINT": "Paint",
    "HINDALCO": "Metals",        "CIPLA": "Pharma",        "DRREDDY": "Pharma",
    "BPCL": "Energy",            "GRASIM": "Cement",       "ADANIPORTS": "Infrastructure",
    "EICHERMOT": "Auto",         "HEROMOTOCO": "Auto",     "BAJAJ-AUTO": "Auto",
    "BRITANNIA": "FMCG",         "SBILIFE": "Insurance",   "APOLLOHOSP": "Healthcare",
    "DIVISLAB": "Pharma",        "HDFCLIFE": "Insurance",  "M&M": "Auto",
    "SHRIRAMFIN": "NBFC",        "BEL": "Defence",
}

DEFENSIVE_SECTORS = {"FMCG", "Pharma", "IT", "Healthcare"}

YF_SUFFIX = ".NS"

def _to_yf_ticker(symbol: str) -> str:
    """Convert NSE symbol to Yahoo Finance ticker. e.g. RELIANCE → RELIANCE.NS"""
    return f"{symbol}{YF_SUFFIX}"


# ── Stock data model ──────────────────────────────────────────────────────────
class StockData:
    """Single stock's OHLCV + derived metrics for a given period."""
    __slots__ = (
        "symbol", "sector", "open_price", "close_price",
        "high", "low", "chg_pct", "volume", "avg_volume",
        "pe_ratio", "week52_high", "week52_low",
        "rsi", "beta", "div_yield", "mkt_cap_b", "days",
    )

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)

    def to_dict(self) -> dict:
        return {s: getattr(self, s) for s in self.__slots__}


# ── RSI from real price history ───────────────────────────────────────────────
def _compute_rsi(closes: pd.Series, period: int = 14) -> float:
    """RSI(14) from closing prices. Returns 50.0 if not enough data."""
    if len(closes) < period + 1:
        return 50.0
    delta    = closes.diff().dropna()
    gain     = delta.clip(lower=0)
    loss     = (-delta).clip(lower=0)
    avg_gain = gain.rolling(window=period).mean().iloc[-1]
    avg_loss = loss.rolling(window=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    return round(float(100 - (100 / (1 + avg_gain / avg_loss))), 1)


# ── Single stock fetch with all 3 bugs fixed ─────────────────────────────────
def _fetch_single_stock(
    symbol:    str,
    from_date: date,
    to_date:   date,
) -> Optional[StockData]:
    """
    Fetch real OHLCV + metadata from Yahoo Finance for one NSE symbol.

    BUG FIXES applied here:
      1. chg_pct = (last_close - first_close) / first_close
         — both values are closing prices; immune to open-price noise.
      2. end date = to_date (not +1). Then rows hard-clipped to <= to_date
         — prevents Yahoo returning an extra row on some calls.
      3. Cached by (symbol, from_date, to_date)
         — same inputs always return identical StockData object.
    """
    cache_key = (symbol, from_date, to_date)
    if cache_key in _FETCH_CACHE:
        return _FETCH_CACHE[cache_key]  # BUG 3 FIX: return cached result

    days = (to_date - from_date).days
    if days <= 0:
        raise ValueError(f"to_date must be after from_date (got {days} days)")

    result = None
    try:
        ticker = yf.Ticker(_to_yf_ticker(symbol))

        # ── BUG 2 FIX: use to_date as exact end, then hard-clip rows ─────────
        hist = ticker.history(
            start       = from_date.strftime("%Y-%m-%d"),
            end         = to_date.strftime("%Y-%m-%d"),   # no +1 day
            auto_adjust = True,
        )
        if not hist.empty:
            # Hard-clip: drop any rows Yahoo snuck in beyond to_date
            hist = hist[hist.index.normalize() <= pd.Timestamp(to_date)]

        if hist.empty:
            _FETCH_CACHE[cache_key] = None
            return None

        # ── BUG 1 FIX: use close-to-close, not open-to-close ─────────────────
        first_close = round(float(hist["Close"].iloc[0]),  2)   # first day close
        last_close  = round(float(hist["Close"].iloc[-1]), 2)   # last  day close
        high_p      = round(float(hist["High"].max()),     2)
        low_p       = round(float(hist["Low"].min()),      2)
        volume      = int(hist["Volume"].iloc[-1])               # last day volume
        avg_vol     = int(hist["Volume"].mean())                 # avg over period

        chg_pct = round(((last_close - first_close) / first_close) * 100, 2) \
                  if first_close and first_close != 0 else 0.0

        # ── RSI from 1 year of history ────────────────────────────────────────
        rsi_hist = ticker.history(
            start       = (from_date - timedelta(days=365)).strftime("%Y-%m-%d"),
            end         = to_date.strftime("%Y-%m-%d"),
            auto_adjust = True,
        )
        rsi_val = _compute_rsi(rsi_hist["Close"]) if not rsi_hist.empty else 50.0

        # ── Fundamentals ──────────────────────────────────────────────────────
        info    = ticker.info
        pe      = round(float(info.get("trailingPE")       or info.get("forwardPE") or 20.0), 1)
        beta    = round(float(info.get("beta")             or 1.0),  2)
        w52h    = round(float(info.get("fiftyTwoWeekHigh") or high_p * 1.2), 2)
        w52l    = round(float(info.get("fiftyTwoWeekLow")  or low_p  * 0.8), 2)
        mkt_cap = round(float(info.get("marketCap")        or 0) / 1e9, 1)
        div_yld = round(float(info.get("dividendYield")    or 0) * 100, 2)

        result = StockData(
            symbol      = symbol,
            sector      = SECTOR_MAP.get(symbol, "Diversified"),
            open_price  = first_close,   # shown as "open" in UI; using first close for stability
            close_price = last_close,
            high        = high_p,
            low         = low_p,
            chg_pct     = chg_pct,
            volume      = volume,
            avg_volume  = avg_vol,
            pe_ratio    = pe,
            week52_high = w52h,
            week52_low  = w52l,
            rsi         = rsi_val,
            beta        = beta,
            div_yield   = div_yld,
            mkt_cap_b   = mkt_cap,
            days        = days,
        )

    except Exception:
        result = None

    _FETCH_CACHE[cache_key] = result   # BUG 3 FIX: store in cache
    return result


# ── Public API ────────────────────────────────────────────────────────────────
def fetch_all_stocks(from_date: date, to_date: date) -> List[StockData]:
    """Fetch all 50 Nifty stocks. Returns list sorted by chg_pct descending."""
    stocks = []
    for sym in NIFTY50_SYMBOLS:
        s = _fetch_single_stock(sym, from_date, to_date)
        if s is not None:
            stocks.append(s)
    stocks.sort(key=lambda s: s.chg_pct, reverse=True)
    return stocks


def fetch_all_stocks_with_status(
    from_date: date,
    to_date:   date,
) -> Generator[Tuple[str, int, Optional[StockData]], None, None]:
    """
    Generator yielding (symbol, index, StockData_or_None) one at a time.
    Used by app.py to drive the Streamlit progress bar.
    All results are cached — repeat calls on same date range are instant.
    """
    for i, sym in enumerate(NIFTY50_SYMBOLS):
        yield sym, i, _fetch_single_stock(sym, from_date, to_date)


def clear_cache() -> None:
    """Clear the fetch cache. Call this if you want fresh data for all tickers."""
    _FETCH_CACHE.clear()


def get_cache_size() -> int:
    """Returns number of cached ticker entries."""
    return len(_FETCH_CACHE)


def get_top_gainers(stocks: List[StockData], n: int = 10) -> List[StockData]:
    return stocks[:n]


def get_top_losers(stocks: List[StockData], n: int = 10) -> List[StockData]:
    return list(reversed(stocks[-n:]))


def get_date_range_label(from_date: date, to_date: date) -> str:
    fmt = "%d %b %Y"
    return f"{from_date.strftime(fmt)} – {to_date.strftime(fmt)}"


def trading_days_estimate(calendar_days: int) -> int:
    return round(calendar_days * 5 / 7)
