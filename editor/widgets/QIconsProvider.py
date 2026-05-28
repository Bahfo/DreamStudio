from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QFileInfo
from PyQt6.QtWidgets import QFileIconProvider


class DreamStudioIconProvider(QFileIconProvider):
    def icon(self, file_info: QFileInfo) -> QIcon:
        if not isinstance(file_info, QFileInfo):
            return super().icon(file_info)

        name = file_info.fileName()
        name_lower = name.lower()
        extension = file_info.suffix().lower()

        if file_info.isDir():
            if name_lower in [".vscode", "vscode"]:
                return QIcon("assets/types/vscode.png")
            elif name_lower in [".vs", "vs"]:
                return QIcon("assets/types/vs.png")
            elif name_lower in ["venv", ".venv"]:
                return QIcon("assets/types/venv.png")
            elif name_lower in ["ai", "agents", ".ai", ".agents"]:
                return QIcon("assets/types/ai.png")
            elif name_lower in [
                "pytest_cache",
                ".pytest_cache",
                "test",
                ".test",
                "tests",
                ".tests",
            ]:
                return QIcon("assets/types/tests.png")
            elif name_lower == "assets":
                return QIcon("assets/types/assets.png")
            elif name_lower in ["build", ".build", "bin", ".bin"]:
                return QIcon("assets/types/build.png")
            elif name_lower in ["containers", "container", "docker"]:
                return QIcon("assets/types/docker_dir.png")
            elif name_lower == "dso" or name_lower == ".dso":
                return QIcon("assets/types/dream.png")
            elif name_lower == "git" or name_lower == ".git":
                return QIcon("assets/types/git_init.png")
            elif name_lower == "include":
                return QIcon("assets/types/include.png")
            elif name_lower == "src" or name_lower == "editor":
                return QIcon("assets/types/src.png")
            return QIcon("assets/types/folder.png")

        if name_lower in ["license", "copyright"]:
            return QIcon("assets/types/license.png")
        elif name_lower in [".gitignore", ".gitattributes"]:
            return QIcon("assets/types/git.png")
        elif name_lower == "vs":
            return QIcon("assets/types/vs.png")
        elif name_lower == "vscode":
            return QIcon("assets/types/vscode.png")

        elif extension == "bash" or extension == "sh":
            return QIcon("assets/types/bash.png")
        elif extension == "bin":
            return QIcon("assets/types/bin.png")
        elif extension == "c":
            return QIcon("assets/types/c.png")
        elif extension == "cmake":
            return QIcon("assets/types/cmake.png")
        elif extension == "cpp":
            return QIcon("assets/types/cpp.png")
        elif extension == "css":
            return QIcon("assets/types/css.png")
        elif extension == "csv":
            return QIcon("assets/types/csv.png")
        elif extension == "d":
            return QIcon("assets/types/d.png")
        elif extension == "docker":
            return QIcon("assets/types/docker.png")
        elif extension == "docx":
            QIcon("assets/types/docx.png")
        elif extension == "h" or extension == "hpp":
            return QIcon("assets/types/h.png")
        elif extension == "html":
            return QIcon("assets/types/html.png")
        elif extension == "ipynb":
            return QIcon("assets/types/ipynb.png")
        elif extension == "js":
            return QIcon("assets/types/javascript.png")
        elif extension == "json":
            return QIcon("assets/types/json.png")
        elif extension in ["png", "jpeg", "apng", "avif", "gif", "webp"]:
            return QIcon("assets/types/jpeg.png")
        elif extension == "md":
            return QIcon("assets/types/md.png")
        elif extension == "pdf":
            return QIcon("assets/types/pdf.png")
        elif extension in ["pyc", "pyx", "pyz"]:
            return QIcon("assets/types/pyc.png")
        elif extension == "py":
            return QIcon("assets/types/python.png")
        elif extension == "ps1":
            return QIcon("assets/types/shell.png")
        elif extension == "svg":
            return QIcon("assets/types/svg.png")
        elif extension == "sql":
            QIcon("assets/types/data.png")
        elif extension == "ts":
            return QIcon("assets/types/typescript.png")
        elif extension == "txt":
            return QIcon("assets/types/txt.png")

        return QIcon("assets/types/file.png")
