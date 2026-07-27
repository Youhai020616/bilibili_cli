"""User profile commands."""

from __future__ import annotations

from typing import Any, Callable

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.commands._common import fail, wants_json
from bili_cli.errors import BiliError
from bili_cli.index_cache import save_index
from bili_cli.output import fmt_count, print_json, print_search_results, print_table, status, success, warning
from bili_cli.utils.export import export_data


@click.group("user", help="User profile commands")
def user_group() -> None:
    pass


@user_group.command("info", help="Show user profile")
@click.argument("mid")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def info(mid: str, account: str | None, as_json: bool, json_output: bool) -> None:
    _show_info(mid, account=account, as_json=wants_json(as_json, json_output), command="user.info")


@user_group.command("videos", help="List user videos")
@click.argument("mid")
@click.option("--limit", "--count", type=int, default=20, help="Result limit")
@click.option("--page", type=int, default=1, help="Result page")
@click.option("--order", type=click.Choice(["pubdate", "click", "stow"]), default="pubdate", help="Sort order")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def videos(
    mid: str,
    limit: int,
    page: int,
    order: str,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    json_mode = wants_json(as_json, json_output)
    result = _call_client(
        lambda client: client.user_videos(mid, limit=limit, page=page, order=order),
        account=account,
        as_json=json_mode,
        command="user.videos",
    )
    items = result.get("items") or []
    save_index(items, query=f"user:{mid}:videos", item_type="video")
    _maybe_export(items, output, json_mode=json_mode)
    if json_mode:
        print_json(result, command="user.videos", strategy="api", account=account)
    else:
        print_search_results(items, f"user {mid} videos")


@user_group.command("followers", help="List user followers")
@click.argument("mid")
@click.option("--limit", "--count", type=int, default=20, help="Result limit")
@click.option("--page", type=int, default=1, help="Result page")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def followers(
    mid: str,
    limit: int,
    page: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    _show_relation(
        mid,
        relation="followers",
        limit=limit,
        page=page,
        account=account,
        as_json=wants_json(as_json, json_output),
        output=output,
    )


@user_group.command("following", help="List accounts followed by a user")
@click.argument("mid")
@click.option("--limit", "--count", type=int, default=20, help="Result limit")
@click.option("--page", type=int, default=1, help="Result page")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def following(
    mid: str,
    limit: int,
    page: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    _show_relation(
        mid,
        relation="following",
        limit=limit,
        page=page,
        account=account,
        as_json=wants_json(as_json, json_output),
        output=output,
    )


@user_group.command("favorites", help="List public favorite folders")
@click.argument("mid")
@click.option("--limit", "--count", type=int, default=20, help="Result limit")
@click.option("--page", type=int, default=1, help="Result page")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
@click.option("-o", "--output", default=None, help="Export to .json/.csv/.yaml")
def favorites(
    mid: str,
    limit: int,
    page: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
    output: str | None,
) -> None:
    json_mode = wants_json(as_json, json_output)
    result = _call_client(
        lambda client: client.user_favorites(mid, limit=limit, page=page),
        account=account,
        as_json=json_mode,
        command="user.favorites",
    )
    items = result.get("items") or []
    _maybe_export(items, output, json_mode=json_mode)
    if json_mode:
        print_json(result, command="user.favorites", strategy="api", account=account)
    else:
        _print_favorites(items)


@click.command("profile", help="Show a user profile summary")
@click.argument("mid")
@click.option("--videos", "include_videos", is_flag=True, help="Include recent videos")
@click.option("--followers", "include_followers", is_flag=True, help="Include followers")
@click.option("--following", "include_following", is_flag=True, help="Include following")
@click.option("--favorites", "include_favorites", is_flag=True, help="Include favorite folders")
@click.option("--limit", "--count", type=int, default=10, help="Section result limit")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def profile(
    mid: str,
    include_videos: bool,
    include_followers: bool,
    include_following: bool,
    include_favorites: bool,
    limit: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    json_mode = wants_json(as_json, json_output)
    result = _call_client(lambda client: client.user_info(mid), account=account, as_json=json_mode, command="profile")
    sections: dict[str, Any] = {}
    errors: dict[str, dict[str, Any]] = {}
    if include_videos:
        _add_optional_section(sections, errors, "videos", account, lambda client: client.user_videos(mid, limit=limit))
    if include_followers:
        _add_optional_section(sections, errors, "followers", account, lambda client: client.user_followers(mid, limit=limit))
    if include_following:
        _add_optional_section(sections, errors, "following", account, lambda client: client.user_following(mid, limit=limit))
    if include_favorites:
        _add_optional_section(sections, errors, "favorites", account, lambda client: client.user_favorites(mid, limit=limit))
    if sections:
        result["sections"] = sections
    if errors:
        result["section_errors"] = errors
    if json_mode:
        print_json(result, command="profile", strategy="api", account=account)
    else:
        _print_profile(result)


def _show_info(mid: str, *, account: str | None, as_json: bool, command: str) -> None:
    result = _call_client(lambda client: client.user_info(mid), account=account, as_json=as_json, command=command)
    if as_json:
        print_json(result, command=command, strategy="api", account=account)
    else:
        _print_profile(result)


def _show_relation(
    mid: str,
    *,
    relation: str,
    limit: int,
    page: int,
    account: str | None,
    as_json: bool,
    output: str | None,
) -> None:
    command = f"user.{relation}"
    method = "user_followers" if relation == "followers" else "user_following"
    result = _call_client(
        lambda client: getattr(client, method)(mid, limit=limit, page=page),
        account=account,
        as_json=as_json,
        command=command,
    )
    items = result.get("items") or []
    save_index(items, query=f"user:{mid}:{relation}", item_type="user")
    _maybe_export(items, output, json_mode=as_json)
    if as_json:
        print_json(result, command=command, strategy="api", account=account)
    else:
        _print_relation_users(items, title=relation.title())


def _call_client(
    fn: Callable[[BiliAPIClient], dict[str, Any]],
    *,
    account: str | None,
    as_json: bool,
    command: str,
) -> dict[str, Any]:
    client = BiliAPIClient.from_config(account)
    try:
        return fn(client)
    except BiliError as exc:
        fail(exc, as_json=as_json, command=command, strategy="api")
    finally:
        client.close()


def _add_optional_section(
    sections: dict[str, Any],
    errors: dict[str, dict[str, Any]],
    name: str,
    account: str | None,
    fn: Callable[[BiliAPIClient], dict[str, Any]],
) -> None:
    client = BiliAPIClient.from_config(account)
    try:
        sections[name] = fn(client)
    except BiliError as exc:
        errors[name] = {"code": exc.code, "message": exc.message, "retryable": exc.retryable}
    finally:
        client.close()


def _maybe_export(items: list[dict[str, Any]], output: str | None, *, json_mode: bool) -> None:
    if not output:
        return
    export_data(items, output)
    if not json_mode:
        success(f"Exported {len(items)} items to {output}")


def _print_profile(data: dict[str, Any]) -> None:
    counts = data.get("counts") or {}
    official = data.get("official") or {}
    status("User", f"{data.get('name') or '-'} ({data.get('mid')})")
    status("URL", data.get("url") or "-")
    if data.get("sign"):
        status("Sign", data.get("sign"))
    if official.get("title"):
        status("Official", official.get("title"))
    status(
        "Counts",
        (
            f"followers={fmt_count(counts.get('followers'))} "
            f"following={fmt_count(counts.get('following'))} "
            f"videos={fmt_count(counts.get('video') or counts.get('archive'))} "
            f"likes={fmt_count(counts.get('likes'))}"
        ),
    )
    sections = data.get("sections") or {}
    if sections.get("videos"):
        print_search_results(sections["videos"].get("items") or [], "profile videos")
    if sections.get("followers"):
        _print_relation_users(sections["followers"].get("items") or [], title="Followers")
    if sections.get("following"):
        _print_relation_users(sections["following"].get("items") or [], title="Following")
    if sections.get("favorites"):
        _print_favorites(sections["favorites"].get("items") or [])
    for name, error in (data.get("section_errors") or {}).items():
        warning(f"{name}: {error.get('code')} {error.get('message')}")


def _print_relation_users(items: list[dict[str, Any]], *, title: str) -> None:
    rows = [[item.get("mid"), item.get("name"), item.get("sign") or "-", item.get("level") or "-"] for item in items]
    print_table(title, ["MID", "Name", "Sign", "Level"], rows)


def _print_favorites(items: list[dict[str, Any]]) -> None:
    rows = [[item.get("id"), item.get("title"), fmt_count(item.get("media_count")), item.get("url") or "-"] for item in items]
    print_table("Favorite folders", ["ID", "Title", "Media", "URL"], rows)
