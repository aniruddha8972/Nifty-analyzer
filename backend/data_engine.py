"""
backend/data_engine.py
──────────────────────
╔══════════════════════════════════════════════════════════════════╗
║  CHANGED FROM PREVIOUS VERSION                                   ║
║  ─────────────────────────────────────────────────────────────   ║
║  OLD: deterministic math.sin() fake data generator              ║
║  NEW: real market data fetched via yfinance (Yahoo Finance API)  ║
║                                                                  ║
║  Key changes made in this file:                                  ║
║  1. Removed: _rng(), _sym_seed(), _date_seed() — fake RNG gone  ║
║  2. Removed: generate_stock() — single fake stock builder gone  ║
║  3. Added:   YF_SUFFIX map — NSE ticker suffix (.NS)            ║
║  4. Added:   _compute_rsi() — real RSI from price history       ║
║  5. Added:   _fetch_single_stock() — yfinance per-stock fetch   ║
║  6. Changed: fetch_all_stocks() — now calls yfinance in batch   ║
║  7. Added:   fetch_all_stocks_with_status() — yields progress   ║
╚══════════════════════════════════════════════════════════════════╝

yfinance maps NSE symbols using the ".NS" suffix.
Example: RELIANCE → RELIANCE.NS on Yahoo Finance.

All other files (ai_model.py, app.py, frontend/, pipeline/) are
UNCHANGED — StockData fields remain identical so nothing else breaks.
"""

from datetime import date, timedelta
from typing import Dict, Generator, List, Optional, Tuple
import warnings

import yfinance as yf
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)


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

# ── CHANGED: NSE ticker suffix map ───────────────────────────────────────────
# Yahoo Finance requires ".NS" appended to NSE symbols.
# Special cases handled explicitly (e.g. BAJAJ-AUTO → BAJAJ-AUTO.NS works fine).
YF_SUFFIX = ".NS"

def _to_yf_ticker(symbol: str) -> str:
    """Convert NSE symbol to Yahoo Finance ticker. e.g. RELIANCE → RELIANCE.NS"""
    return f"{symbol}{YF_SUFFIX}"


# ── Stock data model (UNCHANGED — same fields as before) ─────────────────────
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


# ── CHANGED: RSI computed from real price history ────────────────────────────
def _compute_rsi(closes: pd.Series, period: int = 14) -> float:
    """
    Compute RSI(14) from a pandas Series of closing prices.
    Returns 50.0 as neutral fallback if not enough data.
    """
    if len(closes) < period + 1:
        return 50.0
    delta = closes.diff().dropna()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_gain = gain.rolling(window=period).mean().iloc[-1]
    avg_loss = loss.rolling(window=period).mean().iloc[-1]
    if avg_loss == 0:
        return 100.0
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi), 1)


# ── CHANGED: real data fetch per stock via yfinance ──────────────────────────
def _fetch_single_stock(
    symbol: str,
    from_date: date,
    to_date: date,
) -> Optional[StockData]:
    """
    Fetch real OHLCV + metadata from Yahoo Finance for one NSE symbol.
    Returns None if Yahoo Finance returns no data (e.g. delisted / bad ticker).

    yfinance calls made:
      - yf.Ticker(symbol).history(start, end)   → OHLCV rows for the period
      - yf.Ticker(symbol).info                  → PE, beta, 52W H/L, mktCap, div
    We also fetch 1 extra year of history for RSI(14) calculation.
    """
    ticker_str = _to_yf_ticker(symbol)
    days = (to_date - from_date).days
    if days <= 0:
        raise ValueError(f"to_date must be after from_date (got {days} days)")

    try:
        ticker = yf.Ticker(ticker_str)

        # ── Period OHLCV (the user's chosen date range) ───────────────────────
        hist = ticker.history(
            start = from_date.strftime("%Y-%m-%d"),
            end   = (to_date + timedelta(days=1)).strftime("%Y-%m-%d"),  # end is exclusive
            auto_adjust = True,
        )
        if hist.empty:
            return None

        open_p  = round(float(hist["Open"].iloc[0]),   2)
        close_p = round(float(hist["Close"].iloc[-1]), 2)
        high_p  = round(float(hist["High"].max()),     2)
        low_p   = round(float(hist["Low"].min()),      2)
        volume  = int(hist["Volume"].iloc[-1])           # last day volume
        avg_vol = int(hist["Volume"].mean())             # avg over period

        chg_pct = round(((close_p - open_p) / open_p) * 100, 2) if open_p else 0.0

        # ── RSI — fetch 1 year of daily closes for accuracy ───────────────────
        rsi_start = from_date - timedelta(days=365)
        rsi_hist  = ticker.history(
            start = rsi_start.strftime("%Y-%m-%d"),
            end   = (to_date + timedelta(days=1)).strftime("%Y-%m-%d"),
            auto_adjust = True,
        )
        rsi_val = _compute_rsi(rsi_hist["Close"]) if not rsi_hist.empty else 50.0

        # ── Fundamentals from ticker.info ─────────────────────────────────────
        info    = ticker.info  # single network call, cached by yfinance

        pe      = round(float(info.get("trailingPE")       or info.get("forwardPE") or 20.0), 1)
        beta    = round(float(info.get("beta")             or 1.0),  2)
        w52h    = round(float(info.get("fiftyTwoWeekHigh") or high_p * 1.2), 2)
        w52l    = round(float(info.get("fiftyTwoWeekLow")  or low_p  * 0.8), 2)
        mkt_cap = round(float(info.get("marketCap")        or 0) / 1e9, 1)
        div_yld = round(float(info.get("dividendYield")    or 0) * 100, 2)  # yfinance gives ratio

        return StockData(
            symbol      = symbol,
            sector      = SECTOR_MAP.get(symbol, "Diversified"),
            open_price  = open_p,
            close_price = close_p,
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
        # Never crash the whole app for one bad ticker — return None and skip
        return None


# ── CHANGED: batch fetch all 50 stocks ───────────────────────────────────────
def fetch_all_stocks(from_date: date, to_date: date) -> List[StockData]:
    """
    Fetch real market data for all 50 Nifty stocks via yfinance.
    Skips any symbol that returns no data (logs nothing — silent skip).
    Returns list sorted by chg_pct descending.
    """
    stocks: List[StockData] = []
    for sym in NIFTY50_SYMBOLS:
        s = _fetch_single_stock(sym, from_date, to_date)
        if s is not None:
            stocks.append(s)
    stocks.sort(key=lambda s: s.chg_pct, reverse=True)
    return stocks


# ── CHANGED: generator version for Streamlit progress bar ────────────────────
def fetch_all_stocks_with_status(
    from_date: date,
    to_date:   date,
) -> Generator[Tuple[str, int, Optional[StockData]], None, None]:
    """
    Generator that yields (symbol, index, StockData_or_None) one at a time.
    Used by app.py to drive a Streamlit progress bar while fetching.

    Usage in app.py:
        results = []
        for sym, i, data in fetch_all_stocks_with_status(f, t):
            progress_bar.progress((i+1) / 50, text=f"Fetching {sym}...")
            if data: results.append(data)
    """
    for i, sym in enumerate(NIFTY50_SYMBOLS):
        s = _fetch_single_stock(sym, from_date, to_date)
        yield sym, i, s


# ── Unchanged helpers ─────────────────────────────────────────────────────────
def get_top_gainers(stocks: List[StockData], n: int = 10) -> List[StockData]:
    return stocks[:n]


def get_top_losers(stocks: List[StockData], n: int = 10) -> List[StockData]:
    return list(reversed(stocks[-n:]))


def get_date_range_label(from_date: date, to_date: date) -> str:
    fmt = "%d %b %Y"
    return f"{from_date.strftime(fmt)} – {to_date.strftime(fmt)}"


def trading_days_estimate(calendar_days: int) -> int:
    return round(calendar_days * 5 / 7)
