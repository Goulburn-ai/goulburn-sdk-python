"""CLI tests using Click's CliRunner + respx-mocked HTTP."""
import httpx
import pytest
import respx
from click.testing import CliRunner

from goulburn.cli import cli

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


def test_auth_verify_success(respx_mock):
    respx_mock.get(OWNER_ME_PATH).mock(return_value=httpx.Response(200, json=OWNER_PAYLOAD))
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--api-key", "gbok_test", "--base-url", "https://api.example.com", "auth", "verify"],
    )
    assert result.exit_code == 0, result.output
    assert "test@example.com" in result.output
    assert "Test User" in result.output
    assert "abc123" in result.output


def test_auth_verify_401_exits_nonzero(respx_mock):
    respx_mock.get(OWNER_ME_PATH).mock(return_value=httpx.Response(401, json={"detail": "nope"}))
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--api-key", "gbok_test", "--base-url", "https://api.example.com", "auth", "verify"],
    )
    assert result.exit_code == 2
    assert "Auth failed" in result.output


def test_auth_verify_missing_key_exits_nonzero(monkeypatch):
    monkeypatch.delenv("GOULBURN_API_KEY", raising=False)
    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "verify"])
    assert result.exit_code != 0


def test_version_flag():
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "goulburn" in result.output.lower()
