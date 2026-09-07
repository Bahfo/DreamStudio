"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

ELF information popover widget for DreamStudio.

Compact QWidget that behaves like a tooltip/popover attached to the
gutter button. Shows textual summary plus structured section table.
"""

from __future__ import annotations

from editor import *

from editor.Ironica.inspector.binding import ElfHeader, ElfSection

logger = logging.getLogger(__name__)


class ElfInfoPopup(QFrame):
    """Compact ELF inspection popover.

    Layout:
        QFrame (styled)
         -> header/title
         -> summary QLabel (rich text)
         -> separator
         -> QTableWidget (sections)

    Behaviour:
        * Frameless, ToolTip-like, does not steal focus
        * Positioned relative to gutter button via ``move_near()``
        * Adapts position if insufficient room
        * Closes on Esc, outside click, or explicit ``close()``
        * Follows QSS/theme via palette, no hard-coded colors in Python
          beyond resolving from palette.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent,
            Qt.WindowType.ToolTip
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setObjectName("ElfInfoPopup")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setLineWidth(1)

        self._init_ui()
        self._apply_theme()

        # Close when clicking outside — we install event filter on parent/app
        self._outside_filter_installed = False

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        # Header
        self._header = QLabel(self)
        self._header.setObjectName("ElfPopupHeader")
        self._header.setTextFormat(Qt.TextFormat.RichText)
        self._header.setWordWrap(True)
        self._header.setText("ELF Inspection")
        outer.addWidget(self._header)

        # Summary
        self._summary = QLabel(self)
        self._summary.setObjectName("ElfPopupSummary")
        self._summary.setTextFormat(Qt.TextFormat.RichText)
        self._summary.setWordWrap(True)
        self._summary.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        outer.addWidget(self._summary)

        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setObjectName("ElfPopupSeparator")
        outer.addWidget(sep)

        # Section table label
        lbl = QLabel("Sections", self)
        lbl.setObjectName("ElfPopupSectionLabel")
        outer.addWidget(lbl)

        self._table = QTableWidget(self)
        self._table.setObjectName("ElfPopupTable")
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["#", "Name", "Type", "Address", "Offset", "Size", "Flags"]
        )
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(True)
        self._table.setSortingEnabled(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self._table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._table.setMinimumHeight(180)
        self._table.setMaximumHeight(320)
        outer.addWidget(self._table, 1)

        # Close hint
        hint = QLabel("Press Esc to close • Click outside to dismiss", self)
        hint.setObjectName("ElfPopupHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignRight)
        outer.addWidget(hint)

        self.resize(720, 420)
        self.setMinimumWidth(680)
        self.setMaximumWidth(820)

    def _apply_theme(self) -> None:
        """Derive colors from palette so QSS can theme us."""
        try:
            pal = self.palette() if self.parent() is None else self.parent().palette()
            bg = pal.color(QPalette.ColorRole.Window)
            border = pal.color(QPalette.ColorRole.Mid)
            base = pal.color(QPalette.ColorRole.Base)
            is_dark = bg.lightness() < 128
            if is_dark:
                card_bg = bg.lighter(108).name()
                header_bg = bg.lighter(112).name()
            else:
                card_bg = "#FFFFFF"
                header_bg = bg.name()
            self.setStyleSheet(
                f"QFrame#ElfInfoPopup {{"
                f" background-color: {card_bg};"
                f" border: 1px solid {border.name()};"
                f" border-radius: 6px;"
                f"}}"
                f"QLabel#ElfPopupHeader {{"
                f" font-size: 14px; font-weight: 700; padding: 2px 0px;"
                f"}}"
                f"QLabel#ElfPopupHint {{"
                f" color: #888888; font-size: 10px; padding: 2px 0px;"
                f"}}"
            )
        except Exception:
            pass

    def changeEvent(self, event) -> None:
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            if getattr(self, "_in_change_event", False):
                super().changeEvent(event)
                return
            self._in_change_event = True
            try:
                self._apply_theme()
            finally:
                self._in_change_event = False
        super().changeEvent(event)

    def set_content(
        self,
        file_name: str,
        header: ElfHeader | None,
        sections: list[ElfSection],
        version: str = "",
    ) -> None:
        """Populate popup with ELF header + sections.

        Args:
            file_name: Display file name.
            header: Parsed ELF header or None.
            sections: Parsed sections list.
            version: Inspector version string.
        """
        safe_name = html.escape(file_name) if file_name else "Binary"
        if header is None:
            self._header.setText(f"<b>{safe_name}</b> — ELF inspection failed")
            self._summary.setText(
                "<i>File could not be parsed as ELF. "
                "No header information available.</i>"
            )
            self._table.setRowCount(0)
            return

        self._header.setText(f"<b>{safe_name}</b> — ELF Inspection")

        # Summary: human-readable text with both table data repeated in prose
        file_format = "ELF"
        entry_hex = f"0x{header.entry:X}"
        ph_off = f"0x{header.program_header_offset:X}"
        sh_off = f"0x{header.section_header_offset:X}"
        summary_html = (
            f"<div style='line-height:1.4'>"
            f"<b>{html.escape(header.class_name)}</b> &bull; "
            f"{html.escape(header.data_name)} &bull; "
            f"{html.escape(header.machine_name)}<br/>"
            f"Type: {html.escape(header.type_name)}<br/>"
            f"Entry: <code>{entry_hex}</code> &nbsp; "
            f"PH off: <code>{ph_off}</code> &nbsp; "
            f"SH off: <code>{sh_off}</code><br/>"
            f"Program headers: {header.program_header_count} &nbsp; "
            f"Section headers: {header.section_header_count} &nbsp; "
            f"SHSTR index: {header.section_name_string_table_index}<br/>"
            f"File format: {file_format} &nbsp; "
            f"Inspector: v{html.escape(version) if version else '—'}"
            f"</div>"
        )
        self._summary.setText(summary_html)

        # Table
        self._table.setRowCount(len(sections))
        for row, sec in enumerate(sections):
            vals = [
                str(sec.index),
                sec.name if sec.name else "(no name)",
                sec.type_name,
                f"0x{sec.address:X}",
                f"0x{sec.offset:X}",
                str(sec.size),
                sec.flags_name,
            ]
            for col, txt in enumerate(vals):
                item = QTableWidgetItem(txt)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                # Align numeric columns right
                if col in (0, 3, 4, 5):
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                self._table.setItem(row, col, item)

        # Resize columns sensibly
        try:
            self._table.resizeColumnsToContents()
            # Give extra to Name column
            self._table.horizontalHeader().setSectionResizeMode(
                1, QHeaderView.ResizeMode.Stretch
            )
        except Exception:
            pass

    def move_near(
        self, anchor_widget: QWidget, editor_widget: QWidget | None = None
    ) -> None:
        """Position popup near *anchor_widget* (gutter button).

        Uses ``mapToGlobal`` and adapts if insufficient room below/adjacent.
        Keeps popup inside screen and inside application window when possible.
        """
        try:
            # Global position of button's bottom-left
            anchor_rect = anchor_widget.rect()
            global_pos = anchor_widget.mapToGlobal(QPoint(0, anchor_rect.height() + 4))
            self.adjustSize()
            pw = self.width()
            ph = self.height()

            screen = QGuiApplication.screenAt(global_pos)
            if screen is None:
                screen = QGuiApplication.primaryScreen()
            if screen is not None:
                avail = screen.availableGeometry()
                # Horizontal: keep inside screen
                if global_pos.x() + pw > avail.right() - 8:
                    global_pos.setX(max(avail.left() + 8, avail.right() - pw - 8))
                # Vertical: flip above if not enough room below
                if global_pos.y() + ph > avail.bottom() - 8:
                    above = anchor_widget.mapToGlobal(QPoint(0, -ph - 4))
                    if above.y() >= avail.top() + 8:
                        global_pos = above
                    else:
                        global_pos.setY(max(avail.top() + 8, avail.bottom() - ph - 8))

            # Also ensure inside application window if provided
            if editor_widget is not None:
                try:
                    win = editor_widget.window()
                    if win is not None:
                        win_geo = win.geometry()
                        # Clamp to window if window is smaller than screen
                        if global_pos.x() + pw > win_geo.right() - 8:
                            global_pos.setX(
                                max(win_geo.left() + 8, win_geo.right() - pw - 8)
                            )
                        if global_pos.y() + ph > win_geo.bottom() - 8:
                            global_pos.setY(
                                max(win_geo.top() + 8, win_geo.bottom() - ph - 8)
                            )
                except Exception:
                    pass

            self.move(global_pos)
        except Exception as exc:
            logger.debug("ElfInfoPopup positioning failed: %s", exc)
            # Fallback: center near anchor
            try:
                self.move(anchor_widget.mapToGlobal(QPoint(0, anchor_widget.height())))
            except Exception:
                pass

    def show_near(
        self, anchor_widget: QWidget, editor_widget: QWidget | None = None
    ) -> None:
        """Show popup positioned near *anchor_widget*."""
        self.move_near(anchor_widget, editor_widget)
        self.show()
        try:
            self.raise_()
        except Exception:
            pass
        self._install_outside_filter()

    def _install_outside_filter(self) -> None:
        if self._outside_filter_installed:
            return
        app = QApplication.instance()
        if app is not None:
            try:
                app.installEventFilter(self)
                self._outside_filter_installed = True
            except Exception:
                pass

    def _remove_outside_filter(self) -> None:
        if not self._outside_filter_installed:
            return
        app = QApplication.instance()
        if app is not None:
            try:
                app.removeEventFilter(self)
            except Exception:
                pass
        self._outside_filter_installed = False

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if self.isVisible():
            et = event.type()
            if et == QEvent.Type.MouseButtonPress:
                try:
                    if isinstance(watched, QWidget):
                        pos = (
                            event.globalPosition().toPoint()
                            if hasattr(event, "globalPosition")
                            else event.globalPos()
                        )
                        if not self.geometry().contains(
                            self.mapFromGlobal(pos)
                        ) and not self.rect().contains(pos):
                            if not self._is_inside_popup_or_anchor(pos):
                                self.close()
                    else:
                        gpos = (
                            event.globalPosition().toPoint()
                            if hasattr(event, "globalPosition")
                            else None
                        )
                        if gpos is not None and not self.geometry().contains(gpos):
                            self.close()
                except Exception:
                    pass
            elif et == QEvent.Type.KeyPress:
                try:
                    if event.key() == Qt.Key.Key_Escape:
                        self.close()
                        return True
                except Exception:
                    pass
        return super().eventFilter(watched, event)

    def _is_inside_popup_or_anchor(self, global_pos: QPoint) -> bool:
        try:
            if self.geometry().contains(global_pos):
                return True
        except Exception:
            pass
        return False

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._remove_outside_filter()
        super().closeEvent(event)

    def hideEvent(self, event) -> None:
        self._remove_outside_filter()
        super().hideEvent(event)
