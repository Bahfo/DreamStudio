from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

import json
from pathlib import Path


class _ToolCombo(QComboBox):
    CONTAINER_STYLE: str = """
        QFrame {
            background-color: #252526;
            border: 1px solid #3E3E42;
        }
    """

    def showPopup(self) -> None:
        try:
            self.view().setMinimumWidth(self.width())
        except Exception:
            pass
        super().showPopup()
        try:
            container = self.view().window()
            if container is None or container is self.window():
                return
            container.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            container.setStyleSheet(self.CONTAINER_STYLE)
            try:
                layout = container.layout()
                if layout is not None:
                    layout.setContentsMargins(0, 0, 0, 0)
                    layout.setSpacing(0)
            except Exception:
                pass
            width = max(self.width(), container.width())
            container.resize(width, container.height())
            anchor = self.mapToGlobal(QPoint(0, self.height()))
            try:
                screen = QApplication.primaryScreen()
                available = screen.availableGeometry() if screen else None
            except Exception:
                available = None
            if available is not None:
                if anchor.y() + container.height() > available.bottom():
                    anchor.setY(self.mapToGlobal(QPoint(0, 0)).y() - container.height())
                anchor.setX(
                    min(
                        anchor.x(),
                        available.right() - container.width() + 1,
                    )
                )
            container.move(anchor)
            container.update()
        except Exception:
            pass


class _Plug(QWidget):
    """Circular connection plug rendered on a node edge."""

    DIAMETER: int = 12

    def __init__(self, kind: str, index: int, parent=None) -> None:
        """Create a plug marker.

        Args:
            kind: ``"input"`` for left-edge plugs, anything else for
                right-edge output plugs.
            index: Zero-based plug number used for the tooltip.
            parent: Parent widget, expected to be the owning node.
        """
        super().__init__(parent)
        self._fill = QColor("#6BA368") if kind == "input" else QColor("#C98A3D")
        self.setFixedSize(self.DIAMETER, self.DIAMETER)
        label = "Input" if kind == "input" else "Output"
        self.setToolTip(f"{label} {index + 1}")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#141414"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.setBrush(QBrush(self._fill))
        painter.drawEllipse(1, 1, self.DIAMETER - 2, self.DIAMETER - 2)


class Node(QWidget):
    """
    Graphical node in the Nodes Designer canvas.
    """

    TOOL_OPTIONS: tuple = (
        "Compile",
        "Run Test",
        "Link",
        "Package",
        "Deploy",
        "Debug",
    )

    TOOL_MAP: dict = {
        "Compile": ("(Compilation Node)", "compile.json"),
        "Run Test": ("(Test Runner Node)", "run_test.json"),
        "Link": ("(Linker Node)", "link.json"),
        "Package": ("(Packaging Node)", "package.json"),
        "Deploy": ("(Deployment Node)", "deploy.json"),
        "Debug": ("(Debugging Node)", "debug.json"),
    }

    tool_changed = pyqtSignal(str)

    def __init__(
        self,
        node_title: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("Node")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self.setStyleSheet("""
            QWidget#Node { 
                border: 1px solid #888888; 
                border-radius: 6px;
                background-color: #2A2626;}
            """)

        self._drag_position = None
        self._default_title: str = node_title
        self._option_widgets: dict = {}
        self._options_container: QWidget | None = None
        self._options_layout: QVBoxLayout | None = None
        self._resize_animation: QPropertyAnimation | None = None
        self._input_plugs: list = []
        self._output_plugs: list = []

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(5, 5, 5, 5)
        self._layout.setSpacing(6)

        self.title_widget = QWidget()
        self._set_gradient()
        self.title_widget_layout = QHBoxLayout(self.title_widget)

        self.title = QLabel(node_title)
        self.title.setStyleSheet("""
            background: transparent;
            color: white;
            border: none;
        """)
        self.title_widget_layout.addWidget(self.title)

        self._layout.addWidget(self.title_widget)

        self._build_tool_row()
        self._init_options_container()

        self._layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.position().toPoint()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_position is not None:
            delta = event.position().toPoint() - self._drag_position
            self.move(self.pos() + delta)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_plugs()

    def _build_tool_row(self) -> None:
        """Build the Tool selector row beneath the title bar.

        Creates a ``Tool:`` label paired with a themed combo box
        offering the six pipeline actions. The selection is exposed
        via :attr:`selected_tool` and the :attr:`tool_changed` signal.
        """
        self.tool_row = QWidget()
        self.tool_row.setObjectName("ToolRow")
        self.tool_row.setStyleSheet("""
            QWidget#ToolRow {
                background: transparent;
                border: none;
            }
        """)
        row_layout = QHBoxLayout(self.tool_row)
        row_layout.setContentsMargins(2, 0, 2, 0)
        row_layout.setSpacing(8)

        self.tool_label = QLabel("Tool:")
        self.tool_label.setStyleSheet("""
            background: transparent;
            color: #C9C9C9;
            border: none;
        """)
        row_layout.addWidget(self.tool_label)

        self.tool_combo = _ToolCombo()
        self.tool_combo.setObjectName("ToolCombo")
        self.tool_combo.addItems(list(self.TOOL_OPTIONS))
        self.tool_combo.setStyleSheet("""
            QComboBox#ToolCombo {
                background-color: #1F1F1F;
                color: #F1F1F1;
                border: none;
                border-radius: 5px;
                padding: 4px 8px;
                min-height: 22px;
            }
            QComboBox#ToolCombo:hover {
                background-color: #2A2A2A;
            }
            QComboBox#ToolCombo:focus {
                background-color: #2A2A2A;
            }
            QComboBox#ToolCombo::drop-down {
                border: none;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background: #2D2D30;
                width: 22px;
            }
            QComboBox#ToolCombo QAbstractItemView {
                background-color: #252526;
                color: #F1F1F1;
                selection-background-color: #4D2E2E;
                selection-color: #FFFFFF;
                border: 1px solid #3E3E42;
                outline: none;
                padding: 2px;
            }
        """)

        popup = QListView()
        popup.setObjectName("ToolComboPopup")
        popup.setFrameShape(QFrame.Shape.NoFrame)
        popup.setFrameShadow(QFrame.Shadow.Plain)
        popup.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        popup.setStyleSheet("""
            QListView#ToolComboPopup {
                background-color: #252526;
                color: #F1F1F1;
                border: none;
                outline: none;
                padding: 2px;
            }
            QListView#ToolComboPopup::item {
                background: transparent;
                color: #F1F1F1;
                min-height: 22px;
                padding: 4px 8px;
                border: none;
            }
            QListView#ToolComboPopup::item:hover {
                background: #2A2A2A;
                color: #F1F1F1;
            }
            QListView#ToolComboPopup::item:selected {
                background: #4D2E2E;
                color: #FFFFFF;
            }
        """)
        try:
            popup_base = QColor("#252526")
            popup_palette = popup.palette()
            popup_palette.setColor(QPalette.ColorRole.Base, popup_base)
            popup.setPalette(popup_palette)
            popup.viewport().setPalette(popup_palette)
        except Exception:
            pass
        self.tool_combo.setView(popup)
        self.tool_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tool_combo.setCurrentIndex(-1)
        self.tool_combo.currentTextChanged.connect(self._on_tool_changed)
        row_layout.addWidget(self.tool_combo, 1)

        self._layout.addWidget(self.tool_row)

    @property
    def selected_tool(self) -> str:
        """Return the currently selected tool name."""
        try:
            return self.tool_combo.currentText()
        except Exception:
            return ""

    def _on_tool_changed(self, name: str) -> None:
        """Handle tool selection changes and build the matching node body.

        Args:
            name: Newly selected tool name from :attr:`tool_combo`.

        Returns:
            None. Emits :attr:`tool_changed`, updates the title, and
            builds or clears the options area with a smooth resize.
        """
        self.tool_changed.emit(name)

        if not name:
            return
        entry = self.TOOL_MAP.get(name)
        if entry is None:
            self.title.setText(self._default_title)
            self._clear_options()
            return
        node_title, json_name = entry
        self.title.setText(node_title)
        json_path = Path(__file__).resolve().parent / "json" / json_name
        self._build_options(json_path)

    def _init_options_container(self) -> None:
        """Create the hidden container that hosts JSON-built option rows.

        Returns:
            None. Inserts an empty hidden widget just above the bottom
            stretch so later builds expand the node downwards.
        """
        self._options_container = QWidget()
        self._options_container.setObjectName("OptionsContainer")
        self._options_container.setStyleSheet("""
            QWidget#OptionsContainer {
                background: transparent;
                border: none;
            }
        """)
        self._options_layout = QVBoxLayout(self._options_container)
        self._options_layout.setContentsMargins(16, 2, 16, 2)
        self._options_layout.setSpacing(6)
        self._options_container.setVisible(False)
        self._layout.insertWidget(self._layout.count() - 1, self._options_container)


    def _set_gradient(self, end_color: str = "#4D2E2E") -> None:
        """Apply the title-bar gradient via stylesheet.

        Args:
            end_color: Hex color of the gradient's right stop, taken
                from the active tool's JSON ``color`` entry. Invalid
                values fall back to the default maroon.

        Returns:
            None. Kept stylesheet-driven so it persists across repaints.
        """
        if not QColor(end_color).isValid():
            end_color = "#4D2E2E"
        self.title_widget.setStyleSheet(f"""
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
            stop: 0 #272222, stop: 1 {end_color});
            border: none;
            border-radius: 5px;
        """)

    def _build_options(self, json_file: str | Path) -> dict:
        """Build node option widgets from a static JSON description file.

        Reads files shaped like ``json/compile.json``::

            {"name": "compile", "color": "#4D2E2E",
             "properties": {"output-name": {"type": "QLineEdit", ...}, ...}}

        Supported ``type`` values are ``QLineEdit``, ``QCheckBox``,
        ``QComboBox`` and ``QListWidget`` (a checkable multi-select
        list). A ``nodes`` entry holding ``input``/``output`` counts
        defines the side plugs instead of an option row. Previous
        option rows are discarded first so the builder is idempotent.

        Args:
            json_file: Path to the JSON file describing the node options.

        Returns:
            Mapping of property key to the created input widget. Empty
            when the file is missing, invalid, or holds no properties.
        """
        self._reset_options_layout()

        try:
            with open(str(json_file), "r", encoding="utf-8") as handle:
                menu_data = json.load(handle)
        except FileNotFoundError:
            print(f"Options JSON not found: {json_file}")
            return {}
        except json.JSONDecodeError as exc:
            print(f"Error parsing JSON file: {exc}")
            return {}
        except OSError as exc:
            print(f"Error reading JSON file: {exc}")
            return {}

        if isinstance(menu_data, dict) and "properties" in menu_data:
            properties = menu_data.get("properties", {})
        elif isinstance(menu_data, dict):
            properties = menu_data
        else:
            print(f"Unsupported options JSON format: {json_file}")
            return {}

        if not isinstance(properties, dict):
            return {}

        nodes_spec = properties.pop("nodes", {})
        if not isinstance(nodes_spec, dict):
            nodes_spec = {}
        input_count = self._parse_plug_count(nodes_spec.get("input", 0))
        output_count = self._parse_plug_count(nodes_spec.get("output", 0))
        self._set_gradient(str(menu_data.get("color", "#4D2E2E")))

        for key, spec in properties.items():
            if not isinstance(spec, dict):
                continue
            widget_type = str(spec.get("type", ""))
            label_text = str(spec.get("name", key))
            if widget_type == "QLineEdit":
                row = self._make_label_row(label_text)
                editor = QLineEdit()
                editor.setText(str(spec.get("value", "")))
                editor.setStyleSheet(self._input_style())
                row.layout().addWidget(editor, 1)
                self._place_option_row(row)
                self._option_widgets[key] = editor
            elif widget_type == "QCheckBox":
                checkbox = QCheckBox(label_text)
                checkbox.setChecked(bool(spec.get("value", False)))
                checkbox.setStyleSheet(self._checkbox_style())
                self._place_option_row(checkbox)
                self._option_widgets[key] = checkbox
            elif widget_type == "QComboBox":
                row = self._make_label_row(label_text)
                combo = _ToolCombo()
                values = [str(v) for v in spec.get("values", [])]
                combo.addItems(values)
                if values:
                    combo.setCurrentIndex(0)
                combo.setStyleSheet(self._combo_style())
                row.layout().addWidget(combo, 1)
                self._place_option_row(row)
                self._option_widgets[key] = combo
            elif widget_type == "QListWidget":
                label = QLabel(label_text)
                label.setStyleSheet("""
                    background: transparent;
                    color: #C9C9C9;
                    border: none;
                """)
                self._place_option_row(label)
                check_list = QListWidget()
                check_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
                check_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                values = [str(v) for v in spec.get("values", [])]
                checked = spec.get("checked", spec.get("value", []))
                checked_set = {str(v) for v in checked} if isinstance(checked, list) else set()
                for value in values:
                    item = QListWidgetItem(value)
                    item.setFlags(
                        item.flags()
                        | Qt.ItemFlag.ItemIsUserCheckable
                        | Qt.ItemFlag.ItemIsEnabled
                    )
                    if value in checked_set:
                        item.setCheckState(Qt.CheckState.Checked)
                    else:
                        item.setCheckState(Qt.CheckState.Unchecked)
                    check_list.addItem(item)
                visible_rows = min(max(len(values), 1), 5)
                check_list.setFixedHeight(visible_rows * 28 + 6)
                check_list.setStyleSheet(self._list_style())
                self._place_option_row(check_list)
                self._option_widgets[key] = check_list
            else:
                continue

        if self._options_container is not None:
            self._options_container.setVisible(True)
        self._build_plugs(input_count, output_count)
        self._animate_expand()
        return dict(self._option_widgets)

    def _clear_options(self) -> None:
        """Remove built option rows and shrink the node back down.

        Returns:
            None. Hides the options container and animates the node
            back to its collapsed height.
        """
        self._reset_options_layout()
        self._clear_plugs()
        self._set_gradient()
        if self._options_container is not None:
            self._options_container.setVisible(False)
        self._animate_collapse()

    def _reset_options_layout(self) -> None:
        """Discard existing option rows and widget references.

        Returns:
            None.
        """
        self._option_widgets = {}
        if self._options_layout is None:
            return
        while self._options_layout.count():
            item = self._options_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setVisible(False)
                widget.setParent(None)
                widget.deleteLater()

    def _place_option_row(self, widget: QWidget) -> None:
        """Insert a row widget into the options layout and show it.

        Args:
            widget: Row, checkbox, label, or list to display.

        Returns:
            None. Showing explicitly keeps the row counted in size
            hints even when the container is already visible, so the
            node measures and animates to the true content height.
        """
        if self._options_layout is None:
            return
        self._options_layout.addWidget(widget)
        widget.setVisible(True)


    def _parse_plug_count(self, raw: object) -> int:
        """Normalize a plug count from JSON into a safe integer.

        Args:
            raw: Raw ``input``/``output`` value from the ``nodes``
                JSON entry.

        Returns:
            Count clamped to the 0..8 range; 0 for non-numeric input.
        """
        try:
            count = int(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0
        return max(0, min(8, count))

    def _build_plugs(self, input_count: int, output_count: int) -> None:
        """Create input plugs on the left edge and outputs on the right.

        Args:
            input_count: Number of left-edge input plugs to render.
            output_count: Number of right-edge output plugs to render.

        Returns:
            None. Replaces any previously built plugs.
        """
        self._clear_plugs()
        for index in range(input_count):
            plug = _Plug("input", index, self)
            plug.show()
            self._input_plugs.append(plug)
        for index in range(output_count):
            plug = _Plug("output", index, self)
            plug.show()
            self._output_plugs.append(plug)
        self._position_plugs()

    def _clear_plugs(self) -> None:
        """Remove all rendered side plugs.

        Returns:
            None.
        """
        for plug in self._input_plugs + self._output_plugs:
            plug.setVisible(False)
            plug.setParent(None)
            plug.deleteLater()
        self._input_plugs = []
        self._output_plugs = []

    def _position_plugs(self) -> None:
        """Spread plugs evenly along the left and right node edges.

        Returns:
            None. Called after builds and on every resize so plugs
            track the animated node height.
        """
        if not self._input_plugs and not self._output_plugs:
            return
        top = (
            self.title_widget.height()
            + self.tool_row.height()
            + self._layout.contentsMargins().top()
            + 12
        )
        bottom = self.height() - 12
        if bottom <= top:
            bottom = top + 1
        for plugs, is_input in ((self._input_plugs, True), (self._output_plugs, False)):
            count = len(plugs)
            for index, plug in enumerate(plugs):
                if count <= 1:
                    y = (top + bottom) // 2 - _Plug.DIAMETER // 2
                else:
                    span = bottom - top - _Plug.DIAMETER
                    y = top + round(index * span / (count - 1))
                x = 0 if is_input else self.width() - _Plug.DIAMETER
                plug.move(x, y)

    def _make_label_row(self, label_text: str) -> QWidget:
        """Create a horizontal ``label + stretch`` row for an option.

        Args:
            label_text: Display name shown on the left of the row.

        Returns:
            Container widget whose layout the caller extends with an
            input widget.
        """
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(2, 0, 2, 0)
        row_layout.setSpacing(8)
        label = QLabel(label_text)
        label.setStyleSheet("""
            background: transparent;
            color: #C9C9C9;
            border: none;
        """)
        row_layout.addWidget(label)
        return row

    def _input_style(self) -> str:
        """Return the shared dark stylesheet for line-edit inputs.

        Returns:
            Stylesheet string applied to ``QLineEdit`` option widgets.
        """
        return """
            QLineEdit {
                background-color: #1F1F1F;
                color: #F1F1F1;
                border: 1px solid #3E3E42;
                border-radius: 5px;
                padding: 4px 8px;
                min-height: 20px;
            }
            QLineEdit:focus {
                border: 1px solid #6E3A3A;
            }
        """

    def _checkbox_style(self) -> str:
        """Return the shared dark stylesheet for checkbox options.

        Returns:
            Stylesheet string applied to ``QCheckBox`` option widgets.
        """
        return """
            QCheckBox {
                background: transparent;
                color: #F1F1F1;
                border: none;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border-radius: 3px;
                border: 1px solid #3E3E42;
                background: #1F1F1F;
            }
            QCheckBox::indicator:checked {
                background: #4D2E2E;
                border: 1px solid #6E3A3A;
            }
        """

    def _combo_style(self) -> str:
        """Return the shared dark stylesheet for combo option widgets.

        Returns:
            Stylesheet string applied to ``QComboBox`` option widgets.
        """
        return """
            QComboBox {
                background-color: #1F1F1F;
                color: #F1F1F1;
                border: none;
                border-radius: 5px;
                padding: 4px 8px;
                min-height: 22px;
            }
            QComboBox:hover {
                background-color: #2A2A2A;
            }
        """

    def _list_style(self) -> str:
        """Return the shared dark stylesheet for checkable list options.

        Returns:
            Stylesheet string applied to ``QListWidget`` option widgets.
        """
        return """
            QListWidget {
                background-color: #1F1F1F;
                color: #F1F1F1;
                border: 1px solid #3E3E42;
                border-radius: 5px;
                outline: none;
                padding: 2px;
            }
            QListWidget::item {
                background: transparent;
                min-height: 22px;
                padding: 2px 4px;
                border: none;
            }
            QListWidget::item:hover {
                background: #2A2A2A;
            }
            QListWidget::indicator {
                width: 15px;
                height: 15px;
                border-radius: 3px;
                border: 1px solid #3E3E42;
                background: #252526;
            }
            QListWidget::indicator:checked {
                background: #4D2E2E;
                border: 1px solid #6E3A3A;
            }
        """

    def _animate_expand(self) -> None:
        """Smoothly resize the node to fit the freshly built options.

        Returns:
            None. Starts a short ``InOutCubic`` size animation aimed
            exactly at the layout's current size hint, growing or
            shrinking so the height always fits the contents.
        """
        if self._options_container is None:
            return
        self._options_container.updateGeometry()
        self._layout.activate()
        hint = self.sizeHint()
        target = QSize(max(self.width(), hint.width()), hint.height())
        self._animate_resize(target)

    def _animate_collapse(self) -> None:
        """Smoothly shrink the node after its options were cleared.

        Returns:
            None. Animates back to the collapsed size hint while
            keeping the current width.
        """
        self._layout.activate()
        hint = self.sizeHint()
        target = QSize(self.width(), max(hint.height(), self.minimumSizeHint().height()))
        self._animate_resize(target)

    def _animate_resize(self, target: QSize) -> None:
        """Animate the node ``size`` property towards *target*.

        Args:
            target: Desired final node size after the animation.

        Returns:
            None.
        """
        try:
            if self._resize_animation is not None:
                self._resize_animation.stop()
        except Exception:
            pass
        self._resize_animation = QPropertyAnimation(self, b"size", self)
        self._resize_animation.setDuration(350)
        self._resize_animation.setStartValue(self.size())
        self._resize_animation.setEndValue(target)
        self._resize_animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._resize_animation.start()
