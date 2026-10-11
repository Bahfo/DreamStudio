"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Project-template card for the solution start window.

Holds the selectable card widget, search-match highlighting and manifest tag
derivation so ``startup_window`` stays focused on window flow and filtering.
"""

import html
import os

from editor import *

from editor.utils.solution.theme import startup_highlight


def highlight_html(text: str, query: str, color: str) -> str:
    """Return *text* as HTML with *query* matches wrapped in a highlight span.

    Args:
        text: Plain source text to display.
        query: Case-insensitive substring to highlight (empty disables).
        color: Background color used for the highlight span.

    Returns:
        HTML string safe for a rich-text ``QLabel``.
    """
    safe = html.escape(str(text))
    needle = query.strip()
    if not needle:
        return safe
    try:
        pattern = re.compile(re.escape(needle), re.IGNORECASE)
    except re.error:
        return safe
    return pattern.sub(
        lambda match: f'<span style="background-color:{color};'
        f'color:white;">{html.escape(match.group(0))}</span>',
        safe,
    )


def entry_tags(project_entry: dict) -> list:
    """Derive pill tags for a manifest entry.

    Args:
        project_entry: Manifest entry with ``manifest`` and ``project_type``.

    Returns:
        Ordered, deduplicated list of tag strings (capped at 7).
    """
    manifest = project_entry.get("manifest") or {}
    tags: list = []

    languages = manifest.get("languages") or project_entry.get("languages") or []
    if isinstance(languages, str):
        languages = [languages]
    for language in languages:
        text = str(language).strip()
        if text and text not in tags:
            tags.append(text)

    platforms = manifest.get("platforms") or manifest.get("platform") or []
    if isinstance(platforms, str):
        platforms = [platforms]
    for platform in platforms:
        text = str(platform).strip()
        if text and text not in tags:
            tags.append(text)

    if not platforms:
        project_type = str(project_entry.get("project_type", ""))
        if "pi" in project_type.lower() or "raspberry" in project_type.lower():
            tags.extend([t for t in ("Linux", "Raspberry Pi") if t not in tags])
        elif project_type and project_type != "directory":
            tags.extend([t for t in ("Linux",) if t not in tags])

    extra = manifest.get("tags") or []
    if isinstance(extra, str):
        extra = [extra]
    for tag in extra:
        text = str(tag).strip()
        if text and text not in tags:
            tags.append(text)

    return tags[:7]


def resolve_entry_icon(project_entry: dict) -> QIcon:
    """Resolve a manifest-provided icon, falling back to a native icon.

    Args:
        project_entry: Manifest entry that may carry an ``icon`` value.

    Returns:
        The template icon or a generic file icon.
    """
    icon_value = project_entry.get("icon")

    if isinstance(icon_value, QIcon):
        return icon_value

    if isinstance(icon_value, str) and icon_value:
        icon_path = icon_value

        if not os.path.isabs(icon_path):
            manifest_path = project_entry.get("manifest_path", "")

            if manifest_path:
                icon_path = os.path.join(
                    os.path.dirname(manifest_path),
                    icon_path,
                )

        icon = QIcon(icon_path)

        if not icon.isNull():
            return icon

    return QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)


class ProjectCard(QFrame):
    """Visual project-template card used by the solution picker.

    Attributes:
        project_entry: Manifest entry dict backing this card.
        clicked: Emitted with the entry on single click.
        double_clicked: Emitted with the entry on double click.
    """

    clicked = pyqtSignal(object)
    double_clicked = pyqtSignal(object)

    def __init__(self, project_entry: dict, parent=None) -> None:
        """Build the card widgets for *project_entry*.

        Args:
            project_entry: Manifest entry with display info and tags.
            parent: Optional parent widget.
        """
        super().__init__(parent)

        self.project_entry = project_entry
        self._selected = False
        self._query = ""

        self.setObjectName("SolutionProjectCard")
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setMinimumHeight(104)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._build_ui()

    def _build_ui(self) -> None:
        """Create the icon, rich-text labels and tag pills."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(14)

        icon_frame = QFrame(self)
        icon_frame.setObjectName("SolutionProjectIconFrame")
        icon_frame.setFixedSize(52, 52)

        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(5, 5, 5, 5)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._icon_label = QLabel(icon_frame)
        self._icon_label.setObjectName("SolutionProjectIcon")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon_label.setFixedSize(42, 42)

        icon = self._resolve_icon()

        if not icon.isNull():
            self._icon_label.setPixmap(icon.pixmap(QSize(38, 38)))

        icon_layout.addWidget(self._icon_label)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        self._name_label = QLabel(self)
        self._name_label.setObjectName("SolutionProjectName")
        self._name_label.setWordWrap(True)
        self._name_label.setTextFormat(Qt.TextFormat.RichText)

        self._description_label = QLabel(self)
        self._description_label.setObjectName("SolutionProjectDescription")
        self._description_label.setWordWrap(True)
        self._description_label.setTextFormat(Qt.TextFormat.RichText)
        self._description_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )

        self._tags_row = QHBoxLayout()
        self._tags_row.setContentsMargins(0, 4, 0, 0)
        self._tags_row.setSpacing(6)
        self._tags_row.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )

        content_layout.addWidget(self._name_label)
        content_layout.addWidget(self._description_label, 1)
        content_layout.addLayout(self._tags_row)

        layout.addWidget(
            icon_frame,
            0,
            Qt.AlignmentFlag.AlignTop,
        )
        layout.addLayout(content_layout, 1)

        self.refresh_text()

    def _resolve_icon(self) -> QIcon:
        """Resolve this card's icon via the shared manifest helper.

        Returns:
            The template icon or a generic file icon.
        """
        return resolve_entry_icon(self.project_entry)

    def refresh_text(self, query: str = "") -> None:
        """Refresh title, description and tags, highlighting *query*.

        Args:
            query: Current search text used for match highlighting.
        """
        self._query = query or ""
        color = startup_highlight(self._theme_mode())
        name = str(self.project_entry.get("display_name", "Unnamed Project"))
        description = str(
            self.project_entry.get(
                "description",
                "No description is available for this project template.",
            )
        )
        self._name_label.setText(highlight_html(name, self._query, color))
        short = description if len(description) <= 220 else description[:217] + "..."
        self._description_label.setText(highlight_html(short, self._query, color))

        while self._tags_row.count():
            item = self._tags_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for tag in entry_tags(self.project_entry):
            pill = QLabel(str(tag), self)
            pill.setObjectName("SolutionTagPill")
            self._tags_row.addWidget(pill)

        self._tags_row.addStretch(1)

    def _theme_mode(self) -> str:
        """Find the start window's theme mode by walking ancestors.

        Returns:
            ``"light"`` when an ancestor reports light mode, else ``"dark"``.
        """
        parent = self.parentWidget()
        while parent is not None:
            if hasattr(parent, "_theme_mode"):
                try:
                    return str(parent._theme_mode)  # noqa: SLF001
                except Exception:
                    return "dark"
            parent = parent.parentWidget()
        return "dark"

    def set_selected(self, selected: bool) -> None:
        """Update the card selection state.

        Args:
            selected: Whether this card is the active selection.
        """
        self._selected = selected

        self.setProperty(
            "selected",
            selected,
        )

        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event) -> None:
        """Emit :attr:`clicked` on left-button press."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.project_entry)

        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Emit :attr:`double_clicked` on left-button double click."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.project_entry)

        super().mouseDoubleClickEvent(event)
