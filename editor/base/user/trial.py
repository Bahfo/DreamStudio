from editor import *


class FreeTrialWindow(QWidget):
    """
    A modern, sleek free trial and subscription window for DreamStudio.
    """

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self._layout = QVBoxLayout(self)

        self._layout.setContentsMargins(30, 30, 30, 30)
        self._layout.setSpacing(14)
        self.setStyleSheet("""
            QWidget {
                background-color: #0B0C10;
                color: #C5C6C7;
                font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
            }
        """)

        self.title = QLabel("Build Effortlessly with DreamStudio")
        self.title.setStyleSheet("""
            color: #FFFFFF;
            font-size: 32px;
            font-weight: 700;
            letter-spacing: -0.5px;
            background: transparent;
        """)

        self.explaination1 = QLabel(
            "Get more out of DreamStudio and elevate your productivity with powerful "
            "extended tools designed to make your development faster, smoother, "
            "and more enjoyable."
        )
        self.explaination1.setWordWrap(True)
        self.explaination1.setStyleSheet("""
            color: #8E95A5;
            font-size: 15px;
            line-height: 1.4;
            background: transparent;
        """)

        self.access_layout = QHBoxLayout()
        self.access_layout.setContentsMargins(0, 10, 0, 10)
        self.access_layout.setSpacing(14)

        self.start_trial_btn = QPushButton("Start Free Trial")
        self.start_trial_btn.setFixedSize(180, 46)
        self.start_trial_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_trial_btn.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                border: none;
                background-color: #6366F1;
                color: #FFFFFF;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4F46E5;
            }
            QPushButton:pressed {
                background-color: #4338CA;
            }
        """)

        self.subscribe_btn = QPushButton("Purchase Now")
        self.subscribe_btn.setFixedSize(180, 46)
        self.subscribe_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.subscribe_btn.setStyleSheet("""
            QPushButton {
                border-radius: 8px;
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid #2D313E;
                color: #E2E8F0;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.08);
                border-color: #4B5563;
                color: #FFFFFF;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.02);
            }
        """)

        self.access_layout.addWidget(self.start_trial_btn)
        self.access_layout.addWidget(self.subscribe_btn)
        self.access_layout.addStretch()

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(
            "background-color: #1A1C24; min-height: 1px; max-height: 1px; border: none;"
        )

        self.explaination2 = QLabel("Perks of Subscription")
        self.explaination2.setStyleSheet("""
            color: #FFFFFF;
            font-size: 22px;
            font-weight: 600;
            background: transparent;
            margin-top: 6px;
        """)

        self.explaination3 = QLabel(
            "Unlock the next level of development using tools that help you write code faster and safer."
        )
        self.explaination3.setWordWrap(True)
        self.explaination3.setStyleSheet("""
            color: #8E95A5;
            font-size: 14px;
            background: transparent;
        """)

        self.perks_label = QLabel()
        self.perks_label.setWordWrap(True)
        self.perks_label.setTextFormat(Qt.TextFormat.RichText)
        self.perks_label.setStyleSheet("background: transparent;")
        self.perks_label.setText("""
        <style>
            .perk-list {
                margin: 0;
                padding: 0;
                list-style-type: none;
            }
            .perk-item {
                margin-bottom: 12px;
                font-size: 14px;
                line-height: 1.5;
            }
            .check-icon {
                color: #6366F1;
                font-weight: bold;
                font-size: 15px;
                margin-right: 8px;
            }
            .title {
                color: #F3F4F6;
                font-weight: 600;
            }
            .desc {
                color: #9CA3AF;
            }
        </style>
        <div class="perk-list">
            <div class="perk-item">
                <span class="check-icon">✓</span>
                <span class="title"> Advanced Debugging:</span> 
                <span class="desc">Tools like IntelliTrace and a comprehensive debugging system.</span>
            </div>
            <div class="perk-item">
                <span class="check-icon">✓</span>
                <span class="title"> Code Quality Tools:</span> 
                <span class="desc">Automated test generation and integrated code quality testing.</span>
            </div>
            <div class="perk-item">
                <span class="check-icon">✓</span>
                <span class="title"> Cloud Subscription:</span> 
                <span class="desc">Expanded access to EXcellent TechStacks cloud services.</span>
            </div>
            <div class="perk-item">
                <span class="check-icon">✓</span>
                <span class="title"> Learning Resources:</span> 
                <span class="desc">Extensive documentation and guides to accelerate learning.</span>
            </div>
            <div class="perk-item">
                <span class="check-icon">✓</span>
                <span class="title"> Specialized Plugins:</span> 
                <span class="desc">Dedicated extensions for data tools, visualization, SQL, and databases.</span>
            </div>
            <div class="perk-item">
                <span class="check-icon">✓</span>
                <span class="title"> AI Assistance:</span> 
                <span class="desc">Powered by Ether AI with non-resetting generation context as long as you're subscribed.</span>
            </div>
        </div>
        """)

        self._layout.addWidget(self.title)
        self._layout.addWidget(self.explaination1)
        self._layout.addLayout(self.access_layout)
        self._layout.addSpacing(10)
        self._layout.addWidget(divider)
        self._layout.addSpacing(6)
        self._layout.addWidget(self.explaination2)
        self._layout.addWidget(self.explaination3)
        self._layout.addSpacing(8)
        self._layout.addWidget(self.perks_label)
        self._layout.addStretch()
