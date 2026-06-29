"""
MarketplaceAPI - Wraps ExtensionsTab functionality.

Provides access to the extension marketplace.
"""


class MarketplaceAPI:
    """API for the extensions marketplace."""

    def __init__(self, main_window):
        self._main = main_window

    def _marketplace(self):
        return getattr(self._main, "marketplace", None)

    def filterExtensions(self, query: str) -> None:
        """Filter marketplace extensions by a search query."""
        mp = self._marketplace()
        if mp is not None and hasattr(mp, "filter_marketplace"):
            mp.filter_marketplace(query)

    def openMarketplace(self) -> None:
        """Open the marketplace panel."""
        self._main.open_tools_panel("Marketplace")

    def getWidget(self):
        """Get the raw marketplace widget."""
        return self._marketplace()
