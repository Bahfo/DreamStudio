import os
import re
import fnmatch
from PyQt6.QtCore import QThread, pyqtSignal

DEFAULT_IGNORED_DIRS = {
    "venv",
    ".venv",
    "env",
    ".env",
    "site-packages",
    "node_modules",
    ".next",
    ".nuxt",
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "build",
    "dist",
    "*.egg-info",
    ".eggs",
    "bin",
    "obj",
}


class SearchWorker(QThread):

    match_found = pyqtSignal(str, int, str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(
        self,
        term,
        is_regex,
        includes,
        excludes,
        match_word,
        match_case,
        directory,
    ):
        super().__init__()

        self.term = term
        self.is_regex = is_regex
        self.match_case = match_case
        self.match_word = match_word
        self.directory = directory
        self._is_cancelled = False

        if isinstance(includes, str):
            self.includes = [i.strip() for i in includes.split(",") if i.strip()]
        else:
            self.includes = [i.strip() for i in includes if i.strip()]
        if not self.includes:
            self.includes = ["*"]

        if isinstance(excludes, str):
            user_excludes = [e.strip() for e in excludes.split(",") if e.strip()]
        else:
            user_excludes = [e.strip() for e in excludes if e.strip()]

        self.dir_excludes = set(user_excludes).union(DEFAULT_IGNORED_DIRS)
        self.file_excludes = set(user_excludes)

    def cancel(self):
        """Allows the GUI to safely stop the search mid-way."""
        self._is_cancelled = True

    def run(self):
        try:
            pattern_str = self.term if self.is_regex else re.escape(self.term)
            if self.match_word:
                pattern_str = rf"\b{pattern_str}\b"

            flags = 0 if self.match_case else re.IGNORECASE
            pattern = re.compile(pattern_str, flags)

            total_matches = 0

            for root, dirs, files in os.walk(self.directory):
                if self._is_cancelled:
                    break

                dirs[:] = [d for d in dirs if not self._is_dir_excluded(d)]

                for file in files:
                    if self._is_cancelled:
                        break

                    if self._is_file_included(file):
                        filepath = os.path.join(root, file)
                        matches = self._search_file(filepath, pattern)
                        total_matches += matches

            if not self._is_cancelled:
                self.finished.emit(total_matches)

        except Exception as e:
            self.error.emit(str(e))

    def _is_dir_excluded(self, dirname):
        """Checks if a directory matches any default or user exclude patterns."""

        if dirname.startswith("."):
            return True

        for exc in self.dir_excludes:
            clean_exc = exc.rstrip("/\\")
            if fnmatch.fnmatch(dirname, clean_exc) or fnmatch.fnmatch(
                dirname.lower(), clean_exc.lower()
            ):
                return True
        return False

    def _is_file_included(self, filename):
        """Checks if a file matches include rules and is NOT explicitly excluded."""
        for exc in self.file_excludes:
            clean_exc = exc.rstrip("/\\")
            if fnmatch.fnmatch(filename, clean_exc):
                return False

        return any(fnmatch.fnmatch(filename, inc) for inc in self.includes)

    def _search_file(self, filepath, pattern):
        """Reads a file line by line while skipping binary files efficiently."""
        matches = 0
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:

                first_chunk = f.read(1024)
                if "\x00" in first_chunk:
                    return 0

                f.seek(0)
                for line_num, line in enumerate(f, 1):
                    if self._is_cancelled:
                        break
                    if pattern.search(line):
                        self.match_found.emit(filepath, line_num, line.strip())
                        matches += 1
        except (PermissionError, OSError):
            pass

        return matches
