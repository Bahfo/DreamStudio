"""
(C) COPYRIGHT 2026 - EXcellent TechStacks, All Rights Reserved.
Python Debugger Module:
"""

from editor import *

from editor.utils.notifications.notification_manager import get_notification_manager

logger = logging.getLogger(__name__)


def resolve_breakpoints(
    file_path: str, raw_line_numbers: set[int] | list[int]
) -> dict[int, int]:
    """Translates requested breakpoints inside a file into a valid executable Python lines."""
    # Syntax errors: Will be triggered to pause debugging (TODO to implement later)

    if not os.path.exists(file_path):
        get_notification_manager().add_error(
            "Debug Error",
            f"File not found for debugging: {file_path}",
            "Debugger",
        )
        return {}

    with open(file_path, "r", encoding="utf-8") as file:
        source_code = file.read()

    try:
        code_obj = compile(source_code, file_path, "exec")

        def _collect_executable_lines(code, acc: set) -> None:
            for _, _, line in code.co_lines():
                if line is not None and line > 0:
                    acc.add(line)
            for const in code.co_consts:
                if hasattr(const, "co_lines"):
                    _collect_executable_lines(const, acc)

        _lines: set[int] = set()
        _collect_executable_lines(code_obj, _lines)
        executable_lines = sorted(_lines)
    except SyntaxError:
        return {line: line for line in raw_line_numbers}
        # TODO: Implement a GUI fallback to tell user that a syntax error

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


def start_debugger(session: "DebugSession") -> None:
    """Initialize the debugging session."""
    logger.info(
        "Debug session started for %s with %d breakpoints",
        session.file_path,
        len(session.resolved_breakpoints),
    )
    get_notification_manager().add_info(
        "Debug Started",
        f"Debug session started: {os.path.basename(session.file_path)} "
        f"({len(session.resolved_breakpoints)} breakpoints)",
        "Debugger",
    )


class DebugSession(QObject):
    """Manages the lifecycle of a single debug session."""

    session_started = pyqtSignal()
    session_paused = pyqtSignal(int, str)
    session_ended = pyqtSignal()
    session_error = pyqtSignal(str)

    def __init__(self, file_path, breakpoints, main_window):
        super().__init__(main_window)

        self.file_path = file_path
        self.breakpoints = breakpoints
        self.main_window = main_window

        self.resolved_breakpoints = resolve_breakpoints(file_path, breakpoints)

        self._sorted_bp_lines = sorted(self.resolved_breakpoints.values())
        self._current_bp_index = -1

        self.target_editor = main_window.tab_editors.get_editor_for_path(file_path)

        self._process = None
        self._is_running = False


    def is_running(self):
        return self._is_running


    def start(self):
        """Start the debug session:"""
        if self._is_running:
            return

        start_debugger(self)
        self._is_running = True

        self.main_window.status_bar.set_debug_background()

        self.main_window.options_menu.debug_frame.show_at_default_position()
        self.main_window.options_menu.debug_frame.set_session(self)
        self.main_window.options_menu.debug_frame.enable_controls()

        self._set_debug_button_enabled(False)

        if self._sorted_bp_lines:
            self._current_bp_index = 0
            first_line = self._sorted_bp_lines[0]
            self.on_debugger_paused(first_line)

        self.session_started.emit()

    def stop(self):
        """Terminate the debug session and clean up all UI state."""
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=2)
            except Exception as exc:
                logger.warning("Error terminating debug process: %s", exc)
                get_notification_manager().add_warning(
                    "Debug Stop Error",
                    f"Error stopping debug process: {exc}",
                    "Debugger",
                )
        self._process = None
        self._is_running = False

        self._cleanup_ui()
        self.session_ended.emit()

    def restart(self):
        """Stop the current session and start a fresh one with the same file and breakpoints."""
        self.stop()
        self.start()


    def on_debugger_paused(self, line, frame_info=""):
        """Handle the debugger pausing at a given line."""
        if self.target_editor is None:
            return

        try:
            self.target_editor.set_execution_line_highlight(line)

            info = frame_info or f"Paused at line {line}"
            self.target_editor.show_debug_stack_frame(line, info)
            self.target_editor._update_debug_stack_position()
        except RuntimeError:
            self.stop()
            return

        self.session_paused.emit(line, info)


    def continue_execution(self):
        """Jump to the next breakpoint (same as step_over)."""
        self.step_over()

    def step_over(self):
        """Advance to the next breakpoint in the file."""
        if not self._sorted_bp_lines:
            return

        next_idx = self._current_bp_index + 1
        if next_idx >= len(self._sorted_bp_lines):
            next_idx = 0

        self._current_bp_index = next_idx
        line = self._sorted_bp_lines[next_idx]
        self.on_debugger_paused(line)

    def step_into(self):
        """Go back to the previous breakpoint in the file."""
        if not self._sorted_bp_lines:
            return

        prev_idx = self._current_bp_index - 1
        if prev_idx < 0:
            prev_idx = len(self._sorted_bp_lines) - 1

        self._current_bp_index = prev_idx
        line = self._sorted_bp_lines[prev_idx]
        self.on_debugger_paused(line)

    def step_out(self):
        """Step out of current function – for now treated as step_over."""
        self.step_over()


    def _cleanup_ui(self):
        """Reset all debug-related UI elements to their idle state."""
        if self.target_editor is not None:
            try:
                self.target_editor.clear_all_execution_highlights()
                self.target_editor.hide_debug_stack_frame()
            except RuntimeError:
                pass

        self.main_window.status_bar.reset_background()

        self.main_window.options_menu.debug_frame.disable_controls()
        self.main_window.options_menu.debug_frame.hide()
        self.main_window.options_menu.debug_frame.set_session(None)

        self._set_debug_button_enabled(True)

    def _set_debug_button_enabled(self, enabled):
        """Safely enable or disable the debug button in the options bar."""
        btn = getattr(self.main_window, "_debug_btn_ref", None)
        if btn is not None:
            btn.setEnabled(enabled)
