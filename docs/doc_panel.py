"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Documentation window displayed via Help -> Documentation.
"""

from dataclasses import dataclass

from editor import *


@dataclass
class DocPage:
    """One documentation page.

    Attributes:
        number: Ordering prefix parsed from the file name.
        title: Human-readable title shown in the navigation.
        path: Absolute path of the markdown source file.
    """

    number: int
    title: str
    path: str


class VerticalTabBar(QTabBar):
    """Vertical tab bar with horizontal text.

    The bar is placed on the west side so tabs are stacked
    vertically. Qt would normally draw the text rotated 90
    degrees for ``West``; this class re-implements ``paintEvent``
    to keep the label horizontal while preserving the vertical
    layout and ensuring the text is fully visible.
    """

    def tabSizeHint(self, index: int) -> QSize:
        """Return size for each tab.

        Width is the bar thickness (must fit the text width),
        height is the tab height when stacked vertically.

        Args:
            index: Tab index.

        Returns:
            Size for the tab.
        """
        text = self.tabText(index)
        fm = self.fontMetrics()
        text_width = fm.horizontalAdvance(text) if text else 0
        width = max(180, text_width + 24)
        return QSize(width, 40)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """Paint tabs with horizontal text.

        Draws the tab shape via the style (so QSS still applies)
        and then draws the text horizontally centered with
        ``QPainter`` to avoid the vertical rotation and the
        clipping caused by the transpose/rotate approach.

        Args:
            event: Paint event.
        """
        painter = QStylePainter(self)
        option = QStyleOptionTab()
        for index in range(self.count()):
            self.initStyleOption(option, index)

            painter.drawControl(QStyle.ControlElement.CE_TabBarTabShape, option)
            rect = self.tabRect(index)
            if rect.isNull():
                continue
            painter.save()

            color = option.palette.color(QPalette.ColorRole.WindowText)

            if not color.isValid():
                color = QColor("#FFFFFF")
            painter.setPen(color)

            painter.drawText(
                rect,
                int(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter),
                self.tabText(index),
            )
            painter.restore()


class DocumentationWindow(QWidget):
    """Documentation viewer embedded as an editor tab.

    Pages are discovered from ``docs/<number>_<slug>.md`` and shown in a
    west-side navigation next to a styled reader. Content colours are
    derived from the active palette, so the reader follows every IDE
    theme without per-theme stylesheets.

    Attributes:
        tabs: Main tab widget holding documentation pages.
        pages: Discovered :class:`DocPage` entries in display order.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the documentation window.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)
        self.pages: list[DocPage] = []
        self._browsers: list = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_header())

        self.tabs = QTabWidget(self)
        self.tabs.setTabBar(VerticalTabBar())
        self.tabs.setTabPosition(QTabWidget.TabPosition.West)
        layout.addWidget(self.tabs, 1)

        self._load_pages()
        self._apply_content_theme()

    def _build_header(self) -> QWidget:
        """Create the title bar with search and page counter."""
        header = QFrame(self)
        header.setObjectName("DocsHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)
        header_layout.setSpacing(8)

        title = QLabel("Documentation", header)
        title.setObjectName("DocsTitle")
        header_layout.addWidget(title)

        header_layout.addStretch(1)

        self._search = QLineEdit(header)
        self._search.setObjectName("DocsSearch")
        self._search.setPlaceholderText("Search pages…  (Enter: find in page)")
        self._search.setClearButtonEnabled(True)
        self._search.setFixedWidth(260)
        self._search.textChanged.connect(self.set_search)
        self._search.returnPressed.connect(self._find_next_in_page)
        header_layout.addWidget(self._search)

        self._counter = QLabel(header)
        self._counter.setObjectName("DocsCounter")
        header_layout.addWidget(self._counter)

        return header

    @staticmethod
    def _page_title(path) -> str:
        """Derive a display title from a ``<number>_<slug>.md`` file name."""
        stem = path.stem
        parts = stem.split("_", 1)
        slug = parts[1] if len(parts) == 2 else stem
        small = {"of", "and", "the", "for", "in", "on", "to", "a"}
        words = []
        for chunk in slug.split("_"):
            spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", chunk)
            words.extend(spaced.split(" "))
        titled = [
            word if index and word.lower() in small else word.capitalize()
            for index, word in enumerate(w for w in words if w)
        ]
        return " ".join(titled)

    @staticmethod
    def _page_number(path) -> int:
        """Derive the ordering number from a ``<number>_<slug>.md`` name."""
        try:
            return int(path.stem.split("_", 1)[0])
        except (ValueError, IndexError):
            return 1_000_000

    def _load_pages(self) -> None:
        """Discover markdown pages and build one reader tab each."""
        script_dir = Path(__file__).parent
        candidates = sorted(
            (
                p
                for p in script_dir.iterdir()
                if p.is_file() and p.suffix == ".md"
            ),
            key=lambda p: (self._page_number(p), p.name),
        )
        for path in candidates:
            page = DocPage(
                number=self._page_number(path),
                title=self._page_title(path),
                path=str(path),
            )
            browser = QTextBrowser(self.tabs)
            browser.setObjectName("DocsContent")
            browser.setOpenExternalLinks(True)
            browser.setMarkdown(self.open_markdown_file(page.path))
            browser.setToolTip(page.title)
            self.pages.append(page)
            self._browsers.append(browser)
            self.tabs.addTab(browser, page.title)
        self._update_counter()

    def _content_stylesheet(self) -> str:
        """Build the reader stylesheet from the active palette colors."""
        palette = self.palette()
        base = palette.color(QPalette.ColorRole.Base).name()
        text = palette.color(QPalette.ColorRole.Text).name()
        window = palette.color(QPalette.ColorRole.Window).name()
        mid = palette.color(QPalette.ColorRole.Mid).name()
        link = palette.color(QPalette.ColorRole.Link).name()
        highlight = palette.color(QPalette.ColorRole.Highlight).name()
        return (
            f"body {{ color: {text}; line-height: 1.55; }}"
            f"h1, h2 {{ color: {text}; margin-top: 0.6em; }}"
            f"h1 {{ font-size: x-large; border-bottom: 1px solid {mid}; "
            f"padding-bottom: 6px; }}"
            f"h2 {{ font-size: large; }}"
            f"h3 {{ font-size: medium; }}"
            f"p, li {{ margin-top: 0.35em; margin-bottom: 0.35em; }}"
            f"a {{ color: {link}; text-decoration: none; }}"
            f"code {{ background-color: {window}; padding: 1px 5px; "
            f"border: 1px solid {mid}; border-radius: 3px; }}"
            f"pre {{ background-color: {window}; border: 1px solid {mid}; "
            f"border-radius: 6px; padding: 10px 12px; }}"
            f"pre code {{ background-color: transparent; border: none; padding: 0; }}"
            f"blockquote {{ color: {text}; border-left: 3px solid {highlight}; "
            f"margin-left: 0; padding-left: 12px; }}"
            f"table {{ border-collapse: collapse; margin: 0.8em 0; }}"
            f"th, td {{ border: 1px solid {mid}; padding: 6px 10px; }}"
            f"th {{ background-color: {window}; }}"
            f"hr {{ border: none; border-top: 1px solid {mid}; }}"
            f"img {{ max-width: 100%; }}"
        )

    def _apply_content_theme(self) -> None:
        """Restyle every reader page from the active palette."""
        stylesheet = self._content_stylesheet()
        for browser in self._browsers:
            try:
                browser.document().setDefaultStyleSheet(stylesheet)
                browser.reload()
            except Exception:
                pass

    def changeEvent(self, event) -> None:
        """Re-theme the reader when the application palette changes."""
        if event.type() in (
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        ):
            self._apply_content_theme()
        super().changeEvent(event)

    def page_count(self) -> int:
        """Return the number of discovered documentation pages."""
        return len(self.pages)

    def current_page(self) -> int:
        """Return the index of the visible page."""
        return self.tabs.currentIndex()

    def show_page(self, index: int) -> None:
        """Show the page at *index* when it exists and is visible."""
        if 0 <= index < self.tabs.count():
            self.tabs.setCurrentIndex(index)

    def set_search(self, text: str) -> None:
        """Filter navigation tabs by title substring (case-insensitive)."""
        query = (text or "").strip().casefold()
        bar = self.tabs.tabBar()
        for index, page in enumerate(self.pages):
            try:
                bar.setTabVisible(index, not query or query in page.title.casefold())
            except Exception:
                pass
        visible = sum(
            1 for index in range(len(self.pages)) if bar.isTabVisible(index)
        )
        if query and visible:
            for index in range(len(self.pages)):
                if bar.isTabVisible(index):
                    self.tabs.setCurrentIndex(index)
                    break
        self._update_counter()

    def _find_next_in_page(self) -> None:
        """Jump to the next occurrence of the search text in the page."""
        query = (self._search.text() or "").strip()
        if not query:
            return
        browser = self._browsers[self.tabs.currentIndex()]
        try:
            found = browser.find(query)
            if not found:
                browser.moveCursor(QTextCursor.MoveMode.Start)
                browser.find(query)
        except Exception:
            pass

    def _update_counter(self) -> None:
        """Refresh the "visible of total" page counter."""
        try:
            bar = self.tabs.tabBar()
            visible = sum(
                1 for index in range(len(self.pages)) if bar.isTabVisible(index)
            )
            self._counter.setText(f"{visible} of {len(self.pages)} pages")
        except Exception:
            pass

    def open_markdown_file(self, file_path: str) -> str:
        """
        Opens desired documentation file in context of markdown.
        """
        with open(file_path, "r", encoding="utf-8") as file:
            contents = file.read()
            return contents
