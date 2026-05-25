"""Exception taxonomy for the goulburn SDK.

All exceptions raised by the SDK derive from GoulburnError, so a
catch-all is one line. Specific subclasses let callers branch on
the meaningful failure modes without parsing strings.
"""
from __future__ import annotations

from typing import Any


class GoulburnError(Exception):
    """Base class for every exception raised by this SDK."""


class APIError(GoulburnError):
    """Non-2xx response from the goulburn API.

    Attributes:
        status_code: HTTP status returned.
        detail: Server-supplied detail message (best-effort parsed from
            the JSON body's `detail` field; falls back to the body string).
        body: Raw response body — useful for debugging non-JSON errors.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        *,
        body: Any = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.body = body
        super().__init__(f"HTTP {status_code}: {detail}")


class AuthenticationError(APIError):
    """401 — the API key is missing, malformed, or revoked."""


class NotFoundError(APIError):
    """404 — the requested resource does not exist."""


class RateLimitError(APIError):
    """429 — the caller has exceeded a rate-limit window.

    Attributes:
        retry_after_seconds: If the server sent a Retry-After header, this is
            the parsed integer. None if the header was absent or unparseable.
    """

    def __init__(
        self,
        status_code: int,
        detail: str,
        *,
        body: Any = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(status_code, detail, body=body)
        self.retry_after_seconds = retry_after_seconds
