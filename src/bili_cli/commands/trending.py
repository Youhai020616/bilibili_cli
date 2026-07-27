"""Trending/ranking commands."""

from __future__ import annotations

from typing import Any

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.browser.ranking import browser_ranking
from bili_cli.commands._common import fail
from bili_cli.errors import BiliError
from bili_cli.output import info, print_json, print_table, print_trending, success
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
    _show_trending(
        count=count,
        source=source,
        rid=rid,
        account=account,
        as_json=as_json,
        json_output=json_output,
        output=output,
        command="trending",
    )


@click.command("ranking", help="Show ranking videos")
@click.option("--count", type=int, default=20, help="Result count")
@click.option("--rid", type=int, default=0, help="Ranking category rid")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def ranking(
    count: int,
    rid: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    _show_trending(
        count=count,
        source="ranking",
        rid=rid,
        account=account,
        as_json=as_json,
        json_output=json_output,
        output=output,
        command="ranking",
    )


@click.command("hot-search", help="Show hot search words")
@click.option("--count", type=int, default=10, help="Result count")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def hot_search(
    count: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    json_mode = as_json or json_output
    client = BiliAPIClient.from_config(account)
    try:
        result = client.hot_search(count=count)
    except BiliError as exc:
        client.close()
        fail(exc, as_json=json_mode, command="hot-search", strategy="api")
    finally:
        client.close()
    items = result.get("items") or []
    if output:
        export_data(items, output)
        if not json_mode:
            success(f"Exported {len(items)} items to {output}")
    if json_mode:
        print_json(result, command="hot-search", strategy="api", account=account)
    else:
        _print_hot_search(result)


def _show_trending(
    *,
    count: int,
    source: str,
    rid: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
    command: str,
) -> None:
    json_mode = as_json or json_output
    client = BiliAPIClient.from_config(account)
    try:
        result = client.trending(count=count, source=source, rid=rid)
        strategy = "api"
        fallback_used = False
    except BiliError as exc:
        client.close()
        if source != "ranking":
            fail(exc, as_json=json_mode, command=command, strategy="api")
        if not json_mode:
            info("API ranking failed; trying browser fallback")
        try:
            result = browser_ranking(rid=rid, account=account, limit=count)
        except BiliError as browser_exc:
            fail(browser_exc, as_json=json_mode, command=command, strategy="browser")
        strategy = "browser"
        fallback_used = True
    finally:
        client.close()
    items = result.get("items") or []
    if output:
        export_data(items, output)
        if not json_mode:
            success(f"Exported {len(items)} items to {output}")
    if json_mode:
        print_json(result, command=command, strategy=strategy, fallback_used=fallback_used, account=account)
    else:
        print_trending(items, title=source)


def _print_hot_search(result: dict[str, Any]) -> None:
    items = result.get("items") or []
    rows = [[item.get("rank"), item.get("keyword"), item.get("show_name")] for item in items]
    print_table("Hot search", ["#", "Keyword", "Show"], rows)
