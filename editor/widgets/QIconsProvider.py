from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QFileInfo
from PyQt6.QtWidgets import QFileIconProvider


class DreamStudioIconProvider(QFileIconProvider):
    def icon(self, file_info: QFileInfo) -> QIcon:
        if file_info.isDir():
            return QIcon("assets/types/folder.png")

        extension = file_info.suffix().lower()
        if extension == "py":
            return QIcon("assets/types/python.png")
        elif extension == "asm":
            return QIcon("assets/types/asm.png")
        elif extension == "bin":
            return QIcon("assets/types/bin.png")
        elif extension == "bsharp":
            return QIcon("assets/types/b_sharp.png")
        elif extension == "c":
            return QIcon("assets/types/c.png")
        elif extension == "cmake":
            return QIcon("assets/types/cmake.png")
        elif extension == "coffeescript":
            return QIcon("assets/types/coffeescript.png")
        elif extension == "cpp":
            return QIcon("assets/types/cpp.png")
        elif extension == "csharp":
            return QIcon("assets/types/csharp.png")
        elif extension == "css":
            return QIcon("assets/types/css.png")
        elif extension == "csv":
            return QIcon("assets/types/csv.png")
        elif extension == "d":
            return QIcon("assets/types/d.png")
        elif extension == "dart":
            return QIcon("assets/types/dart.png")
        elif extension == "docker":
            return QIcon("assets/types/docker.png")
        elif extension == "flutter":
            return QIcon("assets/types/flutter.png")
        elif extension == "fsharp":
            return QIcon("assets/types/fsharp.png")
        elif extension == "git":
            return QIcon("assets/types/git.png")
        elif extension == "git":
            return QIcon("assets/types/git.png")
        elif extension == "go":
            return QIcon("assets/types/go.png")
        elif extension == "h" or extension == "hpp":
            return QIcon("assets/types/h.png")
        elif extension == "html":
            return QIcon("assets/types/html.png")
        elif extension == "ipynb":
            return QIcon("assets/types/ipynb.png")
        elif extension == "js":
            return QIcon("assets/types/javascript.png")
        elif extension in ["png", "jpeg", "apng", "avif", "gif", "webp"]:
            return QIcon("assets/types/jpeg.png")
        elif extension == "lua":
            return QIcon("assets/types/lua.png")
        elif extension == "md":
            return QIcon("assets/types/md.png")
        elif extension == "pdf":
            return QIcon("assets/types/pdf.png")
        elif extension in ["pyc", "pyx", "pyz"]:
            return QIcon("assets/types/pyc.png")
        elif extension == "python":
            return QIcon("assets/types/py.png")
        elif extension in ["rar", "zip", "tar", "gz"]:
            return QIcon("assets/types/rar.png")
        elif extension == "rb":
            return QIcon("assets/types/ruby.png")
        elif extension == "rs":
            return QIcon("assets/types/rust.png")
        elif extension == "ps1" or extension == "bash":
            return QIcon("assets/types/shell.png")
        elif extension == "svg":
            return QIcon("assets/types/svg.png")
        elif extension == "swift":
            return QIcon("assets/types/swift.png")
        elif extension == "ts":
            return QIcon("assets/types/typescript.png")
        elif extension == "vb":
            return QIcon("assets/types/vb.png")
        elif extension == "vs":
            return QIcon("assets/types/vs.png")
        elif extension == "vscode":
            return QIcon("assets/types/vscode.png")

        return QIcon("assets/types/file.png")
