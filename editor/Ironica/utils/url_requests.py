"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Utility to support URL links out of the box.
"""

import re
import urllib.request
from typing import Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor

from PyQt6.QtCore import Qt, QTimer, QUrl, QPoint, QObject, pyqtSignal, QEvent
from PyQt6.QtGui import QColor, QDesktopServices, QCursor
from PyQt6.QtWidgets import QToolTip
from PyQt6.Qsci import QsciScintilla

URL_REGEX = re.compile(r"https?://[^\s()<>]+(?:\([\w\d]+\)|([^[:punct:]\s]|/))")


class URLLinkManager(QObject):
    """
    Scanner for URL support. It checks the reachability of a URL link
    asynchronously, highlights valid/invalid URLs, and enables the
    CTRL+CLICK browser navigation.
    """

    url_validated = pyqtSignal(str, bool)  # URL, is_valid

    INDIC_VALID = 9
    INDIC_INVALID = 10
    INDIC_PENDING = 11

    def __init__(self, editor: QsciScintilla):
        super().__init__(editor)

        self.editor = editor
        self.executor = ThreadPoolExecutor(max_workers=4)

        self.cache: Dict[str, bool] = {}
        self.url_map: Dict[Tuple[int, int], str] = {}

    def _setup_indicators(self):
        self._configure_indicator(
            self.INDIC_VALID,
            QColor("#22C55E"),
            fill_alpha=40,
            outline_alpha=200,
        )

    def _configure_indicator(self, indic_id, color, fill_alpha, outline_alpha):
        pass
