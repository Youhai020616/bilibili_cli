from __future__ import annotations

from typing import Any

from bili_cli import constants
from bili_cli.api.client import BiliAPIClient


class FakeClient(BiliAPIClient):
    def __init__(self, responses: dict[str, dict[str, Any]]):
        super().__init__(account="default", request_delay=0)
        self.responses = responses

    def get_json(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        if url == constants.LIVE_MAIN_LIST_URL:
            return self.responses["list"]
        if url == constants.LIVE_ROOM_INFO_URL:
            return self.responses["room"]
        if url == constants.LIVE_ANCHOR_INFO_URL:
            return self.responses["anchor"]
        if url == constants.LIVE_PLAY_INFO_URL:
            return self.responses["play"]
        if url == constants.LIVE_DANMAKU_HISTORY_URL:
            return self.responses["danmaku"]
        if url == constants.LIVE_DANMU_CONF_URL:
            return self.responses["danmaku_conf"]
        raise AssertionError(f"Unexpected URL: {url}")


def _play_response() -> dict[str, Any]:
    return {
        "code": 0,
        "data": {
            "playurl_info": {
                "playurl": {
                    "g_qn_desc": [{"qn": 10000, "desc": "origin"}],
                    "stream": [
                        {
                            "protocol_name": "http_stream",
                            "format": [
                                {
                                    "format_name": "flv",
                                    "codec": [
                                        {
                                            "codec_name": "avc",
                                            "current_qn": 10000,
                                            "accept_qn": [10000, 400],
                                            "base_url": "/live/test.flv?",
                                            "url_info": [{"host": "https://live.example.com", "extra": "token=1"}],
                                        }
                                    ],
                                }
                            ],
                        }
                    ],
                }
            }
        },
    }


def test_live_list_normalizes_recommended_rooms() -> None:
    client = FakeClient(
        {
            "list": {
                "code": 0,
                "data": {
                    "online_total": 2,
                    "recommend_room_list": [
                        {"roomid": 1, "uid": 2, "title": "Room", "uname": "Anchor", "online": 3, "area_v2_name": "Tech"}
                    ],
                },
            }
        }
    )
    data = client.live_list(count=1)
    assert data["items"][0]["room_id"] == 1
    assert data["items"][0]["anchor"] == "Anchor"


def test_live_info_redacts_stream_urls_by_default() -> None:
    client = FakeClient(
        {
            "room": {"code": 0, "data": {"room_id": 1, "uid": 2, "title": "Room", "live_status": 1}},
            "anchor": {"code": 0, "data": {"info": {"uid": 2, "uname": "Anchor"}}},
            "play": _play_response(),
        }
    )
    data = client.live_info(1)
    stream = data["streams"][0]
    assert data["is_live"] is True
    assert stream["url_present"] is True
    assert "url" not in stream


def test_live_streams_can_include_urls() -> None:
    client = FakeClient(
        {
            "room": {"code": 0, "data": {"room_id": 1, "uid": 2, "title": "Room", "live_status": 1}},
            "play": _play_response(),
        }
    )
    data = client.live_streams(1, show_urls=True)
    assert data["streams"][0]["url"] == "https://live.example.com/live/test.flv?token=1"


def test_live_danmaku_normalizes_history_items() -> None:
    client = FakeClient(
        {
            "room": {"code": 0, "data": {"room_id": 1, "short_id": 0, "live_status": 1}},
            "danmaku": {
                "code": 0,
                "data": {
                    "room": [
                        {
                            "id_str": "1",
                            "text": "hello",
                            "uid": 2,
                            "nickname": "User",
                            "timeline": "2026-01-01 00:00:00",
                            "user_level": [5],
                        }
                    ],
                    "admin": [],
                },
            },
        }
    )
    data = client.live_danmaku(1, count=1)
    assert data["items"][0]["text"] == "hello"
    assert data["items"][0]["uname"] == "User"


def test_live_danmaku_conf_redacts_token() -> None:
    client = FakeClient(
        {
            "room": {"code": 0, "data": {"room_id": 1, "short_id": 0, "live_status": 1}},
            "danmaku_conf": {
                "code": 0,
                "data": {
                    "host": "broadcast.example.com",
                    "port": 2243,
                    "token": "secret",
                    "host_server_list": [{"host": "wss.example.com", "port": 2243, "ws_port": 2244, "wss_port": 443}],
                },
            },
        }
    )
    data = client.live_danmaku_conf(1)
    assert data["token_present"] is True
    assert "secret" not in str(data)
