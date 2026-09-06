"""
(C) COPYRIGHT 2026 - EXcellent TechStacks, All Rights Reserved.

Python Debugger Module: Helper script to communicate with C++ debugging utilities
for the debugger monitor.
"""

from editor import *

# Local Imports
from editor.widgets.QExitDialog import ErrorDialog


def show_error_message(message, cancel_text):
    error_message = ErrorDialog(
        title="Debugging Session Failure",
        message=message,
        cancel_text=cancel_text,
    )

    error_message.exec()


def handle_metrics(metrics: dict):
    """Callback function to process incoming metrics."""
    pid = metrics.get("pid")
    proc = metrics.get("process", {})
    sys_info = metrics.get("system", {})
    processor = metrics.get("processor", {})

    return pid, proc, sys_info, processor


def launch_monitor(executable_path: str, process_id: int) -> None:
    """
    Python API to launch DreamStudioProcessManager given the executable path and
    PID to launch the monitor by.
    """
    buffer = ""

    if not os.path.exists(executable_path):
        show_error_message(
            message="DreamStudio Process Manager is not found.",
            cancel_text="Ok",
        )
        return

    try:
        process = subprocess.Popen(
            [executable_path, str(process_id)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
        )
    except (OSError, FileNotFoundError) as exc:
        show_error_message(
            message=f"Failed to launch Process Manager: {exc}",
            cancel_text="Ok",
        )
        return

    try:
        depth = 0
        started = False
        in_string = False
        escape_next = False
        # Non-blocking readline with poll timeout to avoid hanging forever
        while True:
            if process.poll() is not None and not process.stdout:
                break
            line = process.stdout.readline()
            if line == "":
                if process.poll() is not None:
                    break
                continue
            buffer += line

            for ch in line:
                if escape_next:
                    escape_next = False
                    continue
                if ch == "\\" and in_string:
                    escape_next = True
                    continue
                if ch == '"':
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if ch == "{":
                    depth += 1
                    started = True
                elif ch == "}":
                    depth -= 1

            if started and depth <= 0:
                try:
                    payload = json.loads(buffer)
                    handle_metrics(payload)
                except json.JSONDecodeError:
                    pass
                buffer = ""
                started = False
                depth = 0
                in_string = False
                escape_next = False

    except KeyboardInterrupt:
        pass

    finally:
        try:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    pass
        except Exception:
            pass
