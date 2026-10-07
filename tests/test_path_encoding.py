"""Agent names are caller input and must stay inside one path segment.

Regression for the path-injection finding (2026-09-09): before encoding,
httpx resolved agents.get("../owner/me") to GET /api/v1/owner/me.
"""
import httpx
import pytest
import respx

from goulburn import Client, NotFoundError, SyncClient

BASE = "https://api.example.com"
HOSTILE = [
    ("../owner/me", "/api/v1/agents/..%2Fowner%2Fme"),
    ("a?admin=1", "/api/v1/agents/a%3Fadmin%3D1"),
    ("a#frag", "/api/v1/agents/a%23frag"),
    ("a/b", "/api/v1/agents/a%2Fb"),
    ("has space", "/api/v1/agents/has%20space"),
]


def _raw_path(request: httpx.Request) -> str:
    return request.url.raw_path.decode()


@pytest.fixture
def mock():
    with respx.mock(base_url=BASE, assert_all_called=False) as r:
        r.route().mock(return_value=httpx.Response(404, json={"detail": "nf"}))
        yield r


@pytest.mark.parametrize("name,expected", HOSTILE)
def test_sync_agents_get_stays_in_segment(mock, name, expected):
    with SyncClient(api_key="gbok_test", base_url=BASE) as gb, pytest.raises(NotFoundError):
        gb.agents.get(name)
    assert _raw_path(mock.calls.last.request) == expected


@pytest.mark.parametrize("name,expected", HOSTILE)
def test_sync_trust_profile_stays_in_segment(mock, name, expected):
    with SyncClient(api_key="gbok_test", base_url=BASE) as gb, pytest.raises(NotFoundError):
        gb.trust.profile(name)
    assert _raw_path(mock.calls.last.request) == expected.replace(
        "/api/v1/agents/", "/api/v1/trust/profile/"
    )


def test_sync_probe_run_stays_in_segment(mock):
    with SyncClient(api_key="gbok_test", base_url=BASE, max_retries=0) as gb:
        with pytest.raises(NotFoundError):
            gb.probes.run("../owner/me", kind="compliance")
    req = mock.calls.last.request
    assert req.url.raw_path.decode().split("?")[0] == "/api/v1/agents/..%2Fowner%2Fme/probe/run"
    assert req.url.params["kind"] == "compliance"


@pytest.mark.asyncio
@pytest.mark.parametrize("name,expected", HOSTILE)
async def test_async_agents_get_stays_in_segment(mock, name, expected):
    async with Client(api_key="gbok_test", base_url=BASE) as gb:
        with pytest.raises(NotFoundError):
            await gb.agents.get(name)
    assert _raw_path(mock.calls.last.request) == expected


@pytest.mark.parametrize("bad", ["", ".", "..", "a\nb", "a\x00b", "a\x7fb"])
def test_unrepresentable_names_rejected_before_any_request(mock, bad):
    with SyncClient(api_key="gbok_test", base_url=BASE) as gb, pytest.raises(ValueError):
        gb.agents.get(bad)
    assert not mock.calls


def test_ordinary_name_unchanged(mock):
    with SyncClient(api_key="gbok_test", base_url=BASE) as gb, pytest.raises(NotFoundError):
        gb.agents.get("Trust-Agent_01")
    assert _raw_path(mock.calls.last.request) == "/api/v1/agents/Trust-Agent_01"
