"""
frontend/portfolio_components.py
All reusable UI components for the Portfolio tab.
"""

import streamlit as st
from backend.constants import STOCKS


# ── Portfolio summary bar ──────────────────────────────────────────────────────

def render_portfolio_summary(totals: dict) -> None:
    inv  = totals["total_invested"]
    cur  = totals["total_current"]
    pnl  = totals["total_pnl"]
    pct  = totals["total_pnl_pct"]
    best = totals.get("best")
    worst= totals.get("worst")

    pnl_col  = "stat-green" if pnl  >= 0 else "stat-red"
    pct_sign = "+" if pct >= 0 else ""

    best_html  = (f'<div class="stat-sub">{best["symbol"]} {best["pnl_pct"]:+.2f}%</div>'
                  if best else "")
    worst_html = (f'<div class="stat-sub">{worst["symbol"]} {worst["pnl_pct"]:+.2f}%</div>'
                  if worst else "")

    st.markdown(f"""
    <div class="stat-bar">
      <div class="stat-item">
        <div class="stat-label">Total Invested</div>
        <div class="stat-value">₹{inv:,.0f}</div>
        <div class="stat-sub">{totals['n_profit']+totals['n_loss']} holdings</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Current Value</div>
        <div class="stat-value {pnl_col}">₹{cur:,.0f}</div>
        <div class="stat-sub">live prices</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Total P&amp;L</div>
        <div class="stat-value {pnl_col}">₹{pnl:+,.0f}</div>
        <div class="stat-sub {pnl_col}">{pct_sign}{pct:.2f}%</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Best / Worst</div>
        <div class="stat-value stat-green">{best["pnl_pct"]:+.1f}%" if best else "—"</div>
        <div class="stat-sub stat-red">{worst["pnl_pct"]:+.1f}%  {worst["symbol"]}" if worst else "—"</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_portfolio_summary_v2(totals: dict) -> None:
    """Clean version without fstring nesting issues."""
    inv  = totals["total_invested"]
    cur  = totals["total_current"]
    pnl  = totals["total_pnl"]
    pct  = totals["total_pnl_pct"]
    best = totals.get("best")
    worst= totals.get("worst")

    pnl_col = "#00e5a0" if pnl >= 0 else "#ff4560"
    n_hold  = totals['n_profit'] + totals['n_loss']

    best_str  = f"{best['symbol']} {best['pnl_pct']:+.1f}%"   if best  else "—"
    worst_str = f"{worst['symbol']} {worst['pnl_pct']:+.1f}%" if worst else "—"

    st.markdown(f"""
    <div class="stat-bar">
      <div class="stat-item">
        <div class="stat-label">Total Invested</div>
        <div class="stat-value">₹{inv:,.0f}</div>
        <div class="stat-sub">{n_hold} holdings</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Current Value</div>
        <div class="stat-value" style="color:{pnl_col}">₹{cur:,.0f}</div>
        <div class="stat-sub">live prices (5-min cache)</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Total P&amp;L</div>
        <div class="stat-value" style="color:{pnl_col}">₹{pnl:+,.0f}</div>
        <div class="stat-sub" style="color:{pnl_col}">{pct:+.2f}%</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Best / Worst</div>
        <div class="stat-value stat-green" style="font-size:14px">{best_str}</div>
        <div class="stat-sub stat-red">{worst_str}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Holdings table ─────────────────────────────────────────────────────────────

def render_holdings_table(rows: list[dict]) -> None:
    """Full holdings table using st.dataframe for reliable rendering."""
    import pandas as pd

    if not rows:
        st.markdown('<div class="empty-state"><div class="empty-icon">💼</div>'
                    '<div class="empty-title">No holdings yet</div>'
                    '<div class="empty-sub">Add your first stock below</div></div>',
                    unsafe_allow_html=True)
        return

    # Build clean DataFrame
    records = []
    for r in rows:
        records.append({
            "Symbol":      r["symbol"],
            "Sector":      r["sector"],
            "Qty":         r["qty"],
            "Avg Buy (₹)": r["avg_buy_price"],
            "Live (₹)":    r["current_price"] if r["current_price"] > 0 else None,
            "Invested (₹)":r["invested"],
            "Current (₹)": r["current_val"],
            "P&L (₹)":     r["pnl"],
            "P&L %":       r["pnl_pct"],
            "ML Advice":   r["advice"],
            "Reason":      r["advice_reason"],
        })

    df = pd.DataFrame(records)

    # Colour P&L columns: green if positive, red if negative
    def colour_pnl(val):
        if isinstance(val, (int, float)):
            color = "#00e5a0" if val >= 0 else "#ff4560"
            return f"color: {color}; font-weight: 700"
        return ""

    def colour_advice(val):
        val = str(val)
        if "BUY" in val:    return "color: #10b981; font-weight: 600"
        if "HOLD" in val:   return "color: #f59e0b; font-weight: 600"
        if "STOP" in val or "BOOK" in val: return "color: #ef4444; font-weight: 600"
        if "REDUCE" in val: return "color: #f59e0b; font-weight: 600"
        return "color: #888888"

    styled = (
        df.style
        .applymap(colour_pnl,     subset=["P&L (₹)", "P&L %"])
        .applymap(colour_advice,  subset=["ML Advice"])
        .format({
            "Avg Buy (₹)":  "₹{:,.2f}",
            "Live (₹)":     "₹{:,.2f}",
            "Invested (₹)": "₹{:,.0f}",
            "Current (₹)":  "₹{:,.0f}",
            "P&L (₹)":      "₹{:+,.0f}",
            "P&L %":        "{:+.2f}%",
            "Qty":          "{:,}",
        }, na_rep="N/A")
        .set_properties(**{
            "background-color": "#0c0c12",
            "color":            "#e8e8f0",
            "border":           "1px solid #1e1e2e",
            "font-size":        "13px",
        })
        .set_table_styles([
            {"selector": "thead th", "props": [
                ("background-color", "#050508"),
                ("color",            "#00e5a0"),
                ("font-family",      "'Space Mono', monospace"),
                ("font-size",        "10px"),
                ("letter-spacing",   "1.5px"),
                ("text-transform",   "uppercase"),
                ("border-bottom",    "2px solid #00e5a0"),
                ("padding",          "10px 14px"),
            ]},
            {"selector": "tbody tr:hover td", "props": [
                ("background-color", "#12121a"),
            ]},
            {"selector": "td", "props": [
                ("padding",          "9px 14px"),
                ("border-bottom",    "1px solid #1a1a28"),
            ]},
        ])
    )

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=min(80 + len(rows) * 52, 600),  # auto-height, max 600px
    )


# ── Add holding form ───────────────────────────────────────────────────────────

def render_add_holding_form() -> tuple | None:
    """
    Renders add-holding form. Returns (symbol, qty, price, date) on submit,
    or None if not submitted.
    """
    st.markdown("""
    <div style="background:#0c0c12;border:1px solid #1e1e2e;border-radius:10px;
                padding:20px 24px 16px;margin:16px 0 8px">
      <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:3px;
                  text-transform:uppercase;color:#4a4a60;margin-bottom:14px">
        ➕ &nbsp; ADD HOLDING
      </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4, col5 = st.columns([2.5, 1.5, 2, 2, 1.5])

    with col1:
        symbol = st.selectbox(
            "Stock Symbol",
            options=sorted(STOCKS.keys()),
            key="pf_symbol",
        )
    with col2:
        qty = st.number_input(
            "Quantity (shares)",
            min_value=1, max_value=1_000_000,
            value=10, step=1,
            key="pf_qty",
        )
    with col3:
        price = st.number_input(
            "Buy Price (₹)",
            min_value=0.01, max_value=1_000_000.0,
            value=1000.0, step=0.5, format="%.2f",
            key="pf_price",
        )
    with col4:
        from datetime import date
        buy_date = st.date_input(
            "Buy Date",
            value=date.today(),
            max_value=date.today(),
            key="pf_date",
        )
    with col5:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        submitted = st.button("➕  ADD", use_container_width=True, type="primary",
                              key="pf_add_btn")

    st.markdown("</div>", unsafe_allow_html=True)

    if submitted:
        return symbol, int(qty), float(price), str(buy_date)
    return None


# ── Remove / manage holdings ───────────────────────────────────────────────────

def render_manage_holdings(rows: list[dict]) -> str | None:
    """
    Renders a row of remove buttons for each holding.
    Returns the symbol to remove, or None.
    """
    if not rows:
        return None

    st.markdown("""
    <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:3px;
                text-transform:uppercase;color:#4a4a60;margin:20px 0 8px">
      🗑 &nbsp; REMOVE HOLDING
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(min(len(rows), 8))
    to_remove = None
    for i, r in enumerate(rows):
        with cols[i % 8]:
            if st.button(f"✕ {r['symbol']}", key=f"rm_{r['symbol']}",
                         use_container_width=True):
                to_remove = r["symbol"]
    return to_remove


# ── Advice summary cards ───────────────────────────────────────────────────────

def render_advice_cards(rows: list[dict]) -> None:
    """Show top advice cards — the most urgent actions first."""
    if not rows:
        return

    # Sort by urgency: STOP LOSS > BOOK PROFIT > BUY MORE > AVERAGE DOWN > rest
    urgency = {
        "STOP LOSS":    0, "BOOK PROFIT": 1, "BUY MORE":     2,
        "AVERAGE DOWN": 3, "BOOK PARTIAL":4, "HOLD / ADD":   5,
        "REDUCE":       6, "HOLD":        7, "NO ML DATA":   8, "REVIEW": 9,
    }
    def _sort_key(r):
        for k, v in urgency.items():
            if k in r.get("advice",""):
                return v
        return 99

    sorted_rows = sorted(rows, key=_sort_key)[:5]

    cols = st.columns(len(sorted_rows))
    for i, r in enumerate(sorted_rows):
        with cols[i]:
            pnl_col = "#00e5a0" if r["pnl_pct"] >= 0 else "#ff4560"
            price_str = f"₹{r['current_price']:,.0f}" if r['current_price'] > 0 else "—"
            st.markdown(f"""
            <div class="stock-card" style="--accent-color:{r['advice_color']}">
              <div class="card-symbol">{r['symbol']}</div>
              <div class="card-sector">{r['sector']}</div>
              <div class="card-signal" style="color:{r['advice_color']};font-size:12px;margin:6px 0">
                {r['advice']}
              </div>
              <hr class="card-divider">
              <div class="card-detail" style="text-align:left;font-size:10px;line-height:1.7">
                Live: {price_str}<br>
                Avg: ₹{r['avg_buy_price']:,.0f} &middot; {r['qty']} shares<br>
                P&L: <span style="color:{pnl_col}">{r['pnl_pct']:+.2f}%</span>
                &nbsp;₹<span style="color:{pnl_col}">{r['pnl']:+,.0f}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)


# ── Import / Export controls ───────────────────────────────────────────────────

def render_portfolio_io(portfolio: dict):
    """Export JSON download + import upload."""
    from backend.portfolio import export_portfolio_json, import_portfolio_json

    st.markdown("""
    <div style="font-family:'Space Mono',monospace;font-size:9px;letter-spacing:3px;
                text-transform:uppercase;color:#4a4a60;margin:20px 0 8px">
      📁 &nbsp; SAVE / LOAD PORTFOLIO
    </div>
    """, unsafe_allow_html=True)

    col_exp, col_imp, _ = st.columns([2, 3, 5])

    with col_exp:
        json_str = export_portfolio_json(portfolio)
        st.download_button(
            "💾  Export JSON",
            data=json_str,
            file_name="my_portfolio.json",
            mime="application/json",
            use_container_width=True,
            key="pf_export",
        )

    with col_imp:
        uploaded = st.file_uploader(
            "Import JSON",
            type=["json"],
            label_visibility="collapsed",
            key="pf_import",
        )
        if uploaded is not None:
            content = uploaded.read().decode("utf-8")
            imported, err = import_portfolio_json(content)
            if err:
                st.error(f"Import failed: {err}")
            else:
                st.session_state["portfolio"] = imported
                st.success(f"Imported {len(imported)} holdings!")
                st.rerun()
