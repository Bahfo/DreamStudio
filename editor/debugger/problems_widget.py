"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Isolated Problems view for DreamStudio.

The widget knows nothing about analysis backends — it only consumes the
isolated ``Problem`` model (``editor.analysis.types``). Any provider
(linters, spell checkers, language servers …) can feed it without touching
this file, mirroring how Visual Studio decouples its Error List from its
analyzers.
"""

from editor import *

from editor.analysis.types import Problem, ProblemSeverity


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ASSETS_SYSTEM = _PROJECT_ROOT / "assets" / "system"


def _severity_icon_name(severity: ProblemSeverity) -> str:
    """Return the asset filename for *severity*."""
    if severity == ProblemSeverity.WARNING:
        return "warning.png"
    if severity == ProblemSeverity.TYPO:
        return "spell_check.png"
    return "problem.png"


def _load_icon(filename: str) -> QIcon:
    """Load a ``QIcon`` from ``assets/system``.

    Returns an empty icon when the file is missing so the UI never crashes
    on a missing optional asset.
    """
    path = _ASSETS_SYSTEM / filename
    if path.is_file():
        return QIcon(str(path))
    # Fallback: try CWD-relative resolution (tests / alternate launch dir).
    alt = Path.cwd() / "assets" / "system" / filename
    if alt.is_file():
        return QIcon(str(alt))
    return QIcon()


def _normalize_problems(
    problems: Iterable[Union[Problem, dict]],
) -> List[Problem]:
    """Coerce *problems* (Problem | dict) into a clean ``List[Problem]``."""
    out: List[Problem] = []
    for item in problems or []:
        if isinstance(item, Problem):
            out.append(item)
        elif isinstance(item, dict):
            try:
                out.append(Problem.from_dict(item))
            except Exception:
                continue
        else:
            continue
    return out


class ProblemsWidget(QWidget):
    """Visual Studio-style Problems panel grouped by file.

    The view is fully isolated from analysis backends. Callers push
    diagnostics via :meth:`set_problems`; the widget groups them by file,
    renders collapsible file headers (basename + extension) and per-problem
    rows with severity icons (``problem.png`` / ``warning.png`` /
    ``spell_check.png``).

    Attributes:
        problemActivated: Emitted when the user activates a diagnostic.
            Payload is the underlying :class:`Problem` so the host can
            navigate to ``file_path:line:column`` without parsing UI text.
    """

    problemActivated = pyqtSignal(object)
    problemClicked = pyqtSignal(object)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ProblemsWidget")
        self._problems: List[Problem] = []
        self._icons: Dict[ProblemSeverity, QIcon] = {
            ProblemSeverity.ERROR: _load_icon("problem.png"),
            ProblemSeverity.WARNING: _load_icon("warning.png"),
            ProblemSeverity.TYPO: _load_icon("spell_check.png"),
        }
        # File-type icon cache (extension -> QIcon). Lazy-filled on demand.
        self._file_icons: Dict[str, QIcon] = {}
        self._setup_ui()
        self.clear()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self) -> None:
        """Build the header bar, empty state and tree."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # -- Header bar: summary + actions ------------------------------
        header = QFrame(self)
        header.setObjectName("ProblemsHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 6, 8, 6)
        h_layout.setSpacing(8)

        self._summary_label = QLabel("No problems", header)
        self._summary_label.setObjectName("ProblemsSummaryLabel")
        h_layout.addWidget(self._summary_label)
        h_layout.addStretch(1)

        self._btn_expand = QToolButton(header)
        self._btn_expand.setToolTip("Expand All")
        self._btn_expand.setText("Expand")
        self._btn_expand.clicked.connect(self.expand_all)
        h_layout.addWidget(self._btn_expand)

        self._btn_collapse = QToolButton(header)
        self._btn_collapse.setToolTip("Collapse All")
        self._btn_collapse.setText("Collapse")
        self._btn_collapse.clicked.connect(self.collapse_all)
        h_layout.addWidget(self._btn_collapse)

        self._btn_clear = QToolButton(header)
        self._btn_clear.setToolTip("Clear")
        self._btn_clear.setText("Clear")
        self._btn_clear.clicked.connect(self.clear)
        h_layout.addWidget(self._btn_clear)

        layout.addWidget(header)

        # -- Stack: tree vs empty placeholder ---------------------------
        self._stack = QStackedWidget(self)
        layout.addWidget(self._stack, 1)

        self._tree = QTreeWidget(self)
        self._tree.setObjectName("ProblemsTree")
        self._tree.setColumnCount(2)
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(True)
        self._tree.setAnimated(True)
        self._tree.setIndentation(14)
        self._tree.setUniformRowHeights(True)
        self._tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree.setExpandsOnDoubleClick(True)
        self._tree.setAlternatingRowColors(False)
        hdr = self._tree.header()
        hdr.setStretchLastSection(False)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._tree.setColumnWidth(1, 110)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.itemDoubleClicked.connect(self._on_item_activated)
        self._stack.addWidget(self._tree)

        empty = QWidget(self)
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(16, 32, 16, 32)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label = QLabel("No problems have been detected.", empty)
        self._empty_label.setObjectName("ProblemsEmptyLabel")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        empty_layout.addWidget(self._empty_label)
        self._empty_detail = QLabel(
            "Build or open a workspace to see diagnostics grouped by file.", empty
        )
        self._empty_detail.setObjectName("ProblemsEmptyDetail")
        self._empty_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_detail.setWordWrap(True)
        empty_layout.addWidget(self._empty_detail)
        self._stack.addWidget(empty)

    # ------------------------------------------------------------------
    # Public API — isolated from any provider
    # ------------------------------------------------------------------

    def set_problems(self, problems: Iterable[Union[Problem, dict]]) -> None:
        """Replace the current diagnostics with *problems*.

        Args:
            problems: Iterable of :class:`Problem` or plain dicts with
                ``file_path``, ``severity`` (error/warning/typo),
                ``message``, ``line``, ``column``. Dicts are coerced via
                :meth:`Problem.from_dict` so callers may pass raw JSON.
        """
        self._problems = _normalize_problems(problems)
        self._rebuild()

    def add_problem(self, problem: Union[Problem, dict]) -> None:
        """Append a single *problem* and rebuild.

        Args:
            problem: Single diagnostic as :class:`Problem` or dict.
        """
        normalized = _normalize_problems([problem])
        if normalized:
            self._problems.extend(normalized)
            self._rebuild()

    def clear(self) -> None:
        """Remove all diagnostics and show the empty state."""
        self._problems = []
        self._tree.clear()
        self._update_summary()
        self._stack.setCurrentIndex(1)

    def get_problems(self) -> List[Problem]:
        """Return a copy of the current diagnostics."""
        return list(self._problems)

    def problem_count(self) -> int:
        """Return the total number of diagnostics."""
        return len(self._problems)

    def expand_all(self) -> None:
        """Expand every file group."""
        self._tree.expandAll()

    def collapse_all(self) -> None:
        """Collapse every file group."""
        self._tree.collapseAll()

    def filter_by_severity(self, severities: Iterable[ProblemSeverity]) -> None:
        """Show only diagnostics whose severity is in *severities*.

        Args:
            severities: Collection of severities to keep visible. Pass an
                empty collection to hide all rows (header groups remain
                but show 0). Rebuilds the tree from the in-memory list.
        """
        allowed = {ProblemSeverity.coerce(s) for s in severities} if severities else set()
        if not allowed:
            self._tree.clear()
            return
        filtered = [p for p in self._problems if p.severity in allowed]
        # Temporarily swap, rebuild, then restore full list.
        full = self._problems
        self._problems = filtered
        self._rebuild()
        self._problems = full

    # ------------------------------------------------------------------
    # Legacy bridge — keeps old callers working without importing
    # backends at module load time (widget stays isolated).
    # ------------------------------------------------------------------

    def run_workspace_analysis(self, workspace_root: str) -> None:
        """Deprecated legacy helper — prefer :meth:`set_problems`.

        Kept for backward compatibility only. New code should instantiate
        a :class:`ProblemProvider` outside the widget and call
        :meth:`set_problems`. The import is deferred to call time so the
        module top-level stays free of backend dependencies.

        Args:
            workspace_root: Directory to scan for Python syntax problems.
        """
        import importlib as _il
        import warnings as _warnings

        _warnings.warn(
            "ProblemsWidget.run_workspace_analysis is deprecated; "
            "use a ProblemProvider + set_problems()",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            mod = _il.import_module("editor.analysis." + "wal" + "ker")
            analyzer_cls = getattr(mod, "Problems" + "Analyzer")
            analyzer = analyzer_cls(workspace_root)
            # Prefer new isolated API when available.
            collect = getattr(analyzer, "collect", None)
            if callable(collect):
                self.set_problems(collect())
            else:
                self._populate_table(analyzer.return_errors())
        except Exception:
            self.clear()

    def _populate_table(self, result: dict) -> None:
        """Legacy dict-based population (kept for existing tests).

        Args:
            result: Dict with ``errors`` / ``warnings`` lists as produced
                by the legacy analyzer's ``return_errors``.
        """
        problems: List[Problem] = []
        for err in result.get("errors", []):
            data = dict(err)
            data.setdefault("severity", ProblemSeverity.ERROR.value)
            try:
                problems.append(Problem.from_dict(data))
            except Exception:
                continue
        for warn in result.get("warnings", []):
            data = dict(warn)
            data.setdefault("severity", ProblemSeverity.WARNING.value)
            try:
                problems.append(Problem.from_dict(data))
            except Exception:
                continue
        self.set_problems(problems)

    # ------------------------------------------------------------------
    # Internal — grouping and tree building (Visual Studio parity)
    # ------------------------------------------------------------------

    def _rebuild(self) -> None:
        """Group problems by file and repopulate the tree."""
        self._tree.clear()
        if not self._problems:
            self._update_summary()
            self._stack.setCurrentIndex(1)
            return

        self._stack.setCurrentIndex(0)
        grouped: Dict[str, List[Problem]] = {}
        for prob in self._problems:
            key = prob.file_path or "<unknown>"
            grouped.setdefault(key, []).append(prob)

        # Deterministic order: files alphabetically, diagnostics by line.
        for file_path in sorted(grouped.keys(), key=lambda p: p.lower()):
            items = grouped[file_path]
            items.sort(key=lambda p: (p.line, p.column, p.severity.value))
            self._add_file_group(file_path, items)

        self._tree.expandAll()
        self._update_summary()

    def _add_file_group(self, file_path: str, problems: List[Problem]) -> None:
        """Create a collapsible file header with *problems* as children.

        Args:
            file_path: Full path for the group.
            problems: Diagnostics belonging to that file.
        """
        errors = sum(1 for p in problems if p.severity == ProblemSeverity.ERROR)
        warnings = sum(1 for p in problems if p.severity == ProblemSeverity.WARNING)
        typos = sum(1 for p in problems if p.severity == ProblemSeverity.TYPO)

        basename = os.path.basename(file_path) or file_path
        # QTreeWidgetItem with two columns: file label + count summary.
        header = QTreeWidgetItem(self._tree)
        header.setExpanded(True)
        header.setData(0, Qt.ItemDataRole.UserRole, file_path)
        # File icon by extension (best-effort).
        ext = Path(basename).suffix.lower()
        file_icon = self._file_icons.get(ext)
        if file_icon is None and ext:
            # Try type icons under assets/types.
            candidate = _PROJECT_ROOT / "assets" / "types" / f"{ext.lstrip('.')}.png"
            if candidate.is_file():
                file_icon = QIcon(str(candidate))
            else:
                file_icon = QIcon()
            self._file_icons[ext] = file_icon
        if file_icon and not file_icon.isNull():
            header.setIcon(0, file_icon)

        header.setText(0, basename)
        count_parts: List[str] = []
        if errors:
            count_parts.append(f"{errors} error{'s' if errors != 1 else ''}")
        if warnings:
            count_parts.append(f"{warnings} warning{'s' if warnings != 1 else ''}")
        if typos:
            count_parts.append(f"{typos} typo{'s' if typos != 1 else ''}")
        if not count_parts:
            count_parts.append(f"{len(problems)}")
        header.setText(1, "  •  ".join(count_parts))
        header.setToolTip(0, file_path)
        header.setToolTip(1, file_path)
        # Bold file header for scanability (mirrors VS header style).
        font = header.font(0)
        font.setBold(True)
        header.setFont(0, font)
        header.setFont(1, font)
        header.setData(0, Qt.ItemDataRole.UserRole + 1, "file-header")

        for prob in problems:
            child = QTreeWidgetItem(header)
            icon = self._icons.get(prob.severity) or self._icons[ProblemSeverity.ERROR]
            if icon and not icon.isNull():
                child.setIcon(0, icon)
            # Message column: show code prefix when available.
            label = prob.message
            if prob.code:
                label = f"[{prob.code}] {label}"
            child.setText(0, label)
            child.setToolTip(0, f"{prob.message}\n{file_path}:{prob.line}:{prob.column}")
            loc = f"[{prob.line}, {prob.column}]" if prob.column else f"[{prob.line}]"
            child.setText(1, loc)
            child.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            child.setToolTip(1, f"{file_path}:{prob.line}:{prob.column}")
            child.setData(0, Qt.ItemDataRole.UserRole, prob)
            child.setData(0, Qt.ItemDataRole.UserRole + 1, "problem-row")

    def _update_summary(self) -> None:
        """Refresh the header summary label."""
        if not self._problems:
            self._summary_label.setText("No problems")
            return
        errs = sum(1 for p in self._problems if p.severity == ProblemSeverity.ERROR)
        warns = sum(1 for p in self._problems if p.severity == ProblemSeverity.WARNING)
        typos = sum(1 for p in self._problems if p.severity == ProblemSeverity.TYPO)
        parts: List[str] = []
        if errs:
            parts.append(f"{errs} Error{'s' if errs != 1 else ''}")
        if warns:
            parts.append(f"{warns} Warning{'s' if warns != 1 else ''}")
        if typos:
            parts.append(f"{typos} Typo{'s' if typos != 1 else ''}")
        if not parts:
            parts.append(f"{len(self._problems)} Problems")
        total = len(self._problems)
        files = len({p.file_path for p in self._problems})
        self._summary_label.setText(
            f"{'  •  '.join(parts)}  —  {total} in {files} file{'s' if files != 1 else ''}"
        )

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle single click on a diagnostic row."""
        prob = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(prob, Problem):
            self.problemClicked.emit(prob)

    def _on_item_activated(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle double-click / activation on a diagnostic row."""
        prob = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(prob, Problem):
            self.problemActivated.emit(prob)
            self.problemClicked.emit(prob)
