"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

An independent, generic caching engine for editor requests.
Tracks, stores, and invalidates lookups based on immutable contexts.
"""

import hashlib
from typing import Dict, Any, Optional
from .domain_models import PythonContext


class LanguageCache:
    """
    An independent Least Recently Used (LRU) style cache.
    Ensures language providers remain entirely stateless.
    """

    def __init__(self, max_size: int = 128) -> None:
        self._cache: Dict[str, Any] = {}
        self._max_size = max_size
        self._keys_order: list[str] = []

    def _generate_key(self, context: PythonContext, request_type: str) -> str:
        """Generates a unique, stable cache key from a context snapshot."""
        # Hash the code string to avoid giant key storage strings
        code_hash = hashlib.sha256(context.source_code.encode("utf-8")).hexdigest()
        file_path = context.file_path or "unsaved_buffer"
        return f"{request_type}:{code_hash}:{context.line}:{context.column}:{file_path}"

    def get(self, context: PythonContext, request_type: str) -> Optional[Any]:
        """Retrieves a cached value if present, updating its access history."""
        key = self._generate_key(context, request_type)
        if key in self._cache:
            # Move key to the end to keep it fresh
            self._keys_order.remove(key)
            self._keys_order.append(key)
            return self._cache[key]
        return None

    def set(self, context: PythonContext, request_type: str, value: Any) -> None:
        """Stores a value associated with a context, evicting oldest keys if full."""
        key = self._generate_key(context, request_type)
        if key in self._cache:
            return

        # Handle eviction limit
        if len(self._cache) >= self._max_size:
            oldest_key = self._keys_order.pop(0)
            self._cache.pop(oldest_key, None)

        self._cache[key] = value
        self._keys_order.append(key)

    def clear(self) -> None:
        """Clears all cached calculations."""
        self._cache.clear()
        self._keys_order.clear()
