"""
agents/bug_fixer.py  — Auto-patches known bugs and deprecated APIs.
Run:  python agents/bug_fixer.py
"""

import ast, re, sys
from pathlib import Path

ROOT  = Path(__file__).parent.parent
FIXES = []

def read(p):   return Path(p).read_text()
def write(p,t): Path(p).write_text(t)

def patch(path, old, new, desc):
    p = Path(path)
    src = p.read_text()
    if old in src:
        p.write_text(src.replace(old, new))
        FIXES.append((str(p.relative_to(ROOT)), desc))
        return True
    return False

def syntax_ok(path):
    try:
        ast.parse(Path(path).read_text())
        return True
    except SyntaxError as e:
        return (False, str(e))

# FIX 1: pandas applymap -> map
patch(ROOT / "frontend/portfolio_components.py",
      ".applymap(colour_pnl,", ".map(colour_pnl,",
      "pandas: .applymap -> .map (deprecated in 2.1)")
patch(ROOT / "frontend/portfolio_components.py",
      ".applymap(colour_advice,", ".map(colour_advice,",
      "pandas: .applymap -> .map second call")

# FIX 2: fetch_sentiment.clear() wrong function
patch(ROOT / "app.py",
      "fetch_sentiment.clear()", "fetch_sentiment_data.clear()",
      "app.py: fetch_sentiment is a plain wrapper, use fetch_sentiment_data.clear()")

# FIX 3: ensure fetch_sentiment_data imported
app = read(ROOT / "app.py")
if "fetch_sentiment_data" not in app:
    patch(ROOT / "app.py",
          "from backend.ml        import predict, fetch_sentiment\n",
          "from backend.ml        import predict, fetch_sentiment, fetch_sentiment_data\n",
          "app.py: add fetch_sentiment_data to imports")

# FIX 4: top-level pandas import in portfolio_components
pc = read(ROOT / "frontend/portfolio_components.py")
if pc.count("import pandas as pd") == 0:
    patch(ROOT / "frontend/portfolio_components.py",
          "import streamlit as st\nfrom backend.constants",
          "import streamlit as st\nimport pandas as pd\nfrom backend.constants",
          "portfolio_components.py: add top-level pandas import")

# FIX 5: remove duplicate inline pandas import if top-level exists
pc2 = read(ROOT / "frontend/portfolio_components.py")
if pc2.count("import pandas as pd") > 1:
    patch(ROOT / "frontend/portfolio_components.py",
          "    import pandas as pd\n\n    if not rows:",
          "    if not rows:",
          "portfolio_components.py: remove duplicate inline pandas import")

# FIX 6: guard empty username in auth.py
patch(ROOT / "backend/auth.py",
      'def _local_pf_path(username: str) -> Path:\n    return _PORTFOLIO_DIR / f"{username.lower()}.json"',
      'def _local_pf_path(username: str) -> Path:\n    safe = (username or "anonymous").lower()\n    return _PORTFOLIO_DIR / f"{safe}.json"',
      "auth.py: guard empty username in _local_pf_path")

# FIX 7: pin supabase version
patch(ROOT / "requirements.txt",
      "supabase>=2.3.0\n", "supabase>=2.3.0,<3.0.0\n",
      "requirements.txt: pin supabase <3.0.0")

# FIX 8: CORS security in streamlit config
cfg = ROOT / ".streamlit/config.toml"
if cfg.exists():
    txt = cfg.read_text()
    if "enableCORS" not in txt:
        cfg.write_text(txt + "\n[server]\nenableCORS = false\nenableXsrfProtection = true\n")
        FIXES.append((".streamlit/config.toml", "Add CORS/XSRF security settings"))

# FIX 9: yfinance column normalisation
patch(ROOT / "backend/data.py",
      "        if isinstance(df.columns, pd.MultiIndex):\n            df.columns = df.columns.get_level_values(0)\n        return df.dropna()",
      "        if isinstance(df.columns, pd.MultiIndex):\n            df.columns = df.columns.get_level_values(0)\n        df.columns = [str(c).strip() for c in df.columns]\n        return df.dropna()",
      "data.py: normalise column names after MultiIndex flatten")

# FIX 10: plotly in requirements
req = read(ROOT / "requirements.txt")
if "plotly" not in req:
    with open(ROOT / "requirements.txt", "a") as f:
        f.write("plotly>=5.18.0\n")
    FIXES.append(("requirements.txt", "Add plotly dependency"))

# REPORT
print("\n" + "="*62)
print("  BUG FIXER AGENT")
print("="*62)
if FIXES:
    print(f"\n  Applied {len(FIXES)} fix(es):\n")
    for f, d in FIXES:
        print(f"  [{f}]\n    -> {d}\n")
else:
    print("\n  No fixes needed.")

print("  Syntax check...")
ok = True
for fpath in sorted(ROOT.rglob("*.py")):
    if "__pycache__" in str(fpath) or "agents/" in str(fpath):
        continue
    r = syntax_ok(fpath)
    if r is True:
        print(f"    OK  {fpath.relative_to(ROOT)}")
    else:
        print(f"    ERR {fpath.relative_to(ROOT)} — {r[1]}")
        ok = False
print()
if ok:
    print("  All files pass.")
else:
    sys.exit(1)
