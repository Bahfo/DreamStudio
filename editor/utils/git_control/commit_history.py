# Written by Bahaa Nofal - 9/7/2026
# commit_history.py
"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Commit History Graph for DreamStudio: This module code sets up the graph
widget of Git Source Control. It follows branch history detailed strcuture.
Alongside the ability to view info about a certain push.
"""

from PyQt6.QtWidgets import (
    QStyledItemDelegate,
    QVBoxLayout,
    QTreeView,
    QWidget,
    QStyle,
)
from PyQt6.QtGui import (
    QStandardItemModel,
    QGuiApplication,
    QStandardItem,
    QPainter,
    QColor,
    QBrush,
    QFont,
    QPen,
)
from PyQt6.QtCore import Qt, QRectF, QEvent

from editor.widgets.QToolTip import ToolTip


class GitGraphDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lane_width = 20
        self.padding_left = 10
        self.lane_colors = [
            QColor("#3b82f6"),  # Blue
            QColor("#ef4444"),  # Red
            QColor("#10b981"),  # Emerald
            QColor("#f59e0b"),  # Amber
            QColor("#8b5cf6"),  # Purple
        ]

    def paint(self, painter: QPainter, option, index):
        lane = index.data(Qt.ItemDataRole.UserRole + 1)
        connections = index.data(Qt.ItemDataRole.UserRole + 2) or []
        message = index.data(Qt.ItemDataRole.UserRole + 3) or ""
        author = index.data(Qt.ItemDataRole.UserRole + 4) or ""

        if lane is None:
            super().paint(painter, option, index)
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        elif option.state & QStyle.StateFlag.State_MouseOver:
            painter.fillRect(option.rect, option.palette.alternateBase())

        row_y = option.rect.y()
        row_h = option.rect.height()
        center_y = row_y + (row_h / 2)

        max_seen_lane = lane
        for from_lane, to_lane in connections:
            max_seen_lane = max(max_seen_lane, from_lane, to_lane)

            color = self.lane_colors[from_lane % len(self.lane_colors)]
            painter.setPen(QPen(color, 2))

            start_x = (
                self.padding_left
                + (from_lane * self.lane_width)
                + (self.lane_width / 2)
            )
            end_x = (
                self.padding_left + (to_lane * self.lane_width) + (self.lane_width / 2)
            )

            if from_lane == to_lane:
                painter.drawLine(
                    int(start_x), int(row_y), int(start_x), int(row_y + row_h)
                )
            else:
                painter.drawLine(
                    int(start_x), int(row_y), int(end_x), int(row_y + row_h)
                )

        node_color = self.lane_colors[lane % len(self.lane_colors)]
        node_x = self.padding_left + (lane * self.lane_width) + (self.lane_width / 2)

        painter.setPen(QPen(QColor("#ffffff"), 1.5))
        painter.setBrush(QBrush(node_color))
        painter.drawEllipse(QRectF(node_x - 5, center_y - 5, 10, 10))

        text_start_x = self.padding_left + ((max_seen_lane + 1) * self.lane_width) + 15
        font_metrics = painter.fontMetrics()
        font = painter.font()

        font.setWeight(QFont.Weight.Normal)
        painter.setFont(font)
        painter.setPen(
            option.palette.text().color()
            if not (option.state & QStyle.StateFlag.State_Selected)
            else option.palette.highlightedText().color()
        )
        painter.drawText(int(text_start_x), int(center_y + 4), message)

        message_width = font_metrics.horizontalAdvance(message)
        font.setWeight(QFont.Weight.Light)
        painter.setFont(font)
        painter.setPen(
            option.palette.highlightedText().color()
            if (option.state & QStyle.StateFlag.State_Selected)
            else QColor("#888888")
        )
        painter.drawText(
            int(text_start_x + message_width + 12), int(center_y + 4), author
        )

        painter.restore()

    def sizeHint(self, option, index):
        return super().sizeHint(option, index).expandedTo(option.rect.size())


class GitGraph(QWidget):
    def __init__(self, commits: list):
        super().__init__()
        self.resize(600, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tree_view = QTreeView(self)
        self.tree_view.setObjectName("GitGraphTreeView")
        self.tree_view.setIndentation(0)
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setItemDelegate(GitGraphDelegate(self.tree_view))
        layout.addWidget(self.tree_view)

        self.tooltip = ToolTip(self.tree_view)

        self.tree_view.setMouseTracking(True)
        self.tree_view.entered.connect(self.on_tree_item_hovered)
        self.tree_view.viewport().installEventFilter(self)

        model = QStandardItemModel()
        for lane, connections, msg, author in commits:
            item = QStandardItem()
            item.setData(lane, Qt.ItemDataRole.UserRole + 1)
            item.setData(connections, Qt.ItemDataRole.UserRole + 2)
            item.setData(msg, Qt.ItemDataRole.UserRole + 3)
            item.setData(author, Qt.ItemDataRole.UserRole + 4)
            model.appendRow(item)

        self.tree_view.setModel(model)

    def eventFilter(self, source, event):
        if source == self.tree_view.viewport() and event.type() == QEvent.Type.Leave:
            self.tooltip.start_hide_sequence()
        return super().eventFilter(source, event)

    def on_tree_item_hovered(self, index):
        if not index.isValid():
            self.tooltip.start_hide_sequence()
            return

        lane = index.data(Qt.ItemDataRole.UserRole + 1)
        connections = index.data(Qt.ItemDataRole.UserRole + 2) or []
        message = index.data(Qt.ItemDataRole.UserRole + 3) or ""
        author = index.data(Qt.ItemDataRole.UserRole + 4) or ""

        if lane is None:
            self.tooltip.start_hide_sequence()
            return

        self.tooltip.set_commit_info(
            commit_sha=f"sha_{index.row()}",
            author=author,
            date="Just now",
            message=message,
            branch="main",
        )

        visual_rect = self.tree_view.visualRect(index)
        viewport = self.tree_view.viewport()

        padding_left = 10
        lane_width = 20
        max_seen_lane = lane
        for from_lane, to_lane in connections:
            max_seen_lane = max(max_seen_lane, from_lane, to_lane)

        text_start_x = padding_left + ((max_seen_lane + 1) * lane_width) + 15

        font_metrics = self.tree_view.fontMetrics()
        text_width = (
            font_metrics.horizontalAdvance(message)
            + 12
            + font_metrics.horizontalAdvance(author)
        )

        content_end_x = text_start_x + text_width

        local_side_point = visual_rect.topLeft()
        local_side_point.setX(int(content_end_x + 20))

        global_side_pos = viewport.mapToGlobal(local_side_point)

        self.tooltip.adjustSize()
        tooltip_width = self.tooltip.width()

        screen = (
            QGuiApplication.screenAt(global_side_pos) or QGuiApplication.primaryScreen()
        )
        screen_geo = screen.availableGeometry()

        target_x = global_side_pos.x()
        target_y = global_side_pos.y() - 4

        if target_x + tooltip_width > screen_geo.right():
            global_row_left = viewport.mapToGlobal(visual_rect.topLeft())
            target_x = global_row_left.x() + text_start_x - tooltip_width - 20

        self.tooltip.move(target_x, target_y)
        self.tooltip.show()
