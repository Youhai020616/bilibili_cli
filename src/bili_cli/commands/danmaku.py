"""Danmaku commands."""

from __future__ import annotations

import json

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.commands._common import fail
from bili_cli.errors import BiliError
from bili_cli.index_cache import resolve_video_ref
from bili_cli.output import console, print_danmaku, print_json, success


@click.command("danmaku", help="Fetch video danmaku")
@click.argument("video_id")
@click.option("--page", type=int, default=1, help="Video page number")
@click.option("--format", "fmt", type=click.Choice(["table", "json", "xml", "ass"]), default="table", help="Output format")
@click.option("--limit", type=int, default=100, help="Limit items returned unless --all is set")
@click.option("--all", "include_all", is_flag=True, help="Return all danmaku items")
@click.option("-o", "--output", default=None, help="Write output to a file")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON envelope")
def danmaku(
    video_id: str,
    page: int,
    fmt: str,
    limit: int,
    include_all: bool,
    output: str | None,
    account: str | None,
    as_json: bool,
) -> None:
    video_id = resolve_video_ref(video_id)
    client = BiliAPIClient.from_config(account)
    try:
        result = client.danmaku(video_id, page=page)
    except BiliError as exc:
        client.close()
        fail(exc, as_json=as_json, command="danmaku", strategy="api")
    finally:
        client.close()

    result = _limit_result(result, limit=limit, include_all=include_all)
    if as_json:
        print_json(result, command="danmaku", strategy="api", account=account)
        return

    text: str | None = None
    if fmt == "json":
        text = json.dumps(result, ensure_ascii=False, indent=2)
    elif fmt == "xml":
        text = _to_xml(result.get("items") or [])
    elif fmt == "ass":
        text = _to_ass(result.get("items") or [])

    if text is not None:
        if output:
            from pathlib import Path

            path = Path(output).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            success(f"Wrote danmaku to {path}")
        else:
            console.print(text)
        return

    print_danmaku(result.get("items") or [])


def _limit_result(result: dict, *, limit: int, include_all: bool) -> dict:
    items = result.get("items") or []
    total = len(items)
    if include_all:
        result["total"] = total
        return result
    capped = max(0, limit)
    return {**result, "total": total, "items": items[:capped], "truncated": total > capped}


def _to_xml(items: list[dict]) -> str:
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<i>"]
    for item in items:
        p = ",".join(
            [
                str(item.get("time", 0)),
                str(item.get("mode", 1)),
                str(item.get("size", 25)),
                str(item.get("color", 16777215)),
                str(item.get("timestamp", 0)),
                str(item.get("pool", 0)),
                str(item.get("user_hash", "")),
                str(item.get("id", "")),
            ]
        )
        text = str(item.get("text", "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        lines.append(f'  <d p="{p}">{text}</d>')
    lines.append("</i>")
    return "\n".join(lines)


def _to_ass(items: list[dict]) -> str:
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1920",
        "PlayResY: 1080",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Arial,42,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,0,8,20,20,20,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for item in items:
        start = float(item.get("time") or 0)
        end = start + 5
        text = str(item.get("text", "")).replace("\n", " ").replace("{", "").replace("}", "")
        lines.append(f"Dialogue: 0,{_ass_time(start)},{_ass_time(end)},Default,,0,0,0,,{text}")
    return "\n".join(lines)


def _ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}:{minutes:02d}:{secs:05.2f}"
