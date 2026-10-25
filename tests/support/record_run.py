#!/usr/bin/env python3
"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Record a completed test run in the durable history and per-suite READMEs.

Only the standard library is used so the runner never depends on tools that
are not part of the project environment.
"""

import argparse
import json
import os
from pathlib import Path

from update_suite_readme import update_readme

VERDICTS = {
    0: "PASSED",
    1: "FAILED",
    2: "INFRASTRUCTURE ERROR",
    3: "INTERRUPTED",
    4: "NO TESTS",
}


def _load_summary(run_dir: Path) -> dict:
    path = run_dir / "summary.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _counts(summary: dict) -> dict:
    counts = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "blocked": 0,
        "errors": 0,
    }
    for key in counts:
        counts[key] = int(summary.get(key, 0) or 0)
    return counts


def _suite_names(suite_paths, summary: dict) -> list:
    names = [s.get("name") for s in summary.get("suites", []) if s.get("name")]
    if names:
        return names
    return [Path(p).name.removesuffix("_test") for p in suite_paths]


def _append_history(
    history_file: Path,
    run_id: str,
    timestamp: str,
    suite_names: list,
    git_rev: str,
    dirty: bool,
    duration: int,
    verdict: str,
    counts: dict,
) -> None:
    history_file.parent.mkdir(parents=True, exist_ok=True)
    if history_file.is_file():
        text = history_file.read_text(encoding="utf-8")
        # The initial placeholder is not a historical record; replace it once.
        text = text.replace(
            "*No runs recorded yet. Run `./tests/run_tests.sh` to execute tests.*",
            "",
        )
    else:
        text = "# DreamStudio IDE Test History\n\n## Test Run Index\n\n"

    dirty_marker = " (dirty)" if dirty else ""
    entry = (
        f"## {run_id}\n\n"
        f"- **Timestamp**: {timestamp}\n"
        f"- **Suites**: {', '.join(suite_names)}\n"
        f"- **Git**: {git_rev}{dirty_marker}\n"
        f"- **Duration**: {duration}s\n"
        f"- **Verdict**: {verdict}\n"
        f"- **Passed**: {counts['passed']} | "
        f"**Failed**: {counts['failed']} | "
        f"**Errors**: {counts['errors']} | "
        f"**Skipped**: {counts['skipped']} | "
        f"**Blocked**: {counts['blocked']}\n"
        f"- **Report**: `tests/reports/runs/{run_id}/report.md`\n"
        f"- **Console**: `tests/reports/runs/{run_id}/console.log`\n"
        f"- **Summary**: `tests/reports/runs/{run_id}/summary.json`\n\n"
    )
    history_file.write_text(text.rstrip() + "\n\n" + entry, encoding="utf-8")


def _write_machine_record(
    history_dir: Path,
    run_id: str,
    timestamp: str,
    suite_names: list,
    git_rev: str,
    dirty: bool,
    duration: int,
    exit_code: int,
    verdict: str,
    counts: dict,
) -> None:
    history_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "run_id": run_id,
        "timestamp": timestamp,
        "suites": suite_names,
        "git_revision": git_rev,
        "dirty": dirty,
        "duration_seconds": duration,
        "exit_code": exit_code,
        "verdict": verdict,
        "counts": counts,
    }
    (history_dir / f"{run_id}.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _update_readmes(
    suite_paths,
    summary: dict,
    run_dir: Path,
    run_id: str,
    timestamp: str,
) -> None:
    suites = {s.get("name"): s for s in summary.get("suites", [])}
    for suite_path in suite_paths:
        path = Path(suite_path)
        suite_name = path.name.removesuffix("_test")
        suite = suites.get(
            suite_name,
            {
                "name": suite_name,
                "verdict": summary.get("verdict", "NO RESULTS"),
                "tests": [],
            },
        )
        report_rel = os.path.relpath(run_dir / "report.md", path.resolve()).replace(os.sep, "/")
        update_readme(
            path / "README.md",
            suite,
            suite_name,
            run_id,
            timestamp,
            report_rel,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Record a test run")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--timestamp", required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--duration", type=int, required=True)
    parser.add_argument("--suite-path", action="append", required=True)
    parser.add_argument("--history-file", required=True)
    parser.add_argument("--history-dir", required=True)
    parser.add_argument("--git-rev", required=True)
    parser.add_argument("--dirty", action="store_true")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    summary = _load_summary(run_dir)
    counts = _counts(summary)
    verdict = summary.get("verdict") or VERDICTS.get(args.exit_code, "INFRASTRUCTURE ERROR")
    suite_names = _suite_names(args.suite_path, summary)

    _append_history(
        Path(args.history_file),
        args.run_id,
        args.timestamp,
        suite_names,
        args.git_rev,
        args.dirty,
        args.duration,
        verdict,
        counts,
    )
    _write_machine_record(
        Path(args.history_dir),
        args.run_id,
        args.timestamp,
        suite_names,
        args.git_rev,
        args.dirty,
        args.duration,
        args.exit_code,
        verdict,
        counts,
    )
    _update_readmes(
        args.suite_path,
        summary,
        run_dir.resolve(),
        args.run_id,
        args.timestamp,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
