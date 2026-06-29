from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QMenu,
)


class CardButton(QWidget):
    def __init__(self, icon_path, title, description, publisher, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.init_ui(icon_path, title, description, publisher)

    def init_ui(self, icon_path, title, description, publisher):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(12)
        self.setObjectName("CardButton")

        self.icon_label = QLabel(self)
        self.icon_label.setFixedSize(48, 48)
        self.set_circular_icon(icon_path)
        main_layout.addWidget(self.icon_label)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title, self)
        self.title_label.setObjectName("TitleLabel")

        self.desc_label = QLabel(description, self)
        self.desc_label.setObjectName("DescLabel")
        self.desc_label.setWordWrap(True)

        self.pub_label = QLabel(publisher, self)
        self.pub_label.setObjectName("PubLabel")

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.desc_label)
        text_layout.addWidget(self.pub_label)

        main_layout.addLayout(text_layout, stretch=1)

        self.install_btn = QPushButton("Install", self)
        self.install_btn.setFixedSize(70, 24)
        self.install_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.action_menu = QMenu(self)
        self.action_menu.addAction("Install Release Version")
        self.action_menu.addAction("Install Pre-Release Version")
        self.install_btn.setMenu(self.action_menu)

        main_layout.addWidget(self.install_btn, alignment=Qt.AlignmentFlag.AlignTop)

        self.setStyleSheet(
            """
            QWidget {
                background-color: #181818;
                font-family: 'inter', Arial;}
            CardButton:hover {background-color: #202020;}
            QLabel {background-color: transparent;}
            #TitleLabel {
                color: #cccccc;
                font-size: 13px;
                font-weight: bold;}
            #DescLabel {
                color: #858585;
                font-size: 12px;}
            #PubLabel {
                color: #858585;
                font-size: 11px;}
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 12px;
                font-weight: 500;
                padding-right: 15px;}
            QPushButton::menu-indicator {
                image: none;
                subcontrol-position: right center;
                subcontrol-origin: padding;
                left: -4px;}
            ExtensionCard:hover QPushButton {
                background-color: #1177bb;
                color: white;}
            QMenu {
                background-color: #1f1f1f;
                border: 1px solid #454545;
                color: #cccccc;
                padding: 4px 0px;}
            QMenu::item {
                padding: 6px 20px 6px 12px;
                font-size: 12px;}
            QMenu::item:selected {
                background-color: #007acc;
                color: white;}
        """
        )

    def retheme(self, t) -> None:
        bg = t.color("card.background")
        hover_bg = t.color("widget.border")
        title_fg = t.color("widget.text_bright")
        desc_fg = t.color("widget.text")
        accent = t.color("widget.accent")
        btn_hover = t.color("button.hover")
        menu_bg = t.color("menu.background")
        menu_fg = t.color("menu.text")
        menu_sel = t.color("menu.selected")
        menu_border = t.color("menu.border")
        self.setStyleSheet(
            f"""
            QWidget {{
                background-color: {bg};
                font-family: 'inter', Arial;}}
            CardButton:hover {{background-color: {hover_bg};}}
            QLabel {{background-color: transparent;}}
            #TitleLabel {{
                color: {title_fg};
                font-size: 13px;
                font-weight: bold;}}
            #DescLabel {{
                color: {desc_fg};
                font-size: 12px;}}
            #PubLabel {{
                color: {desc_fg};
                font-size: 11px;}}
            QPushButton {{
                background-color: {accent};
                color: white;
                border: none;
                border-radius: 2px;
                font-size: 12px;
                font-weight: 500;
                padding-right: 15px;}}
            QPushButton:hover {{
                background-color: {btn_hover};}}
            QPushButton::menu-indicator {{
                image: none;
                subcontrol-position: right center;
                subcontrol-origin: padding;
                left: -4px;}}
            QMenu {{
                background-color: {menu_bg};
                border: 1px solid {menu_border};
                color: {menu_fg};
                padding: 4px 0px;}}
            QMenu::item {{
                padding: 6px 20px 6px 12px;
                font-size: 12px;}}
            QMenu::item:selected {{
                background-color: {menu_sel};
                color: white;}}
        """
        )

    def set_circular_icon(self, icon_path):
        """Creates a smooth circular cutout for any source image."""
        src_pixmap = QPixmap(icon_path)
        if src_pixmap.isNull():
            self.icon_label.setStyleSheet(
                "background-color: #333; border-radius: 24px;"
            )
            return

        size = self.icon_label.size()
        target = QPixmap(size)
        target.fill(Qt.GlobalColor.transparent)

        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        path = QPainterPath()
        path.addEllipse(0, 0, size.width(), size.height())
        painter.setClipPath(path)

        painter.drawPixmap(0, 0, size.width(), size.height(), src_pixmap)
        painter.end()

        self.icon_label.setPixmap(target)
