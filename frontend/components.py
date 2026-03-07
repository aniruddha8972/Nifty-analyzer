"""
frontend/components.py
All reusable Streamlit HTML components.
"""

import streamlit as st


# ── App header ─────────────────────────────────────────────────────────────────

def render_header(label: str = "") -> None:
    date_html = (
        f'<div class="app-range">📅 {label}</div>' if label else ""
    )
    st.markdown(f"""
    <div class="app-header">
      <div class="app-wordmark">Nifty 50 · Market Intelligence</div>
      <div class="app-title">Market Analyzer</div>
      <div class="app-subtitle">
        Real NSE data &nbsp;·&nbsp; ML ensemble prediction
        &nbsp;·&nbsp; Live news sentiment &nbsp;·&nbsp; No API key
      </div>
      {date_html}
    </div>
    """, unsafe_allow_html=True)


# ── Stat bar (4 summary metrics) ───────────────────────────────────────────────

def render_stat_bar(data: list[dict]) -> None:
    changes = [s["change_pct"] for s in data]
    top_g   = max(data, key=lambda x: x["change_pct"])
    top_l   = min(data, key=lambda x: x["change_pct"])
    avg_chg = sum(changes) / len(changes)
    buy_ct  = sum(1 for s in data if "BUY" in s.get("signal", ""))

    g_col = "stat-green" if avg_chg >= 0 else "stat-red"
    sign  = "+" if avg_chg >= 0 else ""

    st.markdown(f"""
    <div class="stat-bar">
      <div class="stat-item">
        <div class="stat-label">Top Gainer</div>
        <div class="stat-value stat-green">{top_g['change_pct']:+.2f}%</div>
        <div class="stat-sub">{top_g['symbol']} · {top_g['sector']}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Top Loser</div>
        <div class="stat-value stat-red">{top_l['change_pct']:+.2f}%</div>
        <div class="stat-sub">{top_l['symbol']} · {top_l['sector']}</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">Avg Return</div>
        <div class="stat-value {g_col}">{sign}{avg_chg:.2f}%</div>
        <div class="stat-sub">{sum(1 for c in changes if c>0)} up · {sum(1 for c in changes if c<0)} down</div>
      </div>
      <div class="stat-item">
        <div class="stat-label">AI Buy Signals</div>
        <div class="stat-value stat-green">{buy_ct}</div>
        <div class="stat-sub">of {len(data)} stocks analysed</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


# ── Section header ─────────────────────────────────────────────────────────────

def render_section(title: str, badge: str = "") -> None:
    badge_html = f'<span class="section-badge">{badge}</span>' if badge else ""
    st.markdown(f"""
    <div class="section-header">
      <span class="section-title">{title}</span>
      {badge_html}
    </div>
    """, unsafe_allow_html=True)


# ── Stock cards ────────────────────────────────────────────────────────────────

def render_gainer_cards(stocks: list[dict]) -> None:
    """Render top 10 gainer cards in 2 rows of 5."""
    cols = st.columns(5)
    for i, s in enumerate(stocks[:10]):
        with cols[i % 5]:
            st.markdown(f"""
            <div class="stock-card" style="--accent-color:#10b981">
              <div class="card-symbol">{s['symbol']}</div>
              <div class="card-sector">{s['sector']}</div>
              <div class="card-change stat-green">{s['change_pct']:+.2f}%</div>
              <hr class="card-divider">
              <div class="card-detail">
                H&nbsp;₹{s['period_high']:,.0f}<br>
                L&nbsp;₹{s['period_low']:,.0f}<br>
                Last&nbsp;₹{s['last_close']:,.0f}
              </div>
            </div>
            """, unsafe_allow_html=True)
        if i == 4:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)


def render_loser_cards(stocks: list[dict]) -> None:
    """Render top 10 loser cards in 2 rows of 5."""
    cols = st.columns(5)
    for i, s in enumerate(stocks[:10]):
        with cols[i % 5]:
            st.markdown(f"""
            <div class="stock-card" style="--accent-color:#ff4560">
              <div class="card-symbol">{s['symbol']}</div>
              <div class="card-sector">{s['sector']}</div>
              <div class="card-change stat-red">{s['change_pct']:+.2f}%</div>
              <hr class="card-divider">
              <div class="card-detail">
                H&nbsp;₹{s['period_high']:,.0f}<br>
                L&nbsp;₹{s['period_low']:,.0f}<br>
                Last&nbsp;₹{s['last_close']:,.0f}
              </div>
            </div>
            """, unsafe_allow_html=True)
        if i == 4:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)


def render_prediction_cards(stocks: list[dict]) -> None:
    """Render top 5 AI prediction cards."""
    cols = st.columns(5)
    for i, s in enumerate(stocks[:5]):
        with cols[i]:
            sent      = s.get("sentiment", 0.0)
            sent_col  = "#00e5a0" if sent >= 0 else "#ff4560"
            pred_ret  = s.get("predicted_return", 0.0)
            pred_col  = "#00e5a0" if pred_ret >= 0 else "#ff4560"
            n_rows    = s.get("training_rows", 0)
            st.markdown(f"""
            <div class="stock-card" style="--accent-color:{s['sig_color']}">
              <div class="card-symbol">{s['symbol']}</div>
              <div class="card-sector">{s['sector']}</div>
              <div class="card-score" style="color:{s['sig_color']}">{s['final_score']:.0f}<span style="font-size:13px;opacity:.5">/100</span></div>
              <div class="card-signal" style="color:{s['sig_color']}">{s['signal']}</div>
              <hr class="card-divider">
              <div class="card-detail">
                10d pred&nbsp;<span style="color:{pred_col}">{pred_ret:+.2f}%</span><br>
                RSI {s['rsi']:.1f} &middot; Sent <span style="color:{sent_col}">{sent:+.2f}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)


# ── Data tables ────────────────────────────────────────────────────────────────

def _sig_color(v: str) -> str:
    if "STRONG BUY" in str(v): return "background:#052e1a;color:#10b981"
    if "BUY"         in str(v): return "background:#0a2a0a;color:#34d399"
    if "HOLD"        in str(v): return "background:#1a1500;color:#f59e0b"
    return                              "background:#1a0505;color:#ef4444"

def _chg_color(v) -> str:
    try:
        return "color:#10b981" if float(str(v).replace("%","").replace("+","")) >= 0 else "color:#ff4560"
    except Exception:
        return ""


def render_movers_table(stocks: list[dict]) -> None:
    import pandas as pd
    df = pd.DataFrame(stocks)[[
        "symbol","sector","period_high","period_low",
        "first_close","last_close","change_pct","rsi","vol_ratio"
    ]].rename(columns={
        "symbol":"Symbol","sector":"Sector",
        "period_high":"Period High","period_low":"Period Low",
        "first_close":"First Close","last_close":"Last Close",
        "change_pct":"Change %","rsi":"RSI(14)","vol_ratio":"Vol Ratio",
    })
    styled = (
        df.style
        .applymap(_chg_color, subset=["Change %"])
        .format({
            "Period High":"₹{:,.0f}", "Period Low":"₹{:,.0f}",
            "First Close":"₹{:,.0f}", "Last Close":"₹{:,.0f}",
            "Change %":"{:+.2f}%",    "RSI(14)":"{:.1f}",
            "Vol Ratio":"{:.2f}x",
        })
    )
    st.dataframe(styled, use_container_width=True)


def render_predictions_table(stocks: list[dict]) -> None:
    import pandas as pd
    cols_needed = ["symbol","sector","final_score","signal","predicted_return",
                   "ml_score","sentiment","change_pct","rsi","macd_cross",
                   "bb_pos","period_high","period_low","last_close"]
    df_src = pd.DataFrame(stocks)
    # predicted_return may not exist in old data — fill with 0
    for c in cols_needed:
        if c not in df_src.columns:
            df_src[c] = 0.0
    df = df_src[cols_needed].rename(columns={
        "symbol":"Symbol","sector":"Sector","final_score":"Score",
        "signal":"Signal","predicted_return":"Pred 10d %",
        "ml_score":"ML Score","sentiment":"Sentiment",
        "change_pct":"Change %","rsi":"RSI","macd_cross":"MACD",
        "bb_pos":"BB Pos %","period_high":"High","period_low":"Low","last_close":"Last",
    })
    styled = (
        df.style
        .applymap(_sig_color,  subset=["Signal"])
        .applymap(_chg_color,  subset=["Change %"])
        .applymap(_chg_color,  subset=["Pred 10d %"])
        .format({
            "Score":"{:.1f}",       "ML Score":"{:.1f}",
            "Pred 10d %":"{:+.2f}%","Sentiment":"{:+.2f}",
            "Change %":"{:+.2f}%",  "RSI":"{:.1f}",
            "BB Pos %":"{:.1f}%",
            "High":"₹{:,.0f}",      "Low":"₹{:,.0f}", "Last":"₹{:,.0f}",
        })
    )
    st.dataframe(styled, use_container_width=True, height=500)


def render_all_stocks_table(data: list[dict]) -> None:
    import pandas as pd
    df = pd.DataFrame(sorted(data, key=lambda x: x["change_pct"], reverse=True))[[
        "symbol","sector","period_high","period_low","first_close","last_close",
        "change_pct","rsi","vol_ratio","volatility","final_score","signal"
    ]].rename(columns={
        "symbol":"Symbol","sector":"Sector",
        "period_high":"High","period_low":"Low",
        "first_close":"First","last_close":"Last",
        "change_pct":"Change %","rsi":"RSI",
        "vol_ratio":"Vol Ratio","volatility":"Volatility %",
        "final_score":"AI Score","signal":"Signal",
    })
    styled = (
        df.style
        .applymap(_sig_color,  subset=["Signal"])
        .applymap(_chg_color,  subset=["Change %"])
        .format({
            "High":"₹{:,.0f}","Low":"₹{:,.0f}",
            "First":"₹{:,.0f}","Last":"₹{:,.0f}",
            "Change %":"{:+.2f}%","RSI":"{:.1f}",
            "Vol Ratio":"{:.2f}x","Volatility %":"{:.2f}%",
            "AI Score":"{:.1f}",
        })
    )
    st.dataframe(styled, use_container_width=True, height=700)


# ── Empty state ────────────────────────────────────────────────────────────────

def render_empty_state() -> None:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-icon">📊</div>
      <div class="empty-title">Select a date range &amp; click Analyse</div>
      <div class="empty-sub">
        Use the <strong>Quick Preset</strong> above or set a custom
        <strong>From → To</strong> date range,<br>
        then click <strong>▶ Analyse</strong>
      </div>
    </div>
    """, unsafe_allow_html=True)
