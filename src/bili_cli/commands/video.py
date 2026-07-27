"""Video detail and comment commands."""

from __future__ import annotations

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.commands._common import fail, wants_json
from bili_cli.errors import BiliError
from bili_cli.index_cache import resolve_video_ref
from bili_cli.output import print_comments, print_json, print_search_results, print_video_detail, success
from bili_cli.utils.export import export_data


@click.group("video", help="Video commands")
def video_group() -> None:
    pass


@video_group.command("info", help="Show video detail")
@click.argument("video_id")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def video_info(video_id: str, account: str | None, as_json: bool, json_output: bool) -> None:
    _show_video_info(video_id, account=account, as_json=wants_json(as_json, json_output), command="video.info")


@click.command("detail", help="Show video detail, supports short index")
@click.argument("video_id")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def detail(video_id: str, account: str | None, as_json: bool, json_output: bool) -> None:
    _show_video_info(video_id, account=account, as_json=wants_json(as_json, json_output), command="detail")


@click.command("read", help="Read video detail from the last search result index")
@click.argument("index")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def read(index: str, account: str | None, as_json: bool, json_output: bool) -> None:
    _show_video_info(index, account=account, as_json=wants_json(as_json, json_output), command="read")


@video_group.command("pages", help="Show video pages")
@click.argument("video_id")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def pages(video_id: str, account: str | None, as_json: bool) -> None:
    video_id = resolve_video_ref(video_id)
    client = BiliAPIClient.from_config(account)
    try:
        result = client.video_detail(video_id)
    except BiliError as exc:
        client.close()
        fail(exc, as_json=as_json, command="video.pages", strategy="api")
    finally:
        client.close()
    page_items = result.get("pages") or []
    if as_json:
        print_json({"video": {"bvid": result.get("bvid"), "aid": result.get("aid")}, "pages": page_items}, command="video.pages", strategy="api", account=account)
    else:
        rows = [[p.get("page"), p.get("cid"), p.get("part") or "-", p.get("duration")] for p in page_items]
        from bili_cli.output import print_table

        print_table("Pages", ["Page", "CID", "Part", "Duration"], rows)


@video_group.command("tags", help="Show video tags")
@click.argument("video_id")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def tags(video_id: str, account: str | None, as_json: bool) -> None:
    video_id = resolve_video_ref(video_id)
    client = BiliAPIClient.from_config(account)
    try:
        items = client.video_tags(video_id)
    except BiliError as exc:
        client.close()
        fail(exc, as_json=as_json, command="video.tags", strategy="api")
    finally:
        client.close()
    if as_json:
        print_json({"tags": items}, command="video.tags", strategy="api", account=account)
    else:
        from bili_cli.output import print_table

        print_table("Tags", ["ID", "Name"], [[item.get("tag_id"), item.get("tag_name")] for item in items])


@video_group.command("related", help="Show related videos")
@click.argument("video_id")
@click.option("--limit", "--count", type=int, default=10, help="Result limit")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
def related(video_id: str, limit: int, account: str | None, as_json: bool) -> None:
    video_id = resolve_video_ref(video_id)
    client = BiliAPIClient.from_config(account)
    try:
        items = client.video_related(video_id, limit=limit)
    except BiliError as exc:
        client.close()
        fail(exc, as_json=as_json, command="video.related", strategy="api")
    finally:
        client.close()
    if as_json:
        print_json({"items": items}, command="video.related", strategy="api", account=account)
    else:
        print_search_results(items, "related")


@video_group.command("comments", help="Show video comments")
@click.argument("video_id")
@click.option("--count", type=int, default=20, help="Comment count")
@click.option("--sort", type=click.Choice(["hot", "new"]), default="hot", help="Comment sort")
@click.option("--replies", default=None, help="Reply thread rpid")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def video_comments(
    video_id: str,
    count: int,
    sort: str,
    replies: str | None,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    _show_comments(
        video_id,
        count=count,
        sort=sort,
        replies=replies,
        account=account,
        as_json=wants_json(as_json, json_output),
        output=output,
        command="video.comments",
    )


@click.command("comments", help="Show video comments, supports short index")
@click.argument("video_id")
@click.option("--count", type=int, default=20, help="Comment count")
@click.option("--sort", type=click.Choice(["hot", "new"]), default="hot", help="Comment sort")
@click.option("--replies", default=None, help="Reply thread rpid")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def comments(
    video_id: str,
    count: int,
    sort: str,
    replies: str | None,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    _show_comments(
        video_id,
        count=count,
        sort=sort,
        replies=replies,
        account=account,
        as_json=wants_json(as_json, json_output),
        output=output,
        command="comments",
    )


def _show_video_info(video_id: str, *, account: str | None, as_json: bool, command: str) -> None:
    video_id = resolve_video_ref(video_id)
    client = BiliAPIClient.from_config(account)
    try:
        result = client.video_detail(video_id)
    except BiliError as exc:
        client.close()
        fail(exc, as_json=as_json, command=command, strategy="api")
    finally:
        client.close()
    if as_json:
        print_json(result, command=command, strategy="api", account=account)
    else:
        print_video_detail(result)


def _show_comments(
    video_id: str,
    *,
    count: int,
    sort: str,
    replies: str | None,
    account: str | None,
    as_json: bool,
    output: str | None,
    command: str,
) -> None:
    video_id = resolve_video_ref(video_id)
    client = BiliAPIClient.from_config(account)
    try:
        result = client.comments(video_id, count=count, sort=sort, replies_to=replies)
    except BiliError as exc:
        client.close()
        fail(exc, as_json=as_json, command=command, strategy="api")
    finally:
        client.close()
    comments_data = result.get("comments") or []
    if output:
        export_data(comments_data, output)
        if not as_json:
            success(f"Exported {len(comments_data)} comments to {output}")
    if as_json:
        print_json(result, command=command, strategy="api", account=account)
    else:
        print_comments(comments_data)
