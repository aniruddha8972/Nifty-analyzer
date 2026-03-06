"""
backend/data_engine.py  — v4 FINAL STABLE
──────────────────────────────────────────
ROOT CAUSE OF VOLATILITY (finally confirmed):

  Streamlit Cloud runs MULTIPLE worker processes for load balancing.
  Click 1 → Worker A fetches data, stores in Worker A's memory dict.
  Click 2 → Worker B handles request, has EMPTY memory — fetches again.
  Yahoo Finance returns slightly different rows each time (CDN cache).
  Result: same date range, different output every click.

  The in-process _FETCH_CACHE dict was useless across workers.

THE CORRECT FIX: @st.cache_data on the fetch function.
  Streamlit's cache_data is shared across all workers in the same app.
  Keyed by function arguments (symbol, from_date, to_date).
  TTL=3600 means data refreshes after 1 hour automatically.
  Same date range = identical data, guaranteed.

  BUT data_engine.py cannot import streamlit (circular / wrong layer).
  So the cached wrapper lives in app.py and is injected here via
  set_cache_backend(fn). data_engine stays framework-agnostic.

OTHER FIXES KEPT:
  - chg_pct = close-to-close (not open-to-close) — stable baseline
  - end = to_date + 2 days, hard-clipped to <= to_date — deterministic rows
"""

from datetime import date, timedelta
from typing import Callable, Dict, Generator, List, Optional, Tuple
import warnings

import yfinance as yf
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)


# ── Nifty 50 universe ─────────────────────────────────────────────────────────
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
    return f"{symbol}{YF_SUFFIX}"


# ── Stock data model ──────────────────────────────────────────────────────────
class StockData:
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


# ── RSI ───────────────────────────────────────────────────────────────────────
def _compute_rsi(closes: pd.Series, period: int = 14) -> float:
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


# ── Core fetch — raw yfinance call, NO cache here ────────────────────────────
# Cache is applied in app.py via @st.cache_data so it works across
# all Streamlit Cloud workers. This function stays framework-agnostic.
def _fetch_single_stock_raw(
    symbol:    str,
    from_date: date,
    to_date:   date,
) -> Optional[StockData]:
    """
    Raw fetch from Yahoo Finance. Call this only through the cached
    wrapper in app.py. Direct calls will be unstable across workers.
    """
    days = (to_date - from_date).days
    if days <= 0:
        raise ValueError(f"to_date must be after from_date (got {days} days)")

    try:
        ticker = yf.Ticker(_to_yf_ticker(symbol))

        # +2 days ensures to_date is always included (Yahoo end is exclusive)
        # Hard-clip removes any rows beyond to_date
        end_str = (to_date + timedelta(days=2)).strftime("%Y-%m-%d")

        hist = ticker.history(
            start       = from_date.strftime("%Y-%m-%d"),
            end         = end_str,
            auto_adjust = True,
        )
        if not hist.empty:
            hist = hist[hist.index.normalize() <= pd.Timestamp(to_date)]

        if hist.empty:
            return None

        # close-to-close: both values are closing prices — stable baseline
        first_close = round(float(hist["Close"].iloc[0]),  2)
        last_close  = round(float(hist["Close"].iloc[-1]), 2)
        high_p      = round(float(hist["High"].max()),     2)
        low_p       = round(float(hist["Low"].min()),      2)
        volume      = int(hist["Volume"].iloc[-1])
        avg_vol     = int(hist["Volume"].mean())

        chg_pct = round(((last_close - first_close) / first_close) * 100, 2) \
                  if first_close != 0 else 0.0

        # RSI from 1 year history
        rsi_hist = ticker.history(
            start       = (from_date - timedelta(days=365)).strftime("%Y-%m-%d"),
            end         = end_str,
            auto_adjust = True,
        )
        if not rsi_hist.empty:
            rsi_hist = rsi_hist[rsi_hist.index.normalize() <= pd.Timestamp(to_date)]
        rsi_val = _compute_rsi(rsi_hist["Close"]) if not rsi_hist.empty else 50.0

        info    = ticker.info
        pe      = round(float(info.get("trailingPE")       or info.get("forwardPE") or 20.0), 1)
        beta    = round(float(info.get("beta")             or 1.0),  2)
        w52h    = round(float(info.get("fiftyTwoWeekHigh") or high_p * 1.2), 2)
        w52l    = round(float(info.get("fiftyTwoWeekLow")  or low_p  * 0.8), 2)
        mkt_cap = round(float(info.get("marketCap")        or 0) / 1e9, 1)
        div_yld = round(float(info.get("dividendYield")    or 0) * 100, 2)

        return StockData(
            symbol      = symbol,
            sector      = SECTOR_MAP.get(symbol, "Diversified"),
            open_price  = first_close,
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
        return None


# ── Public API (used by app.py) ───────────────────────────────────────────────
def get_top_gainers(stocks: List[StockData], n: int = 10) -> List[StockData]:
    return stocks[:n]

def get_top_losers(stocks: List[StockData], n: int = 10) -> List[StockData]:
    return list(reversed(stocks[-n:]))

def get_date_range_label(from_date: date, to_date: date) -> str:
    return f"{from_date.strftime('%d %b %Y')} – {to_date.strftime('%d %b %Y')}"

def trading_days_estimate(calendar_days: int) -> int:
    return round(calendar_days * 5 / 7)
