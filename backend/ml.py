"""
backend/ml.py  —  v5: 5-year × 500-stock historically-trained ensemble
───────────────────────────────────────────────────────────────────────────────

WHAT CHANGED FROM v4
─────────────────────
v4: 3-year history, only Nifty 50 stocks (~35,000 rows)
v5: 5-year history, full active index universe (up to 500 stocks)
    ~625,000 training rows (500 stocks × 1,250 trading days)
    Dataset built by streaming OHLCV — never holds all DFs in RAM at once
    Models keyed by universe hash — retrain only when index changes
    Memory-efficient: dataset stored as np.ndarray (X, y), not DataFrames
    n_jobs=-1 on RF, lighter GB for speed on large datasets

TRAINING PIPELINE
──────────────────
1. build_dataset(universe)  — stream-fetches 5yr OHLCV per stock,
                               extracts features row-by-row, discards raw DF
2. _get_trained_models(key) — fits RF + GB + Ridge on full dataset,
                               keyed by universe hash so retrains on index switch
3. predict(stats, universe) — scores using today's 17 features

DATA COUNTS (Nifty 500)
────────────────────────
  500 stocks × ~1,250 trading days (5 years) ≈ 625,000 rows
  After warmup (30 bars) + forward window (10 bars) ≈ 590,000 training rows
  17 features × 590,000 rows ≈ 80 MB as float32 ndarray — fits in memory

FEATURE SET (17 features — unchanged from v4)
───────────────────────────────────────────────
  Technical (8):     rsi, macd_x, bb_pos, pos_rng, mom5, vol_ratio, volatility, sector
  Sentiment proxy (7): overnight_gap, intraday_range, close_loc, vol_surge,
                       news_event, sentiment_3d, big_gap_5d
  Market-relative (2): stock_vs_mkt, stock_rs5
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

from backend.constants import (
    FREE_RSS, NEG_WORDS, POS_WORDS, SECTOR_SCORE, STOCKS, INDEX_UNIVERSE
)

# ── Constants ──────────────────────────────────────────────────────────────────
HISTORY_YEARS = 5          # was 3 — now 5
FORWARD_DAYS  = 10
WARMUP_BARS   = 30

FEATURE_COLS = [
    # Technical (8)
    "rsi", "macd_x", "bb_pos", "pos_rng", "mom5",
    "vol_ratio", "volatility", "sector",
    # Sentiment proxies (7)
    "overnight_gap", "intraday_range", "close_loc",
    "vol_surge", "news_event", "sentiment_3d", "big_gap_5d",
    # Market-relative (2)
    "stock_vs_mkt", "stock_rs5",
]


# ══════════════════════════════════════════════════════════════════════
#  STEP 1 — Fetch helpers (cached 24h per symbol)
# ══════════════════════════════════════════════════════════════════════

def _hist_range() -> tuple[str, str]:
    end   = date.today()
    start = end - timedelta(days=365 * HISTORY_YEARS + 60)   # +60 buffer
    return str(start), str(end + timedelta(days=1))


def _safe_df(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Flatten yfinance MultiIndex columns and validate OHLCV presence."""
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        # New yfinance: (field, ticker) layout
        tickers_l1 = df.columns.get_level_values(1).unique().tolist()
        if ticker in tickers_l1:
            df = df.xs(ticker, axis=1, level=1)
        else:
            df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).strip() for c in df.columns]
    needed = {"Open", "High", "Low", "Close", "Volume"}
    if not needed.issubset(df.columns):
        return pd.DataFrame()
    for col in needed:
        s = df[col]
        if isinstance(s, pd.DataFrame):
            df[col] = s.iloc[:, 0]
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df[list(needed)].dropna()


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_history(symbol: str) -> pd.DataFrame:
    """5 years of daily OHLCV for one stock. Cached 24h per symbol."""
    start, end = _hist_range()
    ticker = f"{symbol}.NS"
    try:
        raw = yf.download(ticker, start=start, end=end,
                          auto_adjust=True, progress=False)
        return _safe_df(raw, ticker)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_nifty_history() -> pd.Series:
    """5 years of Nifty 50 daily closes. Cached 24h."""
    start, end = _hist_range()
    try:
        raw = yf.download("^NSEI", start=start, end=end,
                          auto_adjust=True, progress=False)
        df = _safe_df(raw, "^NSEI")
        if df.empty:
            return pd.Series(dtype=float)
        return df["Close"].astype(float).dropna()
    except Exception:
        return pd.Series(dtype=float)


# ══════════════════════════════════════════════════════════════════════
#  STEP 2 — Vectorised feature extraction (per stock, returns np.ndarray)
# ══════════════════════════════════════════════════════════════════════

def _extract_features_array(df: pd.DataFrame,
                             nifty_cl: pd.Series,
                             sector_score: int) -> np.ndarray:
    """
    Vectorised rolling feature extraction for one stock.
    Returns float32 ndarray shape (n_valid_rows, 18):
      columns 0-16: FEATURE_COLS
      column 17:    fwd_ret (label)
    Returns empty array if insufficient data.
    """
    if df.empty or len(df) < WARMUP_BARS + FORWARD_DAYS + 5:
        return np.empty((0, 18), dtype=np.float32)

    cl  = df["Close"].astype(float)
    op  = df["Open"].astype(float)
    hi  = df["High"].astype(float)
    lo  = df["Low"].astype(float)
    vol = df["Volume"].astype(float)
    n   = len(cl)

    # ── TECHNICAL (8) ─────────────────────────────────────────────────

    delta = cl.diff()
    gain  = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss  = (-delta).clip(lower=0).ewm(com=13, adjust=False).mean()
    rsi   = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)

    ema12     = cl.ewm(span=12, adjust=False).mean()
    ema26     = cl.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_sig  = macd_line.ewm(span=9, adjust=False).mean()
    macd_x    = ((macd_line > macd_sig).astype(float) * 2 - 1)

    bb_mid = cl.rolling(20).mean()
    bb_std = cl.rolling(20).std().replace(0, np.nan)
    bb_pos = ((cl - (bb_mid - 2*bb_std)) / (4*bb_std) * 100).fillna(50)

    h20     = hi.rolling(20).max()
    l20     = lo.rolling(20).min()
    pos_rng = ((cl - l20) / (h20 - l20).replace(0, np.nan) * 100).fillna(50)

    mom5      = cl.pct_change(5) * 100
    avg_vol   = vol.rolling(20).mean().replace(0, np.nan)
    vol_ratio = (vol / avg_vol).fillna(1.0)
    volatility= cl.pct_change().rolling(20).std() * 100

    # ── SENTIMENT PROXIES (7) ─────────────────────────────────────────

    overnight_gap  = (op / cl.shift(1) - 1) * 100
    intraday_range = (hi - lo) / cl * 100
    day_rng        = (hi - lo).replace(0, np.nan)
    close_loc      = ((cl - lo) / day_rng).fillna(0.5)
    vol_surge      = vol_ratio.copy()
    news_event     = overnight_gap.abs() * np.log1p(vol_surge)
    sentiment_3d   = overnight_gap.rolling(3).sum().fillna(0)
    big_gap_5d     = overnight_gap.abs().rolling(5).max().fillna(0)

    # ── MARKET-RELATIVE (2) ───────────────────────────────────────────

    nifty_aligned = nifty_cl.reindex(cl.index, method="ffill")
    stock_ret_1d  = cl.pct_change() * 100
    nifty_ret_1d  = nifty_aligned.pct_change() * 100
    stock_vs_mkt  = stock_ret_1d - nifty_ret_1d

    stock_ret_5d  = cl.pct_change(5) * 100
    nifty_ret_5d  = nifty_aligned.pct_change(5) * 100
    stock_rs5     = stock_ret_5d - nifty_ret_5d

    # ── TARGET ────────────────────────────────────────────────────────
    fwd_ret = (cl.shift(-FORWARD_DAYS) / cl - 1) * 100

    # Assemble DataFrame, slice warmup, drop NaN
    feat_df = pd.DataFrame({
        "rsi":           rsi,
        "macd_x":        macd_x,
        "bb_pos":        bb_pos,
        "pos_rng":       pos_rng,
        "mom5":          mom5,
        "vol_ratio":     vol_ratio,
        "volatility":    volatility,
        "sector":        float(sector_score),
        "overnight_gap": overnight_gap,
        "intraday_range":intraday_range,
        "close_loc":     close_loc,
        "vol_surge":     vol_surge,
        "news_event":    news_event,
        "sentiment_3d":  sentiment_3d,
        "big_gap_5d":    big_gap_5d,
        "stock_vs_mkt":  stock_vs_mkt,
        "stock_rs5":     stock_rs5,
        "fwd_ret":       fwd_ret,
    }, index=df.index)

    valid = feat_df.iloc[WARMUP_BARS:].dropna()
    if valid.empty:
        return np.empty((0, 18), dtype=np.float32)

    return valid.values.astype(np.float32)


# ══════════════════════════════════════════════════════════════════════
#  STEP 3 — Build full dataset (streaming — never holds all DFs in RAM)
# ══════════════════════════════════════════════════════════════════════

def _universe_key(universe: dict) -> str:
    """Stable hash string for a universe dict — used as cache key."""
    return ",".join(sorted(universe.keys()))


@st.cache_data(ttl=86400, show_spinner=False)
def build_dataset(universe_key: str, universe_json: str) -> tuple:
    """
    Build 5-year training dataset for the given universe.
    Streams OHLCV stock-by-stock — discards each DataFrame after
    feature extraction so memory stays bounded (~80 MB peak for 500 stocks).

    Args:
        universe_key  : sorted comma-joined symbols (cache key)
        universe_json : JSON string of {symbol: sector} (actual data)

    Returns:
        (X, y, n_rows, n_stocks_ok)
          X: float32 ndarray (n_rows, 17)
          y: float32 ndarray (n_rows,)
    """
    import json
    universe = json.loads(universe_json)

    nifty_cl = fetch_nifty_history()

    chunks_X = []
    chunks_y = []
    n_ok     = 0

    for sym, sec in universe.items():
        df    = fetch_history(sym)      # cached 24h per symbol
        score = SECTOR_SCORE.get(sec, 2)
        arr   = _extract_features_array(df, nifty_cl, score)
        if arr.shape[0] == 0:
            continue
        chunks_X.append(arr[:, :17])   # features
        chunks_y.append(arr[:, 17])    # label
        n_ok += 1
        del df, arr                    # release RAM immediately

    if not chunks_X:
        return (np.empty((0, 17), dtype=np.float32),
                np.empty(0, dtype=np.float32), 0, 0)

    X = np.concatenate(chunks_X, axis=0)
    y = np.concatenate(chunks_y, axis=0)
    del chunks_X, chunks_y

    return X, y, int(X.shape[0]), n_ok


# ══════════════════════════════════════════════════════════════════════
#  STEP 4 — Train ensemble (keyed by universe hash)
# ══════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def _get_trained_models(universe_key: str, universe_json: str):
    """
    Trains RF + GB + Ridge on the full 5-year dataset.
    Keyed by universe_key so models retrain only when the index changes.
    Cached in memory (cache_resource) — survives reruns.

    For 500 stocks / 590k rows:
      RF  — 80 shallow trees, n_jobs=-1 — ~45s first run
      GB  — 60 trees, fast because depth=3
      Ridge — <1s
    Total: ~60s first load per universe. Subsequent runs: instant.
    """
    X, y, n_rows, n_stocks = build_dataset(universe_key, universe_json)

    if n_rows < 500:
        return None, None, None, n_rows, n_stocks

    # Sub-sample for very large datasets to keep training < 90s on Streamlit Cloud
    # 500k rows is sufficient; more doesn't improve accuracy meaningfully
    MAX_ROWS = 500_000
    if n_rows > MAX_ROWS:
        idx = np.random.default_rng(42).choice(n_rows, MAX_ROWS, replace=False)
        idx.sort()
        X_tr = X[idx]
        y_tr = y[idx]
    else:
        X_tr, y_tr = X, y

    rf = Pipeline([
        ("sc", StandardScaler()),
        ("m",  RandomForestRegressor(
            n_estimators=80, max_depth=5,
            min_samples_leaf=30, random_state=42, n_jobs=-1,
        )),
    ])
    gb = Pipeline([
        ("sc", StandardScaler()),
        ("m",  GradientBoostingRegressor(
            n_estimators=60, max_depth=3,
            learning_rate=0.10, subsample=0.7, random_state=42,
        )),
    ])
    ridge = Pipeline([("sc", StandardScaler()), ("m", Ridge(alpha=1.0))])

    rf.fit(X_tr, y_tr)
    gb.fit(X_tr, y_tr)
    ridge.fit(X_tr, y_tr)

    return rf, gb, ridge, n_rows, n_stocks


# ══════════════════════════════════════════════════════════════════════
#  NEWS SENTIMENT — live RSS at prediction time
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_sentiment_data(symbols: tuple) -> dict:
    """
    Scrape free RSS feeds for each symbol.
    Returns {sym -> {"score": float, "headlines": [str]}}
    score is -1.0 to +1.0. Cached 30 min.
    """
    import requests
    from bs4 import BeautifulSoup

    all_items: list[tuple[str, str]] = []
    for url in FREE_RSS:
        try:
            r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.content, "lxml-xml")
            for tag in soup.find_all("title")[:80]:
                txt = tag.text.strip()
                if txt and len(txt) > 10:
                    all_items.append((txt, txt.lower()))
        except Exception:
            pass

    result = {}
    for sym in symbols:
        sym_lower = sym.lower()
        matched = [(d, l) for d, l in all_items if sym_lower in l]
        if not matched:
            result[sym] = {"score": 0.0, "headlines": []}
            continue
        words = re.findall(r"\b\w+\b", " ".join(l for _, l in matched))
        p = sum(1 for w in words if w in POS_WORDS)
        n = sum(1 for w in words if w in NEG_WORDS)
        score = round((p - n) / (p + n), 2) if (p + n) > 0 else 0.0
        seen, kept = set(), []
        for disp, _ in matched:
            clean = disp.strip()
            if clean not in seen and len(kept) < 5:
                seen.add(clean); kept.append(clean)
        result[sym] = {"score": score, "headlines": kept}

    return result


def fetch_sentiment(symbols: tuple) -> dict:
    """Backward-compatible wrapper — returns just scores."""
    data = fetch_sentiment_data(symbols)
    return {sym: v["score"] for sym, v in data.items()}


# ══════════════════════════════════════════════════════════════════════
#  STEP 5 — Map stat dict → 17-feature vector
# ══════════════════════════════════════════════════════════════════════

def _stat_to_features(s: dict) -> np.ndarray:
    return np.array([[
        s["rsi"],
        float(s["macd_cross"]),
        s["bb_pos"],
        s["pos_in_range"],
        s["mom5"],
        s["vol_ratio"],
        s["volatility"],
        float(SECTOR_SCORE.get(s["sector"], 2)),
        s.get("overnight_gap",   0.0),
        s.get("intraday_range",  1.0),
        s.get("close_loc",       0.5),
        s.get("vol_ratio",       1.0),
        s.get("news_event",      0.0),
        s.get("sentiment_3d",    0.0),
        s.get("big_gap_5d",      0.0),
        s.get("stock_vs_mkt",    0.0),
        s.get("stock_rs5",       0.0),
    ]], dtype=float)


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def predict(stats: list[dict],
            universe: dict[str, str] | None = None) -> list[dict]:
    """
    Score every stock using the 17-feature 5-year ensemble.

    universe: {symbol: sector} dict for the active index.
              If None, falls back to STOCKS (Nifty 50) for backward compat.

    Flow:
      1. Derive universe_key for cache lookup
      2. Load/train models (from cache_resource or train ~60s for 500 stocks)
      3. Build 17-feature vector per stock from today's data
      4. Ensemble: RF 40% + GB 40% + Ridge 20%
      5. Normalise 0-100, blend with live RSS sentiment (80% ML + 20% sent)
      6. Assign signal: STRONG BUY / BUY / HOLD / AVOID

    Adds to each stat dict:
      ml_score, sentiment, final_score, predicted_return,
      signal, sig_color, training_rows, n_features, training_stocks
    """
    import json

    if not stats:
        return stats

    active    = universe if universe else STOCKS
    u_key     = _universe_key(active)
    u_json    = json.dumps(active, sort_keys=True)

    rf, gb, ridge, n_rows, n_stocks = _get_trained_models(u_key, u_json)

    # Fallback if training failed
    if rf is None:
        for s in stats:
            s.update(ml_score=50.0, sentiment=0.0, final_score=50.0,
                     predicted_return=0.0, signal="🟠 HOLD",
                     sig_color="#f59e0b", training_rows=n_rows,
                     training_stocks=n_stocks,
                     n_features=len(FEATURE_COLS), news_headlines=[])
        return stats

    raw_preds = []
    for s in stats:
        x    = _stat_to_features(s)
        pred = (0.40 * float(rf.predict(x)[0])
              + 0.40 * float(gb.predict(x)[0])
              + 0.20 * float(ridge.predict(x)[0]))
        raw_preds.append(pred)

    raw = np.array(raw_preds)
    mn, mx    = raw.min(), raw.max()
    ml_scores = ((raw - mn) / (mx - mn) * 100
                 if mx > mn else np.full(len(stats), 50.0))

    sent_data = fetch_sentiment_data(tuple(s["symbol"] for s in stats))
    sentiment = {sym: v["score"]    for sym, v in sent_data.items()}
    headlines = {sym: v["headlines"] for sym, v in sent_data.items()}

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
            "training_stocks":  n_stocks,
            "n_features":       len(FEATURE_COLS),
            "news_headlines":   headlines.get(s["symbol"], []),
        })

    return enriched
