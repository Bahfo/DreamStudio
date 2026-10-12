"""
SplashController: displays startup progress.

The splash screen contains zero business logic. It only receives
progress updates and renders status text.
"""

import logging
import time
import os

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QFont,
    QColor,
    QImage,
    QPainter,
    QPixmap,
    QPainterPath,
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QSplashScreen, QApplication

from fonts.font_strapper import Fonts

logger = logging.getLogger(__name__)

_SPLASH_WIDTH = 690
_SPLASH_HEIGHT = 450
_CORNER_RADIUS = 0.0
_MIN_VISIBLE_SECONDS = 5.0
_FADE_IN_MS = 550
_FADE_FRAME_MS = 16


def _get_icon_src_path() -> str:
    import sys

    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "icon_src", "blue_geometry.svg")
    return os.path.normpath(
        os.path.join(
            os.path.dirname(__file__), os.pardir, "icon_src", "blue_geometry.svg"
        )
    )


_SVG_PATH = _get_icon_src_path()


def _get_sans_font(
    point_size: int, weight: QFont.Weight = QFont.Weight.Normal
) -> QFont:
    """Helper to generate a clean, cross-platform sans-serif font."""
    font = QFont()
    font.setStyleHint(QFont.StyleHint.SansSerif)
    font.setFamilies(
        [
            Fonts.FONT_INTER,
            "Roboto",
            Fonts.FONT_SEGOE_UI,
            "Helvetica Neue",
            "Arial",
            "sans-serif",
        ]
    )
    font.setPointSize(point_size)
    font.setWeight(weight)
    return font


def _render_pixmap(status_text: str, progress: float) -> QPixmap:
    """Render the splash content onto a high-DPI-aware QPixmap."""

    app = QApplication.instance()
    ratio = (
        app.primaryScreen().devicePixelRatio() if app and app.primaryScreen() else 1.0
    )

    pixmap = QPixmap(int(_SPLASH_WIDTH * ratio), int(_SPLASH_HEIGHT * ratio))
    pixmap.fill(Qt.GlobalColor.transparent)
    pixmap.setDevicePixelRatio(ratio)

    painter = QPainter(pixmap)

    painter.setRenderHints(
        QPainter.RenderHint.Antialiasing
        | QPainter.RenderHint.TextAntialiasing
        | QPainter.RenderHint.SmoothPixmapTransform
    )

    logical_rect = QRectF(0, 0, _SPLASH_WIDTH, _SPLASH_HEIGHT)

    clip_path = QPainterPath()
    clip_path.addRoundedRect(logical_rect, _CORNER_RADIUS, _CORNER_RADIUS)
    painter.setClipPath(clip_path)

    if os.path.isfile(_SVG_PATH):
        renderer = QSvgRenderer(_SVG_PATH)
        if renderer.isValid():
            renderer.render(painter, logical_rect)
    else:
        logger.warning("SVG not found: %s", _SVG_PATH)

    bar_h = 4
    bar_y = _SPLASH_HEIGHT - bar_h

    painter.fillRect(QRectF(0, bar_y, _SPLASH_WIDTH, bar_h), QColor(0, 0, 0, 60))

    fill_w = int(_SPLASH_WIDTH * progress)
    if fill_w > 0:
        painter.fillRect(QRectF(0, bar_y, fill_w, bar_h), QColor("#FFFFFF"))

    status_font = _get_sans_font(8)
    painter.setFont(status_font)
    painter.setPen(QColor("#FFFFFFD0"))
    painter.drawText(
        QRectF(15, bar_y - 28, _SPLASH_WIDTH - 30, 20),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        status_text,
    )

    painter.end()

    return pixmap


def _with_opacity(source: QPixmap, opacity: float) -> QPixmap:
    """Return *source* with its overall alpha scaled by *opacity*.

    Paints through an explicit ARGB image so the result carries a real
    alpha channel on every platform (a plain ``QPixmap`` may be
    allocated without one, which would fade from black instead).

    Args:
        source: Fully rendered splash pixmap.
        opacity: 0.0 (fully transparent) to 1.0 (unchanged).

    Returns:
        New pixmap with the same size and device pixel ratio.
    """
    clamped = max(0.0, min(1.0, opacity))
    image = source.toImage().convertToFormat(
        QImage.Format.Format_ARGB32_Premultiplied
    )
    painter = QPainter(image)
    painter.setCompositionMode(
        QPainter.CompositionMode.CompositionMode_DestinationIn
    )
    painter.fillRect(image.rect(), QColor(0, 0, 0, round(255 * clamped)))
    painter.end()
    faded = QPixmap.fromImage(image)
    faded.setDevicePixelRatio(source.devicePixelRatio())
    return faded


class _ClickThroughSplash(QSplashScreen):
    """Splash screen that ignores mouse clicks.

    ``QSplashScreen`` hides itself when clicked, which would leave the
    boot running in the background with no visible feedback. Swallowing
    the press/double-click events keeps the splash up until the
    controller closes it programmatically.
    """

    def mousePressEvent(self, event) -> None:
        """Ignore mouse presses so a click cannot dismiss the splash.

        Args:
            event: The incoming mouse-press event.
        """
        if event is not None:
            event.ignore()

    def mouseDoubleClickEvent(self, event) -> None:
        """Ignore double-clicks for the same reason as single clicks.

        Args:
            event: The incoming mouse double-click event.
        """
        if event is not None:
            event.ignore()


class SplashController:
    """Thin wrapper around QSplashScreen for startup progress."""

    def __init__(self) -> None:
        self._splash: QSplashScreen | None = None
        self._step_count = 0
        self._current_step = 0
        self._status_text = "Starting..."
        self._closed = False
        self._shown_at = 0.0
        logger.info("SplashController created")

    def set_step_count(self, count: int) -> None:
        """Define total number of steps for progress calculation."""
        self._step_count = count

    def show(self) -> None:
        """Display the splash screen with a fade-in animation."""
        base = _render_pixmap(self._status_text, 0.0)

        self._splash = _ClickThroughSplash(_with_opacity(base, 0.0))
        self._splash.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self._splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._splash.show()
        self._start_fade_in(base)
        self._shown_at = time.monotonic()
        logger.info("Splash screen shown")

    def _start_fade_in(self, base: QPixmap) -> None:
        """Fade the splash pixmap from transparent to *base*.

        The fade is painted into the pixmap itself (rather than using
        window opacity), so it renders identically with or without a
        compositing window manager. It runs to completion inside
        ``show()`` via a short nested event loop, since boot phases
        after ``show()`` perform long blocking work that would
        otherwise freeze the fade mid-flight.

        Args:
            base: Fully opaque target pixmap to fade towards.
        """
        from PyQt6.QtCore import QElapsedTimer, QEventLoop, QTimer

        if self._splash is None:
            return
        clock = QElapsedTimer()
        clock.start()
        loop = QEventLoop()
        ticker = QTimer()
        ticker.setInterval(_FADE_FRAME_MS)
        state = {"done": False}

        def _paint_frame() -> None:
            if self._splash is None:
                return
            raw = clock.elapsed() / _FADE_IN_MS
            progress = 1.0 if raw >= 1.0 else raw
            eased = progress * progress * (3.0 - 2.0 * progress)
            self._splash.setPixmap(_with_opacity(base, eased))
            self._splash.repaint()
            if progress >= 1.0:
                _finish()

        def _finish() -> None:
            if state["done"]:
                return
            state["done"] = True
            ticker.stop()
            if self._splash is not None:
                self._splash.setPixmap(base)
                self._splash.repaint()
            loop.quit()

        ticker.timeout.connect(_paint_frame)
        QTimer.singleShot(_FADE_IN_MS + 800, _finish)
        _paint_frame()
        ticker.start()
        loop.exec()
        _finish()

    def update_status(self, message: str, step: int | None = None) -> None:
        """Update displayed status text and optionally advance step."""
        if step is not None:
            self._current_step = step
        self._status_text = message

        if self._splash and not self._closed:
            progress = 0.0
            if self._step_count > 0:
                progress = self._current_step / self._step_count

            pixmap = _render_pixmap(self._status_text, progress)
            self._splash.setPixmap(pixmap)
            self._splash.repaint()

            app = QApplication.instance()
            if app:
                app.processEvents()
            logger.debug(
                "Splash status: %s (%d/%d)",
                message,
                self._current_step,
                self._step_count,
            )

    def close(self) -> None:
        """Close and delete the splash screen.

        Keeps the splash visible for at least ``_MIN_VISIBLE_SECONDS``
        so it stays on screen a bit longer on fast startups.
        """
        if self._splash and not self._closed:
            remaining = _MIN_VISIBLE_SECONDS - (time.monotonic() - self._shown_at)
            app = QApplication.instance()
            while remaining > 0:
                chunk = min(remaining, 0.05)
                time.sleep(chunk)
                if app:
                    app.processEvents()
                remaining -= chunk
            self._splash.close()
            self._splash.deleteLater()
            self._splash = None
            self._closed = True
            app = QApplication.instance()
            if app:
                app.processEvents()
            logger.info("Splash screen closed")

    @property
    def is_visible(self) -> bool:
        return self._splash is not None and not self._closed
