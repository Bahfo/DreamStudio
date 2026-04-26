from PyQt6.QtCore import Qt, QSize, QEvent, pyqtSignal
from PyQt6.QtGui import QIcon, QLinearGradient, QPainter, QColor
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QLineEdit,
    QMenuBar,
)


class DreamStudioTitleBar(QWidget):
    maximize_requested = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.offset = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.window().installEventFilter(self)

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
        edit_menu.addSeparator()
        edit_menu.addAction("Indent Selection")
        edit_menu.addAction("Unindent Selection")
        edit_menu.addAction("Manage Indentation")

        # VIEW
        view_menu = self.menubar.addMenu("View")
        view_menu.addAction("Change Editor Layout")
        view_menu.addAction("Appearance")
        view_menu.addSeparator()
        view_menu.addAction("File Explorer")
        view_menu.addAction("Search Explorer")
        view_menu.addAction("Unit Testing Window")
        view_menu.addAction("Ether AI Chat Window")
        view_menu.addSeparator()
        view_menu.addAction("Change Visibilty Settings")
        view_menu.addAction("Reset Font Size in all Editors")
        view_menu.addAction("Reset Appearance Settings in all Editors")

        # TOOL
        tool_menu = self.menubar.addMenu("Tools")
        tool_menu.addAction("Command Window")
        tool_menu.addAction("Solution Explorer")
        tool_menu.addAction("File Search Explorer")
        tool_menu.addAction("Ether AI Chat Window")
        tool_menu.addAction("Server Explorer")
        tool_menu.addAction("Web Broswer")
        tool_menu.addAction("Object Window Viewer")
        tool_menu.addAction("Code Definition Window Browser")
        tool_menu.addSeparator()
        tool_menu.addAction("Errors List")
        tool_menu.addAction("Outputs Window")
        tool_menu.addAction("Startup Page")
        tool_menu.addAction("Tasks TODO List")
        tool_menu.addAction("Notifications")
        tool_menu.addSeparator()
        tool_menu.addAction("User's History")
        tool_menu.addAction("Project Properties Manager")
        tool_menu.addAction("Code Analysis Manager")
        tool_menu.addAction("Code Snippets Manager")

        # CODE
        code_menu = self.menubar.addMenu("Code")
        code_menu.addAction("Format Code")
        code_menu.addAction("Minify Code in Current File")
        code_menu.addAction("Comment Current Line")
        code_menu.addAction("Comment Current Selection")
        code_menu.addAction("Uncomment Current Line")
        code_menu.addAction("Uncomment Current Selection")
        code_menu.addAction("Dublicate Current Line")
        code_menu.addAction("Dublicate Current Selection")
        code_menu.addAction("Sort Imports and Trivial Codes")
        code_menu.addSeparator()
        code_menu.addAction("Go to Definition")
        code_menu.addAction("Go to Declaration")
        code_menu.addAction("Go to Implementation")
        code_menu.addAction("Find Usages and References in Current File")
        code_menu.addAction("Go to Symbol")

        build_menu = self.menubar.addMenu("Run")
        build_menu.addAction("Run Current File")
        build_menu.addAction("Run File Selection")
        build_menu.addAction("Run Current File with Configured Arguments")
        build_menu.addAction("Run Current File without Debugging")
        build_menu.addSeparator()
        build_menu.addAction("Stop Current Execution")
        build_menu.addAction("Restart Debugging")
        build_menu.addSeparator()
        build_menu.addAction("Step Over")
        build_menu.addAction("Step Into")
        build_menu.addAction("Step Out")
        build_menu.addAction("Continue")
        build_menu.addSeparator()
        build_menu.addAction("Add New Breakpoing at Current File")
        build_menu.addAction("Enable All Breakpoints")
        build_menu.addAction("Disable All Breakpoints")
        build_menu.addAction("Remove All Breakpoints")

        # EXTENSIONS
        extens_menu = self.menubar.addMenu("Extensions")
        extens_menu.addAction("Manage Extensions")
        extens_menu.addAction("Add New Extension")
        extens_menu.addAction("Refresh Extensions")
        extens_menu.addAction("More About Extensions ...")

        # HELP
        help_menu = self.menubar.addMenu("Help")
        help_menu.addAction("Welcome")
        help_menu.addAction("Show All Commands")
        help_menu.addAction("Documentation")
        help_menu.addSeparator()
        help_menu.addAction("View License")
        help_menu.addAction("Check for Updates")
        help_menu.addAction("About")

        layout.addWidget(self.menubar, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addSpacing(40)

        #################################
        # Search Navigation
        #################################
        self.studioSearch = QLineEdit()
        self.studioSearch.setPlaceholderText("Search DreamStudio (Ctrl+Q)")
        self.studioSearch.setClearButtonEnabled(True)
        self.studioSearch.setFixedWidth(400)
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
        win = self.window()

        if win.isMaximized():
            win.showNormal()
            self.btn_maximize.setText("◻")
            return

        self._restore_geometry = win.normalGeometry()
        if not self._restore_geometry.isValid():
            self._restore_geometry = win.geometry()

        win.showMaximized()
        self.btn_maximize.setText("❐")

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()

    def sync_titlebar_state(self):
        win = self.window()
        self.btn_maximize.setText("❐" if win.isMaximized() else "◻")

    def mousePressEvent(self, event):
        win = self.window()
        if event.button() == Qt.MouseButton.LeftButton:
            self.offset = event.globalPosition().toPoint() - win.pos()
            event.accept()

    def mouseMoveEvent(self, event):
        win = self.window()
        if self.offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            if win.isMaximized():
                cursor_x = event.globalPosition().toPoint().x()
                max_width = win.width()
                width_ratio = cursor_x / max_width

                win.showNormal()
                normal_width = win.width()
                new_x = int(cursor_x - (normal_width * width_ratio))
                new_y = event.globalPosition().toPoint().y() - self.offset.y()

                win.move(new_x, new_y)

                self.offset = event.globalPosition().toPoint() - win.pos()
                return

            win.move(event.globalPosition().toPoint() - self.offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.offset = None
        super().mouseReleaseEvent(event)

    def moveEvent(self, event):
        super().moveEvent(event)

    def eventFilter(self, obj, event):
        if obj == self.window():
            if event.type() == QEvent.Type.WindowStateChange:
                self.sync_titlebar_state()
        return super().eventFilter(obj, event)

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(1.0, QColor("#004073"))

        painter.fillRect(self.rect(), gradient)
        return super().paintEvent(a0)
