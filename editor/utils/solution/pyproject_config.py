"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

pyproject.toml configuration manager for DreamStudio projects.

Stores tool configuration (ruff, pyright) inside the ``.ds/`` folder
so each project can customize analysis exclusions without polluting the
repository root.
"""

from __future__ import annotations

import logging
import os

from editor.utils.solution.paths import DEFAULT_EXCLUDES

logger = logging.getLogger(__name__)

_PYPROJECT_TEMPLATE = """\
# DreamStudio per-project analysis configuration.
# Edit the exclude lists below to control which directories are skipped.

[tool.ruff]
exclude = {ruff_excludes}

[tool.pyright]
exclude = {pyright_excludes}
"""


def _pyproject_path(root: str) -> str:
    """Return the path to ``.ds/pyproject.toml`` for *root*."""
    return os.path.join(root, ".ds", "pyproject.toml")


def _default_excludes_list() -> list[str]:
    """Return the default exclusion list derived from ``DEFAULT_EXCLUDES``."""
    return sorted(DEFAULT_EXCLUDES)


def ensure_pyproject(root: str) -> str:
    """Create ``.ds/pyproject.toml`` with defaults if it doesn't exist.

    Returns the path to the config file.
    """
    path = _pyproject_path(root)
    if os.path.isfile(path):
        return path
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        excludes = _default_excludes_list()
        # Format as TOML array
        ruff_arr = "[" + ", ".join(f'"{e}"' for e in excludes) + "]"
        pyright_arr = "[" + ", ".join(f'"{e}"' for e in excludes) + "]"
        content = _PYPROJECT_TEMPLATE.format(
            ruff_excludes=ruff_arr,
            pyright_excludes=pyright_arr,
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as exc:
        logger.warning("Could not create pyproject.toml: %s", exc)
    return path


def load_pyproject_config(root: str) -> dict:
    """Read ``.ds/pyproject.toml`` and return a parsed dict.

    Returns an empty dict if the file doesn't exist or can't be parsed.
    """
    path = _pyproject_path(root)
    if not os.path.isfile(path):
        return {}
    try:
        # Try tomllib (Python 3.11+) or tomli
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                return {}
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as exc:
        logger.warning("Could not parse pyproject.toml: %s", exc)
        return {}


def get_ruff_excludes(root: str) -> list[str]:
    """Return the ruff exclusion list from ``.ds/pyproject.toml``."""
    config = load_pyproject_config(root)
    return (
        config.get("tool", {}).get("ruff", {}).get("exclude", _default_excludes_list())
    )


def get_pyright_excludes(root: str) -> list[str]:
    """Return the pyright exclusion list from ``.ds/pyproject.toml``."""
    config = load_pyproject_config(root)
    return (
        config.get("tool", {})
        .get("pyright", {})
        .get("exclude", _default_excludes_list())
    )


def ensure_and_load(root: str) -> dict:
    """Ensure the config exists and return it."""
    ensure_pyproject(root)
    return load_pyproject_config(root)
