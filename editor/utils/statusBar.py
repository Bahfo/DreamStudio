from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QComboBox,
    QLabel,
    QProgressBar,
    QListWidget,
)


class BootstrapDetailMenu(QFrame):
    def __init__(self, messages, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("BootstrapDetailMenu")
        self.setFixedSize(500, 350)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(36)
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(12, 0, 12, 0)
        self.title_label = QLabel("Bootstrap Progress")
        self.title_label.setStyleSheet("color: #FFFFFF; font-size: 13px; font-weight: bold; background: transparent;")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        layout.addWidget(self.title_bar)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                color: #CCCCCC;
                border: none;
                font-size: 12px;
                font-family: monospace;
                padding: 8px;
            }
            QListWidget::item {
                padding: 3px 6px;
                border-bottom: 1px solid #2A2D30;
            }
        """)
        for msg in messages:
            self.list_widget.addItem(msg)
        self.list_widget.scrollToBottom()
        layout.addWidget(self.list_widget)

    def add_message(self, msg):
        self.list_widget.addItem(msg)
        self.list_widget.scrollToBottom()

    def retheme(self, t):
        bg = t.color("window.background", "#1E1E1E")
        text = t.color("widget.text", "#CCCCCC")
        border = t.color("widget.border", "#3C3C3C")
        title_bg = t.color("titlebar.background", "#25272B")
        title_text = t.color("titlebar.text", "#FFFFFF")
        item_border = t.color("widget.border", "#2A2D30")

        self.title_label.setStyleSheet(
            f"color: {title_text}; font-size: 13px; font-weight: bold; background: transparent;"
        )
        self.title_bar.setStyleSheet(f"background-color: {title_bg}; border-bottom: 1px solid {border};")

        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg};
                color: {text};
                border: none;
                font-size: 12px;
                font-family: monospace;
                padding: 8px;
            }}
            QListWidget::item {{
                padding: 3px 6px;
                border-bottom: 1px solid {item_border};
            }}
        """)


class StatusBar(QFrame):
    bootstrap_done = pyqtSignal(bool)

    def __init__(self, master):
        super().__init__(master)
        self._saved_btn_fixed = None

        self.setFrameShape(QFrame.Shape.Panel)
        self.setFixedHeight(30)
        self.setStyleSheet("""
        QFrame{
        border: 0;
        border-radius: 0px;
        background-color: #25272B;
        }""")
        statusbar_layout = QHBoxLayout(self)
        statusbar_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        statusbar_layout.setContentsMargins(5, 0, 5, 0)

        self.zoomBtn = QComboBox()
        self.zoomBtn.setFixedSize(40, 28)
        self.zoomBtn.addItems(["75%", "100%", "110%", "125%"])
        self.zoomBtn.view().setMinimumWidth(80)
        self.zoomBtn.setCurrentIndex(1)

        self.zoomBtn.view().setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.zoomBtn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.zoomBtn.currentTextChanged.connect(self.on_zoom_toggle)

        self.zoomBtn.setStyleSheet("""
            QComboBox {
                background: transparent;
                color: white;
                border: none;
                padding-left: 5px;
            }

            QComboBox::drop-down {
                border: none;
                width: 0px;
            }

            QAbstractItemView {
                background-color: #2B2D30;
                color: white;
                border: 1px solid #333333;
                selection-background-color: #2E436E;
                outline: none;
                padding: 5px;
            }""")
        statusbar_layout.addWidget(self.zoomBtn)

        statusbar_layout.addSpacing(3)

        self.warningBtn = QPushButton("0")
        self.warningBtn.setFixedSize(30, 28)
        self.warningBtn.setIcon(QIcon("assets/system/warning.png"))
        self.warningBtn.setIconSize(QSize(17, 17))
        self.warningBtn.setStyleSheet("""
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        }""")
        statusbar_layout.addWidget(self.warningBtn)

        statusbar_layout.addSpacing(3)

        self.errorsBtn = QPushButton("0")
        self.errorsBtn.setFixedSize(30, 28)
        self.errorsBtn.setIcon(QIcon("assets/system/problem.png"))
        self.errorsBtn.setIconSize(QSize(17, 17))
        self.errorsBtn.setStyleSheet("""
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        }""")
        statusbar_layout.addWidget(self.errorsBtn)

        statusbar_layout.addSpacing(3)

        self.statusBtn = QPushButton("   Ready")
        self.statusBtn.setFixedSize(80, 28)
        self.statusBtn.setIcon(QIcon("assets/system/status.png"))
        self.statusBtn.setIconSize(QSize(17, 17))
        self.statusBtn.setStyleSheet("""
        QPushButton{
        background-color: transparent;
        font-size:12px;
        font-family: Arial;
        border: none;
        color: white;
        border-radius: 0px;
        padding-left: 5px;
        padding-right: 5px;
        }
        QPushButton:hover{
        background-color: #333;
        }""")
        statusbar_layout.addWidget(self.statusBtn)

        self.bootstrap_progress_container = QFrame()
        self.bootstrap_progress_container.setFixedSize(100, 20)
        progress_container_layout = QHBoxLayout(self.bootstrap_progress_container)
        progress_container_layout.setContentsMargins(0, 0, 0, 0)
        self.bootstrap_progress = QProgressBar()
        self.bootstrap_progress.setTextVisible(False)
        self.bootstrap_progress.setFixedHeight(6)
        self.bootstrap_progress.setRange(0, 0)
        self.bootstrap_progress.hide()
        self.bootstrap_progress.setStyleSheet("""
            QProgressBar {
                background-color: #3C3C3C;
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #5A8AC5;
                border-radius: 3px;
            }
        """)
        progress_container_layout.addWidget(self.bootstrap_progress)
        statusbar_layout.addWidget(self.bootstrap_progress_container)

        statusbar_layout.addStretch()

        self.lines_and_cols = QLabel()
        self.lines_and_cols.setText("Ln 1 : Col 1")
        self.lines_and_cols.setStyleSheet("""
        QLabel{addPermanentWidget
        background-color: transparent;
        border:none;
        border-radius: 0px;
        color: white;
        font-size: 12px;
        font-family: Arial;
        }
        """)
        statusbar_layout.addWidget(self.lines_and_cols)

        self.spacing_options = QLabel()
        self.spacing_options.setText("Indent: 4 Spaces")
        self.spacing_options.setStyleSheet("""
        QLabel{
        background-color: transparent;
        border:none;
        border-radius: 0px;
        color: white;
        font-size: 12px;
        font-family: Arial;
        padding-left: 7px;
        }
        """)
        statusbar_layout.addWidget(self.spacing_options)

        self.EOL = QLabel()
        self.EOL.setText("LF")
        self.EOL.setStyleSheet("""
        QLabel{
        background-color: transparent;
        border:none;
        border-radius: 0px;
        color: white;
        font-size: 12px;
        font-family: Arial;
        padding-left: 7px;
        padding-right: 13px;
        }
        """)
        statusbar_layout.addWidget(self.EOL)

        self.terminalWindow = QPushButton("   Open Terminal")
        self.terminalWindow.setFixedSize(120, 28)
        self.terminalWindow.setIcon(QIcon("assets/system/code.png"))
        self.terminalWindow.setIconSize(QSize(17, 17))
        self.terminalWindow.setStyleSheet("""
        QPushButton{
        background-color: transparent;
        font-size:12px;
        font-family: Arial;
        border: none;
        color: white;
        border-radius: 0px;
        padding-left: 5px;
        padding-right: 10px;
        }
        QPushButton:hover{
        background-color: #333;
        }""")
        statusbar_layout.addWidget(self.terminalWindow)

        self.notificationBtn = QPushButton("")
        self.notificationBtn.setFixedSize(30, 28)
        self.notificationBtn.setIcon(QIcon("assets/system/notificaiton.png"))
        self.notificationBtn.setIconSize(QSize(20, 20))
        self.notificationBtn.setStyleSheet("""
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        padding-left: 5px;
        padding-right: 10px;
        }
        QPushButton:hover{background-color: #333}""")
        statusbar_layout.addWidget(self.notificationBtn)

        self._bootstrap_log: list[str] = []

    def retheme(self, t) -> None:
        self._theme = t
        bg = t.color("statusbar.background")
        text = t.color("statusbar.text")
        self.setStyleSheet(f"""
        QFrame{{border: 0; border-radius: 0px; background-color: {bg};}}""")
        self.zoomBtn.setStyleSheet(f"""
            QComboBox {{background: transparent; color: {text}; border: none; padding-left: 5px;}}
            QComboBox::drop-down {{border: none; width: 0px;}}
            QAbstractItemView {{
                background-color: {t.color("menu.background")};
                color: {text};
                border: 1px solid {t.color("menu.border")};
                selection-background-color: {t.color("menu.selected")};
                outline: none;
                padding: 5px;
            }}""")
        btn_style = f"""
        QPushButton{{background-color: transparent; border: none; color: {text}; border-radius: 0px;}}
        QPushButton:hover{{background-color: {t.color("notifications.button_hover")};}}"""
        self.warningBtn.setStyleSheet(btn_style)
        self.errorsBtn.setStyleSheet(btn_style)
        label_style = f"""
        QLabel{{background-color: transparent; border:none; border-radius: 0px; color: {text}; font-size: 12px; font-family: Arial;}}"""
        self.lines_and_cols.setStyleSheet(label_style)
        self.spacing_options.setStyleSheet(label_style + "padding-left: 7px;")
        self.EOL.setStyleSheet(label_style + "padding-left: 7px; padding-right: 13px;")
        self.terminalWindow.setStyleSheet(f"""
        QPushButton{{background-color: transparent; font-size:12px; font-family: Arial; border: none; color: {text}; border-radius: 0px; padding-left: 5px; padding-right: 10px;}}
        QPushButton:hover{{background-color: {t.color("notifications.button_hover")};}}""")
        self.statusBtn.setStyleSheet(f"""
        QPushButton{{background-color: transparent; font-size:12px; font-family: Arial; border: none; color: {text}; border-radius: 0px; padding-left: 5px; padding-right: 5px;}}
        QPushButton:hover{{background-color: {t.color("notifications.button_hover")};}}""")
        self.bootstrap_progress_container.setStyleSheet("background: transparent; border: none;")
        self.bootstrap_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {t.color("widget.border", "#3C3C3C")};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {t.color("widget.accent", "#4A6FA5")};
                border-radius: 3px;
            }}
        """)
        self.notificationBtn.setStyleSheet(f"""
        QPushButton{{background-color: transparent; border: none; color: {text}; border-radius: 0px; padding-left: 5px; padding-right: 10px;}}
        QPushButton:hover{{background-color: {t.color("notifications.button_hover")};}}""")
        popup = getattr(self, '_bootstrap_popup', None)
        if popup is not None and hasattr(popup, 'retheme'):
            popup.retheme(t)

    def on_zoom_toggle(self, zoomText: str):
        if not zoomText:
            return

        try:
            percent = int(zoomText.replace("%", "").strip())
            zoom_map = {"75": -2, "100": 0, "110": 1, "125": 3, "150": 5}
            zoom_level = zoom_map.get(str(percent), 0)
            self.text_zoom_toggle(zoom_level)
        except Exception as e:
            print(f"Zoom error: {e}")

    def set_bootstrap_status(self, step_name: str, message: str) -> None:
        msg = f"[{step_name}] {message}"
        self._bootstrap_log.append(msg)
        if self._saved_btn_fixed is None:
            self._saved_btn_fixed = self.statusBtn.width()
            self._saved_btn_text = self.statusBtn.text()
            self.statusBtn.setMinimumSize(80, 28)
            self.statusBtn.setMaximumSize(16777215, 28)
        self.statusBtn.setText(f"  {message}")
        self.statusBtn.setToolTip(f"Step: {step_name}")
        self.bootstrap_progress.show()
        popup = getattr(self, '_bootstrap_popup', None)
        if popup is not None and popup.isVisible():
            popup.add_message(msg)

    def set_bootstrap_finished(self, success: bool) -> None:
        self.bootstrap_progress.hide()
        if self._saved_btn_fixed is not None:
            w = self._saved_btn_fixed
            self._saved_btn_fixed = None
            self._saved_btn_text = None
            self.statusBtn.setFixedSize(w, 28)
        if success:
            self.statusBtn.setText("  Ready")
            self.statusBtn.setToolTip("Project initialized successfully")
        else:
            self.statusBtn.setText("  Failed")
            self.statusBtn.setToolTip("Project initialization failed")
        self.bootstrap_done.emit(True)
        popup = getattr(self, '_bootstrap_popup', None)
        if popup is not None and popup.isVisible():
            popup.add_message(
                "Bootstrap completed successfully." if success else "Bootstrap failed."
            )

    def show_bootstrap_details(self) -> None:
        if not self._bootstrap_log:
            return
        popup = getattr(self, '_bootstrap_popup', None)
        if popup is not None and popup.isVisible():
            popup.close()
            return
        popup = BootstrapDetailMenu(self._bootstrap_log, self.window())
        if hasattr(self, '_theme') and self._theme is not None:
            popup.retheme(self._theme)
        btn_pos = self.statusBtn.mapToGlobal(self.statusBtn.rect().topLeft())
        screen = self.screen().geometry()
        popup_x = max(screen.left(), min(btn_pos.x(), screen.right() - popup.width()))
        popup_y = btn_pos.y() - popup.height() - 4
        if popup_y < screen.top():
            popup_y = btn_pos.y() + self.statusBtn.height() + 4
        popup.move(popup_x, popup_y)
        popup.show()
        self._bootstrap_popup = popup

    def clear_bootstrap_log(self) -> None:
        self._bootstrap_log.clear()

    def text_zoom_toggle(self, zoom_level: int):
        main_win = self.window()
        tabs = getattr(main_win, "tab_editors", None)
        if not tabs:
            return

        for i in range(tabs.count()):
            editor = tabs.widget(i)
            if editor and hasattr(editor, "zoomTo"):
                editor.zoomTo(zoom_level)
