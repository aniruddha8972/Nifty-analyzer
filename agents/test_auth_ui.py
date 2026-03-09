"""
agents/test_auth_ui.py — Auth page HTML/CSS rendering tests
Tests that the auth page HTML is valid, self-contained, and won't
leak raw HTML tags into the browser.
"""
import ast, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PASS = []; FAIL = []

def test(name, fn):
    try:
        fn()
        PASS.append(name)
        print(f"  ✅ {name}")
    except AssertionError as e:
        FAIL.append((name, str(e)))
        print(f"  ❌ {name}\n     {e}")

def expect(cond, msg=""):
    if not cond: raise AssertionError(msg)

# ── Load source ───────────────────────────────────────────────────────────────
src = (ROOT / "frontend/auth_page.py").read_text()

# ── Parse all st.markdown calls and extract their HTML string args ────────────
def extract_markdown_strings(source: str) -> list[str]:
    """
    Extract the literal string argument from every st.markdown(...) call.
    Returns list of HTML strings (only those with unsafe_allow_html=True).
    """
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call): continue
        # Match st.markdown(...)
        func = node.func
        is_markdown = (
            (isinstance(func, ast.Attribute) and func.attr == "markdown") or
            (isinstance(func, ast.Name) and func.id == "markdown")
        )
        if not is_markdown: continue
        # Check unsafe_allow_html=True keyword
        unsafe = any(
            (kw.arg == "unsafe_allow_html" and isinstance(kw.value, ast.Constant) and kw.value.value is True)
            for kw in node.keywords
        )
        if not unsafe: continue
        # Extract the string argument (first positional)
        if not node.args: continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            results.append(arg.value)
        elif isinstance(arg, ast.JoinedStr):
            # f-string — reconstruct with placeholder text for tag analysis
            parts = []
            for v in arg.values:
                if isinstance(v, ast.Constant): parts.append(v.value)
                else: parts.append("PLACEHOLDER")
            results.append("".join(parts))
    return results

html_blocks = extract_markdown_strings(src)

def count_tags(html: str):
    """Count opening and closing tags (ignoring self-closing)."""
    opens  = re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)[^>]*(?<!/)>', html)
    closes = re.findall(r'</([a-zA-Z][a-zA-Z0-9]*)>', html)
    # Remove self-closing tags from opens
    self_closing = {'br','hr','img','input','meta','link','canvas','col','area','base','embed','source','track','wbr'}
    opens_filtered = [t.lower() for t in opens if t.lower() not in self_closing]
    return opens_filtered, [t.lower() for t in closes]

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_syntax():
    ast.parse(src)  # raises SyntaxError if bad

def test_imports_request_password_reset():
    expect("request_password_reset" in src, "Must import request_password_reset from backend.auth")

def test_no_unclosed_divs_per_block():
    """Every individual st.markdown block must have balanced div tags."""
    problems = []
    for i, block in enumerate(html_blocks):
        opens, closes = count_tags(block)
        div_opens  = opens.count("div")
        div_closes = closes.count("div")
        if div_opens != div_closes:
            # Show first 80 chars of the block for diagnosis
            preview = block.strip()[:80].replace('\n',' ')
            problems.append(f"Block {i}: {div_opens} <div> opens vs {div_closes} </div> closes — '{preview}'")
    expect(not problems, "Unbalanced divs:\n  " + "\n  ".join(problems))

def test_no_unclosed_spans():
    """Spans must be balanced per block."""
    problems = []
    for i, block in enumerate(html_blocks):
        opens, closes = count_tags(block)
        if opens.count("span") != closes.count("span"):
            preview = block.strip()[:80].replace('\n',' ')
            problems.append(f"Block {i}: span mismatch — '{preview}'")
    expect(not problems, "\n  ".join(problems))

def test_no_unclosed_buttons():
    """Button tags must be balanced."""
    problems = []
    for i, block in enumerate(html_blocks):
        opens, closes = count_tags(block)
        if opens.count("button") != closes.count("button"):
            preview = block.strip()[:80].replace('\n',' ')
            problems.append(f"Block {i}: button mismatch — '{preview}'")
    expect(not problems, "\n  ".join(problems))

def test_no_stray_closing_tags():
    """No block should start with a closing tag (orphaned </div> etc)."""
    problems = []
    for i, block in enumerate(html_blocks):
        stripped = block.strip()
        if re.match(r'^</', stripped):
            problems.append(f"Block {i} starts with closing tag: '{stripped[:60]}'")
    expect(not problems, "\n  ".join(problems))

def test_no_naked_opening_tags_without_close():
    """
    Blocks that open a major structural tag must also close it.
    Specifically: a block opening <div class="nse-page"> must also close it.
    """
    for i, block in enumerate(html_blocks):
        if 'class="nse-page"' in block or "class='nse-page'" in block:
            # This block opens the outer shell — must close itself
            opens, closes = count_tags(block)
            expect(
                opens.count("div") == closes.count("div"),
                f"Block {i} opens nse-page but has {opens.count('div')} opens vs {closes.count('div')} closes"
            )

def test_card_html_is_self_contained():
    """The main card HTML block must be fully self-contained (no unclosed tags of any kind)."""
    card_blocks = [b for b in html_blocks if 'nse-card' in b or 'nse-page' in b or 'nse-tabs' in b]
    for i, block in enumerate(card_blocks):
        opens, closes = count_tags(block)
        all_open  = sorted(opens)
        all_close = sorted(closes)
        expect(
            all_open == all_close,
            f"Card block has unbalanced tags.\n  Opens:  {all_open}\n  Closes: {all_close}\n  Preview: {block[:100]}"
        )

def test_no_widget_inside_html_open_block():
    """
    A st.markdown block that opens a div (more opens than closes) must NOT
    be immediately followed by Streamlit widget calls — this is the root
    cause of the raw HTML display bug.
    """
    # Find markdown calls that leave unclosed divs, then check next line
    lines = src.split('\n')
    problems = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # Find st.markdown calls that span single line and have more < than >
        if 'st.markdown(' in line and 'unsafe_allow_html=True' in line:
            # Check if this opens more tags than it closes
            opens, closes = count_tags(line)
            if opens.count("div") > closes.count("div"):
                # Check if next non-empty non-markdown line is a widget
                j = i+1
                while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                    j += 1
                if j < len(lines):
                    next_line = lines[j].strip()
                    widget_calls = ['st.text_input', 'st.button', 'st.selectbox', 'st.columns', 'st.spinner']
                    if any(w in next_line for w in widget_calls):
                        problems.append(f"Line {i+1}: unclosed markdown div followed by widget at line {j+1}: {next_line[:60]}")
        i += 1
    expect(not problems, "HTML div left open before widget:\n  " + "\n  ".join(problems))

def test_render_auth_page_defined():
    expect("def render_auth_page" in src)

def test_three_panels_defined():
    for fn in ["_render_login", "_render_register", "_render_forgot"]:
        expect(f"def {fn}" in src, f"{fn} not defined")

def test_forgot_password_flow():
    expect("request_password_reset" in src, "Must call request_password_reset")
    expect("reset_sent" in src, "Must track reset_sent state")
    expect("nse-ok" in src or "auth-success" in src or "success" in src.lower(), "Must show success state after send")

def test_tab_switching_no_hidden_visibility():
    """Tabs must NOT use visibility:hidden to hide real buttons — causes layout gaps."""
    expect("visibility:hidden" not in src, "Must not use visibility:hidden for tab buttons")

def test_particle_canvas_present():
    expect("canvas" in src.lower(), "Must have particle canvas")
    expect("requestAnimationFrame" in src, "Canvas must animate")

def test_responsive_media_queries():
    expect("@media" in src, "Must have responsive @media queries")
    expect("max-width" in src, "Must have max-width breakpoints")

def test_mobile_column_stacking():
    expect("flex-direction:column" in src or "flex-direction: column" in src,
           "Mobile: columns must stack on small screens")

def test_no_raw_html_in_card_body_st_markdown():
    """
    The nse-card-body / nse-inner section must be a fully self-contained
    HTML block — all tags opened must be closed in the SAME st.markdown call.
    """
    for block in html_blocks:
        if "nse-card-body" in block or "nse-inner" in block:
            opens, closes = count_tags(block)
            expect(
                sorted(opens) == sorted(closes),
                f"nse-card-body block is not self-contained:\n  Opens: {sorted(opens)}\n  Closes: {sorted(closes)}"
            )


def test_uses_components_html():
    """Shell must use components.v1.html — the only reliable way to render HTML on Streamlit Cloud."""
    expect("components.html" in src, "Must use st.components.v1.html() for the card shell")
    expect("import streamlit.components.v1" in src or "components.v1" in src,
           "Must import streamlit.components.v1")

def test_no_markdown_with_open_divs_before_widgets():
    """After the fix, no st.markdown block should open a div that's left unclosed."""
    problems = []
    lines = src.split('\n')
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Only single-line markdown calls
        if 'st.markdown(' in stripped and 'unsafe_allow_html=True' in stripped:
            opens, closes = count_tags(stripped)
            if opens.count("div") > closes.count("div"):
                j = i + 1
                while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                    j += 1
                if j < len(lines):
                    next_ln = lines[j].strip()
                    widgets = ['st.text_input','st.button','st.selectbox','st.columns','st.spinner']
                    if any(w in next_ln for w in widgets):
                        problems.append(f"Line {i+1}: unclosed div before widget at line {j+1}")
    expect(not problems, "Open div before widget:\n  " + "\n  ".join(problems))

def test_reset_has_redirect_to():
    auth_src = (ROOT / "backend/auth.py").read_text()
    expect("redirect_to" in auth_src, "reset_password_email must pass redirect_to param")
    expect("app" in auth_src and "url" in auth_src,
           "Must read app URL from st.secrets['app']['url']")

def test_shell_html_self_contained():
    """_shell_html() must return complete HTML5 document."""
    expect("def _shell_html" in src, "_shell_html function must exist")
    expect("<!DOCTYPE html>" in src, "Shell must be a full HTML document")
    expect("</html>" in src, "Shell must close </html>")

def test_switchers_no_html_wrappers():
    """Switcher buttons must NOT be wrapped in st.markdown div blocks."""
    lines = src.split('\n')
    in_switchers = False
    open_div_before_button = False
    for i, line in enumerate(lines):
        if 'def _switchers' in line:
            in_switchers = True
        if in_switchers and 'def _render' in line:
            break
        if in_switchers:
            stripped = line.strip()
            if 'st.markdown' in stripped and '<div' in stripped and 'unsafe_allow_html=True' in stripped:
                open_div_before_button = True
    expect(not open_div_before_button,
           "_switchers() must not wrap st.button calls in st.markdown div blocks")

test("ARCH     — uses components.v1.html for shell",             test_uses_components_html)
test("HTML     — no open div before widget (post-fix verify)",   test_no_markdown_with_open_divs_before_widgets)
test("AUTH     — reset email passes redirect_to param",          test_reset_has_redirect_to)
test("AUTH     — shell_html returns full HTML document",         test_shell_html_self_contained)
test("HTML     — switcher buttons have no div wrappers",         test_switchers_no_html_wrappers)


# ── Register tests ────────────────────────────────────────────────────────────
test("SYNTAX   — auth_page.py parses cleanly",                  test_syntax)
test("IMPORT   — request_password_reset imported",              test_imports_request_password_reset)
test("HTML     — no unclosed <div> tags per markdown block",    test_no_unclosed_divs_per_block)
test("HTML     — no unclosed <span> tags per block",            test_no_unclosed_spans)
test("HTML     — no unclosed <button> tags per block",          test_no_unclosed_buttons)
test("HTML     — no orphaned closing tags at block start",      test_no_stray_closing_tags)
test("HTML     — nse-page shell is self-contained",             test_no_naked_opening_tags_without_close)
test("HTML     — card HTML block is fully self-contained",      test_card_html_is_self_contained)
test("HTML     — no widget after unclosed div (root cause fix)",test_no_widget_inside_html_open_block)
test("HTML     — nse-card-body block self-contained",           test_no_raw_html_in_card_body_st_markdown)
test("FUNC     — render_auth_page() defined",                   test_render_auth_page_defined)
test("FUNC     — all 3 panels defined",                         test_three_panels_defined)
test("FUNC     — forgot password flow present",                 test_forgot_password_flow)
test("DESIGN   — no visibility:hidden tab hack",                test_tab_switching_no_hidden_visibility)
test("DESIGN   — particle canvas present",                      test_particle_canvas_present)
test("DESIGN   — responsive @media queries",                    test_responsive_media_queries)
test("DESIGN   — mobile column stacking CSS",                   test_mobile_column_stacking)

# ── Report ────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
if FAIL:
    print(f"  ❌ FAILURES FOUND")
    print(f"  {len(PASS)}/{len(PASS)+len(FAIL)} passed · {len(FAIL)} failed")
    for name, err in FAIL:
        print(f"\n  FAILED: {name}")
        print(f"  {err}")
    print('='*60)
    sys.exit(1)
else:
    print(f"  ✅ ALL PASS")
    print(f"  {len(PASS)}/{len(PASS)} tests passed · 0 failed")
    print('='*60)
