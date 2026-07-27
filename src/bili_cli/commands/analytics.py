"""Analytics and notification commands."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.commands._common import fail, wants_json
from bili_cli.errors import BiliError
from bili_cli.index_cache import load_index
from bili_cli.output import fmt_count, print_json, print_table, status, success
from bili_cli.publish_tasks import list_publish_tasks
from bili_cli.session import has_session
from bili_cli.utils.export import export_data


@click.command("analytics", help="Show account or video analytics")
@click.option("--video", default=None, help="Video id for video analytics")
@click.option("--account", default=None, help="Account profile name")
@click.option("--csv", "output", default=None, help="Export to CSV/JSON/YAML")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def analytics(video: str | None, account: str | None, output: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    if video:
        client = BiliAPIClient.from_config(account)
        try:
            detail = client.video_detail(video)
            tags = client.video_tags(video)
            related = client.video_related(video, limit=5)
            comments = client.comments(video, count=5)
        except BiliError as exc:
            client.close()
            fail(exc, as_json=json_mode, command="analytics", strategy="api")
        finally:
            client.close()
        result = {
            "mode": "video",
            "video": {
                "bvid": detail.get("bvid"),
                "aid": detail.get("aid"),
                "title": detail.get("title"),
                "owner": (detail.get("owner") or {}).get("name"),
                "views": (detail.get("stat") or {}).get("view"),
                "likes": (detail.get("stat") or {}).get("like"),
                "coins": (detail.get("stat") or {}).get("coin"),
                "favorites": (detail.get("stat") or {}).get("favorite"),
                "replies": (detail.get("stat") or {}).get("reply"),
                "url": detail.get("url"),
            },
            "tags": [item.get("tag_name") for item in tags],
            "related_count": len(related),
            "comment_total": comments.get("total"),
            "comment_sample": comments.get("comments") or [],
        }
        _export_or_print(result, output, json_mode=json_mode, command="analytics", strategy="api", account=account)
        return

    index = load_index()
    tasks = list_publish_tasks(limit=10)
    status_data = {
        "account": account or "default",
        "has_session": has_session(account),
        "search_cache_items": len(index.get("items") or []),
        "search_query": index.get("query"),
        "publish_tasks": len(tasks),
        "publish_statuses": dict(Counter(task.get("status") for task in tasks)),
        "recent_tasks": [
            {
                "task_id": task.get("task_id"),
                "status": task.get("status"),
                "title": (task.get("plan") or {}).get("title"),
            }
            for task in tasks[:5]
        ],
    }
    _export_or_print(status_data, output, json_mode=json_mode, command="analytics", strategy="local", account=account)


@click.command("notifications", help="Show unread notification counts")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def notifications(account: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    client = BiliAPIClient.from_config(account)
    try:
        result = client.notifications()
    except BiliError as exc:
        client.close()
        fail(exc, as_json=json_mode, command="notifications", strategy="api")
    finally:
        client.close()
    if json_mode:
        print_json(result, command="notifications", strategy="api", account=account)
    else:
        rows = [[key, value] for key, value in result.get("counts", {}).items()]
        print_table("Notification counts", ["Type", "Unread"], rows)


@click.command("messages", help="Show message session summary")
@click.option("--limit", type=int, default=20, help="Result limit")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def messages(limit: int, account: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    client = BiliAPIClient.from_config(account)
    try:
        result = client.messages(limit=limit)
    except BiliError as exc:
        client.close()
        fail(exc, as_json=json_mode, command="messages", strategy="api")
    finally:
        client.close()
    if json_mode:
        print_json(result, command="messages", strategy="api", account=account)
    else:
        rows = [[item.get("talker_id"), item.get("nickname"), fmt_count(item.get("unread")), item.get("last_text") or "-"] for item in result.get("items") or []]
        print_table("Message sessions", ["ID", "Name", "Unread", "Last message"], rows)


def _export_or_print(
    result: dict,
    output: str | None,
    *,
    json_mode: bool,
    command: str,
    strategy: str,
    account: str | None,
) -> None:
    if output:
        export_data(result, output)
        if not json_mode:
            success(f"Exported analytics to {Path(output).expanduser()}")
    if json_mode:
        print_json(result, command=command, strategy=strategy, account=account)
    else:
        _print_analytics(result)


def _print_analytics(result: dict) -> None:
    if result.get("mode") == "video":
        video = result.get("video") or {}
        status("Video", f"{video.get('title')} ({video.get('bvid')})")
        status("Owner", video.get("owner"))
        status("Views", fmt_count(video.get("views")))
        status("Likes", fmt_count(video.get("likes")))
        status("Coins", fmt_count(video.get("coins")))
        status("Favorites", fmt_count(video.get("favorites")))
        status("Replies", fmt_count(video.get("replies")))
        status("Related", fmt_count(result.get("related_count")))
        status("Comments", fmt_count(result.get("comment_total")))
        return
    status("Account", result.get("account"))
    status("Local session", "yes" if result.get("has_session") else "no")
    status("Search cache items", fmt_count(result.get("search_cache_items")))
    status("Publish tasks", fmt_count(result.get("publish_tasks")))
    status("Task statuses", result.get("publish_statuses"))
