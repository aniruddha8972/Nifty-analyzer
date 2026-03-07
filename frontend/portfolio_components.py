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
    """Full holdings table with P&L and ML advice per row."""
    if not rows:
        st.markdown('<div class="empty-state"><div class="empty-icon">💼</div>'
                    '<div class="empty-title">No holdings yet</div>'
                    '<div class="empty-sub">Add your first stock below</div></div>',
                    unsafe_allow_html=True)
        return

    # Build HTML table
    rows_html = ""
    for r in rows:
        pnl_col   = "#00e5a0" if r["pnl"] >= 0 else "#ff4560"
        price_str = f"₹{r['current_price']:,.2f}" if r['current_price'] > 0 else "N/A"
        rows_html += f"""
        <tr>
          <td style="font-family:'Space Mono',monospace;font-weight:700;color:#e8e8f0">{r['symbol']}</td>
          <td style="color:#6b6b80;font-size:11px">{r['sector']}</td>
          <td style="font-family:'Space Mono',monospace">{r['qty']}</td>
          <td style="font-family:'Space Mono',monospace">₹{r['avg_buy_price']:,.2f}</td>
          <td style="font-family:'Space Mono',monospace">{price_str}</td>
          <td style="font-family:'Space Mono',monospace">₹{r['invested']:,.0f}</td>
          <td style="font-family:'Space Mono',monospace;color:{pnl_col}">₹{r['current_val']:,.0f}</td>
          <td style="font-family:'Space Mono',monospace;font-weight:700;color:{pnl_col}">₹{r['pnl']:+,.0f}</td>
          <td style="font-family:'Space Mono',monospace;font-weight:700;color:{pnl_col}">{r['pnl_pct']:+.2f}%</td>
          <td style="font-weight:600;color:{r['advice_color']};white-space:nowrap">{r['advice']}</td>
        </tr>
        <tr>
          <td colspan="10" style="padding:2px 12px 10px 12px;font-family:'DM Sans',sans-serif;
              font-size:11px;color:#555570;border-bottom:1px solid #1e1e2e">
            {r['advice_reason']}
          </td>
        </tr>
        """

    st.markdown(f"""
    <div style="overflow-x:auto;margin:12px 0">
      <table style="width:100%;border-collapse:collapse;font-family:'DM Sans',sans-serif;font-size:13px">
        <thead>
          <tr style="background:#0c0c12;border-bottom:2px solid #00e5a0">
            <th style="padding:10px 12px;text-align:left;font-family:'Space Mono',monospace;
                font-size:10px;letter-spacing:1.5px;color:#00e5a0">SYMBOL</th>
            <th style="padding:10px 12px;text-align:left;font-size:10px;letter-spacing:1px;color:#4a4a60">SECTOR</th>
            <th style="padding:10px 12px;text-align:center;font-size:10px;letter-spacing:1px;color:#4a4a60">QTY</th>
            <th style="padding:10px 12px;text-align:center;font-size:10px;letter-spacing:1px;color:#4a4a60">AVG BUY ₹</th>
            <th style="padding:10px 12px;text-align:center;font-size:10px;letter-spacing:1px;color:#4a4a60">LIVE ₹</th>
            <th style="padding:10px 12px;text-align:center;font-size:10px;letter-spacing:1px;color:#4a4a60">INVESTED</th>
            <th style="padding:10px 12px;text-align:center;font-size:10px;letter-spacing:1px;color:#4a4a60">CURRENT</th>
            <th style="padding:10px 12px;text-align:center;font-size:10px;letter-spacing:1px;color:#4a4a60">P&amp;L ₹</th>
            <th style="padding:10px 12px;text-align:center;font-size:10px;letter-spacing:1px;color:#4a4a60">P&amp;L %</th>
            <th style="padding:10px 12px;text-align:left;font-size:10px;letter-spacing:1px;color:#4a4a60">ML ADVICE</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
    """, unsafe_allow_html=True)


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
