"""goulburn — Python SDK + CLI for the goulburn.ai Trust API.

Public surface:

    from goulburn import Client, SyncClient
    from goulburn import (
        AuthenticationError,
        APIError,
        GoulburnError,
        RateLimitError,
    )

Authentication uses Owner API keys (gbok_ prefix) minted from
https://goulburn.ai/settings → "SDK & CLI keys". Pass the key via
the GOULBURN_API_KEY environment variable, or explicitly to the
client constructor.
"""

from goulburn._client import Client, SyncClient
from goulburn._errors import (
    APIError,
    AuthenticationError,
    GoulburnError,
    NotFoundError,
    RateLimitError,
)
from goulburn._models import Owner

__version__ = "0.1.0"
__all__ = [
    "Client",
    "SyncClient",
    "Owner",
    "GoulburnError",
    "APIError",
    "AuthenticationError",
    "NotFoundError",
    "RateLimitError",
    "__version__",
]
