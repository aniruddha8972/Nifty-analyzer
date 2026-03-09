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


def _get_active_universe() -> dict:
    """Return stock universe for the currently selected index."""
    import streamlit as _st
    from backend.constants import INDEX_UNIVERSE, NIFTY_50
    idx = _st.session_state.get("selected_index", "Nifty 50")
    return INDEX_UNIVERSE.get(idx, NIFTY_50)


def _section(title: str, subtitle: str = "") -> None:
    sub_html = f'<span style="font-size:11px;color:#5a5a78;margin-left:12px">{subtitle}</span>' if subtitle else ""
    st.markdown(f"""
    <div style="margin:4px 0 18px">
      <span style="font-family:'IBM Plex Mono',monospace;font-size:13px;
                   font-weight:700;color:#eeeef8">{title}</span>
      {sub_html}
    </div>
    """, unsafe_allow_html=True)


def _metric(label: str, value: str, color: str = "#eeeef8", sub: str = "") -> str:
    sub_html = f'<div style="font-size:10px;color:#5a5a78;margin-top:2px">{sub}</div>' if sub else ""
    return f"""
    <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                padding:14px 16px;text-align:center">
      <div style="font-family:'Inter',sans-serif;font-size:10px;
                  letter-spacing:1px;text-transform:uppercase;color:#5a5a78;
                  margin-bottom:6px">{label}</div>
      <div style="font-family:'IBM Plex Mono',monospace;font-size:18px;
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
            paper_bgcolor="#04040a",
            plot_bgcolor="#04040a",
            margin=dict(t=10, l=0, r=0, b=0),
            height=460,
            coloraxis_colorbar=dict(
                title="Return %",
                tickfont=dict(color="#6b6b80", size=10),
                title_font=dict(color="#6b6b80"),
                bgcolor="#09090f",
                bordercolor="#1c1c2e",
                len=0.8,
            ),
            font=dict(family="Inter", color="#eeeef8"),
        )

        st.plotly_chart(fig, key="heatmap_treemap")

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
            <div style="background:#09090f;border:1px solid #1c1c2e;
                        border-left:3px solid {color};border-radius:8px;
                        padding:12px;text-align:center">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                          letter-spacing:1px;color:#5a5a78;text-transform:uppercase;
                          margin-bottom:6px">{sec['sector']}</div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:16px;
                          font-weight:700;color:{color}">{sign}{chg:.2f}%</div>
              <div style="font-size:10px;color:#33334a;margin-top:4px">
                {sec['sector_gainers']}↑ {sec['sector_losers']}↓
              </div>
            </div>
            """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  2. BACKTESTING ENGINE
# ══════════════════════════════════════════════════════════════════════

def render_backtest_tab() -> None:
    """Backtest UI — uses active index universe from session state."""
    from backend.analytics import run_backtest
    from backend.data import fetch_ohlcv
    _universe  = _get_active_universe()
    _idx_name  = __import__("streamlit").session_state.get("selected_index", "Nifty 50")
    _idx_count = len(_universe)
    _section("Backtest Engine",
             f"Walk-forward simulation · {_idx_name} ({_idx_count} stocks) · 3yr history")

    st.markdown("""
    <div style="background:#0a1a10;border:1px solid #1a3a28;border-radius:8px;
                padding:12px 16px;margin-bottom:16px;font-family:'Inter',sans-serif;
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
        <div style="text-align:center;padding:60px 0;color:#33334a;
                    font-family:'IBM Plex Mono',monospace;font-size:12px">
          Configure strategy above and click ▶ Run Backtest
        </div>
        """, unsafe_allow_html=True)
        return

    if run_btn:
        with st.spinner(f"Running backtest on {_idx_count} stocks ({_idx_name}) · 3yr history…"):
            # Fetch 3yr OHLCV for each stock
            from datetime import date, timedelta
            end   = date.today()
            start = end - timedelta(days=3 * 365)
            cache = {}
            prog  = st.progress(0)
            syms  = list(_universe.keys())
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
            fig.add_hline(y=0, line_dash="dot", line_color="#33334a", line_width=1)
            fig.update_layout(
                paper_bgcolor="#04040a", plot_bgcolor="#04040a",
                height=260, margin=dict(t=10, l=0, r=0, b=0),
                xaxis=dict(gridcolor="#1c1c2e", color="#6b6b80"),
                yaxis=dict(gridcolor="#1c1c2e", color="#6b6b80",
                           title="Cumulative Return %"),
                font=dict(family="Inter", color="#6b6b80"),
                showlegend=False,
            )
            st.plotly_chart(fig, key="backtest_equity")
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
            .set_properties(**{"background-color":"#09090f","color":"#eeeef8",
                               "border":"1px solid #1c1c2e"})
        )
        _section("Per-Stock Backtest Results")
        st.dataframe(styled, width="stretch", hide_index=True, height=300)


# ══════════════════════════════════════════════════════════════════════
#  3. CORRELATION MATRIX
# ══════════════════════════════════════════════════════════════════════

def render_correlation_tab(portfolio_symbols: list[str] | None = None) -> None:
    """Correlation matrix + diversification — uses active index universe."""
    from backend.analytics import (
        build_correlation_matrix, get_top_correlations,
        get_portfolio_diversification
    )
    from backend.data import fetch_ohlcv
    _universe  = _get_active_universe()
    _idx_name  = __import__("streamlit").session_state.get("selected_index", "Nifty 50")
    _idx_count = len(_universe)
    _section("Correlation Matrix",
             f"1-year daily return correlations · {_idx_name} ({_idx_count} stocks)")

    run_btn = st.button("🔄  Compute Correlations", type="primary", key="corr_run")

    if not run_btn and "corr_result" not in st.session_state:
        st.markdown("""
        <div style="text-align:center;padding:60px 0;color:#33334a;
                    font-family:'IBM Plex Mono',monospace;font-size:12px">
          Click Compute Correlations to analyse the active index (cached for session)
        </div>
        """, unsafe_allow_html=True)
        return

    if run_btn:
        with st.spinner(f"Fetching 1 year of data for {_idx_count} stocks ({_idx_name})…"):
            from datetime import date, timedelta
            end   = date.today()
            start = end - timedelta(days=365)
            cache = {}
            prog  = st.progress(0)
            syms  = list(_universe.keys())
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
            <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:10px;
                        padding:16px 20px;margin-bottom:20px;display:flex;align-items:center;gap:20px">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:32px;
                          font-weight:700;color:{s_color}">{score}</div>
              <div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;
                            letter-spacing:2px;color:#5a5a78;text-transform:uppercase">
                  Your Portfolio Diversification Score
                </div>
                <div style="font-family:'Inter',sans-serif;font-size:13px;
                            color:#eeeef8;margin-top:4px">{div['message']}</div>
                <div style="font-family:'Inter',sans-serif;font-size:11px;
                            color:#5a5a78;margin-top:2px">
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
            paper_bgcolor="#04040a", plot_bgcolor="#04040a",
            height=600, margin=dict(t=10, l=0, r=0, b=0),
            xaxis=dict(tickfont=dict(size=8, color="#6b6b80"), tickangle=45),
            yaxis=dict(tickfont=dict(size=8, color="#6b6b80")),
            font=dict(family="Inter"),
        )
        st.plotly_chart(fig, key="corr_heatmap")
    except ImportError:
        st.info("Install plotly for the correlation heatmap visualization.")

    # ── Top correlated pairs ───────────────────────────────────────────
    most_corr, most_inv = get_top_correlations(corr_matrix, top_n=8)

    def _colour_corr_high(val):
        """Green for high positive correlation (bad — stocks move together)."""
        if not isinstance(val, float):
            return ""
        intensity = int(abs(val) * 180)
        if val >= 0.7:
            return f"color:#ff4560;font-weight:700"
        elif val >= 0.4:
            return f"color:#f59e0b;font-weight:600"
        return "color:#eeeef8"

    def _colour_corr_low(val):
        """Green for low/negative correlation (good — natural hedge)."""
        if not isinstance(val, float):
            return ""
        if val <= -0.1:
            return "color:#00e5a0;font-weight:700"
        elif val <= 0.2:
            return "color:#34d399;font-weight:600"
        return "color:#eeeef8"

    c1, c2 = st.columns(2)
    with c1:
        _section("Most Correlated Pairs", "move together — avoid holding both")
        if most_corr:
            rows = [{"Stock A": p["stock_a"], "Stock B": p["stock_b"],
                     "Correlation": p["correlation"]} for p in most_corr]
            pair_df = pd.DataFrame(rows)
            styled  = (pair_df.style
                       .format({"Correlation": "{:.3f}"})
                       .map(_colour_corr_high, subset=["Correlation"])
                       .set_properties(**{"background-color": "#09090f",
                                          "color": "#eeeef8",
                                          "border": "1px solid #1c1c2e"}))
            st.dataframe(styled, width="stretch", hide_index=True)

    with c2:
        _section("Most Inverse Pairs", "natural hedges — good for diversification")
        if most_inv:
            rows = [{"Stock A": p["stock_a"], "Stock B": p["stock_b"],
                     "Correlation": p["correlation"]} for p in most_inv]
            pair_df = pd.DataFrame(rows)
            styled  = (pair_df.style
                       .format({"Correlation": "{:.3f}"})
                       .map(_colour_corr_low, subset=["Correlation"])
                       .set_properties(**{"background-color": "#09090f",
                                          "color": "#eeeef8",
                                          "border": "1px solid #1c1c2e"}))
            st.dataframe(styled, width="stretch", hide_index=True)


# ══════════════════════════════════════════════════════════════════════
#  4. EVENTS CALENDAR
# ══════════════════════════════════════════════════════════════════════

_EVENT_COLORS = {
    "fo_expiry":      "#f59e0b",
    "results":        "#00e5a0",
    "results_season": "#8b5cf6",
    "market_closed":  "#5a5a78",
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
    <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:3px;
                text-transform:uppercase;color:#5a5a78;margin-bottom:12px">
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
                color     = evt.get("color", "#6b6b80")
                # Only append opacity suffix for 7-char hex colours (#rrggbb)
                border_color = f"{color}44" if color.startswith("#") and len(color) == 7 else color
                desc_text = evt.get("description", "")
                desc_html = f'<span style="color:#6b6b80;font-size:10px"> — {desc_text}</span>' if desc_text else ""
                evts_html += (
                    f'<span style="display:inline-block;background:rgba(0,0,0,0.3);'
                    f'border:1px solid {border_color};border-radius:4px;'
                    f'padding:2px 8px;margin:2px;font-size:11px;color:{color}">'
                    f'{evt["title"]}{desc_html}</span>'
                )

            badge_color = "#ff4560" if days_away <= 3 else "#f59e0b" if days_away <= 7 else "#5a5a78"
            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:16px;
                        padding:12px 0;border-bottom:1px solid #0e0e18">
              <div style="min-width:120px;text-align:right">
                <div style="font-family:'IBM Plex Mono',monospace;font-size:13px;
                            font-weight:700;color:#eeeef8">
                  {d_obj.strftime('%d %b %Y')}
                </div>
                <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
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
        raw_month    = today.month + m_offset - 1   # 0-indexed
        target_year  = today.year + raw_month // 12
        target_month = raw_month % 12 + 1

        month_name = date(target_year, target_month, 1).strftime("%B %Y")
        st.markdown(f"""
        <div style="font-family:'IBM Plex Mono',monospace;font-size:11px;letter-spacing:2px;
                    text-transform:uppercase;color:#00e5a0;margin:20px 0 8px">
          {month_name}
        </div>
        """, unsafe_allow_html=True)

        _render_month_grid(target_year, target_month, events_dict, today)


def _render_month_grid(year: int, month: int,
                       events_dict: dict, today: date) -> None:
    import calendar as _cal
    cal  = _cal.monthcalendar(year, month)
    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

    # Day-name header row — single line per cell
    header = "".join(
        f'<div style="text-align:center;font-family:IBM Plex Mono,monospace;'
        f'font-size:9px;letter-spacing:1px;color:#33334a;padding:4px">{d}</div>'
        for d in days
    )

    cells = ""
    for week in cal:
        for day_num in week:
            if day_num == 0:
                cells += '<div style="background:#04040a;border-radius:4px;min-height:52px"></div>'
                continue

            d          = date(year, month, day_num)
            d_str      = str(d)
            evts       = events_dict.get(d_str, [])
            is_today   = d == today
            is_weekend = d.weekday() >= 5

            bg     = "#0a1520" if is_today else "#09090f"
            nc     = "#00e5a0" if is_today else ("#6b6b80" if is_weekend else "#eeeef8")
            border = "1px solid #00e5a0" if is_today else "1px solid #0e0e18"

            # Coloured dots for events — one line each
            dots = "".join(
                f'<div style="display:inline-block;width:7px;height:7px;'
                f'border-radius:50%;background:{e.get("color","#6b6b80")};'
                f'margin:1px"></div>'
                for e in evts[:3]
            )
            dots_html = f'<div style="margin-top:3px">{dots}</div>' if dots else ""

            # Tooltip — ascii only, no quotes
            tip = " | ".join(
                e["title"].encode("ascii", "ignore").decode().replace('"', "")
                for e in evts
            )
            tip_attr = f'title="{tip}"' if tip else ""

            # Everything on ONE line — critical for Streamlit markdown
            cells += (
                f'<div {tip_attr} style="background:{bg};border:{border};'
                f'border-radius:4px;padding:5px 6px;min-height:52px;cursor:default">'
                f'<div style="font-family:IBM Plex Mono,monospace;font-size:10px;'
                f'font-weight:700;color:{nc}">{day_num}</div>'
                f'{dots_html}</div>'
            )

    # Legend items
    legend_items = [
        ("#f59e0b", "F&amp;O Expiry"),
        ("#00e5a0", "Results"),
        ("#8b5cf6", "Results Season"),
        ("#ef4444", "Budget"),
        ("#5a5a78", "Market Closed"),
    ]
    legend = "".join(
        f'<span style="font-size:10px;color:#6b6b80;margin-right:14px">'
        f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
        f'background:{c};margin-right:4px;vertical-align:middle"></span>{label}</span>'
        for c, label in legend_items
    )

    st.markdown(
        f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-bottom:4px">{header}</div>'
        f'<div style="display:grid;grid-template-columns:repeat(7,1fr);gap:3px">{cells}</div>'
        f'<div style="margin-top:10px;display:flex;flex-wrap:wrap">{legend}</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════
#  NEWS FEED TAB
# ══════════════════════════════════════════════════════════════════════

def render_news_tab(data: list[dict]) -> None:
    """
    News Feed tab — shows Google News headlines per stock.
    Only stocks that have at least 1 article in the last 48h are shown.
    data: list of enriched stat dicts from predict().
    """
    import streamlit as st
    from datetime import datetime, timezone

    _section("Market News Feed",
             "Google News · last 48h · stocks with coverage only")

    if not data:
        st.markdown(
            '<div style="text-align:center;padding:60px 0;color:#33334a;'
            'font-family:\'IBM Plex Mono\',monospace;font-size:12px">'
            'Run analysis first to load news.</div>',
            unsafe_allow_html=True,
        )
        return

    # Filter to stocks that have news
    with_news = [
        s for s in data
        if s.get("news_count", 0) > 0 and s.get("news_headlines")
    ]

    if not with_news:
        st.markdown(
            '<div style="text-align:center;padding:60px 0;color:#33334a;'
            'font-family:\'IBM Plex Mono\',monospace;font-size:12px">'
            'No recent news found for any stock in the current universe.<br>'
            'Google News may be rate-limiting — try refreshing in 5 minutes.</div>',
            unsafe_allow_html=True,
        )
        return

    # Sort by news_count desc, then by |sentiment| desc (most newsworthy first)
    with_news.sort(
        key=lambda s: (s.get("news_count", 0), abs(s.get("sentiment", 0.0))),
        reverse=True,
    )

    # ── Summary bar ───────────────────────────────────────────────────
    total_articles = sum(s.get("news_count", 0) for s in with_news)
    pos_stocks = sum(1 for s in with_news if s.get("sentiment", 0) > 0.1)
    neg_stocks = sum(1 for s in with_news if s.get("sentiment", 0) < -0.1)
    neu_stocks = len(with_news) - pos_stocks - neg_stocks

    st.markdown(f"""
    <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap">
      <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                  padding:12px 20px;min-width:120px;text-align:center">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                    margin-bottom:4px">Stocks covered</div>
        <div style="font-size:22px;font-weight:700;color:#e0e0ff">{len(with_news)}</div>
      </div>
      <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                  padding:12px 20px;min-width:120px;text-align:center">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                    margin-bottom:4px">Total articles</div>
        <div style="font-size:22px;font-weight:700;color:#e0e0ff">{total_articles}</div>
      </div>
      <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                  padding:12px 20px;min-width:120px;text-align:center">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                    margin-bottom:4px">Positive tone</div>
        <div style="font-size:22px;font-weight:700;color:#00e5a0">{pos_stocks}</div>
      </div>
      <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                  padding:12px 20px;min-width:120px;text-align:center">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                    margin-bottom:4px">Negative tone</div>
        <div style="font-size:22px;font-weight:700;color:#ff4560">{neg_stocks}</div>
      </div>
      <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                  padding:12px 20px;min-width:120px;text-align:center">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                    margin-bottom:4px">Neutral</div>
        <div style="font-size:22px;font-weight:700;color:#5a5a78">{neu_stocks}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Optional sector filter ─────────────────────────────────────────
    sectors = sorted({s.get("sector", "Other") for s in with_news})
    filter_col, search_col = st.columns([2, 3])
    with filter_col:
        selected_sector = st.selectbox(
            "Filter by sector",
            ["All sectors"] + sectors,
            key="news_sector_filter",
        )
    with search_col:
        search_sym = st.text_input(
            "Search symbol",
            placeholder="e.g. RELIANCE",
            key="news_sym_search",
        ).strip().upper()

    if selected_sector != "All sectors":
        with_news = [s for s in with_news if s.get("sector") == selected_sector]
    if search_sym:
        with_news = [s for s in with_news if search_sym in s.get("symbol", "")]

    if not with_news:
        st.info("No stocks match your filter.")
        return

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Per-stock news cards ───────────────────────────────────────────
    for s in with_news:
        sym       = s.get("symbol", "")
        sector    = s.get("sector", "")
        sent      = s.get("sentiment", 0.0)
        conf      = s.get("sent_confidence", 0.0)
        n_art     = s.get("news_count", 0)
        latest_ts = s.get("news_latest", "")
        headlines = s.get("news_headlines", [])
        signal    = s.get("signal", "🟠 HOLD")
        sig_color = s.get("sig_color", "#f59e0b")
        ml_score  = s.get("final_score", 50.0)

        # Sentiment colour and label
        if   sent >  0.3: sent_col, sent_label = "#00e5a0", "Positive"
        elif sent < -0.3: sent_col, sent_label = "#ff4560", "Negative"
        else:             sent_col, sent_label = "#f59e0b", "Neutral"

        # Confidence bar (filled squares)
        conf_pct = int(conf * 10)
        conf_bar = "█" * conf_pct + "░" * (10 - conf_pct)

        # Build headline list HTML
        hl_items = "".join(
            f'<li style="margin-bottom:6px;color:#c0c0d8;font-size:13px;'
            f'font-family:\'Inter\',sans-serif;line-height:1.5">'
            f'{h}</li>'
            for h in headlines
        )

        st.markdown(f"""
        <div style="background:#09090f;border:1px solid #1c1c2e;
                    border-left:3px solid {sig_color};
                    border-radius:10px;padding:16px 20px;margin-bottom:12px">

          <!-- Header row -->
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;
                      flex-wrap:wrap">
            <span style="font-family:'IBM Plex Mono',monospace;font-size:15px;
                         font-weight:700;color:#e0e0ff">{sym}</span>
            <span style="font-size:11px;color:#5a5a78;background:#13131f;
                         border:1px solid #1c1c2e;border-radius:4px;
                         padding:2px 8px">{sector}</span>
            <span style="font-size:11px;color:{sig_color};background:#09090f;
                         border:1px solid {sig_color}44;border-radius:4px;
                         padding:2px 8px">{signal}</span>
            <span style="font-size:11px;color:#5a5a78;margin-left:auto">
              Score&nbsp;<b style="color:#e0e0ff">{ml_score:.0f}</b>/100
            </span>
          </div>

          <!-- Sentiment + stats row -->
          <div style="display:flex;gap:24px;margin-bottom:12px;flex-wrap:wrap">
            <div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                          letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                          margin-bottom:2px">Sentiment</div>
              <div style="font-size:14px;font-weight:600;color:{sent_col}">
                {sent:+.3f} &nbsp;<span style="font-size:11px">{sent_label}</span>
              </div>
            </div>
            <div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                          letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                          margin-bottom:2px">Articles (48h)</div>
              <div style="font-size:14px;font-weight:600;color:#e0e0ff">{n_art}</div>
            </div>
            <div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                          letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                          margin-bottom:2px">Confidence</div>
              <div style="font-size:11px;font-family:'IBM Plex Mono',monospace;
                          color:{sent_col};letter-spacing:1px">{conf_bar}</div>
            </div>
            {f'<div><div style="font-family:\'IBM Plex Mono\',monospace;font-size:8px;letter-spacing:2px;color:#5a5a78;text-transform:uppercase;margin-bottom:2px">Latest</div><div style="font-size:11px;color:#5a5a78">{latest_ts}</div></div>' if latest_ts else ''}
          </div>

          <!-- Headlines -->
          <ul style="margin:0;padding-left:18px">
            {hl_items}
          </ul>

        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  NIFTY INDEX CHARTS TAB
# ══════════════════════════════════════════════════════════════════════

def render_index_charts_tab() -> None:
    """
    Live Nifty index charts — 4 indices × 6 timeframes.
    Uses yfinance for OHLCV, Plotly for candlestick + volume.
    """
    import streamlit as st
    import yfinance as yf
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    from datetime import date, timedelta
    import pandas as pd

    _section("Nifty Index Charts", "Live · OHLCV candlestick · Select index & timeframe")

    # ── Index selector ────────────────────────────────────────────────
    INDEX_MAP = {
        "Nifty 50":        "^NSEI",
        "Nifty Next 50":   "^NSMIDCP",
        "Nifty Midcap 150": "^CRSMID",
        "Nifty Smallcap 250": "^CRSLDX",
    }
    TIMEFRAME_MAP = {
        "1 Day":   {"period": "1d",  "interval": "5m",  "label": "5-min candles"},
        "1 Month": {"period": "1mo", "interval": "1d",  "label": "Daily candles"},
        "6 Months":{"period": "6mo", "interval": "1d",  "label": "Daily candles"},
        "YTD":     {"period": "ytd", "interval": "1d",  "label": "Daily candles"},
        "1 Year":  {"period": "1y",  "interval": "1wk", "label": "Weekly candles"},
        "5 Years": {"period": "5y",  "interval": "1mo", "label": "Monthly candles"},
    }

    col_idx, col_tf = st.columns([2, 2])
    with col_idx:
        sel_index = st.selectbox(
            "Index", list(INDEX_MAP.keys()), key="chart_index"
        )
    with col_tf:
        sel_tf = st.selectbox(
            "Timeframe", list(TIMEFRAME_MAP.keys()),
            index=1, key="chart_timeframe"
        )

    ticker  = INDEX_MAP[sel_index]
    tf_cfg  = TIMEFRAME_MAP[sel_tf]

    # ── Fetch ─────────────────────────────────────────────────────────
    @st.cache_data(ttl=300, show_spinner=False)
    def _fetch_index(ticker: str, period: str, interval: str):
        try:
            df = yf.download(ticker, period=period, interval=interval,
                             auto_adjust=True, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [str(c).strip() for c in df.columns]
            return df.dropna()
        except Exception:
            return None

    with st.spinner(f"Loading {sel_index} ({sel_tf})…"):
        df = _fetch_index(ticker, tf_cfg["period"], tf_cfg["interval"])

    if df is None or df.empty:
        st.error(f"Could not load data for {sel_index}. Yahoo Finance may be temporarily unavailable.")
        return

    # ── Compute indicators ────────────────────────────────────────────
    cl = df["Close"].squeeze().astype(float)
    ma20 = cl.rolling(20).mean()
    ma50 = cl.rolling(50).mean()

    first_c = float(cl.iloc[0])
    last_c  = float(cl.iloc[-1])
    chg_pct = (last_c - first_c) / first_c * 100
    chg_abs = last_c - first_c
    hi      = float(df["High"].squeeze().max())
    lo      = float(df["Low"].squeeze().min())

    chg_col = "#00e5a0" if chg_pct >= 0 else "#ff4560"
    arrow   = "▲" if chg_pct >= 0 else "▼"

    # ── Metrics bar ───────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex;gap:14px;margin-bottom:18px;flex-wrap:wrap">
      <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                  padding:12px 18px;min-width:130px">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                    margin-bottom:4px">{sel_index}</div>
        <div style="font-size:22px;font-weight:700;color:#e0e0ff">
          {last_c:,.2f}
        </div>
        <div style="font-size:13px;font-weight:600;color:{chg_col}">
          {arrow} {chg_abs:+,.2f} ({chg_pct:+.2f}%)
        </div>
      </div>
      <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                  padding:12px 18px;min-width:110px;text-align:center">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                    margin-bottom:4px">Period High</div>
        <div style="font-size:18px;font-weight:700;color:#00e5a0">{hi:,.2f}</div>
      </div>
      <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                  padding:12px 18px;min-width:110px;text-align:center">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                    margin-bottom:4px">Period Low</div>
        <div style="font-size:18px;font-weight:700;color:#ff4560">{lo:,.2f}</div>
      </div>
      <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                  padding:12px 18px;min-width:110px;text-align:center">
        <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:2px;color:#5a5a78;text-transform:uppercase;
                    margin-bottom:4px">Candles</div>
        <div style="font-size:16px;font-weight:600;color:#e0e0ff">{len(df)}</div>
        <div style="font-size:10px;color:#5a5a78">{tf_cfg['label']}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Candlestick chart ─────────────────────────────────────────────
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.78, 0.22],
    )

    op = df["Open"].squeeze().astype(float)
    hi_s = df["High"].squeeze().astype(float)
    lo_s = df["Low"].squeeze().astype(float)

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=op, high=hi_s, low=lo_s, close=cl,
        name=sel_index,
        increasing_line_color="#00e5a0",
        decreasing_line_color="#ff4560",
        increasing_fillcolor="#00e5a0",
        decreasing_fillcolor="#ff4560",
    ), row=1, col=1)

    # MA20
    if not ma20.isna().all():
        fig.add_trace(go.Scatter(
            x=df.index, y=ma20,
            line=dict(color="#4c8eff", width=1.2),
            name="MA 20",
        ), row=1, col=1)

    # MA50
    if not ma50.isna().all():
        fig.add_trace(go.Scatter(
            x=df.index, y=ma50,
            line=dict(color="#f59e0b", width=1.2, dash="dot"),
            name="MA 50",
        ), row=1, col=1)

    # Volume bars
    vol_s = df.get("Volume", None)
    if vol_s is not None:
        vol_s = vol_s.squeeze().astype(float)
        vol_colors = ["#00e5a0" if c >= o else "#ff4560"
                      for c, o in zip(cl.values, op.values)]
        fig.add_trace(go.Bar(
            x=df.index, y=vol_s,
            marker_color=vol_colors,
            opacity=0.6,
            name="Volume",
        ), row=2, col=1)

    fig.update_layout(
        height=520,
        plot_bgcolor="#05050d",
        paper_bgcolor="#05050d",
        font=dict(family="IBM Plex Mono, monospace", color="#8888aa", size=10),
        xaxis_rangeslider_visible=False,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01,
            xanchor="left", x=0,
            font=dict(size=10, color="#8888aa"),
            bgcolor="rgba(0,0,0,0)",
        ),
        margin=dict(l=8, r=8, t=10, b=8),
    )
    fig.update_xaxes(
        gridcolor="#111120", showgrid=True,
        linecolor="#111120", tickfont=dict(size=9),
    )
    fig.update_yaxes(
        gridcolor="#111120", showgrid=True,
        linecolor="#111120", tickfont=dict(size=9),
    )

    st.plotly_chart(fig, use_container_width=True)

    # ── All-4-indices mini-comparison ─────────────────────────────────
    st.markdown("---")
    _section("All Indices — Performance Comparison",
             f"{sel_tf} returns · Refreshed every 5 min")

    mini_cols = st.columns(4)
    for i, (iname, iticker) in enumerate(INDEX_MAP.items()):
        with mini_cols[i]:
            mini_df = _fetch_index(iticker, tf_cfg["period"], "1d")
            if mini_df is not None and not mini_df.empty:
                mcl = mini_df["Close"].squeeze().astype(float)
                mc0 = float(mcl.iloc[0])
                mcl_last = float(mcl.iloc[-1])
                mpct = (mcl_last - mc0) / mc0 * 100 if mc0 else 0.0
                mcolor = "#00e5a0" if mpct >= 0 else "#ff4560"
                marrow = "▲" if mpct >= 0 else "▼"
                is_active = "border:1px solid #00e5a0" if iname == sel_index else "border:1px solid #1c1c2e"
                st.markdown(f"""
                <div style="background:#09090f;{is_active};border-radius:8px;
                            padding:12px;text-align:center">
                  <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                              letter-spacing:1.5px;color:#5a5a78;text-transform:uppercase;
                              margin-bottom:6px">{iname}</div>
                  <div style="font-size:16px;font-weight:700;color:#e0e0ff">
                    {mcl_last:,.0f}
                  </div>
                  <div style="font-size:12px;font-weight:600;color:{mcolor}">
                    {marrow} {mpct:+.2f}%
                  </div>
                </div>""", unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:#09090f;border:1px solid #1c1c2e;
                            border-radius:8px;padding:12px;text-align:center">
                  <div style="font-size:9px;color:#5a5a78">{iname}</div>
                  <div style="font-size:12px;color:#3a3a52">N/A</div>
                </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
#  GLOBAL SENTIMENT TAB (called from render_news_tab as a section)
# ══════════════════════════════════════════════════════════════════════

def render_global_sentiment_section() -> None:
    """Render global market sentiment section — world + India macro news."""
    import streamlit as st
    from backend.sentiment import fetch_global_sentiment
    from datetime import datetime

    _section("Global Market Sentiment",
             "Reuters · BBC · CNBC · FT · ET · Moneycontrol · NSE · 30-min cache")

    with st.spinner("Fetching global news feeds…"):
        g = fetch_global_sentiment()

    mood       = g["mood"]
    mood_color = g["mood_color"]
    overall    = g["overall_score"]
    india_sc   = g["india_score"]
    world_sc   = g["world_score"]
    n_art      = g["n_articles"]
    conf       = g["confidence"]
    headlines  = g["headlines"]
    by_source  = g["by_source"]

    # ── Global mood banner ────────────────────────────────────────────
    conf_pct = int(conf * 10)
    conf_bar = "█" * conf_pct + "░" * (10 - conf_pct)

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(0,0,0,0.6),rgba(0,0,0,0.3));
                border:1px solid {mood_color}33;border-radius:14px;
                padding:20px 24px;margin-bottom:20px;
                border-left:4px solid {mood_color}">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:16px">
        <div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                      letter-spacing:3px;color:#5a5a78;text-transform:uppercase;
                      margin-bottom:6px">Global Market Mood</div>
          <div style="font-size:28px;font-weight:700;color:{mood_color}">{mood}</div>
          <div style="font-size:11px;color:#5a5a78;margin-top:4px;
                      font-family:'IBM Plex Mono',monospace">
            {conf_bar}  confidence {conf:.0%}
          </div>
        </div>
        <div style="display:flex;gap:28px;flex-wrap:wrap">
          <div style="text-align:center">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                        letter-spacing:2px;color:#5a5a78;text-transform:uppercase">Overall</div>
            <div style="font-size:20px;font-weight:700;
                        color:{'#00e5a0' if overall>=0 else '#ff4560'}">{overall:+.2f}</div>
          </div>
          <div style="text-align:center">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                        letter-spacing:2px;color:#5a5a78;text-transform:uppercase">India</div>
            <div style="font-size:20px;font-weight:700;
                        color:{'#00e5a0' if india_sc>=0 else '#ff4560'}">{india_sc:+.2f}</div>
          </div>
          <div style="text-align:center">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                        letter-spacing:2px;color:#5a5a78;text-transform:uppercase">World</div>
            <div style="font-size:20px;font-weight:700;
                        color:{'#00e5a0' if world_sc>=0 else '#ff4560'}">{world_sc:+.2f}</div>
          </div>
          <div style="text-align:center">
            <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                        letter-spacing:2px;color:#5a5a78;text-transform:uppercase">Articles</div>
            <div style="font-size:20px;font-weight:700;color:#e0e0ff">{n_art}</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── By-source breakdown ───────────────────────────────────────────
    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                letter-spacing:3px;color:#3a3a52;text-transform:uppercase;
                margin-bottom:10px">Sources</div>""", unsafe_allow_html=True)

    src_cols = st.columns(4)
    for i, (src, info) in enumerate(by_source.items()):
        sc  = info.get("score", 0.0)
        n   = info.get("n", 0)
        err = info.get("error", False)
        col = "#00e5a0" if sc > 0.05 else "#ff4560" if sc < -0.05 else "#f59e0b"
        with src_cols[i % 4]:
            st.markdown(f"""
            <div style="background:#09090f;border:1px solid #1c1c2e;
                        border-radius:8px;padding:10px 12px;margin-bottom:8px">
              <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                          letter-spacing:1px;color:#5a5a78;margin-bottom:3px">{src}</div>
              {"<div style='font-size:11px;color:#3a3a52'>Unavailable</div>" if err else
               f"<div style='font-size:14px;font-weight:700;color:{col}'>{sc:+.2f}</div>"
               f"<div style='font-size:9px;color:#3a3a52'>{n} articles</div>"}
            </div>""", unsafe_allow_html=True)

    # ── Latest headlines ──────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;
                letter-spacing:3px;color:#3a3a52;text-transform:uppercase;
                margin-bottom:12px">Latest Headlines</div>""", unsafe_allow_html=True)

    for item in headlines[:15]:
        title   = item["title"]
        source  = item["source"]
        sc      = item["score"]
        pub_dt  = item.get("pub_dt")
        is_india = item.get("is_india", False)

        ts_str = ""
        if pub_dt:
            try:
                ts_str = pub_dt.strftime("%d %b · %H:%M UTC")
            except Exception:
                pass

        sc_col   = "#00e5a0" if sc > 0 else "#ff4560" if sc < 0 else "#5a5a78"
        src_badge = f'<span style="background:rgba(0,229,160,0.08);border:1px solid rgba(0,229,160,0.2);border-radius:4px;padding:1px 6px;font-size:8px;color:#00e5a0">India</span>' if is_india else ""

        st.markdown(f"""
        <div style="background:#09090f;border:1px solid #1c1c2e;border-radius:8px;
                    padding:10px 14px;margin-bottom:6px;
                    display:flex;justify-content:space-between;align-items:center">
          <div style="flex:1">
            <div style="font-size:12px;color:#c0c0d8;line-height:1.5">{title}</div>
            <div style="font-family:'IBM Plex Mono',monospace;font-size:8px;
                        color:#3a3a52;margin-top:3px">
              {source} {src_badge}
              {"· " + ts_str if ts_str else ""}
            </div>
          </div>
          <div style="font-family:'IBM Plex Mono',monospace;font-size:12px;
                      font-weight:700;color:{sc_col};margin-left:16px;min-width:40px;
                      text-align:right">{sc:+.1f}</div>
        </div>
        """, unsafe_allow_html=True)
