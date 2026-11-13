"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Shared live-window harness for the gui_qa suite: event-driving primitives,
geometry probes, sweep recording, race helpers, and native-dialog guards.

All primitives run against the real QApplication in offscreen mode and rely
only on PyQt6.QtTest.QTest, so no operating-system pointer is moved.
"""

from __future__ import annotations

import contextlib
import unittest.mock
from typing import Any, Callable, Iterable, Sequence

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QToolButton,
    QWidget,
)

CLICKABLE_TYPES: tuple[type, ...] = (QToolButton, QPushButton, QCheckBox)
TEXT_TYPES: tuple[type, ...] = (QLineEdit, QTextEdit)

DEFAULT_WINDOW_SIZE = (1280, 800)
PUMP_SLICE_MS = 10


# -----------------------------------------------------------------------------
# Event pumping
# -----------------------------------------------------------------------------


def pump(qapp: QApplication, ms: int = 50) -> None:
    """Process Qt events for *ms* wall-clock milliseconds.

    Args:
        qapp: The live QApplication instance.
        ms: Approximate duration to keep processing events.
    """
    QTest.qWait(max(0, ms))


def pump_until(
    qapp: QApplication,
    predicate: Callable[[], bool],
    timeout_ms: int = 5000,
    slice_ms: int = PUMP_SLICE_MS,
) -> bool:
    """Process events until *predicate* turns true or the timeout expires.

    Args:
        qapp: The live QApplication instance.
        predicate: Zero-argument callable polled between event slices.
        timeout_ms: Maximum wall-clock time to wait.
        slice_ms: Event-processing slice length per iteration.

    Returns:
        True when *predicate* was satisfied, False on timeout.
    """
    return bool(pump_until_value(qapp, predicate, timeout_ms, slice_ms)[0])


def pump_until_value(
    qapp: QApplication,
    predicate: Callable[[], Any],
    timeout_ms: int = 5000,
    slice_ms: int = PUMP_SLICE_MS,
) -> tuple[bool, Any]:
    """Like :func:`pump_until` but also returns the last predicate value.

    Args:
        qapp: The live QApplication instance.
        predicate: Zero-argument callable polled between event slices.
        timeout_ms: Maximum wall-clock time to wait.
        slice_ms: Event-processing slice length per iteration.

    Returns:
        Tuple of (satisfied, last_value).
    """
    QTest.qWait(min(slice_ms, max(1, timeout_ms)))
    value = predicate()
    if value:
        return True, value
    remaining = timeout_ms
    while remaining > 0:
        QTest.qWait(min(slice_ms, remaining))
        remaining -= slice_ms
        value = predicate()
        if value:
            return True, value
    return False, value


# -----------------------------------------------------------------------------
# Finding widgets
# -----------------------------------------------------------------------------


def find_button(parent: QWidget, tooltip: str) -> QWidget | None:
    """Find the first descendant button whose toolTip matches exactly.

    Args:
        parent: Widget to search under.
        tooltip: Exact tooltip text to match.

    Returns:
        The matching button widget, or None when absent.
    """
    for child in parent.findChildren(QWidget):
        if child.toolTip() == tooltip and isinstance(
            child, CLICKABLE_TYPES + (QWidget,)
        ):
            return child
    return None


def find_buttons_by_tooltip(parent: QWidget, tooltips: Iterable[str]) -> dict[str, QWidget | None]:
    """Map each requested tooltip to its button widget (or None).

    Args:
        parent: Widget to search under.
        tooltips: Tooltip strings to look up.

    Returns:
        Dict mapping tooltip -> widget or None.
    """
    return {tip: find_button(parent, tip) for tip in tooltips}


def find_by_object_name(parent: QWidget, name: str) -> QWidget | None:
    """Find the first descendant widget whose objectName matches.

    Args:
        parent: Widget to search under.
        name: objectName to match.

    Returns:
        The matching widget, or None when absent.
    """
    for child in parent.findChildren(QWidget):
        if child.objectName() == name:
            return child
    return None


def code_editor(widget: Any, _depth: int = 0) -> Any:
    """Unwrap editor wrappers down to the real ``CodeEditor`` widget.

    ``EditorContainer.current_editor()`` returns an ``EditorAPI`` facade that
    wraps the ``MiniMapHostWidget`` instead of the ``CodeEditor`` it hosts.
    Key events sent to that wrapper never reach the text buffer, so every
    typing test must target the unwrapped editor.

    Args:
        widget: An ``EditorAPI``, ``MiniMapHostWidget``, or ``CodeEditor``.
        _depth: Internal recursion guard.

    Returns:
        The innermost ``CodeEditor`` widget, or the input when it cannot be
        unwrapped further.
    """
    if widget is None or _depth > 3:
        return widget
    inner = getattr(widget, "editor", None)
    if inner is not None and inner is not widget and isinstance(inner, QWidget):
        return code_editor(inner, _depth + 1)
    return widget


def cursor_position(editor: Any) -> tuple[int, int]:
    """Return the ``(line, column)`` cursor position of a Scintilla editor.

    The PyQt6 Scintilla binding only exposes ``getCursorPosition()``.

    Args:
        editor: The editor widget to query.

    Returns:
        Tuple of (line, column).
    """
    line, column = editor.getCursorPosition()
    return int(line), int(column)


def center(widget: QWidget) -> QPoint:
    """Return the center point of *widget*'s rect.

    Args:
        widget: Widget to measure.

    Returns:
        QPoint at the widget center.
    """
    rect = widget.rect()
    return QPoint(rect.width() // 2, rect.height() // 2)


# -----------------------------------------------------------------------------
# Event driving
# -----------------------------------------------------------------------------


def close_popups_soon(qapp: QApplication, delay_ms: int = 0, exclude: QWidget | None = None) -> None:
    """Schedule an immediate close of any popup that opens during a click.

    ``QMenu.exec()`` runs a nested event loop, so a click on a menu button
    blocks the test. Scheduling a closer lets that nested loop dismiss the
    menu and return control to the test. The popup is only closed, never
    deleted, and a popup that owns *exclude* is left alone.

    Args:
        qapp: The live QApplication instance.
        delay_ms: Delay before the closer runs.
        exclude: Widget whose popup window must stay open.
    """
    from PyQt6.QtCore import QTimer

    def closer() -> None:
        """Close and release the currently active popup widget.

        Returns:
            None.
        """
        popup = QApplication.activePopupWidget()
        if popup is None:
            return
        if exclude is not None and (
            popup is exclude or popup.isAncestorOf(exclude)
        ):
            return
        popup.close()

    QTimer.singleShot(delay_ms, closer)


def click(
    qapp: QApplication,
    widget: QWidget,
    button: Qt.MouseButton = Qt.MouseButton.LeftButton,
    pos: QPoint | None = None,
) -> None:
    """Send a real mouse click to *widget* and pump the event loop.

    A popup opened by the click is dismissed automatically so nested menu
    event loops cannot block the test.

    Args:
        qapp: The live QApplication instance.
        widget: Target widget (uses its viewport for scintilla editors).
        button: Mouse button to press.
        pos: Optional in-widget position; defaults to the center.

    Raises:
        AssertionError: If *widget* is gone or invisible.
    """
    if widget is None or not widget.isVisible():
        raise AssertionError(f"Cannot click invisible or missing widget: {widget!r}")
    target = getattr(widget, "viewport", lambda: widget)()
    close_popups_soon(qapp, exclude=target)
    QTest.mouseClick(target, button, pos=pos or center(widget))
    pump(qapp)


def guarded_click(
    qapp: QApplication,
    widget: QWidget,
    button: Qt.MouseButton = Qt.MouseButton.LeftButton,
    pos: QPoint | None = None,
) -> None:
    """Click *widget* with every native dialog stubbed to cancel.

    Args:
        qapp: The live QApplication instance.
        widget: Target widget.
        button: Mouse button to press.
        pos: Optional in-widget position; defaults to the center.
    """
    with modal_guard(cancel=True):
        click(qapp, widget, button, pos)


def double_click(qapp: QApplication, widget: QWidget) -> None:
    """Send a real double click to *widget*'s center and pump the loop.

    Args:
        qapp: The live QApplication instance.
        widget: Target widget.
    """
    if widget is None or not widget.isVisible():
        raise AssertionError(f"Cannot double-click missing widget: {widget!r}")
    target = getattr(widget, "viewport", lambda: widget)()
    QTest.mouseDClick(target, Qt.MouseButton.LeftButton, pos=center(widget))
    pump(qapp)


def right_click(qapp: QApplication, widget: QWidget) -> None:
    """Send a real right click to *widget*'s center and pump the loop.

    Args:
        qapp: The live QApplication instance.
        widget: Target widget.
    """
    click(qapp, widget, Qt.MouseButton.RightButton)


SPECIAL_KEYS: dict[str, Qt.Key] = {
    "\n": Qt.Key.Key_Return,
    "\r": Qt.Key.Key_Return,
    "\t": Qt.Key.Key_Tab,
    "\b": Qt.Key.Key_Backspace,
}


def type_text(qapp: QApplication, widget: QWidget, text: str) -> None:
    """Send *text* as real key events into *widget* and pump the loop.

    Control characters are delivered as key presses because QTest's ASCII
    key table (``qasciikey.cpp``) asserts on tab and newline.

    Args:
        qapp: The live QApplication instance.
        widget: Target widget; must hold or be able to take keyboard focus.
        text: Characters to type.
    """
    if widget is None:
        raise AssertionError("Cannot type into a missing widget")
    for char in text:
        key = SPECIAL_KEYS.get(char)
        if key is not None:
            QTest.keyClick(widget, key)
        else:
            QTest.keyClicks(widget, char)
    pump(qapp)


def press_key(
    qapp: QApplication,
    widget: QWidget,
    key: Qt.Key,
    modifiers: Qt.KeyboardModifier | None = None,
) -> None:
    """Send a single key press to *widget* and pump the loop.

    Args:
        qapp: The live QApplication instance.
        widget: Target widget.
        key: Qt key to press.
        modifiers: Optional keyboard modifiers.
    """
    if modifiers:
        QTest.keyClick(widget, key, modifiers)
    else:
        QTest.keyClick(widget, key)
    pump(qapp)


def key_sequence(qapp: QApplication, widget: QWidget, sequence: str) -> None:
    """Send a QKeySequence (e.g. ``Ctrl+F``) to *widget* and pump the loop.

    Args:
        qapp: The live QApplication instance.
        widget: Target widget.
        sequence: Key sequence string understood by QKeySequence.
    """
    QTest.keySequence(widget, sequence)
    pump(qapp)


def key_walk(
    qapp: QApplication,
    widget: QWidget,
    keys: Sequence[tuple[Qt.Key, Qt.KeyboardModifier | None]],
) -> None:
    """Send a sequence of (key, modifier) steps, pumping after each one.

    Args:
        qapp: The live QApplication instance.
        widget: Target widget.
        keys: Sequence of (Qt.Key, modifier-or-None) tuples.
    """
    for key, modifiers in keys:
        press_key(qapp, widget, key, modifiers)


def mouse_move(qapp: QApplication, widget: QWidget, pos: QPoint) -> None:
    """Move the test pointer onto *widget* at *pos* and pump the loop.

    Args:
        qapp: The live QApplication instance.
        widget: Target widget.
        pos: In-widget position for the move.
    """
    target = getattr(widget, "viewport", lambda: widget)()
    QTest.mouseMove(target, pos)
    pump(qapp)


# -----------------------------------------------------------------------------
# Sweep recording
# -----------------------------------------------------------------------------


class Sweep:
    """Record per-step failures during an explicit walk and raise at the end.

    Attributes:
        title: Human-readable sweep title for the failure report.
        failures: Collected (step, message) tuples.
    """

    def __init__(self, title: str) -> None:
        """Create an empty sweep.

        Args:
            title: Name shown in the aggregated failure message.
        """
        self.title = title
        self.failures: list[tuple[str, str]] = []

    def step(self, label: str, fn: Callable[[], Any], *args: Any, **kwargs: Any) -> Any:
        """Run one recorded step; a raised exception is captured, not raised.

        Args:
            label: Step description used in the failure report.
            fn: Callable to execute.
            args: Positional arguments forwarded to *fn*.
            kwargs: Keyword arguments forwarded to *fn*.

        Returns:
            The callable's result, or None when the step failed.
        """
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - sweep records any failure
            self.failures.append((label, f"{type(exc).__name__}: {exc}"))
            return None

    def note(self, label: str, message: str) -> None:
        """Record a failure manually without executing a callable.

        Args:
            label: Step description used in the failure report.
            message: Failure detail.
        """
        self.failures.append((label, message))

    @property
    def ok(self) -> bool:
        """Return True when no step has failed."""
        return not self.failures

    def finish(self) -> None:
        """Raise an AssertionError listing every failed step, if any.

        Raises:
            AssertionError: When at least one recorded step failed.
        """
        if not self.ok:
            lines = [f"{self.title}: {len(self.failures)} broken step(s)"]
            for label, message in self.failures:
                lines.append(f"  - {label}: {message}")
            raise AssertionError("\n".join(lines))

    def __enter__(self) -> "Sweep":
        """Enter the sweep context.

        Returns:
            This Sweep instance.
        """
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Finish the sweep, raising if any step failed.

        Args:
            exc_type: Exception type from the with-block, if any.
            exc: Exception instance from the with-block, if any.
            tb: Traceback from the with-block, if any.
        """
        self.finish()


# -----------------------------------------------------------------------------
# Geometry probes
# -----------------------------------------------------------------------------


def live_probe(widget: QWidget) -> list[str]:
    """Walk *widget*'s tree and report visible children with a broken size.

    The tree is traversed through direct children only, so the cost stays
    linear in the number of widgets.

    Args:
        widget: Root widget to inspect recursively.

    Returns:
        List of human-readable issue strings; empty when clean.
    """
    issues: list[str] = []
    stack: list[QWidget] = [widget]
    while stack:
        current = stack.pop()
        for child in current.children():
            if isinstance(child, QWidget):
                stack.append(child)
        if current is widget or not current.isVisible():
            continue
        if current.width() <= 0 or current.height() <= 0:
            issues.append(
                f"zero-size visible widget: {current.objectName() or type(current).__name__} "
                f"({current.width()}x{current.height()})"
            )
    return issues


def assert_positive_size(widget: QWidget, label: str = "widget") -> None:
    """Assert that *widget* is visible with a positive size.

    Args:
        widget: Widget to check.
        label: Name used in the failure message.

    Raises:
        AssertionError: When the widget is missing, hidden, or zero-sized.
    """
    if widget is None:
        raise AssertionError(f"{label} is missing")
    if not widget.isVisible():
        raise AssertionError(f"{label} is not visible")
    if widget.width() <= 0 or widget.height() <= 0:
        raise AssertionError(
            f"{label} has a non-positive size ({widget.width()}x{widget.height()})"
        )


def assert_regions_disjoint(regions: dict[str, Any]) -> None:
    """Assert that no pair of named chrome regions overlaps.

    Args:
        regions: Mapping of region name to QWidget (or QRect).

    Raises:
        AssertionError: When any two regions overlap.
    """
    from PyQt6.QtCore import QRect

    rects: dict[str, QRect] = {}
    for name, region in regions.items():
        if region is None:
            continue
        rects[name] = region if isinstance(region, QRect) else region.geometry()
    names = sorted(rects)
    overlaps: list[str] = []
    for i, first in enumerate(names):
        for second in names[i + 1 :]:
            if rects[first].intersects(rects[second]):
                overlaps.append(f"{first} overlaps {second}")
    if overlaps:
        details = ", ".join(overlaps)
        raise AssertionError(f"Chrome regions overlap: {details}")


# -----------------------------------------------------------------------------
# Toggle, race, and combo helpers
# -----------------------------------------------------------------------------


def toggle_contract(
    qapp: QApplication,
    toggle: Callable[[], Any],
    is_visible: Callable[[], bool],
    rounds: int = 3,
) -> bool:
    """Assert a toggle flips its target visibility on every invocation.

    Args:
        qapp: The live QApplication instance.
        toggle: Zero-argument callable that toggles the panel.
        is_visible: Zero-argument callable reporting target visibility.
        rounds: Number of toggle invocations to verify.

    Returns:
        The final visibility state after all rounds.

    Raises:
        AssertionError: When visibility does not flip exactly once per toggle.
    """
    states = []
    for index in range(rounds):
        before = bool(is_visible())
        toggle()
        pump(qapp)
        after = bool(is_visible())
        if after == before:
            raise AssertionError(
                f"Toggle round {index}: visibility stuck at {before}; "
                "toggle did not flip the target"
            )
        states.append(after)
    return states[-1]


def race_probe(qapp: QApplication, fn: Callable[[], Any], n: int = 5) -> None:
    """Run *fn* n times in a tight loop, pumping between calls.

    Args:
        qapp: The live QApplication instance.
        fn: Zero-argument interaction to repeat rapidly.
        n: Number of repetitions.
    """
    for _ in range(max(1, n)):
        fn()
        pump(qapp)


def combo_probe(qapp: QApplication, *steps: tuple[str, Callable[[], Any]]) -> None:
    """Run overlapping interaction steps, pumping between each one.

    Args:
        qapp: The live QApplication instance.
        steps: Ordered (label, callable) pairs; each callable is invoked once.
    """
    for _label, fn in steps:
        fn()
        pump(qapp)


class SignalCounter:
    """Count emissions of one Qt signal, capturing payloads.

    Attributes:
        count: Number of emissions observed.
        payloads: Argument tuples received per emission.
    """

    def __init__(self, signal: Any) -> None:
        """Connect to *signal*.

        Args:
            signal: Bound PyQt signal to observe.
        """
        self.count = 0
        self.payloads: list[tuple] = []
        signal.connect(self._on_signal)

    def _on_signal(self, *args: Any) -> None:
        """Increment the counter and store the payload.

        Args:
            args: Signal payload.
        """
        self.count += 1
        self.payloads.append(args)

    def reset(self) -> None:
        """Clear the counter and payloads."""
        self.count = 0
        self.payloads.clear()


def signal_probe(signal: Any) -> SignalCounter:
    """Start counting emissions of *signal*.

    Args:
        signal: Bound PyQt signal to observe.

    Returns:
        The SignalCounter attached to the signal.
    """
    return SignalCounter(signal)


# -----------------------------------------------------------------------------
# Widget-focused probes
# -----------------------------------------------------------------------------


def poke(qapp: QApplication, widget: QWidget, sweep: Sweep) -> None:
    """Click every clickable child of *widget*, recording each step.

    Open combo popups are dismissed with Escape after their click. Buttons
    that an earlier interaction hid are skipped, and the walk stops when
    *widget* hides itself (for example through a "Close Panel" button).

    Args:
        qapp: The live QApplication instance.
        widget: Root widget whose clickable children are exercised.
        sweep: Sweep used to record failures without aborting the walk.
    """
    clickable: list[QWidget] = []
    for child in widget.findChildren(QWidget):
        if isinstance(child, CLICKABLE_TYPES) and child.isVisibleTo(widget):
            clickable.append(child)
    seen: set[int] = set()
    for index, child in enumerate(clickable):
        if id(child) in seen:
            continue
        seen.add(id(child))
        if not child.isVisible():
            continue
        label = (
            f"click {type(child).__name__}"
            f"'{child.toolTip() or child.objectName() or index}'"
        )
        sweep.step(label, guarded_click, qapp, child)
        popup = QApplication.activePopupWidget()
        if popup is not None:
            sweep.step(f"dismiss popup after {label}", _close_popup, qapp, popup)
        if not widget.isVisible():
            return


def _close_popup(qapp: QApplication, popup: QWidget) -> None:
    """Close an open popup widget with Escape, then pump.

    Args:
        qapp: The live QApplication instance.
        popup: Popup widget to dismiss.
    """
    QTest.keyClick(popup, Qt.Key.Key_Escape)
    pump(qapp)


def type_probe(qapp: QApplication, widget: QWidget, sweep: Sweep, text: str = "qa") -> None:
    """Type text into every text-entry child of *widget*, then back it out.

    Args:
        qapp: The live QApplication instance.
        widget: Root widget whose text entries are exercised.
        sweep: Sweep used to record failures without aborting the walk.
        text: Text to type into each entry.
    """
    entries: list[QWidget] = []
    for child in widget.findChildren(QWidget):
        if isinstance(child, TEXT_TYPES) and child.isVisibleTo(widget) and not child.isReadOnly():
            entries.append(child)
    for index, child in enumerate(entries):
        label = f"type into {type(child).__name__} #{index}"
        sweep.step(label, _type_and_clear, qapp, child, text)


def _type_and_clear(qapp: QApplication, entry: QWidget, text: str) -> None:
    """Type *text* into *entry* then remove it again with backspaces.

    Args:
        qapp: The live QApplication instance.
        entry: Text-entry widget.
        text: Text to type.

    Raises:
        AssertionError: If the entry does not return to its original content.
    """
    original = entry.toPlainText() if hasattr(entry, "toPlainText") else entry.text()
    entry.setFocus()
    QTest.keyClicks(entry, text)
    pump(qapp)
    for _ in text:
        QTest.keyClick(entry, Qt.Key.Key_Backspace)
    pump(qapp)
    leftover = entry.toPlainText() if hasattr(entry, "toPlainText") else entry.text()
    if leftover != original:
        raise AssertionError(
            f"text entry did not return to its original content: "
            f"{original!r} -> {leftover!r}"
        )


def focus_walk(qapp: QApplication, widget: QWidget, max_tabs: int = 60) -> list[str]:
    """Tab through *widget*'s focus chain and report focus anomalies.

    Args:
        qapp: The live QApplication instance.
        widget: Root widget to start the walk from.
        max_tabs: Safety cap on Tab presses.

    Returns:
        List of issue strings; empty when the chain behaves.
    """
    issues: list[str] = []
    first = QApplication.focusWidget()
    if first is None:
        QTest.keyClick(widget, Qt.Key.Key_Tab)
        pump(qapp)
        first = QApplication.focusWidget()
    if first is None:
        return ["no focusable widget found via Tab"]
    seen: set[int] = set()
    current = first
    for index in range(max_tabs):
        seen.add(id(current))
        previous = current
        QTest.keyClick(widget, Qt.Key.Key_Tab)
        pump(qapp)
        current = QApplication.focusWidget()
        if current is None:
            issues.append(f"focus lost after Tab #{index}")
            break
        if current is previous:
            issues.append(
                f"Tab #{index} did not move focus from "
                f"{type(previous).__name__} '{previous.objectName()}'"
            )
            break
        if id(current) == id(first):
            break
    if not seen:
        issues.append("focus walk visited no widgets")
    return issues


def resize_stress(
    qapp: QApplication,
    window: QWidget,
    sizes: Sequence[tuple[int, int]] = (
        DEFAULT_WINDOW_SIZE,
        (320, 240),
        (1920, 1080),
        DEFAULT_WINDOW_SIZE,
    ),
) -> list[str]:
    """Resize *window* through *sizes* and report geometry issues after each.

    Args:
        qapp: The live QApplication instance.
        window: Window to resize.
        sizes: Sequence of (width, height) tuples applied in order.

    Returns:
        Aggregated live_probe issues across every size.
    """
    issues: list[str] = []
    for width, height in sizes:
        window.resize(width, height)
        pump(qapp, 80)
        issues.extend(live_probe(window))
    return issues


# -----------------------------------------------------------------------------
# Dialog guards and leak checks
# -----------------------------------------------------------------------------


@contextlib.contextmanager
def modal_guard(
    paths: Sequence[str] | None = None,
    cancel: bool = False,
    text: str = "qa_name",
):
    """Stub every native dialog getter for the duration of the block.

    File dialogs return the first entry of *paths* (or empty when *cancel*),
    input dialogs return *text* (or cancel), the color dialog returns a
    fixed blue, message boxes answer without blocking, and the IDE's own
    modal dialogs (``ConfirmDialog``, ``RenameDialog``,
    ``UnsavedChangesDialog``, ``ErrorDialog``) answer through the same
    guard. All patches are local to the with-block.

    Args:
        paths: Paths returned by file dialogs in order; last one repeats.
        cancel: When True, every dialog reports cancellation instead.
        text: Text returned by QInputDialog.getText and RenameDialog.

    Yields:
        The list of calls recorded as (dialog, method, args) tuples.
    """
    from PyQt6.QtGui import QColor
    from PyQt6.QtWidgets import (
        QColorDialog,
        QDialog,
        QFileDialog,
        QInputDialog,
        QMessageBox,
    )

    from editor.widgets.QExitDialog import (
        ConfirmDialog,
        ErrorDialog,
        RenameDialog,
        UnsavedChangesDialog,
    )

    calls: list[tuple[str, str]] = []
    queue = list(paths or [])
    if not queue:
        queue = [""]

    def file_result(*_args: Any, **_kwargs: Any) -> tuple[str, str]:
        """Return the next queued path (or cancellation) for file dialogs.

        Args:
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            (path, filter) tuple shaped like QFileDialog getters.
        """
        calls.append(("QFileDialog", "getter"))
        if cancel:
            return ("", "")
        path = queue.pop(0) if len(queue) > 1 else queue[0]
        return (path, "")

    def dir_result(*_args: Any, **_kwargs: Any) -> str:
        """Return the next queued path (or cancellation) for directory dialogs.

        Args:
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            Directory path string, empty when cancelled.
        """
        calls.append(("QFileDialog", "getExistingDirectory"))
        if cancel:
            return ""
        path = queue.pop(0) if len(queue) > 1 else queue[0]
        return path

    def text_result(*_args: Any, **_kwargs: Any) -> tuple[str, bool]:
        """Return the canned input text (or cancellation) for input dialogs.

        Args:
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            (text, accepted) tuple shaped like QInputDialog.getText.
        """
        calls.append(("QInputDialog", "getText"))
        return (text, not cancel)

    def color_result(*_args: Any, **_kwargs: Any) -> QColor:
        """Return a fixed color (or an invalid one) for the color dialog.

        Args:
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            QColor instance.
        """
        calls.append(("QColorDialog", "getColor"))
        return QColor("#0055ff") if not cancel else QColor()

    def rename_result(_dialog: Any, *_args: Any, **_kwargs: Any) -> str | None:
        """Return the canned name for the custom rename dialog.

        Args:
            _dialog: The RenameDialog instance.
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            The canned text, or None when the dialog reports cancellation.
        """
        calls.append(("RenameDialog", "get_name"))
        return None if cancel else text

    def confirm_result(_dialog: Any, *_args: Any, **_kwargs: Any) -> int:
        """Answer the custom confirmation dialog without blocking.

        Args:
            _dialog: The ConfirmDialog instance.
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            The QDialog dialog code matching the guard mode.
        """
        calls.append(("ConfirmDialog", "exec"))
        return QDialog.DialogCode.Rejected if cancel else QDialog.DialogCode.Accepted

    def unsaved_result(dialog: Any, *_args: Any, **_kwargs: Any) -> int:
        """Answer the unsaved-changes dialog without blocking.

        Args:
            dialog: The UnsavedChangesDialog instance.
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            The QDialog dialog code matching the guard mode.
        """
        calls.append(("UnsavedChangesDialog", "exec"))
        if not cancel:
            dialog.result = UnsavedChangesDialog.RESULT_DISCARD
        return QDialog.DialogCode.Rejected if cancel else QDialog.DialogCode.Accepted

    def error_result(_dialog: Any, *_args: Any, **_kwargs: Any) -> int:
        """Dismiss the custom error dialog without blocking.

        Args:
            _dialog: The ErrorDialog instance.
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            Always QDialog.DialogCode.Rejected.
        """
        calls.append(("ErrorDialog", "exec"))
        return QDialog.DialogCode.Rejected

    def message_box_result(*_args: Any, **_kwargs: Any) -> Any:
        """Answer a static QMessageBox helper without blocking.

        Args:
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            The standard button matching the guard mode.
        """
        calls.append(("QMessageBox", "static"))
        if cancel:
            return QMessageBox.StandardButton.No
        return QMessageBox.StandardButton.Ok

    def message_box_exec(_dialog: Any, *_args: Any, **_kwargs: Any) -> Any:
        """Answer an exec()'d QMessageBox without blocking.

        Args:
            _dialog: The QMessageBox instance.
            _args: Ignored dialog arguments.
            _kwargs: Ignored dialog keyword arguments.

        Returns:
            The standard button matching the guard mode.
        """
        calls.append(("QMessageBox", "exec"))
        if cancel:
            return QMessageBox.StandardButton.No
        return QMessageBox.StandardButton.Ok

    patches = [
        unittest.mock.patch.object(QFileDialog, "getOpenFileName", side_effect=file_result),
        unittest.mock.patch.object(
            QFileDialog, "getOpenFileNames", side_effect=lambda *a, **k: (file_result(), [])
        ),
        unittest.mock.patch.object(QFileDialog, "getSaveFileName", side_effect=file_result),
        unittest.mock.patch.object(QFileDialog, "getExistingDirectory", side_effect=dir_result),
        unittest.mock.patch.object(QFileDialog, "getExistingDirectoryUrl", side_effect=dir_result),
        unittest.mock.patch.object(QInputDialog, "getText", side_effect=text_result),
        unittest.mock.patch.object(
            QInputDialog, "getItem", side_effect=lambda *a, **k: (text, not cancel)
        ),
        unittest.mock.patch.object(
            QInputDialog, "getMultiLineText", side_effect=text_result
        ),
        unittest.mock.patch.object(
            QColorDialog, "getColor", side_effect=color_result
        ),
        unittest.mock.patch.object(
            QMessageBox, "information", side_effect=message_box_result
        ),
        unittest.mock.patch.object(
            QMessageBox, "warning", side_effect=message_box_result
        ),
        unittest.mock.patch.object(
            QMessageBox, "critical", side_effect=message_box_result
        ),
        unittest.mock.patch.object(
            QMessageBox, "about", side_effect=message_box_result
        ),
        unittest.mock.patch.object(
            QMessageBox, "question", side_effect=message_box_result
        ),
        unittest.mock.patch.object(
            QMessageBox, "exec", autospec=True, side_effect=message_box_exec
        ),
        unittest.mock.patch.object(
            RenameDialog, "get_name", autospec=True, side_effect=rename_result
        ),
        unittest.mock.patch.object(
            ConfirmDialog, "exec", autospec=True, side_effect=confirm_result
        ),
        unittest.mock.patch.object(
            UnsavedChangesDialog, "exec", autospec=True, side_effect=unsaved_result
        ),
        unittest.mock.patch.object(
            ErrorDialog, "exec", autospec=True, side_effect=error_result
        ),
    ]
    with contextlib.ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        yield calls


def top_level_dialogs() -> list[QWidget]:
    """Return every live top-level QDialog across the application.

    Returns:
        List of QDialog widgets that are top-level windows.
    """
    app = QApplication.instance()
    if app is None:
        return []
    return [w for w in app.topLevelWidgets() if isinstance(w, QDialog) and w.isWindow()]


def popup_count() -> int:
    """Return the number of currently open popup widgets.

    Returns:
        Count of active popup widgets.
    """
    count = 0
    popup = QApplication.activePopupWidget()
    while popup is not None:
        count += 1
        popup = QApplication.activePopupWidget() if popup.parentWidget() is None else None
    return count


# -----------------------------------------------------------------------------
# Service probes
# -----------------------------------------------------------------------------


def service_probe(
    service: Any,
    calls: dict[str, Callable[[], Any]],
    sweep: Sweep | None = None,
) -> dict[str, Any]:
    """Invoke benign public-API callables against *service* and record issues.

    Args:
        service: Service object under test (used only for the report labels).
        calls: Mapping of step label to zero-argument callable.
        sweep: Optional external Sweep; a local one is used when omitted.

    Returns:
        Mapping of step label to callable result.
    """
    local = sweep if sweep is not None else Sweep(f"service probe {type(service).__name__}")
    results: dict[str, Any] = {}
    for label, fn in calls.items():
        results[label] = local.step(label, fn)
    if sweep is None:
        local.finish()
    return results


def roundtrip_probe(
    apply: Callable[[], None],
    check: Callable[[], None],
    revert: Callable[[], None],
    restore_check: Callable[[], None],
) -> None:
    """Apply a change, verify it, revert, and verify the clean state.

    Args:
        apply: Callable performing the change.
        check: Callable asserting the applied state.
        revert: Callable reverting the change.
        restore_check: Callable asserting the restored state.

    Raises:
        AssertionError: When any stage fails; reverts are still attempted.
    """
    apply()
    try:
        check()
    finally:
        revert()
        restore_check()


def assert_alive(qapp: QApplication, window: QWidget | None = None) -> None:
    """Assert the QApplication (and window, when given) still exists.

    Args:
        qapp: The live QApplication instance.
        window: Optional main window to check too.

    Raises:
        AssertionError: When the application or window vanished.
    """
    if QApplication.instance() is None:
        raise AssertionError("QApplication disappeared")
    if window is not None and not window.isVisible():
        raise AssertionError("main window disappeared or was hidden")


def settle_analysis(qapp: QApplication, problems: QWidget, timeout_ms: int = 20000) -> None:
    """Stop the problem scanner's timers and wait for every worker thread.

    The workspace scanner runs several QThreads parented to the
    ProblemsWidget; deleting the widget while one of them runs aborts Qt.
    Teardown must call this before the window is deleted.

    Args:
        qapp: The live QApplication instance.
        problems: The ProblemsWidget instance (private internals are used).
        timeout_ms: Maximum wall-clock time to wait for the workers.
    """
    from PyQt6.QtCore import QThread

    stop = getattr(problems, "_stop_timers", None)
    if callable(stop):
        with contextlib.suppress(Exception):
            stop()

    def running_threads() -> list:
        """Return the child QThreads that are still running.

        Returns:
            List of running QThread children.
        """
        running = []
        for thread in problems.findChildren(QThread):
            try:
                if thread.isRunning():
                    running.append(thread)
            except RuntimeError:
                continue
        return running

    remaining = max(0, timeout_ms)
    while remaining > 0 and running_threads():
        pump(qapp, 50)
        remaining -= 50

    # Pending single-shot callbacks may still arm a new worker; let them run
    # and wait again so no thread survives the widget destruction.
    pump(qapp, 100)
    remaining = max(0, timeout_ms)
    while remaining > 0 and running_threads():
        pump(qapp, 50)
        remaining -= 50


def settle_editors(window: QWidget) -> None:
    """Shut down the analysis managers of every editor open in *window*.

    Args:
        window: The DreamStudio main window.
    """
    try:
        tabs = window.hero_window._text_editor_center.tabs
    except AttributeError:
        return
    for index in range(tabs.count()):
        try:
            widget = tabs.widget(index)
        except RuntimeError:
            continue
        editor = getattr(widget, "editor", None)
        if editor is None:
            editor = widget
        manager = getattr(editor, "_analysis_manager", None)
        if manager is None:
            continue
        shutdown = getattr(manager, "shutdown", None)
        if callable(shutdown):
            with contextlib.suppress(Exception):
                shutdown()
