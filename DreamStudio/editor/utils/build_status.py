from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import QFrame, QPushButton, QHBoxLayout, QComboBox, QLabel


class BuildFunctionalityBar(QFrame):
    def __init__(self, master):
        super().__init__(master)

        self.setFrameShape(QFrame.Shape.Panel)
        self.setFixedSize(450, 30)
        self.setStyleSheet(
            """
        QFrame{
        border: 0;
        border-radius: 0px;
        background-color: #25272B;
        }"""
        )
        buildbar_layout = QHBoxLayout(self)
        buildbar_layout.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        buildbar_layout.setContentsMargins(5, 0, 5, 0)

        #################################
        # Running Status
        #################################
        self.runningStatus = QLabel()
        self.runningStatus.setText("Status: Running")
        self.runningStatus

        self.rerunBtn = QPushButton()
        self.rerunBtn.setFixedSize(30, 28)
        self.rerunBtn.setIcon(QIcon("assets/system/replay.png"))
        self.rerunBtn.setIconSize(QSize(20, 20))
        self.rerunBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        buildbar_layout.addWidget(self.rerunBtn)

        self.pauseBtn = QPushButton()
        self.pauseBtn.setFixedSize(30, 28)
        self.pauseBtn.setIcon(QIcon("assets/system/pause.png"))
        self.pauseBtn.setIconSize(QSize(20, 20))
        self.pauseBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        buildbar_layout.addWidget(self.pauseBtn)

        self.stopBtn = QPushButton()
        self.stopBtn.setFixedSize(30, 28)
        self.stopBtn.setIcon(QIcon("assets/system/stop.png"))
        self.stopBtn.setIconSize(QSize(20, 20))
        self.stopBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        buildbar_layout.addWidget(self.stopBtn)

        self.stepInBtn = QPushButton()
        self.stepInBtn.setFixedSize(30, 28)
        self.stepInBtn.setIcon(QIcon("assets/system/step_forward.png"))
        self.stepInBtn.setIconSize(QSize(20, 20))
        self.stepInBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        buildbar_layout.addWidget(self.stepInBtn)

        self.stepOutBtn = QPushButton()
        self.stepOutBtn.setFixedSize(30, 28)
        self.stepOutBtn.setIcon(QIcon("assets/system/step_back.png"))
        self.stepOutBtn.setIconSize(QSize(20, 20))
        self.stepOutBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        buildbar_layout.addWidget(self.stepOutBtn)

        self.hotRunBtn = QPushButton()
        self.hotRunBtn.setFixedSize(30, 28)
        self.hotRunBtn.setIcon(QIcon("assets/system/hot_run.png"))
        self.hotRunBtn.setIconSize(QSize(23, 23))
        self.hotRunBtn.setStyleSheet(
            """
        QPushButton{
        background-color: transparent;
        border: none;
        color: white;
        border-radius: 10px;
        padding-top:4px;
        padding-left:2px;
        padding-right:2px;
        }
        QPushButton:hover{background-color:#333}"""
        )
        buildbar_layout.addWidget(self.hotRunBtn)
