"""
frontend/analytics_components.py
─────────────────────────────────
UI components for the Analytics & Intelligence tab.

  render_heatmap_tab(stock_data)
  render_backtest_tab(backtest_result)
  render_correlation_tab(corr_matrix, returns_df, portfolio_symbols)
  render_events_tab(events_dict)
"""

import json
from datetime import date, timedelta

import pandas as pd
import streamlit as st


# ══════════════════════════════════════════════════════════════════════
#  SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════

def _section(title: str, subtitle: str = "") -> None:
    sub_html = f'<span style="font-size:11px;color:#4a4a60;margin-left:12px">{subtitle}</span>' if subtitle else ""
    st.markdown(f"""
    <div style="margin:4px 0 18px">
      <span style="font-family:'Space Mono',monospace;font-size:13px;
                   font-weight:700;color:#e8e8f0">{title}</span>
      {sub_html}
    </div>
    """, unsafe_allow_html=True)


def _metric(label: str, value: str, color: str = "#e8e8f0", sub: str = "") -> str:
    sub_html = f'<div style="font-size:10px;color:#4a4a60;margin-top:2px">{sub}</div>' if sub else ""
    return f"""
    <div style="background:#08080e;border:1px solid #1a1a28;border-radius:8px;
                padding:14px 16px;text-align:center">
      <div style="font-family:'DM Sans',sans-serif;font-size:10px;
                  letter-spacing:1px;text-transform:uppercase;color:#4a4a60;
                  margin-bottom:6px">{label}</div>
      <div style="font-family:'Space Mono',monospace;font-size:18px;
                  font-weight:700;color:{color}">{value}</div>
      {sub_html}
    </div>"""


# ══════════════════════════════════════════════════════════════════════
#  1. SECTOR HEATMAP
# ══════════════════════════════════════════════════════════════════════

def render_heatmap_tab(stock_data: list[dict]) -> None:
    """Sector heatmap + sector summary cards."""
    from backend.analytics import build_heatmap_data, get_sector_summary

    _section("Sector Heatmap", "colour = return % · size = equal weight")

    if not stock_data:
        st.info("Run the Market Analyzer first to see the heatmap.")
        return

    df = build_heatmap_data(stock_data)
    if df.empty:
        st.warning("No data available.")
        return

    # ── Plotly treemap ─────────────────────────────────────────────────
    try:
        import plotly.express as px
        import plotly.graph_objects as go

        # Colour scale: deep red → neutral → deep green
        max_abs = max(df["change_pct"].abs().max(), 0.5)

        fig = px.treemap(
            df,
            path=["sector", "symbol"],
            values="abs_change",
            color="change_pct",
            color_continuous_scale=[
                [0.0,  "#7f0000"],
                [0.2,  "#cc2233"],
                [0.4,  "#ff4560"],
                [0.5,  "#1a1a2e"],
                [0.6,  "#00a370"],
                [0.8,  "#00c896"],
                [1.0,  "#00e5a0"],
            ],
            color_continuous_midpoint=0,
            range_color=[-max_abs, max_abs],
            hover_data={"change_pct": ":.2f", "last_close": ":.2f",
                        "rsi": ":.1f", "abs_change": False},
            custom_data=["symbol", "change_pct", "last_close", "rsi", "signal"],
        )

        fig.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Return: %{customdata[1]:.2f}%<br>"
                "Close: ₹%{customdata[2]:,.2f}<br>"
                "RSI: %{customdata[3]:.1f}<br>"
                "Signal: %{customdata[4]}<extra></extra>"
            ),
            texttemplate="<b>%{label}</b><br>%{customdata[1]:.1f}%",
            textfont_size=11,
        )

        fig.update_layout(
            paper_bgcolor="#050508",
            plot_bgcolor="#050508",
            margin=dict(t=10, l=0, r=0, b=0),
            height=460,
            coloraxis_colorbar=dict(
                title="Return %",
                tickfont=dict(color="#6b6b80", size=10),
                title_font=dict(color="#6b6b80"),
                bgcolor="#0c0c12",
                bordercolor="#1e1e2e",
                len=0.8,
            ),
            font=dict(family="DM Sans", color="#e8e8f0"),
        )

        st.plotly_chart(fig, use_container_width=True)

    except ImportError:
        # Fallback: HTML grid if plotly not installed
        _render_heatmap_grid_fallback(df)

    # ── Sector summary cards ───────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _section("Sector Performance")
    summary = get_sector_summary(df)
    _render_sector_cards(summary)


def _render_heatmap_grid_fallback(df: pd.DataFrame) -> None:
    """Simple HTML grid fallback if plotly not available."""
    max_abs = max(df["change_pct"].abs().max(), 0.5)
    cells = ""
    for sector, grp in df.groupby("sector"):
        for _, row in grp.iterrows():
            pct    = row["change_pct"]
            norm   = (pct + max_abs) / (2 * max_abs)   # 0–1
            r = int(255 * (1 - norm))
            g = int(200 * norm)
            color  = f"rgb({r},{g},60)"
            cells += f"""
            <div style="background:{color};border-radius:6px;padding:8px;
                        text-align:center;font-size:10px;font-weight:700">
              <div>{row['symbol']}</div>
              <div>{pct:+.1f}%</div>
            </div>"""
    st.markdown(f'<div style="display:grid;grid-template-columns:repeat(8,1fr);gap:4px">{cells}</div>',
                unsafe_allow_html=True)


def _render_sector_cards(summary: list[dict]) -> None:
    cols = st.columns(min(len(summary), 6))
    for i, sec in enumerate(summary[:6]):
        chg   = sec["sector_avg_change"]
        color = "#00e5a0" if chg >= 0 else "#ff4560"
        sign  = "+" if chg >= 0 else ""
        with cols[i]:
            st.markdown(f"""
            <div style="background:#08080e;border:1px solid #1a1a28;
                        border-left:3px solid {color};border-radius:8px;
                        padding:12px;text-align:center">
              <div style="font-family:'Space Mono',monospace;font-size:9px;
                          letter-spacing:1px;color:#4a4a60;text-transform:uppercase;
                          margin-bottom:6px">{sec['sector']}</div>
              <div style="font-family:'Space Mono',monospace;font-size:16px;
                          font-weight:700;color:{color}">{sign}{chg:.2f}%</div>
              <div style="font-size:10px;color:#3a3a4e;margin-top:4px">
                {sec['sector_gainers']}↑ {sec['sector_losers']}↓
              </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  2. BACKTESTING ENGINE
# ══════════════════════════════════════════════════════════════════════

def render_backtest_tab() -> None:
    """Backtest UI — strategy config + results."""
    from backend.analytics import run_backtest
    from backend.data import fetch_ohlcv
    from backend.constants import STOCKS

    _section("Backtest Engine", "Walk-forward simulation on 3yr historical data")

    st.markdown("""
    <div style="background:#0a1a10;border:1px solid #1a3a28;border-radius:8px;
                padding:12px 16px;margin-bottom:16px;font-family:'DM Sans',sans-serif;
                font-size:12px;color:#6b6b80">
      ℹ Simulates buying every BUY signal on historical data using only past data at each point.
      Scores are a lightweight version of the full ML ensemble.
    </div>
    """, unsafe_allow_html=True)

    # ── Strategy config ────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        hold_days = st.slider("Hold Days", 5, 60, 20, key="bt_hold")
    with c2:
        min_score = st.slider("Min Score (BUY threshold)", 40, 80, 55, key="bt_score")
    with c3:
        stop_loss = st.slider("Stop Loss %", -20, -2, -8, key="bt_sl")
    with c4:
        take_profit = st.slider("Take Profit %", 5, 40, 15, key="bt_tp")

    run_btn = st.button("▶  Run Backtest", type="primary", key="bt_run")

    if not run_btn and "bt_result" not in st.session_state:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;color:#3a3a4e;
                    font-family:'Space Mono',monospace;font-size:12px">
          Configure strategy above and click ▶ Run Backtest
        </div>
        """, unsafe_allow_html=True)
        return

    if run_btn:
        with st.spinner("Running backtest on 3 years of historical data…"):
            # Fetch 3yr OHLCV for each stock
            from datetime import date, timedelta
            end   = date.today()
            start = end - timedelta(days=3 * 365)
            cache = {}
            prog  = st.progress(0)
            syms  = list(STOCKS.keys())
            for i, sym in enumerate(syms):
                df = fetch_ohlcv(sym, str(start), str(end + timedelta(days=1)))
                if not df.empty:
                    cache[sym] = df
                prog.progress((i + 1) / len(syms))
            prog.empty()

            result = run_backtest(
                cache,
                hold_days=hold_days,
                min_score=min_score,
                stop_loss=float(stop_loss),
                take_profit=float(take_profit),
            )
            st.session_state["bt_result"] = result

    result = st.session_state.get("bt_result", {})
    if not result or not result.get("summary"):
        st.warning("No trades generated. Try lowering the min score.")
        return

    _render_backtest_results(result)


def _render_backtest_results(result: dict) -> None:
    s = result["summary"]

    # ── KPI row ────────────────────────────────────────────────────────
    wr_color  = "#00e5a0" if s["win_rate"] >= 55 else "#ff4560"
    ret_color = "#00e5a0" if s["avg_return"] >= 0 else "#ff4560"
    sh_color  = "#00e5a0" if s["sharpe"] >= 1 else "#f59e0b"

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    metrics = [
        (m1, "Win Rate",      f"{s['win_rate']}%",    wr_color,  f"{s['total_trades']} trades"),
        (m2, "Avg Return",    f"{s['avg_return']:+.2f}%", ret_color, f"per trade"),
        (m3, "Sharpe Ratio",  f"{s['sharpe']:.2f}",   sh_color,  "annualised"),
        (m4, "Max Drawdown",  f"-{s['max_drawdown']:.1f}%", "#f59e0b", "cumulative"),
        (m5, "Best Trade",    f"{s['best_trade']:+.2f}%",  "#00e5a0", "single trade"),
        (m6, "Worst Trade",   f"{s['worst_trade']:+.2f}%", "#ff4560", "single trade"),
    ]
    for col, label, val, color, sub in metrics:
        with col:
            st.markdown(_metric(label, val, color, sub), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Equity curve ───────────────────────────────────────────────────
    curve = result.get("equity_curve", [])
    if curve:
        try:
            import plotly.graph_objects as go
            curve_df = pd.DataFrame(curve)
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=curve_df["date"],
                y=curve_df["cumulative_return"],
                fill="tozeroy",
                fillcolor="rgba(0,229,160,0.08)",
                line=dict(color="#00e5a0", width=2),
                name="Cumulative Return %",
            ))
            fig.add_hline(y=0, line_dash="dot", line_color="#3a3a4e", line_width=1)
            fig.update_layout(
                paper_bgcolor="#050508", plot_bgcolor="#050508",
                height=260, margin=dict(t=10, l=0, r=0, b=0),
                xaxis=dict(gridcolor="#1a1a28", color="#6b6b80"),
                yaxis=dict(gridcolor="#1a1a28", color="#6b6b80",
                           title="Cumulative Return %"),
                font=dict(family="DM Sans", color="#6b6b80"),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            pass

    # ── Per-symbol table ───────────────────────────────────────────────
    by_sym = result.get("by_symbol", {})
    if by_sym:
        sym_rows = sorted(by_sym.items(), key=lambda x: x[1]["win_rate"], reverse=True)
        sym_df = pd.DataFrame([
            {"Symbol": sym, "Trades": d["trades"],
             "Win Rate %": d["win_rate"], "Avg Return %": d["avg_return"]}
            for sym, d in sym_rows
        ])

        def _color_wr(val):
            if isinstance(val, (int, float)):
                return f"color: {'#00e5a0' if val >= 55 else '#ff4560'}; font-weight:600"
            return ""
        def _color_ret(val):
            if isinstance(val, (int, float)):
                return f"color: {'#00e5a0' if val >= 0 else '#ff4560'}"
            return ""

        styled = (
            sym_df.style
            .map(_color_wr,  subset=["Win Rate %"])
            .map(_color_ret, subset=["Avg Return %"])
            .format({"Win Rate %": "{:.1f}%", "Avg Return %": "{:+.2f}%"})
            .set_properties(**{"background-color":"#0c0c12","color":"#e8e8f0",
                               "border":"1px solid #1e1e2e"})
        )
        _section("Per-Stock Backtest Results")
        st.dataframe(styled, width="stretch", hide_index=True, height=300)


# ══════════════════════════════════════════════════════════════════════
#  3. CORRELATION MATRIX
# ══════════════════════════════════════════════════════════════════════

def render_correlation_tab(portfolio_symbols: list[str] | None = None) -> None:
    """Correlation matrix + diversification score."""
    from backend.analytics import (
        build_correlation_matrix, get_top_correlations,
        get_portfolio_diversification
    )
    from backend.data import fetch_ohlcv
    from backend.constants import STOCKS

    _section("Correlation Matrix", "1-year daily return correlations across all 50 stocks")

    run_btn = st.button("🔄  Compute Correlations", type="primary", key="corr_run")

    if not run_btn and "corr_result" not in st.session_state:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;color:#3a3a4e;
                    font-family:'Space Mono',monospace;font-size:12px">
          Click Compute Correlations to analyse all 50 stocks (cached for session)
        </div>
        """, unsafe_allow_html=True)
        return

    if run_btn:
        with st.spinner("Fetching 1 year of data for all 50 stocks…"):
            from datetime import date, timedelta
            end   = date.today()
            start = end - timedelta(days=365)
            cache = {}
            prog  = st.progress(0)
            syms  = list(STOCKS.keys())
            for i, sym in enumerate(syms):
                df = fetch_ohlcv(sym, str(start), str(end + timedelta(days=1)))
                if not df.empty:
                    cache[sym] = df
                prog.progress((i + 1) / len(syms))
            prog.empty()

            corr_matrix, returns_df = build_correlation_matrix(cache)
            st.session_state["corr_result"] = {
                "matrix": corr_matrix, "returns": returns_df
            }

    cached = st.session_state.get("corr_result", {})
    corr_matrix = cached.get("matrix", pd.DataFrame())
    returns_df  = cached.get("returns", pd.DataFrame())

    if corr_matrix.empty:
        st.warning("Could not compute correlations — need more data.")
        return

    # ── Portfolio diversification score ───────────────────────────────
    if portfolio_symbols:
        div = get_portfolio_diversification(corr_matrix, portfolio_symbols)
        score = div.get("score")
        if score is not None:
            s_color = "#00e5a0" if score >= 70 else "#f59e0b" if score >= 45 else "#ff4560"
            st.markdown(f"""
            <div style="background:#08080e;border:1px solid #1a1a28;border-radius:10px;
                        padding:16px 20px;margin-bottom:20px;display:flex;align-items:center;gap:20px">
              <div style="font-family:'Space Mono',monospace;font-size:32px;
                          font-weight:700;color:{s_color}">{score}</div>
              <div>
                <div style="font-family:'Space Mono',monospace;font-size:11px;
                            letter-spacing:2px;color:#4a4a60;text-transform:uppercase">
                  Your Portfolio Diversification Score
                </div>
                <div style="font-family:'DM Sans',sans-serif;font-size:13px;
                            color:#e8e8f0;margin-top:4px">{div['message']}</div>
                <div style="font-family:'DM Sans',sans-serif;font-size:11px;
                            color:#4a4a60;margin-top:2px">
                  Avg pairwise correlation: {div['avg_correlation']:.3f}
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    # ── Heatmap ────────────────────────────────────────────────────────
    try:
        import plotly.graph_objects as go

        syms = corr_matrix.columns.tolist()
        z    = corr_matrix.values

        fig = go.Figure(go.Heatmap(
            z=z, x=syms, y=syms,
            colorscale=[
                [0.0, "#1a0a30"],
                [0.3, "#3730a3"],
                [0.45, "#1a1a2e"],
                [0.5, "#0f1117"],
                [0.6, "#0a3a20"],
                [0.8, "#00a370"],
                [1.0, "#00e5a0"],
            ],
            zmid=0, zmin=-1, zmax=1,
            hovertemplate="%{y} ↔ %{x}<br>Corr: %{z:.3f}<extra></extra>",
            colorbar=dict(
                title="Correlation", tickfont=dict(color="#6b6b80"),
                title_font=dict(color="#6b6b80"),
            ),
        ))
        fig.update_layout(
            paper_bgcolor="#050508", plot_bgcolor="#050508",
            height=600, margin=dict(t=10, l=0, r=0, b=0),
            xaxis=dict(tickfont=dict(size=8, color="#6b6b80"), tickangle=45),
            yaxis=dict(tickfont=dict(size=8, color="#6b6b80")),
            font=dict(family="DM Sans"),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.info("Install plotly for the correlation heatmap visualization.")

    # ── Top correlated pairs ───────────────────────────────────────────
    most_corr, most_inv = get_top_correlations(corr_matrix, top_n=8)

    c1, c2 = st.columns(2)
    with c1:
        _section("Most Correlated Pairs", "move together — avoid holding both")
        if most_corr:
            rows = [{"Stock A": p["stock_a"], "Stock B": p["stock_b"],
                     "Correlation": p["correlation"]} for p in most_corr]
            pair_df = pd.DataFrame(rows)
            styled  = (pair_df.style
                       .format({"Correlation": "{:.3f}"})
                       .background_gradient(subset=["Correlation"],
                                            cmap="RdYlGn", vmin=-1, vmax=1)
                       .set_properties(**{"background-color":"#0c0c12",
                                          "color":"#e8e8f0","border":"1px solid #1e1e2e"}))
            st.dataframe(styled, width="stretch", hide_index=True)

    with c2:
        _section("Most Inverse Pairs", "natural hedges — good for diversification")
        if most_inv:
            rows = [{"Stock A": p["stock_a"], "Stock B": p["stock_b"],
                     "Correlation": p["correlation"]} for p in most_inv]
            pair_df = pd.DataFrame(rows)
            styled  = (pair_df.style
                       .format({"Correlation": "{:.3f}"})
                       .background_gradient(subset=["Correlation"],
                                            cmap="RdYlGn_r", vmin=-1, vmax=1)
                       .set_properties(**{"background-color":"#0c0c12",
                                          "color":"#e8e8f0","border":"1px solid #1e1e2e"}))
            st.dataframe(styled, width="stretch", hide_index=True)


# ══════════════════════════════════════════════════════════════════════
#  4. EVENTS CALENDAR
# ══════════════════════════════════════════════════════════════════════

_EVENT_COLORS = {
    "fo_expiry":      "#f59e0b",
    "results":        "#00e5a0",
    "results_season": "#8b5cf6",
    "market_closed":  "#4a4a60",
    "budget":         "#ef4444",
    "dividend":       "#3b82f6",
}

def render_events_tab() -> None:
    """Events calendar — F&O expiry, results, holidays, budget."""
    from backend.analytics import build_events_calendar, get_upcoming_events

    _section("Market Events Calendar", "F&O expiry · Results season · Holidays · Budget")

    events_dict = build_events_calendar(months_ahead=3)

    # ── Upcoming events strip ─────────────────────────────────────────
    upcoming = get_upcoming_events(events_dict, days_ahead=45)

    st.markdown("""
    <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:3px;
                text-transform:uppercase;color:#4a4a60;margin-bottom:12px">
      NEXT 45 DAYS
    </div>
    """, unsafe_allow_html=True)

    if not upcoming:
        st.info("No events in the next 45 days.")
    else:
        for item in upcoming[:20]:
            d_obj    = item["date_obj"]
            days_away = item["days_away"]
            if days_away == 0: day_label = "TODAY"
            elif days_away == 1: day_label = "TOMORROW"
            else: day_label = f"IN {days_away} DAYS"

            evts_html = ""
            for evt in item["events"]:
                color = evt.get("color", "#6b6b80")
                desc_html = f'<span style="color:#6b6b80"> — {evt["description"]}</span>' if evt.get("description") else ""
            evts_html += f"""
                <span style="display:inline-block;background:rgba(0,0,0,0.3);
                             border:1px solid {color}33;border-radius:4px;
                             padding:2px 8px;margin:2px;font-size:11px;color:{color}">
                  {evt['title']}{desc_html}
                </span>"""

            badge_color = "#ff4560" if days_away <= 3 else "#f59e0b" if days_away <= 7 else "#4a4a60"
            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:16px;
                        padding:12px 0;border-bottom:1px solid #0e0e18">
              <div style="min-width:120px;text-align:right">
                <div style="font-family:'Space Mono',monospace;font-size:13px;
                            font-weight:700;color:#e8e8f0">
                  {d_obj.strftime('%d %b %Y')}
                </div>
                <div style="font-family:'Space Mono',monospace;font-size:9px;
                            letter-spacing:1px;color:{badge_color};margin-top:2px">
                  {d_obj.strftime('%A').upper()} · {day_label}
                </div>
              </div>
              <div style="flex:1">{evts_html}</div>
            </div>
            """, unsafe_allow_html=True)

    # ── Full calendar grid ─────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _section("Full Calendar View")

    today = date.today()
    # Show current month + next 2 months
    for m_offset in range(3):
        target_month = today.month + m_offset
        target_year  = today.year + (target_month - 1) // 12
        target_month = ((target_month - 1) % 12) + 1

        month_name = date(target_year, target_month, 1).strftime("%B %Y")
        st.markdown(f"""
        <div style="font-family:'Space Mono',monospace;font-size:11px;letter-spacing:2px;
                    text-transform:uppercase;color:#00e5a0;margin:20px 0 8px">
          {month_name}
        </div>
        """, unsafe_allow_html=True)

        _render_month_grid(target_year, target_month, events_dict, today)


def _render_month_grid(year: int, month: int,
                       events_dict: dict, today: date) -> None:
    import calendar
    cal    = calendar.monthcalendar(year, month)
    days   = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    # Header
    header = "".join(
        f'<div style="text-align:center;font-family:\'Space Mono\',monospace;'
        f'font-size:9px;letter-spacing:1px;color:#3a3a4e;padding:4px">{d}</div>'
        for d in days
    )

    cells = ""
    for week in cal:
        for day_num in week:
            if day_num == 0:
                cells += '<div style="background:#050508;border-radius:4px;min-height:52px"></div>'
                continue

            d     = date(year, month, day_num)
            d_str = str(d)
            evts  = events_dict.get(d_str, [])
            is_today   = d == today
            is_weekend = d.weekday() >= 5

            bg_color    = "#0a1520" if is_today else "#08080e"
            num_color   = "#00e5a0" if is_today else "#6b6b80" if is_weekend else "#e8e8f0"
            border_val  = "1px solid #00e5a0" if is_today else "1px solid #0e0e18"

            dots = ""
            for evt in evts[:3]:
                color = evt.get("color", "#6b6b80")
                dots += f'<div style="background:{color};width:6px;height:6px;border-radius:50%;margin:1px 1px 0"></div>'

            dots_row = f'<div style="display:flex;flex-wrap:wrap;margin-top:4px">{dots}</div>' if dots else ""
            title_attr = " | ".join(e["title"] for e in evts) if evts else ""
            title_html = f'title="{title_attr}"' if title_attr else ""

            cells += f"""
            <div {title_html} style="background:{bg_color};border:{border_val};
                  border-radius:4px;padding:5px 6px;min-height:52px;cursor:default">
              <div style="font-family:'Space Mono',monospace;font-size:10px;
                          font-weight:700;color:{num_color}">{day_num}</div>
              {dots_row}
            </div>"""

    st.markdown(f"""
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-bottom:4px">
      {header}
    </div>
    <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px">
      {cells}
    </div>
    <div style="display:flex;gap:12px;margin-top:10px;flex-wrap:wrap">
      <span style="font-size:10px;color:#6b6b80">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                     background:#f59e0b;margin-right:4px"></span>F&O Expiry
      </span>
      <span style="font-size:10px;color:#6b6b80">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                     background:#00e5a0;margin-right:4px"></span>Results
      </span>
      <span style="font-size:10px;color:#6b6b80">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                     background:#ef4444;margin-right:4px"></span>Budget
      </span>
      <span style="font-size:10px;color:#6b6b80">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;
                     background:#4a4a60;margin-right:4px"></span>Market Closed
      </span>
    </div>
    """, unsafe_allow_html=True)
