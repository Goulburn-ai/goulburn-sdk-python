"""v0.2 surface tests: agents.list/get, probes.run, trust.profile."""
from __future__ import annotations

import httpx
import pytest
import respx

from goulburn import Agent, AgentList, Client, ProbeRunResult, TrustProfile


@pytest.fixture
def respx_mock():
    with respx.mock(base_url="https://api.example.com", assert_all_called=False) as r:
        yield r


# ── agents.list ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agents_list_returns_typed_list(respx_mock):
    respx_mock.get("/api/v1/agents/mine").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"name": "alpha", "description": "first agent", "status": "active"},
                    {"name": "beta", "description": "second"},
                ],
                "next_cursor": None,
                "has_more": False,
            },
        )
    )
    async with Client(api_key="gbok_x", base_url="https://api.example.com") as gb:
        result = await gb.agents.list()
    assert isinstance(result, AgentList)
    assert len(result.data) == 2
    assert result.data[0].name == "alpha"
    assert result.data[0].description == "first agent"
    # extra='allow' preserves untyped fields
    assert result.data[0].status == "active"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_agents_list_empty(respx_mock):
    respx_mock.get("/api/v1/agents/mine").mock(
        return_value=httpx.Response(200, json={"data": [], "next_cursor": None, "has_more": False})
    )
    async with Client(api_key="gbok_x", base_url="https://api.example.com") as gb:
        result = await gb.agents.list()
    assert result.data == []
    assert result.has_more is False


# ── agents.get ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_agents_get_single_agent(respx_mock):
    respx_mock.get("/api/v1/agents/myagent").mock(
        return_value=httpx.Response(
            200,
            json={"name": "myagent", "description": "test", "endpoint_url": "https://x.example.com"},
        )
    )
    async with Client(api_key="gbok_x", base_url="https://api.example.com") as gb:
        agent = await gb.agents.get("myagent")
    assert isinstance(agent, Agent)
    assert agent.name == "myagent"
    assert agent.endpoint_url == "https://x.example.com"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_agents_get_404_raises_not_found(respx_mock):
    from goulburn import NotFoundError

    respx_mock.get("/api/v1/agents/nope").mock(
        return_value=httpx.Response(404, json={"detail": "Agent not found"})
    )
    async with Client(api_key="gbok_x", base_url="https://api.example.com") as gb:
        with pytest.raises(NotFoundError):
            await gb.agents.get("nope")


# ── probes.run ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_probe_run_compliance(respx_mock):
    route = respx_mock.post("/api/v1/agents/myagent/probe/run").mock(
        return_value=httpx.Response(200, json={"probe_ids": ["abc", "def"], "kind": "compliance"})
    )
    async with Client(api_key="gbok_x", base_url="https://api.example.com") as gb:
        result = await gb.probes.run("myagent", kind="compliance")
    assert isinstance(result, ProbeRunResult)
    assert route.calls.last.request.url.params["kind"] == "compliance"


@pytest.mark.asyncio
async def test_probe_run_capability(respx_mock):
    route = respx_mock.post("/api/v1/agents/myagent/probe/run").mock(
        return_value=httpx.Response(200, json={"probe_id": "xyz", "kind": "capability"})
    )
    async with Client(api_key="gbok_x", base_url="https://api.example.com") as gb:
        await gb.probes.run("myagent", kind="capability")
    assert route.calls.last.request.url.params["kind"] == "capability"


@pytest.mark.asyncio
async def test_probe_run_invalid_kind_raises_locally(respx_mock):
    """Local validation must reject bad kind without hitting the network."""
    async with Client(api_key="gbok_x", base_url="https://api.example.com") as gb:
        with pytest.raises(ValueError):
            await gb.probes.run("myagent", kind="something_else")


@pytest.mark.asyncio
async def test_probe_run_429_surfaces_rate_limit(respx_mock):
    from goulburn import RateLimitError

    respx_mock.post("/api/v1/agents/myagent/probe/run").mock(
        return_value=httpx.Response(
            429,
            json={"detail": "On-demand compliance probe already ran. Try again in 45m."},
            headers={"Retry-After": "2700"},
        )
    )
    async with Client(
        api_key="gbok_x",
        base_url="https://api.example.com",
        max_retries=0,
    ) as gb:
        with pytest.raises(RateLimitError) as exc:
            await gb.probes.run("myagent", kind="compliance")
    assert exc.value.retry_after_seconds == 2700


# ── trust.profile ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_trust_profile_returns_layers(respx_mock):
    payload = {
        "agent": "myagent",
        "tier": "verified",
        "overall_score": 67,
        "layers": {
            "identity": {"score": 80},
            "capability": {"score": 60},
            "track_record": {"score": 50},
            "social": {"score": 40},
            "compliance": {"score": 85},
        },
    }
    respx_mock.get("/api/v1/trust/profile/myagent").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with Client(api_key="gbok_x", base_url="https://api.example.com") as gb:
        profile = await gb.trust.profile("myagent")
    assert isinstance(profile, TrustProfile)
    assert profile.agent == "myagent"
    assert profile.overall_score == 67
    assert profile.layers["compliance"]["score"] == 85
