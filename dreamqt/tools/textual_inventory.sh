# (C) COPYRIGHT 2026 Gizmo MicroSystems - All Rights Reserved.
# File is used to get actual DreamStudio's usage of Qt. 

rg -n --hidden \
  -g '*.py' \
  -g '*.ui' \
  -g '*.qrc' \
  -g '*.toml' \
  -g '!dreamqt/**' \
  -g '!.git/**' \
  -g '!venv/**' \
  -g '!.venv/**' \
  -g '!build/**' \
  -g '!dist/**' \
  '(PyQt6|PyQt5|PySide6|QScintilla|Qsci)' \
  . > dreamqt/baseline/pyqt-import-inventory.txt