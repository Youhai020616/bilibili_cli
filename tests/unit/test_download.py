from __future__ import annotations

from bili_cli.commands.download import _public_download_result
from bili_cli.downloader.streams import public_stream_plan, select_streams


def test_select_streams_dash() -> None:
    playurl = {
        "dash": {
            "video": [
                {"id": 64, "baseUrl": "video-64", "bandwidth": 100, "mimeType": "video/mp4"},
                {"id": 80, "baseUrl": "video-80", "bandwidth": 200, "mimeType": "video/mp4"},
            ],
            "audio": [
                {"id": 30280, "baseUrl": "audio-1", "bandwidth": 50, "mimeType": "audio/mp4"},
                {"id": 30216, "baseUrl": "audio-2", "bandwidth": 100, "mimeType": "audio/mp4"},
            ],
        }
    }
    streams = select_streams(playurl)
    assert streams["video"]["id"] == 80
    assert streams["audio"]["id"] == 30280


def test_select_streams_durl() -> None:
    playurl = {"durl": [{"url": "video-only", "size": 123}]}
    streams = select_streams(playurl)
    assert streams["kind"] == "durl"
    assert streams["video"]["url"] == "video-only"
    assert streams["audio"] is None


def test_public_stream_plan_redacts_urls() -> None:
    plan = public_stream_plan(
        {
            "kind": "dash",
            "video": {"url": "video-url", "backup_urls": ["b1"], "id": 80, "kind": "video"},
            "audio": {"url": "audio-url", "backup_urls": [], "id": 30280, "kind": "audio"},
        }
    )
    assert plan["video"]["url_present"] is True
    assert "url" not in plan["video"]
    assert plan["audio"]["backup_url_count"] == 0


def test_public_download_result_drops_private_streams() -> None:
    result = {
        "video": {"bvid": "BV1xx411c7mD"},
        "pages": [
            {
                "page": 1,
                "streams": {"video": {"url_present": True}},
                "_private_streams": {"video": {"url": "expiring-url"}},
            }
        ],
    }

    public = _public_download_result(result)

    assert "_private_streams" not in public["pages"][0]
    assert "_private_streams" in result["pages"][0]
