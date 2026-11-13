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
    py_version=$(
        "${VENV_PYTHON}" -c \
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    )
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
            desc=$(
                grep -A 2 "## Overview" "${readme}" 2>/dev/null |
                    sed -n '2p' |
                    xargs || echo "No description"
            )
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
# Interactive terminal interface
# -----------------------------------------------------------------------------
TUI_TTY_STATE=""
TUI_TTY_FD=""
TUI_SCREEN_ACTIVE=false
TUI_PANEL_LEFT=1
TUI_PANEL_INNER_WIDTH=0


tui_restore_terminal() {
    if [[ -n "${TUI_TTY_FD}" ]]; then
        if [[ -n "${TUI_TTY_STATE}" ]]; then
            stty "${TUI_TTY_STATE}" <&"${TUI_TTY_FD}" 2>/dev/null || true
        fi

        printf '\033[0m\033[?25h' >&"${TUI_TTY_FD}" 2>/dev/null || true
        if [[ "${TUI_SCREEN_ACTIVE}" == true ]]; then
            printf '\033[?1049l' >&"${TUI_TTY_FD}" 2>/dev/null || true
        fi
        exec {TUI_TTY_FD}>&-
    fi

    TUI_TTY_STATE=""
    TUI_TTY_FD=""
    TUI_SCREEN_ACTIVE=false
}


tui_draw_text() {
    local row="$1"
    local offset="$2"
    local style="$3"
    local value="$4"
    local width=$((TUI_PANEL_INNER_WIDTH - offset))

    if (( width <= 0 )); then
        return 0
    fi

    value="${value:0:width}"
    printf '\033[%d;%dH%b%-*s\033[0m' \
        "${row}" "$((TUI_PANEL_LEFT + 1 + offset))" "${style}" "${width}" "${value}" \
        >&"${TUI_TTY_FD}"
}


tui_render() {
    local -n names_ref="$1"
    local -n selected_ref="$2"
    local current="$3"
    local notice="$4"
    local dimensions rows columns panel_width panel_height panel_top panel_left
    local inner_width list_height first last index item row label marker pointer
    local selection_summary suite_meta meta_offset horizontal title
    local color_enabled=true style_border style_title style_body style_muted
    local style_heading style_selected style_check style_notice style_footer
    local current_selected selected_all=false selected_count="${#selected_ref[@]}"
    local total_suites
    total_suites=$((${#names_ref[@]} - 1))

    if [[ -n "${NO_COLOR:-}" || "${TERM:-dumb}" == dumb ]]; then
        color_enabled=false
    fi

    dimensions=$(stty size <&"${TUI_TTY_FD}" 2>/dev/null || true)
    if [[ "${dimensions}" =~ ^([0-9]+)[[:space:]]+([0-9]+)$ ]]; then
        rows="${BASH_REMATCH[1]}"
        columns="${BASH_REMATCH[2]}"
    else
        rows="${LINES:-24}"
        columns="${COLUMNS:-80}"
    fi

    if (( columns < 52 || rows < 16 )); then
        printf '\033[0m\033[2J\033[H' >&"${TUI_TTY_FD}"
        if [[ "${color_enabled}" == true ]]; then
            printf '\033[44;97m' >&"${TUI_TTY_FD}"
        fi
        printf '\033[%d;1H  Resize the terminal to at least 52 columns by 16 rows.' \
            "$((rows / 2))" >&"${TUI_TTY_FD}"
        printf '\033[%d;1H  Press Q to quit.' "$((rows / 2 + 1))" >&"${TUI_TTY_FD}"
        return 0
    fi

    panel_width=$((columns - 8))
    if (( panel_width > 88 )); then
        panel_width=88
    fi
    panel_height=$((rows - 4))
    if (( panel_height > 26 )); then
        panel_height=26
    fi

    inner_width=$((panel_width - 2))
    list_height=$((panel_height - 11))
    panel_top=$(((rows - panel_height) / 2 + 1))
    panel_left=$(((columns - panel_width) / 2 + 1))
    TUI_PANEL_LEFT="${panel_left}"
    TUI_PANEL_INNER_WIDTH="${inner_width}"

    first=0
    if (( current >= list_height )); then
        first=$((current - list_height + 1))
    fi
    last=$((first + list_height - 1))
    if (( last >= ${#names_ref[@]} )); then
        last=$((${#names_ref[@]} - 1))
    fi

    if (( selected_count == 1 )) && [[ "${selected_ref[0]}" == 0 ]]; then
        selected_all=true
        selection_summary="ALL ${#names_ref[@]} ENTRIES SELECTED"
        selection_summary="ALL $((${#names_ref[@]} - 1)) SUITES SELECTED"
    elif (( selected_count == 0 )); then
        selection_summary="NO SUITES SELECTED"
    else
        selection_summary="${selected_count} SUITES SELECTED"
    fi

    style_border=$'\033[97;44m'
    style_title=$'\033[104;97;1m'
    style_body=$'\033[47;30m'
    style_muted=$'\033[47;90m'
    style_heading=$'\033[47;34;1m'
    style_selected=$'\033[104;97;1m'
    style_check=$'\033[47;32;1m'
    style_notice=$'\033[47;33;1m'
    style_footer=$'\033[47;34m'

    if [[ "${color_enabled}" == true ]]; then
        printf '\033[0m\033[44;97m\033[2J\033[H' >&"${TUI_TTY_FD}"
        for ((row = 1; row <= rows; row++)); do
            printf '\033[%d;1H\033[44m%*s' "${row}" "${columns}" '' >&"${TUI_TTY_FD}"
        done
    else
        printf '\033[0m\033[2J\033[H' >&"${TUI_TTY_FD}"
        style_border=""
        style_title=""
        style_body=""
        style_muted=""
        style_heading=""
        style_selected=""
        style_check=""
        style_notice=""
        style_footer=""
    fi

    printf -v horizontal '%*s' "${inner_width}" ''
    horizontal="${horizontal// /─}"
    title="  DREAMSTUDIO IDE   /   TEST SUITE MANAGER"

    printf '\033[%d;%dH%b┌%s┐' \
        "${panel_top}" "${panel_left}" "${style_border}" "${horizontal}" >&"${TUI_TTY_FD}"

    for ((row = 1; row < panel_height - 1; row++)); do
        printf '\033[%d;%dH%b│%b%*s%b│' \
            "$((panel_top + row))" "${panel_left}" "${style_border}" \
            "${style_body}" "${inner_width}" '' "${style_border}" >&"${TUI_TTY_FD}"
    done

    printf '\033[%d;%dH%b└%s┘' \
        "$((panel_top + panel_height - 1))" "${panel_left}" \
        "${style_border}" "${horizontal}" >&"${TUI_TTY_FD}"

    tui_draw_text "$((panel_top + 1))" 0 "${style_title}" "${title}"
    tui_draw_text "$((panel_top + 2))" 2 "${style_body}" \
        "Select the test suites to include in this run."

    tui_draw_text "$((panel_top + 4))" 2 "${style_heading}" "AVAILABLE TEST SUITES"
    suite_meta="${#names_ref[@]} OPTIONS"
    meta_offset=$((inner_width - ${#suite_meta} - 2))
    tui_draw_text "$((panel_top + 4))" "${meta_offset}" "${style_muted}" "${suite_meta}"

    for ((index = first; index <= last; index++)); do
        row=$((panel_top + 5 + index - first))
        current_selected=false
        if (( index == 0 )); then
            current_selected="${selected_all}"
        else
            for item in "${selected_ref[@]}"; do
                if [[ "${item}" == "${index}" ]]; then
                    current_selected=true
                    break
                fi
            done
        fi

        marker='[ ]'
        if [[ "${current_selected}" == true ]]; then
            marker='[✓]'
        fi

        pointer=' '
        if (( index == current )); then
            pointer='›'
            tui_draw_text "${row}" 0 "${style_selected}" "${pointer}"
            tui_draw_text "${row}" 3 "${style_selected}" "${marker}"
            label="${names_ref[index]}"
            if (( ${#label} > inner_width - 13 )); then
                label="${label:0:inner_width-14}…"
            fi
            tui_draw_text "${row}" 9 "${style_selected}" "${label}"
        else
            tui_draw_text "${row}" 0 "${style_body}" "${pointer}"
            if [[ "${current_selected}" == true ]]; then
                tui_draw_text "${row}" 3 "${style_check}" "${marker}"
            else
                tui_draw_text "${row}" 3 "${style_body}" "${marker}"
            fi
            label="${names_ref[index]}"
            if (( ${#label} > inner_width - 13 )); then
                label="${label:0:inner_width-14}…"
            fi
            tui_draw_text "${row}" 9 "${style_body}" "${label}"
        fi
    done

    tui_draw_text "$((panel_top + 5 + list_height))" 0 "${style_muted}" "${horizontal}"
    tui_draw_text "$((panel_top + 6 + list_height))" 2 "${style_heading}" \
        "SELECTION: ${selection_summary}"

    if [[ -n "${notice}" ]]; then
        tui_draw_text "$((panel_top + 7 + list_height))" 2 "${style_notice}" "${notice}"
    else
        tui_draw_text "$((panel_top + 7 + list_height))" 2 "${style_muted}" \
            "Use Space to toggle an entry. Select at least one suite to continue."
    fi

    tui_draw_text "$((panel_top + 8 + list_height))" 2 "${style_footer}" \
        '↑/↓ Move  SPACE Toggle  A All  N Clear'
    tui_draw_text "$((panel_top + 9 + list_height))" 2 "${style_footer}" \
        'ENTER Run  Q Quit'
}


run_interactive_tui() {
    local suites suite_names=() suite_paths=() selected=()
    local current=0 key sequence item updated=() run_paths=() notice=""
    local already_selected index

    if [[ ! -r /dev/tty || ! -w /dev/tty ]]; then
        die "Interactive mode requires a terminal. Use --all or --suite NAME instead."
    fi

    mapfile -t suites < <(discover_suites)
    if [[ ${#suites[@]} -eq 0 ]]; then
        die_with_code 4 "No test suites available"
    fi

    for item in "${suites[@]}"; do
        suite_names+=("${item%%:*}")
        suite_paths+=("${item#*:}")
    done

    suite_names=("All suites" "${suite_names[@]}")
    if ! exec {TUI_TTY_FD}<>/dev/tty; then
        die "Unable to open the controlling terminal"
    fi

    if ! TUI_TTY_STATE=$(stty -g <&"${TUI_TTY_FD}" 2>/dev/null); then
        tui_restore_terminal
        die "Unable to read terminal settings"
    fi

    trap 'tui_restore_terminal; exit 3' INT TERM
    if ! stty -echo -icanon min 1 time 0 <&"${TUI_TTY_FD}"; then
        tui_restore_terminal
        trap - INT TERM
        die "Unable to configure terminal input"
    fi

    printf '\033[?1049h\033[?25l' >&"${TUI_TTY_FD}"
    TUI_SCREEN_ACTIVE=true

    while true; do
        tui_render suite_names selected "${current}" "${notice}"
        notice=""

        if ! IFS= read -r -s -n 1 -u "${TUI_TTY_FD}" key; then
            tui_restore_terminal
            trap - INT TERM
            die "Unable to read terminal input"
        fi

        case "${key}" in
            $'\x1b')
                sequence=""
                IFS= read -r -s -n 2 -t 0.05 -u "${TUI_TTY_FD}" sequence || true
                case "${sequence}" in
                    '[A'|'[H'|'[1~')
                        if [[ "${sequence}" == '[H' || "${sequence}" == '[1~' ]]; then
                            current=0
                        elif (( current > 0 )); then
                            current=$((current - 1))
                        fi
                        ;;
                    '[B'|'[F'|'[4~')
                        if [[ "${sequence}" == '[F' || "${sequence}" == '[4~' ]]; then
                            current=$((${#suite_names[@]} - 1))
                        elif (( current < ${#suite_names[@]} - 1 )); then
                            current=$((current + 1))
                        fi
                        ;;
                esac
                ;;
            ' ')
                if (( current == 0 )); then
                    if (( ${#selected[@]} == ${#suite_paths[@]} )); then
                        selected=()
                    else
                        selected=()
                        for ((index = 1; index <= ${#suite_paths[@]}; index++)); do
                            selected+=("${index}")
                        done
                    fi
                else
                    updated=()
                    already_selected=false
                    for item in "${selected[@]}"; do
                        if [[ "${item}" == "${current}" ]]; then
                            already_selected=true
                        else
                            updated+=("${item}")
                        fi
                    done
                    if [[ "${already_selected}" == false ]]; then
                        updated+=("${current}")
                    fi
                    selected=("${updated[@]}")
                fi
                ;;
            a|A)
                selected=()
                for ((index = 1; index <= ${#suite_paths[@]}; index++)); do
                    selected+=("${index}")
                done
                ;;
            n|N)
                selected=()
                ;;
            '')
                if (( ${#selected[@]} > 0 )); then
                    break
                fi
                notice="Select at least one suite before starting."
                ;;
            q|Q)
                tui_restore_terminal
                trap - INT TERM
                log_info "Test selection cancelled"
                return 0
                ;;
            j)
                if (( current < ${#suite_names[@]} - 1 )); then
                    current=$((current + 1))
                fi
                ;;
            k)
                if (( current > 0 )); then
                    current=$((current - 1))
                fi
                ;;
        esac
    done

    tui_restore_terminal
    trap - INT TERM

    if (( ${#selected[@]} == ${#suite_paths[@]} )); then
        run_paths=("${suite_paths[@]}")
    else
        for ((index = 1; index <= ${#suite_paths[@]}; index++)); do
            for item in "${selected[@]}"; do
                if [[ "${item}" == "${index}" ]]; then
                    run_paths+=("${suite_paths[index - 1]}")
                    break
                fi
            done
        done
    fi

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
    trap '
        if [[ -s "${runner_pid_file}" ]]; then
            kill -INT "$(cat "${runner_pid_file}")" 2>/dev/null || true
        fi
        log_warn "Interrupt received; waiting for the test runner to save results..."
    ' INT TERM

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
            "${VENV_PYTHON}" - "${run_dir}/summary.json" 2>/dev/null <<'PY' || echo 2
import json
import sys

with open(sys.argv[1], encoding="utf-8") as summary_file:
    print(int(json.load(summary_file).get("exit_code", 2)))
PY
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
