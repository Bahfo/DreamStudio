from PIL import Image, ImageTk
import customtkinter as ctk

_PIL_CACHE = {}


def _load_pil(path):
    if path is None:
        return None
    img = _PIL_CACHE.get(path)
    if img is None:
        img = Image.open(path).convert("RGBA")
        _PIL_CACHE[path] = img
    return img


class AppIcons:
    _tk_cache = {}

    @classmethod
    def padded_icon(cls, path, size=(16, 16), padding=8):
        key = (path, size, padding)
        if key in cls._tk_cache:
            return cls._tk_cache[key]

        base = _load_pil(path)
        icon = base.resize(size, Image.LANCZOS)

        canvas = Image.new(
            "RGBA",
            (size[0] + padding, size[1]),
            (0, 0, 0, 0),
        )
        canvas.paste(icon, (0, 0), icon)

        tk_img = ImageTk.PhotoImage(canvas)
        cls._tk_cache[key] = tk_img
        return tk_img


_CTK_CACHE = {}


def load_ctk_icon(path, size, dark_path=None):
    key = (path, size, dark_path)
    if key in _CTK_CACHE:
        return _CTK_CACHE[key]

    light = _load_pil(path)
    dark = _load_pil(dark_path) if dark_path else None

    img = ctk.CTkImage(
        light_image=light,
        dark_image=dark,
        size=size,
    )
    _CTK_CACHE[key] = img
    return img
