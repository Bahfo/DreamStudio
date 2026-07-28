"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Consolidated folding utilities for DreamStudio.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget
from PyQt6.Qsci import QsciScintilla

logger = logging.getLogger(__name__)


@dataclass
class FoldRegion:
    """A single collapsible code region."""

    start_line: int
    end_line: int
    kind: str = "block"
    folded: bool = False
    uid: str = ""

    def __post_init__(self) -> None:
        if not self.uid:
            self.uid = f"{self.kind}:{self.start_line}:{self.end_line}"


class FoldMarginMarker(QWidget):
    """Custom-painted JetBrains-style fold marker."""

    def __init__(self, expanded: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        self._expanded = expanded
        self.setFixedSize(16, 16)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.update()

    def paintEvent(self, event) -> None:
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
        if not self._expanded:
            painter.drawLine(cx, cy - half, cx, cy + half)

        painter.end()


class FoldManager:
    """Language-agnostic fold region manager for a QsciScintilla editor."""

    FOLD_MARGIN = 3
    FOLD_MARGIN_WIDTH = 16

    def __init__(self, editor: QsciScintilla) -> None:
        if editor is None:
            raise ValueError("FoldManager requires a non-None editor")
        self._editor = editor
        self._regions: List[FoldRegion] = []
        self._setup_margin()
        self._connect_signals()

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

        e.markerDefine(
            QsciScintilla.MarkerSymbol.BoxedPlus, QsciScintilla.SC_MARKNUM_FOLDER
        )
        e.markerDefine(
            QsciScintilla.MarkerSymbol.BoxedMinus, QsciScintilla.SC_MARKNUM_FOLDEROPEN
        )
        e.markerDefine(
            QsciScintilla.MarkerSymbol.BoxedPlus, QsciScintilla.SC_MARKNUM_FOLDEREND
        )
        e.markerDefine(
            QsciScintilla.MarkerSymbol.BoxedMinus,
            QsciScintilla.SC_MARKNUM_FOLDEROPENMID,
        )
        e.markerDefine(
            QsciScintilla.MarkerSymbol.VerticalLine, QsciScintilla.SC_MARKNUM_FOLDERSUB
        )
        e.markerDefine(
            QsciScintilla.MarkerSymbol.VerticalLine,
            QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL,
        )
        e.markerDefine(
            QsciScintilla.MarkerSymbol.BottomLeftCorner,
            QsciScintilla.SC_MARKNUM_FOLDERTAIL,
        )

        e.setFoldMarginColors(mid, mid)

    def _connect_signals(self) -> None:
        self._editor.marginClicked.connect(self._on_margin_clicked)

    def _on_margin_clicked(self, margin: int, line: int, modifiers: int) -> None:
        """Handle click on a margin to toggle fold state."""
        if margin != self.FOLD_MARGIN:
            return

        region = self.get_region_at_line(line)
        if region is None:
            return

        if region.folded:
            self.expand_region(region)
        else:
            self.collapse_region(region)

    def register_fold_region(
        self, start_line: int, end_line: int, kind: str = "block"
    ) -> FoldRegion:
        region = FoldRegion(start_line=start_line, end_line=end_line, kind=kind)
        self._regions.append(region)
        return region

    def set_fold_regions(self, regions: List[FoldRegion]) -> None:
        """Bulk-replace all fold regions and re-apply fold levels."""
        old_folded: Dict[str, bool] = {
            r.uid: r.folded for r in self._regions if r.folded
        }
        for region in regions:
            if region.uid in old_folded:
                region.folded = old_folded[region.uid]

        self._regions = list(regions)
        self._apply_fold_levels()

    def clear_fold_regions(self) -> None:
        self._regions.clear()
        self._apply_fold_levels()

    def get_fold_regions(self) -> List[FoldRegion]:
        return list(self._regions)

    def get_region_at_line(self, line: int) -> Optional[FoldRegion]:
        for r in self._regions:
            if r.start_line == line:
                return r
        return None

    def _apply_fold_levels(self) -> None:
        """Translate the custom regions into working nested fold levels."""
        e = self._editor
        total_lines = e.lines()
        if total_lines == 0:
            return

        BASE = QsciScintilla.SC_FOLDLEVELBASE

        # Step 1: Initialize all lines back to base depth
        for ln in range(total_lines):
            e.SendScintilla(QsciScintilla.SCI_SETFOLDLEVEL, ln, BASE)

        # Step 2: Track line depths exclusively inside block bodies
        depth = [0] * total_lines
        for region in self._regions:
            s = max(0, region.start_line)
            end = min(total_lines - 1, region.end_line)
            if s >= total_lines or end < s:
                continue
            # Body lines are strictly greater than start_line to generate folding offsets
            for ln in range(s + 1, end + 1):
                depth[ln] += 1

        # Step 3: Map headers
        header_lines: Dict[int, FoldRegion] = {}
        for region in self._regions:
            if region.start_line < total_lines:
                header_lines[region.start_line] = region

        # Step 4: Write values to Scintilla core
        for ln in range(total_lines):
            level = BASE + depth[ln]
            if ln in header_lines:
                level |= QsciScintilla.SC_FOLDLEVELHEADERFLAG
            e.SendScintilla(QsciScintilla.SCI_SETFOLDLEVEL, ln, level)

        # Step 5: Restore state memory blocks across buffer updates
        for region in self._regions:
            if region.folded and region.start_line < total_lines:
                is_expanded = e.SendScintilla(
                    QsciScintilla.SCI_GETFOLDEXPANDED, region.start_line
                )
                if is_expanded:
                    e.SendScintilla(QsciScintilla.SCI_TOGGLEFOLD, region.start_line)

    def collapse_region(self, region: FoldRegion) -> None:
        if region.folded:
            return
        self._editor.SendScintilla(QsciScintilla.SCI_TOGGLEFOLD, region.start_line)
        region.folded = True

    def expand_region(self, region: FoldRegion) -> None:
        if not region.folded:
            return
        self._editor.SendScintilla(QsciScintilla.SCI_TOGGLEFOLD, region.start_line)
        region.folded = False

    def collapse_all(self) -> None:
        for region in self._regions:
            self.collapse_region(region)

    def expand_all(self) -> None:
        for region in self._regions:
            self.expand_region(region)

    def collapse_kind(self, kind: str) -> None:
        for region in self._regions:
            if region.kind == kind:
                self.collapse_region(region)

    def expand_kind(self, kind: str) -> None:
        for region in self._regions:
            if region.kind == kind:
                self.expand_region(region)
