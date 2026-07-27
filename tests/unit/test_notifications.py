from __future__ import annotations

from typing import Any

from bili_cli import constants
from bili_cli.api.client import BiliAPIClient


class FakeClient(BiliAPIClient):
    def __init__(self, responses: dict[str, dict[str, Any]]):
        super().__init__(account="default", request_delay=0)
        self.responses = responses

    def get_json(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        if url == constants.MSGFEED_UNREAD_URL:
            return self.responses["unread"]
        if url == constants.VC_SESSION_LIST_URL:
            return self.responses["sessions"]
        raise AssertionError(f"Unexpected URL: {url}")


def test_notifications_normalize_counts() -> None:
    client = FakeClient({"unread": {"code": 0, "data": {"reply": 1, "like": 2, "msg": 3}}})
    data = client.notifications()
    assert data["counts"]["reply"] == 1
    assert data["counts"]["like"] == 2


def test_messages_normalize_sessions() -> None:
    client = FakeClient(
        {
            "sessions": {
                "code": 0,
                "data": {
                    "session_list": [
                        {
                            "talker_id": 2,
                            "nickname": "User",
                            "unread_count": 4,
                            "last_msg": {"content": "hello"},
                            "session_ts": 123,
                        }
                    ]
                },
            }
        }
    )
    data = client.messages(limit=1)
    assert data["items"][0]["nickname"] == "User"
    assert data["items"][0]["last_text"] == "hello"
