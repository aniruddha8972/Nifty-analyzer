"""
backend/ml.py  —  v4: 17-feature historically-trained ensemble
───────────────────────────────────────────────────────────────────────────────

WHAT CHANGED FROM v3
─────────────────────
v3: 8 technical features only, trained on 50 rows (one per stock)
v4: 17 features (8 technical + 7 sentiment proxies + 2 market-relative),
    trained on ~35,000 real historical rows (50 stocks × 3 years daily)

SENTIMENT PROXY FEATURES (no API, no scraping — derived from OHLCV)
──────────────────────────────────────────────────────────────────────
These capture market-visible news reactions without needing raw text:

  overnight_gap    Open vs prev close — what happened after hours / pre-market
  intraday_range   High-Low as % of close — uncertainty / news volatility
  close_loc        Where close sits in day's H-L range (0=low, 1=high)
  vol_surge        Today's volume vs 20-day avg — news-driven activity
  news_event       |gap| × log(vol_surge) — combined news event score
  sentiment_3d     Sum of last 3 overnight gaps — short news narrative
  big_gap_5d       Largest gap in last 5 days — recent event flag

MARKET-RELATIVE FEATURES (from Nifty 50 index, no API)
────────────────────────────────────────────────────────
  stock_vs_mkt     Stock 1-day return minus Nifty — idiosyncratic move
  stock_rs5        Stock 5-day return minus Nifty — relative strength

TRAINING PIPELINE
──────────────────
1. fetch_history()       — 3 years daily OHLCV per stock (cached 24h)
2. fetch_nifty_history() — 3 years Nifty index (cached 24h)
3. build_dataset()       — vectorised rolling feature extraction → ~35,000 rows
4. _get_trained_models() — fits RF + GB + Ridge, cached in memory
5. predict()             — scores each stock using today's 17 features

DATA COUNTS
────────────
  50 stocks × ~750 trading days (3 years) ≈ 37,500 rows
  After warmup (30 bars) + forward window (10 bars) ≈ 35,000 training rows
  Each row labelled with actual 10-day forward return
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

from backend.constants import FREE_RSS, NEG_WORDS, POS_WORDS, SECTOR_SCORE, STOCKS, INDEX_UNIVERSE

# ── Constants ──────────────────────────────────────────────────────────────────
HISTORY_YEARS = 3
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
#  STEP 1 — Fetch 3-year history (cached 24h)
# ══════════════════════════════════════════════════════════════════════

def _hist_range() -> tuple[str, str]:
    end   = date.today()
    start = end - timedelta(days=365 * HISTORY_YEARS + 30)
    return str(start), str(end + timedelta(days=1))


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_history(symbol: str) -> pd.DataFrame:
    """3 years of daily OHLCV for one stock. Cached 24h."""
    start, end = _hist_range()
    try:
        df = yf.download(f"{symbol}.NS", start=start, end=end,
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df[["Open","High","Low","Close","Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_nifty_history() -> pd.Series:
    """3 years of Nifty 50 daily closes for market-relative features. Cached 24h."""
    start, end = _hist_range()
    try:
        df = yf.download("^NSEI", start=start, end=end,
                         auto_adjust=True, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df["Close"].astype(float).dropna()
    except Exception:
        return pd.Series(dtype=float)


# ══════════════════════════════════════════════════════════════════════
#  STEP 2 — Vectorised rolling feature extraction
# ══════════════════════════════════════════════════════════════════════

def _extract_features(df: pd.DataFrame,
                      nifty_cl: pd.Series,
                      sector_score: int) -> pd.DataFrame:
    """
    Vectorised rolling computation of all 17 features.
    Every row = one trading day = one real training sample.
    Last column 'fwd_ret' = actual 10-day forward return (the label).
    """
    cl  = df["Close"].astype(float)
    op  = df["Open"].astype(float)
    hi  = df["High"].astype(float)
    lo  = df["Low"].astype(float)
    vol = df["Volume"].astype(float)

    # ── TECHNICAL (8) ─────────────────────────────────────────────────

    # RSI(14) — EWM approximation, fully vectorised
    delta = cl.diff()
    gain  = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss  = (-delta).clip(lower=0).ewm(com=13, adjust=False).mean()
    rsi   = (100 - 100 / (1 + gain / loss.replace(0, np.nan))).fillna(50)

    # MACD(12,26,9): +1 bullish, -1 bearish
    ema12     = cl.ewm(span=12, adjust=False).mean()
    ema26     = cl.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_sig  = macd_line.ewm(span=9, adjust=False).mean()
    macd_x    = (macd_line > macd_sig).astype(int) * 2 - 1

    # Bollinger Band position (0 = lower band, 100 = upper band)
    bb_mid = cl.rolling(20).mean()
    bb_std = cl.rolling(20).std().replace(0, np.nan)
    bb_pos = ((cl - (bb_mid - 2*bb_std)) / (4*bb_std) * 100).fillna(50)

    # Position in 20-day high-low range
    h20     = hi.rolling(20).max()
    l20     = lo.rolling(20).min()
    pos_rng = ((cl - l20) / (h20 - l20).replace(0, np.nan) * 100).fillna(50)

    # 5-day momentum
    mom5 = cl.pct_change(5) * 100

    # Volume ratio (today vs 20-day avg)
    avg_vol   = vol.rolling(20).mean().replace(0, np.nan)
    vol_ratio = (vol / avg_vol).fillna(1.0)

    # 20-day rolling volatility
    volatility = cl.pct_change().rolling(20).std() * 100

    # ── SENTIMENT PROXIES (7) ─────────────────────────────────────────

    # Overnight gap: open vs previous close
    overnight_gap = (op / cl.shift(1) - 1) * 100

    # Intraday range as % of close
    intraday_range = (hi - lo) / cl * 100

    # Close location in day's range (0=at low, 1=at high)
    day_rng   = (hi - lo).replace(0, np.nan)
    close_loc = ((cl - lo) / day_rng).fillna(0.5)

    # Volume surge (same as vol_ratio — kept separate for model clarity)
    vol_surge = vol_ratio.copy()

    # News event: gap magnitude × log(volume surge)
    news_event = overnight_gap.abs() * np.log1p(vol_surge)

    # 3-day cumulative overnight gap — short-term news trend
    sentiment_3d = overnight_gap.rolling(3).sum().fillna(0)

    # Largest gap in last 5 days — recent news event flag
    big_gap_5d = overnight_gap.abs().rolling(5).max().fillna(0)

    # ── MARKET-RELATIVE (2) ───────────────────────────────────────────

    # Align Nifty to stock's trading calendar
    nifty_aligned = nifty_cl.reindex(cl.index, method="ffill")
    stock_ret_1d  = cl.pct_change() * 100
    nifty_ret_1d  = nifty_aligned.pct_change() * 100
    stock_vs_mkt  = stock_ret_1d - nifty_ret_1d

    stock_ret_5d  = cl.pct_change(5) * 100
    nifty_ret_5d  = nifty_aligned.pct_change(5) * 100
    stock_rs5     = stock_ret_5d - nifty_ret_5d

    # ── TARGET ────────────────────────────────────────────────────────
    fwd_ret = (cl.shift(-FORWARD_DAYS) / cl - 1) * 100

    out = pd.DataFrame({
        # Technical
        "rsi":           rsi,
        "macd_x":        macd_x.astype(float),
        "bb_pos":        bb_pos,
        "pos_rng":       pos_rng,
        "mom5":          mom5,
        "vol_ratio":     vol_ratio,
        "volatility":    volatility,
        "sector":        float(sector_score),
        # Sentiment proxies
        "overnight_gap": overnight_gap,
        "intraday_range":intraday_range,
        "close_loc":     close_loc,
        "vol_surge":     vol_surge,
        "news_event":    news_event,
        "sentiment_3d":  sentiment_3d,
        "big_gap_5d":    big_gap_5d,
        # Market-relative
        "stock_vs_mkt":  stock_vs_mkt,
        "stock_rs5":     stock_rs5,
        # Label
        "fwd_ret":       fwd_ret,
    }, index=df.index)

    return out.iloc[WARMUP_BARS:].dropna()


# ══════════════════════════════════════════════════════════════════════
#  STEP 3 — Build full training dataset
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=86400, show_spinner=False)
def build_dataset() -> tuple:
    """
    Build training dataset from 3 years of history across all 50 stocks.
    Returns (X, y, n_rows):
      X: (n_rows, 17) — 8 technical + 7 sentiment proxy + 2 market-relative
      y: (n_rows,)    — actual 10-day forward returns
      n_rows ~ 35,000
    """
    nifty_cl = fetch_nifty_history()

    frames = []
    for sym, sec in STOCKS.items():
        df = fetch_history(sym)
        if df.empty or len(df) < WARMUP_BARS + FORWARD_DAYS + 5:
            continue
        feat = _extract_features(df, nifty_cl, SECTOR_SCORE.get(sec, 2))
        if not feat.empty:
            frames.append(feat)

    if not frames:
        return np.empty((0, len(FEATURE_COLS))), np.empty(0), 0

    combined = pd.concat(frames, ignore_index=True)
    X = combined[FEATURE_COLS].values.astype(float)
    y = combined["fwd_ret"].values.astype(float)
    return X, y, len(combined)


# ══════════════════════════════════════════════════════════════════════
#  STEP 4 — Train ensemble (cached in memory)
# ══════════════════════════════════════════════════════════════════════

@st.cache_resource(show_spinner=False)
def _get_trained_models():
    """
    Trains RF + GB + Ridge on ~35,000 historical rows with 17 features.
    @st.cache_resource keeps fitted models in memory across reruns.
    First load: ~25s. Subsequent calls: instant.
    """
    X, y, n_rows = build_dataset()

    if n_rows < 100:
        return None, None, None, n_rows

    rf = Pipeline([
        ("sc", StandardScaler()),
        ("m",  RandomForestRegressor(
            n_estimators=60, max_depth=4,
            min_samples_leaf=20, random_state=42, n_jobs=1,
        )),
    ])
    gb = Pipeline([
        ("sc", StandardScaler()),
        ("m",  GradientBoostingRegressor(
            n_estimators=60, max_depth=3,
            learning_rate=0.12, subsample=0.8, random_state=42,
        )),
    ])
    ridge = Pipeline([("sc", StandardScaler()), ("m", Ridge(alpha=1.0))])

    rf.fit(X, y)
    gb.fit(X, y)
    ridge.fit(X, y)

    return rf, gb, ridge, n_rows


# ══════════════════════════════════════════════════════════════════════
#  NEWS SENTIMENT — live RSS at prediction time (unchanged)
# ══════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_sentiment_data(symbols: tuple) -> dict:
    """
    Scrape free RSS feeds for each symbol.
    Returns dict: { sym -> {"score": float, "headlines": [str, ...]} }
    score is -1.0 to +1.0. headlines are the raw matching titles (title-cased).
    Cached 30 min.
    """
    import requests
    from bs4 import BeautifulSoup

    # Collect all (title, text) pairs — keep original case for display
    all_items: list[tuple[str, str]] = []   # (display_text, lowercase_text)
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
        # Match headlines containing the symbol name
        matched = [(disp, low) for disp, low in all_items if sym_lower in low]
        if not matched:
            result[sym] = {"score": 0.0, "headlines": []}
            continue

        # Score using POS/NEG word lists
        words = re.findall(r"\b\w+\b", " ".join(low for _, low in matched))
        p = sum(1 for w in words if w in POS_WORDS)
        n = sum(1 for w in words if w in NEG_WORDS)
        score = round((p - n) / (p + n), 2) if (p + n) > 0 else 0.0

        # Keep up to 5 unique display headlines, cleaned up
        seen   = set()
        kept   = []
        for disp, _ in matched:
            clean = disp.strip()
            if clean not in seen and len(kept) < 5:
                seen.add(clean)
                kept.append(clean)

        result[sym] = {"score": score, "headlines": kept}

    return result


def fetch_sentiment(symbols: tuple) -> dict:
    """Backward-compatible wrapper — returns just scores."""
    data = fetch_sentiment_data(symbols)
    return {sym: v["score"] for sym, v in data.items()}


# ══════════════════════════════════════════════════════════════════════
#  STEP 5 — Map current stat dict → 17-feature vector
# ══════════════════════════════════════════════════════════════════════

def _stat_to_features(s: dict) -> np.ndarray:
    """
    Convert a stat dict (from data.py compute_stats) into the same
    17-feature vector the models were trained on.
    Matches FEATURE_COLS order exactly.
    """
    return np.array([[
        # Technical (8) — all present in stat dict
        s["rsi"],
        float(s["macd_cross"]),
        s["bb_pos"],
        s["pos_in_range"],
        s["mom5"],
        s["vol_ratio"],
        s["volatility"],
        float(SECTOR_SCORE.get(s["sector"], 2)),
        # Sentiment proxies (7) — new fields added to data.py
        s.get("overnight_gap",   0.0),
        s.get("intraday_range",  1.0),
        s.get("close_loc",       0.5),
        s.get("vol_ratio",       1.0),   # vol_surge = vol_ratio
        s.get("news_event",      0.0),
        s.get("sentiment_3d",    0.0),
        s.get("big_gap_5d",      0.0),
        # Market-relative (2)
        s.get("stock_vs_mkt",    0.0),
        s.get("stock_rs5",       0.0),
    ]], dtype=float)


# ══════════════════════════════════════════════════════════════════════
#  PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def predict(stats: list[dict]) -> list[dict]:
    """
    Score every stock using the 17-feature historically-trained ensemble.

    Flow:
      1. Load trained models (from cache or train ~25s)
      2. Build 17-feature vector for each stock from today's data
      3. Run ensemble: RF 40% + GB 40% + Ridge 20%
      4. Normalise to 0–100 ML score
      5. Blend with live RSS sentiment (80% ML + 20% sentiment)
      6. Assign signal: STRONG BUY / BUY / HOLD / AVOID

    Adds to each stat dict:
      ml_score, sentiment, final_score, predicted_return,
      signal, sig_color, training_rows, n_features
    """
    if not stats:
        return stats

    rf, gb, ridge, n_rows = _get_trained_models()

    # Fallback: training failed
    if rf is None:
        for s in stats:
            s.update(ml_score=50.0, sentiment=0.0, final_score=50.0,
                     predicted_return=0.0, signal="🟠 HOLD",
                     sig_color="#f59e0b", training_rows=n_rows,
                     n_features=len(FEATURE_COLS), news_headlines=[])
        return stats

    # Build predictions
    raw_preds = []
    for s in stats:
        x    = _stat_to_features(s)
        pred = (0.40 * float(rf.predict(x)[0])
              + 0.40 * float(gb.predict(x)[0])
              + 0.20 * float(ridge.predict(x)[0]))
        raw_preds.append(pred)

    raw = np.array(raw_preds)

    # Normalise to 0–100
    mn, mx    = raw.min(), raw.max()
    ml_scores = (raw - mn) / (mx - mn) * 100 if mx > mn else np.full(len(stats), 50.0)

    # Live RSS sentiment + headlines (prediction time only)
    sent_data  = fetch_sentiment_data(tuple(s["symbol"] for s in stats))
    sentiment  = {sym: v["score"] for sym, v in sent_data.items()}
    headlines  = {sym: v["headlines"] for sym, v in sent_data.items()}

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
            "n_features":       len(FEATURE_COLS),
            "news_headlines":   headlines.get(s["symbol"], []),
        })

    return enriched
