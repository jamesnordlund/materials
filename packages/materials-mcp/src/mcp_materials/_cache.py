"""In-memory LRU cache for MCP tool responses.

Provides ``_cache_key`` for deterministic key construction and
``InMemoryCache`` with LRU eviction, TTL expiry, and pattern-based
invalidation.

Configuration via environment variables:
    MCP_CACHE_MAX_ENTRIES  -- maximum cache entries (default: 256)
    MCP_CACHE_TTL_SECONDS  -- default TTL in seconds (default: 3600)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

_MAX_ENTRIES_CAP = 10000


def _cache_key(tool_name: str, db_version: str | None, **kwargs) -> str:
    """Construct a deterministic cache key.

    1. Sort kwargs by key name.
    2. JSON-serialize (tool_name, db_version, sorted kwargs) with sort_keys=True.
    3. SHA256 hash the serialized string.
    4. Return ``f"{tool_name}:{hash_hex[:16]}"``.

    Including db_version ensures entries are auto-invalidated when the
    database version changes (R-PERF-001).
    """
    payload = json.dumps(
        [tool_name, db_version, kwargs],
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
    return f"{tool_name}:{digest}"


@dataclass
class CacheEntry:
    """A single cached response."""

    key: str
    value: str
    db_version: str | None
    created_at: float
    ttl_seconds: int
    size_bytes: int


def _env_int(name: str, default: int) -> int:
    """Read an integer from an environment variable, or return *default*."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


class InMemoryCache:
    """Thread-safe in-memory LRU cache with TTL expiry.

    Parameters
    ----------
    max_entries:
        Maximum number of entries before LRU eviction (default from
        ``MCP_CACHE_MAX_ENTRIES`` env var, or 256).
    default_ttl:
        Default time-to-live in seconds (default from
        ``MCP_CACHE_TTL_SECONDS`` env var, or 3600).
    """

    def __init__(
        self,
        max_entries: int | None = None,
        default_ttl: int | None = None,
    ) -> None:
        raw_max = (
            max_entries
            if max_entries is not None
            else _env_int("MCP_CACHE_MAX_ENTRIES", 256)
        )
        if raw_max > _MAX_ENTRIES_CAP:
            logger.warning(
                "MCP_CACHE_MAX_ENTRIES=%d exceeds cap; clamping to %d",
                raw_max,
                _MAX_ENTRIES_CAP,
            )
            raw_max = _MAX_ENTRIES_CAP
        self.max_entries = raw_max
        self.default_ttl = (
            default_ttl
            if default_ttl is not None
            else _env_int("MCP_CACHE_TTL_SECONDS", 3600)
        )
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, key: str) -> str | None:
        """Return the cached value for *key*, or ``None``.

        Expired entries are removed on access. A successful lookup promotes
        the entry to most-recently-used position (O(1)).
        """
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.time() - entry.created_at >= entry.ttl_seconds:
                del self._store[key]
                return None
            self._store.move_to_end(key)
            return entry.value

    def put(self, key: str, value: str, *, ttl: int | None = None) -> None:
        """Store *value* under *key*; evict LRU entry if at capacity."""
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        entry = CacheEntry(
            key=key,
            value=value,
            db_version=None,
            created_at=time.time(),
            ttl_seconds=ttl_seconds,
            size_bytes=len(value.encode()),
        )
        with self._lock:
            if key in self._store:
                del self._store[key]
            elif len(self._store) >= self.max_entries:
                self._store.popitem(last=False)  # evict LRU (oldest)
            self._store[key] = entry

    def invalidate(self, pattern: str | None = None) -> int:
        """Remove entries whose key starts with *pattern*.

        If *pattern* is ``None``, remove **all** entries.
        Returns the number of entries removed.
        """
        with self._lock:
            if pattern is None:
                count = len(self._store)
                self._store.clear()
                return count
            to_remove = [k for k in self._store if k.startswith(pattern)]
            for k in to_remove:
                del self._store[k]
            return len(to_remove)
