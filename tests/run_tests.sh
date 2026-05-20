#!/usr/bin/env bash
# DreamStudio Test Runner
# Runs Python unit tests and Bash structural tests.
#
# Usage:
#   bash tests/run_tests.sh              # Run all tests
#   bash tests/run_tests.sh --unit       # Run only Python unit tests
#   bash tests/run_tests.sh --bash       # Run only Bash structural tests

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}   DreamStudio Test Suite${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""

RUN_UNIT=true
RUN_BASH=true

if [[ $# -gt 0 ]]; then
    case "$1" in
        --unit) RUN_BASH=false ;;
        --bash) RUN_UNIT=false ;;
        *) echo "Usage: $0 [--unit | --bash]"; exit 1 ;;
    esac
fi

EXIT_CODE=0

if $RUN_UNIT; then
    echo -e "${YELLOW}[1/2] Python Unit Tests${NC}"
    echo ""
    PYTHONPATH="${PYTHONPATH:-}:$PROJECT_DIR" "$PROJECT_DIR/venv/bin/python3" -m pytest tests/ \
        -v \
        --tb=short \
        --no-header \
        -p no:warnings \
        2>&1 || {
        echo -e "${RED}Python tests failed${NC}"
        EXIT_CODE=1
    }
    echo ""
fi

if $RUN_BASH; then
    echo -e "${YELLOW}[2/2] Bash Structural Tests${NC}"
    echo ""
    bash tests/test_bash.sh || {
        echo -e "${RED}Bash tests failed${NC}"
        EXIT_CODE=1
    }
    echo ""
fi

echo -e "${YELLOW}========================================${NC}"
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}All tests passed${NC}"
else
    echo -e "${RED}Some tests failed${NC}"
fi
echo -e "${YELLOW}========================================${NC}"

exit $EXIT_CODE
