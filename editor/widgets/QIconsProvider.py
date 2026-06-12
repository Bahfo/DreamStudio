from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QFileInfo
from PyQt6.QtWidgets import QFileIconProvider


class DreamStudioIconProvider(QFileIconProvider):
    def icon(self, file_info: QFileInfo) -> QIcon:
        if not isinstance(file_info, QFileInfo):
            return super().icon(file_info)

        name = file_info.fileName() # Maybe needed in future
        name_lower = name.lower()
        extension = file_info.suffix().lower()

        if file_info.isDir():
            return QIcon("assets/types/folder.png")

        if name_lower in ["license", "copyright"]:
            return QIcon("assets/types/license.png")
        elif name_lower in [".gitignore", ".gitattributes"]:
            return QIcon("assets/types/git.png")

        elif extension == "bash" or extension == "sh":
            return QIcon("assets/types/bash.png")
        elif extension == "bin":
            return QIcon("assets/types/bin.png")
        elif extension == "css":
            return QIcon("assets/types/css.png")
        elif extension == "csv":
            return QIcon("assets/types/csv.png")
        elif extension == "docker":
            return QIcon("assets/types/docker.png")
        elif extension == "docx":
            return QIcon("assets/types/docx.png")
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
        elif extension == "poly":
            return QIcon("assets/types/poly.png")
        elif extension in ["pyc", "pyx", "pyz"]:
            return QIcon("assets/types/pyc.png")
        elif extension == "py":
            return QIcon("assets/types/python.png")
        elif extension == "ps1":
            return QIcon("assets/types/shell.png")
        elif extension == "svg":
            return QIcon("assets/types/svg.png")
        elif extension == "sql":
            return QIcon("assets/types/data.png")
        elif extension == "ts":
            return QIcon("assets/types/typescript.png")

        return QIcon("assets/types/file.png")
