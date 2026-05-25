# goulburn

Python SDK and CLI for the [goulburn.ai](https://goulburn.ai) Trust API.

`pip install goulburn` gets you both a Python client library and a `goulburn` CLI that authenticates against your fleet using an Owner API key issued from [/settings](https://goulburn.ai/settings).

## Installation

```bash
pip install goulburn
```

Python 3.10 or later.

## Quick start

### 1. Mint an Owner API key

Open [goulburn.ai/settings](https://goulburn.ai/settings) and create a key under "SDK & CLI keys". Copy the `gbok_...` token — it's shown only once.

### 2. Verify auth from the CLI

```bash
export GOULBURN_API_KEY=gbok_...
goulburn auth verify
```

You'll see your owner identity if the key is valid.

### 3. Use the SDK from Python

```python
import asyncio
from goulburn import Client

async def main():
    async with Client() as gb:  # reads GOULBURN_API_KEY from env
        me = await gb.auth.verify()
        print(f"Signed in as {me.email}")

asyncio.run(main())
```

Or synchronously:

```python
from goulburn import SyncClient

with SyncClient() as gb:
    me = gb.auth.verify()
    print(f"Signed in as {me.email}")
```

## Configuration

- `GOULBURN_API_KEY` — your Owner API key (starts with `gbok_`).
- `GOULBURN_API_BASE` — defaults to `https://api.goulburn.ai`. Override for local development.

Or pass them explicitly:

```python
Client(api_key="gbok_...", base_url="https://api.goulburn.ai")
```

## What's in v0.1

This is the alpha release. The supported surface is intentionally small:

- `goulburn auth verify` / `client.auth.verify()` — confirm the API key is valid and surface the owner identity.

The next release expands to agent management, probe execution, trust score queries, and CI gate integration. See the [roadmap](https://github.com/Goulburn-ai/goulburn-sdk-python/issues) for what's coming.

## License

MIT. See [LICENSE](LICENSE).
