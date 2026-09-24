"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
"""

from editor import *
from editor.utils.resource_path import resource_path

logger = logging.getLogger(__name__)
_PROJECTS_DIR = "manifests/projects"
_REQUIRED_KEYS = (
    "project_type",
    "display_name",
    "description",
    "initialization",
)


class ManifestScanError(Exception):
    """Raised when the manifests directory cannot be located or read."""


def projects_dir() -> str:
    base = resource_path(_PROJECTS_DIR)
    if not os.path.isdir(base):
        raise ManifestScanError(f"Projects manifests directory not found: {base}")
    return base


def load_manifest(path: str) -> dict:
    import yaml

    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Manifest is not a YAML dict: {path}")
    missing = [key for key in _REQUIRED_KEYS if key not in data]
    if missing:
        raise ValueError(f"Manifest is missing required keys {missing}: {path}")
    return data


def scan_project_types() -> list[dict]:
    base = projects_dir()
    entries: list[dict] = []
    for filename in sorted(os.listdir(base)):
        if not filename.endswith((".yaml", ".yml")):
            continue
        path = os.path.join(base, filename)
        try:
            manifest = load_manifest(path)
        except Exception as exc:
            logger.warning("Skipping invalid project manifest %s: %s", path, exc)
            continue
        entries.append(
            {
                "manifest_path": path,
                "project_type": manifest.get("project_type"),
                "display_name": manifest.get("display_name", filename),
                "description": manifest.get("description", ""),
                "manifest": manifest,
            }
        )
    entries.sort(key=lambda item: str(item["display_name"]).lower())
    return entries


def find_project_type(project_type: str) -> dict | None:
    for entry in scan_project_types():
        if entry.get("project_type") == project_type:
            return entry
    return None
