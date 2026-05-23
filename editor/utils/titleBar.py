from PyQt6.QtCore import Qt, QSize, QEvent, pyqtSignal
from PyQt6.QtGui import QIcon, QLinearGradient, QPainter, QColor, QAction
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
        self.icon_btn.setStyleSheet("""
            QPushButton{
            color: white;
            background-color: transparent;
            border: none;
            border-radius: 4px;
            font-size: 13px;}
            """)
        layout.addWidget(self.icon_btn)

        #################################
        # MenuBar
        #################################
        self.menubar = QMenuBar()
        self.menubar.setFixedHeight(30)
        self.menubar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        self.menubar.setStyleSheet("""
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
            padding: 4px 6px;
        }

        QMenu::item {
            min-width: 300px; 
            padding: 8px 15px 8px 32px;
            background-color: transparent;
            margin: 0px;
        }

        QMenu::item:selected {
            background-color: #2E436E; 
            color: white;
        }

        QMenu::icon {
            position: absolute;
            left: 7px;
        }

        QMenu::separator {
            height: 1px;
            background-color: #3F4145;
            margin: 4px 0px;
        }
        """)

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
        self.studioSearch.setStyleSheet("""
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
        }""")
        layout.addWidget(self.studioSearch)
        layout.addSpacing(10)

        #################################
        # Account
        #################################
        self.accountBtn = QPushButton()
        self.accountBtn.setIcon(QIcon("assets/system/account.png"))
        self.accountBtn.setIconSize(QSize(26, 26))
        self.accountBtn.setStyleSheet("""
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
            }""")
        layout.addWidget(self.accountBtn)
        layout.addStretch()

        self.btn_minimize = QPushButton("—")
        self.btn_minimize.setFixedSize(30, 30)
        self.btn_minimize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_minimize.setStyleSheet("""
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
            }""")
        layout.addWidget(self.btn_minimize)

        self.btn_maximize = QPushButton("◻")
        self.btn_maximize.setFixedSize(30, 30)
        self.btn_maximize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_maximize.setStyleSheet("""
            QPushButton{
            color: white;
            background-color: transparent;
            border: none;
            border-radius: 4px;
            font-size: 12px;}
            QPushButton:hover{
            background-color:#444;}
            
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);}""")
        layout.addWidget(self.btn_maximize)

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
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
            }""")
        layout.addWidget(self.btn_close)

        self.btn_minimize.clicked.connect(self.parent.showMinimized)
        self.btn_maximize.clicked.connect(self.toggle_maximize)
        self.btn_close.clicked.connect(self.parent.close)

        self.setup_menus()

    def setup_menus(self):
        menus_config = {
            "File": [
                ("New File", "assets/menus/new_file.png", self.set_new_file),
                ("New Project", "assets/menus/new_project.png", self.set_new_project),
                ("New Window", None, self.set_new_window),
                None,
                ("Open...", "assets/menus/open.png", self.set_open_file),
                ("Open Recent Project", None, self.set_open_recent_project),
                None,
                (
                    "Save Current File",
                    "assets/menus/save.png",
                    self.set_save_current_file,
                ),
                ("Save File As...", None, self.set_save_file_as),
                ("Save All Files", None, self.set_save_all_files),
                (
                    "Save All and Close Window",
                    None,
                    self.set_save_all_and_close,
                ),
                None,
                (
                    "Close Editor",
                    "assets/menus/close_editor.png",
                    self.set_close_editor,
                ),
                (
                    "Close DreamStudio",
                    None,
                    self.set_close_dreamstudio,
                ),
                None,
                (
                    "Import...",
                    "assets/menus/import.png",
                    self.set_import_configurations,
                ),
                (
                    "Export...",
                    "assets/menus/export.png",
                    self.set_export_configurations,
                ),
                (
                    "Settings and Preferences",
                    "assets/menus/settings.png",
                    self.set_open_settings,
                ),
                ("Exit", None, self.parent.close),
            ],
            "Edit": [
                ("Undo", "assets/menus/undo.png", self.set_undo),
                ("Redo", "assets/menus/redo.png", self.set_redo),
                None,
                ("Cut Selection", "assets/menus/cut.png", self.set_cut),
                ("Copy Selection", "assets/menus/copy.png", self.set_copy),
                (
                    "Copy Selection as Plain Text",
                    "assets/menus/copy_text.png",
                    self.set_copy_as_plain_text,
                ),
                ("Paste Clipboard", "assets/menus/paste.png", self.set_paste),
                ("Delete Selection", None, self.set_delete_selection),
                None,
                ("Find and Replace", "assets/menus/find.png", self.set_find_replace),
                (
                    "Search in Selected Text",
                    "assets/menus/search_sel.png",
                    self.set_search_in_selected,
                ),
                ("Find and Replace in Files", None, self.set_find_replace_in_files),
                None,
                ("Select All", None, self.set_select_all),
                ("Unselect All", None, self.set_unselect_all),
                ("Indent Selection", None, self.set_indent_selection),
                ("Unindent Selection", None, self.set_unindent_selection),
                ("Manage Indentation", None, self.set_manage_indentation),
            ],
            "View": [
                ("Change Editor Layout", None, self.generic_callback),
                ("Appearance", "assets/menus/appearance.png", self.generic_callback),
                None,
                ("File Explorer", "assets/menus/explorer.png", self.generic_callback),
                ("Search Explorer", None, self.generic_callback),
                (
                    "Unit Testing Window",
                    "assets/menus/testing.png",
                    self.generic_callback,
                ),
                (
                    "Ether AI Chat Window",
                    "assets/menus/ai_chat.png",
                    self.generic_callback,
                ),
                ("Change Visibility Settings", None, self.generic_callback),
                ("Reset Font Size", None, self.generic_callback),
            ],
            "Tools": [
                ("Command Window", "assets/menus/command.png", self.generic_callback),
                (
                    "Ether AI Chat Window",
                    "assets/menus/ai_chat.png",
                    self.generic_callback,
                ),
                ("Server Explorer", None, self.generic_callback),
                ("Web Browser", "assets/menus/browser.png", self.generic_callback),
                ("Object Window Viewer", None, self.generic_callback),
                ("Code Definition Window Browser", None, self.generic_callback),
                ("Errors List", "assets/menus/errors.png", self.generic_callback),
                ("Outputs Window", None, self.generic_callback),
                ("Tasks TODO List", "assets/menus/todo.png", self.generic_callback),
                (
                    "Notifications",
                    "assets/menus/notifications.png",
                    self.generic_callback,
                ),
                (
                    "Code Analysis Manager",
                    "assets/menus/analysis.png",
                    self.generic_callback,
                ),
                ("Code Snippets Manager", None, self.generic_callback),
            ],
            "Code": [
                ("Format Code", "assets/menus/format.png", self.generic_callback),
                ("Minify Code in Current File", None, self.generic_callback),
                (
                    "Comment Current Line",
                    "assets/menus/comment.png",
                    self.generic_callback,
                ),
                None,
                ("Comment Current Selection", None, self.generic_callback),
                ("Uncomment Current Line", None, self.generic_callback),
                ("Uncomment Current Selection", None, self.generic_callback),
                ("Duplicate Current Line", None, self.generic_callback),
                ("Duplicate Current Selection", None, self.generic_callback),
                ("Sort Code", None, self.generic_callback),
                None,
                ("Go to Definition", None, self.generic_callback),
                ("Go to Declaration", None, self.generic_callback),
                ("Go to Implementation", None, self.generic_callback),
                (
                    "Find Usages and References in Current File",
                    None,
                    self.generic_callback,
                ),
                ("Go to Symbol", None, self.generic_callback),
            ],
            "Run": [
                ("Run Current File", "assets/menus/run.png", self.generic_callback),
                (
                    "Run Current File with Configured Arguments",
                    "assets/menus/run_args.png",
                    self.generic_callback,
                ),
                (
                    "Run Current File without Debugging",
                    "assets/menus/run_no_debug.png",
                    self.generic_callback,
                ),
                (
                    "Stop Current Execution",
                    "assets/menus/stop.png",
                    self.generic_callback,
                ),
                (
                    "Restart Debugging",
                    "assets/menus/restart.png",
                    self.generic_callback,
                ),
                None,
                ("Step Over", None, self.generic_callback),
                ("Step Into", None, self.generic_callback),
                ("Step Out", None, self.generic_callback),
                ("Continue", None, self.generic_callback),
                None,
                (
                    "Add New Breakpoint at Current File",
                    "assets/menus/breakpoint.png",
                    self.generic_callback,
                ),
                ("Enable All Breakpoints", None, self.generic_callback),
                ("Disable All Breakpoints", None, self.generic_callback),
                ("Remove All Breakpoints", None, self.generic_callback),
            ],
            "Marketplace": [
                (
                    "Open Marketplace",
                    "assets/menus/manage_ext.png",
                    self.generic_callback,
                ),
                (
                    "Refresh Extensions",
                    "assets/menus/refresh_ext.png",
                    self.generic_callback,
                ),
            ],
            "Help": [
                ("Welcome", None, self.show_welcome),
                ("Show All Commands", None, self.generic_callback),
                ("Documentation", "assets/menus/docs.png", self.generic_callback),
                ("View License", "assets/menus/license.png", self.generic_callback),
                ("Check for Updates", None, self.generic_callback),
                ("About", "assets/menus/info.png", self.generic_callback),
            ],
        }

        for menu_name, items in menus_config.items():
            menu = self.menubar.addMenu(menu_name)

            for item in items:
                if item is None:
                    menu.addSeparator()
                else:
                    text, icon_path, callback = item
                    action = QAction(QIcon(icon_path), text, self)
                    if callback:
                        if callback == self.generic_callback:
                            action.triggered.connect(
                                lambda checked, t=text: callback(t)
                            )
                        else:
                            action.triggered.connect(callback)

                    menu.addAction(action)

    def generic_callback(self, action_name):
        print(f"Action Triggered: {action_name}")

    def show_welcome(self):
        self.parent.ui_build_show_welcome()

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

    _gradient_colors = ["#004073", "#11324E", "#1E2E3B", "#24292D", "#25272B"]

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        stops = [0.85, 0.7, 0.5, 0.3, 0.1]
        gradient = QLinearGradient(0, 0, self.width(), 0)
        colors = getattr(self, "_gradient_colors", ["#004073", "#11324E", "#1E2E3B", "#24292D", "#25272B"])
        for stop, color in zip(stops, colors):
            gradient.setColorAt(stop, QColor(color))
        painter.fillRect(self.rect(), gradient)
        return super().paintEvent(a0)

    ##########################################################
    # Callback actions for menubar from editor
    #
    # Easier to manipulate by handling for each file a set of
    # operations instead of relying on a single file to do all
    # operations.
    ##########################################################

    def set_new_file(self):
        return self.parent.ui_build_add_new_editor()

    def set_new_project(self):
        return

    def set_new_window(self):
        return

    def set_open_recent_project(self):
        return

    def set_open_file(self):
        return self.parent.ui_build_open_file()

    def set_save_current_file(self):
        return self.parent.ui_build_save_file()

    def set_save_all_files(self):
        return self.parent.ui_build_save_all()

    def set_save_file_as(self):
        return self.parent.ui_build_save_as()

    def set_save_all_and_close(self):
        self.set_save_all_files()
        self.parent.close()

    def set_close_editor(self):
        return self.parent.ui_build_close_all_editors()

    def set_close_dreamstudio(self):
        self.set_save_all_files()
        self.parent.close()

    def set_import_configurations(self):
        return

    def set_export_configurations(self):
        return

    def set_open_settings(self):
        return

    def _get_current_editor(self):
        editor = self.parent.options_menu._get_current_editor()
        return editor

    def set_cut(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "cut"):
            editor.cut()

    def set_undo(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "undo"):
            editor.undo()

    def set_redo(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "redo"):
            editor.redo()

    def set_copy(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "copy"):
            editor.copy()

    def set_copy_as_plain_text(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "copy_selection_as_plain_text"):
            editor.copy_selection_as_plain_text()

    def set_paste(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "paste"):
            editor.paste()

    def set_delete_selection(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "removeSelectedText"):
            editor.removeSelectedText()

    def set_select_all(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "selectAll"):
            editor.selectAll()

    def set_unselect_all(self):
        editor = self._get_current_editor()
        if editor:
            line, index = editor.getCursorPosition()
            editor.setCursorPosition(line, index)

    def set_indent_selection(self):
        editor = self._get_current_editor()
        if editor:
            line_from, _, line_to, _ = editor.getSelection()

            editor.beginUndoAction()

            if line_from != -1:
                for line in range(line_from, line_to + 1):
                    current_indent = editor.indentation(line)
                    editor.setIndentation(
                        line, current_indent + editor.indentationWidth()
                    )
            else:
                line, _ = editor.getCursorPosition()
                current_indent = editor.indentation(line)
                editor.setIndentation(line, current_indent + editor.indentationWidth())

            editor.endUndoAction()

    def set_unindent_selection(self):
        editor = self._get_current_editor()
        if editor:
            line_from, _, line_to, _ = editor.getSelection()

            editor.beginUndoAction()

            if line_from != -1:
                for line in range(line_from, line_to + 1):
                    current_indent = editor.indentation(line)
                    new_indent = max(0, current_indent - editor.indentationWidth())
                    editor.setIndentation(line, new_indent)
            else:
                line, _ = editor.getCursorPosition()
                current_indent = editor.indentation(line)
                new_indent = max(0, current_indent - editor.indentationWidth())
                editor.setIndentation(line, new_indent)

            editor.endUndoAction()

    def retheme(self, t) -> None:
        tb_bg = t.color("titlebar.background")
        tb_text = t.color("titlebar.text")
        btn_hover = t.color("titlebar.btn_hover")
        self._gradient_colors = [
            t.color("titlebar.gradient_0"),
            t.color("titlebar.gradient_1"),
            t.color("titlebar.gradient_2"),
            t.color("titlebar.gradient_3"),
            t.color("titlebar.gradient_4"),
        ]
        self.setStyleSheet(f"background-color: {tb_bg};")
        self.icon_btn.setStyleSheet(
            f"""
            QPushButton{{color: {tb_text}; background-color: transparent; border: none; border-radius: 4px; font-size: 13px;}}"""
        )
        self.menubar.setStyleSheet(
            f"""
            QMenuBar {{background-color: transparent; color: {t.color("menubar.text")}; font-size: 13px; border: none;}}
            QMenuBar::item {{background: transparent; padding: 7px 5px; margin: 0px 2px; border-radius: 4px;}}
            QMenuBar::item:selected {{background-color: {t.color("menubar.selected")}; color: {t.color("menubar.text_bright")};}}
            QMenu {{background-color: {t.color("menu.background")}; color: {t.color("menu.text")}; border: 1px solid {t.color("menu.border")}; padding: 4px 6px;}}
            QMenu::item {{min-width: 300px; padding: 8px 15px 8px 32px; background-color: transparent; margin: 0px;}}
            QMenu::item:selected {{background-color: {t.color("menu.selected")}; color: {t.color("menubar.text_bright")};}}
            QMenu::icon {{position: absolute; left: 7px;}}
            QMenu::separator {{height: 1px; background-color: {t.color("menu.separator")}; margin: 4px 0px;}}"""
        )
        self.studioSearch.setStyleSheet(f"""
            QLineEdit{{background-color: transparent; color: {tb_text}; font-size:13px; font-style:normal; border:0.5px solid #9D9D9D; padding-left:15px; border-radius:5px;}}
            QLineEdit:placeholder{{font-style:italic;}}""")
        win_btn_style = f"""
            QPushButton{{color: {tb_text}; background-color: transparent; border: none; border-radius: 4px; font-size: 12px;}}
            QPushButton:hover{{background-color: {btn_hover};}}"""
        self.accountBtn.setStyleSheet(win_btn_style)
        self.btn_minimize.setStyleSheet(win_btn_style)
        self.btn_maximize.setStyleSheet(win_btn_style)
        self.btn_close.setStyleSheet(win_btn_style + f"""
            QPushButton:hover{{background-color: #E81123; color: white;}}""")

    def set_find_replace(self):
        return self.parent.toggle_find_replace()

    def set_search_in_selected(self):
        return

    def set_find_replace_in_files(self):
        return

    def set_manage_indentation(self):
        return
