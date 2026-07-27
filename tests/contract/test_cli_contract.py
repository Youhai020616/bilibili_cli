from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

import bili_cli.commands.interact as interact_cmd
import bili_cli.commands.search as search_cmd
import bili_cli.commands.video as video_cmd
import bili_cli.commands.trending as trending_cmd


class FakeSearchClient:
    def __init__(self) -> None:
        self.closed = False

    def search(self, **_kwargs):
        return {
            "keyword": "AI",
            "type": "video",
            "items": [
                {
                    "title": "Demo",
                    "bvid": "BV1xx411c7mD",
                    "aid": 2,
                    "author": "Author",
                    "play": 123,
                    "duration": 60,
                }
            ],
        }

    def close(self) -> None:
        self.closed = True


class FakeVideoClient:
    def __init__(self) -> None:
        self.closed = False

    def comments(self, *_args, **_kwargs):
        return {
            "comments": [
                {
                    "rpid": 1,
                    "member": {"uname": "user"},
                    "message": "nice",
                    "like": 4,
                    "reply_count": 0,
                }
            ],
            "cursor": {"all_count": 1, "is_end": True},
        }

    def video_detail(self, *_args, **_kwargs):
        return {"bvid": "BV1xx411c7mD", "aid": 2, "title": "Demo", "url": "https://www.bilibili.com/video/BV1xx411c7mD/"}

    def close(self) -> None:
        self.closed = True


class FakeFavoriteClient:
    def favorite_resources(self, *_args, **_kwargs):
        return {
            "folder": {"id": 123, "title": "Folder", "media_count": 1},
            "page": 1,
            "limit": 20,
            "has_more": False,
            "items": [
                {
                    "type": "video",
                    "bvid": "BV1xx411c7mD",
                    "aid": 2,
                    "title": "Demo",
                    "author": "Author",
                    "play": 123,
                    "duration": 60,
                }
            ],
        }

    def close(self) -> None:
        return None


def _parse_json(output: str) -> dict[str, object]:
    return json.loads(output.strip())


def test_search_json_contract(monkeypatch) -> None:
    fake = FakeSearchClient()
    runner = CliRunner()
    monkeypatch.setattr(search_cmd.BiliAPIClient, "from_config", classmethod(lambda cls, account=None: fake))
    monkeypatch.setattr(search_cmd, "save_index", lambda *args, **kwargs: None)

    result = runner.invoke(search_cmd.search, ["AI", "--json"])

    assert result.exit_code == 0, result.output
    payload = _parse_json(result.output)
    assert payload["ok"] is True
    assert payload["schema_version"] == "1"
    assert payload["command"] == "search"
    assert payload["strategy"] == "api"
    assert payload["fallback_used"] is False
    assert payload["data"]["items"][0]["bvid"] == "BV1xx411c7mD"


def test_comments_json_contract(monkeypatch) -> None:
    fake = FakeVideoClient()
    runner = CliRunner()
    monkeypatch.setattr(video_cmd.BiliAPIClient, "from_config", classmethod(lambda cls, account=None: fake))

    result = runner.invoke(video_cmd.comments, ["BV1xx411c7mD", "--json"])

    assert result.exit_code == 0, result.output
    payload = _parse_json(result.output)
    assert payload["ok"] is True
    assert payload["schema_version"] == "1"
    assert payload["command"] == "comments"
    assert payload["strategy"] == "api"
    assert payload["data"]["comments"][0]["message"] == "nice"


def test_like_dry_run_contract(monkeypatch, tmp_path) -> None:
    fake = FakeVideoClient()
    runner = CliRunner()
    monkeypatch.setattr(interact_cmd.BiliAPIClient, "from_config", classmethod(lambda cls, account=None: fake))
    monkeypatch.setattr(interact_cmd, "write_audit_event", lambda **kwargs: Path(tmp_path / "audit.jsonl"))

    result = runner.invoke(interact_cmd.like, ["BV1xx411c7mD", "--json"])

    assert result.exit_code == 0, result.output
    payload = _parse_json(result.output)
    assert payload["ok"] is True
    assert payload["schema_version"] == "1"
    assert payload["command"] == "like"
    assert payload["data"]["dry_run"] is True
    assert payload["data"]["executed"] is False
    assert payload["data"]["next_action"].startswith("Re-run with --yes")


def test_favorite_items_json_contract(monkeypatch) -> None:
    fake = FakeFavoriteClient()
    runner = CliRunner()
    monkeypatch.setattr(interact_cmd.BiliAPIClient, "from_config", classmethod(lambda cls, account=None: fake))
    monkeypatch.setattr(interact_cmd, "save_index", lambda *args, **kwargs: None)

    result = runner.invoke(interact_cmd.favorite_items, ["123", "--json"])

    assert result.exit_code == 0, result.output
    payload = _parse_json(result.output)
    assert payload["ok"] is True
    assert payload["schema_version"] == "1"
    assert payload["command"] == "favorite.items"
    assert payload["strategy"] == "api"
    assert payload["data"]["items"][0]["bvid"] == "BV1xx411c7mD"


def test_hot_search_json_contract(monkeypatch) -> None:
    class FakeClient:
        def hot_search(self, *, count: int = 10):
            return {"title": "Hot", "trackid": "abc", "items": [{"rank": 1, "keyword": "AI", "show_name": "AI"}]}

        def close(self) -> None:
            return None

    fake = FakeClient()
    runner = CliRunner()
    monkeypatch.setattr(trending_cmd.BiliAPIClient, "from_config", classmethod(lambda cls, account=None: fake))

    result = runner.invoke(trending_cmd.hot_search, ["--json"])

    assert result.exit_code == 0, result.output
    payload = _parse_json(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "hot-search"
    assert payload["data"]["items"][0]["keyword"] == "AI"
