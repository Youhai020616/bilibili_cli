"""Download command."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import click

from bili_cli.api.client import BiliAPIClient
from bili_cli.commands._common import fail, wants_json
from bili_cli.config import get_value
from bili_cli.downloader.download import download_url, merge_dash, stream_extension
from bili_cli.downloader.streams import public_stream_plan, select_streams
from bili_cli.errors import BiliError
from bili_cli.index_cache import resolve_video_ref
from bili_cli.output import info, print_json, status, success
from bili_cli.utils.sanitize import safe_filename


@click.command("download", help="Download Bilibili video media")
@click.argument("video_id")
@click.option("--output", "output_dir", default=None, help="Output directory")
@click.option("--quality", default="best", help="Quality: best/360p/480p/720p/1080p or qn number")
@click.option("--page", default="1", help="Page number or all")
@click.option("--audio-only", is_flag=True, help="Download only audio stream")
@click.option("--cover", is_flag=True, help="Download cover image")
@click.option("--subtitle", is_flag=True, help="Download first available subtitle")
@click.option("--danmaku", "danmaku_format", type=click.Choice(["none", "json", "xml", "ass"]), default="none", help="Download danmaku sidecar")
@click.option("--with-metadata", is_flag=True, help="Write metadata JSON")
@click.option("--links-only", is_flag=True, help="Only print/download plan, do not download media")
@click.option("--show-urls", is_flag=True, help="Include expiring media URLs in JSON output")
@click.option("--overwrite", is_flag=True, help="Overwrite existing files")
@click.option("--account", default=None, help="Account profile name")
@click.option("--json", "as_json", is_flag=True, help="Output JSON")
@click.option("--json-output", "json_output", is_flag=True, help="Output JSON")
def download(
    video_id: str,
    output_dir: str | None,
    quality: str,
    page: str,
    audio_only: bool,
    cover: bool,
    subtitle: bool,
    danmaku_format: str,
    with_metadata: bool,
    links_only: bool,
    show_urls: bool,
    overwrite: bool,
    account: str | None,
    as_json: bool,
    json_output: bool,
) -> None:
    json_mode = wants_json(as_json, json_output)
    video_ref = resolve_video_ref(video_id)
    client = BiliAPIClient.from_config(account)
    try:
        detail = client.video_detail(video_ref)
        pages = _select_pages(detail.get("pages") or [], page)
        output_base = Path(output_dir or get_value("default.download_dir", "~/Downloads")).expanduser()
        plans = []
        for page_data in pages:
            playurl = client.playurl(video_ref, cid=page_data.get("cid"), quality=quality, page=int(page_data.get("page") or 1))
            streams = select_streams(playurl, audio_only=audio_only)
            plans.append(
                _build_page_plan(
                    detail,
                    page_data,
                    playurl,
                    streams,
                    output_base,
                    audio_only=audio_only,
                    show_urls=show_urls,
                    video_ref=video_ref,
                )
            )
        result = {"video": _video_public(detail), "pages": plans}

        if links_only:
            if json_mode:
                print_json(_public_download_result(result), command="download", strategy="api", account=account)
            else:
                _print_download_plan(result)
            return

        for plan in plans:
            _execute_plan(
                plan,
                cover=cover,
                subtitle=subtitle,
                danmaku_format=danmaku_format,
                with_metadata=with_metadata,
                overwrite=overwrite,
                client=client,
                detail=detail,
            )
        if json_mode:
            print_json(_public_download_result(result), command="download", strategy="api", account=account)
        else:
            success(f"Downloaded {len(plans)} page(s) to {output_base}")
    except BiliError as exc:
        fail(exc, as_json=json_mode, command="download", strategy="api")
    finally:
        client.close()


def _select_pages(pages: list[dict[str, Any]], page: str) -> list[dict[str, Any]]:
    if page == "all":
        return pages
    try:
        page_num = int(page)
    except ValueError as exc:
        from bili_cli.errors import APIError

        raise APIError("Page must be an integer or `all`", "UNSUPPORTED_INPUT") from exc
    for item in pages:
        if int(item.get("page") or 0) == page_num:
            return [item]
    from bili_cli.errors import APIError

    raise APIError(f"Page out of range: {page}", "UNSUPPORTED_INPUT")


def _build_page_plan(
    detail: dict[str, Any],
    page_data: dict[str, Any],
    playurl: dict[str, Any],
    streams: dict[str, Any],
    output_base: Path,
    *,
    audio_only: bool,
    show_urls: bool,
    video_ref: str,
) -> dict[str, Any]:
    title = safe_filename(str(detail.get("title") or video_ref or "video"))
    page_num = int(page_data.get("page") or 1)
    page_title = safe_filename(str(page_data.get("part") or f"p{page_num}"))
    stem = title if len(detail.get("pages") or []) == 1 else f"{title}_P{page_num}_{page_title}"
    output_dir = output_base / stem
    video_stream = streams.get("video")
    audio_stream = streams.get("audio")
    video_path = output_dir / f"{stem}.video{stream_extension(video_stream)}" if video_stream else None
    audio_path = output_dir / f"{stem}.audio{stream_extension(audio_stream, '.m4a')}" if audio_stream else None
    final_suffix = ".m4a" if audio_only else ".mp4"
    final_path = output_dir / f"{stem}{final_suffix}"
    return {
        "video_ref": video_ref,
        "page": page_num,
        "cid": page_data.get("cid"),
        "part": page_data.get("part") or "",
        "requested_quality": playurl.get("requested_quality"),
        "actual_quality": playurl.get("actual_quality"),
        "accept_quality": playurl.get("accept_quality"),
        "accept_description": playurl.get("accept_description"),
        "cover_url": detail.get("pic"),
        "subtitles": (detail.get("subtitle") or {}).get("list") or [],
        "streams": public_stream_plan(streams, show_urls=show_urls),
        "paths": {
            "dir": str(output_dir),
            "video": str(video_path) if video_path else None,
            "audio": str(audio_path) if audio_path else None,
            "final": str(final_path),
            "cover": str(output_dir / "cover.jpg"),
            "subtitle": str(output_dir / "subtitle.json"),
            "danmaku": str(output_dir / "danmaku"),
            "metadata": str(output_dir / "metadata.json"),
        },
        "_private_streams": streams,
    }


def _execute_plan(
    plan: dict[str, Any],
    *,
    cover: bool,
    subtitle: bool,
    danmaku_format: str,
    with_metadata: bool,
    overwrite: bool,
    client: BiliAPIClient,
    detail: dict[str, Any],
) -> None:
    paths = plan["paths"]
    streams = plan["_private_streams"]
    referer = "https://www.bilibili.com/"
    video_path = None
    audio_path = None
    if streams.get("video"):
        info(f"Downloading video page {plan['page']}")
        video_path = download_url(streams["video"]["url"], Path(paths["video"]), referer=referer, overwrite=overwrite)
    if streams.get("audio"):
        info(f"Downloading audio page {plan['page']}")
        audio_path = download_url(streams["audio"]["url"], Path(paths["audio"]), referer=referer, overwrite=overwrite)
    final_path = merge_dash(video_path, audio_path, Path(paths["final"]), overwrite=overwrite)
    final_target = Path(paths["final"])
    if final_path != final_target and final_path.exists():
        final_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(final_path, final_target)
        final_path = final_target
    plan["downloaded"] = {"final": str(final_path)}
    if cover:
        _download_cover(detail, plan, overwrite=overwrite)
    if subtitle:
        _download_subtitle(detail, plan, overwrite=overwrite)
    if danmaku_format != "none":
        _download_danmaku(client, plan, danmaku_format, overwrite=overwrite)
    if with_metadata:
        metadata = {key: value for key, value in plan.items() if key != "_private_streams"}
        Path(paths["metadata"]).write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    plan.pop("_private_streams", None)


def _download_cover(detail: dict[str, Any], plan: dict[str, Any], *, overwrite: bool) -> None:
    cover_url = detail.get("pic")
    if not cover_url:
        return
    if cover_url.startswith("//"):
        cover_url = "https:" + cover_url
    download_url(cover_url, Path(plan["paths"]["cover"]), referer="https://www.bilibili.com/", overwrite=overwrite)


def _download_subtitle(detail: dict[str, Any], plan: dict[str, Any], *, overwrite: bool) -> None:
    subtitles = (detail.get("subtitle") or {}).get("list") or []
    if not subtitles:
        return
    sub = subtitles[0]
    url = sub.get("subtitle_url") or sub.get("url")
    if not url:
        return
    if url.startswith("//"):
        url = "https:" + url
    target = Path(plan["paths"]["subtitle"])
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        return
    target.write_text(json.dumps(sub, ensure_ascii=False, indent=2), encoding="utf-8")
    download_url(url, target.with_suffix(".srt"), referer="https://www.bilibili.com/", overwrite=overwrite)


def _download_danmaku(client: BiliAPIClient, plan: dict[str, Any], fmt: str, *, overwrite: bool) -> None:
    from bili_cli.commands.danmaku import _to_ass, _to_xml

    result = client.danmaku(plan["video_ref"], page=plan["page"])
    items = result.get("items") or []
    danmaku_dir = Path(plan["paths"]["danmaku"])
    danmaku_dir.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        target = danmaku_dir / "danmaku.json"
        if target.exists() and not overwrite:
            return
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    elif fmt == "xml":
        target = danmaku_dir / "danmaku.xml"
        if target.exists() and not overwrite:
            return
        target.write_text(_to_xml(items), encoding="utf-8")
    elif fmt == "ass":
        target = danmaku_dir / "danmaku.ass"
        if target.exists() and not overwrite:
            return
        target.write_text(_to_ass(items), encoding="utf-8")


def _video_public(detail: dict[str, Any]) -> dict[str, Any]:
    owner = detail.get("owner") or {}
    return {
        "bvid": detail.get("bvid"),
        "aid": detail.get("aid"),
        "title": detail.get("title"),
        "owner": {"mid": owner.get("mid"), "name": owner.get("name")},
        "pages": len(detail.get("pages") or []),
    }


def _public_download_result(result: dict[str, Any]) -> dict[str, Any]:
    pages = []
    for page in result.get("pages") or []:
        pages.append({key: value for key, value in page.items() if key != "_private_streams"})
    return {**result, "pages": pages}


def _print_download_plan(result: dict[str, Any]) -> None:
    video = result["video"]
    status("Video", f"{video.get('title')} ({video.get('bvid')})")
    for page in result["pages"]:
        status("Page", f"{page['page']} cid={page['cid']} quality={page['actual_quality']}")
        status("Final", page["paths"]["final"])
