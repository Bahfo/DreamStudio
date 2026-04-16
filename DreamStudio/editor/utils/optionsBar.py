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
        self.options = QPushButton("☰")
        self.options.setFixedSize(30, 28)
        self.options.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 12px;
        font-size: 14px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        optionsMenu_layout.addWidget(self.options)
        optionsMenu_layout.addSpacing(15)

        # File & Folder
        self.fileMenu = self.create_menu_button(
            text=None, image="assets/system/new.png", image_size=QSize(22, 22)
        )
        self.folderMenu = self.create_menu_button(
            text=None, image="assets/system/open.png", image_size=QSize(18, 18)
        )

        optionsMenu_layout.addWidget(self.fileMenu)
        optionsMenu_layout.addWidget(self.folderMenu)

        optionsMenu_layout.addSpacing(3)
        optionsMenu_layout.addWidget(
            VSeparator(), alignment=Qt.AlignmentFlag.AlignVCenter
        )

        # Edit Operations
        self.cutBtn = self.create_menu_button(
            text=None, image="assets/system/cut.png", image_size=QSize(21, 21)
        )
        self.copyBtn = self.create_menu_button(
            text=None, image="assets/system/copy.png", image_size=QSize(24, 24)
        )
        self.pasteBtn = self.create_menu_button(
            text=None, image="assets/system/paste.png", image_size=QSize(22, 22)
        )
        self.undoBtn = self.create_menu_button(
            text=None, image="assets/system/undo.png", image_size=QSize(18, 18)
        )
        self.redoBtn = self.create_menu_button(
            text=None, image="assets/system/redo.png", image_size=QSize(18, 18)
        )
        self.saveBtn = self.create_menu_button(
            text=None, image="assets/system/save.png", image_size=QSize(24, 24)
        )

        optionsMenu_layout.addWidget(self.cutBtn)
        optionsMenu_layout.addWidget(self.copyBtn)
        optionsMenu_layout.addWidget(self.pasteBtn)
        optionsMenu_layout.addWidget(self.undoBtn)
        optionsMenu_layout.addWidget(self.redoBtn)
        optionsMenu_layout.addWidget(self.saveBtn)

        optionsMenu_layout.addSpacing(3)
        optionsMenu_layout.addWidget(
            VSeparator(), alignment=Qt.AlignmentFlag.AlignVCenter
        )

        # Text Buttons CSS (Monitor & Config)
        text_btn_css = """
        QPushButton{
            background-color: #34373C;
            font-size:12px;
            border: none;
            color: white;
            border-radius: 0px;
            padding-left: 5px;
            padding-right: 10px;
        }
        QPushButton:hover{background-color: #333;}
        """

        # Tools & Execution
        self.monitor = self.create_menu_button(
            image="assets/system/monitor.png",
            image_size=QSize(17, 17),
            text="   Hardware Monitor",
            btn_size=QSize(150, 28),
            custom_css=text_btn_css,
        )

        self.config_run_options = self.create_menu_button(
            image="assets/system/config.png",
            image_size=QSize(19, 19),
            text="   Run Configuration",
            btn_size=QSize(150, 28),
            custom_css=text_btn_css,
        )

        self.runBtn = self.create_menu_button(
            text=None, image="assets/system/run.png", image_size=QSize(18, 18)
        )
        self.debugBtn = self.create_menu_button(
            text=None, image="assets/system/bug.png", image_size=QSize(22, 22)
        )

        optionsMenu_layout.addWidget(self.monitor)
        optionsMenu_layout.addWidget(self.config_run_options)
        optionsMenu_layout.addWidget(self.runBtn)
        optionsMenu_layout.addWidget(self.debugBtn)

        optionsMenu_layout.addStretch()

        # Right-side Options
        self.readOnlyBtn = self.create_menu_button(
            text=None, image="assets/system/lock.png", image_size=QSize(21, 21)
        )
        self.containerToolsBtn = self.create_menu_button(
            text=None, image="assets/system/container.png", image_size=QSize(21, 21)
        )

        optionsMenu_layout.addWidget(self.readOnlyBtn)
        optionsMenu_layout.addWidget(self.containerToolsBtn)

        self.searchBtn = self.create_menu_button(
            text=None, image="assets/system/search.png", image_size=QSize(21, 21)
        )
        optionsMenu_layout.addWidget(self.searchBtn)

        self.settingsBtn = self.create_menu_button(
            text=None, image="assets/system/settings.png"
        )
        optionsMenu_layout.addWidget(self.settingsBtn)

    def create_menu_button(
        self,
        image,
        image_size=QSize(24, 24),
        text=None,
        btn_size=QSize(30, 28),
        custom_css=None,
        function=None,
    ):
        btn = QPushButton(text) if text else QPushButton()
        btn.setFixedSize(btn_size)
        btn.setIcon(QIcon(image))
        btn.setIconSize(image_size)

        # Default stylesheet for icon buttons
        default_css = """
        QPushButton{
            background-color: transparent;
            border: none;
            color: white;
            border-radius: 10px;
            padding-top:4px;
            padding-left:2px;
            padding-right:2px;
        }
        QPushButton:hover{background-color:#333}
        """

        btn.setStyleSheet(custom_css if custom_css else default_css)

        if function:
            btn.clicked.connect(function)

        return btn
