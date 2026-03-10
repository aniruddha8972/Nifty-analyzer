"""
frontend/design.py — re-exports styles + helpers.
All CSS lives in styles.py for test compatibility.
"""
from frontend.styles import CSS, inject  # noqa
import streamlit as st

# Aliases
FINANCE_CSS = CSS


def page_hero(eye: str, title: str, sub: str = "") -> None:
    sub_h = f'<div class="page-sub">{sub}</div>' if sub else ""
    st.markdown(f"""
    <div class="page-hero">
      <div class="page-eye">{eye}</div>
      <div class="page-h1">{title}</div>
      {sub_h}
    </div>""", unsafe_allow_html=True)


def section(title: str, badge: str = "") -> None:
    b = f'<span class="sec-badge">{badge}</span>' if badge else ""
    st.markdown(f"""
    <div class="sec-wrap">
      <div class="sec-line"></div>
      <div class="sec-title">{title}</div>
      {b}
      <div class="sec-line"></div>
    </div>""", unsafe_allow_html=True)


def kpi_row(cards: list) -> None:
    acc = {"green":"var(--green)","amber":"var(--amber)","red":"var(--red)","blue":"var(--blue)"}
    cols = st.columns(len(cards))
    for col, c in zip(cols, cards):
        a  = acc.get(c.get("accent","green"), "var(--green)")
        vc = c.get("val_color", "var(--fg)")
        s  = f'<div class="stat-sub">{c["sub"]}</div>' if c.get("sub") else ""
        col.markdown(f"""
        <div class="stat-item" style="--stat-accent:{a}">
          <div class="stat-label">{c['label']}</div>
          <div class="stat-value" style="color:{vc}">{c['value']}</div>
          {s}
        </div>""", unsafe_allow_html=True)


def sig_class(sig: str) -> str:
    if "STRONG BUY" in sig: return "sig-sb"
    if "BUY"        in sig: return "sig-b"
    if "HOLD"       in sig: return "sig-h"
    return "sig-a"


def chg_color(v) -> str:
    try: return "var(--green)" if float(v) >= 0 else "var(--red)"
    except: return "var(--fg3)"


# Backward-compat aliases
render_page_hero  = page_hero
render_section    = section
render_stat_cards = kpi_row
