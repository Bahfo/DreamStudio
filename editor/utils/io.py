"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Atomic JSON/YAML persistence helpers shared by all config services.
"""

import json
import logging
import os
import shutil
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _atomic_write_text(path: str, content: str) -> None:
    """Write *content* atomically via unique temp file plus rename."""
    import tempfile as _tempfile

    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)
    fd, tmp = _tempfile.mkstemp(dir=directory or ".", prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            try:
                handle.flush()
                os.fsync(handle.fileno())
            except Exception:
                pass
        os.replace(tmp, path)
        try:
            dir_fd = os.open(directory or ".", os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception:
            pass
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except Exception:
            pass


def backup_corrupt_file(path: str) -> str | None:
    """Copy corrupt config aside with timestamp; return backup path."""
    try:
        if os.path.isfile(path):
            import time as _time

            stamp = _time.strftime("%Y%m%d-%H%M%S") + f"-{_time.time_ns() % 1000000000}"
            backup = f"{path}.corrupt.{stamp}.bak"
            shutil.copyfile(path, backup)
            logger.warning("Corrupt config backed up to %s", backup)
            return backup
    except Exception as exc:
        logger.warning("Could not back up corrupt config: %s", exc)
    return None


def load_json(
    path: str,
    default: Any = None,
    validate: Callable[[Any], Any] | None = None,
) -> Any:
    """Load JSON file with backup and default fallback.

    Args:
        path: Source file path.
        default: Value returned when missing or corrupt.
        validate: Optional transform applied to parsed content.

    Returns:
        Parsed (and validated) content or *default*.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logger.warning("Config load failed %s: %s", path, exc)
        if os.path.isfile(path):
            backup_corrupt_file(path)
        return default
    if validate is not None:
        try:
            return validate(data)
        except Exception as exc:
            logger.warning("Config validation failed %s: %s", path, exc)
            return default
    return data


def save_json(path: str, data: Any, indent: int = 4) -> None:
    """Persist *data* as pretty JSON atomically."""
    _atomic_write_text(path, json.dumps(data, indent=indent))


def load_yaml(path: str, default: Any = None) -> Any:
    """Load YAML file with JSON fallback and default on failure."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except OSError as exc:
        logger.warning("Config load failed %s: %s", path, exc)
        return default
    try:
        import yaml as _yaml

        data = _yaml.safe_load(text)
        if data is not None:
            return data
    except Exception:
        pass
    try:
        return json.loads(text)
    except Exception as exc:
        logger.warning("Config parse failed %s: %s", path, exc)
        backup_corrupt_file(path)
        return default


def save_yaml(path: str, data: Any) -> None:
    """Persist *data* as YAML atomically."""
    import yaml as _yaml

    _atomic_write_text(path, _yaml.safe_dump(data, default_flow_style=False))
