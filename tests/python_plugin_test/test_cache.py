"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for the LRU language-request cache and its source-hash memoization.
"""

from __future__ import annotations

import hashlib

import pytest

from editor.Ironica.plugins.python import cache as cache_module
from editor.Ironica.plugins.python.cache import LanguageCache
from editor.Ironica.plugins.python.domain_models import PythonContext


def _context(
    source: str = "x = 1\n",
    line: int = 0,
    column: int = 0,
    file_path: str | None = "/tmp/module.py",
    project_root: str | None = "/tmp/project",
) -> PythonContext:
    return PythonContext(source, line, column, file_path, project_root)


class TestCacheKeyGeneration:
    """Tests for the stable keys derived from context snapshots."""

    def test_same_context_produces_same_key(self):
        """Identical snapshots address the same cache entry."""
        cache = LanguageCache()

        first = cache._generate_key(_context(), "definition")
        second = cache._generate_key(_context(), "definition")

        assert first == second

    @pytest.mark.parametrize(
        "changed",
        [
            _context(line=1),
            _context(column=1),
            _context(source="x = 2\n"),
            _context(file_path="/tmp/other.py"),
            _context(project_root="/tmp/other"),
            _context(file_path=None),
        ],
    )
    def test_each_context_component_changes_the_key(self, changed):
        """Line, column, source, path, and project root are all significant."""
        cache = LanguageCache()

        assert cache._generate_key(_context(), "definition") != cache._generate_key(
            changed, "definition"
        )

    def test_request_type_changes_the_key(self):
        """Different request types never collide for the same caret."""
        cache = LanguageCache()
        context = _context()

        assert cache._generate_key(context, "definition") != cache._generate_key(
            context, "hover"
        )

    def test_unsaved_buffer_uses_a_stable_sentinel(self):
        """A missing path maps to the documented ``unsaved_buffer`` marker."""
        cache = LanguageCache()
        key = cache._generate_key(_context(file_path=None), "definition")

        assert ":unsaved_buffer:" in key
        assert key.endswith(":") is False

    def test_empty_project_root_is_represented(self):
        """Missing project roots are encoded as an empty key segment."""
        cache = LanguageCache()
        key = cache._generate_key(_context(project_root=None), "definition")

        assert key.endswith(":")


class TestSourceHashMemoization:
    """Tests for the per-buffer SHA-256 memoization."""

    @staticmethod
    def _counting_sha256(monkeypatch):
        calls = []
        real_sha256 = hashlib.sha256

        def wrapper(data=b""):
            calls.append(data)
            return real_sha256(data)

        monkeypatch.setattr(cache_module.hashlib, "sha256", wrapper)
        return calls

    def test_repeated_hashing_of_the_same_buffer_is_avoided(self, monkeypatch):
        """The same consecutive source string hashes only once."""
        calls = self._counting_sha256(monkeypatch)
        cache = LanguageCache()
        context = _context(source="shared source")

        for _ in range(5):
            cache._generate_key(context, "definition")

        assert len(calls) == 1

    def test_changed_source_is_hashed_again(self, monkeypatch):
        """A changed buffer always produces a fresh hash."""
        calls = self._counting_sha256(monkeypatch)
        cache = LanguageCache()

        cache._generate_key(_context(source="one"), "definition")
        cache._generate_key(_context(source="two"), "definition")

        assert len(calls) == 2
        assert calls[0] != calls[1]

    def test_returning_to_a_previous_source_rehashes(self, monkeypatch):
        """Only the immediately previous source is memoized."""
        calls = self._counting_sha256(monkeypatch)
        cache = LanguageCache()

        cache._generate_key(_context(source="one"), "definition")
        cache._generate_key(_context(source="two"), "definition")
        cache._generate_key(_context(source="one"), "definition")

        assert len(calls) == 3

    def test_unicode_source_hashes_utf8_bytes(self):
        """Unicode buffers hash their UTF-8 representation deterministically."""
        cache = LanguageCache()
        first = cache._generate_key(_context(source="grüß"), "definition")

        cache.clear()
        second = cache._generate_key(_context(source="grüß"), "definition")

        assert first == second
        assert hashlib.sha256("grüß".encode()).hexdigest() in first


class TestLruBehaviour:
    """Tests for access ordering, eviction, and storage semantics."""

    def test_set_then_get_round_trips(self):
        """Stored values are returned unchanged."""
        cache = LanguageCache()
        context = _context()

        cache.set(context, "definition", ("/tmp/a.py", 1, 0))

        assert cache.get(context, "definition") == ("/tmp/a.py", 1, 0)

    def test_missing_entries_return_none(self):
        """A cache miss is reported as ``None``."""
        cache = LanguageCache()

        assert cache.get(_context(), "definition") is None

    def test_reading_an_entry_refreshes_its_lru_position(self):
        """A hit moves the key to the most-recently-used position."""
        cache = LanguageCache(max_size=2)
        first = _context(line=0)
        second = _context(line=1)
        third = _context(line=2)

        cache.set(first, "definition", "first")
        cache.set(second, "definition", "second")
        assert cache.get(first, "definition") == "first"
        cache.set(third, "definition", "third")

        assert cache.get(first, "definition") == "first"
        assert cache.get(second, "definition") is None
        assert cache.get(third, "definition") == "third"

    def test_least_recently_used_entry_is_evicted(self):
        """Without a hit, the oldest insertion is evicted first."""
        cache = LanguageCache(max_size=2)
        first = _context(line=0)
        second = _context(line=1)
        third = _context(line=2)

        cache.set(first, "definition", "first")
        cache.set(second, "definition", "second")
        cache.set(third, "definition", "third")

        assert cache.get(first, "definition") is None
        assert cache.get(second, "definition") == "second"
        assert cache.get(third, "definition") == "third"

    def test_reinserting_an_existing_key_keeps_the_first_value(self):
        """Current contract: ``set`` never overwrites an existing key."""
        cache = LanguageCache()
        context = _context()

        cache.set(context, "definition", "first")
        cache.set(context, "definition", "second")

        assert cache.get(context, "definition") == "first"
        assert len(cache._keys_order) == 1

    def test_zero_capacity_cache_stores_nothing(self):
        """A zero-capacity cache degrades to a no-op instead of crashing."""
        cache = LanguageCache(max_size=0)
        context = _context()

        cache.set(context, "definition", "value")

        assert cache.get(context, "definition") is None
        assert cache._cache == {}
        assert cache._keys_order == []

    def test_negative_capacity_cache_stores_nothing(self):
        """Negative capacities are treated like a disabled cache."""
        cache = LanguageCache(max_size=-5)
        context = _context()

        cache.set(context, "definition", "value")

        assert cache.get(context, "definition") is None

    def test_single_entry_cache_evicts_on_every_new_key(self):
        """A capacity of one retains only the newest request."""
        cache = LanguageCache(max_size=1)
        first = _context(line=0)
        second = _context(line=1)

        cache.set(first, "definition", "first")
        cache.set(second, "definition", "second")

        assert cache.get(first, "definition") is None
        assert cache.get(second, "definition") == "second"

    def test_clear_removes_entries_and_hash_memo(self, monkeypatch):
        """clear() resets storage, ordering, and the remembered source hash."""
        cache = LanguageCache()
        context = _context(source="payload")
        cache.set(context, "definition", "value")

        calls = []
        real_sha256 = hashlib.sha256

        def wrapper(data=b""):
            calls.append(data)
            return real_sha256(data)

        monkeypatch.setattr(cache_module.hashlib, "sha256", wrapper)
        cache.clear()

        assert cache.get(context, "definition") is None
        assert cache._cache == {}
        assert cache._keys_order == []
        cache._generate_key(context, "definition")
        assert len(calls) == 1

    def test_clear_is_idempotent(self):
        """Clearing an empty cache remains safe."""
        cache = LanguageCache()

        cache.clear()
        cache.clear()

        assert cache.get(_context(), "definition") is None
