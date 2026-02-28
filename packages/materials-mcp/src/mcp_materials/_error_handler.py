"""Centralized error-handling decorator for MPContribs tool functions.

Provides ``contribs_error_handler`` which wraps async tool functions with
structured try/except logic, mapping known exception types (HTTPError,
MPContribsClientError) to appropriate error responses.

Imports are performed lazily inside the wrapper to avoid circular import
issues between this module, ``contribs_tools``, and ``_validation``.
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Coroutine
from typing import Any


def contribs_error_handler(entity_type: str) -> Callable:
    """Decorator that catches exceptions from async contribs tool functions.

    Wraps the decorated async function so that:

    * ``HTTPError`` (bravado) is delegated to
      :func:`mcp_materials.contribs_tools._handle_http_error`.
    * ``MPContribsClientError`` yields an ``api_error`` category response.
    * Any other ``Exception`` yields an ``internal_error`` category response.

    Args:
        entity_type: A label such as ``"project"`` or ``"contribution"``
            used when formatting HTTP error messages.

    Returns:
        A decorator that wraps an ``async def`` tool function.
    """

    def decorator(
        fn: Callable[..., Coroutine[Any, Any, str]],
    ) -> Callable[..., Coroutine[Any, Any, str]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> str:
            # Lazy imports to break circular dependency chains.
            from mcp_materials._validation import _error_response
            from mcp_materials.contribs_tools import _handle_http_error

            # Resolve optional exception classes at call time.
            try:
                from bravado.exception import HTTPError
            except ImportError:
                HTTPError = None

            try:
                from mpcontribs.client import MPContribsClientError
            except (ImportError, AttributeError):
                MPContribsClientError = None

            try:
                return await fn(*args, **kwargs)
            except TimeoutError:
                # asyncio.TimeoutError is an alias for the builtin
                # TimeoutError in Python 3.11+.
                from mcp_materials.contribs_tools import _TIMEOUT_MSG, API_TIMEOUT

                return _error_response(
                    _TIMEOUT_MSG.format(timeout=API_TIMEOUT),
                    error_category="timeout_error",
                )
            except Exception as exc:
                if HTTPError is not None and isinstance(exc, HTTPError):
                    # Attempt to extract a meaningful entity_id from kwargs.
                    entity_id = str(
                        kwargs.get("project_name")
                        or kwargs.get("project")
                        or kwargs.get("contribution_id")
                        or kwargs.get("table_id")
                        or kwargs.get("structure_id")
                        or kwargs.get("attachment_id")
                        or ""
                    )
                    return _handle_http_error(exc, entity_type, entity_id)
                if MPContribsClientError is not None and isinstance(
                    exc, MPContribsClientError
                ):
                    return _error_response(
                        str(exc), error_category="api_error"
                    )
                return _error_response(
                    str(exc), error_category="internal_error"
                )

        return wrapper

    return decorator
