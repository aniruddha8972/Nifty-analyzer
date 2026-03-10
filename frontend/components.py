"""
frontend/components.py
All reusable Streamlit HTML components.
"""

import streamlit as st


# ── App header ─────────────────────────────────────────────────────────────────

def render_header(label: str = "", index_name: str = "Nifty 50", stock_count: int = 50) -> None:
    from datetime import datetime
    import streamlit as _st

    now       = datetime.now()
    time_str  = now.strftime("%H:%M:%S")
    date_str  = now.strftime("%a, %d %b %Y")
    # Market hours: NSE 09:15–15:30 IST (we show live/closed based on hour)
    hour      = now.hour
    is_live   = 9 <= hour < 16
    mkt_label = "MARKET LIVE" if is_live else "MARKET CLOSED"
    mkt_color = "#00e5a0" if is_live else "#ff3d5a"
    mkt_bg    = "rgba(0,229,160,.08)" if is_live else "rgba(255,61,90,.08)"
    mkt_bdr   = "rgba(0,229,160,.25)" if is_live else "rgba(255,61,90,.25)"

    range_pill = ""
    if label:
        range_pill = f"""
        <div style="display:inline-flex;align-items:center;gap:6px;
                    background:rgba(76,142,255,.08);border:1px solid rgba(76,142,255,.2);
                    border-radius:6px;padding:4px 12px;
                    font-family:'IBM Plex Mono',monospace;font-size:9px;
                    letter-spacing:1.5px;text-transform:uppercase;color:#4c8eff">
          <span style="opacity:.6">RANGE</span>
          <span style="font-weight:600">{label}</span>
        </div>"""

    _st.markdown(f"""
    <style>
    @keyframes hdr-pulse {{
      0%,100% {{ opacity:1; }} 50% {{ opacity:.4; }}
    }}
    @keyframes hdr-slide {{
      from {{ opacity:0; transform:translateY(-8px); }}
      to   {{ opacity:1; transform:translateY(0); }}
    }}
    @keyframes shimmer-bar {{
      0%   {{ background-position: 200% center; }}
      100% {{ background-position:-200% center; }}
    }}
    .nse-header-wrap {{
      position:relative; overflow:hidden;
      background:linear-gradient(135deg,#06061a 0%,#080820 40%,#060616 100%);
      border:1px solid #1a1a3a; border-radius:14px;
      margin-bottom:22px; padding:0;
      box-shadow:0 8px 40px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.04);
      animation: hdr-slide .35s ease both;
    }}
    .nse-header-shimmer {{
      position:absolute; top:0; left:0; right:0; height:2px;
      background:linear-gradient(90deg,
        transparent 0%,#00e5a0 20%,#f0a500 40%,#4c8eff 60%,#00e5a0 80%,transparent 100%);
      background-size:200% auto;
      animation: shimmer-bar 4s linear infinite;
    }}
    .nse-header-grid {{
      display:grid;
      grid-template-columns:1fr auto;
      align-items:center;
      gap:16px;
      padding:18px 24px 16px;
    }}
    .nse-header-noise {{
      position:absolute;inset:0;pointer-events:none;opacity:.025;
      background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    }}
    .nse-wordmark {{
      font-family:'IBM Plex Mono',monospace;
      font-size:8px; letter-spacing:5px; text-transform:uppercase;
      color:#00e5a0; opacity:.75; margin-bottom:6px;
      display:flex; align-items:center; gap:10px;
    }}
    .nse-wordmark::before {{
      content:''; display:inline-block;
      width:18px; height:1px; background:#00e5a0; opacity:.5;
    }}
    .nse-title {{
      font-family:'IBM Plex Mono',monospace;
      font-size:clamp(20px,2.5vw,28px); font-weight:700;
      letter-spacing:-.5px; line-height:1.1;
      background:linear-gradient(135deg,#e8e9f5 0%,#9fa3c4 60%,#5a5e8a 100%);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent;
      background-clip:text;
    }}
    .nse-title em {{
      font-style:normal;
      background:linear-gradient(135deg,#00e5a0,#00b878);
      -webkit-background-clip:text; -webkit-text-fill-color:transparent;
      background-clip:text;
    }}
    .nse-meta {{
      display:flex; align-items:center; flex-wrap:wrap; gap:6px; margin-top:10px;
    }}
    .nse-pill {{
      display:inline-flex; align-items:center; gap:5px;
      padding:3px 10px; border-radius:5px;
      font-family:'IBM Plex Mono',monospace;
      font-size:9px; font-weight:500; letter-spacing:1px; text-transform:uppercase;
    }}
    .nse-pill-idx {{
      background:rgba(240,165,0,.08); border:1px solid rgba(240,165,0,.2); color:#f0a500;
    }}
    .nse-pill-ml {{
      background:rgba(76,142,255,.08); border:1px solid rgba(76,142,255,.2); color:#4c8eff;
    }}
    .nse-pill-snt {{
      background:rgba(0,229,160,.08); border:1px solid rgba(0,229,160,.2); color:#00e5a0;
    }}
    .nse-pill-cnt {{
      background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.08); color:#5a5e8a;
    }}
    .nse-right {{
      display:flex; flex-direction:column; align-items:flex-end; gap:8px;
    }}
    .nse-clock {{
      font-family:'IBM Plex Mono',monospace;
      font-size:22px; font-weight:700; color:#e8e9f5;
      letter-spacing:2px; line-height:1;
    }}
    .nse-date {{
      font-family:'IBM Plex Mono',monospace;
      font-size:9px; letter-spacing:2px; text-transform:uppercase;
      color:#3a3e6a;
    }}
    .nse-status {{
      display:inline-flex; align-items:center; gap:6px;
      padding:4px 12px; border-radius:6px;
      font-family:'IBM Plex Mono',monospace;
      font-size:9px; font-weight:700; letter-spacing:2px;
    }}
    .nse-dot {{
      width:6px; height:6px; border-radius:50%;
      animation: hdr-pulse 2s ease-in-out infinite;
    }}
    .nse-divider {{
      height:1px; background:linear-gradient(90deg,transparent,#1a1a3a 20%,#1a1a3a 80%,transparent);
      margin:0 24px;
    }}
    .nse-footer-bar {{
      display:flex; align-items:center; justify-content:space-between;
      padding:8px 24px 12px; flex-wrap:wrap; gap:8px;
    }}
    .nse-tag {{
      font-family:'IBM Plex Mono',monospace;
      font-size:8px; letter-spacing:2px; text-transform:uppercase; color:#2e315c;
    }}
    </style>

    <div class="nse-header-wrap">
      <div class="nse-header-noise"></div>
      <div class="nse-header-shimmer"></div>
      <div class="nse-header-grid">

        <!-- LEFT: Brand + meta -->
        <div>
          <div class="nse-wordmark">Quantitative Intelligence Platform</div>
          <div class="nse-title">NSE <em>Market</em> Analyzer</div>
          <div class="nse-meta">
            <span class="nse-pill nse-pill-idx">⬡ {index_name}</span>
            <span class="nse-pill nse-pill-cnt">{stock_count} Stocks</span>
            <span class="nse-pill nse-pill-ml">⚙ RF + GB + Ridge</span>
            <span class="nse-pill nse-pill-snt">◎ News Sentiment</span>
            {range_pill}
          </div>
        </div>

        <!-- RIGHT: Clock + status -->
        <div class="nse-right">
          <div class="nse-clock">{time_str} <span style="font-size:11px;color:#2e315c">IST</span></div>
          <div class="nse-date">{date_str}</div>
          <div class="nse-status"
               style="background:{mkt_bg};border:1px solid {mkt_bdr};color:{mkt_color}">
            <span class="nse-dot" style="background:{mkt_color}"></span>
            {mkt_label}
          </div>
        </div>

      </div>

      <div class="nse-divider"></div>
      <div class="nse-footer-bar">
        <span class="nse-tag">NSE · BSE · India Equity Markets</span>
        <span class="nse-tag">5yr historical · ML ensemble · real-time sentiment</span>
        <span class="nse-tag">⚠ Not financial advice</span>
      </div>
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
    """Render top 5 AI prediction cards with Google News sentiment."""
    cols = st.columns(5)
    for i, s in enumerate(stocks[:5]):
        with cols[i]:
            sent      = s.get("sentiment", 0.0)
            sent_col  = "#00e5a0" if sent >= 0 else "#ff4560"
            pred_ret  = s.get("predicted_return", 0.0)
            pred_col  = "#00e5a0" if pred_ret >= 0 else "#ff4560"
            n_art     = s.get("news_count",  0)
            conf      = s.get("sent_confidence", 0.0)
            latest_ts = s.get("news_latest", "")
            conf_col  = "#00e5a0" if conf >= 0.5 else "#f59e0b" if conf >= 0.2 else "#5a5a78"
            news_line = (
                f'<span style="color:{conf_col}">{n_art} articles</span>' +
                (f'<br><span style="font-size:9px;color:#3a3a52">{latest_ts}</span>' if latest_ts else "")
                if n_art > 0 else '<span style="color:#3a3a52">no recent news</span>'
            )
            st.markdown(f"""
            <div class="stock-card" style="--accent-color:{s['sig_color']}">
              <div class="card-symbol">{s['symbol']}</div>
              <div class="card-sector">{s['sector']}</div>
              <div class="card-score" style="color:{s['sig_color']}">{s['final_score']:.0f}<span style="font-size:13px;opacity:.5">/100</span></div>
              <div class="card-signal" style="color:{s['sig_color']}">{s['signal']}</div>
              <hr class="card-divider">
              <div class="card-detail">
                10d pred&nbsp;<span style="color:{pred_col}">{pred_ret:+.2f}%</span><br>
                RSI {s['rsi']:.1f} &middot; Sent <span style="color:{sent_col}">{sent:+.2f}</span><br>
                {news_line}
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
    st.dataframe(styled, width="stretch")


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
    st.dataframe(styled, width="stretch", height=500)


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
    st.dataframe(styled, width="stretch", height=700)


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
