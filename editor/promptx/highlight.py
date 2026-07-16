from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont


class PromptXHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self._build_rules()

    def _build_rules(self):
        self._error_fmt = QTextCharFormat()
        self._error_fmt.setForeground(QColor("#FF5252"))
        self._error_fmt.setFontWeight(QFont.Weight.Bold)

        self._cmd_fmt = QTextCharFormat()
        self._cmd_fmt.setForeground(QColor("#FFD740"))
        self._cmd_fmt.setFontWeight(QFont.Weight.Bold)

        self._num_fmt = QTextCharFormat()
        self._num_fmt.setForeground(QColor("#69F0AE"))

        self._success_fmt = QTextCharFormat()
        self._success_fmt.setForeground(QColor("#40C4FF"))
        self._success_fmt.setFontWeight(QFont.Weight.Bold)

        self._prompt_fmt = QTextCharFormat()
        self._prompt_fmt.setForeground(QColor("#888888"))

        commands = (
            "changedir|clear|clearhistory|clone|copydir|cpuinfo|date|deletedir|"
            "diskinfo|download|echo|env|erase|find|fileinfo|head|help|here|"
            "history|ip_scan|kill|makedir|me|meminfo|mybox|netlist|newbie|"
            "pacman|peek|ping|ps|quit|rename|shift|sysinfo|tail|unzip|uptime|"
            "whoami|zip"
        )

        self._prompt_rx = QRegularExpression(r"^.*>>>\s")

        self._cmd_rx = QRegularExpression(
            rf"(?<=>>> )({commands})\b",
            QRegularExpression.PatternOption.CaseInsensitiveOption,
        )

        self._num_rx = QRegularExpression(r"(?<![\d.:])\b\d+\b(?![\d.:])")

        self._success_keywords = [
            "success",
            "successful",
            "successfully",
            "done",
            "created",
            "completed",
            "copied",
            "renamed",
            "shifted",
            "downloaded",
            "extracted",
            "archive",
            "cloned",
            "removed",
            "deleted",
            "cleared",
        ]

    def highlightBlock(self, text):
        if text.startswith("Error"):
            self.setFormat(0, len(text), self._error_fmt)
            return

        lower = text.lower()
        for kw in self._success_keywords:
            if kw in lower:
                self.setFormat(0, len(text), self._success_fmt)
                break

        it = self._num_rx.globalMatch(text)
        while it.hasNext():
            match = it.next()
            self.setFormat(match.capturedStart(), match.capturedLength(), self._num_fmt)

        if ">>>" in text:
            it = self._prompt_rx.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(0, match.capturedLength(), self._prompt_fmt)

            it = self._cmd_rx.globalMatch(text)
            while it.hasNext():
                match = it.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), self._cmd_fmt)


