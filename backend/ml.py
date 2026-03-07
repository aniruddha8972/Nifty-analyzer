"""
backend/ml.py
─────────────────────────────────────────────────────────────────────
Proper ML pipeline with real historical training data.

HOW IT WORKS
────────────
1. fetch_history()  — downloads 3 years of daily OHLCV for all 50 stocks
                      (cached 24h, separate from the user's date range)

2. build_dataset()  — vectorised rolling-window feature extraction:
                      every trading day per stock = one training row.
                      Features = 8 technical indicators
                      Target   = actual 10-day forward return (%)
                      ~35,000–40,000 real labelled rows

3. _get_trained_models() — fits RF + GB + Ridge on the full history.
                           Cached with @st.cache_resource so it only
                           retrains when the Streamlit process restarts
                           or when the 24h data TTL expires.

4. predict()        — computes today's features for each stock, runs
                      them through the trained ensemble, blends with
                      news sentiment, returns enriched stat dicts.

DATA COUNTS
───────────
  50 stocks × ~750 trading days (3 years) = ~37,500 training rows
  After warmup (30 bars) + forward window (10 bars): ~35,000 rows
"""

import re
from datetime import date, timedelta

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.constants import FREE_RSS, NEG_WORDS, POS_WORDS, SECTOR_SCORE, STOCKS

HISTORY_YEARS = 3
FORWARD_DAYS  = 10
WARMUP_BARS   = 30
FEATURE_COLS  = ["rsi","macd_x","bb_pos","pos_rng","mom5","vol_ratio","volatility","sector"]


# ══════════════════════════════════════════════════════════════════════
#  STEP 1 — Fetch 3-year history (cached 24h)
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_history(symbol: str) -> pd.DataFrame:
    """Download 3 years of daily OHLCV. Cached 24h, independent of user range."""
    end   = date.today()
    start = end - timedelta(days=365 * HISTORY_YEARS + 30)
    try:
        df = yf.download(
            f"{symbol}.NS",
            start=str(start),
            end=str(end + timedelta(days=1)),
            auto_adjust=True,
            progress=False,
        )
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


# ══════════════════════════════════════════════════════════════════════
#  STEP 2 — Vectorised rolling feature extraction
# ══════════════════════════════════════════════════════════════════════

def _extract_features(df: pd.DataFrame, sector_score: int) -> pd.DataFrame:
    """
    Every row in the output = one trading day = one training sample.
    Features are computed on the window ending that day.
    Target = actual 10-day forward return.
    """
    cl  = df["Close"].astype(float)
    hi  = df["High"].astype(float)
    lo  = df["Low"].astype(float)
    vol = df["Volume"].astype(float)

    # RSI(14) — EWM approximation, fully vectorised
    delta = cl.diff()
    gain  = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss  = (-delta).clip(lower=0).ewm(com=13, adjust=False).mean()
    rsi   = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)

    # MACD(12, 26, 9) cross: +1 bullish, -1 bearish
    ema12     = cl.ewm(span=12, adjust=False).mean()
    ema26     = cl.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_sig  = macd_line.ewm(span=9, adjust=False).mean()
    macd_x    = (macd_line > macd_sig).astype(int) * 2 - 1

    # Bollinger Band position (0=bottom band, 100=top band)
    bb_mid = cl.rolling(20).mean()
    bb_std = cl.rolling(20).std().replace(0, np.nan)
    bb_pos = ((cl - (bb_mid - 2 * bb_std)) / (4 * bb_std) * 100).fillna(50)

    # Position in 20-day high-low range
    h20     = hi.rolling(20).max()
    l20     = lo.rolling(20).min()
    rng20   = (h20 - l20).replace(0, np.nan)
    pos_rng = ((cl - l20) / rng20 * 100).fillna(50)

    # 5-day momentum
    mom5 = cl.pct_change(5) * 100

    # Volume ratio: today vs 20-day avg
    avg_vol   = vol.rolling(20).mean().replace(0, np.nan)
    vol_ratio = (vol / avg_vol).fillna(1.0)

    # 20-day rolling volatility
    volat = cl.pct_change().rolling(20).std() * 100

    # Target: actual 10-day forward return (the real label)
    fwd_ret = (cl.shift(-FORWARD_DAYS) / cl - 1) * 100

    out = pd.DataFrame({
        "rsi":        rsi,
        "macd_x":     macd_x.astype(float),
        "bb_pos":     bb_pos,
        "pos_rng":    pos_rng,
        "mom5":       mom5,
        "vol_ratio":  vol_ratio,
        "volatility": volat,
        "sector":     float(sector_score),
        "fwd_ret":    fwd_ret,
    }, index=df.index)

    # Drop warmup rows and any row without a valid forward return
    return out.iloc[WARMUP_BARS:].dropna()


# ══════════════════════════════════════════════════════════════════════
#  STEP 3 — Build full training dataset (50 stocks × 3 years)
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=86400, show_spinner=False)
def build_dataset() -> tuple:
    """
    Fetch 3-year history for all 50 stocks and build the training dataset.
    Returns (X, y, n_rows):
      X: (n_rows, 8) feature matrix
      y: (n_rows,)   10-day forward returns
      n_rows ~ 35,000–40,000
    """
    frames = []
    for sym, sec in STOCKS.items():
        df = fetch_history(sym)
        if df.empty or len(df) < WARMUP_BARS + FORWARD_DAYS + 5:
            continue
        feat = _extract_features(df, SECTOR_SCORE.get(sec, 2))
        if not feat.empty:
            frames.append(feat)

    if not frames:
        return np.empty((0, 8)), np.empty(0), 0

    combined = pd.concat(frames, ignore_index=True)
    X = combined[FEATURE_COLS].values.astype(float)
    y = combined["fwd_ret"].values.astype(float)
    return X, y, len(combined)


# ══════════════════════════════════════════════════════════════════════
#  STEP 4 — Train ensemble (cached in memory, only trains once)
# ══════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def _get_trained_models():
    """
    Trains RF + GB + Ridge on ~35,000 historical rows.
    @st.cache_resource keeps fitted objects in memory across reruns.
    Training time: ~15-25s on first load, then instant from cache.
    """
    X, y, n_rows = build_dataset()

    if n_rows < 100:
        return None, None, None, n_rows

    rf = Pipeline([
        ("sc", StandardScaler()),
        ("m",  RandomForestRegressor(
            n_estimators=100, max_depth=4,
            min_samples_leaf=10, random_state=42, n_jobs=1,
        )),
    ])
    gb = Pipeline([
        ("sc", StandardScaler()),
        ("m",  GradientBoostingRegressor(
            n_estimators=100, max_depth=3,
            learning_rate=0.08, subsample=0.8, random_state=42,
        )),
    ])
    ridge = Pipeline([("sc", StandardScaler()), ("m", Ridge(alpha=1.0))])

    rf.fit(X, y)
    gb.fit(X, y)
    ridge.fit(X, y)

    return rf, gb, ridge, n_rows


# ══════════════════════════════════════════════════════════════════════
#  NEWS SENTIMENT — free RSS, no API key
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_sentiment(symbols: tuple) -> dict:
    """Scrape free RSS feeds for stock sentiment. Falls back to 0.0."""
    import requests
    from bs4 import BeautifulSoup

    headlines = []
    for url in FREE_RSS:
        try:
            r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.content, "lxml-xml")
            for tag in soup.find_all(["title", "description"])[:60]:
                if tag.text:
                    headlines.append(tag.text.lower())
        except Exception:
            pass

    result = {}
    for sym in symbols:
        relevant = [h for h in headlines if sym.lower() in h]
        if not relevant:
            result[sym] = 0.0
            continue
        words = re.findall(r"\b\w+\b", " ".join(relevant))
        p = sum(1 for w in words if w in POS_WORDS)
        n = sum(1 for w in words if w in NEG_WORDS)
        result[sym] = round((p - n) / (p + n), 2) if (p + n) > 0 else 0.0

    return result


# ══════════════════════════════════════════════════════════════════════
#  STEP 5 — Map stat dict to feature vector
# ══════════════════════════════════════════════════════════════════════

def _stat_to_features(s: dict) -> np.ndarray:
    """Convert a current stat dict into the same 8-feature vector used in training."""
    return np.array([[
        s["rsi"],
        float(s["macd_cross"]),
        s["bb_pos"],
        s["pos_in_range"],
        s["mom5"],
        s["vol_ratio"],
        s["volatility"],
        float(SECTOR_SCORE.get(s["sector"], 2)),
    ]], dtype=float)


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def predict(stats: list[dict]) -> list[dict]:
    """
    Score every stock using the historically-trained ensemble.
    Adds ml_score, sentiment, final_score, predicted_return,
    signal, sig_color, training_rows to each stat dict.
    """
    if not stats:
        return stats

    rf, gb, ridge, n_rows = _get_trained_models()

    # Fallback if training data unavailable
    if rf is None:
        for s in stats:
            s.update(ml_score=50.0, sentiment=0.0, final_score=50.0,
                     predicted_return=0.0, signal="🟠 HOLD",
                     sig_color="#f59e0b", training_rows=n_rows)
        return stats

    # Predict for each stock using today's features
    raw_preds = []
    for s in stats:
        x    = _stat_to_features(s)
        pred = (0.40 * float(rf.predict(x)[0])
              + 0.40 * float(gb.predict(x)[0])
              + 0.20 * float(ridge.predict(x)[0]))
        raw_preds.append(pred)

    raw = np.array(raw_preds)

    # Normalise to 0–100 score
    mn, mx    = raw.min(), raw.max()
    ml_scores = (raw - mn) / (mx - mn) * 100 if mx > mn else np.full(len(stats), 50.0)

    # News sentiment
    sentiment = fetch_sentiment(tuple(s["symbol"] for s in stats))

    enriched = []
    for s, ml_sc, raw_pred in zip(stats, ml_scores, raw_preds):
        sent  = sentiment.get(s["symbol"], 0.0)
        final = round(float(np.clip(ml_sc * 0.80 + sent * 10 + 10, 0, 100)), 1)

        if   final >= 72: sig, col = "🟢 STRONG BUY", "#10b981"
        elif final >= 55: sig, col = "🟡 BUY",         "#34d399"
        elif final >= 35: sig, col = "🟠 HOLD",        "#f59e0b"
        else:             sig, col = "🔴 AVOID",       "#ef4444"

        enriched.append({
            **s,
            "ml_score":         round(float(ml_sc), 1),
            "sentiment":        sent,
            "final_score":      final,
            "predicted_return": round(float(raw_pred), 2),
            "signal":           sig,
            "sig_color":        col,
            "training_rows":    n_rows,
        })

    return enriched
