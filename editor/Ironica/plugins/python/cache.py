"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.
An independent, generic caching engine for editor requests.
"""

import hashlib
from typing import Any, Dict, Optional

from .domain_models import PythonContext


class LanguageCache:
    """Least Recently Used (LRU) cache keyed by context snapshots."""

    def __init__(self, max_size: int = 128) -> None:
        self._cache: Dict[str, Any] = {}
        self._max_size = max_size
        self._keys_order: list[str] = []
        self._last_source: str = ""
        self._last_code_hash: str = ""

    def _code_hash(self, source_code: str) -> str:
        """Return cached SHA-256 for *source_code*, hashing once per buffer."""
        if source_code == self._last_source and self._last_code_hash:
            return self._last_code_hash
        code_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
        self._last_source = source_code
        self._last_code_hash = code_hash
        return code_hash

    def _generate_key(self, context: PythonContext, request_type: str) -> str:
        """Generate a unique, stable cache key from a context snapshot."""
        code_hash = self._code_hash(context.source_code)
        file_path = context.file_path or "unsaved_buffer"
        project_root = getattr(context, "project_root", None) or ""
        return f"{request_type}:{code_hash}:{context.line}:{context.column}:{file_path}:{project_root}"

    def get(self, context: PythonContext, request_type: str) -> Optional[Any]:
        """Retrieve a cached value if present, updating access history."""
        key = self._generate_key(context, request_type)
        if key in self._cache:
            self._keys_order.remove(key)
            self._keys_order.append(key)
            return self._cache[key]
        return None

    def set(self, context: PythonContext, request_type: str, value: Any) -> None:
        """Store a value, evicting oldest keys when full."""
        if self._max_size <= 0:
            return
        key = self._generate_key(context, request_type)
        if key in self._cache:
            return

        if len(self._cache) >= self._max_size:
            oldest_key = self._keys_order.pop(0)
            self._cache.pop(oldest_key, None)

        self._cache[key] = value
        self._keys_order.append(key)

    def clear(self) -> None:
        """Clear all cached calculations and the memoized source hash."""
        self._cache.clear()
        self._keys_order.clear()
        self._last_source = ""
        self._last_code_hash = ""
