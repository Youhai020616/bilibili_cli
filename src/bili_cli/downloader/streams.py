"""Stream selection for Bilibili playurl responses."""

from __future__ import annotations

from typing import Any

from bili_cli.errors import APIError


def select_streams(playurl: dict[str, Any], *, audio_only: bool = False) -> dict[str, Any]:
    dash = playurl.get("dash") or {}
    if dash:
        audio_streams = sorted(
            dash.get("audio") or [],
            key=lambda item: (item.get("id") or 0, item.get("bandwidth") or 0),
            reverse=True,
        )
        video_streams = sorted(
            dash.get("video") or [],
            key=lambda item: (item.get("id") or 0, item.get("bandwidth") or 0),
            reverse=True,
        )
        audio = audio_streams[0] if audio_streams else None
        video = None if audio_only else (video_streams[0] if video_streams else None)
        if audio_only and not audio:
            raise APIError("No audio stream found", "UNSUPPORTED_CONTENT_TYPE")
        if not audio_only and not video:
            raise APIError("No video stream found", "UNSUPPORTED_CONTENT_TYPE")
        return {
            "kind": "dash",
            "video": _normalize_dash_stream(video, "video") if video else None,
            "audio": _normalize_dash_stream(audio, "audio") if audio else None,
        }

    durl = playurl.get("durl") or []
    if durl and not audio_only:
        first = durl[0]
        return {
            "kind": "durl",
            "video": {
                "kind": "video",
                "id": playurl.get("actual_quality"),
                "url": first.get("url"),
                "backup_urls": first.get("backup_url") or [],
                "bandwidth": None,
                "codecs": "",
                "mime_type": "",
                "size": first.get("size"),
            },
            "audio": None,
        }

    raise APIError("No downloadable streams found", "UNSUPPORTED_CONTENT_TYPE")


def public_stream_plan(streams: dict[str, Any], *, show_urls: bool = False) -> dict[str, Any]:
    result = {"kind": streams.get("kind"), "video": None, "audio": None}
    for key in ("video", "audio"):
        stream = streams.get(key)
        if not stream:
            continue
        public = {item_key: value for item_key, value in stream.items() if item_key not in {"url", "backup_urls"}}
        public["url_present"] = bool(stream.get("url"))
        public["backup_url_count"] = len(stream.get("backup_urls") or [])
        if show_urls:
            public["url"] = stream.get("url")
            public["backup_urls"] = stream.get("backup_urls") or []
        result[key] = public
    return result


def _normalize_dash_stream(stream: dict[str, Any] | None, kind: str) -> dict[str, Any] | None:
    if not stream:
        return None
    return {
        "kind": kind,
        "id": stream.get("id"),
        "url": stream.get("baseUrl") or stream.get("base_url"),
        "backup_urls": stream.get("backupUrl") or stream.get("backup_url") or [],
        "bandwidth": stream.get("bandwidth"),
        "codecs": stream.get("codecs"),
        "mime_type": stream.get("mimeType") or stream.get("mime_type"),
        "width": stream.get("width"),
        "height": stream.get("height"),
        "frame_rate": stream.get("frameRate") or stream.get("frame_rate"),
    }
