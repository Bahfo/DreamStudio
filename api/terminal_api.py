"""
TerminalAPI - Wraps terminal and shell emulator functionality.

Provides access to terminal sessions, output, and shell commands.
"""


class TerminalAPI:
    """API for interacting with the terminal."""

    def __init__(self, main_window):
        self._main = main_window

    def _terminal(self):
        return getattr(self._main, "terminalWidget", None)

    def toggleTerminal(self) -> None:
        """Toggle terminal panel visibility."""
        self._main.toggle_terminal()

    def isTerminalVisible(self) -> bool:
        """Check if the terminal panel is visible."""
        term = self._terminal()
        if term is None:
            return False
        return term.isVisible()

    def appendOutput(self, text: str) -> None:
        """Append text to the terminal output."""
        term = self._terminal()
        if term is not None and hasattr(term, "append_output"):
            term.append_output(text)

    def clearOutput(self) -> None:
        """Clear the terminal output."""
        term = self._terminal()
        if term is not None:
            output = getattr(term, "output", None)
            if output is not None and hasattr(output, "clear"):
                output.clear()

    def executeCommand(self, command: str) -> None:
        """Execute a command in the terminal."""
        from editor.terminal.commands_window import execute_command
        execute_command(command)

    def switchTab(self, index: int) -> None:
        """Switch to a terminal tab by index."""
        term = self._terminal()
        if term is not None and hasattr(term, "switch_tab"):
            term.switch_tab(index)

    def getTerminalWidget(self):
        """Get the raw terminal widget."""
        return self._terminal()
