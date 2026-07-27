"""Account write interaction commands."""

from __future__ import annotations

from typing import Any, Callable

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.audit import write_audit_event
from bili_cli.commands._common import fail, wants_json
from bili_cli.errors import BiliError
from bili_cli.index_cache import resolve_video_ref, save_index
from bili_cli.output import fmt_count, print_json, print_search_results, print_table, status, success
from bili_cli.utils.export import export_data


@click.command("like", help="Like or unlike a video")
@click.argument("video_id")
@click.option("--unlike", is_flag=True, help="Cancel like")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Execute the write action")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def like(video_id: str, unlike: bool, dry_run: bool, yes: bool, account: str | None, as_json: bool, json_output: bool) -> None:
    video_ref = resolve_video_ref(video_id)
    target = _video_target(video_ref, account=account, as_json=wants_json(as_json, json_output), command="like")
    _write_action(
        command="like",
        action="unlike" if unlike else "like",
        target=target,
        account=account,
        dry_run=dry_run,
        yes=yes,
        as_json=wants_json(as_json, json_output),
        execute=lambda client: client.like_video(video_ref, unlike=unlike),
    )


@click.command("coin", help="Give coins to a video")
@click.argument("video_id")
@click.option("--count", type=click.IntRange(1, 2), default=1, help="Coin count")
@click.option("--select-like", is_flag=True, help="Also like the video")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Execute the write action")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def coin(
    video_id: str,
    count: int,
    select_like: bool,
    dry_run: bool,
    yes: bool,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    video_ref = resolve_video_ref(video_id)
    target = {**_video_target(video_ref, account=account, as_json=wants_json(as_json, json_output), command="coin"), "coin_count": count}
    _write_action(
        command="coin",
        action="coin",
        target=target,
        account=account,
        dry_run=dry_run,
        yes=yes,
        as_json=wants_json(as_json, json_output),
        execute=lambda client: client.coin_video(video_ref, count=count, select_like=select_like),
    )


@click.command("follow", help="Follow or unfollow a user")
@click.argument("mid")
@click.option("--unfollow", is_flag=True, help="Cancel follow")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Execute the write action")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def follow(mid: str, unfollow: bool, dry_run: bool, yes: bool, account: str | None, as_json: bool, json_output: bool) -> None:
    _write_action(
        command="follow",
        action="unfollow" if unfollow else "follow",
        target={"mid": str(mid), "url": f"https://space.bilibili.com/{mid}"},
        account=account,
        dry_run=dry_run,
        yes=yes,
        as_json=wants_json(as_json, json_output),
        execute=lambda client: client.follow_user(mid, unfollow=unfollow),
    )


@click.group("favorite", help="Favorite folder interactions")
def favorite_group() -> None:
    pass


@favorite_group.command("folders", help="List your favorite folders")
@click.option("--limit", "--count", type=int, default=50, help="Result limit")
@click.option("--page", type=int, default=1, help="Result page")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def favorite_folders(limit: int, page: int, account: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    client = BiliAPIClient.from_config(account)
    try:
        result = client.favorite_folders(limit=limit, page=page)
    except BiliError as exc:
        fail(exc, as_json=json_mode, command="favorite.folders", strategy="api")
    finally:
        client.close()
    if json_mode:
        print_json(result, command="favorite.folders", strategy="api", account=account)
    else:
        rows = [[item.get("id"), item.get("title"), item.get("media_count")] for item in result.get("items") or []]
        print_table("Favorite folders", ["ID", "Title", "Media"], rows)


@favorite_group.command("items", help="List items in a favorite folder")
@click.argument("folder_id")
@click.option("--limit", "--count", type=int, default=20, help="Result limit")
@click.option("--page", type=int, default=1, help="Result page")
@click.option("--keyword", default="", help="Filter by keyword")
@click.option("--order", type=click.Choice(["mtime", "view", "pubtime"]), default="mtime", help="Sort order")
@click.option("--media-type", type=int, default=0, help="Bilibili media type, 0 means all")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export items to .json/.csv/.yaml")
def favorite_items(
    folder_id: str,
    limit: int,
    page: int,
    keyword: str,
    order: str,
    media_type: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    json_mode = wants_json(as_json, json_output)
    client = BiliAPIClient.from_config(account)
    try:
        result = client.favorite_resources(
            folder_id,
            limit=limit,
            page=page,
            keyword=keyword,
            order=order,
            media_type=media_type,
        )
    except BiliError as exc:
        fail(exc, as_json=json_mode, command="favorite.items", strategy="api")
    finally:
        client.close()

    items = result.get("items") or []
    save_index(items, query=f"favorite:{folder_id}:items", item_type="video")
    if output:
        export_data(items, output)
        if not json_mode:
            success(f"Exported {len(items)} items to {output}")
    if json_mode:
        print_json(result, command="favorite.items", strategy="api", account=account)
    else:
        folder = result.get("folder") or {}
        status("Folder", f"{folder.get('title') or folder_id} ({folder.get('id') or folder_id})")
        status("Items", f"{len(items)} shown / {fmt_count(folder.get('media_count'))} total")
        print_search_results(items, folder.get("title") or f"favorite {folder_id}")


favorite_group.add_command(favorite_items, "list")


@favorite_group.command("add", help="Add a video to a favorite folder")
@click.argument("video_id")
@click.option("--folder", "folder_id", required=True, help="Favorite folder id")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Execute the write action")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def favorite_add(
    video_id: str,
    folder_id: str,
    dry_run: bool,
    yes: bool,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    _favorite_video(video_id, folder_id, remove=False, dry_run=dry_run, yes=yes, account=account, as_json=wants_json(as_json, json_output))


@favorite_group.command("remove", help="Remove a video from a favorite folder")
@click.argument("video_id")
@click.option("--folder", "folder_id", required=True, help="Favorite folder id")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Execute the write action")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def favorite_remove(
    video_id: str,
    folder_id: str,
    dry_run: bool,
    yes: bool,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    _favorite_video(video_id, folder_id, remove=True, dry_run=dry_run, yes=yes, account=account, as_json=wants_json(as_json, json_output))


@click.group("watchlater", help="Watch later interactions")
def watchlater_group() -> None:
    pass


@watchlater_group.command("add", help="Add a video to watch later")
@click.argument("video_id")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Execute the write action")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def watchlater_add(video_id: str, dry_run: bool, yes: bool, account: str | None, as_json: bool, json_output: bool) -> None:
    video_ref = resolve_video_ref(video_id)
    target = _video_target(video_ref, account=account, as_json=wants_json(as_json, json_output), command="watchlater.add")
    _write_action(
        command="watchlater.add",
        action="watchlater.add",
        target=target,
        account=account,
        dry_run=dry_run,
        yes=yes,
        as_json=wants_json(as_json, json_output),
        execute=lambda client: client.watchlater_add(video_ref),
    )


@click.group("comment", help="Comment write interactions")
def comment_group() -> None:
    pass


@comment_group.command("post", help="Post a comment to a video")
@click.argument("video_id")
@click.argument("message")
@click.option("--root", default=None, help="Root rpid for reply thread")
@click.option("--parent", default=None, help="Parent rpid for nested reply")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Execute the write action")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def comment_post(
    video_id: str,
    message: str,
    root: str | None,
    parent: str | None,
    dry_run: bool,
    yes: bool,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    video_ref = resolve_video_ref(video_id)
    target = {
        **_video_target(video_ref, account=account, as_json=wants_json(as_json, json_output), command="comment.post"),
        "message_length": len(message),
        "root": root,
        "parent": parent,
    }
    _write_action(
        command="comment.post",
        action="comment.post",
        target=target,
        account=account,
        dry_run=dry_run,
        yes=yes,
        as_json=wants_json(as_json, json_output),
        execute=lambda client: client.comment_post(video_ref, message, root=root, parent=parent),
    )


@comment_group.command("delete", help="Delete a comment from a video")
@click.argument("video_id")
@click.argument("rpid")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Execute the write action")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def comment_delete(
    video_id: str,
    rpid: str,
    dry_run: bool,
    yes: bool,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    video_ref = resolve_video_ref(video_id)
    target = {**_video_target(video_ref, account=account, as_json=wants_json(as_json, json_output), command="comment.delete"), "rpid": rpid}
    _write_action(
        command="comment.delete",
        action="comment.delete",
        target=target,
        account=account,
        dry_run=dry_run,
        yes=yes,
        as_json=wants_json(as_json, json_output),
        execute=lambda client: client.comment_delete(video_ref, rpid=rpid),
    )


def _favorite_video(
    video_id: str,
    folder_id: str,
    *,
    remove: bool,
    dry_run: bool,
    yes: bool,
    account: str | None,
    as_json: bool,
) -> None:
    video_ref = resolve_video_ref(video_id)
    target = {**_video_target(video_ref, account=account, as_json=as_json, command="favorite"), "folder_id": folder_id}
    _write_action(
        command="favorite.remove" if remove else "favorite.add",
        action="favorite.remove" if remove else "favorite.add",
        target=target,
        account=account,
        dry_run=dry_run,
        yes=yes,
        as_json=as_json,
        execute=lambda client: client.favorite_video(video_ref, folder_id=folder_id, remove=remove),
    )


def _video_target(video_id: str, *, account: str | None, as_json: bool, command: str) -> dict[str, Any]:
    client = BiliAPIClient.from_config(account)
    try:
        detail = client.video_detail(video_id)
    except BiliError as exc:
        fail(exc, as_json=as_json, command=command, strategy="api")
    finally:
        client.close()
    return {
        "bvid": detail.get("bvid"),
        "aid": detail.get("aid"),
        "title": detail.get("title"),
        "url": detail.get("url"),
    }


def _write_action(
    *,
    command: str,
    action: str,
    target: dict[str, Any],
    account: str | None,
    dry_run: bool,
    yes: bool,
    as_json: bool,
    execute: Callable[[BiliAPIClient], dict[str, Any]],
) -> None:
    effective_dry_run = dry_run or not yes
    if effective_dry_run:
        result = {
            "action": action,
            "target": target,
            "dry_run": True,
            "executed": False,
            "next_action": f"Re-run with --yes to execute {action}",
        }
        audit_path = write_audit_event(
            command=command,
            action=action,
            target=target,
            account=account,
            dry_run=True,
            strategy="api",
            ok=True,
            result={"executed": False},
        )
        result["audit_log"] = str(audit_path)
        _print_write_result(result, command=command, account=account, as_json=as_json)
        return

    client = BiliAPIClient.from_config(account)
    try:
        result = execute(client)
    except BiliError as exc:
        write_audit_event(
            command=command,
            action=action,
            target=target,
            account=account,
            dry_run=False,
            strategy="api",
            ok=False,
            error={"code": exc.code, "message": exc.message, "retryable": exc.retryable},
        )
        fail(exc, as_json=as_json, command=command, strategy="api")
    finally:
        client.close()

    result = {**result, "dry_run": False, "executed": True}
    audit_path = write_audit_event(
        command=command,
        action=action,
        target=target,
        account=account,
        dry_run=False,
        strategy="api",
        ok=True,
        result={"executed": True},
    )
    result["audit_log"] = str(audit_path)
    _print_write_result(result, command=command, account=account, as_json=as_json)


def _print_write_result(result: dict[str, Any], *, command: str, account: str | None, as_json: bool) -> None:
    if as_json:
        print_json(result, command=command, strategy="api", account=account)
        return
    success("Dry run prepared" if result.get("dry_run") else "Write action executed")
    status("Action", result.get("action"))
    target = result.get("target") or result.get("video") or {}
    if target.get("title"):
        status("Target", f"{target.get('title')} ({target.get('bvid') or target.get('mid')})")
    elif target.get("mid"):
        status("Target", target.get("mid"))
    if result.get("dry_run"):
        status("Next", result.get("next_action"))
    status("Audit", result.get("audit_log"))
