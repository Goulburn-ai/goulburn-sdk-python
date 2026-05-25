"""HTTP client for the goulburn.ai Trust API.

Two flavours:
- Client: async, the preferred form. Uses httpx.AsyncClient under the hood.
- SyncClient: synchronous wrapper for callers who can't use async (CLI,
  notebooks, simple scripts). Implemented via httpx.Client — not by
  blocking on the async client — so neither flavour pays for the other.

Retry behaviour:
- 408, 425, 429, 500-504 are retried up to `max_retries` times (default 3)
  with exponential backoff + jitter.
- 4xx-other are NOT retried (they're caller errors).
- 401/404/429 are mapped to dedicated subclasses; other non-2xx → APIError.

Auth:
- Reads GOULBURN_API_KEY from env unless `api_key` is passed explicitly.
- Sent as `Authorization: Bearer gbok_...`.

Base URL:
- Reads GOULBURN_API_BASE from env (defaults to https://api.goulburn.ai).
- Passing `base_url` overrides both.
"""
from __future__ import annotations

import os
import random
from types import TracebackType
from typing import Any

import httpx

from goulburn._errors import (
    APIError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)
from goulburn._models import Owner

# ── Defaults ────────────────────────────────────────────────────────
_DEFAULT_BASE_URL = "https://api.goulburn.ai"
_DEFAULT_TIMEOUT = 30.0  # seconds
_DEFAULT_MAX_RETRIES = 3
_RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


def _resolve_api_key(explicit: str | None) -> str:
    if explicit:
        return explicit
    env = os.environ.get("GOULBURN_API_KEY", "").strip()
    if not env:
        raise AuthenticationError(
            status_code=0,
            detail=(
                "No API key configured. Pass api_key='gbok_...' to the "
                "client, or set the GOULBURN_API_KEY environment variable. "
                "Mint a key at https://goulburn.ai/settings."
            ),
        )
    return env


def _resolve_base_url(explicit: str | None) -> str:
    if explicit:
        return explicit.rstrip("/")
    return os.environ.get("GOULBURN_API_BASE", _DEFAULT_BASE_URL).rstrip("/")


def _backoff_seconds(attempt: int, retry_after: float | None = None) -> float:
    """Exponential backoff with jitter. attempt is 1-indexed."""
    if retry_after is not None and retry_after >= 0:
        return retry_after
    base = min(2 ** (attempt - 1), 30.0)
    jitter: float = random.uniform(0, base / 4)
    return float(base + jitter)


def _parse_retry_after(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return max(0, int(value.strip()))
    except (TypeError, ValueError):
        return None


def _map_error(resp: httpx.Response) -> APIError:
    """Map an httpx response to the right APIError subclass."""
    body: Any
    detail: str
    try:
        body = resp.json()
        if isinstance(body, dict):
            detail = str(body.get("detail") or body.get("error") or body)
        else:
            detail = str(body)
    except Exception:
        body = resp.text
        detail = body or f"HTTP {resp.status_code}"

    if resp.status_code == 401:
        return AuthenticationError(resp.status_code, detail, body=body)
    if resp.status_code == 404:
        return NotFoundError(resp.status_code, detail, body=body)
    if resp.status_code == 429:
        return RateLimitError(
            resp.status_code,
            detail,
            body=body,
            retry_after_seconds=_parse_retry_after(resp.headers.get("retry-after")),
        )
    return APIError(resp.status_code, detail, body=body)


# ── Async API ───────────────────────────────────────────────────────


class _AuthNamespace:
    """Methods under client.auth — async variant."""

    def __init__(self, client: Client) -> None:
        self._c = client

    async def verify(self) -> Owner:
        """GET /api/v1/owner/me — confirm the key works, return identity.

        Raises AuthenticationError if the key is invalid or revoked.
        """
        data = await self._c._request("GET", "/api/v1/owner/me")
        return Owner.model_validate(data)


class Client:
    """Async client for the goulburn.ai Trust API.

    Use as an async context manager for automatic cleanup:

        async with Client() as gb:
            me = await gb.auth.verify()

    Or manage the lifecycle yourself:

        gb = Client()
        try:
            ...
        finally:
            await gb.aclose()
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = _resolve_api_key(api_key)
        self._base_url = _resolve_base_url(base_url)
        self._max_retries = max_retries
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": _user_agent(),
                "Accept": "application/json",
            },
            transport=transport,
        )
        self.auth = _AuthNamespace(self)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> Client:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 2):
            try:
                resp = await self._http.request(method, path, json=json, params=params)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt > self._max_retries:
                    raise APIError(0, f"Network error after {attempt - 1} retries: {exc}") from exc
                await _async_sleep(_backoff_seconds(attempt))
                continue

            if 200 <= resp.status_code < 300:
                if not resp.content:
                    return None
                try:
                    return resp.json()
                except Exception:
                    return resp.text

            if resp.status_code in _RETRYABLE_STATUS and attempt <= self._max_retries:
                retry_after = _parse_retry_after(resp.headers.get("retry-after"))
                await _async_sleep(_backoff_seconds(attempt, retry_after))
                continue

            raise _map_error(resp)

        # Should be unreachable.
        raise APIError(0, f"Exhausted retries: {last_exc}")


# ── Sync wrapper ────────────────────────────────────────────────────


class _SyncAuthNamespace:
    def __init__(self, client: SyncClient) -> None:
        self._c = client

    def verify(self) -> Owner:
        data = self._c._request("GET", "/api/v1/owner/me")
        return Owner.model_validate(data)


class SyncClient:
    """Synchronous client. Same surface as Client, blocking-style.

    Implemented with httpx.Client (not by .run-ing the async client) so
    callers in non-async contexts (CLI, notebooks, simple scripts)
    don't pay for an event loop.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        *,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_MAX_RETRIES,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = _resolve_api_key(api_key)
        self._base_url = _resolve_base_url(base_url)
        self._max_retries = max_retries
        self._http = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "User-Agent": _user_agent(),
                "Accept": "application/json",
            },
            transport=transport,
        )
        self.auth = _SyncAuthNamespace(self)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> SyncClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        import time as _time

        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 2):
            try:
                resp = self._http.request(method, path, json=json, params=params)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_exc = exc
                if attempt > self._max_retries:
                    raise APIError(0, f"Network error after {attempt - 1} retries: {exc}") from exc
                _time.sleep(_backoff_seconds(attempt))
                continue

            if 200 <= resp.status_code < 300:
                if not resp.content:
                    return None
                try:
                    return resp.json()
                except Exception:
                    return resp.text

            if resp.status_code in _RETRYABLE_STATUS and attempt <= self._max_retries:
                retry_after = _parse_retry_after(resp.headers.get("retry-after"))
                _time.sleep(_backoff_seconds(attempt, retry_after))
                continue

            raise _map_error(resp)

        raise APIError(0, f"Exhausted retries: {last_exc}")


# ── Helpers ─────────────────────────────────────────────────────────


def _user_agent() -> str:
    from goulburn import __version__ as version
    return f"goulburn-sdk-python/{version}"


async def _async_sleep(seconds: float) -> None:
    """Indirection so tests can patch sleep without touching asyncio."""
    import asyncio
    await asyncio.sleep(seconds)
