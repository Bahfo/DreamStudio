from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QFrame, QPushButton, QHBoxLayout


class VSeparator(QFrame):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(1)
        self.setFixedHeight(18)
        self.setStyleSheet("background-color: #444444; border: none;")
        self._color = "#444444"

    def retheme(self, t) -> None:
        self._color = t.color("optionsbar.separator")
        self.setStyleSheet(f"background-color: {self._color}; border: none;")


class OptionsMenu(QFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

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
        # File & Folder
        self.fileMenu = self.create_menu_button(
            text=None,
            image="assets/system/new.png",
            image_size=QSize(22, 22),
            tooltip="Create a new file",
            function=self._on_new_file,
        )
        self.folderMenu = self.create_menu_button(
            text=None,
            image="assets/system/open.png",
            image_size=QSize(18, 18),
            tooltip="Open a file",
            function=self._on_open_file,
        )

        optionsMenu_layout.addWidget(self.fileMenu)
        optionsMenu_layout.addWidget(self.folderMenu)

        optionsMenu_layout.addSpacing(3)
        optionsMenu_layout.addWidget(
            VSeparator(), alignment=Qt.AlignmentFlag.AlignVCenter
        )

        # Edit Operations
        self.cutBtn = self.create_menu_button(
            text=None,
            image="assets/system/cut.png",
            image_size=QSize(21, 21),
            tooltip="Cut selected text",
            function=self._on_cut,
        )
        self.copyBtn = self.create_menu_button(
            text=None,
            image="assets/system/copy.png",
            image_size=QSize(24, 24),
            tooltip="Copy selected text",
            function=self._on_copy,
        )
        self.pasteBtn = self.create_menu_button(
            text=None,
            image="assets/system/paste.png",
            image_size=QSize(22, 22),
            tooltip="Paste text from clipboard",
            function=self._on_paste,
        )
        self.undoBtn = self.create_menu_button(
            text=None,
            image="assets/system/undo.png",
            image_size=QSize(18, 18),
            tooltip="Undo last editor action",
            function=self._on_undo,
        )
        self.redoBtn = self.create_menu_button(
            text=None,
            image="assets/system/redo.png",
            image_size=QSize(18, 18),
            tooltip="Redo last editor action",
            function=self._on_redo,
        )
        self.saveBtn = self.create_menu_button(
            text=None,
            image="assets/system/save.png",
            image_size=QSize(24, 24),
            tooltip="Save file",
            function=self._on_save,
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
        self._text_btn_css_template = """
        QPushButton{{
            background-color: {bg};
            font-size:12px;
            border: none;
            color: {fg};
            border-radius: 0px;
            padding-left: 5px;
            padding-right: 10px;
        }}
        QPushButton:hover{{background-color: {hover};}}

        QToolTip{{
        color: {fg};
        font-family: 'inter';
        padding: 6px 5px;
        font-size: 12px;
        background-color: {bg};
        border: none;}}
        """
        text_btn_base_bg = "#34373C"
        text_btn_base_fg = "white"
        text_btn_base_hover = "#333"
        text_btn_css = self._text_btn_css_template.format(
            bg=text_btn_base_bg, fg=text_btn_base_fg, hover=text_btn_base_hover
        )

        # Tools & Execution
        self.monitor = self.create_menu_button(
            image="assets/system/monitor.png",
            image_size=QSize(17, 17),
            text="   Hardware Monitor",
            btn_size=QSize(150, 28),
            custom_css=text_btn_css,
            tooltip="Monitor hardware behavior while running your solution",
            function=self._on_open_monitor,
        )
        self.monitor.setProperty("_custom_text_btn", True)

        self.config_run_options = self.create_menu_button(
            image="assets/system/config.png",
            image_size=QSize(19, 19),
            text="   Run Configuration",
            btn_size=QSize(150, 28),
            custom_css=text_btn_css,
            tooltip="Configure running options for custom run and debug support",
        )
        self.config_run_options.setProperty("_custom_text_btn", True)

        self.runBtn = self.create_menu_button(
            text=None,
            image="assets/system/run.png",
            image_size=QSize(18, 18),
            tooltip="Run current file",
        )
        self.debugBtn = self.create_menu_button(
            text=None,
            image="assets/system/bug.png",
            image_size=QSize(22, 22),
            tooltip="Debug current file",
        )

        optionsMenu_layout.addWidget(self.monitor)
        optionsMenu_layout.addWidget(self.config_run_options)
        optionsMenu_layout.addWidget(self.runBtn)
        optionsMenu_layout.addWidget(self.debugBtn)

        optionsMenu_layout.addStretch()

        # Right-side Options
        self.etherAIBtn = self.create_menu_button(
            text=None,
            image="assets/system/ai.png",
            image_size=QSize(21, 21),
            tooltip="Open EtherAI",
        )
        self.readOnlyBtn = self.create_menu_button(
            text=None,
            image="assets/system/lock.png",
            image_size=QSize(19, 19),
            tooltip="Make current file read-only",
            function=self._on_toggle_readonly,
        )

        optionsMenu_layout.addWidget(self.etherAIBtn)
        optionsMenu_layout.addWidget(self.readOnlyBtn)

        self.searchBtn = self.create_menu_button(
            text=None,
            image="assets/system/search.png",
            image_size=QSize(21, 21),
            tooltip="Search inside the current file",
            function=self._on_search,
        )
        optionsMenu_layout.addWidget(self.searchBtn)

        self.settingsBtn = self.create_menu_button(
            text=None,
            image="assets/system/settings.png",
            tooltip="Show IDE Settings",
        )
        optionsMenu_layout.addWidget(self.settingsBtn)

    def create_menu_button(
        self,
        image,
        tooltip,
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
        btn.setToolTip(tooltip)

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

    def _get_current_editor(self):
        tabs = getattr(self.master, "tab_editors", None)
        if tabs:
            return tabs.currentWidget()
        return None

    def _on_new_file(self):
        if hasattr(self.master, "ui_build_add_new_editor"):
            self.master.ui_build_add_new_editor()

    def _on_open_file(self):
        if hasattr(self.master, "ui_build_open_file"):
            self.master.ui_build_open_file()

    def _on_cut(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "cut"):
            editor.cut()

    def _on_copy(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "copy"):
            editor.copy()

    def _on_paste(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "paste"):
            editor.paste()

    def _on_undo(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "undo"):
            editor.undo()

    def _on_redo(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "redo"):
            editor.redo()

    def _on_save(self):
        tabs = getattr(self.master, "tab_editors", None)
        if tabs and hasattr(tabs, "save_current_file"):
            tabs.save_current_file()

    def update_styles(self, t) -> None:
        bg = t.color("optionsbar.background")
        hover = t.color("button.hover")
        fg = t.color("button.text")
        tooltip_bg = t.color("tooltip.background")
        self.setStyleSheet(
            f"""
        QFrame{{border: 0px; border-radius: 0px; background-color: {bg};}}"""
        )
        for sep in self.findChildren(VSeparator):
            sep.retheme(t)
        for widget in self.findChildren(QPushButton):
            if widget.property("_custom_text_btn"):
                widget.setStyleSheet(
                    self._text_btn_css_template.format(bg=bg, fg=fg, hover=hover)
                )
            elif widget.property("_default_styled") is None:
                widget.setProperty("_default_styled", True)
            widget.setStyleSheet(
                f"""
                QPushButton{{background-color: transparent; 
                    border: none; color: {fg}; border-radius: 10px; 
                    padding-top:4px; padding-left:2px; padding-right:2px;}}
                QPushButton:hover{{background-color: {hover};}}
                QToolTip{{color: {fg}; font-family: 'inter'; padding: 6px 5px; 
                    font-size: 12px; background-color: {tooltip_bg}; 
                    border: none;}}
            """
            )

    def _on_open_monitor(self):
        if hasattr(self.master, "open_tools_panel"):
            self.master.open_tools_panel("system_monitor")

    def _on_search(self):
        if hasattr(self.master, "toggle_find_replace"):
            self.master.toggle_find_replace()

    def _on_toggle_readonly(self):
        editor = self._get_current_editor()
        if editor and hasattr(editor, "make_file_readonly"):
            editor.make_file_readonly()
