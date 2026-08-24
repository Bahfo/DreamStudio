from editor import *

from fonts.font_strapper import Fonts

# Local Imports
from editor.base.user.gradient import GradientBanner

_THEME_DIR = os.path.join(os.path.dirname(__file__), "theme")
_LIGHT_QSS = os.path.join(_THEME_DIR, "light.qss")
_DARK_QSS = os.path.join(_THEME_DIR, "dark.qss")


class IDEStartPage(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Start Page - Custom IDE")
        self.resize(1024, 750)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.banner_widget = GradientBanner(self)
        self.banner_widget.setObjectName("BannerWidget")

        banner_layout = QVBoxLayout(self.banner_widget)
        banner_layout.setContentsMargins(40, 0, 0, 0)
        banner_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_label = QLabel("DreamStudio 2026")
        title_label.setObjectName("BannerTitle")
        banner_layout.addWidget(title_label)
        title_label.setStyleSheet(
            f"font-family: '{Fonts.FONT_MONTSERRAT}', Arial, sans-serif;"
        )

        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 30, 40, 30)
        content_layout.setSpacing(50)

        self.left_column = QWidget()
        left_layout = QVBoxLayout(self.left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        btn_new = QPushButton("Start a New Project")
        btn_open = QPushButton("Open a Recent Project")
        btn_new.setObjectName("ActionLink")
        btn_open.setObjectName("ActionLink")
        btn_new.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)

        left_layout.addWidget(btn_new)
        left_layout.addWidget(btn_open)

        recent_header = QLabel("Recent Projects")
        recent_header.setObjectName("SectionHeader")
        left_layout.addSpacing(20)
        left_layout.addWidget(recent_header)
        left_layout.addStretch()

        self.right_column = QWidget()
        right_layout = QVBoxLayout(self.right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)

        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(15)

        self.btn_get_started = QPushButton("Get Started")
        self.btn_get_started.setObjectName("ActiveTab")
        self.btn_get_started.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_get_started.clicked.connect(lambda: self.switch_main_tab(0))

        self.btn_latest_news = QPushButton("Latest News")
        self.btn_latest_news.setObjectName("InactiveTab")
        self.btn_latest_news.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_latest_news.clicked.connect(lambda: self.switch_main_tab(1))

        tab_layout.addWidget(self.btn_get_started)
        tab_layout.addWidget(self.btn_latest_news)
        tab_layout.addStretch()

        self.btn_theme_toggle = QPushButton("Switch Theme")
        self.btn_theme_toggle.setObjectName("ThemeToggleBtn")
        self.btn_theme_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_theme_toggle.clicked.connect(self.retheme)
        tab_layout.addWidget(self.btn_theme_toggle)

        right_layout.addLayout(tab_layout)

        self.main_stack = QStackedWidget()
        right_layout.addWidget(self.main_stack)

        self.page_get_started = QWidget()
        get_started_layout = QVBoxLayout(self.page_get_started)
        get_started_layout.setContentsMargins(0, 0, 0, 0)

        sub_nav_layout = QHBoxLayout()
        sub_nav_layout.setSpacing(20)
        sub_nav_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.sub_buttons = []
        sub_links = ["Welcome", "Learn", "Upgrade"]
        for i, link_text in enumerate(sub_links):
            btn_sub = QPushButton(link_text)
            btn_sub.setObjectName("SubNavLink")
            btn_sub.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_sub.clicked.connect(lambda checked, index=i: self.switch_sub_tab(index))
            sub_nav_layout.addWidget(btn_sub)
            self.sub_buttons.append(btn_sub)

        get_started_layout.addLayout(sub_nav_layout)
        get_started_layout.addSpacing(5)

        self.sub_stack = QStackedWidget()
        get_started_layout.addWidget(self.sub_stack)

        self.page_welcome = QWidget()
        welcome_layout = QVBoxLayout(self.page_welcome)
        welcome_layout.setContentsMargins(0, 0, 0, 0)

        news_box = QFrame()
        news_box.setObjectName("NewsBox")
        news_box_layout = QVBoxLayout(news_box)
        news_box_layout.setContentsMargins(20, 20, 20, 20)
        news_box_layout.setSpacing(12)

        box_title = QLabel("Welcome to DreamStudio 2026 - Quiet Vally Edition")
        box_title.setObjectName("NewsBoxTitle")
        box_desc = QLabel(
            "Start your journey by exploring DreamStudio through a set of comprehensive "
            "tutorials designed to get your started in no time with the all features "
            "designed in DreamStudio. You can see the Beginners Tutorials (accessed below), "
            "view the community forum support hub. Or access the Core API Documentations."
        )
        box_desc.setObjectName("NewsBoxDescription")
        box_desc.setWordWrap(True)

        news_box_layout.addWidget(box_title)
        news_box_layout.addWidget(box_desc)
        news_box_layout.addSpacing(5)

        for blink in [
            "Beginner Developer Learning Center",
            "Community Forum Support Hub",
            "Core API Documentation",
        ]:
            btn_blink = QPushButton(blink)
            btn_blink.setObjectName("ActionLink")
            btn_blink.setCursor(Qt.CursorShape.PointingHandCursor)
            news_box_layout.addWidget(btn_blink)

        welcome_layout.addWidget(news_box)
        welcome_layout.addStretch()

        self.page_learn = QWidget()
        learn_layout = QVBoxLayout(self.page_learn)
        learn_layout.addWidget(
            QLabel("Learn Tab: Video tutorials and docs will go here.")
        )
        learn_layout.addStretch()

        self.page_upgrade = QWidget()
        upgrade_layout = QVBoxLayout(self.page_upgrade)
        upgrade_layout.addWidget(QLabel("Upgrade Tab: License information goes here."))
        upgrade_layout.addStretch()

        self.sub_stack.addWidget(self.page_welcome)
        self.sub_stack.addWidget(self.page_learn)
        self.sub_stack.addWidget(self.page_upgrade)

        self.page_latest_news = QWidget()
        latest_news_layout = QVBoxLayout(self.page_latest_news)
        latest_news_layout.setContentsMargins(0, 0, 0, 0)

        self.main_stack.addWidget(self.page_get_started)
        self.main_stack.addWidget(self.page_latest_news)

        content_layout.addWidget(self.left_column, stretch=3)
        content_layout.addWidget(self.right_column, stretch=5)

        main_layout.addWidget(self.banner_widget)
        main_layout.addWidget(content_widget, stretch=1)

        self._dark = False
        self.apply_styles()

    def switch_main_tab(self, index):
        """Switches between Get Started and Latest News"""
        self.main_stack.setCurrentIndex(index)

        if index == 0:
            self.btn_get_started.setObjectName("ActiveTab")
            self.btn_latest_news.setObjectName("InactiveTab")
        else:
            self.btn_get_started.setObjectName("InactiveTab")
            self.btn_latest_news.setObjectName("ActiveTab")

        self.btn_get_started.style().unpolish(self.btn_get_started)
        self.btn_get_started.style().polish(self.btn_get_started)
        self.btn_latest_news.style().unpolish(self.btn_latest_news)
        self.btn_latest_news.style().polish(self.btn_latest_news)

    def switch_sub_tab(self, index):
        """Switches between Welcome, Learn, and Upgrade"""
        self.sub_stack.setCurrentIndex(index)

    def apply_styles(self):
        path = _DARK_QSS if self._dark else _LIGHT_QSS
        try:
            with open(path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Failed to load theme: {e}")

    def retheme(self):
        self._dark = not self._dark
        self.banner_widget.set_dark_mode(self._dark)
        self.btn_theme_toggle.setText("Light Theme" if self._dark else "Dark Theme")
        self.apply_styles()
