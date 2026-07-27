"""File download and ffmpeg merge helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import httpx
from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn

from bili_cli.constants import DEFAULT_USER_AGENT
from bili_cli.errors import APIError
from bili_cli.utils.ffmpeg import ffmpeg_path


def download_url(
    url: str,
    output_path: Path,
    *,
    referer: str,
    overwrite: bool = False,
    timeout: int = 60,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        return output_path
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Referer": referer,
        "Origin": "https://www.bilibili.com",
    }
    with httpx.Client(timeout=timeout, follow_redirects=True, headers=headers) as client:
        with client.stream("GET", url) as resp:
            if resp.status_code >= 400:
                raise APIError(f"Download failed with HTTP {resp.status_code}", "DOWNLOAD_FAILED", True)
            total = int(resp.headers.get("content-length") or 0)
            with Progress(
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                TimeRemainingColumn(),
            ) as progress:
                task_id = progress.add_task(output_path.name, total=total or None)
                with output_path.open("wb") as fh:
                    for chunk in resp.iter_bytes():
                        fh.write(chunk)
                        progress.update(task_id, advance=len(chunk))
    return output_path


def merge_dash(video_path: Path | None, audio_path: Path | None, output_path: Path, *, overwrite: bool = False) -> Path:
    if audio_path is None:
        if video_path is None:
            raise APIError("No media files to merge", "UNSUPPORTED_CONTENT_TYPE")
        return video_path
    if video_path is None:
        return audio_path
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise APIError("ffmpeg is required to merge video and audio", "FFMPEG_MISSING", True)
    if output_path.exists() and not overwrite:
        return output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y" if overwrite else "-n",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c",
        "copy",
        str(output_path),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise APIError(f"ffmpeg merge failed: {proc.stderr.strip()[-500:]}", "FFMPEG_FAILED", True)
    return output_path


def stream_extension(stream: dict[str, Any] | None, default: str = ".m4s") -> str:
    if not stream:
        return default
    mime = str(stream.get("mime_type") or "")
    if "mp4" in mime:
        return ".m4s"
    if "audio" in mime:
        return ".m4a"
    return default
