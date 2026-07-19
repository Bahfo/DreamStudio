"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Consolidated folding utilities for DreamStudio.

This module is the single source of truth for all fold-related
data models and the language-agnostic ``FoldManager`` that controls
QScintilla's internal margin and folding UI.

Language-specific folding logic (e.g. Python indentation parsing)
lives in ``editor.texteditor.plugins.<lang>.folding`` and imports
the ``FoldRegion`` dataclass from here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget
from PyQt6.Qsci import QsciScintilla

logger = logging.getLogger(__name__)


# ==================================================================
# Data models
# ==================================================================


@dataclass
class FoldRegion:
    """A single collapsible code region.

    Attributes:
        start_line: First line of the foldable block (0-indexed).
        end_line:   Last line of the foldable block (0-indexed, inclusive).
        label:      Optional placeholder text shown when collapsed
                    (e.g. ``"..."`` or ``"# 5 hidden lines"``).
        kind:       Category tag for the region (``"import"``,
                    ``"class"``, ``"function"``, ``"block"``, etc.).
        folded:     Whether the region is currently collapsed.
    """
    start_line: int
    end_line: int
    label: str = "..."
    kind: str = "block"
    folded: bool = False


# ==================================================================
# Custom fold margin marker (JetBrains-style)
# ==================================================================


class FoldMarginMarker(QWidget):
    """Custom-painted fold marker replacing QScintilla's default
    ugly box-style markers.

    Renders a clean JetBrains-style ``+`` / ``-`` indicator inside
    a rounded rectangle with smooth antialiased lines.
    """

    def __init__(self, expanded: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._expanded = expanded
        self.setFixedSize(16, 16)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(100, 100, 100, 60)
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.PenStyle.NoPen)
        r = self.rect().adjusted(1, 1, -1, -1)
        painter.drawEllipse(r)

        painter.setPen(QPen(QColor(200, 200, 200), 1.5))
        cx, cy = r.center().x(), r.center().y()
        half = 3
        painter.drawLine(cx - half, cy, cx + half, cy)
        if self._expanded:
            painter.drawLine(cx, cy - half, cx, cy + half)

        painter.end()


# ==================================================================
# FoldManager — language-agnostic fold region controller
# ==================================================================


class FoldManager:
    """Language-agnostic fold region manager for a ``QsciScintilla``
    editor.

    ``FoldManager`` owns:

    - A dedicated QScintilla margin (Margin 1 by default) for fold
      markers.
    - The list of ``FoldRegion`` objects registered by language
      plugins.
    - Custom ``FoldMarginMarker`` painting for clean visual
      indicators.

    Language plugins call :meth:`register_fold_region` (or
    :meth:`set_fold_regions` for bulk updates) to tell the manager
    where collapsible blocks exist.  The manager translates these
    into QScintilla fold levels on the appropriate margin.

    **Lifecycle:**

    1. Created once per ``CodeEditor``.
    2. Language plugin calls ``set_fold_regions(...)`` after loading
       or editing a file.
    3. User clicks a fold marker -> QScintilla toggles fold level ->
       manager synchronises its ``FoldRegion.folded`` state.

    **Margin layout (JetBrains standard)::**

        [Margin 0: Line Numbers] [Margin 1: Folding] [Text]
    """

    FOLD_MARGIN = 1
    FOLD_MARGIN_WIDTH = 16

    def __init__(self, editor: QsciScintilla) -> None:
        if editor is None:
            raise ValueError("FoldManager requires a non-None editor")
        self._editor = editor
        self._regions: List[FoldRegion] = []
        self._setup_margin()

    # ------------------------------------------------------------------
    # Margin configuration
    # ------------------------------------------------------------------

    def _setup_margin(self) -> None:
        """Configure the dedicated fold margin with clean markers."""
        e = self._editor

        e.setMarginType(self.FOLD_MARGIN, QsciScintilla.MarginType.SymbolMargin)
        e.setMarginWidth(self.FOLD_MARGIN, self.FOLD_MARGIN_WIDTH)
        e.setMarginSensitivity(self.FOLD_MARGIN, True)
        e.setMarginMarkerMask(self.FOLD_MARGIN, QsciScintilla.SC_MASK_FOLDERS)

        pal = e.palette()
        bg = pal.color(pal.ColorRole.Window)
        mid = bg.lighter(130) if bg.lightness() < 128 else bg.darker(115)

        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDER)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDEREND)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDERTAIL)
        e.setMarkerForegroundColor(mid, QsciScintilla.SC_MARKNUM_FOLDERSUB)

        e.markerDefine(QsciScintilla.MarkerSymbol.BoxedPlus, QsciScintilla.SC_MARKNUM_FOLDER)
        e.markerDefine(QsciScintilla.MarkerSymbol.BoxedMinus, QsciScintilla.SC_MARKNUM_FOLDEROPEN)
        e.markerDefine(QsciScintilla.MarkerSymbol.BoxedPlus, QsciScintilla.SC_MARKNUM_FOLDEREND)
        e.markerDefine(QsciScintilla.MarkerSymbol.BoxedMinus, QsciScintilla.SC_MARKNUM_FOLDEROPENMID)
        e.markerDefine(QsciScintilla.MarkerSymbol.VerticalLine, QsciScintilla.SC_MARKNUM_FOLDERSUB)
        e.markerDefine(QsciScintilla.MarkerSymbol.VerticalLine, QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)
        e.markerDefine(QsciScintilla.MarkerSymbol.BottomLeftCorner, QsciScintilla.SC_MARKNUM_FOLDERTAIL)

        e.setFoldMarginColors(mid, mid)
        e.setFolding(QsciScintilla.FoldStyle.PlainFoldStyle)

    # ------------------------------------------------------------------
    # Public API — region registration
    # ------------------------------------------------------------------

    def register_fold_region(
        self,
        start_line: int,
        end_line: int,
        label: str = "...",
        kind: str = "block",
    ) -> FoldRegion:
        """Register a single collapsible code region."""
        region = FoldRegion(
            start_line=start_line,
            end_line=end_line,
            label=label,
            kind=kind,
        )
        self._regions.append(region)
        return region

    def set_fold_regions(self, regions: List[FoldRegion]) -> None:
        """Bulk-replace all fold regions and re-apply fold levels."""
        self._regions = list(regions)
        self._apply_fold_levels()

    def clear_fold_regions(self) -> None:
        """Remove all fold regions and reset the margin."""
        self._regions.clear()
        self._apply_fold_levels()

    def get_fold_regions(self) -> List[FoldRegion]:
        """Return the current list of fold regions (read-only copy)."""
        return list(self._regions)

    def get_region_at_line(self, line: int) -> Optional[FoldRegion]:
        """Return the ``FoldRegion`` that starts on *line*, or ``None``."""
        for r in self._regions:
            if r.start_line == line:
                return r
        return None

    # ------------------------------------------------------------------
    # Fold level application
    # ------------------------------------------------------------------

    def _apply_fold_levels(self) -> None:
        """Translate the ``_regions`` list into QScintilla fold levels."""
        e = self._editor
        total_lines = e.lines()
        if total_lines == 0:
            return

        e.SendScintilla(QsciScintilla.SCI_SETFOLDFLAGS, 0)

        for ln in range(total_lines):
            e.SendScintilla(QsciScintilla.SCI_SETFOLDLEVEL, ln, 0)

        for region in self._regions:
            s = max(0, region.start_line)
            end = min(total_lines - 1, region.end_line)

            if s >= total_lines or end < s:
                continue

            header_level = 0 | QsciScintilla.SC_FOLDLEVELHEADERFLAG
            e.SendScintilla(QsciScintilla.SCI_SETFOLDLEVEL, s, header_level)

            for ln in range(s + 1, end + 1):
                e.SendScintilla(QsciScintilla.SCI_SETFOLDLEVEL, ln, 1)

            if end + 1 < total_lines:
                e.SendScintilla(QsciScintilla.SCI_SETFOLDLEVEL, end + 1, 0)

    # ------------------------------------------------------------------
    # Collapse / expand helpers
    # ------------------------------------------------------------------

    def collapse_region(self, region: FoldRegion) -> None:
        """Collapse a specific fold region."""
        if region.folded:
            return
        self._editor.SendScintilla(QsciScintilla.SCI_TOGGLEFOLD, region.start_line)
        region.folded = True

    def expand_region(self, region: FoldRegion) -> None:
        """Expand a previously collapsed fold region."""
        if not region.folded:
            return
        self._editor.SendScintilla(QsciScintilla.SCI_TOGGLEFOLD, region.start_line)
        region.folded = False

    def collapse_all(self) -> None:
        """Collapse all registered fold regions."""
        for region in self._regions:
            self.collapse_region(region)

    def expand_all(self) -> None:
        """Expand all registered fold regions."""
        for region in self._regions:
            self.expand_region(region)

    def collapse_kind(self, kind: str) -> None:
        """Collapse all regions matching *kind*."""
        for region in self._regions:
            if region.kind == kind:
                self.collapse_region(region)

    def expand_kind(self, kind: str) -> None:
        """Expand all regions matching *kind*."""
        for region in self._regions:
            if region.kind == kind:
                self.expand_region(region)
