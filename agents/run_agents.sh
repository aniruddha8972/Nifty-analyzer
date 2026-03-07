#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════
# run_agents.sh — Production Readiness Pipeline
# ══════════════════════════════════════════════════════════════════════
# Runs Bug Fixer → Tests → Bug Fixer → Tests (up to 3 iterations)
# until all tests pass.
#
# Usage:
#   cd nifty50_pro
#   bash agents/run_agents.sh
# ══════════════════════════════════════════════════════════════════════

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

MAX_ITERATIONS=3
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        NIFTY 50 ANALYZER — PRODUCTION READINESS PIPELINE    ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

for i in $(seq 1 $MAX_ITERATIONS); do
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BOLD}  ITERATION $i / $MAX_ITERATIONS${NC}"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

  # ── Step 1: Bug Fixer Agent ──────────────────────────────────────
  echo ""
  echo -e "${YELLOW}▶  STEP 1 — Bug Fixer Agent${NC}"
  echo ""
  python agents/bug_fixer.py
  echo ""

  # ── Step 2: Test Agent ───────────────────────────────────────────
  echo -e "${YELLOW}▶  STEP 2 — Test Agent${NC}"
  echo ""
  if python agents/test_agent.py; then
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅  ALL TESTS PASS — APP IS PRODUCTION READY               ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Deploy with:  ${BOLD}streamlit run app.py${NC}"
    echo -e "  Or push to Streamlit Cloud and add Supabase secrets."
    echo ""
    exit 0
  fi

  if [ $i -lt $MAX_ITERATIONS ]; then
    echo ""
    echo -e "${YELLOW}  ↻  Failures detected — running Bug Fixer again…${NC}"
    echo ""
  fi
done

echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║  ❌  TESTS STILL FAILING AFTER $MAX_ITERATIONS ITERATIONS                ║${NC}"
echo -e "${RED}║  Manual review required — see failures above.               ║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""
exit 1
