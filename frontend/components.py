"""
frontend/components.py
All reusable Streamlit HTML components.
"""

import streamlit as st


# ── App header ─────────────────────────────────────────────────────────────────

def render_header(label: str = "", index_name: str = "Nifty 50",
                  stock_count: int = 50, user: dict | None = None,
                  on_logout=None) -> None:
    from datetime import datetime
    import streamlit as _st

    now      = datetime.now()
    time_str = now.strftime("%H:%M:%S")
    date_str = now.strftime("%a, %d %b %Y")
    is_live  = 9 <= now.hour < 16
    mkt_txt  = "MARKET LIVE" if is_live else "MARKET CLOSED"
    mkt_c    = "#00e5a0"             if is_live else "#ff3d5a"
    mkt_bg   = "rgba(0,229,160,.07)" if is_live else "rgba(255,61,90,.07)"
    mkt_bdr  = "rgba(0,229,160,.22)" if is_live else "rgba(255,61,90,.22)"

    name     = (user or {}).get("name", "")
    username = (user or {}).get("username", "")
    initials = "".join(w[0].upper() for w in name.split()[:2]) if name else "?"

    # ── Step 1: inject CSS separately (no f-string, always works) ──
    _st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@300;400;500;600&display=swap');
@keyframes nse-pulse{0%,100%{opacity:1}50%{opacity:.3}}
@keyframes nse-enter{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:none}}
@keyframes nse-shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
.nse-hdr-wrap{position:relative;overflow:hidden;
  background:linear-gradient(160deg,#070718 0%,#09091f 40%,#070715 100%);
  border:1px solid rgba(255,255,255,.06);border-radius:16px;margin-bottom:20px;
  box-shadow:0 0 0 1px rgba(0,229,160,.04),0 12px 48px rgba(0,0,0,.6),inset 0 1px 0 rgba(255,255,255,.05);
  animation:nse-enter .35s cubic-bezier(.22,1,.36,1) both}
.nse-hdr-glow{pointer-events:none;position:absolute;
  top:-80px;left:-60px;width:320px;height:220px;
  background:radial-gradient(ellipse,rgba(0,229,160,.06) 0%,transparent 70%)}
.nse-hdr-shimmer{position:absolute;top:0;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,#00e5a0 20%,#4c8eff 50%,#f0a500 70%,#00e5a0 90%,transparent);
  background-size:200% auto;animation:nse-shimmer 5s linear infinite}
.nse-hdr-body{position:relative;z-index:1;
  display:grid;grid-template-columns:1fr auto;align-items:center;gap:16px;padding:18px 24px 14px}
.nse-wordmark{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:4px;
  text-transform:uppercase;color:#00e5a0;opacity:.55;margin-bottom:7px;
  display:flex;align-items:center;gap:10px}
.nse-wordmark::before{content:'';display:inline-block;width:20px;height:1px;background:currentColor;opacity:.8}
.nse-title{font-family:'IBM Plex Mono',monospace;
  font-size:clamp(18px,2.4vw,28px);font-weight:700;letter-spacing:-.4px;line-height:1;
  background:linear-gradient(135deg,#d8daf5 0%,#8890c0 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:10px}
.nse-title em{font-style:normal;
  background:linear-gradient(130deg,#00e5a0 20%,#00c882 100%);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}
.nse-pills{display:flex;flex-wrap:wrap;gap:5px}
.nse-pill{display:inline-flex;align-items:center;gap:4px;padding:3px 10px;border-radius:5px;
  font-family:'IBM Plex Mono',monospace;font-size:9px;font-weight:500;letter-spacing:1px;text-transform:uppercase}
.nse-right-panel{display:flex;align-items:center;gap:16px}
.nse-clock-block{text-align:right}
.nse-clock{font-family:'IBM Plex Mono',monospace;font-size:22px;font-weight:700;
  color:#dde0f5;letter-spacing:3px;line-height:1}
.nse-clock-tz{font-size:9px;color:#2a2d52;font-weight:400;letter-spacing:2px}
.nse-clock-date{font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:2px;
  text-transform:uppercase;color:#2e315c;margin-top:3px}
.nse-mkt-status{display:inline-flex;align-items:center;gap:5px;padding:4px 11px;
  border-radius:5px;margin-top:6px;font-family:'IBM Plex Mono',monospace;font-size:9px;
  font-weight:700;letter-spacing:2px;text-transform:uppercase}
.nse-dot{width:6px;height:6px;border-radius:50%;animation:nse-pulse 2s infinite}
.nse-divider{height:1px;margin:0 24px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.04) 20%,rgba(255,255,255,.04) 80%,transparent)}
.nse-footer{display:flex;align-items:center;justify-content:space-between;
  flex-wrap:wrap;gap:6px;padding:7px 24px 10px}
.nse-tag{font-family:'IBM Plex Mono',monospace;font-size:8px;letter-spacing:1.5px;
  text-transform:uppercase;color:#1a1d38}
.nse-user{display:flex;align-items:center;gap:10px;
  border-left:1px solid rgba(255,255,255,.05);padding-left:16px}
.nse-avatar{width:36px;height:36px;border-radius:50%;flex-shrink:0;
  background:linear-gradient(135deg,#00e5a0,#00b878);
  display:flex;align-items:center;justify-content:center;
  font-family:'IBM Plex Mono',monospace;font-size:13px;font-weight:700;color:#04040c;
  box-shadow:0 0 0 2px rgba(0,229,160,.2)}
.nse-user-name{font-family:'IBM Plex Mono',monospace;font-size:11px;
  font-weight:700;color:#e8e9f5;white-space:nowrap}
.nse-user-handle{font-family:'IBM Plex Mono',monospace;font-size:9px;color:#2e315c;margin-top:2px}
@media(max-width:640px){
  .nse-hdr-body{grid-template-columns:1fr;gap:10px}
  .nse-right-panel{justify-content:space-between}
  .nse-clock{font-size:18px}}
</style>""", unsafe_allow_html=True)

    # ── Step 2: build dynamic HTML as a plain string (no f-string CSS inside) ──
    range_pill = (
        f'<span class="nse-pill" style="background:rgba(76,142,255,.08);'
        f'border:1px solid rgba(76,142,255,.22);color:#4c8eff">📅 {label}</span>'
    ) if label else ""

    user_html = (
        f'<div class="nse-user">'
        f'  <div class="nse-avatar">{initials}</div>'
        f'  <div class="nse-user-info">'
        f'    <div class="nse-user-name">{name}</div>'
        f'    <div class="nse-user-handle">@{username}</div>'
        f'  </div>'
        f'</div>'
    ) if name else ""

    html = (
        '<div class="nse-hdr-wrap">'
        '  <div class="nse-hdr-glow"></div>'
        '  <div class="nse-hdr-shimmer"></div>'
        '  <div class="nse-hdr-body">'
        '    <div>'
        '      <div class="nse-wordmark">Quantitative Intelligence Platform</div>'
        f'     <div class="nse-title">NSE <em>Market</em> Analyzer</div>'
        '      <div class="nse-pills">'
        f'       <span class="nse-pill" style="background:rgba(240,165,0,.07);border:1px solid rgba(240,165,0,.2);color:#f0a500">⬡ {index_name}</span>'
        f'       <span class="nse-pill" style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);color:#3a3e6a">{stock_count} stocks</span>'
        '        <span class="nse-pill" style="background:rgba(76,142,255,.07);border:1px solid rgba(76,142,255,.2);color:#4c8eff">⚙ RF · GB · Ridge</span>'
        '        <span class="nse-pill" style="background:rgba(0,229,160,.07);border:1px solid rgba(0,229,160,.18);color:#00e5a0">◎ News Sentiment</span>'
        f'       {range_pill}'
        '      </div>'
        '    </div>'
        '    <div class="nse-right-panel">'
        '      <div class="nse-clock-block">'
        f'       <div class="nse-clock">{time_str} <span class="nse-clock-tz">IST</span></div>'
        f'       <div class="nse-clock-date">{date_str}</div>'
        f'       <div class="nse-mkt-status" style="background:{mkt_bg};border:1px solid {mkt_bdr};color:{mkt_c}">'
        f'         <span class="nse-dot" style="background:{mkt_c}"></span>{mkt_txt}'
        '        </div>'
        '      </div>'
        f'     {user_html}'
        '    </div>'
        '  </div>'
        '  <div class="nse-divider"></div>'
        '  <div class="nse-footer">'
        '    <span class="nse-tag">NSE &middot; BSE &middot; India Equity Markets</span>'
        '    <span class="nse-tag">5yr history &middot; ML ensemble &middot; live sentiment</span>'
        '    <span class="nse-tag">&#9888; not financial advice</span>'
        '  </div>'
        '</div>'
    )
    _st.markdown(html, unsafe_allow_html=True)




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
