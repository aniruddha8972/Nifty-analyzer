"""
agents/test_auth_ui.py — Auth page HTML/CSS + OTP flow tests (v7)
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

src      = (ROOT / "frontend/auth_page.py").read_text()
auth_src = (ROOT / "backend/auth.py").read_text()

def extract_markdown_strings(source):
    tree = ast.parse(source)
    results = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call): continue
        func = node.func
        is_md = (isinstance(func, ast.Attribute) and func.attr == "markdown") or \
                (isinstance(func, ast.Name) and func.id == "markdown")
        if not is_md: continue
        unsafe = any(kw.arg == "unsafe_allow_html" and isinstance(kw.value, ast.Constant)
                     and kw.value.value is True for kw in node.keywords)
        if not unsafe: continue
        if not node.args: continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            results.append(arg.value)
        elif isinstance(arg, ast.JoinedStr):
            parts = []
            for v in arg.values:
                if isinstance(v, ast.Constant): parts.append(v.value)
                else: parts.append("PLACEHOLDER")
            results.append("".join(parts))
    return results

html_blocks = extract_markdown_strings(src)

def count_tags(html):
    self_closing = {'br','hr','img','input','meta','link','canvas','col','area','base','embed','source','track','wbr'}
    opens  = [t.lower() for t in re.findall(r'<([a-zA-Z][a-zA-Z0-9]*)[^>]*(?<!/)>', html)
              if t.lower() not in self_closing]
    closes = [t.lower() for t in re.findall(r'</([a-zA-Z][a-zA-Z0-9]*)>', html)]
    return opens, closes

# ── HTML structural tests ─────────────────────────────────────────────────────

def test_syntax():          ast.parse(src); ast.parse(auth_src)
def test_components_html(): expect("components.html" in src)

def test_no_unclosed_divs():
    probs = []
    for i, block in enumerate(html_blocks):
        o, c = count_tags(block)
        if o.count("div") != c.count("div"):
            probs.append(f"Block {i}: {o.count('div')} opens vs {c.count('div')} closes — '{block.strip()[:60]}'")
    expect(not probs, "\n  ".join(probs))

def test_no_unclosed_spans():
    probs = []
    for i, block in enumerate(html_blocks):
        o, c = count_tags(block)
        if o.count("span") != c.count("span"):
            probs.append(f"Block {i}: span mismatch")
    expect(not probs, "\n  ".join(probs))

def test_no_stray_closing_tags():
    probs = []
    for i, block in enumerate(html_blocks):
        if re.match(r'^\s*</', block.strip()):
            probs.append(f"Block {i} starts with closing tag: '{block.strip()[:50]}'")
    expect(not probs, "\n  ".join(probs))

def test_no_widget_after_unclosed_div():
    lines = src.split('\n')
    probs = []
    widgets = ['st.text_input','st.button','st.selectbox','st.columns','st.spinner']
    for i, line in enumerate(lines):
        stripped = line.strip()
        if 'st.markdown(' in stripped and 'unsafe_allow_html=True' in stripped:
            o, c = count_tags(stripped)
            if o.count("div") > c.count("div"):
                j = i+1
                while j < len(lines) and (not lines[j].strip() or lines[j].strip().startswith('#')):
                    j += 1
                if j < len(lines) and any(w in lines[j] for w in widgets):
                    probs.append(f"Line {i+1}: unclosed div before widget at {j+1}")
    expect(not probs, "\n  ".join(probs))

def test_switchers_no_html_wrap():
    lines = src.split('\n')
    in_sw = False
    for line in lines:
        if 'def _switchers' in line: in_sw = True
        if in_sw and 'def _render' in line: break
        if in_sw and 'st.markdown' in line and '<div' in line and 'unsafe_allow_html' in line:
            expect(False, "_switchers() wraps st.button in st.markdown div")

# ── OTP flow tests ────────────────────────────────────────────────────────────

def test_no_password_fields():
    expect('type="password"' not in src and "type='password'" not in src,
           "Auth page must not have password input fields")

def test_otp_send_function():
    expect("send_otp" in src, "Must call send_otp()")
    expect("from backend.auth import" in src and "send_otp" in src)

def test_otp_verify_function():
    expect("verify_otp" in src, "Must call verify_otp()")

def test_two_step_flow():
    expect("otp_step" in src, "Must track otp_step state")
    expect('"email"' in src and '"verify"' in src, "Must have email and verify steps")

def test_otp_email_state():
    expect("otp_email" in src, "Must store otp_email in session state")

def test_local_mode_code_display():
    expect("otp_local" in src, "Must handle local OTP code display")
    expect("otp-local-code" in src or "LOCAL" in src, "Must show local OTP code")

def test_resend_button():
    expect("Resend" in src or "resend" in src, "Must have resend code button")

def test_back_button():
    expect("Go Back" in src or "go_back" in src or "otp_back" in src, "Must have back button from OTP step")

def test_six_digit_validation():
    # Supabase can send 6 or 8 digit codes depending on template/config
    expect("isdigit" in src, "Must validate numeric OTP")
    expect("6 <=" in src or "len(code) != 6" in src or "6–8" in src,
           "Must validate OTP length (6–8 digits)")

# ── auth.py OTP backend tests ─────────────────────────────────────────────────

def test_auth_send_otp_defined():
    expect("def send_otp" in auth_src)

def test_auth_verify_otp_defined():
    expect("def verify_otp" in auth_src)

def test_auth_no_password_in_login_flow():
    expect("sign_in_with_otp" in auth_src, "Must use sign_in_with_otp")
    expect("verify_otp" in auth_src)

def test_auth_local_otp_store():
    expect("_LOCAL_OTP" in auth_src, "Must have in-memory OTP store for local mode")
    expect("_OTP_TTL" in auth_src, "Must have OTP TTL")

def test_auth_local_otp_expiry():
    expect("time.time()" in auth_src, "Must check expiry with time.time()")

def test_auth_register_no_password():
    expect("def register" in auth_src)
    # register should not require password for OTP mode
    lines = auth_src.split('\n')
    for i, line in enumerate(lines):
        if 'def _sb_register' in line:
            sig = lines[i]
            expect("password" not in sig or "password: str = " in auth_src,
                   "_sb_register should not require password")

def test_auth_backward_compat():
    expect("def login" in auth_src, "login() must remain for backward compat")
    expect("def request_password_reset" in auth_src, "request_password_reset must remain")
    expect("def validate_password" in auth_src, "validate_password must remain")
    expect("def update_password" in auth_src, "update_password must remain")

# ── Design tests ──────────────────────────────────────────────────────────────

def test_shell_is_full_html():
    expect("<!DOCTYPE html>" in src)
    expect("</html>" in src)

def test_responsive():
    expect("@media" in src and "max-width" in src)

def test_mobile_stacking():
    expect("flex-direction:column" in src or "flex-direction: column" in src)

def test_particle_canvas():
    expect("canvas" in src and "requestAnimationFrame" in src)

def test_no_visibility_hidden():
    expect("visibility:hidden" not in src)

# ── Register and run ──────────────────────────────────────────────────────────

test("SYNTAX   — both files parse cleanly",                     test_syntax)
test("ARCH     — uses components.v1.html for shell",            test_components_html)
test("HTML     — no unclosed <div> per markdown block",         test_no_unclosed_divs)
test("HTML     — no unclosed <span> per markdown block",        test_no_unclosed_spans)
test("HTML     — no orphaned closing tags",                     test_no_stray_closing_tags)
test("HTML     — no widget after unclosed div",                 test_no_widget_after_unclosed_div)
test("HTML     — switchers have no div wrappers",               test_switchers_no_html_wrap)
test("OTP UI   — no password input fields",                     test_no_password_fields)
test("OTP UI   — send_otp() called",                            test_otp_send_function)
test("OTP UI   — verify_otp() called",                          test_otp_verify_function)
test("OTP UI   — two-step flow (email → verify)",               test_two_step_flow)
test("OTP UI   — otp_email stored in session state",            test_otp_email_state)
test("OTP UI   — local mode code display",                      test_local_mode_code_display)
test("OTP UI   — resend code button",                           test_resend_button)
test("OTP UI   — back button from verify step",                 test_back_button)
test("OTP UI   — 6-digit validation",                           test_six_digit_validation)
test("OTP AUTH — send_otp() defined in backend",                test_auth_send_otp_defined)
test("OTP AUTH — verify_otp() defined in backend",              test_auth_verify_otp_defined)
test("OTP AUTH — uses sign_in_with_otp API",                    test_auth_no_password_in_login_flow)
test("OTP AUTH — local mode OTP store",                         test_auth_local_otp_store)
test("OTP AUTH — OTP expiry enforced",                          test_auth_local_otp_expiry)
test("OTP AUTH — register no longer requires password",         test_auth_register_no_password)
test("OTP AUTH — backward compat aliases present",              test_auth_backward_compat)
test("DESIGN   — shell is full HTML document",                  test_shell_is_full_html)
test("DESIGN   — responsive media queries",                     test_responsive)
test("DESIGN   — mobile column stacking",                       test_mobile_stacking)
test("DESIGN   — particle canvas animation",                    test_particle_canvas)
test("DESIGN   — no visibility:hidden hack",                    test_no_visibility_hidden)

print(f"\n{'='*62}")
if FAIL:
    print(f"  ❌ FAILURES FOUND — {len(PASS)}/{len(PASS)+len(FAIL)} passed · {len(FAIL)} failed")
    for name, err in FAIL:
        print(f"\n  FAILED: {name}\n  {err}")
else:
    print(f"  ✅ ALL PASS — {len(PASS)}/{len(PASS)} · 0 failed")
print('='*62)
sys.exit(1 if FAIL else 0)
