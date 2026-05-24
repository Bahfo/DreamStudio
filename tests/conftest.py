import sys
from unittest.mock import MagicMock

_pyqt6_modules = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.Qsci",
    "PyQt6.QtWebEngineWidgets",
]

def _build_mock_hierarchy():
    root = MagicMock()
    class _MockWithParent(MagicMock):
        """Mock that ignores positional __init__ args (avoids spec-on-mock error)."""
        def __init__(self, *args, **kwargs):
            super().__init__()
        def _get_child_mock(self, **kw):
            return MagicMock(**kw)

    root.QtCore = MagicMock()
    root.QtCore.Qt = MagicMock()
    root.QtCore.QTimer = _MockWithParent
    root.QtCore.QThread = _MockWithParent
    root.QtCore.pyqtSignal = lambda *a, **kw: MagicMock()
    root.QtCore.QMutex = _MockWithParent
    root.QtCore.QWaitCondition = _MockWithParent
    root.QtCore.QObject = _MockWithParent
    root.QtCore.QDir = _MockWithParent
    root.QtCore.QEvent = _MockWithParent
    root.QtCore.QSize = _MockWithParent
    root.QtCore.QUrl = _MockWithParent
    root.QtCore.QPoint = _MockWithParent
    root.QtCore.QRect = _MockWithParent
    root.QtCore.QDir = _MockWithParent

    root.QtCore.Qt.KeyboardModifier = type("KeyboardModifier", (), {
        "ControlModifier": 67108864,
        "MetaModifier": 268435456,
    })
    root.QtCore.Qt.MouseButton = type("MouseButton", (), {
        "LeftButton": 1,
    })
    root.QtCore.Qt.AlignmentFlag = type("AlignmentFlag", (), {
        "AlignLeft": 1,
        "AlignVCenter": 4,
        "AlignTop": 32,
        "AlignCenter": 132,
    })
    root.QtCore.Qt.WindowType = type("WindowType", (), {
        "ToolTip": 256,
        "FramelessWindowHint": 2048,
        "Window": 511,
    })
    root.QtCore.Qt.WidgetAttribute = type("WidgetAttribute", (), {
        "WA_Hover": 128,
        "WA_ShowWithoutActivating": 256,
        "WA_TransparentForMouseEvents": 512,
    })
    root.QtCore.Qt.FocusPolicy = type("FocusPolicy", (), {
        "NoFocus": 0,
    })
    root.QtCore.Qt.TextElideMode = type("TextElideMode", (), {
        "ElideRight": 1,
    })
    root.QtCore.Qt.ShortcutContext = type("ShortcutContext", (), {
        "ApplicationShortcut": 0,
    })
    root.QtCore.Qt.ScrollBarPolicy = type("ScrollBarPolicy", (), {
        "ScrollBarAlwaysOff": 0,
    })
    root.QtCore.Qt.CursorShape = type("CursorShape", (), {
        "PointingHandCursor": 14,
    })
    root.QtCore.Qt.Orientation = type("Orientation", (), {
        "Vertical": 1,
        "Horizontal": 2,
    })

    root.QtGui = MagicMock()
    root.QtGui.QFont = _MockWithParent
    root.QtGui.QIcon = _MockWithParent
    root.QtGui.QColor = _MockWithParent
    root.QtGui.QKeyEvent = MagicMock
    root.QtGui.QPainter = MagicMock
    root.QtGui.QPixmap = MagicMock
    root.QtGui.QLinearGradient = MagicMock
    root.QtGui.QBrush = MagicMock
    root.QtGui.QPen = MagicMock
    root.QtGui.QPalette = MagicMock
    root.QtGui.QPainterPath = MagicMock
    root.QtGui.QShortcut = MagicMock
    root.QtGui.QKeySequence = MagicMock
    root.QtGui.QWindow = MagicMock

    root.QtWidgets = MagicMock()
    root.QtWidgets.QApplication = MagicMock
    root.QtWidgets.QWidget = MagicMock
    root.QtWidgets.QMainWindow = MagicMock
    root.QtWidgets.QFrame = MagicMock
    root.QtWidgets.QPushButton = MagicMock
    root.QtWidgets.QVBoxLayout = MagicMock
    root.QtWidgets.QHBoxLayout = MagicMock
    root.QtWidgets.QSplitter = MagicMock
    root.QtWidgets.QStackedWidget = MagicMock
    root.QtWidgets.QFileDialog = MagicMock
    root.QtWidgets.QListWidget = MagicMock
    root.QtWidgets.QListWidgetItem = MagicMock
    root.QtWidgets.QTabWidget = MagicMock
    root.QtWidgets.QTabBar = MagicMock
    root.QtWidgets.QStyle = MagicMock
    root.QtWidgets.QLabel = MagicMock
    root.QtWidgets.QComboBox = MagicMock
    root.QtWidgets.QToolTip = MagicMock
    root.QtWidgets.QStyleOptionTab = MagicMock
    root.QtWidgets.QGraphicsOpacityEffect = MagicMock
    root.QtWidgets.QShortcut = MagicMock

    root.QtWidgets.QStyle.StateFlag = type("StateFlag", (), {
        "State_MouseOver": 1,
        "State_HasFocus": 2,
    })
    root.QtWidgets.QStyle.ControlElement = type("ControlElement", (), {
        "CE_TabBarTabLabel": 1,
    })
    root.QtWidgets.QStyle.StandardPixmap = type("StandardPixmap", (), {
        "SP_MessageBoxWarning": 1,
    })

    class _QsciLexerCustomMock:
        """Mock base for QsciLexerCustom subclasses; returns MagicMock for unknown attrs."""
        def __init__(self, parent=None):
            self._mock_state = 0
        def __getattr__(self, name):
            if name.startswith('_'):
                raise AttributeError(name)
            return MagicMock()
        def state(self):
            return self._mock_state
        def setState(self, val):
            self._mock_state = val
        def editor(self):
            return getattr(self, '_mock_editor', None)
        def setEditor(self, editor):
            self._mock_editor = editor

    root.Qsci = MagicMock()
    root.Qsci.QsciScintilla = MagicMock
    root.Qsci.QsciLexerCustom = _QsciLexerCustomMock
    root.Qsci.QsciLexerCMake = MagicMock
    root.Qsci.QsciAPIs = MagicMock

    root.Qsci.QsciScintilla.EdgeMode = type("EdgeMode", (), {
        "EdgeLine": 1,
    })
    root.Qsci.QsciScintilla.MarginType = type("MarginType", (), {
        "NumberMargin": 0,
        "SymbolMargin": 1,
    })
    root.Qsci.QsciScintilla.FoldStyle = type("FoldStyle", (), {
        "PlainFoldStyle": 0,
    })
    root.Qsci.QsciScintilla.MarkerSymbol = type("MarkerSymbol", (), {
        "Plus": 2,
        "Minus": 3,
    })
    root.Qsci.QsciScintilla.AutoCompletionSource = type("AutoCompletionSource", (), {
        "AcsNone": 0,
    })
    root.Qsci.QsciScintilla.IndicatorStyle = type("IndicatorStyle", (), {
        "TextColorIndicator": 0,
        "RoundBoxIndicator": 1,
        "ThinCompositionIndicator": 2,
        "SquiggleIndicator": 3,
    })
    root.Qsci.QsciScintilla.WrapMode = type("WrapMode", (), {
        "WrapWord": 0,
        "WrapNone": 1,
    })
    root.Qsci.QsciScintilla.BraceMatch = type("BraceMatch", (), {
        "StrictBraceMatch": 0,
    })
    root.Qsci.QsciScintilla.EolMode = type("EolMode", (), {
        "EolWindows": 1,
        "EolMac": 2,
        "EolUnix": 3,
    })

    root.Qsci.QsciScintilla.SCI_POSITIONFROMPOINT = 2027
    root.Qsci.QsciScintilla.SCI_GETCURRENTPOS = 2008
    root.Qsci.QsciScintilla.SCI_POINTXFROMPOSITION = 2165
    root.Qsci.QsciScintilla.SCI_POINTYFROMPOSITION = 2166

    root.QtWebEngineWidgets = MagicMock()
    root.QtWebEngineWidgets.QWebEngineView = MagicMock

    return root


mock_pyqt6 = _build_mock_hierarchy()

for mod_name in _pyqt6_modules:
    if mod_name == "PyQt6":
        sys.modules["PyQt6"] = mock_pyqt6
    elif mod_name.startswith("PyQt6."):
        parts = mod_name.split(".")
        target = mock_pyqt6
        for part in parts[1:]:
            target = getattr(target, part)
        sys.modules[mod_name] = target
