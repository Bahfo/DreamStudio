# (C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""Thread-safe whole-document analysis bridge for DreamStudio.

Computes semantic highlights + fold regions off the main thread while
rendering the overlays back on the primary window buffer, so typing in
large files never blocks the UI.

CPU-bound Python analysis (ast / tokenize / jedi) holds the GIL, so it
cannot be made non-blocking with worker threads alone.  Remote-capable
providers (``remote_analysis = True``, e.g. the Python plugin) are sent
to a dedicated analysis-server subprocess; everything else falls back to
the in-process path, which keeps unit-test dummies dependency-free.
"""

from __future__ import annotations

from editor import *

from editor.Ironica.analysis_bridge import AnalysisProcessError
from editor.Ironica.process_manager import process_manager

logger = logging.getLogger("DreamStudio.Analysis.Worker")


@dataclass(frozen=True)
class _AnalysisRequest:
    """Immutable work item handed to the worker thread."""

    request_id: int
    source: str
    provider: object
    config: Optional[dict] = None
    theme_name: Optional[str] = None


class _AnalysisWorker(threading.Thread):
    """Runs provider analysis for the latest buffer (latest-wins).

    A plain ``threading.Thread`` (not a ``QThread``) so that an editor
    garbage-collected mid-analysis can never trip Qt's "QThread destroyed
    while running" abort; results are shipped back through the owner's
    signal, which is thread-safe to emit from any thread.
    """

    def __init__(self, owner: "AnalysisManager") -> None:
        super().__init__(name="DreamStudio-AnalysisWorker", daemon=True)
        self._owner = owner
        self._wake = threading.Event()
        self._started_once = False
        self._current_request: Optional[_AnalysisRequest] = None
        self._is_shutting_down = False

    def process(
        self,
        request_id: int,
        source: str,
        provider: object,
        config: Optional[dict] = None,
        theme_name: Optional[str] = None,
    ) -> None:
        """Enqueue the newest request, replacing any pending one."""
        if self._is_shutting_down:
            return
        self._current_request = _AnalysisRequest(
            request_id=request_id,
            source=source,
            provider=provider,
            config=config,
            theme_name=theme_name,
        )
        self._wake.set()
        if not self._started_once:
            self._started_once = True
            self.start()

    @staticmethod
    def _analyze(provider: object, source: str):
        """Compute semantic highlights + fold regions for *source*."""
        highlights = None
        fold_regions = None
        try:
            get_semantic = getattr(provider, "get_semantic_highlights", None)
            if callable(get_semantic):
                highlights = get_semantic(source)
            if getattr(provider, "has_folding", lambda: False)():
                fold_regions = provider.get_fold_regions(source)
        except Exception as exc:
            logger.error("Whole-document analysis failed: %s", exc)
            return None, None
        return highlights, fold_regions

    def _remote_analysis(self, request: _AnalysisRequest):
        """Ask the shared analysis subprocess to compute highlights + folds.

        The subprocess resolves the python config and theme itself, so
        only plain-data (source, config, theme) crosses the wire.

        Returns:
            ``(highlights, fold_regions)`` — or ``None`` if the request
            was dropped because this owner is no longer the focused tab.
        """
        response = process_manager.request(
            self._owner.owner_id,
            (
                "analysis",
                request.request_id,
                request.source,
                request.config,
                request.theme_name,
            ),
        )
        if response is None:
            return None
        if not isinstance(response, (tuple, list)) or not response:
            raise AnalysisProcessError(f"malformed server response: {response!r}")
        if response[0] != "analysis":
            raise AnalysisProcessError(f"server error: {response}")
        return response[2], response[3]

    def run(self) -> None:
        while not self._is_shutting_down:
            self._wake.wait(timeout=0.2)
            self._wake.clear()

            request = self._current_request
            if request is None:
                continue
            self._current_request = None

            if self._is_shutting_down:
                continue

            try:
                if getattr(request.provider, "remote_analysis", False):
                    try:
                        result = self._remote_analysis(request)
                        if result is None:
                            continue  # dropped — owner is no longer active
                        highlights, fold_regions = result
                    except Exception as exc:
                        if self._is_shutting_down or not process_manager.is_active(
                            self._owner.owner_id
                        ):
                            # Intentional teardown / lost focus — not a bug.
                            logger.debug("Analysis subprocess failed: %s", exc)
                            continue
                        logger.error("Analysis subprocess failed: %s", exc)
                        # Graceful degradation: compute in-process instead.
                        highlights, fold_regions = self._analyze(
                            request.provider, request.source
                        )
                else:
                    highlights, fold_regions = self._analyze(
                        request.provider, request.source
                    )
            except Exception as exc:
                logger.error("Analysis failed: %s", exc)
                highlights, fold_regions = None, None

            # A newer request may have arrived while we worked; only the
            # newest buffer's result is worth shipping back.
            if not self._is_shutting_down and self._current_request is None:
                try:
                    self._owner._results_ready.emit(
                        request.request_id, highlights, fold_regions
                    )
                except RuntimeError:
                    pass  # Owner torn down while we were computing

    def shutdown(self) -> None:
        """Stop the worker.

        The shared process is deliberately left untouched: it is owned by
        the process manager and stays warm for other tabs.  The worker is
        a daemon thread, so it simply exits once its current round-trip
        finishes — never blocking the caller on a busy child.
        """
        self._is_shutting_down = True
        self._current_request = None
        self._wake.set()


class AnalysisManager(QObject):
    """Latest-wins coordinator between a ``CodeEditor`` and the worker."""

    _results_ready = pyqtSignal(int, object, object)

    def __init__(
        self, editor, parent: Optional[QObject] = None
    ) -> None:
        """Create the manager, spawning a worker owned by this object.

        Args:
            editor: The ``CodeEditor`` whose text is analysed.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self._editor = editor
        self._owner_id = id(editor)
        self._enabled = True
        self._request_counter: int = 0
        self._worker = _AnalysisWorker(self)
        self._results_ready.connect(self._apply_results)
        destroyed = getattr(self._editor, "destroyed", None)
        if destroyed is not None:
            destroyed.connect(self.shutdown)

    @property
    def owner_id(self) -> int:
        return self._owner_id

    def set_enabled(self, active: bool) -> None:
        """Gate submission while this editor is not the focused tab."""
        self._enabled = active

    def is_enabled(self) -> bool:
        return self._enabled

    def invalidate(self) -> None:
        """Increment the request counter to invalidate any pending analysis."""
        self._request_counter += 1

    @pyqtSlot(str)
    def request_analysis(self, source: str) -> None:
        """Hand the latest buffer to the worker thread.

        Every submission gets a fresh request id so a slower (stale)
        evaluation can never be applied over a newer buffer.

        Args:
            source: The full editor buffer content.
        """
        if not self._enabled:
            return
        if not source:
            return
        provider = getattr(self._editor, "current_provider", None)
        if provider is None:
            return

        editor = self._editor
        lang = getattr(editor, "current_lang", None)
        config = None
        if lang:
            try:
                from editor.Ironica.language_engine import LanguageRegistry

                config = LanguageRegistry.get_config(lang)
            except Exception as exc:
                logger.debug("Unable to resolve language config: %s", exc)
        theme_name = getattr(editor, "_theme_name", None)

        self._request_counter += 1
        self._worker.process(
            self._request_counter, source, provider, config, theme_name
        )

    @pyqtSlot(int, object, object)
    def _apply_results(
        self, request_id: int, highlights, fold_regions
    ) -> None:
        """Render worker results back on the UI thread.

        Results for superseded requests are dropped so stale overlays
        never repaint a newer buffer.

        Args:
            request_id: Id of the request that produced these results.
            highlights: Semantic overlay list, or ``None``.
            fold_regions: Fold-region list, or ``None``.
        """
        if request_id < self._request_counter:
            return  # Drop out-of-order evaluations

        editor = self._editor
        try:
            if highlights is not None:
                editor._apply_semantic_overlays(highlights)
            if fold_regions is not None:
                editor._apply_fold_regions(fold_regions)
        except Exception as exc:
            logger.debug("Failed to apply analysis results: %s", exc)
        finally:
            try:
                editor._on_analysis_finished()
            except RuntimeError:
                pass

    def shutdown(self) -> None:
        """Shut the worker down before the editor is destroyed."""
        try:
            self._worker.shutdown()
        except Exception as exc:
            logger.debug("Analysis worker shutdown failed: %s", exc)
        process_manager.release(self._owner_id)
