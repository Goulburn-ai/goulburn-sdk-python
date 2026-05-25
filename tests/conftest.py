"""Test harness for the goulburn SDK.

Environment isolation: clear GOULBURN_API_KEY / GOULBURN_API_BASE so a
developer's real key doesn't leak into the test run.
"""
import pytest


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("GOULBURN_API_KEY", raising=False)
    monkeypatch.delenv("GOULBURN_API_BASE", raising=False)
