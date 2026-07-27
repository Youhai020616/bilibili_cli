"""Live stream recording helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path

from bili_cli.errors import APIError
from bili_cli.utils.ffmpeg import ffmpeg_path


def record_live_stream(
    url: str,
    output_path: Path,
    *,
    duration: int | None = None,
    overwrite: bool = False,
) -> Path:
    ffmpeg = ffmpeg_path()
    if not ffmpeg:
        raise APIError("ffmpeg is required to record live streams", "FFMPEG_MISSING", True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() and not overwrite:
        return output_path
    cmd = [ffmpeg, "-y" if overwrite else "-n", "-i", url, "-c", "copy"]
    if duration and duration > 0:
        cmd.extend(["-t", str(duration)])
    cmd.append(str(output_path))
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise APIError(f"ffmpeg record failed: {proc.stderr.strip()[-500:]}", "FFMPEG_FAILED", True)
    return output_path
