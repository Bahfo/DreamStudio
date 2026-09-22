"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Documentation window displayed via Help -> Documentation.
"""

from editor import *


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

    Attributes:
        tabs: Main tab widget holding documentation pages.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the documentation window.

        Args:
            parent: Optional parent widget.
        """
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget(self)
        tabs.setTabBar(VerticalTabBar())
        tabs.setTabPosition(QTabWidget.TabPosition.West)

        script_dir = Path(__file__).parent
        files = sorted(
            (
                p
                for p in script_dir.iterdir()
                if p.is_file()
                and p.suffix == ".md"
                and p.name.split("_", 1)[0].isdigit()
                and 1 <= int(p.name.split("_", 1)[0]) <= 5
            ),
            key=lambda p: int(p.name.split("_", 1)[0]),
        )

        for path in files:
            tab = QTextBrowser()
            tab.setMarkdown(self.open_markdown_file(str(path)))
            tabs.addTab(tab, path.name)

        layout.addWidget(tabs)
        self.tabs = tabs

    def open_markdown_file(self, file_path: str) -> str:
        """
        Opens desired documentation file in context of markdown.
        """
        with open(file_path, "r") as file:
            contents = file.read()
            return contents
