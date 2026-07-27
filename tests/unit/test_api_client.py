from __future__ import annotations

from typing import Any

from bili_cli import constants
from bili_cli.api.client import BiliAPIClient


class FakeClient(BiliAPIClient):
    def __init__(self, responses: dict[str, dict[str, Any]]):
        super().__init__(account="default", request_delay=0)
        self.responses = responses

    def get_json(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        key = "view" if "view" in url else "comments"
        return self.responses[key]


def test_video_detail_adds_url() -> None:
    client = FakeClient(
        {
            "view": {
                "code": 0,
                "data": {"bvid": "BV1xx411c7mD", "aid": 2, "title": "Title", "owner": {}, "pages": []},
            }
        }
    )
    data = client.video_detail("BV1xx411c7mD")
    assert data["url"] == "https://www.bilibili.com/video/BV1xx411c7mD/"


def test_comments_normalization() -> None:
    client = FakeClient(
        {
            "view": {
                "code": 0,
                "data": {"bvid": "BV1xx411c7mD", "aid": 2, "title": "Title", "owner": {}, "pages": []},
            },
            "comments": {
                "code": 0,
                "data": {
                    "cursor": {"all_count": 1, "is_end": True, "pagination_reply": {}},
                    "replies": [
                        {
                            "rpid": 1,
                            "oid": 2,
                            "mid": 3,
                            "ctime": 100,
                            "like": 4,
                            "rcount": 0,
                            "content": {"message": "nice"},
                            "member": {"mid": "3", "uname": "user", "level_info": {"current_level": 5}},
                        }
                    ],
                },
            },
        }
    )
    data = client.comments("BV1xx411c7mD", count=1)
    assert data["comments"][0]["message"] == "nice"
    assert data["comments"][0]["member"]["uname"] == "user"


def test_favorite_resources_normalization() -> None:
    class FavoriteClient(BiliAPIClient):
        def __init__(self) -> None:
            super().__init__(account="default", request_delay=0)
            self.last_url = ""
            self.last_params: dict[str, Any] = {}

        def get_json(
            self,
            url: str,
            *,
            params: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
        ) -> dict[str, Any]:
            self.last_url = url
            self.last_params = params or {}
            return {
                "code": 0,
                "data": {
                    "info": {
                        "id": 123,
                        "fid": 123,
                        "mid": 456,
                        "title": "Folder",
                        "media_count": 1,
                        "upper": {"mid": 456, "name": "Owner"},
                    },
                    "has_more": False,
                    "ttl": 1,
                    "medias": [
                        {
                            "id": 2,
                            "type": 2,
                            "title": "Video",
                            "intro": "Intro",
                            "cover": "cover.jpg",
                            "duration": 60,
                            "upper": {"mid": 3, "name": "UP"},
                            "cnt_info": {"play": 10, "danmaku": 2, "collect": 4, "reply": 5},
                            "bvid": "BV1xx411c7mD",
                            "fav_time": 100,
                            "pubtime": 90,
                        },
                        {
                            "id": 9,
                            "type": 12,
                            "title": "Audio",
                            "intro": "Audio intro",
                            "upper": {"mid": 4, "name": "Audio UP"},
                            "cnt_info": {"play": 6},
                            "link": "https://www.bilibili.com/audio/au9",
                        }
                    ],
                },
            }

    client = FavoriteClient()
    data = client.favorite_resources(123, limit=99, page=0, keyword="AI", order="view", media_type=2)

    assert client.last_url == constants.FAVORITE_RESOURCE_LIST_URL
    assert client.last_params == {
        "media_id": 123,
        "pn": 1,
        "ps": 50,
        "keyword": "AI",
        "order": "view",
        "type": 2,
    }
    assert data["limit"] == 50
    assert data["folder"]["title"] == "Folder"
    assert data["items"][0]["type"] == "video"
    assert data["items"][0]["bvid"] == "BV1xx411c7mD"
    assert data["items"][0]["url"] == "https://www.bilibili.com/video/BV1xx411c7mD/"
    assert data["items"][1]["type"] == "media"
    assert data["items"][1]["aid"] is None
    assert data["items"][1]["url"] == "https://www.bilibili.com/audio/au9"
