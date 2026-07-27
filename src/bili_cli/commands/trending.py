"""Trending/ranking commands."""

from __future__ import annotations

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.commands._common import fail
from bili_cli.errors import BiliError
from bili_cli.output import print_json, print_trending, success
from bili_cli.utils.export import export_data


@click.command("trending", help="Show popular/ranking videos")
@click.option("--count", type=int, default=20, help="Result count")
@click.option("--source", type=click.Choice(["popular", "ranking"]), default="popular", help="Source list")
@click.option("--rid", type=int, default=0, help="Ranking category rid")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def trending(
    count: int,
    source: str,
    rid: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    json_mode = as_json or json_output
    client = BiliAPIClient.from_config(account)
    try:
        result = client.trending(count=count, source=source, rid=rid)
    except BiliError as exc:
        client.close()
        fail(exc, as_json=json_mode, command="trending", strategy="api")
    finally:
        client.close()
    items = result.get("items") or []
    if output:
        export_data(items, output)
        if not json_mode:
            success(f"Exported {len(items)} items to {output}")
    if json_mode:
        print_json(result, command="trending", strategy="api", account=account)
    else:
        print_trending(items, title=source)
