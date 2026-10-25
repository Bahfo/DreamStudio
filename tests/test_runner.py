#!/usr/bin/env python3
# ruff: noqa: BLE001, S110
"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Main test runner with TUI progress display and structured reporting.

``run_tests.sh`` invokes this module once per selected set of suites. The
runner deliberately treats pytest's JUnit XML as the authoritative source of
results; terminal output is only used for live progress. This keeps counts
honest even when traceback text contains lines that look like test results.
"""

import argparse
import atexit
import json
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

#: Exit codes used by pytest itself (see pytest documentation).
PYTEST_OK = 0
PYTEST_TESTS_FAILED = 1
PYTEST_INTERRUPTED = 2
PYTEST_INTERNAL_ERROR = 3
PYTEST_USAGE_ERROR = 4
PYTEST_NO_TESTS = 5

#: Runner exit codes (mirrored in run_tests.sh and TESTING_STANDARDS.md).
EXIT_PASSED = 0
EXIT_FAILED = 1
EXIT_INFRASTRUCTURE = 2
EXIT_INTERRUPTED = 3
EXIT_NO_TESTS = 4

_VERBOSE_RE = re.compile(
    r"^(?P<nodeid>[^\s]+::[^\s]+)\s+"
    r"(?P<status>PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)\b"
    r"(?:\s+\[[^\]]*\])?"
)

_LINE_RE = re.compile(r"(?P<file>[^\s:]+\.py):(?P<line>\d+):")

_ACTIVE_PROCESS: subprocess.Popen | None = None
_INTERRUPTED = False


@dataclass
class TestResult:
    """Individual test result."""

    name: str
    status: str  # passed, failed, skipped, blocked, error
    duration: float
    file: str
    line: int
    message: str = ""
    traceback: str = ""


@dataclass
class SuiteResult:
    """Result for a test suite."""

    name: str
    path: str
    tests: list[TestResult]
    start_time: float
    end_time: float
    exit_code: int
    verdict: str = ""
    log_tail: str = ""


@dataclass
class RunSummary:
    """Overall run summary."""

    run_id: str
    timestamp: str
    suites: list[SuiteResult]
    total_tests: int
    passed: int
    failed: int
    skipped: int
    blocked: int
    errors: int
    duration: float
    exit_code: int
    verdict: str


class ProgressDisplay:
    """TUI progress display for test execution.

    On a terminal the display redraws in place. When stdout is redirected
    (for example through ``tee`` in ``run_tests.sh``) the runner emits one
    line per test instead, which keeps console logs readable and still gives
    live progress.
    """

    def __init__(self, suites: list[str]):
        self.suites = suites
        self.current_suite_idx = 0
        self.suite_status = {s: "PENDING" for s in suites}
        self.suite_counts = {
            s: {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "blocked": 0,
                "error": 0,
            }
            for s in suites
        }
        self.current_test = ""
        self.last_failure = None
        self.lock = threading.RLock()
        self.running = True
        self.start_time = time.time()
        self.is_tty = sys.stdout.isatty()

    def set_current_suite(self, suite: str, status: str = "RUNNING"):
        with self.lock:
            self.suite_status[suite] = status
            if suite in self.suites:
                self.current_suite_idx = self.suites.index(suite)

    def record_result(self, suite: str, status: str):
        with self.lock:
            counts = self.suite_counts.setdefault(
                suite,
                {
                    "passed": 0,
                    "failed": 0,
                    "skipped": 0,
                    "blocked": 0,
                    "error": 0,
                },
            )
            key = status if status in counts else "error"
            counts[key] += 1

    def set_suite_counts(self, suite: str, counts: dict):
        with self.lock:
            self.suite_counts[suite] = {
                key: int(counts.get(key, 0)) for key in ("passed", "failed", "skipped", "blocked", "error")
            }

    def totals(self) -> dict:
        with self.lock:
            totals = {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "blocked": 0,
                "error": 0,
            }
            for counts in self.suite_counts.values():
                for key in totals:
                    totals[key] += counts.get(key, 0)
            return totals

    def set_current_test(self, test_name: str):
        with self.lock:
            self.current_test = test_name

    def record_failure(self, test_name: str, message: str):
        with self.lock:
            self.last_failure = (test_name, message)

    def render(self) -> str:
        with self.lock:
            elapsed = time.time() - self.start_time
            totals = self.totals()
            lines = []
            lines.append("DreamStudio Test Runner")
            lines.append("────────────────────────────────────────")

            for i, suite in enumerate(self.suites):
                status = self.suite_status[suite]
                prefix = f"[{i + 1}/{len(self.suites)}]"
                marker = "▶" if i == self.current_suite_idx else " "
                lines.append(f"{marker} {prefix} {suite:<20} {status}")

            lines.append("")
            current = self.suites[self.current_suite_idx] if self.suites else "N/A"
            lines.append(f"Current suite: {current}")
            lines.append(f"Elapsed: {elapsed:.1f}s")
            lines.append(
                "Passed: {passed}  Failed: {failed}  Skipped: {skipped}  "
                "Blocked: {blocked}  Errors: {error}".format(**totals)
            )
            lines.append("")

            if self.current_test:
                lines.append(f"Running: {self.current_test}")

            if self.last_failure:
                lines.append("")
                lines.append("Last Failure:")
                lines.append(f"  {self.last_failure[0]}")
                lines.append(f"  {self.last_failure[1][:80]}")

            return "\n".join(lines)

    def clear_screen(self):
        if self.is_tty:
            sys.stdout.write("\033[2J\033[H")

    def update(self):
        if self.is_tty:
            self.clear_screen()
            sys.stdout.write(self.render())
            sys.stdout.flush()

    def announce_result(self, suite: str, nodeid: str, status: str):
        """Emit live progress for a single test."""
        if not self.is_tty:
            print(f"  [{suite}] {status.upper():<8} {nodeid}", flush=True)


def _status_from_junit(case: ET.Element) -> str:
    """Return the runner status for a JUnit ``testcase`` element."""
    if case.find("failure") is not None:
        return "failed"
    if case.find("error") is not None:
        return "error"
    skipped = case.find("skipped")
    if skipped is not None:
        message = (skipped.get("message") or "").strip().lower()
        if message.startswith("blocked:"):
            return "blocked"
        return "skipped"
    return "passed"


def _infer_module_file(classname: str, project_root: Path) -> str:
    """Infer a test module path from a JUnit ``classname``."""
    if not classname:
        return ""
    parts = classname.split(".")
    for end in range(len(parts), 0, -1):
        candidate = Path(*parts[:end]).with_suffix(".py")
        if (project_root / candidate).is_file():
            return candidate.as_posix()
    return classname.replace(".", "/")


def _display_name(classname: str, name: str, module_file: str) -> str:
    """Build a pytest-style node id for a JUnit ``testcase``."""
    if not module_file:
        return name
    prefix_parts = Path(module_file).with_suffix("").parts
    class_parts = classname.split(".") if classname else []
    if class_parts[: len(prefix_parts)] == list(prefix_parts):
        class_parts = class_parts[len(prefix_parts) :]
    if class_parts:
        return "::".join([module_file, *class_parts, name])
    return f"{module_file}::{name}"


def _extract_line(text: str) -> int:
    """Extract the first source line referenced in a traceback."""
    match = _LINE_RE.search(text or "")
    if match:
        try:
            return int(match.group("line"))
        except ValueError:
            return 0
    return 0


def parse_junit(junit_path: Path, suite_name: str, project_root: Path) -> list[TestResult]:
    """Parse a pytest JUnit XML file into ``TestResult`` objects."""
    if not junit_path.is_file():
        return []

    try:
        root = ET.parse(junit_path).getroot()
    except ET.ParseError:
        return []

    results: list[TestResult] = []
    for case in root.iter("testcase"):
        status = _status_from_junit(case)
        classname = case.get("classname", "")
        name = case.get("name", "").strip()
        if not name:
            # pytest emits a nameless placeholder testcase when a test is
            # interrupted mid-execution; it is not a real result.
            continue
        module_file = _infer_module_file(classname, project_root)
        display = _display_name(classname, name, module_file)

        try:
            duration = float(case.get("time", "0") or 0)
        except ValueError:
            duration = 0.0

        message = ""
        traceback_text = ""
        for tag in ("failure", "error", "skipped"):
            node = case.find(tag)
            if node is None:
                continue
            message = (node.get("message") or "").strip()
            traceback_text = (node.text or "").strip()
            if not message and traceback_text:
                message = traceback_text.splitlines()[0]
            break

        results.append(
            TestResult(
                name=display,
                status=status,
                duration=duration,
                file=module_file,
                line=_extract_line(traceback_text),
                message=message,
                traceback=traceback_text,
            )
        )

    return results


def _live_result(nodeid: str, status: str) -> TestResult:
    """Create a progress-only result from a verbose pytest line."""
    mapping = {
        "PASSED": "passed",
        "FAILED": "failed",
        "SKIPPED": "skipped",
        "ERROR": "error",
        "XFAIL": "skipped",
        "XPASS": "passed",
    }
    file_part = nodeid.split("::", 1)[0]
    return TestResult(
        name=nodeid,
        status=mapping.get(status, "error"),
        duration=0.0,
        file=file_part,
        line=0,
    )


def _pump_output(stream, output_queue: "queue.Queue[str | None]") -> None:
    """Forward subprocess output to *output_queue* until EOF."""
    try:
        for line in stream:
            output_queue.put(line)
    except Exception:
        pass
    finally:
        output_queue.put(None)


def _terminate_process(process: subprocess.Popen) -> None:
    """Ask pytest to stop, escalating to terminate/kill if needed."""
    if process.poll() is not None:
        return
    try:
        process.send_signal(signal.SIGINT)
    except Exception:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass


def run_pytest_suite(
    suite_path: Path,
    run_dir: Path,
    progress: ProgressDisplay,
    suite_name: str,
) -> SuiteResult:
    """Run pytest for a single suite and collect authoritative results."""
    global _ACTIVE_PROCESS

    start_time = time.time()
    junit_path = run_dir / f"junit_{suite_name}.xml"
    pytest_log_path = run_dir / "pytest.log"

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(suite_path),
        "-p",
        "no:cacheprovider",
        "-v",
        "--tb=short",
        "--color=no",
        "--junitxml",
        str(junit_path),
        "-o",
        "junit_family=xunit2",
    ]

    env = os.environ.copy()
    env["QT_QPA_PLATFORM"] = "offscreen"
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    env.setdefault("PYTEST_CACHE_DIR", str(run_dir / ".pytest_cache"))

    progress.set_current_suite(suite_name, "RUNNING")

    tests: list[TestResult] = []
    log_tail_lines = []

    with open(pytest_log_path, "w", encoding="utf-8") as pytest_log:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            cwd=str(PROJECT_ROOT),
        )
        _ACTIVE_PROCESS = process

        try:
            assert process.stdout is not None
            output_queue: queue.Queue[str | None] = queue.Queue()
            reader = threading.Thread(
                target=_pump_output,
                args=(process.stdout, output_queue),
                daemon=True,
                name=f"pytest-output-{suite_name}",
            )
            reader.start()

            # A descendant process can inherit pytest's stdout and keep the
            # pipe open after pytest itself exits. Drain with a bounded grace
            # period so that run completion never depends on pipe EOF.
            drain_deadline: float | None = None
            while True:
                try:
                    line = output_queue.get(timeout=0.1)
                except queue.Empty:
                    if _INTERRUPTED and process.poll() is None:
                        _terminate_process(process)
                        break
                    if process.poll() is not None:
                        if drain_deadline is None:
                            drain_deadline = time.time() + 1.0
                        elif time.time() >= drain_deadline:
                            break
                    continue

                if line is None:
                    break

                pytest_log.write(line)
                pytest_log.flush()

                stripped = line.rstrip()
                if stripped:
                    log_tail_lines.append(stripped)
                    del log_tail_lines[:-200]

                if _INTERRUPTED and process.poll() is None:
                    _terminate_process(process)
                    break

                match = _VERBOSE_RE.match(stripped)
                if not match:
                    continue

                nodeid = match.group("nodeid")
                raw_status = match.group("status")
                result = _live_result(nodeid, raw_status)

                # Only count each node once during live progress.
                if not any(t.name == nodeid for t in tests):
                    tests.append(result)
                    progress.record_result(suite_name, result.status)
                    if result.status in ("failed", "error"):
                        progress.record_failure(nodeid, raw_status)
                    progress.set_current_test(nodeid)
                    progress.announce_result(suite_name, nodeid, result.status)
                    progress.update()

            process.wait()
            reader.join(timeout=1.0)
        finally:
            if process.poll() is None:
                _terminate_process(process)
            try:
                process.stdout.close()
            except Exception:
                pass
            _ACTIVE_PROCESS = None

    end_time = time.time()
    exit_code = process.returncode if process.returncode is not None else 130

    junit_tests = parse_junit(junit_path, suite_name, PROJECT_ROOT)
    if junit_tests:
        tests = junit_tests
    elif _INTERRUPTED or exit_code == PYTEST_NO_TESTS:
        # A partial interrupt or an empty suite has no artificial results to
        # report. The suite verdict carries the meaning instead.
        tests = []
    elif not tests:
        tests = [
            TestResult(
                name=f"{suite_name}::<no results>",
                status="error",
                duration=end_time - start_time,
                file=str(suite_path),
                line=0,
                message="pytest produced no JUnit results",
            )
        ]

    if _INTERRUPTED:
        verdict = "INTERRUPTED"
    elif exit_code == PYTEST_OK:
        verdict = "PASSED"
    elif exit_code == PYTEST_TESTS_FAILED:
        verdict = "FAILED"
    elif exit_code == PYTEST_NO_TESTS:
        verdict = "NO TESTS"
    else:
        verdict = "INFRASTRUCTURE ERROR"

    counts = {
        status: sum(1 for t in tests if t.status == status)
        for status in ("passed", "failed", "skipped", "blocked", "error")
    }
    progress.set_suite_counts(suite_name, counts)
    progress.set_current_suite(suite_name, verdict)
    progress.update()

    log_tail = ""
    if verdict in ("INFRASTRUCTURE ERROR", "NO TESTS") or not tests:
        log_tail = "\n".join(log_tail_lines[-80:])

    return SuiteResult(
        name=suite_name,
        path=str(suite_path),
        tests=tests,
        start_time=start_time,
        end_time=end_time,
        exit_code=exit_code,
        verdict=verdict,
        log_tail=log_tail,
    )


def generate_report(run_dir: Path, summary: RunSummary) -> str:
    """Generate human-readable report.md."""
    lines = []
    lines.append(f"# Test Run Report: {summary.run_id}")
    lines.append("")
    lines.append(f"**Timestamp**: {summary.timestamp}")
    lines.append(f"**Duration**: {summary.duration:.2f}s")
    lines.append(f"**Overall Verdict**: {summary.verdict}")
    lines.append(f"**Exit Code**: {summary.exit_code}")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Total Tests | {summary.total_tests} |")
    lines.append(f"| Passed | {summary.passed} |")
    lines.append(f"| Failed | {summary.failed} |")
    lines.append(f"| Errors | {summary.errors} |")
    lines.append(f"| Skipped | {summary.skipped} |")
    lines.append(f"| Blocked | {summary.blocked} |")
    lines.append("")

    lines.append("## Suite Results")
    lines.append("")

    for suite in summary.suites:
        suite_passed = sum(1 for t in suite.tests if t.status == "passed")
        suite_failed = sum(1 for t in suite.tests if t.status == "failed")
        suite_errors = sum(1 for t in suite.tests if t.status == "error")
        suite_skipped = sum(1 for t in suite.tests if t.status == "skipped")
        suite_blocked = sum(1 for t in suite.tests if t.status == "blocked")
        suite_duration = suite.end_time - suite.start_time

        lines.append(f"### {suite.name} ({suite.verdict})")
        lines.append("")
        lines.append(f"- **Path**: `{suite.path}`")
        lines.append(f"- **Duration**: {suite_duration:.2f}s")
        lines.append(
            f"- **Tests**: {len(suite.tests)} "
            f"(Passed: {suite_passed}, Failed: {suite_failed}, "
            f"Errors: {suite_errors}, Skipped: {suite_skipped}, "
            f"Blocked: {suite_blocked})"
        )
        lines.append(f"- **pytest Exit Code**: {suite.exit_code}")
        lines.append("")

        failures = [t for t in suite.tests if t.status in ("failed", "error", "blocked")]
        if failures:
            lines.append("#### Failures & Blockers")
            lines.append("")
            for test in failures:
                lines.append(
                    f"- **{test.name}** (`{test.file}`"
                    + (f":{test.line}" if test.line else "")
                    + f") — `{test.status}`"
                )
                if test.message:
                    lines.append(f"  - Message: {test.message}")
                if test.traceback:
                    lines.append("  ```")
                    for trace_line in test.traceback.splitlines()[:25]:
                        lines.append(f"  {trace_line}")
                    lines.append("  ```")
            lines.append("")

        if suite.log_tail:
            lines.append("#### pytest Output (tail)")
            lines.append("")
            lines.append("```")
            lines.extend(suite.log_tail.splitlines()[-60:])
            lines.append("```")
            lines.append("")

    lines.append("## Artifacts")
    lines.append("")
    lines.append("- **Console Log**: `console.log`")
    lines.append("- **Summary JSON**: `summary.json`")
    lines.append("- **Environment**: `environment.txt`")
    for suite in summary.suites:
        lines.append(f"- **JUnit XML ({suite.name})**: " f"`{suite.name}/junit_{suite.name}.xml`")
        lines.append(f"- **pytest Log ({suite.name})**: `{suite.name}/pytest.log`")

    report = "\n".join(lines) + "\n"
    report_path = run_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")
    return str(report_path)


def generate_summary_json(run_dir: Path, summary: RunSummary) -> str:
    """Generate machine-readable summary.json."""
    data = asdict(summary)
    data["suites"] = []
    for suite in summary.suites:
        suite_dict = asdict(suite)
        suite_dict["tests"] = [asdict(t) for t in suite.tests]
        data["suites"].append(suite_dict)

    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return str(summary_path)


def _overall_exit_code(suites: list[SuiteResult], interrupted: bool) -> int:
    """Classify the run honestly using the documented exit codes."""
    if interrupted or any(s.verdict == "INTERRUPTED" for s in suites):
        return EXIT_INTERRUPTED

    if any(s.verdict == "INFRASTRUCTURE ERROR" for s in suites):
        return EXIT_INFRASTRUCTURE

    total_tests = sum(len(s.tests) for s in suites)
    if total_tests == 0 or all(s.verdict == "NO TESTS" for s in suites):
        return EXIT_NO_TESTS

    if any(t.status in ("failed", "error") for s in suites for t in s.tests):
        return EXIT_FAILED

    return EXIT_PASSED


def _verdict_for(exit_code: int) -> str:
    return {
        EXIT_PASSED: "PASSED",
        EXIT_FAILED: "FAILED",
        EXIT_INFRASTRUCTURE: "INFRASTRUCTURE ERROR",
        EXIT_INTERRUPTED: "INTERRUPTED",
        EXIT_NO_TESTS: "NO TESTS",
    }.get(exit_code, "INFRASTRUCTURE ERROR")


def _handle_signal(signum, frame):
    """Mark the run interrupted and stop the active pytest process."""
    global _INTERRUPTED
    _INTERRUPTED = True
    process = _ACTIVE_PROCESS
    if process is not None and process.poll() is None:
        try:
            process.send_signal(signal.SIGINT)
        except Exception:
            pass
    try:
        print("\nInterrupted — saving partial results...", flush=True)
    except OSError:
        # The console consumer may already have exited; results are persisted
        # to files regardless.
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="DreamStudio Test Runner")
    parser.add_argument("--run-id", required=True, help="Unique run identifier")
    parser.add_argument("--run-dir", required=True, help="Directory for run artifacts")
    parser.add_argument("--suites", nargs="+", required=True, help="Suite paths to run")
    args = parser.parse_args()

    run_id = args.run_id
    run_dir = Path(args.run_dir)
    suite_paths = [Path(p) for p in args.suites]
    suite_names = [p.name.removesuffix("_test") for p in suite_paths]

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    run_dir.mkdir(parents=True, exist_ok=True)

    # ``run_tests.sh`` forwards signals received only by the shell to this
    # process using this file. It lives in the per-run directory, which is
    # never reused.
    pid_file = run_dir / "runner.pid"
    pid_file.write_text(f"{os.getpid()}\n", encoding="utf-8")
    atexit.register(pid_file.unlink, missing_ok=True)

    progress = ProgressDisplay(suite_names)
    progress.update()

    all_suite_results: list[SuiteResult] = []

    for suite_path, suite_name in zip(suite_paths, suite_names):
        if _INTERRUPTED:
            break

        if not suite_path.exists():
            print(f"Suite path not found: {suite_path}", flush=True)
            all_suite_results.append(
                SuiteResult(
                    name=suite_name,
                    path=str(suite_path),
                    tests=[],
                    start_time=time.time(),
                    end_time=time.time(),
                    exit_code=PYTEST_USAGE_ERROR,
                    verdict="INFRASTRUCTURE ERROR",
                    log_tail=f"Suite path not found: {suite_path}",
                )
            )
            continue

        suite_run_dir = run_dir / suite_name
        suite_run_dir.mkdir(parents=True, exist_ok=True)

        try:
            result = run_pytest_suite(suite_path, suite_run_dir, progress, suite_name)
            all_suite_results.append(result)
        except Exception as exc:
            import traceback

            print(f"Error running suite {suite_name}: {exc}", flush=True)
            traceback.print_exc()
            all_suite_results.append(
                SuiteResult(
                    name=suite_name,
                    path=str(suite_path),
                    tests=[],
                    start_time=time.time(),
                    end_time=time.time(),
                    exit_code=EXIT_INFRASTRUCTURE,
                    verdict="INFRASTRUCTURE ERROR",
                    log_tail=str(exc),
                )
            )

    total_tests = sum(len(s.tests) for s in all_suite_results)
    passed = sum(1 for s in all_suite_results for t in s.tests if t.status == "passed")
    failed = sum(1 for s in all_suite_results for t in s.tests if t.status == "failed")
    skipped = sum(1 for s in all_suite_results for t in s.tests if t.status == "skipped")
    blocked = sum(1 for s in all_suite_results for t in s.tests if t.status == "blocked")
    errors = sum(1 for s in all_suite_results for t in s.tests if t.status == "error")

    overall_exit_code = _overall_exit_code(all_suite_results, _INTERRUPTED)

    summary = RunSummary(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        suites=all_suite_results,
        total_tests=total_tests,
        passed=passed,
        failed=failed,
        skipped=skipped,
        blocked=blocked,
        errors=errors,
        duration=time.time() - progress.start_time,
        exit_code=overall_exit_code,
        verdict=_verdict_for(overall_exit_code),
    )

    generate_report(run_dir, summary)
    generate_summary_json(run_dir, summary)

    progress.clear_screen()
    print(progress.render())
    print()
    print(f"Run complete. Verdict: {summary.verdict} " f"(exit code {overall_exit_code})")
    print(f"Report: {run_dir}/report.md")
    print(f"Summary: {run_dir}/summary.json")

    if _INTERRUPTED:
        return EXIT_INTERRUPTED
    return overall_exit_code


if __name__ == "__main__":
    sys.exit(main())
