"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
Solution-marker persistence for the ``.ds`` workspace footprint.
"""

from editor import *

from editor.utils.io import load_yaml, save_json
from editor.utils.solution.paths import DS_DIR, ds_dir, is_solution, marker_path

logger = logging.getLogger(__name__)

SOLUTION_MARKER_VERSION = 1

SOLUTION_DIR = DS_DIR


def is_solution_dir(path: str) -> bool:
    """Check whether *path* carries a solution marker file."""
    return is_solution(path)


def read_solution(path: str) -> dict | None:
    """Read the solution marker for *path*."""
    marker = marker_path(path)
    if not os.path.isfile(marker):
        return None
    try:
        data = load_yaml(marker, default=None)
        return data if isinstance(data, dict) else None
    except Exception as exc:
        logger.warning("Could not read solution marker %s: %s", marker, exc)
        return None


def write_solution(
    path: str,
    name: str,
    project_type: str = "",
    manifest: str = "",
    created_at: str = "",
) -> dict:
    """Write the solution marker inside *path*."""
    if not created_at:
        created_at = str(time.time())
    payload = {
        "version": SOLUTION_MARKER_VERSION,
        "name": name,
        "project_type": project_type,
        "manifest": manifest,
        "created_at": created_at,
    }

    ds_dir_path = ds_dir(path)
    try:
        os.makedirs(ds_dir_path, exist_ok=True)
        marker = marker_path(path)
        save_json(marker, payload)
        logger.info("Solution marker written: %s", marker)
    except OSError as exc:
        logger.error("Could not write solution marker in %s: %s", path, exc)
        raise
    return payload


def ensure_solution_marker(
    path: str,
    name: str,
    project_type: str = "",
    manifest: str = "",
) -> dict:
    """Write the marker for *path* and stamp its display name best-effort."""
    payload = write_solution(
        path,
        name=name,
        project_type=project_type,
        manifest=manifest,
    )
    try:
        from editor.utils.properties.project_data_engine import ProjectDataEngine

        ProjectDataEngine(path).commit_solution_properties({"name": name})
    except Exception:
        pass
    return payload
