"""
(C) COPYRIGHT 2026 - EXcellent TechStacks, All Rights Reserved.

Python Debugger Module: Helper methods and classes to compute Python debugging
using the official Python Debugger.
"""

import bisect
import os


def resolve_breakpoints(
    file_path: str, raw_line_numbers: set[int] | list[int]
) -> dict[int, int]:
    """
    Translates requested breakpoints inside a file into a valid executable
    Python lines.

    :param file_path: Path to the Python file.
    :param raw_line_numbers: Line numbers where the user placed breakpoints.
    :return: Dictionary mapping {requested_line: actual_executable_line}
    """
    # Edge cases handled:
    # Comments and Blank Lines: Automatically skipped to forward line.
    # Breakpoints at EOF: Ignores and fails safely.
    # Syntax errors: Will be triggered to pause debugging (TODO to implement later)

    if not os.path.exists(file_path):
        pass  # TODO: Here must be a notification that file is not found.

    with open(file_path, "r", encoding="utf-8") as file:
        source_code = file.read()

    try:
        code_obj = compile(source_code, file_path, "exec")
        executable_lines = sorted(
            {
                line
                for _, _, line in code_obj.co_lines()
                if line is not None and line > 0
            }
        )
    except SyntaxError as e:
        # If can't compile -> return raw line as fallback
        return {line: line for line in raw_line_numbers}
        # TODO: Implement a GUI fallback to tell user that a syntax error
        # is shown.

    if not executable_lines:
        return {}

    resolved_map = {}

    for raw_line in raw_line_numbers:
        idx = bisect.bisect_left(executable_lines, raw_line)

        if idx < len(executable_lines):
            resolved_map[raw_line] = executable_lines[idx]
        else:
            pass

    return resolved_map
