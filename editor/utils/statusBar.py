from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QFrame,
    QPushButton,
    QHBoxLayout,
    QComboBox,
    QLabel
)


class StatusBar(QFrame):
    def __init__(self, master):
        super().__init__(master)

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

        #################################
        # BUTTONS AND OPTIONS
        #################################
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

    def retheme(self, t) -> None:
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
        self.notificationBtn.setStyleSheet(f"""
        QPushButton{{background-color: transparent; border: none; color: {text}; border-radius: 0px; padding-left: 5px; padding-right: 10px;}}
        QPushButton:hover{{background-color: {t.color("notifications.button_hover")};}}""")

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
        self.statusBtn.setText(f"  {message}")
        self.statusBtn.setToolTip(f"Step: {step_name}")

    def set_bootstrap_finished(self, success: bool) -> None:
        if success:
            self.statusBtn.setText("  Ready")
            self.statusBtn.setToolTip("Project initialized successfully")
        else:
            self.statusBtn.setText("  Failed")
            self.statusBtn.setToolTip("Project initialization failed")

    def text_zoom_toggle(self, zoom_level: int):
        main_win = self.window()
        tabs = getattr(main_win, "tab_editors", None)
        if not tabs:
            return

        for i in range(tabs.count()):
            editor = tabs.widget(i)
            if editor and hasattr(editor, "zoomTo"):
                editor.zoomTo(zoom_level)
