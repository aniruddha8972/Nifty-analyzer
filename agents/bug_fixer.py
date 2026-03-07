"""
agents/bug_fixer.py
────────────────────
Bug Fixer Agent — scans source files for known issues and fixes them.
Run:  python agents/bug_fixer.py
"""

import ast, re, sys
from pathlib import Path

ROOT  = Path(__file__).parent.parent
FIXES = []

def read(p):   return Path(p).read_text()
def write(p, t): Path(p).write_text(t)

def patch(path, old, new, desc):
    p = Path(path)
    src = p.read_text()
    if old in src:
        p.write_text(src.replace(old, new))
        FIXES.append((str(p.relative_to(ROOT)), desc))
        return True
    return False

def re_patch(path, pattern, replacement, desc, flags=0):
    p = Path(path)
    src = p.read_text()
    new_src, n = re.subn(pattern, replacement, src, flags=flags)
    if n:
        p.write_text(new_src)
        FIXES.append((str(p.relative_to(ROOT)), desc))
    return n > 0

def syntax_ok(path):
    try:
        ast.parse(Path(path).read_text())
        return True
    except SyntaxError as e:
        return (False, str(e))

# ── FIX 1: pandas applymap -> map ─────────────────────────────────────────────
patch(ROOT / "frontend/portfolio_components.py",
      ".applymap(colour_pnl,",
      ".map(colour_pnl,",
      "pandas: .applymap -> .map (deprecated in pandas 2.1)")
patch(ROOT / "frontend/portfolio_components.py",
      ".applymap(colour_advice,",
      ".map(colour_advice,",
      "pandas: .applymap -> .map second call")

# ── FIX 2: use_container_width -> width in st.dataframe ───────────────────────
for fpath in ROOT.rglob("*.py"):
    if "__pycache__" in str(fpath):
        continue
    src = fpath.read_text()
    if "st.dataframe" in src and "width="stretch"" in src:
        new_src = src.replace("width="stretch"", 'width="stretch"')
        fpath.write_text(new_src)
        FIXES.append((str(fpath.relative_to(ROOT)),
                      "st.dataframe: use_container_width -> width=stretch"))
# ── FIX 3: fetch_sentiment.clear() on non-cached wrapper ──────────────────────
patch(ROOT / "app.py",
      "fetch_sentiment.clear()",
      "fetch_sentiment_data.clear()",
      "app.py: fetch_sentiment is not @cached — use fetch_sentiment_data.clear()")

# ── FIX 4: ensure fetch_sentiment_data imported in app.py ─────────────────────
app = read(ROOT / "app.py")
if "fetch_sentiment_data" not in app:
    patch(ROOT / "app.py",
          "from backend.ml        import predict, fetch_sentiment\n",
          "from backend.ml        import predict, fetch_sentiment, fetch_sentiment_data\n",
          "app.py: add fetch_sentiment_data to imports")

# ── FIX 5: top-level pandas import in portfolio_components.py ─────────────────
pc = read(ROOT / "frontend/portfolio_components.py")
if "import pandas as pd" not in pc:
    patch(ROOT / "frontend/portfolio_components.py",
          "import streamlit as st\nfrom backend.constants",
          "import streamlit as st\nimport pandas as pd\nfrom backend.constants",
          "portfolio_components.py: add top-level pandas import")
# Remove duplicate inline import
pc2 = read(ROOT / "frontend/portfolio_components.py")
if pc2.count("import pandas as pd") > 1:
    patch(ROOT / "frontend/portfolio_components.py",
          "    import pandas as pd\n\n    if not rows:",
          "    if not rows:",
          "portfolio_components.py: remove duplicate inline pandas import")

# ── FIX 6: unused day_val variable in portfolio.py ────────────────────────────
patch(ROOT / "backend/portfolio.py",
      "        day_val     = price * qty   # same as current_val when price is latest\n\n        rows.append",
      "        rows.append",
      "portfolio.py: remove unused day_val variable")

# ── FIX 7: guard empty username in auth.py local path ─────────────────────────
patch(ROOT / "backend/auth.py",
      'def _local_pf_path(username: str) -> Path:\n    return _PORTFOLIO_DIR / f"{username.lower()}.json"',
      'def _local_pf_path(username: str) -> Path:\n    safe = (username or "anonymous").lower()\n    return _PORTFOLIO_DIR / f"{safe}.json"',
      "auth.py: guard empty username in _local_pf_path")

# ── FIX 8: requirements.txt — pin supabase major version ──────────────────────
patch(ROOT / "requirements.txt",
      "supabase>=2.3.0\n",
      "supabase>=2.3.0,<3.0.0\n",
      "requirements.txt: pin supabase <3.0.0 to avoid breaking changes")

# ── FIX 9: CORS + XSRF in streamlit config ────────────────────────────────────
cfg_path = ROOT / ".streamlit/config.toml"
if cfg_path.exists():
    cfg = cfg_path.read_text()
    if "enableCORS" not in cfg:
        cfg_path.write_text(cfg + "\n[server]\nenableCORS = false\nenableXsrfProtection = true\n")
        FIXES.append((".streamlit/config.toml", "Add CORS/XSRF security settings"))

# ── FIX 10: normalise yfinance column names after MultiIndex flatten ───────────
patch(ROOT / "backend/data.py",
      "        if isinstance(df.columns, pd.MultiIndex):\n            df.columns = df.columns.get_level_values(0)\n        return df.dropna()",
      "        if isinstance(df.columns, pd.MultiIndex):\n            df.columns = df.columns.get_level_values(0)\n        df.columns = [str(c).strip() for c in df.columns]\n        return df.dropna()",
      "data.py: normalise column names after MultiIndex flatten")

# ── FIX 11: refresh in app.py must not clear portfolio/auth ───────────────────
app2 = read(ROOT / "app.py")
if "st.session_state.clear()" in app2:
    patch(ROOT / "app.py",
          "st.session_state.clear()\n    st.rerun()",
          "for k in ['data','from_d','to_d']:\n        st.session_state.pop(k, None)\n    st.rerun()",
          "app.py: refresh clears auth — fix to only clear market data keys")

# ── REPORT ────────────────────────────────────────────────────────────────────
print("\n" + "="*62)
print("  BUG FIXER AGENT — RESULTS")
print("="*62)
if FIXES:
    print(f"\n  Applied {len(FIXES)} fix(es):\n")
    for f, desc in FIXES:
        print(f"  [{f}]\n    -> {desc}\n")
else:
    print("\n  No fixes needed — codebase already clean.")

print("  Syntax checking all Python files...")
all_ok = True
for fpath in sorted(ROOT.rglob("*.py")):
    if "__pycache__" in str(fpath) or "agents/" in str(fpath):
        continue
    result = syntax_ok(fpath)
    if result is True:
        print(f"    OK  {fpath.relative_to(ROOT)}")
    else:
        print(f"    ERR {fpath.relative_to(ROOT)} — {result[1]}")
        all_ok = False

print()
if all_ok:
    print("  All files pass syntax check.")
else:
    print("  Syntax errors found — see above.")
    sys.exit(1)
