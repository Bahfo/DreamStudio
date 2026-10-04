from editor import *

# Local Imports
from editor.widgets.QSegmentedProgressBar import (
    SegmentedProgressBar,
    FlowLayout,
)


def _badge_color(value: object) -> str:
    """Return a valid badge color, falling back to neutral white."""
    if isinstance(value, str):
        candidate = value.strip()
        if len(candidate) == 7 and candidate.startswith("#"):
            try:
                int(candidate[1:], 16)
                return candidate
            except ValueError:
                pass
    return "#ffffff"


def get_interpreter_info() -> dict:
    """
    Extracts the Python interpreter engine configurations and
    runtime variables, then returns a dictionary containing all
    these information.
    """
    version = platform.python_version()
    compiler = platform.python_compiler()
    implementation = platform.python_implementation()
    api_version = getattr(sys, "api_version", None)
    hex_version = sys.hexversion

    return {
        "version": version,
        "compiler": compiler,
        "implementation": implementation,
        "api_version": api_version,
        "hex_version": hex_version,
    }


def get_interpreter_path(workspace_dir: str | None = None) -> dict:
    """
    Returns the interpreter path information.

    Distinguishes IDE runtime from workspace venv so callers do not
    mistake one for the other.
    """
    executable = sys.executable
    prefix = sys.prefix
    stdlib_dir = sysconfig.get_path("stdlib")
    purelib_dir = sysconfig.get_path("purelib")
    sys_path = sys.prefix
    workspace_python = ""
    try:
        if workspace_dir and os.path.isdir(workspace_dir):
            from editor.debugger.run.python_resolver import find_venv_python

            workspace_python = find_venv_python(workspace_dir) or ""
    except Exception:
        workspace_python = ""

    return {
        "executable": executable,
        "prefix": prefix,
        "stdlib_dir": stdlib_dir,
        "purelib_dir": purelib_dir,
        "sys_path": sys_path,
        "workspace_python": workspace_python,
        "note": "executable/prefix are the IDE runtime; workspace_python is the project venv when present.",
    }


def get_env_variables() -> dict:
    """
    Returns environment variables.
    """
    return {
        "vevn_path": os.environ.get("VIRTUAL_ENV"),
        "python_path": os.environ.get("PYTHONPATH"),
    }


class LanguageBadge(QWidget):
    def __init__(self, name: str, percentage: float, color_hex: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(6)

        dot = QLabel()
        dot.setFixedSize(8, 8)
        dot.setStyleSheet(f"background-color: {color_hex}; border-radius: 4px;")

        text = QLabel(
            f"<span style='color: #c9d1d9; font-weight: 600;'>{name}</span> "
            f"<span style='color: #8b949e;'>{percentage:.1f}%</span>"
        )
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        layout.addWidget(dot)
        layout.addWidget(text)


class LanguageAnalyzer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 8, 4, 8)
        self.main_layout.setSpacing(10)
        self.setStyleSheet("background-color: transparent;")

        self.setMinimumHeight(65)

        self.bar = SegmentedProgressBar()

        self.legend_container = QWidget()
        self.legend_layout = FlowLayout(self.legend_container, margin=0, spacing=8)

        self.main_layout.addWidget(self.bar)
        self.main_layout.addWidget(self.legend_container)

        self.setStyleSheet("font-family: Segoe UI, Inter, sans-serif; font-size: 12px;")

    def _get_ignore_patterns(self, target_dir: str) -> list:
        """Parses .gitignore if it exists, otherwise uses sensible defaults."""
        patterns = [
            ".git",
            "venv",
            ".venv",
            "env",
            "__pycache__",
            "node_modules",
            "build",
            "dist",
            ".idea",
            ".vscode",
        ]
        gitignore_path = os.path.join(target_dir, ".gitignore")

        if os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pat = line.strip("/")
                        if pat not in patterns:
                            patterns.append(pat)
        return patterns

    def analyze_directory(self, target_dir: str):
        stats = {}
        total_bytes = 0
        ignore_patterns = self._get_ignore_patterns(target_dir)
        try:
            from editor.Ironica.language_engine import LanguageRegistry
        except Exception:
            LanguageRegistry = None
        extensions = LanguageRegistry.get_all_extensions() if LanguageRegistry else {}
        language_details = {}
        if LanguageRegistry is not None:
            for extension, lang_id in extensions.items():
                try:
                    config = LanguageRegistry.get_config(lang_id) or {}
                    language_details[extension] = (
                        LanguageRegistry.get_display_name(lang_id),
                        _badge_color(config.get("badge_color")),
                    )
                except Exception:
                    language_details[extension] = (lang_id, _badge_color(None))

        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [
                d
                for d in dirs
                if not any(fnmatch.fnmatch(d, p) for p in ignore_patterns)
            ]

            for f in files:
                if any(fnmatch.fnmatch(f, p) for p in ignore_patterns):
                    continue

                ext = Path(f).suffix.lower()
                detail = language_details.get(ext)
                if detail is None:
                    continue
                display_name, color_hex = detail
                try:
                    size = os.path.getsize(os.path.join(root, f))
                    key = (extensions.get(ext, ""), display_name)
                    count, _old_color = stats.get(key, (0, color_hex))
                    stats[key] = (count + size, color_hex)
                    total_bytes += size
                except OSError:
                    pass

        if total_bytes == 0:
            return

        sorted_stats = sorted(stats.items(), key=lambda item: item[1][0], reverse=True)

        bar_data = []
        while self.legend_layout.count():
            child = self.legend_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for (_lang_id, display_name), (byte_count, color_hex) in sorted_stats:
            percentage = (byte_count / total_bytes) * 100
            if percentage < 0.1:
                continue

            bar_data.append((percentage, QColor(color_hex)))

            badge = LanguageBadge(display_name, percentage, color_hex)
            self.legend_layout.addWidget(badge)

        self.bar.set_data(bar_data)
