"""
backend/data.py
Fetches OHLCV data from Yahoo Finance and computes all technical +
sentiment-proxy indicators.

New in v4:
  - fetch_nifty()      — downloads Nifty 50 index for market-relative features
  - compute_stats()    — now returns 9 extra sentiment-proxy fields:
                         overnight_gap, intraday_range, close_loc,
                         news_event, sentiment_3d, big_gap_5d,
                         stock_vs_mkt, stock_rs5
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from backend.constants import STOCKS, INDEX_UNIVERSE


# ── Helpers ────────────────────────────────────────────────────────────────────

def _download(ticker: str, start: str, end: str) -> pd.DataFrame:
    """Shared yfinance download with MultiIndex column flattening."""
    try:
        df = yf.download(ticker, start=start, end=end,
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.columns = [str(c).strip() for c in df.columns]  # normalise column names
        return df.dropna()
    except Exception:
        return pd.DataFrame()


# ── Nifty index (cached 24h — used for market-relative features) ───────────────

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_nifty(start: str, end: str) -> pd.Series:
    """
    Download Nifty 50 index close prices for the given range.
    Returns a Series indexed by date. Cached 24h.
    """
    df = _download("^NSEI", start, end)
    if df.empty or "Close" not in df.columns:
        return pd.Series(dtype=float)
    return df["Close"].astype(float)


# ── Per-stock OHLCV (cached 1h — user date range) ─────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Single cached yfinance download per (symbol, start, end).
    end = to_date + 1 day because Yahoo's end is exclusive.
    Hard-clips result so no rows beyond to_date leak through.
    """
    try:
        df = yf.download(f"{symbol}.NS", start=start, end=end,
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[df.index <= pd.Timestamp(end) - pd.Timedelta(days=1)]
        return df
    except Exception:
        return pd.DataFrame()


# ── Feature computation ────────────────────────────────────────────────────────

def compute_stats(symbol: str, sector: str, df: pd.DataFrame,
                  nifty_cl: pd.Series | None = None) -> dict | None:
    """
    Compute all technical + sentiment-proxy features from OHLCV.
    Returns None if data is insufficient (< 5 rows).

    Sentiment proxies (derived purely from OHLCV — no external data):
      overnight_gap   — open vs prev close: overnight news reaction
      intraday_range  — high-low range: intraday uncertainty / news volatility
      close_loc       — where close sits in day's range (0=low, 1=high)
      news_event      — gap magnitude × volume surge: news event score
      sentiment_3d    — 3-day cumulative overnight gaps: short news trend
      big_gap_5d      — max gap in last 5 days: recent event flag

    Market-relative (requires nifty_cl):
      stock_vs_mkt    — stock 1-day return minus Nifty return
      stock_rs5       — stock 5-day return minus Nifty 5-day return
    """
    if df.empty or len(df) < 5:
        return None

    cl  = df["Close"].astype(float)
    hi  = df["High"].astype(float)
    lo  = df["Low"].astype(float)
    op  = df["Open"].astype(float)
    vol = df["Volume"].astype(float)

    first_c = float(cl.iloc[0])
    last_c  = float(cl.iloc[-1])
    if first_c == 0:
        return None

    p_high = float(hi.max())
    p_low  = float(lo.min())
    avg_v  = float(vol.mean())
    last_v = float(vol.iloc[-1])

    # Period return
    chg = round((last_c - first_c) / first_c * 100, 2)

    # RSI(14)
    rsi = 50.0
    if len(cl) >= 15:
        d    = cl.diff().dropna()
        gain = d.clip(lower=0).rolling(14).mean().iloc[-1]
        loss = (-d).clip(lower=0).rolling(14).mean().iloc[-1]
        rsi  = round(100 - 100 / (1 + gain / loss), 1) if loss > 0 else 100.0

    # MACD(12, 26, 9)
    ema12  = cl.ewm(span=12, adjust=False).mean()
    ema26  = cl.ewm(span=26, adjust=False).mean()
    macd_v = float((ema12 - ema26).iloc[-1])
    sig_v  = float((ema12 - ema26).ewm(span=9, adjust=False).mean().iloc[-1])
    macd_x = 1 if macd_v > sig_v else -1

    # Bollinger Band position
    bb_pos = 50.0
    if len(cl) >= 20:
        mid = cl.rolling(20).mean().iloc[-1]
        std = cl.rolling(20).std().iloc[-1]
        if std > 0:
            bb_pos = round((last_c - (mid - 2 * std)) / (4 * std) * 100, 1)

    # Position in period range
    rng     = p_high - p_low
    pos_rng = round((last_c - p_low) / rng * 100, 1) if rng > 0 else 50.0

    # Volatility & 5-day momentum
    rets  = cl.pct_change().dropna()
    volat = round(float(rets.std() * 100), 2)
    mom5  = round(float(
        (cl.iloc[-1] - cl.iloc[-min(5, len(cl))]) / cl.iloc[-min(5, len(cl))] * 100
    ), 2)

    vol_ratio = round(last_v / avg_v, 2) if avg_v > 0 else 1.0

    # ── SENTIMENT PROXY FEATURES ───────────────────────────────────────────

    # Overnight gap: how did stock open vs yesterday's close?
    # Captures after-hours news, earnings, global cues
    if len(cl) >= 2:
        overnight_gaps = (op / cl.shift(1) - 1) * 100
        last_gap       = float(overnight_gaps.iloc[-1])
        sentiment_3d   = round(float(overnight_gaps.iloc[-3:].sum()), 2)
        big_gap_5d     = round(float(overnight_gaps.abs().iloc[-5:].max()), 2)
    else:
        last_gap = sentiment_3d = big_gap_5d = 0.0

    # Intraday range: high-low / close — measures news uncertainty
    last_hi  = float(hi.iloc[-1])
    last_lo  = float(lo.iloc[-1])
    intraday_range = round((last_hi - last_lo) / last_c * 100, 2) if last_c > 0 else 0.0

    # Close location in day's range (0 = closed at low, 1 = closed at high)
    day_rng   = last_hi - last_lo
    close_loc = round((last_c - last_lo) / day_rng, 3) if day_rng > 0 else 0.5

    # News event score: gap magnitude × log(volume surge)
    news_event = round(abs(last_gap) * float(np.log1p(vol_ratio)), 3)

    # ── MARKET-RELATIVE FEATURES ───────────────────────────────────────────

    stock_vs_mkt = 0.0
    stock_rs5    = 0.0

    if nifty_cl is not None and not nifty_cl.empty and len(cl) >= 2:
        # Align Nifty to stock dates
        nifty_aligned = nifty_cl.reindex(cl.index, method="ffill")

        if len(nifty_aligned.dropna()) >= 2:
            nifty_ret_1d  = float(nifty_aligned.pct_change().iloc[-1]) * 100
            stock_ret_1d  = float(cl.pct_change().iloc[-1]) * 100
            stock_vs_mkt  = round(stock_ret_1d - nifty_ret_1d, 3)

            if len(cl) >= 6:
                nifty_ret_5d = float(nifty_aligned.pct_change(5).iloc[-1]) * 100
                stock_ret_5d = float(cl.pct_change(5).iloc[-1]) * 100
                stock_rs5    = round(stock_ret_5d - nifty_ret_5d, 3)

    return dict(
        # Identity
        symbol=symbol, sector=sector,
        # Price summary
        period_high=round(p_high, 2), period_low=round(p_low, 2),
        first_close=round(first_c, 2), last_close=round(last_c, 2),
        # Technical features
        change_pct=chg, rsi=rsi,
        macd=round(macd_v, 2), macd_cross=macd_x, bb_pos=bb_pos,
        pos_in_range=pos_rng, volatility=volat,
        mom5=mom5, vol_ratio=vol_ratio,
        avg_volume=int(avg_v), last_volume=int(last_v),
        # Sentiment proxy features
        overnight_gap=round(last_gap, 3),
        intraday_range=intraday_range,
        close_loc=close_loc,
        news_event=news_event,
        sentiment_3d=sentiment_3d,
        big_gap_5d=big_gap_5d,
        # Market-relative features
        stock_vs_mkt=stock_vs_mkt,
        stock_rs5=stock_rs5,
    )


# ── Batch fetch ────────────────────────────────────────────────────────────────

def fetch_all(from_d: date, to_d: date,
              progress_callback=None,
              stocks: dict[str, str] | None = None) -> list[dict]:
    """
    Fetch and compute stats for the given stock universe.
    stocks: dict of {symbol: sector}. Defaults to STOCKS (Nifty 50).
    Calls progress_callback(i, symbol, total) on each iteration if provided.
    """
    universe = stocks if stocks is not None else STOCKS
    total    = len(universe)
    start    = str(from_d)
    end      = str(to_d + timedelta(days=1))

    # Fetch Nifty index for market-relative features
    nifty_cl = fetch_nifty(start, end)

    out = []
    for i, (sym, sec) in enumerate(universe.items()):
        if progress_callback:
            progress_callback(i, sym, total)
        df  = fetch_ohlcv(sym, start, end)
        row = compute_stats(sym, sec, df, nifty_cl=nifty_cl)
        if row:
            out.append(row)

    return out
