from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPainter, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QStyle,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QLineEdit,
    QStyleOption,
    QStyle,
    QMenuBar,
)


class DreamStudioTitleBar(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.offset = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        #################################
        # Title
        #################################

        self.icon_btn = QPushButton("   DreamStudio")
        self.icon_btn.setIcon(QIcon("assets/logos/dreamStudio_icon.png"))
        self.icon_btn.setIconSize(QSize(26, 26))
        self.icon_btn.setFixedSize(120, 30)
        self.icon_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.icon_btn.setStyleSheet(
            """
            QPushButton{
            color: white;
            background-color: transparent;
            border: none;
            border-radius: 4px;
            font-size: 13px;}
            """
        )
        layout.addWidget(self.icon_btn)

        #################################
        # MenuBar
        #################################
        self.menubar = QMenuBar()
        self.menubar.setFixedHeight(30)
        self.menubar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.menubar.setStyleSheet(
            """
            QMenuBar {
                background-color: transparent;
                color: #D1D1D1;
                font-size: 13px;
                border: none;
            }
            QMenuBar::item {
                background: transparent;
                padding: 7px 5px;
                margin: 0px 2px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: rgba(63, 65, 69, 0.2);
                color: white;
            }
            QMenu {
            background-color: #2B2D30;
            color: #D1D1D1;
            border: 1px solid #3F4145;
            min-width: 350px;
            padding: 2px; 
            }

            QMenu::item {
            padding: 8px 12px 8px 8px; /*top left down right*/
            background-color: transparent;
            }

            QMenu::icon {padding-right: 20px;}
            QMenu::item:selected {background-color:#2E436E}"""
        )

        # FILE
        file_menu = self.menubar.addMenu("File")

        file_menu.addAction("New File")
        file_menu.addAction("New Project")
        file_menu.addAction("New Window")
        file_menu.addSeparator()
        file_menu.addAction("Open ...")
        file_menu.addAction("Open Recent Project")
        file_menu.addSeparator()
        file_menu.addAction("Save Current File")
        file_menu.addAction("Save File As ...")
        file_menu.addAction("Save All Files")
        file_menu.addAction("Save All and Close Window")
        file_menu.addSeparator()
        file_menu.addAction("Add Folder to Workspace ...")
        file_menu.addAction("Close Editor")
        file_menu.addAction("Close Project")
        file_menu.addAction("Close DreamStudio")
        file_menu.addSeparator()
        file_menu.addAction("Import ...")
        file_menu.addAction("Export ...")
        file_menu.addSeparator()
        file_menu.addAction("Settings and Preferences")
        file_menu.addAction("Exit")

        # EDIT
        edit_menu = self.menubar.addMenu("Edit")

        edit_menu.addAction("Undo")
        edit_menu.addAction("Redo")
        edit_menu.addSeparator()
        edit_menu.addAction("Cut Selection")
        edit_menu.addAction("Copy Selection")
        edit_menu.addAction("Copy Selection as Plain Text")
        edit_menu.addAction("Paste Clipboard")
        edit_menu.addAction("Delete Selection")
        edit_menu.addSeparator()
        edit_menu.addAction("Find")
        edit_menu.addAction("Replace")
        edit_menu.addAction("Search in Selected Text")
        edit_menu.addAction("Find in Files")
        edit_menu.addAction("Replace in Files")
        edit_menu.addSeparator()
        edit_menu.addAction("Select All")
        edit_menu.addAction("Unselect All")
        edit_menu.addAction("Extend Selection")
        edit_menu.addAction("Shrink Selection")
        edit_menu.addSeparator()
        edit_menu.addAction("Indent Selection")
        edit_menu.addAction("Unindent Selection")
        edit_menu.addAction("Manage Indentation")
        edit_menu.addSeparator()
        edit_menu.addAction("Toggle Line Comment")
        edit_menu.addAction("Toggle Break Comment")
        edit_menu.addAction("Fill Lines")

        # VIEW
        view_menu = self.menubar.addMenu("View")

        # TOOL
        tool_menu = self.menubar.addMenu("Tools")

        # NAVIGATION
        navi_menu = self.menubar.addMenu("Navigate")

        # CODE
        code_menu = self.menubar.addMenu("Code")

        # BUILD
        build_menu = self.menubar.addMenu("Build")

        # EXTENSIONS
        extens_menu = self.menubar.addMenu("Extensions")

        # WINDOW MANAGER
        wind_menu = self.menubar.addMenu("Window")

        # HELP
        help_menu = self.menubar.addMenu("Help")

        layout.addWidget(self.menubar, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addSpacing(40)

        #################################
        # Search Navigation
        #################################
        self.studioSearch = QLineEdit()
        self.studioSearch.setPlaceholderText("Search DreamStudio (Ctrl+Q)")
        self.studioSearch.setClearButtonEnabled(True)
        self.studioSearch.setFixedWidth(300)
        self.studioSearch.setFixedHeight(24)
        self.studioSearch.setStyleSheet(
            """
        QLineEdit{
        background-color:transparent;
        color: #D1D1D1;
        font-size:13px;
        font-style:normal;
        border:0.5px solid #9D9D9D;
        padding-left:15px;
        border-radius:5px;}
        
        QLineEdit:placeholder{
        font-style:italic;
        }"""
        )
        layout.addWidget(self.studioSearch)
        layout.addSpacing(10)

        #################################
        # Account
        #################################
        self.accountBtn = QPushButton()
        self.accountBtn.setIcon(QIcon("assets/system/account.png"))
        self.accountBtn.setIconSize(QSize(26, 26))
        self.accountBtn.setStyleSheet(
            """
            QPushButton{
            color: white;
            background-color: transparent;
            border: none;
            border-radius: 13px;
            font-size: 12px;
            padding:0px;}
            QPushButton:hover{
            background-color:#444;}

            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }"""
        )
        layout.addWidget(self.accountBtn)
        layout.addStretch()

        self.btn_minimize = QPushButton("—")
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_minimize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minimize.setStyleSheet(
            """
            QPushButton{
            color: white;
            background-color: transparent;
            border: none;
            border-radius: 4px;
            font-size: 12px;}
            QPushButton:hover{
            background-color:#444;}
            
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }"""
        )
        layout.addWidget(self.btn_minimize)

        self.btn_maximize = QPushButton("◻")
        self.btn_maximize.setFixedSize(30, 30)
        self.btn_maximize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_maximize.setStyleSheet(
            """
            QPushButton{
            color: white;
            background-color: transparent;
            border: none;
            border-radius: 4px;
            font-size: 12px;}
            QPushButton:hover{
            background-color:#444;}
            
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);}"""
        )
        layout.addWidget(self.btn_maximize)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet(
            """
            QPushButton{
            color: white;
            background-color: transparent;
            border: none;
            border-radius: 4px;
            font-size: 16px;}
            QPushButton:hover{
            background-color:#444;}
            
            QPushButton:hover {
                background-color: #E81123; /* Windows red close */
                color: white;
            }"""
        )
        layout.addWidget(self.btn_close)

        self.btn_minimize.clicked.connect(self.parent.showMinimized)
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        self.btn_close.clicked.connect(self.parent.close)

    def toggle_maximize(self):
        """Toggles between maximized and normal window states."""
        if self.parent.isMaximized():
            self.parent.showNormal()
            self.btn_maximize.setText("◻")
        else:
            self.parent.showMaximized()
            self.btn_maximize.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - self.parent.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.offset is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.parent.move(event.globalPosition().toPoint() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.offset = None
        event.accept()

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, opt, painter, self
        )
