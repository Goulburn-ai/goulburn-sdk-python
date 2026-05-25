"""SyncClient — symmetric coverage for the blocking client."""
import httpx
import pytest
import respx

from goulburn import AuthenticationError, Owner, SyncClient

OWNER_ME_PATH = "/api/v1/owner/me"
OWNER_PAYLOAD = {"owner_id": "x", "email": "a@b.c", "display_name": ""}


@pytest.fixture
def respx_mock():
    with respx.mock(base_url="https://api.example.com", assert_all_called=False) as r:
        yield r


def test_sync_verify(respx_mock):
    respx_mock.get(OWNER_ME_PATH).mock(return_value=httpx.Response(200, json=OWNER_PAYLOAD))
    with SyncClient(api_key="gbok_test", base_url="https://api.example.com") as gb:
        me = gb.auth.verify()
    assert isinstance(me, Owner)
    assert me.email == "a@b.c"


def test_sync_401(respx_mock):
    respx_mock.get(OWNER_ME_PATH).mock(return_value=httpx.Response(401, json={"detail": "no"}))
    with SyncClient(api_key="gbok_test", base_url="https://api.example.com") as gb:
        with pytest.raises(AuthenticationError):
            gb.auth.verify()


def test_sync_missing_api_key_raises():
    with pytest.raises(AuthenticationError):
        SyncClient(base_url="https://api.example.com")
