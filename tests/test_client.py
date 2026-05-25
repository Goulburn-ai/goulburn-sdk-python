"""Async client tests using respx to mock httpx.

These exercise the real Client class against a mocked transport — no
network calls. respx + httpx is the standard pattern for testing
httpx-based SDKs.
"""
import httpx
import pytest
import respx

from goulburn import (
    APIError,
    AuthenticationError,
    Client,
    NotFoundError,
    Owner,
    RateLimitError,
)

OWNER_ME_PATH = "/api/v1/owner/me"
OWNER_PAYLOAD = {
    "owner_id": "abc123",
    "email": "test@example.com",
    "display_name": "Test User",
}


@pytest.fixture
def respx_mock():
    with respx.mock(base_url="https://api.example.com", assert_all_called=False) as r:
        yield r


@pytest.mark.asyncio
async def test_auth_verify_returns_owner(respx_mock):
    respx_mock.get(OWNER_ME_PATH).mock(return_value=httpx.Response(200, json=OWNER_PAYLOAD))

    async with Client(api_key="gbok_test", base_url="https://api.example.com") as gb:
        owner = await gb.auth.verify()

    assert isinstance(owner, Owner)
    assert owner.email == "test@example.com"
    assert owner.owner_id == "abc123"
    assert owner.display_name == "Test User"


@pytest.mark.asyncio
async def test_authorization_header_is_bearer_owner_key(respx_mock):
    route = respx_mock.get(OWNER_ME_PATH).mock(return_value=httpx.Response(200, json=OWNER_PAYLOAD))

    async with Client(api_key="gbok_test", base_url="https://api.example.com") as gb:
        await gb.auth.verify()

    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer gbok_test"


@pytest.mark.asyncio
async def test_user_agent_identifies_sdk(respx_mock):
    route = respx_mock.get(OWNER_ME_PATH).mock(return_value=httpx.Response(200, json=OWNER_PAYLOAD))

    async with Client(api_key="gbok_test", base_url="https://api.example.com") as gb:
        await gb.auth.verify()

    ua = route.calls.last.request.headers["User-Agent"]
    assert ua.startswith("goulburn-sdk-python/")


@pytest.mark.asyncio
async def test_401_raises_authentication_error(respx_mock):
    respx_mock.get(OWNER_ME_PATH).mock(
        return_value=httpx.Response(401, json={"detail": "Invalid or revoked API key"})
    )

    async with Client(api_key="gbok_test", base_url="https://api.example.com") as gb:
        with pytest.raises(AuthenticationError) as exc:
            await gb.auth.verify()
    assert exc.value.status_code == 401
    assert "Invalid" in exc.value.detail


@pytest.mark.asyncio
async def test_404_raises_not_found_error(respx_mock):
    respx_mock.get(OWNER_ME_PATH).mock(return_value=httpx.Response(404, json={"detail": "nope"}))
    async with Client(api_key="gbok_test", base_url="https://api.example.com") as gb:
        with pytest.raises(NotFoundError):
            await gb.auth.verify()


@pytest.mark.asyncio
async def test_429_raises_rate_limit_with_retry_after(respx_mock):
    respx_mock.get(OWNER_ME_PATH).mock(
        return_value=httpx.Response(
            429,
            json={"detail": "too many"},
            headers={"Retry-After": "12"},
        )
    )
    async with Client(
        api_key="gbok_test",
        base_url="https://api.example.com",
        max_retries=0,  # surface the 429 to the caller without retrying
    ) as gb:
        with pytest.raises(RateLimitError) as exc:
            await gb.auth.verify()
    assert exc.value.status_code == 429
    assert exc.value.retry_after_seconds == 12


@pytest.mark.asyncio
async def test_retryable_5xx_then_success(respx_mock, monkeypatch):
    # Patch sleep so the test doesn't actually wait
    async def _no_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("goulburn._client._async_sleep", _no_sleep)

    respx_mock.get(OWNER_ME_PATH).mock(
        side_effect=[
            httpx.Response(503, json={"detail": "warming"}),
            httpx.Response(200, json=OWNER_PAYLOAD),
        ]
    )

    async with Client(api_key="gbok_test", base_url="https://api.example.com") as gb:
        owner = await gb.auth.verify()
    assert owner.email == "test@example.com"


@pytest.mark.asyncio
async def test_4xx_other_does_not_retry(respx_mock, monkeypatch):
    """400 is a caller error — must NOT retry."""
    calls = {"n": 0}

    def _handler(request):
        calls["n"] += 1
        return httpx.Response(400, json={"detail": "bad body"})

    respx_mock.get(OWNER_ME_PATH).mock(side_effect=_handler)

    async with Client(api_key="gbok_test", base_url="https://api.example.com", max_retries=5) as gb:
        with pytest.raises(APIError) as exc:
            await gb.auth.verify()
    assert exc.value.status_code == 400
    assert calls["n"] == 1  # exactly one attempt — no retry


def test_missing_api_key_raises_authentication_error():
    with pytest.raises(AuthenticationError) as exc:
        Client(base_url="https://api.example.com")
    assert "GOULBURN_API_KEY" in exc.value.detail or "API key" in exc.value.detail


def test_explicit_api_key_beats_env(monkeypatch):
    monkeypatch.setenv("GOULBURN_API_KEY", "gbok_env")
    c = Client(api_key="gbok_explicit", base_url="https://api.example.com")
    assert c._http.headers["Authorization"] == "Bearer gbok_explicit"


def test_env_api_key_used_when_no_explicit(monkeypatch):
    monkeypatch.setenv("GOULBURN_API_KEY", "gbok_env")
    c = Client(base_url="https://api.example.com")
    assert c._http.headers["Authorization"] == "Bearer gbok_env"


def test_base_url_default():
    c = Client(api_key="gbok_test")
    assert c._base_url == "https://api.goulburn.ai"


def test_base_url_env_override(monkeypatch):
    monkeypatch.setenv("GOULBURN_API_BASE", "https://api.staging.goulburn.ai")
    c = Client(api_key="gbok_test")
    assert c._base_url == "https://api.staging.goulburn.ai"


def test_base_url_explicit_beats_env(monkeypatch):
    monkeypatch.setenv("GOULBURN_API_BASE", "https://api.staging.goulburn.ai")
    c = Client(api_key="gbok_test", base_url="https://api.local")
    assert c._base_url == "https://api.local"
