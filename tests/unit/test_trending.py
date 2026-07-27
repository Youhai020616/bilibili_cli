from __future__ import annotations

import json

from click.testing import CliRunner

from bili_cli.api.client import BiliAPIClient
from bili_cli.commands import trending as trending_cmd
from bili_cli.errors import CaptchaRequiredError


class FakeClient(BiliAPIClient):
    def __init__(self) -> None:
        super().__init__(account="default", request_delay=0)
        self.calls: list[tuple[str, object]] = []

    def trending(self, *, count: int = 20, source: str = "popular", rid: int = 0):
        self.calls.append(("trending", (count, source, rid)))
        return {
            "source": source,
            "rid": rid,
            "items": [
                {
                    "title": "Demo",
                    "bvid": "BV1xx411c7mD",
                    "aid": 2,
                    "author": "Author",
                    "play": 123,
                    "duration": "01:00",
                }
            ],
        }

    def hot_search(self, *, count: int = 10):
        self.calls.append(("hot_search", count))
        return {
            "title": "Hot search",
            "trackid": "abc",
            "items": [
                {
                    "rank": 1,
                    "keyword": "AI",
                    "show_name": "AI",
                    "icon": "icon.png",
                    "goto": "search",
                    "uri": "uri",
                    "link": "https://search.bilibili.com/all?keyword=AI",
                }
            ],
        }

    def close(self) -> None:
        return None


def test_ranking_command_json(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(trending_cmd.BiliAPIClient, "from_config", classmethod(lambda cls, account=None: fake))
    runner = CliRunner()

    result = runner.invoke(trending_cmd.ranking, ["--rid", "36", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "ranking"
    assert payload["data"]["source"] == "ranking"
    assert fake.calls[0] == ("trending", (20, "ranking", 36))


def test_hot_search_command_json(monkeypatch) -> None:
    fake = FakeClient()
    monkeypatch.setattr(trending_cmd.BiliAPIClient, "from_config", classmethod(lambda cls, account=None: fake))
    runner = CliRunner()

    result = runner.invoke(trending_cmd.hot_search, ["--count", "1", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["command"] == "hot-search"
    assert payload["data"]["items"][0]["keyword"] == "AI"
    assert fake.calls[0] == ("hot_search", 1)


def test_ranking_command_falls_back_to_browser(monkeypatch) -> None:
    class CaptchaClient(FakeClient):
        def trending(self, *, count: int = 20, source: str = "popular", rid: int = 0):
            raise CaptchaRequiredError("-352")

    fake = CaptchaClient()
    monkeypatch.setattr(trending_cmd.BiliAPIClient, "from_config", classmethod(lambda cls, account=None: fake))
    monkeypatch.setattr(
        trending_cmd,
        "browser_ranking",
        lambda *, rid, account, limit: {"source": "ranking", "rid": rid, "items": [{"title": "Browser item"}]},
    )
    runner = CliRunner()

    result = runner.invoke(trending_cmd.ranking, ["--rid", "0", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["strategy"] == "browser"
    assert payload["fallback_used"] is True
    assert payload["data"]["items"][0]["title"] == "Browser item"
