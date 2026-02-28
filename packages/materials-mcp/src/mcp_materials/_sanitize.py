r"""API key sanitization for log messages and error output.

Prevents accidental leakage of Materials Project API keys (MP_API_KEY,
PMG_MAPI_KEY), bearer tokens, URLs, basic auth credentials, and query
parameter secrets by replacing them with [REDACTED] in any string
passed through sanitize_message.
"""

from __future__ import annotations

import os
import re


def sanitize_message(message: str) -> str:
    r"""Replace sensitive values found in message with [REDACTED].

    Sanitizes:
    1. MP_API_KEY and PMG_MAPI_KEY environment variable values
    2. Bearer tokens (Bearer [a-zA-Z0-9\-_.]+)
    3. URLs (https?://[^\s]+)
    4. Basic auth credentials (Authorization: Basic [a-zA-Z0-9\-_.=]+)
    5. Query parameters with token/key/secret names ([?&](token|key|api_key|apikey|secret)=[^&\s]+)

    For each pattern whose value is non-empty and at least 4 characters long,
    every occurrence in message is replaced.  The length check prevents
    replacing empty or trivially short strings that would cause false-positive
    redactions.

    Args:
        message: The string to sanitize.

    Returns:
        A copy of message with all matching sensitive values replaced by
        [REDACTED].
    """
    # Redact environment variable API keys
    key_vars = ("MP_API_KEY", "PMG_MAPI_KEY")
    for var in key_vars:
        value = os.environ.get(var, "")
        if len(value) >= 4:
            message = message.replace(value, "[REDACTED]")

    # Redact Bearer tokens: Bearer [token-chars]+
    message = re.sub(
        r"Bearer\s+[a-zA-Z0-9\-_.]+",
        "Bearer [REDACTED]",
        message,
        flags=re.IGNORECASE,
    )

    # Redact URLs: https?://[anything-until-whitespace]
    message = re.sub(
        r"https?://[^\s]+",
        "[REDACTED_URL]",
        message,
        flags=re.IGNORECASE,
    )

    # Redact Basic auth: Authorization: Basic [token]
    message = re.sub(
        r"Authorization:\s*Basic\s+[a-zA-Z0-9\-_.=]+",
        "Authorization: Basic [REDACTED]",
        message,
        flags=re.IGNORECASE,
    )

    # Redact query parameters: ?token=value, &key=value, etc.
    message = re.sub(
        r"([?&](?:token|key|api_key|apikey|secret)=)[^&\s]+",
        r"\1[REDACTED]",
        message,
        flags=re.IGNORECASE,
    )

    return message
