from __future__ import annotations

from typing import Any

from bili_cli.api.client import BiliAPIClient


class FakeClient(BiliAPIClient):
    def __init__(self, responses: dict[str, dict[str, Any]]):
        super().__init__(account="default", request_delay=0)
        self.responses = responses

    def get_json(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
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
