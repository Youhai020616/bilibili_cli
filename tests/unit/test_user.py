from __future__ import annotations

from typing import Any

from bili_cli import constants
from bili_cli.api.client import BiliAPIClient


class FakeClient(BiliAPIClient):
    def __init__(self, responses: dict[str, dict[str, Any]]):
        super().__init__(account="default", request_delay=0)
        self.responses = responses

    def get_json(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        if url == constants.USER_CARD_URL:
            return self.responses["card"]
        if url == constants.RELATION_STAT_URL:
            return self.responses["relation"]
        if url == constants.SPACE_NAVNUM_URL:
            return self.responses["navnum"]
        if url == constants.SPACE_SETTING_URL:
            return self.responses["setting"]
        if url == constants.SPACE_ARC_SEARCH_URL:
            return self.responses["videos"]
        raise AssertionError(f"Unexpected URL: {url}")


def test_user_info_normalizes_profile_counts() -> None:
    client = FakeClient(
        {
            "card": {
                "code": 0,
                "data": {
                    "card": {
                        "mid": "2",
                        "name": "User",
                        "sex": "secret",
                        "face": "face.jpg",
                        "sign": "hello",
                        "level_info": {"current_level": 6},
                        "vip": {"type": 1, "status": 1, "label": {"text": "VIP"}},
                        "official_verify": {"type": 0, "desc": "official"},
                    },
                    "archive_count": 12,
                    "article_count": 3,
                    "follower": 100,
                    "like_num": 200,
                },
            },
            "relation": {"code": 0, "data": {"following": 9, "follower": 101}},
            "navnum": {"code": 0, "data": {"video": 11, "audio": 2, "favourite": {"master": 4, "guest": 5}}},
            "setting": {"code": 0, "data": {"privacy": {"fav_video": 0}}},
        }
    )
    data = client.user_info("2")
    assert data["name"] == "User"
    assert data["level"] == 6
    assert data["counts"]["followers"] == 101
    assert data["counts"]["video"] == 11
    assert data["privacy"]["fav_video"] == 0


def test_user_videos_normalizes_space_vlist() -> None:
    client = FakeClient(
        {
            "videos": {
                "code": 0,
                "data": {
                    "page": {"count": 1},
                    "list": {
                        "vlist": [
                            {
                                "bvid": "BV1xx411c7mD",
                                "aid": 2,
                                "title": "<em>Title</em>",
                                "author": "User",
                                "mid": 3,
                                "play": 4,
                                "video_review": 5,
                                "created": 100,
                                "length": "01:00",
                            }
                        ]
                    },
                },
            }
        }
    )
    data = client.user_videos("2", limit=1)
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Title"
    assert data["items"][0]["url"] == "https://www.bilibili.com/video/BV1xx411c7mD/"
