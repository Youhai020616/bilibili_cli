from __future__ import annotations

import types

from bili_cli.browser import login as browser_login


def test_import_cookies_from_browser(monkeypatch) -> None:
    saved = {}

    class Cookie:
        def __init__(self, name: str, value: str):
            self.name = name
            self.value = value
            self.domain = ".bilibili.com"
            self.path = "/"
            self.expires = 0
            self.secure = True
            self._rest = {"HttpOnly": True}

    fake_browser_cookie3 = types.SimpleNamespace(chrome=lambda domain_name=None: [Cookie("SESSDATA", "abc"), Cookie("bili_jct", "def")])

    def fake_save_cookies(cookies, account=None):
        saved["cookies"] = cookies
        saved["account"] = account

    monkeypatch.setitem(__import__("sys").modules, "browser_cookie3", fake_browser_cookie3)
    monkeypatch.setattr(browser_login, "save_cookies", fake_save_cookies)

    result = browser_login.import_cookies_from_browser(account="default", browser_name="chrome")

    assert result["imported"] is True
    assert result["cookies"] == 2
    assert saved["account"] == "default"
    assert len(saved["cookies"]) == 2
