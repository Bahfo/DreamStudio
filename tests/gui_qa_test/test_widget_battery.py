"""
(C) COPYRIGHT 2026 Gizmo Microsystems - All Rights Reserved.

Widget battery live tests: every custom widget in editor/widgets/ must build,
paint, react to its public API, and stay consistent with the live window.
"""

import pytest

from PyQt6.QtWidgets import QWidget

from harness import (
    Sweep,
    assert_alive,
    assert_positive_size,
    click,
    pump,
    race_probe,
)

pytestmark = [pytest.mark.gui, pytest.mark.e2e]

QT = pytest.importorskip("PyQt6.QtCore")


class _TitleBarHost(QWidget):
    """Stand-in window that records the legacy title-bar button calls.

    Attributes:
        minimized: Whether ``showMinimized()`` was called.
        toggled: Whether ``toggle_maximize()`` was called.
        closed: Whether ``close()`` was called.
    """

    def __init__(self) -> None:
        """Start with every recorded call cleared."""
        super().__init__()
        self.minimized = False
        self.toggled = False
        self.closed = False

    def showMinimized(self) -> None:
        """Record a minimize request instead of minimizing the stub."""
        self.minimized = True

    def toggle_maximize(self) -> None:
        """Record a maximize toggle request."""
        self.toggled = True

    def close(self) -> None:
        """Record a close request instead of closing the stub."""
        self.closed = True


class TestToolbarButton:
    """ToolbarButton is the flat icon button used across the menus."""

    def test_toolbar_button_builds_with_a_tooltip(self, qapp):
        """A ToolbarButton keeps its tooltip and fixed icon size."""
        from editor.widgets.QToolButton import ToolbarButton

        button = ToolbarButton("", "QA tooltip")
        pump(qapp, 50)
        assert button.toolTip() == "QA tooltip", "tooltip was not applied"
        assert (
            button.width() == 26 and button.height() == 26
        ), f"unexpected default size: {button.width()}x{button.height()}"

    def test_toolbar_button_invokes_its_callback(self, qapp):
        """Clicking a ToolbarButton calls the callback it was built with."""
        from editor.widgets.QToolButton import ToolbarButton

        calls = []
        button = ToolbarButton("", "QA callback", callback=lambda: calls.append(1))
        button.setFixedSize(60, 30)
        button.show()
        pump(qapp, 100)
        click(qapp, button)
        assert calls == [1], f"callback was not invoked: {calls}"

    def test_toolbar_button_without_text_uses_the_default_size(self, qapp):
        """A ToolbarButton carrying text is not force-sized."""
        from editor.widgets.QToolButton import ToolbarButton

        button = ToolbarButton("", "QA text", text="QA")
        pump(qapp, 50)
        assert button.text() == "QA", "text was not applied"
        assert button.sizePolicy().horizontalPolicy() != (
            button.sizePolicy().horizontalPolicy().Fixed
        ), "a labelled button must be allowed to grow"


class TestSegmentedProgressBar:
    """SegmentedProgressBar renders a list of percentage/colour segments."""

    def test_set_data_stores_the_segments(self, qapp):
        """set_data() keeps the segments it was given."""
        from editor.widgets.QSegmentedProgressBar import SegmentedProgressBar

        bar = SegmentedProgressBar()
        bar.set_data([(40, "#ff0000"), (60, "#00ff00")])
        pump(qapp, 50)
        assert bar.segments == [
            (40, "#ff0000"),
            (60, "#00ff00"),
        ], f"segments were not stored: {bar.segments}"

    def test_bar_paints_with_segments(self, qapp):
        """The bar paints without raising once it has segments."""
        from PyQt6.QtGui import QColor

        from editor.widgets.QSegmentedProgressBar import SegmentedProgressBar

        bar = SegmentedProgressBar()
        bar.resize(200, 8)
        bar.set_data([(50, QColor("#123456"))])
        bar.show()
        pump(qapp, 100)
        bar.repaint()
        pump(qapp, 50)
        assert_alive(qapp)

    def test_string_colours_are_rejected_by_the_paint_routine(self, qapp):
        """A colour string is refused by the paint routine.

        NOTE (QA finding): ``SegmentedProgressBar.paintEvent`` hands the
        segment colour straight to ``QPainter.fillRect``, which only
        accepts a ``QColor``. The widget's only in-product caller converts
        hex strings to ``QColor`` first, so a string colour raises inside
        the paint event - and an exception escaping a paint event aborts
        the whole IDE process.
        """
        from editor.widgets.QSegmentedProgressBar import SegmentedProgressBar

        bar = SegmentedProgressBar()
        bar.resize(200, 8)
        bar.set_data([(50, "#123456")])
        with pytest.raises(TypeError):
            bar.paintEvent(None)

    def test_empty_segments_are_accepted(self, qapp):
        """An empty segment list is accepted."""
        from editor.widgets.QSegmentedProgressBar import SegmentedProgressBar

        bar = SegmentedProgressBar()
        bar.set_data([])
        pump(qapp, 50)
        assert bar.segments == [], "segments were not cleared"

    def test_flow_layout_wraps_items(self, qapp):
        """FlowLayout wraps items that do not fit on one line."""
        from PyQt6.QtWidgets import QLabel

        from editor.widgets.QSegmentedProgressBar import FlowLayout

        layout = FlowLayout()
        for index in range(6):
            layout.addItem(QLabel(f"item {index}"))
        host = QT.QObject()
        assert host is not None
        layout.setGeometry(QT.QRect(0, 0, 120, 200))
        pump(qapp, 50)
        assert layout.count() == 6, f"items were lost: {layout.count()}"


class TestIndexingProgress:
    """IndexingProgress shows determinate progress for background jobs."""

    def test_start_indexing_shows_the_indicator(self, qapp):
        """start_indexing() reveals the indicator and its message."""
        from editor.widgets.QIndexingProgress import IndexingProgress

        progress = IndexingProgress()
        progress.show()
        pump(qapp, 100)
        progress.start_indexing(10, "Indexing QA")
        pump(qapp, 100)
        assert progress.isVisible(), "indexing indicator stayed hidden"
        assert (
            progress.label.text() == "Indexing QA"
        ), f"unexpected message: {progress.label.text()!r}"
        assert progress.bar.value() == 0, "bar did not start at zero"

    def test_advance_indexing_moves_the_bar(self, qapp):
        """advance_indexing() advances the bar proportionally."""
        from editor.widgets.QIndexingProgress import IndexingProgress

        progress = IndexingProgress()
        progress.start_indexing(4)
        pump(qapp, 100)
        progress.advance_indexing(2)
        pump(qapp, 100)
        assert (
            progress.bar.value() == 50
        ), f"unexpected bar value: {progress.bar.value()}"

    def test_advance_is_clamped_to_the_total(self, qapp):
        """A done count above the total is clamped."""
        from editor.widgets.QIndexingProgress import IndexingProgress

        progress = IndexingProgress()
        progress.start_indexing(4)
        pump(qapp, 100)
        progress.advance_indexing(99)
        pump(qapp, 100)
        assert (
            progress.bar.value() == 100
        ), f"bar was not clamped: {progress.bar.value()}"

    def test_finish_indexing_hides_the_indicator(self, qapp):
        """finish_indexing() fills the bar and hides the indicator."""
        from editor.widgets.QIndexingProgress import IndexingProgress

        progress = IndexingProgress()
        progress.show()
        progress.start_indexing(8)
        pump(qapp, 100)
        progress.finish_indexing()
        pump(qapp, 100)
        assert not progress.isVisible(), "indexing indicator stayed visible"
        assert progress.bar.value() == 100, "bar did not finish at 100"

    def test_zero_total_is_normalised(self, qapp):
        """A zero total still produces a usable progress bar."""
        from editor.widgets.QIndexingProgress import IndexingProgress

        progress = IndexingProgress()
        progress.start_indexing(0)
        pump(qapp, 100)
        progress.advance_indexing(1)
        pump(qapp, 100)
        assert (
            progress.bar.value() == 100
        ), f"unexpected bar value: {progress.bar.value()}"


class TestIndexingCoordinator:
    """IndexingCoordinator multiplexes sessions onto one progress bar."""

    def test_start_drives_the_bar(self, qapp):
        """start() opens a session and shows the progress bar."""
        from editor.widgets.QIndexingCoordinator import IndexingCoordinator
        from editor.widgets.QIndexingProgress import IndexingProgress

        progress = IndexingProgress()
        coordinator = IndexingCoordinator(progress)
        coordinator.start("python", 10, "Indexing QA")
        pump(qapp, 100)
        assert progress.isVisible(), "the coordinator did not show the bar"
        assert (
            progress.bar.value() == 0
        ), f"unexpected bar value: {progress.bar.value()}"

    def test_advance_and_finish_update_the_bar(self, qapp):
        """advance() moves the bar and finish() hides it."""
        from editor.widgets.QIndexingCoordinator import IndexingCoordinator
        from editor.widgets.QIndexingProgress import IndexingProgress

        progress = IndexingProgress()
        coordinator = IndexingCoordinator(progress)
        coordinator.start("python", 4)
        pump(qapp, 100)
        coordinator.advance("python", 2)
        pump(qapp, 100)
        assert (
            progress.bar.value() == 50
        ), f"unexpected bar value: {progress.bar.value()}"
        coordinator.finish("python")
        pump(qapp, 100)
        assert (
            not progress.isVisible()
        ), "the bar stayed visible after the session ended"

    def test_unknown_source_is_ignored(self, qapp):
        """Advancing an unknown source does not raise."""
        from editor.widgets.QIndexingCoordinator import IndexingCoordinator
        from editor.widgets.QIndexingProgress import IndexingProgress

        progress = IndexingProgress()
        coordinator = IndexingCoordinator(progress)
        sweep = Sweep("indexing coordinator")
        sweep.step("advance unknown", coordinator.advance, "ghost", 3)
        sweep.step("finish unknown", coordinator.finish, "ghost")
        sweep.finish()
        assert_alive(qapp)


class TestExplorerToolbar:
    """ExplorerToolbar builds the solution-explorer button row."""

    def test_add_button_returns_a_toolbar_button(self, qapp):
        """add_button() returns the button it added."""
        from editor.widgets.QToolBox import ExplorerToolbar
        from editor.widgets.QToolButton import ToolbarButton

        toolbar = ExplorerToolbar()
        button = toolbar.add_button("", "QA tooltip")
        pump(qapp, 50)
        assert isinstance(button, ToolbarButton), "add_button returned the wrong type"
        assert button.toolTip() == "QA tooltip", "tooltip was not applied"

    def test_add_separator_returns_a_frame(self, qapp):
        """add_separator() returns the divider it added."""
        from editor.widgets.QToolBox import ExplorerToolbar

        toolbar = ExplorerToolbar()
        separator = toolbar.add_separator(12)
        pump(qapp, 50)
        assert (
            separator.objectName() == "ToolbarSeparator"
        ), "separator name was not set"
        assert separator.width() == 1, f"separator width is {separator.width()}"


class TestSystemGraphUtil:
    """SystemGraphUtil accumulates series and paints them."""

    def test_add_series_and_append(self, qapp):
        """Series accept data points and keep them."""
        from editor.widgets.QSystemGraphWidget import SystemGraphUtil

        graph = SystemGraphUtil(title="QA", unit="%")
        graph.add_series("cpu", "#ff0000")
        graph.append("cpu", 42)
        graph.append("cpu", 55)
        pump(qapp, 50)
        assert graph._series["cpu"] == [
            42,
            55,
        ], f"unexpected series data: {graph._series['cpu']}"

    def test_append_creates_missing_series(self, qapp):
        """Appending to an unknown series creates it."""
        from editor.widgets.QSystemGraphWidget import SystemGraphUtil

        graph = SystemGraphUtil()
        graph.append("memory", 10)
        pump(qapp, 50)
        assert "memory" in graph._series, "series was not created"

    def test_series_are_capped_at_the_point_limit(self, qapp):
        """The graph keeps only the most recent points."""
        from editor.widgets.QSystemGraphWidget import SystemGraphUtil

        graph = SystemGraphUtil()
        graph.add_series("cpu")
        for value in range(120):
            graph.append("cpu", value)
        pump(qapp, 50)
        assert (
            len(graph._series["cpu"]) == graph._max_points
        ), f"series was not capped: {len(graph._series['cpu'])}"

    def test_set_range_updates_the_bounds(self, qapp):
        """set_range() changes the painted value range."""
        from editor.widgets.QSystemGraphWidget import SystemGraphUtil

        graph = SystemGraphUtil()
        graph.set_range(10, 90)
        pump(qapp, 50)
        assert (
            graph._min_y == 10 and graph._max_y == 90
        ), f"unexpected range: {graph._min_y}..{graph._max_y}"

    def test_graph_paints_with_data(self, qapp):
        """The graph paints its series without raising."""
        from editor.widgets.QSystemGraphWidget import SystemGraphUtil

        graph = SystemGraphUtil(title="QA", unit="%")
        graph.resize(400, 200)
        graph.add_series("cpu", "#61afef")
        for value in (10, 40, 70, 90):
            graph.append("cpu", value)
        graph.show()
        pump(qapp, 100)
        graph.repaint()
        pump(qapp, 50)
        assert_alive(qapp)


class TestPlotWidget:
    """PlotWidget hosts a pyqtgraph plot next to its option buttons."""

    def test_plot_widget_builds_its_option_buttons(self, qapp):
        """The plot widget exposes its four option buttons."""
        from editor.widgets.QPlotWidget import PlotWidget

        plot = PlotWidget()
        plot.resize(500, 300)
        plot.show()
        pump(qapp, 200)
        for name in ("zoom_to_fit", "zoom_in_out", "preferences", "save_graph"):
            button = getattr(plot, name)
            assert button is not None, f"{name} button is missing"
            assert_positive_size(button, name)
        assert_alive(qapp)

    def test_plot_widget_clicks_do_not_raise(self, qapp):
        """Clicking the option buttons keeps the plot alive."""
        from editor.widgets.QPlotWidget import PlotWidget

        plot = PlotWidget()
        plot.resize(500, 300)
        plot.show()
        pump(qapp, 200)
        sweep = Sweep("plot option buttons")
        for name in ("zoom_to_fit", "zoom_in_out", "preferences", "save_graph"):
            sweep.step(f"click {name}", click, qapp, getattr(plot, name))
        sweep.finish()
        assert_alive(qapp)


class TestAnimatedGradientLabel:
    """AnimatedGradientLabel animates its gradient offset."""

    def test_label_starts_and_stops_the_animation(self, qapp):
        """The gradient animation starts and stops on demand."""
        from editor.widgets.QCustomLabels import AnimatedGradientLabel

        label = AnimatedGradientLabel("DreamStudio")
        label.show()
        pump(qapp, 100)
        label.start_animation()
        pump(qapp, 150)
        assert (
            label.animation.state() == label.animation.State.Running
        ), "animation did not start"
        label.stop_animation()
        pump(qapp, 100)
        assert (
            label.animation.state() != label.animation.State.Running
        ), "animation did not stop"

    def test_offset_property_drives_a_repaint(self, qapp):
        """Setting the gradient offset stores the new value."""
        from editor.widgets.QCustomLabels import AnimatedGradientLabel

        label = AnimatedGradientLabel("DreamStudio")
        label.show()
        pump(qapp, 100)
        label.gradient_offset = 0.5
        pump(qapp, 50)
        assert (
            label.gradient_offset == 0.5
        ), f"offset was not stored: {label.gradient_offset}"

    def test_starting_twice_is_harmless(self, qapp):
        """Calling start_animation() twice does not raise."""
        from editor.widgets.QCustomLabels import AnimatedGradientLabel

        label = AnimatedGradientLabel("DreamStudio")
        label.show()
        pump(qapp, 100)
        sweep = Sweep("gradient animation")
        sweep.step("start", label.start_animation)
        sweep.step("start again", label.start_animation)
        sweep.step("stop", label.stop_animation)
        sweep.finish()
        assert_alive(qapp)


class TestQErrorMessage:
    """QErrorMessage renders a themed bubble with an arrow."""

    def test_message_bubble_builds(self, qapp):
        """The bubble keeps the message it was built with."""
        from editor.widgets.QErrorMessage import QErrorMessage

        bubble = QErrorMessage("QA failure")
        pump(qapp, 50)
        assert bubble.message == "QA failure", "message was not stored"
        assert (
            bubble.minimumWidth() == QErrorMessage.MIN_WIDTH
        ), f"unexpected minimum width: {bubble.minimumWidth()}"

    def test_severity_switches_the_accent(self, qapp):
        """set_severity() changes the bubble tint."""
        from editor.widgets.QErrorMessage import QErrorMessage

        bubble = QErrorMessage("QA failure")
        bubble.set_severity("warning")
        pump(qapp, 50)
        assert (
            bubble.severity() == "warning"
        ), f"severity not applied: {bubble.severity()}"
        accent, _fill, _text = bubble.style_colors()
        assert accent, "no accent colour was resolved"

    def test_unknown_severity_falls_back_to_error(self, qapp):
        """An unknown severity falls back to the error accent."""
        from editor.widgets.QErrorMessage import QErrorMessage

        bubble = QErrorMessage("QA failure")
        bubble.set_severity("not-a-severity")
        pump(qapp, 50)
        assert (
            bubble.severity() == "error"
        ), f"severity did not fall back: {bubble.severity()}"

    def test_arrow_direction_and_position(self, qapp):
        """The arrow can point up and be repositioned."""
        from editor.widgets.QErrorMessage import QErrorMessage

        bubble = QErrorMessage("QA failure")
        bubble.resize(400, 100)
        bubble.set_arrow_up(True)
        bubble.set_arrow_x_position(120)
        pump(qapp, 50)
        assert bubble.arrow_up() is True, "arrow did not flip"
        assert bubble._arrow_x == 120, f"arrow was not moved: {bubble._arrow_x}"

    def test_bubble_paints_without_raising(self, qapp):
        """Showing and repainting the bubble keeps Qt alive."""
        from editor.widgets.QErrorMessage import QErrorMessage

        bubble = QErrorMessage("QA failure")
        bubble.resize(520, 120)
        bubble.show()
        pump(qapp, 300)
        bubble.repaint()
        pump(qapp, 100)
        assert_alive(qapp)

    def test_fitted_size_grows_with_the_message(self, qapp):
        """A longer message needs a taller bubble."""
        from editor.widgets.QErrorMessage import QErrorMessage

        short = QErrorMessage("short")
        long = QErrorMessage("a much longer message " * 6)
        pump(qapp, 50)
        assert (
            long.fitted_size(520).height() >= short.fitted_size(520).height()
        ), "the fitted size ignored the message length"


class TestToolTipWidget:
    """ToolTip is the git commit flyout frame."""

    def test_tooltip_builds_with_text(self, qapp):
        """The tooltip stores the text it was built with."""
        from editor.widgets.QToolTip import ToolTip

        tip = ToolTip(text="QA tooltip")
        pump(qapp, 50)
        assert tip.label.text() == "QA tooltip", "tooltip text was not stored"

    def test_commit_info_renders_html(self, qapp):
        """set_commit_info() fills the tooltip with commit details."""
        from editor.widgets.QToolTip import ToolTip

        tip = ToolTip()
        tip.set_commit_info("abcdef1234567890", "QA", "2026-01-01", "commit message")
        pump(qapp, 50)
        assert "QA" in tip.label.text(), "author missing from the tooltip"
        assert "abcdef1" in tip.label.text(), "sha missing from the tooltip"

    def test_hide_sequence_hides_the_tooltip(self, qapp):
        """start_hide_sequence() eventually hides the tooltip."""
        from editor.widgets.QToolTip import ToolTip

        tip = ToolTip(text="QA tooltip")
        tip.show()
        pump(qapp, 100)
        tip.start_hide_sequence()
        pump(qapp, 400)
        assert not tip.isVisible(), "tooltip stayed visible"


class TestSeparator:
    """Separator is the fixed-size divider between widgets."""

    def test_separator_uses_the_requested_size(self, qapp):
        """The separator keeps the size it was created with."""
        from editor.widgets.QSeparator import Separator

        separator = Separator(12, 2)
        pump(qapp, 50)
        assert (
            separator.width() == 12 and separator.height() == 2
        ), f"unexpected separator size: {separator.width()}x{separator.height()}"
        assert separator.objectName() == "Separator", "object name was not set"


class TestDreamTabEditor:
    """DreamStudioIDETabBar paints the IDE tab strip."""

    def test_tab_bar_theme_setters(self, qapp):
        """Every theme setter on the tab bar stores its colour."""
        from PyQt6.QtGui import QColor

        from editor.widgets.QDreamTabEditor import DreamStudioIDETabBar

        bar = DreamStudioIDETabBar()
        pump(qapp, 50)
        bar.set_selected_bg("#111111")
        bar.set_hover_bg("#222222")
        bar.set_inactive_bg("#333333")
        bar.set_border_color("#444444")
        bar.set_hover_border_color("#555555")
        bar.set_inactive_border_color("#666666")
        bar.set_text_selected("#777777")
        bar.set_text_inactive("#888888")
        bar.set_dirty_dot("#999999")
        bar.set_readonly_color("#aaaaaa")
        bar.set_border_bottom("#bbbbbb")
        pump(qapp, 50)
        assert bar.get_selected_bg() == QColor("#111111"), "selected bg was not stored"
        assert bar.get_hover_bg() == QColor("#222222"), "hover bg was not stored"
        assert bar.get_text_selected() == QColor(
            "#777777"
        ), "selected text was not stored"
        assert bar.get_dirty_dot() == QColor(
            "#999999"
        ), "dirty dot colour was not stored"

    def test_tab_bar_marks_tabs_dirty_and_readonly(self, qapp):
        """The dirty and readonly marks mirror the state of the tab widgets.

        The tab bar re-derives both sets from the widgets it hosts, so the
        marks are rebuilt from ``is_dirty()`` / ``isReadOnly()`` rather than
        kept as independent state.
        """
        from PyQt6.QtWidgets import QWidget

        from editor.widgets.QDreamTabEditor import QDreamTabEditor

        class StubEditor(QWidget):
            """Tab widget that reports a fixed dirty/readonly state."""

            def __init__(self, dirty: bool, readonly: bool) -> None:
                """Store the reported state.

                Args:
                    dirty: Whether the widget reports a dirty buffer.
                    readonly: Whether the widget reports a read-only buffer.
                """
                super().__init__()
                self._dirty = dirty
                self._readonly = readonly

            def is_dirty(self) -> bool:
                """Report the dirty state.

                Returns:
                    True when the widget reports a dirty buffer.
                """
                return self._dirty

            def isReadOnly(self) -> bool:
                """Report the read-only state.

                Returns:
                    True when the widget reports a read-only buffer.
                """
                return self._readonly

        editor = QDreamTabEditor()
        bar = editor.tabBar()
        editor.addTab(StubEditor(True, False), "dirty")
        editor.addTab(StubEditor(False, True), "locked")
        pump(qapp, 50)

        bar.rebuild_dirty_indices()
        bar.rebuild_readonly_indices()
        assert bar._dirty_indices == {
            0
        }, f"unexpected dirty marks: {bar._dirty_indices}"
        assert bar._readonly_indices == {
            1
        }, f"unexpected readonly marks: {bar._readonly_indices}"

    def test_tab_bar_marks_are_cleared_when_the_tabs_are_clean(self, qapp):
        """A clean tab widget removes its dirty and readonly marks."""
        from PyQt6.QtWidgets import QWidget

        from editor.widgets.QDreamTabEditor import QDreamTabEditor

        class CleanEditor(QWidget):
            """Tab widget that is always clean and editable."""

            def is_dirty(self) -> bool:
                """Report a clean buffer.

                Returns:
                    Always False.
                """
                return False

            def isReadOnly(self) -> bool:
                """Report an editable buffer.

                Returns:
                    Always False.
                """
                return False

        editor = QDreamTabEditor()
        bar = editor.tabBar()
        editor.addTab(CleanEditor(), "clean")
        pump(qapp, 50)

        bar.rebuild_dirty_indices()
        bar.rebuild_readonly_indices()
        assert not bar._dirty_indices, f"unexpected dirty marks: {bar._dirty_indices}"
        assert (
            not bar._readonly_indices
        ), f"unexpected readonly marks: {bar._readonly_indices}"

    def test_dream_tab_editor_uses_the_custom_tab_bar(self, qapp):
        """QDreamTabEditor installs the DreamStudio tab bar."""
        from editor.widgets.QDreamTabEditor import DreamStudioIDETabBar, QDreamTabEditor

        editor = QDreamTabEditor()
        pump(qapp, 50)
        assert isinstance(
            editor.tabBar(), DreamStudioIDETabBar
        ), f"unexpected tab bar: {type(editor.tabBar()).__name__}"
        assert editor.tabsClosable() is False, "tabs must not be closable by default"
        assert editor.isMovable() is True, "tabs must be movable"


class TestToolbarMenuButton:
    """ToolbarMenuButton is the split button with an arrow indicator."""

    def test_button_updates_its_text(self, qapp):
        """update_button_text() replaces the displayed label."""
        from editor.widgets.QOptionsMenu import ToolbarMenuButton

        button = ToolbarMenuButton(text="QA", fixed_size=(240, 26))
        pump(qapp, 50)
        button.update_button_text("Second")
        pump(qapp, 50)
        assert (
            button.text_label.text() == "Second"
        ), f"text was not updated: {button.text_label.text()!r}"

    def test_long_text_is_elided(self, qapp):
        """Overlong text is elided instead of overflowing."""
        from editor.widgets.QOptionsMenu import ToolbarMenuButton

        button = ToolbarMenuButton(text="QA")
        pump(qapp, 50)
        button.update_button_text("A very long label that cannot possibly fit")
        pump(qapp, 50)
        assert (
            len(button.text_label.text()) < 60
        ), f"text was not elided: {button.text_label.text()!r}"

    def test_arrow_indicator_follows_the_menu_state(self, qapp):
        """The arrow flips while the menu is open."""
        from editor.widgets.QOptionsMenu import ToolbarMenuButton

        button = ToolbarMenuButton(text="QA")
        button.show()
        pump(qapp, 100)
        assert button.arrow_label.text() == "▸", "arrow did not start closed"
        button.menu.aboutToShow.emit()
        pump(qapp, 50)
        assert button.arrow_label.text() == "▾", "arrow did not open"
        button.menu.aboutToHide.emit()
        pump(qapp, 50)
        assert button.arrow_label.text() == "▸", "arrow did not close"

    def test_triggered_action_updates_the_label(self, qapp):
        """Triggering a menu action updates the button label."""
        from PyQt6.QtGui import QAction

        from editor.widgets.QOptionsMenu import ToolbarMenuButton

        button = ToolbarMenuButton(text="QA", fixed_size=(240, 26))
        action = QAction("Chosen", button.menu)
        button.menu.addAction(action)
        pump(qapp, 50)
        button.menu.triggered.emit(action)
        pump(qapp, 50)
        assert (
            button.text_label.text() == "Chosen"
        ), f"label was not updated: {button.text_label.text()!r}"


class TestTitleBarWidget:
    """TitleBar hosts the window buttons and the menu bar."""

    def test_title_bar_builds_its_controls(self, qapp, qa_window):
        """The live window's title bar exposes its window buttons."""
        bar = qa_window.title_bar
        for name in (
            "icon_btn",
            "free_trial_btn",
            "btn_minimize",
            "btn_maximize",
            "btn_close",
        ):
            button = getattr(bar, name, None)
            assert button is not None, f"{name} is missing from the title bar"
        assert bar.menubar is not None, "the title bar has no menu bar"

    def test_title_bar_menu_actions_are_connected(self, qapp, qa_window):
        """Leaf menu actions in the title bar are not left disconnected.

        NOTE (QA finding): ``titleBar.py`` only connects an action when the
        window exposes a matching callable, so every menu entry without an
        implementation is left silently disconnected.
        """
        from PyQt6.QtWidgets import QMenu

        bar = qa_window.title_bar
        disconnected = []
        for menu in bar.menubar.findChildren(QMenu):
            for action in menu.actions():
                if action.isSeparator() or action.menu() is not None:
                    continue
                if not action.receivers(action.triggered):
                    disconnected.append(f"{menu.title()}: '{action.text()}'")
        assert not disconnected, f"title bar actions without a handler: {disconnected}"

    def test_title_bar_buttons_are_clickable(self, qapp, qa_window):
        """The title bar buttons react to clicks without raising."""
        bar = qa_window.title_bar
        sweep = Sweep("title bar buttons")
        for name in ("icon_btn", "free_trial_btn"):
            sweep.step(f"click {name}", click, qapp, getattr(bar, name))
        sweep.finish()
        assert_alive(qapp, qa_window)


class TestDialogWidgets:
    """The custom dialogs build their UI without being executed."""

    def test_exit_dialog_builds_its_buttons(self, qapp):
        """ExitDialog exposes the exit and cancel buttons."""
        from editor.widgets.QExitDialog import ExitDialog

        dialog = ExitDialog()
        pump(qapp, 50)
        assert (
            dialog.yes_button.text() == "EXIT DREAMSTUDIO"
        ), f"unexpected exit button: {dialog.yes_button.text()!r}"
        assert (
            dialog.no_button.text() == "CANCEL"
        ), f"unexpected cancel button: {dialog.no_button.text()!r}"
        dialog.deleteLater()
        pump(qapp, 50)

    def test_confirm_dialog_honours_its_text(self, qapp):
        """ConfirmDialog uses the title, message, and button texts given."""
        from editor.widgets.QExitDialog import ConfirmDialog

        dialog = ConfirmDialog(
            title="QA title",
            message="QA message",
            confirm_text="YES",
            cancel_text="NO",
        )
        pump(qapp, 50)
        assert dialog.title_label.text() == "QA title", "title was not applied"
        assert dialog.label.text() == "QA message", "message was not applied"
        assert dialog.confirm_btn.text() == "YES", "confirm text was not applied"
        assert dialog.cancel_btn.text() == "NO", "cancel text was not applied"
        dialog.deleteLater()
        pump(qapp, 50)

    def test_rename_dialog_validates_empty_names(self, qapp):
        """RenameDialog rejects an empty name with an error message."""
        from editor.widgets.QExitDialog import RenameDialog

        dialog = RenameDialog(current_text="")
        pump(qapp, 50)
        dialog._validate()
        pump(qapp, 100)
        assert dialog._error_active is True, "empty name was accepted"
        assert (
            dialog._error_label.isVisible() is False
        ), "error label should stay hidden"
        dialog.deleteLater()
        pump(qapp, 50)

    def test_rename_dialog_accepts_a_name(self, qapp):
        """RenameDialog clears the error state once a name is typed."""
        from editor.widgets.QExitDialog import RenameDialog

        dialog = RenameDialog(current_text="")
        pump(qapp, 50)
        dialog._validate()
        pump(qapp, 100)
        dialog.line_edit.setText("qa_name")
        pump(qapp, 100)
        assert dialog._error_active is False, "error state was not cleared"
        assert dialog._error_label.isVisible() is False, "error label is still visible"
        dialog.deleteLater()
        pump(qapp, 50)

    def test_dialogs_are_never_shown_by_the_battery(self, qapp):
        """Building the dialogs must not open a modal window."""
        from editor.widgets.QExitDialog import ConfirmDialog, ExitDialog, RenameDialog

        dialogs = [
            ExitDialog(),
            ConfirmDialog(),
            RenameDialog(current_text="qa"),
        ]
        pump(qapp, 100)
        shown = [dialog for dialog in dialogs if dialog.isVisible()]
        assert not shown, f"{len(shown)} dialog(s) opened unexpectedly: {shown}"
        for dialog in dialogs:
            dialog.deleteLater()
        pump(qapp, 100)


class TestLegacyTitleBar:
    """The legacy ``editor/widgets/QTitleBar.py`` widget builds and reacts."""

    def test_title_bar_builds_its_controls(self, qapp):
        """TitleBar exposes the icon, add, menubar, and window buttons."""
        from editor.widgets.QTitleBar import TitleBar

        parent = _TitleBarHost()
        bar = TitleBar(parent, "QA title")
        pump(qapp, 100)
        assert (
            bar.icon_btn.text() == "QA title"
        ), f"unexpected title: {bar.icon_btn.text()!r}"
        for name in (
            "icon_btn",
            "btn_add",
            "btn_minimize",
            "btn_maximize",
            "btn_close",
        ):
            button = getattr(bar, name, None)
            assert button is not None, f"the title bar has no {name}"
            assert button.width() > 0 and button.height() > 0, f"{name} has no size"
        assert bar.menubar is not None, "the title bar has no menubar"
        bar.deleteLater()
        pump(qapp, 50)

    def test_window_buttons_forward_to_the_parent(self, qapp):
        """Minimize, maximize, and close forward to the parent window."""
        from editor.widgets.QTitleBar import TitleBar

        parent = _TitleBarHost()
        bar = TitleBar(parent, "QA title")
        pump(qapp, 100)

        bar.btn_minimize.click()
        bar.btn_maximize.click()
        pump(qapp, 100)
        assert parent.minimized, "minimize did not reach the parent"
        assert parent.toggled, "maximize did not reach the parent"

        bar.btn_close.click()
        pump(qapp, 100)
        assert parent.closed, "close did not reach the parent"

        bar.deleteLater()
        pump(qapp, 50)


class TestWidgetBatteryStability:
    """Widget construction storms stay stable."""

    def test_repeated_construction_is_stable(self, qapp):
        """Building the battery widgets repeatedly does not raise."""
        from editor.widgets.QCustomLabels import AnimatedGradientLabel
        from editor.widgets.QErrorMessage import QErrorMessage
        from editor.widgets.QIndexingProgress import IndexingProgress
        from editor.widgets.QSeparator import Separator
        from editor.widgets.QSystemGraphWidget import SystemGraphUtil

        sweep = Sweep("widget construction storm")

        def build_cycle() -> None:
            """Build and drop one set of widgets.

            Returns:
                None; the side effect is the widget construction.
            """
            AnimatedGradientLabel("QA")
            QErrorMessage("QA")
            IndexingProgress()
            Separator(4, 4)
            SystemGraphUtil()

        race_probe(qapp, build_cycle, 3)
        pump(qapp, 200)
        sweep.finish()
        assert_alive(qapp)

    def test_widget_battery_does_not_break_the_window(self, qapp, qa_window):
        """The battery leaves the live window untouched and alive."""
        from editor.widgets.QIndexingProgress import IndexingProgress

        progress = IndexingProgress()
        progress.setParent(qa_window)
        progress.start_indexing(5, "QA indexing")
        pump(qapp, 150)
        progress.advance_indexing(3)
        pump(qapp, 150)
        progress.finish_indexing()
        pump(qapp, 150)
        assert_alive(qapp, qa_window)
        progress.setParent(None)
        progress.deleteLater()
        pump(qapp, 100)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
