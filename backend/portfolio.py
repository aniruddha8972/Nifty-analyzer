"""
backend/portfolio.py
────────────────────
Portfolio tracker with live P&L + ML advisor.

Portfolio is stored in st.session_state["portfolio"] as a dict:
  { symbol: { qty, avg_buy_price, lots: [{date,qty,price},...] } }

No external API needed — live prices come from yfinance (same as market analyzer).

Key functions:
  add_holding(symbol, qty, price, buy_date)  → adds/updates a holding
  remove_holding(symbol)                     → removes a stock
  fetch_live_prices(symbols)                 → latest close prices from yfinance
  compute_portfolio_pnl(portfolio, prices)   → full P&L per stock + totals
  get_portfolio_advice(pnl_data, ml_stats)   → ML-driven HOLD/BUY MORE/SELL advice
  export_portfolio_json(portfolio)           → JSON string for download
  import_portfolio_json(json_str)            → parse and validate
"""

import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

from backend.constants import STOCKS


# ── Live price fetch ───────────────────────────────────────────────────────────

@st.cache_data(ttl=300, show_spinner=False)   # 5-minute cache
def fetch_live_prices(symbols: tuple) -> dict[str, float]:
    """
    Fetch the most recent closing price for each symbol.
    Uses a 5-day window to guarantee at least one trading day.
    Returns { symbol: price }. Missing symbols get price 0.0.
    """
    end   = date.today() + timedelta(days=1)
    start = date.today() - timedelta(days=7)
    prices = {}
    for sym in symbols:
        try:
            df = yf.download(
                f"{sym}.NS",
                start=str(start), end=str(end),
                auto_adjust=True, progress=False,
            )
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if not df.empty and "Close" in df.columns:
                prices[sym] = round(float(df["Close"].dropna().iloc[-1]), 2)
            else:
                prices[sym] = 0.0
        except Exception:
            prices[sym] = 0.0
    return prices


# ── Portfolio CRUD ─────────────────────────────────────────────────────────────

def _get_portfolio() -> dict:
    if "portfolio" not in st.session_state:
        st.session_state["portfolio"] = {}
    return st.session_state["portfolio"]


def add_holding(symbol: str, qty: int, price: float,
                buy_date: str | None = None) -> None:
    """
    Add qty shares of symbol bought at price.
    If the stock already exists, adds a new lot and recalculates avg price.
    """
    portfolio = _get_portfolio()
    if buy_date is None:
        buy_date = str(date.today())

    if symbol in portfolio:
        entry = portfolio[symbol]
        old_cost  = entry["qty"] * entry["avg_buy_price"]
        new_cost  = qty * price
        new_qty   = entry["qty"] + qty
        entry["avg_buy_price"] = round((old_cost + new_cost) / new_qty, 2)
        entry["qty"]           = new_qty
        entry["lots"].append({"date": buy_date, "qty": qty, "price": price})
    else:
        sector = STOCKS.get(symbol, "Unknown")
        portfolio[symbol] = {
            "symbol":        symbol,
            "sector":        sector,
            "qty":           qty,
            "avg_buy_price": round(price, 2),
            "lots":          [{"date": buy_date, "qty": qty, "price": price}],
        }
    st.session_state["portfolio"] = portfolio


def remove_holding(symbol: str) -> None:
    portfolio = _get_portfolio()
    portfolio.pop(symbol, None)
    st.session_state["portfolio"] = portfolio


def update_qty(symbol: str, new_qty: int) -> None:
    """Update quantity for a holding (e.g. partial sell)."""
    portfolio = _get_portfolio()
    if symbol in portfolio:
        if new_qty <= 0:
            remove_holding(symbol)
        else:
            portfolio[symbol]["qty"] = new_qty
            st.session_state["portfolio"] = portfolio


# ── P&L calculation ────────────────────────────────────────────────────────────

def compute_portfolio_pnl(
    portfolio: dict,
    prices:    dict[str, float],
) -> tuple[list[dict], dict]:
    """
    Compute P&L for every holding plus portfolio-level totals.

    Returns:
      rows   — list of per-stock dicts with P&L fields
      totals — { total_invested, total_current, total_pnl, total_pnl_pct,
                 best_performer, worst_performer, n_profit, n_loss }
    """
    rows = []
    total_invested = 0.0
    total_current  = 0.0

    for sym, entry in portfolio.items():
        price = prices.get(sym, 0.0)
        qty   = entry["qty"]
        avg   = entry["avg_buy_price"]

        invested    = qty * avg
        current_val = qty * price if price > 0 else 0.0
        pnl         = current_val - invested
        pnl_pct     = (pnl / invested * 100) if invested > 0 else 0.0
        day_val     = price * qty   # same as current_val when price is latest

        rows.append({
            "symbol":        sym,
            "sector":        entry["sector"],
            "qty":           qty,
            "avg_buy_price": avg,
            "current_price": price,
            "invested":      round(invested, 2),
            "current_val":   round(current_val, 2),
            "pnl":           round(pnl, 2),
            "pnl_pct":       round(pnl_pct, 2),
            "lots":          entry.get("lots", []),
            # advice filled later by get_portfolio_advice()
            "advice":        "⏳ Analysing…",
            "advice_color":  "#888888",
            "advice_reason": "",
        })
        total_invested += invested
        total_current  += current_val

    total_pnl     = total_current - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    totals = {
        "total_invested": round(total_invested, 2),
        "total_current":  round(total_current, 2),
        "total_pnl":      round(total_pnl, 2),
        "total_pnl_pct":  round(total_pnl_pct, 2),
        "n_profit":       sum(1 for r in rows if r["pnl"] > 0),
        "n_loss":         sum(1 for r in rows if r["pnl"] < 0),
        "best":           max(rows, key=lambda x: x["pnl_pct"])  if rows else None,
        "worst":          min(rows, key=lambda x: x["pnl_pct"])  if rows else None,
    }

    return rows, totals


# ── ML-powered advisor ─────────────────────────────────────────────────────────

def get_portfolio_advice(
    pnl_rows:  list[dict],
    ml_stats:  list[dict] | None,
) -> list[dict]:
    """
    Attach ML-driven advice to each portfolio row.

    Logic matrix (P&L position × ML signal):
    ┌────────────────┬─────────────┬──────────────────────────────────┐
    │ ML Signal      │ P&L         │ Advice                           │
    ├────────────────┼─────────────┼──────────────────────────────────┤
    │ STRONG BUY     │ any         │ BUY MORE — strong conviction     │
    │ BUY            │ loss > -5%  │ AVERAGE DOWN — dip opportunity   │
    │ BUY            │ profit/flat │ HOLD / ADD — uptrend intact      │
    │ HOLD           │ profit>10%  │ BOOK PARTIAL — protect gains     │
    │ HOLD           │ any         │ HOLD — wait for clearer signal   │
    │ AVOID          │ profit> 5%  │ BOOK PROFIT — exit while ahead   │
    │ AVOID          │ loss < -8%  │ STOP LOSS — cut losses now       │
    │ AVOID          │ small       │ REDUCE — trim position           │
    └────────────────┴─────────────┴──────────────────────────────────┘
    """
    # Build lookup: symbol → ML stat
    ml_map = {}
    if ml_stats:
        for s in ml_stats:
            ml_map[s["symbol"]] = s

    enriched = []
    for row in pnl_rows:
        sym   = row["symbol"]
        pnl_p = row["pnl_pct"]
        ml    = ml_map.get(sym)

        if ml is None:
            # No ML data — advice based on P&L only
            if pnl_p > 15:
                advice, col, reason = "🟡 REVIEW",     "#f59e0b", "Strong gain — consider reviewing position"
            elif pnl_p < -10:
                advice, col, reason = "🟠 REVIEW",     "#f59e0b", "Significant loss — review your thesis"
            else:
                advice, col, reason = "⬜ NO ML DATA", "#666688", "Run Market Analyzer for ML advice"
        else:
            sig       = ml.get("signal", "🟠 HOLD")
            ml_score  = ml.get("final_score", 50)
            sent      = ml.get("sentiment", 0.0)
            pred_ret  = ml.get("predicted_return", 0.0)

            if "STRONG BUY" in sig:
                advice = "🟢 BUY MORE"
                col    = "#10b981"
                reason = (f"ML score {ml_score:.0f}/100 — strong conviction. "
                          f"Pred return {pred_ret:+.2f}%. Your P&L: {pnl_p:+.1f}%")

            elif "BUY" in sig and pnl_p < -5:
                advice = "🟢 AVERAGE DOWN"
                col    = "#34d399"
                reason = (f"You're down {pnl_p:.1f}% but ML is bullish (score {ml_score:.0f}). "
                          f"Good opportunity to lower avg cost. Pred return {pred_ret:+.2f}%")

            elif "BUY" in sig:
                advice = "🟢 HOLD / ADD"
                col    = "#10b981"
                reason = (f"ML BUY signal (score {ml_score:.0f}). "
                          f"Your P&L: {pnl_p:+.1f}%. Pred return {pred_ret:+.2f}%")

            elif "AVOID" in sig and pnl_p > 5:
                advice = "🔴 BOOK PROFIT"
                col    = "#ef4444"
                reason = (f"You're up {pnl_p:.1f}% — ML score {ml_score:.0f} signals weakness. "
                          f"Consider taking profits. Sent: {sent:+.2f}")

            elif "AVOID" in sig and pnl_p < -8:
                advice = "🔴 STOP LOSS"
                col    = "#ff2244"
                reason = (f"Down {pnl_p:.1f}% and ML bearish (score {ml_score:.0f}). "
                          f"Consider cutting losses. Pred return {pred_ret:+.2f}%")

            elif "AVOID" in sig:
                advice = "🟠 REDUCE"
                col    = "#f59e0b"
                reason = (f"ML AVOID (score {ml_score:.0f}). "
                          f"Your P&L: {pnl_p:+.1f}%. Consider trimming position")

            elif "HOLD" in sig and pnl_p > 12:
                advice = "🟡 BOOK PARTIAL"
                col    = "#fbbf24"
                reason = (f"Up {pnl_p:.1f}% with HOLD signal — consider booking "
                          f"partial profits to lock in gains")

            else:
                advice = "🟡 HOLD"
                col    = "#f59e0b"
                reason = (f"ML HOLD (score {ml_score:.0f}). "
                          f"Your P&L: {pnl_p:+.1f}%. Maintain position")

        enriched.append({**row, "advice": advice, "advice_color": col, "advice_reason": reason})

    return enriched


# ── Import / Export ────────────────────────────────────────────────────────────

def export_portfolio_json(portfolio: dict) -> str:
    """Serialize portfolio to a JSON string for download."""
    return json.dumps(portfolio, indent=2, default=str)


def import_portfolio_json(json_str: str) -> tuple[dict | None, str]:
    """
    Parse and validate a portfolio JSON string.
    Returns (portfolio_dict, error_message).
    error_message is empty string if successful.
    """
    try:
        data = json.loads(json_str)
        if not isinstance(data, dict):
            return None, "Invalid format: expected a JSON object"
        validated = {}
        for sym, entry in data.items():
            if not isinstance(entry, dict):
                continue
            if "qty" not in entry or "avg_buy_price" not in entry:
                continue
            validated[sym] = {
                "symbol":        sym,
                "sector":        STOCKS.get(sym, entry.get("sector", "Unknown")),
                "qty":           int(entry["qty"]),
                "avg_buy_price": float(entry["avg_buy_price"]),
                "lots":          entry.get("lots", []),
            }
        return validated, ""
    except Exception as e:
        return None, f"Parse error: {e}"
