"""
AnalyzerAPI - Wraps code complexity analysis functionality.

Provides access to Python code complexity analysis.
"""

from editor.texteditor.analyzer.complexity_analyzer import analyze_python_complexity


class AnalyzerAPI:
    """API for code complexity analysis."""

    def __init__(self, main_window):
        self._main = main_window

    def analyzeSource(self, source: str, file_path: str = None) -> dict:
        """Analyze the complexity of a Python source string."""
        return analyze_python_complexity(source, file_path)

    def analyzeCurrentFile(self) -> dict:
        """Analyze the complexity of the current editor content."""
        editor = self._main._get_current_editor()
        if editor is None:
            return {}
        source = editor.text()
        file_path = getattr(editor, "current_file_path", None)
        return analyze_python_complexity(source, file_path)

    def getResults(self) -> dict:
        """Get the last analysis results from the current editor."""
        editor = self._main._get_current_editor()
        if editor is None:
            return {}
        return getattr(editor, "_complexity_results", {}) or {}

    def showPopup(self) -> None:
        """Show the complexity popup at the info button."""
        editor = self._main._get_current_editor()
        if editor is not None:
            editor._show_complexity_popup()

    def runAnalysis(self) -> None:
        """Trigger complexity analysis on the current editor."""
        editor = self._main._get_current_editor()
        if editor is not None:
            editor._run_complexity_analysis()
