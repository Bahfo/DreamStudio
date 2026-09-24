"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Solution marker management: read/write ``.ds/solution.yaml`` so a solution
folder can be recognized and typed on later launches.
"""

from editor import *

logger = logging.getLogger(__name__)

SOLUTION_DIR = ".ds"
SOLUTION_FILE = "solution.yaml"
SOLUTION_MARKER_VERSION = 1


def _marker_path(path: str) -> str:
    return os.path.join(path, SOLUTION_DIR, SOLUTION_FILE)


def is_solution_dir(path: str) -> bool:
    """Return ``True`` when *path* carries a solution marker file.

    Args:
        path: Candidate solution folder path.
    """
    return os.path.isfile(_marker_path(path))


def read_solution(path: str) -> dict | None:
    """Read the solution marker of *path*, or ``None`` when absent.

    Args:
        path: Solution folder path.
    """
    marker = _marker_path(path)
    if not os.path.isfile(marker):
        return None
    try:
        with open(marker, "r", encoding="utf-8") as fh:
            data = json.load(fh)
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
    """Write a solution marker into *path* and return the stored data.

    Args:
        path: Solution folder path (created when missing).
        name: Display name of the solution.
        project_type: Machine-readable project type identifier.
        manifest: Relative manifest path used to scaffold the project.
        created_at: ISO timestamp; defaults to now when empty.

    Returns:
        The marker dict that was persisted.
    """
    if not created_at:
        created_at = str(time.time())
    payload = {
        "version": SOLUTION_MARKER_VERSION,
        "name": name,
        "project_type": project_type,
        "manifest": manifest,
        "created_at": created_at,
    }

    ds_dir = os.path.join(path, SOLUTION_DIR)
    try:
        os.makedirs(ds_dir, exist_ok=True)
        marker = _marker_path(path)
        with open(marker, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=4)
        logger.info("Solution marker written: %s", marker)
    except OSError as exc:
        logger.error("Could not write solution marker in %s: %s", path, exc)
        raise
    return payload
