"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Isolated Problems view for DreamStudio.

The widget knows nothing about analysis backends. It is a pure presentation
layer on top of :class:`~editor.analysis.diagnostic_store.DiagnosticStore`,
which owns all diagnostic state, scope decisions (active buffer vs workspace)
and staleness checks. Any provider (Ruff, spell checkers, language servers …)
feeds the store without touching this file, mirroring how Visual Studio
decouples its Error List from its analyzers.

Scanning policy is decided by *event type*, never by a user setting:

* **active buffer scope** — a debounced, off-thread re-analysis of the current
  editor text (AST + external providers via stdin) after typing, tab
  activation or save;
* **workspace scope** — an indexed, batched, off-thread sweep plus one
  external provider pass on workspace lifecycle events and on the explicit
  "Analyze Workspace" action.

Both always run; the user never chooses between them.
"""

from editor import *

import logging
import re

from editor.analysis.diagnostic_store import DiagnosticStore
from editor.analysis.types import Problem, ProblemSeverity
from editor.utils.resource_path import resource_path

logger = logging.getLogger(__name__)

#: Squiggle color per severity (red / yellow / blue / teal) — IDE theme
#: accents so indicators always look native.
SEVERITY_COLORS = {
    ProblemSeverity.ERROR: "#F14C4C",
    ProblemSeverity.WARNING: "#FCC700",
    ProblemSeverity.TYPO: "#3794FF",
    ProblemSeverity.INFO: "#4EC9B0",
}


#: Debounce before a workspace (re)index starts — rapid switches collapse.
_SCAN_DEBOUNCE_MS = 250

#: Quiet period after the last keystroke before the active buffer is
#: re-analyzed. Short enough that squiggles track typing, long enough that a
#: burst of keystrokes produces a single analysis.
_LIVE_DEBOUNCE_MS = 250

#: Files analyzed per background batch, keeping each worker slice short.
_LAZY_BATCH_SIZE = 24

#: Pause between batches so the GUI thread keeps a full event loop slice.
_LAZY_BATCH_GAP_MS = 40

#: How often the workspace is re-indexed for on-disk changes.
_LAZY_WATCH_INTERVAL_MS = 4000

_EDITOR_SUFFIXES = (".py", ".pyi")

_PROJECT_ROOT = Path(resource_path("."))
_ASSETS_SYSTEM = Path(resource_path("assets/system"))


def _severity_icon_name(severity: ProblemSeverity) -> str:
    """Return the asset filename for *severity*."""
    if severity == ProblemSeverity.WARNING:
        return "warning.png"
    if severity == ProblemSeverity.TYPO:
        return "spell_check.png"
    if severity == ProblemSeverity.INFO:
        return "info.png"
    return "problem.png"


def _load_icon(filename: str) -> QIcon:
    """Load a ``QIcon`` from ``assets/system``.

    Returns an empty icon when the file is missing so the UI never crashes
    on a missing optional asset.
    """
    path = _ASSETS_SYSTEM / filename
    if path.is_file():
        return QIcon(str(path))
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


#: Icon asset per diagnostic category, so different problem types are
#: distinguishable at a glance instead of collapsing onto the severity icon.
CATEGORY_ICONS = {
    "syntax": "problem.png",
    "name": "bug.png",
    "type": "problem.png",
    "unused": "info.png",
    "style": "spell_check.png",
    "marker": "warning.png",
}


def _hover_text(problem: Problem) -> str:
    """Build the editor hover text for *problem*.

    Args:
        problem: Diagnostic to describe.

    Returns:
        Multi-line string with rule code, message and provider name.
    """
    head = problem.code or problem.severity.value.title()
    lines = [f"{head}", problem.message]
    source = problem.source or "unknown"
    if problem.code:
        lines.append(f"Source: {source}")
    return "\n".join(lines)


class _IndexThread(QThread):
    """Off-GUI-thread workspace index (stat only, no file reads)."""

    indexed = pyqtSignal(int, object, int)

    def __init__(self, root: str, known: Optional[dict], gen: int, parent=None) -> None:
        super().__init__(parent)
        self._root = root
        self._known = known
        self._gen = gen

    def run(self) -> None:
        """Collect the file list; never touch GUI objects here."""
        entries: List[tuple] = []
        skipped = 0
        try:
            from editor.analysis.walker import index_python_files

            entries, skipped = index_python_files(self._root, self._known)
        except Exception as exc:
            logger.warning("Workspace index failed: %s", exc)
        self.indexed.emit(self._gen, entries, skipped)


class _BatchThread(QThread):
    """Off-GUI-thread analysis of one indexed batch of files.

    Every registered provider runs for each file; results are merged by the
    provider layer before they reach the GUI thread.
    """

    batch_done = pyqtSignal(int, object)

    def __init__(self, paths: List[str], gen: int, root: str, parent=None) -> None:
        super().__init__(parent)
        self._paths = paths
        self._gen = gen
        self._root = root

    def run(self) -> None:
        """Read + analyze the batch; never touch GUI objects here.

        Workspace scope deliberately uses the built-in provider only: one
        external process per file would make a sweep prohibitively expensive.
        External providers cover the workspace in a single pass instead.
        """
        from editor.analysis.providers import analyze_saved_file

        results: List[tuple] = []
        for path in self._paths:
            try:
                stat = os.stat(path)
                with open(path, "r", encoding="utf-8") as handle:
                    content = handle.read()
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                logger.debug("Batch skip %s: %s", path, exc)
                continue
            problems: List[Problem] = []
            try:
                problems = analyze_saved_file(path, content).problems
            except Exception as exc:
                logger.warning("Batch analyze failed %s: %s", path, exc)
                problems = []
            results.append((path, problems, stat.st_mtime, stat.st_size))
        self.batch_done.emit(self._gen, results)


class _LiveParseThread(QThread):
    """Off-GUI-thread analysis of the active buffer snapshot.

    Text is read on the GUI thread and parsed here, so external providers
    (which run as subprocesses) can never stall typing.
    """

    live_done = pyqtSignal(int, str, int, object, object, object, object)

    def __init__(
        self,
        path: str,
        text: str,
        gen: int,
        root: str,
        revision: int,
        semantic: bool = True,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._path = path
        self._text = text
        self._gen = gen
        self._root = root
        self._revision = revision
        self._semantic = semantic

    def run(self) -> None:
        """Analyze the snapshot; never touch GUI or disk objects here.

        The fast pass (built-in + Ruff stdin) is emitted first so squiggles
        appear immediately; the slower semantic pass follows and enriches the
        same file without disturbing the fast result.
        """
        from editor.analysis.providers import (
            analyze_buffer_fast,
            analyze_buffer_semantic,
        )

        problems: List[Problem] = []
        errors: List[str] = []
        notes: List[str] = []
        try:
            outcome = analyze_buffer_fast(self._path, self._text, self._root)
            problems = outcome.problems
            errors = outcome.errors
            notes = outcome.notes
        except Exception as exc:
            logger.warning("Live parse failed %s: %s", self._path, exc)
            errors = [str(exc)]
        self.live_done.emit(
            self._gen, self._path, self._revision, problems, errors, notes, None
        )

        if not self._semantic:
            return
        semantic: List[Problem] = []
        semantic_errors: List[str] = []
        semantic_notes: List[str] = []
        try:
            outcome = analyze_buffer_semantic(self._path, self._text, self._root)
            semantic = outcome.problems
            semantic_errors = outcome.errors
            semantic_notes = outcome.notes
        except Exception as exc:
            logger.warning("Live semantic analysis failed %s: %s", self._path, exc)
            semantic_errors = [str(exc)]
        self.live_done.emit(
            self._gen,
            self._path,
            self._revision,
            semantic,
            semantic_errors,
            semantic_notes,
            "pyright",
        )


class _WorkspaceProviderThread(QThread):
    """Off-GUI-thread whole-workspace pass of the external providers.

    Only external providers run here; the built-in provider keeps using the
    incremental batches so a workspace is never walked twice.
    """

    provider_done = pyqtSignal(int, object, object, object)

    def __init__(self, root: str, gen: int, parent=None) -> None:
        super().__init__(parent)
        self._root = root
        self._gen = gen

    def run(self) -> None:
        """Run the external workspace scan; never touch GUI objects here."""
        from editor.analysis.providers import scan_external_workspace

        groups: Dict[str, List[Problem]] = {}
        errors: List[str] = []
        notes: List[str] = []
        try:
            outcome = scan_external_workspace(self._root)
            groups = dict(outcome.groups or {})
            errors = outcome.errors
            notes = outcome.notes
        except Exception as exc:
            logger.warning("Workspace provider scan failed %s: %s", self._root, exc)
            errors = [str(exc)]
        self.provider_done.emit(self._gen, groups, errors, notes)


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
    countsChanged = pyqtSignal(int, int)
    providerError = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ProblemsWidget")
        self._problems: List[Problem] = []
        self._icons: Dict[ProblemSeverity, QIcon] = {
            ProblemSeverity.ERROR: _load_icon("problem.png"),
            ProblemSeverity.WARNING: _load_icon("warning.png"),
            ProblemSeverity.TYPO: _load_icon("spell_check.png"),
            ProblemSeverity.INFO: _load_icon("info.png"),
        }
        # Category icons (syntax / undefined name / unused / style …) let the
        # panel distinguish problem types beyond plain severity.
        self._category_icons: Dict[str, QIcon] = {
            category: _load_icon(asset) for category, asset in CATEGORY_ICONS.items()
        }
        # File-type icon cache (extension -> QIcon). Lazy-filled on demand.
        self._file_icons: Dict[str, QIcon] = {}
        self._scan_root: str = ""
        self._scan_gen: int = 0
        self._live_gen: int = 0
        self._pending_index: Optional[tuple] = None
        self._index_queue: List[tuple] = []
        self._queued_paths: set = set()
        self._file_stamps: Dict[str, tuple] = {}
        self._provider_errors: List[str] = []
        self._provider_notes: List[str] = []
        self._store = DiagnosticStore(self)
        self._store.changed.connect(self._on_store_changed)
        self._skipped_files: int = 0
        self._scan_busy: bool = False
        self._live_busy: bool = False
        self._semantic_busy: bool = False
        self._index_incremental: bool = False
        self._scan_timer = None
        self._live_timer = None
        self._watch_timer = None
        self._index_thread = None
        self._batch_thread = None
        self._live_thread = None
        self._provider_thread = None
        self._tracked_tabs = None
        self._live_editor = None
        self._dirty_signal_editors: List = []
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

        self._btn_refresh = QToolButton(header)
        self._btn_refresh.setToolTip(
            "Analyze Workspace — rescan the workspace and repopulate"
        )
        self._btn_refresh.setText("Analyze")
        self._btn_refresh.clicked.connect(self.analyze_workspace)
        h_layout.addWidget(self._btn_refresh)

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

    def set_problems(
        self, problems: Iterable[Union[Problem, dict]], skipped: int = 0
    ) -> None:
        """Replace the current diagnostics with *problems*.

        Args:
            problems: Iterable of :class:`Problem` or plain dicts with
                ``file_path``, ``severity`` (error/warning/typo),
                ``message``, ``line``, ``column``. Dicts are coerced via
                :meth:`Problem.from_dict` so callers may pass raw JSON.
            skipped: Number of files skipped during scan, shown distinctly
                from a clean result.
        """
        self._problems = _normalize_problems(problems)
        self._skipped_files = int(skipped or 0)
        self._active_filter: set | None = None
        self._store.set_paths(self._problems)
        self._render_all()

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
        """Remove all diagnostics and show the empty state.

        Cached provider results are dropped as well so the panel never
        contradicts the coordinator; the explicit "Analyze" action (or the
        next edit) repopulates it.
        """
        self._store.clear_results()
        self._problems = []
        self._rebuild()
        self._repaint_open_editors()

    def _show_analysis_error(self, detail: str) -> None:
        """Surface scan failure distinctly from a clean result."""
        self._problems = []
        try:
            self._tree.clear()
        except Exception:
            pass
        try:
            self._empty_label.setText(f"Analysis failed: {detail or 'unknown error'}")
        except Exception:
            pass
        try:
            self._stack.setCurrentIndex(1)
        except Exception:
            pass
        try:
            self._summary_label.setText("Analysis failed")
        except Exception:
            pass

    def get_problems(self) -> List[Problem]:
        """Return a copy of the current diagnostics."""
        return list(self._problems)

    def problem_count(self) -> int:
        """Return the total number of diagnostics."""
        return len(self._problems)

    def problem_counts(self) -> tuple:
        """Return current ``(errors, warnings)`` counts.

        Returns:
            Tuple of error and warning counts derived from the cache.
        """
        errors = sum(1 for p in self._problems if p.severity == ProblemSeverity.ERROR)
        warnings = sum(
            1 for p in self._problems if p.severity == ProblemSeverity.WARNING
        )
        return errors, warnings

    def analyze_workspace(self) -> None:
        """Explicit "Analyze Workspace" action.

        Drops every cached result and re-runs the full workspace scope:
        re-index, batched built-in analysis, external provider pass and a
        fresh active-buffer analysis. Also recovers from an accidental
        :meth:`clear` or an applied filter.
        """
        root = self._scan_root or os.getcwd()
        self._stop_timers()
        self._file_stamps = {}
        self._provider_errors = []
        self._provider_notes = []
        self._index_queue = []
        self._queued_paths = set()
        self._scan_gen += 1
        self._store.reset(self._scan_gen)
        self._active_filter = None
        self._problems = []
        self._rebuild()
        self.run_workspace_analysis(root)
        self._schedule_live_reparse(immediate=True)

    def refresh(self) -> None:
        """Alias of :meth:`analyze_workspace` kept for existing callers."""
        self.analyze_workspace()

    def request_file(self, path: str) -> None:
        """Ensure a single file is analyzed by the workspace scope.

        Used when a Python file is opened that has no cached diagnostics yet
        (including after a save, so results match the saved content).

        Args:
            path: Absolute path of the file to analyze.
        """
        if not path or not path.endswith(_EDITOR_SUFFIXES):
            return
        if not os.path.isfile(path):
            return
        if self._store.has_results(path) and self._store.revision_for(path) == 0:
            return
        try:
            stat = os.stat(path)
        except OSError:
            return
        self._enqueue([(path, stat.st_mtime, stat.st_size)])
        self._schedule_batch(0)

    def stop_scanning(self) -> None:
        """Stop every timer and drain worker threads (safe shutdown)."""
        self._stop_timers()
        for thread in (
            self._index_thread,
            self._batch_thread,
            self._live_thread,
            self._provider_thread,
        ):
            try:
                if thread is not None and thread.isRunning():
                    thread.wait(2000)
            except Exception:
                pass

    def _stop_timers(self) -> None:
        """Stop all debounce/watch timers owned by the scanner."""
        for timer in (self._scan_timer, self._live_timer, self._watch_timer):
            try:
                if timer is not None:
                    timer.stop()
            except Exception:
                pass

    def expand_all(self) -> None:
        """Expand every file group."""
        self._tree.expandAll()

    def collapse_all(self) -> None:
        """Collapse every file group."""
        self._tree.collapseAll()

    def _visible_problems(self) -> List[Problem]:
        """Return problems honoring the active severity filter."""
        active = getattr(self, "_active_filter", None)
        if active is None:
            return list(self._problems)
        return [p for p in self._problems if p.severity in active]

    def filter_by_severity(self, severities: Iterable[ProblemSeverity]) -> None:
        """Show only diagnostics whose severity is in *severities*.

        Args:
            severities: Collection of severities to keep visible. Pass an
                empty collection to hide all rows without mutating the
                underlying collection.
        """
        allowed = (
            {ProblemSeverity.coerce(s) for s in severities} if severities else set()
        )
        self._active_filter = allowed
        self._rebuild()

    # ------------------------------------------------------------------
    # Legacy bridge — keeps old callers working without importing
    # backends at module load time (widget stays isolated).
    # ------------------------------------------------------------------

    def run_workspace_analysis(self, workspace_root: str) -> None:
        """Start continuous scanning of *workspace_root* off the GUI thread.

        Two isolated workers keep the UI responsive: an indexer that only
        ``stat``s files, and short analysis batches that merge results into
        the per-file cache. Every batch hands control back to the event loop
        before the next one starts, so the GUI never blocks.

        Args:
            workspace_root: Directory to scan for Python diagnostics.
        """
        root = os.path.abspath(workspace_root or "")
        if not root or not os.path.isdir(root):
            self.set_problems([])
            return
        self._scan_gen += 1
        if root != self._scan_root:
            self._stop_timers()
            self._scan_root = root
            self._file_stamps = {}
            self._index_queue = []
            self._queued_paths = set()
            self._pending_index = (root, self._scan_gen, False)
            self._provider_errors = []
            self._provider_notes = []
            self._store.reset(self._scan_gen)
            self._debounce_index()
            return
        self._provider_errors = []
        self._provider_notes = []
        self._pending_index = (root, self._scan_gen, False)
        if not self._store.generation:
            self._store.reset(self._scan_gen)
        self._debounce_index()

    def _debounce_index(self) -> None:
        """Schedule the workspace index after the debounce window."""
        try:
            timer = self._scan_timer
            if timer is None:
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(self._start_pending_index)
                self._scan_timer = timer
            timer.start(_SCAN_DEBOUNCE_MS)
        except Exception:
            self._start_pending_index()

    def _start_pending_index(self) -> None:
        """Launch the workspace index on its worker thread."""
        pending = self._pending_index
        if pending is None:
            return
        try:
            if self._index_thread is not None and self._index_thread.isRunning():
                self._scan_timer.start(_SCAN_DEBOUNCE_MS)
                return
        except RuntimeError:
            pass
        root, gen, incremental = pending
        self._pending_index = None
        self._index_incremental = bool(incremental)
        known = self._file_stamps if incremental else None
        thread = _IndexThread(root, known, gen, parent=self)
        thread.indexed.connect(self._on_indexed)
        self._index_thread = thread
        thread.start()

    def _on_indexed(self, gen: object, entries: object, skipped: object) -> None:
        """Queue indexed files and pump analysis batches."""
        try:
            if int(gen) != int(self._scan_gen):
                return
        except (TypeError, ValueError):
            return
        try:
            self._skipped_files = int(skipped or 0)
        except (TypeError, ValueError):
            self._skipped_files = 0
        self._enqueue(entries if isinstance(entries, list) else [])
        self._start_watch_timer()
        if not getattr(self, "_index_incremental", False):
            self._start_workspace_providers()
        self._schedule_batch(0)

    def _enqueue(self, entries: List[tuple]) -> None:
        """Append ``(path, mtime, size)`` entries not already queued."""
        for entry in entries:
            try:
                path, mtime, size = entry
            except (TypeError, ValueError):
                continue
            if path in self._queued_paths:
                continue
            self._queued_paths.add(path)
            self._index_queue.append((path, mtime, size))

    def _schedule_batch(self, delay: int) -> None:
        """Schedule the next analysis batch after *delay* milliseconds."""
        QTimer.singleShot(max(0, int(delay)), self._start_batch)

    def _start_batch(self) -> None:
        """Analyze the next slice of the queue on a worker thread."""
        if self._scan_busy or not self._index_queue:
            return
        try:
            if self._batch_thread is not None and self._batch_thread.isRunning():
                self._scan_busy = True
                self._schedule_batch(_LAZY_BATCH_GAP_MS)
                return
        except RuntimeError:
            pass
        batch = self._index_queue[:_LAZY_BATCH_SIZE]
        del self._index_queue[: len(batch)]
        for path, _mtime, _size in batch:
            self._queued_paths.discard(path)
        gen = self._scan_gen
        self._scan_busy = True
        thread = _BatchThread(
            [path for path, _m, _s in batch], gen, self._scan_root, parent=self
        )
        thread.batch_done.connect(self._on_batch_done)
        self._batch_thread = thread
        thread.start()

    def _on_batch_done(self, gen: object, results: object) -> None:
        """Merge a finished batch and immediately schedule the next slice."""
        self._scan_busy = False
        try:
            stale = int(gen) != int(self._scan_gen)
        except (TypeError, ValueError):
            stale = True
        if not stale and isinstance(results, list):
            pairs = []
            for item in results:
                try:
                    path, problems, mtime, size = item
                except (TypeError, ValueError):
                    continue
                self._file_stamps[path] = (mtime, size)
                pairs.append((path, list(problems)))
            self._store.set_disk_results(pairs)
        self._schedule_batch(_LAZY_BATCH_GAP_MS)

    def _start_watch_timer(self) -> None:
        """Arm the repeating timer that re-indexes for on-disk changes."""
        timer = self._watch_timer
        if timer is None:
            timer = QTimer(self)
            timer.timeout.connect(self._on_watch_tick)
            self._watch_timer = timer
        if not timer.isActive():
            timer.start(_LAZY_WATCH_INTERVAL_MS)

    def _on_watch_tick(self) -> None:
        """Re-index the workspace and analyze only changed files."""
        if self._scan_busy or self._index_queue or self._pending_index is not None:
            return
        try:
            if self._index_thread is not None and self._index_thread.isRunning():
                return
        except RuntimeError:
            return
        root = self._scan_root
        if not root or not os.path.isdir(root):
            return
        self._pending_index = (root, self._scan_gen, True)
        self._start_pending_index()

    def _on_store_changed(self, touched: object) -> None:
        """Re-render the panel and editor squiggles from the coordinator.

        Args:
            touched: Paths whose diagnostics changed; an empty list means
                every tracked file changed.
        """
        paths = [path for path in (touched or []) if isinstance(path, str)]
        self._problems = self._store.problems()
        self._rebuild()
        if not paths:
            self._repaint_open_editors()
            return
        self._repaint_paths({path: self._store.problems_for(path) for path in paths})

    def _render_all(self) -> None:
        """Re-render everything from the coordinator state."""
        self._on_store_changed([])

    def _start_workspace_providers(self) -> None:
        """Launch the external whole-workspace provider pass."""
        root = self._scan_root
        if not root or not os.path.isdir(root):
            return
        try:
            if self._provider_thread is not None and self._provider_thread.isRunning():
                return
        except RuntimeError:
            pass
        thread = _WorkspaceProviderThread(root, self._scan_gen, parent=self)
        thread.provider_done.connect(self._on_provider_done)
        self._provider_thread = thread
        thread.start()

    def _on_provider_done(
        self, gen: object, groups: object, errors: object, notes: object = None
    ) -> None:
        """Merge external workspace diagnostics and record provider health.

        Each provider writes into its own coordinator bucket, so Ruff and the
        semantic provider coexist instead of replacing each other. Failures
        are surfaced (log + empty-state hint + :attr:`providerError`) instead
        of silently looking like a clean scan; capability notes are shown
        separately because a missing optional tool is not a failure.
        """
        try:
            if int(gen) != int(self._scan_gen):
                return
        except (TypeError, ValueError):
            return
        if isinstance(groups, list):
            groups = {"external": list(groups)}
        for source, items in (groups or {}).items():
            self._store.set_external_results(
                list(items) if isinstance(items, list) else [], source=source
            )
        self._record_provider_errors(errors)
        self._record_provider_notes(notes)
        self._update_summary()

    def _record_provider_errors(self, errors: object) -> None:
        """Merge provider failure messages into the visible provider status."""
        messages = (
            [str(item) for item in errors] if isinstance(errors, (list, tuple)) else []
        )
        merged = list(dict.fromkeys(self._provider_errors + messages))
        if merged != self._provider_errors:
            for message in merged:
                if message not in self._provider_errors:
                    logger.warning("Problems provider issue: %s", message)
                    self.providerError.emit(message)
        self._provider_errors = merged
        self._show_provider_status()

    def provider_errors(self) -> List[str]:
        """Return provider failure messages recorded by the scanner."""
        return list(self._provider_errors)

    def _record_provider_notes(self, notes: object) -> None:
        """Merge non-fatal provider notes into the visible provider status."""
        messages = (
            [str(item) for item in notes] if isinstance(notes, (list, tuple)) else []
        )
        merged = list(dict.fromkeys(self._provider_notes + messages))
        if merged != self._provider_notes:
            for message in merged:
                if message not in self._provider_notes:
                    logger.info("Problems provider note: %s", message)
        self._provider_notes = merged
        self._show_provider_status()

    def provider_notes(self) -> List[str]:
        """Return provider capability notes (missing optional tools)."""
        return list(self._provider_notes)

    def _show_provider_status(self) -> None:
        """Surface provider health in the header tooltip and empty state."""
        parts: List[str] = [f"failed: {message}" for message in self._provider_errors]
        parts += [f"note: {message}" for message in self._provider_notes]
        hint = "; ".join(parts)
        try:
            if self._provider_errors:
                tooltip = f"Provider issues — {hint}"
            elif self._provider_notes:
                tooltip = f"Provider notes — {hint}"
            else:
                tooltip = "All providers healthy"
            self._summary_label.setToolTip(tooltip)
            if self._provider_errors:
                self._empty_detail.setText(f"Provider issue: {hint}")
            elif self._provider_notes:
                self._empty_detail.setText(f"Some providers are unavailable: {hint}")
            else:
                self._empty_detail.setText(
                    "Build or open a workspace to see diagnostics grouped by file."
                )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Editor tracking — underlines + live re-parse of the active buffer
    # ------------------------------------------------------------------

    def track_tabs(self, tabs) -> None:
        """Follow tab switches so underlines stay in sync with editors.

        Args:
            tabs: Tab container exposing ``count()``, ``widget(i)`` and
                a ``currentChanged`` signal.
        """
        try:
            old = getattr(self, "_tracked_tabs", None)
            if old is not None:
                try:
                    old.currentChanged.disconnect(self._on_tracked_tab_changed)
                except (TypeError, RuntimeError):
                    pass
            self._tracked_tabs = tabs
            if tabs is None:
                return
            tabs.currentChanged.connect(self._on_tracked_tab_changed)
            self._sync_open_editors()
            self._attach_live(tabs.currentWidget())
            self._repaint_open_editors()
        except Exception:
            pass

    def _sync_open_editors(self) -> None:
        """Register every open editor for saved/unsaved tracking."""
        try:
            tabs = getattr(self, "_tracked_tabs", None)
            if tabs is None:
                return
            for index in range(tabs.count()):
                editor = self._unwrap_editor(tabs.widget(index))
                if editor is not None:
                    self._sync_dirty_state(editor)
        except Exception:
            pass

    def _on_tracked_tab_changed(self, _index: int = -1) -> None:
        """Activate the buffer scope for the newly focused tab.

        An editor becoming active is an automatic active-buffer event: its
        cached diagnostics are repainted and, when the file has never been
        analyzed, the workspace scope is asked to cover it.
        """
        try:
            tabs = getattr(self, "_tracked_tabs", None)
            if tabs is None:
                return
            widget = tabs.currentWidget()
            self._attach_live(widget)
            editor = self._unwrap_editor(widget)
            if editor is None:
                return
            path = getattr(editor, "current_file_path", "") or ""
            self._paint_editor(editor, self.problems_for(path))
            self._sync_dirty_state(editor)
            if path.endswith(_EDITOR_SUFFIXES) and not self._store.has_results(path):
                self.request_file(path)
        except Exception:
            pass

    def _attach_live(self, widget) -> None:
        """Point active-buffer tracking at *widget*'s editor."""
        try:
            self._set_live_tracking(False)
            editor = self._unwrap_editor(widget)
            self._live_editor = editor
            if editor is None:
                return
            self._set_live_tracking(True)
            self._sync_dirty_state(editor)
            self._schedule_live_reparse()
        except Exception:
            pass

    def _set_live_tracking(self, enabled: bool) -> None:
        """Connect or disconnect the typing listener on the active editor."""
        connected = bool(getattr(self, "_live_connected", False))
        if connected == enabled:
            return
        editor = getattr(self, "_live_editor", None)
        if editor is None:
            self._live_connected = False
            return
        try:
            signal = getattr(editor, "textChanged", None)
            if signal is None or not hasattr(signal, "connect"):
                self._live_connected = False
                return
            if enabled:
                signal.connect(self._on_buffer_changed)
            else:
                signal.disconnect(self._on_buffer_changed)
            self._live_connected = enabled
        except (TypeError, RuntimeError):
            self._live_connected = False

    def _on_buffer_changed(self) -> None:
        """Handle a keystroke in the active buffer.

        A new buffer revision invalidates any analysis still running for the
        previous text, and the debounced re-analysis of the latest text is
        (re)scheduled.
        """
        editor = getattr(self, "_live_editor", None)
        if editor is None:
            return
        path = getattr(editor, "current_file_path", "") or ""
        self._store.note_buffer_change(path)
        if path:
            self._store.mark_dirty(path)
        self._schedule_live_reparse()

    def _sync_dirty_state(self, editor) -> None:
        """Mirror an editor's saved/unsaved state into the coordinator.

        The dirty signal is connected once per editor, so a save is noticed
        even when the document became dirty after it was opened.

        Args:
            editor: Editor whose ``is_dirty()``/``dirty_state_changed`` state
                is authoritative for saved-vs-unsaved handling.
        """
        if editor is None:
            return
        self._connect_dirty_signal(editor)
        path = getattr(editor, "current_file_path", "") or ""
        if not path:
            return
        try:
            is_dirty = bool(editor.is_dirty())
        except Exception:
            is_dirty = False
        if is_dirty:
            self._store.mark_dirty(path)
            return
        if self._store.is_dirty(path):
            self._on_dirty_state_changed(path, False)

    def _connect_dirty_signal(self, editor) -> None:
        """Connect ``dirty_state_changed`` for *editor* exactly once."""
        for known in self._dirty_signal_editors:
            if known is editor:
                return
        signal = getattr(editor, "dirty_state_changed", None)
        if signal is None or not hasattr(signal, "connect"):
            return
        try:
            signal.connect(
                lambda state, ed=editor: self._on_editor_dirty_changed(ed, state)
            )
        except (TypeError, RuntimeError):
            return
        self._dirty_signal_editors.append(editor)

    def _on_editor_dirty_changed(self, editor, is_dirty: object) -> None:
        """Route an editor dirty event to the coordinator transition."""
        path = getattr(editor, "current_file_path", "") or ""
        if not path:
            return
        self._on_dirty_state_changed(path, bool(is_dirty))

    def _on_dirty_state_changed(self, path: str, is_dirty: object) -> None:
        """Transition a document between unsaved and saved state.

        On save the buffer-scope diagnostics are discarded and the file is
        re-analyzed from disk, so the panel reflects the saved content.

        Args:
            path: Absolute path of the document.
            is_dirty: New dirty flag reported by the editor.
        """
        if bool(is_dirty):
            self._store.mark_dirty(path)
            return
        self._store.mark_clean(path)
        editor = getattr(self, "_live_editor", None)
        if (
            editor is not None
            and (getattr(editor, "current_file_path", "") or "") == path
        ):
            self._store.note_buffer_change(path)
            self._schedule_live_reparse()
        if path.endswith(_EDITOR_SUFFIXES):
            self.request_file(path)
        self._repaint_paths({path: self._store.problems_for(path)})

    def _schedule_live_reparse(self, immediate: bool = False) -> None:
        """Restart the debounce timer for active-buffer analysis.

        Args:
            immediate: Parse on the next event-loop turn when ``True``.
        """
        try:
            timer = self._live_timer
            if timer is None:
                timer = QTimer(self)
                timer.setSingleShot(True)
                timer.timeout.connect(self._live_reparse_active)
                self._live_timer = timer
            timer.start(0 if immediate else _LIVE_DEBOUNCE_MS)
        except Exception:
            pass

    def _live_reparse_active(self) -> None:
        """Snapshot the active buffer and parse it on a worker thread."""
        try:
            editor = getattr(self, "_live_editor", None)
            if editor is None:
                return
            path = getattr(editor, "current_file_path", "") or ""
            if not path or not path.endswith(_EDITOR_SUFFIXES):
                return
            if self._live_busy:
                self._schedule_live_reparse()
                return
            try:
                text = editor.text()
            except Exception:
                return
            self._live_gen += 1
            self._live_busy = True
            revision = self._store.note_buffer_change(path)
            run_semantic = not self._semantic_busy
            self._semantic_busy = run_semantic
            thread = _LiveParseThread(
                path,
                text,
                self._live_gen,
                self._scan_root,
                revision,
                semantic=run_semantic,
                parent=self,
            )
            thread.live_done.connect(self._on_live_done)
            self._live_thread = thread
            thread.start()
        except Exception:
            self._live_busy = False
            self._semantic_busy = False

    def _on_live_done(
        self,
        gen: object,
        path: str,
        revision: object,
        problems: object,
        errors: object = None,
        notes: object = None,
        source: object = None,
    ) -> None:
        """Apply an active-buffer result, rejecting stale revisions.

        The coordinator compares the result's buffer revision with the latest
        known one, so a slow analysis of an older revision can never overwrite
        the diagnostics of the text currently in the editor. Results are stored
        per provider, so the fast lint pass and the slower semantic pass
        contribute independently.
        """
        provider = str(source) if source else None
        if provider is None:
            self._live_busy = False
        else:
            self._semantic_busy = False
        try:
            stale = int(gen) != int(self._live_gen)
        except (TypeError, ValueError):
            return
        if stale:
            # A semantic pass that finished for superseded text is discarded;
            # re-analyze so the newest revision still gets its semantic result.
            if provider is not None:
                self._schedule_live_reparse()
            return
        items = list(problems) if isinstance(problems, list) else []
        self._record_provider_errors(errors)
        self._record_provider_notes(notes)
        self._store.set_live_results(path, revision, items, source=provider or "all")

    @staticmethod
    def _unwrap_editor(widget):
        """Unwrap a tab widget to its ``CodeEditor``, if any."""
        if widget is None:
            return None
        try:
            from editor.Ironica.utils.minimap import ensure_inner

            editor = ensure_inner(widget)
            if editor is not None:
                return editor
        except Exception:
            pass
        if hasattr(widget, "set_diagnostics") and hasattr(widget, "text"):
            return widget
        return None

    def problems_for(self, path: str) -> list:
        """Return the visible diagnostics for *path*.

        Args:
            path: Absolute file path.

        Returns:
            Merged diagnostics owned by the coordinator for that file.
        """
        if not path:
            return []
        return self._store.problems_for(path)

    def _repaint_open_editors(self) -> None:
        """Paint cached diagnostics into every open editor by file path."""
        try:
            tabs = getattr(self, "_tracked_tabs", None)
            if tabs is None:
                return
            by_path: Dict[str, list] = {}
            for prob in self._problems:
                by_path.setdefault(prob.file_path, []).append(prob)
            count = tabs.count()
        except Exception:
            return
        for index in range(count):
            try:
                editor = self._unwrap_editor(tabs.widget(index))
            except Exception:
                continue
            if editor is None:
                continue
            path = getattr(editor, "current_file_path", "") or ""
            self._paint_editor(editor, by_path.get(path, []))

    def _repaint_paths(self, by_path: Dict[str, list]) -> None:
        """Repaint only the open editors whose path is in *by_path*."""
        painted: List[int] = []
        try:
            tabs = getattr(self, "_tracked_tabs", None)
            count = tabs.count() if tabs is not None else 0
        except Exception:
            count = 0
        for index in range(count):
            try:
                editor = self._unwrap_editor(tabs.widget(index))
                if editor is None:
                    continue
                path = getattr(editor, "current_file_path", "") or ""
                if path in by_path:
                    painted.append(id(editor))
                    self._paint_editor(editor, by_path[path])
            except Exception:
                continue
        live = getattr(self, "_live_editor", None)
        if live is not None and id(live) not in painted:
            try:
                path = getattr(live, "current_file_path", "") or ""
                if path in by_path:
                    self._paint_editor(live, by_path[path])
            except Exception:
                pass

    def _paint_editor(self, editor, problems: list) -> None:
        """Paint squiggle indicators for *problems* into *editor*.

        Uses the exact ranges reported by the analyzers (multi-line ranges
        included) instead of guessing token boundaries, and batches the whole
        result in a single call so the editor repaints once.

        Args:
            editor: Editor widget supporting diagnostic indicators.
            problems: Diagnostics visible for this editor's file.
        """
        try:
            setter = getattr(editor, "set_diagnostic_ranges", None)
            if setter is None:
                setter = getattr(editor, "set_diagnostics", None)
            clearer = getattr(editor, "clear_diagnostics", None)
            if setter is None or clearer is None:
                return
            from editor.analysis.providers import is_deemphasized

            ranges = []
            muted = []
            for problem in problems or []:
                start_line, start_col, end_line, end_col = problem.range_0based
                if is_deemphasized(problem):
                    muted.append((start_line, start_col, end_line, end_col))
                    continue
                ranges.append(
                    (
                        start_line,
                        start_col,
                        end_line,
                        end_col,
                        SEVERITY_COLORS.get(problem.severity, "#F14C4C"),
                    )
                )
            setter(ranges)
            muter = getattr(editor, "set_deemphasized_ranges", None)
            if muter is not None:
                muter(muted)
            labeller = getattr(editor, "set_diagnostic_labels", None)
            if labeller is not None:
                labels = []
                for problem in problems or []:
                    start_line, start_col, end_line, end_col = problem.range_0based
                    labels.append(
                        {
                            "start_line": start_line,
                            "start_col": start_col,
                            "end_line": end_line,
                            "end_col": end_col,
                            "text": _hover_text(problem),
                        }
                    )
                labeller(labels)
        except Exception:
            pass

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
        visible = self._visible_problems()
        if not visible:
            self._update_summary()
            try:
                skipped = getattr(self, "_skipped_files", 0) or 0
                provider_issues = list(getattr(self, "_provider_errors", []) or [])
                if provider_issues:
                    self._empty_label.setText(
                        "No problems, but some providers failed to run."
                    )
                    self._show_provider_status()
                elif skipped and not self._problems:
                    self._empty_label.setText(
                        f"No problems. Skipped {skipped} file(s)."
                    )
                elif not self._problems:
                    self._empty_label.setText("No problems have been detected.")
            except Exception:
                pass
            self._stack.setCurrentIndex(1)
            return

        self._stack.setCurrentIndex(0)
        grouped: Dict[str, List[Problem]] = {}
        for prob in visible:
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
            icon = self._icon_for(prob)
            if icon and not icon.isNull():
                child.setIcon(0, icon)
            # Message column: show code prefix when available.
            label = prob.message
            if prob.code:
                label = f"[{prob.code}] {label}"
            child.setText(0, label)
            child.setToolTip(
                0, f"{prob.message}\n{file_path}:{prob.line}:{prob.column}"
            )
            loc = f"[{prob.line}, {prob.column}]" if prob.column else f"[{prob.line}]"
            child.setText(1, loc)
            child.setTextAlignment(
                1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            child.setToolTip(1, f"{file_path}:{prob.line}:{prob.column}")
            child.setData(0, Qt.ItemDataRole.UserRole, prob)
            child.setData(0, Qt.ItemDataRole.UserRole + 1, "problem-row")

    def _update_summary(self) -> None:
        """Refresh the header summary label and publish counts."""
        errors, warnings = self.problem_counts()
        if not self._problems:
            self._summary_label.setText("No problems")
            self.countsChanged.emit(0, 0)
            return
        typos = sum(1 for p in self._problems if p.severity == ProblemSeverity.TYPO)
        parts: List[str] = []
        if errors:
            parts.append(f"{errors} Error{'s' if errors != 1 else ''}")
        if warnings:
            parts.append(f"{warnings} Warning{'s' if warnings != 1 else ''}")
        if typos:
            parts.append(f"{typos} Typo{'s' if typos != 1 else ''}")
        if not parts:
            parts.append(f"{len(self._problems)} Problems")
        total = len(self._problems)
        files = len({p.file_path for p in self._problems})
        self._summary_label.setText(
            f"{'  •  '.join(parts)}  —  {total} in {files} file{'s' if files != 1 else ''}"
        )
        self.countsChanged.emit(errors, warnings)

    def closeEvent(self, event) -> None:
        """Drain scanner workers before the widget is destroyed."""
        self.stop_scanning()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _icon_for(self, problem: Problem) -> QIcon:
        """Return the icon representing *problem*'s type.

        Falls back to the severity icon when the category has no dedicated
        asset or the asset is missing.

        Args:
            problem: Diagnostic to illustrate.

        Returns:
            A :class:`QIcon` (possibly null).
        """
        try:
            from editor.analysis.providers import diagnostic_category

            category = diagnostic_category(problem)
        except Exception:
            category = ""
        icon = self._category_icons.get(category)
        if icon is not None and not icon.isNull():
            return icon
        return self._icons.get(problem.severity) or self._icons[ProblemSeverity.ERROR]

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle single click on a diagnostic row.

        Emits :attr:`problemActivated` so the host can navigate to
        ``file_path:line:column`` with a single click, exactly as it does on
        double-click.
        """
        prob = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(prob, Problem):
            self.problemClicked.emit(prob)
            self.problemActivated.emit(prob)

    def _on_item_activated(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle double-click / activation on a diagnostic row."""
        prob = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(prob, Problem):
            self.problemActivated.emit(prob)
            self.problemClicked.emit(prob)
