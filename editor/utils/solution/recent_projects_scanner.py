"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Recent-solutions persistence built on ``~/.dreamstudio/settings``.

Stores a capped, deduplicated list of opened/created solution paths so the
IDE can remember and re-offer them on every launch.
"""

from editor import *

logger = logging.getLogger(__name__)

_RECENT_KEY = "solutions"
_RECENT_LIST_KEY = "recent"
MAX_RECENT = 10


def user_settings_path() -> str:
    """Return the absolute path of the user-settings JSON file."""
    return os.path.join(Path.home(), ".dreamstudio", "settings", "user_settings.json")


def _read_settings() -> dict:
    try:
        with open(user_settings_path(), "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_settings(data: dict) -> None:
    path = user_settings_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=4)
    except OSError as exc:
        logger.error("Could not persist user settings: %s", exc)


def list_recent() -> list[dict]:
    """Return the recent-solutions entries, newest first.

    Returns:
        Up to ``MAX_RECENT`` dict entries with ``path``, ``name``,
        ``project_type`` and ``last_opened`` keys.
    """
    data = _read_settings()
    entries = data.get(_RECENT_KEY, {}).get(_RECENT_LIST_KEY, [])
    if not isinstance(entries, list):
        return []
    return [entry for entry in entries if isinstance(entry, dict)]


def add_or_update(path: str, name: str = "", project_type: str = "") -> None:
    """Record *path* as the most-recent solution, deduplicating by path.

    Args:
        path: Absolute solution path.
        name: Solution display name (kept when already known).
        project_type: Project-type identifier (kept when already known).
    """
    path = os.path.abspath(path)
    if not os.path.isdir(path):
        return
    if not name:
        name = os.path.basename(path) or path

    data = _read_settings()
    section = data.setdefault(_RECENT_KEY, {})
    entries = section.setdefault(_RECENT_LIST_KEY, [])
    if not isinstance(entries, list):
        entries = []
        section[_RECENT_LIST_KEY] = entries

    existing = next((e for e in entries if e.get("path") == path), None)
    if existing:
        entries.remove(existing)
        name = name or existing.get("name", name)
        project_type = project_type or existing.get("project_type", project_type)

    entries.insert(
        0,
        {
            "path": path,
            "name": name,
            "project_type": project_type,
            "last_opened": str(time.time()),
        },
    )
    del entries[MAX_RECENT:]
    _write_settings(data)


def remove(path: str) -> None:
    """Remove *path* from the recent-solutions list.

    Args:
        path: Absolute solution path to forget.
    """
    path = os.path.abspath(path)
    data = _read_settings()
    section = data.setdefault(_RECENT_KEY, {})
    entries = section.get(_RECENT_LIST_KEY, [])
    if not isinstance(entries, list):
        return
    entries[:] = [e for e in entries if e.get("path") != path]
    _write_settings(data)


def last_opened() -> dict | None:
    """Return the most recent entry, or ``None`` when the list is empty."""
    entries = list_recent()
    return entries[0] if entries else None
