"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

GitIgnore parser and service for Solution Explorer highlighting.
Reads .gitignore line by line, matches files/directories and
exposes patterns via a singleton service that watches the file
for modifications or first-time creation.
"""

from __future__ import annotations

from editor import *

logger = logging.getLogger(__name__)

GITIGNORE_FILENAME = ".gitignore"

GITIGNORE_FG = QColor("#8C8C8C")
GITIGNORE_FG_BRUSH = QBrush(GITIGNORE_FG)
GITIGNORE_FG_BRUSH.setStyle(Qt.BrushStyle.SolidPattern)
GITIGNORE_BG = GITIGNORE_FG
GITIGNORE_BG_BRUSH = GITIGNORE_FG_BRUSH


def parse_gitignore_file(path: str) -> list[str]:
    patterns: list[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    continue
                if line.startswith("\\#") or line.startswith("\\!"):
                    line = line[1:]
                patterns.append(line)
    except OSError as exc:
        logger.debug("parse_gitignore failed for %s: %s", path, exc)
    return patterns


def is_ignored(relative_posix: str, is_dir: bool, patterns: list[str]) -> bool:
    if not patterns:
        return False
    rel = relative_posix.replace(os.sep, "/").lstrip("/")
    if not rel or rel == ".":
        return False
    basename = rel.rsplit("/", 1)[-1] if "/" in rel else rel
    ignored = False
    for pat in patterns:
        if not pat:
            continue
        negated = pat.startswith("!")
        raw = pat[1:] if negated else pat
        if not raw:
            continue
        is_dir_pat = raw.endswith("/")
        pat_core = raw.rstrip("/")
        if not pat_core:
            continue
        anchored = pat_core.startswith("/")
        if anchored:
            pat_core = pat_core.lstrip("/")

        matched = False

        def _translate_pat(pat: str) -> str:
            # Translate gitignore pat with ** support to regex
            # Handle /**/, **/, /**, ** specially for zero-or-more dirs
            # Escape first, then replace placeholders
            # Order matters: handle /**/ first
            esc = re.escape(pat)
            # /**/ -> (?:/.*)?/  (zero or more dirs)
            esc = esc.replace(r"/\*\*/", r"/___DS___/")
            esc = esc.replace(r"\*\*/", r"___DS_SLASH___")
            esc = esc.replace(r"/\*\*", r"___SLASH_DS___")
            esc = esc.replace(r"\*\*", "___STARSTAR___")
            esc = esc.replace(r"\*", r"[^/]*")
            esc = esc.replace(r"\?", r"[^/]")
            esc = esc.replace(r"/___DS___/", r"(?:/.*)?/")
            esc = esc.replace("___DS_SLASH___", r"(?:.*/)?")
            esc = esc.replace("___SLASH_DS___", r"(?:/.*)?")
            esc = esc.replace("___STARSTAR___", r".*")
            return esc

        def _match(name: str, pattern: str) -> bool:
            # Handle ** via regex, otherwise fnmatch with ** support
            if "**" in pattern:
                try:
                    rx = _translate_pat(pattern)
                    return re.fullmatch(rx, name) is not None
                except re.error:
                    return fnmatch.fnmatch(name, pattern.replace("**", "*"))
            return fnmatch.fnmatch(name, pattern)

        if anchored:
            if _match(rel, pat_core) or _match(rel, pat_core + "/*"):
                matched = True
            if is_dir_pat and (rel == pat_core or rel.startswith(pat_core + "/")):
                matched = True
        else:
            if "/" in pat_core:
                if _match(rel, pat_core) or _match(rel, pat_core + "/*"):
                    matched = True
                if is_dir_pat and (rel == pat_core or rel.startswith(pat_core + "/")):
                    matched = True
                if not matched:
                    if _match(rel, "*/" + pat_core) or _match(rel, "*/" + pat_core + "/*"):
                        matched = True
            else:
                if _match(basename, pat_core):
                    matched = True
                if is_dir_pat:
                    parts = rel.split("/")
                    for part in parts:
                        if _match(part, pat_core):
                            matched = True
                            break
                    if not matched and (rel == pat_core or rel.startswith(pat_core + "/")):
                        if _match(parts[0], pat_core):
                            matched = True
        if matched:
            ignored = not negated
    return ignored


class GitIgnoreService(QObject):
    patterns_updated = pyqtSignal(list)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._root: str = ""
        self._patterns: list[str] = []
        self._watcher: Optional[QFileSystemWatcher] = None
        self._gitignore_path: str = ""
        try:
            self._watcher = QFileSystemWatcher(self)
            self._watcher.directoryChanged.connect(self._on_directory_changed)
            self._watcher.fileChanged.connect(self._on_file_changed)
        except Exception as exc:
            logger.debug("GitIgnore watcher init failed: %s", exc)
            self._watcher = None
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.stop)

    def set_root(self, root_path: str) -> None:
        resolved = os.path.abspath(os.path.expanduser(root_path)) if root_path else ""
        if resolved == self._root:
            self._reload()
            return
        self._root = resolved
        self._gitignore_path = os.path.join(self._root, GITIGNORE_FILENAME) if self._root else ""
        self._refresh_watcher()
        self._reload()

    def stop(self) -> None:
        if self._watcher is None:
            return
        try:
            for p in self._watcher.directories():
                self._watcher.removePath(p)
            for p in self._watcher.files():
                self._watcher.removePath(p)
        except Exception:
            pass

    def patterns(self) -> list[str]:
        return list(self._patterns)

    def is_active(self) -> bool:
        return bool(self._patterns) or (
            self._gitignore_path and os.path.isfile(self._gitignore_path)
        )

    def _refresh_watcher(self) -> None:
        if self._watcher is None or not self._root:
            return
        try:
            for p in list(self._watcher.directories()):
                self._watcher.removePath(p)
            for p in list(self._watcher.files()):
                self._watcher.removePath(p)
        except Exception:
            pass
        try:
            if os.path.isdir(self._root):
                self._watcher.addPath(self._root)
            if self._gitignore_path and os.path.isfile(self._gitignore_path):
                self._watcher.addPath(self._gitignore_path)
        except Exception as exc:
            logger.debug("GitIgnore watcher refresh failed: %s", exc)

    def _on_directory_changed(self, path: str) -> None:
        if not self._root:
            return
        git_exists = self._gitignore_path and os.path.isfile(self._gitignore_path)
        in_watcher = False
        try:
            in_watcher = self._gitignore_path in self._watcher.files()
        except Exception:
            pass
        if git_exists and not in_watcher:
            try:
                self._watcher.addPath(self._gitignore_path)
            except Exception:
                pass
            self._reload()
        elif not git_exists and in_watcher:
            try:
                self._watcher.removePath(self._gitignore_path)
            except Exception:
                pass
            self._patterns = []
            self.patterns_updated.emit([])
        elif git_exists:
            self._reload()
        else:
            if self._patterns:
                self._patterns = []
                self.patterns_updated.emit([])

    def _on_file_changed(self, path: str) -> None:
        if path == self._gitignore_path:
            try:
                if self._watcher is not None and path not in self._watcher.files():
                    if os.path.isfile(path):
                        self._watcher.addPath(path)
            except Exception:
                pass
            self._reload()

    def _reload(self) -> None:
        if not self._gitignore_path or not os.path.isfile(self._gitignore_path):
            if self._patterns:
                self._patterns = []
                self.patterns_updated.emit([])
            return
        patterns = parse_gitignore_file(self._gitignore_path)
        if patterns != self._patterns:
            self._patterns = patterns
            self.patterns_updated.emit(list(patterns))
        else:
            self.patterns_updated.emit(list(patterns))


_gitignore_service: Optional[GitIgnoreService] = None


def get_gitignore_service() -> GitIgnoreService:
    global _gitignore_service
    if _gitignore_service is None:
        _gitignore_service = GitIgnoreService()
    return _gitignore_service
