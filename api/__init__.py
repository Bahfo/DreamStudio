"""
DreamStudio API - Public API for building DreamStudio IDE extensions.

Usage:
    from api import DreamStudioAPI

    # After creating the DreamStudio window:
    app_api = DreamStudioAPI(main_window)
    app_api.codeEditor.openFile("path/to/file.py")
"""

from api.code_editor_api import CodeEditorAPI
from api.tab_editor_api import TabEditorAPI
from api.file_explorer_api import FileExplorerAPI
from api.theme_api import ThemeAPI, SyntaxThemeAPI
from api.terminal_api import TerminalAPI
from api.git_api import GitAPI
from api.project_api import ProjectAPI
from api.search_api import SearchAPI
from api.ui_api import UIAPI
from api.analyzer_api import AnalyzerAPI
from api.lsp_api import LspAPI
from api.marketplace_api import MarketplaceAPI
from api.tools_api import ToolsAPI
from api.status_bar_api import StatusBarAPI
from api.title_bar_api import TitleBarAPI
from api.options_bar_api import OptionsBarAPI
from api.source_control_api import SourceControlAPI


class DreamStudioAPI:
    """Unified facade for all DreamStudio IDE APIs."""

    def __init__(self, main_window):
        """
        Initialize the DreamStudio API with the main window instance.

        Args:
            main_window: The DreamStudio(QMainWindow) instance.
        """
        self._main = main_window
        self._code_editor = None
        self._tab_editor = None
        self._file_explorer = None
        self._theme = None
        self._syntax_theme = None
        self._terminal = None
        self._git = None
        self._project = None
        self._search = None
        self._ui = None
        self._analyzer = None
        self._lsp = None
        self._marketplace = None
        self._tools = None
        self._status_bar = None
        self._title_bar = None
        self._options_bar = None
        self._source_control = None

    @property
    def codeEditor(self) -> CodeEditorAPI:
        """Access the code editor API."""
        if self._code_editor is None:
            self._code_editor = CodeEditorAPI(self._main)
        return self._code_editor

    @property
    def tabEditor(self) -> TabEditorAPI:
        """Access the tab editor API."""
        if self._tab_editor is None:
            self._tab_editor = TabEditorAPI(self._main)
        return self._tab_editor

    @property
    def fileExplorer(self) -> FileExplorerAPI:
        """Access the file explorer API."""
        if self._file_explorer is None:
            self._file_explorer = FileExplorerAPI(self._main)
        return self._file_explorer

    @property
    def theme(self) -> ThemeAPI:
        """Access the UI theme API."""
        if self._theme is None:
            self._theme = ThemeAPI(self._main)
        return self._theme

    @property
    def syntaxTheme(self) -> SyntaxThemeAPI:
        """Access the syntax theme API."""
        if self._syntax_theme is None:
            self._syntax_theme = SyntaxThemeAPI(self._main)
        return self._syntax_theme

    @property
    def terminal(self) -> TerminalAPI:
        """Access the terminal API."""
        if self._terminal is None:
            self._terminal = TerminalAPI(self._main)
        return self._terminal

    @property
    def git(self) -> GitAPI:
        """Access the git/source control API."""
        if self._git is None:
            self._git = GitAPI(self._main)
        return self._git

    @property
    def project(self) -> ProjectAPI:
        """Access the project management API."""
        if self._project is None:
            self._project = ProjectAPI(self._main)
        return self._project

    @property
    def search(self) -> SearchAPI:
        """Access the find/replace API."""
        if self._search is None:
            self._search = SearchAPI(self._main)
        return self._search

    @property
    def ui(self) -> UIAPI:
        """Access the UI/window management API."""
        if self._ui is None:
            self._ui = UIAPI(self._main)
        return self._ui

    @property
    def analyzer(self) -> AnalyzerAPI:
        """Access the code analyzer API."""
        if self._analyzer is None:
            self._analyzer = AnalyzerAPI(self._main)
        return self._analyzer

    @property
    def lsp(self) -> LspAPI:
        """Access the LSP (Language Server Protocol) API."""
        if self._lsp is None:
            self._lsp = LspAPI(self._main)
        return self._lsp

    @property
    def marketplace(self) -> MarketplaceAPI:
        """Access the extensions marketplace API."""
        if self._marketplace is None:
            self._marketplace = MarketplaceAPI(self._main)
        return self._marketplace

    @property
    def tools(self) -> ToolsAPI:
        """Access the tools manager API."""
        if self._tools is None:
            self._tools = ToolsAPI(self._main)
        return self._tools

    @property
    def statusBar(self) -> StatusBarAPI:
        """Access the status bar API."""
        if self._status_bar is None:
            self._status_bar = StatusBarAPI(self._main)
        return self._status_bar

    @property
    def titleBar(self) -> TitleBarAPI:
        """Access the title bar API."""
        if self._title_bar is None:
            self._title_bar = TitleBarAPI(self._main)
        return self._title_bar

    @property
    def optionsBar(self) -> OptionsBarAPI:
        """Access the options bar API."""
        if self._options_bar is None:
            self._options_bar = OptionsBarAPI(self._main)
        return self._options_bar

    @property
    def sourceControl(self) -> SourceControlAPI:
        """Access the source control API."""
        if self._source_control is None:
            self._source_control = SourceControlAPI(self._main)
        return self._source_control

    def getCurrentEditor(self):
        """Get the current active code editor widget."""
        return self._main._get_current_editor()

    def getCurrentDirectory(self) -> str:
        """Get the current working directory."""
        return getattr(self._main, "currentDirectory", "")

    def setCurrentDirectory(self, path: str) -> None:
        """Set the current working directory."""
        self._main.currentDirectory = path
