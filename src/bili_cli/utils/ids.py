"""Bilibili ID parsing helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bili_cli.errors import UnsupportedInputError

BVID_RE = re.compile(r"\b(BV[0-9A-Za-z]{10})\b")
AID_RE = re.compile(r"\b(?:av|aid)(\d+)\b", re.IGNORECASE)
VIDEO_URL_RE = re.compile(r"bilibili\.com/video/(BV[0-9A-Za-z]{10}|av\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class VideoRef:
    raw: str
    bvid: str | None = None
    aid: int | None = None

    @property
    def display(self) -> str:
        if self.bvid:
            return self.bvid
        if self.aid is not None:
            return f"av{self.aid}"
        return self.raw


def parse_video_ref(value: str) -> VideoRef:
    text = value.strip()
    if not text:
        raise UnsupportedInputError("Empty video id")

    url_match = VIDEO_URL_RE.search(text)
    if url_match:
        text = url_match.group(1)

    bvid_match = BVID_RE.search(text)
    if bvid_match:
        return VideoRef(raw=value, bvid=bvid_match.group(1))

    aid_match = AID_RE.search(text)
    if aid_match:
        return VideoRef(raw=value, aid=int(aid_match.group(1)))

    if text.isdigit():
        return VideoRef(raw=value, aid=int(text))

    raise UnsupportedInputError(f"Unsupported Bilibili video id: {value}")


def video_url(bvid: str | None = None, aid: int | None = None) -> str:
    if bvid:
        return f"https://www.bilibili.com/video/{bvid}/"
    if aid is not None:
        return f"https://www.bilibili.com/video/av{aid}/"
    return "https://www.bilibili.com/"
