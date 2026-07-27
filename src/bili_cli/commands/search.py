"""Search command."""

from __future__ import annotations

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.browser.search import browser_search
from bili_cli.commands._common import fail, wants_json
from bili_cli.constants import SEARCH_ORDER_MAP, SEARCH_TYPE_MAP
from bili_cli.errors import BiliError
from bili_cli.index_cache import save_index
from bili_cli.output import info, print_json, print_search_results, success
from bili_cli.utils.export import export_data


@click.command("search", help="Search Bilibili content")
@click.argument("keyword")
@click.option("--type", "search_type", type=click.Choice(list(SEARCH_TYPE_MAP.keys())), default="video", help="Search type")
@click.option("--sort", type=click.Choice(list(SEARCH_ORDER_MAP.keys())), default="default", help="Video search sort")
@click.option("--limit", "--count", type=int, default=20, help="Result limit")
@click.option("--page", type=int, default=1, help="Result page")
@click.option("--account", default=None, help="Account profile name")
@click.option("--browser-fallback", is_flag=True, help="Use headed browser fallback if API search is blocked")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def search(
    keyword: str,
    search_type: str,
    sort: str,
    limit: int,
    page: int,
    account: str | None,
    browser_fallback: bool,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    json_mode = wants_json(as_json, json_output)
    client = BiliAPIClient.from_config(account)
    if not json_mode:
        info(f"Searching [{search_type}]: {keyword}")
    try:
        result = client.search(keyword=keyword, search_type=search_type, limit=limit, page=page, order=sort)
    except BiliError as exc:
        client.close()
        if not browser_fallback or search_type != "video":
            fail(exc, as_json=json_mode, command="search", strategy="api")
        if not json_mode:
            info("API search failed; trying browser fallback")
        try:
            result = browser_search(keyword, account=account, limit=limit)
        except BiliError as browser_exc:
            fail(browser_exc, as_json=json_mode, command="search", strategy="browser")
        strategy = "browser"
        fallback_used = True
    else:
        strategy = "api"
        fallback_used = False
    finally:
        client.close()

    items = result.get("items") or []
    save_index(items, query=keyword, item_type=search_type)
    if output:
        export_data(items, output)
        if not json_mode:
            success(f"Exported {len(items)} items to {output}")
    if json_mode:
        print_json(result, command="search", strategy=strategy, fallback_used=fallback_used, account=account)
    else:
        print_search_results(items, keyword)
