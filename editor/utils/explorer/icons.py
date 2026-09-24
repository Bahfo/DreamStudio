from editor import *
from editor.utils.resource_path import resource_path


class DreamStudioIconProvider(QFileIconProvider):
    _EXT_ICON = {
        "bash": "bash.png",
        "sh": "bash.png",
        "bat": "bat.png",
        "bin": "bin.png",
        "bsharp": "bsharp.png",
        "c": "c.png",
        "css": "css.png",
        "csv": "csv.png",
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
        "pyc": "pyc.png",
        "pyx": "pyc.png",
        "pyz": "pyc.png",
        "py": "python.png",
        "ps1": "shell.png",
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

    def icon(self, file_info: QFileInfo) -> QIcon:
        if not isinstance(file_info, QFileInfo):
            return super().icon(file_info)

        if file_info.isDir():
            return QIcon(resource_path("assets/types/folder.png"))

        name_lower = file_info.fileName().lower()
        if name_lower in self._NAME_ICON:
            return QIcon(resource_path(f"assets/types/{self._NAME_ICON[name_lower]}"))

        ext = file_info.suffix().lower()
        icon_file = self._EXT_ICON.get(ext)
        if icon_file:
            return QIcon(resource_path(f"assets/types/{icon_file}"))

        return QIcon(resource_path("assets/types/file.png"))
