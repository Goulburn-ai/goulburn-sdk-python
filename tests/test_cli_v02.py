"""CLI v0.2 commands."""
import httpx
import pytest
import respx
from click.testing import CliRunner

from goulburn.cli import cli


@pytest.fixture
def respx_mock():
    with respx.mock(base_url="https://api.example.com", assert_all_called=False) as r:
        yield r


def _common_args():
    return ["--api-key", "gbok_test", "--base-url", "https://api.example.com"]


def test_agents_list_renders(respx_mock):
    respx_mock.get("/api/v1/agents/mine").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"name": "alpha", "description": "first agent"},
                    {"name": "beta", "description": "second"},
                ],
                "next_cursor": None,
                "has_more": False,
            },
        )
    )
    result = CliRunner().invoke(cli, [*_common_args(), "agents", "list"])
    assert result.exit_code == 0, result.output
    assert "alpha" in result.output
    assert "beta" in result.output
    assert "2 agent(s)" in result.output


def test_agents_list_empty(respx_mock):
    respx_mock.get("/api/v1/agents/mine").mock(
        return_value=httpx.Response(200, json={"data": [], "next_cursor": None, "has_more": False})
    )
    result = CliRunner().invoke(cli, [*_common_args(), "agents", "list"])
    assert result.exit_code == 0
    assert "No agents found" in result.output


def test_agents_get_renders_json(respx_mock):
    respx_mock.get("/api/v1/agents/myagent").mock(
        return_value=httpx.Response(
            200,
            json={"name": "myagent", "description": "x", "status": "active"},
        )
    )
    result = CliRunner().invoke(cli, [*_common_args(), "agents", "get", "myagent"])
    assert result.exit_code == 0
    assert '"name"' in result.output
    assert '"myagent"' in result.output


def test_agents_get_404_exits_nonzero(respx_mock):
    respx_mock.get("/api/v1/agents/nope").mock(
        return_value=httpx.Response(404, json={"detail": "no"})
    )
    result = CliRunner().invoke(cli, [*_common_args(), "agents", "get", "nope"])
    assert result.exit_code == 3


def test_probe_run_compliance(respx_mock):
    respx_mock.post("/api/v1/agents/x/probe/run").mock(
        return_value=httpx.Response(200, json={"probe_ids": ["a", "b"]})
    )
    result = CliRunner().invoke(
        cli, [*_common_args(), "probe", "run", "x", "--kind", "compliance"]
    )
    assert result.exit_code == 0
    assert "probe_ids" in result.output


def test_probe_run_rejects_invalid_kind(respx_mock):
    result = CliRunner().invoke(cli, [*_common_args(), "probe", "run", "x", "--kind", "bogus"])
    assert result.exit_code != 0
    assert "bogus" in result.output.lower() or "invalid" in result.output.lower()


def test_trust_query_human_output(respx_mock):
    respx_mock.get("/api/v1/trust/profile/y").mock(
        return_value=httpx.Response(
            200,
            json={
                "agent": "y",
                "tier": "verified",
                "overall_score": 60,
                "layers": {
                    "identity": {"score": 80},
                    "compliance": {"score": 70},
                },
            },
        )
    )
    result = CliRunner().invoke(cli, [*_common_args(), "trust", "query", "y"])
    assert result.exit_code == 0
    assert "verified" in result.output
    assert "60" in result.output
    assert "identity" in result.output


def test_trust_query_json_flag(respx_mock):
    respx_mock.get("/api/v1/trust/profile/y").mock(
        return_value=httpx.Response(
            200, json={"agent": "y", "tier": "v", "overall_score": 1, "layers": {}}
        )
    )
    result = CliRunner().invoke(cli, [*_common_args(), "trust", "query", "y", "--json"])
    assert result.exit_code == 0
    assert '"agent"' in result.output
    assert '"layers"' in result.output
