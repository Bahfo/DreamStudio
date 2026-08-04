"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Consolidated folding utilities for DreamStudio.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from PyQt6.QtCore import QPointF, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QPixmap
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
    ARROW_SIZE = 14

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

        # Tail markers share a thin vertical connecting line; the fold
        # headers (up/down chevrons) are drawn as pixmaps in
        # ``_apply_theme_colours``.
        for marker in (
            QsciScintilla.SC_MARKNUM_FOLDERSUB,
            QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL,
            QsciScintilla.SC_MARKNUM_FOLDERTAIL,
        ):
            e.markerDefine(QsciScintilla.MarkerSymbol.VerticalLine, marker)

        self._apply_colours(e)

    def _arrow_pixmap(self, color: QColor, up: bool) -> QPixmap:
        """Build a VS Code-style chevron-arrow pixmap for a fold header.

        *up* points the chevron toward the top of the fold; otherwise it
        points toward the body below the header.
        """
        s = self.ARROW_SIZE
        pm = QPixmap(s, s)
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(color, 2.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        c = s / 2.0
        arm = 4.5
        apex = c + (-arm * 0.8 if up else arm * 0.8)
        base = c + (arm * 0.8 if up else -arm * 0.8)
        p.drawLine(QPointF(c - arm, base), QPointF(c, apex))
        p.drawLine(QPointF(c, apex), QPointF(c + arm, base))
        p.end()
        return pm

    def _apply_theme_colours(self, e: QsciScintilla, bg: QColor) -> None:
        """Derive the fold-gutter colours from the editor background *bg*."""
        dark = bg.lightness() < 128
        arrow_colour = QColor(197, 197, 197) if dark else QColor(80, 80, 80)
        line_colour = QColor(128, 128, 128) if dark else QColor(160, 160, 160)
        mid = bg.lighter(130) if dark else bg.darker(115)

        e.setMarkerForegroundColor(line_colour, QsciScintilla.SC_MARKNUM_FOLDERSUB)
        e.setMarkerForegroundColor(line_colour, QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)
        e.setMarkerForegroundColor(line_colour, QsciScintilla.SC_MARKNUM_FOLDERTAIL)

        # A collapsed fold points back up toward its header; an expanded
        # fold points down into its body (VS Code chevron style).
        e.SendScintilla(
            QsciScintilla.SCI_MARKERDEFINEPIXMAP,
            QsciScintilla.SC_MARKNUM_FOLDER,
            self._arrow_pixmap(arrow_colour, up=True),
        )
        e.SendScintilla(
            QsciScintilla.SCI_MARKERDEFINEPIXMAP,
            QsciScintilla.SC_MARKNUM_FOLDEROPEN,
            self._arrow_pixmap(arrow_colour, up=False),
        )
        e.SendScintilla(
            QsciScintilla.SCI_MARKERDEFINEPIXMAP,
            QsciScintilla.SC_MARKNUM_FOLDEREND,
            self._arrow_pixmap(arrow_colour, up=True),
        )
        e.SendScintilla(
            QsciScintilla.SCI_MARKERDEFINEPIXMAP,
            QsciScintilla.SC_MARKNUM_FOLDEROPENMID,
            self._arrow_pixmap(arrow_colour, up=False),
        )

        e.setFoldMarginColors(mid, mid)

    def _apply_colours(self, e: QsciScintilla) -> None:
        """Apply the fold-margin colours from the editor's palette.

        The colours are derived from the editor's current palette so a
        theme switch can re-run this method to keep the fold gutter in
        sync with the active theme.
        """
        pal = e.palette()
        bg = pal.color(pal.ColorRole.Window)
        self._apply_theme_colours(e, bg)

    def retheme(self, bg: QColor) -> None:
        """Recolour the fold gutter after a theme change.

        The gutter background uses a shade of the editor background
        (*bg*) so it stays visually anchored to the active theme.
        """
        self._apply_theme_colours(self._editor, bg)

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
