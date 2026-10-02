"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

An independent, generic caching engine for editor requests.
Tracks, stores, and invalidates lookups based on immutable contexts.
"""

from editor import *
from .domain_models import PythonContext


class LanguageCache:
    """Least Recently Used (LRU) cache keyed by context snapshots.

    Attributes:
        _cache: Mapping of generated keys to cached values.
        _max_size: Maximum entries before oldest-first eviction.
    """

    def __init__(self, max_size: int = 128) -> None:
        self._cache: Dict[str, Any] = {}
        self._max_size = max_size
        self._keys_order: list[str] = []
        self._last_source: str = ""
        self._last_code_hash: str = ""

    def _code_hash(self, source_code: str) -> str:
        """Return cached SHA-256 for *source_code*, hashing once per buffer.

        Args:
            source_code: Full source text to hash.

        Returns:
            Hex digest, reused when the same buffer object or equal
            text is hashed consecutively (e.g. ``get`` then ``set``).
        """
        if source_code == self._last_source and self._last_code_hash:
            return self._last_code_hash
        code_hash = hashlib.sha256(source_code.encode("utf-8")).hexdigest()
        self._last_source = source_code
        self._last_code_hash = code_hash
        return code_hash

    def _generate_key(self, context: PythonContext, request_type: str) -> str:
        """Generate a unique, stable cache key from a context snapshot.

        Args:
            context: Immutable editor state snapshot.
            request_type: Request kind prefix (e.g. ``"definition"``).

        Returns:
            Stable string key for the cache mapping.
        """
        code_hash = self._code_hash(context.source_code)
        file_path = context.file_path or "unsaved_buffer"
        return f"{request_type}:{code_hash}:{context.line}:{context.column}:{file_path}"

    def get(self, context: PythonContext, request_type: str) -> Optional[Any]:
        """Retrieve a cached value if present, updating access history.

        Args:
            context: Immutable editor state snapshot.
            request_type: Request kind prefix.

        Returns:
            Cached value or ``None`` on miss.
        """
        key = self._generate_key(context, request_type)
        if key in self._cache:
            # Move key to the end to keep it fresh
            self._keys_order.remove(key)
            self._keys_order.append(key)
            return self._cache[key]
        return None

    def set(self, context: PythonContext, request_type: str, value: Any) -> None:
        """Store a value, evicting oldest keys when full.

        Args:
            context: Immutable editor state snapshot.
            request_type: Request kind prefix.
            value: Value to cache.
        """
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
        """Clear all cached calculations and the memoized source hash."""
        self._cache.clear()
        self._keys_order.clear()
        self._last_source = ""
        self._last_code_hash = ""
