# Written by Bahaa Nofal - 9/7/2026
# commit_history.py
"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Commit History Graph for DreamStudio: This module code sets up the graph
widget of Git Source Control. It follows branch history detailed strcuture.
Alongside the ability to view info about a certain push.
"""

from editor import *

from editor.widgets.QToolTip import ToolTip


def compute_commit_graph(commits):
    """
    Compute lane assignments and connections for a list of git commits (newest first).
    Returns a list of dictionaries with row metadata and geometric graph paths.
    """
    if not commits:
        return []

    active_lanes = []
    results = []
    overall_max_lanes = 1

    for commit in commits:
        sha = commit.hexsha

        # 1. Determine lane for current commit
        if sha in active_lanes:
            my_lane = active_lanes.index(sha)
        else:
            if None in active_lanes:
                my_lane = active_lanes.index(None)
                active_lanes[my_lane] = sha
            else:
                my_lane = len(active_lanes)
                active_lanes.append(sha)

        # Active lanes entering from top of row
        in_lanes = [i for i, l_sha in enumerate(active_lanes) if l_sha is not None]

        # 2. Compute outgoing connections (from center_y to bottom_y)
        next_lanes = list(active_lanes)
        out_connections = []

        # Pass-through connections for other active branches
        for i, l_sha in enumerate(next_lanes):
            if i != my_lane and l_sha is not None:
                out_connections.append((i, i, i))

        parents = commit.parents if commit.parents else []

        if not parents:
            next_lanes[my_lane] = None
        else:
            # Primary parent connection
            p0_sha = parents[0].hexsha
            if p0_sha in next_lanes:
                p0_lane = next_lanes.index(p0_sha)
                out_connections.append((my_lane, p0_lane, my_lane))
                next_lanes[my_lane] = None
            else:
                next_lanes[my_lane] = p0_sha
                out_connections.append((my_lane, my_lane, my_lane))

            # Secondary parents (merge sources)
            for p in parents[1:]:
                p_sha = p.hexsha
                if p_sha in next_lanes:
                    p_lane = next_lanes.index(p_sha)
                    out_connections.append((my_lane, p_lane, my_lane))
                else:
                    if None in next_lanes:
                        p_lane = next_lanes.index(None)
                        next_lanes[p_lane] = p_sha
                    else:
                        p_lane = len(next_lanes)
                        next_lanes.append(p_sha)
                    out_connections.append((my_lane, p_lane, my_lane))

        active_lanes = next_lanes
        overall_max_lanes = max(overall_max_lanes, len(active_lanes), my_lane + 1)

        msg = commit.message.strip().split("\n")[0] if commit.message else ""
        author = commit.author.name if commit.author else ""

        results.append(
            {
                "lane": my_lane,
                "in_lanes": in_lanes,
                "out_connections": out_connections,
                "message": msg,
                "author": author,
                "sha": sha,
            }
        )

    for res in results:
        res["max_lanes"] = overall_max_lanes

    return results


class GitGraphDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lane_width = 18
        self.padding_left = 12
        self.lane_colors = [
            QColor("#3b82f6"),  # Blue
            QColor("#ef4444"),  # Red
            QColor("#10b981"),  # Emerald
            QColor("#f59e0b"),  # Amber
            QColor("#8b5cf6"),  # Purple
            QColor("#ec4899"),  # Pink
            QColor("#06b6d4"),  # Cyan
        ]

    def paint(self, painter: QPainter, option, index):
        lane = index.data(Qt.ItemDataRole.UserRole + 1)
        in_lanes = index.data(Qt.ItemDataRole.UserRole + 2) or []
        out_connections = index.data(Qt.ItemDataRole.UserRole + 3) or []
        message = index.data(Qt.ItemDataRole.UserRole + 4) or ""
        author = index.data(Qt.ItemDataRole.UserRole + 5) or ""
        max_lanes = index.data(Qt.ItemDataRole.UserRole + 6) or 1

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

        # 1. Draw top half lines (inbound lanes)
        for l_idx in in_lanes:
            color = self.lane_colors[l_idx % len(self.lane_colors)]
            painter.setPen(QPen(color, 2))
            x = self.padding_left + (l_idx * self.lane_width) + (self.lane_width / 2)
            painter.drawLine(int(x), int(row_y), int(x), int(center_y))

        # 2. Draw bottom half lines (outbound connections)
        for from_lane, to_lane, color_lane in out_connections:
            color = self.lane_colors[color_lane % len(self.lane_colors)]
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
                    int(start_x), int(center_y), int(start_x), int(row_y + row_h)
                )
            else:
                painter.drawLine(
                    int(start_x), int(center_y), int(end_x), int(row_y + row_h)
                )

        # 3. Draw commit node
        node_color = self.lane_colors[lane % len(self.lane_colors)]
        node_x = self.padding_left + (lane * self.lane_width) + (self.lane_width / 2)

        painter.setPen(QPen(QColor("#ffffff"), 1.5))
        painter.setBrush(QBrush(node_color))
        painter.drawEllipse(QRectF(node_x - 4.5, center_y - 4.5, 9, 9))

        # 4. Draw commit text aligned to a fixed graph column
        text_start_x = self.padding_left + (max_lanes * self.lane_width) + 12
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
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self._current_hover_row = -1

        self.tree_view.setMouseTracking(True)
        self.tree_view.entered.connect(self.on_tree_item_hovered)
        self.tree_view.viewport().installEventFilter(self)

        self.model = QStandardItemModel()
        self.tree_view.setModel(self.model)

    def set_commits(self, processed_commits: list):
        self.model.clear()
        for c in processed_commits:
            item = QStandardItem()
            item.setData(c["lane"], Qt.ItemDataRole.UserRole + 1)
            item.setData(c["in_lanes"], Qt.ItemDataRole.UserRole + 2)
            item.setData(c["out_connections"], Qt.ItemDataRole.UserRole + 3)
            item.setData(c["message"], Qt.ItemDataRole.UserRole + 4)
            item.setData(c["author"], Qt.ItemDataRole.UserRole + 5)
            item.setData(c["max_lanes"], Qt.ItemDataRole.UserRole + 6)
            item.setData(c["sha"], Qt.ItemDataRole.UserRole + 7)
            self.model.appendRow(item)

    def eventFilter(self, source, event):
        if source == self.tree_view.viewport() and event.type() == QEvent.Type.Leave:
            self._current_hover_row = -1
            self.tooltip.start_hide_sequence()
        return super().eventFilter(source, event)

    def on_tree_item_hovered(self, index):
        if not index.isValid():
            self.tooltip.start_hide_sequence()
            return

        lane = index.data(Qt.ItemDataRole.UserRole + 1)
        message = index.data(Qt.ItemDataRole.UserRole + 4) or ""
        author = index.data(Qt.ItemDataRole.UserRole + 5) or ""
        max_lanes = index.data(Qt.ItemDataRole.UserRole + 6) or 1
        sha = index.data(Qt.ItemDataRole.UserRole + 7) or "head"

        if lane is None:
            self.tooltip.start_hide_sequence()
            return

        self._current_hover_row = index.row()

        self.tooltip.set_commit_info(
            commit_sha=sha[:7],
            author=author,
            date="Recent",
            message=message,
            branch="main",
        )

        self.tooltip.adjustSize()

        visual_rect = self.tree_view.visualRect(index)
        viewport = self.tree_view.viewport()

        padding_left = 12
        lane_width = 18
        text_x = padding_left + (max_lanes * lane_width) + 12

        local_point = visual_rect.topLeft()
        local_point.setX(int(text_x))
        local_point.setY(int(visual_rect.center().y()))

        global_pos = viewport.mapToGlobal(local_point)

        tooltip_width = self.tooltip.width()
        tooltip_height = self.tooltip.height()

        screen = QGuiApplication.screenAt(global_pos) or QGuiApplication.primaryScreen()
        screen_geo = screen.availableGeometry()

        target_x = global_pos.x()
        target_y = global_pos.y() - (tooltip_height // 2)

        if target_x + tooltip_width > screen_geo.right():
            target_x = global_pos.x() - tooltip_width - 20

        if target_y < screen_geo.top():
            target_y = screen_geo.top() + 4
        elif target_y + tooltip_height > screen_geo.bottom():
            target_y = screen_geo.bottom() - tooltip_height - 4

        self.tooltip.hide_timer.stop()
        self.tooltip.move(target_x, target_y)
        self.tooltip.show()
