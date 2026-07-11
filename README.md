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

Open [goulburn.ai/settings](https://goulburn.ai/settings) and create a key under "SDK & CLI keys". Copy the `gbok_...` token. It is shown only once.

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

- `GOULBURN_API_KEY`: your Owner API key (starts with `gbok_`).
- `GOULBURN_API_BASE`: defaults to `https://api.goulburn.ai`. Override for local development.

Or pass them explicitly:

```python
Client(api_key="gbok_...", base_url="https://api.goulburn.ai")
```

## What's in v0.2

The supported surface, all available in both async (`Client`) and sync (`SyncClient`) flavours:

| CLI | Python | Endpoint |
|---|---|---|
| `goulburn auth verify` | `client.auth.verify()` | `GET /api/v1/owner/me` |
| `goulburn agents list` | `client.agents.list()` | `GET /api/v1/agents/mine` |
| `goulburn agents get <name>` | `client.agents.get(name)` | `GET /api/v1/agents/{name}` |
| `goulburn probe run <name> --kind <k>` | `client.probes.run(name, kind=...)` | `POST /api/v1/agents/{name}/probe/run` |
| `goulburn trust query <name>` | `client.trust.profile(name)` | `GET /api/v1/trust/profile/{name}` |

Future releases add the CI Gate GitHub Action, webhook signing, Terraform provider, and self-hosted probe runner integration. See the [roadmap](https://github.com/Goulburn-ai/goulburn-sdk-python/issues) for what's coming.

## Example: a CI-style smoke check

```bash
# In your CI pipeline, after a deploy:
goulburn probe run my_agent --kind compliance
goulburn trust query my_agent
# Pipe to `jq` if you want to fail the build on a tier drop.
goulburn trust query my_agent --json | jq -e '.overall_score >= 60'
```

## License

MIT. See [LICENSE](LICENSE).
