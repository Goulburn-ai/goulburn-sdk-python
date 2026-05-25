"""SyncClient v0.2 surface — symmetry check."""
import httpx
import pytest
import respx

from goulburn import SyncClient


@pytest.fixture
def respx_mock():
    with respx.mock(base_url="https://api.example.com", assert_all_called=False) as r:
        yield r


def test_sync_agents_list(respx_mock):
    respx_mock.get("/api/v1/agents/mine").mock(
        return_value=httpx.Response(
            200,
            json={"data": [{"name": "alpha"}], "next_cursor": None, "has_more": False},
        )
    )
    with SyncClient(api_key="gbok_x", base_url="https://api.example.com") as gb:
        result = gb.agents.list()
    assert result.data[0].name == "alpha"


def test_sync_probe_run(respx_mock):
    respx_mock.post("/api/v1/agents/x/probe/run").mock(
        return_value=httpx.Response(200, json={"probe_id": "z"})
    )
    with SyncClient(api_key="gbok_x", base_url="https://api.example.com") as gb:
        result = gb.probes.run("x", kind="compliance")
    assert "probe_id" in result.model_dump()


def test_sync_trust_profile(respx_mock):
    respx_mock.get("/api/v1/trust/profile/y").mock(
        return_value=httpx.Response(
            200,
            json={"agent": "y", "tier": "identified", "overall_score": 30, "layers": {}},
        )
    )
    with SyncClient(api_key="gbok_x", base_url="https://api.example.com") as gb:
        profile = gb.trust.profile("y")
    assert profile.agent == "y"
