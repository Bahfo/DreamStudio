#!/usr/bin/env bash
# Bash-based structural tests for DreamStudio
# Usage: bash tests/test_bash.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

FAILED=0
PASSED=0

pass() {
    PASSED=$((PASSED + 1))
    echo "  [PASS] $1"
}

fail() {
    FAILED=$((FAILED + 1))
    echo "  [FAIL] $1"
}

check_file_exists() {
    if [[ -f "$1" ]]; then
        pass "File exists: $1"
    else
        fail "File missing: $1"
    fi
}

check_dir_exists() {
    if [[ -d "$1" ]]; then
        pass "Directory exists: $1"
    else
        fail "Directory missing: $1"
    fi
}

check_syntax() {
    if python3 -c "import py_compile; py_compile.compile('$1', doraise=True)" 2>/dev/null; then
        pass "Syntax OK: $1"
    else
        fail "Syntax ERROR: $1"
    fi
}

echo ""
echo "=== DreamStudio Structural Tests ==="
echo ""

echo "--- Entry Points ---"
check_file_exists "run.py"
check_file_exists "interface.py"
check_file_exists "welcome.py"

echo ""
echo "--- Core Directories ---"
check_dir_exists "editor"
check_dir_exists "editor/texteditor"
check_dir_exists "editor/lsp"
check_dir_exists "editor/utils"
check_dir_exists "editor/terminal"
check_dir_exists "backend"
check_dir_exists "assets"
check_dir_exists ".ai"

echo ""
echo "--- Core Files ---"
CORE_FILES=(
    "editor/ui_build.py"
    "editor/texteditor/code_editor.py"
    "editor/texteditor/tab_editor.py"
    "editor/lsp/jedi_worker.py"
    "editor/utils/statusBar.py"
    "backend/dirty_tracker.py"
    "editor/texteditor/minimap.py"
)
for f in "${CORE_FILES[@]}"; do
    check_file_exists "$f"
done

echo ""
echo "--- Python Syntax Check ---"
find . -name "*.py" \
    -not -path "./venv/*" \
    -not -path "./.venv/*" \
    -not -path "./__pycache__/*" \
    -not -path "./.git/*" \
    -print0 | while IFS= read -r -d '' f; do
    check_syntax "$f"
done

echo ""
echo "--- No Bare Except:Pass ---"
BAD=$(grep -r "except\s*:" --include="*.py" . \
    --exclude-dir=venv --exclude-dir=.venv --exclude-dir=.git --exclude-dir=__pycache__ --exclude-dir=tests \
    -l 2>/dev/null || true)
if [[ -z "$BAD" ]]; then
    pass "No bare except: blocks found in project code"
else
    fail "Bare except: found in:"
    echo "$BAD"
fi

echo ""
echo "--- No Placeholder TODOs ---"
STUBS=$(grep -rn "# TODO:" --include="*.py" . \
    -not -path "./venv/*" \
    -not -path "./.git/*" \
    -not -path "./tests/*" 2>/dev/null || true)
if [[ -z "$STUBS" ]]; then
    pass "No placeholder TODOs found"
else
    echo "  [INFO] TODOs found (not necessarily bad):"
    echo "$STUBS" | head -10
fi

echo ""
echo "--- Key Features Present ---"
if grep -q "handle_jedi_goto_results" editor/texteditor/code_editor.py; then
    pass "handle_jedi_goto_results exists"
else
    fail "handle_jedi_goto_results missing"
fi

if grep -q "_format_definition_tooltip" editor/texteditor/code_editor.py; then
    pass "_format_definition_tooltip exists"
else
    fail "_format_definition_tooltip missing"
fi

if grep -q "set_virtual_environment" editor/lsp/jedi_worker.py; then
    pass "set_virtual_environment exists in worker"
else
    fail "set_virtual_environment missing in worker"
fi

if grep -q "environment=self._jedi_env" editor/lsp/jedi_worker.py; then
    pass "Jedi environment parameter is passed"
else
    fail "Jedi environment parameter missing"
fi

if grep -q "QToolTip" editor/texteditor/code_editor.py; then
    pass "QToolTip integration present"
else
    fail "QToolTip integration missing"
fi

if grep -q "TOOLTIP_STYLE" run.py; then
    pass "Tooltip styling in run.py"
else
    fail "Tooltip styling missing in run.py"
fi

if grep -q "TOOLTIP_STYLE" interface.py; then
    pass "Tooltip styling in interface.py"
else
    fail "Tooltip styling missing in interface.py"
fi

echo ""
echo "--- No Old Patterns (in_builtin filter) ---"
if grep -q 'not d\.get("in_builtin"' editor/texteditor/code_editor.py 2>/dev/null; then
    fail "Old in_builtin filter still present"
else
    pass "Old in_builtin filter removed"
fi

echo ""
echo "--- No Old Patterns (_unresolvable) ---"
if grep -q "_unresolvable" editor/texteditor/code_editor.py 2>/dev/null; then
    fail "Old _unresolvable pattern still present"
else
    pass "Old _unresolvable pattern removed"
fi

echo ""
echo "========================"
echo "Results: $PASSED passed, $FAILED failed"
echo "========================"

if [[ $FAILED -gt 0 ]]; then
    exit 1
fi
