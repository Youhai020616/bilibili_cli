from __future__ import annotations

from bili_cli.errors import LoginRequiredError
from bili_cli.output import error_envelope, fmt_count, success_envelope


def test_success_envelope() -> None:
    data = success_envelope({"hello": "world"}, command="search", strategy="api", account="default")
    assert data["ok"] is True
    assert data["schema_version"] == "1"
    assert data["command"] == "search"
    assert data["strategy"] == "api"
    assert data["account"] == "default"
    assert data["data"] == {"hello": "world"}


def test_error_envelope() -> None:
    data = error_envelope(LoginRequiredError(), command="status", strategy="api")
    assert data["ok"] is False
    assert data["error"]["code"] == "LOGIN_REQUIRED"
    assert data["error"]["retryable"] is True
    assert "next_action" in data["error"]


def test_fmt_count() -> None:
    assert fmt_count(None) == "-"
    assert fmt_count(9999) == "9999"
    assert fmt_count(12000) == "1.2W"
