"""
pipeline/report.py
Generates a styled Excel workbook with 4 sheets:
  1. Top Gainers      — with News Headlines column
  2. Top Losers       — with News Headlines column
  3. AI Predictions   — with News Headlines column
  4. Summary Dashboard

News headlines are the actual RSS article titles that matched each stock symbol
during sentiment analysis — up to 5 per stock, pipe-separated in the cell.
"""

import io
from datetime import date

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter


# ── Style helpers ──────────────────────────────────────────────────────────────

def _fill(hex_color: str) -> PatternFill:
    return PatternFill("solid", fgColor=hex_color)

def _font(bold: bool = False, color: str = "f0f0f0", size: int = 11) -> Font:
    return Font(bold=bold, color=color, size=size, name="Calibri")

def _border() -> Border:
    s = Side(style="thin", color="1a1a1a")
    return Border(left=s, right=s, top=s, bottom=s)

def _ctr() -> Alignment:
    return Alignment(horizontal="center", vertical="center", wrap_text=True)

def _lft(wrap: bool = False) -> Alignment:
    return Alignment(horizontal="left", vertical="center", wrap_text=wrap)

def _header_row(ws, row: int, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill   = _fill("00e5a0")
        cell.font   = _font(True, "0D0D0D", 11)
        cell.border = _border()
        cell.alignment = _ctr()

def _data_row(ws, row: int, ncols: int, bg: str = "1a1a2e") -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row=row, column=c)
        cell.fill   = _fill(bg)
        cell.font   = _font()
        cell.border = _border()
        cell.alignment = _ctr()

def _title(ws, text: str, ncols: int, row: int = 1) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    cell = ws.cell(row=row, column=1, value=text)
    cell.fill      = _fill("0D0D0D")
    cell.font      = Font(bold=True, color="00e5a0", size=14, name="Calibri")
    cell.alignment = _ctr()
    ws.row_dimensions[row].height = 32

def _col_widths(ws, widths: list[int]) -> None:
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

def _format_news(headlines: list) -> str:
    """Format a list of headlines into a readable cell string."""
    if not headlines:
        return "—  No relevant news found"
    # Clean and number them
    lines = []
    for i, h in enumerate(headlines[:5], 1):
        h = h.strip()
        if h:
            lines.append(f"{i}. {h}")
    return "\n".join(lines) if lines else "—  No relevant news found"


# ── Sheet writers ──────────────────────────────────────────────────────────────

def _write_movers(ws, rows: list[dict], title: str, is_gain: bool) -> None:
    hdrs = [
        "#", "Symbol", "Sector",
        "Period High ₹", "Period Low ₹", "First Close ₹", "Last Close ₹",
        "Change %", "RSI(14)", "Vol Ratio", "Volatility %",
        "Sentiment Score", "News Headlines (used in sentiment analysis)",
    ]
    n = len(hdrs)

    _title(ws, title, n)
    ws.row_dimensions[2].height = 4
    for c, h in enumerate(hdrs, 1):
        ws.cell(row=3, column=c, value=h)
    _header_row(ws, 3, n)

    for i, s in enumerate(rows, 1):
        r   = i + 3
        chg = s["change_pct"]
        sent  = s.get("sentiment", 0.0)
        news  = _format_news(s.get("news_headlines", []))

        vals = [
            i, s["symbol"], s["sector"],
            s["period_high"], s["period_low"],
            s["first_close"], s["last_close"],
            f"{chg:+.2f}%",
            s["rsi"], s["vol_ratio"],
            f"{s['volatility']:.2f}%",
            f"{sent:+.2f}",
            news,
        ]

        bg = "052e1a" if is_gain else "2e0505"
        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.fill   = _fill(bg)
            cell.font   = _font()
            cell.border = _border()
            # News column: left-aligned with wrap; others centred
            if c == n:
                cell.alignment = _lft(wrap=True)
                cell.font = _font(color="c8c8d8", size=9)
            elif c == n - 1:
                # Sentiment score coloured
                col = "10b981" if sent >= 0 else "ff5472"
                cell.font = _font(True, col)
                cell.alignment = _ctr()
            else:
                cell.alignment = _ctr()

        ws.cell(row=r, column=8).font = _font(True, "10b981" if chg >= 0 else "ff5472")

        # Taller rows to show multiple headlines
        n_lines = news.count("\n") + 1
        ws.row_dimensions[r].height = max(20, min(n_lines * 16, 80))

    _col_widths(ws, [4, 14, 13, 14, 14, 14, 14, 11, 10, 11, 12, 13, 60])
    ws.sheet_view.showGridLines = False


def _write_predictions(ws, rows: list[dict]) -> None:
    hdrs = [
        "#", "Symbol", "Sector",
        "ML Score", "Sentiment Score", "Final Score", "Signal",
        "Pred 10d Return %",
        "Period High ₹", "Period Low ₹", "Last Close ₹",
        "Change %", "RSI", "MACD", "BB Pos %",
        "News Headlines (used in sentiment analysis)",
    ]
    n = len(hdrs)

    _title(ws, "🤖  AI Predictions — Buy Signals", n)
    ws.row_dimensions[2].height = 4
    for c, h in enumerate(hdrs, 1):
        ws.cell(row=3, column=c, value=h)
    _header_row(ws, 3, n)

    for i, s in enumerate(rows, 1):
        r   = i + 3
        sig = s.get("signal", "🟠 HOLD")
        sc  = s.get("final_score", 50)
        se  = s.get("sentiment", 0.0)
        pr  = s.get("predicted_return", 0.0)
        news = _format_news(s.get("news_headlines", []))

        if   "STRONG BUY" in sig: bg, fc = "052e1a", "10b981"
        elif "BUY"         in sig: bg, fc = "0a2a0a", "34d399"
        elif "HOLD"        in sig: bg, fc = "1a1500", "f59e0b"
        else:                      bg, fc = "1a0505", "ef4444"

        sent_col = "10b981" if se >= 0 else "ff5472"
        pred_col = "10b981" if pr >= 0 else "ff5472"

        sig_clean = (sig.replace("🟢","").replace("🟡","")
                        .replace("🟠","").replace("🔴","").strip())

        vals = [
            i, s["symbol"], s["sector"],
            s.get("ml_score", 50),
            f"{se:+.2f}",
            sc,
            sig_clean,
            f"{pr:+.2f}%",
            s["period_high"], s["period_low"], s["last_close"],
            f"{s['change_pct']:+.2f}%",
            s["rsi"],
            "Bullish" if s.get("macd_cross", 0) > 0 else "Bearish",
            f"{s.get('bb_pos', 50):.1f}%",
            news,
        ]

        for c, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=c, value=v)
            cell.fill   = _fill(bg)
            cell.font   = _font()
            cell.border = _border()
            cell.alignment = _ctr()

        # Coloured overrides
        ws.cell(row=r, column=5).font  = _font(True, sent_col)  # sentiment
        ws.cell(row=r, column=6).font  = _font(True, fc)         # final score
        ws.cell(row=r, column=7).font  = _font(True, fc)         # signal
        ws.cell(row=r, column=8).font  = _font(True, pred_col)   # pred return

        # News cell — last column, left-aligned small text
        news_cell = ws.cell(row=r, column=n)
        news_cell.alignment = _lft(wrap=True)
        news_cell.font      = _font(color="c8c8d8", size=9)

        n_lines = news.count("\n") + 1
        ws.row_dimensions[r].height = max(20, min(n_lines * 16, 80))

    _col_widths(ws, [4, 14, 13, 11, 13, 12, 15, 14, 14, 14, 13, 11, 10, 11, 12, 65])
    ws.sheet_view.showGridLines = False


def _write_summary(ws, all_stats: list[dict], from_d: date, to_d: date) -> None:
    _title(ws, "📊  Summary Dashboard", 4)
    ws.row_dimensions[2].height = 10

    changes = [s["change_pct"] for s in all_stats]
    tg = max(all_stats, key=lambda x: x["change_pct"])
    tl = min(all_stats, key=lambda x: x["change_pct"])

    # Training info
    n_rows   = all_stats[0].get("training_rows", 0) if all_stats else 0
    n_feats  = all_stats[0].get("n_features",    0) if all_stats else 0

    kv_rows = [
        ("Period",             f"{from_d.strftime('%d %b %Y')} → {to_d.strftime('%d %b %Y')}", "f0f0f0"),
        ("Stocks analysed",    len(all_stats),                                                   "f0f0f0"),
        ("Avg market return",  f"{sum(changes)/len(changes):+.2f}%",                             "f0f0f0"),
        ("Gainers",            sum(1 for c in changes if c > 0),                                 "10b981"),
        ("Losers",             sum(1 for c in changes if c < 0),                                 "ff5472"),
        ("Top Gainer",         f"{tg['symbol']}  {tg['change_pct']:+.2f}%",                     "10b981"),
        ("Top Loser",          f"{tl['symbol']}  {tl['change_pct']:+.2f}%",                     "ff5472"),
        ("STRONG BUY count",   sum(1 for s in all_stats if "STRONG BUY" in s.get("signal","")), "10b981"),
        ("BUY count",          sum(1 for s in all_stats if s.get("signal","").strip() == "🟡 BUY"), "34d399"),
        ("HOLD count",         sum(1 for s in all_stats if "HOLD" in s.get("signal","")),        "f59e0b"),
        ("AVOID count",        sum(1 for s in all_stats if "AVOID" in s.get("signal","")),       "ef4444"),
        ("",                   "",                                                                "333333"),
        ("ML Training rows",   f"{n_rows:,}" if n_rows else "N/A",                               "00e5a0"),
        ("ML Features",        f"{n_feats} (8 technical + 7 sentiment proxies + 2 mkt-relative)" if n_feats else "N/A", "00e5a0"),
        ("ML Target",          "Actual 10-day forward return",                                    "00e5a0"),
        ("Ensemble",           "RandomForest 40% + GradientBoosting 40% + Ridge 20%",            "00e5a0"),
    ]

    for i, (k, v, col) in enumerate(kv_rows, 3):
        for c, val in enumerate([k, v], 1):
            cell = ws.cell(row=i, column=c, value=val)
            cell.fill      = _fill("1a1a2e")
            cell.border    = _border()
            cell.alignment = _lft()
            cell.font      = _font(c == 1, "888888" if c == 1 else col)
        ws.row_dimensions[i].height = 22

    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 55

    r = len(kv_rows) + 5
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
    cell = ws.cell(row=r, column=1,
                   value="⚠  For educational purposes only. "
                         "Not financial advice. Consult a SEBI-registered advisor.")
    cell.font      = Font(italic=True, color="f59e0b", size=9, name="Calibri")
    cell.fill      = _fill("1a1a2e")
    cell.alignment = _lft()
    ws.sheet_view.showGridLines = False


# ── Public entry point ─────────────────────────────────────────────────────────

def generate(
    all_stats:   list[dict],
    gainers:     list[dict],
    losers:      list[dict],
    predictions: list[dict],
    from_d:      date,
    to_d:        date,
) -> bytes:
    """Build and return the full Excel workbook as bytes."""
    wb    = openpyxl.Workbook()
    label = f"{from_d.strftime('%d %b %Y')} → {to_d.strftime('%d %b %Y')}"

    ws1 = wb.active
    ws1.title = "Top Gainers"
    ws1.sheet_properties.tabColor = "10b981"
    _write_movers(ws1, gainers, f"📈  Top Gainers  ·  {label}", True)

    ws2 = wb.create_sheet("Top Losers")
    ws2.sheet_properties.tabColor = "ef4444"
    _write_movers(ws2, losers, f"📉  Top Losers  ·  {label}", False)

    ws3 = wb.create_sheet("AI Predictions")
    ws3.sheet_properties.tabColor = "00e5a0"
    _write_predictions(ws3, predictions)

    ws4 = wb.create_sheet("Summary")
    ws4.sheet_properties.tabColor = "f59e0b"
    _write_summary(ws4, all_stats, from_d, to_d)

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
