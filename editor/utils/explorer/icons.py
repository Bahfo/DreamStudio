from editor import *
from editor.utils.resource_path import resource_path


class DreamStudioIconProvider(QFileIconProvider):
    """Provides file, name-based, and folder icons for the explorer tree.

    Attributes:
        _EXT_ICON: Mapping of lowercase file extension to icon file name.
        _NAME_ICON: Mapping of lowercase full file name to icon file name.
        _FOLDER_NAME_ICON: Mapping of lowercase folder name to icon file name.
    """
    _EXT_ICON = {
        "bash": "bash.png",
        "bat": "bat.png",
        "bin": "bin.png",
        "bsharp": "bsharp.png",
        "c": "c.png",
        "cpp": "cplusplus.png",
        "cmake": "make.png",
        "css": "css.png",
        "csv": "csv.png",
        "d": "dlang.png",
        "docker": "docker.png",
        "docx": "docx.png",
        "html": "html.png",
        "h": "h.png",
        "hpp": "hplusplus.png",
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
        "makefile": "make.png",
        "cmakelists": "make.png",
        "cmakelists.txt": "make.png",
        "dockerfile": "docker.png",
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
        """Resolves the icon for a file or folder.

        Args:
            file_info: File metadata provided by the file system model.

        Returns:
            Matching ``QIcon`` or the generic file/folder fallback.
        """
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
        icon_file = self._NAME_ICON.get(name_lower)
        if icon_file is None:
            # NOTE: catches `CMakeLists.txt` (stem `cmakelists`) and variants
            # such as `Makefile.am` or `Dockerfile.dev`.
            try:
                stem_lower = file_info.completeBaseName().lower()
            except Exception:
                stem_lower = ""
            if stem_lower:
                icon_file = self._NAME_ICON.get(stem_lower)
        if icon_file:
            candidate = resource_path(f"assets/types/{icon_file}")
            if os.path.exists(candidate):
                return QIcon(candidate)

        ext = file_info.suffix().lower()
        icon_file = self._EXT_ICON.get(ext)
        if icon_file:
            return QIcon(resource_path(f"assets/types/{icon_file}"))

        return QIcon(resource_path("assets/types/file.png"))
