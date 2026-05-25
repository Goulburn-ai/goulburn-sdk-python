"""goulburn CLI entry point — `goulburn <command>`.

Phase 1a scope: one working command (`auth verify`). Subsequent phases
expand under the same root.

Configuration:
- GOULBURN_API_KEY env var (or --api-key)
- GOULBURN_API_BASE env var (or --base-url)
"""
from __future__ import annotations

import sys

import click

from goulburn import SyncClient, __version__
from goulburn._errors import (
    APIError,
    AuthenticationError,
    GoulburnError,
)


@click.group(help="goulburn CLI — manage your fleet from the terminal.")
@click.version_option(__version__, prog_name="goulburn")
@click.option(
    "--api-key",
    envvar="GOULBURN_API_KEY",
    help="Owner API key. Defaults to $GOULBURN_API_KEY.",
)
@click.option(
    "--base-url",
    envvar="GOULBURN_API_BASE",
    default=None,
    help="Override the API base URL. Defaults to $GOULBURN_API_BASE.",
)
@click.pass_context
def cli(ctx: click.Context, api_key: str | None, base_url: str | None) -> None:
    ctx.ensure_object(dict)
    ctx.obj["api_key"] = api_key
    ctx.obj["base_url"] = base_url


# ── auth subcommands ────────────────────────────────────────────────


@cli.group(help="Authentication helpers.")
def auth() -> None:  # noqa: D401 — Click group docstring is its help text
    pass


@auth.command("verify", help="Confirm the API key works and show your identity.")
@click.pass_context
def auth_verify(ctx: click.Context) -> None:
    api_key = ctx.obj.get("api_key")
    base_url = ctx.obj.get("base_url")
    try:
        with SyncClient(api_key=api_key, base_url=base_url) as gb:
            me = gb.auth.verify()
    except AuthenticationError as e:
        click.echo(f"Auth failed: {e.detail}", err=True)
        sys.exit(2)
    except APIError as e:
        click.echo(f"API error ({e.status_code}): {e.detail}", err=True)
        sys.exit(3)
    except GoulburnError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(4)

    click.echo(f"Signed in as: {me.email}")
    if me.display_name:
        click.echo(f"Display name: {me.display_name}")
    click.echo(f"Owner ID:     {me.owner_id}")





# ── agents subcommands ──────────────────────────────────────────────


@cli.group(help="Manage your agents.")
def agents() -> None:
    pass


@agents.command("list", help="List agents owned by the authenticated owner.")
@click.pass_context
def agents_list(ctx: click.Context) -> None:
    api_key = ctx.obj.get("api_key")
    base_url = ctx.obj.get("base_url")
    try:
        with SyncClient(api_key=api_key, base_url=base_url) as gb:
            result = gb.agents.list()
    except AuthenticationError as e:
        click.echo(f"Auth failed: {e.detail}", err=True)
        sys.exit(2)
    except APIError as e:
        click.echo(f"API error ({e.status_code}): {e.detail}", err=True)
        sys.exit(3)
    except GoulburnError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(4)

    if not result.data:
        click.echo("No agents found. Register one at https://goulburn.ai/agents/register")
        return
    click.echo(f"{len(result.data)} agent(s):")
    for a in result.data:
        # Description may be long; truncate for the list view.
        desc = (a.description or "").replace("\n", " ")
        if len(desc) > 60:
            desc = desc[:57] + "..."
        click.echo(f"  - {a.name}  {desc}")


@agents.command("get", help="Show details for one agent.")
@click.argument("name")
@click.pass_context
def agents_get(ctx: click.Context, name: str) -> None:
    api_key = ctx.obj.get("api_key")
    base_url = ctx.obj.get("base_url")
    try:
        with SyncClient(api_key=api_key, base_url=base_url) as gb:
            agent = gb.agents.get(name)
    except AuthenticationError as e:
        click.echo(f"Auth failed: {e.detail}", err=True)
        sys.exit(2)
    except APIError as e:
        click.echo(f"API error ({e.status_code}): {e.detail}", err=True)
        sys.exit(3)
    except GoulburnError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(4)

    # Use model_dump to get the full extra='allow' payload, not just typed fields.
    body = agent.model_dump()
    # Drop nulls for cleaner human-readable output
    body = {k: v for k, v in body.items() if v is not None}
    import json as _json
    click.echo(_json.dumps(body, indent=2, default=str))


# ── probe subcommands ──────────────────────────────────────────────


@cli.group(help="Run probes against your agents.")
def probe() -> None:
    pass


@probe.command("run", help="Trigger an on-demand probe.")
@click.argument("agent_name")
@click.option(
    "--kind",
    type=click.Choice(["compliance", "capability"]),
    required=True,
    help="Probe type: compliance (3-probe safety suite) or capability (behavioural drift).",
)
@click.pass_context
def probe_run(ctx: click.Context, agent_name: str, kind: str) -> None:
    api_key = ctx.obj.get("api_key")
    base_url = ctx.obj.get("base_url")
    try:
        with SyncClient(api_key=api_key, base_url=base_url) as gb:
            result = gb.probes.run(agent_name, kind=kind)
    except AuthenticationError as e:
        click.echo(f"Auth failed: {e.detail}", err=True)
        sys.exit(2)
    except APIError as e:
        click.echo(f"API error ({e.status_code}): {e.detail}", err=True)
        sys.exit(3)
    except GoulburnError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(4)

    body = {k: v for k, v in result.model_dump().items() if v is not None}
    import json as _json
    click.echo(_json.dumps(body, indent=2, default=str))


# ── trust subcommands ──────────────────────────────────────────────


@cli.group(help="Trust score queries.")
def trust() -> None:
    pass


@trust.command("query", help="Show the full trust profile for an agent.")
@click.argument("agent_name")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
@click.pass_context
def trust_query(ctx: click.Context, agent_name: str, as_json: bool) -> None:
    api_key = ctx.obj.get("api_key")
    base_url = ctx.obj.get("base_url")
    try:
        with SyncClient(api_key=api_key, base_url=base_url) as gb:
            profile = gb.trust.profile(agent_name)
    except APIError as e:
        click.echo(f"API error ({e.status_code}): {e.detail}", err=True)
        sys.exit(3)
    except GoulburnError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(4)

    if as_json:
        import json as _json
        click.echo(_json.dumps(profile.model_dump(), indent=2, default=str))
        return

    click.echo(f"Agent:         {profile.agent}")
    click.echo(f"Tier:          {profile.tier}")
    click.echo(f"Overall score: {profile.overall_score}")
    click.echo("Layers:")
    for layer_name, layer_data in (profile.layers or {}).items():
        score = layer_data.get("score") if isinstance(layer_data, dict) else None
        click.echo(f"  {layer_name:<14} {score}")


def main() -> None:
    """Setuptools / hatch entry point for the `goulburn` console script."""
    cli(obj={})  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
