from __future__ import annotations

import pytest

from bili_cli.errors import UnsupportedInputError
from bili_cli.utils.ids import parse_video_ref, video_url


def test_parse_bvid() -> None:
    ref = parse_video_ref("BV1xx411c7mD")
    assert ref.bvid == "BV1xx411c7mD"
    assert ref.aid is None


def test_parse_av_id() -> None:
    ref = parse_video_ref("av2")
    assert ref.aid == 2
    assert ref.bvid is None


def test_parse_aid_number() -> None:
    ref = parse_video_ref("2")
    assert ref.aid == 2


def test_parse_video_url() -> None:
    ref = parse_video_ref("https://www.bilibili.com/video/BV1xx411c7mD/")
    assert ref.bvid == "BV1xx411c7mD"


def test_reject_invalid_id() -> None:
    with pytest.raises(UnsupportedInputError):
        parse_video_ref("not-a-video-id")


def test_video_url() -> None:
    assert video_url("BV1xx411c7mD") == "https://www.bilibili.com/video/BV1xx411c7mD/"
    assert video_url(aid=2) == "https://www.bilibili.com/video/av2/"
