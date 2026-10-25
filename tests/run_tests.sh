#!/usr/bin/env bash
# =============================================================================
# DreamStudio IDE - Test Runner
# =============================================================================
# Production-grade test runner with TUI interface, suite selection, and
# historical reporting. All test execution goes through this script.
#
# Usage:
#   ./tests/run_tests.sh                    # Interactive TUI
#   ./tests/run_tests.sh --suite bootstrapping  # Run single suite
#   ./tests/run_tests.sh --all              # Run all suites non-interactively
#   ./tests/run_tests.sh --list             # List available suites
#   ./tests/run_tests.sh --help             # Show help
#
# Exit codes:
#   0  - All selected tests passed
#   1  - Test failures detected
#   2  - Infrastructure/error (not a test failure)
#   3  - Interrupted by user
#   4  - No tests found/executed
# =============================================================================

set -euo pipefail

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly VENV_PYTHON="${PROJECT_ROOT}/venv/bin/python"
readonly TEST_RUNNER="${SCRIPT_DIR}/test_runner.py"
readonly REPORTS_DIR="${SCRIPT_DIR}/reports"
readonly RUNS_DIR="${REPORTS_DIR}/runs"
readonly HISTORY_DIR="${REPORTS_DIR}/history"
readonly HISTORY_FILE="${REPORTS_DIR}/HISTORY.md"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------
log_info() { echo -e "${GREEN}[INFO]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_debug() { echo -e "${CYAN}[DEBUG]${NC} $*"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $*"; }

die() {
    log_error "$*"
    exit 2
}

die_with_code() {
    local code="$1"
    shift
    log_error "$*"
    exit "${code}"
}

require_file() {
    [[ -f "$1" ]] || die "${2:-Required file not found: $1}"
}

require_dir() {
    [[ -d "$1" ]] || die "${2:-Required directory not found: $1}"
}

# -----------------------------------------------------------------------------
# Pre-flight Checks
# -----------------------------------------------------------------------------
preflight_checks() {
    log_step "Running pre-flight checks..."
    
    # Check virtual environment
    require_file "${VENV_PYTHON}" "Virtual environment not found at ${VENV_PYTHON}"
    
    # Check test runner
    require_file "${TEST_RUNNER}" "Test runner not found at ${TEST_RUNNER}"
    
    # Check project structure
    require_dir "${PROJECT_ROOT}/editor" "editor/ directory not found"
    require_dir "${PROJECT_ROOT}/config" "config/ (bootstrap) directory not found"
    require_file "${SCRIPT_DIR}/support/update_suite_readme.py"
    require_file "${SCRIPT_DIR}/support/record_run.py"

    # Ensure reports directories exist
    mkdir -p "${RUNS_DIR}" "${HISTORY_DIR}"
    
    # Verify Python version
    local py_version
    py_version=$("${VENV_PYTHON}" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [[ "${py_version}" != "3.12" ]]; then
        log_warn "Python version is ${py_version}, expected 3.12"
    fi
    
    log_info "Pre-flight checks passed"
}

# -----------------------------------------------------------------------------
# Suite Discovery
# -----------------------------------------------------------------------------
discover_suites() {
    local suites=()
    for dir in "${SCRIPT_DIR}"/*_test/; do
        [[ -d "${dir}" ]] || continue
        local basename=$(basename "${dir}")
        # Remove _test suffix for display
        local suite_name="${basename%_test}"
        suites+=("${suite_name}:${dir}")
    done
    
    if [[ ${#suites[@]} -eq 0 ]]; then
        die_with_code 4 "No test suites found in ${SCRIPT_DIR}"
    fi
    
    printf '%s\n' "${suites[@]}"
}

list_suites() {
    log_info "Available test suites:"
    echo
    local suites
    mapfile -t suites < <(discover_suites)
    for entry in "${suites[@]}"; do
        local name="${entry%%:*}"
        local path="${entry#*:}"
        local readme="${path}/README.md"
        local desc="No description"
        if [[ -f "${readme}" ]]; then
            desc=$(grep -A 2 "## Overview" "${readme}" 2>/dev/null | sed -n '2p' | xargs || echo "No description")
        fi
        printf "  ${BOLD}%-20s${NC} %s\n" "${name}" "${desc}"
    done
    echo
}

# -----------------------------------------------------------------------------
# Run ID Generation
# -----------------------------------------------------------------------------
generate_run_id() {
    local timestamp
    timestamp=$(date -u +"%Y%m%dT%H%M%SZ")
    local git_rev=""
    if git -C "${PROJECT_ROOT}" rev-parse --short HEAD >/dev/null 2>&1; then
        git_rev=$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD)
        local dirty=""
        if [[ -n "$(git -C "${PROJECT_ROOT}" status --porcelain 2>/dev/null)" ]]; then
            dirty="-dirty"
        fi
        git_rev="${git_rev}${dirty}"
    else
        git_rev="nogit"
    fi
    echo "${timestamp}-${git_rev}"
}

# -----------------------------------------------------------------------------
# Interactive TUI
# -----------------------------------------------------------------------------
run_interactive_tui() {
    local suites
    mapfile -t suites < <(discover_suites)
    
    if [[ ${#suites[@]} -eq 0 ]]; then
        die "No test suites available"
    fi
    
    local selected=()
    local current=0
    
    # Build suite names array for display
    local suite_names=()
    local suite_paths=()
    for entry in "${suites[@]}"; do
        suite_names+=("${entry%%:*}")
        suite_paths+=("${entry#*:}")
    done
    
    # Add "All Suites" option
    suite_names=("All Suites" "${suite_names[@]}")
    suite_paths=("__ALL__" "${suite_paths[@]}")
    
    clear
    echo -e "${BOLD}${CYAN}DreamStudio IDE Test Runner${NC}"
    echo -e "${CYAN}────────────────────────────────────────${NC}"
    echo
    echo "Use ↑/↓ to navigate, SPACE to toggle, ENTER to run, q to quit"
    echo
    
    while true; do
        clear
        echo -e "${BOLD}${CYAN}DreamStudio IDE Test Runner${NC}"
        echo -e "${CYAN}────────────────────────────────────────${NC}"
        echo
        
        for i in "${!suite_names[@]}"; do
            local prefix="  "
            [[ $i -eq $current ]] && prefix="${BOLD}${MAGENTA}▶ ${NC}"
            
            local status=""
            if [[ " ${selected[*]} " =~ " ${i} " ]]; then
                status="${GREEN}[✓]${NC} "
            else
                status="    "
            fi
            
            echo -e "${prefix}${status}${suite_names[i]}"
        done
        
        echo
        echo -e "${CYAN}────────────────────────────────────────${NC}"
        echo -e "Selected: ${#selected[@]} suite(s)"
        
        # Read key
        IFS= read -rsn1 key
        
        case "${key}" in
            $'\x1b') # Escape sequence
                read -rsn2 key
                case "${key}" in
                    '[A') # Up
                        ((current > 0)) && ((current--))
                        ;;
                    '[B') # Down
                        ((current < ${#suite_names[@]} - 1)) && ((current++))
                        ;;
                esac
                ;;
            ' ') # Space - toggle
                if [[ " ${selected[*]} " =~ " ${current} " ]]; then
                    local kept=()
                    local item
                    for item in "${selected[@]}"; do
                        [[ "${item}" == "${current}" ]] || kept+=("${item}")
                    done
                    selected=("${kept[@]}")
                else
                    selected+=("${current}")
                fi
                ;;
            '') # Enter - run
                if [[ ${#selected[@]} -eq 0 ]]; then
                    log_warn "No suites selected"
                    sleep 1
                else
                    break
                fi
                ;;
            'q'|'Q') # Quit
                echo
                log_info "Cancelled by user"
                exit 0
                ;;
        esac
    done
    
    # Build list of paths to run
    local run_paths=()
    for idx in "${selected[@]}"; do
        if [[ "${suite_paths[idx]}" == "__ALL__" ]]; then
            run_paths=("${suite_paths[@]:1}") # All except __ALL__
            break
        else
            run_paths+=("${suite_paths[idx]}")
        fi
    done
    
    run_selected_suites "${run_paths[@]}"
}

# -----------------------------------------------------------------------------
# Execute Selected Suites
# -----------------------------------------------------------------------------
run_selected_suites() {
    local suite_paths=("$@")
    if [[ ${#suite_paths[@]} -eq 0 ]]; then
        die_with_code 4 "No suites selected"
    fi

    local base_run_id
    base_run_id=$(generate_run_id)
    local run_id="${base_run_id}"
    local suffix=1
    # Reserve the directory atomically so two runners can never share or
    # overwrite the same artifact directory, even within the same second.
    while true; do
        if mkdir "${RUNS_DIR}/${run_id}" 2>/dev/null; then
            break
        fi
        if [[ -e "${RUNS_DIR}/${run_id}" ]]; then
            suffix=$((suffix + 1))
            run_id="${base_run_id}-${suffix}"
            if [[ ${suffix} -gt 1000 ]]; then
                die "Could not allocate a unique run directory for ${base_run_id}"
            fi
            continue
        fi
        die "Could not create run directory: ${RUNS_DIR}/${run_id}"
    done
    local run_dir="${RUNS_DIR}/${run_id}"

    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    local dirty_bool=false
    if [[ -n "$(git -C "${PROJECT_ROOT}" status --porcelain 2>/dev/null)" ]]; then
        dirty_bool=true
    fi

    log_info "Starting test run: ${run_id}"
    log_info "Run directory: ${run_dir}"

    # Record sanitized environment (no tokens or environment dump).
    {
        echo "Run ID: ${run_id}"
        echo "Timestamp: ${timestamp}"
        echo "Git revision: $(git -C "${PROJECT_ROOT}" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
        echo "Git dirty: ${dirty_bool}"
        echo "Python: $("${VENV_PYTHON}" --version)"
        echo "pytest: $("${VENV_PYTHON}" -m pytest --version 2>&1)"
        echo "Platform: $(uname -s)"
        echo "Suites: ${#suite_paths[@]}"
        for p in "${suite_paths[@]}"; do
            echo "  - $(basename "${p}")"
        done
    } > "${run_dir}/environment.txt"

    local start_time
    start_time=$(date +%s)

    local runner_pid_file="${run_dir}/runner.pid"
    local pipeline_pid
    local pipeline_status=0

    # Forward an interrupt received only by this shell to the Python runner.
    # Ctrl-C signals the whole process group, but CI or a supervisor may
    # signal only the shell.
    trap 'if [[ -s "${runner_pid_file}" ]]; then kill -INT "$(cat "${runner_pid_file}")" 2>/dev/null || true; fi; log_warn "Interrupt received; waiting for the test runner to save results..."' INT TERM

    # Run in the background so the trap is executed immediately while waiting.
    # ``tee`` ignores INT/TERM so it cannot close the pipe before the runner
    # has written its durable report.
    QT_QPA_PLATFORM=offscreen \
    PYTEST_CACHE_DIR="${PROJECT_ROOT}/.pytest_cache" \
    "${VENV_PYTHON}" "${TEST_RUNNER}" \
        --run-id "${run_id}" \
        --run-dir "${run_dir}" \
        --suites "${suite_paths[@]}" \
        2>&1 | (trap '' INT TERM; exec tee "${run_dir}/console.log") &
    pipeline_pid=$!

    set +e
    while true; do
        wait "${pipeline_pid}"
        pipeline_status=$?
        # A trapped signal makes ``wait`` return early without reaping the
        # job. Wait again until ``tee`` has actually exited.
        if ! kill -0 "${pipeline_pid}" 2>/dev/null; then
            break
        fi
    done
    set -e
    trap - INT TERM

    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # summary.json is authoritative for the runner's exit code; the pipeline
    # status only describes ``tee``.
    local exit_code=0
    if [[ -f "${run_dir}/summary.json" ]]; then
        exit_code=$(
            "${VENV_PYTHON}" -c \
                'import json, sys; print(int(json.load(open(sys.argv[1], encoding="utf-8")).get("exit_code", 2)))' \
                "${run_dir}/summary.json" 2>/dev/null || echo 2
        )
        [[ "${exit_code}" =~ ^[0-4]$ ]] || exit_code=2
    elif [[ ${pipeline_status} -ge 128 ]]; then
        exit_code=3
    else
        exit_code=2
    fi

    local git_rev
    git_rev=$(git -C "${PROJECT_ROOT}" rev-parse --short HEAD 2>/dev/null || echo "unknown")

    local record_args=(
        --run-id "${run_id}"
        --run-dir "${run_dir}"
        --timestamp "${timestamp}"
        --exit-code "${exit_code}"
        --duration "${duration}"
        --history-file "${HISTORY_FILE}"
        --history-dir "${HISTORY_DIR}"
        --git-rev "${git_rev}"
    )
    if [[ "${dirty_bool}" == "true" ]]; then
        record_args+=(--dirty)
    fi
    local suite_path
    for suite_path in "${suite_paths[@]}"; do
        record_args+=(--suite-path "${suite_path}")
    done

    if ! "${VENV_PYTHON}" "${SCRIPT_DIR}/support/record_run.py" \
        "${record_args[@]}"; then
        log_warn "Could not record run ${run_id} in history"
    fi

    log_info "Run recorded in ${HISTORY_FILE}"
    return "${exit_code}"
}

# -----------------------------------------------------------------------------
# Non-interactive Execution
# -----------------------------------------------------------------------------
run_non_interactive() {
    local suite_name="$1"
    local suite_paths=()
    
    if [[ "${suite_name}" == "all" ]]; then
        mapfile -t suite_paths < <(discover_suites | cut -d: -f2)
    else
        local found=false
        while IFS=: read -r name path; do
            if [[ "${name}" == "${suite_name}" ]]; then
                suite_paths=("${path}")
                found=true
                break
            fi
        done < <(discover_suites)
        
        [[ "${found}" == true ]] || die "Suite not found: ${suite_name}"
    fi
    
    run_selected_suites "${suite_paths[@]}"
}

# -----------------------------------------------------------------------------
# Help
# -----------------------------------------------------------------------------
show_help() {
    cat <<EOF
DreamStudio IDE Test Runner
============================

USAGE:
    ./tests/run_tests.sh [OPTIONS]

OPTIONS:
    --suite NAME        Run a specific suite by name
    --all               Run all suites (non-interactive)
    --list              List available suites and exit
    --interactive       Force interactive TUI (default when no args)
    --help              Show this help

SUITES:
    Available suites are discovered from tests/*_test/ directories.

EXAMPLES:
    ./tests/run_tests.sh                    # Interactive mode
    ./tests/run_tests.sh --suite bootstrapping  # Run bootstrapping suite
    ./tests/run_tests.sh --all              # Run all suites for CI

EXIT CODES:
    0  All tests passed
    1  Test failures detected
    2  Infrastructure/error (not a test failure)
    3  Interrupted by user
    4  No tests found/executed

ENVIRONMENT:
    QT_QPA_PLATFORM=offscreen  (forced for headless testing)
    PYTEST_CACHE_DIR           (set to .pytest_cache in project root)

REPORTS:
    Each run creates a unique directory under tests/reports/runs/<run_id>/
    containing report.md, summary.json, console.log, environment.txt

HISTORY:
    Global history is maintained in tests/reports/HISTORY.md
    Per-suite history is in each suite's README.md

EOF
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    local mode="interactive"
    local suite=""
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --suite)
                shift
                suite="$1"
                mode="non-interactive"
                ;;
            --all)
                suite="all"
                mode="non-interactive"
                ;;
            --list)
                preflight_checks
                list_suites
                exit 0
                ;;
            --interactive)
                mode="interactive"
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                die "Unknown option: $1 (use --help)"
                ;;
        esac
        shift
    done
    
    preflight_checks
    
    case "${mode}" in
        interactive)
            run_interactive_tui
            ;;
        non-interactive)
            run_non_interactive "${suite}"
            ;;
    esac
}

set +e
main "$@"
status=$?
set -e
exit "${status}"
