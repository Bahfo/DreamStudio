# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os

# Resolve project root relative to this spec file itself
# PyInstaller provides SPEC when executing the spec; fallback to __file__ for manual runs
try:
    _spec_path = Path(SPEC).resolve()  # type: ignore[name-defined]
except NameError:
    try:
        _spec_path = Path(__file__).resolve()
    except NameError:
        _spec_path = Path.cwd() / "packaging" / "DreamStudio.spec"
SPEC_DIR = _spec_path.parent
PROJECT_ROOT = SPEC_DIR.parent
SPEC = str(_spec_path)
SPEC_DIR_ALIAS = SPEC_DIR
# PROJECT_ROOT is the authoritative base

block_cipher = None

a = Analysis(
    [str(PROJECT_ROOT / "startup.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[
        (str(PROJECT_ROOT / "native" / "build" / "lib" / "libinspector.so"), "native/build/lib"),
        (str(PROJECT_ROOT / "hex-editor" / "build" / "libinspector.so"), "hex-editor/build"),
        (str(PROJECT_ROOT / "hex-editor" / "build" / "libbinary_inspector.so"), "hex-editor/build"),
        # Extra copy for binding.py fallback this.parent / libinspector.so
        (str(PROJECT_ROOT / "native" / "build" / "lib" / "libinspector.so"), "editor/Ironica/inspector"),
    ],
    datas=[
        (str(PROJECT_ROOT / "assets"), "assets"),
        (str(PROJECT_ROOT / "editor" / "qss"), "editor/qss"),
        (str(PROJECT_ROOT / "editor" / "base" / "json"), "editor/base/json"),
        (str(PROJECT_ROOT / "editor" / "Ironica" / "keywords"), "editor/Ironica/keywords"),
        (str(PROJECT_ROOT / "editor" / "Ironica" / "snippets"), "editor/Ironica/snippets"),
        (str(PROJECT_ROOT / "editor" / "Ironica" / "themes"), "editor/Ironica/themes"),
        (str(PROJECT_ROOT / "fonts"), "fonts"),
        (str(PROJECT_ROOT / "icon_src"), "icon_src"),
        (str(PROJECT_ROOT / "manifests"), "manifests"),
        (str(PROJECT_ROOT / "editor" / "utils" / "tools" / "json"), "editor/utils/tools/json"),
        # Ensure analysis_server.py is available as data/script for subprocess
        (str(PROJECT_ROOT / "editor" / "Ironica" / "analysis_server.py"), "editor/Ironica"),
        # Ensure plugins discovery jsons are not stripped
        (str(PROJECT_ROOT / "editor" / "Ironica" / "plugins"), "editor/Ironica/plugins"),
    ],
    hiddenimports=[
        "editor.utils.notifications.notification_manager",
        "editor.Ironica.plugins.registration",
        "editor.Ironica.plugins.python.provider",
        "editor.Ironica.analysis_bridge",
        "editor.Ironica.analysis_server",
        "editor.Ironica.analysis_worker",
        "editor.Ironica.language_engine",
        "jedi",
        "parso",
        "pyte",
        "wcwidth",
        "psutil",
        "yaml",
        "git",
        "pyqtgraph",
        "PyQt6.sip",
        "PyQt6.Qsci",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PySide2", "PySide6", "PyQt5.sip"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DreamStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ------------------------------------------------------------------
# Analysis Server (standalone subprocess executable)
# ------------------------------------------------------------------
a_server = Analysis(
    [str(PROJECT_ROOT / "editor" / "Ironica" / "analysis_server_entry.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "editor.Ironica.analysis_server",
        "editor.Ironica.language_engine",
        "editor.Ironica.retheme",
        "editor.Ironica.plugins.python.semantic_highlights",
        "editor.Ironica.plugins.python.folding",
        "jedi",
        "parso",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "PyQt5", "PySide2", "PySide6", "PyQt5.sip"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz_server = PYZ(a_server.pure, a_server.zipped_data, cipher=block_cipher)

exe_server = EXE(
    pyz_server,
    a_server.scripts,
    [],
    exclude_binaries=True,
    name="DreamStudioAnalysisServer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    exe_server,
    a.binaries,
    a.zipfiles,
    a.datas,
    a_server.binaries,
    a_server.zipfiles,
    a_server.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="DreamStudio",
)
