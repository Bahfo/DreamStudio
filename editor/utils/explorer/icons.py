from editor import *
from editor.utils.resource_path import resource_path


class DreamStudioIconProvider(QFileIconProvider):
    _EXT_ICON = {
        "bash": "bash.png",
        "bat": "bat.png",
        "bin": "bin.png",
        "bsharp": "bsharp.png",
        "c": "c.png",
        "css": "css.png",
        "csv": "csv.png",
        "d": "dlang.png",
        "docker": "docker.png",
        "docx": "docx.png",
        "html": "html.png",
        "h": "h.png",
        "ipynb": "ipynb.png",
        "js": "javascript.png",
        "json": "json.png",
        "png": "jpeg.png",
        "jpeg": "jpeg.png",
        "apng": "jpeg.png",
        "avif": "jpeg.png",
        "gif": "jpeg.png",
        "webp": "jpeg.png",
        "md": "md.png",
        "pdf": "pdf.png",
        "poly": "poly.png",
        "ps1": "powershell.png",
        "ps": "powershell.png",
        "pyc": "pyc.png",
        "pyx": "pyc.png",
        "pyz": "pyc.png",
        "py": "python.png",
        "sh": "shell.png",
        "svg": "svg.png",
        "sql": "data.png",
        "ts": "typescript.png",
        "yaml": "yaml.png",
    }

    _NAME_ICON = {
        "license": "license.png",
        "copyright": "license.png",
        ".gitignore": "git.png",
        ".gitattributes": "git.png",
        "Makefile": "make.png",
        "CMakelists": "make.png",
        "Dockerfile": "docker.png",
        ".dockerignore": "docker.png",
    }

    _FOLDER_NAME_ICON = {
        "windows": "windows.png",
        "win32": "windows.png",
        "win": "windows.png",
        "linux": "linux.png",
        "test": "test.png",
        "tests": "test.png",
        "config": "config.png",
        "configs": "config.png",
        "python": "pyfolder.png",
        "__pycache__": "pyfolder.png",
        "assets": "assets.png",
        "asset": "assets.png",
        "libs": "libs.png",
        "lib": "libs.png",
    }

    def icon(self, file_info: QFileInfo) -> QIcon:
        if not isinstance(file_info, QFileInfo):
            return super().icon(file_info)

        if file_info.isDir():
            folder_icon = self._FOLDER_NAME_ICON.get(file_info.fileName().lower())
            if folder_icon:
                candidate = resource_path(f"assets/types/{folder_icon}")
                if os.path.exists(candidate):
                    return QIcon(candidate)
            return QIcon(resource_path("assets/types/folder.png"))

        name_lower = file_info.fileName().lower()
        if name_lower in self._NAME_ICON:
            return QIcon(resource_path(f"assets/types/{self._NAME_ICON[name_lower]}"))

        ext = file_info.suffix().lower()
        icon_file = self._EXT_ICON.get(ext)
        if icon_file:
            return QIcon(resource_path(f"assets/types/{icon_file}"))

        return QIcon(resource_path("assets/types/file.png"))
