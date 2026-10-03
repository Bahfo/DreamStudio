"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""

from editor import *

from editor.utils.solution.paths import DS_DIR, SOLUTION_FILE, ds_dir

logger = logging.getLogger(__name__)

SOLUTION_MARKER_VERSION = 1

SOLUTION_DIR = DS_DIR


def _marker_path(path: str) -> str:
    from editor.utils.solution.paths import marker_path

    return marker_path(path)


def is_solution_dir(path: str) -> bool:
    return os.path.isfile(_marker_path(path))


def read_solution(path: str) -> dict | None:
    from editor.utils.io import load_yaml

    marker = _marker_path(path)
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
    if not created_at:
        created_at = str(time.time())
    payload = {
        "version": SOLUTION_MARKER_VERSION,
        "name": name,
        "project_type": project_type,
        "manifest": manifest,
        "created_at": created_at,
    }

    from editor.utils.io import save_json

    ds_dir_path = ds_dir(path)
    try:
        os.makedirs(ds_dir_path, exist_ok=True)
        marker = _marker_path(path)
        save_json(marker, payload)
        logger.info("Solution marker written: %s", marker)
    except OSError as exc:
        logger.error("Could not write solution marker in %s: %s", path, exc)
        raise
    return payload
