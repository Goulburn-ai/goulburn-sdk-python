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


def main() -> None:
    """Setuptools / hatch entry point for the `goulburn` console script."""
    cli(obj={})  # pylint: disable=no-value-for-parameter


if __name__ == "__main__":
    main()
