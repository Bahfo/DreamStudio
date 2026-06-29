"""
StatusBarAPI - Wraps StatusBar functionality.

Provides access to status bar information and bootstrap status.
"""


class StatusBarAPI:
    """API for the status bar."""

    def __init__(self, main_window):
        self._main = main_window

    def _bar(self):
        return getattr(self._main, "status_bar", None)

    def setZoomLevel(self, level: int) -> None:
        """Set the text zoom level."""
        bar = self._bar()
        if bar is not None:
            bar.text_zoom_toggle(level)

    def onZoomToggle(self, zoom_text: str) -> None:
        """Handle zoom toggle from status bar."""
        bar = self._bar()
        if bar is not None:
            bar.on_zoom_toggle(zoom_text)

    def setBootstrapStatus(self, step_name: str, message: str) -> None:
        """Update the bootstrap progress status."""
        bar = self._bar()
        if bar is not None:
            bar.set_bootstrap_status(step_name, message)

    def setBootstrapFinished(self, success: bool) -> None:
        """Mark bootstrap as finished."""
        bar = self._bar()
        if bar is not None:
            bar.set_bootstrap_finished(success)

    def showBootstrapDetails(self) -> None:
        """Show the bootstrap detail menu."""
        bar = self._bar()
        if bar is not None:
            bar.show_bootstrap_details()

    def clearBootstrapLog(self) -> None:
        """Clear the bootstrap log."""
        bar = self._bar()
        if bar is not None:
            bar.clear_bootstrap_log()

    def getWidget(self):
        """Get the raw status bar widget."""
        return self._bar()
