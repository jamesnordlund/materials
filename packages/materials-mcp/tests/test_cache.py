"""Tests for _cache.py -- InMemoryCache, _cache_key, and tool-level integration.

Unit tests cover:
  - Deterministic key construction
  - Get/put round-trip
  - LRU eviction
  - TTL expiry
  - Pattern-based and full invalidation
  - Performance (1000 get ops < 1s)

Tool-level integration tests cover:
  - mp_provenance_get: second call with same args returns cache hit (no MPRester)
  - mp_summary_search_advanced: same pattern
  - mp_insertion_electrodes_search: same pattern

Traces: R-PERF-001, R-PERF-004, R-PERF-013
"""

from __future__ import annotations

import asyncio
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from mcp_materials._cache import InMemoryCache, _cache_key

# ============================================================================
# _cache_key tests
# ============================================================================


class TestCacheKey(unittest.TestCase):
    """Tests for _cache_key determinism and sensitivity."""

    def test_deterministic(self):
        """Same inputs produce the same key."""
        k1 = _cache_key("tool_a", "v1", x=1, y="hello")
        k2 = _cache_key("tool_a", "v1", x=1, y="hello")
        self.assertEqual(k1, k2)

    def test_different_db_version(self):
        """Different db_version produces a different key."""
        k1 = _cache_key("tool_a", "v1", x=1)
        k2 = _cache_key("tool_a", "v2", x=1)
        self.assertNotEqual(k1, k2)

    def test_different_tool_name(self):
        """Different tool_name produces a different key."""
        k1 = _cache_key("tool_a", "v1", x=1)
        k2 = _cache_key("tool_b", "v1", x=1)
        self.assertNotEqual(k1, k2)

    def test_different_kwargs(self):
        """Different kwargs produce a different key."""
        k1 = _cache_key("tool_a", "v1", x=1)
        k2 = _cache_key("tool_a", "v1", x=2)
        self.assertNotEqual(k1, k2)

    def test_key_format(self):
        """Key format is tool_name:hex_hash."""
        k = _cache_key("my_tool", "v1", a=1)
        self.assertTrue(k.startswith("my_tool:"))
        self.assertEqual(len(k.split(":")[1]), 16)

    def test_kwarg_order_independent(self):
        """kwargs order does not affect the key."""
        k1 = _cache_key("tool", "v1", a=1, b=2)
        k2 = _cache_key("tool", "v1", b=2, a=1)
        self.assertEqual(k1, k2)

    def test_none_db_version(self):
        """db_version=None is a valid input."""
        k = _cache_key("tool", None, x=1)
        self.assertTrue(k.startswith("tool:"))


# ============================================================================
# InMemoryCache tests
# ============================================================================


class TestInMemoryCache(unittest.TestCase):
    """Tests for InMemoryCache store/retrieve/eviction/TTL/invalidation."""

    def test_get_put_roundtrip(self):
        """put() then get() returns the stored value."""
        cache = InMemoryCache(max_entries=10, default_ttl=60)
        cache.put("k1", "value1")
        self.assertEqual(cache.get("k1"), "value1")

    def test_get_missing(self):
        """get() for a missing key returns None."""
        cache = InMemoryCache(max_entries=10, default_ttl=60)
        self.assertIsNone(cache.get("nonexistent"))

    def test_lru_eviction(self):
        """When max_entries is exceeded, the oldest (LRU) entry is evicted."""
        cache = InMemoryCache(max_entries=3, default_ttl=3600)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        # Cache is full. Insert one more; "a" (oldest) should be evicted.
        cache.put("d", "4")
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.get("b"), "2")
        self.assertEqual(cache.get("c"), "3")
        self.assertEqual(cache.get("d"), "4")

    def test_lru_access_promotes(self):
        """Accessing an entry promotes it, so a different entry gets evicted."""
        cache = InMemoryCache(max_entries=3, default_ttl=3600)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        # Access "a" to promote it.
        cache.get("a")
        # Insert "d"; "b" (now oldest) should be evicted instead of "a".
        cache.put("d", "4")
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), "1")

    def test_ttl_expiry(self):
        """An entry with TTL=0 expires immediately."""
        cache = InMemoryCache(max_entries=10, default_ttl=3600)
        cache.put("k1", "value1", ttl=0)
        self.assertIsNone(cache.get("k1"))

    def test_invalidate_pattern(self):
        """invalidate(pattern) removes matching entries."""
        cache = InMemoryCache(max_entries=10, default_ttl=3600)
        cache.put("tool_a:abc", "1")
        cache.put("tool_a:def", "2")
        cache.put("tool_b:xyz", "3")
        removed = cache.invalidate("tool_a")
        self.assertEqual(removed, 2)
        self.assertIsNone(cache.get("tool_a:abc"))
        self.assertIsNone(cache.get("tool_a:def"))
        self.assertEqual(cache.get("tool_b:xyz"), "3")

    def test_invalidate_all(self):
        """invalidate(None) clears all entries."""
        cache = InMemoryCache(max_entries=10, default_ttl=3600)
        cache.put("a", "1")
        cache.put("b", "2")
        cache.put("c", "3")
        removed = cache.invalidate(None)
        self.assertEqual(removed, 3)
        self.assertIsNone(cache.get("a"))
        self.assertIsNone(cache.get("b"))
        self.assertIsNone(cache.get("c"))

    def test_put_overwrites(self):
        """Putting the same key replaces the value."""
        cache = InMemoryCache(max_entries=10, default_ttl=3600)
        cache.put("k1", "old")
        cache.put("k1", "new")
        self.assertEqual(cache.get("k1"), "new")

    def test_performance_1000_gets(self):
        """1000 get operations complete in <1 second."""
        cache = InMemoryCache(max_entries=2000, default_ttl=3600)
        for i in range(1000):
            cache.put(f"key_{i}", f"value_{i}")
        t0 = time.monotonic()
        for i in range(1000):
            cache.get(f"key_{i}")
        elapsed = time.monotonic() - t0
        self.assertLess(elapsed, 1.0, f"1000 get ops took {elapsed:.3f}s")


# ============================================================================
# Tool-level cache integration tests
# ============================================================================


def _make_mp_rester_mock(docs=None, doc=None, db_version="2025.1.1"):
    """Create a mock MPRester context manager.

    For search-style endpoints, *docs* is returned.
    For get_data_by_id endpoints, *doc* is returned.
    """
    mpr = MagicMock()
    mpr.__enter__ = MagicMock(return_value=mpr)
    mpr.__exit__ = MagicMock(return_value=False)
    mpr.get_database_version.return_value = db_version

    if docs is not None:
        mpr.tasks.search.return_value = docs
        mpr.materials.summary.search.return_value = docs
        mpr.insertion_electrodes.search.return_value = docs
    if doc is not None:
        mpr.materials.provenance.get_data_by_id.return_value = doc
    return mpr


class TestProvenanceCacheIntegration(unittest.TestCase):
    """Verify mp_provenance_get uses cache on second call."""

    @patch("mcp_materials.mp_provenance_tools._check_prerequisites")
    @patch("mcp_materials.mp_provenance_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_provenance_tools.MPRester")
    def test_second_call_uses_cache(self, mock_rester_cls, mock_db, mock_prereq):
        import mcp_materials.mp_provenance_tools as mod

        mock_prereq.return_value = (None, "fake_key")
        mock_db.return_value = ("2025.1.1", None)

        doc = SimpleNamespace(
            material_id="mp-149",
            task_ids=["mp-149"],
            last_updated=None,
            created_at=None,
            history=None,
            authors=None,
            remarks=None,
        )
        mpr_instance = _make_mp_rester_mock(doc=doc)
        mock_rester_cls.return_value = mpr_instance

        cache = InMemoryCache(max_entries=256, default_ttl=3600)
        old_cache = mod._cache
        mod._cache = cache

        try:
            # First call: cache miss, MPRester is called.
            result1 = asyncio.get_event_loop().run_until_complete(
                mod.mp_provenance_get(material_id="mp-149")
            )
            self.assertEqual(mock_rester_cls.call_count, 1)
            data1 = json.loads(result1)
            self.assertEqual(data1["count"], 1)

            # Second call: cache hit, MPRester should NOT be called again.
            result2 = asyncio.get_event_loop().run_until_complete(
                mod.mp_provenance_get(material_id="mp-149")
            )
            self.assertEqual(mock_rester_cls.call_count, 1)
            self.assertEqual(result1, result2)
        finally:
            mod._cache = old_cache


class TestSearchCacheIntegration(unittest.TestCase):
    """Verify mp_summary_search_advanced uses cache on second call."""

    @patch("mcp_materials.mp_search_tools._check_prerequisites")
    @patch("mcp_materials.mp_search_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_search_tools.MPRester")
    def test_second_call_uses_cache(self, mock_rester_cls, mock_db, mock_prereq):
        import mcp_materials.mp_search_tools as mod

        mock_prereq.return_value = (None, "fake_key")
        mock_db.return_value = ("2025.1.1", None)

        doc = SimpleNamespace(
            material_id="mp-149",
            formula_pretty="Si",
            energy_above_hull=0.0,
            band_gap=1.1,
            density=2.33,
            volume=40.9,
            nsites=2,
            symmetry=None,
            is_stable=True,
            is_metal=False,
        )
        mpr_instance = _make_mp_rester_mock(docs=[doc])
        mock_rester_cls.return_value = mpr_instance

        cache = InMemoryCache(max_entries=256, default_ttl=3600)
        old_cache = mod._cache
        mod._cache = cache

        try:
            # First call.
            result1 = asyncio.get_event_loop().run_until_complete(
                mod.mp_summary_search_advanced(
                    must_include_elements=["Si"],
                    max_results=10,
                )
            )
            self.assertEqual(mock_rester_cls.call_count, 1)

            # Second call: should be a cache hit.
            result2 = asyncio.get_event_loop().run_until_complete(
                mod.mp_summary_search_advanced(
                    must_include_elements=["Si"],
                    max_results=10,
                )
            )
            self.assertEqual(mock_rester_cls.call_count, 1)
            self.assertEqual(result1, result2)
        finally:
            mod._cache = old_cache


class TestElectrodeCacheIntegration(unittest.TestCase):
    """Verify mp_insertion_electrodes_search uses cache on second call."""

    @patch("mcp_materials.mp_property_tools._check_prerequisites")
    @patch("mcp_materials.mp_property_tools.get_db_version", new_callable=AsyncMock)
    @patch("mcp_materials.mp_property_tools.MPRester")
    def test_second_call_uses_cache(self, mock_rester_cls, mock_db, mock_prereq):
        import mcp_materials.mp_property_tools as mod

        mock_prereq.return_value = (None, "fake_key")
        mock_db.return_value = ("2025.1.1", None)

        doc = SimpleNamespace(
            battery_id="mp-1234",
            battery_formula="LiMnO2",
            framework_formula="MnO2",
            working_ion="Li",
            num_steps=1,
            max_delta_volume=5.0,
            average_voltage=3.5,
            capacity_grav=200.0,
            capacity_vol=600.0,
            energy_grav=700.0,
            energy_vol=2100.0,
            stability_charge=0.1,
            stability_discharge=0.2,
            material_ids=["mp-1234"],
            formula_pretty="LiMnO2",
        )
        mpr_instance = _make_mp_rester_mock(docs=[doc])
        mock_rester_cls.return_value = mpr_instance

        cache = InMemoryCache(max_entries=256, default_ttl=3600)
        old_cache = mod._cache
        mod._cache = cache

        try:
            # First call.
            result1 = asyncio.get_event_loop().run_until_complete(
                mod.mp_insertion_electrodes_search(working_ion="Li")
            )
            self.assertEqual(mock_rester_cls.call_count, 1)

            # Second call: should be a cache hit.
            result2 = asyncio.get_event_loop().run_until_complete(
                mod.mp_insertion_electrodes_search(working_ion="Li")
            )
            self.assertEqual(mock_rester_cls.call_count, 1)
            self.assertEqual(result1, result2)
        finally:
            mod._cache = old_cache


if __name__ == "__main__":
    unittest.main()
