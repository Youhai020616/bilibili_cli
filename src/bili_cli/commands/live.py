"""Live room commands."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.commands._common import fail, wants_json
from bili_cli.config import get_value
from bili_cli.downloader.live import record_live_stream
from bili_cli.errors import APIError, BiliError
from bili_cli.output import fmt_count, print_json, print_table, status, success
from bili_cli.utils.sanitize import safe_filename


@click.group("live", help="Live room commands")
def live_group() -> None:
    pass


@live_group.command("list", help="List recommended or searched live rooms")
@click.option("--keyword", default=None, help="Search keyword")
@click.option("--count", "--limit", type=int, default=20, help="Result limit")
@click.option("--page", type=int, default=1, help="Search page")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def live_list(keyword: str | None, count: int, page: int, account: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    result = _call_client(lambda client: client.live_list(keyword=keyword, count=count, page=page), account=account, as_json=json_mode, command="live.list")
    if json_mode:
        print_json(result, command="live.list", strategy="api", account=account)
    else:
        _print_live_rooms(result.get("items") or [], title="Live rooms")


@live_group.command("info", help="Show live room information")
@click.argument("room_id")
@click.option("--show-urls", is_flag=True, help="Include expiring stream URLs")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def live_info(room_id: str, show_urls: bool, account: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    result = _call_client(lambda client: client.live_info(room_id, show_urls=show_urls), account=account, as_json=json_mode, command="live.info")
    if json_mode:
        print_json(result, command="live.info", strategy="api", account=account)
    else:
        _print_live_info(result, show_urls=show_urls)


@live_group.command("streams", help="Show live room stream variants")
@click.argument("room_id")
@click.option("--show-urls", is_flag=True, help="Include expiring stream URLs")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def live_streams(room_id: str, show_urls: bool, account: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    result = _call_client(lambda client: client.live_streams(room_id, show_urls=show_urls), account=account, as_json=json_mode, command="live.streams")
    if json_mode:
        print_json(result, command="live.streams", strategy="api", account=account)
    else:
        _print_streams(result.get("streams") or [], show_urls=show_urls)


@live_group.command("danmaku", help="Fetch recent live danmaku")
@click.argument("room_id")
@click.option("--count", "--limit", type=int, default=20, help="Maximum items")
@click.option("--duration", type=int, default=0, help="Poll duration in seconds; 0 fetches once")
@click.option("--interval", type=int, default=5, help="Polling interval in seconds")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def live_danmaku(
    room_id: str,
    count: int,
    duration: int,
    interval: int,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    json_mode = wants_json(as_json, json_output)
    result = _collect_live_danmaku(room_id, count=count, duration=duration, interval=interval, account=account, as_json=json_mode)
    if json_mode:
        print_json(result, command="live.danmaku", strategy="api", account=account)
    else:
        _print_live_danmaku(result.get("items") or [])


@live_group.command("danmaku-conf", help="Show live danmaku connection metadata")
@click.argument("room_id")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def live_danmaku_conf(room_id: str, account: str | None, as_json: bool, json_output: bool) -> None:
    json_mode = wants_json(as_json, json_output)
    result = _call_client(lambda client: client.live_danmaku_conf(room_id), account=account, as_json=json_mode, command="live.danmaku-conf")
    if json_mode:
        print_json(result, command="live.danmaku-conf", strategy="api", account=account)
    else:
        rows = [[item.get("host"), item.get("port"), item.get("ws_port") or "-", item.get("wss_port") or "-"] for item in result.get("hosts") or []]
        status("Token", "present" if result.get("token_present") else "missing")
        print_table("Danmaku hosts", ["Host", "TCP", "WS", "WSS"], rows)


@live_group.command("record", help="Record a live room with ffmpeg")
@click.argument("room_id")
@click.option("--output", "output", default=None, help="Output file or directory")
@click.option("--duration", type=int, default=60, help="Record duration in seconds")
@click.option("--quality", default="best", help="Quality qn, or best")
@click.option("--overwrite", is_flag=True, help="Overwrite output file")
@click.option("--show-url", is_flag=True, help="Include selected expiring stream URL in output")
@click.option("--dry-run", is_flag=True, help="Preview only, even when --yes is provided")
@click.option("--yes", is_flag=True, help="Start recording")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def live_record(
    room_id: str,
    output: str | None,
    duration: int,
    quality: str,
    overwrite: bool,
    show_url: bool,
    dry_run: bool,
    yes: bool,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    json_mode = wants_json(as_json, json_output)
    info = _call_client(lambda client: client.live_info(room_id, show_urls=True), account=account, as_json=json_mode, command="live.record")
    if not info.get("is_live"):
        fail(APIError("Live room is not currently live", "NOT_LIVE"), as_json=json_mode, command="live.record", strategy="api")
    stream = _select_stream(info.get("streams") or [], quality=quality)
    output_path = _record_output_path(info, stream, output)
    visible_stream = {key: value for key, value in stream.items() if show_url or key not in {"url", "urls"}}
    result = {
        "room": {key: info.get(key) for key in ["room_id", "short_id", "title", "status", "online", "url"]},
        "stream": visible_stream,
        "output": str(output_path),
        "duration": duration,
        "dry_run": dry_run or not yes,
        "executed": False,
        "next_action": "Re-run with --yes to start recording",
    }
    if dry_run or not yes:
        _print_record_result(result, as_json=json_mode, account=account)
        return
    try:
        record_live_stream(str(stream["url"]), output_path, duration=duration, overwrite=overwrite)
    except BiliError as exc:
        fail(exc, as_json=json_mode, command="live.record", strategy="ffmpeg")
    result["dry_run"] = False
    result["executed"] = True
    result.pop("next_action", None)
    _print_record_result(result, as_json=json_mode, account=account)


def _call_client(
    fn,
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


def _select_stream(streams: list[dict[str, Any]], *, quality: str) -> dict[str, Any]:
    candidates = [item for item in streams if item.get("url")]
    if not candidates:
        raise APIError("No live stream URL available", "UNSUPPORTED_CONTENT_TYPE", True)
    if quality != "best":
        try:
            qn = int(quality)
        except ValueError as exc:
            raise APIError("Quality must be `best` or a numeric qn", "UNSUPPORTED_INPUT") from exc
        matching = [item for item in candidates if item.get("current_qn") == qn]
        if matching:
            return matching[0]
    return sorted(candidates, key=lambda item: item.get("current_qn") or 0, reverse=True)[0]


def _collect_live_danmaku(
    room_id: str,
    *,
    count: int,
    duration: int,
    interval: int,
    account: str | None,
    as_json: bool,
) -> dict[str, Any]:
    client = BiliAPIClient.from_config(account)
    seen = set()
    items: list[dict[str, Any]] = []
    end_at = time.time() + max(duration, 0)
    last_result: dict[str, Any] = {}
    try:
        while True:
            last_result = client.live_danmaku(room_id, count=count)
            for item in last_result.get("items") or []:
                item_id = item.get("id") or f"{item.get('timeline')}:{item.get('uid')}:{item.get('text')}"
                if item_id in seen:
                    continue
                seen.add(item_id)
                items.append(item)
            if duration <= 0 or time.time() >= end_at or len(items) >= count:
                break
            time.sleep(max(interval, 1))
    except BiliError as exc:
        fail(exc, as_json=as_json, command="live.danmaku", strategy="api")
    finally:
        client.close()
    return {
        "room_id": last_result.get("room_id") or str(room_id),
        "short_id": last_result.get("short_id"),
        "live_status": last_result.get("live_status"),
        "is_live": last_result.get("is_live"),
        "duration": duration,
        "interval": interval,
        "items": items[: max(count, 0)],
    }


def _record_output_path(info: dict[str, Any], stream: dict[str, Any], output: str | None) -> Path:
    ext = ".flv" if stream.get("format") == "flv" else ".ts"
    default_dir = Path(get_value("default.download_dir", "~/Downloads")).expanduser() / "live"
    base = Path(output).expanduser() if output else default_dir
    if base.suffix:
        return base
    stem = safe_filename(f"{info.get('room_id')}_{info.get('title') or 'live'}")
    return base / f"{stem}{ext}"


def _print_live_rooms(items: list[dict[str, Any]], *, title: str) -> None:
    rows = [
        [
            item.get("room_id"),
            item.get("title"),
            item.get("anchor"),
            fmt_count(item.get("online")),
            (item.get("area") or {}).get("name") or "-",
        ]
        for item in items
    ]
    print_table(title, ["Room", "Title", "Anchor", "Online", "Area"], rows)


def _print_live_info(data: dict[str, Any], *, show_urls: bool) -> None:
    anchor = data.get("anchor") or {}
    area = data.get("area") or {}
    status("Room", f"{data.get('title')} ({data.get('room_id')})")
    status("Status", data.get("status"))
    status("Anchor", f"{anchor.get('name') or '-'} ({anchor.get('uid') or data.get('uid')})")
    status("Online", fmt_count(data.get("online")))
    status("Area", f"{area.get('parent_name') or '-'} / {area.get('name') or '-'}")
    status("URL", data.get("url"))
    _print_streams(data.get("streams") or [], show_urls=show_urls)


def _print_streams(items: list[dict[str, Any]], *, show_urls: bool) -> None:
    columns = ["Protocol", "Format", "Codec", "QN", "URLs"]
    rows = []
    for item in items:
        row = [item.get("protocol"), item.get("format"), item.get("codec"), item.get("current_qn"), item.get("url_count")]
        if show_urls:
            row.append(item.get("url") or "-")
        rows.append(row)
    if show_urls:
        columns.append("URL")
    print_table("Live streams", columns, rows)


def _print_live_danmaku(items: list[dict[str, Any]]) -> None:
    rows = [[item.get("timeline"), item.get("uname"), item.get("text"), item.get("user_level") or "-"] for item in items]
    print_table("Live danmaku", ["Time", "User", "Text", "Level"], rows)


def _print_record_result(result: dict[str, Any], *, as_json: bool, account: str | None) -> None:
    if as_json:
        print_json(result, command="live.record", strategy="api", account=account)
        return
    success("Record dry run prepared" if result.get("dry_run") else "Recording finished")
    status("Room", result.get("room", {}).get("title"))
    status("Output", result.get("output"))
    if result.get("dry_run"):
        status("Next", result.get("next_action"))
