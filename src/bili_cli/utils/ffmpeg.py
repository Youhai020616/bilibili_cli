"""ffmpeg availability helpers."""

from __future__ import annotations

import shutil


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")
