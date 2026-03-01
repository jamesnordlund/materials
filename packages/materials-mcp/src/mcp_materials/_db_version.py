"""Cached Materials Project database version fetcher."""

from __future__ import annotations

import asyncio
import threading
import time

from mcp_materials._prereqs import HAS_MP_API
from mcp_materials._sanitize import sanitize_message

if HAS_MP_API:
    from mp_api.client import MPRester

_cached_db_version: str | None = None
_cached_at: float = 0.0
_DB_VERSION_TTL: float = 300.0  # 5 minutes
_lock = threading.Lock()


async def get_db_version(api_key: str) -> tuple[str | None, str | None]:
    """Fetch and cache the MP database version.

    Returns:
        (db_version, error_message). If fetch fails, db_version is None
        and error_message describes the failure. The caller should set
        metadata.db_version = None and metadata.db_version_error = error_message
        rather than failing the entire tool invocation (R-ERR-006).
    """
    global _cached_db_version, _cached_at
    now = time.monotonic()
    with _lock:
        if _cached_db_version and (now - _cached_at) < _DB_VERSION_TTL:
            return _cached_db_version, None
    try:
        def _fetch():
            with MPRester(api_key) as mpr:
                return mpr.get_database_version()
        version = await asyncio.wait_for(
            asyncio.to_thread(_fetch), timeout=10.0  # shorter timeout for version check
        )
        with _lock:
            _cached_db_version = version
            _cached_at = now
        return version, None
    except Exception as e:
        return None, sanitize_message(str(e))
