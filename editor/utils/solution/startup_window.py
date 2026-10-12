"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Solution start window shown before the DreamStudio main window boots.
"""

import os

from editor import *

from editor.utils.solution.QDreamDialog import CreateSolutionDialog
from editor.utils.solution.dialogs import themed_box
from editor.utils.solution.manifests_scanner import scan_project_types
from editor.utils.solution.project_card import ProjectCard, resolve_entry_icon
from editor.utils.solution.recent_projects_scanner import (
    add_or_update,
    list_recent,
    remove as remove_recent,
)
from editor.utils.solution.solution_marker import (
    ensure_solution_marker,
    is_solution_dir,
    read_solution,
)
from editor.utils.solution.theme import center_on_screen, load_startup_qss

_START_WINDOW_TITLE = "Welcome to DreamStudio"

_WINDOW_WIDTH = 900
_WINDOW_HEIGHT = 650

_ALL_LANGUAGES = "All languages"
_ALL_PLATFORMS = "All platforms"
_ALL_TYPES = "All project types"

_FADE_OUT_MS = 150
_FADE_IN_MS = 150


class SolutionStartWindow(QMainWindow):
    """Two-step Visual-Studio-style solution start window.

    Attributes:
        solution_selected: Emitted with the chosen solution dict.
        prompt_cancelled: Emitted when the window closes without a choice.
    """

    solution_selected = pyqtSignal(object)
    prompt_cancelled = pyqtSignal()

    def __init__(self, registry=None) -> None:
        """Build the welcome-first start window.

        Args:
            registry: Optional bootstrap registry for config lookups.
        """
        super().__init__()

        self._registry = registry
        self._choice_made = False
        self._selection: dict = {}
        self._project_types: list[dict] = []
        self._project_cards: list[ProjectCard] = []
        self._project_items: list[QListWidgetItem] = []
        self._selected_project_entry: dict = {}
        self._theme_mode = "dark"
        self._page_anim: QPropertyAnimation | None = None
        self._pending_page: int = -1

        self.setObjectName("SolutionStartWindow")
        self.setWindowTitle(_START_WINDOW_TITLE)

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowCloseButtonHint
        )

        self.resize(_WINDOW_WIDTH, _WINDOW_HEIGHT)
        self.setFixedSize(_WINDOW_WIDTH, _WINDOW_HEIGHT)

        self._build_ui()
        self._load_intro_settings()
        self._apply_local_theme()
        center_on_screen(self)

    def _build_ui(self) -> None:
        """Build the top bar and the welcome/create stacked pages."""
        central = QWidget(self)
        central.setObjectName("SolutionStartCentral")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        self._stack = QStackedWidget(central)
        self._stack.setObjectName("SolutionStack")
        self._welcome_page = self._build_welcome_page()
        self._create_page = self._build_create_page()
        self._stack.addWidget(self._welcome_page)
        self._stack.addWidget(self._create_page)
        self._stack.setCurrentIndex(0)

        root.addWidget(self._stack, 1)

    def _build_topbar(self) -> QWidget:
        """Build the slim bar with back navigation and theme toggle.

        Returns:
            The configured top-bar widget.
        """
        bar = QFrame(self)
        bar.setObjectName("SolutionTopBar")
        bar.setFrameShape(QFrame.Shape.NoFrame)
        bar.setFixedHeight(46)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 6, 16, 6)
        layout.setSpacing(8)

        self._back_btn = QPushButton("← Back", bar)
        self._back_btn.setObjectName("SolutionLinkButton")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self.show_welcome)
        self._back_btn.setVisible(False)

        layout.addWidget(self._back_btn)
        layout.addStretch(1)

        hint = QLabel("DreamStudio Setup", bar)
        hint.setObjectName("SolutionSelectionHint")
        layout.addWidget(hint)

        self._theme_toggle = QPushButton("◐ Light theme", bar)
        self._theme_toggle.setObjectName("SolutionGhostButton")
        self._theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._theme_toggle.clicked.connect(self.toggle_theme)
        layout.addWidget(self._theme_toggle)

        layout.addSpacing(50)

        self._minimize_btn = QPushButton("—")
        self._minimize_btn.setObjectName("SolutionMinBtn")
        self._minimize_btn.clicked.connect(self.showMinimized)
        layout.addWidget(self._minimize_btn)

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("SolutionCloseBtn")
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._close_btn)

        return bar

    def _build_welcome_page(self) -> QWidget:
        """Build the Visual-Studio-like first screen.

        Returns:
            Welcome page with create/open actions and recent solutions.
        """
        page = QWidget(self)
        layout = QHBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(32)

        left = QFrame(page)
        left.setObjectName("SolutionWelcomeActions")
        left.setFrameShape(QFrame.Shape.NoFrame)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        brand = QLabel("DreamStudio", left)
        brand.setObjectName("SolutionBrandLabel")

        subtitle = QLabel("Get started", left)
        subtitle.setObjectName("SolutionSubtitleLabel")

        intro = QLabel(
            "Create a new solution from a template, or open an "
            "existing solution folder from disk.",
            left,
        )
        intro.setObjectName("SolutionHint")
        intro.setWordWrap(True)

        self._create_action_btn = QPushButton("＋  Create New Solution", left)
        self._create_action_btn.setObjectName("SolutionActionCard")
        self._create_action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._create_action_btn.setMinimumHeight(56)
        self._create_action_btn.clicked.connect(self.show_create)

        create_desc = QLabel("Start from a DreamStudio project template.", left)
        create_desc.setObjectName("SolutionActionDesc")

        self._open_action_btn = QPushButton("⧉  Open Existing Solution", left)
        self._open_action_btn.setObjectName("SolutionActionCard")
        self._open_action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_action_btn.setMinimumHeight(56)
        self._open_action_btn.clicked.connect(self._browse_open)

        open_desc = QLabel("Open a solution folder in the filesystem.", left)
        open_desc.setObjectName("SolutionActionDesc")

        left_layout.addWidget(brand)
        left_layout.addWidget(subtitle)
        left_layout.addWidget(intro)
        left_layout.addSpacing(12)
        left_layout.addWidget(self._create_action_btn)
        left_layout.addWidget(create_desc)
        left_layout.addSpacing(4)
        left_layout.addWidget(self._open_action_btn)
        left_layout.addWidget(open_desc)
        left_layout.addStretch(1)

        right = QFrame(page)
        right.setObjectName("SolutionRecentPanel")
        right.setFrameShape(QFrame.Shape.NoFrame)
        right.setMinimumWidth(300)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        recent_title = QLabel("Recent Solutions", right)
        recent_title.setObjectName("SolutionSectionTitle")

        recent_hint = QLabel("Double-click to open. Right-click to dismiss.", right)
        recent_hint.setObjectName("SolutionHint")
        recent_hint.setWordWrap(True)

        self._recent_list = QListWidget(right)
        self._recent_list.setFrameShape(QFrame.Shape.NoFrame)
        self._recent_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._recent_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self._recent_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._recent_list.setSpacing(6)
        self._recent_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._recent_list.customContextMenuRequested.connect(
            self._show_recent_context_menu
        )
        self._recent_list.itemDoubleClicked.connect(self._open_recent_item)
        self._recent_list.itemActivated.connect(self._open_recent_item)

        self._browse_btn = QPushButton("Open Existing Solution...", right)
        self._browse_btn.setObjectName("SolutionGhostButton")
        self._browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._browse_btn.clicked.connect(self._browse_open)

        right_layout.addWidget(recent_title)
        right_layout.addWidget(recent_hint)
        right_layout.addSpacing(4)
        right_layout.addWidget(self._recent_list, 1)
        right_layout.addWidget(self._browse_btn)

        layout.addWidget(left, 1)
        layout.addWidget(right, 1)

        return page

    def _build_create_page(self) -> QWidget:
        """Build the filterable template picker matching the reference image.

        Returns:
            Create-project page with search, filters and template cards.
        """
        page = QWidget(self)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 14, 24, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(16)

        title = QLabel("Create a new project", page)
        title.setObjectName("SolutionTitleLabel")
        header.addWidget(title, 0, Qt.AlignmentFlag.AlignVCenter)

        self._search_box = QLineEdit(page)
        self._search_box.setObjectName("SolutionSearchBox")
        self._search_box.setPlaceholderText("Search for templates...")
        self._search_box.setClearButtonEnabled(True)
        self._search_box.setMinimumHeight(36)
        self._search_box.setMinimumWidth(220)
        self._search_box.textChanged.connect(self._filter_projects)
        header.addWidget(self._search_box, 1)

        self._clear_all_btn = QPushButton("Clear all", page)
        self._clear_all_btn.setObjectName("SolutionLinkButton")
        self._clear_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clear_all_btn.clicked.connect(self._clear_all_filters)
        header.addWidget(self._clear_all_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        layout.addLayout(header)

        filter_row = QHBoxLayout()
        filter_row.setObjectName("SolutionFilterLayout")
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(12)

        self._language_filter = QComboBox(page)
        self._language_filter.setMinimumHeight(34)
        self._language_filter.currentIndexChanged.connect(
            lambda _index: self._apply_filters()
        )

        self._platform_filter = QComboBox(page)
        self._platform_filter.setMinimumHeight(34)
        self._platform_filter.currentIndexChanged.connect(
            lambda _index: self._apply_filters()
        )

        self._type_filter = QComboBox(page)
        self._type_filter.setMinimumHeight(34)
        self._type_filter.currentIndexChanged.connect(
            lambda _index: self._apply_filters()
        )

        filter_row.addWidget(self._language_filter, 1)
        filter_row.addWidget(self._platform_filter, 1)
        filter_row.addWidget(self._type_filter, 1)
        filter_row.addStretch(1)

        layout.addLayout(filter_row)

        content = QHBoxLayout()
        content.setContentsMargins(0, 6, 0, 0)
        content.setSpacing(24)

        left_panel = QFrame(page)
        left_panel.setObjectName("SolutionLeftPanel")
        left_panel.setFrameShape(QFrame.Shape.NoFrame)
        left_panel.setMinimumWidth(225)
        left_panel.setMaximumWidth(255)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        recent_templates_title = QLabel("Recent project templates", left_panel)
        recent_templates_title.setObjectName("SolutionSectionTitle")

        self._recent_templates_list = QListWidget(left_panel)
        self._recent_templates_list.setFrameShape(QFrame.Shape.NoFrame)
        self._recent_templates_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._recent_templates_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self._recent_templates_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._recent_templates_list.setSpacing(4)
        self._recent_templates_list.itemClicked.connect(self._open_recent_template_item)
        self._recent_templates_list.itemActivated.connect(
            self._open_recent_template_item
        )

        left_layout.addWidget(recent_templates_title)
        left_layout.addWidget(self._recent_templates_list, 1)

        self._project_list = QListWidget(page)
        self._project_list.setFrameShape(QFrame.Shape.NoFrame)
        self._project_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._project_list.setVerticalScrollMode(
            QAbstractItemView.ScrollMode.ScrollPerPixel
        )
        self._project_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._project_list.setSpacing(8)

        content.addWidget(left_panel, 0)
        content.addWidget(self._project_list, 1)

        layout.addLayout(content, 1)

        footer = QHBoxLayout()
        footer.setContentsMargins(0, 6, 0, 0)
        footer.setSpacing(8)

        self._selection_hint = QLabel("Select a project template to continue.", page)
        self._selection_hint.setObjectName("SolutionSelectionHint")
        self._selection_hint.setWordWrap(True)

        self._create_button = QPushButton("Next", page)
        self._create_button.setObjectName("SolutionPrimaryButton")
        self._create_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._create_button.setMinimumHeight(38)
        self._create_button.setMinimumWidth(150)
        self._create_button.setEnabled(False)
        self._create_button.clicked.connect(self._start_create_for_selected)

        footer.addWidget(self._selection_hint, 1)
        footer.addWidget(self._create_button)

        layout.addLayout(footer)

        self._populate_project_types()
        self._refresh_filter_options()

        return page

    def _apply_local_theme(self) -> None:
        """Apply the active standalone QSS file and refresh card highlights."""
        self.setStyleSheet(load_startup_qss(self._theme_mode))
        if self._theme_mode == "light":
            self._theme_toggle.setText("◑ Dark theme")
        else:
            self._theme_toggle.setText("◐ Light theme")

        for card in self._project_cards:
            card.refresh_text(
                self._search_box.text() if hasattr(self, "_search_box") else ""
            )

    def toggle_theme(self) -> None:
        """Toggle between the dark and light start-window themes."""
        self._theme_mode = "light" if self._theme_mode == "dark" else "dark"
        self._apply_local_theme()

    def show_welcome(self, _checked: bool = False, animated: bool = True) -> None:
        """Show the Visual-Studio-like first screen.

        Args:
            _checked: Absorbs ``QPushButton.clicked``'s checked flag.
            animated: Fade out the current page and fade in welcome.
        """
        self._switch_page(0, animated=animated)
        self._back_btn.setVisible(False)
        if not animated or self._stack.currentIndex() == 0:
            self._recent_list.setFocus()

    def show_create(self, _checked: bool = False, animated: bool = True) -> None:
        """Show the filterable template picker page.

        Args:
            _checked: Absorbs ``QPushButton.clicked``'s checked flag.
            animated: Fade out the current page and fade in create.
        """
        self._switch_page(1, animated=animated)
        self._back_btn.setVisible(True)
        if not animated or self._stack.currentIndex() == 1:
            self._search_box.setFocus()

    def _switch_page(self, index: int, animated: bool = True) -> None:
        """Cross-fade the stack to *index* via fade-out then fade-in.

        Args:
            index: Target page inside the stacked widget.
            animated: Run the opacity animation; otherwise switch instantly.
        """
        if self._stack.currentIndex() == index:
            self._stop_page_animation()
            return
        if not animated:
            self._stop_page_animation()
            self._stack.setCurrentIndex(index)
            return
        current = self._stack.currentWidget()
        if current is None:
            self._stack.setCurrentIndex(index)
            return
        self._stop_page_animation()
        self._pending_page = index
        effect = QGraphicsOpacityEffect(current)
        effect.setOpacity(1.0)
        current.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(_FADE_OUT_MS)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        anim.finished.connect(self._finish_fade_out)
        self._page_anim = anim
        anim.start()

    def _finish_fade_out(self) -> None:
        """Swap to the pending page and fade it in from transparent."""
        anim = self._page_anim
        self._page_anim = None
        target = self._pending_page
        self._pending_page = -1
        current = self._stack.currentWidget()
        if current is not None:
            current.setGraphicsEffect(None)
        if target < 0 or target >= self._stack.count():
            return
        self._stack.setCurrentIndex(target)
        nxt = self._stack.widget(target)
        if nxt is None:
            return
        effect = QGraphicsOpacityEffect(nxt)
        effect.setOpacity(0.0)
        nxt.setGraphicsEffect(effect)
        fade_in = QPropertyAnimation(effect, b"opacity", self)
        fade_in.setDuration(_FADE_IN_MS)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QEasingCurve.Type.InOutQuad)
        fade_in.finished.connect(self._finish_fade_in)
        self._page_anim = fade_in
        fade_in.start()
        if target == 0:
            self._recent_list.setFocus()
        else:
            self._search_box.setFocus()

    def _finish_fade_in(self) -> None:
        """Clear the fade-in effect once the new page is fully opaque."""
        anim = self._page_anim
        self._page_anim = None
        widget = self._stack.currentWidget()
        if widget is not None:
            widget.setGraphicsEffect(None)
        if anim is not None:
            anim.deleteLater()

    def _stop_page_animation(self) -> None:
        """Stop any running page fade and clear leftover opacity effects."""
        anim = self._page_anim
        self._page_anim = None
        self._pending_page = -1
        if anim is not None:
            try:
                anim.stop()
            except Exception:
                pass
            anim.deleteLater()
        for page in (
            getattr(self, "_welcome_page", None),
            getattr(self, "_create_page", None),
        ):
            if page is not None:
                page.setGraphicsEffect(None)

    def _all_languages(self) -> list:
        """Collect sorted unique languages across manifest entries.

        Returns:
            Alphabetically sorted language names.
        """
        seen: dict = {}
        for entry in self._project_types:
            manifest = entry.get("manifest") or {}
            values = manifest.get("languages") or entry.get("languages") or []
            if isinstance(values, str):
                values = [values]
            for value in values:
                text = str(value).strip()
                if text and text.lower() not in seen:
                    seen[text.lower()] = text
        return [seen[key] for key in sorted(seen)]

    def _refresh_filter_options(self) -> None:
        """Rebuild language/platform/type combos from loaded templates."""
        language_signal = self._language_filter.blockSignals(True)
        platform_signal = self._platform_filter.blockSignals(True)
        type_signal = self._type_filter.blockSignals(True)

        try:
            self._language_filter.clear()
            self._language_filter.addItem(_ALL_LANGUAGES, "")
            for language in self._all_languages():
                self._language_filter.addItem(language, language)
            self._language_filter.setCurrentIndex(0)

            self._platform_filter.clear()
            self._platform_filter.addItem(_ALL_PLATFORMS, "")
            self._platform_filter.addItem("Linux Desktop", "linux")
            self._platform_filter.addItem("Raspberry Pi", "raspberry_pi")
            self._platform_filter.addItem("Development SDK", "development_sdk")
            self._platform_filter.setCurrentIndex(0)

            self._type_filter.clear()
            self._type_filter.addItem(_ALL_TYPES, "")
            for entry in sorted(
                self._project_types,
                key=lambda item: str(item.get("display_name", "")).lower(),
            ):
                label = str(entry.get("display_name", entry.get("project_type", "")))
                self._type_filter.addItem(label, entry.get("project_type", ""))
            self._type_filter.setCurrentIndex(0)
        finally:
            self._language_filter.blockSignals(language_signal)
            self._platform_filter.blockSignals(platform_signal)
            self._type_filter.blockSignals(type_signal)

    def _clear_all_filters(self) -> None:
        """Clear search text and reset every filter combo."""
        self._search_box.clear()
        self._language_filter.setCurrentIndex(0)
        self._platform_filter.setCurrentIndex(0)
        self._type_filter.setCurrentIndex(0)
        self._apply_filters()

    def _populate_project_types(self) -> None:
        """Load manifests and build one selectable card per template."""
        self._project_types = scan_project_types()

        self._project_list.clear()
        self._project_cards.clear()
        self._project_items.clear()

        for entry in self._project_types:
            item = QListWidgetItem(self._project_list)
            item.setData(
                Qt.ItemDataRole.UserRole,
                entry,
            )
            item.setSizeHint(QSize(0, 116))

            card = ProjectCard(
                entry,
                self._project_list,
            )

            card.clicked.connect(self._select_project_entry)
            card.double_clicked.connect(self._select_and_create)

            self._project_list.addItem(item)
            self._project_list.setItemWidget(item, card)

            self._project_items.append(item)
            self._project_cards.append(card)

        if self._project_types:
            self._select_project_by_index(0)
        else:
            self._selection_hint.setText("No project templates were found.")

    def _matches_filters(self, entry: dict, query: str) -> bool:
        """Check whether *entry* satisfies search text and combo filters.

        Args:
            entry: Manifest entry under test.
            query: Case-folded search text (already stripped).

        Returns:
            ``True`` when the entry should stay visible.
        """
        name = str(entry.get("display_name", ""))
        description = str(entry.get("description", ""))
        searchable = f"{name}\n{description}".casefold()
        if query and query not in searchable:
            return False

        language_value = str(self._language_filter.currentData() or "").strip()
        if language_value:
            manifest = entry.get("manifest") or {}
            values = manifest.get("languages") or entry.get("languages") or []
            if isinstance(values, str):
                values = [values]
            normalized = {str(item).strip().lower() for item in values}
            if language_value.lower() not in normalized:
                return False

        platform_value = str(self._platform_filter.currentData() or "").strip().lower()
        if platform_value:
            manifest = entry.get("manifest") or {}
            raw = manifest.get("platforms") or manifest.get("platform") or []
            if isinstance(raw, str):
                raw = [raw]
            if raw:
                normalized_platforms = {str(item).strip().lower() for item in raw}
                match = platform_value in normalized_platforms
                if not match and platform_value == "raspberry_pi":
                    match = any("pi" in item for item in normalized_platforms)
                if not match:
                    return False

        type_value = str(self._type_filter.currentData() or "").strip()
        if type_value and entry.get("project_type") != type_value:
            return False

        return True

    def _apply_filters(self) -> None:
        """Show only templates matching search text and all three filters."""
        query = self._search_box.text().strip().casefold()
        first_visible_index = -1

        for index, entry in enumerate(self._project_types):
            matches = self._matches_filters(entry, query)
            self._project_items[index].setHidden(not matches)
            self._project_cards[index].refresh_text(self._search_box.text().strip())

            if matches and first_visible_index < 0:
                first_visible_index = index

        selected_index = -1

        if self._selected_project_entry:
            for index, entry in enumerate(self._project_types):
                if entry is self._selected_project_entry:
                    selected_index = index
                    break

        if selected_index >= 0 and not self._project_items[selected_index].isHidden():
            self._select_project_entry(self._selected_project_entry)
        elif first_visible_index >= 0:
            self._select_project_by_index(first_visible_index)
        else:
            self._clear_project_selection()

    def _select_project_by_index(
        self,
        index: int,
    ) -> None:
        """Select the template card at *index* when it is visible.

        Args:
            index: Position inside the loaded project-type list.
        """
        if not (0 <= index < len(self._project_items)):
            self._clear_project_selection()
            return

        item = self._project_items[index]
        entry = self._project_types[index]

        if item.isHidden():
            self._clear_project_selection()
            return

        self._project_list.setCurrentItem(item)
        self._select_project_entry(entry)

    def _select_project_entry(
        self,
        entry: dict,
    ) -> None:
        """Mark *entry* as selected and enable the Next button.

        Args:
            entry: Manifest entry chosen by the user.
        """
        if not entry:
            self._clear_project_selection()
            return

        self._selected_project_entry = entry

        selected_index = -1

        for index, current_entry in enumerate(self._project_types):
            is_selected = current_entry is entry

            self._project_cards[index].set_selected(is_selected)

            if is_selected:
                selected_index = index

        if selected_index >= 0:
            self._project_list.setCurrentRow(selected_index)
            self._sync_recent_templates_selection()

        name = entry.get("display_name", "Project")

        self._selection_hint.setText(f"Selected: {name}")
        self._create_button.setEnabled(True)

    def _clear_project_selection(self) -> None:
        """Clear the template selection and disable the Next button."""
        self._selected_project_entry = {}

        for card in self._project_cards:
            card.set_selected(False)

        self._project_list.clearSelection()
        self._create_button.setEnabled(False)
        self._selection_hint.setText("Select a project template to continue.")

    def _select_and_create(
        self,
        entry: dict,
    ) -> None:
        """Select *entry* then immediately start the create dialog.

        Args:
            entry: Manifest entry double-clicked by the user.
        """
        self._select_project_entry(entry)
        self._start_create_for_selected()

    def _filter_projects(
        self,
        text: str,
    ) -> None:
        """Filter template cards as the search text changes.

        Args:
            text: Raw search-box content (combos are read separately).
        """
        del text
        self._apply_filters()

    def _populate_recent_templates(self) -> None:
        """Fill the left recent-templates list from recents plus catalog."""
        self._recent_templates_list.clear()

        ordered: list = []
        seen_types: set = set()

        for record in list_recent():
            project_type = str(record.get("project_type", ""))
            if not project_type or project_type in seen_types:
                continue
            match = next(
                (
                    entry
                    for entry in self._project_types
                    if entry.get("project_type") == project_type
                ),
                None,
            )
            if match is not None:
                ordered.append(match)
                seen_types.add(project_type)

        for entry in self._project_types:
            if len(ordered) >= 9:
                break
            if entry.get("project_type") not in seen_types:
                ordered.append(entry)
                seen_types.add(entry.get("project_type"))

        if not ordered:
            item = QListWidgetItem("No templates yet.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._recent_templates_list.addItem(item)
            return

        for entry in ordered:
            widget = QWidget(self._recent_templates_list)
            row = QHBoxLayout(widget)
            row.setContentsMargins(8, 6, 8, 6)
            row.setSpacing(8)

            icon_label = QLabel(widget)
            icon_label.setFixedSize(22, 22)
            icon = resolve_entry_icon(entry)
            if not icon.isNull():
                icon_label.setPixmap(icon.pixmap(QSize(20, 20)))

            name_label = QLabel(str(entry.get("display_name", "Project")), widget)
            name_label.setWordWrap(True)

            manifest = entry.get("manifest") or {}
            languages = manifest.get("languages") or []
            badge_text = str(languages[0]) if languages else ""
            badge = QLabel(badge_text, widget)
            badge.setObjectName("SolutionLangBadge")
            badge.setVisible(bool(badge_text))

            row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(name_label, 1)
            row.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

            item = QListWidgetItem(self._recent_templates_list)
            item.setData(Qt.ItemDataRole.UserRole, entry)
            item.setSizeHint(QSize(0, 44))
            item.setToolTip(str(entry.get("description", ""))[:220])
            self._recent_templates_list.addItem(item)
            self._recent_templates_list.setItemWidget(item, widget)

        self._sync_recent_templates_selection()

    def _sync_recent_templates_selection(self) -> None:
        """Highlight the left recent row matching the active template."""
        if not hasattr(self, "_recent_templates_list"):
            return
        selected_type = (self._selected_project_entry or {}).get("project_type")
        for row in range(self._recent_templates_list.count()):
            item = self._recent_templates_list.item(row)
            entry = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(entry, dict) and entry.get("project_type") == selected_type:
                self._recent_templates_list.setCurrentRow(row)
                break

    def _open_recent_template_item(self, item) -> None:
        """Select the catalog card matching a recent-template row.

        Args:
            item: Activated recent-template list item.
        """
        entry = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(entry, dict):
            for index, candidate in enumerate(self._project_types):
                if candidate is entry or (
                    candidate.get("project_type") == entry.get("project_type")
                ):
                    if not self._project_items[index].isHidden():
                        self._select_project_by_index(index)
                    else:
                        self._clear_all_filters()
                        self._select_project_by_index(index)
                    self._project_list.scrollToItem(
                        self._project_items[index],
                        QAbstractItemView.ScrollHint.PositionAtCenter,
                    )
                    break

    def _load_intro_settings(self) -> None:
        """Populate welcome recents and the create-page recent templates."""
        self._refresh_recent_list()
        self._populate_recent_templates()

    def _refresh_recent_list(self) -> None:
        """Reload the welcome recent-solutions list from history.

        The placeholder row carries no path data, so the dismiss menu
        safely ignores it.
        """
        last = self._last_directory()
        self._recent_list.clear()
        paths_in_recent = []

        for record in list_recent():
            path = record.get("path", "")
            paths_in_recent.append(path)
            item = QListWidgetItem(self._recent_list)
            name = record.get("name") or os.path.basename(path.rstrip(os.sep)) or path
            item.setText(f"{name}\n{path}")
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)

        if not paths_in_recent:
            item = QListWidgetItem("No recent solutions yet.")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._recent_list.addItem(item)

        if last:
            for index in range(self._recent_list.count()):
                item = self._recent_list.item(index)
                row_path = item.data(Qt.ItemDataRole.UserRole)
                if row_path == last:
                    self._recent_list.setCurrentRow(index)
                    break

    def _show_recent_context_menu(self, position) -> None:
        """Show the right-click menu for the welcome recent list.

        Args:
            position: Viewport-local position where the menu was requested.
        """
        item = self._recent_list.itemAt(position)
        if item is None:
            return
        path = item.data(Qt.ItemDataRole.UserRole)
        if not path:
            return
        menu = QMenu(self._recent_list)
        dismiss_action = menu.addAction("Dismiss")
        chosen = menu.exec(self._recent_list.viewport().mapToGlobal(position))
        if chosen == dismiss_action:
            self._dismiss_recent_path(str(path))

    def _dismiss_recent_path(self, path: str) -> None:
        """Remove *path* from history only, leaving the folder on disk.

        Args:
            path: Absolute solution path to forget.
        """
        try:
            remove_recent(path)
        except Exception:
            pass
        self._refresh_recent_list()
        self._populate_recent_templates()

    def _last_directory(self) -> str:
        """Return the last workspace directory from the registry config.

        Returns:
            Stored directory path or an empty string.
        """
        try:
            config = self._registry.get("config") if self._registry else {}

            return (config.get("workspace") or {}).get(
                "last_directory",
                "",
            )
        except Exception:
            return ""

    def set_tab(self, index: int) -> None:
        """Show the requested landing page for legacy callers.

        Index 0 focuses project creation.
        Index 1 focuses recent projects.

        Args:
            index: Legacy tab number (0 create, 1 open/recent).
        """
        if index == 1:
            self.show_welcome()
        else:
            self.show_create()

    def _start_create_for_selected(self) -> None:
        """Open the create dialog for the selected template."""
        entry = self._selected_project_entry

        if not entry:
            return

        dialog = CreateSolutionDialog(
            self,
            project_entry=entry,
        )

        if dialog.exec() != CreateSolutionDialog.DialogCode.Accepted:
            return

        if not dialog.result_data:
            return

        data = dict(dialog.result_data)

        scaffold = {
            "target": data["path"],
            "name": data["name"],
            "project_type": data["project_type"],
            "manifest_path": data["manifest_path"],
        }

        self._emit_selection(
            data,
            scaffold,
        )

    def _open_recent_item(
        self,
        item,
    ) -> None:
        """Open the solution path stored on a recent list *item*.

        Args:
            item: Activated recent-solution list item.
        """
        path = item.data(Qt.ItemDataRole.UserRole)

        if path:
            self._open_solution(path)

    def _browse_open(self) -> None:
        """Open an existing solution folder chosen from the filesystem."""
        start = self._last_directory() or os.path.expanduser("~")

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Solution Folder",
            start,
        )

        if folder:
            self._open_solution(folder)

    def _open_solution(
        self,
        path: str,
    ) -> None:
        """Open *path* as a solution, creating a marker when missing.

        Args:
            path: Filesystem folder selected or restored by the user.
        """
        absolute = os.path.abspath(path)

        if not os.path.isdir(absolute):
            themed_box(
                self,
                QMessageBox.Icon.Warning,
                "Folder unavailable",
                f"The folder no longer exists:\n{absolute}",
            ).exec()
            return

        project_type = "directory"
        name = os.path.basename(absolute.rstrip(os.sep)) or absolute

        if is_solution_dir(absolute):
            try:
                marker = read_solution(absolute)

                project_type = marker.get("project_type") or project_type
                name = marker.get("name") or name
            except Exception:
                pass
        else:
            try:
                ensure_solution_marker(
                    absolute,
                    name=name,
                    project_type=project_type,
                )
            except OSError:
                pass

        try:
            add_or_update(
                absolute,
                name=name,
                project_type=project_type,
            )
        except Exception:
            pass

        self._emit_selection(
            {
                "path": absolute,
                "name": name,
                "project_type": project_type,
            },
            None,
        )

    def _emit_selection(
        self,
        data: dict,
        scaffold,
    ) -> None:
        """Emit the final solution choice and remember it locally.

        Args:
            data: Solution metadata with path, name and project type.
            scaffold: Optional scaffold payload for a newly created project.
        """
        selection = {
            "path": data["path"],
            "name": data.get(
                "name",
                "",
            ),
            "project_type": data.get(
                "project_type",
                "",
            ),
            "_scaffold": scaffold,
        }

        self._choice_made = True
        self._selection = selection
        self.solution_selected.emit(selection)

    def _force_normal_window_state(self) -> None:
        """Keep the fixed-size picker as a normal window (kept for compat)."""
        self.setWindowState(
            self.windowState()
            & ~Qt.WindowState.WindowMaximized
            & ~Qt.WindowState.WindowFullScreen
        )
        self.showNormal()

    def showEvent(self, event) -> None:
        """Center the fixed-size window whenever it becomes visible."""
        super().showEvent(event)
        center_on_screen(self)

    def closeEvent(self, event) -> None:
        """Emit prompt_cancelled when dismissed without a selection."""
        if not self._choice_made:
            self.prompt_cancelled.emit()

        super().closeEvent(event)


def _complete_selection(
    result: dict,
    selection: dict,
    loop,
) -> None:
    """Store *selection* in *result* and quit the nested event loop.

    Args:
        result: Mutable carrier for selection and scaffold payloads.
        selection: Emitted solution metadata.
        loop: Nested event loop waiting for the user choice.
    """
    result["selection"] = selection
    result["scaffold"] = (
        selection.get("_scaffold") if isinstance(selection, dict) else None
    )
    loop.quit()


def run_start_window_selection(window) -> tuple:
    """Run *window* modally and return its (selection, scaffold) tuple.

    Args:
        window: Configured start window to execute.

    Returns:
        Tuple of selection dict (or ``None``) and scaffold payload.
    """
    from PyQt6.QtCore import QEventLoop

    result: dict = {}
    loop = QEventLoop()

    window.solution_selected.connect(
        lambda selection: _complete_selection(
            result,
            selection,
            loop,
        )
    )

    window.prompt_cancelled.connect(loop.quit)

    window._force_normal_window_state()
    window.show()
    window.raise_()
    window.activateWindow()
    center_on_screen(window)

    loop.exec()

    try:
        window.close()
        window.deleteLater()
    except Exception:
        pass

    return (
        result.get("selection"),
        result.get("scaffold"),
    )
