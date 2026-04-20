from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QLineEdit,
    QFrame,
    QLabel,
    QStyle,
)
from PyQt6.QtGui import QColor, QPainter, QLinearGradient, QBrush, QPixmap

from editor.widgets.QCustomLabels import AnimatedGradientLabel


class EtherAIMainScreen(QFrame):
    def __init__(self, master=None):
        super().__init__(master)

        send_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight)

        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet("background-color: #1E1E1E;")
        self.background_img = QPixmap("assets/themes/bubble.png")

        self.gradient_start = (self.width(), self.height())

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(40, 40, 40, 40)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.is_active = False

        self.welcome_message = AnimatedGradientLabel("Hi, DreamStudio Developer", self)
        self._layout.addWidget(self.welcome_message)

        sub_text = QLabel("Ready to Start Creating?")
        sub_text.setStyleSheet(
            """color: #9aa0a6; 
            font-size: 18px; 
            font-family: 'inter'; 
            background-color: transparent;"""
        )
        self._layout.addWidget(sub_text)

        self._layout.addSpacing(int(self.height() / 2))

        self.prompt_box = QLineEdit()
        self.prompt_box.setStyleSheet(
            """background-color: transparent; 
               border: 1px solid #F5F5F5; 
               padding: 8px;
               border-radius: 8px;
               """
        )
        self._layout.addWidget(self.prompt_box)
        self._layout.addSpacing(10)

        self.send_prompt = QPushButton("Send")
        self.send_prompt.setIcon(send_icon)
        self.send_prompt.setFixedSize(90, 35)
        self.send_prompt.setStyleSheet(
            """QPushButton{
            border-radius: 8px; 
            background: #0060BF;}
            QPushButton:hover{
            background: #094E93;
            }"""
        )
        self._layout.addWidget(self.send_prompt)

        self._layout.addSpacing(40)

        self.features_label = QLabel()
        self.features_label.setText("Try these prompts first")
        self.features_label.setStyleSheet(
            """
            color: #F5F5F5; 
            font-size: 18px;
            font-family: 'inter'; 
            background-color: transparent;"""
        )
        self._layout.addWidget(self.features_label)
        self._layout.addSpacing(10)

        self.fix_issues_prompt = QPushButton("Review my code in the current file")
        self.fix_issues_prompt.setFixedSize(230, 35)
        self.fix_issues_prompt.setStyleSheet(
            """QPushButton{
            border-radius: 8px; 
            border: 2px solid #1088E3;
            background: transparent;}
            QPushButton:hover {
            border: 2px solid #0B5B98;}"""
        )
        self._layout.addWidget(self.fix_issues_prompt)

        self.add_documentation_prompt = QPushButton(
            "Add documentation to this file's methods and classes"
        )
        self.add_documentation_prompt.setFixedSize(350, 35)
        self.add_documentation_prompt.setStyleSheet(
            """QPushButton{
            border-radius: 8px; 
            border: 2px solid #1088E3;
            background: transparent;}
            QPushButton:hover {
            border: 2px solid #0B5B98;}"""
        )
        self._layout.addWidget(self.add_documentation_prompt)

        self._layout.addSpacing(40)

        self.warningsLabelAI = QLabel()
        self.warningsLabelAI.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.warningsLabelAI.setText("AI can make mistakes, so please check your codes")
        self.warningsLabelAI.setStyleSheet(
            """
            color: #A5A5A5; 
            font-size: 12px;
            font-family: 'inter'; 
            background-color: transparent;"""
        )
        self._layout.addWidget(self.warningsLabelAI)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        actual_width = event.size().width()

        if actual_width > 10 and not self.is_active:
            print("EtherAI Opened")
            self.is_active = True
            self.welcome_message.start_animation()

        elif actual_width <= 10 and self.is_active:
            print("EtherAI Closed")
            self.is_active = False
            self.welcome_message.stop_animation()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        if not self.background_img.isNull():
            painter.drawPixmap(self.rect(), self.background_img)

        gradient = QLinearGradient(
            self.width(), self.height(), self.width() / 2, self.height() / 2
        )

        gradient.setColorAt(0.0, QColor(81, 43, 214, 180))
        gradient.setColorAt(1.0, QColor(30, 30, 30, 100))

        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
