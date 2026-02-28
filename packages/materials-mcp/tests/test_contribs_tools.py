"""Tests for contribs_tools.py -- MPContribs tool functions.

All tests mock the ContribsClient (and bravado.exception.HTTPError) so
mpcontribs-client need not be installed for the test suite to pass.
"""

import asyncio
import json
import os
import unittest
from unittest.mock import patch

from tests.conftest import _mock_contribs_client

# =============================================================================
# Prerequisite gate tests
# =============================================================================


class TestContribsPrerequisites(unittest.TestCase):
    """Tools must return install guidance when mpcontribs-client is absent."""

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", False)
    def test_error_when_mpcontribs_not_installed(self):
        from mcp_materials.contribs_tools import contribs_search_projects

        result = json.loads(asyncio.run(contribs_search_projects()))
        self.assertIn("error", result)
        self.assertIn("not installed", result["error"])

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", False)
    def test_get_project_error_when_missing(self):
        from mcp_materials.contribs_tools import contribs_get_project

        result = json.loads(asyncio.run(contribs_get_project("test_project")))
        self.assertIn("error", result)

    def test_error_without_api_key(self):
        from mcp_materials.contribs_tools import contribs_search_projects

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MP_API_KEY", None)
            os.environ.pop("PMG_MAPI_KEY", None)
            with patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True):
                result = json.loads(asyncio.run(contribs_search_projects()))
                self.assertIn("error", result)
                self.assertIn("MP_API_KEY", result["error"])


# =============================================================================
# Input validation tests
# =============================================================================


class TestContribsInputValidation(unittest.TestCase):
    """New validators (project_name, object_id, per_page, page)."""

    def test_invalid_project_name_too_short(self):
        from mcp_materials._validation import _validate_project_name

        self.assertIsNotNone(_validate_project_name("ab"))

    def test_invalid_project_name_too_long(self):
        from mcp_materials._validation import _validate_project_name

        self.assertIsNotNone(_validate_project_name("a" * 32))

    def test_invalid_project_name_special_chars(self):
        from mcp_materials._validation import _validate_project_name

        self.assertIsNotNone(_validate_project_name("my-project"))

    def test_valid_project_name(self):
        from mcp_materials._validation import _validate_project_name

        self.assertIsNone(_validate_project_name("carrier_transport"))
        self.assertIsNone(_validate_project_name("abc"))

    def test_invalid_object_id_short(self):
        from mcp_materials._validation import _validate_object_id

        self.assertIsNotNone(_validate_object_id("abc123"))

    def test_invalid_object_id_non_hex(self):
        from mcp_materials._validation import _validate_object_id

        self.assertIsNotNone(_validate_object_id("zzzzzzzzzzzzzzzzzzzzzzzz"))

    def test_valid_object_id(self):
        from mcp_materials._validation import _validate_object_id

        self.assertIsNone(_validate_object_id("507f1f77bcf86cd799439011"))

    def test_per_page_range(self):
        from mcp_materials._validation import _validate_per_page

        self.assertIsNotNone(_validate_per_page(0))
        self.assertIsNotNone(_validate_per_page(101))
        self.assertIsNone(_validate_per_page(1))
        self.assertIsNone(_validate_per_page(100))

    def test_page_range(self):
        from mcp_materials._validation import _validate_page

        self.assertIsNotNone(_validate_page(0))
        self.assertIsNone(_validate_page(1))
        self.assertIsNone(_validate_page(999))


# =============================================================================
# Mocked tool tests
# =============================================================================


class TestContribsSearchProjectsMocked(unittest.TestCase):
    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_search_returns_projects(self, MockClient):
        from mcp_materials.contribs_tools import contribs_search_projects

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.projects.queryProjects.return_value.result.return_value = {
            "data": [
                {
                    "name": "carrier_transport",
                    "title": "Carrier Transport",
                    "description": "Transport properties",
                    "authors": "J. Doe",
                    "urls": [],
                }
            ]
        }

        result = json.loads(asyncio.run(contribs_search_projects(title="Carrier")))
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["projects"][0]["name"], "carrier_transport")

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_search_empty_results(self, MockClient):
        from mcp_materials.contribs_tools import contribs_search_projects

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.projects.queryProjects.return_value.result.return_value = {"data": []}

        result = json.loads(asyncio.run(contribs_search_projects(title="nonexistent")))
        self.assertEqual(result["count"], 0)


class TestContribsGetProjectMocked(unittest.TestCase):
    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_get_project_metadata(self, MockClient):
        from mcp_materials.contribs_tools import contribs_get_project

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.get_project.return_value = {
            "name": "carrier_transport",
            "title": "Carrier Transport",
            "description": "Community data",
            "authors": "J. Doe",
            "columns": {"col1": {"unit": "eV"}},
            "references": [{"url": "https://example.com"}],
        }

        result = json.loads(asyncio.run(contribs_get_project("carrier_transport")))
        self.assertEqual(result["name"], "carrier_transport")
        self.assertIn("columns", result)


class TestContribsSearchContributionsMocked(unittest.TestCase):
    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_search_contributions(self, MockClient):
        from mcp_materials.contribs_tools import contribs_search_contributions

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.contributions.queryContributions.return_value.result.return_value = {
            "data": [
                {
                    "id": "507f1f77bcf86cd799439011",
                    "identifier": "mp-149",
                    "formula": "Si",
                    "data": {"band_gap": {"value": 1.11, "unit": "eV"}},
                    "structures": [],
                    "tables": [],
                }
            ],
            "total_count": 1,
        }

        result = json.loads(
            asyncio.run(
                contribs_search_contributions(project="carrier_transport")
            )
        )
        self.assertEqual(result["total_count"], 1)
        self.assertEqual(result["contributions"][0]["identifier"], "mp-149")

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_pagination_has_more(self, MockClient):
        from mcp_materials.contribs_tools import contribs_search_contributions

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.contributions.queryContributions.return_value.result.return_value = {
            "data": [{"id": "aaa", "identifier": "mp-1", "formula": "X",
                       "data": {}, "structures": [], "tables": []}],
            "total_count": 50,
        }

        result = json.loads(
            asyncio.run(
                contribs_search_contributions(
                    project="carrier_transport", page=1, per_page=10
                )
            )
        )
        self.assertTrue(result["has_more"])

    def test_invalid_data_filters_key(self):
        from mcp_materials.contribs_tools import contribs_search_contributions

        with patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True):
            result = json.loads(
                asyncio.run(
                    contribs_search_contributions(
                        project="carrier_transport",
                        data_filters={"bad_key__gte": 1.0},
                    )
                )
            )
            self.assertIn("error", result)
            self.assertIn("data__", result["error"])

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_valid_data_filters_forwarded(self, MockClient):
        """T6: Valid data_filters are forwarded to the API client."""
        from mcp_materials.contribs_tools import contribs_search_contributions

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.contributions.queryContributions.return_value.result.return_value = {
            "data": [],
            "total_count": 0,
        }

        filters = {"data__band_gap__value__gte": 1.0}
        asyncio.run(
            contribs_search_contributions(
                project="carrier_transport",
                data_filters=filters,
            )
        )

        call_kwargs = (
            client.contributions.queryContributions.call_args[1]
        )
        self.assertEqual(call_kwargs["data__band_gap__value__gte"], 1.0)


class TestContribsGetContributionMocked(unittest.TestCase):
    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_get_single_contribution(self, MockClient):
        from mcp_materials.contribs_tools import contribs_get_contribution

        client = _mock_contribs_client()
        MockClient.return_value = client
        cid = "507f1f77bcf86cd799439011"
        client.get_contribution.return_value = {
            "id": cid,
            "identifier": "mp-149",
            "project": "carrier_transport",
            "data": {"value": 42},
            "structures": [],
            "tables": [],
            "attachments": [],
        }

        result = json.loads(asyncio.run(contribs_get_contribution(cid)))
        self.assertEqual(result["id"], cid)

    def test_invalid_contribution_id(self):
        from mcp_materials.contribs_tools import contribs_get_contribution

        result = json.loads(asyncio.run(contribs_get_contribution("bad-id")))
        self.assertIn("error", result)


class TestContribsGetTableMocked(unittest.TestCase):
    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_get_table(self, MockClient):
        import pandas as pd
        from mcp_materials.contribs_tools import contribs_get_table

        client = _mock_contribs_client()
        MockClient.return_value = client
        tid = "507f1f77bcf86cd799439011"
        df = pd.DataFrame({"col_a": [1, 2, 3], "col_b": [4, 5, 6]})
        client.get_table.return_value = df

        result = json.loads(asyncio.run(contribs_get_table(tid)))
        self.assertEqual(result["total_rows"], 3)
        self.assertEqual(result["columns"], ["col_a", "col_b"])
        self.assertFalse(result["truncated"])

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_table_truncation(self, MockClient):
        import pandas as pd
        from mcp_materials.contribs_tools import contribs_get_table

        client = _mock_contribs_client()
        MockClient.return_value = client
        tid = "507f1f77bcf86cd799439011"
        df = pd.DataFrame({"x": range(200)})
        client.get_table.return_value = df

        result = json.loads(asyncio.run(contribs_get_table(tid, max_rows=50)))
        self.assertTrue(result["truncated"])
        self.assertEqual(len(result["data"]), 50)
        self.assertEqual(result["total_rows"], 200)


    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_table_all_rows(self, MockClient):
        """T4: max_rows=-1 returns all rows without truncation."""
        import pandas as pd
        from mcp_materials.contribs_tools import contribs_get_table

        client = _mock_contribs_client()
        MockClient.return_value = client
        tid = "507f1f77bcf86cd799439011"
        df = pd.DataFrame({"x": range(200)})
        client.get_table.return_value = df

        result = json.loads(asyncio.run(contribs_get_table(tid, max_rows=-1)))
        self.assertFalse(result["truncated"])
        self.assertEqual(len(result["data"]), 200)
        self.assertEqual(result["total_rows"], 200)

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_table_max_rows_absolute_cap(self, MockClient):
        """H6: max_rows=-1 with very large table is capped at MAX_ROWS_ABSOLUTE."""
        import pandas as pd
        from mcp_materials.contribs_tools import MAX_ROWS_ABSOLUTE, contribs_get_table

        client = _mock_contribs_client()
        MockClient.return_value = client
        tid = "507f1f77bcf86cd799439011"
        # Create a large table with more rows than MAX_ROWS_ABSOLUTE
        large_size = MAX_ROWS_ABSOLUTE + 10000
        df = pd.DataFrame({"x": range(large_size)})
        client.get_table.return_value = df

        result = json.loads(asyncio.run(contribs_get_table(tid, max_rows=-1)))
        # Should be truncated because total_rows > MAX_ROWS_ABSOLUTE
        self.assertTrue(result["truncated"])
        # Data should be capped at MAX_ROWS_ABSOLUTE
        self.assertEqual(len(result["data"]), MAX_ROWS_ABSOLUTE)
        # But total_rows should reflect the actual table size
        self.assertEqual(result["total_rows"], large_size)

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_table_max_rows_explicit_cap(self, MockClient):
        """H6: Explicit max_rows > MAX_ROWS_ABSOLUTE is capped."""
        import pandas as pd
        from mcp_materials.contribs_tools import MAX_ROWS_ABSOLUTE, contribs_get_table

        client = _mock_contribs_client()
        MockClient.return_value = client
        tid = "507f1f77bcf86cd799439011"
        # Create a table with more rows than our requested max_rows
        df = pd.DataFrame({"x": range(MAX_ROWS_ABSOLUTE + 5000)})
        client.get_table.return_value = df

        # Request more than MAX_ROWS_ABSOLUTE
        requested = MAX_ROWS_ABSOLUTE + 1000
        result = json.loads(asyncio.run(contribs_get_table(tid, max_rows=requested)))
        # Should be truncated
        self.assertTrue(result["truncated"])
        # Data should be capped at MAX_ROWS_ABSOLUTE, not the requested amount
        self.assertEqual(len(result["data"]), MAX_ROWS_ABSOLUTE)
        self.assertEqual(result["total_rows"], MAX_ROWS_ABSOLUTE + 5000)


class TestContribsGetStructureMocked(unittest.TestCase):
    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    @patch("pymatgen.io.cif.CifWriter")
    def test_get_structure_cif(self, MockCif, MockClient):
        from mcp_materials.contribs_tools import contribs_get_structure

        client = _mock_contribs_client()
        MockClient.return_value = client

        from unittest.mock import MagicMock

        mock_structure = MagicMock()
        client.get_structure.return_value = mock_structure
        MockCif.return_value.__str__ = MagicMock(return_value="data_cif\nloop_\n")

        sid = "507f1f77bcf86cd799439011"
        result = asyncio.run(contribs_get_structure(sid, output_format="cif"))
        self.assertIn("data_cif", result)
        MockCif.assert_called_once_with(mock_structure)

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_get_structure_json(self, MockClient):
        from mcp_materials.contribs_tools import contribs_get_structure

        client = _mock_contribs_client()
        MockClient.return_value = client

        from unittest.mock import MagicMock

        mock_structure = MagicMock()
        mock_structure.to_json.return_value = '{"lattice": {}}'
        client.get_structure.return_value = mock_structure

        sid = "507f1f77bcf86cd799439011"
        result = asyncio.run(contribs_get_structure(sid, output_format="json"))
        self.assertIn("lattice", result)

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_invalid_structure_id(self, MockClient):
        from mcp_materials.contribs_tools import contribs_get_structure

        result = json.loads(asyncio.run(contribs_get_structure("bad-id")))
        self.assertIn("error", result)
        MockClient.assert_not_called()

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_invalid_output_format(self, MockClient):
        from mcp_materials.contribs_tools import contribs_get_structure

        sid = "507f1f77bcf86cd799439011"
        result = json.loads(asyncio.run(contribs_get_structure(sid, output_format="poscar")))
        self.assertIn("error", result)
        self.assertIn("poscar", result["error"])
        MockClient.assert_not_called()


class TestContribsGetAttachmentMocked(unittest.TestCase):
    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_get_attachment_metadata(self, MockClient):
        from mcp_materials.contribs_tools import contribs_get_attachment

        client = _mock_contribs_client()
        MockClient.return_value = client
        aid = "507f1f77bcf86cd799439011"
        client.attachments.getAttachmentById.return_value.result.return_value = {
            "id": aid,
            "name": "spectrum.csv",
            "mime": "text/csv",
            "content": "15432",
        }

        result = json.loads(asyncio.run(contribs_get_attachment(aid)))
        self.assertEqual(result["id"], aid)
        self.assertEqual(result["filename"], "spectrum.csv")
        self.assertEqual(result["mime_type"], "text/csv")
        self.assertEqual(result["content"], "15432")

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_size_bytes_non_numeric(self, MockClient):
        from mcp_materials.contribs_tools import contribs_get_attachment

        client = _mock_contribs_client()
        MockClient.return_value = client
        aid = "507f1f77bcf86cd799439011"
        client.attachments.getAttachmentById.return_value.result.return_value = {
            "id": aid,
            "name": "image.png",
            "mime": "image/png",
            "content": "not-a-number",
        }

        result = json.loads(asyncio.run(contribs_get_attachment(aid)))
        self.assertEqual(result["content"], "not-a-number")

    def test_invalid_attachment_id(self):
        from mcp_materials.contribs_tools import contribs_get_attachment

        result = json.loads(asyncio.run(contribs_get_attachment("bad-id")))
        self.assertIn("error", result)


class TestContribsGetProjectStatsMocked(unittest.TestCase):
    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_stats(self, MockClient):
        from mcp_materials.contribs_tools import contribs_get_project_stats

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.get_totals.return_value = (42, 5)

        result = json.loads(
            asyncio.run(contribs_get_project_stats("carrier_transport"))
        )
        self.assertEqual(result["total_contributions"], 42)
        self.assertEqual(result["total_pages"], 5)


# =============================================================================
# apikey kwarg assertion
# =============================================================================


class TestContribsClientApiKeyKwarg(unittest.TestCase):
    """Verify ContribsClient is constructed with explicit apikey= kwarg."""

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_apikey_passed_to_client(self, MockClient):
        from mcp_materials.contribs_tools import contribs_search_projects

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.projects.queryProjects.return_value.result.return_value = {"data": []}

        asyncio.run(contribs_search_projects())
        MockClient.assert_called_once_with(apikey="test-api-key-for-testing")


# =============================================================================
# Singleton / cached factory tests
# =============================================================================


class TestContribsClientSingleton(unittest.TestCase):
    """Verify ContribsClient is created once and reused across calls."""

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_client_reused_across_calls(self, MockClient):
        """The singleton factory should create the client only once for the same API key."""
        from mcp_materials.contribs_tools import _get_contribs_client, _reset_contribs_client

        _reset_contribs_client()
        client_mock = _mock_contribs_client()
        MockClient.return_value = client_mock

        c1 = _get_contribs_client("test-key")
        c2 = _get_contribs_client("test-key")
        self.assertIs(c1, c2)
        MockClient.assert_called_once_with(apikey="test-key")

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_client_recreated_for_new_api_key(self, MockClient):
        """A different API key should trigger a new client creation."""
        from mcp_materials.contribs_tools import _get_contribs_client, _reset_contribs_client

        _reset_contribs_client()
        client_mock = _mock_contribs_client()
        MockClient.return_value = client_mock

        _get_contribs_client("key-a")
        _get_contribs_client("key-b")
        self.assertEqual(MockClient.call_count, 2)

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_reset_clears_singleton(self, MockClient):
        """_reset_contribs_client should clear the cached instance."""
        from mcp_materials.contribs_tools import _get_contribs_client, _reset_contribs_client

        _reset_contribs_client()
        client_mock = _mock_contribs_client()
        MockClient.return_value = client_mock

        _get_contribs_client("test-key")
        _reset_contribs_client()
        _get_contribs_client("test-key")
        self.assertEqual(MockClient.call_count, 2)

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_singleton_used_by_tool_functions(self, MockClient):
        """Two sequential tool calls should share the same client instance."""
        from mcp_materials.contribs_tools import contribs_get_project, contribs_get_project_stats

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.get_project.return_value = {
            "name": "test", "title": "", "description": "",
            "authors": "", "columns": {}, "references": [],
        }
        client.get_totals.return_value = (10, 1)

        asyncio.run(contribs_get_project("test_project"))
        asyncio.run(contribs_get_project_stats("test_project"))
        # Client constructor should be called only once (singleton reuse)
        MockClient.assert_called_once_with(apikey="test-api-key-for-testing")


# =============================================================================
# End-to-end HTTP error propagation
# =============================================================================


class TestContribsEndToEndErrorHandling(unittest.TestCase):
    """Verify full exception chain works inside tool invocation."""

    def _mock_bravado_module(self):
        """Install a fake bravado.exception module in sys.modules."""
        import types

        from tests.conftest import FakeHTTPError

        bravado_mod = types.ModuleType("bravado")
        exception_mod = types.ModuleType("bravado.exception")
        exception_mod.HTTPError = FakeHTTPError
        bravado_mod.exception = exception_mod
        return {"bravado": bravado_mod, "bravado.exception": exception_mod}

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_http_403_end_to_end(self, MockClient):
        import sys

        from mcp_materials.contribs_tools import contribs_get_project

        from tests.conftest import FakeHTTPError

        client = _mock_contribs_client()
        MockClient.return_value = client
        fake_modules = self._mock_bravado_module()
        with patch("mcp_materials.contribs_tools.HTTPError", FakeHTTPError), \
             patch.dict(sys.modules, fake_modules):
            client.get_project.side_effect = FakeHTTPError(403, "Forbidden")
            result = json.loads(
                asyncio.run(contribs_get_project("carrier_transport"))
            )
            self.assertIn("error", result)
            self.assertIn("Permission denied", result["error"])

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_http_404_end_to_end(self, MockClient):
        import sys

        from mcp_materials.contribs_tools import contribs_get_project

        from tests.conftest import FakeHTTPError

        client = _mock_contribs_client()
        MockClient.return_value = client
        fake_modules = self._mock_bravado_module()
        with patch("mcp_materials.contribs_tools.HTTPError", FakeHTTPError), \
             patch.dict(sys.modules, fake_modules):
            client.get_project.side_effect = FakeHTTPError(404, "Not found")
            result = json.loads(
                asyncio.run(contribs_get_project("carrier_transport"))
            )
            self.assertIn("error", result)
            self.assertIn("not found", result["error"])

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_generic_exception_caught(self, MockClient):
        """Generic Exception is caught and returned as JSON error."""
        from mcp_materials.contribs_tools import contribs_search_projects

        client = _mock_contribs_client()
        MockClient.return_value = client
        client.projects.queryProjects.return_value.result.side_effect = RuntimeError(
            "boom"
        )

        result = json.loads(asyncio.run(contribs_search_projects()))
        self.assertIn("error", result)
        self.assertIn("boom", result["error"])


# =============================================================================
# HTTP error handling tests (helper-level)
# =============================================================================


class TestHTTPErrorHandling(unittest.TestCase):
    def test_403_permission_denied(self):
        from mcp_materials.contribs_tools import _handle_http_error

        class FakeHTTPError(Exception):
            status_code = 403

        result = json.loads(
            _handle_http_error(FakeHTTPError(), "project", "test")
        )
        self.assertIn("Permission denied", result["error"])

    def test_404_not_found(self):
        from mcp_materials.contribs_tools import _handle_http_error

        class FakeHTTPError(Exception):
            status_code = 404

        result = json.loads(
            _handle_http_error(FakeHTTPError(), "project", "test_proj")
        )
        self.assertIn("not found", result["error"])
        self.assertIn("test_proj", result["error"])

    def test_429_rate_limit(self):
        from mcp_materials.contribs_tools import _handle_http_error

        class FakeHTTPError(Exception):
            status_code = 429

        result = json.loads(
            _handle_http_error(FakeHTTPError(), "project", "test")
        )
        self.assertIn("Rate limit", result["error"])


# =============================================================================
# Tool annotations test
# =============================================================================


class TestContribsToolAnnotations(unittest.TestCase):
    """All contribs tools must carry read-only annotations."""

    def test_annotations_read_only(self):
        from mcp_materials._validation import TOOL_ANNOTATIONS

        self.assertTrue(TOOL_ANNOTATIONS.readOnlyHint)
        self.assertFalse(TOOL_ANNOTATIONS.destructiveHint)
        self.assertTrue(TOOL_ANNOTATIONS.idempotentHint)
        # Tools only access Materials Project APIs, so openWorldHint is False
        self.assertFalse(TOOL_ANNOTATIONS.openWorldHint)


# =============================================================================
# Timeout Tests
# =============================================================================


class TestContribsAPITimeout(unittest.TestCase):
    """asyncio.to_thread calls in contribs_tools must have timeout protection."""

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_search_projects_timeout(self, MockClient):
        """Timeout on contribs_search_projects returns a user-friendly error."""
        from mcp_materials.contribs_tools import contribs_search_projects

        client = _mock_contribs_client()
        MockClient.return_value = client

        async def _hang(*a, **kw):
            await asyncio.sleep(9999)

        with patch("mcp_materials.contribs_tools.asyncio.to_thread", side_effect=_hang), \
             patch("mcp_materials.contribs_tools.API_TIMEOUT", 0.01):
            result = json.loads(asyncio.run(contribs_search_projects()))
            self.assertIn("error", result)
            self.assertIn("timed out", result["error"].lower())

    @patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True)
    @patch("mcp_materials.contribs_tools.ContribsClient")
    def test_get_project_timeout(self, MockClient):
        """Timeout on contribs_get_project returns a user-friendly error."""
        from mcp_materials.contribs_tools import contribs_get_project

        client = _mock_contribs_client()
        MockClient.return_value = client

        async def _hang(*a, **kw):
            await asyncio.sleep(9999)

        with patch("mcp_materials.contribs_tools.asyncio.to_thread", side_effect=_hang), \
             patch("mcp_materials.contribs_tools.API_TIMEOUT", 0.01):
            result = json.loads(asyncio.run(contribs_get_project("carrier_transport")))
            self.assertIn("error", result)
            self.assertIn("timed out", result["error"].lower())

    def test_api_timeout_constant_exists(self):
        """API_TIMEOUT module-level constant must exist and be positive."""
        from mcp_materials.contribs_tools import API_TIMEOUT

        self.assertIsInstance(API_TIMEOUT, (int, float))
        self.assertGreater(API_TIMEOUT, 0)


# =============================================================================
# data_filters value validation tests
# =============================================================================


class TestDataFilterValueValidation(unittest.TestCase):
    """Value validation for data_filters to prevent API injection."""

    def test_nested_dict_rejected(self):
        """Nested dict values in data_filters must be rejected."""
        from mcp_materials.contribs_tools import contribs_search_contributions

        with patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True):
            result = json.loads(
                asyncio.run(
                    contribs_search_contributions(
                        project="carrier_transport",
                        data_filters={"data__band_gap__value__gte": {"$gt": 1}},
                    )
                )
            )
            self.assertIn("error", result)
            self.assertIn("data_filters", result["error"])

    def test_mongo_operator_string_rejected(self):
        """String values resembling MongoDB operators must be rejected."""
        from mcp_materials.contribs_tools import contribs_search_contributions

        with patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True):
            result = json.loads(
                asyncio.run(
                    contribs_search_contributions(
                        project="carrier_transport",
                        data_filters={"data__field__contains": "$where"},
                    )
                )
            )
            self.assertIn("error", result)
            self.assertIn("$", result["error"])

    def test_list_of_dicts_rejected(self):
        """Lists containing non-primitive items must be rejected."""
        from mcp_materials.contribs_tools import contribs_search_contributions

        with patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True):
            result = json.loads(
                asyncio.run(
                    contribs_search_contributions(
                        project="carrier_transport",
                        data_filters={"data__field__value__gte": [{"$gt": 1}]},
                    )
                )
            )
            self.assertIn("error", result)

    def test_none_value_rejected(self):
        """None values in data_filters must be rejected."""
        from mcp_materials.contribs_tools import contribs_search_contributions

        with patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True):
            result = json.loads(
                asyncio.run(
                    contribs_search_contributions(
                        project="carrier_transport",
                        data_filters={"data__field__value__gte": None},
                    )
                )
            )
            self.assertIn("error", result)

    def test_mongo_regex_rejected(self):
        """String values with MongoDB $regex operator must be rejected."""
        from mcp_materials.contribs_tools import contribs_search_contributions

        with patch("mcp_materials._prereqs.HAS_MPCONTRIBS", True):
            result = json.loads(
                asyncio.run(
                    contribs_search_contributions(
                        project="carrier_transport",
                        data_filters={"data__field__contains": "$regex"},
                    )
                )
            )
            self.assertIn("error", result)

    def test_valid_simple_types_accepted(self):
        """Valid primitive values (str, int, float, bool) must be accepted."""
        from mcp_materials.contribs_tools import _validate_data_filters

        self.assertIsNone(
            _validate_data_filters({"data__field__value__gte": 1.0})
        )
        self.assertIsNone(
            _validate_data_filters({"data__field__value__gte": 42})
        )
        self.assertIsNone(
            _validate_data_filters({"data__field__contains": "silicon"})
        )
        self.assertIsNone(
            _validate_data_filters({"data__field__exact": True})
        )

    def test_valid_list_of_primitives_accepted(self):
        """Lists of primitives must be accepted."""
        from mcp_materials.contribs_tools import _validate_data_filters

        self.assertIsNone(
            _validate_data_filters({"data__field__value__gte": [1.0, 2.0, 3.0]})
        )
        self.assertIsNone(
            _validate_data_filters({"data__field__contains": ["a", "b"]})
        )

    def test_list_with_mongo_string_rejected(self):
        """Lists containing strings with MongoDB operators must be rejected."""
        from mcp_materials.contribs_tools import _validate_data_filters

        err = _validate_data_filters(
            {"data__field__contains": ["safe", "$ne"]}
        )
        self.assertIsNotNone(err)
        self.assertIn("$", err)


if __name__ == "__main__":
    unittest.main()
