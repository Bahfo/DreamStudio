from editor import *

class TitleBar(QWidget):
    def __init__(self, parent, title):
        super().__init__(parent)
        self._title_parent = parent
        self.setFixedHeight(40)
        self.offset = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._filter_window = self.window()
        try:
            self._filter_window.installEventFilter(self)
        except Exception:
            pass
        try:
            self.destroyed.connect(self._cleanup_filter)
        except Exception:
            pass

        #################################
        # Title
        #################################

        self.icon_btn = QPushButton(title)
        self.icon_btn.setIcon(QIcon("assets/dreamStudio_icon.png"))
        self.icon_btn.setIconSize(QSize(26, 26))
        self.icon_btn.setFixedHeight(30)
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

        self.btn_minimize.clicked.connect(self._title_parent.showMinimized)
        self.btn_close.clicked.connect(self._title_parent.close)

    def _cleanup_filter(self):
        win = getattr(self, "_filter_window", None)
        if win is not None:
            try:
                win.removeEventFilter(self)
            except Exception:
                pass

    def closeEvent(self, event):
        self._cleanup_filter()
        super().closeEvent(event)
