"""
backend/ai_model.py
───────────────────
Internal multi-factor scoring model.
No external API or key required.

Each stock is scored 0–100 across 9 independent factors.
The score maps to a recommendation tier and risk level.
"""

from dataclasses import dataclass, field
from typing import List
from backend.data_engine import StockData, DEFENSIVE_SECTORS


# ── Output model ─────────────────────────────────────────────────────────────
@dataclass
class StockAnalysis:
    symbol:         str
    score:          int          # 0–100
    recommendation: str          # STRONG BUY / BUY / HOLD / SELL / STRONG SELL
    rec_color:      str          # hex colour for UI
    risk_level:     str          # Low / Medium / Med-High / High
    signals:        List[str] = field(default_factory=list)

    # thresholds
    TIERS = {
        "STRONG BUY":  (72, 100, "#10b981"),
        "BUY":         (58,  71, "#34d399"),
        "HOLD":        (43,  57, "#f59e0b"),
        "SELL":        (29,  42, "#f87171"),
        "STRONG SELL": ( 0,  28, "#ef4444"),
    }

    @classmethod
    def from_score(cls, symbol: str, score: int, risk: str, signals: List[str]) -> "StockAnalysis":
        score = max(0, min(100, score))
        for name, (lo, hi, col) in cls.TIERS.items():
            if lo <= score <= hi:
                return cls(symbol=symbol, score=score, recommendation=name,
                           rec_color=col, risk_level=risk, signals=signals)
        return cls(symbol=symbol, score=score, recommendation="HOLD",
                   rec_color="#f59e0b", risk_level=risk, signals=signals)


# ── Scoring factors ───────────────────────────────────────────────────────────
def _score_rsi(s: StockData) -> tuple:
    if s.rsi < 35:
        return +15, "Oversold RSI (< 35)"
    if s.rsi > 70:
        return -15, "Overbought RSI (> 70)"
    if 45 <= s.rsi <= 58:          # tightened from 42–60 — true neutral zone only
        return  +5, "RSI in neutral zone"
    return 0, None


def _score_momentum(s: StockData) -> tuple:
    t1 = 6 if s.days > 90 else 4
    t2 = 12 if s.days > 90 else 8
    if   s.chg_pct >  t2: return +13, "Very strong period gain"
    elif s.chg_pct >  t1: return  +8, "Strong period momentum"
    elif s.chg_pct >  1.5: return  +4, "Mild positive momentum"
    elif s.chg_pct < -t2: return -12, "Heavy period decline"
    elif s.chg_pct < -t1: return  -8, "Negative momentum"
    return 0, None


def _score_52w_range(s: StockData) -> tuple:
    rng = s.week52_high - s.week52_low
    if rng <= 0:
        return 0, None
    pos = (s.close_price - s.week52_low) / rng
    if   pos < 0.20: return +14, "Near 52W low — value zone"
    elif pos < 0.40: return  +7, "Below 52W midpoint"
    elif pos > 0.88: return -11, "Near 52W high — caution"
    return 0, None


def _score_volume(s: StockData) -> tuple:
    if s.avg_volume <= 0:
        return 0, None
    vr = s.volume / s.avg_volume
    if   vr > 1.6: return  +9, "High volume conviction"
    elif vr > 1.2: return  +4, "Above-average volume"
    elif vr < 0.55: return -5, "Low volume — weak signal"
    return 0, None


def _score_pe(s: StockData) -> tuple:
    if   s.pe_ratio < 12: return +10, "Deeply undervalued (P/E < 12)"
    elif s.pe_ratio < 18: return  +6, "Undervalued P/E"
    elif s.pe_ratio > 55: return  -9, "Very expensive (P/E > 55)"
    elif s.pe_ratio > 35: return  -4, "Premium valuation"
    return 0, None


def _score_beta(s: StockData) -> tuple:
    if   s.beta > 1.5:  return -6, "High beta — volatile",     "High"
    elif s.beta > 1.2:  return  0, "Above-avg volatility",     "Med-High"
    elif s.beta < 0.65: return +6, "Low beta — defensive",     "Low"
    return 0, None, "Medium"


def _score_dividend(s: StockData) -> tuple:
    if   s.div_yield > 2.5: return +6, "Strong dividend yield"
    elif s.div_yield > 1.0: return +3, "Moderate dividend"
    return 0, None


def _score_sector(s: StockData) -> tuple:
    if s.sector in DEFENSIVE_SECTORS:
        return +3, f"Defensive sector ({s.sector})"
    return 0, None


def _score_mean_reversion(s: StockData) -> tuple:
    if s.days > 60 and s.chg_pct < -5:
        return +4, "Mean-reversion potential"
    return 0, None


# ── Main scorer ───────────────────────────────────────────────────────────────
def analyse_stock(s: StockData) -> StockAnalysis:
    """
    Run all 9 scoring factors and return a StockAnalysis.
    Score starts at 50 (neutral). Each factor adds or subtracts points.
    """
    total  = 50
    signals: List[str] = []
    risk   = "Medium"

    # RSI
    pts, msg = _score_rsi(s)
    total += pts
    if msg: signals.append(msg)

    # Momentum
    pts, msg = _score_momentum(s)
    total += pts
    if msg: signals.append(msg)

    # 52-week range
    pts, msg = _score_52w_range(s)
    total += pts
    if msg: signals.append(msg)

    # Volume
    pts, msg = _score_volume(s)
    total += pts
    if msg: signals.append(msg)

    # P/E
    pts, msg = _score_pe(s)
    total += pts
    if msg: signals.append(msg)

    # Beta / risk level
    beta_result = _score_beta(s)
    total += beta_result[0]
    if beta_result[1]: signals.append(beta_result[1])
    risk = beta_result[2]

    # Dividend
    pts, msg = _score_dividend(s)
    total += pts
    if msg: signals.append(msg)

    # Sector
    pts, msg = _score_sector(s)
    total += pts
    if msg: signals.append(msg)

    # Mean reversion
    pts, msg = _score_mean_reversion(s)
    total += pts
    if msg: signals.append(msg)

    return StockAnalysis.from_score(s.symbol, total, risk, signals)


def analyse_all(stocks: list) -> dict:
    """Return {symbol: StockAnalysis} for a list of StockData objects."""
    return {s.symbol: analyse_stock(s) for s in stocks}
