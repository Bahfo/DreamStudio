"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Diagnostic coordinator for DreamStudio.

This module owns *all* Problems state. Providers never touch the UI, and the
UI never merges provider output itself — both sides go through
:class:`DiagnosticStore`, which is the single source of truth for:

* **scope** — workspace (saved/disk) results versus active-buffer results;
* **staleness** — every result carries the workspace generation and the buffer
  revision it was produced from, and is rejected when either moved on;
* **dirty buffers** — while a document has unsaved edits the in-memory result
  is authoritative and disk results for that file are never surfaced;
* **de-duplication** — disk and buffer buckets are merged through the shared
  provider merge rules, so repeated scans never accumulate duplicates.

The Problems widget is a pure presentation layer on top of this store.
"""

from editor import *

import logging

from editor.analysis.providers import merge_problems
from editor.analysis.types import Problem

logger = logging.getLogger(__name__)

#: Bucket for built-in results derived from the file on disk.
BUCKET_DISK_AST = "disk_builtin"

#: Prefix for external provider buckets; one sub-bucket per provider source
#: (``disk_external:ruff``, ``disk_external:pyright``) so several providers can
#: report into the same file without replacing each other.
BUCKET_DISK_EXTERNAL = "disk_external"

#: Bucket for results derived from an in-memory editor buffer.
BUCKET_LIVE = "live"

#: Prefix for buffer-scope buckets when results are stored per provider.
BUCKET_LIVE_PREFIX = "live"


def external_bucket(source: str) -> str:
    """Return the disk bucket name reserved for provider *source*."""
    return f"{BUCKET_DISK_EXTERNAL}:{source}"


def live_bucket(source: str) -> str:
    """Return the buffer bucket name reserved for provider *source*."""
    return f"{BUCKET_LIVE_PREFIX}:{source}"


def _is_external(bucket: str) -> bool:
    """Return ``True`` for an external-provider bucket name."""
    return bucket == BUCKET_DISK_EXTERNAL or bucket.startswith(
        f"{BUCKET_DISK_EXTERNAL}:"
    )


def _is_live(bucket: str) -> bool:
    """Return ``True`` for a buffer-scope bucket name."""
    return bucket == BUCKET_LIVE or bucket.startswith(f"{BUCKET_LIVE_PREFIX}:")


class DiagnosticStore(QObject):
    """Single source of truth for the Problems panel and editor squiggles.

    Attributes:
        changed: Emitted with the list of file paths whose diagnostics
            changed. An empty list means "everything changed".

    Notes:
        Buckets are per provider (``disk_builtin``, ``disk_external:<source>``,
        ``live``) so AST, Ruff and basedpyright results coexist for one file
        and only the provider that produced a result can replace it.
    """

    changed = pyqtSignal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._generation: int = 0
        self._buckets: Dict[str, Dict[str, List[Problem]]] = {}
        self._live_revision: Dict[str, Dict[str, int]] = {}
        self._revision: Dict[str, int] = {}
        self._dirty: set = set()

    # ------------------------------------------------------------------
    # Generation / lifecycle
    # ------------------------------------------------------------------

    @property
    def generation(self) -> int:
        """Return the current workspace generation."""
        return self._generation

    def reset(self, generation: int) -> None:
        """Drop every cached result and start a new *generation*.

        Args:
            generation: Monotonic workspace generation. Results tagged with
                an older generation are rejected afterwards.
        """
        self._generation = int(generation)
        self._buckets = {}
        self._live_revision = {}
        self._revision = {}
        self._dirty = set()
        self.changed.emit([])

    def is_current(self, generation: object) -> bool:
        """Return ``True`` when *generation* is still the active one."""
        try:
            return int(generation) == int(self._generation)
        except (TypeError, ValueError):
            return False

    def clear_results(self) -> None:
        """Drop every cached diagnostic, keeping scope bookkeeping intact.

        Used by the panel's Clear action: dirty/revision state and the
        workspace generation survive so scanning policy keeps working while
        the visible results start from empty.
        """
        if not self._buckets:
            return
        self._buckets = {}
        self.changed.emit([])

    # ------------------------------------------------------------------
    # Buffer revisions (auto scope)
    # ------------------------------------------------------------------

    def note_buffer_change(self, path: str) -> int:
        """Record a new buffer state for *path* and return its revision.

        Args:
            path: Absolute path of the edited buffer.

        Returns:
            The revision that future analysis results must match.
        """
        if not path:
            return 0
        revision = self._revision.get(path, 0) + 1
        self._revision[path] = revision
        return revision

    def revision_for(self, path: str) -> int:
        """Return the latest known buffer revision for *path*."""
        if not path:
            return 0
        return self._revision.get(path, 0)

    # ------------------------------------------------------------------
    # Dirty state (saved vs unsaved documents)
    # ------------------------------------------------------------------

    def mark_dirty(self, path: str) -> None:
        """Declare *path* as having unsaved edits (buffer authoritative)."""
        if not path:
            return
        if path not in self._dirty:
            self._dirty.add(path)
            self.changed.emit([path])

    def mark_clean(self, path: str) -> bool:
        """Declare *path* saved again and discard its buffer diagnostics.

        Disk results for the file are dropped as well so nothing stale stays
        on screen until the post-save analysis completes.

        Args:
            path: Absolute path of the saved document.

        Returns:
            ``True`` when the document actually transitioned from dirty.
        """
        if not path:
            return False
        was_dirty = path in self._dirty
        self._dirty.discard(path)
        buckets = self._buckets.get(path)
        touched = False
        if buckets:
            for bucket in list(buckets):
                if buckets.pop(bucket, None) is not None:
                    touched = True
            if not buckets:
                self._buckets.pop(path, None)
        self._live_revision.pop(path, None)
        self.changed.emit([path])
        return was_dirty or touched

    def is_dirty(self, path: str) -> bool:
        """Return ``True`` when *path* has unsaved edits."""
        return path in self._dirty

    @property
    def dirty_paths(self) -> set:
        """Return the set of paths with unsaved edits."""
        return set(self._dirty)

    # ------------------------------------------------------------------
    # Result intake
    # ------------------------------------------------------------------

    def set_disk_results(
        self, results: Iterable[tuple], bucket: str = BUCKET_DISK_AST
    ) -> List[str]:
        """Store workspace-scope results produced from files on disk.

        Args:
            results: Iterable of ``(path, problems)`` pairs.
            bucket: :data:`BUCKET_DISK_AST` for the built-in provider,
                :data:`BUCKET_DISK_EXTERNAL` for external providers.

        Returns:
            Paths whose visible diagnostics changed.
        """
        touched: List[str] = []
        for entry in results or []:
            try:
                path, problems = entry
            except (TypeError, ValueError):
                continue
            if not path:
                continue
            previous = self.problems_for(path)
            self._set_bucket(path, bucket, problems)
            if self.problems_for(path) != previous:
                touched.append(path)
        return self._announce(touched)

    def set_external_results(
        self, problems: Iterable[Problem], source: str = "external"
    ) -> List[str]:
        """Store one whole-workspace external provider pass.

        Args:
            problems: Diagnostics from that provider. They replace only that
                provider's previous results, so several providers can report
                into the same file simultaneously.
            source: Provider tag (``"ruff"``, ``"pyright"`` …) selecting the
                sub-bucket this pass owns.

        Returns:
            Paths whose visible diagnostics changed.
        """
        bucket = external_bucket(source)
        grouped: Dict[str, List[Problem]] = {}
        for problem in problems or []:
            grouped.setdefault(problem.file_path, []).append(problem)
        touched: List[str] = []
        # A whole-workspace pass is authoritative for its own provider bucket:
        # drop its previous results first so fixed problems disappear instead
        # of lingering from an earlier scan.
        for path in list(self._buckets):
            if bucket in self._buckets[path]:
                previous = self.problems_for(path)
                self._set_bucket(path, bucket, [])
                if self.problems_for(path) != previous:
                    touched.append(path)
        for path, items in grouped.items():
            previous = self.problems_for(path)
            self._set_bucket(path, bucket, items)
            if self.problems_for(path) != previous:
                touched.append(path)
        return self._announce(touched)

    def set_live_results(
        self,
        path: str,
        revision: object,
        problems: Iterable[Problem],
        source: str = "all",
    ) -> List[str]:
        """Store buffer-scope results for a possibly unsaved document.

        The result is rejected when it was produced for an older buffer
        revision than the one currently known — this is what makes rapid
        typing and rapid undo/redo safe. Buffer results are kept per provider
        source, so a fast lint pass and a slower semantic pass can both
        contribute while only the newest revision stays visible.

        Args:
            path: Absolute path of the buffer.
            revision: Buffer revision the analysis was produced from.
            problems: Buffer diagnostics from that provider.
            source: Provider tag owning this sub-bucket (``"all"`` for an
                already-merged result).

        Returns:
            Paths whose visible diagnostics changed; empty when the result
            was rejected as stale.
        """
        if not path:
            return []
        try:
            revision = int(revision)
        except (TypeError, ValueError):
            return []
        if revision < self.revision_for(path):
            logger.debug("Discarding stale buffer result r%s for %s", revision, path)
            return []
        bucket = live_bucket(source)
        previous = self.problems_for(path)
        self._set_bucket(path, bucket, problems)
        self._live_revision.setdefault(path, {})[bucket] = revision
        self._drop_stale_live_buckets(path, revision)
        if self.problems_for(path) == previous:
            return []
        return self._announce([path])

    def _drop_stale_live_buckets(self, path: str, revision: int) -> None:
        """Hide buffer buckets produced from an older revision.

        Args:
            path: Absolute path of the buffer.
            revision: Revision that just became current.
        """
        revisions = self._live_revision.get(path, {})
        buckets = self._buckets.get(path)
        if not buckets:
            return
        for bucket in [key for key in buckets if _is_live(key)]:
            if revisions.get(bucket, revision) < revision:
                buckets.pop(bucket, None)
        if not buckets:
            self._buckets.pop(path, None)

    def live_revision_applied(self, path: str) -> int:
        """Return the newest buffer revision stored for *path*.

        Args:
            path: Absolute path of the buffer.

        Returns:
            Highest applied revision, or ``0`` when nothing was stored.
        """
        revisions = self._live_revision.get(path, {})
        return max(revisions.values()) if revisions else 0

    def purge_paths(self, paths: Iterable[str]) -> List[str]:
        """Drop on-disk results for files that no longer exist.

        Buffer-scope buckets survive so an open unsaved editor keeps its
        diagnostics; only saved-state results are discarded. A single
        announcement covers all purged paths.

        Args:
            paths: Absolute file paths to purge.

        Returns:
            Paths whose visible diagnostics changed.
        """
        touched: List[str] = []
        for path in paths or []:
            if not path:
                continue
            buckets = self._buckets.get(path)
            if not buckets:
                continue
            previous = self.problems_for(path)
            for bucket in [key for key in buckets if not _is_live(key)]:
                buckets.pop(bucket, None)
            if not buckets:
                self._buckets.pop(path, None)
            if self.problems_for(path) != previous:
                touched.append(path)
        return self._announce(touched)

    def set_paths(self, problems: Iterable[Problem]) -> List[str]:
        """Replace the whole state with *problems* (external callers).

        Args:
            problems: Diagnostics to display.

        Returns:
            Paths whose visible diagnostics changed.
        """
        self._buckets = {}
        grouped: Dict[str, List[Problem]] = {}
        for problem in problems or []:
            grouped.setdefault(problem.file_path, []).append(problem)
        touched: List[str] = []
        for path, items in grouped.items():
            previous = self.problems_for(path)
            self._set_bucket(path, BUCKET_DISK_AST, items)
            if self.problems_for(path) != previous:
                touched.append(path)
        return self._announce(touched)

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def problems(self) -> List[Problem]:
        """Return every visible diagnostic in display order.

        Returns:
            De-duplicated diagnostics for all tracked files.
        """
        visible: List[Problem] = []
        for path in sorted(self._buckets.keys(), key=lambda item: item.lower()):
            visible.extend(self.problems_for(path))
        return visible

    def problems_for(self, path: str) -> List[Problem]:
        """Return the visible diagnostics for *path*.

        While the document is dirty only buffer-scope results are visible, so
        a background workspace scan can never replace newer in-memory state
        with stale on-disk results.

        Args:
            path: Absolute file path.

        Returns:
            Merged, de-duplicated diagnostics (possibly empty). For a saved
            document the disk buckets and the buffer bucket are merged; for a
            dirty document only the buffer bucket is visible, so background
            workspace results can never replace newer in-memory state.
        """
        buckets = self._buckets.get(path)
        if not buckets:
            return []
        live = [
            item for key, items in buckets.items() if _is_live(key) for item in items
        ]
        if path in self._dirty:
            return merge_problems(live)
        external = [
            item
            for key, items in buckets.items()
            if _is_external(key)
            for item in items
        ]
        return merge_problems(live, buckets.get(BUCKET_DISK_AST) or [], external)

    def paths(self) -> List[str]:
        """Return every file path with cached diagnostics."""
        return list(self._buckets.keys())

    def has_results(self, path: str) -> bool:
        """Return ``True`` when *path* has any cached (visible or hidden) result."""
        return bool(self._buckets.get(path))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _set_bucket(self, path: str, bucket: str, problems: Iterable[Problem]) -> None:
        """Replace one bucket of *path* with *problems*."""
        entries = self._buckets.setdefault(path, {})
        items = list(problems or [])
        if items:
            entries[bucket] = items
        else:
            entries.pop(bucket, None)
        if not entries:
            self._buckets.pop(path, None)

    def _announce(self, touched: List[str]) -> List[str]:
        """Emit :attr:`changed` when *touched* is non-empty.

        Args:
            touched: Paths whose visible diagnostics changed.

        Returns:
            The deduplicated, sorted ``touched`` list.
        """
        unique = sorted({path for path in touched if path})
        if unique:
            self.changed.emit(unique)
        return unique
