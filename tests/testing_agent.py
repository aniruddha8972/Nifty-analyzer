"""
tests/testing_agent.py
───────────────────────
Repetitive testing agent for the Nifty 50 scoring model.

Runs N rounds of analysis using varied synthetic StockData objects
designed to simulate the FULL realistic range of real yfinance values.
After all rounds it produces a diagnostic report that flags:

  • Score instability  — same stock type gives wildly different scores
  • Factor dominance   — one factor drowning out all others
  • Tier distribution  — is HOLD swallowing everything?
  • Edge case crashes  — zero volume, missing PE, extreme beta etc.
  • Monotonicity bugs  — better fundamentals should score higher
  • Gain/score paradox — top gainers scoring SELL or vice versa

Run:
    python tests/testing_agent.py
    python tests/testing_agent.py --rounds 200 --verbose
"""

import sys, os, argparse, random, statistics, collections
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.data_engine import StockData, SECTOR_MAP, DEFENSIVE_SECTORS
from backend.ai_model import analyse_stock, StockAnalysis

ROUNDS_DEFAULT = 100

# ── Colour codes for terminal output ─────────────────────────────────────────
GRN  = "\033[92m"
RED  = "\033[91m"
YLW  = "\033[93m"
BLU  = "\033[94m"
CYN  = "\033[96m"
DIM  = "\033[2m"
BOLD = "\033[1m"
RST  = "\033[0m"

def ok(msg):   print(f"  {GRN}✓{RST}  {msg}")
def fail(msg): print(f"  {RED}✗{RST}  {RED}{msg}{RST}")
def warn(msg): print(f"  {YLW}⚠{RST}  {YLW}{msg}{RST}")
def info(msg): print(f"  {BLU}→{RST}  {msg}")
def head(msg): print(f"\n{BOLD}{CYN}{msg}{RST}")
def sep():     print(f"  {DIM}{'─'*64}{RST}")


# ── Stock factory — builds realistic StockData from explicit parameters ───────
def make_stock(
    symbol     = "TEST",
    sector     = "Banking",
    close      = 1000.0,
    open_p     = None,       # defaults to close * (1 - chg/100)
    chg_pct    = 0.0,
    high_mult  = 1.03,
    low_mult   = 0.97,
    volume     = 3_000_000,
    avg_volume = 3_000_000,
    pe         = 22.0,
    w52h_mult  = 1.25,
    w52l_mult  = 0.75,
    rsi        = 55.0,
    beta       = 1.0,
    div        = 1.0,
    days       = 30,
) -> StockData:
    if open_p is None:
        denom = 1 + chg_pct / 100
        open_p = round(close / denom, 2) if denom != 0 else close
    return StockData(
        symbol      = symbol,
        sector      = sector,
        open_price  = round(open_p, 2),
        close_price = round(close, 2),
        high        = round(close * high_mult, 2),
        low         = round(close * low_mult, 2),
        chg_pct     = chg_pct,
        volume      = volume,
        avg_volume  = avg_volume,
        pe_ratio    = pe,
        week52_high = round(close * w52h_mult, 2),
        week52_low  = round(close * w52l_mult, 2),
        rsi         = rsi,
        beta        = beta,
        div_yield   = div,
        mkt_cap_b   = round(close * 1e10 / 1e9, 1),
        days        = days,
    )


# ══════════════════════════════════════════════════════════════════════════════
#  TEST SUITES
# ══════════════════════════════════════════════════════════════════════════════

issues = []   # global list of (severity, description) collected across all tests

def record(severity, msg):
    issues.append((severity, msg))
    if severity == "FAIL": fail(msg)
    elif severity == "WARN": warn(msg)
    else: ok(msg)


# ── Suite 1: Determinism ──────────────────────────────────────────────────────
def suite_determinism(rounds: int) -> dict:
    head(f"SUITE 1 — Determinism  ({rounds} rounds)")
    sep()
    s = make_stock(symbol="DET", chg_pct=5.0, rsi=65, pe=18, beta=0.9)
    scores = [analyse_stock(s).score for _ in range(rounds)]
    unique = set(scores)
    if len(unique) == 1:
        ok(f"Score is perfectly deterministic across {rounds} runs: {scores[0]}")
    else:
        record("FAIL", f"Score is NOT deterministic! Got {len(unique)} unique values: {sorted(unique)}")
    return {"scores": scores}


# ── Suite 2: Monotonicity — better inputs → higher score ─────────────────────
def suite_monotonicity() -> None:
    head("SUITE 2 — Monotonicity (better inputs → higher score)")
    sep()

    checks = [
        # (description, worse_kwargs, better_kwargs)
        ("RSI: 75 should score < RSI: 50",
            dict(rsi=75), dict(rsi=50)),
        ("RSI: 50 should score < RSI: 30 (oversold)",
            dict(rsi=50), dict(rsi=30)),
        ("P/E: 50 should score < P/E: 15",
            dict(pe=50), dict(pe=15)),
        ("P/E: 15 should score < P/E: 10",
            dict(pe=15), dict(pe=10)),
        ("Beta: 1.8 should score < Beta: 0.6",
            dict(beta=1.8), dict(beta=0.6)),
        ("Div: 0 should score < Div: 3",
            dict(div=0.0), dict(div=3.0)),
        ("chg_pct: -10 should score < chg_pct: +10",
            dict(chg_pct=-10), dict(chg_pct=10)),
        ("Volume ratio 0.4 should score < 2.0",
            dict(volume=1_000_000, avg_volume=3_000_000),
            dict(volume=6_000_000, avg_volume=3_000_000)),
        ("Near 52W high should score < near 52W low",
            dict(w52h_mult=1.02, w52l_mult=0.60),   # near high
            dict(w52h_mult=1.50, w52l_mult=0.98)),   # near low
    ]

    passed = failed_count = 0
    for desc, worse_kw, better_kw in checks:
        base = dict(chg_pct=2, rsi=65, pe=22, beta=1.0, div=1.0,
                    volume=3_000_000, avg_volume=3_000_000,
                    w52h_mult=1.25, w52l_mult=0.75)
        worse_args  = {**base, **worse_kw}
        better_args = {**base, **better_kw}
        s_worse  = make_stock(**worse_args)
        s_better = make_stock(**better_args)
        sc_worse  = analyse_stock(s_worse).score
        sc_better = analyse_stock(s_better).score
        if sc_better >= sc_worse:
            ok(f"{desc}  [{sc_worse} vs {sc_better}]")
            passed += 1
        else:
            record("FAIL", f"MONOTONICITY BROKEN: {desc}  [{sc_worse} vs {sc_better}]")
            failed_count += 1

    info(f"Monotonicity: {passed}/{passed+failed_count} checks passed")


# ── Suite 3: Factor isolation — each factor fires correctly ───────────────────
def suite_factor_isolation() -> dict:
    head("SUITE 3 — Factor Isolation (each factor in isolation)")
    sep()

    # Neutral baseline — RSI=65 is outside all RSI zones (not oversold/overbought/neutral)
    # chg_pct=2.0 triggers mild momentum +4, which is stable across all factor checks
    neutral = make_stock(
        sector="Banking",           # non-defensive → sector gives 0 pts
        chg_pct=2.0,                # mild positive → +4 pts momentum (stable)
        rsi=65.0,                   # between neutral(58) and overbought(70) → 0 pts
        pe=22.0,                    # between 18 and 35 → 0 pts
        beta=1.0,                   # between 0.65 and 1.2 → 0 pts
        div=0.5,                    # below 1.0 → 0 pts
        w52h_mult=1.25,             # position ~44% into range → 0 pts
        w52l_mult=0.75,
        volume=3_000_000,
        avg_volume=3_000_000,       # ratio = 1.0 → 0 pts
        days=30,
    )
    base_score = analyse_stock(neutral).score
    info(f"Neutral baseline score: {base_score}")

    results = {}
    factor_checks = [
        ("RSI oversold",      dict(rsi=30),   +15),
        ("RSI overbought",    dict(rsi=75),   -15),
        ("RSI neutral",       dict(rsi=52),   +5),
        ("PE < 12",           dict(pe=10),    +10),
        ("PE < 18",           dict(pe=16),    +6),
        ("PE > 55",           dict(pe=60),    -9),
        ("PE > 35",           dict(pe=40),    -4),
        ("Beta low (<0.65)",  dict(beta=0.5), +6),
        ("Beta high (>1.5)",  dict(beta=1.7), -6),
        ("Div > 2.5%",        dict(div=3.0),  +6),
        ("Div > 1%",          dict(div=1.5),  +3),
        ("Defensive sector",  dict(sector="FMCG"), +3),
        ("Vol > 1.6x",        dict(volume=5_000_000, avg_volume=3_000_000), +9),
        ("Vol < 0.55x",       dict(volume=1_000_000, avg_volume=3_000_000), -5),
    ]

    passed = failed_count = 0
    for fname, override, expected_delta in factor_checks:
        kwargs = dict(
            sector="Banking", chg_pct=2.0, rsi=65.0, pe=22.0,
            beta=1.0, div=0.5, w52h_mult=1.25, w52l_mult=0.75,
            volume=3_000_000, avg_volume=3_000_000, days=30,
        )
        kwargs.update(override)
        s = make_stock(**kwargs)
        sc = analyse_stock(s).score
        actual_delta = sc - base_score
        # Allow ±2 tolerance for interaction effects
        if abs(actual_delta - expected_delta) <= 2:
            ok(f"{fname:<28} expected Δ{expected_delta:+d}  got Δ{actual_delta:+d}  score={sc}")
            passed += 1
        else:
            record("WARN", f"{fname:<28} expected Δ{expected_delta:+d}  got Δ{actual_delta:+d}  score={sc}  ← off by {actual_delta-expected_delta:+d}")
            failed_count += 1
        results[fname] = {"expected": expected_delta, "actual": actual_delta, "score": sc}

    info(f"Factor isolation: {passed}/{passed+failed_count} checks within tolerance")
    return results


# ── Suite 4: Tier distribution across random realistic stocks ─────────────────
def suite_distribution(rounds: int, verbose: bool = False) -> dict:
    head(f"SUITE 4 — Tier Distribution  ({rounds} random realistic stocks)")
    sep()

    rng = random.Random(42)   # fixed seed for reproducibility
    tier_counts = collections.Counter()
    scores_all  = []

    for i in range(rounds):
        s = make_stock(
            symbol    = f"S{i:03d}",
            sector    = rng.choice(list(set(SECTOR_MAP.values()))),
            chg_pct   = rng.uniform(-15, 15),
            rsi       = rng.uniform(25, 80),
            pe        = rng.uniform(8, 65),
            beta      = rng.uniform(0.4, 2.0),
            div       = rng.uniform(0, 4),
            w52h_mult = rng.uniform(1.05, 1.6),
            w52l_mult = rng.uniform(0.5,  0.95),
            volume    = int(rng.uniform(500_000, 10_000_000)),
            avg_volume= int(rng.uniform(500_000, 10_000_000)),
            days      = rng.choice([7, 14, 30, 90, 180, 365]),
        )
        a = analyse_stock(s)
        tier_counts[a.recommendation] += 1
        scores_all.append(a.score)

    total = sum(tier_counts.values())
    print(f"\n  {'Tier':<16} {'Count':>6}  {'%':>6}  Bar")
    sep()
    for tier in ["STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"]:
        cnt = tier_counts.get(tier, 0)
        pct = cnt / total * 100
        bar = "█" * int(pct / 2)
        # Flag if HOLD is too dominant (>60%) or any tier is 0
        flag = ""
        if tier == "HOLD" and pct > 60:
            flag = f"  {YLW}⚠ HOLD dominance{RST}"
            record("WARN", f"HOLD tier is {pct:.1f}% of all stocks — model may be too conservative")
        if cnt == 0:
            flag = f"  {RED}✗ EMPTY{RST}"
            record("FAIL", f"Tier '{tier}' never triggered in {rounds} rounds — dead tier")
        print(f"  {tier:<16} {cnt:>6}  {pct:>5.1f}%  {bar}{flag}")

    sep()
    mean_score = statistics.mean(scores_all)
    std_score  = statistics.stdev(scores_all)
    info(f"Score stats — mean: {mean_score:.1f}  stdev: {std_score:.1f}  "
         f"min: {min(scores_all)}  max: {max(scores_all)}")

    # Healthy range checks
    if mean_score < 40 or mean_score > 60:
        record("WARN", f"Mean score {mean_score:.1f} is far from neutral (50) — model may be biased")
    else:
        ok(f"Mean score {mean_score:.1f} is near neutral (50) ✓")

    if std_score < 8:
        record("WARN", f"Stdev {std_score:.1f} is very low — scores are too bunched, model lacks discrimination")
    elif std_score > 25:
        record("WARN", f"Stdev {std_score:.1f} is very high — scores are too spread, model may be over-reactive")
    else:
        ok(f"Stdev {std_score:.1f} is in healthy range (8–25) ✓")

    return {"tier_counts": dict(tier_counts), "mean": mean_score, "std": std_score}


# ── Suite 5: Edge cases — zeros, extremes, missing data ──────────────────────
def suite_edge_cases() -> None:
    head("SUITE 5 — Edge Cases (zeros, extremes, boundary values)")
    sep()

    cases = [
        ("Zero volume",          dict(volume=0,        avg_volume=0)),
        ("Zero PE",              dict(pe=0.0)),
        ("Zero dividend",        dict(div=0.0)),
        ("Zero beta",            dict(beta=0.0)),
        ("Very high PE (999)",   dict(pe=999.0)),
        ("Very high beta (5.0)", dict(beta=5.0)),
        ("RSI at exact 35",      dict(rsi=35.0)),
        ("RSI at exact 70",      dict(rsi=70.0)),
        ("RSI at exact 42",      dict(rsi=42.0)),
        ("RSI at exact 60",      dict(rsi=60.0)),
        ("52W high == low",      dict(w52h_mult=1.0, w52l_mult=1.0)),
        ("52W low > close",      dict(w52h_mult=0.5, w52l_mult=0.3)),
        ("chg_pct = 0",          dict(chg_pct=0.0)),
        ("chg_pct = +100%",      dict(chg_pct=100.0)),
        ("chg_pct = -100%",      dict(chg_pct=-100.0)),
        ("1 day period",         dict(days=1)),
        ("365 day period",       dict(days=365)),
    ]

    passed = crashed = 0
    for desc, kw in cases:
        base = dict(chg_pct=2.0, rsi=65.0, pe=22.0, beta=1.0, div=1.0,
                    volume=3_000_000, avg_volume=3_000_000,
                    w52h_mult=1.25, w52l_mult=0.75, days=30)
        base.update(kw)
        try:
            s = make_stock(**base)
            a = analyse_stock(s)
            assert 0 <= a.score <= 100, f"Score {a.score} out of range"
            assert a.recommendation in {"STRONG BUY","BUY","HOLD","SELL","STRONG SELL"}
            ok(f"{desc:<35}  score={a.score}  rec={a.recommendation}")
            passed += 1
        except Exception as e:
            record("FAIL", f"{desc:<35}  CRASHED: {e}")
            crashed += 1

    info(f"Edge cases: {passed}/{passed+crashed} passed without crash")


# ── Suite 6: Gain/score sanity — top gainer shouldn't always be STRONG BUY ───
def suite_gain_score_sanity(rounds: int) -> None:
    head(f"SUITE 6 — Gain/Score Sanity  ({rounds} rounds)")
    sep()
    info("A top gainer with bad fundamentals should NOT be STRONG BUY")
    info("A top loser with great fundamentals should NOT be STRONG SELL")

    rng = random.Random(99)
    paradoxes = 0

    for _ in range(rounds):
        # Top gainer but terrible fundamentals
        gainer_bad = make_stock(
            chg_pct=rng.uniform(10, 20),   # big gain
            rsi=rng.uniform(75, 90),        # overbought
            pe=rng.uniform(60, 100),        # very expensive
            beta=rng.uniform(1.6, 2.5),     # high volatility
            div=0.0,
            w52h_mult=1.01,                 # near 52W high
            w52l_mult=0.50,
        )
        a_gb = analyse_stock(gainer_bad)
        if a_gb.recommendation == "STRONG BUY":
            paradoxes += 1

        # Top loser but great fundamentals
        loser_good = make_stock(
            chg_pct=rng.uniform(-20, -10),  # big loss
            rsi=rng.uniform(20, 34),         # oversold
            pe=rng.uniform(8, 14),           # cheap
            beta=rng.uniform(0.4, 0.65),     # low volatility
            div=rng.uniform(2.5, 4.0),
            w52h_mult=1.60,                  # near 52W low
            w52l_mult=0.98,
        )
        a_lg = analyse_stock(loser_good)
        if a_lg.recommendation == "STRONG SELL":
            paradoxes += 1

    if paradoxes == 0:
        ok(f"No gain/score paradoxes found in {rounds*2} checks ✓")
    else:
        record("FAIL", f"{paradoxes} gain/score paradoxes found — "
               "model is dominated by momentum, ignoring fundamentals")

    # Specific extreme examples
    info("Specific extreme test cases:")
    cases = [
        ("Mega gainer + terrible fundamentals",
            make_stock(chg_pct=25, rsi=85, pe=80, beta=2.0, div=0, w52h_mult=1.01, w52l_mult=0.5),
            {"HOLD", "SELL", "STRONG SELL"}),
        ("Mega loser + perfect fundamentals",
            make_stock(chg_pct=-25, rsi=25, pe=9, beta=0.5, div=3.5, w52h_mult=1.8, w52l_mult=0.99, days=90),
            {"BUY", "STRONG BUY", "HOLD"}),
        ("Flat + neutral everything",
            make_stock(chg_pct=0, rsi=50, pe=22, beta=1.0, div=0.5),
            {"HOLD"}),
    ]
    for desc, s, expected_recs in cases:
        a = analyse_stock(s)
        if a.recommendation in expected_recs:
            ok(f"{desc:<45}  score={a.score}  rec={a.recommendation}")
        else:
            record("WARN", f"{desc:<45}  score={a.score}  rec={a.recommendation}  "
                   f"(expected one of {expected_recs})")


# ── Suite 7: Score stability — small input changes = small score changes ──────
def suite_stability(rounds: int) -> None:
    head(f"SUITE 7 — Score Stability  ({rounds} rounds with tiny perturbations)")
    sep()
    info("A ±0.1 change in RSI/PE/beta should cause a score change ≤ 5 points")

    rng = random.Random(7)
    large_jumps = 0

    for _ in range(rounds):
        base_rsi  = rng.uniform(36, 69)     # avoid oversold/overbought zones
        base_pe   = rng.uniform(19, 34)
        base_beta = rng.uniform(0.66, 1.19)

        s1 = make_stock(rsi=base_rsi,        pe=base_pe,        beta=base_beta)
        s2 = make_stock(rsi=base_rsi + 0.1,  pe=base_pe + 0.1,  beta=base_beta + 0.01)

        sc1 = analyse_stock(s1).score
        sc2 = analyse_stock(s2).score
        diff = abs(sc2 - sc1)
        if diff > 5:   # >5 means two factors fired simultaneously from one tiny nudge
            large_jumps += 1

    if large_jumps == 0:
        ok(f"No large score jumps (>5pts) from tiny input changes in {rounds} rounds ✓")
    else:
        record("WARN", f"{large_jumps}/{rounds} rounds showed score jumps > 5 pts from ±0.1 input change "
               "— possible compound boundary sensitivity")


# ── Suite 8: Repetitive stress test — score all 50 Nifty tickers N times ─────
def suite_stress(rounds: int) -> None:
    head(f"SUITE 8 — Stress Test  (all 50 symbols × {rounds} random periods)")
    sep()

    rng = random.Random(2024)
    all_syms = list(SECTOR_MAP.keys())
    crashes  = 0
    score_by_sym: dict[str, list] = {s: [] for s in all_syms}

    for _ in range(rounds):
        for sym in all_syms:
            s = make_stock(
                symbol    = sym,
                sector    = SECTOR_MAP[sym],
                chg_pct   = rng.uniform(-20, 20),
                rsi       = rng.uniform(20, 85),
                pe        = rng.uniform(6, 70),
                beta      = rng.uniform(0.3, 2.5),
                div       = rng.uniform(0, 4),
                w52h_mult = rng.uniform(1.05, 1.7),
                w52l_mult = rng.uniform(0.4, 0.95),
                volume    = int(rng.uniform(100_000, 15_000_000)),
                avg_volume= int(rng.uniform(100_000, 15_000_000)),
                days      = rng.choice([7, 14, 30, 60, 90, 180, 365]),
            )
            try:
                a = analyse_stock(s)
                assert 0 <= a.score <= 100
                score_by_sym[sym].append(a.score)
            except Exception as e:
                crashes += 1

    total_runs = rounds * len(all_syms)
    if crashes == 0:
        ok(f"Zero crashes in {total_runs:,} scoring runs ✓")
    else:
        record("FAIL", f"{crashes} crashes in {total_runs:,} runs")

    # Detect symbols with suspiciously wide score variance
    volatile_syms = []
    for sym, scores in score_by_sym.items():
        if len(scores) < 2: continue
        spread = max(scores) - min(scores)
        if spread < 20:
            volatile_syms.append((sym, spread, min(scores), max(scores)))

    if not volatile_syms:
        ok(f"All symbols show good score range (spread ≥ 20) across varied inputs ✓")
    else:
        warn(f"{len(volatile_syms)} symbols have narrow score spread (<20pts) — "
             "may indicate a stuck factor")
        for sym, spread, lo, hi in volatile_syms[:5]:
            info(f"  {sym}: spread={spread}  range=[{lo},{hi}]")


# ══════════════════════════════════════════════════════════════════════════════
#  FINAL REPORT
# ══════════════════════════════════════════════════════════════════════════════

def print_final_report():
    head("FINAL DIAGNOSTIC REPORT")
    sep()

    fails = [(s,m) for s,m in issues if s == "FAIL"]
    warns = [(s,m) for s,m in issues if s == "WARN"]
    oks   = [(s,m) for s,m in issues if s == "OK"]

    print(f"\n  {BOLD}Summary:{RST}")
    print(f"    {GRN}✓ Passed:{RST}   {len(oks)}")
    print(f"    {YLW}⚠ Warnings:{RST} {len(warns)}")
    print(f"    {RED}✗ Failures:{RST} {len(fails)}")

    if fails:
        print(f"\n  {RED}{BOLD}FAILURES (must fix):{RST}")
        for _, m in fails:
            print(f"    {RED}✗{RST} {m}")

    if warns:
        print(f"\n  {YLW}{BOLD}WARNINGS (should investigate):{RST}")
        for _, m in warns:
            print(f"    {YLW}⚠{RST} {m}")

    if not fails and not warns:
        print(f"\n  {GRN}{BOLD}✓ All checks passed — model is stable and well-calibrated!{RST}")
    elif not fails:
        print(f"\n  {YLW}{BOLD}Model is stable with minor calibration warnings.{RST}")
    else:
        print(f"\n  {RED}{BOLD}Model has issues that will cause volatile/unreliable scores.{RST}")

    sep()
    print()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Nifty 50 scoring model testing agent")
    parser.add_argument("--rounds",  type=int, default=ROUNDS_DEFAULT,
                        help=f"Number of random rounds per suite (default: {ROUNDS_DEFAULT})")
    parser.add_argument("--verbose", action="store_true", help="Show extra detail")
    args = parser.parse_args()

    print(f"\n{BOLD}{'═'*66}{RST}")
    print(f"{BOLD}  NIFTY 50 SCORING MODEL — TESTING AGENT{RST}")
    print(f"{BOLD}  Rounds: {args.rounds}   Suites: 8{RST}")
    print(f"{BOLD}{'═'*66}{RST}")

    suite_determinism(args.rounds)
    suite_monotonicity()
    suite_factor_isolation()
    suite_distribution(args.rounds, args.verbose)
    suite_edge_cases()
    suite_gain_score_sanity(args.rounds)
    suite_stability(args.rounds)
    suite_stress(args.rounds)

    print_final_report()

    # Exit 1 if any failures
    sys.exit(1 if any(s == "FAIL" for s, _ in issues) else 0)


if __name__ == "__main__":
    main()
