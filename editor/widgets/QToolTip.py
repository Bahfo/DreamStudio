from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QGuiApplication

from fonts.font_strapper import Fonts


class ToolTip(QFrame):
    def __init__(self, parent=None, text: str = ""):
        super().__init__(
            parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        self.label = QLabel(text, self)
        layout.addWidget(self.label)

        self.hide_timer = QTimer(self)
        self.hide_timer.setSingleShot(True)
        self.hide_timer.setInterval(200)
        self.hide_timer.timeout.connect(self.hide)

    def enterEvent(self, event):
        self.hide_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hide_timer.start()
        super().leaveEvent(event)

    def show_at_widget(self, target_widget):
        self.hide_timer.stop()
        global_target_pos = target_widget.mapToGlobal(
            QPoint(0, target_widget.height() + 4)
        )
        self.adjustSize()
        tooltip_width = self.width()

        screen = QGuiApplication.screenAt(global_target_pos)
        if not screen:
            screen = QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry()

        target_x = global_target_pos.x()
        target_y = global_target_pos.y()

        if target_x + tooltip_width > screen_geo.right():
            target_x = screen_geo.right() - tooltip_width - 8

        self.move(target_x, target_y)
        self.show()

    def start_hide_sequence(self):
        self.hide_timer.start()

    def set_commit_info(self, commit_sha, author, date, message, branch="main"):
        """
        A dedicated function to set the tooltip for Git Source Control.
        """

        html_content = f"""
        <div style="font-family: '{Fonts.FONT_INTER}', '{Fonts.FONT_SEGOE_UI}', Arial, sans-serif; 
            font-size: 13px; 
            line-height: 1.4; 
            color: #cccccc;">
            <div style="margin-bottom: 8px;">
                <!-- Author Link Name -->
                <span style="color: #3794ff; 
                    font-weight: 500; 
                    font-size: 13px; 
                    margin-left: 2px;">
                    {author}
                </span>

                <span style="color: #969696; 
                    font-size: 12px; 
                    margin-left: 4px;">
                    {date}
                </span>
            </div>
            
            <div style="color: #e3e3e3; 
                font-size: 13px; 
                margin-bottom: 12px; 
                font-weight: 400;">
                Commit Message: {message}
            </div>
            
            <hr style="border: 0; border-top: 1px solid #303031; margin: 8px 0;" />

            <div style="font-size: 12px; color: #3794ff;">
                <span style="color: #58a6ff; 
                    font-weight: bold; 
                    font-size: 14px;">⚲</span> 
                <span style="font-family: monospace; 
                    margin-left: 2px;">
                    SHA Build Number: {commit_sha[:7]}
                </span> 
            </div>
        </div>
        """
        self.label.setText(html_content)
