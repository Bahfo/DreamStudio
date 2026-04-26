from PyQt6.QtCore import Qt, QSize, QEvent
from PyQt6.QtGui import QPainter, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QApplication,
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
        self.setStyleSheet("background: #004073")

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

    def _state_str(self, win):
        flags = []
        if win._is_fake_max:
            flags.append("Maximized")
        if win.isFullScreen():
            flags.append("FullScreen")
        if win.isMinimized():
            flags.append("Minimized")
        if not flags:
            flags.append("Normal")
        return "|".join(flags)

    def toggle_maximize(self):
        win = self.window()
        self._dbg("toggle_maximize BEFORE")

        self.offset = None

        if getattr(self, "_is_fake_max", False):
            print("[TITLEBAR] restoring from fake maximize")
            if hasattr(self, "_normal_geometry"):
                win.setGeometry(self._normal_geometry)
            self._is_fake_max = False
            self.btn_maximize.setText("◻")
        else:
            print("[TITLEBAR] entering fake maximize")
            self._normal_geometry = win.geometry()
            win.setGeometry(win.screen().availableGeometry())
            self._is_fake_max = True
            self.btn_maximize.setText("❐")

        self._dbg("toggle_maximize AFTER")

    def mousePressEvent(self, event):
        win = self.window()
        print(f"[TITLEBAR] mousePressEvent button={event.button()}")

        if event.button() == Qt.MouseButton.LeftButton:
            if getattr(self, "_is_fake_max", False):
                print("[TITLEBAR] press ignored because fake maximized")
                self.offset = None
                return

            self.offset = event.globalPosition().toPoint() - win.pos()
            print(f"[TITLEBAR] offset set -> {self.offset}")
            event.accept()

    def mouseMoveEvent(self, event):
        win = self.window()
        print(f"[TITLEBAR] mouseMoveEvent buttons={event.buttons()}")

        if getattr(self, "_is_fake_max", False):
            return

        if self.offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.offset
            print(f"[TITLEBAR] moving window -> {new_pos}")
            win.move(new_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        print(f"[TITLEBAR] mouseReleaseEvent button={event.button()}")
        self.offset = None
        event.accept()

    def resizeEvent(self, event):
        print(f"[TITLEBAR] resizeEvent")
        super().resizeEvent(event)

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_Widget, opt, painter, self
        )

    def moveEvent(self, event):
        if self.isMaximized():
            return  # block invalid moves
        super().moveEvent(event)

    def _state_str(self, win):
        flags = []
        if win.isMaximized():
            flags.append("Maximized")
        if win.isMinimized():
            flags.append("Minimized")
        if win.isFullScreen():
            flags.append("FullScreen")
        if not flags:
            flags.append("Normal")
        return "|".join(flags)

    def _geo_str(self, win):
        g = win.geometry()
        return f"{g.x()},{g.y()} {g.width()}x{g.height()}"

    def _dbg(self, label):
        win = self.window()
        print(f"[TITLEBAR] {label} state={self._state_str(win)}")

    def eventFilter(self, obj, event):
        if obj == self.window():
            if event.type() == QEvent.Type.WindowStateChange:
                self._dbg("eventFilter WindowStateChange")
            elif event.type() == QEvent.Type.Move:
                self._dbg("eventFilter Move")
            elif event.type() == QEvent.Type.Resize:
                self._dbg("eventFilter Resize")
        return super().eventFilter(obj, event)
