from PIL import Image
import customtkinter as ctk
import os

_ICON_CACHE = {}

_ICON_CONFIG = {
    "asm": ("assets/types/asm.png", (13, 13)),
    "bat": ("assets/types/shell.png", (15, 15)),
    "bsharp": ("assets/types/b_sharp.png", (15, 15)),
    "bin": ("assets/types/bin.png", (15, 15)),
    "c": ("assets/types/c.png", (15, 15)),
    "cmake": ("assets/types/cmake.png", (15, 15)),
    "cpp": ("assets/types/cpp.png", (15, 15)),
    "cs": ("assets/types/csharp.png", (15, 15)),
    "csharp": ("assets/types/csharp.png", (15, 15)),
    "csv": ("assets/types/csv.png", (15, 15)),
    "css": ("assets/types/css.png", (15, 15)),
    "d": ("assets/types/d.png", (15, 15)),
    "docker": ("assets/types/docker.png", (15, 15)),
    "folder": ("assets/types/folder.png", (15, 15)),
    "flutter": ("assets/types/flutter.png", (15, 15)),
    "fsharp": ("assets/types/fsharp.png", (15, 15)),
    "git": ("assets/types/git.png", (15, 15)),
    "go": ("assets/types/go.png", (15, 15)),
    "html": ("assets/types/html.png", (15, 15)),
    "ipynb": ("assets/types/ipynb.png", (15, 15)),
    "js": ("assets/types/javascript.png", (15, 15)),
    "javascript": ("assets/types/javascript.png", (15, 15)),
    "jpeg": ("assets/types/jpeg.png", (15, 15)),
    "jpg": ("assets/types/jpeg.png", (15, 15)),
    "md": ("assets/types/md.png", (15, 15)),
    "pdf": ("assets/types/pdf.png", (12, 12)),
    "pyc": ("assets/types/pyc.png", (15, 15)),
    "py": ("assets/types/python.png", (15, 15)),
    "python": ("assets/types/python.png", (15, 15)),
    "rar": ("assets/types/rar.png", (15, 15)),
    "rb": ("assets/types/ruby.png", (15, 15)),
    "rs": ("assets/types/rust.png", (15, 15)),
    "rust": ("assets/types/rust.png", (15, 15)),
    "sh": ("assets/types/shell.png", (15, 15)),
    "shell": ("assets/types/shell.png", (15, 15)),
    "svg": ("assets/types/svg.png", (15, 15)),
    "swift": ("assets/types/swift.png", (15, 15)),
    "ts": ("assets/types/typescript.png", (15, 15)),
    "typescript": ("assets/types/typescript.png", (15, 15)),
    "vb": ("assets/types/vb.png", (15, 15)),
    "vs": ("assets/types/vs.png", (15, 15)),
    "vscode": ("assets/types/vscode.png", (15, 15)),
    "default": ("assets/types/file.png", (15, 15)),
    "png": ("assets/types/jpeg.png", (15, 15)),
    "gif": ("assets/types/jpeg.png", (15, 15)),
    "ico": ("assets/types/jpeg.png", (15, 15)),
    "ps1": ("assets/types/shell.png", (15, 15)),
    "fish": ("assets/types/shell.png", (15, 15)),
}

def get_icon(name):
    if name in _ICON_CACHE:
        return _ICON_CACHE[name]
    
    config = _ICON_CONFIG.get(name, _ICON_CONFIG.get("default"))
    if config is None:
        return None
    path = config[0]
    size = config[1]
    
    if not os.path.exists(path):
        _ICON_CACHE[name] = None
        return None
    
    try:
        img = Image.open(path)
        ctk_img = ctk.CTkImage(img, img, size)
        _ICON_CACHE[name] = ctk_img
        return ctk_img
    except Exception:
        _ICON_CACHE[name] = None
        return None

def has_icon(name):
    return name in _ICON_CONFIG

ICONS = get_icon
ICONS_CONFIG = _ICON_CONFIG

def preload_icons():
    for name in _ICON_CONFIG:
        get_icon(name)