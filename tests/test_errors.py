"""Exception taxonomy tests — the public catch-everything contract."""
from goulburn import APIError, AuthenticationError, GoulburnError, NotFoundError, RateLimitError


def test_all_errors_inherit_from_goulburn_error():
    for klass in (APIError, AuthenticationError, NotFoundError, RateLimitError):
        assert issubclass(klass, GoulburnError)


def test_specific_errors_inherit_from_api_error():
    for klass in (AuthenticationError, NotFoundError, RateLimitError):
        assert issubclass(klass, APIError)


def test_api_error_carries_status_and_detail():
    e = APIError(500, "boom", body={"detail": "boom"})
    assert e.status_code == 500
    assert e.detail == "boom"
    assert e.body == {"detail": "boom"}
    assert "500" in str(e)


def test_rate_limit_error_carries_retry_after():
    e = RateLimitError(429, "slow down", retry_after_seconds=42)
    assert e.retry_after_seconds == 42
