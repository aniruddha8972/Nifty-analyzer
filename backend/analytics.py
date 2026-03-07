"""
backend/analytics.py
─────────────────────
Analytics & Intelligence backend — powers 4 new tabs:

  1. Sector Heatmap    — treemap + sector P&L summary from OHLCV data
  2. Backtesting       — walk-forward signal simulation on historical data
  3. Correlation Matrix — pairwise return correlations across all 50 stocks
  4. Events Calendar   — NSE corporate actions (results, dividends, F&O expiry)

All functions are pure data — no Streamlit imports here.
"""

from datetime import date, timedelta, datetime
from collections import defaultdict
import re

import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════════
#  1. SECTOR HEATMAP DATA
# ══════════════════════════════════════════════════════════════════════

def build_heatmap_data(stock_data: list[dict]) -> pd.DataFrame:
    """
    Transform stock_data list into a DataFrame for treemap / heatmap rendering.

    Returns DataFrame with columns:
      symbol, sector, change_pct, last_close, rsi, signal,
      abs_change  (for sizing nodes)
    """
    if not stock_data:
        return pd.DataFrame()

    rows = []
    for s in stock_data:
        rows.append({
            "symbol":     s["symbol"],
            "sector":     s["sector"],
            "change_pct": s["change_pct"],
            "last_close": s["last_close"],
            "rsi":        s.get("rsi", 50),
            "signal":     s.get("signal", "—"),
            "abs_change": abs(s["change_pct"]) + 0.1,   # always positive, for sizing
        })
    df = pd.DataFrame(rows)

    # Sector-level aggregates
    sector_agg = (
        df.groupby("sector")
        .agg(
            sector_avg_change=("change_pct", "mean"),
            sector_stock_count=("symbol", "count"),
            sector_gainers=("change_pct", lambda x: (x > 0).sum()),
            sector_losers=("change_pct", lambda x: (x < 0).sum()),
        )
        .reset_index()
    )
    df = df.merge(sector_agg, on="sector", how="left")
    return df


def get_sector_summary(heatmap_df: pd.DataFrame) -> list[dict]:
    """
    Returns one row per sector sorted by avg change.
    Used for the sector summary bar below the heatmap.
    """
    if heatmap_df.empty:
        return []
    cols = ["sector", "sector_avg_change", "sector_stock_count",
            "sector_gainers", "sector_losers"]
    return (
        heatmap_df[cols]
        .drop_duplicates("sector")
        .sort_values("sector_avg_change", ascending=False)
        .to_dict("records")
    )


# ══════════════════════════════════════════════════════════════════════
#  2. BACKTESTING ENGINE
# ══════════════════════════════════════════════════════════════════════

def _score_to_signal(score: float) -> str:
    if score >= 72: return "STRONG BUY"
    if score >= 55: return "BUY"
    if score >= 35: return "HOLD"
    return "AVOID"


def run_backtest(
    ohlcv_cache: dict[str, pd.DataFrame],   # symbol → full 3yr OHLCV df
    hold_days:   int   = 20,
    min_score:   float = 55.0,              # BUY threshold
    stop_loss:   float = -8.0,              # % stop loss
    take_profit: float = 15.0,              # % take profit
) -> dict:
    """
    Walk-forward backtest of the ML BUY signal.

    For each stock, on each date:
      1. Compute a simplified momentum/RSI score from data up to that date only
      2. If score >= min_score → simulate buying at next-day open
      3. Hold for hold_days (or until stop/take-profit hit)
      4. Record trade result

    Returns dict with:
      trades       — list of individual trade results
      summary      — win_rate, avg_return, total_trades, sharpe, max_drawdown
      equity_curve — cumulative return over time (for chart)
      by_symbol    — per-symbol win rate
    """
    trades = []
    equity = {}   # date → cumulative pnl

    for sym, df in ohlcv_cache.items():
        if df.empty or len(df) < 60:
            continue

        df = df.copy().sort_index()
        cl = df["Close"].astype(float)
        op = df["Open"].astype(float) if "Open" in df.columns else cl

        dates = df.index.tolist()

        for i in range(30, len(dates) - hold_days - 2):
            window = cl.iloc[:i]

            # Simple score: RSI momentum + MACD direction
            # (lightweight version of full ML — uses only past data)
            rsi = 50.0
            if len(window) >= 15:
                d    = window.diff().dropna()
                gain = d.clip(lower=0).rolling(14).mean().iloc[-1]
                loss = (-d).clip(lower=0).rolling(14).mean().iloc[-1]
                rsi  = 100 - 100 / (1 + gain / loss) if loss > 0 else 100.0

            ema12  = window.ewm(span=12).mean().iloc[-1]
            ema26  = window.ewm(span=26).mean().iloc[-1]
            macd_x = 1 if ema12 > ema26 else -1

            mom5 = float((window.iloc[-1] - window.iloc[-5]) / window.iloc[-5] * 100) \
                   if len(window) >= 5 else 0.0

            # Simplified composite score
            score = (
                (rsi / 100) * 40 +
                (1 if macd_x > 0 else 0) * 25 +
                (min(max(mom5, -5), 5) / 10 + 0.5) * 35
            )

            if score < min_score:
                continue

            # Entry: next day open
            entry_idx = i + 1
            if entry_idx >= len(dates):
                continue

            entry_price = float(op.iloc[entry_idx])
            if entry_price <= 0:
                continue

            # Simulate hold
            exit_price = entry_price
            exit_reason = "time"
            actual_hold = 0

            for j in range(1, hold_days + 1):
                if entry_idx + j >= len(dates):
                    break
                cur_price = float(cl.iloc[entry_idx + j])
                pnl_pct   = (cur_price - entry_price) / entry_price * 100
                actual_hold = j

                if pnl_pct <= stop_loss:
                    exit_price  = cur_price
                    exit_reason = "stop_loss"
                    break
                if pnl_pct >= take_profit:
                    exit_price  = cur_price
                    exit_reason = "take_profit"
                    break
                exit_price = cur_price

            ret_pct = (exit_price - entry_price) / entry_price * 100
            entry_date = dates[entry_idx]

            trade = {
                "symbol":      sym,
                "entry_date":  str(entry_date)[:10],
                "entry_price": round(entry_price, 2),
                "exit_price":  round(exit_price, 2),
                "return_pct":  round(ret_pct, 2),
                "hold_days":   actual_hold,
                "exit_reason": exit_reason,
                "score":       round(score, 1),
                "win":         ret_pct > 0,
            }
            trades.append(trade)

            # Build equity curve
            d_str = str(entry_date)[:10]
            equity[d_str] = equity.get(d_str, 0) + ret_pct

    if not trades:
        return {"trades": [], "summary": {}, "equity_curve": [], "by_symbol": {}}

    # Summary statistics
    returns = [t["return_pct"] for t in trades]
    wins    = [r for r in returns if r > 0]
    losses  = [r for r in returns if r <= 0]

    avg_ret   = float(np.mean(returns))
    std_ret   = float(np.std(returns)) if len(returns) > 1 else 1.0
    sharpe    = round(avg_ret / std_ret * np.sqrt(252 / max(20, 1)), 2) if std_ret > 0 else 0.0

    # Cumulative equity curve
    sorted_dates = sorted(equity.keys())
    cumulative   = 0.0
    curve        = []
    for d in sorted_dates:
        cumulative += equity[d]
        curve.append({"date": d, "cumulative_return": round(cumulative, 2)})

    # Max drawdown on equity curve
    peak = 0.0
    max_dd = 0.0
    for point in curve:
        peak  = max(peak, point["cumulative_return"])
        dd    = peak - point["cumulative_return"]
        max_dd = max(max_dd, dd)

    # Per-symbol breakdown
    by_sym = defaultdict(lambda: {"trades": 0, "wins": 0, "total_return": 0.0})
    for t in trades:
        by_sym[t["symbol"]]["trades"]       += 1
        by_sym[t["symbol"]]["wins"]         += int(t["win"])
        by_sym[t["symbol"]]["total_return"] += t["return_pct"]
    by_symbol = {}
    for sym, d in by_sym.items():
        by_symbol[sym] = {
            "trades":       d["trades"],
            "win_rate":     round(d["wins"] / d["trades"] * 100, 1) if d["trades"] else 0,
            "avg_return":   round(d["total_return"] / d["trades"], 2) if d["trades"] else 0,
        }

    summary = {
        "total_trades":  len(trades),
        "win_rate":      round(len(wins) / len(trades) * 100, 1),
        "avg_return":    round(avg_ret, 2),
        "avg_win":       round(float(np.mean(wins)), 2)   if wins   else 0.0,
        "avg_loss":      round(float(np.mean(losses)), 2) if losses else 0.0,
        "sharpe":        sharpe,
        "max_drawdown":  round(max_dd, 2),
        "total_return":  round(sum(returns), 2),
        "best_trade":    round(max(returns), 2),
        "worst_trade":   round(min(returns), 2),
        "hold_days":     hold_days,
        "min_score":     min_score,
    }

    return {
        "trades":       trades[-200:],   # last 200 trades for display
        "summary":      summary,
        "equity_curve": curve,
        "by_symbol":    by_symbol,
    }


# ══════════════════════════════════════════════════════════════════════
#  3. CORRELATION MATRIX
# ══════════════════════════════════════════════════════════════════════

def build_correlation_matrix(
    ohlcv_cache: dict[str, pd.DataFrame],
    min_overlap: int = 100,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build pairwise return correlation matrix for all stocks with enough data.

    Returns:
      corr_matrix   — symmetric DataFrame of correlations (-1 to 1)
      returns_df    — daily returns DataFrame used to compute it
    """
    close_dict = {}
    for sym, df in ohlcv_cache.items():
        if df.empty or len(df) < min_overlap:
            continue
        if "Close" in df.columns:
            close_dict[sym] = df["Close"].astype(float)

    if len(close_dict) < 2:
        return pd.DataFrame(), pd.DataFrame()

    prices_df  = pd.DataFrame(close_dict).sort_index()
    returns_df = prices_df.pct_change().dropna(how="all")

    # Only keep columns with enough data
    valid_cols = [c for c in returns_df.columns
                  if returns_df[c].notna().sum() >= min_overlap]
    returns_df = returns_df[valid_cols].dropna()

    corr_matrix = returns_df.corr().round(3)
    return corr_matrix, returns_df


def get_top_correlations(
    corr_matrix: pd.DataFrame,
    top_n: int = 10,
) -> tuple[list[dict], list[dict]]:
    """
    Extract top N most correlated and most inversely correlated pairs.

    Returns (most_correlated, most_inverse) — each is a list of dicts:
      { stock_a, stock_b, correlation }
    """
    if corr_matrix.empty:
        return [], []

    pairs = []
    symbols = corr_matrix.columns.tolist()
    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            pairs.append({
                "stock_a":     symbols[i],
                "stock_b":     symbols[j],
                "correlation": corr_matrix.iloc[i, j],
            })

    pairs_sorted = sorted(pairs, key=lambda x: x["correlation"], reverse=True)
    most_corr    = [p for p in pairs_sorted if p["correlation"] < 1.0][:top_n]
    most_inverse = sorted(pairs, key=lambda x: x["correlation"])[:top_n]

    return most_corr, most_inverse


def get_portfolio_diversification(
    corr_matrix: pd.DataFrame,
    portfolio_symbols: list[str],
) -> dict:
    """
    Score how diversified a portfolio is based on avg pairwise correlation.
    Lower avg correlation = better diversification.
    """
    if corr_matrix.empty or len(portfolio_symbols) < 2:
        return {"score": None, "avg_correlation": None, "message": "Need 2+ holdings"}

    held = [s for s in portfolio_symbols if s in corr_matrix.columns]
    if len(held) < 2:
        return {"score": None, "avg_correlation": None, "message": "Holdings not in data"}

    sub = corr_matrix.loc[held, held]
    # Average of upper triangle (exclude diagonal)
    n   = len(held)
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += abs(sub.iloc[i, j])
            count += 1

    avg_corr = total / count if count else 0
    # Score: 0 = perfectly correlated (bad), 100 = uncorrelated (good)
    score = round((1 - avg_corr) * 100, 1)

    if score >= 70:   msg = "Well diversified — stocks move independently"
    elif score >= 45: msg = "Moderately diversified — some sector concentration"
    else:             msg = "Low diversification — holdings move together"

    return {"score": score, "avg_correlation": round(avg_corr, 3), "message": msg}


# ══════════════════════════════════════════════════════════════════════
#  4. EVENTS CALENDAR
# ══════════════════════════════════════════════════════════════════════

def get_fo_expiry_dates(year: int, month: int) -> list[date]:
    """
    NSE F&O contracts expire on the last Thursday of each month.
    Returns list of expiry dates for the given month.
    """
    import calendar
    # Find last Thursday
    cal = calendar.monthcalendar(year, month)
    thursdays = [week[3] for week in cal if week[3] != 0]
    last_thu  = thursdays[-1]
    return [date(year, month, last_thu)]


def build_events_calendar(
    months_ahead: int = 2,
    stock_data:   list[dict] | None = None,
) -> dict[str, list[dict]]:
    """
    Build a calendar of market events for the next N months.

    Returns dict: { "YYYY-MM-DD": [ {type, title, symbol, description}, ... ] }

    Event types:
      fo_expiry    — F&O monthly expiry (last Thursday)
      results      — Quarterly results (estimated from known schedule)
      market_closed — NSE holidays
      dividend     — Estimated dividend ex-dates (from pattern)
    """
    today    = date.today()
    events   = defaultdict(list)

    # ── F&O Expiry dates ───────────────────────────────────────────────
    for m_offset in range(months_ahead + 1):
        target_month = today.month + m_offset
        target_year  = today.year + (target_month - 1) // 12
        target_month = ((target_month - 1) % 12) + 1
        for exp_date in get_fo_expiry_dates(target_year, target_month):
            events[str(exp_date)].append({
                "type":        "fo_expiry",
                "title":       "⚡ F&O Expiry",
                "symbol":      "ALL",
                "description": "Monthly F&O contracts expire — expect high volatility",
                "color":       "#f59e0b",
            })

    # ── NSE Holidays 2025 ──────────────────────────────────────────────
    nse_holidays_2025 = [
        ("2025-01-26", "Republic Day"),
        ("2025-02-26", "Mahashivratri"),
        ("2025-03-14", "Holi"),
        ("2025-03-31", "Id-Ul-Fitr (Ramzan Eid)"),
        ("2025-04-10", "Shri Ram Navami"),
        ("2025-04-14", "Dr. Baba Saheb Ambedkar Jayanti"),
        ("2025-04-18", "Good Friday"),
        ("2025-05-01", "Maharashtra Day"),
        ("2025-08-15", "Independence Day"),
        ("2025-08-27", "Ganesh Chaturthi"),
        ("2025-10-02", "Gandhi Jayanti / Dussehra"),
        ("2025-10-20", "Diwali Laxmi Pujan"),
        ("2025-10-21", "Diwali-Balipratipada"),
        ("2025-11-05", "Prakash Gurpurb Sri Guru Nanak Dev Ji"),
        ("2025-12-25", "Christmas"),
        ("2026-01-26", "Republic Day"),
        ("2026-03-20", "Holi"),
    ]
    for d_str, name in nse_holidays_2025:
        events[d_str].append({
            "type":        "market_closed",
            "title":       f"🏛 Market Closed",
            "symbol":      "NSE",
            "description": name,
            "color":       "#6b6b80",
        })

    # ── Quarterly Results Season ───────────────────────────────────────
    # Q3 FY25 results: Jan–Feb 2025
    # Q4 FY25 results: Apr–May 2025
    # Q1 FY26 results: Jul–Aug 2025
    # Q2 FY26 results: Oct–Nov 2025
    results_windows = [
        ("2025-01-10", "2025-02-15", "Q3 FY25"),
        ("2025-04-10", "2025-05-20", "Q4 FY25"),
        ("2025-07-10", "2025-08-15", "Q1 FY26"),
        ("2025-10-10", "2025-11-20", "Q2 FY26"),
        ("2026-01-10", "2026-02-15", "Q3 FY26"),
    ]

    # Key results dates for top stocks
    key_results = [
        ("2025-01-09", "TCS",       "Q3 FY25 Results"),
        ("2025-01-13", "INFY",      "Q3 FY25 Results"),
        ("2025-01-15", "HDFCBANK",  "Q3 FY25 Results"),
        ("2025-01-16", "WIPRO",     "Q3 FY25 Results"),
        ("2025-01-17", "RELIANCE",  "Q3 FY25 Results"),
        ("2025-01-18", "ICICIBANK", "Q3 FY25 Results"),
        ("2025-04-10", "TCS",       "Q4 FY25 Results"),
        ("2025-04-17", "INFOSYS",   "Q4 FY25 Results"),
        ("2025-04-19", "HDFCBANK",  "Q4 FY25 Results"),
        ("2025-07-10", "TCS",       "Q1 FY26 Results"),
        ("2025-07-17", "INFOSYS",   "Q1 FY26 Results"),
        ("2025-10-10", "TCS",       "Q2 FY26 Results"),
        ("2026-01-09", "TCS",       "Q3 FY26 Results"),
    ]
    for d_str, sym, title in key_results:
        events[d_str].append({
            "type":        "results",
            "title":       f"📊 {sym} Results",
            "symbol":      sym,
            "description": title,
            "color":       "#00e5a0",
        })

    # ── Results season banners ─────────────────────────────────────────
    for start_str, end_str, season in results_windows:
        try:
            s = date.fromisoformat(start_str)
            e = date.fromisoformat(end_str)
            if s <= today + timedelta(days=60):
                events[start_str].append({
                    "type":        "results_season",
                    "title":       f"📅 {season} Season Begins",
                    "symbol":      "ALL",
                    "description": f"Quarterly earnings season — expect volatility",
                    "color":       "#8b5cf6",
                })
        except Exception:
            pass

    # ── Budget Day ─────────────────────────────────────────────────────
    budget_dates = [
        ("2025-02-01", "Union Budget 2025-26"),
        ("2026-02-01", "Union Budget 2026-27"),
    ]
    for d_str, title in budget_dates:
        events[d_str].append({
            "type":        "budget",
            "title":       "🏛 Union Budget",
            "symbol":      "GOI",
            "description": title + " — Major market mover",
            "color":       "#ef4444",
        })

    return dict(events)


def get_upcoming_events(
    events_dict: dict[str, list[dict]],
    days_ahead: int = 30,
) -> list[dict]:
    """
    Return events in the next N days, sorted by date.
    Each item has: date, events list.
    """
    today  = date.today()
    cutoff = today + timedelta(days=days_ahead)
    result = []

    for d_str, evts in sorted(events_dict.items()):
        try:
            d = date.fromisoformat(d_str)
        except Exception:
            continue
        if today <= d <= cutoff:
            result.append({
                "date":       d_str,
                "date_obj":   d,
                "days_away":  (d - today).days,
                "events":     evts,
            })

    return sorted(result, key=lambda x: x["date"])
