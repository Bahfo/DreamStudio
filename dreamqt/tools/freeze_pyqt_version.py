# (C) COPYRIGHT 2026 Gizmo MicroSystems - All Rights Reserved.
# File is used to get exact version of PyQt modules and freeze them.

import importlib.metadata as metadata
import json
import platform
import sys
from pathlib import Path

packages = {}

for dist in metadata.distributions():
    name = dist.metadata.get("Name", "")
    normalized = name.lower().replace("_", "-")

    if any(token in normalized for token in ("pyqt", "qt", "sip", "scintilla")):
        packages[name] = dist.version

qt_runtime = {}

try:
    from PyQt6 import QtCore

    for attribute in (
        "PYQT_VERSION_STR",
        "QT_VERSION_STR",
    ):
        qt_runtime[attribute] = getattr(QtCore, attribute, None)

    qt_runtime["runtime_qt_version"] = QtCore.qVersion()
except Exception as exc:
    qt_runtime["import_error"] = repr(exc)

environment = {
    "python": sys.version,
    "python_executable": sys.executable,
    "python_prefix": sys.prefix,
    "platform": platform.platform(),
    "architecture": platform.machine(),
    "qt_runtime": qt_runtime,
    "relevant_packages": packages,
}

output = Path("dreamqt/baseline/environment.json")
output.parent.mkdir(parents=True, exist_ok=True)

output.write_text(
    json.dumps(environment, indent=4),
    encoding="utf-8",
)

print(json.dumps(environment, indent=4))
print(f"\nSaved: {output}")
