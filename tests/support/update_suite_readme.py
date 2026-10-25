#!/usr/bin/env python3
"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Update a suite README with the latest run while preserving authored content.

Called by ``tests/run_tests.sh`` after each run. The suite README is a durable,
version-controlled summary, so this helper:

* replaces only the ``## Latest Run`` section,
* appends (never rewrites) rows to the ``## Historical Runs`` table,
* never duplicates a run ID,
* leaves scope, limitations, and reproduction sections untouched.
"""

import argparse
import json
from pathlib import Path

LATEST_HEADING = "## Latest Run"
HISTORY_HEADING = "## Historical Runs"

FALLBACK_DOC = """# {title}

## Overview
Test suite for {suite} functionality.

## Latest Run
{latest}

## Historical Runs

| Run ID | Timestamp | Verdict | Passed | Failed | Errors | Skipped | Blocked | Report |
|--------|-----------|---------|--------|--------|--------|---------|---------|--------|
{row}

## Scope & Limitations
- Test scope: TODO
- Known limitations: TODO
- Manual verification needed: TODO

## Failure Reproduction
```bash
./tests/run_tests.sh --suite {suite}
```
"""


def _latest_block(suite, run_id, timestamp, report_rel):
    """Render the latest-run Markdown block."""
    verdict = suite.get("verdict", "UNKNOWN")
    counts = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "blocked": 0,
        "error": 0,
    }
    for test in suite.get("tests", []):
        status = test.get("status")
        if status in counts:
            counts[status] += 1

    return (
        f"- **Run ID**: {run_id}\n"
        f"- **Timestamp**: {timestamp}\n"
        f"- **Verdict**: {verdict}\n"
        f"- **Passed**: {counts['passed']} | "
        f"**Failed**: {counts['failed']} | "
        f"**Errors**: {counts['error']} | "
        f"**Skipped**: {counts['skipped']} | "
        f"**Blocked**: {counts['blocked']}\n"
        f"- [Report]({report_rel})"
    )


def _history_row(suite, run_id, timestamp, report_rel):
    """Render one historical table row."""
    counts = {
        "passed": 0,
        "failed": 0,
        "error": 0,
        "skipped": 0,
        "blocked": 0,
    }
    for test in suite.get("tests", []):
        status = test.get("status")
        if status in counts:
            counts[status] += 1

    return (
        f"| {run_id} | {timestamp} | {suite.get('verdict', 'UNKNOWN')} | "
        f"{counts['passed']} | {counts['failed']} | {counts['error']} | "
        f"{counts['skipped']} | {counts['blocked']} | "
        f"[Report]({report_rel}) |"
    )


def _replace_section(text, heading, body):
    """Replace the body of *heading* up to the next level-2 heading."""
    lines = text.splitlines()
    try:
        start = lines.index(heading)
    except ValueError:
        return None

    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break

    before = lines[: start + 1]
    after = lines[end:]
    while after and not after[0].strip():
        after = after[1:]
    new_lines = before + [""] + body.splitlines() + [""]
    if after:
        new_lines += after
    return "\n".join(new_lines).rstrip() + "\n"


def _append_history_row(text, row, run_id):
    """Append *row* to the historical table, avoiding duplicates."""
    lines = text.splitlines()
    try:
        heading_index = lines.index(HISTORY_HEADING)
    except ValueError:
        return None

    if any(run_id in line for line in lines[heading_index:]):
        return text

    table_start = None
    separator = None
    for i in range(heading_index + 1, len(lines)):
        if lines[i].startswith("## "):
            break
        if lines[i].startswith("| Run ID"):
            table_start = i
        if table_start is not None and set(lines[i].replace("|", "").strip()) <= {
            "-",
            ":",
            " ",
        }:
            separator = i
            break

    if separator is None:
        insertion = heading_index + 1
        table_lines = [
            "",
            "| Run ID | Timestamp | Verdict | Passed | Failed | Errors | Skipped | Blocked | Report |",
            "|--------|-----------|---------|--------|--------|--------|---------|---------|--------|",
            row,
        ]
        return "\n".join(lines[:insertion] + table_lines + lines[insertion:]).rstrip() + "\n"

    return "\n".join(lines[: separator + 1] + [row] + lines[separator + 1 :]).rstrip() + "\n"


def update_readme(
    readme: Path,
    suite: dict,
    suite_name: str,
    run_id: str,
    timestamp: str,
    report_rel: str,
) -> None:
    """Apply latest-run and history updates to *readme*."""
    latest = _latest_block(suite, run_id, timestamp, report_rel)
    row = _history_row(suite, run_id, timestamp, report_rel)

    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
    else:
        text = FALLBACK_DOC.format(
            title=f"{suite_name.title()} Test Suite",
            suite=suite_name,
            latest=latest,
            row=row,
        )

    replaced = _replace_section(text, LATEST_HEADING, latest)
    if replaced is not None:
        text = replaced

    appended = _append_history_row(text, row, run_id)
    if appended is not None:
        text = appended

    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text(text.rstrip() + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Update a suite README")
    parser.add_argument("--readme", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--suite", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--timestamp", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    suite = next(
        (s for s in summary.get("suites", []) if s.get("name") == args.suite),
        {
            "name": args.suite,
            "verdict": "NO RESULTS",
            "tests": [],
        },
    )

    update_readme(
        Path(args.readme),
        suite,
        args.suite,
        args.run_id,
        args.timestamp,
        args.report,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
