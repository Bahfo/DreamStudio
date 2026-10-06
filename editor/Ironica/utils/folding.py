"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Consolidated folding utilities for DreamStudio.
"""

from __future__ import annotations

from editor import *

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

    # NOTE: Must stay in sync with CodeEditor.MARGIN_FOLD. Fold owns
    # margin 3; modified/saved owns margin 4 (last before text).
    FOLD_MARGIN = 3
    FOLD_MARGIN_WIDTH = 14
    ARROW_SIZE = 12

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
        margin = int(getattr(e, "MARGIN_FOLD", self.FOLD_MARGIN))

        e.setMarginType(margin, QsciScintilla.MarginType.SymbolMargin)
        e.setMarginWidth(margin, self.FOLD_MARGIN_WIDTH)
        e.setMarginSensitivity(margin, True)
        e.setMarginMarkerMask(margin, QsciScintilla.SC_MASK_FOLDERS)

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

    @staticmethod
    def _blend(first: QColor, second: QColor, amount: float) -> QColor:
        """Blend *first* toward *second* by *amount* (0.0-1.0).

        Args:
            first: Base colour.
            second: Colour to blend toward.
            amount: Blend factor clamped to ``0.0``-``1.0``.

        Returns:
            The blended ``QColor``.
        """
        t = max(0.0, min(1.0, amount))
        return QColor(
            int(first.red() + (second.red() - first.red()) * t),
            int(first.green() + (second.green() - first.green()) * t),
            int(first.blue() + (second.blue() - first.blue()) * t),
        )

    def _arrow_pixmap(
        self, color: QColor, up: bool, stem_color: QColor | None = None
    ) -> QPixmap:
        """Build a VS Code-style chevron-arrow pixmap for a fold header.

        The arrow is painted on an 8x supersampled canvas with a thin
        round-capped stroke and generous padding, then downscaled with
        smooth filtering at the screen's device pixel ratio so it
        renders soft and anti-aliased instead of pixelated. A short
        vertical stem below the chevron ties the header into the fold
        extent line drawn on the lines beneath it.

        Args:
            color: Chevron stroke colour.
            up: Chevron direction; ``True`` points toward the fold header.
            stem_color: Extent-line colour, or ``None`` for no stem.

        Returns:
            A DPR-aware ``QPixmap`` of logical size ``ARROW_SIZE``.
        """
        s = self.ARROW_SIZE
        scale = 8
        try:
            dpr = float(self._editor.devicePixelRatioF() or 1.0)
        except Exception:
            dpr = 1.0
        if dpr < 1.0:
            dpr = 1.0
        big = QImage(s * scale, s * scale, QImage.Format.Format_ARGB32)
        big.fill(QColor(0, 0, 0, 0))
        p = QPainter(big)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        pen = QPen(color, scale * 1.15)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        c = (s * scale) / 2.0
        arm = 3.0 * scale
        apex = c + (-arm * 0.8 if up else arm * 0.8)
        base = c + (arm * 0.8 if up else -arm * 0.8)
        p.drawLine(QPointF(c - arm, base), QPointF(c, apex))
        p.drawLine(QPointF(c, apex), QPointF(c + arm, base))
        if stem_color is not None:
            stem = QPen(stem_color, scale * 1.2)
            stem.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(stem)
            low = max(base, apex) + scale * 0.6
            p.drawLine(QPointF(c, low), QPointF(c, s * scale))
        p.end()
        target = max(1, int(round(s * dpr)))
        small = QPixmap.fromImage(
            big.scaled(
                target,
                target,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        small.setDevicePixelRatio(dpr)
        return small

    def _apply_theme_colours(self, e: QsciScintilla, bg: QColor) -> None:
        """Derive the fold-gutter colours from the editor background *bg*."""
        dark = bg.lightness() < 128
        if dark:
            arrow_colour = self._blend(QColor(197, 197, 197), bg, 0.35)
            line_colour = self._blend(QColor(128, 128, 128), bg, 0.25)
            mid = bg.lighter(107)
        else:
            arrow_colour = self._blend(QColor(80, 80, 80), bg, 0.35)
            line_colour = self._blend(QColor(160, 160, 160), bg, 0.25)
            mid = bg.darker(105)

        fold_markers = (
            QsciScintilla.SC_MARKNUM_FOLDER,
            QsciScintilla.SC_MARKNUM_FOLDEROPEN,
            QsciScintilla.SC_MARKNUM_FOLDEREND,
            QsciScintilla.SC_MARKNUM_FOLDEROPENMID,
            QsciScintilla.SC_MARKNUM_FOLDERSUB,
            QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL,
            QsciScintilla.SC_MARKNUM_FOLDERTAIL,
        )
        for marker in fold_markers:
            e.setMarkerBackgroundColor(mid, marker)
        e.setMarkerForegroundColor(line_colour, QsciScintilla.SC_MARKNUM_FOLDERSUB)
        e.setMarkerForegroundColor(line_colour, QsciScintilla.SC_MARKNUM_FOLDERMIDTAIL)
        e.setMarkerForegroundColor(line_colour, QsciScintilla.SC_MARKNUM_FOLDERTAIL)

        # A collapsed fold points back up toward its header; an expanded
        # fold points down into its body (VS Code chevron style).
        e.SendScintilla(
            QsciScintilla.SCI_MARKERDEFINEPIXMAP,
            QsciScintilla.SC_MARKNUM_FOLDER,
            self._arrow_pixmap(arrow_colour, up=True, stem_color=line_colour),
        )
        e.SendScintilla(
            QsciScintilla.SCI_MARKERDEFINEPIXMAP,
            QsciScintilla.SC_MARKNUM_FOLDEROPEN,
            self._arrow_pixmap(arrow_colour, up=False, stem_color=line_colour),
        )
        e.SendScintilla(
            QsciScintilla.SCI_MARKERDEFINEPIXMAP,
            QsciScintilla.SC_MARKNUM_FOLDEREND,
            self._arrow_pixmap(arrow_colour, up=True, stem_color=line_colour),
        )
        e.SendScintilla(
            QsciScintilla.SCI_MARKERDEFINEPIXMAP,
            QsciScintilla.SC_MARKNUM_FOLDEROPENMID,
            self._arrow_pixmap(arrow_colour, up=False, stem_color=line_colour),
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
        expected = int(getattr(self._editor, "MARGIN_FOLD", self.FOLD_MARGIN))
        if margin != expected:
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
        """Translate the custom regions into working nested fold levels.

        Writes every line exactly once (no separate reset pass) and
        accumulates nesting depth with a difference array, so the whole
        pass is ``O(lines + regions)`` with ``n`` Scintilla calls for
        ``n`` lines. Modification notifications are masked during the
        bulk write to avoid per-line re-layout churn.
        """
        e = self._editor
        total_lines = e.lines()
        if total_lines == 0:
            return

        BASE = QsciScintilla.SC_FOLDLEVELBASE
        HEADER = QsciScintilla.SC_FOLDLEVELHEADERFLAG

        depth_diff = [0] * (total_lines + 1)
        is_header = [False] * total_lines
        for region in self._regions:
            s = max(0, region.start_line)
            end = min(total_lines - 1, region.end_line)
            if 0 <= region.start_line < total_lines:
                is_header[region.start_line] = True
            if s >= total_lines or end <= s:
                continue
            depth_diff[s + 1] += 1
            if end + 1 < total_lines:
                depth_diff[end + 1] -= 1

        set_mask = getattr(QsciScintilla, "SCI_SETMODEVENTMASK", None)
        get_mask = getattr(QsciScintilla, "SCI_GETMODEVENTMASK", None)
        old_mask = None
        try:
            if set_mask is not None and get_mask is not None:
                try:
                    old_mask = e.SendScintilla(get_mask)
                    e.SendScintilla(set_mask, 0)
                except Exception:
                    old_mask = None
            running = 0
            for ln in range(total_lines):
                running += depth_diff[ln]
                level = BASE + running
                if is_header[ln]:
                    level |= HEADER
                e.SendScintilla(QsciScintilla.SCI_SETFOLDLEVEL, ln, level)
        finally:
            if old_mask is not None:
                try:
                    e.SendScintilla(set_mask, old_mask)
                except Exception:
                    pass

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
