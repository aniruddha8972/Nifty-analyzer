"""
backend/data.py
Fetches OHLCV data from Yahoo Finance and computes all technical indicators.
No logic changes from the working version — only structure.
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from backend.constants import STOCKS


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    """
    Single cached yfinance download per (symbol, start, end).
    end = to_date + 1 day because Yahoo's end is exclusive.
    Hard-clips result so no rows beyond to_date ever leak through.
    """
    try:
        df = yf.download(
            f"{symbol}.NS",
            start=start,
            end=end,
            auto_adjust=True,
            progress=False,
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df[df.index <= pd.Timestamp(end) - pd.Timedelta(days=1)]
        return df
    except Exception:
        return pd.DataFrame()


def compute_stats(symbol: str, sector: str, df: pd.DataFrame) -> dict | None:
    """
    Compute all technical features from a clean OHLCV DataFrame.
    Returns None if data is insufficient (< 3 rows).
    """
    if df.empty or len(df) < 3:
        return None

    cl  = df["Close"].astype(float)
    hi  = df["High"].astype(float)
    lo  = df["Low"].astype(float)
    vol = df["Volume"].astype(float)

    first_c = float(cl.iloc[0])
    last_c  = float(cl.iloc[-1])
    if first_c == 0:
        return None

    p_high = float(hi.max())
    p_low  = float(lo.min())
    avg_v  = float(vol.mean())
    last_v = float(vol.iloc[-1])

    # Period return: close-to-close, both from the same metric
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

    # Volatility and 5-day momentum
    rets  = cl.pct_change().dropna()
    volat = round(float(rets.std() * 100), 2)
    mom5  = round(float(
        (cl.iloc[-1] - cl.iloc[-min(5, len(cl))]) / cl.iloc[-min(5, len(cl))] * 100
    ), 2)

    vol_ratio = round(last_v / avg_v, 2) if avg_v > 0 else 1.0

    return dict(
        symbol=symbol, sector=sector,
        period_high=round(p_high, 2), period_low=round(p_low, 2),
        first_close=round(first_c, 2), last_close=round(last_c, 2),
        change_pct=chg, rsi=rsi,
        macd=round(macd_v, 2), macd_cross=macd_x, bb_pos=bb_pos,
        pos_in_range=pos_rng, volatility=volat,
        mom5=mom5, vol_ratio=vol_ratio,
        avg_volume=int(avg_v), last_volume=int(last_v),
    )


def fetch_all(from_d: date, to_d: date, progress_callback=None) -> list[dict]:
    """
    Fetch and compute stats for all 50 Nifty stocks.
    Calls progress_callback(i, symbol) on each iteration if provided.
    """
    end   = str(to_d + timedelta(days=1))
    start = str(from_d)
    out   = []

    for i, (sym, sec) in enumerate(STOCKS.items()):
        if progress_callback:
            progress_callback(i, sym)
        row = compute_stats(sym, sec, fetch_ohlcv(sym, start, end))
        if row:
            out.append(row)

    return out
