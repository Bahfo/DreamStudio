"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Pure translation helpers converting VCS status snapshots into absolute
path color indices and theme-aware brushes for the Solution Explorer.
"""

import os
from typing import Dict

from PyQt6.QtGui import QColor

MODIFIED_KIND = "modified"
ADDED_KIND = "added"

_DARK_COLORS = {MODIFIED_KIND: QColor("#E58E3A"), ADDED_KIND: QColor("#73C991")}
_LIGHT_COLORS = {MODIFIED_KIND: QColor("#B26800"), ADDED_KIND: QColor("#2E7D32")}


def resolve_vcs_colors(bg_lightness: int) -> Dict[str, QColor]:
    """Pick readable VCS colors for the given background lightness."""
    return _LIGHT_COLORS if bg_lightness >= 128 else _DARK_COLORS


def build_status_index(repo_root: str, snapshot: Dict[str, str]) -> Dict[str, str]:
    """
    Expand a repo-relative snapshot into an absolute-path color index.

    Every ancestor directory up to the repository root inherits the most
    severe descendant status, mirroring JetBrains folder coloring: any
    modified descendant marks the whole chain orange even when other
    descendants are merely added.

    Args:
        repo_root: Absolute repository working directory.
        snapshot: Repository-relative path to ``M``/``U``/``A`` symbols.

    Returns:
        Normalized absolute path to ``modified``/``added`` kinds.
    """
    index: Dict[str, str] = {}
    root_norm = os.path.normpath(repo_root)

    for relative, status in snapshot.items():
        if status == "M":
            kind = MODIFIED_KIND
        elif status in ("U", "A"):
            kind = ADDED_KIND
        else:
            continue

        current = os.path.normpath(os.path.join(repo_root, relative))
        while True:
            if index.get(current) != MODIFIED_KIND:
                index[current] = kind
            parent = os.path.dirname(current)
            if parent == current or not parent.startswith(root_norm):
                break
            current = parent

    return index
