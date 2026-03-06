"""
backend/ml.py
ML ensemble prediction: RandomForest + GradientBoosting + Ridge.
News sentiment from free public RSS feeds — no API key required.
No logic changes from the working version.
"""

import re

import numpy as np
import streamlit as st
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from backend.constants import FREE_RSS, NEG_WORDS, POS_WORDS, SECTOR_SCORE


# ── Feature builder ────────────────────────────────────────────────────────────

def _build_features(stats: list[dict]) -> np.ndarray:
    return np.array([
        [
            s["rsi"], s["macd_cross"], s["bb_pos"], s["pos_in_range"],
            s["change_pct"], s["mom5"], s["vol_ratio"], s["volatility"],
            SECTOR_SCORE.get(s["sector"], 2),
        ]
        for s in stats
    ], dtype=float)


def _build_target(stats: list[dict]) -> np.ndarray:
    """
    Craft a domain-knowledge target:
    lower RSI + lower range position + bigger drop + higher volume = more attractive.
    """
    return np.array([
        (70 - s["rsi"])          * 0.30
        + (50 - s["pos_in_range"]) * 0.25
        + (-s["change_pct"])       * 0.15
        + s["vol_ratio"]           * 0.10
        + (20 - s["volatility"])   * 0.10
        + s["macd_cross"]          * 5.0
        + SECTOR_SCORE.get(s["sector"], 2) * 2.0
        for s in stats
    ], dtype=float)


# ── Three models ───────────────────────────────────────────────────────────────

def _make_rf() -> Pipeline:
    return Pipeline([
        ("sc", StandardScaler()),
        ("m",  RandomForestRegressor(
            n_estimators=200, max_depth=6, random_state=42, n_jobs=1,
        )),
    ])


def _make_gb() -> Pipeline:
    return Pipeline([
        ("sc", StandardScaler()),
        ("m",  GradientBoostingRegressor(
            n_estimators=200, max_depth=4, learning_rate=0.05,
            subsample=0.8, random_state=42,
        )),
    ])


def _make_ridge() -> Pipeline:
    return Pipeline([("sc", StandardScaler()), ("m", Ridge(alpha=1.0))])


# ── News sentiment (free RSS, no API) ─────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def fetch_sentiment(symbols: tuple) -> dict[str, float]:
    """
    Scrape free public RSS feeds for headlines mentioning each stock.
    Returns sentiment score -1.0 to +1.0 per symbol.
    Falls back to 0.0 if no internet or no headlines found.
    """
    import requests
    from bs4 import BeautifulSoup

    headlines: list[str] = []
    for url in FREE_RSS:
        try:
            r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            soup = BeautifulSoup(r.content, "lxml-xml")
            for tag in soup.find_all(["title", "description"])[:60]:
                if tag.text:
                    headlines.append(tag.text.lower())
        except Exception:
            pass

    result: dict[str, float] = {}
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


# ── Main prediction entry point ────────────────────────────────────────────────

def predict(stats: list[dict]) -> list[dict]:
    """
    Run the ML ensemble + news sentiment on all stocks.
    Adds ml_score, sentiment, final_score, signal, sig_color to each stat dict.
    Fully deterministic (n_jobs=1, random_state=42 everywhere).
    """
    if len(stats) < 5:
        for s in stats:
            s.update(ml_score=50.0, sentiment=0.0, final_score=50.0,
                     signal="🟠 HOLD", sig_color="#f59e0b")
        return stats

    X = _build_features(stats)
    y = _build_target(stats)

    rf    = _make_rf();    rf.fit(X, y)
    gb    = _make_gb();    gb.fit(X, y)
    ridge = _make_ridge(); ridge.fit(X, y)

    # Weighted ensemble: RF 40% + GB 40% + Ridge 20%
    raw = 0.40 * rf.predict(X) + 0.40 * gb.predict(X) + 0.20 * ridge.predict(X)

    mn, mx = raw.min(), raw.max()
    ml_scores = (raw - mn) / (mx - mn) * 100 if mx > mn else np.full(len(stats), 50.0)

    sentiment = fetch_sentiment(tuple(s["symbol"] for s in stats))

    enriched = []
    for s, ml_sc in zip(stats, ml_scores):
        sent  = sentiment.get(s["symbol"], 0.0)
        final = round(float(np.clip(ml_sc * 0.80 + sent * 10 + 10, 0, 100)), 1)

        if   final >= 72: sig, col = "🟢 STRONG BUY", "#10b981"
        elif final >= 55: sig, col = "🟡 BUY",         "#34d399"
        elif final >= 35: sig, col = "🟠 HOLD",        "#f59e0b"
        else:             sig, col = "🔴 AVOID",       "#ef4444"

        enriched.append({
            **s,
            "ml_score":    round(float(ml_sc), 1),
            "sentiment":   sent,
            "final_score": final,
            "signal":      sig,
            "sig_color":   col,
        })

    return enriched
