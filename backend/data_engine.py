"""
backend/data_engine.py
─────────────────────
Nifty 50 data generation engine.
Produces deterministic, date-seeded simulated OHLCV data for all 50 stocks.
In a production setup, swap `generate_stock()` with a real broker API call
(Zerodha Kite, Upstox, NSE official feed, etc.).
"""

import math
from datetime import date, datetime, timedelta
from typing import Dict, List, Tuple

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


# ── RNG (deterministic) ──────────────────────────────────────────────────────
def _rng(s: float) -> float:
    """Simple deterministic pseudo-random in [0, 1) seeded by float."""
    x = math.sin(s) * 10000
    return x - math.floor(x)


def _sym_seed(symbol: str) -> int:
    return sum(ord(c) for c in symbol)


def _date_seed(from_date: date, to_date: date) -> float:
    ts_from = datetime.combine(from_date, datetime.min.time()).timestamp()
    ts_to   = datetime.combine(to_date,   datetime.min.time()).timestamp()
    return ts_from / 1e10 + ts_to / 2.1e11


# ── Stock data model ─────────────────────────────────────────────────────────
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


def generate_stock(symbol: str, from_date: date, to_date: date) -> StockData:
    """
    Generate deterministic simulated OHLCV data for a symbol over a period.
    Output is stable: same inputs always produce same outputs.
    Swap this function body with a real API call for production use.
    """
    days = (to_date - from_date).days
    if days <= 0:
        raise ValueError(f"to_date must be after from_date (got {days} days)")

    seed = _sym_seed(symbol)
    ds   = _date_seed(from_date, to_date)

    base      = 200.0 + _rng(seed + ds) * 3800.0
    max_swing = min(0.65, 0.05 + days * 0.0014)
    chg       = (_rng(seed * 7 + ds * 3) - 0.48) * max_swing

    open_p  = round(base, 2)
    close_p = round(base * (1 + chg), 2)
    high_p  = round(max(open_p, close_p) * (1 + _rng(seed * 3 + ds) * 0.05), 2)
    low_p   = round(min(open_p, close_p) * (1 - _rng(seed * 5 + ds) * 0.04), 2)

    vol     = int(500_000 + _rng(seed * 11 + ds) * 9_500_000)
    avg_vol = int(vol * (0.75 + _rng(seed * 37) * 0.5))

    pe      = round(12.0 + _rng(seed * 17) * 38.0, 1)
    w52h    = round(close_p * (1 + _rng(seed * 19) * 0.45), 2)
    w52l    = round(close_p * (1 - _rng(seed * 23) * 0.35), 2)
    rsi     = round(30.0 + _rng(seed * 29 + ds) * 55.0, 1)
    beta    = round(0.5  + _rng(seed * 31) * 1.5, 2)
    div     = round(_rng(seed * 41) * 3.5, 2)
    mkt_cap = round(close_p * (1e9 + _rng(seed * 13) * 9e11) / 1e9, 1)

    return StockData(
        symbol      = symbol,
        sector      = SECTOR_MAP.get(symbol, "Diversified"),
        open_price  = open_p,
        close_price = close_p,
        high        = high_p,
        low         = low_p,
        chg_pct     = round(chg * 100, 2),
        volume      = vol,
        avg_volume  = avg_vol,
        pe_ratio    = pe,
        week52_high = w52h,
        week52_low  = w52l,
        rsi         = rsi,
        beta        = beta,
        div_yield   = div,
        mkt_cap_b   = mkt_cap,
        days        = days,
    )


def fetch_all_stocks(from_date: date, to_date: date) -> List[StockData]:
    """Return StockData for every Nifty 50 symbol, sorted by chg_pct descending."""
    stocks = [generate_stock(sym, from_date, to_date) for sym in NIFTY50_SYMBOLS]
    stocks.sort(key=lambda s: s.chg_pct, reverse=True)
    return stocks


def get_top_gainers(stocks: List[StockData], n: int = 10) -> List[StockData]:
    return stocks[:n]


def get_top_losers(stocks: List[StockData], n: int = 10) -> List[StockData]:
    return list(reversed(stocks[-n:]))


def get_date_range_label(from_date: date, to_date: date) -> str:
    fmt = "%d %b %Y"
    return f"{from_date.strftime(fmt)} – {to_date.strftime(fmt)}"


def trading_days_estimate(calendar_days: int) -> int:
    return round(calendar_days * 5 / 7)
