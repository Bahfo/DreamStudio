from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QFrame, QPushButton, QHBoxLayout


class VSeparator(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(1)
        self.setFixedHeight(18)
        self.setStyleSheet("background-color: #444444; border: none;")


class OptionsMenu(QFrame):
    def __init__(self, master):
        super().__init__(master)

        self.setFrameShape(QFrame.Shape.Panel)
        self.setFixedHeight(35)
        self.setStyleSheet(
            """
        QFrame{
        border: 0px;
        border-radius: 0px;
        background-color: #25272B;
        }"""
        )
        optionsMenu_layout = QHBoxLayout(self)
        optionsMenu_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        optionsMenu_layout.setContentsMargins(5, 0, 5, 0)

        #################################
        # Options
        #################################
        self.fileMenu = QPushButton()
        self.fileMenu.setFixedSize(30, 28)
        self.fileMenu.setIcon(QIcon("assets/system/new.png"))
        self.fileMenu.setIconSize(QSize(22, 22))
        self.fileMenu.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.fileMenu)

        self.folderMenu = QPushButton()
        self.folderMenu.setFixedSize(30, 28)
        self.folderMenu.setIcon(QIcon("assets/system/open.png"))
        self.folderMenu.setIconSize(QSize(18, 18))
        self.folderMenu.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.folderMenu)

        optionsMenu_layout.addSpacing(3)
        optionsMenu_layout.addWidget(
            VSeparator(), alignment=Qt.AlignmentFlag.AlignVCenter
        )

        self.cutBtn = QPushButton()
        self.cutBtn.setFixedSize(30, 28)
        self.cutBtn.setIcon(QIcon("assets/system/cut.png"))
        self.cutBtn.setIconSize(QSize(21, 21))
        self.cutBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.cutBtn)

        self.copyBtn = QPushButton()
        self.copyBtn.setFixedSize(30, 28)
        self.copyBtn.setIcon(QIcon("assets/system/copy.png"))
        self.copyBtn.setIconSize(QSize(24, 24))
        self.copyBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.copyBtn)

        self.pasteBtn = QPushButton()
        self.pasteBtn.setFixedSize(30, 28)
        self.pasteBtn.setIcon(QIcon("assets/system/paste.png"))
        self.pasteBtn.setIconSize(QSize(22, 22))
        self.pasteBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.pasteBtn)

        self.undoBtn = QPushButton()
        self.undoBtn.setFixedSize(30, 28)
        self.undoBtn.setIcon(QIcon("assets/system/undo.png"))
        self.undoBtn.setIconSize(QSize(18, 18))
        self.undoBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.undoBtn)

        self.redoBtn = QPushButton()
        self.redoBtn.setFixedSize(30, 28)
        self.redoBtn.setIcon(QIcon("assets/system/redo.png"))
        self.redoBtn.setIconSize(QSize(18, 18))
        self.redoBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.redoBtn)

        self.saveBtn = QPushButton()
        self.saveBtn.setFixedSize(30, 28)
        self.saveBtn.setIcon(QIcon("assets/system/save.png"))
        self.saveBtn.setIconSize(QSize(24, 24))
        self.saveBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 0px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.saveBtn)

        optionsMenu_layout.addSpacing(3)
        optionsMenu_layout.addWidget(
            VSeparator(), alignment=Qt.AlignmentFlag.AlignVCenter
        )

        self.monitor = QPushButton("   Hardware Monitor")
        self.monitor.setFixedSize(150, 28)
        self.monitor.setIcon(QIcon("assets/system/monitor.png"))
        self.monitor.setIconSize(QSize(17, 17))
        self.monitor.setStyleSheet(
            """
        QPushButton{
        background-color: #34373C;
        font-size:12px;
        border: none;
        color: white;
        border-radius: 0px;
        padding-left: 5px;
        padding-right: 10px;
        }
        QPushButton:hover{
        background-color: #333;
        }"""
        )
        optionsMenu_layout.addWidget(self.monitor)

        self.config_run_options = QPushButton("   Run Configuration")
        self.config_run_options.setFixedSize(150, 28)
        self.config_run_options.setIcon(QIcon("assets/system/config.png"))
        self.config_run_options.setIconSize(QSize(17, 17))
        self.config_run_options.setStyleSheet(
            """
        QPushButton{
        background-color: #34373C;
        font-size:12px;
        border: none;
        color: white;
        border-radius: 0px;
        padding-left: 5px;
        padding-right: 10px;
        }
        QPushButton:hover{
        background-color: #333;
        }"""
        )
        optionsMenu_layout.addWidget(self.config_run_options)

        self.runBtn = QPushButton()
        self.runBtn.setFixedSize(30, 28)
        self.runBtn.setIcon(QIcon("assets/system/run.png"))
        self.runBtn.setIconSize(QSize(18, 18))
        self.runBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.runBtn)

        self.debugBtn = QPushButton()
        self.debugBtn.setFixedSize(30, 28)
        self.debugBtn.setIcon(QIcon("assets/system/bug.png"))
        self.debugBtn.setIconSize(QSize(22, 22))
        self.debugBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.debugBtn)

        optionsMenu_layout.addStretch()

        #################################
        # Right-side Options
        #################################
        self.readOnlyBtn = QPushButton()
        self.readOnlyBtn.setFixedSize(30, 28)
        self.readOnlyBtn.setIcon(QIcon("assets/system/lock.png"))
        self.readOnlyBtn.setIconSize(QSize(21, 21))
        self.readOnlyBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.readOnlyBtn)

        self.containerToolsBtn = QPushButton()
        self.containerToolsBtn.setFixedSize(30, 28)
        self.containerToolsBtn.setIcon(QIcon("assets/system/container.png"))
        self.containerToolsBtn.setIconSize(QSize(21, 21))
        self.containerToolsBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.containerToolsBtn)

        self.searchBtn = QPushButton()
        self.searchBtn.setFixedSize(30, 28)
        self.searchBtn.setIcon(QIcon("assets/system/search.png"))
        self.searchBtn.setIconSize(QSize(21, 21))
        self.searchBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.searchBtn)

        self.settingsBtn = QPushButton()
        self.settingsBtn.setFixedSize(30, 28)
        self.settingsBtn.setIcon(QIcon("assets/system/settings.png"))
        self.settingsBtn.setIconSize(QSize(24, 24))
        self.settingsBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.settingsBtn)
