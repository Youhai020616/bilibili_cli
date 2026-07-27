"""Console and structured output helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from bili_cli.errors import BiliError

SCHEMA_VERSION = "1"
console = Console()
err_console = Console(stderr=True)


def success(message: str) -> None:
    console.print(f"[bold green]OK[/] {message}")


def error(message: str) -> None:
    err_console.print(f"[bold red]ERROR[/] {message}")


def warning(message: str) -> None:
    console.print(f"[bold yellow]WARN[/] {message}")


def info(message: str) -> None:
    console.print(f"[dim]INFO[/] {message}")


def status(label: str, value: Any, style: str = "") -> None:
    value_text = str(value)
    if style:
        console.print(f"  [bold]{label}:[/] [{style}]{value_text}[/]")
    else:
        console.print(f"  [bold]{label}:[/] {value_text}")


def success_envelope(
    data: Any,
    *,
    command: str | None = None,
    strategy: str | None = None,
    fallback_used: bool = False,
    account: str | None = None,
) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "ok": True,
        "schema_version": SCHEMA_VERSION,
        "data": data,
    }
    if command:
        envelope["command"] = command
    if strategy:
        envelope["strategy"] = strategy
        envelope["fallback_used"] = fallback_used
    if account:
        envelope["account"] = account
    return envelope


def error_envelope(exc: BiliError, *, command: str | None = None, strategy: str | None = None) -> dict[str, Any]:
    envelope: dict[str, Any] = {
        "ok": False,
        "schema_version": SCHEMA_VERSION,
        "error": {
            "code": exc.code,
            "message": exc.message,
            "retryable": exc.retryable,
        },
    }
    if exc.next_action:
        envelope["error"]["next_action"] = exc.next_action
    if command:
        envelope["command"] = command
    if strategy:
        envelope["strategy"] = strategy
    return envelope


def print_json(data: Any, **metadata: Any) -> None:
    envelope = success_envelope(data, **metadata)
    console.print_json(json.dumps(envelope, ensure_ascii=False, indent=2))


def print_error_json(exc: BiliError, **metadata: Any) -> None:
    err_console.print_json(json.dumps(error_envelope(exc, **metadata), ensure_ascii=False, indent=2))


def print_table(title: str, columns: list[str], rows: list[list[Any]]) -> None:
    table = Table(title=title, box=box.ROUNDED, show_lines=True)
    for column in columns:
        table.add_column(column, overflow="fold", max_width=40)
    for row in rows:
        table.add_row(*[str(value) for value in row])
    console.print(table)


def fmt_count(value: Any) -> str:
    if value is None or value == "":
        return "-"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        if value >= 100000000:
            return f"{value / 100000000:.1f}B"
        if value >= 10000:
            return f"{value / 10000:.1f}W"
        return str(int(value))
    return str(value)


def strip_html(text: Any) -> str:
    if text is None:
        return ""
    return re.sub(r"<[^>]+>", "", str(text)).replace("&amp;", "&")


def format_ts(value: Any) -> str:
    try:
        ts = int(value)
    except (TypeError, ValueError):
        return "-"
    if ts <= 0:
        return "-"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def print_search_results(items: list[dict[str, Any]], keyword: str = "") -> None:
    if not items:
        warning("No results")
        return
    table = Table(title=f"Search results: {keyword} ({len(items)})", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Title", max_width=42, overflow="fold")
    table.add_column("Author", max_width=16, overflow="fold")
    table.add_column("Views", justify="right", width=9)
    table.add_column("Duration", width=9)
    table.add_column("Type", width=8)
    table.add_column("ID", style="dim", max_width=18, overflow="ellipsis")
    for i, item in enumerate(items, 1):
        table.add_row(
            str(i),
            strip_html(item.get("title") or item.get("name") or "-"),
            strip_html(item.get("author") or item.get("uname") or "-"),
            fmt_count(item.get("play") or item.get("view") or "-"),
            str(item.get("duration") or "-"),
            str(item.get("type") or "video"),
            str(item.get("bvid") or item.get("mid") or item.get("id") or "-"),
        )
    console.print(table)


def print_video_detail(data: dict[str, Any]) -> None:
    owner = data.get("owner") or {}
    stat_data = data.get("stat") or {}
    panel_text = Text()
    panel_text.append(f"Title: {data.get('title', '-')}\n", style="bold")
    panel_text.append(f"Author: {owner.get('name', '-')} (@{owner.get('mid', '-')})\n")
    panel_text.append(f"Published: {format_ts(data.get('pubdate'))}\n")
    panel_text.append(
        f"Views {fmt_count(stat_data.get('view'))}  "
        f"Likes {fmt_count(stat_data.get('like'))}  "
        f"Coins {fmt_count(stat_data.get('coin'))}  "
        f"Favorites {fmt_count(stat_data.get('favorite'))}  "
        f"Replies {fmt_count(stat_data.get('reply'))}\n"
    )
    panel_text.append(f"Pages: {len(data.get('pages') or [])}  Duration: {data.get('duration', '-')}\n")
    desc = data.get("desc") or ""
    if desc:
        panel_text.append(f"\n{desc[:800]}\n")
    title = f"{data.get('bvid', '-')} / av{data.get('aid', '-')}"
    console.print(Panel(panel_text, title=title, border_style="blue"))


def print_comments(comments: list[dict[str, Any]]) -> None:
    if not comments:
        info("No comments")
        return
    table = Table(title=f"Comments ({len(comments)})", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("User", max_width=18, overflow="fold")
    table.add_column("Content", max_width=54, overflow="fold")
    table.add_column("Likes", justify="right", width=8)
    table.add_column("Replies", justify="right", width=8)
    for i, item in enumerate(comments, 1):
        member = item.get("member") or {}
        table.add_row(
            str(i),
            str(member.get("uname") or item.get("user") or "-"),
            str(item.get("message") or item.get("content") or "-"),
            fmt_count(item.get("like")),
            fmt_count(item.get("reply_count") or item.get("rcount") or 0),
        )
    console.print(table)


def print_danmaku(items: list[dict[str, Any]]) -> None:
    if not items:
        info("No danmaku")
        return
    table = Table(title=f"Danmaku ({len(items)})", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Time", justify="right", width=8)
    table.add_column("Text", max_width=70, overflow="fold")
    for i, item in enumerate(items[:50], 1):
        table.add_row(str(i), f"{float(item.get('time', 0)):.1f}s", str(item.get("text") or ""))
    console.print(table)


def print_trending(items: list[dict[str, Any]], title: str = "Trending") -> None:
    if not items:
        warning("No trending data")
        return
    table = Table(title=f"{title} ({len(items)})", box=box.ROUNDED, show_lines=True)
    table.add_column("#", width=4, justify="right")
    table.add_column("Title", max_width=46, overflow="fold")
    table.add_column("Author", max_width=16, overflow="fold")
    table.add_column("Views", justify="right", width=9)
    table.add_column("ID", style="dim", max_width=18, overflow="ellipsis")
    for i, item in enumerate(items, 1):
        owner = item.get("owner") or {}
        stat_data = item.get("stat") or {}
        table.add_row(
            str(i),
            strip_html(item.get("title") or "-"),
            str(owner.get("name") or "-"),
            fmt_count(stat_data.get("view") or item.get("view")),
            str(item.get("bvid") or item.get("aid") or "-"),
        )
    console.print(table)
