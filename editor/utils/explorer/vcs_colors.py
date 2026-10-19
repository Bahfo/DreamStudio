"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Pure translation helpers converting VCS status snapshots into absolute path color indices and theme-aware brushes for the Solution Explorer.
"""

from editor import *

MODIFIED_KIND = "modified"
ADDED_KIND = "added"

_DARK_COLORS = {MODIFIED_KIND: QColor("#E58E3A"), ADDED_KIND: QColor("#73C991")}
_LIGHT_COLORS = {MODIFIED_KIND: QColor("#B26800"), ADDED_KIND: QColor("#2E7D32")}


def resolve_vcs_colors(bg_lightness: int) -> Dict[str, QColor]:
    """Pick readable VCS colors for the given background lightness."""
    return _LIGHT_COLORS if bg_lightness >= 128 else _DARK_COLORS


def build_status_index(repo_root: str, snapshot: Dict[str, str]) -> Dict[str, str]:
    """Expand a repo-relative snapshot into an absolute-path color index."""
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
        root_norm_case = os.path.normcase(root_norm)
        cur_case = os.path.normcase(current)
        if not (cur_case == root_norm_case or cur_case.startswith(root_norm_case + os.sep)):
            continue
        while True:
            if index.get(current) != MODIFIED_KIND:
                index[current] = kind
            parent = os.path.dirname(current)
            if parent == current:
                break
            parent_case = os.path.normcase(parent)
            if not (parent_case == root_norm_case or parent_case.startswith(root_norm_case + os.sep)):
                break
            current = parent

    return index
